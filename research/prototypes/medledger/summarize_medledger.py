#!/usr/bin/env python3
"""Summarize MedLedger vs NormalizedLedger mechanism screen results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

PRIMARY_METRICS = {
    "jaccard": "delta_jaccard",
    "f1": "delta_f1",
    "prauc": "delta_prauc",
    "ddi_rate": "delta_ddi_rate",
    "average_medication_count": "delta_avg_med",
}


def _read(path: Path, variant: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "complete" or value.get("variant") != variant:
        raise ValueError(f"{path} is not a complete {variant} result")
    if value.get("source_bound_references", {}).get("test_accessed") is not False:
        raise ValueError(f"{path} does not prove that Test stayed sealed")
    return value


def _count_matched_evaluation(
    medledger_dir: Path,
    normalized_dir: Path,
    medledger_avg_med: float,
) -> dict[str, Any]:
    """Find threshold for NormalizedLedger that best matches MedLedger's AvgMed."""
    npz_path = normalized_dir / "selected_predictions.npz"
    if not npz_path.is_file():
        return {"status": "predictions_npz_missing"}

    data = np.load(npz_path)
    dev_logits = data["dev_logits"]
    dev_targets = data["dev_targets"]
    dev_probs = 1.0 / (1.0 + np.exp(-dev_logits.astype(np.float64)))

    # Coarse to fine search for threshold matching medledger_avg_med
    best_diff = float("inf")
    best_threshold = 0.35
    best_avg_med = 0.0
    best_jaccard = 0.0

    thresholds = [round(t, 3) for t in np.arange(0.01, 0.99, 0.01)]
    for t in thresholds:
        predicted = dev_probs >= t
        counts = predicted.sum(axis=1)
        # Note: visit-level mean count is a close proxy for patient-macro AvgMed
        mean_count = float(counts.mean())
        diff = abs(mean_count - medledger_avg_med)
        if diff < best_diff:
            best_diff = diff
            best_threshold = t
            best_avg_med = mean_count

            # Approximate visit Jaccard for tracking
            intersection = np.logical_and(predicted, dev_targets > 0.5).sum(axis=1)
            union = np.logical_or(predicted, dev_targets > 0.5).sum(axis=1)
            both_empty = union == 0
            jaccards = np.where(
                both_empty, 1.0, np.where(union > 0, intersection / np.maximum(union, 1), 0.0)
            )
            best_jaccard = float(jaccards.mean())

    return {
        "matched_threshold": best_threshold,
        "matched_predicted_count_mean": best_avg_med,
        "target_count_to_match": medledger_avg_med,
        "absolute_count_difference": best_diff,
        "control_jaccard_at_matched_count": best_jaccard,
    }


