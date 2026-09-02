#!/usr/bin/env python3
"""Gate 01 — Score-Geometry Sufficiency.

Idea: 002-score-geometry-sufficiency
Stage: Idea / Hypothesis Selection
Scope: Validation-only falsification of low-complexity non-monotone score mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NamedTuple

BUDGETS: tuple[float, ...] = (0.10, 0.20, 0.30)
BUDGET_LABELS: dict[float, str] = {0.10: "10%", 0.20: "20%", 0.30: "30%"}
QUINTILES: tuple[float, ...] = (0.20, 0.40, 0.60, 0.80)

# Pinned scientific identities matching Gate 01 / Qualification v1.1
FROZEN_DATASET_MANIFEST_SHA256 = "82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712"
FROZEN_DATASET_ID = "molerec-table1-comparison-v1-1"
FROZEN_SNAPSHOT_ID = "molerec-table1-c721-www23"
FROZEN_SNAPSHOT_SHA256 = "42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58"
FROZEN_MEDICATION_VOCABULARY_SHA256 = (
    "6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08"
)
FROZEN_DDI_ASSET_SHA256 = "dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7"
FROZEN_BASELINE_ENVIRONMENT_NAME = "medrec-molerec-table1"
FROZEN_MOLEREC_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"
FROZEN_BASELINE_CORE_SHA256 = "516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511"
FROZEN_ADAPTER_SHA256 = "9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531"
FROZEN_UPSTREAM_RUN_ID = "gate-02-confidence-sufficiency-20260902-155433"
FROZEN_UPSTREAM_CANDIDATE_SHA256 = (
    "50b8f7587f44ec81dd5ec0ec188d953cf9edfbb332279ce3fb759ae33ed2e736"
)
FROZEN_UPSTREAM_CANDIDATE_ROWS = 15549
FROZEN_VALIDATION_PATIENT_COUNT = 1059

SPLIT_SEED = 2002
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 1203


class Gate01CandidateRecord(NamedTuple):
    patient_id: str
    visit_id: str
    patient_order: int
    visit_order: int
    gate01_partition: str  # "dev" or "audit"
    medication_code: str
    model_score: float
    active_ddi_degree: int
    pareto_beneficial: bool
    delta_jaccard: float
    delta_violation: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "visit_id": self.visit_id,
            "patient_order": int(self.patient_order),
            "visit_order": int(self.visit_order),
            "gate01_partition": str(self.gate01_partition),
            "medication_code": str(self.medication_code),
            "model_score": float(self.model_score),
            "active_ddi_degree": int(self.active_ddi_degree),
            "pareto_beneficial": bool(self.pareto_beneficial),
            "delta_jaccard": float(self.delta_jaccard),
            "delta_violation": int(self.delta_violation),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], partition: str) -> Gate01CandidateRecord:
        return cls(
            patient_id=str(data["patient_id"]),
            visit_id=str(data["visit_id"]),
            patient_order=int(data["patient_order"]),
            visit_order=int(data["visit_order"]),
            gate01_partition=partition,
            medication_code=str(data["medication_code"]),
            model_score=float(data["model_score"]),
            active_ddi_degree=int(data["active_ddi_degree"]),
            pareto_beneficial=bool(data["pareto_beneficial"]),
            delta_jaccard=float(data["delta_jaccard"]),
            delta_violation=int(data["delta_violation"]),
        )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def partition_validation_patients(
    patient_orders: Iterable[int],
    seed: int = SPLIT_SEED,
) -> tuple[frozenset[int], frozenset[int]]:
    """Preregistered deterministic 50/50 patient-level split into Dev and Audit partitions."""
    unique_orders = sorted(set(patient_orders))
    shuffled = list(unique_orders)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    n_dev = len(shuffled) // 2
    dev_set = frozenset(shuffled[:n_dev])
    audit_set = frozenset(shuffled[n_dev:])
    return dev_set, audit_set


def fit_dev_score_geometry(
    dev_candidates: list[Gate01CandidateRecord],
) -> dict[str, Any]:
    """Fit preregistered quintile score map on Idea002-Dev candidates only.

    Audit candidates/labels must NEVER participate in this function.
    """
    n_dev = len(dev_candidates)
    if n_dev == 0:
        raise ValueError("Dev candidates list is empty; cannot fit score geometry")

    sorted_scores = sorted(c.model_score for c in dev_candidates)

    cutpoints: dict[str, float] = {}
    for q in QUINTILES:
        # Nearest-rank index: ceil(q * N_D) (1-based), so index ceil(q * N_D) - 1 (0-based)
        idx = math.ceil(q * n_dev) - 1
        cutpoints[f"{q:.1f}"] = float(sorted_scores[idx])

    c02 = cutpoints["0.2"]
    c04 = cutpoints["0.4"]
    c06 = cutpoints["0.6"]
    c08 = cutpoints["0.8"]

    def _assign_bin(s: float) -> int:
        if s <= c02:
            return 1
        if s <= c04:
            return 2
        if s <= c06:
            return 3
        if s <= c08:
            return 4
        return 5

    bins: dict[int, list[Gate01CandidateRecord]] = {b: [] for b in range(1, 6)}
    for c in dev_candidates:
        bins[_assign_bin(c.model_score)].append(c)

    bin_info: dict[str, dict[str, Any]] = {}
    bin_empirical_risks: dict[int, float] = {}

    intervals = {
        1: "s <= c_0.2",
        2: "c_0.2 < s <= c_0.4",
        3: "c_0.4 < s <= c_0.6",
        4: "c_0.6 < s <= c_0.8",
        5: "s > c_0.8",
    }

    for b in range(1, 6):
        b_cands = bins[b]
        cnt = len(b_cands)
        pats = len(set(c.patient_order for c in b_cands))
        pb_count = sum(1 for c in b_cands if c.pareto_beneficial)
        pb_rate = (pb_count / cnt) if cnt > 0 else 0.0
        bin_empirical_risks[b] = pb_rate
        bin_info[f"B{b}"] = {
            "score_interval": intervals[b],
            "candidate_count": cnt,
            "distinct_patients": pats,
            "pareto_beneficial_count": pb_count,
            "empirical_pb_rate": pb_rate,
        }

    # Priority rank: higher empirical PB rate gets lower rank number (1 is highest priority)
    sorted_bins_by_risk = sorted(range(1, 6), key=lambda b: (-bin_empirical_risks[b], b))
    for rank, b in enumerate(sorted_bins_by_risk, start=1):
        bin_info[f"B{b}"]["priority_rank"] = rank

    priority_ordering = [f"B{b}" for b in sorted_bins_by_risk]

    # Check Dev candidate order equivalence with ScoreOnly
    # ScoreOnly sort key: s_t(m) asc, medication_code asc, patient_order asc, visit_order asc
    def _score_only_key(c: Gate01CandidateRecord) -> tuple[float, str, int, int]:
        return (c.model_score, c.medication_code, c.patient_order, c.visit_order)

    # ScoreGeometry sort key: g(s) desc, s asc, medication_code asc, patient_order asc, visit_order asc
    def _score_geom_key(c: Gate01CandidateRecord) -> tuple[float, float, str, int, int]:
        b = _assign_bin(c.model_score)
        g_s = bin_empirical_risks[b]
        return (-g_s, c.model_score, c.medication_code, c.patient_order, c.visit_order)

    dev_score_sorted = sorted(dev_candidates, key=_score_only_key)
    dev_geom_sorted = sorted(dev_candidates, key=_score_geom_key)

    dev_order_eq = [
        (c.patient_order, c.visit_order, c.medication_code) for c in dev_score_sorted
    ] == [(c.patient_order, c.visit_order, c.medication_code) for c in dev_geom_sorted]

    return {
        "cutpoints": cutpoints,
        "bins": bin_info,
        "bin_empirical_risks": bin_empirical_risks,
        "priority_ordering": priority_ordering,
        "order_equivalent_to_scoreonly": dev_order_eq,
        "dev_early_stop_verdict": "STOP_DEV_ORDER_EQUIVALENT" if dev_order_eq else None,
    }


def evaluate_audit_policies(
    audit_candidates: list[Gate01CandidateRecord],
    dev_cutpoints: dict[str, float],
    dev_bin_risks: dict[int, float],
) -> dict[str, Any]:
    """Evaluate policies on Audit partition candidates."""
    n_audit = len(audit_candidates)
    if n_audit == 0:
        raise ValueError("Audit candidates list is empty")

    k_by_budget: dict[str, int] = {BUDGET_LABELS[b]: math.floor(b * n_audit) for b in BUDGETS}

    # 1. Random policy: point estimate = base prevalence on Audit
    p_random = sum(1 for c in audit_candidates if c.pareto_beneficial) / n_audit

    # 2. ScoreOnly: s_t(m) asc, medication_code asc, patient_order asc, visit_order asc
    def _score_key(c: Gate01CandidateRecord) -> tuple[float, str, int, int]:
        return (c.model_score, c.medication_code, c.patient_order, c.visit_order)

    score_sorted = sorted(audit_candidates, key=_score_key)

    # 3. ScoreGeometry: g(s) desc, s asc, medication_code asc, patient_order asc, visit_order asc
    c02 = dev_cutpoints["0.2"]
    c04 = dev_cutpoints["0.4"]
    c06 = dev_cutpoints["0.6"]
    c08 = dev_cutpoints["0.8"]

    def _assign_bin(s: float) -> int:
        if s <= c02:
            return 1
        if s <= c04:
            return 2
        if s <= c06:
            return 3
        if s <= c08:
            return 4
        return 5

    def _geom_key(c: Gate01CandidateRecord) -> tuple[float, float, str, int, int]:
        b = _assign_bin(c.model_score)
        g_s = dev_bin_risks[b]
        return (-g_s, c.model_score, c.medication_code, c.patient_order, c.visit_order)

    geom_sorted = sorted(audit_candidates, key=_geom_key)

    # 4. Oracle: Y^PB desc, Delta J desc, -Delta V desc, medication_code asc, patient_order asc, visit_order asc
    def _oracle_key(c: Gate01CandidateRecord) -> tuple[int, float, int, str, int, int]:
        return (
            0 if c.pareto_beneficial else 1,
            -c.delta_jaccard,
            c.delta_violation,  # delta_violation is negative; smaller violation means larger magnitude reduction
            c.medication_code,
            c.patient_order,
            c.visit_order,
        )

    oracle_sorted = sorted(audit_candidates, key=_oracle_key)

    score_yields: dict[str, float] = {}
    geom_yields: dict[str, float] = {}
    oracle_yields: dict[str, float] = {}

    for b in BUDGETS:
        label = BUDGET_LABELS[b]
        k = k_by_budget[label]
        if k > 0:
            score_yields[label] = sum(1 for c in score_sorted[:k] if c.pareto_beneficial) / k
            geom_yields[label] = sum(1 for c in geom_sorted[:k] if c.pareto_beneficial) / k
            oracle_yields[label] = sum(1 for c in oracle_sorted[:k] if c.pareto_beneficial) / k
        else:
            score_yields[label] = 0.0
            geom_yields[label] = 0.0
            oracle_yields[label] = 0.0

    score_minus_random = {label: score_yields[label] - p_random for label in score_yields}
    geom_minus_score = {label: geom_yields[label] - score_yields[label] for label in geom_yields}
    oracle_minus_score = {
        label: oracle_yields[label] - score_yields[label] for label in oracle_yields
    }
    oracle_minus_geom = {
        label: oracle_yields[label] - geom_yields[label] for label in oracle_yields
    }

    geom_residual_capture: dict[str, float | None] = {}
    for label in geom_yields:
        denom = oracle_minus_score[label]
        if denom > 0:
            geom_residual_capture[label] = geom_minus_score[label] / denom
        else:
            geom_residual_capture[label] = None

    audit_order_eq = [
        (c.patient_order, c.visit_order, c.medication_code) for c in score_sorted
    ] == [(c.patient_order, c.visit_order, c.medication_code) for c in geom_sorted]

    return {
        "random_yield": p_random,
        "score_only_yield": score_yields,
        "score_geometry_yield": geom_yields,
        "oracle_yield": oracle_yields,
        "score_minus_random": score_minus_random,
        "geometry_minus_score": geom_minus_score,
        "oracle_minus_score": oracle_minus_score,
        "oracle_minus_geometry": oracle_minus_geom,
        "geometry_residual_capture": geom_residual_capture,
        "audit_order_equivalent_to_scoreonly": audit_order_eq,
    }


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def run_audit_patient_bootstrap(
    audit_candidates: list[Gate01CandidateRecord],
    dev_cutpoints: dict[str, float],
    dev_bin_risks: dict[int, float],
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Patient-clustered bootstrap on Audit partition with score map frozen from Dev."""
    by_patient_order: dict[int, list[Gate01CandidateRecord]] = {}
    for c in audit_candidates:
        by_patient_order.setdefault(c.patient_order, []).append(c)

    unique_orders = sorted(by_patient_order.keys())
    u = len(unique_orders)
    if u == 0:
        return {}

    rng = random.Random(seed)

    boot_score_yields: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_geom_yields: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_score_minus_random: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_geom_minus_score: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_oracle_minus_score: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_oracle_minus_geom: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_geom_rc: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}

    for _ in range(replicates):
        sampled_orders = [unique_orders[rng.randrange(u)] for _ in range(u)]
        resampled_candidates: list[Gate01CandidateRecord] = []
        for order in sampled_orders:
            resampled_candidates.extend(by_patient_order[order])

        res = evaluate_audit_policies(
            resampled_candidates,
            dev_cutpoints=dev_cutpoints,
            dev_bin_risks=dev_bin_risks,
        )

        for b in BUDGETS:
            label = BUDGET_LABELS[b]
            boot_score_yields[label].append(res["score_only_yield"][label])
            boot_geom_yields[label].append(res["score_geometry_yield"][label])
            boot_score_minus_random[label].append(res["score_minus_random"][label])
            boot_geom_minus_score[label].append(res["geometry_minus_score"][label])
            boot_oracle_minus_score[label].append(res["oracle_minus_score"][label])
            boot_oracle_minus_geom[label].append(res["oracle_minus_geometry"][label])
            rc_val = res["geometry_residual_capture"][label]
            if rc_val is not None:
                boot_geom_rc[label].append(rc_val)

    intervals: dict[str, Any] = {
        "score_only_yield": {},
        "score_geometry_yield": {},
        "score_minus_random": {},
        "geometry_minus_score": {},
        "oracle_minus_score": {},
        "oracle_minus_geometry": {},
        "geometry_residual_capture": {},
    }
    for b in BUDGETS:
        label = BUDGET_LABELS[b]
        intervals["score_only_yield"][label] = {
            "lower": _percentile(boot_score_yields[label], 0.025),
            "upper": _percentile(boot_score_yields[label], 0.975),
        }
        intervals["score_geometry_yield"][label] = {
            "lower": _percentile(boot_geom_yields[label], 0.025),
            "upper": _percentile(boot_geom_yields[label], 0.975),
        }
        intervals["score_minus_random"][label] = {
            "lower": _percentile(boot_score_minus_random[label], 0.025),
            "upper": _percentile(boot_score_minus_random[label], 0.975),
        }
        intervals["geometry_minus_score"][label] = {
            "lower": _percentile(boot_geom_minus_score[label], 0.025),
            "upper": _percentile(boot_geom_minus_score[label], 0.975),
        }
        intervals["oracle_minus_score"][label] = {
            "lower": _percentile(boot_oracle_minus_score[label], 0.025),
            "upper": _percentile(boot_oracle_minus_score[label], 0.975),
        }
        intervals["oracle_minus_geometry"][label] = {
            "lower": _percentile(boot_oracle_minus_geom[label], 0.025),
            "upper": _percentile(boot_oracle_minus_geom[label], 0.975),
        }
        if boot_geom_rc[label]:
            intervals["geometry_residual_capture"][label] = {
                "lower": _percentile(boot_geom_rc[label], 0.025),
                "upper": _percentile(boot_geom_rc[label], 0.975),
            }
        else:
            intervals["geometry_residual_capture"][label] = None

    return intervals


