#!/usr/bin/env python3
"""Run the one-seed NeedCover Train/Gate01-Dev architecture screen on 319."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch
from needcover import (
    CANDIDATE_COUNT,
    DEFAULT_DIAGNOSIS_HASH_WIDTH,
    DEFAULT_HIDDEN_DIM,
    DEFAULT_HISTORY_LENGTH,
    DEFAULT_PROCEDURE_HASH_WIDTH,
    DEFAULT_PROVISIONAL_WEIGHT,
    DEFAULT_THRESHOLD,
    VARIANTS,
    NeedCoverModel,
    PackedVisits,
    build_relation_features,
    build_visit_examples,
    coverage_residual_diagnostics,
    evaluate_surface,
    history_feature_dimension,
    needcover_loss,
    pack_visit_examples,
    target_sets_from_matrix,
    threshold_sets,
)

DEFAULT_SEED = 20260914
DEFAULT_EPOCHS = 8
DEFAULT_BATCH_SIZE = 64
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_WEIGHT_DECAY = 1e-4
GATE01_SPLIT_NAMESPACE = "idea008-gate01-v1"


def gate01_dev(patient_id: int) -> bool:
    """Return the existing Gate 01 Dev half split for a patient id."""

    value = int.from_bytes(
        hashlib.sha256(f"{GATE01_SPLIT_NAMESPACE}:{int(patient_id)}".encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _load_array(root: Path, name: str) -> np.ndarray:
    value = np.load(root / name, mmap_mode="r")
    return np.asarray(value, dtype=np.float32)


def _assert_alignment(examples: tuple[Any, ...], targets: np.ndarray, name: str) -> None:
    if len(examples) != targets.shape[0]:
        raise RuntimeError(f"{name} examples are not aligned with the canonical target array")
    for row, example in enumerate(examples):
        expected = set(int(value) for value in example.target_medications)
        observed = set(int(index) for index in np.flatnonzero(targets[row] > 0.5))
        if expected != observed:
            raise RuntimeError(f"{name} target mismatch at visit row {row}")


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def _batch_tensors(
    packed: PackedVisits,
    rows: np.ndarray,
    device: torch.device,
) -> dict[str, torch.Tensor]:
    return {
        "diagnosis_codes": torch.from_numpy(packed.diagnosis_codes[rows]).to(device=device),
        "diagnosis_mask": torch.from_numpy(packed.diagnosis_mask[rows]).to(device=device),
        "procedure_codes": torch.from_numpy(packed.procedure_codes[rows]).to(device=device),
        "procedure_mask": torch.from_numpy(packed.procedure_mask[rows]).to(device=device),
        "history_features": torch.from_numpy(packed.history_features[rows]).to(device=device),
        "history_mask": torch.from_numpy(packed.history_mask[rows]).to(device=device),
    }


def _train(
    model: NeedCoverModel,
    packed: PackedVisits,
    targets: np.ndarray,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    learning_rate: float,
    weight_decay: float,
    provisional_weight: float,
    device: torch.device,
) -> dict[str, float]:
    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch_size must be positive")
    if targets.ndim != 2 or targets.shape[0] != len(packed.diagnosis_codes):
        raise ValueError("targets are not aligned with packed visits")
    generator = np.random.default_rng(int(seed))
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    model.train()
    last: dict[str, float] = {}
    for _ in range(epochs):
        order = generator.permutation(len(targets))
        totals = {"final_bce": 0.0, "provisional_bce": 0.0, "total": 0.0}
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            batch = _batch_tensors(packed, rows, device)
            target = torch.from_numpy(targets[rows]).to(device=device)
            optimizer.zero_grad(set_to_none=True)
            output = model(**batch)
            loss, detail = needcover_loss(
                output,
                target,
                provisional_weight=provisional_weight,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            for key in totals:
                totals[key] += detail[key]
            batches += 1
        last = {key: value / batches for key, value in totals.items()}
    return last


def _predict(
    model: NeedCoverModel,
    packed: PackedVisits,
    *,
    batch_size: int,
    device: torch.device,
) -> dict[str, np.ndarray]:
    model.eval()
    final_logits: list[np.ndarray] = []
    provisional_logits: list[np.ndarray] = []
    coverage: list[np.ndarray] = []
    residual: list[np.ndarray] = []
    problem_mask: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(packed.diagnosis_codes), batch_size):
            rows = np.arange(start, min(start + batch_size, len(packed.diagnosis_codes)))
            output = model(**_batch_tensors(packed, rows, device))
            final_logits.append(output.final_logits.cpu().numpy())
            provisional_logits.append(output.provisional_logits.cpu().numpy())
            coverage.append(output.coverage.cpu().numpy())
            residual.append(output.residual.cpu().numpy())
            problem_mask.append(output.problem_mask.cpu().numpy())
    return {
        "final_logits": np.concatenate(final_logits, axis=0),
        "provisional_logits": np.concatenate(provisional_logits, axis=0),
        "coverage": np.concatenate(coverage, axis=0),
        "residual": np.concatenate(residual, axis=0),
        "problem_mask": np.concatenate(problem_mask, axis=0),
    }


def _per_visit_jaccard(targets: np.ndarray, predictions: tuple[frozenset[int], ...]) -> np.ndarray:
    values = np.zeros(len(predictions), dtype=np.float32)
    for row, (target, prediction) in enumerate(
        zip(target_sets_from_matrix(targets), predictions),  # noqa: B905
    ):
        union = target | set(prediction)
        values[row] = 1.0 if not union else len(target & set(prediction)) / len(union)
    return values


def _single_diagnostic(
    targets: np.ndarray,
    static_predictions: tuple[frozenset[int], ...],
    needcover_predictions: tuple[frozenset[int], ...],
    diagnosis_counts: np.ndarray,
    static_diagnostics: dict[str, float],
    needcover_diagnostics: dict[str, float],
) -> dict[str, Any]:
    """Run the one permitted small-delta diagnostic, without retuning."""

    static_jaccard = _per_visit_jaccard(targets, static_predictions)
    needcover_jaccard = _per_visit_jaccard(targets, needcover_predictions)
    delta = needcover_jaccard - static_jaccard
    strata: dict[str, dict[str, float]] = {}
    bins = (
        ("1", diagnosis_counts == 1),
        ("2", diagnosis_counts == 2),
        ("3-4", (diagnosis_counts >= 3) & (diagnosis_counts <= 4)),
        ("5+", diagnosis_counts >= 5),
    )
    for name, mask in bins:
        if not bool(mask.any()):
            continue
        strata[name] = {
            "visit_count": float(mask.sum()),
            "jaccard_delta": float(delta[mask].mean()),
        }
    multimorbidity = diagnosis_counts >= 2
    if bool(multimorbidity.any()):
        strata["multimorbidity_2+"] = {
            "visit_count": float(multimorbidity.sum()),
            "jaccard_delta": float(delta[multimorbidity].mean()),
        }
    single = diagnosis_counts == 1
    if bool(single.any()):
        strata["single_diagnosis"] = {
            "visit_count": float(single.sum()),
            "jaccard_delta": float(delta[single].mean()),
        }
    return {
        "reason": "NeedCover-StaticTwoPass Jaccard delta is in (+0.002, +0.004]; no tuning",
        "strata": strata,
        "coverage_collapse": {
            "NeedCover": {
                "near_boundary_fraction": needcover_diagnostics["coverage_near_boundary_fraction"],
                "coverage_std": needcover_diagnostics["coverage_std"],
                "residual_std": needcover_diagnostics["residual_std"],
            },
            "StaticTwoPass": {
                "near_boundary_fraction": static_diagnostics["coverage_near_boundary_fraction"],
                "coverage_std": static_diagnostics["coverage_std"],
                "residual_std": static_diagnostics["residual_std"],
            },
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


def _survival_check(global_metrics: dict[str, float], need_metrics: dict[str, float]) -> bool:
    jaccard_gain = need_metrics["jaccard"] - global_metrics["jaccard"]
    ddi_gain = need_metrics["ddi_rate"] - global_metrics["ddi_rate"]
    primary = jaccard_gain >= 0.008
    pareto = jaccard_gain >= 0.004 and ddi_gain <= -0.010
    if not (primary or pareto):
        return False
    count_inflation = need_metrics["mean_medication_count"] > (
        global_metrics["mean_medication_count"]
        + max(1.0, 0.10 * global_metrics["mean_medication_count"])
    )
    corroborated = (
        need_metrics["precision"] >= global_metrics["precision"]
        and need_metrics["f1"] >= global_metrics["f1"]
        and need_metrics["prauc"] >= global_metrics["prauc"]
    )
    return not (count_inflation and not corroborated)


def run(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    ehr = np.asarray(dill.load((snapshot / "ehr_adj_final.pkl").open("rb")), dtype=np.float32)
    relation_features, edge_mask = build_relation_features(ehr, ddi)

    split_point = int(len(records) * 2 / 3)
    train_patient_indices = tuple(range(split_point))
    dev_patient_indices = tuple(
        patient_id for patient_id in range(split_point, len(records)) if gate01_dev(patient_id)
    )
    train_examples = build_visit_examples(
        records, train_patient_indices, history_length=args.history_length
    )
    dev_examples = build_visit_examples(
        records, dev_patient_indices, history_length=args.history_length
    )
    train_scores = _load_array(train_dev_root, "train_scores.npy")
    train_targets = _load_array(train_dev_root, "train_targets.npy")
    dev_scores = _load_array(train_dev_root, "dev_scores.npy")
    dev_targets = _load_array(train_dev_root, "dev_targets.npy")
    for name, value in (
        ("train_scores", train_scores),
        ("train_targets", train_targets),
        ("dev_scores", dev_scores),
        ("dev_targets", dev_targets),
    ):
        if value.ndim != 2 or value.shape[1] != CANDIDATE_COUNT:
            raise RuntimeError(f"{name} does not have the frozen [visits, 131] shape")
    _assert_alignment(train_examples, train_targets, "Train")
    _assert_alignment(dev_examples, dev_targets, "Gate01-Dev")
    if len(train_examples) != train_scores.shape[0] or len(dev_examples) != dev_scores.shape[0]:
        raise RuntimeError("record-derived examples are not aligned with canonical MoleRec scores")

    all_examples = (*train_examples, *dev_examples)
    max_diagnoses = max(len(item.diagnosis_codes) for item in all_examples)
    max_procedures = max(len(item.procedure_codes) for item in all_examples)
    train_inputs = pack_visit_examples(
        train_examples,
        max_diagnoses=max_diagnoses,
        max_procedures=max_procedures,
        diagnosis_hash_width=args.diagnosis_hash_width,
        procedure_hash_width=args.procedure_hash_width,
        history_length=args.history_length,
    )
    dev_inputs = pack_visit_examples(
        dev_examples,
        max_diagnoses=max_diagnoses,
        max_procedures=max_procedures,
        diagnosis_hash_width=args.diagnosis_hash_width,
        procedure_hash_width=args.procedure_hash_width,
        history_length=args.history_length,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    global_predictions = threshold_sets(dev_scores, threshold=args.threshold)
    global_metrics = evaluate_surface(
        target_sets_from_matrix(dev_targets), global_predictions, dev_scores, ddi
    )

    variant_metrics: dict[str, dict[str, float]] = {}
    variant_diagnostics: dict[str, dict[str, float]] = {}
    variant_counts: dict[str, dict[str, float]] = {
        "GlobalStrong": {
            "mean": global_metrics["mean_medication_count"],
            "std": global_metrics["std_medication_count"],
        }
    }
    variant_predictions: dict[str, tuple[frozenset[int], ...]] = {}
    train_losses: dict[str, dict[str, float]] = {}
    for variant in VARIANTS:
        _seed_everything(args.seed)
        model = NeedCoverModel(
            diagnosis_hash_width=args.diagnosis_hash_width,
            procedure_hash_width=args.procedure_hash_width,
            history_feature_dim=history_feature_dimension(
                args.diagnosis_hash_width, args.procedure_hash_width
            ),
            hidden_dim=args.hidden_dim,
            relation_features=relation_features,
            edge_mask=edge_mask,
            variant=variant,
        ).to(device)
        train_losses[variant] = _train(
            model,
            train_inputs,
            train_targets,
            epochs=args.epochs,
            batch_size=args.batch_size,
            seed=args.seed,
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            provisional_weight=args.provisional_weight,
            device=device,
        )
        prediction = _predict(model, dev_inputs, batch_size=args.batch_size, device=device)
        predictions = threshold_sets(prediction["final_logits"], threshold=args.threshold)
        variant_predictions[variant] = predictions
        name = {
            "problem_drug": "ProblemDrug",
            "static_two_pass": "StaticTwoPass",
            "needcover": "NeedCover",
        }[variant]
        variant_metrics[name] = evaluate_surface(
            target_sets_from_matrix(dev_targets), predictions, prediction["final_logits"], ddi
        )
        variant_diagnostics[name] = coverage_residual_diagnostics(
            prediction["coverage"], prediction["residual"], prediction["problem_mask"]
        )
        variant_counts[name] = {
            "mean": variant_metrics[name]["mean_medication_count"],
            "std": variant_metrics[name]["std_medication_count"],
        }

    static_metrics = variant_metrics["StaticTwoPass"]
    need_metrics = variant_metrics["NeedCover"]
    delta = need_metrics["jaccard"] - static_metrics["jaccard"]
    diagnostic: dict[str, Any] | None = None
    if 0.002 < delta <= 0.004:
        diagnostic = _single_diagnostic(
            dev_targets,
            variant_predictions["static_two_pass"],
            variant_predictions["needcover"],
            dev_inputs.diagnosis_counts,
            variant_diagnostics["StaticTwoPass"],
            variant_diagnostics["NeedCover"],
        )
    if delta <= 0.002 or not _survival_check(global_metrics, need_metrics):
        decision = "KILL_NEEDCOVER_MECHANISM"
    else:
        decision = "SURVIVE_NEEDCOVER_FOR_STRICT_REVIEW"
    return {
        "working_name": "NeedCover",
        "prototype_status": "throwaway_pre_idea",
        "source_revision": args.source_revision or _git_revision(),
        "device": str(device),
        "seed": int(args.seed),
        "config": {
            "diagnosis_hash_width": int(args.diagnosis_hash_width),
            "procedure_hash_width": int(args.procedure_hash_width),
            "history_length": int(args.history_length),
            "hidden_dim": int(args.hidden_dim),
            "epochs": int(args.epochs),
            "batch_size": int(args.batch_size),
            "learning_rate": float(args.learning_rate),
            "weight_decay": float(args.weight_decay),
            "provisional_loss_weight": float(args.provisional_weight),
            "inference_threshold_logit": float(args.threshold),
            "candidate_count": CANDIDATE_COUNT,
            "train_only_diagnosis_medication_prior": "not_used",
        },
        "split": {
            "train_patients": len(train_patient_indices),
            "train_visits": len(train_examples),
            "dev_patients": len(dev_patient_indices),
            "dev_visits": len(dev_examples),
            "heldout_resources_read": False,
            "test_resources_read": False,
            "audit_resources_read": False,
            "g3_resources_read": False,
            "g4_resources_read": False,
        },
        "inputs": {
            "current": ["diagnosis_code_set", "procedure_code_set"],
            "history": "prior diagnosis/procedure/medication events only",
            "medication_vocabulary": 131,
            "relation_priors": ["Train-derived EHR co-prescription", "DDI"],
            "hypeMed_required": False,
            "dev_medication_labels_as_inputs": False,
            "ground_truth_cardinality_at_inference": False,
        },
        "architecture": {
            "GlobalStrong": "frozen MoleRec threshold surface",
            "ProblemDrug": "explicit diagnosis nodes + affinities + medication states; no interaction or residual pass",
            "StaticTwoPass": "ProblemDrug front-end + one relation-aware medication layer + static second message",
            "NeedCover": "StaticTwoPass with c_k=sum_i alpha_ki*p_i0 and r_k=1-c_k residual weighting",
            "reasoning_stages": 2,
            "latent_intent_slots": False,
            "problem_activity_gate": False,
            "iterative_refinement": False,
        },
        "metrics": {"GlobalStrong": global_metrics, **variant_metrics},
        "coverage_residual_diagnostics": variant_diagnostics,
        "medication_count_diagnostics": variant_counts,
        "needcover_minus_static_two_pass_jaccard": float(delta),
        "small_delta_diagnostic": diagnostic,
        "last_train_losses": train_losses,
        "decision": decision,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default="")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--diagnosis-hash-width", type=int, default=DEFAULT_DIAGNOSIS_HASH_WIDTH)
    parser.add_argument("--procedure-hash-width", type=int, default=DEFAULT_PROCEDURE_HASH_WIDTH)
    parser.add_argument("--history-length", type=int, default=DEFAULT_HISTORY_LENGTH)
    parser.add_argument("--hidden-dim", type=int, default=DEFAULT_HIDDEN_DIM)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--weight-decay", type=float, default=DEFAULT_WEIGHT_DECAY)
    parser.add_argument("--provisional-weight", type=float, default=DEFAULT_PROVISIONAL_WEIGHT)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()
    result = run(args)
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
