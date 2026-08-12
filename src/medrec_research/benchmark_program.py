"""Deterministic lane selection and steward-acceptance contracts."""

from __future__ import annotations

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
    require_single_line_public_string,
    strict_fields,
)
from .baseline_audit import (
    FINAL_FIVE,
    AuditReviewSet,
    BaselineAudit,
    BaselineProgram,
    Disposition,
)
from .errors import ProtocolValidationError
from .reproduction_characterization import (
    AttemptOutcome,
    ReproductionAttempt,
    ReproductionCharacterization,
    ReproductionStabilityPolicy,
    StabilityStatus,
    VarianceCheck,
)

_HARD_GATES_BY_VERSION = {
    1: ("source", "license"),
    2: ("source",),
}
_CURRENT_SELECTION_SPECIFICATION_VERSION = 2


def _objects(value: object, *, field: str) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ProtocolValidationError(f"{field} must be a list of objects")
    return tuple(value)


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
    registry_authority_sha256: str
    scope_sha256: str
    status: str
    selected_candidate_id: str | None
    candidates: tuple[CandidateSelection, ...]

    SCHEMA_VERSION: ClassVar[int] = 2

    def __post_init__(self) -> None:
        if self.specification_version not in _HARD_GATES_BY_VERSION:
            raise ProtocolValidationError("selection specification version is unsupported")
        for field in (
            "specification_sha256",
            "program_sha256",
            "audit_set_sha256",
            "review_set_sha256",
            "registry_authority_sha256",
            "scope_sha256",
        ):
            require_sha256(getattr(self, field), field=field)
        if (
            self.specification_sha256
            != SelectionSpecification(version=self.specification_version).specification_sha256
        ):
            raise ProtocolValidationError("selection result specification digest is invalid")
        candidates = tuple(
            item if isinstance(item, CandidateSelection) else CandidateSelection.from_dict(item)
            for item in self.candidates
        )
        identities = tuple(item.baseline_id for item in candidates)
        ordinals = tuple(item.priority_ordinal for item in candidates)
        if identities != FINAL_FIVE or ordinals != tuple(range(len(FINAL_FIVE))):
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
            "registry_authority_sha256": self.registry_authority_sha256,
            "review_set_sha256": self.review_set_sha256,
            "schema_version": self.SCHEMA_VERSION,
            "selected_candidate_id": self.selected_candidate_id,
            "scope_sha256": self.scope_sha256,
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
                "registry_authority_sha256",
                "scope_sha256",
                "status",
                "selected_candidate_id",
                "candidates",
            ),
            context="SelectionResult",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError(
                f"SelectionResult schema_version must be {cls.SCHEMA_VERSION}"
            )
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


def _selection_acceptance_payload(
    *,
    selection_sha256: str,
    candidate_id: str,
    reviewer: str,
    decision: str,
    issued_at: str,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "decision": decision,
        "issued_at": issued_at,
        "kind": "selection_acceptance",
        "reviewer": reviewer,
        "schema_version": SelectionAcceptance.SCHEMA_VERSION,
        "selection_sha256": selection_sha256,
    }