def evaluate_gate_01_decision_tree(
    support_sufficient: bool,
    intervals_95: dict[str, Any],
) -> tuple[str, dict[str, bool]]:
    """Formal preregistered Gate 01 decision tree (§14 of protocol)."""
    if not support_sufficient:
        criteria = {
            "support_requirement_met": False,
            "residual_headroom_survives_score_10": False,
            "residual_headroom_survives_score_20": False,
            "geometry_beats_score_10": False,
            "geometry_beats_score_20": False,
        }
        return "INSUFFICIENT_SUPPORT", criteria

    ci_o_s_10 = intervals_95["oracle_minus_score"]["10%"]["lower"] > 0.0
    ci_o_s_20 = intervals_95["oracle_minus_score"]["20%"]["lower"] > 0.0
    residual_headroom_holds = ci_o_s_10 and ci_o_s_20

    ci_g_s_10 = intervals_95["geometry_minus_score"]["10%"]["lower"] > 0.0
    ci_g_s_20 = intervals_95["geometry_minus_score"]["20%"]["lower"] > 0.0
    geometry_beats_score = ci_g_s_10 and ci_g_s_20

    criteria = {
        "support_requirement_met": True,
        "residual_headroom_survives_score_10": ci_o_s_10,
        "residual_headroom_survives_score_20": ci_o_s_20,
        "geometry_beats_score_10": ci_g_s_10,
        "geometry_beats_score_20": ci_g_s_20,
    }

    # Gate 01-B: Does residual headroom still exist on Audit?
    if not residual_headroom_holds:
        return "STOP_NO_RELIABLE_RESIDUAL_HEADROOM", criteria

    # Gate 01-C: Does low-complexity score map beat ScoreOnly?
    if geometry_beats_score:
        return "PASS_INCREMENTAL_SCORE_GEOMETRY", criteria
    return "STOP_NO_INCREMENTAL_SCORE_GEOMETRY", criteria


