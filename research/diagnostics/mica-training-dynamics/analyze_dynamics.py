#!/usr/bin/env python3
"""Build public-safe MICA training-dynamics diagnostics from aggregate progress.

The input directory is intentionally separate from the repository in normal use:
it contains only aggregate ``progress.json`` records copied from the 319
execution plane.  No patient-level arrays, logits, checkpoints, or raw logs are
read by this script.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

TRAIN_VISITS = 10_489
BATCH_SIZE = 16
UPDATES_PER_EPOCH = math.ceil(TRAIN_VISITS / BATCH_SIZE)

ARM_METADATA: dict[str, dict[str, str]] = {
    "shared_pool": {"family": "mica", "label": "SharedPool", "revision": "cd731bb"},
    "drug_query": {"family": "mica", "label": "DrugQuery", "revision": "cd731bb"},
    "mica_late": {"family": "mica", "label": "MICA-Late", "revision": "cd731bb"},
    "v2_core": {"family": "mica-v2", "label": "Core", "revision": "9aba7ba"},
    "fine_history": {"family": "mica-v2", "label": "FineHistory", "revision": "9aba7ba"},
    "dual_evidence": {"family": "mica-v2", "label": "DualEvidence", "revision": "9aba7ba"},
    "self_only": {"family": "mica-v2", "label": "SelfOnly", "revision": "9aba7ba"},
    "set_context": {"family": "mica-v2", "label": "SetContext", "revision": "9aba7ba"},
    "safe_rank": {"family": "mica-v2", "label": "SafeRank", "revision": "6d8d3fd"},
    "dynamic_core": {"family": "dynamic-query", "label": "Core", "revision": "5083cdb"},
    "static_multiquery": {
        "family": "dynamic-query",
        "label": "StaticMultiQuery",
        "revision": "5083cdb",
    },
    "global_dynamic_multiquery": {
        "family": "dynamic-query",
        "label": "GlobalDynamicMultiQuery",
        "revision": "5083cdb",
    },
    "evidence_dynamic_multiquery": {
        "family": "dynamic-query",
        "label": "EvidenceDynamicMultiQuery",
        "revision": "5083cdb",
    },
    "static_query_adapter": {
        "family": "dynamic-query",
        "label": "StaticQueryAdapter",
        "revision": "5083cdb",
    },
    "dynamic_query_adapter": {
        "family": "dynamic-query",
        "label": "DynamicQueryAdapter",
        "revision": "5083cdb",
    },
}

MISSING_PROGRESS = {
    "v2_safe_pto": {
        "family": "mica-v2",
        "label": "SafePTO",
        "reason": "public aggregate result exists, but no epoch-level progress artifact was available",
        "source": "research/prototypes/mica-v2-screen/result.json",
    }
}

BASELINE_METADATA = {
    "MoleRec": {
        "total_epochs": 50,
        "train_patients": 4233,
        "approx_updates_per_epoch": 4233,
        "optimizer": "Adam",
        "learning_rate": 5e-4,
        "scheduler": "none observed",
        "logged_best_epoch_index": 44,
        "logged_best_epoch_human": 45,
        "checkpoint_rule": "strict native validation Jaccard on data_eval; checkpoint per epoch",
    },
    "GAMENet": {
        "total_epochs": 50,
        "train_patients": 4233,
        "approx_updates_per_epoch": 4233,
        "optimizer": "Adam",
        "learning_rate": 5e-4,
        "scheduler": "none observed",
        "logged_best_epoch_index": 48,
        "logged_best_epoch_human": 49,
        "checkpoint_rule": "strict native validation Jaccard on data_eval; checkpoint per epoch",
    },
    "RETAIN": {
        "total_epochs": 50,
        "train_patients": 4233,
        "approx_updates_per_epoch": 4233,
        "optimizer": "Adam",
        "learning_rate": 5e-4,
        "scheduler": "none observed",
        "logged_best_epoch_index": 49,
        "logged_best_epoch_human": 50,
        "checkpoint_rule": "strict native validation Jaccard on data_eval; checkpoint per epoch",
    },
    "SafeDrug": {
        "total_epochs": 50,
        "train_patients": 4233,
        "approx_updates_per_epoch": 4233,
        "optimizer": "Adam",
        "learning_rate": 5e-4,
        "scheduler": "none observed",
        "logged_best_epoch_index": 29,
        "logged_best_epoch_human": 30,
        "checkpoint_rule": "strict native validation Jaccard on data_eval; checkpoint per epoch",
    },
}

METRIC_KEYS = ("jaccard", "prauc", "nll", "f1")
TRAIN_KEYS = ("train_loss", "train_bce", "train_ddi")


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _read_progress(input_dir: Path, arm: str) -> dict[str, Any]:
    path = input_dir / f"{arm}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    epochs = payload.get("epochs")
    if not isinstance(epochs, list) or len(epochs) != 60:
        raise ValueError(f"{arm}: expected exactly 60 aggregate epochs")
    normalized: list[dict[str, Any]] = []
    for expected_epoch, entry in enumerate(epochs, start=1):
        if not isinstance(entry, dict) or entry.get("epoch") != expected_epoch:
            raise ValueError(f"{arm}: epoch sequence is not 1..60")
        row = {key: _finite(entry[key], f"{arm}.{key}") for key in TRAIN_KEYS}
        metrics = entry.get("dev_metrics")
        if not isinstance(metrics, dict):
            raise ValueError(f"{arm}: missing dev_metrics")
        row["epoch"] = expected_epoch
        row["dev"] = {key: _finite(metrics[key], f"{arm}.dev.{key}") for key in METRIC_KEYS}
        normalized.append(row)
    return {
        "status": payload.get("status"),
        "variant": payload.get("variant"),
        "source_revision": payload.get("source_revision"),
        "epochs": normalized,
    }


def _argmax(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    return max(rows, key=lambda row: row["dev"][metric])


def _argmin(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    return min(rows, key=lambda row: row["dev"][metric])


def _summary(arm: str, payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload["epochs"]
    best_j = _argmax(rows, "jaccard")
    best_nll = _argmin(rows, "nll")
    best_prauc = _argmax(rows, "prauc")
    epoch_60 = rows[-1]
    bce = [row["train_bce"] for row in rows]
    total = [row["train_loss"] for row in rows]
    bce_diffs = [bce[index] - bce[index - 1] for index in range(1, len(bce))]
    total_diffs = [total[index] - total[index - 1] for index in range(1, len(total))]
    late_slope = (bce[-1] - bce[9]) / 50.0
    return {
        "arm": arm,
        "label": ARM_METADATA[arm]["label"],
        "family": ARM_METADATA[arm]["family"],
        "source_revision": payload["source_revision"],
        "status": payload["status"],
        "completed_epochs": len(rows),
        "updates_per_epoch": UPDATES_PER_EPOCH,
        "best_jaccard": {
            "epoch": best_j["epoch"],
            "optimizer_updates": best_j["epoch"] * UPDATES_PER_EPOCH,
            "value": best_j["dev"]["jaccard"],
        },
        "best_nll": {"epoch": best_nll["epoch"], "value": best_nll["dev"]["nll"]},
        "best_prauc": {"epoch": best_prauc["epoch"], "value": best_prauc["dev"]["prauc"]},
        "epoch_60": {
            "jaccard": epoch_60["dev"]["jaccard"],
            "prauc": epoch_60["dev"]["prauc"],
            "nll": epoch_60["dev"]["nll"],
            "f1": epoch_60["dev"]["f1"],
            "train_loss": epoch_60["train_loss"],
            "train_bce": epoch_60["train_bce"],
            "train_ddi": epoch_60["train_ddi"],
        },
        "drops": {
            "jaccard": best_j["dev"]["jaccard"] - epoch_60["dev"]["jaccard"],
            "prauc": best_prauc["dev"]["prauc"] - epoch_60["dev"]["prauc"],
            "nll_drift": epoch_60["dev"]["nll"] - best_nll["dev"]["nll"],
        },
        "train_dynamics": {
            "bce_epoch_1": bce[0],
            "bce_epoch_3": bce[2],
            "bce_epoch_10": bce[9],
            "bce_epoch_20": bce[19],
            "bce_epoch_60": bce[-1],
            "bce_decreasing_steps": sum(diff < 0 for diff in bce_diffs),
            "bce_steps": len(bce_diffs),
            "total_loss_decreasing_steps": sum(diff < 0 for diff in total_diffs),
            "total_loss_steps": len(total_diffs),
            "late_bce_slope_per_epoch_10_to_60": late_slope,
            "max_total_loss_increase": max(total_diffs),
        },
    }


def _diagnosis(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    # The observed rule is deliberately conservative: classify as overfit only
    # when the train objective keeps falling while all arms' selected metric
    # surfaces lose materially at the final epoch.  A tiny one-step increase is
    # treated as minibatch noise, not optimization drift.
    overfit_arms = [
        summary
        for summary in summaries
        if summary["drops"]["jaccard"] > 0.01
        and summary["drops"]["prauc"] > 0.01
        and summary["drops"]["nll_drift"] > 0.1
        and summary["train_dynamics"]["bce_decreasing_steps"]
        >= 0.95 * summary["train_dynamics"]["bce_steps"]
    ]
    drift_arms = [
        summary
        for summary in summaries
        if summary["train_dynamics"]["max_total_loss_increase"] > 0.001
    ]
    peak_epochs = [summary["best_jaccard"]["epoch"] for summary in summaries]
    peak_3_or_4 = sum(epoch in (3, 4) for epoch in peak_epochs)
    if len(overfit_arms) == len(summaries) and not drift_arms:
        classification = "OVERFIT_DOMINANT"
    elif drift_arms:
        classification = "OPTIMIZATION_DRIFT"
    elif peak_3_or_4 == len(summaries):
        classification = "RAPID_FIT_LATE_MEMORIZATION"
    else:
        classification = "INCONCLUSIVE"
    return {
        "classification": classification,
        "rule": {
            "overfit_dominant": "train BCE keeps decreasing while Dev NLL rises and Dev Jaccard/PRAUC fall",
            "optimization_drift": "late train total loss has a material increase (threshold 0.001 per epoch)",
            "rapid_fit_late_memorization": "all arms peak at epoch 3 or 4 after rapid early fit",
        },
        "arms_with_overfit_pattern": [summary["arm"] for summary in overfit_arms],
        "arms_with_material_train_drift": [summary["arm"] for summary in drift_arms],
        "peak_epoch_counts": {
            str(epoch): peak_epochs.count(epoch) for epoch in sorted(set(peak_epochs))
        },
        "all_family_peak_in_3_or_4": peak_3_or_4 == len(summaries),
        "interpretation": (
            "Train BCE and total loss continue to fall while Dev metrics degrade after epoch 3-4; "
            "the shared recipe/encoder dynamics dominate the late failure. The evidence does not "
            "isolate DrugQuery, v2, or dynamic-query as the cause."
            if classification == "OVERFIT_DOMINANT"
            else "The observed curves do not satisfy a single high-confidence diagnosis rule."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summaries = []
    curves: list[dict[str, Any]] = []
    for arm in ARM_METADATA:
        payload = _read_progress(args.input_dir, arm)
        summaries.append(_summary(arm, payload))
        for row in payload["epochs"]:
            curves.append(
                {
                    "family": ARM_METADATA[arm]["family"],
                    "arm": ARM_METADATA[arm]["label"],
                    "source_revision": payload["source_revision"],
                    "epoch": row["epoch"],
                    "optimizer_updates": row["epoch"] * UPDATES_PER_EPOCH,
                    "train_total_loss": row["train_loss"],
                    "train_bce": row["train_bce"],
                    "train_ddi": row["train_ddi"],
                    "dev_jaccard": row["dev"]["jaccard"],
                    "dev_f1": row["dev"]["f1"],
                    "dev_prauc": row["dev"]["prauc"],
                    "dev_nll": row["dev"]["nll"],
                }
            )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "learning_curves.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        fields = list(curves[0])
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(curves)
    diagnosis = {
        "schema_version": 1,
        "status": "complete",
        "stage": "STAGE -1A",
        "evidence_class": "aggregate_progress_only",
        "historical_baselines": BASELINE_METADATA,
        "data_contract": {
            "train_visits": TRAIN_VISITS,
            "batch_size": BATCH_SIZE,
            "updates_per_epoch": UPDATES_PER_EPOCH,
            "epoch_3_updates": 3 * UPDATES_PER_EPOCH,
            "epoch_4_updates": 4 * UPDATES_PER_EPOCH,
            "epoch_60_updates": 60 * UPDATES_PER_EPOCH,
            "metrics": [
                "train_loss",
                "train_bce",
                "train_ddi",
                "dev_jaccard",
                "dev_prauc",
                "dev_nll",
                "dev_f1",
            ],
        },
        "training_diagnosis": _diagnosis(summaries),
        "arms": summaries,
        "missing_or_not_used": [
            "Raw logs, patient IDs, logits, targets, checkpoints, and private paths were not read or copied.",
            "Baseline progress is summarized separately because its source logs use different evaluation semantics.",
        ],
        "missing_progress": MISSING_PROGRESS,
    }
    (args.output_dir / "diagnosis.json").write_text(
        json.dumps(diagnosis, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
