#!/usr/bin/env python3
"""Gate 01 — Frequency-Corrected Co-Selection Compatibility.

Idea: 004-co-selection-compatibility
Stage: Idea / Hypothesis Selection
Scope: Retrospective validation-only evaluation of train-only frequency-corrected co-selection compatibility.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import shutil
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NamedTuple

_HARNESS_ROOT = Path(__file__).resolve().parents[4]
if str(_HARNESS_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_HARNESS_ROOT / "src"))

from medrec_research.adapters import ProcessPredictionAdapter  # noqa: E402
from medrec_research.dataset import DatasetManifest  # noqa: E402

BUDGETS: tuple[float, ...] = (0.10, 0.20, 0.30)
BUDGET_LABELS: dict[float, str] = {0.10: "10%", 0.20: "20%", 0.30: "30%"}

# Pinned scientific identities matching Gate 01 / Qualification v1.1
FROZEN_PROTOCOL_COMMIT = "a5f964be67f66852aba8dbfdbf2121b112046ae0"
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

SPLIT_SEED = 2004
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 1204
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
    candidate_count: int
    candidate_prevalence: float
    peer_prevalence_mean: float
    co_selection_compatibility: float  # A_t(m)
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
            "candidate_count": int(self.candidate_count),
            "candidate_prevalence": float(self.candidate_prevalence),
            "peer_prevalence_mean": float(self.peer_prevalence_mean),
            "co_selection_compatibility": float(self.co_selection_compatibility),
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
            candidate_count=int(data["candidate_count"]),
            candidate_prevalence=float(data["candidate_prevalence"]),
            peer_prevalence_mean=float(data["peer_prevalence_mean"]),
            co_selection_compatibility=float(data["co_selection_compatibility"]),
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


def _git_revision(directory: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def verify_clean_checkout(directory: Path, name: str) -> None:
    status_proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [
        line.strip()
        for line in status_proc.stdout.splitlines()
        if line.strip() and not line.strip().startswith("??")
    ]
    if lines:
        raise RuntimeError(
            f"{name} checkout at {directory} has uncommitted tracked changes:\n" + "\n".join(lines)
        )


def verify_frozen_molerec_identity(
    molerec_root: Path,
    checkpoint: Path,
    adapter_path: Path,
) -> tuple[str, str, str, str]:
    actual_source_rev = _git_revision(molerec_root)
    if actual_source_rev != FROZEN_MOLEREC_REVISION:
        raise ValueError(
            f"MoleRec source revision drift: expected {FROZEN_MOLEREC_REVISION}, got {actual_source_rev}"
        )
    if not checkpoint.exists():
        raise FileNotFoundError(f"MoleRec checkpoint not found at {checkpoint}")
    actual_checkpoint_sha256 = _file_sha256(checkpoint)
    if actual_checkpoint_sha256 != FROZEN_CHECKPOINT_SHA256:
        raise ValueError(
            f"Checkpoint checksum drift: expected {FROZEN_CHECKPOINT_SHA256}, got {actual_checkpoint_sha256}"
        )
    core_files = {
        "models.py": _file_sha256(molerec_root / "models.py"),
        "util.py": _file_sha256(molerec_root / "util.py"),
    }
    actual_core_sha256 = _content_sha256(core_files)
    if actual_core_sha256 != FROZEN_BASELINE_CORE_SHA256:
        raise ValueError(
            f"Baseline core checksum drift: expected {FROZEN_BASELINE_CORE_SHA256}, got {actual_core_sha256}"
        )
    actual_adapter_sha256 = _file_sha256(adapter_path)
    if actual_adapter_sha256 != FROZEN_ADAPTER_SHA256:
        raise ValueError(
            f"Adapter checksum drift: expected {FROZEN_ADAPTER_SHA256}, got {actual_adapter_sha256}"
        )
    return (
        actual_source_rev,
        actual_checkpoint_sha256,
        actual_core_sha256,
        actual_adapter_sha256,
    )


def verify_conda_environment(
    conda_executable: str | Path,
    environment_name: str,
) -> str:
    export_proc = subprocess.run(
        [str(conda_executable), "list", "-n", environment_name, "--export"],
        check=True,
        capture_output=True,
        text=True,
    )
    observed_spec = [
        line.strip()
        for line in export_proc.stdout.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    observed_sha256 = hashlib.sha256(
        ("\n".join(sorted(observed_spec)) + "\n").encode("utf-8")
    ).hexdigest()
    if observed_sha256 != FROZEN_BASELINE_ENVIRONMENT_SHA256:
        raise ValueError(
            f"Baseline Conda environment drift: expected {FROZEN_BASELINE_ENVIRONMENT_SHA256}, got {observed_sha256}"
        )
    return observed_sha256


def verify_dataset_manifest_and_snapshot(
    manifest_path: Path,
    dataset_root: Path,
    staged_meta: dict[str, Any],
) -> tuple[DatasetManifest, str]:
    manifest = DatasetManifest.from_file(manifest_path)
    if manifest.manifest_sha256 != FROZEN_DATASET_MANIFEST_SHA256:
        raise ValueError(
            f"Dataset manifest checksum drift: expected {FROZEN_DATASET_MANIFEST_SHA256}, got {manifest.manifest_sha256}"
        )
    if manifest.dataset_id != FROZEN_DATASET_ID:
        raise ValueError(
            f"Dataset ID drift: expected {FROZEN_DATASET_ID}, got {manifest.dataset_id}"
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


def compute_empirical_npmi(
    c_mj: int,
    c_m: int,
    c_j: int,
    v_train: int,
) -> float:
    """Empirical normalized pointwise mutual information with fixed boundaries."""
    if c_mj == 0:
        return -1.0
    if c_mj == v_train:
        return 1.0
    numerator = math.log((c_mj * v_train) / (c_m * c_j))
    denominator = -math.log(c_mj / v_train)
    return float(numerator / denominator)


def compute_co_selection_compatibility(
    candidate_med: str,
    predicted_meds: list[str],
    npmi_table: dict[tuple[str, str], float],
) -> float:
    r"""Exact train-only frequency-corrected co-selection compatibility observable.

    A_t(m) = \frac{1}{n_t - 1} \sum_{j \in \hat M_t \setminus \{m\}} NPMI_{train}(m, j)
    """
    n_t = len(predicted_meds)
    if n_t < 2:
        raise ValueError(f"Prescription size must be at least 2 for candidate, got {n_t}")

    other_meds = [j for j in predicted_meds if j != candidate_med]
    total_npmi = 0.0
    for j in other_meds:
        pair_key = (candidate_med, j) if candidate_med < j else (j, candidate_med)
        score = npmi_table.get(pair_key, -1.0)
        total_npmi += score
    return float(total_npmi / (n_t - 1))


def compute_feature_vectors(
    candidate: Gate01CandidateRecord,
    v_train: int,
) -> tuple[list[float], list[float]]:
    r"""Exact control and augmented feature vectors.

    u = 1 - s_t(m)
    c = log(1 + n_t)
    f = log((C(m) + 0.5) / (V_{train} - C(m) + 0.5))
    q_t(m) = mean peer prevalence
    eps = 0.5 / (V_{train} + 1)
    g = log((q_t(m) + eps) / (1 - q_t(m) + eps))

    x_{ctrl} = [u, c, f, g, u*c, u*f, u*g]
    x_{aug}  = [u, c, f, g, u*c, u*f, u*g, A_t(m)]
    """
    u = 1.0 - candidate.model_score
    n_t = candidate.prescription_size
    c_val = math.log(1.0 + n_t)
    c_m = candidate.candidate_count
    f_val = math.log((c_m + 0.5) / (v_train - c_m + 0.5))
    q_val = candidate.peer_prevalence_mean
    eps = 0.5 / (v_train + 1.0)
    g_val = math.log((q_val + eps) / (1.0 - q_val + eps))

    u_c = u * c_val
    u_f = u * f_val
    u_g = u * g_val

    x_ctrl = [u, c_val, f_val, g_val, u_c, u_f, u_g]
    x_aug = [
        u,
        c_val,
        f_val,
        g_val,
        u_c,
        u_f,
        u_g,
        candidate.co_selection_compatibility,
    ]
    return x_ctrl, x_aug


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
    train_counts: dict[str, int],
    train_prevalence: dict[str, float],
    npmi_table: dict[tuple[str, str], float],
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

            # Observable: CoSelectionCompatibility A_t(m)
            a_t = compute_co_selection_compatibility(med, predicted_meds, npmi_table)

            # Peer-set mean prevalence
            other_meds = [j for j in predicted_meds if j != med]
            peer_prev_mean = sum(train_prevalence.get(j, 0.0) for j in other_meds) / (n_t - 1)

            # Singleton deletion revision outcome
            rev_meds = set(predicted_meds) - {med}
            j_denom_rev = len(rev_meds | target_meds)
            j_rev = len(rev_meds & target_meds) / j_denom_rev if j_denom_rev > 0 else 0.0
            delta_j = j_rev - j_orig
            delta_v = -deg  # strictly reduces violation

            # Pareto-beneficial: false-positive status m not in M_t
            pareto_beneficial = med not in target_meds
            s_m = vocab_scores[med]
            c_m = train_counts.get(med, 0)
            p_m = train_prevalence.get(med, 0.0)

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
                    candidate_count=c_m,
                    candidate_prevalence=p_m,
                    peer_prevalence_mean=peer_prev_mean,
                    co_selection_compatibility=a_t,
                    active_ddi_degree=deg,
                    pareto_beneficial=pareto_beneficial,
                    delta_jaccard=delta_j,
                    delta_violation=delta_v,
                )
            )

    return candidates


def _solve_linear_system(A: list[list[float]], b: list[float]) -> list[float]:
    """Pure-Python Gauss-Jordan solver for small positive-definite systems."""
    n = len(A)
    M = [[*A[i], b[i]] for i in range(n)]

    for i in range(n):
        pivot = i
        max_val = abs(M[i][i])
        for r in range(i + 1, n):
            if abs(M[r][i]) > max_val:
                max_val = abs(M[r][i])
                pivot = r
        if max_val < 1e-15:
            raise ValueError(f"Matrix is singular at row {i}")
        if pivot != i:
            M[i], M[pivot] = M[pivot], M[i]

        div = M[i][i]
        for j in range(i, n + 1):
            M[i][j] /= div

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
    return sorted_v[low] * (1.0 - weight) + sorted_v[high] * weight


def evaluate_audit_policies(
    audit_candidates: list[Gate01CandidateRecord],
    ctrl_beta0: float,
    ctrl_beta: list[float],
    aug_beta0: float,
    aug_beta: list[float],
    v_train: int,
) -> dict[str, Any]:
    """Evaluate candidate rankings under all four policies on Audit candidates."""
    n_a = len(audit_candidates)
    if n_a == 0:
        raise ValueError("Audit candidates list is empty")

    # 1. Random base-rate yield
    random_yield = sum(1 for c in audit_candidates if c.pareto_beneficial) / n_a

    # 2. Compute fitted risks
    audit_ctrl_risks: list[float] = []
    audit_aug_risks: list[float] = []
    for c in audit_candidates:
        x_ctrl, x_aug = compute_feature_vectors(c, v_train)
        r_ctrl = ctrl_beta0 + sum(x_ctrl[j] * ctrl_beta[j] for j in range(len(x_ctrl)))
        r_aug = aug_beta0 + sum(x_aug[j] * aug_beta[j] for j in range(len(x_aug)))
        audit_ctrl_risks.append(r_ctrl)
        audit_aug_risks.append(r_aug)

    scored_items = list(zip(audit_candidates, audit_ctrl_risks, audit_aug_risks, strict=True))

    # Deterministic 5-key tie-breaks:
    # 1. fitted risk descending (-risk)
    # 2. frozen medication score ascending (model_score)
    # 3. medication code ascending (medication_code)
    # 4. patient_order ascending (patient_order)
    # 5. visit_order ascending (visit_order)
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
    aug_sorted = [
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
        "co_selection_augmented": {},
        "oracle": {},
    }
    gaps: dict[str, dict[str, float]] = {
        "co_selection_minus_control": {},
        "oracle_minus_control": {},
        "control_minus_score": {},
    }

    k_by_budget: dict[str, int] = {}

    for budget in BUDGETS:
        label = BUDGET_LABELS[budget]
        k = math.floor(budget * n_a)
        k_by_budget[label] = k

        if k == 0:
            for policy_name in yields:
                yields[policy_name][label] = 0.0
            for gap_name in gaps:
                gaps[gap_name][label] = 0.0
            continue

        y_rand = random_yield
        y_score = sum(1 for c in score_sorted[:k] if c.pareto_beneficial) / k
        y_ctrl = sum(1 for c in ctrl_sorted[:k] if c.pareto_beneficial) / k
        y_aug = sum(1 for c in aug_sorted[:k] if c.pareto_beneficial) / k
        y_oracle = sum(1 for c in oracle_sorted[:k] if c.pareto_beneficial) / k

        yields["random"][label] = y_rand
        yields["score_only"][label] = y_score
        yields["strong_control"][label] = y_ctrl
        yields["co_selection_augmented"][label] = y_aug
        yields["oracle"][label] = y_oracle

        gaps["co_selection_minus_control"][label] = y_aug - y_ctrl
        gaps["oracle_minus_control"][label] = y_oracle - y_ctrl
        gaps["control_minus_score"][label] = y_ctrl - y_score

    return {
        "k_by_budget": k_by_budget,
        "yields": yields,
        "gaps": gaps,
        "audit_candidates_count": n_a,
    }


def run_patient_cluster_bootstrap(
    audit_candidates: list[Gate01CandidateRecord],
    ctrl_beta0: float,
    ctrl_beta: list[float],
    aug_beta0: float,
    aug_beta: list[float],
    v_train: int,
    n_replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, dict[str, dict[str, float]]]:
    """Preregistered patient-clustered bootstrap (seed 1204, 1000 replicates).

    Preserves duplicate patient draws as distinct bootstrap clusters.
    Keeps Dev coefficients frozen without refitting.
    """
    candidates_by_patient: dict[int, list[Gate01CandidateRecord]] = {}
    for c in audit_candidates:
        candidates_by_patient.setdefault(c.patient_order, []).append(c)

    unique_patients = sorted(candidates_by_patient.keys())
    n_patients = len(unique_patients)
    rng = random.Random(seed)

    gap_samples: dict[str, dict[str, list[float]]] = {
        "co_selection_minus_control": {label: [] for label in BUDGET_LABELS.values()},
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
                        candidate_count=c.candidate_count,
                        candidate_prevalence=c.candidate_prevalence,
                        peer_prevalence_mean=c.peer_prevalence_mean,
                        co_selection_compatibility=c.co_selection_compatibility,
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
            aug_beta0=aug_beta0,
            aug_beta=aug_beta,
            v_train=v_train,
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
        "gate_c_co_selection_incremental_10": False,
        "gate_c_co_selection_incremental_20": False,
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

    # Gate C: CoSelectionAugmented - StrongControl > 0 at both 10% and 20%
    aug_10_lower = bootstrap_intervals["co_selection_minus_control"]["10%"]["lower"]
    aug_20_lower = bootstrap_intervals["co_selection_minus_control"]["20%"]["lower"]
    crit["gate_c_co_selection_incremental_10"] = aug_10_lower > 0.0
    crit["gate_c_co_selection_incremental_20"] = aug_20_lower > 0.0

    if crit["gate_c_co_selection_incremental_10"] and crit["gate_c_co_selection_incremental_20"]:
        return "PASS_INCREMENTAL_CO_SELECTION_COMPATIBILITY", crit

    return "STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY", crit


def self_test_gate_01() -> None:
    """Focused synthetic unit test suite verifying all 7 critical paths."""
    print("Running Gate 01 focused synthetic self-test...")

    # 1. NPMI: zero co-selection -> -1.0; full joint support -> +1.0; normal empirical case matches formula
    assert compute_empirical_npmi(0, 10, 20, 100) == -1.0
    assert compute_empirical_npmi(100, 100, 100, 100) == 1.0
    c_mj, c_m, c_j, v = 5, 10, 20, 100
    expected_npmi = math.log((5 * 100) / (10 * 20)) / (-math.log(5 / 100))
    assert math.isclose(compute_empirical_npmi(c_mj, c_m, c_j, v), expected_npmi)

    # 2. Candidate A_t(m) is the exact peer mean
    npmi_tbl = {
        ("M1", "M2"): 0.5,
        ("M1", "M3"): -0.25,
        ("M2", "M3"): 0.8,
    }
    a_m1 = compute_co_selection_compatibility("M1", ["M1", "M2", "M3"], npmi_tbl)
    assert math.isclose(a_m1, (0.5 + (-0.25)) / 2.0)

    # 3. Seed-2004 split is deterministic and patient-disjoint
    dev_p1, audit_p1 = partition_validation_patients(range(1059), seed=2004)
    dev_p2, audit_p2 = partition_validation_patients(range(1059), seed=2004)
    assert dev_p1 == dev_p2
    assert audit_p1 == audit_p2
    assert len(dev_p1) == 529
    assert len(audit_p1) == 530
    assert len(dev_p1 & audit_p1) == 0
    assert len(dev_p1 | audit_p1) == 1059

    # 4. StrongControl and CoSelectionAugmented differ by exactly one feature
    dummy_cand = Gate01CandidateRecord(
        patient_id="p1",
        visit_id="v1",
        patient_order=0,
        visit_order=1,
        gate01_partition="dev",
        medication_code="M1",
        model_score=0.8,
        prescription_size=3,
        candidate_count=20,
        candidate_prevalence=0.02,
        peer_prevalence_mean=0.05,
        co_selection_compatibility=0.123,
        active_ddi_degree=1,
        pareto_beneficial=True,
        delta_jaccard=0.1,
        delta_violation=-1,
    )
    xc, xa = compute_feature_vectors(dummy_cand, v_train=1000)
    assert len(xc) == 7
    assert len(xa) == 8
    assert xa[:7] == xc
    assert xa[7] == dummy_cand.co_selection_compatibility

    # 5. Deterministic tie-breaking is exact
    c1 = Gate01CandidateRecord(
        "p1", "v1", 2, 1, "audit", "M1", 0.6, 2, 10, 0.1, 0.1, 0.0, 1, True, 0.1, -1
    )
    c2 = Gate01CandidateRecord(
        "p2", "v1", 1, 1, "audit", "M1", 0.6, 2, 10, 0.1, 0.1, 0.0, 1, True, 0.1, -1
    )
    c3 = Gate01CandidateRecord(
        "p2", "v2", 1, 2, "audit", "M1", 0.6, 2, 10, 0.1, 0.1, 0.0, 1, True, 0.1, -1
    )
    c4 = Gate01CandidateRecord(
        "p1", "v1", 2, 1, "audit", "M2", 0.6, 2, 10, 0.1, 0.1, 0.0, 1, True, 0.1, -1
    )
    sorted_c = sorted(
        [c4, c1, c3, c2],
        key=lambda c: (c.model_score, c.medication_code, c.patient_order, c.visit_order),
    )
    assert sorted_c == [c2, c3, c1, c4]

    # 6. Patient-cluster bootstrap does not refit Dev models
    X_dev = [[random.gauss(0, 1) for _ in range(7)] for _ in range(30)]
    y_dev = [float(random.choice([0, 1])) for _ in range(30)]
    b0_1, beta_1 = fit_ridge_linear_probability(X_dev, y_dev)
    b0_2, beta_2 = fit_ridge_linear_probability(X_dev, y_dev)
    assert b0_1 == b0_2 and beta_1 == beta_2

    # 7. Decision tree paths
    v_supp, _ = evaluate_decision_tree(False, {})
    assert v_supp == "INCONCLUSIVE_INSUFFICIENT_AUDIT_SUPPORT"

    intervals_no_head = {
        "oracle_minus_control": {
            "10%": {"lower": -0.01, "upper": 0.10},
            "20%": {"lower": 0.05, "upper": 0.15},
        },
        "co_selection_minus_control": {
            "10%": {"lower": 0.02, "upper": 0.05},
            "20%": {"lower": 0.01, "upper": 0.04},
        },
    }
    v_head, _ = evaluate_decision_tree(True, intervals_no_head)
    assert v_head == "STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL"

    intervals_pass = {
        "oracle_minus_control": {
            "10%": {"lower": 0.30, "upper": 0.50},
            "20%": {"lower": 0.30, "upper": 0.50},
        },
        "co_selection_minus_control": {
            "10%": {"lower": 0.02, "upper": 0.05},
            "20%": {"lower": 0.01, "upper": 0.04},
        },
    }
    v_pass, _ = evaluate_decision_tree(True, intervals_pass)
    assert v_pass == "PASS_INCREMENTAL_CO_SELECTION_COMPATIBILITY"

    intervals_fail = {
        "oracle_minus_control": {
            "10%": {"lower": 0.30, "upper": 0.50},
            "20%": {"lower": 0.30, "upper": 0.50},
        },
        "co_selection_minus_control": {
            "10%": {"lower": -0.01, "upper": 0.05},
            "20%": {"lower": 0.01, "upper": 0.04},
        },
    }
    v_fail, _ = evaluate_decision_tree(True, intervals_fail)
    assert v_fail == "STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY"

    print("Gate 01 focused synthetic self-test passed successfully.")


def run_co_selection_compatibility_gate(
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

    # 4. Stage validation inputs and train-only co-selection statistics in medrec-molerec-table1 Python 3.8 env
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
    train_stats = json.loads(Path(meta["train_statistics_path"]).read_text(encoding="utf-8"))
    train_counts: dict[str, int] = train_stats["counts"]
    train_prevalence: dict[str, float] = train_stats["prevalence"]
    eligible_train_visits = int(train_stats["eligible_train_visits"])

    # Load pair NPMI table
    raw_npmi: dict[str, float] = train_stats["npmi"]
    npmi_table: dict[tuple[str, str], float] = {}
    for key, val in raw_npmi.items():
        parts = key.split(":")
        pair = (parts[0], parts[1]) if parts[0] < parts[1] else (parts[1], parts[0])
        npmi_table[pair] = float(val)

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

    # 8. Build candidate records Q_t with train-only co-selection observable A_t(m)
    candidates = build_candidate_records(
        predictions=predictions,
        targets=targets,
        ddi_pairs=ddi_pairs,
        traversal_by_visit=traversal_by_visit,
        dev_patients=dev_patients,
        train_counts=train_counts,
        train_prevalence=train_prevalence,
        npmi_table=npmi_table,
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
    X_dev_aug: list[list[float]] = []
    y_dev_list: list[float] = []
    for c in dev_candidates:
        xc, xa = compute_feature_vectors(c, eligible_train_visits)
        X_dev_ctrl.append(xc)
        X_dev_aug.append(xa)
        y_dev_list.append(1.0 if c.pareto_beneficial else 0.0)

    ctrl_b0, ctrl_beta = fit_ridge_linear_probability(X_dev_ctrl, y_dev_list)
    aug_b0, aug_beta = fit_ridge_linear_probability(X_dev_aug, y_dev_list)

    # Save restricted dev fit record
    dev_fit_record = {
        "dev_candidates_count": len(dev_candidates),
        "strong_control": {
            "intercept": ctrl_b0,
            "coefficients": {
                "u": float(ctrl_beta[0]),
                "c": float(ctrl_beta[1]),
                "f": float(ctrl_beta[2]),
                "g": float(ctrl_beta[3]),
                "u_c": float(ctrl_beta[4]),
                "u_f": float(ctrl_beta[5]),
                "u_g": float(ctrl_beta[6]),
            },
        },
        "co_selection_augmented": {
            "intercept": aug_b0,
            "coefficients": {
                "u": float(aug_beta[0]),
                "c": float(aug_beta[1]),
                "f": float(aug_beta[2]),
                "g": float(aug_beta[3]),
                "u_c": float(aug_beta[4]),
                "u_f": float(aug_beta[5]),
                "u_g": float(aug_beta[6]),
                "co_selection_compatibility": float(aug_beta[7]),
            },
        },
    }
    (output_root / "gate-01-dev-fit.json").write_text(
        json.dumps(dev_fit_record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # 11. Evaluate all policies on Audit partition
    eval_audit = evaluate_audit_policies(
        audit_candidates=audit_candidates,
        ctrl_beta0=ctrl_b0,
        ctrl_beta=ctrl_beta,
        aug_beta0=aug_b0,
        aug_beta=aug_beta,
        v_train=eligible_train_visits,
    )

    # 12. Run patient-clustered bootstrap on Audit candidates
    bootstrap_intervals = run_patient_cluster_bootstrap(
        audit_candidates=audit_candidates,
        ctrl_beta0=ctrl_b0,
        ctrl_beta=ctrl_beta,
        aug_beta0=aug_b0,
        aug_beta=aug_beta,
        v_train=eligible_train_visits,
        n_replicates=BOOTSTRAP_REPLICATES,
        seed=BOOTSTRAP_SEED,
    )

    # 13. Evaluate preregistered mechanical decision tree
    verdict, criteria = evaluate_decision_tree(
        support_passed=support_passed,
        bootstrap_intervals=bootstrap_intervals,
    )

    formal_run_id = output_root.name

    # Public-safe summary artifact
    summary_data = {
        "schema_version": 2,
        "gate_id": "gate-01-co-selection-compatibility",
        "idea_id": "004-co-selection-compatibility",
        "formal_run_id": formal_run_id,
        "harness_revision": harness_rev,
        "verdict": verdict,
        "decision_criteria": criteria,
        "identities": {
            "model_source_revision": source_rev,
            "checkpoint_sha256": checkpoint_sha256,
            "baseline_core_sha256": baseline_core_sha256,
            "adapter_sha256": adapter_sha256,
            "baseline_environment_name": baseline_environment,
            "baseline_environment_sha256": observed_env_sha256,
            "dataset_id": manifest.dataset_id,
            "dataset_manifest_sha256": manifest.manifest_sha256,
            "snapshot_id": FROZEN_SNAPSHOT_ID,
            "snapshot_sha256": actual_snapshot_sha256,
            "medication_vocabulary_sha256": FROZEN_MEDICATION_VOCABULARY_SHA256,
            "ddi_asset_sha256": FROZEN_DDI_ASSET_SHA256,
            "feature_availability_sha256": FROZEN_FEATURE_AVAILABILITY_SHA256,
        },
        "split": {
            "patient_level": True,
            "seed": SPLIT_SEED,
            "source": "validation",
            "validation_patient_count": val_patient_count,
            "dev_patient_count": len(dev_patients),
            "audit_patient_count": len(audit_patients),
            "eligible_dev_patients": len(set(c.patient_order for c in dev_candidates)),
            "eligible_audit_patients": len(set(c.patient_order for c in audit_candidates)),
            "dev_candidates_count": len(dev_candidates),
            "audit_candidates_count": len(audit_candidates),
        },
        "train_statistics": {
            "eligible_train_visits": eligible_train_visits,
            "formula": "empirical_npmi",
        },
        "audit_support": {
            "threshold_required": 50,
            "distinct_beneficial_patients": audit_beneficial_patients,
            "distinct_non_beneficial_patients": audit_non_beneficial_patients,
            "k_by_budget": eval_audit["k_by_budget"],
            "support_requirement_met": support_passed,
        },
        "selector": {
            "algorithm": "fixed_ridge_linear_probability",
            "ridge_penalty": RIDGE_PENALTY,
            "strong_control_coefficients": dev_fit_record["strong_control"],
            "co_selection_augmented_coefficients": dev_fit_record["co_selection_augmented"],
        },
        "policy_yields": eval_audit["yields"],
        "gaps": eval_audit["gaps"],
        "bootstrap": {
            "seed": BOOTSTRAP_SEED,
            "replicates": BOOTSTRAP_REPLICATES,
            "resampling_unit": "patient",
            "confidence_level": "95%_percentile",
            "intervals": bootstrap_intervals,
        },
    }

    summary_json_str = json.dumps(summary_data, indent=2, sort_keys=True) + "\n"
    (output_root / "gate-01-summary.json").write_text(summary_json_str, encoding="utf-8")

    if summary_output is not None:
        summary_output.resolve().parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(summary_json_str, encoding="utf-8")

    return summary_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test", action="store_true", help="Run focused synthetic self-test suite"
    )
    parser.add_argument(
        "--dataset-manifest", type=Path, help="Path to authoritative DatasetManifest JSON"
    )
    parser.add_argument("--dataset-root", type=Path, help="Path to raw dataset snapshot root")
    parser.add_argument("--output-root", type=Path, help="Path to run output root")
    parser.add_argument("--molerec-root", type=Path, help="Path to MoleRec repository root")
    parser.add_argument("--checkpoint", type=Path, help="Path to MoleRec checkpoint file")
    parser.add_argument("--baseline-environment", default=FROZEN_BASELINE_ENVIRONMENT_NAME)
    parser.add_argument("--conda-executable", default=None)
    parser.add_argument("--expected-harness-revision", default=None)
    parser.add_argument("--summary-output", type=Path, default=None)
    args = parser.parse_args()

    if args.self_test:
        self_test_gate_01()
        return

    if not all(
        [
            args.dataset_manifest,
            args.dataset_root,
            args.output_root,
            args.molerec_root,
            args.checkpoint,
        ]
    ):
        parser.error(
            "Missing required execution arguments: --dataset-manifest, --dataset-root, "
            "--output-root, --molerec-root, --checkpoint (or pass --self-test)."
        )

    summary = run_co_selection_compatibility_gate(
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
    print(f"Gate 01 execution complete. Verdict: {summary['verdict']}")


if __name__ == "__main__":
    main()
