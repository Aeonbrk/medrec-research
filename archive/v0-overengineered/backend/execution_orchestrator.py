"""Durable execution orchestration, worker dispatch, transport supervision, and evidence intake."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from ._validation import (
    require_identifier,
    strict_fields,
    write_json_atomic,
)
from .action_gate import ActionRequest
from .aris_bridge import ArisBridge, ArisRevisionRecord
from .aris_transport import (
    ArisTransportManifest,
    ArisTransportReceipt,
    ArisTransportStatus,
    FixedArisTransport,
    transport_package_sha256,
)
from .errors import ProtocolValidationError
from .execution_control import (
    DurableExecutionQueue,
    ExecutionDeclaration,
    ExecutionDeclarationRegistry,
    ExecutionRecord,
    ExecutionState,
)
from .execution_evidence import (
    EvidenceReceipt,
    MonitorObservation,
    RestrictedEvidenceInput,
    assemble_decision_packet,
)
from .execution_worker import DeclarationBoundWorker, ExecutionSubmission
from .remote_preflight import RemoteSessionPreflight
from .reproduction_contract import (
    DecisionPacket,
    H1Approval,
    H2Decision,
    SafeDrugBatchContract,
)

Clock = Callable[[], datetime]


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    from hashlib import sha256

    return sha256(path.read_bytes()).hexdigest()


def _load_optional(path: Path, loader: Callable[[str], Any]) -> Any | None:
    if not path.is_file():
        return None
    try:
        return loader(path.read_text(encoding="utf-8"))
    except (ProtocolValidationError, OSError, UnicodeError):
        return None


class ExecutionOrchestrator:
    """Orchestrate durable execution queues, transport recovery, and evidence intake."""

    def __init__(self, *, root: Path) -> None:
        self.root = root
        self._lock = RLock()
        self._last_transport_poll: datetime | None = None

    def _bound_execution(
        self,
        request_sha256: str,
        declaration_sha256: str,
        remote_revision: str,
        *,
        execution_queue: DurableExecutionQueue,
        execution_registry: ExecutionDeclarationRegistry,
        action_request_dir: Path,
    ) -> tuple[ExecutionRecord, ExecutionDeclaration]:
        record = execution_queue.load(request_sha256)
        declaration = execution_registry.get(record.lane_id, record.action_id)
        if (
            record.declaration_sha256 != declaration_sha256
            or declaration.declaration_sha256 != declaration_sha256
        ):
            raise ProtocolValidationError("execution declaration binding changed")
        request_path = action_request_dir / f"{request_sha256}.json"
        try:
            request = ActionRequest.from_json(request_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ProtocolValidationError) as error:
            raise ProtocolValidationError("bound Action Request is unavailable") from error
        if (
            request.request_sha256 != record.request_sha256
            or request.action_id != record.action_id
            or request.project_id != declaration.project_id
            or request.target_id != declaration.target_id
            or request.remote_revision != remote_revision
        ):
            raise ProtocolValidationError("execution authority binding changed")
        return record, declaration

    def _execution_binding(
        self,
        action_id: str,
        *,
        execution_queue: DurableExecutionQueue,
        execution_registry: ExecutionDeclarationRegistry,
        contract: SafeDrugBatchContract | None,
        h1: H1Approval | None,
        packets: list[DecisionPacket],
        decisions: dict[str, H2Decision],
    ) -> tuple[SafeDrugBatchContract, H1Approval, str | None, str]:
        if contract is None or h1 is None or not h1.is_current(contract):
            raise ProtocolValidationError("execution requires current H1 authority")
        current_records = [
            record
            for record in execution_queue.records()
            if record.contract_sha256 == contract.contract_sha256
            and record.h1_approval_sha256 == h1.approval_sha256
        ]
        current_record = (
            max(current_records, key=lambda record: record.events[-1].journal_sequence)
            if current_records
            else None
        )
        current_lane_id = (
            current_record.lane_id
            if current_record is not None
            else execution_registry.initial_lane_id
        )
        packets_by_lane = {packet.lane_id: packet for packet in packets}
        packet = packets_by_lane.get(current_lane_id)
        decision = decisions.get(current_lane_id)
        if decision is not None and (
            packet is None or not decision.is_current(contract=contract, packet=packet)
        ):
            decision = None
        if action_id != "request_next_lane":
            if decision is not None:
                raise ProtocolValidationError("decided lane cannot continue execution")
            return (
                contract,
                h1,
                current_record.h2_decision_sha256 if current_record is not None else None,
                current_lane_id,
            )
        if decision is None or not decision.go_eligible:
            raise ProtocolValidationError("next lane requires current H2 GO")
        lane_ids = execution_registry.lane_ids
        try:
            lane_id = lane_ids[lane_ids.index(current_lane_id) + 1]
        except (ValueError, IndexError) as error:
            raise ProtocolValidationError("no next registered execution lane") from error
        return contract, h1, decision.decision_sha256, lane_id

    def queue_action_request(
        self,
        value: Mapping[str, object],
        *,
        execution_queue: DurableExecutionQueue,
        execution_registry: ExecutionDeclarationRegistry,
        aris_transport: FixedArisTransport,
        action_request_dir: Path,
        submission_dir: Path,
        transport_manifest_dir: Path,
        contract_path: Path,
        aris_bridge: ArisBridge,
        contract: SafeDrugBatchContract | None,
        h1: H1Approval | None,
        packets: list[DecisionPacket],
        decisions: dict[str, H2Decision],
        preflight: RemoteSessionPreflight | None,
        aris_revision: ArisRevisionRecord | None,
        clock: Clock,
    ) -> dict[str, object]:
        """Enqueue one validated action request bound to current H1 authority."""
        request = ActionRequest.from_dict(value)
        contract_item, h1_item, h2_decision_sha256, lane_id = self._execution_binding(
            request.action_id,
            execution_queue=execution_queue,
            execution_registry=execution_registry,
            contract=contract,
            h1=h1,
            packets=packets,
            decisions=decisions,
        )
        declaration = execution_registry.get(lane_id, request.action_id)
        action_request_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(
            action_request_dir / f"{request.request_sha256}.json",
            request.to_dict(),
        )
        record = execution_queue.enqueue(
            request=request,
            declaration=declaration,
            contract_sha256=contract_item.contract_sha256,
            h1_approval_sha256=h1_item.approval_sha256,
            h2_decision_sha256=h2_decision_sha256,
            blockers=(preflight.blockers if preflight is not None else ("preflight-missing",)),
        )
        self.dispatch_pending(
            execution_queue=execution_queue,
            execution_registry=execution_registry,
            aris_transport=aris_transport,
            action_request_dir=action_request_dir,
            submission_dir=submission_dir,
            transport_manifest_dir=transport_manifest_dir,
            contract_path=contract_path,
            aris_bridge=aris_bridge,
            preflight=preflight,
            aris_revision=aris_revision,
            clock=clock,
        )
        return execution_queue.load(record.request_sha256).to_public_dict()

    def dispatch_pending(
        self,
        *,
        execution_queue: DurableExecutionQueue,
        execution_registry: ExecutionDeclarationRegistry,
        aris_transport: FixedArisTransport,
        action_request_dir: Path,
        submission_dir: Path,
        transport_manifest_dir: Path,
        contract_path: Path,
        aris_bridge: ArisBridge,
        preflight: RemoteSessionPreflight | None,
        aris_revision: ArisRevisionRecord | None,
        clock: Clock,
    ) -> tuple[ExecutionSubmission, ...]:
        """Prepare worker envelopes and submit queued records to ARIS transport."""
        with self._lock:
            worker = DeclarationBoundWorker(
                execution_queue,
                action_request_dir,
                submission_dir,
                clock=clock,
            )
            prepared = []
            for record in execution_queue.records():
                if record.state is not ExecutionState.QUEUED:
                    continue
                try:
                    declaration = execution_registry.get(record.lane_id, record.action_id)
                    submission = worker.prepare(
                        record,
                        declaration,
                        aris_revision=aris_revision,
                    )
                    prepared.append(submission)
                    if submission.status != "awaiting-aris-bridge":
                        continue
                    manifest = self._transport_manifest(
                        record,
                        submission,
                        declaration,
                        aris_transport=aris_transport,
                        transport_manifest_dir=transport_manifest_dir,
                        contract_path=contract_path,
                        aris_bridge=aris_bridge,
                        preflight=preflight,
                        aris_revision=aris_revision,
                    )
                    receipt = aris_transport.submit(
                        manifest,
                        fallback_used=preflight.fallback_used if preflight else False,
                    )
                    self._apply_transport_receipt(execution_queue, record, receipt)
                except ProtocolValidationError:
                    current = execution_queue.load(record.request_sha256)
                    if current.state is ExecutionState.QUEUED:
                        execution_queue.transition(
                            record.request_sha256,
                            state=ExecutionState.REVIEW_PENDING,
                            reason_code="execution-dispatch-invalid",
                        )
            return tuple(prepared)

    def _transport_manifest(
        self,
        record: ExecutionRecord,
        submission: ExecutionSubmission,
        declaration: ExecutionDeclaration,
        *,
        aris_transport: FixedArisTransport,
        transport_manifest_dir: Path,
        contract_path: Path,
        aris_bridge: ArisBridge,
        preflight: RemoteSessionPreflight | None,
        aris_revision: ArisRevisionRecord | None,
    ) -> ArisTransportManifest:
        if preflight is None or preflight.blockers:
            raise ProtocolValidationError("ARIS transport requires a clear remote preflight")
        if not preflight.environment_verified:
            raise ProtocolValidationError("ARIS transport requires a verified remote environment")
        if aris_revision is None or not aris_revision.candidate_valid:
            raise ProtocolValidationError("ARIS transport requires a valid ARIS revision")
        if aris_revision.active_revision is None:
            raise ProtocolValidationError("ARIS transport requires an active ARIS revision")
        contract = _load_optional(contract_path, SafeDrugBatchContract.from_json)
        if contract is None or contract.contract_sha256 != record.contract_sha256:
            raise ProtocolValidationError("ARIS transport contract binding changed")
        contract_values = contract.to_dict()
        stopping_rules = contract_values["stopping_rules"]
        resource_ceiling = contract_values["resource_ceiling"]
        if not isinstance(stopping_rules, Mapping) or not isinstance(resource_ceiling, Mapping):
            raise ProtocolValidationError("ARIS transport resource authority is invalid")
        max_attempts = stopping_rules.get("max_attempts")
        gpu_count = resource_ceiling.get("gpu_count")
        if type(max_attempts) is not int or max_attempts < 1:
            raise ProtocolValidationError("ARIS transport max_attempts is invalid")
        if type(gpu_count) is not int or gpu_count < 1:
            raise ProtocolValidationError("ARIS transport gpu_count is invalid")
        policy_sha256 = aris_transport.registry.policy_sha256
        queue_manager_rel = aris_transport.registry.queue_manager_relative
        manifest = ArisTransportManifest(
            request_sha256=record.request_sha256,
            submission_sha256=submission.submission_sha256,
            declaration_sha256=declaration.declaration_sha256,
            contract_sha256=record.contract_sha256,
            h1_approval_sha256=record.h1_approval_sha256,
            preflight_sha256=preflight.preflight_sha256,
            transport_policy_sha256=policy_sha256,
            transport_package_sha256=transport_package_sha256(),
            queue_manager_sha256=_sha256_file(aris_bridge.repository / queue_manager_rel),
            aris_revision=aris_revision.active_revision,
            project_id=declaration.project_id,
            target_id=declaration.target_id,
            lane_id=declaration.lane_id,
            action_id=declaration.action_id,
            source_revision=declaration.source_revision,
            environment_id=declaration.environment_id,
            resource_profile_id=declaration.resource_profile_id,
            command_template_id=declaration.command_template_id,
            launch_template_id=declaration.launch_template_id,
            evidence_schema_id=declaration.evidence_schema_id,
            source_path_id=declaration.source_path_id,
            data_path_id=declaration.data_path_id,
            output_path_id=declaration.output_path_id,
            max_attempts=max_attempts,
            gpu_count=gpu_count,
        )
        transport_manifest_dir.mkdir(parents=True, exist_ok=True)
        path = transport_manifest_dir / f"{record.request_sha256}.json"
        if path.is_file():
            existing = ArisTransportManifest.from_json(path.read_text(encoding="utf-8"))
            if existing.to_dict() != manifest.to_dict():
                raise ProtocolValidationError("ARIS transport manifest conflicts with history")
            return existing
        write_json_atomic(path, manifest.to_dict())
        return manifest

    def _load_transport_manifest(
        self,
        request_sha256: str,
        *,
        transport_manifest_dir: Path,
    ) -> ArisTransportManifest:
        try:
            return ArisTransportManifest.from_json(
                (transport_manifest_dir / f"{request_sha256}.json").read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, ProtocolValidationError) as error:
            raise ProtocolValidationError("ARIS transport manifest is unavailable") from error

    def _apply_transport_receipt(
        self,
        execution_queue: DurableExecutionQueue,
        record: ExecutionRecord,
        receipt: ArisTransportReceipt,
        *,
        recovering: bool = False,
    ) -> ExecutionRecord:
        if receipt.request_sha256 != record.request_sha256:
            raise ProtocolValidationError("ARIS transport receipt request binding changed")
        paths = {
            ArisTransportStatus.ACCEPTED: (ExecutionState.SUBMITTING,),
            ArisTransportStatus.PENDING: (ExecutionState.SUBMITTING,),
            ArisTransportStatus.RUNNING: (
                ExecutionState.SUBMITTING,
                ExecutionState.RUNNING,
                ExecutionState.MONITORING,
            ),
            ArisTransportStatus.COMPLETED: (
                ExecutionState.SUBMITTING,
                ExecutionState.RUNNING,
                ExecutionState.MONITORING,
                ExecutionState.INTAKE,
            ),
            ArisTransportStatus.FAILED: (ExecutionState.REVIEW_PENDING,),
            ArisTransportStatus.TRANSPORT_FAILURE: (ExecutionState.REVIEW_PENDING,),
            ArisTransportStatus.STUCK: (ExecutionState.STUCK,),
            ArisTransportStatus.CANCELLED: (ExecutionState.CANCELLED,),
        }
        target_path = paths[receipt.status]
        current = execution_queue.load(record.request_sha256)
        if current.state in {
            ExecutionState.COMPLETED,
            ExecutionState.CANCELLED,
            ExecutionState.FAILED,
            ExecutionState.STUCK,
        }:
            return current
        for target in target_path:
            current = execution_queue.load(record.request_sha256)
            if current.state is target:
                continue
            if target is ExecutionState.SUBMITTING:
                allowed = {ExecutionState.QUEUED}
                if recovering:
                    allowed.add(ExecutionState.REVIEW_PENDING)
                if current.state not in allowed:
                    continue
            if target is ExecutionState.RUNNING and current.state is not ExecutionState.SUBMITTING:
                continue
            if target is ExecutionState.MONITORING and current.state is not ExecutionState.RUNNING:
                continue
            if target is ExecutionState.INTAKE and current.state is not ExecutionState.MONITORING:
                continue
            current = execution_queue.transition(
                record.request_sha256,
                state=target,
                reason_code=(
                    receipt.reason_code if target is target_path[-1] else "aris-state-observed"
                ),
            )
        return current

    def advance_transport(
        self,
        *,
        execution_queue: DurableExecutionQueue,
        aris_transport: FixedArisTransport,
        transport_manifest_dir: Path,
        preflight: RemoteSessionPreflight | None,
        clock: Clock,
        dispatch_fn: Callable[[], None] | None = None,
        force: bool = False,
    ) -> tuple[dict[str, object], ...]:
        """Poll and advance active transport items."""
        with self._lock:
            now = clock()
            if now.tzinfo is None:
                raise ProtocolValidationError("ARIS transport clock must be aware")
            if (
                not force
                and self._last_transport_poll is not None
                and (now - self._last_transport_poll).total_seconds()
                < aris_transport.registry.poll_seconds
            ):
                return ()
            self._last_transport_poll = now
            if dispatch_fn:
                dispatch_fn()
            updated = []
            fallback_used = preflight.fallback_used if preflight else False
            for receipt in aris_transport.records():
                record = execution_queue.load(receipt.request_sha256)
                if record.state not in {
                    ExecutionState.SUBMITTING,
                    ExecutionState.RUNNING,
                    ExecutionState.MONITORING,
                }:
                    continue
                try:
                    manifest = self._load_transport_manifest(
                        receipt.request_sha256,
                        transport_manifest_dir=transport_manifest_dir,
                    )
                    observed = aris_transport.monitor(
                        manifest,
                        fallback_used=fallback_used,
                    )
                    current = self._apply_transport_receipt(execution_queue, record, observed)
                except ProtocolValidationError:
                    current = execution_queue.load(record.request_sha256)
                    if current.state in {
                        ExecutionState.SUBMITTING,
                        ExecutionState.RUNNING,
                        ExecutionState.MONITORING,
                    }:
                        current = execution_queue.transition(
                            record.request_sha256,
                            state=ExecutionState.REVIEW_PENDING,
                            reason_code="execution-monitor-invalid",
                        )
                updated.append(current.to_public_dict())
            return tuple(updated)

    def cancel_transport(
        self,
        request_sha256: str,
        *,
        execution_queue: DurableExecutionQueue,
        aris_transport: FixedArisTransport,
        transport_manifest_dir: Path,
        preflight: RemoteSessionPreflight | None,
    ) -> dict[str, object]:
        """Cancel one active transport request."""
        with self._lock:
            manifest = self._load_transport_manifest(
                request_sha256,
                transport_manifest_dir=transport_manifest_dir,
            )
            existing = aris_transport.load(request_sha256)
            recovering = bool(
                existing is not None and existing.status is ArisTransportStatus.TRANSPORT_FAILURE
            )
            fallback_used = preflight.fallback_used if preflight else False
            receipt = aris_transport.cancel(manifest, fallback_used=fallback_used)
            record = execution_queue.load(request_sha256)
            return self._apply_transport_receipt(
                execution_queue,
                record,
                receipt,
                recovering=recovering,
            ).to_public_dict()

    def resume_transport(
        self,
        request_sha256: str,
        *,
        execution_queue: DurableExecutionQueue,
        aris_transport: FixedArisTransport,
        transport_manifest_dir: Path,
        preflight: RemoteSessionPreflight | None,
    ) -> dict[str, object]:
        """Perform one explicit, manifest-bound recovery attempt."""
        with self._lock:
            manifest = self._load_transport_manifest(
                request_sha256,
                transport_manifest_dir=transport_manifest_dir,
            )
            fallback_used = preflight.fallback_used if preflight else False
            receipt = aris_transport.resume(manifest, fallback_used=fallback_used)
            record = execution_queue.load(request_sha256)
            return self._apply_transport_receipt(
                execution_queue,
                record,
                receipt,
                recovering=True,
            ).to_public_dict()

    def control_transport(
        self,
        value: Mapping[str, object],
        *,
        execution_queue: DurableExecutionQueue,
        aris_transport: FixedArisTransport,
        transport_manifest_dir: Path,
        preflight: RemoteSessionPreflight | None,
    ) -> dict[str, object]:
        """Resolve one opaque browser request to a fixed transport operation."""
        payload = strict_fields(
            value,
            required=("kind", "operation", "request_id", "schema_version"),
            context="transport control input",
        )
        if payload.pop("kind") != "transport_control_input" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("transport control input schema is invalid")
        request_id = require_identifier(
            payload.pop("request_id"),
            field="transport_control.request_id",
        )
        operation = payload.pop("operation")
        if operation not in {"cancel", "resume"}:
            raise ProtocolValidationError("transport control operation is not fixed")
        records = [
            record for record in execution_queue.records() if record.request_id == request_id
        ]
        if len(records) != 1:
            raise ProtocolValidationError("transport control request is unavailable")
        record = records[0]
        receipt = aris_transport.load(record.request_sha256)
        if receipt is None:
            raise ProtocolValidationError("transport control receipt is unavailable")
        if operation == "resume":
            recovery_ready = (
                record.state is ExecutionState.REVIEW_PENDING
                and receipt.status is ArisTransportStatus.TRANSPORT_FAILURE
            )
            recovery_replayed = receipt.status is not ArisTransportStatus.TRANSPORT_FAILURE and any(
                event.state is ExecutionState.REVIEW_PENDING
                and event.reason_code.startswith("aris-transport-")
                for event in record.events[:-1]
            )
            if not recovery_ready and not recovery_replayed:
                raise ProtocolValidationError("transport recovery is not permitted")
            updated = (
                record.to_public_dict()
                if recovery_replayed
                else self.resume_transport(
                    record.request_sha256,
                    execution_queue=execution_queue,
                    aris_transport=aris_transport,
                    transport_manifest_dir=transport_manifest_dir,
                    preflight=preflight,
                )
            )
        else:
            active_states = {
                ExecutionState.SUBMITTING,
                ExecutionState.RUNNING,
                ExecutionState.MONITORING,
            }
            terminal_receipt = receipt.status in {
                ArisTransportStatus.COMPLETED,
                ArisTransportStatus.FAILED,
                ArisTransportStatus.STUCK,
                ArisTransportStatus.CANCELLED,
            }
            if (
                record.state not in active_states
                and not (
                    record.state is ExecutionState.REVIEW_PENDING
                    and receipt.status is ArisTransportStatus.TRANSPORT_FAILURE
                )
                and not terminal_receipt
            ):
                raise ProtocolValidationError("transport cancellation is not permitted")
            updated = self.cancel_transport(
                record.request_sha256,
                execution_queue=execution_queue,
                aris_transport=aris_transport,
                transport_manifest_dir=transport_manifest_dir,
                preflight=preflight,
            )
        return {
            "kind": "transport_control_result",
            "operation": operation,
            "record": updated,
            "request_id": request_id,
            "schema_version": 1,
            "status": "applied",
        }

    def apply_monitor_observation(
        self,
        value: Mapping[str, object],
        *,
        execution_queue: DurableExecutionQueue,
        execution_registry: ExecutionDeclarationRegistry,
        action_request_dir: Path,
        preflight: RemoteSessionPreflight | None,
    ) -> dict[str, object]:
        """Apply one public-safe monitor observation to active execution."""
        observation = MonitorObservation.from_dict(value)
        _record, declaration = self._bound_execution(
            observation.request_sha256,
            observation.declaration_sha256,
            observation.remote_revision,
            execution_queue=execution_queue,
            execution_registry=execution_registry,
            action_request_dir=action_request_dir,
        )
        if declaration.declaration_sha256 != observation.declaration_sha256:
            raise ProtocolValidationError("declaration digest does not match observation")
        if preflight is None or preflight.remote_revision != observation.remote_revision:
            raise ProtocolValidationError("remote revision does not match observation")
        if not observation.authority_ok:
            updated = execution_queue.transition(
                observation.request_sha256,
                state=ExecutionState.CANCELLED,
                reason_code=observation.reason_code,
            )
            return updated.to_public_dict()
        if not (observation.privacy_ok and observation.resource_ok and observation.integrity_ok):
            updated = execution_queue.transition(
                observation.request_sha256,
                state=ExecutionState.REVIEW_PENDING,
                reason_code=observation.reason_code,
            )
            return updated.to_public_dict()
        updated = execution_queue.transition(
            observation.request_sha256,
            state=observation.state,
            reason_code=observation.reason_code,
        )
        return updated.to_public_dict()

    def intake_reproduction_evidence(
        self,
        value: Mapping[str, object],
        *,
        execution_queue: DurableExecutionQueue,
        execution_registry: ExecutionDeclarationRegistry,
        action_request_dir: Path,
        packet_dir: Path,
        evidence_dir: Path,
        contract_path: Path,
        h1_path: Path,
        preflight: RemoteSessionPreflight | None,
        clock: Clock,
        on_success: Callable[[], None] | None = None,
    ) -> dict[str, object]:
        """Intake restricted aggregate evidence and assemble a Decision Packet."""
        evidence = RestrictedEvidenceInput.from_dict(value)
        with self._lock:
            record, declaration = self._bound_execution(
                evidence.request_sha256,
                evidence.declaration_sha256,
                evidence.remote_revision,
                execution_queue=execution_queue,
                execution_registry=execution_registry,
                action_request_dir=action_request_dir,
            )
            contract = _load_optional(contract_path, SafeDrugBatchContract.from_json)
            h1 = _load_optional(h1_path, H1Approval.from_json)
            if contract is None or h1 is None or not h1.is_current(contract):
                raise ProtocolValidationError("evidence intake requires current H1 authority")
            if (
                record.contract_sha256 != contract.contract_sha256
                or record.h1_approval_sha256 != h1.approval_sha256
            ):
                raise ProtocolValidationError("evidence intake authority binding changed")
            evidence_dir.mkdir(parents=True, exist_ok=True)
            receipt_path = evidence_dir / f"{evidence.request_sha256}.json"
            if receipt_path.is_file():
                receipt = _load_optional(receipt_path, EvidenceReceipt.from_json)
                if (
                    receipt is None
                    or receipt.request_sha256 != evidence.request_sha256
                    or receipt.evidence_sha256 != evidence.evidence_sha256
                ):
                    raise ProtocolValidationError("evidence intake conflicts with history")
                packet = _load_optional(
                    packet_dir / f"{record.lane_id}.json",
                    DecisionPacket.from_json,
                )
                if packet is None or packet.packet_sha256 != receipt.packet_sha256:
                    raise ProtocolValidationError("evidence receipt packet is unavailable")
                if record.state is ExecutionState.INTAKE:
                    execution_queue.transition(
                        record.request_sha256,
                        state=ExecutionState.REVIEW_PENDING,
                        reason_code="decision-packet-ready",
                    )
                    if on_success:
                        on_success()
                elif record.state is not ExecutionState.REVIEW_PENDING:
                    raise ProtocolValidationError("evidence intake replay state is invalid")
                return packet.to_dict()
            if record.state is not ExecutionState.INTAKE:
                raise ProtocolValidationError("evidence intake requires intake execution state")
            packet_path = packet_dir / f"{record.lane_id}.json"
            if packet_path.is_file():
                raise ProtocolValidationError("execution lane already has a Decision Packet")
            accepted_at = _timestamp(clock())
            packet, receipt = assemble_decision_packet(
                evidence=evidence,
                contract=contract,
                declaration=declaration,
                accepted_at=accepted_at,
            )
            packet_dir.mkdir(parents=True, exist_ok=True)
            write_json_atomic(packet_path, packet.to_dict())
            write_json_atomic(receipt_path, receipt.to_dict())
            execution_queue.transition(
                record.request_sha256,
                state=ExecutionState.REVIEW_PENDING,
                reason_code="decision-packet-ready",
            )
            if on_success:
                on_success()
            return packet.to_dict()


__all__ = ("ExecutionOrchestrator",)
