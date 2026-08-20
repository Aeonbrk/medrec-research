from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from medrec_research.baseline_audit import AuditReviewSet, BaselineAudit, BaselineProgram
from medrec_research.benchmark_program import (
    Diagnostic,
    ReproductionAttempt,
    ReproductionCharacterization,
    ReproductionStabilityPolicy,
    SelectionAcceptance,
    SelectionDiagnostic,
    SelectionResult,
    SelectionSpecification,
    StabilityStatus,
    VarianceCheck,
)
from medrec_research.benchmark_state import ComparisonScope, program_registry_authority_sha256
from medrec_research.errors import ProtocolValidationError
from medrec_research.registry import BaselineRegistry, ReadinessEvidence, ReadinessGate

ROOT = Path(__file__).parents[2]
AUDIT_DIR = ROOT / "baselines" / "audits"
PROGRAM_PATH = ROOT / "baselines" / "programs" / "final-five.toml"
REVIEWS_PATH = ROOT / "fixtures" / "benchmark" / "audit-reviews.json"
REGISTRY_PATH = ROOT / "baselines" / "registry.toml"
SELECTION_FIXTURE = ROOT / "fixtures" / "benchmark" / "selection-result.json"
CHARACTERIZATION_FIXTURE = ROOT / "fixtures" / "benchmark" / "reproduction-characterization-v1.json"
CURRENT_CHARACTERIZATION_FIXTURE = (
    ROOT / "fixtures" / "benchmark" / "reproduction-characterization.json"
)
SELECTION_ACCEPTANCE_FIXTURE = ROOT / "fixtures" / "benchmark" / "selection-acceptance.json"
PRIORITY = (
    "gamenet",
    "safedrug",
    "molerec",
    "retain",
    "leap-safedrug",
)
V2_OUTPUT_IDS = (
    "jaccard",
    "precision",
    "recall",
    "f1",
    "mean_medication_count",
)
GAMENET_COMMIT = "da695b4fc9390882f3a681c82115e81291ae6380"
GAMENET_FULL_SEEDS = (7, 19, 31)


def _authorities() -> tuple[BaselineProgram, tuple[BaselineAudit, ...], AuditReviewSet]:
    program = BaselineProgram.load(PROGRAM_PATH)
    audits = tuple(BaselineAudit.load(AUDIT_DIR / f"{candidate}.toml") for candidate in PRIORITY)
    return program, audits, AuditReviewSet.load(REVIEWS_PATH)


def _diagnostics(audits: tuple[BaselineAudit, ...]) -> tuple[SelectionDiagnostic, ...]:
    values = ("low", "high", "medium", "low", "high", "unresolved")
    return tuple(
        SelectionDiagnostic(
            baseline_id=audit.baseline_id,
            priority_ordinal=ordinal,
            comparison_representativeness=Diagnostic(
                value=values[ordinal], evidence_ids=(audit.evidence[0].evidence_id,)
            ),
            reproduction_risk=Diagnostic(
                value="high" if ordinal == 0 else "low",
                evidence_ids=(audit.evidence[0].evidence_id,),
            ),
            integration_cost=Diagnostic(
                value="high" if ordinal == 0 else "low",
                evidence_ids=(audit.evidence[0].evidence_id,),
            ),
        )
        for ordinal, audit in enumerate(audits)
    )


def _select(
    program: BaselineProgram,
    audits: tuple[BaselineAudit, ...],
    reviews: AuditReviewSet,
    diagnostics: tuple[SelectionDiagnostic, ...],
    *,
    specification: SelectionSpecification | None = None,
) -> SelectionResult:
    scope = ComparisonScope(
        protocol_version="1.0",
        dataset_manifest_sha256="d" * 64,
        adaptation_budget_sha256="a" * 64,
    )
    registry = BaselineRegistry.load(REGISTRY_PATH)
    return (specification or SelectionSpecification()).select(
        program,
        audits,
        reviews,
        diagnostics,
        registry_authority_sha256=program_registry_authority_sha256(program, registry),
        scope_sha256=scope.scope_sha256,
    )


