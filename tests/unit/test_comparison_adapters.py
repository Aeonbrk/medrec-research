from __future__ import annotations

from baselines.comparison_data import _eligible_memberships
from baselines.molerec_comparison import _threshold_indices as molerec_threshold_indices
from baselines.safedrug_comparison import THRESHOLDS, _wire_scores
from baselines.safedrug_comparison import _threshold_indices as safedrug_threshold_indices


def _records() -> list[list[list[list[int]]]]:
    return [
        [
            [[patient], [patient + 10], [patient + 20]],
            [[patient + 1], [patient + 11], [patient + 21]],
        ]
        for patient in range(6)
    ]


def test_staging_separates_current_targets_from_adapter_contexts() -> None:
    _, visits, contexts, targets = _eligible_memberships(_records(), b"k" * 32)

    assert len(visits["test"]) == 1
    assert len(contexts) == 1
    context = contexts[0]
    visit_key = (context["patient_id"], context["visit_id"])
    assert targets[visit_key] == (25,)
    assert context["current_diagnoses"] == (5,)
    assert context["current_procedures"] == (15,)
    assert "current_medications" not in context
    assert context["history"][0][2] == (24,)


def test_static_adapters_preserve_frozen_threshold_boundaries() -> None:
    scores = (0.39, 0.4, 0.49, 0.5)

    assert THRESHOLDS == {"gamenet": 0.5, "retain": 0.4, "safedrug": 0.5}
    assert safedrug_threshold_indices(scores, THRESHOLDS["retain"]) == [1, 2, 3]
    assert safedrug_threshold_indices(scores, THRESHOLDS["gamenet"]) == [3]
    assert molerec_threshold_indices(scores) == [3]


def test_score_translation_preserves_declared_vocabulary_order() -> None:
    assert _wire_scores(("RX_B", "RX_A"), (0.2, 0.8)) == [
        {"medication_code": "RX_B", "score": 0.2},
        {"medication_code": "RX_A", "score": 0.8},
    ]
