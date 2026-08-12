from __future__ import annotations

import pytest

from medrec_research import (
    AttemptValidity,
    BootstrapSpec,
    EvidenceConclusion,
    OutcomeObservation,
    RepairEvidence,
    ReproductionMetric,
    SourceAcceptanceProfile,
    average_precision,
    bootstrap_outcomes,
    classify_reproduction,
    compute_outcomes,
)
from medrec_research.errors import ProtocolValidationError


def _metric_values(value: float, *, medication_count: float = 2.0) -> dict[str, float]:
    return {
        "ddi_rate": value,
        "jaccard": value,
        "f1": value,
        "prauc": value,
        "average_medication_count": medication_count,
    }


def _observations() -> tuple[OutcomeObservation, ...]:
    return tuple(
        OutcomeObservation(
            observation_id=f"visit-{index}",
            metric_values=_metric_values(index / 10, medication_count=float(index)),
        )
        for index in range(1, 6)
    )


def _profile(
    *, missing: tuple[str, ...] = (), failed: str | None = None
) -> SourceAcceptanceProfile:
    intervals = {metric: [0.0, 1.0] for metric in ("ddi_rate", "jaccard", "f1", "prauc")}
    intervals["average_medication_count"] = [0.0, 5.0]
    for metric in missing:
        intervals.pop(metric, None)
    if failed is not None:
        intervals[failed] = [0.0, 0.05]
    return SourceAcceptanceProfile(
        model_id="gamenet",
        acceptance_intervals=intervals,
        source_revision="88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a",
        source_reference="source-native-target",
    )


def test_ddi_and_prauc_are_computed_from_explicit_inputs() -> None:
    observation = OutcomeObservation(
        observation_id="visit-1",
        target_medications=("A", "B"),
        predicted_medications=("A", "B", "C"),
        ddi_pairs=(("A", "B"),),
        prauc_labels=(1, 0, 1),
        prauc_scores=(0.9, 0.8, 0.1),
    )

    outcomes = compute_outcomes((observation,))
    assert outcomes["ddi_rate"] == pytest.approx(1 / 3)
    assert outcomes["jaccard"] == pytest.approx(2 / 3)
    assert outcomes["f1"] == pytest.approx(0.8)
    assert outcomes["prauc"] == pytest.approx(5 / 6)
    assert outcomes["average_medication_count"] == 3.0
    assert average_precision((0, 0), (0.5, 0.4)) == 0.0

    with pytest.raises(ProtocolValidationError, match="PRAUC"):
        compute_outcomes(
            (OutcomeObservation(observation_id="missing-prauc", metric_values={"jaccard": 0.5}),)
        )


def test_bootstrap_is_deterministic_and_uses_exact_eighty_percent_samples() -> None:
    spec = BootstrapSpec(seed=17)
    first = bootstrap_outcomes(_observations(), spec=spec)
    second = bootstrap_outcomes(_observations(), spec=spec)

    assert first == second
    assert tuple(item.metric.value for item in first) == (
        "ddi_rate",
        "jaccard",
        "f1",
        "prauc",
        "average_medication_count",
    )
    assert all(len(item.estimates) == 10 for item in first)
    assert all(item.sample_size == 4 for item in first)
    assert all(item.with_replacement for item in first)
    assert all("seed_variance" not in item.to_dict() for item in first)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rounds": 9},
        {"sample_fraction": 0.5},
        {"with_replacement": False},
    ],
)
def test_bootstrap_spec_is_fixed_to_the_source_native_procedure(kwargs: dict[str, object]) -> None:
    with pytest.raises(ProtocolValidationError):
        BootstrapSpec(**kwargs)


def test_classification_requires_every_interval_and_does_not_weight_away_a_miss() -> None:
    accepted = classify_reproduction(_observations(), _profile())
    assert accepted.conclusion is EvidenceConclusion.ACCEPTED
    assert accepted.validity is AttemptValidity.USABLE
    assert accepted.is_current

    missing = classify_reproduction(_observations(), _profile(missing=("prauc",)))
    assert missing.conclusion is EvidenceConclusion.INCONCLUSIVE
    assert missing.missing_intervals == ("prauc",)

    rejected = classify_reproduction(_observations(), _profile(failed="prauc"))
    assert rejected.conclusion is EvidenceConclusion.REJECTED
    assert rejected.failed_outcomes == ("prauc",)


def test_artifact_changing_repair_downgrades_validity_without_changing_outcome() -> None:
    repair = RepairEvidence(
        repair_id="dependency-repair",
        kind="dependency",
        description="bounded compatibility repair",
        artifact_changed=True,
        before_sha256="a" * 64,
        after_sha256="b" * 64,
    )
    result = classify_reproduction(_observations(), _profile(), repair_evidence=(repair,))
    assert result.conclusion is EvidenceConclusion.ACCEPTED
    assert result.validity is AttemptValidity.USABLE_WITH_LIMITS
    assert "equivalence" in result.limitations[0] or "equivalence" in result.limitations[-1]


def test_evaluation_round_trip_is_public_safe() -> None:
    result = classify_reproduction(_observations(), _profile())
    restored = type(result).from_json(result.to_json())
    assert restored == result
    assert "patient_id" not in result.to_json()
    assert "seed_variance" not in result.to_json()


def test_evaluation_deserialization_rejects_missing_outcomes_and_tampered_uncertainty() -> None:
    result = classify_reproduction(_observations(), _profile())
    missing = result.to_dict()
    missing["outcomes"] = {}
    with pytest.raises(ProtocolValidationError, match="outcomes"):
        type(result).from_dict(missing)

    tampered = result.to_dict()
    tampered["uncertainty"]["jaccard"] = [0.0, 1.0]
    with pytest.raises(ProtocolValidationError, match="uncertainty"):
        type(result).from_dict(tampered)


def test_reproduction_metric_enum_is_complete() -> None:
    assert tuple(item.value for item in ReproductionMetric) == (
        "ddi_rate",
        "jaccard",
        "f1",
        "prauc",
        "average_medication_count",
    )
