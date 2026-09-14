from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1] / ".." / "research/prototypes/theracompose/theracompose.py"
).resolve()
SPEC = importlib.util.spec_from_file_location("theracompose_prototype", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_intent_slot_aggregation_is_four_slot_and_permutation_invariant() -> None:
    slots = (
        (1.0, 0.0, -1.0),
        (0.0, 1.0, -1.0),
        (-1.0, 0.0, 1.0),
        (0.5, 0.5, 0.5),
    )
    activity = (0.8, 0.6, 0.4, 0.2)
    original = MODULE.aggregate_slot_utilities(slots, activity)
    permutation = (2, 0, 3, 1)
    permuted = MODULE.aggregate_slot_utilities(
        tuple(slots[index] for index in permutation),
        tuple(activity[index] for index in permutation),
    )
    assert len(slots) == MODULE.INTENT_SLOTS == 4
    assert permuted == pytest.approx(original)


def test_hard_negative_construction_covers_four_corruption_types() -> None:
    target = frozenset({0, 1, 2})
    scores = tuple(float(index) for index in range(MODULE.CANDIDATE_COUNT))
    ddi = [[0.0] * MODULE.CANDIDATE_COUNT for _ in range(MODULE.CANDIDATE_COUNT)]
    ddi[3][0] = ddi[0][3] = 1.0
    negatives = MODULE.construct_hard_negative_sets((target,), (scores,), ddi)[0]
    assert len(negatives) == 4
    assert tuple(MODULE.HARD_NEGATIVE_TYPES) == (
        "high_score_swap",
        "ddi_inducing_swap",
        "intent_coverage_deletion",
        "redundant_addition",
    )
    assert len(negatives[0]) == len(target)
    assert len(negatives[1]) == len(target)
    assert len(negatives[2]) == len(target) - 1
    assert len(negatives[3]) == len(target) + 1
    assert negatives[0] != target


def test_energy_and_swap_direction_are_consistent() -> None:
    unary = [0.0] * MODULE.CANDIDATE_COUNT
    unary[2] = unary[3] = 1.0
    compatibility = [[0.0] * MODULE.CANDIDATE_COUNT for _ in range(MODULE.CANDIDATE_COUNT)]
    compatibility[2][3] = compatibility[3][2] = 8.0
    risk = [[0.0] * MODULE.CANDIDATE_COUNT for _ in range(MODULE.CANDIDATE_COUNT)]
    support = [[0.5] * MODULE.CANDIDATE_COUNT for _ in range(MODULE.INTENT_SLOTS)]
    activity = [0.5] * MODULE.INTENT_SLOTS
    current = MODULE.set_energy(
        {0, 1}, unary, compatibility, risk, support, activity, expected_cardinality=2
    )
    swapped = MODULE.set_energy(
        {2, 3}, unary, compatibility, risk, support, activity, expected_cardinality=2
    )
    assert swapped < current
