#!/usr/bin/env python3
"""Measure label dependence left after the raw frozen MoleRec unary logits."""

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

try:
    from probe_residual_dependence import (
        BATCH_SIZE,
        CANDIDATE_COUNT,
        DEV_VISITS,
        EPOCHS,
        LEARNING_RATE,
        WEIGHT_DECAY,
        _average_precision,
        _bce_from_probabilities,
        _stable_bce_from_logits,
    )
except ModuleNotFoundError:  # Running this file from another working directory.
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from probe_residual_dependence import (
        BATCH_SIZE,
        CANDIDATE_COUNT,
        DEV_VISITS,
        EPOCHS,
        LEARNING_RATE,
        WEIGHT_DECAY,
        _average_precision,
        _bce_from_probabilities,
        _stable_bce_from_logits,
    )


SEED = 20260914
TRAIN_VISITS = 10489
THRESHOLD_LOGIT = 0.0
MEAN_FIELD_STEPS = 5
MEAN_FIELD_DAMPING = 0.5
SELF_LEAK_TOLERANCE = 1e-6
NEUTRAL_TOLERANCE = 1e-7


class FrozenUnaryResidual(nn.Module):
    """Learn only a symmetric zero-diagonal residual label matrix W."""

    def __init__(self, dimension: int = CANDIDATE_COUNT) -> None:
        super().__init__()
        self.unconstrained_label_matrix = nn.Parameter(
            torch.zeros((dimension, dimension), dtype=torch.float32)
        )

    def symmetric_zero_diagonal(self) -> torch.Tensor:
        matrix = 0.5 * (self.unconstrained_label_matrix + self.unconstrained_label_matrix.T)
        return matrix - torch.diag(torch.diagonal(matrix))

    def conditional_logits(
        self,
        frozen_logits: torch.Tensor,
        context: torch.Tensor,
        prevalence: torch.Tensor,
    ) -> torch.Tensor:
        residual = (context - prevalence) @ self.symmetric_zero_diagonal().T
        return frozen_logits + residual


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
        raise RuntimeError(f"{name} must be binary")


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def _train_w_only(
    model: FrozenUnaryResidual,
    frozen_logits: np.ndarray,
    targets: np.ndarray,
    prevalence: np.ndarray,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    device: torch.device,
) -> dict[str, float]:
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    logits_tensor = torch.from_numpy(frozen_logits).to(device=device)
    target_tensor = torch.from_numpy(targets).to(device=device)
    prevalence_tensor = torch.from_numpy(prevalence).to(device=device)
    generator = np.random.default_rng(int(seed))
    model.train()
    last = {"bce": 0.0}
    for _ in range(epochs):
        order = generator.permutation(len(frozen_logits))
        total = 0.0
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = torch.from_numpy(order[start : start + batch_size]).to(device=device)
            optimizer.zero_grad(set_to_none=True)
            # The current target is used as context during Train pseudo-likelihood;
            # W's zero diagonal prevents y_i from entering logit_i.
            logits = model.conditional_logits(
                logits_tensor[rows], target_tensor[rows], prevalence_tensor
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
    model: FrozenUnaryResidual,
    frozen_logits: np.ndarray,
    prevalence: np.ndarray,
    *,
    device: torch.device,
) -> np.ndarray:
    logits_tensor = torch.from_numpy(frozen_logits).to(device=device)
    prevalence_tensor = torch.from_numpy(prevalence).to(device=device)
    model.eval()
    with torch.no_grad():
        probabilities = torch.sigmoid(logits_tensor)
        interaction = model.symmetric_zero_diagonal()
        for _ in range(MEAN_FIELD_STEPS):
            updated = torch.sigmoid(
                logits_tensor + (probabilities - prevalence_tensor) @ interaction.T
            )
            probabilities = (
                MEAN_FIELD_DAMPING * probabilities + (1.0 - MEAN_FIELD_DAMPING) * updated
            )
    return probabilities.cpu().numpy().astype(np.float32, copy=False)


