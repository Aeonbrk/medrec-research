#!/usr/bin/env python3
"""B0 — Cardinality Attribution Premise Audit Runner.

Evaluates the diagnostic impact of restoring ground-truth medication cardinality
under unchanged frozen MoleRec validation score rankings.

Protocol reference: research/premise-audit/README.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

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
FROZEN_VALIDATION_VISIT_COUNT = 1220

BOOTSTRAP_SEED = 260905
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_CI_QUANTILE_LOWER = 0.025
BOOTSTRAP_CI_QUANTILE_UPPER = 0.975

GATE_MIN_UNDERCOUNT_PREVALENCE = 0.20
GATE_MIN_DELTA_F1 = 0.010
GATE_MIN_DELTA_DDI = 0.005


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _percentile(values: list[float], quantile: float) -> float:
    """Matches medrec_research.evaluation._percentile linear interpolation."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def compute_oracle_count_prediction(
    scores: Mapping[str, float],
    target_count: int,
    vocabulary: Iterable[str],
) -> tuple[str, ...]:
    """Select top k_t medications where k_t = |M_t|.

    Score ties are broken deterministically by medication code ascending.
    Ranks across the complete vocabulary.
    """
    if target_count <= 0:
        return ()
    ranked = sorted(vocabulary, key=lambda m: (-float(scores[m]), str(m)))
    return tuple(ranked[:target_count])


def compute_visit_metrics(
    predicted: Iterable[str],
    target: Iterable[str],
    ddi_pairs: frozenset[tuple[str, str]],
) -> dict[str, Any]:
    """Compute all required metrics for a single visit."""
    pred_set = set(predicted)
    tgt_set = set(target)
    med_count = len(pred_set)
    target_count = len(tgt_set)
    count_error = med_count - target_count
    abs_count_error = abs(count_error)

    if not pred_set and not tgt_set:
        jaccard = 1.0
        precision = 1.0
        recall = 1.0
        f1 = 1.0
    elif not pred_set or not tgt_set:
        jaccard = 0.0
        precision = 0.0
        recall = 0.0
        f1 = 0.0
    else:
        intersection = len(pred_set & tgt_set)
        union = len(pred_set | tgt_set)
        jaccard = intersection / union
        precision = intersection / med_count
        recall = intersection / target_count
        f1 = 0.0 if precision + recall == 0.0 else (2.0 * precision * recall) / (precision + recall)

    pred_list = sorted(pred_set)
    pair_count = len(pred_list) * (len(pred_list) - 1) // 2
    ddi_count = 0
    for i, left in enumerate(pred_list):
        for right in pred_list[i + 1 :]:
            if tuple(sorted((left, right))) in ddi_pairs:
                ddi_count += 1
    visit_ddi_rate = 0.0 if pair_count == 0 else ddi_count / pair_count

    return {
        "count": med_count,
        "target_count": target_count,
        "count_error": count_error,
        "abs_count_error": abs_count_error,
        "jaccard": jaccard,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "ddi_pairs_count": ddi_count,
        "predicted_pairs_count": pair_count,
        "visit_ddi_rate": visit_ddi_rate,
    }


