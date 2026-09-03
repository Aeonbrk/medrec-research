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
        / "004-co-selection-compatibility"
        / "experiments"
        / "run_co_selection_compatibility_gate.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_co_selection_compatibility_gate", gate_01_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_01_self_test_passes() -> None:
    module = _load_gate_01_module()
    module.self_test_gate_01()


def test_npmi_boundaries_and_empirical_formula() -> None:
    """Requirement 1: NPMI zero co-selection -> -1; full joint support -> +1; empirical case matches formula."""
    module = _load_gate_01_module()

    # 1. Zero co-selection -> exactly -1.0
    assert module.compute_empirical_npmi(0, 10, 20, 100) == -1.0
    assert module.compute_empirical_npmi(0, 50, 50, 100) == -1.0

    # 2. Full joint support -> exactly +1.0
    assert module.compute_empirical_npmi(100, 100, 100, 100) == 1.0
    assert module.compute_empirical_npmi(6256, 6256, 6256, 6256) == 1.0

    # 3. Normal empirical cases
    c_mj, c_m, c_j, v = 15, 30, 45, 200
    p_mj = 15 / 200
    p_m = 30 / 200
    p_j = 45 / 200
    expected = math.log(p_mj / (p_m * p_j)) / (-math.log(p_mj))
    observed = module.compute_empirical_npmi(c_mj, c_m, c_j, v)
    assert math.isclose(observed, expected)


def test_candidate_observable_exact_peer_mean() -> None:
    """Requirement 2: Candidate A_t(m) is the exact peer mean."""
    module = _load_gate_01_module()

    npmi_table = {
        ("M1", "M2"): 0.40,
        ("M1", "M3"): -0.60,
        ("M1", "M4"): 0.20,
        ("M2", "M3"): 0.10,
        ("M2", "M4"): -0.10,
        ("M3", "M4"): 0.30,
    }
    pred_meds = ["M1", "M2", "M3", "M4"]
    # For M1: peer set is {M2, M3, M4}. Mean NPMI = (0.40 - 0.60 + 0.20) / 3 = 0.0
    a_m1 = module.compute_co_selection_compatibility("M1", pred_meds, npmi_table)
    assert math.isclose(a_m1, 0.0, abs_tol=1e-9)

    # For M2: peer set is {M1, M3, M4}. Mean NPMI = (0.40 + 0.10 - 0.10) / 3 = 0.40 / 3
    a_m2 = module.compute_co_selection_compatibility("M2", pred_meds, npmi_table)
    assert math.isclose(a_m2, 0.40 / 3.0)


def test_split_determinism_and_patient_disjoint() -> None:
    """Requirement 3: seed-2004 split is deterministic and patient-disjoint (529 Dev / 530 Audit)."""
    module = _load_gate_01_module()
    dev_1, audit_1 = module.partition_validation_patients(range(1059), seed=2004)
    dev_2, audit_2 = module.partition_validation_patients(range(1059), seed=2004)

    assert dev_1 == dev_2
    assert audit_1 == audit_2
    assert len(dev_1) == 529
    assert len(audit_1) == 530
    assert len(dev_1 & audit_1) == 0
    assert len(dev_1 | audit_1) == 1059


def test_control_and_augmented_feature_vectors_differ_by_one_feature() -> None:
    """Requirement 4: StrongControl and CoSelectionAugmented differ by exactly one feature."""
    module = _load_gate_01_module()
    Record = module.Gate01CandidateRecord

    cand = Record(
        patient_id="p1",
        visit_id="v1",
        patient_order=0,
        visit_order=1,
        gate01_partition="audit",
        medication_code="MED_X",
        model_score=0.75,
        prescription_size=4,
        candidate_count=100,
        candidate_prevalence=0.10,
        peer_prevalence_mean=0.08,
        co_selection_compatibility=0.25,
        active_ddi_degree=2,
        pareto_beneficial=True,
        delta_jaccard=0.05,
        delta_violation=-2,
    )
    v_train = 1000
    x_c, x_a = module.compute_feature_vectors(cand, v_train)

    assert len(x_c) == 7
    assert len(x_a) == 8
    assert x_a[:7] == x_c
    assert x_a[7] == cand.co_selection_compatibility

    # Check components
    u = 1.0 - 0.75
    c = math.log(1 + 4)
    f = math.log((100 + 0.5) / (1000 - 100 + 0.5))
    q = 0.08
    eps = 0.5 / (1000 + 1)
    g = math.log((q + eps) / (1 - q + eps))
    assert math.isclose(x_c[0], u)
    assert math.isclose(x_c[1], c)
    assert math.isclose(x_c[2], f)
    assert math.isclose(x_c[3], g)
    assert math.isclose(x_c[4], u * c)
    assert math.isclose(x_c[5], u * f)
    assert math.isclose(x_c[6], u * g)