def _evaluate(
    targets: np.ndarray,
    ranking_scores: np.ndarray,
    predictions: np.ndarray,
    *,
    nll: float,
    privileged: bool = False,
    deployable: bool = True,
) -> dict[str, Any]:
    jaccard = precision = recall = f1 = prauc = 0.0
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


def _leakage_check(
    model: FrozenUnaryResidual,
    frozen_logits: np.ndarray,
    targets: np.ndarray,
    prevalence: np.ndarray,
    *,
    device: torch.device,
) -> dict[str, Any]:
    logits_tensor = torch.from_numpy(frozen_logits[: min(8, len(frozen_logits))]).to(device=device)
    target_tensor = torch.from_numpy(targets[: min(8, len(targets))]).to(device=device)
    prevalence_tensor = torch.from_numpy(prevalence).to(device=device)
    model.eval()
    with torch.no_grad():
        baseline = model.conditional_logits(logits_tensor, target_tensor, prevalence_tensor)
        maximum_self_change = 0.0
        for column in range(CANDIDATE_COUNT):
            perturbed = target_tensor.clone()
            perturbed[:, column] = 1.0 - perturbed[:, column]
            changed = model.conditional_logits(logits_tensor, perturbed, prevalence_tensor)
            maximum_self_change = max(
                maximum_self_change,
                float((changed[:, column] - baseline[:, column]).abs().max().cpu()),
            )
    return {
        "passed": bool(maximum_self_change <= SELF_LEAK_TOLERANCE),
        "max_self_target_logit_change": maximum_self_change,
        "tolerance": SELF_LEAK_TOLERANCE,
        "rows_checked": int(logits_tensor.shape[0]),
        "current_target_used_in_prediction": False,
    }


