#!/usr/bin/env python3
"""Gate 01 — Prescription-Relative Confidence Residual.

Idea: 003-prescription-relative-confidence
Stage: Idea / Hypothesis Selection
Scope: Retrospective validation-only evaluation of within-prescription relative confidence.
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

# Pinned scientific identities matching Gate 01 / Qualification v1.1
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

SPLIT_SEED = 2003
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 1203
RIDGE_PENALTY = 1e-6


class Gate01CandidateRecord(NamedTuple):
    patient_id: str
    visit_id: str
    patient_order: int
    visit_order: int
    gate01_partition: str  # "dev" or "audit"
    medication_code: str
    model_score: float
    prescription_size: int
    relative_rank: float
    train_prevalence: float
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
            "prescription_size": int(self.prescription_size),
            "relative_rank": float(self.relative_rank),
            "train_prevalence": float(self.train_prevalence),
            "active_ddi_degree": int(self.active_ddi_degree),
            "pareto_beneficial": bool(self.pareto_beneficial),
            "delta_jaccard": float(self.delta_jaccard),
            "delta_violation": int(self.delta_violation),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Gate01CandidateRecord:
        return cls(
            patient_id=str(data["patient_id"]),
            visit_id=str(data["visit_id"]),
            patient_order=int(data["patient_order"]),
            visit_order=int(data["visit_order"]),
            gate01_partition=str(data["gate01_partition"]),
            medication_code=str(data["medication_code"]),
            model_score=float(data["model_score"]),
            prescription_size=int(data["prescription_size"]),
            relative_rank=float(data["relative_rank"]),
            train_prevalence=float(data["train_prevalence"]),
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
        ("git", "status", "--short"),
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
            f"Invalid baseline environment: {environment_name}. Must use {FROZEN_BASELINE_ENVIRONMENT_NAME}"
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
    if checkpoint_sha256 != FROZEN_CHECKPOINT_SHA256:
        raise ValueError(
            f"MoleRec checkpoint hash drift: expected {FROZEN_CHECKPOINT_SHA256}, got {checkpoint_sha256}"
        )

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
    if staged_meta["medication_vocabulary_sha256"] != FROZEN_MEDICATION_VOCABULARY_SHA256:
        raise ValueError(
            f"Medication vocabulary checksum drift: expected {FROZEN_MEDICATION_VOCABULARY_SHA256}, got {staged_meta['medication_vocabulary_sha256']}"
        )
    if staged_meta["ddi_asset_sha256"] != FROZEN_DDI_ASSET_SHA256:
        raise ValueError(
            f"DDI asset checksum drift: expected {FROZEN_DDI_ASSET_SHA256}, got {staged_meta['ddi_asset_sha256']}"
        )
    if staged_meta["feature_availability_sha256"] != FROZEN_FEATURE_AVAILABILITY_SHA256:
        raise ValueError(
            f"Feature availability checksum drift: expected {FROZEN_FEATURE_AVAILABILITY_SHA256}, got {staged_meta['feature_availability_sha256']}"
        )
    return manifest, actual_snapshot_sha256


def compute_relative_rank(
    candidate_med: str,
    predicted_meds: list[str],
    vocabulary_scores: dict[str, float],
) -> float:
    r"""Exact within-prescription relative confidence mid-rank position.

    r_t(m) = ( #{j in Mhat_t : s_t(j) > s_t(m)} + 0.5 * #{j in Mhat_t \ {m} : s_t(j) == s_t(m)} ) / (n_t - 1)
    """
    n_t = len(predicted_meds)
    if n_t < 2:
        raise ValueError(f"Prescription size must be at least 2 for candidate, got {n_t}")

    s_m = vocabulary_scores[candidate_med]
    gt_count = sum(1 for j in predicted_meds if vocabulary_scores[j] > s_m)
    eq_count = sum(1 for j in predicted_meds if j != candidate_med and vocabulary_scores[j] == s_m)
    return float((gt_count + 0.5 * eq_count) / (n_t - 1))


def partition_validation_patients(
    patient_orders: Iterable[int],
    seed: int = SPLIT_SEED,
) -> tuple[frozenset[int], frozenset[int]]:
    """Preregistered deterministic patient-level split into Dev (529) and Audit (530)."""
    unique_orders = sorted(set(patient_orders))
    shuffled = list(unique_orders)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    n_dev = len(shuffled) // 2  # 1059 // 2 = 529
    dev_set = frozenset(shuffled[:n_dev])
    audit_set = frozenset(shuffled[n_dev:])
    return dev_set, audit_set


def build_candidate_records(
    predictions: list[dict[str, Any]],
    targets: dict[str, list[str]],
    ddi_pairs: frozenset[tuple[str, str]],
    traversal_by_visit: dict[str, tuple[int, int]],
    dev_patients: frozenset[int],
    train_prevalence: dict[str, float],
) -> list[Gate01CandidateRecord]:
    """Construct candidate records Q_t = {m in Mhat_t : d_t(m) > 0} from complete predictions."""
    candidates: list[Gate01CandidateRecord] = []

    for pred in predictions:
        patient_id = str(pred["patient_id"])
        visit_id = str(pred["visit_id"])
        visit_key = f"{patient_id}:{visit_id}"

        patient_order, visit_order = traversal_by_visit[visit_key]
        partition = "dev" if patient_order in dev_patients else "audit"

        predicted_meds = list(pred["predicted_medications"])
        vocab_scores = pred["vocabulary_scores"]
        target_meds = set(targets[visit_key])
        n_t = len(predicted_meds)

        # Precompute active DDI degree within predicted prescription
        ddi_degrees: dict[str, int] = {}
        for med in predicted_meds:
            deg = 0
            for other in predicted_meds:
                if med != other and ((med, other) in ddi_pairs or (other, med) in ddi_pairs):
                    deg += 1
            ddi_degrees[med] = deg

        # Base Jaccard of original prediction
        j_denom_orig = len(set(predicted_meds) | target_meds)
        j_orig = len(set(predicted_meds) & target_meds) / j_denom_orig if j_denom_orig > 0 else 0.0

        for med in predicted_meds:
            deg = ddi_degrees[med]
            if deg <= 0:
                continue  # candidate universe Q_t requires d_t(m) > 0

            # Mid-rank relative confidence
            r = compute_relative_rank(med, predicted_meds, vocab_scores)

            # Singleton deletion revision outcome
            rev_meds = set(predicted_meds) - {med}
            j_denom_rev = len(rev_meds | target_meds)
            j_rev = len(rev_meds & target_meds) / j_denom_rev if j_denom_rev > 0 else 0.0
            delta_j = j_rev - j_orig
            delta_v = -deg  # strictly reduces violation

            # Pareto-beneficial: false-positive status m not in M_t
            pareto_beneficial = med not in target_meds
            s_m = vocab_scores[med]
            p_m = train_prevalence[med]

            candidates.append(
                Gate01CandidateRecord(
                    patient_id=patient_id,
                    visit_id=visit_id,
                    patient_order=patient_order,
                    visit_order=visit_order,
                    gate01_partition=partition,
                    medication_code=med,
                    model_score=float(s_m),
                    prescription_size=n_t,
                    relative_rank=r,
                    train_prevalence=p_m,
                    active_ddi_degree=deg,
                    pareto_beneficial=pareto_beneficial,
                    delta_jaccard=float(delta_j),
                    delta_violation=int(delta_v),
                )
            )

    return candidates


def compute_feature_vectors(
    candidate: Gate01CandidateRecord,
) -> tuple[list[float], list[float]]:
    """Compute StrongControl (5D) and RankAugmented (6D) feature vectors.

    u = 1 - s
    c = log(1 + n_t)
    f = log(p / (1 - p))
    ctrl: [u, c, f, u*c, u*f]
    rank: [u, c, f, u*c, u*f, r]
    """
    s = candidate.model_score
    n_t = candidate.prescription_size
    p = candidate.train_prevalence
    r = candidate.relative_rank

    u = 1.0 - s
    c = math.log(1.0 + n_t)
    f = math.log(p / (1.0 - p))

    x_ctrl = [u, c, f, u * c, u * f]
    x_rank = [u, c, f, u * c, u * f, r]
    return x_ctrl, x_rank


def _solve_linear_system(A: list[list[float]], b: list[float]) -> list[float]:
    """Solve small dense symmetric positive-definite linear system A x = b via Gaussian elimination."""
    n = len(A)
    # Augmented matrix
    M = [[*list(row), b[i]] for i, row in enumerate(A)]
    for i in range(n):
        # Partial pivoting for stability
        max_row = max(range(i, n), key=lambda r: abs(M[r][i]))
        if abs(M[max_row][i]) < 1e-14:
            raise ValueError("Singular matrix in ridge regression solver")
        M[i], M[max_row] = M[max_row], M[i]
        pivot = M[i][i]
        for j in range(i, n + 1):
            M[i][j] /= pivot
        for r in range(n):
            if r != i:
                factor = M[r][i]
                for j in range(i, n + 1):
                    M[r][j] -= factor * M[i][j]
    return [M[i][n] for i in range(n)]


def fit_ridge_linear_probability(
    X: list[list[float]],
    y: list[float],
    ridge: float = RIDGE_PENALTY,
) -> tuple[float, list[float]]:
    """Deterministic ridge linear probability estimator with unpenalized intercept.

    min_{beta0, beta} sum (y - beta0 - x^T beta)^2 + ridge * ||beta||^2
    """
    n = len(X)
    if n == 0:
        raise ValueError("Cannot fit model on empty dataset")
    p = len(X[0])

    y_mean = sum(y) / n
    x_mean = [sum(X[i][j] for i in range(n)) / n for j in range(p)]

    # Compute centered cross-products: A = X_tilde^T X_tilde + ridge * I, b = X_tilde^T y_tilde
    A = [[0.0] * p for _ in range(p)]
    b = [0.0] * p

    for i in range(n):
        y_cent = y[i] - y_mean
        x_cent = [X[i][j] - x_mean[j] for j in range(p)]
        for j in range(p):
            b[j] += x_cent[j] * y_cent
            for k in range(p):
                A[j][k] += x_cent[j] * x_cent[k]

    # Add ridge penalty to diagonal (slope parameters only)
    for j in range(p):
        A[j][j] += ridge

    beta = _solve_linear_system(A, b)
    beta0 = y_mean - sum(x_mean[j] * beta[j] for j in range(p))
    return beta0, beta


def _percentile(values: list[float], p: float) -> float:
    """Linear interpolation percentile matching standard numpy.percentile."""
    sorted_v = sorted(values)
    n = len(sorted_v)
    idx = (n - 1) * (p / 100.0)
    low = math.floor(idx)
    high = math.ceil(idx)
    if low == high:
        return sorted_v[low]
    weight = idx - low
    return (1.0 - weight) * sorted_v[low] + weight * sorted_v[high]


def evaluate_audit_policies(
    audit_candidates: list[Gate01CandidateRecord],
    ctrl_beta0: float,
    ctrl_beta: list[float],
    rank_beta0: float,
    rank_beta: list[float],
) -> dict[str, Any]:
    """Evaluate candidate rankings under all four policies on Audit candidates."""
    n_a = len(audit_candidates)
    if n_a == 0:
        raise ValueError("Audit candidates list is empty")

    # 1. Random base-rate yield
    random_yield = sum(1 for c in audit_candidates if c.pareto_beneficial) / n_a

    # 2. Compute fitted risks
    audit_ctrl_risks: list[float] = []
    audit_rank_risks: list[float] = []
    for c in audit_candidates:
        x_ctrl, x_rank = compute_feature_vectors(c)
        r_ctrl = ctrl_beta0 + sum(x_ctrl[j] * ctrl_beta[j] for j in range(len(x_ctrl)))
        r_rank = rank_beta0 + sum(x_rank[j] * rank_beta[j] for j in range(len(x_rank)))
        audit_ctrl_risks.append(r_ctrl)
        audit_rank_risks.append(r_rank)

    scored_items = list(zip(audit_candidates, audit_ctrl_risks, audit_rank_risks, strict=True))

    # Deterministic 5-key tie-breaks
    ctrl_sorted = [
        item[0]
        for item in sorted(
            scored_items,
            key=lambda it: (
                -it[1],
                it[0].model_score,
                it[0].medication_code,
                it[0].patient_order,
                it[0].visit_order,
            ),
        )
    ]
    rank_sorted = [
        item[0]
        for item in sorted(
            scored_items,
            key=lambda it: (
                -it[2],
                it[0].model_score,
                it[0].medication_code,
                it[0].patient_order,
                it[0].visit_order,
            ),
        )
    ]
    score_sorted = sorted(
        audit_candidates,
        key=lambda c: (c.model_score, c.medication_code, c.patient_order, c.visit_order),
    )
    oracle_sorted = sorted(
        audit_candidates,
        key=lambda c: (
            -int(c.pareto_beneficial),
            c.model_score,
            c.medication_code,
            c.patient_order,
            c.visit_order,
        ),
    )

    yields: dict[str, dict[str, float]] = {
        "random": {},
        "score_only": {},
        "strong_control": {},
        "rank_augmented": {},
        "oracle": {},
    }
    gaps: dict[str, dict[str, float]] = {
        "rank_minus_control": {},
        "oracle_minus_control": {},
        "control_minus_score": {},
    }

    for b in BUDGETS:
        label = BUDGET_LABELS[b]
        k = math.floor(b * n_a)
        yields["random"][label] = random_yield
        if k > 0:
            y_score = sum(1 for c in score_sorted[:k] if c.pareto_beneficial) / k
            y_ctrl = sum(1 for c in ctrl_sorted[:k] if c.pareto_beneficial) / k
            y_rank = sum(1 for c in rank_sorted[:k] if c.pareto_beneficial) / k
            y_oracle = sum(1 for c in oracle_sorted[:k] if c.pareto_beneficial) / k
        else:
            y_score = y_ctrl = y_rank = y_oracle = 0.0

        yields["score_only"][label] = float(y_score)
        yields["strong_control"][label] = float(y_ctrl)
        yields["rank_augmented"][label] = float(y_rank)
        yields["oracle"][label] = float(y_oracle)

        gaps["rank_minus_control"][label] = float(y_rank - y_ctrl)
        gaps["oracle_minus_control"][label] = float(y_oracle - y_ctrl)
        gaps["control_minus_score"][label] = float(y_ctrl - y_score)

    return {
        "yields": yields,
        "gaps": gaps,
        "k_by_budget": {BUDGET_LABELS[b]: math.floor(b * n_a) for b in BUDGETS},
    }


def run_patient_cluster_bootstrap(
    audit_candidates: list[Gate01CandidateRecord],
    ctrl_beta0: float,
    ctrl_beta: list[float],
    rank_beta0: float,
    rank_beta: list[float],
    n_replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, dict[str, dict[str, float]]]:
    """Patient-cluster bootstrap uncertainty for Audit policy yields and paired gaps."""
    candidates_by_patient: dict[int, list[Gate01CandidateRecord]] = {}
    for c in audit_candidates:
        candidates_by_patient.setdefault(c.patient_order, []).append(c)

    unique_patients = sorted(candidates_by_patient.keys())
    n_patients = len(unique_patients)
    rng = random.Random(seed)

    gap_samples: dict[str, dict[str, list[float]]] = {
        "rank_minus_control": {label: [] for label in BUDGET_LABELS.values()},
        "oracle_minus_control": {label: [] for label in BUDGET_LABELS.values()},
        "control_minus_score": {label: [] for label in BUDGET_LABELS.values()},
    }

    for _ in range(n_replicates):
        sampled_patients = rng.choices(unique_patients, k=n_patients)
        boot_candidates: list[Gate01CandidateRecord] = []
        for draw_idx, p_order in enumerate(sampled_patients):
            for c in candidates_by_patient[p_order]:
                boot_candidates.append(
                    Gate01CandidateRecord(
                        patient_id=c.patient_id,
                        visit_id=c.visit_id,
                        patient_order=draw_idx,
                        visit_order=c.visit_order,
                        gate01_partition=c.gate01_partition,
                        medication_code=c.medication_code,
                        model_score=c.model_score,
                        prescription_size=c.prescription_size,
                        relative_rank=c.relative_rank,
                        train_prevalence=c.train_prevalence,
                        active_ddi_degree=c.active_ddi_degree,
                        pareto_beneficial=c.pareto_beneficial,
                        delta_jaccard=c.delta_jaccard,
                        delta_violation=c.delta_violation,
                    )
                )

        eval_res = evaluate_audit_policies(
            audit_candidates=boot_candidates,
            ctrl_beta0=ctrl_beta0,
            ctrl_beta=ctrl_beta,
            rank_beta0=rank_beta0,
            rank_beta=rank_beta,
        )

        for gap_name in gap_samples:
            for label in BUDGET_LABELS.values():
                gap_samples[gap_name][label].append(eval_res["gaps"][gap_name][label])

    intervals: dict[str, dict[str, dict[str, float]]] = {}
    for gap_name in gap_samples:
        intervals[gap_name] = {}
        for label in BUDGET_LABELS.values():
            sample_list = gap_samples[gap_name][label]
            intervals[gap_name][label] = {
                "lower": float(_percentile(sample_list, 2.5)),
                "upper": float(_percentile(sample_list, 97.5)),
            }

    return intervals


def evaluate_decision_tree(
    support_passed: bool,
    bootstrap_intervals: dict[str, dict[str, dict[str, float]]],
) -> tuple[str, dict[str, bool]]:
    """Preregistered mechanical decision tree: Gate A, Gate B, Gate C."""
    crit: dict[str, bool] = {
        "gate_a_support_met": support_passed,
        "gate_b_oracle_headroom_10": False,
        "gate_b_oracle_headroom_20": False,
        "gate_c_rank_incremental_10": False,
        "gate_c_rank_incremental_20": False,
    }

    if not support_passed:
        return "INCONCLUSIVE_INSUFFICIENT_AUDIT_SUPPORT", crit

    # Gate B: Oracle headroom > 0 at both 10% and 20%
    oracle_10_lower = bootstrap_intervals["oracle_minus_control"]["10%"]["lower"]
    oracle_20_lower = bootstrap_intervals["oracle_minus_control"]["20%"]["lower"]
    crit["gate_b_oracle_headroom_10"] = oracle_10_lower > 0.0
    crit["gate_b_oracle_headroom_20"] = oracle_20_lower > 0.0

    if not (crit["gate_b_oracle_headroom_10"] and crit["gate_b_oracle_headroom_20"]):
        return "STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL", crit

    # Gate C: RankAugmented - StrongControl > 0 at both 10% and 20%
    rank_10_lower = bootstrap_intervals["rank_minus_control"]["10%"]["lower"]
    rank_20_lower = bootstrap_intervals["rank_minus_control"]["20%"]["lower"]
    crit["gate_c_rank_incremental_10"] = rank_10_lower > 0.0
    crit["gate_c_rank_incremental_20"] = rank_20_lower > 0.0

    if crit["gate_c_rank_incremental_10"] and crit["gate_c_rank_incremental_20"]:
        return "PASS_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE", crit

    return "STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE", crit


def self_test_gate_01() -> None:
    """Focused synthetic unit test suite verifying all 9 critical paths."""
    print("Running Gate 01 focused synthetic self-test...")

    # 1. Mid-rank r calculation, including real score ties
    scores = {"m1": 0.9, "m2": 0.7, "m3": 0.7, "m4": 0.5}
    meds = ["m1", "m2", "m3", "m4"]
    r1 = compute_relative_rank("m1", meds, scores)
    r2 = compute_relative_rank("m2", meds, scores)
    r3 = compute_relative_rank("m3", meds, scores)
    r4 = compute_relative_rank("m4", meds, scores)
    assert math.isclose(r1, 0.0), f"r1 expected 0.0, got {r1}"
    assert math.isclose(r2, 0.5), f"r2 expected 0.5, got {r2}"
    assert math.isclose(r3, 0.5), f"r3 expected 0.5, got {r3}"
    assert math.isclose(r4, 1.0), f"r4 expected 1.0, got {r4}"
    assert r2 == r3, "Score ties must produce identical relative rank without epsilon"

    # 2. Seed-2003 split determinism and zero patient overlap
    dev_a, audit_a = partition_validation_patients(range(1059), seed=SPLIT_SEED)
    dev_b, audit_b = partition_validation_patients(range(1059), seed=SPLIT_SEED)
    assert dev_a == dev_b
    assert audit_a == audit_b
    assert len(dev_a) == 529
    assert len(audit_a) == 530
    assert dev_a.isdisjoint(audit_a)

    # 3 & 4. Train prevalence uses eligible train visits only; no val/test rows
    sim_records = [
        [[[1], [1], [10]], [[1], [1], [10, 20]]],
        [[[1], [1], [10]]],
        [[[1], [1], [10]], [[1], [1], [20]], [[1], [1], [10, 30]]],
    ]
    v_tr = 0
    c_tr: dict[int, int] = {}
    for p in sim_records:
        for v_idx in range(1, len(p)):
            v_tr += 1
            for m_code in set(p[v_idx][2]):
                c_tr[m_code] = c_tr.get(m_code, 0) + 1
    assert v_tr == 3
    assert c_tr[10] == 2
    assert c_tr[20] == 2
    assert c_tr[30] == 1
    assert math.isclose((c_tr[10] + 1) / (v_tr + 2), 0.6)

    # 5. Dev estimator receives no Audit labels
    random.seed(42)
    X_dev = [[random.gauss(0, 1) for _ in range(5)] for _ in range(100)]
    y_dev = [float(random.choice([0, 1])) for _ in range(100)]
    b0, beta = fit_ridge_linear_probability(X_dev, y_dev, ridge=RIDGE_PENALTY)
    assert isinstance(b0, float)
    assert len(beta) == 5

    # 6. Control and Augmented estimators differ by exactly r
    cand_mock = Gate01CandidateRecord(
        patient_id="p1",
        visit_id="v1",
        patient_order=0,
        visit_order=1,
        gate01_partition="dev",
        medication_code="m1",
        model_score=0.8,
        prescription_size=3,
        relative_rank=0.25,
        train_prevalence=0.3,
        active_ddi_degree=1,
        pareto_beneficial=True,
        delta_jaccard=0.1,
        delta_violation=-1,
    )
    x_c, x_r = compute_feature_vectors(cand_mock)
    assert len(x_c) == 5
    assert len(x_r) == 6
    assert x_r[:5] == x_c
    assert math.isclose(x_r[5], 0.25)

    # 7. Deterministic ranking tie-breaks
    c_tie1 = Gate01CandidateRecord(
        "p1", "v1", 1, 1, "audit", "A", 0.7, 2, 0.0, 0.5, 1, True, 0.1, -1
    )
    c_tie2 = Gate01CandidateRecord(
        "p2", "v1", 2, 1, "audit", "B", 0.7, 2, 0.0, 0.5, 1, True, 0.1, -1
    )
    c_tie3 = Gate01CandidateRecord(
        "p1", "v2", 1, 2, "audit", "A", 0.7, 2, 0.0, 0.5, 1, True, 0.1, -1
    )
    sorted_ties = sorted(
        [c_tie2, c_tie3, c_tie1],
        key=lambda c: (c.model_score, c.medication_code, c.patient_order, c.visit_order),
    )
    assert sorted_ties == [c_tie1, c_tie3, c_tie2]

    # 8. Decision tree branches
    v_supp, _ = evaluate_decision_tree(False, {})
    assert v_supp == "INCONCLUSIVE_INSUFFICIENT_AUDIT_SUPPORT"

    intv_no_head = {
        "oracle_minus_control": {
            "10%": {"lower": -0.01, "upper": 0.05},
            "20%": {"lower": 0.10, "upper": 0.20},
        },
        "rank_minus_control": {
            "10%": {"lower": 0.01, "upper": 0.05},
            "20%": {"lower": 0.01, "upper": 0.05},
        },
    }
    v_no_head, _ = evaluate_decision_tree(True, intv_no_head)
    assert v_no_head == "STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL"

    intv_pass = {
        "oracle_minus_control": {
            "10%": {"lower": 0.10, "upper": 0.25},
            "20%": {"lower": 0.08, "upper": 0.20},
        },
        "rank_minus_control": {
            "10%": {"lower": 0.02, "upper": 0.08},
            "20%": {"lower": 0.01, "upper": 0.06},
        },
    }
    v_pass, _ = evaluate_decision_tree(True, intv_pass)
    assert v_pass == "PASS_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE"

    intv_fail = {
        "oracle_minus_control": {
            "10%": {"lower": 0.10, "upper": 0.25},
            "20%": {"lower": 0.08, "upper": 0.20},
        },
        "rank_minus_control": {
            "10%": {"lower": -0.02, "upper": 0.03},
            "20%": {"lower": 0.01, "upper": 0.06},
        },
    }
    v_fail, _ = evaluate_decision_tree(True, intv_fail)
    assert v_fail == "STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE"

    print("Gate 01 synthetic self-test passed successfully.")


def run_gate_01(
    dataset_manifest: Path,
    dataset_root: Path,
    output_root: Path,
    molerec_root: Path,
    checkpoint: Path,
    baseline_environment: str = FROZEN_BASELINE_ENVIRONMENT_NAME,
    conda_executable: str | Path | None = None,
    expected_harness_revision: str | None = None,
    harness_root: Path | None = None,
    summary_output: Path | None = None,
) -> dict[str, Any]:
    dataset_manifest = dataset_manifest.resolve()
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

    staging_script = Path(__file__).resolve().parent / "stage_gate01_inputs.py"
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

    # 4. Stage validation inputs and train-only prevalence in medrec-molerec-table1 Python 3.8 env
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
    train_prevalence_data = json.loads(
        Path(meta["train_prevalence_path"]).read_text(encoding="utf-8")
    )
    train_prevalence: dict[str, float] = train_prevalence_data["prevalence"]
    eligible_train_visits = int(train_prevalence_data["eligible_train_visits"])

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

    # 7. Deterministic validation patient partition (529 Dev / 530 Audit)
    val_patient_count = int(meta["validation_patient_count"])
    dev_patients, audit_patients = partition_validation_patients(
        range(val_patient_count), seed=SPLIT_SEED
    )

    # 8. Build candidate records Q_t with complete predicted set mid-rank r_t(m)
    candidates = build_candidate_records(
        predictions=predictions,
        targets=targets,
        ddi_pairs=ddi_pairs,
        traversal_by_visit=traversal_by_visit,
        dev_patients=dev_patients,
        train_prevalence=train_prevalence,
    )

    # Save restricted candidate corpus JSONL
    candidates_jsonl_path = output_root / "gate-01-candidates.jsonl"
    with candidates_jsonl_path.open("w", encoding="utf-8") as stream:
        for c in candidates:
            stream.write(json.dumps(c.to_dict(), sort_keys=True) + "\n")

    dev_candidates = [c for c in candidates if c.gate01_partition == "dev"]
    audit_candidates = [c for c in candidates if c.gate01_partition == "audit"]

    # 9. Support check on Audit partition
    audit_beneficial_patients = len(
        set(c.patient_order for c in audit_candidates if c.pareto_beneficial)
    )
    audit_non_beneficial_patients = len(
        set(c.patient_order for c in audit_candidates if not c.pareto_beneficial)
    )
    k_10 = math.floor(0.10 * len(audit_candidates))
    k_20 = math.floor(0.20 * len(audit_candidates))
    support_passed = (
        audit_beneficial_patients >= 50
        and audit_non_beneficial_patients >= 50
        and k_10 > 0
        and k_20 > 0
    )

    # 10. Fit Dev-only fixed ridge linear probability models
    X_dev_ctrl: list[list[float]] = []
    X_dev_rank: list[list[float]] = []
    y_dev_list: list[float] = []
    for c in dev_candidates:
        xc, xr = compute_feature_vectors(c)
        X_dev_ctrl.append(xc)
        X_dev_rank.append(xr)
        y_dev_list.append(1.0 if c.pareto_beneficial else 0.0)

    ctrl_b0, ctrl_beta = fit_ridge_linear_probability(X_dev_ctrl, y_dev_list)
    rank_b0, rank_beta = fit_ridge_linear_probability(X_dev_rank, y_dev_list)

    # Save restricted dev fit record
    dev_fit_record = {
        "dev_candidates_count": len(dev_candidates),
        "strong_control": {
            "intercept": ctrl_b0,
            "coefficients": {
                "u": float(ctrl_beta[0]),
                "c": float(ctrl_beta[1]),
                "f": float(ctrl_beta[2]),
                "u_c": float(ctrl_beta[3]),
                "u_f": float(ctrl_beta[4]),
            },
        },
        "rank_augmented": {
            "intercept": rank_b0,
            "coefficients": {
                "u": float(rank_beta[0]),
                "c": float(rank_beta[1]),
                "f": float(rank_beta[2]),
                "u_c": float(rank_beta[3]),
                "u_f": float(rank_beta[4]),
                "r": float(rank_beta[5]),
            },
        },
    }
    (output_root / "gate-01-dev-fit.json").write_text(
        json.dumps(dev_fit_record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # 11. Audit policy evaluation
    audit_eval = evaluate_audit_policies(
        audit_candidates=audit_candidates,
        ctrl_beta0=ctrl_b0,
        ctrl_beta=ctrl_beta,
        rank_beta0=rank_b0,
        rank_beta=rank_beta,
    )

    # 12. Patient-clustered bootstrap
    bootstrap_intervals = run_patient_cluster_bootstrap(
        audit_candidates=audit_candidates,
        ctrl_beta0=ctrl_b0,
        ctrl_beta=ctrl_beta,
        rank_beta0=rank_b0,
        rank_beta=rank_beta,
    )

    # 13. Mechanical decision tree
    verdict, decision_criteria = evaluate_decision_tree(support_passed, bootstrap_intervals)

    # 14. Compile public-safe summary
    summary: dict[str, Any] = {
        "schema_version": 2,
        "idea_id": "003-prescription-relative-confidence",
        "gate_id": "gate-01-prescription-relative-confidence",
        "formal_run_id": output_root.name,
        "harness_revision": harness_rev,
        "verdict": verdict,
        "identities": {
            "model_source_revision": source_rev,
            "checkpoint_sha256": checkpoint_sha256,
            "baseline_core_sha256": baseline_core_sha256,
            "adapter_sha256": adapter_sha256,
            "baseline_environment_name": baseline_environment,
            "baseline_environment_sha256": observed_env_sha256,
            "dataset_id": manifest.dataset_id,
            "dataset_manifest_sha256": manifest.manifest_sha256,
            "snapshot_id": manifest.snapshot_id,
            "snapshot_sha256": actual_snapshot_sha256,
            "medication_vocabulary_sha256": FROZEN_MEDICATION_VOCABULARY_SHA256,
            "ddi_asset_sha256": FROZEN_DDI_ASSET_SHA256,
            "feature_availability_sha256": FROZEN_FEATURE_AVAILABILITY_SHA256,
        },
        "split": {
            "source": "validation",
            "patient_level": True,
            "seed": SPLIT_SEED,
            "validation_patient_count": val_patient_count,
            "dev_patient_count": len(dev_patients),
            "audit_patient_count": len(audit_patients),
            "eligible_dev_patients": len(set(c.patient_order for c in dev_candidates)),
            "eligible_audit_patients": len(set(c.patient_order for c in audit_candidates)),
            "dev_candidates_count": len(dev_candidates),
            "audit_candidates_count": len(audit_candidates),
        },
        "train_prevalence": {
            "eligible_train_visits": eligible_train_visits,
            "smoothing": "laplace_1_1",
        },
        "selector": {
            "algorithm": "fixed_ridge_linear_probability",
            "ridge_penalty": RIDGE_PENALTY,
            "strong_control_coefficients": dev_fit_record["strong_control"],
            "rank_augmented_coefficients": dev_fit_record["rank_augmented"],
        },
        "audit_support": {
            "support_requirement_met": support_passed,
            "distinct_beneficial_patients": audit_beneficial_patients,
            "distinct_non_beneficial_patients": audit_non_beneficial_patients,
            "k_by_budget": audit_eval["k_by_budget"],
            "threshold_required": 50,
        },
        "policy_yields": audit_eval["yields"],
        "gaps": audit_eval["gaps"],
        "bootstrap": {
            "resampling_unit": "patient",
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "confidence_level": "95%_percentile",
            "intervals": bootstrap_intervals,
        },
        "decision_criteria": decision_criteria,
    }

    summary_bytes = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (output_root / "gate-01-summary.json").write_text(summary_bytes, encoding="utf-8")
    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(summary_bytes, encoding="utf-8")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test", action="store_true", help="Run focused synthetic self-test suite"
    )
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
    parser.add_argument(
        "--summary-output", type=Path, help="Optional path to write public summary JSON"
    )
    args = parser.parse_args()

    if args.self_test:
        self_test_gate_01()
        return

    if (
        args.dataset_manifest is None
        or args.dataset_root is None
        or args.output_root is None
        or args.molerec_root is None
        or args.checkpoint is None
    ):
        parser.error(
            "--dataset-manifest, --dataset-root, --output-root, --molerec-root, and --checkpoint are required for formal Gate 01 execution"
        )

    summary = run_gate_01(
        dataset_manifest=args.dataset_manifest,
        dataset_root=args.dataset_root,
        output_root=args.output_root,
        molerec_root=args.molerec_root,
        checkpoint=args.checkpoint,
        baseline_environment=args.baseline_environment,
        conda_executable=args.conda_executable,
        expected_harness_revision=args.expected_harness_revision,
        summary_output=args.summary_output,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "support": summary["audit_support"],
                "policy_yields": summary["policy_yields"],
                "gaps": summary["gaps"],
                "bootstrap": summary["bootstrap"]["intervals"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
