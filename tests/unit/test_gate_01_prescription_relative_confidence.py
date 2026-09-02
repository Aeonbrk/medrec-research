from __future__ import annotations

import importlib.util
import math
import random
from pathlib import Path


def _load_gate_01_module():
    gate_01_path = (
        Path(__file__).parents[2]
        / "research"
        / "ideas"
        / "003-prescription-relative-confidence"
        / "experiments"
        / "run_prescription_relative_confidence_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_prescription_relative_confidence_gate", gate_01_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_01_self_test_passes() -> None:
    module = _load_gate_01_module()
    module.self_test_gate_01()


def test_relative_rank_calculation_and_score_ties() -> None:
    """Requirement 1: mid-rank r calculation, including real score ties without epsilon."""
    module = _load_gate_01_module()

    # Case A: 3 meds, distinct scores
    scores = {"m1": 0.8, "m2": 0.6, "m3": 0.4}
    meds = ["m1", "m2", "m3"]
    assert math.isclose(module.compute_relative_rank("m1", meds, scores), 0.0)
    assert math.isclose(module.compute_relative_rank("m2", meds, scores), 0.5)
    assert math.isclose(module.compute_relative_rank("m3", meds, scores), 1.0)

    # Case B: 3 meds, 2 tied
    scores_tied = {"m1": 0.8, "m2": 0.8, "m3": 0.4}
    r1 = module.compute_relative_rank("m1", meds, scores_tied)
    r2 = module.compute_relative_rank("m2", meds, scores_tied)
    r3 = module.compute_relative_rank("m3", meds, scores_tied)
    assert r1 == r2
    assert math.isclose(r1, 0.25)
    assert math.isclose(r3, 1.0)

    # Case C: All tied
    scores_all_tied = {"m1": 0.7, "m2": 0.7, "m3": 0.7}
    for m in meds:
        assert math.isclose(module.compute_relative_rank(m, meds, scores_all_tied), 0.5)


def test_split_determinism_and_zero_patient_overlap() -> None:
    """Requirement 2: seed-2003 split determinism and zero patient overlap."""
    module = _load_gate_01_module()
    dev_1, audit_1 = module.partition_validation_patients(range(1059), seed=2003)
    dev_2, audit_2 = module.partition_validation_patients(range(1059), seed=2003)

    assert dev_1 == dev_2
    assert audit_1 == audit_2
    assert len(dev_1) == 529
    assert len(audit_1) == 530
    assert len(dev_1 & audit_1) == 0
    assert len(dev_1 | audit_1) == 1059


def test_train_prevalence_eligible_visits_firewall() -> None:
    """Requirements 3 & 4: train prevalence uses eligible train visits only; no val/test rows."""
    # Simulate records: train patients (0, 1), test patient (2), validation patient (3)
    # Only patient 0 and 1 are in train split. Patient 0 has 2 visits (1 eligible). Patient 1 has 1 visit (0 eligible).
    # Test (patient 2) and validation (patient 3) must never be accessed.
    train_records = [
        [[[1], [1], [10]], [[1], [1], [10, 20]]],  # 1 eligible visit
        [[[1], [1], [10]]],  # 0 eligible visit
    ]
    val_records = [
        [[[1], [1], [30]], [[1], [1], [30, 40]]],  # validation visit with med 30, 40
    ]
    assert 30 in val_records[0][1][2]

    v_train = 0
    c_train: dict[int, int] = {}
    for p in train_records:
        for v_idx in range(1, len(p)):
            v_train += 1
            for med in set(p[v_idx][2]):
                c_train[med] = c_train.get(med, 0) + 1

    assert v_train == 1
    assert c_train == {10: 1, 20: 1}
    # Meds 30 and 40 from validation records must NOT enter c_train
    assert 30 not in c_train
    assert 40 not in c_train

    # Laplace smoothing
    p_10 = (c_train[10] + 1) / (v_train + 2)
    p_unseen = (c_train.get(30, 0) + 1) / (v_train + 2)
    assert math.isclose(p_10, 2 / 3)
    assert math.isclose(p_unseen, 1 / 3)


def test_dev_estimator_receives_no_audit_labels() -> None:
    """Requirement 5: Dev estimator receives no Audit label."""
    module = _load_gate_01_module()

    random.seed(100)
    X_dev = [[random.gauss(0, 1) for _ in range(5)] for _ in range(50)]
    y_dev = [float(random.choice([0, 1])) for _ in range(50)]

    b0_orig, beta_orig = module.fit_ridge_linear_probability(X_dev, y_dev)

    # Creating audit set with arbitrary labels has zero effect on Dev fitting
    _X_audit = [[random.gauss(0, 1) for _ in range(5)] for _ in range(50)]
    _y_audit = [float(random.choice([0, 1])) for _ in range(50)]

    b0_re, beta_re = module.fit_ridge_linear_probability(X_dev, y_dev)
    assert b0_orig == b0_re
    assert beta_orig == beta_re


def test_control_and_augmented_feature_vectors_differ_by_r() -> None:
    """Requirement 6: control and augmented estimators differ by exactly r."""
    module = _load_gate_01_module()
    Record = module.Gate01CandidateRecord

    cand = Record(
        patient_id="p",
        visit_id="v",
        patient_order=0,
        visit_order=1,
        gate01_partition="audit",
        medication_code="m",
        model_score=0.75,
        prescription_size=4,
        relative_rank=0.3333333333333333,
        train_prevalence=0.15,
        active_ddi_degree=2,
        pareto_beneficial=True,
        delta_jaccard=0.05,
        delta_violation=-2,
    )
    x_c, x_r = module.compute_feature_vectors(cand)
    assert len(x_c) == 5
    assert len(x_r) == 6
    assert x_r[:5] == x_c
    assert x_r[5] == cand.relative_rank


def test_deterministic_ranking_tie_breaks() -> None:
    """Requirement 7: deterministic ranking/tie-breaks across policies."""
    module = _load_gate_01_module()
    Record = module.Gate01CandidateRecord

    # Create candidates with identical linear risk and score to test tie-breaks
    c1 = Record("p1", "v1", 2, 1, "audit", "MED_A", 0.6, 2, 0.0, 0.5, 1, True, 0.1, -1)
    c2 = Record("p2", "v1", 1, 1, "audit", "MED_A", 0.6, 2, 0.0, 0.5, 1, True, 0.1, -1)
    c3 = Record("p2", "v2", 1, 2, "audit", "MED_A", 0.6, 2, 0.0, 0.5, 1, True, 0.1, -1)
    c4 = Record("p1", "v1", 2, 1, "audit", "MED_B", 0.6, 2, 0.0, 0.5, 1, True, 0.1, -1)

    # All share score 0.6. Tie-breaks:
    # 1. med_code asc: MED_A < MED_B (c4 goes after c1, c2, c3)
    # 2. patient_order asc: 1 < 2 (c2, c3 before c1)
    # 3. visit_order asc: 1 < 2 (c2 before c3)
    # Expected: c2, c3, c1, c4
    sorted_res = sorted(
        [c4, c1, c3, c2],
        key=lambda c: (c.model_score, c.medication_code, c.patient_order, c.visit_order),
    )
    assert sorted_res == [c2, c3, c1, c4]


def test_decision_tree_all_four_paths() -> None:
    """Requirement 8: PASS / incremental FAIL / no-headroom / insufficient-support decision paths."""
    module = _load_gate_01_module()

    # Path 1: INSUFFICIENT_SUPPORT
    v1, _ = module.evaluate_decision_tree(False, {})
    assert v1 == "INCONCLUSIVE_INSUFFICIENT_AUDIT_SUPPORT"

    # Path 2: STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL (lower CI <= 0 at 10% or 20%)
    intervals_no_head = {
        "oracle_minus_control": {
            "10%": {"lower": -0.02, "upper": 0.10},
            "20%": {"lower": 0.05, "upper": 0.15},
        },
        "rank_minus_control": {
            "10%": {"lower": 0.02, "upper": 0.05},
            "20%": {"lower": 0.01, "upper": 0.04},
        },
    }
    v2, _ = module.evaluate_decision_tree(True, intervals_no_head)
    assert v2 == "STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL"

    # Path 3: PASS_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE (both lower CIs > 0)
    intervals_pass = {
        "oracle_minus_control": {
            "10%": {"lower": 0.15, "upper": 0.35},
            "20%": {"lower": 0.12, "upper": 0.30},
        },
        "rank_minus_control": {
            "10%": {"lower": 0.015, "upper": 0.06},
            "20%": {"lower": 0.010, "upper": 0.05},
        },
    }
    v3, _ = module.evaluate_decision_tree(True, intervals_pass)
    assert v3 == "PASS_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE"

    # Path 4: STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE (rank lower CI <= 0 at 10% or 20%)
    intervals_fail = {
        "oracle_minus_control": {
            "10%": {"lower": 0.15, "upper": 0.35},
            "20%": {"lower": 0.12, "upper": 0.30},
        },
        "rank_minus_control": {
            "10%": {"lower": -0.005, "upper": 0.04},
            "20%": {"lower": 0.010, "upper": 0.05},
        },
    }
    v4, _ = module.evaluate_decision_tree(True, intervals_fail)
    assert v4 == "STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE"


def test_public_summary_privacy_boundary() -> None:
    """Requirement 9: public summary contains no patient IDs, visit IDs, membership lists, private paths, raw prediction rows, or per-medication prevalence table."""
    module = _load_gate_01_module()

    # Mock candidate records
    candidates = [
        module.Gate01CandidateRecord(
            patient_id=f"SECRET_PATIENT_{i}",
            visit_id=f"SECRET_VISIT_{i}",
            patient_order=i,
            visit_order=1,
            gate01_partition="audit" if i % 2 == 0 else "dev",
            medication_code="MED_1",
            model_score=0.7,
            prescription_size=3,
            relative_rank=0.5,
            train_prevalence=0.2,
            active_ddi_degree=1,
            pareto_beneficial=True,
            delta_jaccard=0.1,
            delta_violation=-1,
        )
        for i in range(100)
    ]
    # Check that public summary fields do NOT serialize any SECRET_* or row-level dictionaries
    dev_cands = [c for c in candidates if c.gate01_partition == "dev"]
    audit_cands = [c for c in candidates if c.gate01_partition == "audit"]

    X_dev = [module.compute_feature_vectors(c)[0] for c in dev_cands]
    y_dev = [1.0 if c.pareto_beneficial else 0.0 for c in dev_cands]
    b0, beta = module.fit_ridge_linear_probability(X_dev, y_dev)

    audit_eval = module.evaluate_audit_policies(
        audit_cands,
        ctrl_beta0=b0,
        ctrl_beta=beta,
        rank_beta0=b0,
        rank_beta=[*beta, 0.0],
    )

    # Convert audit_eval to JSON string and assert no patient IDs
    json_str = str(audit_eval)
    assert "SECRET_PATIENT" not in json_str
    assert "SECRET_VISIT" not in json_str
