from __future__ import annotations

import pytest

from medrec_research import (
    ComparisonPredictionBatch,
    DatasetManifest,
    MedicationScore,
    PredictionRecord,
    ProtocolValidationError,
    TargetFreePrediction,
    evaluate_comparison_predictions,
    evaluate_predictions,
    join_comparison_targets,
)


def _record(
    visit_id: str,
    targets: tuple[str, ...],
    predictions: tuple[str, ...],
    *,
    split: str = "test",
) -> PredictionRecord:
    return PredictionRecord(
        patient_id=f"patient-{visit_id}",
        visit_id=visit_id,
        split=split,
        target_medications=targets,
        predicted_medications=predictions,
    )


@pytest.mark.parametrize(
    ("targets", "predictions", "expected"),
    [
        ((), (), 1.0),
        (("RX_A",), (), 0.0),
        ((), ("RX_A",), 0.0),
    ],
)
def test_empty_set_metric_behavior_is_explicit(
    targets: tuple[str, ...],
    predictions: tuple[str, ...],
    expected: float,
) -> None:
    result = evaluate_predictions((_record("empty-case", targets, predictions),))

    assert result.jaccard == expected
    assert result.precision == expected
    assert result.recall == expected
    assert result.f1 == expected
    assert result.mean_medication_count == len(predictions)


def test_evaluation_uses_visit_macro_aggregation() -> None:
    result = evaluate_predictions(
        (
            _record("both-empty", (), ()),
            _record("false-negative", ("RX_A",), ()),
            _record("false-positive", (), ("RX_A",)),
            _record("partial", ("RX_A", "RX_B"), ("RX_B", "RX_C")),
        )
    )

    assert result.visit_count == 4
    assert result.jaccard == pytest.approx(1 / 3)
    assert result.precision == pytest.approx(3 / 8)
    assert result.recall == pytest.approx(3 / 8)
    assert result.f1 == pytest.approx(3 / 8)
    assert result.mean_medication_count == pytest.approx(3 / 4)


def test_evaluation_rejects_non_test_predictions() -> None:
    with pytest.raises(ProtocolValidationError, match="test split"):
        evaluate_predictions((_record("validation", ("RX_A",), ("RX_A",), split="validation"),))


def _comparison_fixture() -> tuple[
    DatasetManifest,
    ComparisonPredictionBatch,
    dict[tuple[str, str], tuple[str, ...]],
]:
    vocabulary = ("RX_A", "RX_B", "RX_C")
    manifest = DatasetManifest.from_memberships(
        dataset_id="synthetic-medrec",
        snapshot_id="fixture-1",
        provenance="synthetic unit fixture",
        checksum_sha256="d" * 64,
        medication_vocabulary=vocabulary,
        privacy="synthetic",
        patients_by_split={
            "train": ("patient-train",),
            "validation": ("patient-validation",),
            "test": ("patient-test",),
        },
        visits_by_split={
            "train": (("patient-train", "visit-train"),),
            "validation": (("patient-validation", "visit-validation"),),
            "test": (("patient-test", "visit-1"), ("patient-test", "visit-2")),
        },
    )
    batch = ComparisonPredictionBatch(
        method_id="retain",
        medication_vocabulary=vocabulary,
        predictions=(
            TargetFreePrediction(
                patient_id="patient-test",
                visit_id="visit-1",
                predicted_medications=("RX_A", "RX_B"),
                vocabulary_scores=(
                    MedicationScore("RX_A", 0.9),
                    MedicationScore("RX_B", 0.8),
                    MedicationScore("RX_C", 0.1),
                ),
            ),
            TargetFreePrediction(
                patient_id="patient-test",
                visit_id="visit-2",
                predicted_medications=("RX_B",),
                vocabulary_scores=(
                    MedicationScore("RX_A", 0.1),
                    MedicationScore("RX_B", 0.8),
                    MedicationScore("RX_C", 0.7),
                ),
            ),
        ),
    )
    targets = {
        ("patient-test", "visit-1"): ("RX_A",),
        ("patient-test", "visit-2"): ("RX_B", "RX_C"),
    }
    return manifest, batch, targets


def test_comparison_join_is_core_owned_and_evaluates_all_five_outcomes() -> None:
    manifest, batch, targets = _comparison_fixture()

    joined = join_comparison_targets(batch, targets=targets, dataset_manifest=manifest)
    result = evaluate_comparison_predictions(
        joined,
        ddi_pairs=(("RX_A", "RX_B"),),
        bootstrap_seed=17,
    )

    assert joined.evaluation_input.target_free
    assert result.point.ddi_rate == 1.0
    assert result.point.jaccard == 0.5
    assert result.point.f1 == pytest.approx(2 / 3)
    assert result.point.prauc == 1.0
    assert result.point.average_medication_count == 1.5
    assert len(result.rounds) == 10
    assert result == evaluate_comparison_predictions(
        joined,
        ddi_pairs=(("RX_A", "RX_B"),),
        bootstrap_seed=17,
    )


def test_comparison_join_rejects_changed_test_visit_coverage() -> None:
    manifest, batch, targets = _comparison_fixture()
    targets.pop(("patient-test", "visit-2"))

    with pytest.raises(ProtocolValidationError, match="eligible test-visit membership"):
        join_comparison_targets(batch, targets=targets, dataset_manifest=manifest)
