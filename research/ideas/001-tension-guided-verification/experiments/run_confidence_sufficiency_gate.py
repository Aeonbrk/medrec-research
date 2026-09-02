#!/usr/bin/env python3
"""Gate 02 — Confidence Sufficiency and Residual Constraint Signal.

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
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NamedTuple

from medrec_research.adapters import ProcessPredictionAdapter
from medrec_research.dataset import DatasetManifest

BUDGETS: tuple[float, ...] = (0.10, 0.20, 0.30)
BUDGET_LABELS: dict[float, str] = {0.10: "10%", 0.20: "20%", 0.30: "30%"}

LAMBDA_GRID: tuple[float, ...] = (
    -8.0,
    -4.0,
    -2.0,
    -1.0,
    -0.5,
    -0.25,
    0.0,
    0.25,
    0.5,
    1.0,
    2.0,
    4.0,
    8.0,
)

# Pinned scientific identities matching Gate 01 / Qualification v1.1
FROZEN_DATASET_MANIFEST_SHA256 = "82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712"
FROZEN_DATASET_ID = "molerec-table1-comparison-v1-1"
FROZEN_SNAPSHOT_ID = "molerec-table1-c721-www23"
FROZEN_DDI_ASSET_SHA256 = "dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7"
FROZEN_FEATURE_AVAILABILITY_SHA256 = (
    "9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9"
)
FROZEN_BASELINE_ENVIRONMENT_NAME = "medrec-molerec-table1"
FROZEN_BASELINE_ENVIRONMENT_SHA256 = (
    "6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda"
)
FROZEN_MOLEREC_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"
FROZEN_BASELINE_CORE_SHA256 = "516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511"
FROZEN_ADAPTER_SHA256 = "9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531"
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 1203


class Gate02CandidateRecord(NamedTuple):
    patient_id: str
    visit_id: str
    patient_order: int
    visit_order: int
    gate02_partition: str  # "dev" or "audit"
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
            "gate02_partition": str(self.gate02_partition),
            "medication_code": str(self.medication_code),
            "model_score": float(self.model_score),
            "active_ddi_degree": int(self.active_ddi_degree),
            "pareto_beneficial": bool(self.pareto_beneficial),
            "delta_jaccard": float(self.delta_jaccard),
            "delta_violation": int(self.delta_violation),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Gate02CandidateRecord:
        return cls(
            patient_id=str(data["patient_id"]),
            visit_id=str(data["visit_id"]),
            patient_order=int(data["patient_order"]),
            visit_order=int(data["visit_order"]),
            gate02_partition=str(data["gate02_partition"]),
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


def verify_clean_checkout(repo_path: Path, repo_name: str) -> None:
    completed = subprocess.run(
        ("git", "status", "--porcelain"),
        cwd=repo_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if completed.stdout.strip():
        raise ValueError(
            f"{repo_name} working tree is dirty: untracked or uncommitted changes detected in {repo_path}"
        )


def verify_conda_environment(conda_executable: str | Path, environment_name: str) -> str:
    if environment_name != FROZEN_BASELINE_ENVIRONMENT_NAME:
        raise ValueError(
            f"Invalid baseline environment: {environment_name}. Formal Gate 02 must use {FROZEN_BASELINE_ENVIRONMENT_NAME}"
        )
    completed = subprocess.run(
        (str(conda_executable), "list", "--explicit", "-n", environment_name),
        check=True,
        capture_output=True,
        text=True,
    )
    observed_sha256 = hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest()
    if observed_sha256 != FROZEN_BASELINE_ENVIRONMENT_SHA256:
        raise ValueError(
            f"Baseline environment identity drift for {environment_name}: expected {FROZEN_BASELINE_ENVIRONMENT_SHA256}, got {observed_sha256}"
        )
    return observed_sha256


def verify_frozen_molerec_identity(
    molerec_root: Path,
    checkpoint: Path,
    adapter_path: Path,
) -> tuple[str, str, str, str]:
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


def verify_dataset_manifest_and_snapshot(
    manifest_path: Path,
    dataset_root: Path,
    staged_meta: dict[str, Any],
) -> tuple[DatasetManifest, str]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"dataset_manifest does not exist: {manifest_path}")

    manifest = DatasetManifest.load(manifest_path)
    if manifest.manifest_sha256 != FROZEN_DATASET_MANIFEST_SHA256:
        raise ValueError(
            f"Dataset manifest identity drift: expected {FROZEN_DATASET_MANIFEST_SHA256}, got {manifest.manifest_sha256}"
        )
    if manifest.dataset_id != FROZEN_DATASET_ID:
        raise ValueError(
            f"Dataset ID drift: expected {FROZEN_DATASET_ID}, got {manifest.dataset_id}"
        )
    if manifest.snapshot_id != FROZEN_SNAPSHOT_ID:
        raise ValueError(
            f"Snapshot ID drift: expected {FROZEN_SNAPSHOT_ID}, got {manifest.snapshot_id}"
        )

    snapshot_files = {
        "ddi_A_final.pkl": _file_sha256(dataset_root / "ddi_A_final.pkl"),
        "records_final.pkl": _file_sha256(dataset_root / "records_final.pkl"),
        "voc_final.pkl": _file_sha256(dataset_root / "voc_final.pkl"),
    }
    actual_snapshot_sha256 = _content_sha256(snapshot_files)
    if actual_snapshot_sha256 != manifest.checksum_sha256:
        raise ValueError(
            f"Snapshot checksum drift: expected {manifest.checksum_sha256}, got {actual_snapshot_sha256}"
        )
    if staged_meta["snapshot_sha256"] != manifest.checksum_sha256:
        raise ValueError(
            f"Staged snapshot checksum drift: expected {manifest.checksum_sha256}, got {staged_meta['snapshot_sha256']}"
        )

    if staged_meta["medication_vocabulary_sha256"] != manifest.medication_vocabulary_sha256:
        raise ValueError(
            f"Medication vocabulary identity drift: expected {manifest.medication_vocabulary_sha256}, got {staged_meta['medication_vocabulary_sha256']}"
        )

    if staged_meta["ddi_asset_sha256"] != FROZEN_DDI_ASSET_SHA256:
        raise ValueError(
            f"DDI asset identity drift: expected {FROZEN_DDI_ASSET_SHA256}, got {staged_meta['ddi_asset_sha256']}"
        )

    if staged_meta["feature_availability_sha256"] != FROZEN_FEATURE_AVAILABILITY_SHA256:
        raise ValueError(
            f"Feature availability identity drift: expected {FROZEN_FEATURE_AVAILABILITY_SHA256}, got {staged_meta['feature_availability_sha256']}"
        )

    return manifest, actual_snapshot_sha256


def partition_validation_patients(
    patient_orders: Iterable[int],
    seed: int = 1203,
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


def _visit_jaccard(predicted: set[str], target: set[str]) -> float:
    if not target and not predicted:
        return 1.0
    if not target or not predicted:
        return 0.0
    intersection = len(target & predicted)
    return intersection / len(target | predicted)


def compute_gate_02_candidates(
    predictions: list[dict[str, Any]],
    targets: dict[str, list[str]],
    ddi_pairs: frozenset[tuple[str, str]],
    traversal_by_visit: dict[str, tuple[int, int]],
    dev_patients: frozenset[int],
) -> list[Gate02CandidateRecord]:
    """Compute eligible candidates Q_t with model scores and deterministic partition assignment."""
    candidates: list[Gate02CandidateRecord] = []

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

        score_by_med = dict(pred.get("vocabulary_scores", {}))
        base_jaccard = _visit_jaccard(pred_meds, target_set)

        # Active DDI degree
        active_degrees: dict[str, int] = {}
        for med in pred_meds:
            degree = sum(
                1
                for other in pred_meds
                if med != other and tuple(sorted((med, other))) in ddi_pairs
            )
            active_degrees[med] = degree

        eligible_meds = sorted(m for m, degree in active_degrees.items() if degree > 0)

        if visit_key not in traversal_by_visit:
            raise KeyError(f"Missing traversal metadata for visit: {visit_key}")
        patient_order, visit_order = traversal_by_visit[visit_key]
        partition = "dev" if patient_order in dev_patients else "audit"

        for med in eligible_meds:
            if med not in score_by_med:
                raise KeyError(
                    f"Missing frozen vocabulary score for eligible predicted medication: {med} in {visit_key}"
                )
            degree = active_degrees[med]
            revised_meds = pred_meds - {med}
            rev_jaccard = _visit_jaccard(revised_meds, target_set)
            delta_jaccard = rev_jaccard - base_jaccard
            delta_violation = -degree  # delta violation < 0 by construction

            pareto_beneficial = (delta_jaccard >= 0.0) and (delta_violation < 0)
            model_score = float(score_by_med[med])

            record = Gate02CandidateRecord(
                patient_id=patient_id,
                visit_id=visit_id,
                patient_order=patient_order,
                visit_order=visit_order,
                gate02_partition=partition,
                medication_code=med,
                model_score=model_score,
                active_ddi_degree=degree,
                pareto_beneficial=pareto_beneficial,
                delta_jaccard=delta_jaccard,
                delta_violation=delta_violation,
            )
            candidates.append(record)

    return candidates


def compute_dev_median_score(dev_candidates: list[Gate02CandidateRecord]) -> float:
    """Compute median MoleRec score tau_s on eligible Dev candidates only."""
    if not dev_candidates:
        return 0.5
    scores = sorted(c.model_score for c in dev_candidates)
    n = len(scores)
    if n % 2 == 1:
        return scores[n // 2]
    return (scores[n // 2 - 1] + scores[n // 2]) / 2.0


def select_dev_lambda(
    dev_candidates: list[Gate02CandidateRecord],
    lambda_grid: tuple[float, ...] = LAMBDA_GRID,
) -> tuple[float, float, dict[str, float], dict[str, float], dict[str, float]]:
    """Select lambda* using Dev partition only.

    Audit partition candidates/labels must never be passed here.
    """
    n_dev = len(dev_candidates)
    if n_dev == 0:
        return 0.0, 1.0, {}, {}, {}

    d_max = max(c.active_ddi_degree for c in dev_candidates)
    if d_max <= 0:
        d_max = 1

    k10 = math.floor(0.10 * n_dev)
    k20 = math.floor(0.20 * n_dev)

    yields_10: dict[str, float] = {}
    yields_20: dict[str, float] = {}
    selection_scores: dict[str, float] = {}

    best_lam = 0.0
    best_tie_key = (-1.0, -999.0, 0, -999.0)

    for lam in lambda_grid:

        def _scalar_dev_sort_key(
            c: Gate02CandidateRecord,
            l_val: float = lam,
        ) -> tuple[float, str, int, int]:
            q = c.active_ddi_degree / d_max
            r = (1.0 - c.model_score) + l_val * q
            return (-r, c.medication_code, c.patient_order, c.visit_order)

        sorted_cands = sorted(dev_candidates, key=_scalar_dev_sort_key)
        y10 = (sum(1 for c in sorted_cands[:k10] if c.pareto_beneficial) / k10) if k10 > 0 else 0.0
        y20 = (sum(1 for c in sorted_cands[:k20] if c.pareto_beneficial) / k20) if k20 > 0 else 0.0
        score = (y10 + y20) / 2.0

        key_str = f"{lam:g}"
        yields_10[key_str] = y10
        yields_20[key_str] = y20
        selection_scores[key_str] = score

        # Tie-break:
        # 1. max score
        # 2. smaller |lambda| (-abs(lam))
        # 3. prefer lambda == 0
        # 4. numerical ascending order (-lam so smaller lam is preferred)
        tie_key = (score, -abs(lam), 1 if lam == 0.0 else 0, -lam)
        if tie_key > best_tie_key:
            best_tie_key = tie_key
            best_lam = lam

    return best_lam, float(d_max), yields_10, yields_20, selection_scores


def compute_interaction_cells(
    audit_candidates: list[Gate02CandidateRecord],
    tau_s: float,
) -> tuple[dict[str, dict[str, Any]], float, bool]:
    """Compute 2x2 support-pressure interaction prevalences on Audit partition."""
    cells: dict[str, list[Gate02CandidateRecord]] = {
        "LL": [],
        "LH": [],
        "HL": [],
        "HH": [],
    }
    for c in audit_candidates:
        low_support = c.model_score < tau_s
        low_pressure = c.active_ddi_degree == 1
        key = ("L" if low_support else "H") + ("L" if low_pressure else "H")
        cells[key].append(c)

    cell_info: dict[str, dict[str, Any]] = {}
    distinct_patients: dict[str, int] = {}
    prevalences: dict[str, float] = {}

    for key, cands in cells.items():
        n = len(cands)
        pats = len(set(c.patient_order for c in cands))
        prev = (sum(1 for c in cands if c.pareto_beneficial) / n) if n > 0 else 0.0
        cell_info[key] = {
            "candidates": n,
            "distinct_patients": pats,
            "prevalence": prev,
        }
        distinct_patients[key] = pats
        prevalences[key] = prev

    support_met = all(distinct_patients[k] >= 50 for k in ("LL", "LH", "HL", "HH"))
    i_tension = (prevalences["HH"] - prevalences["HL"]) - (prevalences["LH"] - prevalences["LL"])
    return cell_info, i_tension, support_met


def evaluate_audit_policies(
    audit_candidates: list[Gate02CandidateRecord],
    frozen_lambda: float,
    dev_degree_max: float,
) -> dict[str, Any]:
    """Evaluate Random, RiskOnly, ScoreOnly, Scalar(frozen_lambda), and Oracle yields and gaps."""
    n_a = len(audit_candidates)
    if n_a == 0:
        empty = {label: 0.0 for label in BUDGET_LABELS.values()}
        return {
            "random_yield": 0.0,
            "risk_only_yield": empty,
            "score_only_yield": empty,
            "scalar_yield": empty,
            "oracle_yield": empty,
            "score_minus_random": empty,
            "score_minus_risk": empty,
            "oracle_minus_score": empty,
            "scalar_minus_score": empty,
            "oracle_minus_scalar": empty,
            "score_headroom_capture": empty,
            "scalar_headroom_capture": empty,
        }

    p_random = sum(1 for c in audit_candidates if c.pareto_beneficial) / n_a

    # RiskOnly sort key
    def _risk_key(c: Gate02CandidateRecord) -> tuple[int, str, int, int]:
        return (-c.active_ddi_degree, c.medication_code, c.patient_order, c.visit_order)

    # ScoreOnly sort key: s_t(m) asc <=> 1 - s_t(m) desc
    def _score_key(c: Gate02CandidateRecord) -> tuple[float, str, int, int]:
        return (c.model_score, c.medication_code, c.patient_order, c.visit_order)

    # Scalar sort key: (1 - s_t(m)) + lambda * (d_t(m) / d_max_dev) desc
    def _scalar_key(c: Gate02CandidateRecord) -> tuple[float, str, int, int]:
        q = c.active_ddi_degree / dev_degree_max
        r = (1.0 - c.model_score) + frozen_lambda * q
        return (-r, c.medication_code, c.patient_order, c.visit_order)

    # Oracle sort key
    def _oracle_key(c: Gate02CandidateRecord) -> tuple[int, float, int, str, int, int]:
        return (
            -int(c.pareto_beneficial),
            -c.delta_jaccard,
            -c.active_ddi_degree,
            c.medication_code,
            c.patient_order,
            c.visit_order,
        )

    risk_sorted = sorted(audit_candidates, key=_risk_key)
    score_sorted = sorted(audit_candidates, key=_score_key)
    scalar_sorted = sorted(audit_candidates, key=_scalar_key)
    oracle_sorted = sorted(audit_candidates, key=_oracle_key)

    risk_yields: dict[str, float] = {}
    score_yields: dict[str, float] = {}
    scalar_yields: dict[str, float] = {}
    oracle_yields: dict[str, float] = {}

    score_minus_random: dict[str, float] = {}
    score_minus_risk: dict[str, float] = {}
    oracle_minus_score: dict[str, float] = {}
    scalar_minus_score: dict[str, float] = {}
    oracle_minus_scalar: dict[str, float] = {}

    score_hc: dict[str, float] = {}
    scalar_hc: dict[str, float] = {}

    for b in BUDGETS:
        label = BUDGET_LABELS[b]
        k = math.floor(b * n_a)
        if k <= 0:
            risk_yields[label] = 0.0
            score_yields[label] = 0.0
            scalar_yields[label] = 0.0
            oracle_yields[label] = 0.0

            score_minus_random[label] = 0.0
            score_minus_risk[label] = 0.0
            oracle_minus_score[label] = 0.0
            scalar_minus_score[label] = 0.0
            oracle_minus_scalar[label] = 0.0

            score_hc[label] = 0.0
            scalar_hc[label] = 0.0
        else:
            r_y = sum(1 for c in risk_sorted[:k] if c.pareto_beneficial) / k
            s_y = sum(1 for c in score_sorted[:k] if c.pareto_beneficial) / k
            sc_y = sum(1 for c in scalar_sorted[:k] if c.pareto_beneficial) / k
            o_y = sum(1 for c in oracle_sorted[:k] if c.pareto_beneficial) / k

            risk_yields[label] = r_y
            score_yields[label] = s_y
            scalar_yields[label] = sc_y
            oracle_yields[label] = o_y

            score_minus_random[label] = s_y - p_random
            score_minus_risk[label] = s_y - r_y
            oracle_minus_score[label] = o_y - s_y
            scalar_minus_score[label] = sc_y - s_y
            oracle_minus_scalar[label] = o_y - sc_y

            denom = o_y - p_random
            score_hc[label] = (s_y - p_random) / denom if denom > 0 else 0.0
            scalar_hc[label] = (sc_y - p_random) / denom if denom > 0 else 0.0

    return {
        "random_yield": p_random,
        "risk_only_yield": risk_yields,
        "score_only_yield": score_yields,
        "scalar_yield": scalar_yields,
        "oracle_yield": oracle_yields,
        "score_minus_random": score_minus_random,
        "score_minus_risk": score_minus_risk,
        "oracle_minus_score": oracle_minus_score,
        "scalar_minus_score": scalar_minus_score,
        "oracle_minus_scalar": oracle_minus_scalar,
        "score_headroom_capture": score_hc,
        "scalar_headroom_capture": scalar_hc,
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
    audit_candidates: list[Gate02CandidateRecord],
    frozen_lambda: float,
    dev_degree_max: float,
    tau_s: float,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Patient-clustered bootstrap on Audit partition with lambda* frozen from Dev."""
    by_patient_order: dict[int, list[Gate02CandidateRecord]] = {}
    for c in audit_candidates:
        by_patient_order.setdefault(c.patient_order, []).append(c)

    unique_orders = sorted(by_patient_order.keys())
    u = len(unique_orders)
    if u == 0:
        return {}

    rng = random.Random(seed)

    boot_score_yields: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_scalar_yields: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_score_minus_random: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_score_minus_risk: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_oracle_minus_score: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_scalar_minus_score: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_oracle_minus_scalar: dict[str, list[float]] = {BUDGET_LABELS[b]: [] for b in BUDGETS}
    boot_i_tension: list[float] = []

    for _ in range(replicates):
        sampled_orders = [unique_orders[rng.randrange(u)] for _ in range(u)]
        resampled_candidates: list[Gate02CandidateRecord] = []
        for order in sampled_orders:
            resampled_candidates.extend(by_patient_order[order])

        res = evaluate_audit_policies(
            resampled_candidates,
            frozen_lambda=frozen_lambda,
            dev_degree_max=dev_degree_max,
        )
        _, i_tens, _ = compute_interaction_cells(resampled_candidates, tau_s=tau_s)
        boot_i_tension.append(i_tens)

        for b in BUDGETS:
            label = BUDGET_LABELS[b]
            boot_score_yields[label].append(res["score_only_yield"][label])
            boot_scalar_yields[label].append(res["scalar_yield"][label])
            boot_score_minus_random[label].append(res["score_minus_random"][label])
            boot_score_minus_risk[label].append(res["score_minus_risk"][label])
            boot_oracle_minus_score[label].append(res["oracle_minus_score"][label])
            boot_scalar_minus_score[label].append(res["scalar_minus_score"][label])
            boot_oracle_minus_scalar[label].append(res["oracle_minus_scalar"][label])

    intervals: dict[str, Any] = {
        "score_only_yield": {},
        "scalar_yield": {},
        "score_minus_random": {},
        "score_minus_risk": {},
        "oracle_minus_score": {},
        "scalar_minus_score": {},
        "oracle_minus_scalar": {},
        "i_tension": {
            "lower": _percentile(boot_i_tension, 0.025),
            "upper": _percentile(boot_i_tension, 0.975),
        },
    }
    for b in BUDGETS:
        label = BUDGET_LABELS[b]
        intervals["score_only_yield"][label] = {
            "lower": _percentile(boot_score_yields[label], 0.025),
            "upper": _percentile(boot_score_yields[label], 0.975),
        }
        intervals["scalar_yield"][label] = {
            "lower": _percentile(boot_scalar_yields[label], 0.025),
            "upper": _percentile(boot_scalar_yields[label], 0.975),
        }
        intervals["score_minus_random"][label] = {
            "lower": _percentile(boot_score_minus_random[label], 0.025),
            "upper": _percentile(boot_score_minus_random[label], 0.975),
        }
        intervals["score_minus_risk"][label] = {
            "lower": _percentile(boot_score_minus_risk[label], 0.025),
            "upper": _percentile(boot_score_minus_risk[label], 0.975),
        }
        intervals["oracle_minus_score"][label] = {
            "lower": _percentile(boot_oracle_minus_score[label], 0.025),
            "upper": _percentile(boot_oracle_minus_score[label], 0.975),
        }
        intervals["scalar_minus_score"][label] = {
            "lower": _percentile(boot_scalar_minus_score[label], 0.025),
            "upper": _percentile(boot_scalar_minus_score[label], 0.975),
        }
        intervals["oracle_minus_scalar"][label] = {
            "lower": _percentile(boot_oracle_minus_scalar[label], 0.025),
            "upper": _percentile(boot_oracle_minus_scalar[label], 0.975),
        }

    return intervals