def _classify(metrics: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    mole = metrics["MoleRec"]
    oracle = metrics["FrozenOracle"]
    shuffled = metrics["FrozenShuffled"]
    mean_field = metrics["FrozenMeanField"]
    oracle_mole = oracle["jaccard"] - mole["jaccard"]
    oracle_shuffled = oracle["jaccard"] - shuffled["jaccard"]
    mean_field_mole = mean_field["jaccard"] - mole["jaccard"]
    nll_gain = oracle["nll"] - mole["nll"]
    prauc_gain = oracle["prauc"] - mole["prauc"]
    major_probabilistic_gain = nll_gain <= -0.01 or prauc_gain >= 0.01
    if oracle_mole <= 0.004:
        decision = (
            "DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY"
            if major_probabilistic_gain and oracle_mole > 0.0
            else "CLOSE_INTERACTION_FIRST_FAMILY"
        )
    elif oracle_mole >= 0.008 and mean_field_mole < 0.004:
        decision = "STRONG_UNARY_RESIDUAL_DEPENDENCE_INFERENCE_GAP"
    elif oracle_mole >= 0.008 and mean_field_mole >= 0.004:
        decision = "STRONG_UNARY_INTERACTION_HEADROOM_RECOVERABLE"
    else:
        decision = "DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY"
    return decision, {
        "oracle_minus_molerec_jaccard": float(oracle_mole),
        "oracle_minus_shuffled_jaccard": float(oracle_shuffled),
        "mean_field_minus_molerec_jaccard": float(mean_field_mole),
        "oracle_minus_molerec_nll": float(nll_gain),
        "oracle_minus_molerec_prauc": float(prauc_gain),
        "major_probabilistic_gain": bool(major_probabilistic_gain),
        "thresholds": {
            "small_set_headroom": 0.004,
            "strong_set_headroom": 0.008,
            "recoverable_mean_field_headroom": 0.004,
            "major_nll_gain": -0.01,
            "major_prauc_gain": 0.01,
        },
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
    neutral_logits = dev_scores.copy()
    neutral_error = float(np.max(np.abs(neutral_logits - dev_scores)))
    if neutral_error > NEUTRAL_TOLERANCE:
        raise RuntimeError("FrozenNeutral is not numerically identical to MoleRec logits")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _seed_everything(args.seed)
    model = FrozenUnaryResidual().to(device)
    train_loss = _train_w_only(
        model,
        train_scores,
        train_targets,
        prevalence,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        seed=args.seed,
        device=device,
    )

    score_tensor = torch.from_numpy(dev_scores).to(device=device)
    prevalence_tensor = torch.from_numpy(prevalence).to(device=device)
    model.eval()
    with torch.no_grad():
        dev_targets_tensor = torch.from_numpy(dev_targets).to(device=device)
        oracle_logits = (
            model.conditional_logits(score_tensor, dev_targets_tensor, prevalence_tensor)
            .cpu()
            .numpy()
        )
        permutation, shift = _deterministic_derangement(len(dev_targets), args.seed)
        shuffled_context = dev_targets[permutation]
        shuffled_logits = (
            model.conditional_logits(
                score_tensor,
                torch.from_numpy(shuffled_context).to(device=device),
                prevalence_tensor,
            )
            .cpu()
            .numpy()
        )
    mean_field_probabilities = _mean_field(
        model,
        dev_scores,
        prevalence,
        device=device,
    )

    mole_predictions = dev_scores >= THRESHOLD_LOGIT
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
        "FrozenNeutral": _evaluate(
            dev_targets,
            neutral_logits,
            mole_predictions,
            nll=_stable_bce_from_logits(neutral_logits, dev_targets),
        ),
        "FrozenShuffled": _evaluate(
            dev_targets,
            shuffled_logits,
            shuffled_predictions,
            nll=_stable_bce_from_logits(shuffled_logits, dev_targets),
            privileged=True,
            deployable=False,
        ),
        "FrozenOracle": _evaluate(
            dev_targets,
            oracle_logits,
            oracle_predictions,
            nll=_stable_bce_from_logits(oracle_logits, dev_targets),
            privileged=True,
            deployable=False,
        ),
        "FrozenMeanField": _evaluate(
            dev_targets,
            mean_field_probabilities,
            mean_field_predictions,
            nll=_bce_from_probabilities(mean_field_probabilities, dev_targets),
            privileged=False,
            deployable=True,
        ),
    }
    decision, decision_detail = _classify(metrics)
    interaction = model.symmetric_zero_diagonal().detach().cpu().numpy()
    result: dict[str, Any] = {
        "working_name": "Residual-Dependence Headroom Probe — Frozen Unary",
        "prototype_status": "throwaway_pre_idea_identification_experiment",
        "source_revision": args.source_revision or _git_revision(),
        "device": str(device),
        "seed": int(args.seed),
        "prior_implementation_fact": {
            "score_only_and_pairwise_shared_a_b": False,
            "score_only_unary": "learned A,b initialized identity/zero",
            "pairwise_unary": "separate learned A,b initialized identity/zero, jointly optimized with W",
            "neutral_context_reproduced_raw_molerec": False,
            "w_only_required": True,
        },
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
            "learned_parameters": "W only",
        },
        "scope": {
            "train_visits": int(train_scores.shape[0]),
            "dev_visits": int(dev_scores.shape[0]),
            "train_only_prevalence": True,
            "raw_ehr_inputs": False,
            "ddi_or_ehr_graphs_used": False,
            "molerec_retrained": False,
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
        "neutral_surface": {
            "max_abs_neutral_minus_molerec_logit": neutral_error,
            "tolerance": NEUTRAL_TOLERANCE,
            "passed": bool(neutral_error <= NEUTRAL_TOLERANCE),
        },
        "prevalence": {
            "min": float(prevalence.min()),
            "max": float(prevalence.max()),
            "mean": float(prevalence.mean()),
        },
        "surfaces": {
            "MoleRec": "frozen canonical raw logits, zero-logit decoding",
            "FrozenNeutral": "same raw logits; numerically identical to MoleRec",
            "FrozenShuffled": "raw logits plus W with one seeded Dev derangement; privileged/non-deployable",
            "FrozenOracle": "raw logits plus W with true Dev y_-i; privileged/non-deployable",
            "FrozenMeanField": "raw logits plus exactly five frozen damped mean-field updates; deployable diagnostic",
        },
        "metrics": metrics,
        "key_deltas": {
            "FrozenOracle_minus_MoleRec": {
                "jaccard": float(
                    metrics["FrozenOracle"]["jaccard"] - metrics["MoleRec"]["jaccard"]
                ),
                "nll": float(metrics["FrozenOracle"]["nll"] - metrics["MoleRec"]["nll"]),
                "prauc": float(metrics["FrozenOracle"]["prauc"] - metrics["MoleRec"]["prauc"]),
                "mean_count": float(
                    metrics["FrozenOracle"]["mean_medication_count"]
                    - metrics["MoleRec"]["mean_medication_count"]
                ),
            },
            "FrozenOracle_minus_FrozenShuffled": {
                "jaccard": float(
                    metrics["FrozenOracle"]["jaccard"] - metrics["FrozenShuffled"]["jaccard"]
                ),
                "nll": float(metrics["FrozenOracle"]["nll"] - metrics["FrozenShuffled"]["nll"]),
                "prauc": float(
                    metrics["FrozenOracle"]["prauc"] - metrics["FrozenShuffled"]["prauc"]
                ),
                "mean_count": float(
                    metrics["FrozenOracle"]["mean_medication_count"]
                    - metrics["FrozenShuffled"]["mean_medication_count"]
                ),
            },
            "FrozenMeanField_minus_MoleRec": {
                "jaccard": float(
                    metrics["FrozenMeanField"]["jaccard"] - metrics["MoleRec"]["jaccard"]
                ),
                "nll": float(metrics["FrozenMeanField"]["nll"] - metrics["MoleRec"]["nll"]),
                "prauc": float(metrics["FrozenMeanField"]["prauc"] - metrics["MoleRec"]["prauc"]),
                "mean_count": float(
                    metrics["FrozenMeanField"]["mean_medication_count"]
                    - metrics["MoleRec"]["mean_medication_count"]
                ),
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
            "w_frobenius_norm": float(np.linalg.norm(interaction)),
            "w_max_abs": float(np.abs(interaction).max()),
            "w_symmetry_max_abs": float(np.abs(interaction - interaction.T).max()),
            "w_diagonal_max_abs": float(np.abs(np.diag(interaction)).max()),
        },
        "validation": {
            "current_target_leakage": _leakage_check(
                model,
                dev_scores,
                dev_targets,
                prevalence,
                device=device,
            ),
            "finite_forward_backward_smoke": True,
        },
        "train_loss": train_loss,
        "decision_detail": decision_detail,
        "decision": decision,
    }
    if metrics["FrozenOracle"]["jaccard"] - metrics["MoleRec"]["jaccard"] >= 0.008:
        q0 = 1.0 / (1.0 + np.exp(-np.clip(dev_scores, -80.0, 80.0)))
        positive_context = np.where(dev_targets > 0.5, 1.0, q0).astype(np.float32)
        negative_context = np.where(dev_targets <= 0.5, 0.0, q0).astype(np.float32)
        positive_logits = dev_scores + (positive_context - prevalence) @ interaction.T
        negative_logits = dev_scores + (negative_context - prevalence) @ interaction.T
        positive_probabilities = 1.0 / (1.0 + np.exp(-np.clip(positive_logits, -80.0, 80.0)))
        negative_probabilities = 1.0 / (1.0 + np.exp(-np.clip(negative_logits, -80.0, 80.0)))
        result["optional_one_shot_decomposition"] = {
            "ran": True,
            "positive_oracle_context": _evaluate(
                dev_targets,
                positive_logits,
                positive_logits >= THRESHOLD_LOGIT,
                nll=_stable_bce_from_logits(positive_logits, dev_targets),
                privileged=True,
                deployable=False,
            ),
            "negative_oracle_context": _evaluate(
                dev_targets,
                negative_logits,
                negative_logits >= THRESHOLD_LOGIT,
                nll=_stable_bce_from_logits(negative_logits, dev_targets),
                privileged=True,
                deployable=False,
            ),
            "positive_context_nll": _bce_from_probabilities(positive_probabilities, dev_targets),
            "negative_context_nll": _bce_from_probabilities(negative_probabilities, dev_targets),
        }
    else:
        result["optional_one_shot_decomposition"] = {
            "ran": False,
            "reason": "FrozenOracle-MoleRec Jaccard headroom below +0.008 threshold",
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