def run_gate_01(
    *,
    candidate_corpus: Path,
    output_root: Path,
    validation_patient_count: int = FROZEN_VALIDATION_PATIENT_COUNT,
    dev_early_stop: bool = False,
    harness_revision: str | None = None,
    summary_output: Path | None = None,
) -> dict[str, Any]:
    """Execute Gate 01 — Score-Geometry Sufficiency."""
    candidate_corpus = candidate_corpus.resolve()
    output_root = output_root.resolve()

    if not candidate_corpus.exists():
        raise FileNotFoundError(f"Candidate corpus not found: {candidate_corpus}")

    if output_root.exists():
        raise FileExistsError(
            f"output_root already exists: {output_root}. Gate 01 requires a fresh output directory."
        )
    output_root.mkdir(parents=True, exist_ok=False)

    corpus_sha256 = _file_sha256(candidate_corpus)

    # 1. Deterministic validation patient partition (50% Dev / 50% Audit) from full validation patient universe
    dev_patients, audit_patients = partition_validation_patients(
        range(validation_patient_count), seed=SPLIT_SEED
    )

    # 2. Read candidate corpus, assign fresh partitions, ignore historical gate02_partition
    candidates: list[Gate01CandidateRecord] = []
    dev_candidates: list[Gate01CandidateRecord] = []
    audit_candidates: list[Gate01CandidateRecord] = []

    with candidate_corpus.open("r", encoding="utf-8") as stream:
        for line in stream:
            line_str = line.strip()
            if not line_str:
                continue
            row = json.loads(line_str)
            p_order = int(row["patient_order"])
            if p_order in dev_patients:
                part = "dev"
            elif p_order in audit_patients:
                part = "audit"
            else:
                raise ValueError(
                    f"Patient order {p_order} not in validation universe range({validation_patient_count})"
                )

            rec = Gate01CandidateRecord.from_dict(row, partition=part)
            candidates.append(rec)
            if part == "dev":
                dev_candidates.append(rec)
            else:
                audit_candidates.append(rec)

    # Write restricted candidate artifact with fresh partitions
    cand_out_path = output_root / "gate-01-candidates.jsonl"
    with cand_out_path.open("w", encoding="utf-8") as stream:
        for c in candidates:
            stream.write(json.dumps(c.to_dict(), separators=(",", ":")) + "\n")

    # 3. Fit quintile map on Dev partition only
    dev_map = fit_dev_score_geometry(dev_candidates)

    dev_map_path = output_root / "gate-01-dev-map.json"
    with dev_map_path.open("w", encoding="utf-8") as stream:
        json.dump(dev_map, stream, indent=2, sort_keys=True)

    # Dev-only early stop check
    dev_order_eq = bool(dev_map["order_equivalent_to_scoreonly"])
    if dev_early_stop and dev_order_eq:
        verdict = "STOP_DEV_ORDER_EQUIVALENT"
        summary: dict[str, Any] = {
            "schema_version": 1,
            "idea_id": "002-score-geometry-sufficiency",
            "gate_id": "gate-01-score-geometry-sufficiency",
            "verdict": verdict,
            "harness_revision": harness_revision,
            "upstream_audited_candidate_source": {
                "run_id": FROZEN_UPSTREAM_RUN_ID,
                "sha256": corpus_sha256,
                "row_count": len(candidates),
            },
            "identities": {
                "dataset_manifest_sha256": FROZEN_DATASET_MANIFEST_SHA256,
                "dataset_id": FROZEN_DATASET_ID,
                "snapshot_id": FROZEN_SNAPSHOT_ID,
                "snapshot_sha256": FROZEN_SNAPSHOT_SHA256,
                "medication_vocabulary_sha256": FROZEN_MEDICATION_VOCABULARY_SHA256,
                "ddi_asset_sha256": FROZEN_DDI_ASSET_SHA256,
                "baseline_environment_name": FROZEN_BASELINE_ENVIRONMENT_NAME,
                "model_source_revision": FROZEN_MOLEREC_REVISION,
                "checkpoint_sha256": "5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca",
                "baseline_core_sha256": FROZEN_BASELINE_CORE_SHA256,
                "adapter_sha256": FROZEN_ADAPTER_SHA256,
            },
            "split": {
                "source": "validation",
                "patient_level": True,
                "seed": SPLIT_SEED,
                "validation_patient_universe_count": validation_patient_count,
                "dev_patient_count": len(dev_patients),
                "dev_eligible_patient_count": len(set(c.patient_order for c in dev_candidates)),
                "dev_candidate_count": len(dev_candidates),
                "audit_patient_count": len(audit_patients),
                "audit_eligible_patient_count": len(set(c.patient_order for c in audit_candidates)),
                "audit_candidate_count": len(audit_candidates),
            },
            "dev_score_geometry": dev_map,
            "audit_support": None,
            "policy_yields": None,
            "gaps": None,
            "residual_capture": None,
            "bootstrap": None,
            "decision_criteria": {
                "dev_order_equivalent_to_scoreonly": True,
                "dev_early_stop_triggered": True,
            },
        }
        summary_path = output_root / "gate-01-summary.json"
        with summary_path.open("w", encoding="utf-8") as stream:
            json.dump(summary, stream, indent=2, sort_keys=True)
        if summary_output is not None:
            summary_output.parent.mkdir(parents=True, exist_ok=True)
            with summary_output.open("w", encoding="utf-8") as stream:
                json.dump(summary, stream, indent=2, sort_keys=True)
        return summary

    # 4. Audit support check
    audit_beneficial_patients = len(
        set(c.patient_order for c in audit_candidates if c.pareto_beneficial)
    )
    audit_non_beneficial_patients = len(
        set(c.patient_order for c in audit_candidates if not c.pareto_beneficial)
    )
    support_sufficient = (audit_beneficial_patients >= 50) and (audit_non_beneficial_patients >= 50)

    # 5. Evaluate policies on Audit partition
    audit_eval = evaluate_audit_policies(
        audit_candidates,
        dev_cutpoints=dev_map["cutpoints"],
        dev_bin_risks=dev_map["bin_empirical_risks"],
    )

    # 6. Patient-clustered bootstrap on Audit partition
    intervals_95 = run_audit_patient_bootstrap(
        audit_candidates,
        dev_cutpoints=dev_map["cutpoints"],
        dev_bin_risks=dev_map["bin_empirical_risks"],
        replicates=BOOTSTRAP_REPLICATES,
        seed=BOOTSTRAP_SEED,
    )

    # 7. Evaluate formal decision tree
    verdict, criteria = evaluate_gate_01_decision_tree(
        support_sufficient=support_sufficient,
        intervals_95=intervals_95,
    )

    # Add Dev early stop condition tracking to decision criteria
    criteria["dev_order_equivalent_to_scoreonly"] = dev_order_eq
    criteria["dev_early_stop_verdict"] = "STOP_DEV_ORDER_EQUIVALENT" if dev_order_eq else None

    summary = {
        "schema_version": 1,
        "idea_id": "002-score-geometry-sufficiency",
        "gate_id": "gate-01-score-geometry-sufficiency",
        "verdict": verdict,
        "harness_revision": harness_revision,
        "upstream_audited_candidate_source": {
            "run_id": FROZEN_UPSTREAM_RUN_ID,
            "sha256": corpus_sha256,
            "row_count": len(candidates),
        },
        "identities": {
            "dataset_manifest_sha256": FROZEN_DATASET_MANIFEST_SHA256,
            "dataset_id": FROZEN_DATASET_ID,
            "snapshot_id": FROZEN_SNAPSHOT_ID,
            "snapshot_sha256": FROZEN_SNAPSHOT_SHA256,
            "medication_vocabulary_sha256": FROZEN_MEDICATION_VOCABULARY_SHA256,
            "ddi_asset_sha256": FROZEN_DDI_ASSET_SHA256,
            "baseline_environment_name": FROZEN_BASELINE_ENVIRONMENT_NAME,
            "model_source_revision": FROZEN_MOLEREC_REVISION,
            "checkpoint_sha256": "5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca",
            "baseline_core_sha256": FROZEN_BASELINE_CORE_SHA256,
            "adapter_sha256": FROZEN_ADAPTER_SHA256,
        },
        "split": {
            "source": "validation",
            "patient_level": True,
            "seed": SPLIT_SEED,
            "validation_patient_universe_count": validation_patient_count,
            "dev_patient_count": len(dev_patients),
            "dev_eligible_patient_count": len(set(c.patient_order for c in dev_candidates)),
            "dev_candidate_count": len(dev_candidates),
            "audit_patient_count": len(audit_patients),
            "audit_eligible_patient_count": len(set(c.patient_order for c in audit_candidates)),
            "audit_candidate_count": len(audit_candidates),
        },
        "dev_score_geometry": {
            "cutpoints": dev_map["cutpoints"],
            "bins": dev_map["bins"],
            "priority_ordering": dev_map["priority_ordering"],
            "order_equivalent_to_scoreonly": dev_map["order_equivalent_to_scoreonly"],
            "dev_early_stop_verdict": dev_map["dev_early_stop_verdict"],
        },
        "audit_support": {
            "audit_eligible_candidates": len(audit_candidates),
            "audit_eligible_patients": len(set(c.patient_order for c in audit_candidates)),
            "audit_beneficial_patients": audit_beneficial_patients,
            "audit_non_beneficial_patients": audit_non_beneficial_patients,
            "support_sufficient": support_sufficient,
        },
        "policy_yields": {
            "random": {"yield": audit_eval["random_yield"]},
            "score_only": audit_eval["score_only_yield"],
            "score_geometry": audit_eval["score_geometry_yield"],
            "oracle": audit_eval["oracle_yield"],
        },
        "gaps": {
            "score_minus_random": audit_eval["score_minus_random"],
            "geometry_minus_score": audit_eval["geometry_minus_score"],
            "oracle_minus_score": audit_eval["oracle_minus_score"],
            "oracle_minus_geometry": audit_eval["oracle_minus_geometry"],
        },
        "residual_capture": {
            "geometry": audit_eval["geometry_residual_capture"],
        },
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "unit": "patient",
            "intervals_95": intervals_95,
        },
        "decision_criteria": criteria,
    }

    summary_path = output_root / "gate-01-summary.json"
    with summary_path.open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)

    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        with summary_output.open("w", encoding="utf-8") as stream:
            json.dump(summary, stream, indent=2, sort_keys=True)

    return summary