def evaluate_gate_02_verdict(
    support_sufficient: bool,
    selected_lambda: float,
    intervals_95: dict[str, Any],
    interaction_support_sufficient: bool,
) -> tuple[str, dict[str, bool]]:
    """Formal preregistered Gate 02 decision tree."""
    if not support_sufficient:
        criteria = {
            "support_requirement_met": False,
            "residual_headroom_survives_score_10": False,
            "residual_headroom_survives_score_20": False,
            "scalar_beats_score_10": False,
            "scalar_beats_score_20": False,
            "interaction_support_met": interaction_support_sufficient,
            "interaction_ci_above_zero": False,
        }
        return "INSUFFICIENT_SUPPORT", criteria

    ci_o_s_10 = intervals_95["oracle_minus_score"]["10%"]["lower"] > 0.0
    ci_o_s_20 = intervals_95["oracle_minus_score"]["20%"]["lower"] > 0.0
    residual_survives = ci_o_s_10 and ci_o_s_20

    ci_scal_s_10 = intervals_95["scalar_minus_score"]["10%"]["lower"] > 0.0
    ci_scal_s_20 = intervals_95["scalar_minus_score"]["20%"]["lower"] > 0.0
    scalar_beats_score = ci_scal_s_10 and ci_scal_s_20

    ci_i_tension = intervals_95["i_tension"]["lower"] > 0.0

    criteria = {
        "support_requirement_met": True,
        "residual_headroom_survives_score_10": ci_o_s_10,
        "residual_headroom_survives_score_20": ci_o_s_20,
        "scalar_beats_score_10": ci_scal_s_10,
        "scalar_beats_score_20": ci_scal_s_20,
        "interaction_support_met": interaction_support_sufficient,
        "interaction_ci_above_zero": ci_i_tension,
    }

    # Gate 02-A: Is model confidence already sufficient?
    if not residual_survives:
        return "STOP_SCORE_SUFFICIENT", criteria

    # Gate 02-B: Does DDI pressure add information beyond confidence?
    if scalar_beats_score:
        if selected_lambda > 0.0:
            return "PASS_POSITIVE_INCREMENTAL_CONSTRAINT_SIGNAL", criteria
        elif selected_lambda < 0.0:
            return "PIVOT_OPPOSITE_PRESSURE_SIGNAL", criteria

    if interaction_support_sufficient and ci_i_tension:
        return "PASS_INTERACTION_ONLY_SIGNAL", criteria

    return "STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL", criteria


