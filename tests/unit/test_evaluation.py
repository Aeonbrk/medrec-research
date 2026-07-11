from __future__ import annotations

import pytest

from medrec_research import PredictionRecord, ProtocolValidationError, evaluate_predictions


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
