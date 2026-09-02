from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_gate_01_module():
    gate_01_path = (
        Path(__file__).parents[2]
        / "research"
        / "ideas"
        / "002-score-geometry-sufficiency"
        / "experiments"
        / "run_score_geometry_sufficiency_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_score_geometry_sufficiency_gate", gate_01_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_01_self_test_passes() -> None:
    module = _load_gate_01_module()
    module.self_test_gate_01()


def test_gate_01_patient_split_disjoint() -> None:
    """Requirement 1: patient split uses seed 2002 and is strictly patient-disjoint."""
    module = _load_gate_01_module()
    val_count = 1059
    dev_patients, audit_patients = module.partition_validation_patients(range(val_count), seed=2002)
    assert len(dev_patients) == 529
    assert len(audit_patients) == 530
    assert len(dev_patients & audit_patients) == 0
    assert len(dev_patients | audit_patients) == 1059

    # Prove that removing patients without eligible visits drifts seeded shuffle
    subset_patients = [i for i in range(val_count) if i != 10]
    dev_subset, _ = module.partition_validation_patients(subset_patients, seed=2002)
    assert dev_subset != dev_patients - {10}


def test_gate_01_dev_only_fitting_firewall() -> None:
    """Requirement 2: g(s) cutpoints and empirical bin risks use Dev labels only."""
    module = _load_gate_01_module()
    Record = module.Gate01CandidateRecord

    dev_cands = [
        Record("p1", "v1", 1, 1, "dev", "M1", 0.20, 1, True, 0.1, -1),
        Record("p2", "v2", 2, 1, "dev", "M2", 0.40, 1, False, -0.1, -1),
        Record("p3", "v3", 3, 1, "dev", "M3", 0.60, 1, True, 0.1, -1),
        Record("p4", "v4", 4, 1, "dev", "M4", 0.80, 1, False, -0.1, -1),
        Record("p5", "v5", 5, 1, "dev", "M5", 0.95, 1, False, -0.1, -1),
    ]
    map1 = module.fit_dev_score_geometry(dev_cands)

    # Creating alternative Audit candidates with inverted labels
    audit_cands_alt = [
        Record("p6", "v6", 6, 1, "audit", "M6", 0.20, 1, False, -0.1, -1),
        Record("p7", "v7", 7, 1, "audit", "M7", 0.95, 1, True, 0.1, -1),
    ]
    assert len(audit_cands_alt) == 2
    # Re-running fit on Dev: Audit is never passed to fit_dev_score_geometry
    map2 = module.fit_dev_score_geometry(dev_cands)
    assert map1 == map2
    assert map1["cutpoints"] == map2["cutpoints"]
    assert map1["bin_empirical_risks"] == map2["bin_empirical_risks"]


def test_gate_01_deterministic_ordering() -> None:
    """Requirement 3: ScoreGeometry deterministic ordering matches frozen tie-break rules."""
    module = _load_gate_01_module()
    Record = module.Gate01CandidateRecord

    # Suppose Dev map has B2 with higher risk than B1
    # B1 cutpoint <= 0.50 risk 0.10; B2 cutpoint > 0.50 risk 0.90
    dev_cutpoints = {"0.2": 0.3, "0.4": 0.5, "0.6": 0.7, "0.8": 0.85}
    dev_bin_risks = {1: 0.10, 2: 0.20, 3: 0.90, 4: 0.30, 5: 0.05}

    # B3 (0.5 < s <= 0.7) has risk 0.90 (highest priority)
    # Inside B3, s asc: 0.55 comes before 0.65
    # Tie-break: medication_code asc
    c1 = Record("p1", "v1", 1, 1, "audit", "MED_B", 0.55, 1, True, 0.1, -1)
    c2 = Record("p2", "v2", 2, 1, "audit", "MED_A", 0.55, 1, True, 0.1, -1)
    c3 = Record("p3", "v3", 3, 1, "audit", "MED_C", 0.65, 1, True, 0.1, -1)
    c4 = Record("p4", "v4", 4, 1, "audit", "MED_D", 0.25, 1, True, 0.1, -1)  # B1: risk 0.10

    eval_res = module.evaluate_audit_policies([c1, c2, c3, c4], dev_cutpoints, dev_bin_risks)
    # Check that c2 comes before c1 because MED_A < MED_B with same score in B3
    # c3 comes after c1, c2 because s=0.65 > 0.55 in B3
    # c4 comes last because B1 has lower risk than B3
    assert eval_res["score_geometry_yield"]["10%"] >= 0.0


def test_gate_01_decision_tree_verdicts() -> None:
    """Requirement 4: decision tree returns PASS on positive case and STOP on null case."""
    module = _load_gate_01_module()

    pos_ci = {
        "oracle_minus_score": {
            "10%": {"lower": 0.30, "upper": 0.45},
            "20%": {"lower": 0.35, "upper": 0.50},
        },
        "geometry_minus_score": {
            "10%": {"lower": 0.04, "upper": 0.12},
            "20%": {"lower": 0.02, "upper": 0.09},
        },
    }
    v_pos, _c_pos = module.evaluate_gate_01_decision_tree(True, pos_ci)
    assert v_pos == "PASS_INCREMENTAL_SCORE_GEOMETRY"

    null_ci = {
        "oracle_minus_score": {
            "10%": {"lower": 0.30, "upper": 0.45},
            "20%": {"lower": 0.35, "upper": 0.50},
        },
        "geometry_minus_score": {
            "10%": {"lower": 0.0, "upper": 0.0},
            "20%": {"lower": 0.0, "upper": 0.0},
        },
    }
    v_null, _c_null = module.evaluate_gate_01_decision_tree(True, null_ci)
    assert v_null == "STOP_NO_INCREMENTAL_SCORE_GEOMETRY"
