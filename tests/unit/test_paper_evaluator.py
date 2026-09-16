from __future__ import annotations

import pytest

from research.prototypes.paper_contract.evaluator import (
    SelectionCandidate,
    VisitPrediction,
    evaluate,
    select_joint,
)

VOCABULARY = ("A", "B", "C")


def _visit(
    patient: str,
    visit: str,
    target: tuple[str, ...],
    predicted: tuple[str, ...],
    scores: tuple[float, ...] = (0.9, 0.5, 0.1),
) -> VisitPrediction:
    return VisitPrediction(patient, visit, target, predicted, scores)


def test_patient_macro_differs_from_visit_macro_and_empty_sets_are_frozen() -> None:
    result = evaluate(
        (
            _visit("p1", "v1", ("A",), ("A",)),
            _visit("p1", "v2", ("A",), ()),
            _visit("p2", "v1", (), ()),
        ),
        vocabulary=VOCABULARY,
    )

    assert result["jaccard"] == pytest.approx((0.5 + 1.0) / 2.0)
    assert result["visit_macro"]["jaccard"] == pytest.approx(2.0 / 3.0)
    assert result["both_empty_visits"] == 1
    assert result["empty_target_visits"] == 1
    assert result["patients_with_no_eligible_visit"] == 0


def test_average_precision_uses_full_coordinate_space_and_tie_order() -> None:
    result = evaluate(
        (_visit("p", "v", ("B",), ("B",), (0.5, 0.5, 0.1)),),
        vocabulary=VOCABULARY,
    )

    # A wins a score tie by canonical order, so B is ranked second.
    assert result["prauc"] == pytest.approx(0.5)
    assert result["zero_support_coordinates"] == ["A", "C"]


def test_ddi_is_pooled_and_duplicate_pairs_are_not_counted_twice() -> None:
    result = evaluate(
        (
            _visit("p1", "v1", ("A",), ("A", "B")),
            _visit("p2", "v1", ("A",), ("A",)),
        ),
        vocabulary=VOCABULARY,
        ddi_pairs=(("B", "A"),),
    )

    assert result["ddi_rate"] == 1.0
    assert result["predicted_pair_count"] == 1
    assert result["ddi_interacting_pair_count"] == 1


def test_evaluator_rejects_oov_and_duplicate_predictions() -> None:
    with pytest.raises(ValueError, match="outside the declared vocabulary"):
        evaluate((_visit("p", "v", ("D",), ()),), vocabulary=VOCABULARY)
    with pytest.raises(ValueError, match="predicted medications must be unique"):
        evaluate((_visit("p", "v", ("A",), ("A", "A")),), vocabulary=VOCABULARY)


def test_joint_selection_applies_all_tie_breaks() -> None:
    selected = select_joint(
        (
            SelectionCandidate(2, 0.35, 0.7, 1),
            SelectionCandidate(1, 0.30, 0.7, 0),
            SelectionCandidate(0, 0.40, 0.7, 2),
        ),
        operating_point_order=(0.30, 0.35, 0.40),
        native_default=0.35,
    )

    assert selected == SelectionCandidate(2, 0.35, 0.7, 1)
