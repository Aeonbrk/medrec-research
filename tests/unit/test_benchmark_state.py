from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from medrec_research.baseline_audit import BaselineProgram
from medrec_research.benchmark_state import (
    ComparisonScope,
    HumanReviewRecord,
    HumanReviewState,
    derive_benchmark_state,
)
from medrec_research.comparison_scope import ComparisonScope as ProtocolComparisonScope
from medrec_research.registry import (
    BaselineDefinition,
    BaselineReadiness,
    BaselineRegistry,
    ComparisonQualification,
    ReadinessEvidence,
    ReadinessGate,
    ResearchMode,
    SourceIdentity,
    SourceStatus,
)

ROOT = Path(__file__).parents[2]
REVIEW_FIXTURE = ROOT / "fixtures" / "benchmark" / "human-review.json"
CLASSIC_SIX = (
    "gamenet",
    "safedrug",
    "micron",
    "molerec",
    "retain",
    "leap-safedrug",
)
PROGRAM = BaselineProgram(program_id="classic-six", candidate_ids=CLASSIC_SIX)
SCOPE = ComparisonScope(
    protocol_version="1.0",
    dataset_manifest_sha256="d" * 64,
    adaptation_budget_sha256="a" * 64,
)
OTHER_SCOPE = ComparisonScope(
    protocol_version="1.0",
    dataset_manifest_sha256="0" * 64,
    adaptation_budget_sha256="b" * 64,
)


def test_comparison_scope_is_protocol_owned_identity_matcher() -> None:
    assert ProtocolComparisonScope is ComparisonScope
    assert SCOPE.matches(
        protocol_version="1.0",
        dataset_manifest_sha256="d" * 64,
        adaptation_budget_sha256="a" * 64,
    )
    assert not SCOPE.matches(
        protocol_version="1.0",
        dataset_manifest_sha256="0" * 64,
        adaptation_budget_sha256="a" * 64,
    )


def _registered_baseline(baseline_id: str) -> BaselineDefinition:
    return BaselineDefinition(
        baseline_id=baseline_id,
        display_name=baseline_id,
        source=SourceIdentity(
            repository=f"https://example.invalid/{baseline_id}.git",
            revision=f"{baseline_id}-0123456789abcdef",
            status=SourceStatus.PINNED,
        ),
        supported_modes=(ResearchMode.REPRODUCTION, ResearchMode.COMPARISON),
        readiness=BaselineReadiness.REGISTERED,
        adapter_command=("python", "adapter.py"),
        adapter_revision=f"{baseline_id}-adapter-0123456789abcdef",
        environment_sha256="e" * 64,
    )


def _qualification(scope: ComparisonScope, digit: str) -> ComparisonQualification:
    return ComparisonQualification(
        protocol_version=scope.protocol_version,
        dataset_manifest_sha256=scope.dataset_manifest_sha256,
        adaptation_budget_sha256=scope.adaptation_budget_sha256,
        evidence=(
            ReadinessEvidence(ReadinessGate.ADAPTATION_BUDGET, scope.adaptation_budget_sha256),
            ReadinessEvidence(ReadinessGate.COHORT_IDENTITY, digit * 64),
            ReadinessEvidence(ReadinessGate.CORE_INTEGRITY, str((int(digit) + 1) % 10) * 64),
            ReadinessEvidence(
                ReadinessGate.DETERMINISTIC_ADAPTER,
                str((int(digit) + 2) % 10) * 64,
            ),
            ReadinessEvidence(
                ReadinessGate.INDEPENDENT_EVALUATION,
                str((int(digit) + 3) % 10) * 64,
            ),
        ),
    )


def _registry_with_qualified(
    *qualified_ids: str,
    comparison_ready_ids: tuple[str, ...] = (),
) -> BaselineRegistry:
    baselines = []
    for ordinal, baseline_id in enumerate(CLASSIC_SIX, start=1):
        baseline = _registered_baseline(baseline_id)
        if baseline_id in qualified_ids or baseline_id in comparison_ready_ids:
            qualification_scope = SCOPE if baseline_id in qualified_ids else OTHER_SCOPE
            baseline = baseline.advance_readiness(
                BaselineReadiness.SMOKE_READY,
                evidence=(
                    ReadinessEvidence(ReadinessGate.ADAPTER_SMOKE, "1" * 64),
                    ReadinessEvidence(ReadinessGate.ENVIRONMENT_LOCK, "2" * 64),
                ),
            ).advance_readiness(
                BaselineReadiness.COMPARISON_READY,
                qualifications=(_qualification(qualification_scope, str(ordinal)),),
            )
        baselines.append(baseline)
    return BaselineRegistry(tuple(baselines))


def test_three_same_scope_qualifications_do_not_require_review() -> None:
    state = derive_benchmark_state(
        program=PROGRAM,
        registry=_registry_with_qualified(*CLASSIC_SIX[:3]),
        scope=SCOPE,
    )

    assert state.qualified_baseline_ids == CLASSIC_SIX[:3]
    assert state.review_state is HumanReviewState.NOT_REQUIRED
    assert not state.discovery_eligible


