"""Deterministic lane selection and reproduction-stability contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    parse_json_object,
    require_identifier,
    require_int,
    require_sha256,
    strict_fields,
)
from .baseline_audit import (
    CLASSIC_SIX,
    AuditReviewSet,
    BaselineAudit,
    BaselineProgram,
    Disposition,
)
from .errors import ProtocolValidationError

_HARD_GATES = ("source", "license")
_IDENTITY_FIELDS = (
    "source_sha256",
    "environment_sha256",
    "adapter_sha256",
    "adapter_smoke_sha256",
    "input_manifest_sha256",
    "seed_policy_sha256",
)


def _objects(value: object, *, field: str) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ProtocolValidationError(f"{field} must be a list of objects")
    return tuple(value)


def _optional_sha256(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    return require_sha256(value, field=field)


def _optional_nonnegative_int(value: object, *, field: str) -> int | None:
    if value is None:
        return None
    return require_int(value, field=field)


def _optional_nonnegative_number(value: object, *, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a finite non-negative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ProtocolValidationError(f"{field} must be a finite non-negative number")
    return result


class DiagnosticValue(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    value: DiagnosticValue | str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            value = DiagnosticValue(self.value)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError(
                "diagnostic value must be low, medium, high, or unresolved"
            ) from error
        evidence_ids = tuple(
            require_identifier(item, field="diagnostic.evidence_ids") for item in self.evidence_ids
        )
        if not evidence_ids or len(evidence_ids) != len(set(evidence_ids)):
            raise ProtocolValidationError("diagnostic evidence_ids must be non-empty and unique")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "evidence_ids", evidence_ids)

    def to_dict(self) -> dict[str, object]:
        return {"evidence_ids": list(self.evidence_ids), "value": self.value.value}

    @classmethod
    def from_dict(cls, value: object) -> Diagnostic:
        payload = strict_fields(
            value,
            required=("value", "evidence_ids"),
            context="Diagnostic",
        )
        evidence_ids = payload.pop("evidence_ids")
        if not isinstance(evidence_ids, list):
            raise ProtocolValidationError("diagnostic.evidence_ids must be a list")
        return cls(evidence_ids=tuple(evidence_ids), **payload)


@dataclass(frozen=True, slots=True)
class SelectionDiagnostic:
    baseline_id: str
    priority_ordinal: int
    comparison_representativeness: Diagnostic
    reproduction_risk: Diagnostic
    integration_cost: Diagnostic

    def __post_init__(self) -> None:
        require_identifier(self.baseline_id, field="diagnostic.baseline_id")
        require_int(self.priority_ordinal, field="diagnostic.priority_ordinal")
        for field in (
            "comparison_representativeness",
            "reproduction_risk",
            "integration_cost",
        ):
            value = getattr(self, field)
            if not isinstance(value, Diagnostic):
                value = Diagnostic.from_dict(value)
                object.__setattr__(self, field, value)

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_id": self.baseline_id,
            "comparison_representativeness": self.comparison_representativeness.to_dict(),
            "integration_cost": self.integration_cost.to_dict(),
            "priority_ordinal": self.priority_ordinal,
            "reproduction_risk": self.reproduction_risk.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> SelectionDiagnostic:
        payload = strict_fields(
            value,
            required=(
                "baseline_id",
                "priority_ordinal",
                "comparison_representativeness",
                "reproduction_risk",
                "integration_cost",
            ),
            context="SelectionDiagnostic",
        )
        for field in (
            "comparison_representativeness",
            "reproduction_risk",
            "integration_cost",
        ):
            payload[field] = Diagnostic.from_dict(payload[field])
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class CandidateSelection:
    baseline_id: str
    priority_ordinal: int
    audit_sha256: str
    accepted_review_sha256: tuple[str, ...]
    blockers: tuple[str, ...]
    diagnostics: SelectionDiagnostic

    def __post_init__(self) -> None:
        require_identifier(self.baseline_id, field="candidate.baseline_id")
        require_int(self.priority_ordinal, field="candidate.priority_ordinal")
        require_sha256(self.audit_sha256, field="candidate.audit_sha256")
        reviews = tuple(
            require_sha256(item, field="candidate.accepted_review_sha256")
            for item in self.accepted_review_sha256
        )
        if len(reviews) != len(set(reviews)):
            raise ProtocolValidationError("accepted review digests must be unique")
        allowed_blockers = {
            "source_not_pass",
            "license_not_pass",
            "source_review_missing",
            "license_review_missing",
        }
        blockers = tuple(self.blockers)
        if len(blockers) != len(set(blockers)) or not set(blockers) <= allowed_blockers:
            raise ProtocolValidationError("candidate blockers must use the closed blocker set")
        if not isinstance(self.diagnostics, SelectionDiagnostic):
            object.__setattr__(self, "diagnostics", SelectionDiagnostic.from_dict(self.diagnostics))
        if (
            self.diagnostics.baseline_id != self.baseline_id
            or self.diagnostics.priority_ordinal != self.priority_ordinal
        ):
            raise ProtocolValidationError("candidate diagnostics do not match candidate identity")
        object.__setattr__(self, "accepted_review_sha256", reviews)
        object.__setattr__(self, "blockers", blockers)

    @property
    def eligible(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, object]:
        return {
            "accepted_review_sha256": list(self.accepted_review_sha256),
            "audit_sha256": self.audit_sha256,
            "baseline_id": self.baseline_id,
            "blockers": list(self.blockers),
            "diagnostics": self.diagnostics.to_dict(),
            "eligible": self.eligible,
            "priority_ordinal": self.priority_ordinal,
        }

    @classmethod
    def from_dict(cls, value: object) -> CandidateSelection:
        payload = strict_fields(
            value,
            required=(
                "baseline_id",
                "priority_ordinal",
                "audit_sha256",
                "accepted_review_sha256",
                "blockers",
                "diagnostics",
                "eligible",
            ),
            context="CandidateSelection",
        )
        eligible = payload.pop("eligible")
        if type(eligible) is not bool:
            raise ProtocolValidationError("candidate.eligible must be boolean")
        reviews = payload.pop("accepted_review_sha256")
        blockers = payload.pop("blockers")
        if not isinstance(reviews, list) or not isinstance(blockers, list):
            raise ProtocolValidationError("candidate review digests and blockers must be lists")
        result = cls(
            accepted_review_sha256=tuple(reviews),
            blockers=tuple(blockers),
            diagnostics=SelectionDiagnostic.from_dict(payload.pop("diagnostics")),
            **payload,
        )
        if result.eligible is not eligible:
            raise ProtocolValidationError("candidate eligible flag does not match blockers")
        return result


@dataclass(frozen=True, slots=True)
class SelectionResult:
    selection_id: str
    specification_version: int
    specification_sha256: str
    program_sha256: str
    audit_set_sha256: str
    review_set_sha256: str
    status: str
    selected_candidate_id: str | None
    candidates: tuple[CandidateSelection, ...]

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        if self.specification_version != 1:
            raise ProtocolValidationError("selection specification version must be 1")
        for field in (
            "specification_sha256",
            "program_sha256",
            "audit_set_sha256",
            "review_set_sha256",
        ):
            require_sha256(getattr(self, field), field=field)
        if self.specification_sha256 != SelectionSpecification().specification_sha256:
            raise ProtocolValidationError("selection result specification digest is not V1")
        candidates = tuple(
            item if isinstance(item, CandidateSelection) else CandidateSelection.from_dict(item)
            for item in self.candidates
        )
        identities = tuple(item.baseline_id for item in candidates)
        ordinals = tuple(item.priority_ordinal for item in candidates)
        if identities != CLASSIC_SIX or ordinals != tuple(range(len(CLASSIC_SIX))):
            raise ProtocolValidationError("selection candidates must preserve fixed priority order")
        first_eligible = next((item.baseline_id for item in candidates if item.eligible), None)
        expected_status = "proposed" if first_eligible is not None else "blocked"
        if self.status != expected_status or self.selected_candidate_id != first_eligible:
            raise ProtocolValidationError(
                "selected candidate must be the earliest eligible candidate"
            )
        object.__setattr__(self, "candidates", candidates)
        expected_id = f"selection-{content_sha256(self._payload())[:20]}"
        if self.selection_id != expected_id:
            raise ProtocolValidationError(
                f"selection_id does not match result content; expected {expected_id}"
            )

    def _payload(self) -> dict[str, object]:
        return {
            "audit_set_sha256": self.audit_set_sha256,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "kind": "selection_result",
            "program_sha256": self.program_sha256,
            "review_set_sha256": self.review_set_sha256,
            "schema_version": self.SCHEMA_VERSION,
            "selected_candidate_id": self.selected_candidate_id,
            "specification_sha256": self.specification_sha256,
            "specification_version": self.specification_version,
            "status": self.status,
        }

    def to_dict(self) -> dict[str, object]:
        return {"selection_id": self.selection_id, **self._payload()}

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def create(cls, **payload: object) -> SelectionResult:
        candidates = payload.get("candidates", ())
        serializable = {
            **payload,
            "candidates": [
                item.to_dict() if isinstance(item, CandidateSelection) else item
                for item in candidates
            ],
        }
        selection_id = f"selection-{content_sha256(serializable)[:20]}"
        init_payload = dict(payload)
        init_payload.pop("schema_version", None)
        init_payload.pop("kind", None)
        return cls(selection_id=selection_id, **init_payload)

    @classmethod
    def from_dict(cls, value: object) -> SelectionResult:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "selection_id",
                "specification_version",
                "specification_sha256",
                "program_sha256",
                "audit_set_sha256",
                "review_set_sha256",
                "status",
                "selected_candidate_id",
                "candidates",
            ),
            context="SelectionResult",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("SelectionResult schema_version must be 1")
        if payload.pop("kind") != "selection_result":
            raise ProtocolValidationError("SelectionResult kind must be selection_result")
        candidates = _objects(payload.pop("candidates"), field="SelectionResult.candidates")
        return cls(
            candidates=tuple(CandidateSelection.from_dict(item) for item in candidates), **payload
        )

    @classmethod
    def from_json(cls, text: str) -> SelectionResult:
        return cls.from_dict(parse_json_object(text, context="SelectionResult"))

    @classmethod
    def load(cls, path: str | Path) -> SelectionResult:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class SelectionSpecification:
    version: int = 1
    priority_order: tuple[str, ...] = CLASSIC_SIX

    def __post_init__(self) -> None:
        if self.version != 1 or tuple(self.priority_order) != CLASSIC_SIX:
            raise ProtocolValidationError(
                "SelectionSpecification V1 must use the fixed priority order"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_id_integrity": "exact",
            "hard_gates": list(_HARD_GATES),
            "missing_value_policy": "unresolved",
            "priority_direction": "ascending",
            "priority_order": list(self.priority_order),
            "schema_version": 1,
            "version": self.version,
        }

    @property
    def specification_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def select(
        self,
        program: BaselineProgram,
        audits: tuple[BaselineAudit, ...],
        reviews: AuditReviewSet,
        diagnostics: tuple[SelectionDiagnostic, ...],
    ) -> SelectionResult:
        try:
            program.validate_audits(audits)
        except ProtocolValidationError as error:
            raise ProtocolValidationError(
                "selection blocked: all six audits are required in fixed priority order"
            ) from error
        normalized = tuple(
            item if isinstance(item, SelectionDiagnostic) else SelectionDiagnostic.from_dict(item)
            for item in diagnostics
        )
        if tuple(item.baseline_id for item in normalized) != self.priority_order or tuple(
            item.priority_ordinal for item in normalized
        ) != tuple(range(6)):
            raise ProtocolValidationError("diagnostics must match the fixed priority order")
        candidate_results: list[CandidateSelection] = []
        for audit, diagnostic in zip(audits, normalized, strict=True):
            known_evidence = {item.evidence_id for item in audit.evidence}
            cited = {
                *diagnostic.comparison_representativeness.evidence_ids,
                *diagnostic.reproduction_risk.evidence_ids,
                *diagnostic.integration_cost.evidence_ids,
            }
            if not cited <= known_evidence:
                raise ProtocolValidationError(
                    "diagnostic cites evidence outside its candidate audit"
                )
            blockers: list[str] = []
            accepted_reviews: list[str] = []
            for claim_name in _HARD_GATES:
                claim = audit.claim(claim_name)
                if claim.disposition is not Disposition.PASS:
                    blockers.append(f"{claim_name}_not_pass")
                    continue
                review = reviews.matching_review(audit, claim_name)
                if review is None:
                    blockers.append(f"{claim_name}_review_missing")
                else:
                    accepted_reviews.append(review.review_sha256)
            candidate_results.append(
                CandidateSelection(
                    baseline_id=audit.baseline_id,
                    priority_ordinal=diagnostic.priority_ordinal,
                    audit_sha256=audit.audit_sha256,
                    accepted_review_sha256=tuple(dict.fromkeys(accepted_reviews)),
                    blockers=tuple(blockers),
                    diagnostics=diagnostic,
                )
            )
        selected = next((item.baseline_id for item in candidate_results if item.eligible), None)
        payload = {
            "specification_version": self.version,
            "specification_sha256": self.specification_sha256,
            "program_sha256": program.program_sha256,
            "audit_set_sha256": content_sha256(
                {"audits": [audit.audit_sha256 for audit in audits]}
            ),
            "review_set_sha256": content_sha256(reviews.to_dict()),
            "status": "proposed" if selected is not None else "blocked",
            "selected_candidate_id": selected,
            "candidates": tuple(candidate_results),
            "schema_version": SelectionResult.SCHEMA_VERSION,
            "kind": "selection_result",
        }
        return SelectionResult.create(**payload)


class AttemptOutcome(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class StabilityStatus(StrEnum):
    UNRESOLVED = "unresolved"
    FAILED = "failed"
    STABLE = "stable"


@dataclass(frozen=True, slots=True)
class ReproductionAttempt:
    attempt_id: str
    outcome: AttemptOutcome | str
    source_sha256: str | None
    environment_sha256: str | None
    adapter_sha256: str | None
    adapter_smoke_sha256: str | None
    input_manifest_sha256: str | None
    seed_policy_sha256: str | None
    artifact_sha256: str | None

    def __post_init__(self) -> None:
        require_identifier(self.attempt_id, field="attempt.attempt_id")
        try:
            outcome = AttemptOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError("attempt outcome must be completed or failed") from error
        object.__setattr__(self, "outcome", outcome)
        for field in (*_IDENTITY_FIELDS, "artifact_sha256"):
            object.__setattr__(
                self,
                field,
                _optional_sha256(getattr(self, field), field=f"attempt.{field}"),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_sha256": self.adapter_sha256,
            "adapter_smoke_sha256": self.adapter_smoke_sha256,
            "artifact_sha256": self.artifact_sha256,
            "attempt_id": self.attempt_id,
            "environment_sha256": self.environment_sha256,
            "input_manifest_sha256": self.input_manifest_sha256,
            "outcome": self.outcome.value,
            "seed_policy_sha256": self.seed_policy_sha256,
            "source_sha256": self.source_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> ReproductionAttempt:
        payload = strict_fields(
            value,
            required=("attempt_id", "outcome"),
            optional=(*_IDENTITY_FIELDS, "artifact_sha256"),
            context="ReproductionAttempt",
        )
        for field in (*_IDENTITY_FIELDS, "artifact_sha256"):
            payload.setdefault(field, None)
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class VarianceCheck:
    check_id: str
    predeclared: bool | None
    tolerance: float | None
    observed_variance: float | None
    evidence_sha256: str | None

    def __post_init__(self) -> None:
        require_identifier(self.check_id, field="variance.check_id")
        if self.predeclared is not None and type(self.predeclared) is not bool:
            raise ProtocolValidationError("variance.predeclared must be boolean or null")
        object.__setattr__(
            self,
            "tolerance",
            _optional_nonnegative_number(self.tolerance, field="variance.tolerance"),
        )
        object.__setattr__(
            self,
            "observed_variance",
            _optional_nonnegative_number(
                self.observed_variance, field="variance.observed_variance"
            ),
        )
        object.__setattr__(
            self,
            "evidence_sha256",
            _optional_sha256(self.evidence_sha256, field="variance.evidence_sha256"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "evidence_sha256": self.evidence_sha256,
            "observed_variance": self.observed_variance,
            "predeclared": self.predeclared,
            "tolerance": self.tolerance,
        }

    @classmethod
    def from_dict(cls, value: object) -> VarianceCheck:
        payload = strict_fields(
            value,
            required=("check_id",),
            optional=("predeclared", "tolerance", "observed_variance", "evidence_sha256"),
            context="VarianceCheck",
        )
        for field in ("predeclared", "tolerance", "observed_variance", "evidence_sha256"):
            payload.setdefault(field, None)
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class ReproductionStabilityPolicy:
    version: int = 1
    minimum_completed_attempts: int = 2
    maximum_failed_attempts: int = 0

    def __post_init__(self) -> None:
        if (
            self.version != 1
            or self.minimum_completed_attempts != 2
            or self.maximum_failed_attempts != 0
        ):
            raise ProtocolValidationError("ReproductionStabilityPolicy V1 is fixed")

    def to_dict(self) -> dict[str, object]:
        return {
            "maximum_failed_attempts": self.maximum_failed_attempts,
            "minimum_completed_attempts": self.minimum_completed_attempts,
            "mode": "reproduction",
            "require_adapter_smoke_identity": True,
            "require_artifact_digest": True,
            "require_matching_attempt_identities": list(_IDENTITY_FIELDS),
            "require_predeclared_variance_check": True,
            "require_upstream_semantics": ["split", "selection", "evaluation"],
            "schema_version": 1,
            "version": self.version,
        }

    @property
    def policy_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def evaluate(
        self,
        *,
        mode: str,
        accepted_selection_sha256: str | None,
        planned_attempts: int | None,
        attempts: tuple[ReproductionAttempt, ...],
        protocol_violations: int | None,
        variance_checks: tuple[VarianceCheck, ...],
        upstream_fields: tuple[str | None, ...],
    ) -> StabilityStatus:
        if mode != "reproduction":
            return StabilityStatus.FAILED
        if planned_attempts is not None and planned_attempts != len(attempts):
            return StabilityStatus.FAILED
        if any(item.outcome is AttemptOutcome.FAILED for item in attempts):
            return StabilityStatus.FAILED
        if protocol_violations is not None and protocol_violations > 0:
            return StabilityStatus.FAILED
        for field in _IDENTITY_FIELDS:
            observed = {getattr(attempt, field) for attempt in attempts if getattr(attempt, field)}
            if len(observed) > 1:
                return StabilityStatus.FAILED
        for check in variance_checks:
            if check.predeclared is False:
                return StabilityStatus.FAILED
            if (
                check.tolerance is not None
                and check.observed_variance is not None
                and check.observed_variance > check.tolerance
            ):
                return StabilityStatus.FAILED
        completed = sum(item.outcome is AttemptOutcome.COMPLETED for item in attempts)
        missing_attempt_evidence = any(
            any(getattr(attempt, field) is None for field in (*_IDENTITY_FIELDS, "artifact_sha256"))
            for attempt in attempts
        )
        missing_variance_evidence = not variance_checks or any(
            check.predeclared is None
            or check.tolerance is None
            or check.observed_variance is None
            or check.evidence_sha256 is None
            for check in variance_checks
        )
        if (
            accepted_selection_sha256 is None
            or planned_attempts is None
            or completed < self.minimum_completed_attempts
            or protocol_violations is None
            or missing_attempt_evidence
            or missing_variance_evidence
            or any(value is None for value in upstream_fields)
        ):
            return StabilityStatus.UNRESOLVED
        return StabilityStatus.STABLE


@dataclass(frozen=True, slots=True)
class ReproductionCharacterization:
    characterization_id: str
    baseline_id: str
    mode: str
    policy_version: int
    policy_sha256: str
    accepted_selection_sha256: str | None
    planned_attempts: int | None
    attempts: tuple[ReproductionAttempt, ...]
    protocol_violations: int | None
    variance_checks: tuple[VarianceCheck, ...]
    upstream_reference_sha256: str | None
    split_semantics_sha256: str | None
    selection_semantics_sha256: str | None
    evaluation_semantics_sha256: str | None
    status: StabilityStatus | str

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.baseline_id, field="characterization.baseline_id")
        policy = ReproductionStabilityPolicy()
        if self.policy_version != policy.version or self.policy_sha256 != policy.policy_sha256:
            raise ProtocolValidationError("characterization policy does not match V1")
        attempts = tuple(
            item if isinstance(item, ReproductionAttempt) else ReproductionAttempt.from_dict(item)
            for item in self.attempts
        )
        if len({item.attempt_id for item in attempts}) != len(attempts):
            raise ProtocolValidationError("reproduction attempt IDs must be unique")
        checks = tuple(
            item if isinstance(item, VarianceCheck) else VarianceCheck.from_dict(item)
            for item in self.variance_checks
        )
        if len({item.check_id for item in checks}) != len(checks):
            raise ProtocolValidationError("variance check IDs must be unique")
        planned = _optional_nonnegative_int(
            self.planned_attempts, field="characterization.planned_attempts"
        )
        violations = _optional_nonnegative_int(
            self.protocol_violations, field="characterization.protocol_violations"
        )
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "variance_checks", checks)
        object.__setattr__(self, "planned_attempts", planned)
        object.__setattr__(self, "protocol_violations", violations)
        for field in (
            "accepted_selection_sha256",
            "upstream_reference_sha256",
            "split_semantics_sha256",
            "selection_semantics_sha256",
            "evaluation_semantics_sha256",
        ):
            object.__setattr__(
                self,
                field,
                _optional_sha256(getattr(self, field), field=f"characterization.{field}"),
            )
        expected_status = policy.evaluate(
            mode=self.mode,
            accepted_selection_sha256=self.accepted_selection_sha256,
            planned_attempts=planned,
            attempts=attempts,
            protocol_violations=violations,
            variance_checks=checks,
            upstream_fields=(
                self.upstream_reference_sha256,
                self.split_semantics_sha256,
                self.selection_semantics_sha256,
                self.evaluation_semantics_sha256,
            ),
        )
        try:
            status = StabilityStatus(self.status)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError("characterization status is invalid") from error
        if status is not expected_status:
            raise ProtocolValidationError("characterization status does not match its evidence")
        object.__setattr__(self, "status", status)
        expected_id = f"characterization-{content_sha256(self._payload())[:20]}"
        if self.characterization_id != expected_id:
            raise ProtocolValidationError(
                f"characterization_id does not match content; expected {expected_id}"
            )

    def evaluate(self) -> StabilityStatus:
        return self.status

    def _payload(self) -> dict[str, object]:
        return {
            "accepted_selection_sha256": self.accepted_selection_sha256,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "baseline_id": self.baseline_id,
            "evaluation_semantics_sha256": self.evaluation_semantics_sha256,
            "kind": "reproduction_characterization",
            "mode": self.mode,
            "planned_attempts": self.planned_attempts,
            "policy_sha256": self.policy_sha256,
            "policy_version": self.policy_version,
            "protocol_violations": self.protocol_violations,
            "schema_version": self.SCHEMA_VERSION,
            "selection_semantics_sha256": self.selection_semantics_sha256,
            "split_semantics_sha256": self.split_semantics_sha256,
            "status": self.status.value,
            "upstream_reference_sha256": self.upstream_reference_sha256,
            "variance_checks": [check.to_dict() for check in self.variance_checks],
        }

    def to_dict(self) -> dict[str, object]:
        return {"characterization_id": self.characterization_id, **self._payload()}

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def create(
        cls, policy: ReproductionStabilityPolicy, **evidence: object
    ) -> ReproductionCharacterization:
        attempts = tuple(evidence.pop("attempts"))
        checks = tuple(evidence.pop("variance_checks"))
        status = policy.evaluate(
            mode=evidence["mode"],
            accepted_selection_sha256=evidence["accepted_selection_sha256"],
            planned_attempts=evidence["planned_attempts"],
            attempts=attempts,
            protocol_violations=evidence["protocol_violations"],
            variance_checks=checks,
            upstream_fields=(
                evidence["upstream_reference_sha256"],
                evidence["split_semantics_sha256"],
                evidence["selection_semantics_sha256"],
                evidence["evaluation_semantics_sha256"],
            ),
        )
        payload = {
            **evidence,
            "attempts": attempts,
            "variance_checks": checks,
            "policy_version": policy.version,
            "policy_sha256": policy.policy_sha256,
            "status": status,
        }
        canonical_payload = {
            "accepted_selection_sha256": payload["accepted_selection_sha256"],
            "attempts": [attempt.to_dict() for attempt in attempts],
            "baseline_id": payload["baseline_id"],
            "evaluation_semantics_sha256": payload["evaluation_semantics_sha256"],
            "kind": "reproduction_characterization",
            "mode": payload["mode"],
            "planned_attempts": payload["planned_attempts"],
            "policy_sha256": payload["policy_sha256"],
            "policy_version": payload["policy_version"],
            "protocol_violations": payload["protocol_violations"],
            "schema_version": cls.SCHEMA_VERSION,
            "selection_semantics_sha256": payload["selection_semantics_sha256"],
            "split_semantics_sha256": payload["split_semantics_sha256"],
            "status": status.value,
            "upstream_reference_sha256": payload["upstream_reference_sha256"],
            "variance_checks": [check.to_dict() for check in checks],
        }
        return cls(
            characterization_id=f"characterization-{content_sha256(canonical_payload)[:20]}",
            **payload,
        )

    @classmethod
    def from_dict(cls, value: object) -> ReproductionCharacterization:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "characterization_id",
                "baseline_id",
                "mode",
                "policy_version",
                "policy_sha256",
                "status",
                "attempts",
                "variance_checks",
            ),
            optional=(
                "accepted_selection_sha256",
                "planned_attempts",
                "protocol_violations",
                "upstream_reference_sha256",
                "split_semantics_sha256",
                "selection_semantics_sha256",
                "evaluation_semantics_sha256",
            ),
            context="ReproductionCharacterization",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("ReproductionCharacterization schema_version must be 1")
        if payload.pop("kind") != "reproduction_characterization":
            raise ProtocolValidationError(
                "ReproductionCharacterization kind must be reproduction_characterization"
            )
        attempts = _objects(payload.pop("attempts"), field="characterization.attempts")
        checks = _objects(payload.pop("variance_checks"), field="characterization.variance_checks")
        for field in (
            "accepted_selection_sha256",
            "planned_attempts",
            "protocol_violations",
            "upstream_reference_sha256",
            "split_semantics_sha256",
            "selection_semantics_sha256",
            "evaluation_semantics_sha256",
        ):
            payload.setdefault(field, None)
        return cls(
            attempts=tuple(ReproductionAttempt.from_dict(item) for item in attempts),
            variance_checks=tuple(VarianceCheck.from_dict(item) for item in checks),
            **payload,
        )

    @classmethod
    def from_json(cls, text: str) -> ReproductionCharacterization:
        return cls.from_dict(parse_json_object(text, context="ReproductionCharacterization"))

    @classmethod
    def load(cls, path: str | Path) -> ReproductionCharacterization:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


__all__ = (
    "CandidateSelection",
    "Diagnostic",
    "DiagnosticValue",
    "ReproductionAttempt",
    "ReproductionCharacterization",
    "ReproductionStabilityPolicy",
    "SelectionDiagnostic",
    "SelectionResult",
    "SelectionSpecification",
    "StabilityStatus",
    "VarianceCheck",
)