def compute_cohort_aggregates(visit_evals: list[dict[str, Any]]) -> dict[str, float]:
    """Compute aggregate point metrics across a visit collection."""
    n = len(visit_evals)
    if n == 0:
        return {
            "count": 0.0,
            "count_error": 0.0,
            "abs_count_error": 0.0,
            "jaccard": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "evaluator_ddi_rate": 0.0,
            "macro_ddi_rate": 0.0,
            "ddi_pairs_per_visit": 0.0,
            "total_ddi_pairs": 0,
            "total_predicted_pairs": 0,
        }

    total_ddi_pairs = sum(v["ddi_pairs_count"] for v in visit_evals)
    total_pred_pairs = sum(v["predicted_pairs_count"] for v in visit_evals)
    evaluator_ddi_rate = 0.0 if total_pred_pairs == 0 else total_ddi_pairs / total_pred_pairs

    return {
        "count": sum(v["count"] for v in visit_evals) / n,
        "count_error": sum(v["count_error"] for v in visit_evals) / n,
        "abs_count_error": sum(v["abs_count_error"] for v in visit_evals) / n,
        "jaccard": sum(v["jaccard"] for v in visit_evals) / n,
        "precision": sum(v["precision"] for v in visit_evals) / n,
        "recall": sum(v["recall"] for v in visit_evals) / n,
        "f1": sum(v["f1"] for v in visit_evals) / n,
        "evaluator_ddi_rate": evaluator_ddi_rate,
        "macro_ddi_rate": sum(v["visit_ddi_rate"] for v in visit_evals) / n,
        "ddi_pairs_per_visit": sum(v["ddi_pairs_count"] for v in visit_evals) / n,
        "total_ddi_pairs": total_ddi_pairs,
        "total_predicted_pairs": total_pred_pairs,
    }


def run_patient_clustered_bootstrap(
    patient_visits: dict[str, list[dict[str, Any]]],
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, dict[str, float]]:
    """Patient-clustered paired bootstrap for 2000 replicates.

    Resamples patients with replacement; all visits of a sampled patient
    are included together.
    """
    sorted_patients = sorted(patient_visits.keys())
    num_patients = len(sorted_patients)
    rng = random.Random(seed)

    replicate_delta_f1: list[float] = []
    replicate_delta_ddi: list[float] = []
    replicate_delta_jaccard: list[float] = []
    replicate_delta_recall: list[float] = []
    replicate_delta_precision: list[float] = []
    replicate_delta_count: list[float] = []
    replicate_delta_ddi_pairs: list[float] = []

    replicate_orig_f1: list[float] = []
    replicate_oc_f1: list[float] = []
    replicate_orig_ddi: list[float] = []
    replicate_oc_ddi: list[float] = []

    for _ in range(replicates):
        sampled_indices = [rng.randrange(num_patients) for _ in range(num_patients)]
        rep_orig_evals: list[dict[str, Any]] = []
        rep_oc_evals: list[dict[str, Any]] = []

        for idx in sampled_indices:
            patient_id = sorted_patients[idx]
            for pair in patient_visits[patient_id]:
                rep_orig_evals.append(pair["orig"])
                rep_oc_evals.append(pair["oc"])

        orig_agg = compute_cohort_aggregates(rep_orig_evals)
        oc_agg = compute_cohort_aggregates(rep_oc_evals)

        replicate_orig_f1.append(orig_agg["f1"])
        replicate_oc_f1.append(oc_agg["f1"])
        replicate_orig_ddi.append(orig_agg["evaluator_ddi_rate"])
        replicate_oc_ddi.append(oc_agg["evaluator_ddi_rate"])

        replicate_delta_f1.append(oc_agg["f1"] - orig_agg["f1"])
        replicate_delta_ddi.append(oc_agg["evaluator_ddi_rate"] - orig_agg["evaluator_ddi_rate"])
        replicate_delta_jaccard.append(oc_agg["jaccard"] - orig_agg["jaccard"])
        replicate_delta_recall.append(oc_agg["recall"] - orig_agg["recall"])
        replicate_delta_precision.append(oc_agg["precision"] - orig_agg["precision"])
        replicate_delta_count.append(oc_agg["count"] - orig_agg["count"])
        replicate_delta_ddi_pairs.append(
            oc_agg["ddi_pairs_per_visit"] - orig_agg["ddi_pairs_per_visit"]
        )

    def _ci(vals: list[float]) -> dict[str, float]:
        return {
            "mean": sum(vals) / len(vals),
            "ci_lower_95": _percentile(vals, BOOTSTRAP_CI_QUANTILE_LOWER),
            "ci_upper_95": _percentile(vals, BOOTSTRAP_CI_QUANTILE_UPPER),
        }

    return {
        "delta_f1": _ci(replicate_delta_f1),
        "delta_ddi": _ci(replicate_delta_ddi),
        "delta_jaccard": _ci(replicate_delta_jaccard),
        "delta_recall": _ci(replicate_delta_recall),
        "delta_precision": _ci(replicate_delta_precision),
        "delta_count": _ci(replicate_delta_count),
        "delta_ddi_pairs_per_visit": _ci(replicate_delta_ddi_pairs),
        "orig_f1": _ci(replicate_orig_f1),
        "oc_f1": _ci(replicate_oc_f1),
        "orig_ddi": _ci(replicate_orig_ddi),
        "oc_ddi": _ci(replicate_oc_ddi),
    }


