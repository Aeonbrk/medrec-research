#!/usr/bin/env python3
"""Gate 01 — Routing Opportunity Under a Fixed Revision Operator.

Idea: 001-tension-guided-verification
Stage: Idea / Hypothesis Selection
Scope: Retrospective validation-set medication prediction and constraint auditing only.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import random
import secrets
import shutil
from pathlib import Path
from typing import Any, NamedTuple

# Re-use existing comparison process adapter
from medrec_research.adapters import ProcessPredictionAdapter

BUDGETS: tuple[float, ...] = (0.10, 0.20, 0.30)
BUDGET_LABELS: dict[float, str] = {0.10: "10%", 0.20: "20%", 0.30: "30%"}


class CandidateRevisionRecord(NamedTuple):
    patient_id: str
    visit_id: str
    medication_code: str
    base_jaccard: float
    revised_jaccard: float
    delta_jaccard: float
    base_f1: float
    revised_f1: float
    delta_f1: float
    active_ddi_degree: int
    base_ddi_edges: int
    revised_ddi_edges: int
    delta_violation: int
    pareto_beneficial: bool
    harmful_revision: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "visit_id": self.visit_id,
            "medication_code": self.medication_code,
            "base_jaccard": float(self.base_jaccard),
            "revised_jaccard": float(self.revised_jaccard),
            "delta_jaccard": float(self.delta_jaccard),
            "base_f1": float(self.base_f1),
            "revised_f1": float(self.revised_f1),
            "delta_f1": float(self.delta_f1),
            "active_ddi_degree": int(self.active_ddi_degree),
            "base_ddi_edges": int(self.base_ddi_edges),
            "revised_ddi_edges": int(self.revised_ddi_edges),
            "delta_violation": int(self.delta_violation),
            "pareto_beneficial": bool(self.pareto_beneficial),
            "harmful_revision": bool(self.harmful_revision),
        }


def _identifier(key: bytes, kind: str, *indices: int) -> str:
    message = ":".join((kind, *(str(index) for index in indices))).encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _split_ranges(patient_count: int) -> dict[str, range]:
    split_point = int(patient_count * 2 / 3)
    evaluation_length = int((patient_count - split_point) / 2)
    return {
        "train": range(0, split_point),
        "test": range(split_point, split_point + evaluation_length),
        "validation": range(split_point + evaluation_length, patient_count),
    }


def _vocabulary(idx2word: object) -> tuple[str, ...]:
    return tuple(str(idx2word[index]) for index in range(len(idx2word)))  # type: ignore[index]


def _visit_jaccard_and_f1(predicted: set[str], target: set[str]) -> tuple[float, float]:
    if not target and not predicted:
        return (1.0, 1.0)
    if not target or not predicted:
        return (0.0, 0.0)
    intersection = len(target & predicted)
    precision = intersection / len(predicted)
    recall = intersection / len(target)
    f1 = 0.0 if (precision + recall) == 0.0 else (2 * precision * recall) / (precision + recall)
    jaccard = intersection / len(target | predicted)
    return (jaccard, f1)


def _ddi_edge_count(medications: set[str], ddi_pairs: frozenset[tuple[str, str]]) -> int:
    med_list = sorted(medications)
    edges = 0
    for i, left in enumerate(med_list):
        for right in med_list[i + 1 :]:
            if (left, right) in ddi_pairs:
                edges += 1
    return edges


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def stage_validation_cohort(
    dataset_root: Path,
    output_dir: Path,
    dataset_id: str = "molerec-table1-comparison-v1-1",
) -> tuple[
    Path,
    dict[tuple[str, str], tuple[str, ...]],
    frozenset[tuple[str, str]],
    tuple[str, ...],
    list[tuple[str, str]],
]:
    """Reproduce v1.1 patient split and feature staging for the validation split only."""
    try:
        import dill as serializer
    except ImportError:
        import pickle as serializer  # type: ignore[no-redef]

    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = dataset_root / "records_final.pkl"
    vocabulary_path = dataset_root / "voc_final.pkl"
    ddi_path = dataset_root / "ddi_A_final.pkl"

    with records_path.open("rb") as stream:
        records = serializer.load(stream)
    with vocabulary_path.open("rb") as stream:
        voc = serializer.load(stream)
    with ddi_path.open("rb") as stream:
        ddi_matrix = serializer.load(stream)

    medication_vocabulary = _vocabulary(voc["med_voc"].idx2word)
    voc_size = (
        len(voc["diag_voc"].idx2word),
        len(voc["pro_voc"].idx2word),
        len(medication_vocabulary),
    )

    ddi_pairs = frozenset(
        (medication_vocabulary[left], medication_vocabulary[right])
        for left in range(len(medication_vocabulary))
        for right in range(left + 1, len(medication_vocabulary))
        if ddi_matrix[left][right] == 1
    )

    key = secrets.token_bytes(32)
    splits = _split_ranges(len(records))
    validation_patient_indices = splits["validation"]

    contexts: list[dict[str, Any]] = []
    targets: dict[tuple[str, str], tuple[str, ...]] = {}
    expected_visits: list[tuple[str, str]] = []

    for patient_index in validation_patient_indices:
        patient_id = _identifier(key, "patient", patient_index)
        patient = records[patient_index]
        for visit_index in range(1, len(patient)):
            visit_id = _identifier(key, "visit", patient_index, visit_index)
            visit_key = (patient_id, visit_id)
            expected_visits.append(visit_key)

            history = tuple(
                (
                    tuple(int(code) for code in admission[0]),
                    tuple(int(code) for code in admission[1]),
                    tuple(int(code) for code in admission[2]),
                )
                for admission in patient[:visit_index]
            )
            current = patient[visit_index]
            contexts.append(
                {
                    "current_diagnoses": tuple(int(code) for code in current[0]),
                    "current_procedures": tuple(int(code) for code in current[1]),
                    "history": history,
                    "patient_id": patient_id,
                    "visit_id": visit_id,
                }
            )
            targets[visit_key] = tuple(medication_vocabulary[int(code)] for code in current[2])

    features_bundle = {
        "contexts": contexts,
        "dataset_id": dataset_id,
        "medication_vocabulary": medication_vocabulary,
        "schema_version": 1,
        "voc_size": voc_size,
    }
    features_path = output_dir / "features.pkl"
    with features_path.open("wb") as stream:
        serializer.dump(features_bundle, stream)

    return features_path, targets, ddi_pairs, medication_vocabulary, expected_visits


def compute_candidate_revisions(
    predictions: list[dict[str, Any]],
    targets: dict[tuple[str, str], tuple[str, ...]],
    ddi_pairs: frozenset[tuple[str, str]],
) -> list[CandidateRevisionRecord]:
    """Evaluate singleton marginal revision value for every eligible validation candidate."""
    candidate_records: list[CandidateRevisionRecord] = []

    for pred in predictions:
        patient_id = str(pred["patient_id"])
        visit_id = str(pred["visit_id"])
        visit_key = (patient_id, visit_id)
        if visit_key not in targets:
            continue

        target_set = set(targets[visit_key])
        pred_meds = set(pred["predicted_medications"])
        if not pred_meds:
            continue

        base_jaccard, base_f1 = _visit_jaccard_and_f1(pred_meds, target_set)
        base_ddi_edges = _ddi_edge_count(pred_meds, ddi_pairs)

        # Active DDI degree for each predicted medication
        active_degrees: dict[str, int] = {}
        for med in pred_meds:
            degree = 0
            for other in pred_meds:
                if med != other and tuple(sorted((med, other))) in ddi_pairs:
                    degree += 1
            active_degrees[med] = degree

        # Eligible review universe Q_t = {m in M_hat_t : d_t(m) > 0}
        eligible_meds = sorted(m for m, degree in active_degrees.items() if degree > 0)

        for med in eligible_meds:
            degree = active_degrees[med]
            # Fixed singleton revision operator R_0(M_hat_t, m) = M_hat_t \ {m}
            revised_meds = pred_meds - {med}
            rev_jaccard, rev_f1 = _visit_jaccard_and_f1(revised_meds, target_set)
            rev_ddi_edges = _ddi_edge_count(revised_meds, ddi_pairs)

            delta_jaccard = rev_jaccard - base_jaccard
            delta_f1 = rev_f1 - base_f1
            delta_violation = rev_ddi_edges - base_ddi_edges  # strictly < 0 (= -degree)

            # Pareto-beneficial: Delta J >= 0 and Delta V < 0
            pareto_beneficial = (delta_jaccard >= 0.0) and (delta_violation < 0)
            harmful = delta_jaccard < 0.0

            record = CandidateRevisionRecord(
                patient_id=patient_id,
                visit_id=visit_id,
                medication_code=med,
                base_jaccard=base_jaccard,
                revised_jaccard=rev_jaccard,
                delta_jaccard=delta_jaccard,
                base_f1=base_f1,
                revised_f1=rev_f1,
                delta_f1=delta_f1,
                active_ddi_degree=degree,
                base_ddi_edges=base_ddi_edges,
                revised_ddi_edges=rev_ddi_edges,
                delta_violation=delta_violation,
                pareto_beneficial=pareto_beneficial,
                harmful_revision=harmful,
            )
            candidate_records.append(record)

    return candidate_records


def _risk_only_sort_key(c: CandidateRevisionRecord) -> tuple[int, str, str, str]:
    return (-c.active_ddi_degree, c.medication_code, c.patient_id, c.visit_id)


def _oracle_sort_key(c: CandidateRevisionRecord) -> tuple[int, float, int, str, str, str]:
    return (
        -int(c.pareto_beneficial),
        -c.delta_jaccard,
        -c.active_ddi_degree,
        c.medication_code,
        c.patient_id,
        c.visit_id,
    )


def evaluate_policies_at_budgets(
    candidates: list[CandidateRevisionRecord],
) -> tuple[float, dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    n_total = len(candidates)
    if n_total == 0:
        return 0.0, {}, {}, {}, {}

    # 1. Random policy: analytical expectation = overall prevalence P(Y^PB = 1)
    p_random = sum(1 for c in candidates if c.pareto_beneficial) / n_total

    # 2. RiskOnly policy: sort by descending active DDI degree, tie-break by med code
    risk_sorted = sorted(candidates, key=_risk_only_sort_key)

    # 3. Oracle policy: sort by Y^PB desc, Delta J desc, -Delta V desc, med code
    oracle_sorted = sorted(candidates, key=_oracle_sort_key)

    risk_yields: dict[str, float] = {}
    oracle_yields: dict[str, float] = {}
    gap_o_r: dict[str, float] = {}
    gap_o_risk: dict[str, float] = {}

    for b in BUDGETS:
        label = BUDGET_LABELS[b]
        k = max(1, round(b * n_total))
        risk_yield = sum(1 for c in risk_sorted[:k] if c.pareto_beneficial) / k
        oracle_yield = sum(1 for c in oracle_sorted[:k] if c.pareto_beneficial) / k

        risk_yields[label] = risk_yield
        oracle_yields[label] = oracle_yield
        gap_o_r[label] = oracle_yield - p_random
        gap_o_risk[label] = oracle_yield - risk_yield

    return p_random, risk_yields, oracle_yields, gap_o_r, gap_o_risk


def run_patient_clustered_bootstrap(
    candidates: list[CandidateRevisionRecord],
    replicates: int = 1000,
    seed: int = 1203,
) -> dict[str, dict[str, dict[str, float]]]:
    """Patient-level clustered bootstrap with 1,000 resamples."""
    by_patient: dict[str, list[CandidateRevisionRecord]] = {}
    for c in candidates:
        by_patient.setdefault(c.patient_id, []).append(c)

    unique_patients = sorted(by_patient.keys())
    u = len(unique_patients)
    if u == 0:
        return {}

    rng = random.Random(seed)

    boot_risk_yields: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_gap_o_r: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_gap_o_risk: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}

    for _ in range(replicates):
        sampled_patients = [unique_patients[rng.randrange(u)] for _ in range(u)]
        resampled_candidates: list[CandidateRevisionRecord] = []
        for p in sampled_patients:
            resampled_candidates.extend(by_patient[p])

        _, r_yields, _, g_o_r, g_o_risk = evaluate_policies_at_budgets(resampled_candidates)
        for b in BUDGETS:
            label = BUDGET_LABELS[b]
            boot_risk_yields[label].append(r_yields[label])
            boot_gap_o_r[label].append(g_o_r[label])
            boot_gap_o_risk[label].append(g_o_risk[label])

    intervals: dict[str, dict[str, dict[str, float]]] = {
        "risk_only_yield": {},
        "oracle_minus_random": {},
        "oracle_minus_risk_only": {},
    }
    for b in BUDGETS:
        label = BUDGET_LABELS[b]
        intervals["risk_only_yield"][label] = {
            "lower": _percentile(boot_risk_yields[label], 0.025),
            "upper": _percentile(boot_risk_yields[label], 0.975),
        }
        intervals["oracle_minus_random"][label] = {
            "lower": _percentile(boot_gap_o_r[label], 0.025),
            "upper": _percentile(boot_gap_o_r[label], 0.975),
        }
        intervals["oracle_minus_risk_only"][label] = {
            "lower": _percentile(boot_gap_o_risk[label], 0.025),
            "upper": _percentile(boot_gap_o_risk[label], 0.975),
        }

    return intervals


def evaluate_gate_verdict(
    support_sufficient: bool,
    intervals_95: dict[str, dict[str, dict[str, float]]],
) -> tuple[str, dict[str, bool]]:
    if not support_sufficient:
        criteria = {
            "support_requirement_met": False,
            "gap_oracle_random_10_ci_above_zero": False,
            "gap_oracle_random_20_ci_above_zero": False,
            "gap_oracle_risk_indistinguishable_from_zero": False,
        }
        return "insufficient_support", criteria

    ci_o_r_10 = intervals_95["oracle_minus_random"]["10%"]["lower"] > 0.0
    ci_o_r_20 = intervals_95["oracle_minus_random"]["20%"]["lower"] > 0.0
    gap_o_r_above_zero = ci_o_r_10 and ci_o_r_20

    ci_o_risk_10_lower = intervals_95["oracle_minus_risk_only"]["10%"]["lower"]
    ci_o_risk_20_lower = intervals_95["oracle_minus_risk_only"]["20%"]["lower"]
    risk_indistinguishable = (ci_o_risk_10_lower <= 0.0) and (ci_o_risk_20_lower <= 0.0)

    criteria = {
        "support_requirement_met": True,
        "gap_oracle_random_10_ci_above_zero": ci_o_r_10,
        "gap_oracle_random_20_ci_above_zero": ci_o_r_20,
        "gap_oracle_risk_indistinguishable_from_zero": risk_indistinguishable,
    }

    if not gap_o_r_above_zero:
        return "fail", criteria
    if risk_indistinguishable:
        return "downgrade_risk_only", criteria
    return "pass", criteria


def write_candidate_parquet(records: list[CandidateRevisionRecord], path: Path) -> None:
    """Write candidate-level data to parquet file."""
    data = [r.to_dict() for r in records]
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pa.Table.from_pylist(data)
        pq.write_table(table, path)
        return
    except ImportError:
        pass

    try:
        import pandas as pd

        df = pd.DataFrame(data)
        df.to_parquet(path, index=False)
        return
    except ImportError:
        pass

    raise RuntimeError(
        "Writing candidate-revision-values.parquet requires 'pyarrow' or 'pandas' in the execution environment."
    )


def build_public_summary(
    candidates: list[CandidateRevisionRecord],
    p_random: float,
    risk_yields: dict[str, float],
    oracle_yields: dict[str, float],
    gap_o_r: dict[str, float],
    gap_o_risk: dict[str, float],
    intervals_95: dict[str, dict[str, dict[str, float]]],
    verdict: str,
    criteria: dict[str, bool],
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    """Create aggregate-only public-safe summary."""
    eligible_candidates = len(candidates)
    eligible_visits = len(set((c.patient_id, c.visit_id) for c in candidates))
    eligible_patients = len(set(c.patient_id for c in candidates))
    beneficial_patients = len(set(c.patient_id for c in candidates if c.pareto_beneficial))
    non_beneficial_patients = len(set(c.patient_id for c in candidates if not c.pareto_beneficial))

    return {
        "schema_version": 1,
        "kind": "gate_01_routing_opportunity_summary",
        "idea_id": "001-tension-guided-verification",
        "gate_id": "gate-01-routing-opportunity",
        "method_id": "molerec",
        "profile_id": "molerec-embedding",
        "split": "validation",
        "verdict": verdict,
        "support": {
            "eligible_candidates": eligible_candidates,
            "eligible_visits": eligible_visits,
            "eligible_patients": eligible_patients,
            "beneficial_patients": beneficial_patients,
            "non_beneficial_patients": non_beneficial_patients,
            "support_sufficient": criteria["support_requirement_met"],
        },
        "overall_prevalence": {
            "pareto_beneficial_yield": p_random,
            "harmful_revision_yield": 1.0 - p_random,
        },
        "policies": {
            "random": {
                "yield": p_random,
            },
            "risk_only": {
                "yields": risk_yields,
            },
            "oracle": {
                "yields": oracle_yields,
            },
        },
        "gaps": {
            "oracle_minus_random": gap_o_r,
            "oracle_minus_risk_only": gap_o_risk,
        },
        "bootstrap": {
            "replicates": replicates,
            "seed": seed,
            "unit": "patient",
            "intervals_95": intervals_95,
        },
        "decision_criteria": criteria,
    }


def run_gate(
    *,
    dataset_root: Path,
    output_root: Path,
    molerec_root: Path | None = None,
    checkpoint: Path | None = None,
    baseline_environment: str = "medrec-molerec-table1",
    conda_executable: str | Path | None = None,
    harness_root: Path | None = None,
    bootstrap_replicates: int = 1000,
    bootstrap_seed: int = 1203,
    smoke: bool = False,
    predictions_file: Path | None = None,
) -> dict[str, Any]:
    """Execute Gate 01 workflow."""
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    staging_dir = output_root / ".staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    if harness_root is None:
        harness_root = Path(__file__).resolve().parents[4]

    # 1. Stage validation cohort
    (
        features_path,
        targets,
        ddi_pairs,
        medication_vocabulary,
        expected_visits,
    ) = stage_validation_cohort(
        dataset_root=dataset_root,
        output_dir=staging_dir,
    )

    # 2. Obtain predictions from MoleRec Comparison process adapter or precomputed file
    if predictions_file is not None:
        raw = json.loads(predictions_file.read_text(encoding="utf-8"))
        predictions = raw["predictions"]
    else:
        if molerec_root is None or checkpoint is None:
            raise ValueError(
                "molerec_root and checkpoint are required when predictions_file is not provided"
            )
        if conda_executable is None:
            found = shutil.which("conda")
            conda_executable = found if found else "conda"

        adapter_cmd = (
            str(conda_executable),
            "run",
            "--no-capture-output",
            "-n",
            baseline_environment,
            "python",
            str((harness_root / "baselines" / "molerec_comparison.py").resolve()),
            "--upstream-root",
            str(molerec_root.resolve()),
            "--dataset-root",
            str(dataset_root.resolve()),
            "--features",
            str(features_path.resolve()),
            "--checkpoint",
            str(checkpoint.resolve()),
        )
        if smoke:
            adapter_cmd = (*adapter_cmd, "--smoke")

        adapter = ProcessPredictionAdapter(adapter_cmd, timeout_seconds=3600.0)
        batch = adapter.predict_comparison(
            {"dataset_id": "molerec-table1-comparison-v1-1"},
            method_id="molerec",
            expected_visits=expected_visits[:1] if smoke else expected_visits,
            medication_vocabulary=medication_vocabulary,
        )
        predictions = [
            {
                "patient_id": p.patient_id,
                "visit_id": p.visit_id,
                "predicted_medications": list(p.predicted_medications),
            }
            for p in batch.predictions
        ]

    # 3. Compute singleton marginal revision values
    candidates = compute_candidate_revisions(
        predictions=predictions,
        targets=targets,
        ddi_pairs=ddi_pairs,
    )

    # 4. Support requirement check
    beneficial_patients = len(set(c.patient_id for c in candidates if c.pareto_beneficial))
    non_beneficial_patients = len(set(c.patient_id for c in candidates if not c.pareto_beneficial))
    support_sufficient = (beneficial_patients >= 50) and (non_beneficial_patients >= 50)

    # 5. Evaluate policies and bootstrap
    (
        p_random,
        risk_yields,
        oracle_yields,
        gap_o_r,
        gap_o_risk,
    ) = evaluate_policies_at_budgets(candidates)

    intervals_95 = run_patient_clustered_bootstrap(
        candidates=candidates,
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
    )

    # 6. Evaluate verdict
    verdict, criteria = evaluate_gate_verdict(support_sufficient, intervals_95)

    # 7. Write candidate-level parquet artifact (restricted)
    parquet_path = output_root / "candidate-revision-values.parquet"
    write_candidate_parquet(candidates, parquet_path)

    # 8. Write public-safe aggregate summary
    summary = build_public_summary(
        candidates=candidates,
        p_random=p_random,
        risk_yields=risk_yields,
        oracle_yields=oracle_yields,
        gap_o_r=gap_o_r,
        gap_o_risk=gap_o_risk,
        intervals_95=intervals_95,
        verdict=verdict,
        criteria=criteria,
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
    )

    summary_path = output_root / "gate-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return summary


def self_test() -> None:
    """Focused synthetic check for singleton metric signs, eligible-DDI filtering, RiskOnly ordering, and public-summary privacy."""
    # 1. Metric signs & eligible-DDI filtering
    ddi_pairs = frozenset([("m1", "m3"), ("m2", "m3")])
    predictions = [
        {
            "patient_id": "p1",
            "visit_id": "v1",
            "predicted_medications": ["m1", "m2", "m3", "m4"],
        }
    ]
    targets = {
        ("p1", "v1"): ("m1", "m2", "m4"),  # m3 is a false positive involved in DDIs with m1 and m2
    }
    candidates = compute_candidate_revisions(predictions, targets, ddi_pairs)
    eligible_meds = {c.medication_code for c in candidates}
    assert eligible_meds == {"m1", "m2", "m3"}, f"expected {{m1, m2, m3}}, got {eligible_meds}"
    assert "m4" not in eligible_meds, "m4 has degree 0 and must not be in candidate universe"

    m3_cand = next(c for c in candidates if c.medication_code == "m3")
    assert m3_cand.pareto_beneficial is True, "deleting false positive m3 must be Pareto-beneficial"
    assert m3_cand.delta_jaccard > 0, "deleting false positive must increase Jaccard"
    assert m3_cand.delta_violation < 0, "deleting DDI medication must reduce violations"
    assert m3_cand.harmful_revision is False

    m1_cand = next(c for c in candidates if c.medication_code == "m1")
    assert m1_cand.pareto_beneficial is False, (
        "deleting true positive m1 must not be Pareto-beneficial"
    )
    assert m1_cand.delta_jaccard < 0, "deleting true positive must decrease Jaccard"
    assert m1_cand.harmful_revision is True

    # 2. RiskOnly & Oracle ordering
    risk_sorted = sorted(candidates, key=_risk_only_sort_key)
    assert [c.medication_code for c in risk_sorted] == ["m3", "m1", "m2"]

    oracle_sorted = sorted(candidates, key=_oracle_sort_key)
    assert oracle_sorted[0].medication_code == "m3"

    # 3. Policy yields at budgets
    p_rand, r_yields, o_yields, g_o_r, g_o_risk = evaluate_policies_at_budgets(candidates)
    assert p_rand == 1 / 3
    assert o_yields["10%"] == 1.0
    assert r_yields["10%"] == 1.0
    assert g_o_r["10%"] == 1.0 - (1 / 3)

    # 4. Support requirement check (< 50 patients -> insufficient_support)
    intervals_dummy = {
        "risk_only_yield": {
            label: {"lower": 0.5, "upper": 0.7} for label in BUDGET_LABELS.values()
        },
        "oracle_minus_random": {
            label: {"lower": 0.2, "upper": 0.4} for label in BUDGET_LABELS.values()
        },
        "oracle_minus_risk_only": {
            label: {"lower": 0.05, "upper": 0.2} for label in BUDGET_LABELS.values()
        },
    }
    verdict, criteria = evaluate_gate_verdict(
        support_sufficient=False, intervals_95=intervals_dummy
    )
    assert verdict == "insufficient_support"
    assert criteria["support_requirement_met"] is False

    # 5. Gate verdict decisions with support_sufficient=True
    verdict_pass, _ = evaluate_gate_verdict(support_sufficient=True, intervals_95=intervals_dummy)
    assert verdict_pass == "pass"

    intervals_downgrade = {
        **intervals_dummy,
        "oracle_minus_risk_only": {
            label: {"lower": -0.02, "upper": 0.1} for label in BUDGET_LABELS.values()
        },
    }
    verdict_down, _ = evaluate_gate_verdict(
        support_sufficient=True, intervals_95=intervals_downgrade
    )
    assert verdict_down == "downgrade_risk_only"

    intervals_fail = {
        **intervals_dummy,
        "oracle_minus_random": {
            label: {"lower": -0.05, "upper": 0.1} for label in BUDGET_LABELS.values()
        },
    }
    verdict_fail, _ = evaluate_gate_verdict(support_sufficient=True, intervals_95=intervals_fail)
    assert verdict_fail == "fail"

    # 6. Public-summary privacy
    summary = build_public_summary(
        candidates=candidates,
        p_random=p_rand,
        risk_yields=r_yields,
        oracle_yields=o_yields,
        gap_o_r=g_o_r,
        gap_o_risk=g_o_risk,
        intervals_95=intervals_dummy,
        verdict=verdict_pass,
        criteria=criteria,
        replicates=10,
        seed=1203,
    )
    serialized = json.dumps(summary)
    assert "p1" not in serialized, "patient_id must not appear in public summary"
    assert "v1" not in serialized, "visit_id must not appear in public summary"
    assert "/root/" not in serialized, "no filesystem paths in public summary"
    assert summary["verdict"] in ("pass", "downgrade_risk_only", "fail", "insufficient_support")

    # 7. Clustered bootstrap reproducibility
    boot_intervals = run_patient_clustered_bootstrap(candidates, replicates=50, seed=1203)
    assert "risk_only_yield" in boot_intervals
    for b_label in BUDGET_LABELS.values():
        assert (
            boot_intervals["risk_only_yield"][b_label]["lower"]
            <= boot_intervals["risk_only_yield"][b_label]["upper"]
        )

    print("Gate 01 synthetic self-test passed successfully.")


def test_synthetic_gate_01() -> None:
    """Pytest entrypoint for Gate 01 synthetic self-test."""
    self_test()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Run focused synthetic test suite")
    parser.add_argument("--dataset-root", type=Path, help="Path to snapshot root")
    parser.add_argument("--output-root", type=Path, help="Restricted output root")
    parser.add_argument("--molerec-root", type=Path, help="Path to MoleRec checkout")
    parser.add_argument("--checkpoint", type=Path, help="Path to frozen MoleRec checkpoint")
    parser.add_argument("--baseline-environment", default="medrec-molerec-table1")
    parser.add_argument("--conda-executable", type=Path)
    parser.add_argument("--bootstrap-replicates", type=int, default=1000)
    parser.add_argument("--bootstrap-seed", type=int, default=1203)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--predictions-file", type=Path, help="Optional precomputed predictions")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if args.dataset_root is None or args.output_root is None:
        parser.error(
            "--dataset-root and --output-root are required unless --self-test is specified"
        )

    summary = run_gate(
        dataset_root=args.dataset_root,
        output_root=args.output_root,
        molerec_root=args.molerec_root,
        checkpoint=args.checkpoint,
        baseline_environment=args.baseline_environment,
        conda_executable=args.conda_executable,
        bootstrap_replicates=args.bootstrap_replicates,
        bootstrap_seed=args.bootstrap_seed,
        smoke=args.smoke,
        predictions_file=args.predictions_file,
    )
    print(json.dumps({"verdict": summary["verdict"], "support": summary["support"]}, indent=2))


if __name__ == "__main__":
    main()