def test_selection_uses_accepted_hard_gates_before_fixed_priority() -> None:
    program, audits, reviews = _authorities()
    diagnostics = _diagnostics(audits)

    result = _select(
        program,
        audits,
        reviews,
        diagnostics,
        specification=SelectionSpecification(),
    )

    assert result.status == "proposed"
    assert result.selected_candidate_id == "gamenet"
    assert tuple(candidate.baseline_id for candidate in result.candidates) == PRIORITY
    assert result.candidates[0].diagnostics.reproduction_risk.value == "high"
    assert result == SelectionResult.from_json(result.to_json())


def test_selection_records_license_without_treating_it_as_a_hard_gate() -> None:
    program, audits, reviews = _authorities()
    assert SelectionSpecification().version == 2
    assert SelectionSpecification().hard_gates == ("source",)
    result = _select(program, audits, reviews, _diagnostics(audits))

    assert result.selected_candidate_id == "gamenet"
    assert result.candidates[0].blockers == ()

    v1_result = _select(
        program,
        audits,
        reviews,
        _diagnostics(audits),
        specification=SelectionSpecification(version=1),
    )

    assert v1_result.selected_candidate_id is None
    assert v1_result.candidates[0].blockers == ("license_not_pass",)


def test_selection_returns_deterministic_blocked_result_when_none_are_eligible() -> None:
    program, audits, _ = _authorities()
    specification = SelectionSpecification()

    first = _select(
        program,
        audits,
        AuditReviewSet(()),
        _diagnostics(audits),
        specification=specification,
    )
    second = _select(
        program,
        audits,
        AuditReviewSet(()),
        _diagnostics(audits),
        specification=specification,
    )

    assert first == second
    assert first.status == "blocked"
    assert first.selected_candidate_id is None
    assert all(candidate.blockers for candidate in first.candidates)


def test_selection_rejects_incomplete_or_non_predeclared_inputs() -> None:
    program, audits, reviews = _authorities()
    diagnostics = _diagnostics(audits)

    with pytest.raises(ProtocolValidationError, match=r"selection blocked.*final-five audits"):
        _select(program, audits[:-1], reviews, diagnostics[:-1])

    unknown = list(diagnostics)
    unknown[-1] = SelectionDiagnostic(
        baseline_id="other",
        priority_ordinal=5,
        comparison_representativeness=unknown[-1].comparison_representativeness,
        reproduction_risk=unknown[-1].reproduction_risk,
        integration_cost=unknown[-1].integration_cost,
    )
    with pytest.raises(ProtocolValidationError, match="fixed priority order"):
        _select(program, audits, reviews, tuple(unknown))

    duplicate_ordinal = list(diagnostics)
    duplicate_ordinal[1] = SelectionDiagnostic(
        baseline_id="safedrug",
        priority_ordinal=0,
        comparison_representativeness=duplicate_ordinal[1].comparison_representativeness,
        reproduction_risk=duplicate_ordinal[1].reproduction_risk,
        integration_cost=duplicate_ordinal[1].integration_cost,
    )
    with pytest.raises(ProtocolValidationError, match="fixed priority order"):
        _select(program, audits, reviews, tuple(duplicate_ordinal))

    payload = diagnostics[-1].to_dict()
    payload["comparison_representativeness"]["value"] = "favorable"
    with pytest.raises(ProtocolValidationError, match="diagnostic value"):
        SelectionDiagnostic.from_dict(payload)


def test_selection_receipt_rejects_authority_or_candidate_drift() -> None:
    program, audits, reviews = _authorities()
    result = _select(program, audits, reviews, _diagnostics(audits))

    for field, value in (
        ("specification_sha256", "0" * 64),
        ("program_sha256", "1" * 64),
        ("review_set_sha256", "2" * 64),
        ("registry_authority_sha256", "3" * 64),
        ("scope_sha256", "4" * 64),
        ("selected_candidate_id", "retain"),
    ):
        payload = deepcopy(result.to_dict())
        payload[field] = value
        with pytest.raises(ProtocolValidationError):
            SelectionResult.from_dict(payload)


