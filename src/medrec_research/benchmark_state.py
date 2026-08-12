"""Derived readiness state for one benchmark Comparison Scope."""

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
    require_sha256,
    require_single_line_public_string,
    strict_fields,
)
from .baseline_audit import AuditReviewSet, BaselineAudit, BaselineProgram
from .benchmark_program import SelectionAcceptance, SelectionResult, SelectionSpecification
from .comparison_scope import ComparisonScope
from .errors import ProtocolValidationError
from .registry import BaselineRegistry, ComparisonQualification


@dataclass(frozen=True, slots=True)
class QualificationReference:
    baseline_id: str
    qualification_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.baseline_id, field="qualification.baseline_id")
        require_sha256(
            self.qualification_sha256,
            field="qualification.qualification_sha256",
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "baseline_id": self.baseline_id,
            "qualification_sha256": self.qualification_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> QualificationReference:
        return cls(
            **strict_fields(
                value,
                required=("baseline_id", "qualification_sha256"),
                context="QualificationReference",
            )
        )


class HumanReviewState(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    ACCEPTED = "accepted"


def program_registry_authority_sha256(
    program: BaselineProgram,
    registry: BaselineRegistry,
) -> str:
    definitions: list[dict[str, str]] = []
    for baseline_id in program.candidate_ids:
        definition = registry.get(baseline_id).to_dict()
        definition.pop("comparison_qualifications")
        definitions.append(
            {
                "baseline_id": baseline_id,
                "definition_authority_sha256": content_sha256(definition),
            }
        )
    return content_sha256({"definitions": definitions})


def _human_review_payload(
    *,
    scope: ComparisonScope,
    program_sha256: str,
    registry_authority_sha256: str,
    reviewed_qualifications: tuple[QualificationReference, ...],
    reviewer: str,
    issued_at: str,
) -> dict[str, object]:
    return {
        "decision": "accepted",
        "issued_at": issued_at,
        "kind": "human_review",
        "program_sha256": program_sha256,
        "registry_authority_sha256": registry_authority_sha256,
        "reviewed_qualifications": [item.to_dict() for item in reviewed_qualifications],
        "reviewer": reviewer,
        "schema_version": HumanReviewRecord.SCHEMA_VERSION,
        "scope": scope.to_dict(),
    }


@dataclass(frozen=True, slots=True)
class HumanReviewRecord:
    review_id: str
    scope: ComparisonScope
    program_sha256: str
    registry_authority_sha256: str
    reviewed_qualifications: tuple[QualificationReference, ...]
    reviewer: str
    issued_at: str

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.review_id, field="review_id")
        if not isinstance(self.scope, ComparisonScope):
            raise ProtocolValidationError("review scope must be a ComparisonScope")
        require_sha256(self.program_sha256, field="review.program_sha256")
        require_sha256(
            self.registry_authority_sha256,
            field="review.registry_authority_sha256",
        )
        qualifications = tuple(
            item
            if isinstance(item, QualificationReference)
            else QualificationReference.from_dict(item)
            for item in self.reviewed_qualifications
        )
        if len(qualifications) != 4:
            raise ProtocolValidationError("human review must bind exactly four qualifications")
        if len({item.baseline_id for item in qualifications}) != len(qualifications):
            raise ProtocolValidationError("human review qualification IDs must be unique")
        object.__setattr__(self, "reviewed_qualifications", qualifications)
        require_identifier(self.reviewer, field="review.reviewer")
        require_single_line_public_string(self.issued_at, field="review.issued_at")
        expected = f"review-{content_sha256(self._payload())[:20]}"
        if self.review_id != expected:
            raise ProtocolValidationError(
                f"review_id does not match record content; expected {expected}"
            )

    def _payload(self) -> dict[str, object]:
        return _human_review_payload(
            scope=self.scope,
            program_sha256=self.program_sha256,
            registry_authority_sha256=self.registry_authority_sha256,
            reviewed_qualifications=self.reviewed_qualifications,
            reviewer=self.reviewer,
            issued_at=self.issued_at,
        )

    def to_dict(self) -> dict[str, object]:
        return {"review_id": self.review_id, **self._payload()}

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def create(
        cls,
        *,
        scope: ComparisonScope,
        program: BaselineProgram,
        registry: BaselineRegistry,
        reviewed_qualifications: tuple[QualificationReference, ...],
        reviewer: str,
        issued_at: str,
    ) -> HumanReviewRecord:
        normalized = tuple(reviewed_qualifications)
        current = {
            item.baseline_id: item
            for item in _qualification_references(program=program, registry=registry, scope=scope)
        }
        if any(current.get(item.baseline_id) != item for item in normalized):
            raise ProtocolValidationError(
                "human review qualifications must match the current Comparison Scope"
            )
        values = {
            "scope": scope,
            "program_sha256": program.program_sha256,
            "registry_authority_sha256": program_registry_authority_sha256(program, registry),
            "reviewed_qualifications": normalized,
            "reviewer": reviewer,
            "issued_at": issued_at,
        }
        payload = _human_review_payload(**values)
        return cls(
            review_id=f"review-{content_sha256(payload)[:20]}",
            **values,
        )

    @classmethod
    def from_dict(cls, value: object) -> HumanReviewRecord:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "review_id",
                "decision",
                "scope",
                "program_sha256",
                "registry_authority_sha256",
                "reviewed_qualifications",
                "reviewer",
                "issued_at",
            ),
            context="HumanReviewRecord",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("HumanReviewRecord schema_version must be 1")
        if payload.pop("kind") != "human_review":
            raise ProtocolValidationError("HumanReviewRecord kind must be human_review")
        if payload.pop("decision") != "accepted":
            raise ProtocolValidationError("HumanReviewRecord decision must be accepted")
        qualifications = payload.pop("reviewed_qualifications")
        if not isinstance(qualifications, list):
            raise ProtocolValidationError(
                "HumanReviewRecord reviewed_qualifications must be a list"
            )
        return cls(
            scope=ComparisonScope.from_dict(payload.pop("scope")),
            reviewed_qualifications=tuple(
                QualificationReference.from_dict(item) for item in qualifications
            ),
            **payload,
        )

    @classmethod
    def from_json(cls, text: str) -> HumanReviewRecord:
        return cls.from_dict(parse_json_object(text, context="HumanReviewRecord"))

    @classmethod
    def load(cls, path: str | Path) -> HumanReviewRecord:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class BenchmarkState:
    scope: ComparisonScope
    program_sha256: str
    registry_authority_sha256: str
    qualifications: tuple[QualificationReference, ...]
    review_state: HumanReviewState
    discovery_eligible: bool

    @property
    def qualified_baseline_ids(self) -> tuple[str, ...]:
        return tuple(item.baseline_id for item in self.qualifications)

    @property
    def qualified_count(self) -> int:
        return len(self.qualifications)


