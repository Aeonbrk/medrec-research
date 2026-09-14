from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (Path(__file__).parents[2] / "research/prototypes/hyperedit/hyperedit.py").resolve()
SPEC = importlib.util.spec_from_file_location("hyperedit_prototype", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_retrieval_excludes_same_patient_future_and_current_visits() -> None:
    selected = MODULE.select_neighbors(
        (0.99, 0.98, 0.97, 0.96),
        ("patient-a", "patient-a", "patient-b", "patient-c"),
        "patient-a",
        top_k=3,
    )
    assert selected == (2, 3)


def test_retrieval_ties_use_original_visit_order() -> None:
    selected = MODULE.select_neighbors(
        (0.5, 0.5, 0.4),
        ("patient-a", "patient-b", "patient-c"),
        "patient-z",
        top_k=2,
    )
    assert selected == (0, 1)


def test_editor_trajectory_removes_false_positives_then_adds_false_negatives() -> None:
    trajectory = MODULE.edit_trajectory({0, 2}, {1, 2, 3})
    assert trajectory == (MODULE.CANDIDATE_COUNT, 1, 3, 2 * MODULE.CANDIDATE_COUNT)
    state = frozenset({0, 2})
    for action in trajectory:
        state = MODULE.apply_edit_action(state, action)
    assert state == frozenset({1, 2, 3})


def test_editor_rejects_invalid_add_and_remove_actions() -> None:
    with pytest.raises(ValueError, match="already in the set"):
        MODULE.apply_edit_action({4}, 4)
    with pytest.raises(ValueError, match="absent from the set"):
        MODULE.apply_edit_action({4}, MODULE.CANDIDATE_COUNT + 5)


def test_stop_action_is_idempotent() -> None:
    state = MODULE.apply_edit_action({1, 2}, 2 * MODULE.CANDIDATE_COUNT)
    assert state == frozenset({1, 2})