def evaluate_b0_decision(
    undercount_prevalence: float,
    point_delta_f1: float,
    delta_f1_ci_lower: float,
    point_delta_ddi: float,
    delta_ddi_ci_lower: float,
) -> tuple[str, dict[str, bool]]:
    """Frozen decision rule according to research/premise-audit/README.md."""
    cond1 = undercount_prevalence >= GATE_MIN_UNDERCOUNT_PREVALENCE
    cond2 = (point_delta_f1 >= GATE_MIN_DELTA_F1) and (delta_f1_ci_lower > 0.0)
    cond3 = (point_delta_ddi >= GATE_MIN_DELTA_DDI) and (delta_ddi_ci_lower > 0.0)

    criteria = {
        "condition_1_undercount_at_least_20_percent": cond1,
        "condition_2_delta_f1_ge_0_010_and_ci_positive": cond2,
        "condition_3_delta_ddi_ge_0_005_and_ci_positive": cond3,
    }

    if cond1 and cond2 and cond3:
        verdict = "PASS_B0_MATERIAL_COUNT_SAFETY_TRADEOFF"
    else:
        verdict = "FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF"

    return verdict, criteria


def generate_decision_markdown(
    summary: dict[str, Any],
) -> str:
    """Generate b0-decision.md artifact."""
    verdict = summary["verdict"]
    undercount = summary["count_prevalence"]["undercount_prevalence"]
    delta_f1 = summary["paired_deltas"]["delta_f1"]
    delta_f1_ci = summary["bootstrap_analysis"]["delta_f1"]
    delta_ddi = summary["paired_deltas"]["delta_ddi"]
    delta_ddi_ci = summary["bootstrap_analysis"]["delta_ddi"]
    criteria = summary["decision_criteria"]

    next_state = (
        "ACTIVE_METHOD_INVESTMENT_AUTHORIZED"
        if verdict == "PASS_B0_MATERIAL_COUNT_SAFETY_TRADEOFF"
        else "NO_HIGH_VALUE_DIRECTION_YET"
    )

    next_owner = (
        "ccf-idea-optimizer, then ccf-idea-reviewer"
        if verdict == "PASS_B0_MATERIAL_COUNT_SAFETY_TRADEOFF"
        else "ccf-pipeline-orchestrator"
    )

    pass_fail_summary = (
        "exposes a material count-mediated safety/fidelity trade-off"
        if verdict == "PASS_B0_MATERIAL_COUNT_SAFETY_TRADEOFF"
        else "does not produce the required material count-mediated trade-off"
    )

    return f"""<!-- markdownlint-disable MD013 -->

# B0 — Cardinality Attribution Decision Record

## 1. Scientific Protocol Identity

- **Audit Gate**: `B0 — Cardinality Attribution`
- **Single Source of Truth**: `research/premise-audit/README.md`
- **Backbone Identity**: MoleRec Table 1 Comparison Mode (`dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`)
- **Checkpoint SHA256**: `{FROZEN_CHECKPOINT_SHA256}`
- **Dataset Manifest SHA256**: `{FROZEN_DATASET_MANIFEST_SHA256}`
- **Diagnostic Intervention**: `oracle-count` / TopK(scores, |target|) / diagnostic-only / non-deployable
- **Test Split Isolation**: Untouched (100% test isolation, zero test visits indexed or evaluated)

---

## 2. Quantitative Evidence

### 2.1 Sample Size and Count Distribution

- **Validation Cohort Patients**: {summary["cohort"]["validation_cohort_patient_count"]} ({summary["cohort"]["validation_patient_count"]} patients with $\\ge 1$ eligible visit)
- **Validation Visits**: {summary["cohort"]["validation_visit_count"]}
- **Under-count Prevalence ($|\\hat M_t| < |M_t|$)**: {undercount:.4f} ({undercount * 100:.2f}%)
- **Equal-count Prevalence ($|\\hat M_t| = |M_t|$)**: {summary["count_prevalence"]["equalcount_prevalence"]:.4f} ({summary["count_prevalence"]["equalcount_prevalence"] * 100:.2f}%)
- **Over-count Prevalence ($|\\hat M_t| > |M_t|$)**: {summary["count_prevalence"]["overcount_prevalence"]:.4f} ({summary["count_prevalence"]["overcount_prevalence"] * 100:.2f}%)

### 2.2 Primary Paired Outcomes

| Metric | Original Frozen ($\hat M_t^{{orig}}$) | Oracle-Count Diagnostic ($\hat M_t^{{oc}}$) | Paired Delta | 95% Patient Bootstrap CI |
| :--- | :--- | :--- | :--- | :--- |
| **F1** | {summary["original_metrics"]["f1"]:.4f} | {summary["oracle_count_metrics"]["f1"]:.4f} | {delta_f1:+.4f} | [{delta_f1_ci["ci_lower_95"]:+.4f}, {delta_f1_ci["ci_upper_95"]:+.4f}] |
| **Pair-Normalized DDI Rate** | {summary["original_metrics"]["evaluator_ddi_rate"]:.4f} | {summary["oracle_count_metrics"]["evaluator_ddi_rate"]:.4f} | {delta_ddi:+.4f} | [{delta_ddi_ci["ci_lower_95"]:+.4f}, {delta_ddi_ci["ci_upper_95"]:+.4f}] |

### 2.3 Secondary and Corroborating Outcomes

| Metric | Original Frozen ($\hat M_t^{{orig}}$) | Oracle-Count Diagnostic ($\hat M_t^{{oc}}$) | Paired Delta | 95% Patient Bootstrap CI |
| :--- | :--- | :--- | :--- | :--- |
| **Jaccard** | {summary["original_metrics"]["jaccard"]:.4f} | {summary["oracle_count_metrics"]["jaccard"]:.4f} | {summary["paired_deltas"]["delta_jaccard"]:+.4f} | [{summary["bootstrap_analysis"]["delta_jaccard"]["ci_lower_95"]:+.4f}, {summary["bootstrap_analysis"]["delta_jaccard"]["ci_upper_95"]:+.4f}] |
| **Recall** | {summary["original_metrics"]["recall"]:.4f} | {summary["oracle_count_metrics"]["recall"]:.4f} | {summary["paired_deltas"]["delta_recall"]:+.4f} | [{summary["bootstrap_analysis"]["delta_recall"]["ci_lower_95"]:+.4f}, {summary["bootstrap_analysis"]["delta_recall"]["ci_upper_95"]:+.4f}] |
| **Precision** | {summary["original_metrics"]["precision"]:.4f} | {summary["oracle_count_metrics"]["precision"]:.4f} | {summary["paired_deltas"]["delta_precision"]:+.4f} | [{summary["bootstrap_analysis"]["delta_precision"]["ci_lower_95"]:+.4f}, {summary["bootstrap_analysis"]["delta_precision"]["ci_upper_95"]:+.4f}] |
| **Medication Count** | {summary["original_metrics"]["count"]:.2f} | {summary["oracle_count_metrics"]["count"]:.2f} | {summary["paired_deltas"]["delta_count"]:+.2f} | [{summary["bootstrap_analysis"]["delta_count"]["ci_lower_95"]:+.2f}, {summary["bootstrap_analysis"]["delta_count"]["ci_upper_95"]:+.2f}] |
| **Absolute DDI Pairs / Visit** | {summary["original_metrics"]["ddi_pairs_per_visit"]:.4f} | {summary["oracle_count_metrics"]["ddi_pairs_per_visit"]:.4f} | {summary["paired_deltas"]["delta_ddi_pairs_per_visit"]:+.4f} | [{summary["bootstrap_analysis"]["delta_ddi_pairs_per_visit"]["ci_lower_95"]:+.4f}, {summary["bootstrap_analysis"]["delta_ddi_pairs_per_visit"]["ci_upper_95"]:+.4f}] |

---

## 3. Frozen Decision Gate Evaluation

| Condition | Threshold Requirement | Observed Empirical Value | Gate Status |
| :--- | :--- | :--- | :--- |
| **1. Under-count Prevalence** | $P(\\lvert\\hat M_t\\rvert < \\lvert M_t\\rvert) \\ge 0.20$ | {undercount:.4f} ({undercount * 100:.2f}%) | {"PASS" if criteria["condition_1_undercount_at_least_20_percent"] else "FAIL"} |
| **2. F1 Material Recovery** | $\\Delta F1 \\ge +0.010$ and 95% CI lower > 0 | {delta_f1:+.6f} (95% CI: [{delta_f1_ci["ci_lower_95"]:+.4f}, {delta_f1_ci["ci_upper_95"]:+.4f}]) | {"PASS" if criteria["condition_2_delta_f1_ge_0_010_and_ci_positive"] else "FAIL"} |
| **3. Safety-Side Attribution** | $\\Delta DDI \\ge +0.005$ and 95% CI lower > 0 | {delta_ddi:+.6f} (95% CI: [{delta_ddi_ci["ci_lower_95"]:+.4f}, {delta_ddi_ci["ci_upper_95"]:+.4f}]) | {"PASS" if criteria["condition_3_delta_ddi_ge_0_005_and_ci_positive"] else "FAIL"} |

---

## 4. Final Verdict and Next State

- **Verdict**: `{verdict}`
- **Diagnostic Role**: Diagnostic attribution only; oracle-count is strictly non-deployable and not a baseline.
- **Scientific Interpretation**:
  - Restoring reference count under unchanged rankings {pass_fail_summary}.
  - Retrospective target fidelity does not imply clinical efficacy; DDI rate proxy does not imply clinical safety.
- **Next state**: `{next_state}`
- **Next Owner**: `{next_owner}`
"""