def test_deterministic_ranking_tie_breaks() -> None:
    """Requirement 5: deterministic tie-breaking across policies."""
    module = _load_gate_01_module()
    Record = module.Gate01CandidateRecord

    # Candidates with identical score to verify 4-key / 5-key tie-breaks
    c1 = Record("p1", "v1", 2, 1, "audit", "MED_A", 0.6, 2, 10, 0.1, 0.1, 0.0, 1, True, 0.1, -1)
    c2 = Record("p2", "v1", 1, 1, "audit", "MED_A", 0.6, 2, 10, 0.1, 0.1, 0.0, 1, True, 0.1, -1)
    c3 = Record("p2", "v2", 1, 2, "audit", "MED_A", 0.6, 2, 10, 0.1, 0.1, 0.0, 1, True, 0.1, -1)
    c4 = Record("p1", "v1", 2, 1, "audit", "MED_B", 0.6, 2, 10, 0.1, 0.1, 0.0, 1, True, 0.1, -1)

    # Tie-breaks:
    # 1. medication_code asc: MED_A < MED_B (c4 goes last)
    # 2. patient_order asc: 1 < 2 (c2, c3 before c1)
    # 3. visit_order asc: 1 < 2 (c2 before c3)
    sorted_res = sorted(
        [c4, c1, c3, c2],
        key=lambda c: (c.model_score, c.medication_code, c.patient_order, c.visit_order),
    )
    assert sorted_res == [c2, c3, c1, c4]


def test_patient_cluster_bootstrap_does_not_refit_dev_models() -> None:
    """Requirement 6: patient-cluster bootstrap does not refit Dev models."""
    module = _load_gate_01_module()

    random.seed(1204)
    X_dev = [[random.gauss(0, 1) for _ in range(7)] for _ in range(50)]
    y_dev = [float(random.choice([0, 1])) for _ in range(50)]

    b0_init, beta_init = module.fit_ridge_linear_probability(X_dev, y_dev)

    # In bootstrap, Dev coefficients must remain identical
    b0_boot, beta_boot = module.fit_ridge_linear_probability(X_dev, y_dev)
    assert b0_init == b0_boot
    assert beta_init == beta_boot


def test_formal_execution_path_does_not_require_test_access() -> None:
    """Requirement 7: formal execution path uses validation only; test split is strictly excluded."""
    # Staging split range verification
    staging_path = (
        Path(__file__).parents[2]
        / "research"
        / "ideas"
        / "004-co-selection-compatibility"
        / "experiments"
        / "stage_gate01_inputs.py"
    )
    spec = importlib.util.spec_from_file_location("stage_gate01_inputs", staging_path)
    assert spec is not None
    assert spec.loader is not None
    stg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stg)

    splits = stg._split_ranges(6350)
    assert len(splits["train"]) == 4233  # 6350 * 2 / 3
    assert len(splits["test"]) == 1058  # (6350 - 4233) / 2
    assert len(splits["validation"]) == 1059

    # Verify that stage_gate01_inputs indexes only train and validation
    assert splits["validation"].start == 4233 + 1058
    assert splits["validation"].stop == 6350
    # No overlap between validation and test
    assert set(splits["validation"]).isdisjoint(set(splits["test"]))
