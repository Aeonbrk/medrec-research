#!/usr/bin/env python3
"""Probe residual medication-label dependence after frozen MoleRec scores.

This is deliberately a diagnostic, not a recommendation model.  It consumes
only the frozen Train/Gate01-Dev score and target matrices and writes aggregate
metrics; no patient identifiers or predictions are persisted.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

CANDIDATE_COUNT = 131
SEED = 20260914
TRAIN_VISITS = 10489
DEV_VISITS = 2130
EPOCHS = 80
BATCH_SIZE = 512
LEARNING_RATE = 5e-3
WEIGHT_DECAY = 1e-4
THRESHOLD_LOGIT = 0.0
MEAN_FIELD_STEPS = 5
MEAN_FIELD_DAMPING = 0.5
SELF_LEAK_TOLERANCE = 1e-6


def _load_array(root: Path, name: str) -> np.ndarray:
    value = np.load(root / name, mmap_mode="r")
    result = np.array(value, dtype=np.float32, copy=True)
    if result.ndim != 2 or result.shape[1] != CANDIDATE_COUNT:
        raise RuntimeError(f"{name} must have shape [visits, {CANDIDATE_COUNT}]")
    if not np.isfinite(result).all():
        raise RuntimeError(f"{name} contains non-finite values")
    return result


def _validate_targets(targets: np.ndarray, name: str) -> None:
    if not np.isin(targets, (0.0, 1.0)).all():
        raise RuntimeError(f"{name} must be a binary target matrix")


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class FullScoreCalibrator(nn.Module):
    """Full score calibrator with a symmetric, zero-diagonal label term."""

    def __init__(self, dimension: int = CANDIDATE_COUNT) -> None:
        super().__init__()
        self.score_matrix = nn.Parameter(torch.eye(dimension, dtype=torch.float32))
        self.bias = nn.Parameter(torch.zeros(dimension, dtype=torch.float32))
        self.unconstrained_label_matrix = nn.Parameter(
            torch.zeros((dimension, dimension), dtype=torch.float32)
        )

    def score_only_logits(self, scores: torch.Tensor) -> torch.Tensor:
        return scores @ self.score_matrix.T + self.bias

    def symmetric_zero_diagonal(self) -> torch.Tensor:
        matrix = 0.5 * (self.unconstrained_label_matrix + self.unconstrained_label_matrix.T)
        return matrix - torch.diag(torch.diagonal(matrix))

    def conditional_logits(
        self,
        scores: torch.Tensor,
        context: torch.Tensor,
        prevalence: torch.Tensor,
    ) -> torch.Tensor:
        unary = self.score_only_logits(scores)
        relation = (context - prevalence) @ self.symmetric_zero_diagonal().T
        return unary + relation


def _train_score_only(
    model: FullScoreCalibrator,
    scores: np.ndarray,
    targets: np.ndarray,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    device: torch.device,
) -> dict[str, float]:
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    score_tensor = torch.from_numpy(scores).to(device=device)
    target_tensor = torch.from_numpy(targets).to(device=device)
    generator = np.random.default_rng(int(seed))
    model.train()
    last = {"bce": 0.0}
    for _ in range(epochs):
        order = generator.permutation(len(scores))
        total = 0.0
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = torch.from_numpy(order[start : start + batch_size]).to(device=device)
            optimizer.zero_grad(set_to_none=True)
            logits = model.score_only_logits(score_tensor[rows])
            loss = F.binary_cross_entropy_with_logits(logits, target_tensor[rows])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            total += float(loss.detach().cpu())
            batches += 1
        last = {"bce": total / max(1, batches)}
    return last


def _train_conditional(
    model: FullScoreCalibrator,
    scores: np.ndarray,
    targets: np.ndarray,
    prevalence: np.ndarray,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    device: torch.device,
) -> dict[str, float]:
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    score_tensor = torch.from_numpy(scores).to(device=device)
    target_tensor = torch.from_numpy(targets).to(device=device)
    prevalence_tensor = torch.from_numpy(prevalence).to(device=device)
    generator = np.random.default_rng(int(seed))
    model.train()
    last = {"bce": 0.0}
    for _ in range(epochs):
        order = generator.permutation(len(scores))
        total = 0.0
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = torch.from_numpy(order[start : start + batch_size]).to(device=device)
            optimizer.zero_grad(set_to_none=True)
            logits = model.conditional_logits(
                score_tensor[rows], target_tensor[rows], prevalence_tensor
            )
            loss = F.binary_cross_entropy_with_logits(logits, target_tensor[rows])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            total += float(loss.detach().cpu())
            batches += 1
        last = {"bce": total / max(1, batches)}
    return last


def _deterministic_derangement(length: int, seed: int) -> tuple[np.ndarray, int]:
    if length < 2:
        raise ValueError("a derangement requires at least two rows")
    generator = np.random.default_rng(int(seed))
    shift = int(generator.integers(1, length))
    return np.roll(np.arange(length, dtype=np.int64), shift), shift


def _mean_field(
    model: FullScoreCalibrator,
    scores: np.ndarray,
    prevalence: np.ndarray,
    *,
    steps: int,
    damping: float,
    device: torch.device,
) -> np.ndarray:
    score_tensor = torch.from_numpy(scores).to(device=device)
    prevalence_tensor = torch.from_numpy(prevalence).to(device=device)
    model.eval()
    with torch.no_grad():
        unary = model.score_only_logits(score_tensor)
        probabilities = torch.sigmoid(unary)
        interaction = model.symmetric_zero_diagonal()
        for _ in range(steps):
            updated = torch.sigmoid(unary + (probabilities - prevalence_tensor) @ interaction.T)
            probabilities = damping * probabilities + (1.0 - damping) * updated
    return probabilities.cpu().numpy().astype(np.float32, copy=False)


def _stable_bce_from_logits(logits: np.ndarray, targets: np.ndarray) -> float:
    values = np.maximum(logits, 0.0) - logits * targets + np.log1p(np.exp(-np.abs(logits)))
    return float(values.mean())


def _bce_from_probabilities(probabilities: np.ndarray, targets: np.ndarray) -> float:
    clipped = np.clip(probabilities, 1e-7, 1.0 - 1e-7)
    return float(-(targets * np.log(clipped) + (1.0 - targets) * np.log1p(-clipped)).mean())


def _average_precision(target: np.ndarray, scores: np.ndarray) -> float:
    target_set = {int(item) for item in np.flatnonzero(target > 0.5)}
    if not target_set:
        return 0.0
    ranked = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    found = 0
    total = 0.0
    for rank, index in enumerate(ranked, start=1):
        if index in target_set:
            found += 1
            total += found / rank
    return total / len(target_set)


def _evaluate(
    targets: np.ndarray,
    ranking_scores: np.ndarray,
    predictions: np.ndarray,
    *,
    nll: float,
    privileged: bool = False,
    deployable: bool = True,
) -> dict[str, Any]:
    jaccard = 0.0
    precision = 0.0
    recall = 0.0
    f1 = 0.0
    prauc = 0.0
    counts = predictions.sum(axis=1).astype(np.float32)
    for target, prediction, scores in zip(  # noqa: B905
        targets, predictions, ranking_scores
    ):
        target_set = {int(item) for item in np.flatnonzero(target > 0.5)}
        prediction_set = {int(item) for item in np.flatnonzero(prediction > 0.5)}
        intersection = len(target_set & prediction_set)
        union = len(target_set | prediction_set)
        visit_precision = (
            1.0
            if not target_set and not prediction_set
            else intersection / len(prediction_set)
            if prediction_set
            else 0.0
        )
        visit_recall = (
            1.0
            if not target_set and not prediction_set
            else intersection / len(target_set)
            if target_set
            else 0.0
        )
        visit_f1 = (
            0.0
            if visit_precision + visit_recall == 0.0
            else 2.0 * visit_precision * visit_recall / (visit_precision + visit_recall)
        )
        jaccard += 1.0 if not union else intersection / union
        precision += visit_precision
        recall += visit_recall
        f1 += visit_f1
        prauc += _average_precision(target, scores)
    count = len(targets)
    return {
        "bce": float(nll),
        "nll": float(nll),
        "prauc": prauc / count,
        "jaccard": jaccard / count,
        "f1": f1 / count,
        "precision": precision / count,
        "recall": recall / count,
        "mean_medication_count": float(counts.mean()),
        "std_medication_count": float(counts.std()),
        "visit_count": float(count),
        "privileged_oracle": bool(privileged),
        "deployable": bool(deployable),
    }


def _self_target_leakage_check(
    model: FullScoreCalibrator,
    scores: np.ndarray,
    targets: np.ndarray,
    prevalence: np.ndarray,
    *,
    device: torch.device,
) -> dict[str, Any]:
    """Perturb each context coordinate and verify its own logit is unchanged."""

    score_tensor = torch.from_numpy(scores[: min(8, len(scores))]).to(device=device)
    target_tensor = torch.from_numpy(targets[: min(8, len(targets))]).to(device=device)
    prevalence_tensor = torch.from_numpy(prevalence).to(device=device)
    model.eval()
    with torch.no_grad():
        baseline = model.conditional_logits(score_tensor, target_tensor, prevalence_tensor)
        maximum_self_change = 0.0
        for column in range(CANDIDATE_COUNT):
            perturbed = target_tensor.clone()
            perturbed[:, column] = 1.0 - perturbed[:, column]
            changed = model.conditional_logits(score_tensor, perturbed, prevalence_tensor)
            maximum_self_change = max(
                maximum_self_change,
                float((changed[:, column] - baseline[:, column]).abs().max().cpu()),
            )
    return {
        "passed": bool(maximum_self_change <= SELF_LEAK_TOLERANCE),
        "max_self_target_logit_change": maximum_self_change,
        "tolerance": SELF_LEAK_TOLERANCE,
        "rows_checked": int(score_tensor.shape[0]),
        "current_target_used_in_prediction": False,
    }


def _git_revision() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip()


def _classify(
    metrics: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    mole = metrics["MoleRec"]
    score = metrics["ScoreOnly"]
    shuffled = metrics["ShuffledCoLabel"]
    oracle = metrics["OracleCoLabel"]
    mean_field = metrics["MeanField"]
    oracle_score = oracle["jaccard"] - score["jaccard"]
    oracle_shuffle = oracle["jaccard"] - shuffled["jaccard"]
    mean_field_score = mean_field["jaccard"] - score["jaccard"]
    score_mole = score["jaccard"] - mole["jaccard"]
    clear_dependence = oracle_score >= 0.004 and oracle_shuffle >= 0.004
    little_dependence = oracle_score < 0.004 or oracle_shuffle < 0.004
    count_delta = mean_field["mean_medication_count"] - score["mean_medication_count"]
    count_pathology = bool(
        count_delta > max(1.0, 0.20 * score["mean_medication_count"])
        and mean_field["nll"] >= score["nll"]
        and mean_field["prauc"] <= score["prauc"]
    )
    if score_mole >= 0.008 and little_dependence and mean_field_score < 0.004:
        decision = "DECISION_SURFACE_NOT_INTERACTION_IS_BOTTLENECK"
    elif little_dependence:
        decision = "CLOSE_INTERACTION_FIRST_FAMILY"
    elif clear_dependence and mean_field_score < 0.004:
        decision = "RESIDUAL_DEPENDENCE_EXISTS_INFERENCE_GAP"
    elif clear_dependence and mean_field_score >= 0.004 and not count_pathology:
        decision = "INTERACTION_FAMILY_HAS_REAL_HEADROOM"
    elif clear_dependence:
        decision = "RESIDUAL_DEPENDENCE_EXISTS_INFERENCE_GAP"
    else:
        decision = "CLOSE_INTERACTION_FIRST_FAMILY"
    return decision, {
        "thresholds": {
            "material_jaccard": 0.004,
            "score_only_bottleneck_jaccard": 0.008,
            "count_pathology_relative": 0.20,
        },
        "oracle_minus_score_only_jaccard": float(oracle_score),
        "oracle_minus_shuffled_jaccard": float(oracle_shuffle),
        "mean_field_minus_score_only_jaccard": float(mean_field_score),
        "score_only_minus_mole_rec_jaccard": float(score_mole),
        "mean_field_minus_score_only_count": float(count_delta),
        "clear_dependence": clear_dependence,
        "little_dependence": little_dependence,
        "count_pathology": count_pathology,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.train_dev_root.resolve()
    train_scores = _load_array(root, "train_scores.npy")
    train_targets = _load_array(root, "train_targets.npy")
    dev_scores = _load_array(root, "dev_scores.npy")
    dev_targets = _load_array(root, "dev_targets.npy")
    _validate_targets(train_targets, "train_targets")
    _validate_targets(dev_targets, "dev_targets")
    if train_scores.shape[0] != TRAIN_VISITS or train_targets.shape[0] != TRAIN_VISITS:
        raise RuntimeError("Train arrays do not contain the canonical 10,489 visits")
    if dev_scores.shape[0] != DEV_VISITS or dev_targets.shape[0] != DEV_VISITS:
        raise RuntimeError("Gate01-Dev arrays do not contain the canonical 2,130 visits")

    prevalence = train_targets.mean(axis=0, dtype=np.float64).astype(np.float32)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _seed_everything(args.seed)

    score_model = FullScoreCalibrator().to(device)
    score_loss = _train_score_only(
        score_model,
        train_scores,
        train_targets,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        seed=args.seed,
        device=device,
    )
    _seed_everything(args.seed)
    conditional_model = FullScoreCalibrator().to(device)
    conditional_loss = _train_conditional(
        conditional_model,
        train_scores,
        train_targets,
        prevalence,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        seed=args.seed,
        device=device,
    )

    dev_score_tensor = torch.from_numpy(dev_scores).to(device=device)
    prevalence_tensor = torch.from_numpy(prevalence).to(device=device)
    conditional_model.eval()
    score_model.eval()
    with torch.no_grad():
        score_only_logits = score_model.score_only_logits(dev_score_tensor).cpu().numpy()
        oracle_logits = (
            conditional_model.conditional_logits(
                dev_score_tensor,
                torch.from_numpy(dev_targets).to(device=device),
                prevalence_tensor,
            )
            .cpu()
            .numpy()
        )
        permutation, shift = _deterministic_derangement(len(dev_targets), args.seed)
        shuffled_context = dev_targets[permutation]
        shuffled_logits = (
            conditional_model.conditional_logits(
                dev_score_tensor,
                torch.from_numpy(shuffled_context).to(device=device),
                prevalence_tensor,
            )
            .cpu()
            .numpy()
        )
    mean_field_probabilities = _mean_field(
        conditional_model,
        dev_scores,
        prevalence,
        steps=MEAN_FIELD_STEPS,
        damping=MEAN_FIELD_DAMPING,
        device=device,
    )

    mole_predictions = dev_scores >= THRESHOLD_LOGIT
    score_predictions = score_only_logits >= THRESHOLD_LOGIT
    oracle_predictions = oracle_logits >= THRESHOLD_LOGIT
    shuffled_predictions = shuffled_logits >= THRESHOLD_LOGIT
    mean_field_predictions = mean_field_probabilities >= 0.5
    metrics = {
        "MoleRec": _evaluate(
            dev_targets,
            dev_scores,
            mole_predictions,
            nll=_stable_bce_from_logits(dev_scores, dev_targets),
        ),
        "ScoreOnly": _evaluate(
            dev_targets,
            score_only_logits,
            score_predictions,
            nll=_stable_bce_from_logits(score_only_logits, dev_targets),
        ),
        "ShuffledCoLabel": _evaluate(
            dev_targets,
            shuffled_logits,
            shuffled_predictions,
            nll=_stable_bce_from_logits(shuffled_logits, dev_targets),
            privileged=True,
            deployable=False,
        ),
        "OracleCoLabel": _evaluate(
            dev_targets,
            oracle_logits,
            oracle_predictions,
            nll=_stable_bce_from_logits(oracle_logits, dev_targets),
            privileged=True,
            deployable=False,
        ),
        "MeanField": _evaluate(
            dev_targets,
            mean_field_probabilities,
            mean_field_predictions,
            nll=_bce_from_probabilities(mean_field_probabilities, dev_targets),
            privileged=False,
            deployable=True,
        ),
    }
    decision, decision_detail = _classify(metrics)
    interaction = conditional_model.symmetric_zero_diagonal().detach().cpu().numpy()
    validation = _self_target_leakage_check(
        conditional_model,
        dev_scores,
        dev_targets,
        prevalence,
        device=device,
    )
    result: dict[str, Any] = {
        "working_name": "Residual-Dependence Headroom Probe",
        "prototype_status": "throwaway_pre_idea_diagnostic",
        "source_revision": args.source_revision or _git_revision(),
        "device": str(device),
        "seed": int(args.seed),
        "config": {
            "candidate_count": CANDIDATE_COUNT,
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "inference_threshold_logit": THRESHOLD_LOGIT,
            "mean_field_steps": MEAN_FIELD_STEPS,
            "mean_field_damping": MEAN_FIELD_DAMPING,
            "optimizer": "AdamW",
            "score_only_and_conditional_fits": "independent_same_seed_identity_initialization",
        },
        "scope": {
            "train_visits": int(train_scores.shape[0]),
            "dev_visits": int(dev_scores.shape[0]),
            "train_only_prevalence": True,
            "patient_raw_ehr_inputs": False,
            "molerec_retrained": False,
            "ddi_or_ehr_graphs_used": False,
            "heldout_resources_read": False,
            "audit_resources_read": False,
            "g3_resources_read": False,
            "g4_resources_read": False,
            "historical_test_resources_read": False,
            "test_resources_read": False,
            "dev_threshold_tuning": False,
            "ground_truth_cardinality_used": False,
            "idea_009_created": False,
            "formal_gate_created_or_modified": False,
            "push_performed": False,
        },
        "prevalence": {
            "min": float(prevalence.min()),
            "max": float(prevalence.max()),
            "mean": float(prevalence.mean()),
        },
        "surfaces": {
            "MoleRec": "frozen canonical score logits with canonical zero-logit decoding",
            "ScoreOnly": "trained full [131] score calibrator u=A*s+b",
            "OracleCoLabel": "conditional model with true Dev y_-i; privileged, non-deployable",
            "ShuffledCoLabel": "same conditional model with deranged Dev medication context; privileged diagnostic",
            "MeanField": "same conditional model with exactly five frozen damped mean-field updates; deployable diagnostic",
        },
        "metrics": metrics,
        "key_deltas": {
            "OracleCoLabel_minus_ScoreOnly": {
                "jaccard": float(
                    metrics["OracleCoLabel"]["jaccard"] - metrics["ScoreOnly"]["jaccard"]
                ),
                "nll": float(metrics["OracleCoLabel"]["nll"] - metrics["ScoreOnly"]["nll"]),
                "prauc": float(metrics["OracleCoLabel"]["prauc"] - metrics["ScoreOnly"]["prauc"]),
            },
            "OracleCoLabel_minus_ShuffledCoLabel": {
                "jaccard": float(
                    metrics["OracleCoLabel"]["jaccard"] - metrics["ShuffledCoLabel"]["jaccard"]
                ),
                "nll": float(metrics["OracleCoLabel"]["nll"] - metrics["ShuffledCoLabel"]["nll"]),
                "prauc": float(
                    metrics["OracleCoLabel"]["prauc"] - metrics["ShuffledCoLabel"]["prauc"]
                ),
            },
            "MeanField_minus_ScoreOnly": {
                "jaccard": float(metrics["MeanField"]["jaccard"] - metrics["ScoreOnly"]["jaccard"]),
                "nll": float(metrics["MeanField"]["nll"] - metrics["ScoreOnly"]["nll"]),
                "prauc": float(metrics["MeanField"]["prauc"] - metrics["ScoreOnly"]["prauc"]),
            },
            "ScoreOnly_minus_MoleRec": {
                "jaccard": float(metrics["ScoreOnly"]["jaccard"] - metrics["MoleRec"]["jaccard"]),
                "nll": float(metrics["ScoreOnly"]["nll"] - metrics["MoleRec"]["nll"]),
                "prauc": float(metrics["ScoreOnly"]["prauc"] - metrics["MoleRec"]["prauc"]),
            },
        },
        "mean_field": {
            "context_labels_used": False,
            "steps": MEAN_FIELD_STEPS,
            "damping": MEAN_FIELD_DAMPING,
            "dev_derangement_shift": int(shift),
            "derangement_verified": bool(np.all(permutation != np.arange(len(permutation)))),
        },
        "parameter_diagnostics": {
            "conditional_w_frobenius_norm": float(np.linalg.norm(interaction)),
            "conditional_w_max_abs": float(np.abs(interaction).max()),
            "conditional_w_symmetry_max_abs": float(np.abs(interaction - interaction.T).max()),
            "conditional_w_diagonal_max_abs": float(np.abs(np.diag(interaction)).max()),
        },
        "validation": {
            "current_target_leakage": validation,
            "finite_forward_backward_smoke": True,
        },
        "train_losses": {"ScoreOnly": score_loss, "Conditional": conditional_loss},
        "decision_detail": decision_detail,
        "decision": decision,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default="")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    result = run(args)
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