def _matching_qualification(
    baseline_qualifications: tuple[ComparisonQualification, ...],
    scope: ComparisonScope,
) -> ComparisonQualification | None:
    return next(
        (
            qualification
            for qualification in baseline_qualifications
            if qualification.matches(
                protocol_version=scope.protocol_version,
                dataset_manifest_sha256=scope.dataset_manifest_sha256,
                adaptation_budget_sha256=scope.adaptation_budget_sha256,
                protocol_amendment_sha256=scope.protocol_amendment_sha256,
                method_profile_sha256=scope.method_profile_sha256,
            )
        ),
        None,
    )


def _qualification_references(
    *,
    program: BaselineProgram,
    registry: BaselineRegistry,
    scope: ComparisonScope,
) -> tuple[QualificationReference, ...]:
    qualifications: list[QualificationReference] = []
    for baseline_id in program.candidate_ids:
        baseline = registry.get(baseline_id)
        if not baseline.is_comparable:
            continue
        qualification = _matching_qualification(baseline.comparison_qualifications, scope)
        if qualification is not None:
            qualifications.append(
                QualificationReference(baseline_id, qualification.qualification_sha256)
            )
    return tuple(qualifications)


def derive_benchmark_state(
    *,
    program: BaselineProgram,
    registry: BaselineRegistry,
    scope: ComparisonScope,
    review: HumanReviewRecord | None = None,
) -> BenchmarkState:
    qualifications = _qualification_references(program=program, registry=registry, scope=scope)
    authority_sha256 = program_registry_authority_sha256(program, registry)
    if len(qualifications) < 4:
        review_state = HumanReviewState.NOT_REQUIRED
    elif review is not None and (
        review.scope == scope
        and review.program_sha256 == program.program_sha256
        and review.registry_authority_sha256 == authority_sha256
        and all(item in qualifications for item in review.reviewed_qualifications)
    ):
        review_state = HumanReviewState.ACCEPTED
    else:
        review_state = HumanReviewState.PENDING
    return BenchmarkState(
        scope=scope,
        program_sha256=program.program_sha256,
        registry_authority_sha256=authority_sha256,
        qualifications=qualifications,
        review_state=review_state,
        discovery_eligible=(
            len(qualifications) == len(program.candidate_ids)
            and review_state is HumanReviewState.ACCEPTED
        ),
    )


