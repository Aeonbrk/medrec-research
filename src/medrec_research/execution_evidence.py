"""Public-safe monitor and aggregate-evidence contracts for execution intake."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    enum_member,
    parse_json_object,
    require_identifier,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
)
from .errors import ProtocolValidationError
from .execution_control import ExecutionDeclaration, ExecutionState
from .reproduction_contract import (
    AttemptRecord,
    AttemptStatus,
    AttemptValidity,
    DecisionPacket,
    EvidenceConclusion,
    RepairEvidence,
    SafeDrugBatchContract,
)
from .reproduction_evaluation import ReproductionEvaluation

_MONITOR_STATES = frozenset(
    {
        ExecutionState.SUBMITTING,
        ExecutionState.RUNNING,
        ExecutionState.MONITORING,
        ExecutionState.INTAKE,
        ExecutionState.REVIEW_PENDING,
        ExecutionState.CANCELLED,
        ExecutionState.FAILED,
        ExecutionState.STUCK,
    }
)
_LANE_MODELS = {
    "gamenet": "gamenet",
    "safedrug": "safedrug",
    "retain": "retain",
    "leap-safedrug": "leap",
}


def _revision(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ProtocolValidationError(f"{field} must be an immutable revision")
    return value


def _public_json(value: object, *, field: str) -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProtocolValidationError(f"{field} must contain finite numbers")
        return value
    if isinstance(value, str):
        return require_single_line_public_string(value, field=field)
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            safe_key = require_identifier(key, field=f"{field}.key")
            normalized[safe_key] = _public_json(item, field=f"{field}.{safe_key}")
        return normalized
    if isinstance(value, (tuple, list)):
        return [_public_json(item, field=field) for item in value]
    raise ProtocolValidationError(f"{field} must contain public JSON values")


def _artifact_digests(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, Mapping) or not value:
        raise ProtocolValidationError("artifact_digests must be a non-empty object")
    pairs = tuple(
        sorted(
            (
                require_identifier(name, field="artifact_digests.name"),
                require_sha256(digest, field=f"artifact_digests.{name}"),
            )
            for name, digest in value.items()
        )
    )
    return pairs


@dataclass(frozen=True, slots=True)
class MonitorObservation:
    observation_id: str
    request_sha256: str
    declaration_sha256: str
    remote_revision: str
    state: ExecutionState | str
    reason_code: str
    observed_at: str
    authority_ok: bool
    privacy_ok: bool
    integrity_ok: bool
    resource_ok: bool
    observation_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.observation_id, field="monitor.observation_id")
        require_sha256(self.request_sha256, field="monitor.request_sha256")
        require_sha256(self.declaration_sha256, field="monitor.declaration_sha256")
        _revision(self.remote_revision, field="monitor.remote_revision")
        state = enum_member(ExecutionState, self.state, field="monitor.state")
        if state not in _MONITOR_STATES:
            raise ProtocolValidationError("monitor state is not remotely observable")
        object.__setattr__(self, "state", state)
        require_identifier(self.reason_code, field="monitor.reason_code")
        require_single_line_public_string(self.observed_at, field="monitor.observed_at")
        gates = (self.authority_ok, self.privacy_ok, self.integrity_ok, self.resource_ok)
        if any(type(value) is not bool for value in gates):
            raise ProtocolValidationError("monitor hard-gate flags must be booleans")
        if not all(gates) and state is not ExecutionState.CANCELLED:
            raise ProtocolValidationError("hard-gate failure must cancel execution")
        expected = content_sha256(self._content())
        if self.observation_sha256:
            require_sha256(self.observation_sha256, field="monitor.observation_sha256")
            if self.observation_sha256 != expected:
                raise ProtocolValidationError("monitor observation digest does not match content")
        else:
            object.__setattr__(self, "observation_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "authority_ok": self.authority_ok,
            "declaration_sha256": self.declaration_sha256,
            "integrity_ok": self.integrity_ok,
            "kind": "monitor_observation",
            "observation_id": self.observation_id,
            "observed_at": self.observed_at,
            "privacy_ok": self.privacy_ok,
            "reason_code": self.reason_code,
            "remote_revision": self.remote_revision,
            "request_sha256": self.request_sha256,
            "resource_ok": self.resource_ok,
            "schema_version": self.SCHEMA_VERSION,
            "state": self.state.value,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "observation_sha256": self.observation_sha256}

    @classmethod
    def from_dict(cls, value: object) -> MonitorObservation:
        payload = strict_fields(
            value,
            required=(
                "authority_ok",
                "declaration_sha256",
                "integrity_ok",
                "kind",
                "observation_id",
                "observation_sha256",
                "observed_at",
                "privacy_ok",
                "reason_code",
                "remote_revision",
                "request_sha256",
                "resource_ok",
                "schema_version",
                "state",
            ),
            context="MonitorObservation",
        )
        if payload.pop("kind") != "monitor_observation" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("MonitorObservation schema or kind is invalid")
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> MonitorObservation:
        return cls.from_dict(parse_json_object(text, context="MonitorObservation"))


@dataclass(frozen=True, slots=True)
class RestrictedEvidenceInput:
    evidence_id: str
    request_sha256: str
    declaration_sha256: str
    remote_revision: str
    evidence_schema_id: str
    attempt_id: str
    evaluation: ReproductionEvaluation
    qa_qc: object
    artifact_digests: tuple[tuple[str, str], ...]
    repair_evidence: tuple[RepairEvidence, ...]
    deviations: tuple[str, ...]
    authority_ok: bool
    privacy_ok: bool
    resource_ok: bool
    started_at: str
    finished_at: str
    reason: str
    evidence_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        for field in ("evidence_id", "evidence_schema_id", "attempt_id"):
            require_identifier(getattr(self, field), field=f"evidence.{field}")
        require_sha256(self.request_sha256, field="evidence.request_sha256")
        require_sha256(self.declaration_sha256, field="evidence.declaration_sha256")
        _revision(self.remote_revision, field="evidence.remote_revision")
        if not isinstance(self.evaluation, ReproductionEvaluation):
            raise ProtocolValidationError("evidence evaluation is invalid")
        object.__setattr__(self, "qa_qc", _public_json(self.qa_qc, field="evidence.qa_qc"))
        try:
            artifact_values = dict(self.artifact_digests)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError("evidence.artifact_digests must be an object") from error
        artifacts = _artifact_digests(artifact_values)
        object.__setattr__(self, "artifact_digests", artifacts)
        if not isinstance(self.repair_evidence, (tuple, list)):
            raise ProtocolValidationError("evidence.repair_evidence must be a list")
        repairs = tuple(
            item if isinstance(item, RepairEvidence) else RepairEvidence.from_dict(item)
            for item in self.repair_evidence
        )
        object.__setattr__(self, "repair_evidence", repairs)
        if not isinstance(self.deviations, (tuple, list)):
            raise ProtocolValidationError("evidence.deviations must be a list")
        deviations = tuple(
            require_single_line_public_string(item, field="evidence.deviations")
            for item in self.deviations
        )
        if len(set(deviations)) != len(deviations):
            raise ProtocolValidationError("evidence deviations must be unique")
        if deviations and not repairs:
            raise ProtocolValidationError("evidence deviations require repair evidence")
        object.__setattr__(self, "deviations", deviations)
        for field in ("authority_ok", "privacy_ok", "resource_ok"):
            if type(getattr(self, field)) is not bool:
                raise ProtocolValidationError(f"evidence.{field} must be a boolean")
        for field in ("started_at", "finished_at", "reason"):
            require_single_line_public_string(getattr(self, field), field=f"evidence.{field}")
        expected = content_sha256(self._content())
        if self.evidence_sha256:
            require_sha256(self.evidence_sha256, field="evidence_sha256")
            if self.evidence_sha256 != expected:
                raise ProtocolValidationError("evidence digest does not match content")
        else:
            object.__setattr__(self, "evidence_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "artifact_digests": dict(self.artifact_digests),
            "attempt_id": self.attempt_id,
            "authority_ok": self.authority_ok,
            "declaration_sha256": self.declaration_sha256,
            "deviations": list(self.deviations),
            "evaluation": self.evaluation.to_dict(),
            "evidence_id": self.evidence_id,
            "evidence_schema_id": self.evidence_schema_id,
            "finished_at": self.finished_at,
            "kind": "restricted_evidence_input",
            "privacy_ok": self.privacy_ok,
            "qa_qc": self.qa_qc,
            "reason": self.reason,
            "remote_revision": self.remote_revision,
            "repair_evidence": [item.to_dict() for item in self.repair_evidence],
            "request_sha256": self.request_sha256,
            "resource_ok": self.resource_ok,
            "schema_version": self.SCHEMA_VERSION,
            "started_at": self.started_at,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "evidence_sha256": self.evidence_sha256}

    @classmethod
    def from_dict(cls, value: object) -> RestrictedEvidenceInput:
        payload = strict_fields(
            value,
            required=(
                "artifact_digests",
                "attempt_id",
                "authority_ok",
                "declaration_sha256",
                "deviations",
                "evaluation",
                "evidence_id",
                "evidence_schema_id",
                "evidence_sha256",
                "finished_at",
                "kind",
                "privacy_ok",
                "qa_qc",
                "reason",
                "remote_revision",
                "repair_evidence",
                "request_sha256",
                "resource_ok",
                "schema_version",
                "started_at",
            ),
            context="RestrictedEvidenceInput",
        )
        if payload.pop("kind") != "restricted_evidence_input" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("RestrictedEvidenceInput schema or kind is invalid")
        payload["evaluation"] = ReproductionEvaluation.from_dict(payload["evaluation"])
        payload["artifact_digests"] = _artifact_digests(payload["artifact_digests"])
        if not isinstance(payload["repair_evidence"], list):
            raise ProtocolValidationError("RestrictedEvidenceInput repair_evidence must be a list")
        payload["repair_evidence"] = tuple(
            RepairEvidence.from_dict(item) for item in payload["repair_evidence"]
        )
        if not isinstance(payload["deviations"], list):
            raise ProtocolValidationError("RestrictedEvidenceInput deviations must be a list")
        payload["deviations"] = tuple(payload["deviations"])
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> RestrictedEvidenceInput:
        return cls.from_dict(parse_json_object(text, context="RestrictedEvidenceInput"))


@dataclass(frozen=True, slots=True)
class EvidenceReceipt:
    request_sha256: str
    evidence_sha256: str
    packet_sha256: str
    aggregate_table: tuple[dict[str, object], ...]
    accepted_at: str
    receipt_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_sha256(self.request_sha256, field="receipt.request_sha256")
        require_sha256(self.evidence_sha256, field="receipt.evidence_sha256")
        require_sha256(self.packet_sha256, field="receipt.packet_sha256")
        rows = _public_json(list(self.aggregate_table), field="receipt.aggregate_table")
        if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
            raise ProtocolValidationError("receipt aggregate table must contain rows")
        object.__setattr__(self, "aggregate_table", tuple(rows))
        require_single_line_public_string(self.accepted_at, field="receipt.accepted_at")
        expected = content_sha256(self._content())
        if self.receipt_sha256:
            require_sha256(self.receipt_sha256, field="receipt_sha256")
            if self.receipt_sha256 != expected:
                raise ProtocolValidationError("receipt digest does not match content")
        else:
            object.__setattr__(self, "receipt_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "accepted_at": self.accepted_at,
            "aggregate_table": list(self.aggregate_table),
            "evidence_sha256": self.evidence_sha256,
            "kind": "evidence_receipt",
            "packet_sha256": self.packet_sha256,
            "request_sha256": self.request_sha256,
            "schema_version": self.SCHEMA_VERSION,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "receipt_sha256": self.receipt_sha256}

    @classmethod
    def from_dict(cls, value: object) -> EvidenceReceipt:
        payload = strict_fields(
            value,
            required=(
                "accepted_at",
                "aggregate_table",
                "evidence_sha256",
                "kind",
                "packet_sha256",
                "receipt_sha256",
                "request_sha256",
                "schema_version",
            ),
            context="EvidenceReceipt",
        )
        if payload.pop("kind") != "evidence_receipt" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("EvidenceReceipt schema or kind is invalid")
        if not isinstance(payload["aggregate_table"], list):
            raise ProtocolValidationError("EvidenceReceipt aggregate_table must be a list")
        payload["aggregate_table"] = tuple(payload["aggregate_table"])
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> EvidenceReceipt:
        return cls.from_dict(parse_json_object(text, context="EvidenceReceipt"))


def assemble_decision_packet(
    *,
    evidence: RestrictedEvidenceInput,
    contract: SafeDrugBatchContract,
    declaration: ExecutionDeclaration,
    accepted_at: str,
) -> tuple[DecisionPacket, EvidenceReceipt]:
    """Revalidate aggregate evidence against the frozen contract and build one packet."""

    if declaration.lane_id not in _LANE_MODELS:
        raise ProtocolValidationError("lane has no registered SafeDrug contract annex")
    model_id = _LANE_MODELS[declaration.lane_id]
    annex = next((item for item in contract.model_annexes if item.model_id == model_id), None)
    if annex is None:
        raise ProtocolValidationError("execution lane is not present in the current contract")
    evaluation = evidence.evaluation
    if evidence.evidence_schema_id != declaration.evidence_schema_id:
        raise ProtocolValidationError("evidence schema does not match declaration")
    if evaluation.model_id != model_id or evaluation.source_profile.model_id != model_id:
        raise ProtocolValidationError("evaluation model does not match declaration")
    if evaluation.source_profile.source_revision != annex.source_revision:
        raise ProtocolValidationError("evaluation source revision does not match contract")
    if canonical_json(evaluation.source_profile.intervals) != canonical_json(
        annex.acceptance_intervals
    ):
        raise ProtocolValidationError("evaluation acceptance intervals do not match contract")
    if evaluation.error:
        raise ProtocolValidationError("malformed evaluation cannot enter evidence intake")
    missing = tuple(
        metric
        for metric in annex.required_outcomes
        if evaluation.source_profile.interval_for(metric) is None
    )
    failed = tuple(
        estimate.metric.value
        for estimate in evaluation.bootstrap_estimates
        if (interval := evaluation.source_profile.interval_for(estimate.metric)) is not None
        and (estimate.lower < interval[0] or estimate.upper > interval[1])
    )
    if evaluation.validity is AttemptValidity.INVALID or missing:
        conclusion = EvidenceConclusion.INCONCLUSIVE
    elif failed:
        conclusion = EvidenceConclusion.REJECTED
    else:
        conclusion = EvidenceConclusion.ACCEPTED
    if (
        evaluation.missing_intervals != missing
        or evaluation.failed_outcomes != failed
        or evaluation.conclusion is not conclusion
    ):
        raise ProtocolValidationError("evaluation conclusion does not match aggregate evidence")
    if not (evidence.authority_ok and evidence.privacy_ok and evidence.resource_ok):
        raise ProtocolValidationError("hard-gate failure cannot enter evidence intake")
    if evaluation.validity not in {AttemptValidity.USABLE, AttemptValidity.USABLE_WITH_LIMITS}:
        raise ProtocolValidationError("evidence validity is not usable")
    attempt = AttemptRecord(
        attempt_id=evidence.attempt_id,
        lane_id=declaration.lane_id,
        contract_sha256=contract.contract_sha256,
        status=AttemptStatus.COMPLETED,
        validity=evaluation.validity,
        qa_qc=evidence.qa_qc,
        artifact_digests=evidence.artifact_digests,
        repair_evidence=evidence.repair_evidence,
        deviations=evidence.deviations,
        required_outcomes=annex.required_outcomes,
        outcomes=dict(evaluation.outcomes),
        uncertainty=evaluation.uncertainty,
        privacy_ok=evidence.privacy_ok,
        authority_ok=evidence.authority_ok,
        resource_ok=evidence.resource_ok,
        source_revision=annex.source_revision,
        started_at=evidence.started_at,
        finished_at=evidence.finished_at,
        reason=evidence.reason,
    )
    packet = DecisionPacket.create(
        contract=contract,
        packet_id=f"{declaration.lane_id}-packet-{evidence.evidence_sha256[:12]}",
        lane_id=declaration.lane_id,
        attempts=(attempt,),
        conclusion=conclusion,
        validity=evaluation.validity,
        required_outcomes=annex.required_outcomes,
        outcomes=dict(evaluation.outcomes),
        uncertainty=evaluation.uncertainty,
        limitations=evaluation.limitations,
        created_at=accepted_at,
    )
    outcomes = dict(evaluation.outcomes)
    rows = tuple(
        {
            "bootstrap_estimates": list(estimate.estimates),
            "bootstrap_seed": estimate.bootstrap_seed,
            "interval": [estimate.lower, estimate.upper],
            "metric": estimate.metric.value,
            "outcome": outcomes[estimate.metric.value],
            "rounds": estimate.rounds,
            "sample_fraction": estimate.sample_fraction,
            "sample_size": estimate.sample_size,
            "with_replacement": estimate.with_replacement,
        }
        for estimate in evaluation.bootstrap_estimates
    )
    receipt = EvidenceReceipt(
        request_sha256=evidence.request_sha256,
        evidence_sha256=evidence.evidence_sha256,
        packet_sha256=packet.packet_sha256,
        aggregate_table=rows,
        accepted_at=accepted_at,
    )
    return packet, receipt


__all__ = (
    "EvidenceReceipt",
    "MonitorObservation",
    "RestrictedEvidenceInput",
    "assemble_decision_packet",
)