def self_test_b0() -> None:
    """Run synthetic checks to verify B0 logic end-to-end."""
    vocab = ("A01A", "A02A", "A02B", "B01A", "C01A")
    ddi_pairs = frozenset({("A01A", "A02A"), ("B01A", "C01A")})

    # Test deterministic tie-breaking on scores
    scores_tie = {"A01A": 0.5, "A02A": 0.5, "A02B": 0.9, "B01A": 0.1, "C01A": 0.5}
    # Ranking order should be:
    # A02B (0.9), then among 0.5: A01A, A02A, C01A (alphabetical), then B01A (0.1)
    top3 = compute_oracle_count_prediction(scores_tie, 3, vocab)
    assert top3 == ("A02B", "A01A", "A02A"), f"Unexpected tie break: {top3}"

    # Test top-k with full vocabulary ranking
    top3_all = compute_oracle_count_prediction(scores_tie, 3, vocab)
    assert len(top3_all) == 3

    # Test visit metrics
    m1 = compute_visit_metrics(("A01A", "A02A"), ("A01A", "A02B"), ddi_pairs)
    assert m1["count"] == 2
    assert m1["target_count"] == 2
    assert m1["count_error"] == 0
    assert m1["abs_count_error"] == 0
    assert math.isclose(m1["jaccard"], 1.0 / 3.0)
    assert math.isclose(m1["f1"], 0.5)
    assert m1["ddi_pairs_count"] == 1
    assert m1["predicted_pairs_count"] == 1
    assert math.isclose(m1["visit_ddi_rate"], 1.0)

    # Empty prediction edge cases
    m_empty = compute_visit_metrics((), ("A01A",), ddi_pairs)
    assert m_empty["f1"] == 0.0
    assert m_empty["jaccard"] == 0.0
    assert m_empty["visit_ddi_rate"] == 0.0

    # Decision rule check: all pass
    v_pass, c_pass = evaluate_b0_decision(
        undercount_prevalence=0.35,
        point_delta_f1=0.015,
        delta_f1_ci_lower=0.005,
        point_delta_ddi=0.008,
        delta_ddi_ci_lower=0.002,
    )
    assert v_pass == "PASS_B0_MATERIAL_COUNT_SAFETY_TRADEOFF"
    assert all(c_pass.values())

    # Decision rule check: fail on undercount
    v_fail1, _ = evaluate_b0_decision(0.15, 0.020, 0.005, 0.010, 0.002)
    assert v_fail1 == "FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF"

    # Decision rule check: fail on F1
    v_fail2, _ = evaluate_b0_decision(0.30, 0.008, 0.002, 0.010, 0.002)
    assert v_fail2 == "FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF"

    # Decision rule check: fail on DDI
    v_fail3, _ = evaluate_b0_decision(0.30, 0.015, 0.005, 0.003, 0.001)
    assert v_fail3 == "FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF"

    # Decision rule check: fail on CI containing 0
    v_fail4, _ = evaluate_b0_decision(0.30, 0.015, -0.001, 0.010, 0.002)
    assert v_fail4 == "FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Run synthetic self-test")
    parser.add_argument(
        "--predictions-payload",
        type=Path,
        help="Path to precomputed validation predictions payload JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Output directory for b0-summary.json and b0-decision.md",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=BOOTSTRAP_SEED,
        help=f"Bootstrap random seed (default: {BOOTSTRAP_SEED})",
    )
    parser.add_argument(
        "--bootstrap-replicates",
        type=int,
        default=BOOTSTRAP_REPLICATES,
        help=f"Bootstrap replicates (default: {BOOTSTRAP_REPLICATES})",
    )
    parser.add_argument(
        "--ddi-asset",
        type=Path,
        help="Path to ddi_A_final.pkl or ddi-pairs.pkl (optional if payload includes it)",
    )
    args = parser.parse_args()

    if args.self_test:
        self_test_b0()
        print("B0 self-test passed successfully.")
        return

    if not args.predictions_payload:
        parser.error("Either --self-test or --predictions-payload is required.")

    payload_path = args.predictions_payload.resolve()
    if not payload_path.exists():
        raise FileNotFoundError(f"Predictions payload not found at {payload_path}")

    with payload_path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)

    vocabulary = tuple(payload["medication_vocabulary"])
    targets = payload["targets"]
    predictions = payload["predictions"]

    # Load DDI pairs
    ddi_pairs: frozenset[tuple[str, str]]
    if args.ddi_asset and args.ddi_asset.exists():
        try:
            import dill as serializer
        except ImportError:
            import pickle as serializer
        with args.ddi_asset.open("rb") as stream:
            ddi_raw = serializer.load(stream)
        if isinstance(ddi_raw, (set, frozenset, list, tuple)):
            ddi_pairs = frozenset(
                tuple(sorted((str(p[0]), str(p[1]))))
                for p in ddi_raw
                if len(p) == 2 and p[0] != p[1]
            )
        else:
            # Matrix format
            ddi_matrix = ddi_raw
            pairs_list: list[tuple[str, str]] = []
            for left in range(len(vocabulary)):
                for right in range(left + 1, len(vocabulary)):
                    if ddi_matrix[left][right] == 1:
                        pairs_list.append((vocabulary[left], vocabulary[right]))
            ddi_pairs = frozenset(pairs_list)
    else:
        # Fallback to loading from default snapshot path if present
        snapshot_ddi = Path(
            "/root/zhb/medrec-data/snapshots/molerec-table1-c721-www23/ddi_A_final.pkl"
        )
        if snapshot_ddi.exists():
            import pickle as serializer

            with snapshot_ddi.open("rb") as stream:
                ddi_matrix = serializer.load(stream)
            pairs_list = []
            for left in range(len(vocabulary)):
                for right in range(left + 1, len(vocabulary)):
                    if ddi_matrix[left][right] == 1:
                        pairs_list.append((vocabulary[left], vocabulary[right]))
            ddi_pairs = frozenset(pairs_list)
        else:
            raise RuntimeError("DDI asset required: specify --ddi-asset")

    # Evaluate each validation visit
    patient_visits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_orig_evals: list[dict[str, Any]] = []
    all_oc_evals: list[dict[str, Any]] = []

    undercount_count = 0
    equalcount_count = 0
    overcount_count = 0

    for pred_item in predictions:
        patient_id = pred_item["patient_id"]
        visit_id = pred_item["visit_id"]
        visit_key = f"{patient_id}:{visit_id}"
        target_meds = targets.get(visit_key, [])
        orig_preds = pred_item["predicted_medications"]

        raw_scores = pred_item["vocabulary_scores"]
        if isinstance(raw_scores, list):
            scores_map = {item["medication_code"]: float(item["score"]) for item in raw_scores}
        else:
            scores_map = {k: float(v) for k, v in raw_scores.items()}

        target_k = len(target_meds)
        oc_preds = compute_oracle_count_prediction(scores_map, target_k, vocabulary)

        orig_eval = compute_visit_metrics(orig_preds, target_meds, ddi_pairs)
        oc_eval = compute_visit_metrics(oc_preds, target_meds, ddi_pairs)

        orig_count = len(orig_preds)
        if orig_count < target_k:
            undercount_count += 1
        elif orig_count == target_k:
            equalcount_count += 1
        else:
            overcount_count += 1

        all_orig_evals.append(orig_eval)
        all_oc_evals.append(oc_eval)

        patient_visits[patient_id].append(
            {
                "visit_id": visit_id,
                "orig": orig_eval,
                "oc": oc_eval,
            }
        )

    total_visits = len(predictions)
    undercount_prev = undercount_count / total_visits
    equalcount_prev = equalcount_count / total_visits
    overcount_prev = overcount_count / total_visits

    orig_agg = compute_cohort_aggregates(all_orig_evals)
    oc_agg = compute_cohort_aggregates(all_oc_evals)

    point_delta_f1 = oc_agg["f1"] - orig_agg["f1"]
    point_delta_ddi = oc_agg["evaluator_ddi_rate"] - orig_agg["evaluator_ddi_rate"]
    point_delta_jaccard = oc_agg["jaccard"] - orig_agg["jaccard"]
    point_delta_recall = oc_agg["recall"] - orig_agg["recall"]
    point_delta_precision = oc_agg["precision"] - orig_agg["precision"]
    point_delta_count = oc_agg["count"] - orig_agg["count"]
    point_delta_ddi_pairs = oc_agg["ddi_pairs_per_visit"] - orig_agg["ddi_pairs_per_visit"]

    bootstrap_results = run_patient_clustered_bootstrap(
        patient_visits,
        replicates=args.bootstrap_replicates,
        seed=args.bootstrap_seed,
    )

    verdict, criteria = evaluate_b0_decision(
        undercount_prevalence=undercount_prev,
        point_delta_f1=point_delta_f1,
        delta_f1_ci_lower=bootstrap_results["delta_f1"]["ci_lower_95"],
        point_delta_ddi=point_delta_ddi,
        delta_ddi_ci_lower=bootstrap_results["delta_ddi"]["ci_lower_95"],
    )

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "schema_version": 1,
        "gate_id": "B0 — Cardinality Attribution",
        "verdict": verdict,
        "decision_criteria": criteria,
        "frozen_identities": {
            "model_source_revision": FROZEN_MOLEREC_REVISION,
            "checkpoint_sha256": FROZEN_CHECKPOINT_SHA256,
            "baseline_core_sha256": FROZEN_BASELINE_CORE_SHA256,
            "adapter_sha256": FROZEN_ADAPTER_SHA256,
            "baseline_environment_name": FROZEN_BASELINE_ENVIRONMENT_NAME,
            "baseline_environment_sha256": FROZEN_BASELINE_ENVIRONMENT_SHA256,
            "dataset_id": FROZEN_DATASET_ID,
            "dataset_manifest_sha256": FROZEN_DATASET_MANIFEST_SHA256,
            "snapshot_id": FROZEN_SNAPSHOT_ID,
            "snapshot_sha256": FROZEN_SNAPSHOT_SHA256,
            "medication_vocabulary_sha256": FROZEN_MEDICATION_VOCABULARY_SHA256,
            "ddi_asset_sha256": FROZEN_DDI_ASSET_SHA256,
            "feature_availability_sha256": FROZEN_FEATURE_AVAILABILITY_SHA256,
            "protocol_commit": FROZEN_PROTOCOL_COMMIT,
        },
        "cohort": {
            "validation_cohort_patient_count": FROZEN_VALIDATION_PATIENT_COUNT,
            "validation_patient_count": len(patient_visits),
            "validation_visit_count": total_visits,
        },
        "count_prevalence": {
            "undercount_count": undercount_count,
            "equalcount_count": equalcount_count,
            "overcount_count": overcount_count,
            "undercount_prevalence": undercount_prev,
            "equalcount_prevalence": equalcount_prev,
            "overcount_prevalence": overcount_prev,
        },
        "original_metrics": orig_agg,
        "oracle_count_metrics": oc_agg,
        "paired_deltas": {
            "delta_f1": point_delta_f1,
            "delta_ddi": point_delta_ddi,
            "delta_jaccard": point_delta_jaccard,
            "delta_recall": point_delta_recall,
            "delta_precision": point_delta_precision,
            "delta_count": point_delta_count,
            "delta_ddi_pairs_per_visit": point_delta_ddi_pairs,
        },
        "bootstrap_analysis": bootstrap_results,
        "bootstrap_specification": {
            "replicates": args.bootstrap_replicates,
            "seed": args.bootstrap_seed,
            "unit": "patient",
            "confidence_level": 0.95,
        },
        "gate_thresholds": {
            "min_undercount_prevalence": GATE_MIN_UNDERCOUNT_PREVALENCE,
            "min_delta_f1": GATE_MIN_DELTA_F1,
            "min_delta_ddi": GATE_MIN_DELTA_DDI,
        },
    }

    summary_json_path = output_dir / "b0-summary.json"
    summary_json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote public-safe summary to {summary_json_path}")

    decision_md_path = output_dir / "b0-decision.md"
    decision_md_path.write_text(generate_decision_markdown(summary), encoding="utf-8")
    print(f"Wrote decision record to {decision_md_path}")

    print("\n" + "=" * 60)
    print(f"B0 Verdict: {verdict}")
    print(
        f"Under-count Prevalence: {undercount_prev:.4f} (floor >= {GATE_MIN_UNDERCOUNT_PREVALENCE:.2f})"
    )
    print(f"Orig F1: {orig_agg['f1']:.4f} -> Oracle-Count F1: {oc_agg['f1']:.4f}")
    print(
        f"Delta F1: {point_delta_f1:+.4f} (95% CI: [{bootstrap_results['delta_f1']['ci_lower_95']:+.4f}, {bootstrap_results['delta_f1']['ci_upper_95']:+.4f}])"
    )
    print(
        f"Orig DDI: {orig_agg['evaluator_ddi_rate']:.4f} -> Oracle-Count DDI: {oc_agg['evaluator_ddi_rate']:.4f}"
    )
    print(
        f"Delta DDI: {point_delta_ddi:+.4f} (95% CI: [{bootstrap_results['delta_ddi']['ci_lower_95']:+.4f}, {bootstrap_results['delta_ddi']['ci_upper_95']:+.4f}])"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
