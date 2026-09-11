"""Targeted synthetic integrity tests for the frozen Pair/Context runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

RUNNER_PATH = (
    Path(__file__).parents[2]
    / "research/memory/model-reset-20260910-strict-drug-changing-order-revision"
    / "run_pair_context_incremental_value.py"
)
SPEC = importlib.util.spec_from_file_location("pair_context_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_frozen_r0_subject_partition_is_deterministic() -> None:
    subject_id = 10000032
    assert runner.subject_unit_interval(subject_id) == runner.subject_unit_interval(subject_id)
    assert runner.classify_outer(subject_id) in {"Discovery", "Dev", "Holdout"}


def test_strict_pre_order_boundary_excludes_focal_time() -> None:
    records = [
        {"poe_id": "before", "ordertime": 99},
        {"poe_id": "at", "ordertime": 100},
        {"poe_id": "after", "ordertime": 101},
    ]
    selected = runner.history_before(records, 100)
    assert [record["poe_id"] for record in selected] == ["before"]


def test_candidate_control_sample_identity_rejects_mismatch() -> None:
    runner.assert_sample_identity(["event-a", "event-b"], ["event-a", "event-b"])
    with pytest.raises(ValueError, match="sample identity"):
        runner.assert_sample_identity(["event-a"], ["event-b"])


def test_permutation_preserves_labels_and_changes_patient_context() -> None:
    subjects = [1, 1, 2, 2, 3, 3]
    sources = [0, 1, 0, 1, 2, 3]
    destinations = [1, 2, 1, 2, 3, 4]
    permutation = runner.make_context_permutation_for_test(subjects)
    runner.validate_context_permutation(subjects, sources, destinations, permutation)
    assert sorted(permutation) == list(range(len(subjects)))
    assert all(subjects[i] != subjects[permutation[i]] for i in range(len(subjects)))


def test_verdict_is_all_controls_binary() -> None:
    assert runner.compute_verdict({"a": True, "b": True}) == runner.PASS_VERDICT
    assert runner.compute_verdict({"a": True, "b": False}) == runner.ABANDON_VERDICT