@dataclass(frozen=True, slots=True)
class SelectionAcceptance:
    """Durable steward provenance for a selected reproduction candidate."""

    acceptance_id: str
    selection_sha256: str
    candidate_id: str
    reviewer: str
    decision: str
    issued_at: str

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.acceptance_id, field="selection_acceptance.acceptance_id")
        require_sha256(self.selection_sha256, field="selection_acceptance.selection_sha256")
        require_identifier(self.candidate_id, field="selection_acceptance.candidate_id")
        require_identifier(self.reviewer, field="selection_acceptance.reviewer")
        if self.decision != "accepted":
            raise ProtocolValidationError("selection acceptance decision must be accepted")
        require_single_line_public_string(self.issued_at, field="selection_acceptance.issued_at")
        expected = f"selection-acceptance-{content_sha256(self._payload())[:20]}"
        if self.acceptance_id != expected:
            raise ProtocolValidationError(
                f"selection acceptance ID does not match content; expected {expected}"
            )

    @property
    def acceptance_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def _payload(self) -> dict[str, object]:
        return _selection_acceptance_payload(
            selection_sha256=self.selection_sha256,
            candidate_id=self.candidate_id,
            reviewer=self.reviewer,
            decision=self.decision,
            issued_at=self.issued_at,
        )

    def matches(self, selection: SelectionResult) -> bool:
        return (
            selection.status == "proposed"
            and selection.selected_candidate_id == self.candidate_id
            and content_sha256(selection.to_dict()) == self.selection_sha256
        )

    def to_dict(self) -> dict[str, object]:
        return {"acceptance_id": self.acceptance_id, **self._payload()}

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def create(
        cls,
        *,
        selection: SelectionResult,
        candidate_id: str,
        reviewer: str,
        issued_at: str,
    ) -> SelectionAcceptance:
        if selection.status != "proposed" or selection.selected_candidate_id != candidate_id:
            raise ProtocolValidationError("selection acceptance must bind the selected candidate")
        values = {
            "selection_sha256": content_sha256(selection.to_dict()),
            "candidate_id": candidate_id,
            "reviewer": reviewer,
            "decision": "accepted",
            "issued_at": issued_at,
        }
        return cls(
            acceptance_id=f"selection-acceptance-{content_sha256(_selection_acceptance_payload(**values))[:20]}",
            **values,
        )

    @classmethod
    def from_dict(cls, value: object) -> SelectionAcceptance:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "acceptance_id",
                "selection_sha256",
                "candidate_id",
                "reviewer",
                "decision",
                "issued_at",
            ),
            context="SelectionAcceptance",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("SelectionAcceptance schema_version must be 1")
        if payload.pop("kind") != "selection_acceptance":
            raise ProtocolValidationError("SelectionAcceptance kind must be selection_acceptance")
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> SelectionAcceptance:
        return cls.from_dict(parse_json_object(text, context="SelectionAcceptance"))

    @classmethod
    def load(cls, path: str | Path) -> SelectionAcceptance:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class SelectionSpecification:
    version: int = _CURRENT_SELECTION_SPECIFICATION_VERSION
    priority_order: tuple[str, ...] = FINAL_FIVE

    def __post_init__(self) -> None:
        if self.version not in _HARD_GATES_BY_VERSION or tuple(self.priority_order) != FINAL_FIVE:
            raise ProtocolValidationError(
                "selection specification must use a supported version and fixed priority order"
            )

    @property
    def hard_gates(self) -> tuple[str, ...]:
        return _HARD_GATES_BY_VERSION[self.version]

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_id_integrity": "exact",
            "hard_gates": list(self.hard_gates),
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
        *,
        registry_authority_sha256: str,
        scope_sha256: str,
    ) -> SelectionResult:
        try:
            program.validate_audits(audits)
        except ProtocolValidationError as error:
            raise ProtocolValidationError(
                "selection blocked: all final-five audits are required in fixed priority order"
            ) from error
        normalized = tuple(
            item if isinstance(item, SelectionDiagnostic) else SelectionDiagnostic.from_dict(item)
            for item in diagnostics
        )
        if tuple(item.baseline_id for item in normalized) != self.priority_order or tuple(
            item.priority_ordinal for item in normalized
        ) != tuple(range(len(FINAL_FIVE))):
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
            for claim_name in self.hard_gates:
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
            "registry_authority_sha256": registry_authority_sha256,
            "scope_sha256": scope_sha256,
            "status": "proposed" if selected is not None else "blocked",
            "selected_candidate_id": selected,
            "candidates": tuple(candidate_results),
            "schema_version": SelectionResult.SCHEMA_VERSION,
            "kind": "selection_result",
        }
        return SelectionResult.create(**payload)


__all__ = (
    "AttemptOutcome",
    "CandidateSelection",
    "Diagnostic",
    "DiagnosticValue",
    "ReproductionAttempt",
    "ReproductionCharacterization",
    "ReproductionStabilityPolicy",
    "SelectionAcceptance",
    "SelectionDiagnostic",
    "SelectionResult",
    "SelectionSpecification",
    "StabilityStatus",
    "VarianceCheck",
)
