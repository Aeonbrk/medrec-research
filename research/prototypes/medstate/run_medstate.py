#!/usr/bin/env python3
"""Run the one-seed MedState Train/Gate01-Dev architecture screen on 319."""

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
from medstate import (
    CANDIDATE_COUNT,
    DEFAULT_DIAGNOSIS_HASH_WIDTH,
    DEFAULT_HISTORY_FEATURES,
    DEFAULT_NEAR_ZERO_CHANGE,
    DEFAULT_PROCEDURE_HASH_WIDTH,
    DEFAULT_STATE_DIM,
    DEFAULT_THRESHOLD,
    VARIANTS,
    MedStateModel,
    PackedSequences,
    build_patient_sequences,
    build_relation_features,
    evaluate_surface,
    pack_patient_sequences,
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


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def _batch_tensors(
    packed: PackedSequences,
    rows: np.ndarray,
    device: torch.device,
) -> dict[str, torch.Tensor]:
    return {
        "diagnosis_codes": torch.from_numpy(packed.diagnosis_codes[rows]).to(device=device),
        "diagnosis_mask": torch.from_numpy(packed.diagnosis_mask[rows]).to(device=device),
        "procedure_codes": torch.from_numpy(packed.procedure_codes[rows]).to(device=device),
        "procedure_mask": torch.from_numpy(packed.procedure_mask[rows]).to(device=device),
        "history_features": torch.from_numpy(packed.history_features[rows]).to(device=device),
        "visit_mask": torch.from_numpy(packed.visit_mask[rows]).to(device=device),
    }


def _assert_alignment(packed: PackedSequences, targets: np.ndarray, name: str) -> None:
    observed = packed.targets[packed.visit_mask]
    if observed.shape != targets.shape or not np.array_equal(observed, targets):
        raise RuntimeError(f"{name} sequence targets are not aligned with canonical target array")


def _train_variant(
    model: MedStateModel,
    packed: PackedSequences,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    learning_rate: float,
    weight_decay: float,
    device: torch.device,
) -> dict[str, float]:
    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch_size must be positive")
    generator = np.random.default_rng(int(seed))
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    model.train()
    last = {"bce": 0.0}
    for _ in range(epochs):
        order = generator.permutation(len(packed.patient_ids))
        total = 0.0
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            batch = _batch_tensors(packed, rows, device)
            targets = torch.from_numpy(packed.targets[rows]).to(device=device)
            optimizer.zero_grad(set_to_none=True)
            output = model(**batch, observed_targets=targets, collect_states=False)
            if output.loss is None:
                raise RuntimeError("MedState training did not produce a loss")
            output.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            total += float(output.loss.detach().cpu())
            batches += 1
        last = {"bce": total / max(1, batches)}
    return last


def _predict_variant(
    model: MedStateModel,
    packed: PackedSequences,
    *,
    batch_size: int,
    device: torch.device,
) -> dict[str, np.ndarray]:
    model.eval()
    outputs: dict[str, list[np.ndarray]] = {
        "logits": [],
        "state_prev": [],
        "state_pre": [],
    }
    with torch.no_grad():
        for start in range(0, len(packed.patient_ids), batch_size):
            rows = np.arange(start, min(start + batch_size, len(packed.patient_ids)))
            batch = _batch_tensors(packed, rows, device)
            targets = torch.from_numpy(packed.targets[rows]).to(device=device)
            output = model(
                **batch,
                observed_targets=targets,
                collect_states=True,
            )
            if output.state_prev is None or output.state_pre is None:
                raise RuntimeError("MedState prediction did not collect state diagnostics")
            outputs["logits"].append(output.logits.cpu().numpy())
            outputs["state_prev"].append(output.state_prev.cpu().numpy())
            outputs["state_pre"].append(output.state_pre.cpu().numpy())
    return {key: np.concatenate(value, axis=0) for key, value in outputs.items()}


def _flatten_prediction(prediction: dict[str, np.ndarray], packed: PackedSequences) -> np.ndarray:
    return prediction["logits"][packed.visit_mask]


def _per_visit_jaccard(
    targets: np.ndarray,
    predictions: tuple[frozenset[int], ...],
) -> np.ndarray:
    values = np.zeros(len(predictions), dtype=np.float32)
    for row, (target, prediction) in enumerate(
        zip(target_sets_from_matrix(targets), predictions),  # noqa: B905
    ):
        prediction_set = set(prediction)
        union = target | prediction_set
        values[row] = 1.0 if not union else len(target & prediction_set) / len(union)
    return values


def _state_dynamics(
    prediction: dict[str, np.ndarray],
    packed: PackedSequences,
    *,
    near_zero_threshold: float = DEFAULT_NEAR_ZERO_CHANGE,
) -> dict[str, float]:
    state_prev = prediction["state_prev"]
    state_pre = prediction["state_pre"]
    visit_mask = packed.visit_mask
    changes = np.linalg.norm(state_pre - state_prev, axis=-1)
    active_changes = changes[visit_mask]
    prior_active = packed.prior_active[visit_mask]
    if active_changes.size == 0:
        raise RuntimeError("state diagnostics require at least one visit")

    previous = state_prev[:, :-1]
    following = state_prev[:, 1:]
    pair_mask = visit_mask[:, :-1] & visit_mask[:, 1:]
    numerator = (previous * following).sum(axis=-1)
    denominator = np.linalg.norm(previous, axis=-1) * np.linalg.norm(following, axis=-1)
    cosine = numerator / np.maximum(denominator, 1e-8)
    cosine_values = cosine[pair_mask]

    active_mask = prior_active
    never_mask = ~prior_active
    return {
        "state_change_mean": float(active_changes.mean()),
        "state_change_std": float(active_changes.std()),
        "state_cosine_consecutive_mean": (
            float(cosine_values.mean()) if cosine_values.size else 0.0
        ),
        "state_cosine_consecutive_std": (float(cosine_values.std()) if cosine_values.size else 0.0),
        "state_change_active_mean": float(active_changes[active_mask].mean())
        if bool(active_mask.any())
        else 0.0,
        "state_change_never_prescribed_mean": float(active_changes[never_mask].mean())
        if bool(never_mask.any())
        else 0.0,
        "state_change_near_zero_fraction": float(
            (active_changes <= float(near_zero_threshold)).mean()
        ),
        "state_transition_count": float(cosine_values.size),
    }


def _history_delta_diagnostic(
    targets: np.ndarray,
    stateless_predictions: tuple[frozenset[int], ...],
    persistent_predictions: tuple[frozenset[int], ...],
    history_lengths: np.ndarray,
) -> dict[str, Any]:
    """One bounded stratification for a weak positive mechanism delta."""

    stateless = _per_visit_jaccard(targets, stateless_predictions)
    persistent = _per_visit_jaccard(targets, persistent_predictions)
    delta = persistent - stateless
    strata: dict[str, dict[str, float]] = {}
    bins = (
        ("0", history_lengths == 0),
        ("1", history_lengths == 1),
        ("2+", history_lengths >= 2),
    )
    for name, mask in bins:
        if bool(mask.any()):
            strata[name] = {
                "visit_count": float(mask.sum()),
                "jaccard_delta": float(delta[mask].mean()),
            }
    return {
        "reason": "persistent-stateless Jaccard delta is in (+0.002, +0.004]; no tuning",
        "strata": strata,
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


def _decision(
    global_metrics: dict[str, float],
    stateless_metrics: dict[str, float],
    persistent_independent: dict[str, float],
    persistent_relational: dict[str, float],
) -> tuple[str, str, float, float]:
    persistent_by_name = {
        "PersistentIndependent": persistent_independent,
        "PersistentRelational": persistent_relational,
    }
    best_name = max(persistent_by_name, key=lambda name: persistent_by_name[name]["jaccard"])
    best = persistent_by_name[best_name]
    mechanism_delta = best["jaccard"] - stateless_metrics["jaccard"]
    global_delta = best["jaccard"] - global_metrics["jaccard"]
    if mechanism_delta <= 0.002:
        return "KILL_PERSISTENT_MED_STATE", best_name, mechanism_delta, global_delta
    if mechanism_delta < 0.004:
        return "KILL_PERSISTENT_MED_STATE", best_name, mechanism_delta, global_delta
    safety_pareto = global_delta >= 0.004 and best["ddi_rate"] <= global_metrics["ddi_rate"] - 0.010
    if global_delta >= 0.008 or safety_pareto:
        return (
            "SURVIVE_PERSISTENT_MED_STATE_FOR_STRICT_REVIEW",
            best_name,
            mechanism_delta,
            global_delta,
        )
    return "KILL_AS_PAPER_ARCHITECTURE", best_name, mechanism_delta, global_delta


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
    train_sequences = build_patient_sequences(records, train_patient_indices)
    dev_sequences = build_patient_sequences(records, dev_patient_indices)
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

    all_sequences = (*train_sequences, *dev_sequences)
    max_diagnoses = max(
        (len(row) for sequence in all_sequences for row in sequence.diagnosis_codes),
        default=1,
    )
    max_procedures = max(
        (len(row) for sequence in all_sequences for row in sequence.procedure_codes),
        default=1,
    )
    train_inputs = pack_patient_sequences(
        train_sequences,
        max_diagnoses=max_diagnoses,
        max_procedures=max_procedures,
        diagnosis_hash_width=args.diagnosis_hash_width,
        procedure_hash_width=args.procedure_hash_width,
    )
    dev_inputs = pack_patient_sequences(
        dev_sequences,
        max_diagnoses=max_diagnoses,
        max_procedures=max_procedures,
        diagnosis_hash_width=args.diagnosis_hash_width,
        procedure_hash_width=args.procedure_hash_width,
    )
    _assert_alignment(train_inputs, train_targets, "Train")
    _assert_alignment(dev_inputs, dev_targets, "Gate01-Dev")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    global_metrics = evaluate_surface(
        target_sets_from_matrix(dev_targets),
        threshold_sets(dev_scores, threshold=args.threshold),
        dev_scores,
        ddi,
    )

    names = {
        "stateless_relational": "StatelessRelational",
        "persistent_independent": "PersistentIndependent",
        "persistent_relational": "PersistentRelational",
    }
    variant_metrics: dict[str, dict[str, float]] = {}
    variant_dynamics: dict[str, dict[str, float]] = {}
    variant_counts: dict[str, dict[str, float]] = {
        "GlobalStrong": {
            "mean": global_metrics["mean_medication_count"],
            "std": global_metrics["std_medication_count"],
        }
    }
    predictions: dict[str, tuple[frozenset[int], ...]] = {}
    train_losses: dict[str, dict[str, float]] = {}
    for variant in VARIANTS:
        _seed_everything(args.seed)
        model = MedStateModel(
            diagnosis_hash_width=args.diagnosis_hash_width,
            procedure_hash_width=args.procedure_hash_width,
            state_dim=args.state_dim,
            relation_features=relation_features,
            edge_mask=edge_mask,
            variant=variant,
            history_feature_count=DEFAULT_HISTORY_FEATURES,
            detach_every_visit=True,
        ).to(device)
        train_losses[names[variant]] = _train_variant(
            model,
            train_inputs,
            epochs=args.epochs,
            batch_size=args.batch_size,
            seed=args.seed,
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            device=device,
        )
        prediction = _predict_variant(model, dev_inputs, batch_size=args.batch_size, device=device)
        flat_logits = _flatten_prediction(prediction, dev_inputs)
        decoded = threshold_sets(flat_logits, threshold=args.threshold)
        predictions[variant] = decoded
        name = names[variant]
        variant_metrics[name] = evaluate_surface(
            target_sets_from_matrix(dev_targets), decoded, flat_logits, ddi
        )
        variant_dynamics[name] = _state_dynamics(prediction, dev_inputs)
        variant_counts[name] = {
            "mean": variant_metrics[name]["mean_medication_count"],
            "std": variant_metrics[name]["std_medication_count"],
        }

    stateless_metrics = variant_metrics["StatelessRelational"]
    persistent_independent = variant_metrics["PersistentIndependent"]
    persistent_relational = variant_metrics["PersistentRelational"]
    decision, best_name, mechanism_delta, global_delta = _decision(
        global_metrics,
        stateless_metrics,
        persistent_independent,
        persistent_relational,
    )
    dev_history_lengths = dev_inputs.history_lengths[dev_inputs.visit_mask]
    small_delta_diagnostic = None
    if 0.002 < mechanism_delta <= 0.004:
        small_delta_diagnostic = _history_delta_diagnostic(
            dev_targets,
            predictions["stateless_relational"],
            predictions["persistent_independent"]
            if persistent_independent["jaccard"] >= persistent_relational["jaccard"]
            else predictions["persistent_relational"],
            dev_history_lengths,
        )

    metric_deltas: dict[str, dict[str, float]] = {}
    for name, metrics in variant_metrics.items():
        metric_deltas[name] = {
            "jaccard_vs_GlobalStrong": metrics["jaccard"] - global_metrics["jaccard"],
            "ddi_vs_GlobalStrong": metrics["ddi_rate"] - global_metrics["ddi_rate"],
            "mean_count_vs_GlobalStrong": (
                metrics["mean_medication_count"] - global_metrics["mean_medication_count"]
            ),
            "jaccard_vs_StatelessRelational": (metrics["jaccard"] - stateless_metrics["jaccard"]),
            "ddi_vs_StatelessRelational": metrics["ddi_rate"] - stateless_metrics["ddi_rate"],
        }

    persistent_relational_jaccard = _per_visit_jaccard(
        dev_targets, predictions["persistent_relational"]
    )
    stateless_jaccard = _per_visit_jaccard(dev_targets, predictions["stateless_relational"])
    per_visit_delta = persistent_relational_jaccard - stateless_jaccard
    bounded_delta = {
        "mean": float(per_visit_delta.mean()),
        "std": float(per_visit_delta.std()),
        "positive_fraction": float((per_visit_delta > 0.0).mean()),
        "visit_count": float(per_visit_delta.size),
    }
    return {
        "working_name": "MedState Dynamics",
        "prototype_status": "throwaway_pre_idea",
        "source_revision": args.source_revision or _git_revision(),
        "device": str(device),
        "seed": int(args.seed),
        "config": {
            "diagnosis_hash_width": int(args.diagnosis_hash_width),
            "procedure_hash_width": int(args.procedure_hash_width),
            "state_dim": int(args.state_dim),
            "history_feature_count": DEFAULT_HISTORY_FEATURES,
            "epochs": int(args.epochs),
            "batch_size_patients": int(args.batch_size),
            "learning_rate": float(args.learning_rate),
            "weight_decay": float(args.weight_decay),
            "inference_threshold_logit": float(args.threshold),
            "candidate_count": CANDIDATE_COUNT,
            "detach_every_visit": True,
            "auxiliary_trajectory_loss": "none",
        },
        "split": {
            "train_patients": len(train_patient_indices),
            "train_visits": int(train_inputs.visit_mask.sum()),
            "dev_patients": len(dev_patient_indices),
            "dev_visits": int(dev_inputs.visit_mask.sum()),
            "heldout_resources_read": False,
            "test_resources_read": False,
            "audit_resources_read": False,
            "g3_resources_read": False,
            "g4_resources_read": False,
        },
        "inputs": {
            "current": ["diagnosis_code_set", "procedure_code_set"],
            "history": [
                "prescribed_on_previous_visit",
                "historical_prescription_frequency",
                "recency_since_last_prescribed",
            ],
            "medication_vocabulary": CANDIDATE_COUNT,
            "relation_priors": ["Train-derived EHR co-prescription", "DDI"],
            "moleRec_required": False,
            "hypeMed_required": False,
            "current_visit_medication_target_as_input": False,
            "ground_truth_cardinality_at_inference": False,
            "dev_tuned_threshold": False,
        },
        "architecture": {
            "GlobalStrong": "canonical frozen MoleRec threshold surface",
            "StatelessRelational": "identity initialization each visit + current cross-attention + one relation layer; no carry",
            "PersistentIndependent": "persistent identity states + causal assimilation; relation message disabled",
            "PersistentRelational": "persistent identity states + causal assimilation + one patient-conditioned EHR/DDI relation layer",
            "state_update_order": "predict and compute current BCE, then assimilate observed target for next visit",
            "state_init": "shared learned medication identity embedding projection",
            "state_update_parameters_shared_across_medications": True,
            "deep_gnn": False,
            "latent_intent_slots": False,
            "extra_backbone": False,
        },
        "metrics": {"GlobalStrong": global_metrics, **variant_metrics},
        "medication_count_diagnostics": variant_counts,
        "metric_deltas": metric_deltas,
        "state_dynamics_diagnostics": {
            **variant_dynamics,
            "PersistentRelational_minus_StatelessRelational_per_visit_jaccard": bounded_delta,
        },
        "best_persistent": best_name,
        "best_persistent_minus_StatelessRelational_jaccard": float(mechanism_delta),
        "best_persistent_minus_GlobalStrong_jaccard": float(global_delta),
        "small_delta_diagnostic": small_delta_diagnostic,
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
    parser.add_argument("--state-dim", type=int, default=DEFAULT_STATE_DIM)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--weight-decay", type=float, default=DEFAULT_WEIGHT_DECAY)
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
