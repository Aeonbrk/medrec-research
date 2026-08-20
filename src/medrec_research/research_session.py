"""One-command coordinator for a real, fail-closed HITL research session."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Any

from ._validation import (
    content_sha256,
    strict_fields,
    write_json_atomic,
)
from .action_gate import AuthorityBundle
from .agent_team_bridge import AgentTeamBridge
from .aris_bridge import ArisBridge, ArisRevisionRecord
from .aris_transport import (
    ArisTransportManifest,
    ArisTransportReceipt,
    FixedArisTransport,
)
from .baseline_audit import BaselineAudit, BaselineProgram
from .contract_store import ResearchContractStore
from .errors import ProtocolValidationError
from .execution_control import (
    DurableExecutionQueue,
    ExecutionDeclaration,
    ExecutionDeclarationRegistry,
    ExecutionRecord,
)
from .execution_orchestrator import ExecutionOrchestrator
from .execution_worker import ExecutionSubmission
from .project_status import (
    AuthorityDigest,
    BlockerCategory,
    CandidateStatus,
    EvidenceLink,
    MedRecStatus,
    ProjectStage,
    ProjectStatus,
    StatusBlocker,
    _project_lineage,
)
from .registry import BaselineRegistry
from .remote_preflight import RemoteSessionPreflight, run_remote_preflight
from .reproduction_contract import DecisionPacket, H1Approval, H2Decision, SafeDrugBatchContract
from .research_loop_status import ResearchLoopStatus

Clock = Callable[[], datetime]
RunCommand = Callable[..., subprocess.CompletedProcess[str]]


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    from hashlib import sha256

    return sha256(path.read_bytes()).hexdigest()


def _immutable_revision(value: str | None) -> str | None:
    if (
        value is None
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        return None
    return value


def _git_value(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _load_optional(path: Path, loader: Callable[[str], Any]) -> Any | None:
    if not path.is_file():
        return None
    try:
        return loader(path.read_text(encoding="utf-8"))
    except (ProtocolValidationError, OSError, UnicodeError):
        return None


class ResearchSession:
    """Coordinating facade over preflight, contract store, orchestrator, and status broadcast."""

    def __init__(self, root: Path, *, clock: Clock, runtime: Path | None = None) -> None:
        self.root = root.resolve()
        self.clock = clock
        self.runtime = (self.root / "runtime" / "hitl") if runtime is None else runtime.resolve()
        self.status_path = self.runtime / "status.json"
        self.loop_path = self.runtime / "research-loop.json"
        self.action_context_path = self.runtime / "action-context.json"
        self.authority_bundle_path = self.runtime / "authority-bundle.json"
        self.contract_path = (
            self.root / "research" / "hitl-control-console" / "research-contract.md"
        )
        self.h1_path = self.runtime / "h1-approval.json"
        self.h2_dir = self.runtime / "h2-decisions"
        self.packet_dir = self.runtime / "decision-packets"
        self.evidence_dir = self.runtime / "evidence-receipts"
        self.action_request_dir = self.runtime / "action-requests"
        self.submission_dir = self.runtime / "submissions"
        self.transport_manifest_dir = self.runtime / "transport-manifests"
        self.execution_queue_dir = self.runtime / "execution-queue"
        self.execution_dir = self.runtime / "executions"
        self.aris_state_path = self.runtime / "aris-revision.json"

        self.execution_registry = ExecutionDeclarationRegistry.load_package()
        self.execution_queue = DurableExecutionQueue(
            self.execution_queue_dir,
            clock=self.clock,
        )
        self.aris_transport = FixedArisTransport(
            self.runtime / "aris-transport",
            clock=self.clock,
        )
        self.aris_bridge = ArisBridge(
            self._aris_repository_from_manifest(),
            manifest_path=self.root / ".aris" / "installed-skills-codex.txt",
            state_path=self.aris_state_path,
            clock=self.clock,
        )
        self.ai_bridge = AgentTeamBridge(
            self.root,
            runner=subprocess.run,
        )
        self.contract_store = ResearchContractStore()
        self.orchestrator = ExecutionOrchestrator(root=self.root)
        self.preflight: RemoteSessionPreflight | None = None
        self.aris_revision: ArisRevisionRecord | None = None
        self._actions_enabled: bool | None = None
        self._lock = RLock()

    @property
    def actions_enabled(self) -> bool:
        if self._actions_enabled is not None:
            return self._actions_enabled
        auth = self.authority_bundle()
        if auth is None:
            return False
        return (
            self.preflight is not None
            and self.preflight.reachable
            and self.preflight.identity_ok
            and self.preflight.checkout_clean
            and not self.preflight.blockers
        )

    @actions_enabled.setter
    def actions_enabled(self, value: bool | None) -> None:
        self._actions_enabled = value

    def prepare(self, *, timeout_seconds: int = 12) -> tuple[ProjectStatus, ResearchLoopStatus]:
        self.runtime.mkdir(parents=True, exist_ok=True)
        local_revision = _git_value(self.root, "rev-parse", "HEAD")
        self.preflight = run_remote_preflight(
            local_revision=local_revision,
            clock=self.clock,
            timeout_seconds=timeout_seconds,
        )
        self.aris_revision = self.aris_bridge.activate()
        self._dispatch_pending()
        status = self._publish_status(local_revision)
        loop = self.refresh_loop()
        return status, loop

    def _dispatch_pending(self) -> tuple[ExecutionSubmission, ...]:
        return self.orchestrator.dispatch_pending(
            execution_queue=self.execution_queue,
            execution_registry=self.execution_registry,
            action_request_dir=self.action_request_dir,
            submission_dir=self.submission_dir,
            transport_manifest_dir=self.transport_manifest_dir,
            contract_path=self.contract_path,
            aris_bridge=self.aris_bridge,
            preflight=self.preflight,
            aris_revision=self.aris_revision,
            clock=self.clock,
        )

    def _authoritative_inputs(
        self,
    ) -> tuple[BaselineProgram, tuple[BaselineAudit, ...], BaselineRegistry]:
        program = BaselineProgram.load(self.root / "baselines" / "programs" / "final-five.toml")
        audits = tuple(
            BaselineAudit.load(self.root / "baselines" / "audits" / f"{candidate_id}.toml")
            for candidate_id in program.candidate_ids
        )
        registry = BaselineRegistry.load(self.root / "baselines" / "registry.toml")
        return program, audits, registry

    def _aris_repository_from_manifest(self) -> Path:
        manifest_path = self.root / ".aris" / "installed-skills-codex.txt"
        if not manifest_path.is_file():
            return Path("/Users/oian/Codes/master/Auto-claude-code-research-in-sleep")
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("\t")
            if separator and key.strip() == "repo_root":
                return Path(value.strip())
        return Path("/Users/oian/Codes/master/Auto-claude-code-research-in-sleep")

    def _aris_manifest(self) -> tuple[str | None, tuple[str, ...]]:
        manifest_path = self.root / ".aris" / "installed-skills-codex.txt"
        if not manifest_path.is_file():
            return None, ("aris-manifest-missing",)
        try:
            digest = _sha256_file(manifest_path)
        except ProtocolValidationError:
            return None, ("aris-manifest-unreadable",)
        blockers: list[str] = []
        if self.aris_revision is None or not self.aris_revision.candidate_valid:
            blockers.append("aris-candidate-unverified")
        if self.aris_revision is not None and self.aris_revision.fallback_used:
            blockers.append("aris-candidate-fallback")
        return digest, tuple(blockers)

    def _publish_status(self, local_revision: str | None) -> ProjectStatus:
        if self.preflight is None:
            raise ProtocolValidationError("preflight must run before publishing status")
        program, audits, registry = self._authoritative_inputs()
        audits_by_baseline = {audit.baseline_id: audit for audit in audits}
        candidates = tuple(
            CandidateStatus(
                candidate_id=candidate_id,
                display_name=registry.get(candidate_id).display_name,
                readiness=registry.get(candidate_id).readiness.value,
                source_gate=audits_by_baseline[candidate_id].claim("source").disposition.value,
                license_gate=audits_by_baseline[candidate_id].claim("license").disposition.value,
                evidence=tuple(
                    EvidenceLink(item.evidence_id, item.immutable_url)
                    for item in audits_by_baseline[candidate_id].evidence
                ),
            )
            for candidate_id in program.candidate_ids
        )
        blockers: list[StatusBlocker] = []
        for candidate in candidates:
            if candidate.source_gate != "pass":
                blockers.append(
                    StatusBlocker(
                        BlockerCategory.SOURCE_LICENSE,
                        "source-gate-unresolved",
                        candidate.candidate_id,
                    )
                )
            if candidate.license_gate != "pass":
                blockers.append(
                    StatusBlocker(
                        BlockerCategory.SOURCE_LICENSE,
                        "license-gate-unresolved",
                        candidate.candidate_id,
                    )
                )
            if candidate.readiness == "registered":
                blockers.append(
                    StatusBlocker(
                        BlockerCategory.READINESS,
                        "baseline-not-smoke-ready",
                        candidate.candidate_id,
                    )
                )
        blockers.extend(
            StatusBlocker(BlockerCategory.REMOTE_PREFLIGHT, reason)
            for reason in self.preflight.blockers
        )
        aris_digest, aris_blockers = self._aris_manifest()
        blockers.extend(
            StatusBlocker(BlockerCategory.STATUS_INTEGRITY, reason) for reason in aris_blockers
        )
        if local_revision is None or _immutable_revision(local_revision) is None:
            blockers.append(
                StatusBlocker(BlockerCategory.STATUS_INTEGRITY, "local-source-uncommitted")
            )
        if _git_value(self.root, "status", "--porcelain"):
            blockers.append(StatusBlocker(BlockerCategory.STATUS_INTEGRITY, "local-worktree-dirty"))
        if not self.actions_enabled:
            blockers.append(
                StatusBlocker(BlockerCategory.AUTHORIZATION, "action-authority-missing")
            )
        if not self.contract_path.is_file():
            blockers.append(
                StatusBlocker(BlockerCategory.READINESS, "reproduction-contract-missing")
            )

        payload = MedRecStatus.create(
            stage=ProjectStage.AUDIT_BLOCKED,
            qualified_count=sum(
                candidate.readiness == "comparison_ready" for candidate in candidates
            ),
            review_state="pending",
            discovery_eligible=False,
            candidates=candidates,
            shared_lineage=_project_lineage(program, audits),
        )
        authorities = [
            AuthorityDigest("program", program.program_sha256),
            AuthorityDigest(
                "audit-set",
                content_sha256({"audits": [item.audit_sha256 for item in audits]}),
            ),
            AuthorityDigest("registry", content_sha256(registry.to_dict())),
            AuthorityDigest("remote-preflight", self.preflight.preflight_sha256),
        ]
        if aris_digest is not None:
            authorities.append(AuthorityDigest("aris-installed-skills-codex", aris_digest))

        status = ProjectStatus.create(
            project_id="medrec-research",
            authorities=authorities,
            blockers=blockers,
            payload=payload,
            clock=self.clock,
            freshness=timedelta(seconds=60),
        )
        write_json_atomic(self.status_path, status.to_dict())
        return status

    def _records(
        self,
    ) -> tuple[
        SafeDrugBatchContract | None,
        H1Approval | None,
        list[DecisionPacket],
        dict[str, H2Decision],
        tuple[str, ...],
    ]:
        blockers: list[str] = []
        contract = _load_optional(self.contract_path, SafeDrugBatchContract.from_json)
        if contract is None:
            blockers.append("reproduction-contract-missing")
        h1 = _load_optional(self.h1_path, H1Approval.from_json)
        if h1 is None:
            blockers.append("h1-approval-missing")
        elif contract is not None and not h1.is_current(contract):
            blockers.append("h1-approval-stale")

        packets: list[DecisionPacket] = []
        if self.packet_dir.is_dir():
            for path in sorted(self.packet_dir.glob("*.json")):
                packet = _load_optional(path, DecisionPacket.from_json)
                if packet is None:
                    blockers.append("decision-packet-invalid")
                    continue
                packets.append(packet)

        h2_by_packet: dict[str, H2Decision] = {}
        conflicted_packets: set[str] = set()
        if self.h2_dir.is_dir():
            for path in sorted(self.h2_dir.glob("*.json")):
                decision = _load_optional(path, H2Decision.from_json)
                if decision is None:
                    blockers.append("h2-decision-invalid")
                    continue
                existing = h2_by_packet.get(decision.packet_sha256)
                if existing is not None and existing.to_dict() != decision.to_dict():
                    conflicted_packets.add(decision.packet_sha256)
                    blockers.append("h2-decision-conflict")
                else:
                    h2_by_packet[decision.packet_sha256] = decision
        for packet_sha256 in conflicted_packets:
            h2_by_packet.pop(packet_sha256, None)
        decisions = {
            packet.lane_id: h2_by_packet[packet.packet_sha256]
            for packet in packets
            if packet.packet_sha256 in h2_by_packet
        }

        return contract, h1, packets, decisions, tuple(dict.fromkeys(blockers))

    def refresh_loop(self) -> ResearchLoopStatus:
        with self._lock:
            contract, h1, packets, decisions, record_blockers = self._records()
            loop = ResearchLoopStatus.create(
                contract=contract,
                h1=h1,
                packets=packets,
                h2_decisions=decisions,
            )
            remote_blockers = (
                self.preflight.blockers if self.preflight is not None else ("preflight-missing",)
            )
            blockers = tuple(dict.fromkeys((*loop.blockers, *record_blockers, *remote_blockers)))
            loop = ResearchLoopStatus(
                contract_sha256=loop.contract_sha256,
                h1_current=loop.h1_current,
                lanes=loop.lanes,
                blockers=blockers,
                stale=loop.stale or bool(blockers),
            )
            write_json_atomic(self.loop_path, loop.to_dict())
            return loop

    def control_state(self) -> dict[str, object]:
        contract, h1, packets, decisions, record_blockers = self._records()
        h1_current = bool(contract is not None and h1 is not None and h1.is_current(contract))
        lanes = []
        for packet in packets:
            decision = decisions.get(packet.lane_id)
            matches_contract = bool(
                contract is not None and packet.contract_sha256 == contract.contract_sha256
            )
            lanes.append(
                {
                    "current_action": decision.action.value if decision is not None else None,
                    "enabled": h1_current and packet.is_current and matches_contract,
                    "go_eligible": packet.go_eligible,
                    "lane_id": packet.lane_id,
                }
            )
        return {
            "blockers": list(record_blockers),
            "h1": {
                "current": h1_current,
                "enabled": contract is not None and contract.is_current(),
                "owner": h1.owner if h1_current and h1 is not None else None,
            },
            "h2": lanes,
            "kind": "hitl_control",
            "schema_version": 1,
        }

    def contract_state(self) -> dict[str, object]:
        ai_status, ai_reason = self.ai_bridge.availability()
        return self.contract_store.contract_state(
            contract_path=self.contract_path,
            ai_status=ai_status,
            ai_reason=ai_reason,
        )

    def contract_ai(self, value: Mapping[str, object]) -> dict[str, object]:
        payload = strict_fields(
            value,
            required=("kind", "operation", "request_id", "schema_version"),
            context="contract AI input",
        )
        if payload.pop("kind") != "contract_ai_input" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("contract AI input schema is invalid")
        contract = _load_optional(self.contract_path, SafeDrugBatchContract.from_json)
        if contract is None or not contract.is_current():
            raise ProtocolValidationError("contract AI requires a current contract")
        state = self.contract_state()
        result = self.ai_bridge.run(
            operation=str(payload["operation"]),
            request_id=str(payload["request_id"]),
            questionnaire=state["questionnaire"],
        )
        return {
            **result.to_dict(),
            "contract_sha256": contract.contract_sha256,
        }

    def decision_packet_state(self) -> dict[str, object]:
        contract, _, packets, _, record_blockers = self._records()
        return self.contract_store.decision_packet_state(
            evidence_dir=self.evidence_dir,
            contract=contract,
            packets=packets,
            record_blockers=record_blockers,
        )

    def create_h1(self, value: Mapping[str, object]) -> dict[str, object]:
        return self.contract_store.create_h1(
            value,
            contract_path=self.contract_path,
            h1_path=self.h1_path,
            clock=self.clock,
            on_success=self.refresh_loop,
        )

    def create_h2(self, value: Mapping[str, object]) -> dict[str, object]:
        return self.contract_store.create_h2(
            value,
            contract_path=self.contract_path,
            h1_path=self.h1_path,
            packet_dir=self.packet_dir,
            evidence_dir=self.evidence_dir,
            h2_dir=self.h2_dir,
            clock=self.clock,
            on_success=self.refresh_loop,
        )

    def authority_bundle(self) -> AuthorityBundle | None:
        if not self.authority_bundle_path.is_file():
            return None
        try:
            return AuthorityBundle.load(self.authority_bundle_path)
        except (OSError, UnicodeError, ProtocolValidationError):
            return None

    def queue_action_request(self, value: Mapping[str, object]) -> dict[str, object]:
        contract, h1, packets, decisions, _ = self._records()
        return self.orchestrator.queue_action_request(
            value,
            execution_queue=self.execution_queue,
            execution_registry=self.execution_registry,
            aris_transport=self.aris_transport,
            action_request_dir=self.action_request_dir,
            submission_dir=self.submission_dir,
            transport_manifest_dir=self.transport_manifest_dir,
            contract_path=self.contract_path,
            aris_bridge=self.aris_bridge,
            contract=contract,
            h1=h1,
            packets=packets,
            decisions=decisions,
            preflight=self.preflight,
            aris_revision=self.aris_revision,
            clock=self.clock,
        )

    def _dispatch_pending(self) -> tuple[ExecutionSubmission, ...]:
        return self.orchestrator.dispatch_pending(
            execution_queue=self.execution_queue,
            execution_registry=self.execution_registry,
            aris_transport=self.aris_transport,
            action_request_dir=self.action_request_dir,
            submission_dir=self.submission_dir,
            transport_manifest_dir=self.transport_manifest_dir,
            contract_path=self.contract_path,
            aris_bridge=self.aris_bridge,
            preflight=self.preflight,
            aris_revision=self.aris_revision,
            clock=self.clock,
        )

    def advance_transport(self, *, force: bool = False) -> tuple[dict[str, object], ...]:
        return self.orchestrator.advance_transport(
            execution_queue=self.execution_queue,
            aris_transport=self.aris_transport,
            transport_manifest_dir=self.transport_manifest_dir,
            preflight=self.preflight,
            clock=self.clock,
            dispatch_fn=self._dispatch_pending,
            force=force,
        )

    def cancel_transport(self, request_sha256: str) -> dict[str, object]:
        return self.orchestrator.cancel_transport(
            request_sha256,
            execution_queue=self.execution_queue,
            aris_transport=self.aris_transport,
            transport_manifest_dir=self.transport_manifest_dir,
            preflight=self.preflight,
        )

    def resume_transport(self, request_sha256: str) -> dict[str, object]:
        return self.orchestrator.resume_transport(
            request_sha256,
            execution_queue=self.execution_queue,
            aris_transport=self.aris_transport,
            transport_manifest_dir=self.transport_manifest_dir,
            preflight=self.preflight,
        )

    def control_transport(self, value: Mapping[str, object]) -> dict[str, object]:
        return self.orchestrator.control_transport(
            value,
            execution_queue=self.execution_queue,
            aris_transport=self.aris_transport,
            transport_manifest_dir=self.transport_manifest_dir,
            preflight=self.preflight,
        )

    def _apply_transport_receipt(
        self,
        record: ExecutionRecord,
        receipt: ArisTransportReceipt,
        *,
        recovering: bool = False,
    ) -> ExecutionRecord:
        return self.orchestrator._apply_transport_receipt(
            self.execution_queue,
            record,
            receipt,
            recovering=recovering,
        )

    def _bound_execution(
        self, request_sha256: str, declaration_sha256: str, remote_revision: str
    ) -> tuple[ExecutionRecord, ExecutionDeclaration]:
        return self.orchestrator._bound_execution(
            request_sha256,
            declaration_sha256,
            remote_revision,
            execution_queue=self.execution_queue,
            execution_registry=self.execution_registry,
            action_request_dir=self.action_request_dir,
        )

    def _transport_manifest(
        self,
        record: ExecutionRecord,
        submission: ExecutionSubmission,
        declaration: ExecutionDeclaration,
    ) -> ArisTransportManifest:
        return self.orchestrator._transport_manifest(
            record,
            submission,
            declaration,
            aris_transport=self.aris_transport,
            transport_manifest_dir=self.transport_manifest_dir,
            contract_path=self.contract_path,
            aris_bridge=self.aris_bridge,
            preflight=self.preflight,
            aris_revision=self.aris_revision,
        )

    def apply_monitor_observation(self, value: Mapping[str, object]) -> dict[str, object]:
        return self.orchestrator.apply_monitor_observation(
            value,
            execution_queue=self.execution_queue,
            execution_registry=self.execution_registry,
            action_request_dir=self.action_request_dir,
            preflight=self.preflight,
        )

    def intake_reproduction_evidence(self, value: Mapping[str, object]) -> dict[str, object]:
        return self.orchestrator.intake_reproduction_evidence(
            value,
            execution_queue=self.execution_queue,
            execution_registry=self.execution_registry,
            action_request_dir=self.action_request_dir,
            packet_dir=self.packet_dir,
            evidence_dir=self.evidence_dir,
            contract_path=self.contract_path,
            h1_path=self.h1_path,
            preflight=self.preflight,
            clock=self.clock,
            on_success=self.refresh_loop,
        )

    def execution_state(self) -> dict[str, object]:
        return {
            "queue": self.execution_queue.to_public_dict(),
            "registry": self.execution_registry.to_public_dict(),
            "kind": "execution_control",
            "schema_version": 1,
        }

    def aris_revision_state(self) -> dict[str, object]:
        if self.aris_revision is None:
            raise ProtocolValidationError("ARIS revision validation has not run")
        return self.aris_revision.to_dict()


__all__ = ("RemoteSessionPreflight", "ResearchSession", "run_remote_preflight")
