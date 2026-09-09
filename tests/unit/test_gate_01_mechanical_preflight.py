from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[2]
    / "research/ideas/007-privileged-physiological-response-supervision/experiments/gate01_mechanical_preflight.py"
)
SPEC = importlib.util.spec_from_file_location("gate01_mechanical_preflight", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_gate01_split_is_deterministic_and_uses_frozen_intervals() -> None:
    subject_ids = [1001, 1002, 1003, 1004]
    first = [MODULE.classify_gate01(subject_id) for subject_id in subject_ids]
    second = [MODULE.classify_gate01(subject_id) for subject_id in subject_ids]

    assert first == second
    assert set(first) <= {"Gate01-Train", "Gate01-Dev", "Gate01-Audit"}


def test_right_closed_bin_boundaries() -> None:
    assert MODULE.right_closed_bin(0) is None
    assert MODULE.right_closed_bin(1) == 0
    assert MODULE.right_closed_bin(3600) == 0
    assert MODULE.right_closed_bin(3601) == 1
    assert MODULE.right_closed_bin(24 * 3600) == 23
    assert MODULE.right_closed_bin(24 * 3600 + 1) is None


def test_source_units_temperature_conversion_and_rejection() -> None:
    assert MODULE.convert_value(223761, 98.6, " F") == pytest.approx(37.0, abs=1e-12)
    assert MODULE.convert_value(223762, 37.0, "DEGC") == pytest.approx(37.0)
    assert MODULE.convert_value(220045, 70.0, " BPM ") == pytest.approx(70.0)
    assert MODULE.convert_value(220045, 70.0, "beats/min") is None
    assert MODULE.convert_value(223761, 98.6, "degC") is None


def test_median_mask_and_a_zero_retains_example() -> None:
    supported, occupied, valid_values = MODULE.support_from_tensor(
        observed_timestamps={10, 20},
        cell_values={(0, 0): [1.0, 3.0], (2, 5): [7.0]},
    )
    assert supported is True
    assert occupied == 2
    assert valid_values == 3
    assert MODULE.median_cells({(0, 0): [1.0, 3.0]})[(0, 0)] == 2.0

    unsupported, _, _ = MODULE.support_from_tensor(
        observed_timestamps={10}, cell_values={(0, 0): [1.0]}
    )
    assert unsupported is False

    examples = [
        MODULE.FocalExample(
            subject_id=1,
            hadm_id=1,
            decision_time=1,
            focal_medication="A",
            order_poe_id="p1",
            order_pharmacy_ids=frozenset(),
            partition="Gate01-Train",
            supported=False,
        ),
        MODULE.FocalExample(
            subject_id=2,
            hadm_id=2,
            decision_time=1,
            focal_medication="B",
            order_poe_id="p2",
            order_pharmacy_ids=frozenset(),
            partition="Gate01-Train",
            supported=True,
        ),
    ]
    aggregate = MODULE.aggregate_partition(examples, "partition")
    assert aggregate["E_rec"] == 2
    assert aggregate["N_A"] == 1