@dataclass(frozen=True, slots=True)
class LiveBenchmarkAuthority:
    """Current correlated records from which benchmark status may project."""

    program: BaselineProgram
    audits: tuple[BaselineAudit, ...]
    reviews: AuditReviewSet
    registry: BaselineRegistry
    scope: ComparisonScope
    selection: SelectionResult
    review: HumanReviewRecord | None
    benchmark_state: BenchmarkState

    def __post_init__(self) -> None:
        audits = tuple(
            item if isinstance(item, BaselineAudit) else BaselineAudit.from_dict(item)
            for item in self.audits
        )
        object.__setattr__(self, "audits", audits)
        if not isinstance(self.reviews, AuditReviewSet):
            object.__setattr__(self, "reviews", AuditReviewSet.from_dict(self.reviews))
        if not isinstance(self.scope, ComparisonScope):
            object.__setattr__(self, "scope", ComparisonScope.from_dict(self.scope))
        if not isinstance(self.selection, SelectionResult):
            object.__setattr__(self, "selection", SelectionResult.from_dict(self.selection))
        if self.review is not None and not isinstance(self.review, HumanReviewRecord):
            object.__setattr__(self, "review", HumanReviewRecord.from_dict(self.review))
        self.program.validate_audits(self.audits)
        current_state = derive_benchmark_state(
            program=self.program,
            registry=self.registry,
            scope=self.scope,
            review=self.review,
        )
        if self.review is not None and current_state.review_state is not HumanReviewState.ACCEPTED:
            raise ProtocolValidationError("human review is stale")
        if self.benchmark_state != current_state:
            raise ProtocolValidationError("live benchmark state does not match current authorities")
        if self.selection.program_sha256 != self.program.program_sha256:
            raise ProtocolValidationError("selection program authority does not match")
        if self.selection.audit_set_sha256 != self.audit_set_sha256:
            raise ProtocolValidationError("selection audit set authority does not match")
        if self.selection.review_set_sha256 != self.review_set_sha256:
            raise ProtocolValidationError("selection review set authority does not match")
        if self.selection.registry_authority_sha256 != current_state.registry_authority_sha256:
            raise ProtocolValidationError("selection registry authority does not match")
        if self.selection.scope_sha256 != self.scope.scope_sha256:
            raise ProtocolValidationError("selection scope authority does not match")
        expected_selection = SelectionSpecification(
            version=self.selection.specification_version
        ).select(
            self.program,
            self.audits,
            self.reviews,
            tuple(candidate.diagnostics for candidate in self.selection.candidates),
            registry_authority_sha256=current_state.registry_authority_sha256,
            scope_sha256=self.scope.scope_sha256,
        )
        if self.selection != expected_selection:
            raise ProtocolValidationError("selection does not match current hard-gate result")

    @property
    def audit_set_sha256(self) -> str:
        return content_sha256({"audits": [item.audit_sha256 for item in self.audits]})

    @property
    def review_set_sha256(self) -> str:
        return content_sha256(self.reviews.to_dict())

    @property
    def selection_sha256(self) -> str:
        return content_sha256(self.selection.to_dict())

    def accepts_selection_acceptance(self, acceptance: SelectionAcceptance | None) -> bool:
        return acceptance is not None and acceptance.matches(self.selection)

    @classmethod
    def create(
        cls,
        *,
        program: BaselineProgram,
        audits: tuple[BaselineAudit, ...],
        reviews: AuditReviewSet,
        registry: BaselineRegistry,
        scope: ComparisonScope,
        selection: SelectionResult,
        review: HumanReviewRecord | None = None,
    ) -> LiveBenchmarkAuthority:
        return cls(
            program=program,
            audits=audits,
            reviews=reviews,
            registry=registry,
            scope=scope,
            selection=selection,
            review=review,
            benchmark_state=derive_benchmark_state(
                program=program,
                registry=registry,
                scope=scope,
                review=review,
            ),
        )


__all__ = (
    "BenchmarkState",
    "ComparisonScope",
    "HumanReviewRecord",
    "HumanReviewState",
    "LiveBenchmarkAuthority",
    "QualificationReference",
    "derive_benchmark_state",
    "program_registry_authority_sha256",
)
