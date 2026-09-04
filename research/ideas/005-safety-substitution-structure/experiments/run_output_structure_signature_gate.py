#!/usr/bin/env python3
"""Gate 01 — ATC-3 output-structure signature for Idea 005."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import subprocess
import sys
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

_HARNESS_ROOT = Path(__file__).resolve().parents[4]
if str(_HARNESS_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_HARNESS_ROOT / "src"))

from medrec_research.adapters import ProcessPredictionAdapter  # noqa: E402
from medrec_research.dataset import DatasetManifest  # noqa: E402

FROZEN_PROTOCOL_COMMIT = "95966eab6d018e34b6dae4a52271562826bb5b4d"
FROZEN_DATASET_MANIFEST_SHA256 = "82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712"
FROZEN_DATASET_ID = "molerec-table1-comparison-v1-1"
FROZEN_SNAPSHOT_ID = "molerec-table1-c721-www23"
FROZEN_SNAPSHOT_SHA256 = "42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58"
FROZEN_MEDICATION_VOCABULARY_SHA256 = (
    "6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08"
)
FROZEN_DDI_ASSET_SHA256 = "dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7"
FROZEN_FEATURE_AVAILABILITY_SHA256 = (
    "9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9"
)
FROZEN_BASELINE_ENVIRONMENT_NAME = "medrec-molerec-table1"
FROZEN_BASELINE_ENVIRONMENT_SHA256 = (
    "6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda"
)
FROZEN_MOLEREC_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"
FROZEN_CHECKPOINT_SHA256 = "5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca"
FROZEN_BASELINE_CORE_SHA256 = "516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511"
FROZEN_ADAPTER_SHA256 = "9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531"
FROZEN_VALIDATION_PATIENT_COUNT = 1059

SPLIT_SEED = 2005
RAW_THRESHOLD = 0.5
GROUP_MASS_THRESHOLD = 0.5
GATE_A_MIN_GROUPS = 3
GATE_A_MIN_PATIENTS_PER_GROUP = 50
SIGNATURE_MIN_PATIENTS = 50
SIGNATURE_MIN_GROUPS = 3
SIGNATURE_MIN_PATIENTS_PER_GROUP = 10
THRESHOLD_ABOVE_ONE = 1.0 + 1e-12


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _content_sha256(value: object) -> str:
    serialized = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("ascii")).hexdigest()


def _git_revision(directory: Path) -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def verify_clean_checkout(directory: Path, name: str) -> None:
    completed = subprocess.run(
        ("git", "status", "--porcelain"),
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_changes = [
        line for line in completed.stdout.splitlines() if line.strip() and not line.startswith("??")
    ]
    if tracked_changes:
        raise RuntimeError(
            "{} checkout at {} has tracked changes:\n{}".format(
                name, directory, "\n".join(tracked_changes)
            )
        )


def verify_frozen_molerec_identity(
    molerec_root: Path,
    checkpoint: Path,
    adapter_path: Path,
) -> tuple[str, str, str, str]:
    source_revision = _git_revision(molerec_root)
    if source_revision != FROZEN_MOLEREC_REVISION:
        raise ValueError(
            "MoleRec source revision drift: expected {}, got {}".format(
                FROZEN_MOLEREC_REVISION, source_revision
            )
        )
    if not checkpoint.exists():
        raise FileNotFoundError("MoleRec checkpoint not found at {}".format(checkpoint))
    checkpoint_sha256 = _file_sha256(checkpoint)
    if checkpoint_sha256 != FROZEN_CHECKPOINT_SHA256:
        raise ValueError("MoleRec checkpoint identity drift")

    source_files = (
        "src/modules/MoleRec.py",
        "src/modules/SetTransformer.py",
        "src/modules/gnn/GNNs.py",
        "src/modules/gnn/GNNConv.py",
    )
    core_sha256 = _content_sha256(
        {
            "checkpoint_sha256": checkpoint_sha256,
            "revision": FROZEN_MOLEREC_REVISION,
            "source_files": {
                name: _file_sha256(molerec_root / name) for name in source_files
            },
        }
    )
    if core_sha256 != FROZEN_BASELINE_CORE_SHA256:
        raise ValueError("MoleRec baseline core identity drift")

    adapter_sha256 = _file_sha256(adapter_path)
    if adapter_sha256 != FROZEN_ADAPTER_SHA256:
        raise ValueError("MoleRec Comparison adapter identity drift")
    return source_revision, checkpoint_sha256, core_sha256, adapter_sha256


def verify_conda_environment(conda_executable: str | Path, environment_name: str) -> str:
    if environment_name != FROZEN_BASELINE_ENVIRONMENT_NAME:
        raise ValueError(
            "Formal Gate 01 must use {}".format(FROZEN_BASELINE_ENVIRONMENT_NAME)
        )
    completed = subprocess.run(
        (str(conda_executable), "list", "--explicit", "-n", environment_name),
        check=True,
        capture_output=True,
        text=True,
    )
    observed = hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest()
    if observed != FROZEN_BASELINE_ENVIRONMENT_SHA256:
        raise ValueError("Baseline environment identity drift")
    return observed


def verify_dataset_manifest_and_snapshot(
    manifest_path: Path,
    dataset_root: Path,
    staged_meta: dict[str, Any],
) -> tuple[DatasetManifest, str]:
    manifest = DatasetManifest.load(manifest_path)
    if manifest.manifest_sha256 != FROZEN_DATASET_MANIFEST_SHA256:
        raise ValueError("Dataset manifest identity drift")
    if manifest.dataset_id != FROZEN_DATASET_ID:
        raise ValueError("Dataset ID drift")
    if manifest.snapshot_id != FROZEN_SNAPSHOT_ID:
        raise ValueError("Dataset snapshot ID drift")

    snapshot_sha256 = _content_sha256(
        {
            "ddi_A_final.pkl": _file_sha256(dataset_root / "ddi_A_final.pkl"),
            "records_final.pkl": _file_sha256(dataset_root / "records_final.pkl"),
            "voc_final.pkl": _file_sha256(dataset_root / "voc_final.pkl"),
        }
    )
    if snapshot_sha256 != FROZEN_SNAPSHOT_SHA256 or snapshot_sha256 != manifest.checksum_sha256:
        raise ValueError("Dataset snapshot identity drift")
    if staged_meta["snapshot_sha256"] != snapshot_sha256:
        raise ValueError("Staged snapshot identity drift")
    if staged_meta["medication_vocabulary_sha256"] != FROZEN_MEDICATION_VOCABULARY_SHA256:
        raise ValueError("Medication vocabulary identity drift")
    if staged_meta["ddi_asset_sha256"] != FROZEN_DDI_ASSET_SHA256:
        raise ValueError("DDI asset identity drift")
    if staged_meta["feature_availability_sha256"] != FROZEN_FEATURE_AVAILABILITY_SHA256:
        raise ValueError("Feature availability identity drift")
    return manifest, snapshot_sha256


def atc2_parent(medication_code: str) -> str:
    if len(medication_code) < 4:
        raise ValueError("Expected ATC-3 medication code, got {!r}".format(medication_code))
    return medication_code[:3]


def build_sibling_groups(vocabulary: Iterable[str]) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for code in vocabulary:
        grouped[atc2_parent(str(code))].append(str(code))
    return {
        parent: tuple(sorted(members))
        for parent, members in sorted(grouped.items())
        if len(members) >= 2
    }


def group_mass(group: Iterable[str], scores: dict[str, float]) -> float:
    complement = 1.0
    member_count = 0
    for medication in group:
        score = float(scores[medication])
        if not math.isfinite(score) or score < 0.0 or score > 1.0:
            raise ValueError("MoleRec scores must be finite and in [0, 1]")
        complement *= 1.0 - score
        member_count += 1
    if member_count < 2:
        raise ValueError("GroupMass requires a sibling group with at least two members")
    return 1.0 - complement


def partition_validation_patients(
    patient_orders: Iterable[int], seed: int = SPLIT_SEED
) -> tuple[frozenset[int], frozenset[int]]:
    shuffled = sorted(set(patient_orders))
    random.Random(seed).shuffle(shuffled)
    midpoint = len(shuffled) // 2
    return frozenset(shuffled[:midpoint]), frozenset(shuffled[midpoint:])


def medication_f1(labels: list[bool], predictions: list[bool]) -> float:
    tp = sum(1 for label, pred in zip(labels, predictions) if label and pred)
    fp = sum(1 for label, pred in zip(labels, predictions) if not label and pred)
    fn = sum(1 for label, pred in zip(labels, predictions) if label and not pred)
    denominator = 2 * tp + fp + fn
    return 0.0 if denominator == 0 else (2.0 * tp) / denominator


def choose_f1_threshold(score_labels: Iterable[tuple[float, bool]]) -> float:
    rows = sorted(
        ((float(score), bool(label)) for score, label in score_labels),
        key=lambda item: item[0],
        reverse=True,
    )
    if not rows:
        return RAW_THRESHOLD
    if any(not math.isfinite(score) or score < 0.0 or score > 1.0 for score, _ in rows):
        raise ValueError("Threshold fitting received a score outside [0, 1]")

    candidates = sorted(
        {0.0, RAW_THRESHOLD, THRESHOLD_ABOVE_ONE, *(score for score, _ in rows)},
        reverse=True,
    )
    total_positive = sum(1 for _, label in rows if label)
    tp = 0
    fp = 0
    index = 0
    best_threshold = RAW_THRESHOLD
    best_key = (-1.0, float("-inf"), float("-inf"))

    for threshold in candidates:
        while index < len(rows) and rows[index][0] >= threshold:
            if rows[index][1]:
                tp += 1
            else:
                fp += 1
            index += 1
        fn = total_positive - tp
        denominator = 2 * tp + fp + fn
        f1 = 0.0 if denominator == 0 else (2.0 * tp) / denominator
        key = (f1, -abs(threshold - RAW_THRESHOLD), threshold)
        if key > best_key:
            best_key = key
            best_threshold = threshold
    return float(best_threshold)


def fit_per_medication_thresholds(
    predictions: list[dict[str, Any]],
    targets: dict[str, list[str]],
    traversal_by_visit: dict[str, tuple[int, int]],
    dev_patients: frozenset[int],
    vocabulary: Iterable[str],
) -> dict[str, float]:
    rows_by_medication: dict[str, list[tuple[float, bool]]] = {
        medication: [] for medication in vocabulary
    }
    for prediction in predictions:
        key = "{}:{}".format(prediction["patient_id"], prediction["visit_id"])
        patient_order, _ = traversal_by_visit[key]
        if patient_order not in dev_patients:
            continue
        target_set = set(targets[key])
        scores = prediction["vocabulary_scores"]
        for medication in rows_by_medication:
            rows_by_medication[medication].append(
                (float(scores[medication]), medication in target_set)
            )
    return {
        medication: choose_f1_threshold(rows)
        for medication, rows in rows_by_medication.items()
    }


def predicted_set(scores: dict[str, float], thresholds: dict[str, float]) -> frozenset[str]:
    return frozenset(
        medication
        for medication, score in scores.items()
        if float(score) >= float(thresholds[medication])
    )


def signature_flags(
    group: tuple[str, ...],
    target_member: str,
    scores: dict[str, float],
    policy_prediction: frozenset[str],
) -> tuple[bool, bool, float]:
    mass = group_mass(group, scores)
    group_predictions = policy_prediction.intersection(group)
    split_mass_fn = (
        target_member not in policy_prediction
        and not group_predictions
        and mass >= GROUP_MASS_THRESHOLD
    )
    duplicate_sibling_fp = (
        target_member in policy_prediction
        and bool(group_predictions.difference({target_member}))
    )
    if split_mass_fn and duplicate_sibling_fp:
        raise AssertionError("Gate 01 signatures must be mutually exclusive")
    return split_mass_fn, duplicate_sibling_fp, mass


def _empty_policy_stats() -> dict[str, Any]:
    return {
        "split_units": 0,
        "duplicate_units": 0,
        "any_units": 0,
        "split_patients": set(),
        "duplicate_patients": set(),
        "any_patients": set(),
        "any_patients_by_group": defaultdict(set),
    }


def evaluate_audit_units(
    predictions: list[dict[str, Any]],
    targets: dict[str, list[str]],
    traversal_by_visit: dict[str, tuple[int, int]],
    audit_patients: frozenset[int],
    groups: dict[str, tuple[str, ...]],
    calibrated_thresholds: dict[str, float],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    eligible_patients: set[int] = set()
    eligible_patients_by_group: dict[str, set[int]] = defaultdict(set)
    eligible_units = 0
    raw = _empty_policy_stats()
    calibrated = _empty_policy_stats()
    restricted_rows: list[dict[str, Any]] = []

    for prediction in predictions:
        visit_key = "{}:{}".format(prediction["patient_id"], prediction["visit_id"])
        patient_order, visit_order = traversal_by_visit[visit_key]
        if patient_order not in audit_patients:
            continue
        target_set = set(targets[visit_key])
        scores = prediction["vocabulary_scores"]

        adapter_predicted = frozenset(prediction["predicted_medications"])
        threshold_predicted = frozenset(
            medication for medication, score in scores.items() if float(score) >= RAW_THRESHOLD
        )
        if adapter_predicted != threshold_predicted:
            raise ValueError(
                "Frozen adapter predicted set does not equal vocabulary_scores >= 0.5"
            )

        raw_prediction = threshold_predicted
        calibrated_prediction = predicted_set(scores, calibrated_thresholds)

        for parent, group in groups.items():
            observed_members = target_set.intersection(group)
            if len(observed_members) != 1:
                continue
            target_member = next(iter(observed_members))
            eligible_units += 1
            eligible_patients.add(patient_order)
            eligible_patients_by_group[parent].add(patient_order)

            raw_split, raw_duplicate, mass = signature_flags(
                group, target_member, scores, raw_prediction
            )
            cal_split, cal_duplicate, _ = signature_flags(
                group, target_member, scores, calibrated_prediction
            )

            for stats, split_flag, duplicate_flag in (
                (raw, raw_split, raw_duplicate),
                (calibrated, cal_split, cal_duplicate),
            ):
                if split_flag:
                    stats["split_units"] += 1
                    stats["split_patients"].add(patient_order)
                if duplicate_flag:
                    stats["duplicate_units"] += 1
                    stats["duplicate_patients"].add(patient_order)
                if split_flag or duplicate_flag:
                    stats["any_units"] += 1
                    stats["any_patients"].add(patient_order)
                    stats["any_patients_by_group"][parent].add(patient_order)

            restricted_rows.append(
                {
                    "patient_id": prediction["patient_id"],
                    "visit_id": prediction["visit_id"],
                    "patient_order": patient_order,
                    "visit_order": visit_order,
                    "atc2_parent": parent,
                    "group_members": list(group),
                    "target_member": target_member,
                    "group_mass": mass,
                    "raw_split_mass_fn": raw_split,
                    "raw_duplicate_sibling_fp": raw_duplicate,
                    "calibrated_split_mass_fn": cal_split,
                    "calibrated_duplicate_sibling_fp": cal_duplicate,
                }
            )

    def public_policy(stats: dict[str, Any]) -> dict[str, int]:
        parents_at_10 = sum(
            1
            for patients in stats["any_patients_by_group"].values()
            if len(patients) >= SIGNATURE_MIN_PATIENTS_PER_GROUP
        )
        return {
            "split_signature_units": int(stats["split_units"]),
            "split_signature_patients": len(stats["split_patients"]),
            "duplicate_signature_units": int(stats["duplicate_units"]),
            "duplicate_signature_patients": len(stats["duplicate_patients"]),
            "any_signature_units": int(stats["any_units"]),
            "any_signature_patients": len(stats["any_patients"]),
            "signature_parents_with_at_least_10_patients": parents_at_10,
        }

    public = {
        "eligible_units": eligible_units,
        "eligible_patients": len(eligible_patients),
        "candidate_group_count": len(groups),
        "eligible_group_count": sum(1 for patients in eligible_patients_by_group.values() if patients),
        "groups_with_at_least_50_eligible_patients": sum(
            1
            for patients in eligible_patients_by_group.values()
            if len(patients) >= GATE_A_MIN_PATIENTS_PER_GROUP
        ),
        "raw": public_policy(raw),
        "calibrated": public_policy(calibrated),
    }
    return public, restricted_rows


def evaluate_decision_tree(stats: dict[str, Any]) -> tuple[str, dict[str, bool]]:
    gate_a = stats["groups_with_at_least_50_eligible_patients"] >= GATE_A_MIN_GROUPS
    raw = stats["raw"]
    gate_b_patients = raw["any_signature_patients"] >= SIGNATURE_MIN_PATIENTS
    gate_b_groups = (
        raw["signature_parents_with_at_least_10_patients"] >= SIGNATURE_MIN_GROUPS
    )
    calibrated = stats["calibrated"]
    gate_c_patients = calibrated["any_signature_patients"] >= SIGNATURE_MIN_PATIENTS
    gate_c_groups = (
        calibrated["signature_parents_with_at_least_10_patients"] >= SIGNATURE_MIN_GROUPS
    )
    criteria = {
        "gate_a_multi_group_support": gate_a,
        "gate_b_signature_patients": gate_b_patients,
        "gate_b_signature_groups": gate_b_groups,
        "gate_c_calibrated_signature_patients": gate_c_patients,
        "gate_c_calibrated_signature_groups": gate_c_groups,
    }
    if not gate_a:
        return "INCONCLUSIVE_INSUFFICIENT_ATC3_GROUP_SUPPORT", criteria
    if not (gate_b_patients and gate_b_groups):
        return "STOP_NO_MATERIAL_OUTPUT_STRUCTURE_SIGNATURE", criteria
    if not (gate_c_patients and gate_c_groups):
        return "STOP_SIGNATURE_EXPLAINED_BY_PER_DRUG_CALIBRATION", criteria
    return "PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION", criteria


def self_test_gate_01() -> None:
    groups = build_sibling_groups(("A02A", "A02B", "B01A", "B01B", "C01A"))
    assert groups == {"A02": ("A02A", "A02B"), "B01": ("B01A", "B01B")}
    assert math.isclose(
        group_mass(("A02A", "A02B"), {"A02A": 0.4, "A02B": 0.3}),
        0.58,
    )

    dev_1, audit_1 = partition_validation_patients(range(1059), seed=2005)
    dev_2, audit_2 = partition_validation_patients(range(1059), seed=2005)
    assert dev_1 == dev_2 and audit_1 == audit_2
    assert len(dev_1) == 529 and len(audit_1) == 530 and not (dev_1 & audit_1)

    rows = [(0.9, True), (0.8, True), (0.7, False), (0.2, False)]
    assert choose_f1_threshold(rows) == 0.8
    assert choose_f1_threshold([(0.1, False), (0.2, False)]) == RAW_THRESHOLD

    scores = {"A02A": 0.4, "A02B": 0.3}
    split, duplicate, _ = signature_flags(
        ("A02A", "A02B"), "A02A", scores, frozenset()
    )
    assert split and not duplicate
    split, duplicate, _ = signature_flags(
        ("A02A", "A02B"),
        "A02A",
        {"A02A": 0.8, "A02B": 0.7},
        frozenset({"A02A", "A02B"}),
    )
    assert duplicate and not split

    base_stats = {
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
    verdict, _ = evaluate_decision_tree(base_stats)
    assert verdict == "PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION"
    no_raw = json.loads(json.dumps(base_stats))
    no_raw["raw"]["any_signature_patients"] = 49
    assert evaluate_decision_tree(no_raw)[0] == "STOP_NO_MATERIAL_OUTPUT_STRUCTURE_SIGNATURE"
    calibrated_kill = json.loads(json.dumps(base_stats))
    calibrated_kill["calibrated"]["any_signature_patients"] = 49
    assert (
        evaluate_decision_tree(calibrated_kill)[0]
        == "STOP_SIGNATURE_EXPLAINED_BY_PER_DRUG_CALIBRATION"
    )
    no_support = json.loads(json.dumps(base_stats))
    no_support["groups_with_at_least_50_eligible_patients"] = 2
    assert (
        evaluate_decision_tree(no_support)[0]
        == "INCONCLUSIVE_INSUFFICIENT_ATC3_GROUP_SUPPORT"
    )


def run_gate(
    dataset_manifest: Path,
    dataset_root: Path,
    output_root: Path,
    molerec_root: Path,
    checkpoint: Path,
    baseline_environment: str = FROZEN_BASELINE_ENVIRONMENT_NAME,
    conda_executable: str | Path | None = None,
    expected_harness_revision: str | None = None,
    harness_root: Path | None = None,
    summary_output: Path | None = None,
) -> dict[str, Any]:
    dataset_manifest = dataset_manifest.resolve()
    dataset_root = dataset_root.resolve()
    output_root = output_root.resolve()
    molerec_root = molerec_root.resolve()
    checkpoint = checkpoint.resolve()
    if output_root.exists():
        raise FileExistsError("Gate 01 requires a fresh output directory: {}".format(output_root))
    output_root.mkdir(parents=True, exist_ok=False)

    harness_root = _HARNESS_ROOT if harness_root is None else harness_root.resolve()
    verify_clean_checkout(harness_root, "medrec-research")
    verify_clean_checkout(molerec_root, "MoleRec")
    harness_revision = _git_revision(harness_root)
    if expected_harness_revision is not None and harness_revision != expected_harness_revision:
        raise ValueError(
            "Harness revision drift: expected {}, got {}".format(
                expected_harness_revision, harness_revision
            )
        )

    adapter_path = harness_root / "baselines" / "molerec_comparison.py"
    source_revision, checkpoint_sha256, core_sha256, adapter_sha256 = (
        verify_frozen_molerec_identity(molerec_root, checkpoint, adapter_path)
    )

    if conda_executable is None:
        conda_executable = shutil.which("conda") or "conda"
    environment_sha256 = verify_conda_environment(conda_executable, baseline_environment)

    staging_dir = output_root / ".staging"
    staging_dir.mkdir(parents=True, exist_ok=False)
    staging_script = Path(__file__).resolve().parent / "stage_gate01_inputs.py"
    subprocess.run(
        (
            str(conda_executable),
            "run",
            "--no-capture-output",
            "-n",
            baseline_environment,
            "python",
            str(staging_script),
            "--dataset-root",
            str(dataset_root),
            "--output-dir",
            str(staging_dir),
        ),
        check=True,
    )

    meta = json.loads((staging_dir / "validation-meta.json").read_text(encoding="utf-8"))
    manifest, snapshot_sha256 = verify_dataset_manifest_and_snapshot(
        dataset_manifest, dataset_root, meta
    )
    if int(meta["validation_patient_count"]) != FROZEN_VALIDATION_PATIENT_COUNT:
        raise ValueError("Validation patient count drift")

    expected_visits = [tuple(item) for item in meta["expected_visits"]]
    targets: dict[str, list[str]] = meta["targets"]
    vocabulary = tuple(meta["medication_vocabulary"])
    traversal_by_visit = {
        "{}:{}".format(item["patient_id"], item["visit_id"]): (
            int(item["patient_order"]),
            int(item["visit_order"]),
        )
        for item in meta["visit_traversal_metadata"]
    }

    adapter_command = (
        str(conda_executable),
        "run",
        "--no-capture-output",
        "-n",
        baseline_environment,
        "python",
        str(adapter_path),
        "--upstream-root",
        str(molerec_root),
        "--dataset-root",
        str(dataset_root),
        "--features",
        str(Path(meta["features_path"])),
        "--checkpoint",
        str(checkpoint),
    )
    batch = ProcessPredictionAdapter(adapter_command, timeout_seconds=3600.0).predict_comparison(
        {"dataset_id": FROZEN_DATASET_ID},
        method_id="molerec",
        expected_visits=expected_visits,
        medication_vocabulary=vocabulary,
    )
    predictions = [
        {
            "patient_id": prediction.patient_id,
            "visit_id": prediction.visit_id,
            "predicted_medications": list(prediction.predicted_medications),
            "vocabulary_scores": {
                item.medication_code: float(item.score)
                for item in prediction.vocabulary_scores
            },
        }
        for prediction in batch.predictions
    ]

    patient_orders = range(FROZEN_VALIDATION_PATIENT_COUNT)
    dev_patients, audit_patients = partition_validation_patients(patient_orders, seed=SPLIT_SEED)
    thresholds = fit_per_medication_thresholds(
        predictions, targets, traversal_by_visit, dev_patients, vocabulary
    )
    groups = build_sibling_groups(vocabulary)
    stats, restricted_rows = evaluate_audit_units(
        predictions,
        targets,
        traversal_by_visit,
        audit_patients,
        groups,
        thresholds,
    )
    verdict, criteria = evaluate_decision_tree(stats)

    (output_root / "dev-thresholds.json").write_text(
        json.dumps(thresholds, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_root / "gate-01-units.jsonl").open("w", encoding="utf-8") as stream:
        for row in restricted_rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")

    summary = {
        "schema_version": 1,
        "idea_id": "005-safety-substitution-structure",
        "gate_id": "gate-01-output-structure-signature",
        "formal_run_id": output_root.name,
        "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        "harness_revision": harness_revision,
        "verdict": verdict,
        "decision_criteria": criteria,
        "identities": {
            "model_source_revision": source_revision,
            "checkpoint_sha256": checkpoint_sha256,
            "baseline_core_sha256": core_sha256,
            "adapter_sha256": adapter_sha256,
            "baseline_environment_name": baseline_environment,
            "baseline_environment_sha256": environment_sha256,
            "dataset_id": manifest.dataset_id,
            "dataset_manifest_sha256": manifest.manifest_sha256,
            "snapshot_id": manifest.snapshot_id,
            "snapshot_sha256": snapshot_sha256,
            "medication_vocabulary_sha256": FROZEN_MEDICATION_VOCABULARY_SHA256,
            "ddi_asset_sha256": FROZEN_DDI_ASSET_SHA256,
            "feature_availability_sha256": FROZEN_FEATURE_AVAILABILITY_SHA256,
        },
        "split": {
            "source": "validation",
            "patient_level": True,
            "seed": SPLIT_SEED,
            "validation_patient_count": FROZEN_VALIDATION_PATIENT_COUNT,
            "dev_patient_count": len(dev_patients),
            "audit_patient_count": len(audit_patients),
        },
        "group_definition": {
            "medication_level": "ATC-3",
            "candidate_parent": "first three characters / ATC-2",
            "minimum_vocabulary_members": 2,
            "clinical_substitutability_claimed": False,
        },
        "raw_threshold": RAW_THRESHOLD,
        "group_mass_threshold": GROUP_MASS_THRESHOLD,
        "calibration_control": {
            "fit_split": "Dev only",
            "objective": "per-medication F1",
            "tie_break": "closest_to_0.5_then_larger_threshold",
        },
        "audit": stats,
    }
    summary_text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (output_root / "gate-01-summary.json").write_text(summary_text, encoding="utf-8")
    if summary_output is not None:
        summary_output = summary_output.resolve()
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(summary_text, encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--dataset-manifest", type=Path)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--molerec-root", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--baseline-environment", default=FROZEN_BASELINE_ENVIRONMENT_NAME)
    parser.add_argument("--conda-executable", default=None)
    parser.add_argument("--expected-harness-revision", default=None)
    parser.add_argument("--summary-output", type=Path, default=None)
    args = parser.parse_args()

    if args.self_test:
        self_test_gate_01()
        print("Idea 005 Gate 01 self-test passed")
        return
    required = (
        args.dataset_manifest,
        args.dataset_root,
        args.output_root,
        args.molerec_root,
        args.checkpoint,
    )
    if not all(required):
        parser.error(
            "Execution requires --dataset-manifest, --dataset-root, --output-root, "
            "--molerec-root, and --checkpoint (or pass --self-test)."
        )
    summary = run_gate(
        dataset_manifest=args.dataset_manifest,
        dataset_root=args.dataset_root,
        output_root=args.output_root,
        molerec_root=args.molerec_root,
        checkpoint=args.checkpoint,
        baseline_environment=args.baseline_environment,
        conda_executable=args.conda_executable,
        expected_harness_revision=args.expected_harness_revision,
        summary_output=args.summary_output,
    )
    print("Gate 01 execution complete. Verdict: {}".format(summary["verdict"]))


if __name__ == "__main__":
    main()