def summarize(medledger_path: Path, normalized_path: Path) -> dict[str, Any]:
    medledger = _read(medledger_path, "medledger")
    normalized = _read(normalized_path, "normalized")

    if medledger.get("source_revision") != normalized.get("source_revision"):
        raise ValueError("medledger and normalized source revisions differ")
    if medledger.get("parameter_count") != normalized.get("parameter_count"):
        raise ValueError("medledger and normalized parameter counts differ")
    if medledger.get("config", {}).get("seed") != normalized.get("config", {}).get("seed"):
        raise ValueError("medledger and normalized seeds differ")

    full_metrics = medledger["selected_checkpoint"]["Dev"]
    ctrl_metrics = normalized["selected_checkpoint"]["Dev"]

    deltas = {
        output_name: float(full_metrics[input_name] - ctrl_metrics[input_name])
        for input_name, output_name in PRIMARY_METRICS.items()
    }
    delta_j = deltas["delta_jaccard"]

    # Frozen Decision Rule:
    # delta_j <= +0.002: KILL
    # +0.002 < delta_j <= +0.004: WEAK
    # delta_j > +0.004: MEANINGFUL
    # delta_j >= +0.008: STRONG
    if delta_j <= 0.002:
        decision = "KILL"
        decision_label = (
            "KILL (ΔJ <= +0.002: independent accumulation does not add predictive value)"
        )
    elif delta_j <= 0.004:
        decision = "WEAK"
        decision_label = "WEAK (+0.002 < ΔJ <= +0.004: weak signal, do not promote by default)"
    elif delta_j < 0.008:
        decision = "MEANINGFUL"
        decision_label = "MEANINGFUL (ΔJ > +0.004: meaningful mechanism signal)"
    else:
        decision = "STRONG"
        decision_label = (
            "STRONG (ΔJ >= +0.008: strong enough to reconsider as architecture candidate)"
        )

    # Diagnostics:
    # D1. Multiplicity activation
    full_d1 = medledger.get("diagnostics", {}).get("d1_multiplicity", {})
    ctrl_d1 = normalized.get("diagnostics", {}).get("d1_multiplicity", {})

    d1_comparison = {
        "full_mean_mass_outside_top1": full_d1.get("mean_mass_outside_top1"),
        "ctrl_mean_mass_outside_top1": ctrl_d1.get("mean_mass_outside_top1"),
        "delta_mean_mass_outside_top1": (
            full_d1.get("mean_mass_outside_top1", 0.0) - ctrl_d1.get("mean_mass_outside_top1", 0.0)
        ),
        "full_median_mass_outside_top1": full_d1.get("median_mass_outside_top1"),
        "ctrl_median_mass_outside_top1": ctrl_d1.get("median_mass_outside_top1"),
        "full_effective_evidence_count": full_d1.get("mean_effective_evidence_count"),
        "ctrl_effective_evidence_count": ctrl_d1.get("mean_effective_evidence_count"),
        "full_fraction_multiplicity_gt_0.25": full_d1.get("fraction_multiplicity_gt_0.25"),
        "ctrl_fraction_multiplicity_gt_0.25": ctrl_d1.get("fraction_multiplicity_gt_0.25"),
        "mechanism_activated_in_full": bool(full_d1.get("mean_mass_outside_top1", 0.0) > 0.15),
    }

    # D2. Count sensitivity
    count_matched = _count_matched_evaluation(
        medledger_path.parent,
        normalized_path.parent,
        full_metrics["average_medication_count"],
    )
    d2_comparison = {
        "delta_avg_med": deltas["delta_avg_med"],
        "full_avg_med": full_metrics["average_medication_count"],
        "ctrl_avg_med": ctrl_metrics["average_medication_count"],
        "count_matched_control": count_matched,
    }

    # D3. Ranking quality
    d3_comparison = {
        "full_prauc": full_metrics["prauc"],
        "ctrl_prauc": ctrl_metrics["prauc"],
        "delta_prauc": deltas["delta_prauc"],
        "prauc_preserved_or_improved": bool(deltas["delta_prauc"] >= -0.002),
    }

    return {
        "schema_version": 1,
        "status": "complete",
        "comparison": "medledger_minus_normalized",
        "source_revision": medledger["source_revision"],
        "parameter_count": medledger["parameter_count"],
        "seed": medledger["config"]["seed"],
        "medledger": {
            "selected_epoch": medledger["selected_epoch"],
            "selected_threshold": medledger["selected_threshold"],
            "metrics": full_metrics,
            "d1_multiplicity": full_d1,
            "wall_time_seconds": medledger.get("wall_time_seconds"),
            "cuda_peak_memory_mb": medledger.get("cuda_peak_memory_mb"),
        },
        "normalized": {
            "selected_epoch": normalized["selected_epoch"],
            "selected_threshold": normalized["selected_threshold"],
            "metrics": ctrl_metrics,
            "d1_multiplicity": ctrl_d1,
            "wall_time_seconds": normalized.get("wall_time_seconds"),
            "cuda_peak_memory_mb": normalized.get("cuda_peak_memory_mb"),
        },
        "deltas": deltas,
        "diagnostics": {
            "d1_multiplicity_activation": d1_comparison,
            "d2_count_sensitivity": d2_comparison,
            "d3_ranking_quality": d3_comparison,
        },
        "decision": decision,
        "decision_label": decision_label,
        "test_accessed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--medledger", type=Path, required=True)
    parser.add_argument("--normalized", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = summarize(args.medledger, args.normalized)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