def test_selection_result_reports_its_required_schema_version() -> None:
    program, audits, reviews = _authorities()
    result = _select(program, audits, reviews, _diagnostics(audits))
    payload = result.to_dict()
    payload["schema_version"] = 3

    with pytest.raises(ProtocolValidationError, match="schema_version must be 2"):
        SelectionResult.from_dict(payload)


def _attempt(number: int, **overrides: object) -> ReproductionAttempt:
    payload: dict[str, object] = {
        "attempt_id": f"attempt-{number}",
        "outcome": "completed",
        "source_sha256": "1" * 64,
        "environment_sha256": "2" * 64,
        "adapter_sha256": "3" * 64,
        "adapter_smoke_sha256": "4" * 64,
        "input_manifest_sha256": "5" * 64,
        "seed_policy_sha256": "6" * 64,
        "artifact_sha256": f"{number + 6:x}" * 64,
    }
    payload.update(overrides)
    return ReproductionAttempt(**payload)


def _characterization(**overrides: object) -> ReproductionCharacterization:
    payload: dict[str, object] = {
        "baseline_id": "gamenet",
        "mode": "reproduction",
        "accepted_selection_sha256": "a" * 64,
        "planned_attempts": 2,
        "attempts": (_attempt(1), _attempt(2)),
        "protocol_violations": 0,
        "variance_checks": (
            VarianceCheck(
                check_id="medication-count",
                predeclared=True,
                tolerance=0.01,
                observed_variance=0.005,
                evidence_sha256="b" * 64,
            ),
        ),
        "upstream_reference_sha256": "c" * 64,
        "split_semantics_sha256": "d" * 64,
        "selection_semantics_sha256": "e" * 64,
        "evaluation_semantics_sha256": "f" * 64,
    }
    payload.update(overrides)
    return ReproductionCharacterization.create(ReproductionStabilityPolicy(version=1), **payload)


def _v2_variance_checks() -> tuple[VarianceCheck, ...]:
    return tuple(
        VarianceCheck(
            check_id=output_id,
            predeclared=True,
            tolerance=0.01,
            observed_variance=0.005,
            evidence_sha256=f"{ordinal:x}" * 64,
        )
        for ordinal, output_id in enumerate(V2_OUTPUT_IDS, start=1)
    )


def _v2_characterization(**overrides: object) -> ReproductionCharacterization:
    payload: dict[str, object] = {
        "baseline_id": "gamenet",
        "mode": "reproduction",
        "selection_acceptance_sha256": "a" * 64,
        "planned_attempts": 2,
        "attempts": (_attempt(1), _attempt(2)),
        "protocol_violations": 0,
        "variance_checks": _v2_variance_checks(),
        "upstream_reference_sha256": "c" * 64,
        "split_semantics_sha256": "d" * 64,
        "selection_semantics_sha256": "e" * 64,
        "evaluation_semantics_sha256": "f" * 64,
    }
    payload.update(overrides)
    return ReproductionCharacterization.create(ReproductionStabilityPolicy(), **payload)


def _v3_characterization(**overrides: object) -> ReproductionCharacterization:
    payload: dict[str, object] = {
        "baseline_id": "gamenet",
        "mode": "reproduction",
        "selection_acceptance_sha256": "a" * 64,
        "planned_attempts": len(GAMENET_FULL_SEEDS),
        "attempts": tuple(
            _attempt(
                ordinal,
                seed=seed,
                source_revision=GAMENET_COMMIT,
                dataset_id="mimic-iii-v1.4",
            )
            for ordinal, seed in enumerate(GAMENET_FULL_SEEDS, start=1)
        ),
        "protocol_violations": 0,
        "variance_checks": _v2_variance_checks(),
        "upstream_reference_sha256": "c" * 64,
        "split_semantics_sha256": "d" * 64,
        "selection_semantics_sha256": "e" * 64,
        "evaluation_semantics_sha256": "f" * 64,
    }
    payload.update(overrides)
    return ReproductionCharacterization.create(ReproductionStabilityPolicy(version=3), **payload)


