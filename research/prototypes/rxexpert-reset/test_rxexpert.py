"""Focused protocol tests for the Rx-Expert adaptation boundary."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rxexpert import (  # noqa: E402
    CANDIDATE_COUNT,
    assert_temporal_history,
    canonical_index_mapping,
    evaluate_sets,
    mapping_checksum,
    masked_prefix,
    remap_square,
    threshold_set,
    topk_set,
    visit_examples,
)


def _records() -> list[list[list[list[int]]]]:
    return [
        [
            [[1, 2], [3], [4, 5]],
            [[6], [7, 8], [9]],
            [[10], [], [11, 12]],
        ],
        [[[2], [4], [5]], [[3], [6], [7, 8]]],
    ]


def test_masked_prefix_contains_only_prior_medications() -> None:
    records = _records()
    prefix = masked_prefix(records, 0, 2)
    assert prefix[-1][2] == ()
    assert {4, 5, 9} == {code for admission in prefix[:-1] for code in admission[2]}
    assert_temporal_history(records, 0, 2, prefix)
    with pytest.raises(ValueError, match="current target"):
        assert_temporal_history(
            records, 0, 2, (*prefix[:-1], (prefix[-1][0], prefix[-1][1], (11,)))
        )


def test_visit_examples_preserve_order_and_targets() -> None:
    examples = visit_examples(_records(), (0, 1))
    assert len(examples) == 5
    assert examples[0][0:2] == (0, 0)
    assert examples[0][3] == (4, 5)
    assert examples[-1][0:2] == (1, 1)
    assert examples[-1][3] == (7, 8)


def test_medication_mapping_is_code_based_and_reorders_matrices() -> None:
    canonical = tuple(f"m{i}" for i in range(CANDIDATE_COUNT))
    official = tuple(reversed(canonical))
    mapping = canonical_index_mapping(canonical, official)
    assert mapping == tuple(reversed(range(CANDIDATE_COUNT)))
    assert mapping_checksum(canonical, mapping)
    square = np.arange(CANDIDATE_COUNT * CANDIDATE_COUNT).reshape(CANDIDATE_COUNT, CANDIDATE_COUNT)
    remapped = remap_square(square, mapping)
    assert remapped[0, 0] == square[-1, -1]
    with pytest.raises(ValueError, match="ALIGNMENT_UNRESOLVED"):
        canonical_index_mapping(canonical, (*official[:-1], "missing"))


def test_deterministic_decoders() -> None:
    scores = tuple(float(index) for index in range(CANDIDATE_COUNT))
    assert topk_set(scores, 3) == frozenset({128, 129, 130})
    assert threshold_set(tuple([-1.0, 0.0, 1.0] + [0.0] * (CANDIDATE_COUNT - 3))) == frozenset(
        {1, 2, *range(3, CANDIDATE_COUNT)}
    )


def test_metrics_match_expected_set_surface() -> None:
    targets = (frozenset({0, 1}), frozenset({2}))
    predictions = (frozenset({0, 1}), frozenset())
    scores = np.zeros((2, CANDIDATE_COUNT), dtype=np.float32)
    scores[0, 0] = 2.0
    scores[0, 1] = 1.0
    scores[1, 2] = 1.0
    ddi = np.zeros((CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=np.float32)
    metrics = evaluate_sets(targets, predictions, scores, ddi)
    assert metrics["jaccard"] == pytest.approx(0.5)
    assert metrics["f1"] == pytest.approx(0.5)
    assert metrics["mean_medication_count"] == pytest.approx(1.0)