def self_test_gate_01() -> None:
    """Focused synthetic self-test suite covering critical changed paths."""
    print("Running Gate 01 synthetic self-test suite...")

    # 1. Check patient split: seed 2002, 50/50, patient-disjoint, sensitive to universe
    orders = list(range(100))
    dev1, audit1 = partition_validation_patients(orders, seed=2002)
    dev2, audit2 = partition_validation_patients(orders, seed=2002)
    assert dev1 == dev2
    assert audit1 == audit2
    assert len(dev1) == 50
    assert len(audit1) == 50
    assert len(dev1 & audit1) == 0

    # Omitting a patient drifts seeded shuffle
    orders_missing = [i for i in range(100) if i != 42]
    dev_drift, _ = partition_validation_patients(orders_missing, seed=2002)
    assert dev_drift != dev1 - {42}

    # 2. Check Dev-only quintile map calculation and firewall
    # Create 50 Dev candidates with scores uniformly spanning [0.1, 0.99]
    # In B1 (lowest scores), set PB=True (rate 1.0)
    # In B5 (highest scores), set PB=False (rate 0.0)
    dev_synthetic: list[Gate01CandidateRecord] = []
    for i in range(50):
        s = 0.10 + i * (0.80 / 49)
        # Even i: non-beneficial, odd i: beneficial
        is_pb = i < 10  # B1 has PB=True, others have PB=False
        dev_synthetic.append(
            Gate01CandidateRecord(
                patient_id=f"p_{i}",
                visit_id=f"v_{i}",
                patient_order=i,
                visit_order=1,
                gate01_partition="dev",
                medication_code=f"M_{i:02d}",
                model_score=s,
                active_ddi_degree=1,
                pareto_beneficial=is_pb,
                delta_jaccard=0.1 if is_pb else -0.1,
                delta_violation=-1,
            )
        )

    dev_map = fit_dev_score_geometry(dev_synthetic)
    assert len(dev_map["cutpoints"]) == 4
    assert len(dev_map["bins"]) == 5
    # B1 has PB=1.0, B2..B5 have PB=0.0
    assert dev_map["bins"]["B1"]["empirical_pb_rate"] == 1.0
    assert dev_map["bins"]["B5"]["empirical_pb_rate"] == 0.0

    # 3. Check deterministic ordering
    # If B1 has PB=1.0 and B2..B5 have PB=0.0, then B1 is ranked priority 1, B2..B5 priority 2..5
    # Since B1 has lowest scores, ScoreGeometry orders B1 candidates first (g(s) desc),
    # which is the same as ScoreOnly (s asc)!
    # Now let's construct an inverted Dev case where high scores have higher PB rate:
    # B5 (high scores) has PB=True, B1 (low scores) has PB=False
    dev_non_monotonic: list[Gate01CandidateRecord] = []
    for i in range(50):
        s = 0.10 + i * (0.80 / 49)
        is_pb = i >= 40  # B5 has PB=True, B1..B4 have PB=False
        dev_non_monotonic.append(
            Gate01CandidateRecord(
                patient_id=f"p_{i}",
                visit_id=f"v_{i}",
                patient_order=i,
                visit_order=1,
                gate01_partition="dev",
                medication_code=f"M_{i:02d}",
                model_score=s,
                active_ddi_degree=1,
                pareto_beneficial=is_pb,
                delta_jaccard=0.1 if is_pb else -0.1,
                delta_violation=-1,
            )
        )
    nm_map = fit_dev_score_geometry(dev_non_monotonic)
    assert nm_map["bins"]["B5"]["empirical_pb_rate"] == 1.0
    assert nm_map["bins"]["B1"]["empirical_pb_rate"] == 0.0
    assert nm_map["bins"]["B5"]["priority_rank"] == 1
    # Because B5 is priority 1, high score candidates come first in ScoreGeometry,
    # but LAST in ScoreOnly! So order_equivalent_to_scoreonly MUST be False!
    assert nm_map["order_equivalent_to_scoreonly"] is False

    # 4. Check Decision Tree behavior: positive vs null/stop
    # Synthetic positive: Lower CI of Geometry - Score > 0 at 10% and 20%
    pos_intervals = {
        "oracle_minus_score": {
            "10%": {"lower": 0.20, "upper": 0.40},
            "20%": {"lower": 0.25, "upper": 0.45},
        },
        "geometry_minus_score": {
            "10%": {"lower": 0.05, "upper": 0.15},
            "20%": {"lower": 0.03, "upper": 0.12},
        },
    }
    v_pos, crit_pos = evaluate_gate_01_decision_tree(True, pos_intervals)
    assert v_pos == "PASS_INCREMENTAL_SCORE_GEOMETRY"
    assert crit_pos["geometry_beats_score_10"] is True
    assert crit_pos["geometry_beats_score_20"] is True

    # Synthetic null: Geometry - Score lower CI is 0.0 <= 0
    null_intervals = {
        "oracle_minus_score": {
            "10%": {"lower": 0.20, "upper": 0.40},
            "20%": {"lower": 0.25, "upper": 0.45},
        },
        "geometry_minus_score": {
            "10%": {"lower": 0.0, "upper": 0.0},
            "20%": {"lower": 0.0, "upper": 0.0},
        },
    }
    v_null, crit_null = evaluate_gate_01_decision_tree(True, null_intervals)
    assert v_null == "STOP_NO_INCREMENTAL_SCORE_GEOMETRY"
    assert crit_null["geometry_beats_score_10"] is False

    # Synthetic insufficient support
    v_supp, crit_supp = evaluate_gate_01_decision_tree(False, pos_intervals)
    assert v_supp == "INSUFFICIENT_SUPPORT"
    assert crit_supp["support_requirement_met"] is False

    # Synthetic no residual headroom
    no_headroom_intervals = {
        "oracle_minus_score": {
            "10%": {"lower": -0.05, "upper": 0.02},
            "20%": {"lower": 0.25, "upper": 0.45},
        },
        "geometry_minus_score": {
            "10%": {"lower": 0.05, "upper": 0.15},
            "20%": {"lower": 0.03, "upper": 0.12},
        },
    }
    v_head, _crit_head = evaluate_gate_01_decision_tree(True, no_headroom_intervals)
    assert v_head == "STOP_NO_RELIABLE_RESIDUAL_HEADROOM"

    print("Gate 01 synthetic self-test passed successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test", action="store_true", help="Run focused synthetic self-test suite"
    )
    parser.add_argument(
        "--candidate-corpus", type=Path, help="Path to input candidate corpus JSONL"
    )
    parser.add_argument("--output-root", type=Path, help="Directory to save restricted artifacts")
    parser.add_argument(
        "--summary-output", type=Path, help="Optional path to save public gate-01-summary.json"
    )
    parser.add_argument(
        "--validation-patient-count",
        type=int,
        default=FROZEN_VALIDATION_PATIENT_COUNT,
        help="Total validation patient count in universe (default 1059)",
    )
    parser.add_argument(
        "--dev-early-stop",
        action="store_true",
        help="Enforce stopping at Dev if candidate ordering is equivalent to ScoreOnly",
    )
    parser.add_argument(
        "--expected-harness-revision",
        type=str,
        help="Optional expected git commit hash for harness",
    )
    args = parser.parse_args()

    if args.self_test:
        self_test_gate_01()
        return

    if args.candidate_corpus is None or args.output_root is None:
        parser.error(
            "--candidate-corpus and --output-root are required unless --self-test is specified"
        )

    harness_root = Path(__file__).resolve().parents[4]
    harness_rev = _git_revision(harness_root)
    if args.expected_harness_revision and harness_rev != args.expected_harness_revision:
        raise ValueError(
            f"Harness revision drift: expected {args.expected_harness_revision}, got {harness_rev}"
        )

    summary = run_gate_01(
        candidate_corpus=args.candidate_corpus,
        output_root=args.output_root,
        validation_patient_count=args.validation_patient_count,
        dev_early_stop=args.dev_early_stop,
        harness_revision=harness_rev,
        summary_output=args.summary_output,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "dev_score_geometry": {
                    "order_equivalent_to_scoreonly": summary["dev_score_geometry"][
                        "order_equivalent_to_scoreonly"
                    ],
                    "priority_ordering": summary["dev_score_geometry"]["priority_ordering"],
                },
                "audit_support": summary["audit_support"],
                "policy_yields": summary["policy_yields"],
                "gaps": summary["gaps"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
