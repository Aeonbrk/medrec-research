from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from medrec_research.baseline_audit import AuditReviewSet, BaselineAudit, BaselineProgram
from medrec_research.benchmark_program import (
    Diagnostic,
    ReproductionAttempt,
    ReproductionCharacterization,
    ReproductionStabilityPolicy,
    SelectionDiagnostic,
    SelectionResult,
    SelectionSpecification,
    StabilityStatus,
    VarianceCheck,
)
from medrec_research.errors import ProtocolValidationError

ROOT = Path(__file__).parents[2]
AUDIT_DIR = ROOT / "baselines" / "audits"
PROGRAM_PATH = ROOT / "baselines" / "programs" / "classic-six.toml"
REVIEWS_PATH = ROOT / "fixtures" / "benchmark" / "audit-reviews.json"
SELECTION_FIXTURE = ROOT / "fixtures" / "benchmark" / "selection-result.json"
CHARACTERIZATION_FIXTURE = ROOT / "fixtures" / "benchmark" / "reproduction-characterization.json"
PRIORITY = (
    "gamenet",
    "safedrug",
    "micron",
    "molerec",
    "retain",
    "leap-safedrug",
)


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


def test_selection_uses_accepted_hard_gates_before_fixed_priority() -> None:
    program, audits, reviews = _authorities()
    diagnostics = _diagnostics(audits)

    result = SelectionSpecification().select(program, audits, reviews, diagnostics)

    assert result.status == "proposed"
    assert result.selected_candidate_id == "gamenet"
    assert tuple(candidate.baseline_id for candidate in result.candidates) == PRIORITY
    assert result.candidates[0].diagnostics.reproduction_risk.value == "high"
    assert result == SelectionResult.from_json(result.to_json())
    assert result == SelectionResult.load(SELECTION_FIXTURE)


def test_selection_skips_blocked_earlier_candidates_without_hiding_blockers() -> None:
    program, audits, reviews = _authorities()
    gamenet_license = reviews.matching_review(audits[0], "license")
    assert gamenet_license is not None
    without_gamenet_license = AuditReviewSet(
        tuple(review for review in reviews.reviews if review != gamenet_license)
    )

    result = SelectionSpecification().select(
        program, audits, without_gamenet_license, _diagnostics(audits)
    )

    assert result.selected_candidate_id == "molerec"
    assert result.candidates[0].blockers == (
        "source_review_missing",
        "license_review_missing",
    )
    assert tuple(candidate.baseline_id for candidate in result.candidates[1:4]) == (
        "safedrug",
        "micron",
        "molerec",
    )


def test_selection_returns_deterministic_blocked_result_when_none_are_eligible() -> None:
    program, audits, _ = _authorities()
    specification = SelectionSpecification()

    first = specification.select(program, audits, AuditReviewSet(()), _diagnostics(audits))
    second = specification.select(program, audits, AuditReviewSet(()), _diagnostics(audits))

    assert first == second
    assert first.status == "blocked"
    assert first.selected_candidate_id is None
    assert all(candidate.blockers for candidate in first.candidates)


def test_selection_rejects_incomplete_or_non_predeclared_inputs() -> None:
    program, audits, reviews = _authorities()
    diagnostics = _diagnostics(audits)

    with pytest.raises(ProtocolValidationError, match=r"selection blocked.*six audits"):
        SelectionSpecification().select(program, audits[:-1], reviews, diagnostics[:-1])

    unknown = list(diagnostics)
    unknown[-1] = SelectionDiagnostic(
        baseline_id="other",
        priority_ordinal=5,
        comparison_representativeness=unknown[-1].comparison_representativeness,
        reproduction_risk=unknown[-1].reproduction_risk,
        integration_cost=unknown[-1].integration_cost,
    )
    with pytest.raises(ProtocolValidationError, match="fixed priority order"):
        SelectionSpecification().select(program, audits, reviews, tuple(unknown))

    duplicate_ordinal = list(diagnostics)
    duplicate_ordinal[1] = SelectionDiagnostic(
        baseline_id="safedrug",
        priority_ordinal=0,
        comparison_representativeness=duplicate_ordinal[1].comparison_representativeness,
        reproduction_risk=duplicate_ordinal[1].reproduction_risk,
        integration_cost=duplicate_ordinal[1].integration_cost,
    )
    with pytest.raises(ProtocolValidationError, match="fixed priority order"):
        SelectionSpecification().select(program, audits, reviews, tuple(duplicate_ordinal))

    payload = diagnostics[-1].to_dict()
    payload["comparison_representativeness"]["value"] = "favorable"
    with pytest.raises(ProtocolValidationError, match="diagnostic value"):
        SelectionDiagnostic.from_dict(payload)


def test_selection_receipt_rejects_authority_or_candidate_drift() -> None:
    program, audits, reviews = _authorities()
    result = SelectionSpecification().select(program, audits, reviews, _diagnostics(audits))

    for field, value in (
        ("specification_sha256", "0" * 64),
        ("program_sha256", "1" * 64),
        ("review_set_sha256", "2" * 64),
        ("selected_candidate_id", "retain"),
    ):
        payload = deepcopy(result.to_dict())
        payload[field] = value
        with pytest.raises(ProtocolValidationError):
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
    return ReproductionCharacterization.create(ReproductionStabilityPolicy(), **payload)


def test_reproduction_characterization_is_stable_only_with_complete_repeat_evidence() -> None:
    characterization = _characterization()

    assert characterization.evaluate() is StabilityStatus.STABLE
    assert characterization == ReproductionCharacterization.from_json(characterization.to_json())
    assert characterization == ReproductionCharacterization.load(CHARACTERIZATION_FIXTURE)


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
