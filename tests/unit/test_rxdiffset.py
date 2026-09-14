from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1] / ".." / "research/prototypes/rxdiffset/rxdiffset.py"
).resolve()
SPEC = importlib.util.spec_from_file_location("rxdiffset_prototype", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_prevalence_corruption_preserves_replacement_rate_and_not_targets() -> None:
    prevalence = (0.25, 0.50, 0.75, 1.0)
    clean_a = tuple((float(index % 2),) * 4 for index in range(100))
    clean_b = tuple((float((index + 1) % 2),) * 4 for index in range(100))
    preserve = tuple((0.0,) * 4 for _ in range(100))
    replacement = tuple(((index % 4) / 4.0,) * 4 for index in range(100))
    corrupted_a = MODULE.corrupt_membership_with_uniforms(
        clean_a, prevalence, 0.0, preserve, replacement
    )
    corrupted_b = MODULE.corrupt_membership_with_uniforms(
        clean_b, prevalence, 0.0, preserve, replacement
    )
    assert corrupted_a == corrupted_b
    rates = tuple(sum(row[index] for row in corrupted_a) / len(corrupted_a) for index in range(4))
    assert rates == pytest.approx(prevalence, abs=0.01)


def test_reverse_trace_is_seeded_and_has_one_state_per_reverse_transition() -> None:
    schedule = (1.0, 0.8, 0.5, 0.1)
    probabilities = (
        ((0.1, 0.9, 0.2), (0.8, 0.3, 0.7)),
        ((0.2, 0.8, 0.3), (0.7, 0.4, 0.6)),
        ((0.3, 0.7, 0.4), (0.6, 0.5, 0.5)),
    )
    first = MODULE.reverse_trace_from_probabilities(
        probabilities, (0.25, 0.5, 0.75), schedule, seed=17
    )
    second = MODULE.reverse_trace_from_probabilities(
        probabilities, (0.25, 0.5, 0.75), schedule, seed=17
    )
    assert first == second
    assert len(first) == len(schedule)
    assert all(len(state) == 2 and all(len(row) == 3 for row in state) for state in first)
    summary = MODULE.trace_change_summary(first)
    assert 0.0 <= summary["changed_fraction_initial_to_final"] <= 1.0
    assert len(summary["flips_per_reverse_step"]) == len(schedule) - 1


def test_topk_inference_preserves_requested_shape_and_tie_order() -> None:
    logits = (1.0, 1.0, 1.0) + (0.0,) * (MODULE.CANDIDATE_COUNT - 3)
    selected = MODULE.topk_set(logits, 2)
    assert selected == frozenset({0, 1})
    assert len(selected) == 2
    with pytest.raises(ValueError, match="131-candidate"):
        MODULE.topk_set((0.0, 1.0), 1)
