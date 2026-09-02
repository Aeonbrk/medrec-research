from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_gate_02_module():
    gate_02_path = (
        Path(__file__).parents[2]
        / "research"
        / "ideas"
        / "001-tension-guided-verification"
        / "experiments"
        / "run_confidence_sufficiency_gate.py"
    )
    spec = importlib.util.spec_from_file_location("run_confidence_sufficiency_gate", gate_02_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_02_synthetic_critical_paths() -> None:
    module = _load_gate_02_module()
    module.self_test_gate_02()


def test_gate_02_full_patient_universe_split() -> None:
    module = _load_gate_02_module()
    val_patient_count = 858
    dev_full, audit_full = module.partition_validation_patients(range(val_patient_count), seed=1203)
    assert len(dev_full) == 429
    assert len(audit_full) == 429
    assert len(dev_full & audit_full) == 0

    # Omitting patients without eligible visits drifts seeded shuffle
    patients_with_visits = [i for i in range(val_patient_count) if i % 100 != 7]
    dev_subset, _ = module.partition_validation_patients(patients_with_visits, seed=1203)
    assert dev_subset != dev_full.intersection(patients_with_visits)


def test_gate_02_missing_traversal_fail_closed() -> None:
    module = _load_gate_02_module()
    pred_data = [
        {
            "patient_id": "p1",
            "visit_id": "v1",
            "predicted_medications": ["MED_A", "MED_B"],
            "vocabulary_scores": {"MED_A": 0.88, "MED_B": 0.52},
        }
    ]
    targets = {"p1:v1": ["MED_A"]}
    ddi_mock = frozenset([("MED_A", "MED_B")])
    with pytest.raises(KeyError, match="Missing traversal metadata"):
        module.compute_gate_02_candidates(
            predictions=pred_data,
            targets=targets,
            ddi_pairs=ddi_mock,
            traversal_by_visit={},  # missing p1:v1
            dev_patients=frozenset([0]),
        )


def test_gate_02_missing_vocabulary_score_fail_closed() -> None:
    module = _load_gate_02_module()
    pred_data = [
        {
            "patient_id": "p1",
            "visit_id": "v1",
            "predicted_medications": ["MED_A", "MED_B"],
            "vocabulary_scores": {"MED_A": 0.88},  # MED_B score missing
        }
    ]
    targets = {"p1:v1": ["MED_A"]}
    ddi_mock = frozenset([("MED_A", "MED_B")])
    traversal = {"p1:v1": (0, 1)}
    with pytest.raises(KeyError, match="Missing frozen vocabulary score"):
        module.compute_gate_02_candidates(
            predictions=pred_data,
            targets=targets,
            ddi_pairs=ddi_mock,
            traversal_by_visit=traversal,
            dev_patients=frozenset([0]),
        )
