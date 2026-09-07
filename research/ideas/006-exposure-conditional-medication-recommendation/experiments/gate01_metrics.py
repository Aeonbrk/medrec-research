"""Idea 006 Gate 01: Metrics and Paired Patient-Clustered Bootstrap.

SSOT: research/ideas/006-exposure-conditional-medication-recommendation/experiments/gate-01-exposure-conditioned-learning.md
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score


def compute_burst_metrics_single(
    selected: list[int],  # length K
    target_set: set[int],  # positive target medication indices
    active_set: set[int],  # active regimen medication indices
    ddi_matrix: np.ndarray,  # (131, 131) binary symmetric
    k: int,
) -> dict[str, float]:
    """Compute burst-level metrics for a single decision point."""
    k_val = len(selected)
    assert k_val == k, f"Expected {k} selections, got {k_val}"

    # Fidelity: Recall@K
    target_count = len(target_set)
    hits = sum(1 for m in selected if m in target_set)
    recall = hits / target_count if target_count > 0 else 0.0
    hit = 1.0 if hits > 0 else 0.0

    # NDCG@K
    dcg = 0.0
    for r, m in enumerate(selected, start=1):
        if m in target_set:
            dcg += 1.0 / math.log2(r + 1)
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, min(k, target_count) + 1))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    # Safety: DDI metrics
    a_size = len(active_set)

    # Active DDI edges
    active_edges = sum(1 for m in selected for a in active_set if ddi_matrix[m, a] == 1)

    # New DDI edges
    new_edges = 0
    for i in range(k_val):
        for j in range(i + 1, k_val):
            if ddi_matrix[selected[i], selected[j]] == 1:
                new_edges += 1

    # ActiveDDI@K: active_edges / (K * |A_t|)
    active_ddi = (active_edges / (k_val * a_size)) if a_size > 0 else 0.0

    # NewDDI@K: new_edges / (K * (K - 1) / 2)
    new_denom = k_val * (k_val - 1) / 2.0
    new_ddi = new_edges / new_denom if new_denom > 0 else 0.0

    # IncrementalExposureDDI@K: (active_edges + new_edges) / (K * |A_t| + K * (K - 1) / 2)
    total_denom = k_val * a_size + new_denom
    inc_exposure_ddi = (active_edges + new_edges) / total_denom if total_denom > 0 else 0.0

    return {
        "recall": float(recall),
        "hit": float(hit),
        "ndcg": float(ndcg),
        "incremental_exposure_ddi": float(inc_exposure_ddi),
        "active_ddi": float(active_ddi),
        "new_ddi": float(new_ddi),
        "active_edges": int(active_edges),
        "new_edges": int(new_edges),
    }


def compute_mrr_single(ranked_all_indices: list[int], target_set: set[int]) -> float:
    """Compute Reciprocal Rank of the first true target medication."""
    for rank, m in enumerate(ranked_all_indices, start=1):
        if m in target_set:
            return 1.0 / rank
    return 0.0


def evaluate_method_on_universe(
    burst_records: list[dict[str, Any]],  # list of burst metadata dicts
    selected_lists: list[list[int]],  # parallel list of K selections
    ddi_matrix: np.ndarray,
    k: int = 5,
    ranked_all_lists: list[list[int]] | None = None,
    predicted_probs: np.ndarray | None = None,  # (N, 131)
    target_matrix: np.ndarray | None = None,  # (N, 131)
) -> dict[str, Any]:
    """Evaluate aggregate metrics across bursts in universe Q."""
    n_bursts = len(burst_records)
    assert len(selected_lists) == n_bursts

    recalls = []
    hits = []
    ndcgs = []
    inc_ddis = []
    act_ddis = []
    new_ddis = []
    mrrs = []

    for i in range(n_bursts):
        target_set = set(burst_records[i]["target_indices"])
        active_set = set(burst_records[i]["active_indices"])
        sel = selected_lists[i]

        m = compute_burst_metrics_single(sel, target_set, active_set, ddi_matrix, k=k)
        recalls.append(m["recall"])
        hits.append(m["hit"])
        ndcgs.append(m["ndcg"])
        inc_ddis.append(m["incremental_exposure_ddi"])
        act_ddis.append(m["active_ddi"])
        new_ddis.append(m["new_ddi"])

        if ranked_all_lists is not None:
            mrrs.append(compute_mrr_single(ranked_all_lists[i], target_set))

    results: dict[str, Any] = {
        f"Recall@{k}": float(np.mean(recalls)),
        f"IncrementalExposureDDI@{k}": float(np.mean(inc_ddis)),
        f"ActiveDDI@{k}": float(np.mean(act_ddis)),
        f"NewDDI@{k}": float(np.mean(new_ddis)),
        f"NDCG@{k}": float(np.mean(ndcgs)),
        f"Hit@{k}": float(np.mean(hits)),
        "n_bursts": n_bursts,
        # Raw arrays for bootstrapping
        "_raw_recall": np.array(recalls, dtype=np.float64),
        "_raw_inc_ddi": np.array(inc_ddis, dtype=np.float64),
        "_raw_active_ddi": np.array(act_ddis, dtype=np.float64),
        "_raw_new_ddi": np.array(new_ddis, dtype=np.float64),
        "_raw_ndcg": np.array(ndcgs, dtype=np.float64),
        "_raw_hit": np.array(hits, dtype=np.float64),
    }

    if mrrs:
        results["MRR"] = float(np.mean(mrrs))
        results["_raw_mrr"] = np.array(mrrs, dtype=np.float64)

    if predicted_probs is not None and target_matrix is not None:
        y_true_flat = target_matrix.ravel()
        y_pred_flat = predicted_probs.ravel()
        results["micro_PRAUC"] = float(
            average_precision_score(y_true_flat, y_pred_flat, average="micro")
        )

    return results


def patient_clustered_paired_bootstrap(
    patient_ids: list[Any],  # patient ID for each burst
    method_raw_metrics: dict[
        str, dict[str, np.ndarray]
    ],  # method_name -> {"recall": arr, "inc_ddi": arr}
    replicates: int = 2000,
    seed: int = 260907,
) -> dict[str, Any]:
    """Execute paired patient-clustered bootstrap across all evaluated methods."""
    rng = np.random.default_rng(seed)

    unique_patients, inverse_p = np.unique(patient_ids, return_inverse=True)
    n_patients = len(unique_patients)
    patient_counts = np.bincount(inverse_p, minlength=n_patients).astype(np.float64)

    method_names = list(method_raw_metrics.keys())

    # Pre-aggregate metric sums per unique patient
    preagg: dict[str, dict[str, np.ndarray]] = {}
    for m_name in method_names:
        preagg[m_name] = {}
        for metric_key, raw_arr in method_raw_metrics[m_name].items():
            preagg[m_name][metric_key] = np.bincount(
                inverse_p, weights=np.asarray(raw_arr, dtype=np.float64), minlength=n_patients
            )

    # Resample patients with replacement
    samples = rng.choice(n_patients, size=(replicates, n_patients), replace=True)

    # Frequency matrix C: shape (replicates, n_patients)
    C = np.zeros((replicates, n_patients), dtype=np.float64)
    for r in range(replicates):
        np.add.at(C[r], samples[r], 1.0)

    # Total sample burst counts per replicate: shape (replicates,)
    total_n = C @ patient_counts

    boot_means: dict[str, dict[str, np.ndarray]] = {m: {} for m in method_names}
    for m_name in method_names:
        for metric_key in method_raw_metrics[m_name]:
            rep_sums = C @ preagg[m_name][metric_key]
            boot_means[m_name][metric_key] = rep_sums / total_n

    # Compute 95% percentile CIs [2.5, 97.5]
    summary_cis: dict[str, Any] = {"methods": {}, "deltas": {}}

    for m_name in method_names:
        summary_cis["methods"][m_name] = {}
        for metric_key, val_arr in boot_means[m_name].items():
            summary_cis["methods"][m_name][metric_key] = {
                "mean": float(np.mean(val_arr)),
                "std": float(np.std(val_arr)),
                "ci_95": [
                    float(np.percentile(val_arr, 2.5)),
                    float(np.percentile(val_arr, 97.5)),
                ],
            }

    if "ExposureConditional" in method_names and "Base" in method_names:
        delta_risk = boot_means["ExposureConditional"]["inc_ddi"] - boot_means["Base"]["inc_ddi"]
        delta_recall = boot_means["ExposureConditional"]["recall"] - boot_means["Base"]["recall"]
        summary_cis["deltas"]["EC_vs_Base"] = {
            "risk_delta": {
                "mean": float(np.mean(delta_risk)),
                "ci_95": [
                    float(np.percentile(delta_risk, 2.5)),
                    float(np.percentile(delta_risk, 97.5)),
                ],
            },
            "recall_delta": {
                "mean": float(np.mean(delta_recall)),
                "ci_95": [
                    float(np.percentile(delta_recall, 2.5)),
                    float(np.percentile(delta_recall, 97.5)),
                ],
            },
        }

    if "ExposureConditional" in method_names and "DirectExposureRerank" in method_names:
        delta_risk = (
            boot_means["ExposureConditional"]["inc_ddi"]
            - boot_means["DirectExposureRerank"]["inc_ddi"]
        )
        delta_recall = (
            boot_means["ExposureConditional"]["recall"]
            - boot_means["DirectExposureRerank"]["recall"]
        )
        summary_cis["deltas"]["EC_vs_DirectRerank"] = {
            "risk_delta": {
                "mean": float(np.mean(delta_risk)),
                "ci_95": [
                    float(np.percentile(delta_risk, 2.5)),
                    float(np.percentile(delta_risk, 97.5)),
                ],
            },
            "recall_delta": {
                "mean": float(np.mean(delta_recall)),
                "ci_95": [
                    float(np.percentile(delta_recall, 2.5)),
                    float(np.percentile(delta_recall, 97.5)),
                ],
            },
        }

    return summary_cis
