#!/usr/bin/env python3
"""Gate 01 — Routing Opportunity Under a Fixed Revision Operator.

Idea: 001-tension-guided-verification
Stage: Idea / Hypothesis Selection
Scope: Retrospective validation-set medication prediction and constraint auditing only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any, NamedTuple

from medrec_research.adapters import ProcessPredictionAdapter

BUDGETS: tuple[float, ...] = (0.10, 0.20, 0.30)
BUDGET_LABELS: dict[float, str] = {0.10: "10%", 0.20: "20%", 0.30: "30%"}

# Pinned scientific identities from accepted Unified Research Protocol v1.1 Qualification
FROZEN_MOLEREC_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"
FROZEN_BASELINE_CORE_SHA256 = "516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511"
FROZEN_ADAPTER_SHA256 = "9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531"
FROZEN_BASELINE_ENVIRONMENT_SHA256 = (
    "6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda"
)
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 1203


class CandidateRevisionRecord(NamedTuple):
    patient_id: str
    visit_id: str
    patient_order: int
    visit_order: int
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


def _git_revision(path: Path) -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return completed.stdout.strip()


def verify_frozen_molerec_identity(
    molerec_root: Path,
    checkpoint: Path,
    adapter_path: Path,
) -> tuple[str, str, str, str]:
    """Cryptographically verify MoleRec source revision, checkpoint, and adapter identity."""
    source_rev = _git_revision(molerec_root)
    if source_rev != FROZEN_MOLEREC_REVISION:
        raise ValueError(
            f"MoleRec source revision drift: expected {FROZEN_MOLEREC_REVISION}, got {source_rev}"
        )

    checkpoint_sha256 = _file_sha256(checkpoint)
    source_files = (
        "src/modules/MoleRec.py",
        "src/modules/SetTransformer.py",
        "src/modules/gnn/GNNs.py",
        "src/modules/gnn/GNNConv.py",
    )
    source_identity = {
        "revision": FROZEN_MOLEREC_REVISION,
        "source_files": {name: _file_sha256(molerec_root / name) for name in source_files},
    }
    baseline_core_sha256 = _content_sha256(
        {
            "checkpoint_sha256": checkpoint_sha256,
            **source_identity,
        }
    )
    if baseline_core_sha256 != FROZEN_BASELINE_CORE_SHA256:
        raise ValueError(
            f"MoleRec baseline core identity drift: expected {FROZEN_BASELINE_CORE_SHA256}, got {baseline_core_sha256}"
        )

    adapter_sha256 = _file_sha256(adapter_path)
    if adapter_sha256 != FROZEN_ADAPTER_SHA256:
        raise ValueError(
            f"MoleRec adapter identity drift: expected {FROZEN_ADAPTER_SHA256}, got {adapter_sha256}"
        )

    return source_rev, checkpoint_sha256, baseline_core_sha256, adapter_sha256


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
            # Canonical unordered pair lookup
            if tuple(sorted((left, right))) in ddi_pairs:
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


def compute_candidate_revisions(
    predictions: list[dict[str, Any]],
    targets: dict[str, list[str]],
    ddi_pairs: frozenset[tuple[str, str]],
    traversal_by_visit: dict[str, tuple[int, int]] | None = None,
) -> list[CandidateRevisionRecord]:
    """Evaluate singleton marginal revision values using canonical unordered DDI semantics."""
    candidate_records: list[CandidateRevisionRecord] = []

    for pred in predictions:
        patient_id = str(pred["patient_id"])
        visit_id = str(pred["visit_id"])
        visit_key = f"{patient_id}:{visit_id}"
        if visit_key not in targets:
            continue

        target_set = set(targets[visit_key])
        pred_meds = set(pred["predicted_medications"])
        if not pred_meds:
            continue

        base_jaccard, base_f1 = _visit_jaccard_and_f1(pred_meds, target_set)
        base_ddi_edges = _ddi_edge_count(pred_meds, ddi_pairs)

        # Active DDI degree using canonical unordered pair lookup
        active_degrees: dict[str, int] = {}
        for med in pred_meds:
            degree = 0
            for other in pred_meds:
                if med != other and tuple(sorted((med, other))) in ddi_pairs:
                    degree += 1
            active_degrees[med] = degree

        # Eligible review universe Q_t = {m in M_hat_t : d_t(m) > 0}
        eligible_meds = sorted(m for m, degree in active_degrees.items() if degree > 0)

        # Traversal order coordinates for deterministic pseudonym-independent tie-breaking
        if traversal_by_visit is not None and visit_key in traversal_by_visit:
            patient_order, visit_order = traversal_by_visit[visit_key]
        else:
            patient_order, visit_order = 0, 0

        for med in eligible_meds:
            degree = active_degrees[med]
            # Fixed singleton revision operator R_0(M_hat_t, m) = M_hat_t \ {m}
            revised_meds = pred_meds - {med}
            rev_jaccard, rev_f1 = _visit_jaccard_and_f1(revised_meds, target_set)
            rev_ddi_edges = _ddi_edge_count(revised_meds, ddi_pairs)

            delta_jaccard = rev_jaccard - base_jaccard
            delta_f1 = rev_f1 - base_f1
            delta_violation = rev_ddi_edges - base_ddi_edges  # = -degree (< 0)

            # Pareto-beneficial: Delta J >= 0 and Delta V < 0
            pareto_beneficial = (delta_jaccard >= 0.0) and (delta_violation < 0)
            harmful = delta_jaccard < 0.0

            record = CandidateRevisionRecord(
                patient_id=patient_id,
                visit_id=visit_id,
                patient_order=patient_order,
                visit_order=visit_order,
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


def _risk_only_sort_key(c: CandidateRevisionRecord) -> tuple[int, str, int, int]:
    # Preregistered: active DDI degree desc, med_code asc, original traversal order
    return (-c.active_ddi_degree, c.medication_code, c.patient_order, c.visit_order)


def _oracle_sort_key(c: CandidateRevisionRecord) -> tuple[int, float, int, str, int, int]:
    # Preregistered: Y^PB desc, Delta J desc, -Delta V desc, med_code asc, original traversal order
    return (
        -int(c.pareto_beneficial),
        -c.delta_jaccard,
        -c.active_ddi_degree,
        c.medication_code,
        c.patient_order,
        c.visit_order,
    )


def evaluate_policies_at_budgets(
    candidates: list[CandidateRevisionRecord],
) -> tuple[float, dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    n_total = len(candidates)
    if n_total == 0:
        return 0.0, {}, {}, {}, {}

    # 1. Random policy: analytical expectation = overall prevalence P(Y^PB = 1)
    p_random = sum(1 for c in candidates if c.pareto_beneficial) / n_total

    # 2. RiskOnly policy: sort by descending active DDI degree, tie-break by med code & traversal
    risk_sorted = sorted(candidates, key=_risk_only_sort_key)

    # 3. Oracle policy: sort by Y^PB desc, Delta J desc, -Delta V desc, med code & traversal
    oracle_sorted = sorted(candidates, key=_oracle_sort_key)

    risk_yields: dict[str, float] = {}
    oracle_yields: dict[str, float] = {}
    gap_o_r: dict[str, float] = {}
    gap_o_risk: dict[str, float] = {}

    for b in BUDGETS:
        label = BUDGET_LABELS[b]
        k = math.floor(b * n_total)
        if k <= 0:
            raise ValueError(f"budget {label} resulted in 0 review candidates from total {n_total}")
        risk_yield = sum(1 for c in risk_sorted[:k] if c.pareto_beneficial) / k
        oracle_yield = sum(1 for c in oracle_sorted[:k] if c.pareto_beneficial) / k

        risk_yields[label] = risk_yield
        oracle_yields[label] = oracle_yield
        gap_o_r[label] = oracle_yield - p_random
        gap_o_risk[label] = oracle_yield - risk_yield

    return p_random, risk_yields, oracle_yields, gap_o_r, gap_o_risk


def run_patient_clustered_bootstrap(
    candidates: list[CandidateRevisionRecord],
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, dict[str, dict[str, float]]]:
    """Patient-level clustered bootstrap with patient clusters in deterministic traversal order."""
    by_patient_order: dict[int, list[CandidateRevisionRecord]] = {}
    for c in candidates:
        by_patient_order.setdefault(c.patient_order, []).append(c)

    # Enumerate strictly by ascending original patient_order
    unique_patient_orders = sorted(by_patient_order.keys())
    u = len(unique_patient_orders)
    if u == 0:
        return {}

    rng = random.Random(seed)

    boot_risk_yields: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_gap_o_r: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_gap_o_risk: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}

    for _ in range(replicates):
        sampled_orders = [unique_patient_orders[rng.randrange(u)] for _ in range(u)]
        resampled_candidates: list[CandidateRevisionRecord] = []
        for order in sampled_orders:
            resampled_candidates.extend(by_patient_order[order])

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


def write_candidate_jsonl(records: list[CandidateRevisionRecord], path: Path) -> None:
    """Write restricted candidate-level records in standard-library jsonl format."""
    with path.open("w", encoding="utf-8") as stream:
        for r in records:
            stream.write(json.dumps(r.to_dict(), sort_keys=True) + "\n")


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
    identities: dict[str, Any],
) -> dict[str, Any]:
    """Create aggregate-only public-safe summary with frozen identities."""
    eligible_candidates = len(candidates)
    eligible_visits = len(set((c.patient_id, c.visit_id) for c in candidates))
    eligible_patients = len(set(c.patient_order for c in candidates))
    beneficial_patients = len(set(c.patient_order for c in candidates if c.pareto_beneficial))
    non_beneficial_patients = len(
        set(c.patient_order for c in candidates if not c.pareto_beneficial)
    )

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
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "unit": "patient",
            "intervals_95": intervals_95,
        },
        "decision_criteria": criteria,
        "identities": identities,
    }


def run_gate(
    *,
    dataset_root: Path,
    output_root: Path,
    molerec_root: Path,
    checkpoint: Path,
    baseline_environment: str = "medrec-molerec-table1",
    conda_executable: str | Path | None = None,
    harness_root: Path | None = None,
) -> dict[str, Any]:
    """Execute Gate 01 workflow."""
    dataset_root = dataset_root.resolve()
    output_root = output_root.resolve()
    molerec_root = molerec_root.resolve()
    checkpoint = checkpoint.resolve()

    if output_root.exists():
        raise FileExistsError(
            f"output_root already exists: {output_root}. Gate 01 requires a fresh output directory."
        )
    output_root.mkdir(parents=True, exist_ok=False)

    if harness_root is None:
        harness_root = Path(__file__).resolve().parents[4]
    else:
        harness_root = harness_root.resolve()

    staging_script = Path(__file__).resolve().parent / "stage_validation_cohort.py"
    staging_dir = output_root / ".staging"
    staging_dir.mkdir(parents=True, exist_ok=False)

    adapter_path = harness_root / "baselines" / "molerec_comparison.py"

    # 1. Enforce frozen MoleRec source revision, checkpoint hash, and adapter identity
    (
        source_rev,
        checkpoint_sha256,
        baseline_core_sha256,
        adapter_sha256,
    ) = verify_frozen_molerec_identity(
        molerec_root=molerec_root,
        checkpoint=checkpoint,
        adapter_path=adapter_path,
    )

    if conda_executable is None:
        found = shutil.which("conda")
        conda_executable = found if found else "conda"

    # 2. Stage validation cohort inside medrec-molerec-table1 Python 3.8 environment
    stage_cmd = (
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
    )
    subprocess.run(stage_cmd, check=True)

    # 3. Read metadata generated by Python 3.8 staging helper
    meta = json.loads((staging_dir / "validation-meta.json").read_text(encoding="utf-8"))
    features_path = Path(meta["features_path"])
    expected_visits = [tuple(item) for item in meta["expected_visits"]]
    targets = meta["targets"]
    ddi_pairs = frozenset(tuple(item) for item in meta["ddi_pairs"])
    medication_vocabulary = tuple(meta["medication_vocabulary"])
    traversal_by_visit = {
        f"{m['patient_id']}:{m['visit_id']}": (int(m["patient_order"]), int(m["visit_order"]))
        for m in meta["visit_traversal_metadata"]
    }

    # 4. Run target-free Comparison process seam
    adapter_cmd = (
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
        str(features_path),
        "--checkpoint",
        str(checkpoint),
    )

    adapter = ProcessPredictionAdapter(adapter_cmd, timeout_seconds=3600.0)
    batch = adapter.predict_comparison(
        {"dataset_id": meta["dataset_id"]},
        method_id="molerec",
        expected_visits=expected_visits,
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

    # 5. Compute singleton marginal revision values
    candidates = compute_candidate_revisions(
        predictions=predictions,
        targets=targets,
        ddi_pairs=ddi_pairs,
        traversal_by_visit=traversal_by_visit,
    )

    # 6. Support requirement check
    beneficial_patients = len(set(c.patient_order for c in candidates if c.pareto_beneficial))
    non_beneficial_patients = len(
        set(c.patient_order for c in candidates if not c.pareto_beneficial)
    )
    support_sufficient = (beneficial_patients >= 50) and (non_beneficial_patients >= 50)

    # 7. Evaluate policies and bootstrap
    (
        p_random,
        risk_yields,
        oracle_yields,
        gap_o_r,
        gap_o_risk,
    ) = evaluate_policies_at_budgets(candidates)

    intervals_95 = run_patient_clustered_bootstrap(
        candidates=candidates,
        replicates=BOOTSTRAP_REPLICATES,
        seed=BOOTSTRAP_SEED,
    )

    # 8. Evaluate verdict
    verdict, criteria = evaluate_gate_verdict(support_sufficient, intervals_95)

    # 9. Write candidate-level jsonl artifact (restricted)
    jsonl_path = output_root / "candidate-revision-values.jsonl"
    write_candidate_jsonl(candidates, jsonl_path)

    # 10. Write public-safe aggregate summary
    identities = {
        "harness_revision": _git_revision(harness_root),
        "model_source_revision": source_rev,
        "checkpoint_sha256": checkpoint_sha256,
        "baseline_core_sha256": baseline_core_sha256,
        "adapter_sha256": adapter_sha256,
        "baseline_environment_sha256": FROZEN_BASELINE_ENVIRONMENT_SHA256,
        "snapshot_sha256": meta["snapshot_sha256"],
        "ddi_asset_sha256": meta["ddi_asset_sha256"],
        "medication_vocabulary_size": len(medication_vocabulary),
        "medication_vocabulary_sha256": meta["medication_vocabulary_sha256"],
    }

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
        identities=identities,
    )

    summary_path = output_root / "gate-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return summary


def self_test() -> None:
    """Focused synthetic checks: DDI canonicalization, pseudonym invariance, policy ordering, privacy."""
    # --------------------------------------------------------------------------
    # Check 1: DDI pair semantics with non-lexical vocabulary ordering
    # --------------------------------------------------------------------------
    # Vocabulary order: Z is index 0, A is index 1 (differs from lexical order 'A' < 'Z')
    vocab_order = ["MED_Z", "MED_A"]
    # Suppose raw matrix recorded pair (0, 1) as having DDI
    # In old code: tuple was (vocab_order[0], vocab_order[1]) = ("MED_Z", "MED_A") (not sorted).
    # Lookup tuple(sorted(("MED_Z", "MED_A"))) yielded ("MED_A", "MED_Z").
    # If ddi_pairs was not canonicalized, ("MED_A", "MED_Z") in {("MED_Z", "MED_A")} -> FALSE!
    non_canonical_set = frozenset([(vocab_order[0], vocab_order[1])])
    assert ("MED_A", "MED_Z") not in non_canonical_set  # Confirms the bug in non-canonical set

    # Fixed: canonical unordered set
    canonical_set = frozenset([tuple(sorted((vocab_order[0], vocab_order[1])))])
    assert ("MED_A", "MED_Z") in canonical_set  # Must pass under canonical set

    # Verify edge count and active degree with canonical_set
    preds_ddi = [
        {
            "patient_id": "p1",
            "visit_id": "v1",
            "predicted_medications": ["MED_Z", "MED_A"],
        }
    ]
    targets_ddi = {"p1:v1": ["MED_Z"]}
    cands_ddi = compute_candidate_revisions(preds_ddi, targets_ddi, canonical_set)
    assert len(cands_ddi) == 2
    for c in cands_ddi:
        assert c.active_ddi_degree == 1, (
            f"expected active degree 1 for {c.medication_code}, got {c.active_ddi_degree}"
        )
        assert c.base_ddi_edges == 1
        assert c.revised_ddi_edges == 0
        assert c.delta_violation == -1

    # --------------------------------------------------------------------------
    # Check 2: Invariance to pseudonymization keys
    # --------------------------------------------------------------------------
    # Run two synthetic evaluations with different pseudonyms for the exact same patient/visit order
    preds_key1 = []
    targets_key1: dict[str, list[str]] = {}
    traversal_key1: dict[str, tuple[int, int]] = {}
    preds_key2 = []
    targets_key2: dict[str, list[str]] = {}
    traversal_key2: dict[str, tuple[int, int]] = {}

    for i in range(10):
        p1 = f"key1_pat{i}"
        v1 = f"key1_vis{i}"
        p2 = f"key2_pseudonym_{999 - i}"
        v2 = f"key2_visit_{999 - i}"

        preds_key1.append(
            {"patient_id": p1, "visit_id": v1, "predicted_medications": ["m1", "m2", "m3"]}
        )
        targets_key1[f"{p1}:{v1}"] = ["m1", "m2"]
        traversal_key1[f"{p1}:{v1}"] = (i, 1)

        preds_key2.append(
            {"patient_id": p2, "visit_id": v2, "predicted_medications": ["m1", "m2", "m3"]}
        )
        targets_key2[f"{p2}:{v2}"] = ["m1", "m2"]
        traversal_key2[f"{p2}:{v2}"] = (i, 1)

    ddi_mock = frozenset([tuple(sorted(("m1", "m3"))), tuple(sorted(("m2", "m3")))])
    cands_1 = compute_candidate_revisions(
        preds_key1, targets_key1, ddi_mock, traversal_by_visit=traversal_key1
    )
    cands_2 = compute_candidate_revisions(
        preds_key2, targets_key2, ddi_mock, traversal_by_visit=traversal_key2
    )

    p1, r1, o1, g_or1, g_orisk1 = evaluate_policies_at_budgets(cands_1)
    p2, r2, o2, g_or2, g_orisk2 = evaluate_policies_at_budgets(cands_2)
    assert p1 == p2
    assert r1 == r2
    assert o1 == o2
    assert g_or1 == g_or2
    assert g_orisk1 == g_orisk2

    boot_1 = run_patient_clustered_bootstrap(cands_1, replicates=100, seed=1203)
    boot_2 = run_patient_clustered_bootstrap(cands_2, replicates=100, seed=1203)
    assert boot_1 == boot_2, "Bootstrap intervals must be invariant to pseudonymization keys"

    # --------------------------------------------------------------------------
    # Check 3: Metric signs, eligibility, RiskOnly and Oracle ordering
    # --------------------------------------------------------------------------
    ddi_test = frozenset([("m1", "m3"), ("m2", "m3")])
    preds_test = [
        {
            "patient_id": "p0",
            "visit_id": "v0",
            "predicted_medications": ["m1", "m2", "m3", "m4"],
        }
    ]
    targets_test = {
        "p0:v0": ["m1", "m2", "m4"],  # m3 is a false positive involved in DDIs
    }
    cands = compute_candidate_revisions(preds_test, targets_test, ddi_test)
    assert {c.medication_code for c in cands} == {"m1", "m2", "m3"}
    assert "m4" not in {c.medication_code for c in cands}  # Degree 0 excluded

    m3 = next(c for c in cands if c.medication_code == "m3")
    assert m3.pareto_beneficial is True
    assert m3.delta_jaccard > 0
    assert m3.delta_violation < 0
    assert m3.harmful_revision is False

    m1 = next(c for c in cands if c.medication_code == "m1")
    assert m1.pareto_beneficial is False
    assert m1.delta_jaccard < 0
    assert m1.harmful_revision is True

    # RiskOnly sort: m3 (degree 2) precedes m1 (degree 1)
    risk_sorted = sorted(cands, key=_risk_only_sort_key)
    assert [c.medication_code for c in risk_sorted] == ["m3", "m1", "m2"]

    # Oracle sort: m3 (Y^PB=1) precedes others
    oracle_sorted = sorted(cands, key=_oracle_sort_key)
    assert oracle_sorted[0].medication_code == "m3"

    # --------------------------------------------------------------------------
    # Check 4: Gate verdicts
    # --------------------------------------------------------------------------
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
    v_insuf, _ = evaluate_gate_verdict(support_sufficient=False, intervals_95=intervals_dummy)
    assert v_insuf == "insufficient_support"

    v_pass, _ = evaluate_gate_verdict(support_sufficient=True, intervals_95=intervals_dummy)
    assert v_pass == "pass"

    intervals_down = {
        **intervals_dummy,
        "oracle_minus_risk_only": {
            label: {"lower": -0.01, "upper": 0.1} for label in BUDGET_LABELS.values()
        },
    }
    v_down, _ = evaluate_gate_verdict(support_sufficient=True, intervals_95=intervals_down)
    assert v_down == "downgrade_risk_only"

    intervals_fail = {
        **intervals_dummy,
        "oracle_minus_random": {
            label: {"lower": -0.05, "upper": 0.1} for label in BUDGET_LABELS.values()
        },
    }
    v_fail, _ = evaluate_gate_verdict(support_sufficient=True, intervals_95=intervals_fail)
    assert v_fail == "fail"

    # --------------------------------------------------------------------------
    # Check 5: Public-summary privacy
    # --------------------------------------------------------------------------
    summary = build_public_summary(
        candidates=cands,
        p_random=1 / 3,
        risk_yields={"10%": 1.0, "20%": 1.0, "30%": 1.0},
        oracle_yields={"10%": 1.0, "20%": 1.0, "30%": 1.0},
        gap_o_r={"10%": 0.67, "20%": 0.67, "30%": 0.67},
        gap_o_risk={"10%": 0.0, "20%": 0.0, "30%": 0.0},
        intervals_95=intervals_dummy,
        verdict=v_pass,
        criteria={"support_requirement_met": True},
        identities={
            "harness_revision": "mock_rev",
            "model_source_revision": FROZEN_MOLEREC_REVISION,
            "checkpoint_sha256": "mock_cp",
            "baseline_core_sha256": FROZEN_BASELINE_CORE_SHA256,
            "adapter_sha256": FROZEN_ADAPTER_SHA256,
            "baseline_environment_sha256": FROZEN_BASELINE_ENVIRONMENT_SHA256,
            "snapshot_sha256": "mock_snap",
            "ddi_asset_sha256": "mock_ddi",
            "medication_vocabulary_size": 131,
            "medication_vocabulary_sha256": "mock_vocab",
        },
    )
    serialized = json.dumps(summary)
    assert "p0" not in serialized, "patient_id must not leak into public summary"
    assert "v0" not in serialized, "visit_id must not leak into public summary"
    assert "/root/" not in serialized, "filesystem paths must not leak into public summary"

    print("Gate 01 synthetic self-test passed successfully.")


def test_synthetic_gate_01() -> None:
    """Pytest entrypoint for Gate 01 synthetic self-test."""
    self_test()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Run focused synthetic test suite")
    parser.add_argument("--dataset-root", type=Path, help="Path to snapshot root")
    parser.add_argument("--output-root", type=Path, help="New restricted output root")
    parser.add_argument("--molerec-root", type=Path, help="Path to MoleRec checkout")
    parser.add_argument("--checkpoint", type=Path, help="Path to frozen MoleRec checkpoint")
    parser.add_argument("--baseline-environment", default="medrec-molerec-table1")
    parser.add_argument("--conda-executable", type=Path)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    if (
        args.dataset_root is None
        or args.output_root is None
        or args.molerec_root is None
        or args.checkpoint is None
    ):
        parser.error(
            "--dataset-root, --output-root, --molerec-root, and --checkpoint are required for formal Gate 01 execution"
        )

    summary = run_gate(
        dataset_root=args.dataset_root,
        output_root=args.output_root,
        molerec_root=args.molerec_root,
        checkpoint=args.checkpoint,
        baseline_environment=args.baseline_environment,
        conda_executable=args.conda_executable,
    )
    print(json.dumps({"verdict": summary["verdict"], "support": summary["support"]}, indent=2))


if __name__ == "__main__":
    main()