def test_reproduction_characterization_is_stable_only_with_complete_repeat_evidence() -> None:
    characterization = _characterization()

    assert characterization.evaluate() is StabilityStatus.STABLE
    assert characterization == ReproductionCharacterization.from_json(characterization.to_json())
    assert characterization == ReproductionCharacterization.load(CHARACTERIZATION_FIXTURE)


def test_selection_acceptance_binds_only_the_current_selected_candidate() -> None:
    selection = SelectionResult.load(SELECTION_FIXTURE)

    acceptance = SelectionAcceptance.create(
        selection=selection,
        candidate_id="gamenet",
        reviewer="research-steward",
        issued_at="2026-07-12T00:00:00Z",
    )

    assert acceptance.matches(selection)
    assert acceptance == SelectionAcceptance.from_json(acceptance.to_json())
    assert acceptance == SelectionAcceptance.load(SELECTION_ACCEPTANCE_FIXTURE)
    with pytest.raises(ProtocolValidationError, match="selected candidate"):
        SelectionAcceptance.create(
            selection=selection,
            candidate_id="retain",
            reviewer="research-steward",
            issued_at="2026-07-12T00:00:00Z",
        )


def test_v2_stability_policy_owns_complete_canonical_output_ids() -> None:
    policy = ReproductionStabilityPolicy()
    characterization = _v2_characterization()

    assert policy.version == 2
    assert policy.expected_output_ids == V2_OUTPUT_IDS
    assert characterization.evaluate() is StabilityStatus.STABLE
    assert characterization.selection_acceptance_sha256 == "a" * 64
    fixture = ReproductionCharacterization.load(CURRENT_CHARACTERIZATION_FIXTURE)
    assert fixture.policy_version == 2
    assert fixture.baseline_id == "gamenet"

    with pytest.raises(ProtocolValidationError, match="canonical expected output IDs"):
        ReproductionStabilityPolicy(expected_output_ids=("jaccard",))

    assert _v2_characterization(variance_checks=_v2_variance_checks()[:-1]).evaluate() is (
        StabilityStatus.UNRESOLVED
    )
    with pytest.raises(ProtocolValidationError, match="unexpected output"):
        _v2_characterization(
            variance_checks=(
                *_v2_variance_checks()[:-1],
                VarianceCheck("unknown-output", True, 0.01, 0.005, "9" * 64),
            )
        )
    with pytest.raises(ProtocolValidationError, match="variance check IDs must be unique"):
        _v2_characterization(variance_checks=(*_v2_variance_checks(), _v2_variance_checks()[0]))