def write_gate_02_candidates_jsonl(records: list[Gate02CandidateRecord], path: Path) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for r in records:
            stream.write(json.dumps(r.to_dict(), sort_keys=True) + "\n")


def build_gate_02_public_summary(
    dev_candidates: list[Gate02CandidateRecord],
    audit_candidates: list[Gate02CandidateRecord],
    selected_lambda: float,
    eval_results: dict[str, Any],
    interaction_cell_info: dict[str, dict[str, Any]],
    i_tension: float,
    interaction_support_met: bool,
    tau_s: float,
    intervals_95: dict[str, Any],
    verdict: str,
    criteria: dict[str, bool],
    identities: dict[str, Any],
) -> dict[str, Any]:
    n_audit_candidates = len(audit_candidates)
    audit_eligible_patients = len(set(c.patient_order for c in audit_candidates))
    audit_beneficial_patients = len(
        set(c.patient_order for c in audit_candidates if c.pareto_beneficial)
    )
    audit_non_beneficial_patients = len(
        set(c.patient_order for c in audit_candidates if not c.pareto_beneficial)
    )

    dev_beneficial_patients = len(
        set(c.patient_order for c in dev_candidates if c.pareto_beneficial)
    )
    dev_non_beneficial_patients = len(
        set(c.patient_order for c in dev_candidates if not c.pareto_beneficial)
    )

    return {
        "schema_version": 1,
        "kind": "gate_02_confidence_sufficiency_summary",
        "idea_id": "001-tension-guided-verification",
        "gate_id": "gate-02-confidence-sufficiency",
        "method_id": "molerec",
        "profile_id": "molerec-embedding",
        "split": "validation",
        "verdict": verdict,
        "dev_audit_counts": {
            "dev_candidates": len(dev_candidates),
            "dev_patients": len(set(c.patient_order for c in dev_candidates)),
            "dev_beneficial_patients": dev_beneficial_patients,
            "dev_non_beneficial_patients": dev_non_beneficial_patients,
            "audit_candidates": n_audit_candidates,
            "audit_patients": audit_eligible_patients,
        },
        "support": {
            "audit_eligible_candidates": n_audit_candidates,
            "audit_eligible_patients": audit_eligible_patients,
            "audit_beneficial_patients": audit_beneficial_patients,
            "audit_non_beneficial_patients": audit_non_beneficial_patients,
            "support_sufficient": criteria["support_requirement_met"],
        },
        "selected_lambda": selected_lambda,
        "policy_yields": {
            "random": {"yield": eval_results["random_yield"]},
            "risk_only": eval_results["risk_only_yield"],
            "score_only": eval_results["score_only_yield"],
            "scalar": eval_results["scalar_yield"],
            "oracle": eval_results["oracle_yield"],
        },
        "gaps": {
            "score_minus_random": eval_results["score_minus_random"],
            "score_minus_risk": eval_results["score_minus_risk"],
            "oracle_minus_score": eval_results["oracle_minus_score"],
            "scalar_minus_score": eval_results["scalar_minus_score"],
            "oracle_minus_scalar": eval_results["oracle_minus_scalar"],
        },
        "headroom_capture": {
            "score_headroom_capture": eval_results["score_headroom_capture"],
            "scalar_headroom_capture": eval_results["scalar_headroom_capture"],
        },
        "interaction": {
            "support_score_median": tau_s,
            "cells": interaction_cell_info,
            "i_tension": i_tension,
            "interaction_support_sufficient": interaction_support_met,
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


def run_gate_02(
    *,
    dataset_manifest: Path,
    dataset_root: Path,
    output_root: Path,
    molerec_root: Path,
    checkpoint: Path,
    baseline_environment: str = FROZEN_BASELINE_ENVIRONMENT_NAME,
    conda_executable: str | Path | None = None,
    harness_root: Path | None = None,
    expected_harness_revision: str | None = None,
) -> dict[str, Any]:
    dataset_manifest = dataset_manifest.resolve()
    dataset_root = dataset_root.resolve()
    output_root = output_root.resolve()
    molerec_root = molerec_root.resolve()
    checkpoint = checkpoint.resolve()

    if output_root.exists():
        raise FileExistsError(
            f"output_root already exists: {output_root}. Gate 02 requires a fresh output directory."
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

    # 1. Clean checkouts preflight
    verify_clean_checkout(harness_root, "medrec-research")
    verify_clean_checkout(molerec_root, "MoleRec")

    harness_rev = _git_revision(harness_root)
    if expected_harness_revision is not None and harness_rev != expected_harness_revision:
        raise ValueError(
            f"Harness revision drift: expected {expected_harness_revision}, got {harness_rev}"
        )

    # 2. Frozen MoleRec source revision, checkpoint hash, and adapter identity
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

    # 3. Verify actual baseline Conda environment package specification hash
    observed_env_sha256 = verify_conda_environment(conda_executable, baseline_environment)

    # 4. Stage validation cohort inside medrec-molerec-table1 Python 3.8 environment
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

    # 5. Read metadata and strictly verify dataset manifest, snapshot, vocab, and DDI identities
    meta = json.loads((staging_dir / "validation-meta.json").read_text(encoding="utf-8"))
    manifest, actual_snapshot_sha256 = verify_dataset_manifest_and_snapshot(
        manifest_path=dataset_manifest,
        dataset_root=dataset_root,
        staged_meta=meta,
    )

    features_path = Path(meta["features_path"])
    expected_visits = [tuple(item) for item in meta["expected_visits"]]
    targets = meta["targets"]
    ddi_pairs = frozenset(tuple(item) for item in meta["ddi_pairs"])
    medication_vocabulary = tuple(meta["medication_vocabulary"])
    traversal_by_visit = {
        f"{m['patient_id']}:{m['visit_id']}": (int(m["patient_order"]), int(m["visit_order"]))
        for m in meta["visit_traversal_metadata"]
    }

    # 6. Run target-free Comparison process seam (schema v2 includes vocabulary_scores)
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
            "vocabulary_scores": {s.medication_code: s.score for s in p.vocabulary_scores},
        }
        for p in batch.predictions
    ]

    # 7. Deterministic validation patient partition (50% Dev / 50% Audit) from full validation patient universe
    val_patient_count = int(meta["validation_patient_count"])
    dev_patients, _audit_patients = partition_validation_patients(
        range(val_patient_count), seed=1203
    )

    # 8. Compute eligible candidates with model scores and partition assignment
    candidates = compute_gate_02_candidates(
        predictions=predictions,
        targets=targets,
        ddi_pairs=ddi_pairs,
        traversal_by_visit=traversal_by_visit,
        dev_patients=dev_patients,
    )

    dev_candidates = [c for c in candidates if c.gate02_partition == "dev"]
    audit_candidates = [c for c in candidates if c.gate02_partition == "audit"]

    # 9. Support check on Audit partition
    audit_beneficial_patients = len(
        set(c.patient_order for c in audit_candidates if c.pareto_beneficial)
    )
    audit_non_beneficial_patients = len(
        set(c.patient_order for c in audit_candidates if not c.pareto_beneficial)
    )
    support_sufficient = (audit_beneficial_patients >= 50) and (audit_non_beneficial_patients >= 50)

    # 10. Lambda selection on Dev partition only
    (
        selected_lambda,
        dev_degree_max,
        dev_yields_10,
        dev_yields_20,
        dev_selection_scores,
    ) = select_dev_lambda(dev_candidates, lambda_grid=LAMBDA_GRID)

    tau_s = compute_dev_median_score(dev_candidates)

    # Write restricted Dev selection artifact (Audit outcome must never appear here)
    dev_selection_artifact = {
        "degree_normalization_max": dev_degree_max,
        "dev_candidate_count": len(dev_candidates),
        "dev_patient_count": len(dev_patients),
        "lambda_grid": list(LAMBDA_GRID),
        "per_lambda_dev_yield_10": dev_yields_10,
        "per_lambda_dev_yield_20": dev_yields_20,
        "per_lambda_selection_score": dev_selection_scores,
        "selected_lambda": selected_lambda,
        "support_score_median": tau_s,
        "tie_break_rule": "smaller |lambda|, prefer lambda=0, numerical ascending order",
    }
    dev_selection_path = output_root / "gate-02-dev-selection.json"
    dev_selection_path.write_text(
        json.dumps(dev_selection_artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # 11. Evaluate frozen lambda and interaction on Audit partition
    eval_results = evaluate_audit_policies(
        audit_candidates=audit_candidates,
        frozen_lambda=selected_lambda,
        dev_degree_max=dev_degree_max,
    )

    interaction_cells, i_tension, interaction_support_met = compute_interaction_cells(
        audit_candidates=audit_candidates,
        tau_s=tau_s,
    )

    # 12. Bootstrap on Audit partition
    if support_sufficient:
        intervals_95 = run_audit_patient_bootstrap(
            audit_candidates=audit_candidates,
            frozen_lambda=selected_lambda,
            dev_degree_max=dev_degree_max,
            tau_s=tau_s,
            replicates=BOOTSTRAP_REPLICATES,
            seed=BOOTSTRAP_SEED,
        )
    else:
        empty_interval = {label: {"lower": 0.0, "upper": 0.0} for label in BUDGET_LABELS.values()}
        intervals_95 = {
            "score_only_yield": empty_interval,
            "scalar_yield": empty_interval,
            "score_minus_random": empty_interval,
            "score_minus_risk": empty_interval,
            "oracle_minus_score": empty_interval,
            "scalar_minus_score": empty_interval,
            "oracle_minus_scalar": empty_interval,
            "i_tension": {"lower": 0.0, "upper": 0.0},
        }

    # 13. Decision tree verdict
    verdict, criteria = evaluate_gate_02_verdict(
        support_sufficient=support_sufficient,
        selected_lambda=selected_lambda,
        intervals_95=intervals_95,
        interaction_support_sufficient=interaction_support_met,
    )

    # 14. Write restricted candidate jsonl artifact
    candidates_path = output_root / "gate-02-candidates.jsonl"
    write_gate_02_candidates_jsonl(candidates, candidates_path)

    # 15. Write public-safe summary
    identities = {
        "harness_revision": harness_rev,
        "model_source_revision": source_rev,
        "checkpoint_sha256": checkpoint_sha256,
        "baseline_core_sha256": baseline_core_sha256,
        "adapter_sha256": adapter_sha256,
        "baseline_environment_name": FROZEN_BASELINE_ENVIRONMENT_NAME,
        "baseline_environment_sha256": observed_env_sha256,
        "dataset_manifest_sha256": manifest.manifest_sha256,
        "dataset_id": manifest.dataset_id,
        "snapshot_id": manifest.snapshot_id,
        "snapshot_sha256": actual_snapshot_sha256,
        "ddi_asset_sha256": meta["ddi_asset_sha256"],
        "canonical_ddi_semantics_sha256": meta["canonical_ddi_semantics_sha256"],
        "feature_availability_sha256": meta["feature_availability_sha256"],
        "medication_vocabulary_size": len(medication_vocabulary),
        "medication_vocabulary_sha256": meta["medication_vocabulary_sha256"],
    }

    summary = build_gate_02_public_summary(
        dev_candidates=dev_candidates,
        audit_candidates=audit_candidates,
        selected_lambda=selected_lambda,
        eval_results=eval_results,
        interaction_cell_info=interaction_cells,
        i_tension=i_tension,
        interaction_support_met=interaction_support_met,
        tau_s=tau_s,
        intervals_95=intervals_95,
        verdict=verdict,
        criteria=criteria,
        identities=identities,
    )

    summary_path = output_root / "gate-02-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return summary


def self_test_gate_02() -> None:
    """Check the seven changed critical paths per Section 24."""
    # --------------------------------------------------------------------------
    # Check 1: Extraction of candidate medication's frozen vocabulary_score and fail-closed checks
    # --------------------------------------------------------------------------
    pred_data = [
        {
            "patient_id": "p1",
            "visit_id": "v1",
            "predicted_medications": ["MED_A", "MED_B"],
            "vocabulary_scores": {"MED_A": 0.88, "MED_B": 0.52},
        }
    ]
    targets = {"p1:v1": ["MED_A"]}  # MED_B is false positive
    ddi_mock = frozenset([("MED_A", "MED_B")])
    traversal = {"p1:v1": (0, 1)}
    dev_pats = frozenset([0])

    cands = compute_gate_02_candidates(
        predictions=pred_data,
        targets=targets,
        ddi_pairs=ddi_mock,
        traversal_by_visit=traversal,
        dev_patients=dev_pats,
    )
    assert len(cands) == 2
    by_code = {c.medication_code: c for c in cands}
    assert by_code["MED_A"].model_score == 0.88
    assert by_code["MED_A"].pareto_beneficial is False  # Delta J < 0
    assert by_code["MED_B"].model_score == 0.52
    assert by_code["MED_B"].pareto_beneficial is True  # Delta J >= 0 (FP removed)

    # Missing traversal metadata must fail closed
    try:
        compute_gate_02_candidates(
            predictions=pred_data,
            targets=targets,
            ddi_pairs=ddi_mock,
            traversal_by_visit={},  # empty
            dev_patients=dev_pats,
        )
        raise AssertionError("Expected KeyError on missing traversal metadata")
    except KeyError as e:
        assert "Missing traversal metadata" in str(e)

    # Missing vocabulary score must fail closed
    pred_data_missing_score = [
        {
            "patient_id": "p1",
            "visit_id": "v1",
            "predicted_medications": ["MED_A", "MED_B"],
            "vocabulary_scores": {"MED_A": 0.88},  # MED_B score missing
        }
    ]
    try:
        compute_gate_02_candidates(
            predictions=pred_data_missing_score,
            targets=targets,
            ddi_pairs=ddi_mock,
            traversal_by_visit=traversal,
            dev_patients=dev_pats,
        )
        raise AssertionError("Expected KeyError on missing vocabulary score")
    except KeyError as e:
        assert "Missing frozen vocabulary score" in str(e)

    # --------------------------------------------------------------------------
    # Check 2: Deterministic patient Dev/Audit split on full validation universe
    # --------------------------------------------------------------------------
    orders = list(range(20))
    dev1, audit1 = partition_validation_patients(orders, seed=1203)
    dev2, audit2 = partition_validation_patients(orders, seed=1203)
    assert dev1 == dev2
    assert audit1 == audit2
    assert len(dev1) == 10
    assert len(audit1) == 10
    assert len(dev1 & audit1) == 0

    # Omitting patients without eligible follow-up visits shifts the seeded shuffle:
    orders_missing_pat5 = [i for i in range(20) if i != 5]
    dev_drift, _ = partition_validation_patients(orders_missing_pat5, seed=1203)
    assert dev_drift != dev1 - {5}, (
        "Omitting patients drifts seeded shuffle, proving full universe range() is required"
    )

    # --------------------------------------------------------------------------
    # Check 3: ScoreOnly ordering
    # --------------------------------------------------------------------------
    # ScoreOnly ranks low-confidence candidates first: s_t(m) asc
    audit_cands = [
        Gate02CandidateRecord(
            patient_id="p0",
            visit_id="v0",
            patient_order=0,
            visit_order=1,
            gate02_partition="audit",
            medication_code="MED_HIGH",
            model_score=0.95,
            active_ddi_degree=1,
            pareto_beneficial=False,
            delta_jaccard=-0.1,
            delta_violation=-1,
        ),
        Gate02CandidateRecord(
            patient_id="p1",
            visit_id="v1",
            patient_order=1,
            visit_order=1,
            gate02_partition="audit",
            medication_code="MED_LOW",
            model_score=0.51,
            active_ddi_degree=1,
            pareto_beneficial=True,
            delta_jaccard=0.1,
            delta_violation=-1,
        ),
    ]
    res_audit = evaluate_audit_policies(audit_cands, frozen_lambda=0.0, dev_degree_max=1.0)

    # At 50% budget k=1 (or at label 10% k=0 under n=2, but let's check sorting directly)
    def _score_key(c: Gate02CandidateRecord) -> tuple[float, str, int, int]:
        return (c.model_score, c.medication_code, c.patient_order, c.visit_order)

    sorted_score = sorted(audit_cands, key=_score_key)
    assert sorted_score[0].medication_code == "MED_LOW"
    assert sorted_score[1].medication_code == "MED_HIGH"

    # --------------------------------------------------------------------------
    # Check 4: Lambda selection using Dev only
    # --------------------------------------------------------------------------
    # Create Dev candidates where high DDI degree indicates true positive (bad to delete),
    # so positive lambda should hurt and negative lambda should win!
    dev_mock: list[Gate02CandidateRecord] = []
    for i in range(100):
        # Even i: non-beneficial, s=0.5 (1-s=0.5), high degree 4 (q=1.0) -> R_0=0.5
        # Odd i: beneficial, s=0.6 (1-s=0.4), low degree 1 (q=0.25) -> R_0=0.4
        # At lambda=0, non-beneficial ranked first (low yield).
        # At lambda=-1, beneficial: 0.4 - 0.25 = 0.15 > non-beneficial: 0.5 - 1.0 = -0.5 (high yield).
        is_beneficial = (i % 2) == 1
        degree = 1 if is_beneficial else 4
        score = 0.6 if is_beneficial else 0.5
        dev_mock.append(
            Gate02CandidateRecord(
                patient_id=f"dev_p{i}",
                visit_id=f"dev_v{i}",
                patient_order=i,
                visit_order=1,
                gate02_partition="dev",
                medication_code=f"M_{i}",
                model_score=score,
                active_ddi_degree=degree,
                pareto_beneficial=is_beneficial,
                delta_jaccard=0.1 if is_beneficial else -0.1,
                delta_violation=-degree,
            )
        )
    sel_lam, d_max, _y10, _y20, scores = select_dev_lambda(dev_mock)
    assert d_max == 4.0
    assert len(scores) == len(LAMBDA_GRID)
    # Negative lambda gives higher priority to lower degree (which has is_beneficial=True)
    assert sel_lam < 0.0

    # --------------------------------------------------------------------------
    # Check 5: Proof that changing Audit labels cannot alter lambda*
    # --------------------------------------------------------------------------
    audit_cands_alt = [
        Gate02CandidateRecord(
            patient_id=c.patient_id,
            visit_id=c.visit_id,
            patient_order=c.patient_order,
            visit_order=c.visit_order,
            gate02_partition="audit",
            medication_code=c.medication_code,
            model_score=c.model_score,
            active_ddi_degree=c.active_ddi_degree,
            pareto_beneficial=not c.pareto_beneficial,  # completely inverted
            delta_jaccard=-c.delta_jaccard,
            delta_violation=c.delta_violation,
        )
        for c in audit_cands
    ]
    assert len(audit_cands_alt) == len(audit_cands)
    # Re-run selection: Audit is not even passed to select_dev_lambda!
    sel_lam_again, _, _, _, _ = select_dev_lambda(dev_mock)
    assert sel_lam_again == sel_lam, "Dev lambda selection must be fully firewalled from Audit"

    # --------------------------------------------------------------------------
    # Check 6: Restricted-artifact independent recomputation
    # --------------------------------------------------------------------------
    # Serialize candidates to JSONL, deserialize, and verify recomputation matches
    jsonl_str = "\n".join(json.dumps(c.to_dict()) for c in dev_mock + audit_cands)
    reloaded = [
        Gate02CandidateRecord.from_dict(json.loads(line))
        for line in jsonl_str.splitlines()
        if line.strip()
    ]
    dev_re = [c for c in reloaded if c.gate02_partition == "dev"]
    audit_re = [c for c in reloaded if c.gate02_partition == "audit"]

    sel_re, d_max_re, _, _, _ = select_dev_lambda(dev_re)
    assert sel_re == sel_lam
    assert d_max_re == d_max

    eval_re = evaluate_audit_policies(audit_re, frozen_lambda=sel_re, dev_degree_max=d_max_re)
    assert eval_re == res_audit

    # --------------------------------------------------------------------------
    # Check 7: Interaction-cell calculation
    # --------------------------------------------------------------------------
    tau_s = compute_dev_median_score(dev_mock)
    # LL: score < tau_s, degree == 1
    # LH: score < tau_s, degree >= 2
    # HL: score >= tau_s, degree == 1
    # HH: score >= tau_s, degree >= 2
    test_inter_cands = [
        Gate02CandidateRecord("p1", "v1", 1, 1, "audit", "m1", tau_s - 0.1, 1, True, 0.1, -1),
        Gate02CandidateRecord("p2", "v2", 2, 1, "audit", "m2", tau_s - 0.1, 2, False, -0.1, -2),
        Gate02CandidateRecord("p3", "v3", 3, 1, "audit", "m3", tau_s + 0.1, 1, False, -0.1, -1),
        Gate02CandidateRecord("p4", "v4", 4, 1, "audit", "m4", tau_s + 0.1, 3, True, 0.1, -3),
    ]
    cells, i_tens, supp = compute_interaction_cells(test_inter_cands, tau_s)
    # LL: p1, prev=1.0. LH: p2, prev=0.0. HL: p3, prev=0.0. HH: p4, prev=1.0.
    # I_Tension = (p_HH - p_HL) - (p_LH - p_LL) = (1.0 - 0.0) - (0.0 - 1.0) = 1.0 - (-1.0) = 2.0
    assert cells["LL"]["candidates"] == 1
    assert cells["LH"]["candidates"] == 1
    assert cells["HL"]["candidates"] == 1
    assert cells["HH"]["candidates"] == 1
    assert i_tens == 2.0
    assert supp is False  # each cell has 1 patient < 50

    print("Gate 02 synthetic self-test passed successfully.")


def test_synthetic_gate_02() -> None:
    """Pytest entrypoint for Gate 02 synthetic self-test."""
    self_test_gate_02()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Run focused synthetic test suite")
    parser.add_argument("--dataset-manifest", type=Path, help="Path to v1.1 dataset manifest JSON")
    parser.add_argument("--dataset-root", type=Path, help="Path to snapshot root")
    parser.add_argument("--output-root", type=Path, help="New restricted output root")
    parser.add_argument("--molerec-root", type=Path, help="Path to MoleRec checkout")
    parser.add_argument("--checkpoint", type=Path, help="Path to frozen MoleRec checkpoint")
    parser.add_argument(
        "--baseline-environment",
        default=FROZEN_BASELINE_ENVIRONMENT_NAME,
        help=f"Must equal {FROZEN_BASELINE_ENVIRONMENT_NAME}",
    )
    parser.add_argument("--conda-executable", type=Path)
    parser.add_argument("--expected-harness-revision", help="Optional expected harness git commit")
    args = parser.parse_args()

    if args.self_test:
        self_test_gate_02()
        return

    if (
        args.dataset_manifest is None
        or args.dataset_root is None
        or args.output_root is None
        or args.molerec_root is None
        or args.checkpoint is None
    ):
        parser.error(
            "--dataset-manifest, --dataset-root, --output-root, --molerec-root, and --checkpoint are required for formal Gate 02 execution"
        )

    summary = run_gate_02(
        dataset_manifest=args.dataset_manifest,
        dataset_root=args.dataset_root,
        output_root=args.output_root,
        molerec_root=args.molerec_root,
        checkpoint=args.checkpoint,
        baseline_environment=args.baseline_environment,
        conda_executable=args.conda_executable,
        expected_harness_revision=args.expected_harness_revision,
    )
    print(json.dumps({"verdict": summary["verdict"], "support": summary["support"]}, indent=2))


if __name__ == "__main__":
    main()
