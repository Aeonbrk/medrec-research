from __future__ import annotations

import importlib.util
import math
from pathlib import Path


def _load_gate_module():
    path = (
        Path(__file__).parents[2]
        / "research"
        / "ideas"
        / "005-safety-substitution-structure"
        / "experiments"
        / "run_output_structure_signature_gate.py"
    )
    spec = importlib.util.spec_from_file_location("run_output_structure_signature_gate", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_01_self_test_passes() -> None:
    _load_gate_module().self_test_gate_01()


def test_atc2_sibling_grouping_is_prefix_only() -> None:
    module = _load_gate_module()
    groups = module.build_sibling_groups(("A02A", "A02B", "A03A", "B01A", "B01B", "B01C", "C01A"))
    assert groups == {
        "A02": ("A02A", "A02B"),
        "B01": ("B01A", "B01B", "B01C"),
    }


def test_group_mass_uses_fixed_noisy_or_diagnostic() -> None:
    module = _load_gate_module()
    observed = module.group_mass(
        ("A02A", "A02B", "A02C"),
        {"A02A": 0.2, "A02B": 0.3, "A02C": 0.4},
    )
    assert math.isclose(observed, 1.0 - (0.8 * 0.7 * 0.6))


def test_seed_2005_split_is_deterministic_and_patient_disjoint() -> None:
    module = _load_gate_module()
    dev_1, audit_1 = module.partition_validation_patients(range(1059), seed=2005)
    dev_2, audit_2 = module.partition_validation_patients(range(1059), seed=2005)
    assert dev_1 == dev_2
    assert audit_1 == audit_2
    assert len(dev_1) == 529
    assert len(audit_1) == 530
    assert not dev_1.intersection(audit_1)
    assert len(dev_1.union(audit_1)) == 1059


def test_per_medication_threshold_f1_and_tie_breaking() -> None:
    module = _load_gate_module()
    assert module.choose_f1_threshold([(0.9, True), (0.8, True), (0.7, False), (0.2, False)]) == 0.8
    assert module.choose_f1_threshold([(0.9, False), (0.1, False)]) == 0.5


def test_split_mass_and_duplicate_signatures_are_mutually_exclusive() -> None:
    module = _load_gate_module()
    group = ("A02A", "A02B")

    split, duplicate, mass = module.signature_flags(
        group,
        "A02A",
        {"A02A": 0.4, "A02B": 0.3},
        frozenset(),
    )
    assert mass >= 0.5
    assert split is True
    assert duplicate is False

    split, duplicate, _ = module.signature_flags(
        group,
        "A02A",
        {"A02A": 0.8, "A02B": 0.7},
        frozenset({"A02A", "A02B"}),
    )
    assert split is False
    assert duplicate is True


def test_decision_tree_has_exact_four_terminal_states() -> None:
    module = _load_gate_module()
    base = {
        "groups_with_at_least_50_eligible_patients": 3,
        "raw": {
            "any_signature_patients": 50,
            "signature_parents_with_at_least_10_patients": 3,
        },
        "calibrated": {
            "any_signature_patients": 50,
            "signature_parents_with_at_least_10_patients": 3,
        },
    }
    assert (
        module.evaluate_decision_tree(base)[0]
        == "PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION"
    )

    insufficient = {
        **base,
        "groups_with_at_least_50_eligible_patients": 2,
    }
    assert (
        module.evaluate_decision_tree(insufficient)[0]
        == "INCONCLUSIVE_INSUFFICIENT_ATC3_GROUP_SUPPORT"
    )

    no_signature = {
        **base,
        "raw": {
            "any_signature_patients": 49,
            "signature_parents_with_at_least_10_patients": 3,
        },
    }
    assert (
        module.evaluate_decision_tree(no_signature)[0]
        == "STOP_NO_MATERIAL_OUTPUT_STRUCTURE_SIGNATURE"
    )

    calibrated = {
        **base,
        "calibrated": {
            "any_signature_patients": 49,
            "signature_parents_with_at_least_10_patients": 3,
        },
    }
    assert (
        module.evaluate_decision_tree(calibrated)[0]
        == "STOP_SIGNATURE_EXPLAINED_BY_PER_DRUG_CALIBRATION"
    )


def test_stage_script_never_iterates_test_for_gate_inputs() -> None:
    stage_path = (
        Path(__file__).parents[2]
        / "research"
        / "ideas"
        / "005-safety-substitution-structure"
        / "experiments"
        / "stage_gate01_inputs.py"
    )
    spec = importlib.util.spec_from_file_location("stage_gate01_inputs", stage_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    splits = module._split_ranges(6350)
    assert len(splits["train"]) == 4233
    assert len(splits["test"]) == 1058
    assert len(splits["validation"]) == 1059
    assert set(splits["validation"]).isdisjoint(set(splits["test"]))