def test_controlled_gamenet_policy_requires_the_full_predeclared_seed_set() -> None:
    policy = ReproductionStabilityPolicy(version=3)
    characterization = _v3_characterization()

    assert policy.expected_seeds == GAMENET_FULL_SEEDS
    assert characterization.evaluate() is StabilityStatus.STABLE
    assert characterization == ReproductionCharacterization.from_json(characterization.to_json())
    assert (
        _v3_characterization(
            attempts=(
                _attempt(1, seed=7, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
                _attempt(2, seed=19, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
                _attempt(3, seed=0, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
            )
        ).evaluate()
        is StabilityStatus.FAILED
    )
    assert (
        _v3_characterization(
            planned_attempts=4,
            attempts=(
                _attempt(1, seed=7, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
                _attempt(2, seed=19, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
                _attempt(3, seed=31, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
                _attempt(4, seed=7, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
            ),
        ).evaluate()
        is StabilityStatus.FAILED
    )


def test_controlled_gamenet_characterization_binds_to_smoke_ready_registry_identity() -> None:
    baseline = BaselineRegistry.load(REGISTRY_PATH).get("gamenet")
    pinned = replace(
        baseline,
        source=replace(baseline.source, revision=GAMENET_COMMIT, status="pinned"),
        adapter_command=("python", "adapter.py"),
        adapter_revision="3" * 64,
        environment_sha256="2" * 64,
    ).advance_readiness(
        "smoke_ready",
        evidence=(
            ReadinessEvidence(ReadinessGate.ADAPTER_SMOKE, "4" * 64),
            ReadinessEvidence(ReadinessGate.ENVIRONMENT_LOCK, "2" * 64),
        ),
    )

    assert _v3_characterization().matches_baseline_definition(pinned)
    assert not _v3_characterization(
        attempts=(
            _attempt(1, seed=7, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
            _attempt(2, seed=19, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
            _attempt(3, seed=31, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
        )
    ).matches_baseline_definition(replace(pinned, adapter_revision="9" * 64))
    assert not _v3_characterization().matches_baseline_definition(
        replace(
            pinned,
            readiness_evidence=(
                ReadinessEvidence(ReadinessGate.ADAPTER_SMOKE, "9" * 64),
                ReadinessEvidence(ReadinessGate.ENVIRONMENT_LOCK, "2" * 64),
            ),
        )
    )
    assert (
        _v3_characterization(
            attempts=(
                _attempt(1, seed=7, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
                _attempt(2, seed=19, source_revision=GAMENET_COMMIT, dataset_id="mimic-iii-v1.4"),
                _attempt(3, seed=31, source_revision=GAMENET_COMMIT, dataset_id="mimic-iv-v2.2"),
            )
        ).evaluate()
        is StabilityStatus.FAILED
    )


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"planned_attempts": None}, StabilityStatus.UNRESOLVED),
        ({"planned_attempts": 1, "attempts": (_attempt(1),)}, StabilityStatus.UNRESOLVED),
        ({"attempts": (_attempt(1),)}, StabilityStatus.FAILED),
        (
            {"attempts": (_attempt(1), _attempt(2, outcome="failed"))},
            StabilityStatus.FAILED,
        ),
        ({"protocol_violations": None}, StabilityStatus.UNRESOLVED),
        ({"protocol_violations": 1}, StabilityStatus.FAILED),
        ({"variance_checks": ()}, StabilityStatus.UNRESOLVED),
        (
            {"variance_checks": (VarianceCheck("medication-count", False, 0.01, 0.005, "b" * 64),)},
            StabilityStatus.FAILED,
        ),
        (
            {"variance_checks": (VarianceCheck("medication-count", True, 0.01, 0.02, "b" * 64),)},
            StabilityStatus.FAILED,
        ),
        ({"upstream_reference_sha256": None}, StabilityStatus.UNRESOLVED),
        ({"split_semantics_sha256": None}, StabilityStatus.UNRESOLVED),
        ({"selection_semantics_sha256": None}, StabilityStatus.UNRESOLVED),
        ({"evaluation_semantics_sha256": None}, StabilityStatus.UNRESOLVED),
        ({"mode": "comparison"}, StabilityStatus.FAILED),
        ({"accepted_selection_sha256": None}, StabilityStatus.UNRESOLVED),
        (
            {"attempts": (_attempt(1), _attempt(2, seed_policy_sha256="9" * 64))},
            StabilityStatus.FAILED,
        ),
        (
            {"attempts": (_attempt(1), _attempt(2, artifact_sha256=None))},
            StabilityStatus.UNRESOLVED,
        ),
        (
            {"attempts": (_attempt(1), _attempt(2, adapter_smoke_sha256=None))},
            StabilityStatus.UNRESOLVED,
        ),
    ],
)
def test_reproduction_stability_is_three_state_and_falsifiable(
    overrides: dict[str, object], expected: StabilityStatus
) -> None:
    assert _characterization(**overrides).evaluate() is expected
