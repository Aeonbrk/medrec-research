#!/usr/bin/env python3
"""Compute development-only paired patient-cluster bootstrap aggregates.

The script is intended for the private execution plane.  It reads visit-level
targets/logits from a completed external lane and the frozen Stage -1F MICA
lane, then writes only aggregate metrics and percentile intervals.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def _metrics(target: np.ndarray, logits: np.ndarray, ddi: np.ndarray, threshold: float):
    target = np.asarray(target, dtype=np.float32)
    logits = np.asarray(logits, dtype=np.float32)
    score = 1.0 / (1.0 + np.exp(-logits))
    pred = score >= float(threshold)
    truth = target > 0.5
    intersection = np.logical_and(truth, pred).sum(1)
    union = np.logical_or(truth, pred).sum(1)
    target_count = truth.sum(1)
    pred_count = pred.sum(1)
    precision = np.divide(
        intersection,
        pred_count,
        out=np.zeros_like(intersection, dtype=np.float64),
        where=pred_count != 0,
    )
    recall = np.divide(
        intersection,
        target_count,
        out=np.zeros_like(intersection, dtype=np.float64),
        where=target_count != 0,
    )
    f1 = np.divide(
        2.0 * precision * recall,
        precision + recall,
        out=np.zeros_like(precision),
        where=(precision + recall) != 0,
    )
    jaccard = np.divide(
        intersection,
        union,
        out=np.zeros_like(intersection, dtype=np.float64),
        where=union != 0,
    )
    order = np.argsort(-score, axis=1, kind="stable")
    ranked = np.take_along_axis(truth, order, axis=1)
    cumulative = np.cumsum(ranked, axis=1)
    ranks = np.arange(1, score.shape[1] + 1, dtype=np.float64)[None, :]
    ap_num = (cumulative / ranks * ranked).sum(1)
    prauc = np.divide(
        ap_num,
        target_count,
        out=np.zeros_like(ap_num),
        where=target_count != 0,
    )
    edges = np.argwhere(np.triu(np.asarray(ddi) > 0.5, k=1))
    ddi_pairs = np.zeros(pred.shape[0], dtype=np.float64)
    for left, right in edges:
        ddi_pairs += pred[:, int(left)] & pred[:, int(right)]
    pair_total = pred_count.astype(np.float64) * (pred_count - 1.0) / 2.0
    nll = np.maximum(logits, 0.0) - logits * target + np.logaddexp(0.0, -np.abs(logits))
    return {
        "jaccard": jaccard,
        "f1": f1,
        "prauc": prauc,
        "ddi_pairs": ddi_pairs,
        "pair_total": pair_total,
        "pred_count": pred_count.astype(np.float64),
        "nll": nll.mean(1),
    }


def _aggregate(per_visit: dict[str, np.ndarray], indices: np.ndarray) -> dict[str, float]:
    def mean(name: str) -> float:
        return float(per_visit[name][indices].mean())

    pairs = float(per_visit["ddi_pairs"][indices].sum())
    total = float(per_visit["pair_total"][indices].sum())
    return {
        "jaccard": mean("jaccard"),
        "f1": mean("f1"),
        "prauc": mean("prauc"),
        "ddi_rate": pairs / total if total else 0.0,
        "mean_medication_count": mean("pred_count"),
        "nll": mean("nll"),
        "visit_count": float(indices.size),
    }


def _patient_summaries(
    per_visit: dict[str, np.ndarray], patient_keys: np.ndarray
) -> tuple[list[str], dict[str, dict[str, np.ndarray]]]:
    keys = np.asarray(patient_keys).astype(str)
    unique, inverse = np.unique(keys, return_inverse=True)
    summary: dict[str, dict[str, np.ndarray]] = {}
    for name, values in per_visit.items():
        if name in {"jaccard", "f1", "prauc", "pred_count", "nll"}:
            sums = np.bincount(inverse, weights=values, minlength=unique.size)
        else:
            sums = np.bincount(inverse, weights=values, minlength=unique.size)
        summary[name] = sums
    summary["visits"] = np.bincount(inverse, minlength=unique.size).astype(np.float64)
    return [str(value) for value in unique], summary


def _bootstrap_delta(
    mica: dict[str, np.ndarray],
    baseline: dict[str, np.ndarray],
    patient_keys: np.ndarray,
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    keys, mica_by_patient = _patient_summaries(mica, patient_keys)
    _baseline_keys, baseline_by_patient = _patient_summaries(baseline, patient_keys)
    if keys != _baseline_keys:
        raise RuntimeError("MICA and baseline patient cluster identities do not align")
    rng = np.random.RandomState(seed)
    n_patients = len(keys)
    deltas = {name: np.empty(resamples, dtype=np.float64) for name in ("jaccard", "f1", "ddi_rate")}
    for draw in range(resamples):
        selected = rng.randint(0, n_patients, size=n_patients)
        visit_count = float(mica_by_patient["visits"][selected].sum())
        if visit_count <= 0:
            raise RuntimeError("empty bootstrap sample")
        for name in ("jaccard", "f1"):
            mica_value = float(mica_by_patient[name][selected].sum() / visit_count)
            base_value = float(baseline_by_patient[name][selected].sum() / visit_count)
            deltas[name][draw] = mica_value - base_value
        mica_pairs = float(mica_by_patient["ddi_pairs"][selected].sum())
        base_pairs = float(baseline_by_patient["ddi_pairs"][selected].sum())
        mica_total = float(mica_by_patient["pair_total"][selected].sum())
        base_total = float(baseline_by_patient["pair_total"][selected].sum())
        deltas["ddi_rate"][draw] = (mica_pairs / mica_total if mica_total else 0.0) - (
            base_pairs / base_total if base_total else 0.0
        )
    return {
        "cluster_unit": "patient",
        "patient_count": n_patients,
        "resamples": int(resamples),
        "seed": int(seed),
        "delta_definition": "MICA DrugQuery minus strongest qualified external baseline",
        "point": {
            "jaccard": float(
                _aggregate(mica, np.arange(len(patient_keys)))["jaccard"]
                - _aggregate(baseline, np.arange(len(patient_keys)))["jaccard"]
            ),
            "f1": float(
                _aggregate(mica, np.arange(len(patient_keys)))["f1"]
                - _aggregate(baseline, np.arange(len(patient_keys)))["f1"]
            ),
            "ddi_rate": float(
                _aggregate(mica, np.arange(len(patient_keys)))["ddi_rate"]
                - _aggregate(baseline, np.arange(len(patient_keys)))["ddi_rate"]
            ),
        },
        "percentile_95_ci": {
            name: [float(value) for value in np.percentile(values, [2.5, 97.5])]
            for name, values in deltas.items()
        },
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=("mimic_iii", "mimic_iv"), required=True)
    parser.add_argument("--mica-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--ddi", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260916)
    args = parser.parse_args()
    baseline_result = _load_json(args.baseline_dir / "result.json")
    baseline_threshold = float(baseline_result["config"]["threshold"])
    mica_threshold = 0.35
    target = np.asarray(np.load(args.targets), dtype=np.float32)
    mica_logits = np.asarray(np.load(args.mica_dir / "selected_dev_logits.npy"), dtype=np.float32)
    baseline_logits = np.asarray(np.load(args.baseline_dir / "dev_logits.npy"), dtype=np.float32)
    patient_keys = np.asarray(np.load(args.baseline_dir / "dev_patient_keys.npy"))
    if mica_logits.shape != baseline_logits.shape or target.shape != baseline_logits.shape:
        raise RuntimeError(
            f"visit-aligned arrays differ: target={target.shape} mica={mica_logits.shape} baseline={baseline_logits.shape}"
        )
    ddi = np.asarray(np.load(args.ddi), dtype=np.float32)
    mica_per_visit = _metrics(target, mica_logits, ddi, mica_threshold)
    baseline_per_visit = _metrics(target, baseline_logits, ddi, baseline_threshold)
    full_indices = np.arange(target.shape[0])
    aggregate = {
        "dataset": args.dataset,
        "mica": _aggregate(mica_per_visit, full_indices),
        "baseline": _aggregate(baseline_per_visit, full_indices),
        "bootstrap": _bootstrap_delta(
            mica_per_visit, baseline_per_visit, patient_keys, args.resamples, args.seed
        ),
    }
    args.output.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