def test_four_same_scope_qualifications_require_content_addressed_review() -> None:
    registry = _registry_with_qualified(*CLASSIC_SIX[:4])
    pending = derive_benchmark_state(program=PROGRAM, registry=registry, scope=SCOPE)

    assert pending.review_state is HumanReviewState.PENDING

    review = HumanReviewRecord.create(
        scope=SCOPE,
        program=PROGRAM,
        registry=registry,
        reviewed_qualifications=pending.qualifications,
        reviewer="research-steward",
        issued_at="2026-07-11T00:00:00Z",
    )
    accepted = derive_benchmark_state(
        program=PROGRAM,
        registry=registry,
        scope=SCOPE,
        review=HumanReviewRecord.from_json(review.to_json()),
    )

    assert accepted.review_state is HumanReviewState.ACCEPTED
    assert not accepted.discovery_eligible
    assert HumanReviewRecord.load(REVIEW_FIXTURE).review_id


def test_global_readiness_does_not_cross_comparison_scopes() -> None:
    registry = _registry_with_qualified(
        *CLASSIC_SIX[:3],
        comparison_ready_ids=CLASSIC_SIX,
    )

    state = derive_benchmark_state(program=PROGRAM, registry=registry, scope=SCOPE)

    assert state.qualified_count == 3
    assert state.review_state is HumanReviewState.NOT_REQUIRED


def test_six_qualifications_still_require_review() -> None:
    state = derive_benchmark_state(
        program=PROGRAM,
        registry=_registry_with_qualified(*CLASSIC_SIX),
        scope=SCOPE,
    )

    assert state.qualified_count == 6
    assert state.review_state is HumanReviewState.PENDING
    assert not state.discovery_eligible


def test_later_fifth_and_sixth_qualifications_preserve_accepted_review() -> None:
    four_registry = _registry_with_qualified(
        *CLASSIC_SIX[:4],
        comparison_ready_ids=CLASSIC_SIX,
    )
    four_state = derive_benchmark_state(program=PROGRAM, registry=four_registry, scope=SCOPE)
    review = HumanReviewRecord.create(
        scope=SCOPE,
        program=PROGRAM,
        registry=four_registry,
        reviewed_qualifications=four_state.qualifications,
        reviewer="research-steward",
        issued_at="2026-07-11T00:00:00Z",
    )
    six_registry = _registry_with_qualified(
        *CLASSIC_SIX,
        comparison_ready_ids=CLASSIC_SIX,
    )

    six_state = derive_benchmark_state(
        program=PROGRAM,
        registry=six_registry,
        scope=SCOPE,
        review=review,
    )

    assert six_state.registry_authority_sha256 == four_state.registry_authority_sha256
    assert six_state.review_state is HumanReviewState.ACCEPTED
    assert six_state.discovery_eligible


def test_program_definition_or_reviewed_qualification_drift_returns_to_pending() -> None:
    registry = _registry_with_qualified(*CLASSIC_SIX[:4])
    state = derive_benchmark_state(program=PROGRAM, registry=registry, scope=SCOPE)
    review = HumanReviewRecord.create(
        scope=SCOPE,
        program=PROGRAM,
        registry=registry,
        reviewed_qualifications=state.qualifications,
        reviewer="research-steward",
        issued_at="2026-07-11T00:00:00Z",
    )

    renamed = BaselineRegistry(
        (replace(registry.baselines[0], display_name="Changed GAMENet"), *registry.baselines[1:])
    )
    assert (
        derive_benchmark_state(
            program=PROGRAM,
            registry=renamed,
            scope=SCOPE,
            review=review,
        ).review_state
        is HumanReviewState.PENDING
    )

    first = registry.baselines[0]
    qualification = first.comparison_qualifications[0]
    changed_evidence = tuple(
        replace(item, artifact_sha256="9" * 64)
        if item.gate is ReadinessGate.CORE_INTEGRITY
        else item
        for item in qualification.evidence
    )
    changed_first = replace(
        first,
        comparison_qualifications=(replace(qualification, evidence=changed_evidence),),
    )
    changed_qualification = BaselineRegistry((changed_first, *registry.baselines[1:]))
    assert (
        derive_benchmark_state(
            program=PROGRAM,
            registry=changed_qualification,
            scope=SCOPE,
            review=review,
        ).review_state
        is HumanReviewState.PENDING
    )


def test_registry_entries_outside_program_do_not_affect_state_or_review() -> None:
    registry = _registry_with_qualified(*CLASSIC_SIX[:4])
    state = derive_benchmark_state(program=PROGRAM, registry=registry, scope=SCOPE)
    review = HumanReviewRecord.create(
        scope=SCOPE,
        program=PROGRAM,
        registry=registry,
        reviewed_qualifications=state.qualifications,
        reviewer="research-steward",
        issued_at="2026-07-11T00:00:00Z",
    )
    expanded = BaselineRegistry((*registry.baselines, _registered_baseline("reference")))

    expanded_state = derive_benchmark_state(
        program=PROGRAM,
        registry=expanded,
        scope=SCOPE,
        review=review,
    )

    assert expanded_state.registry_authority_sha256 == state.registry_authority_sha256
    assert expanded_state.review_state is HumanReviewState.ACCEPTED
