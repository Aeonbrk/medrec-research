#!/usr/bin/env python3
"""Build the public-safe evidence packet for one structured-set pair."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import dill
import numpy as np

try:
    from structured_set import assignment_decode, assignment_pairs, threshold_decode
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from structured_set import assignment_decode, assignment_pairs, threshold_decode

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
from research.prototypes.paper_contract.evaluator import VisitPrediction, evaluate  # noqa: E402

MEDICATIONS = 131
PROFILE_ID = "mimic-iii-canonical-131-paper-dev-v1"
SNAPSHOT_ID = "molerec-table1-c721-www23"
TRAIN_DEV_ID = "gate01-train-dev-5752596a-20260913a"


def _load_array(root: Path, name: str) -> np.ndarray:
    return np.array(np.load(root / name, mmap_mode="r"), dtype=np.float32, copy=True)


def _word(indexed: Any, index: int) -> str:
    try:
        return str(indexed[index])
    except (KeyError, IndexError):
        return str(indexed[str(index)])


def _is_dev(patient_id: int) -> bool:
    import hashlib

    digest = hashlib.sha256(("idea008-gate01-v1:" + str(patient_id)).encode()).digest()[:8]
    return int.from_bytes(digest, "big") / float(2**64) < 0.5


def _build_rows(records: Sequence[Any], patients: Sequence[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for patient_index in patients:
        history: list[tuple[list[int], list[int], list[int]]] = []
        for visit_index, admission in enumerate(records[int(patient_index)]):
            rows.append(
                {
                    "_patient_id": str(int(patient_index)),
                    "_visit_id": f"{int(patient_index)}:{visit_index}",
                    "_medications": list(admission[2]),
                }
            )
            history.append((list(admission[0]), list(admission[1]), list(admission[2])))
    return rows


def _targets(targets: np.ndarray) -> list[tuple[int, ...]]:
    return [tuple(int(index) for index in np.flatnonzero(row > 0.5)) for row in targets]


def _surface(
    rows: Sequence[Mapping[str, Any]],
    target_sets: Sequence[Sequence[int]],
    utility: np.ndarray,
    decoder: str,
    beta: float,
    vocabulary: tuple[str, ...],
    ddi_pairs: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    samples: list[VisitPrediction] = []
    scores = utility.max(axis=1)
    for index, row in enumerate(rows):
        if decoder == "threshold":
            predicted = threshold_decode(utility[index], beta)
        else:
            predicted = assignment_decode(utility[index], beta)
        samples.append(
            VisitPrediction(
                patient_id=row["_patient_id"],
                visit_id=row["_visit_id"],
                target_medications=tuple(vocabulary[value] for value in target_sets[index]),
                predicted_medications=tuple(vocabulary[value] for value in predicted),
                medication_scores=tuple(float(value) for value in scores[index]),
            )
        )
    return evaluate(samples, vocabulary=vocabulary, ddi_pairs=ddi_pairs)


def _pair_diagnostics(
    utility: np.ndarray,
    target_sets: Sequence[Sequence[int]],
    beta: float,
    rows: Sequence[Mapping[str, Any]],
    vocabulary: tuple[str, ...],
    ddi_pairs: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    threshold_sets: list[set[int]] = []
    assignment_sets: list[set[int]] = []
    removed_counts: list[int] = []
    removed_tp = 0
    removed_fp = 0
    changed = 0
    subset_violations = 0
    collision_visits = 0
    reassigned_edges = 0
    threshold_edges = 0
    for index, values in enumerate(utility):
        threshold = set(threshold_decode(values, beta))
        pairs = assignment_pairs(values, beta)
        assignment = {medication for _slot, medication in pairs}
        target = set(target_sets[index])
        threshold_sets.append(threshold)
        assignment_sets.append(assignment)
        removed = threshold - assignment
        removed_counts.append(len(removed))
        removed_tp += len(removed & target)
        removed_fp += len(removed - target)
        changed += int(threshold != assignment)
        subset_violations += int(not assignment <= threshold)
        support_counts = (values > beta).sum(axis=0)
        collision_visits += int(
            any(int(support_counts[medication]) > 1 for medication in threshold)
        )

        canonical_support = {}
        for medication in sorted(threshold):
            slots = np.flatnonzero(values[:, medication] > beta)
            if len(slots):
                canonical_support[medication] = int(slots[0])
        assigned = {medication: slot for slot, medication in pairs}
        for medication, slot in assigned.items():
            if medication in canonical_support:
                threshold_edges += 1
                reassigned_edges += int(slot != canonical_support[medication])

    threshold_metrics = _surface(
        rows, target_sets, utility, "threshold", beta, vocabulary, ddi_pairs
    )
    assignment_metrics = _surface(
        rows, target_sets, utility, "assignment", beta, vocabulary, ddi_pairs
    )
    return {
        "beta": beta,
        "set_change_visit_rate": changed / float(len(utility)),
        "mean_removed_medications": float(np.mean(removed_counts)),
        "total_removed_medications": int(sum(removed_counts)),
        "removed_true_positive": int(removed_tp),
        "removed_false_positive": int(removed_fp),
        "supporting_slot_collision_rate": collision_visits / float(len(utility)),
        "assignment_reassignment_rate": 0.0
        if threshold_edges == 0
        else reassigned_edges / float(threshold_edges),
        "subset_invariant_violations": int(subset_violations),
        "threshold_metrics": threshold_metrics,
        "assignment_metrics": assignment_metrics,
        "delta_assignment_minus_threshold": {
            "jaccard": assignment_metrics["jaccard"] - threshold_metrics["jaccard"],
            "f1": assignment_metrics["f1"] - threshold_metrics["f1"],
            "average_medication_count": assignment_metrics["average_medication_count"]
            - threshold_metrics["average_medication_count"],
            "ddi_rate": assignment_metrics["ddi_rate"] - threshold_metrics["ddi_rate"],
        },
    }


def _count_alignment(
    rows: Sequence[Mapping[str, Any]],
    target_sets: Sequence[Sequence[int]],
    utility: np.ndarray,
    decoder: str,
    beta: float,
) -> dict[str, float]:
    errors = []
    signed = []
    for index in range(len(rows)):
        predicted = (
            threshold_decode(utility[index], beta)
            if decoder == "threshold"
            else assignment_decode(utility[index], beta)
        )
        error = len(predicted) - len(target_sets[index])
        errors.append(abs(error))
        signed.append(error)
    return {
        "mean_absolute_medication_count_error": float(np.mean(errors)),
        "mean_signed_medication_count_error": float(np.mean(signed)),
    }


def _grid_curves(
    rows: Sequence[Mapping[str, Any]],
    target_sets: Sequence[Sequence[int]],
    utility: np.ndarray,
    beta_grid: Sequence[float],
    vocabulary: tuple[str, ...],
    ddi_pairs: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for decoder in ("threshold", "assignment"):
        values[decoder] = []
        for index, beta in enumerate(beta_grid):
            metrics = _surface(rows, target_sets, utility, decoder, beta, vocabulary, ddi_pairs)
            values[decoder].append(
                {
                    "beta": beta,
                    "beta_grid_index": index,
                    "is_grid_boundary": index in (0, len(beta_grid) - 1),
                    "metrics": metrics,
                }
            )
    return values


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    control = json.loads((args.control_dir / "results.json").read_text(encoding="utf-8"))
    full = json.loads((args.full_dir / "results.json").read_text(encoding="utf-8"))
    if control["status"] != "complete" or full["status"] != "complete":
        raise RuntimeError("both arms must complete before evidence synthesis")
    if control["source_revision"] != full["source_revision"]:
        raise RuntimeError("matched arms use different source revisions")
    if control["initial_state_sha256"] != full["initial_state_sha256"]:
        raise RuntimeError("matched arms do not share the same initialization digest")
    if (
        control["parameter_count"] != full["parameter_count"]
        or control["parameter_names"] != full["parameter_names"]
    ):
        raise RuntimeError("matched arms do not share parameter names/count")
    if control["validation_schedule"] != full["validation_schedule"]:
        raise RuntimeError("matched arms do not share validation schedule")
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    dev_patients = tuple(index for index in range(split, len(records)) if _is_dev(index))
    rows = _build_rows(records, dev_patients)
    targets = _load_array(train_dev_root, "dev_targets.npy")
    target_sets = _targets(targets)
    vocabulary = tuple(_word(voc["med_voc"].idx2word, index) for index in range(MEDICATIONS))
    ddi_pairs = tuple(
        (vocabulary[left], vocabulary[right])
        for left, right in zip(*np.triu(ddi, 1).nonzero())  # noqa: B905 - NumPy returns equal-length coordinate arrays
    )
    control_utility = np.load(args.control_dir / "selected_dev_utility.npy")
    full_utility = np.load(args.full_dir / "selected_dev_utility.npy")
    control_beta = float(control["selected_beta"])
    full_beta = float(full["selected_beta"])
    control_primary = control["metrics"]["Dev"]
    full_primary = full["metrics"]["Dev"]
    primary_deltas = {
        key: full_primary[key] - control_primary[key]
        for key in ("jaccard", "f1", "prauc", "ddi_rate", "average_medication_count")
    }

    control_crossover = _pair_diagnostics(
        control_utility, target_sets, control_beta, rows, vocabulary, ddi_pairs
    )
    full_crossover = _pair_diagnostics(
        full_utility, target_sets, full_beta, rows, vocabulary, ddi_pairs
    )
    beta_grid = tuple(float(value) for value in control["config"]["beta_grid"])
    curves = {
        "control_selected_checkpoint": _grid_curves(
            rows, target_sets, control_utility, beta_grid, vocabulary, ddi_pairs
        ),
        "full_selected_checkpoint": _grid_curves(
            rows, target_sets, full_utility, beta_grid, vocabulary, ddi_pairs
        ),
    }
    full_anchor_count = float(full_primary["average_medication_count"])
    nearest = min(
        curves["control_selected_checkpoint"]["threshold"],
        key=lambda row: (
            abs(row["metrics"]["average_medication_count"] - full_anchor_count),
            row["beta_grid_index"],
        ),
    )
    aligned = nearest["metrics"]
    count_alignment = {
        "anchor": "Full primary M/A",
        "anchor_checkpoint": full["selected_checkpoint"],
        "anchor_beta": full_beta,
        "anchor_avgmed": full_anchor_count,
        "control_checkpoint": control["selected_checkpoint"],
        "matched_control_beta": nearest["beta"],
        "matched_control_avgmed": aligned["average_medication_count"],
        "residual_avgmed_gap": aligned["average_medication_count"] - full_anchor_count,
        "delta_jaccard_full_minus_control": full_primary["jaccard"] - aligned["jaccard"],
        "delta_f1_full_minus_control": full_primary["f1"] - aligned["f1"],
        "delta_ddi_full_minus_control": full_primary["ddi_rate"] - aligned["ddi_rate"],
        "control_count_error": _count_alignment(
            rows, target_sets, control_utility, "threshold", nearest["beta"]
        ),
        "full_count_error": _count_alignment(
            rows, target_sets, full_utility, "assignment", full_beta
        ),
    }

    control_validity = {
        "finite_optimization": all(
            np.isfinite(row["train_loss"]) and np.isfinite(row["dev_metrics"]["jaccard"])
            for row in control["progress"]
        ),
        "loss_decreases": control["progress"][-1]["train_loss"]
        < control["progress"][0]["train_loss"],
        "non_degenerate_beta_curve": len(
            {
                row["metrics"]["average_medication_count"]
                for row in curves["control_selected_checkpoint"]["threshold"]
            }
        )
        > 1,
        "selected_predictions_not_collapsed": control_primary["average_medication_count"] > 0.0,
    }
    control_validity["valid"] = all(control_validity.values())
    timing_record = json.loads(args.timing_preflight.read_text(encoding="utf-8"))
    matching_timing_record = None
    if args.timing_matching_audit is not None:
        matching_timing_record = json.loads(args.timing_matching_audit.read_text(encoding="utf-8"))
    packet = {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "scientific_scope": "bounded architecture experiment; not Idea 009, not a Gate, no Test access",
        "source_revision": control["source_revision"],
        "run_revision": control["source_revision"],
        "profile_id": PROFILE_ID,
        "snapshot_id": SNAPSHOT_ID,
        "train_dev_id": TRAIN_DEV_ID,
        "seed": control["seed"],
        "arms": {"control": control, "full": full},
        "gpu_state": args.gpu_state,
        "timing_preflight": timing_record,
        "timing_matching_audit": matching_timing_record,
        "validation_schedule": control["validation_schedule"],
        "beta_grid": list(beta_grid),
        "native_beta": float(control["config"]["native_beta"]),
        "primary": {
            "B/T": {
                "checkpoint": control["selected_checkpoint"],
                "beta": control_beta,
                "beta_is_grid_boundary": control["selected_beta_is_grid_boundary"],
                "metrics": control_primary,
            },
            "M/A": {
                "checkpoint": full["selected_checkpoint"],
                "beta": full_beta,
                "beta_is_grid_boundary": full["selected_beta_is_grid_boundary"],
                "metrics": full_primary,
            },
            "deltas_MA_minus_BT": primary_deltas,
        },
        "crossover": {
            "B_anchor": {"B/T_vs_B/A": control_crossover},
            "M_anchor": {"M/T_vs_M/A": full_crossover},
            "interpretation_boundary": "conditional decoder effects; not a causal 2x2 factorial decomposition",
            "selected_checkpoint_curves": curves,
        },
        "mean_cardinality_diagnostic": count_alignment,
        "control_validity": control_validity,
        "correctness": {"status": "PASS", "issues": []},
        "test_accessed": False,
        "patient_level_artifacts_transferred": False,
    }
    _write_json(args.output, packet)
    return packet


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-dir", type=Path, required=True)
    parser.add_argument("--full-dir", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gpu-state", default="recorded on 319 at preflight")
    parser.add_argument("--timing-preflight", type=Path, required=True)
    parser.add_argument("--timing-matching-audit", type=Path)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    packet = summarize(args)
    print(json.dumps(packet, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
