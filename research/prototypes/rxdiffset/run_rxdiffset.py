#!/usr/bin/env python3
"""Run the one-seed RxDiffSet-v0 Train/Gate01-Dev architecture screen on 319."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from itertools import pairwise
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch

try:
    from hyperedit import backbone_sets, build_visit_contexts, evaluate_sets, set_change_summary
except ModuleNotFoundError:  # Running directly from the prototype directory.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hyperedit"))
    from hyperedit import backbone_sets, build_visit_contexts, evaluate_sets, set_change_summary

from rxdiffset import (
    CANDIDATE_COUNT,
    DEFAULT_ALPHA_BARS,
    DEFAULT_ATTENTION_HEADS,
    DEFAULT_BLOCKS,
    DEFAULT_CARDINALITY_WEIGHT,
    DEFAULT_HIDDEN_DIM,
    DEFAULT_NOISE_LEVELS,
    RxDiffSetModel,
    build_relation_features,
    corrupt_memberships,
    rx_diffset_loss,
    topk_set,
)

GATE01_SPLIT_NAMESPACE = "idea008-gate01-v1"
DEFAULT_SOURCE_REVISION = "e32382d9046377414ee51e7f6cf5313859700c93"
DEFAULT_SEED = 20260914
DEFAULT_EPOCHS = 6
DEFAULT_BATCH_SIZE = 64
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_WEIGHT_DECAY = 1e-4


def gate01_dev(patient_id: int) -> bool:
    """Return the existing Gate01-Dev half split for a zero-based patient id."""

    value = int.from_bytes(
        hashlib.sha256(f"{GATE01_SPLIT_NAMESPACE}:{patient_id}".encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _load_array(root: Path, name: str) -> np.ndarray:
    # A writable contiguous copy avoids torch.from_numpy warnings for read-only
    # memmaps while retaining the canonical artifact values exactly.
    return np.array(np.load(root / name, mmap_mode="r"), dtype=np.float32, copy=True)


def _target_sets(target_matrix: np.ndarray) -> tuple[frozenset[int], ...]:
    return tuple(
        frozenset(int(index) for index in np.flatnonzero(row > 0.5)) for row in target_matrix
    )


def _assert_alignment(contexts: tuple[Any, ...], targets: np.ndarray) -> None:
    if len(contexts) != targets.shape[0]:
        raise RuntimeError("record order does not align with the frozen MoleRec target array")
    for row, context in enumerate(contexts):
        expected = set(int(value) for value in context.target_medications)
        observed = set(int(index) for index in np.flatnonzero(targets[row] > 0.5))
        if expected != observed:
            raise RuntimeError(f"target mismatch at visit row {row}")


def _batch_tensor(array: np.ndarray, rows: np.ndarray, device: torch.device) -> torch.Tensor:
    return torch.from_numpy(np.ascontiguousarray(array[rows])).to(device=device)


def _train(
    model: RxDiffSetModel,
    embeddings: np.ndarray,
    scores: np.ndarray,
    targets: np.ndarray,
    prevalence: np.ndarray,
    alpha_bars: tuple[float, ...],
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    learning_rate: float,
    weight_decay: float,
    cardinality_weight: float,
    device: torch.device,
) -> dict[str, float]:
    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch size must be positive")
    rng = np.random.default_rng(seed)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    model.train()
    last: dict[str, float] = {}
    target_counts = targets.sum(axis=1).astype(np.int64)
    for _ in range(epochs):
        order = rng.permutation(len(targets))
        totals = {"reconstruction_bce": 0.0, "cardinality_ce": 0.0, "total": 0.0}
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            levels = rng.integers(1, len(alpha_bars), size=len(rows), dtype=np.int64)
            noisy = corrupt_memberships(targets[rows], prevalence, alpha_bars, levels, rng)
            embedding_batch = _batch_tensor(embeddings, rows, device)
            score_batch = _batch_tensor(scores, rows, device)
            noisy_batch = torch.from_numpy(noisy).to(device=device)
            clean_batch = _batch_tensor(targets, rows, device)
            count_batch = torch.from_numpy(target_counts[rows]).to(device=device)
            level_batch = torch.from_numpy(levels).to(device=device)
            optimizer.zero_grad(set_to_none=True)
            output = model(embedding_batch, score_batch, noisy_batch, level_batch)
            loss, detail = rx_diffset_loss(
                output,
                clean_batch,
                count_batch,
                cardinality_weight=cardinality_weight,
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
    model: RxDiffSetModel,
    embeddings: np.ndarray,
    scores: np.ndarray,
    prevalence: np.ndarray,
    alpha_bars: tuple[float, ...],
    *,
    batch_size: int,
    seed: int,
    device: torch.device,
) -> dict[str, Any]:
    """Run one seeded reverse trace and retain final plus one-step logits."""

    rng = np.random.default_rng(seed)
    rows = len(scores)
    current = (rng.random((rows, CANDIDATE_COUNT)) < prevalence[None, :]).astype(np.float32)
    states = [current.copy()]
    first_logits: np.ndarray | None = None
    first_cardinality_logits: np.ndarray | None = None
    flip_counts: list[float] = []
    final_logits: np.ndarray | None = None
    final_cardinality_logits: np.ndarray | None = None
    model.eval()
    with torch.no_grad():
        # t descends from the noisiest level to the clean level.  The denoiser
        # predicts y0, and the next binary state mixes that estimate with the
        # Train prevalence prior at alpha_bar[t-1].
        for level in range(len(alpha_bars) - 1, 0, -1):
            logits_parts: list[np.ndarray] = []
            cardinality_parts: list[np.ndarray] = []
            for start in range(0, rows, batch_size):
                stop = min(start + batch_size, rows)
                row_slice = np.arange(start, stop, dtype=np.int64)
                level_batch = torch.full((stop - start,), level, dtype=torch.long, device=device)
                output = model(
                    _batch_tensor(embeddings, row_slice, device),
                    _batch_tensor(scores, row_slice, device),
                    torch.from_numpy(current[start:stop]).to(device=device),
                    level_batch,
                )
                logits_parts.append(output.clean_logits.cpu().numpy())
                cardinality_parts.append(output.cardinality_logits.cpu().numpy())
            step_logits = np.concatenate(logits_parts, axis=0)
            step_cardinality_logits = np.concatenate(cardinality_parts, axis=0)
            if first_logits is None:
                first_logits = step_logits
                first_cardinality_logits = step_cardinality_logits
            probability = 1.0 / (1.0 + np.exp(-np.clip(step_logits, -30.0, 30.0)))
            alpha_previous = float(alpha_bars[level - 1])
            reverse_probability = alpha_previous * probability + (1.0 - alpha_previous) * prevalence
            next_state = (rng.random(reverse_probability.shape) < reverse_probability).astype(
                np.float32
            )
            flip_counts.append(float(np.not_equal(current, next_state).sum(axis=1).mean()))
            current = next_state
            states.append(current.copy())

        # Evaluate the clean state once more at t=0 so final rankings use the
        # same denoiser surface after the complete reverse process.
        logits_parts = []
        cardinality_parts = []
        for start in range(0, rows, batch_size):
            stop = min(start + batch_size, rows)
            row_slice = np.arange(start, stop, dtype=np.int64)
            level_batch = torch.zeros(stop - start, dtype=torch.long, device=device)
            output = model(
                _batch_tensor(embeddings, row_slice, device),
                _batch_tensor(scores, row_slice, device),
                torch.from_numpy(current[start:stop]).to(device=device),
                level_batch,
            )
            logits_parts.append(output.clean_logits.cpu().numpy())
            cardinality_parts.append(output.cardinality_logits.cpu().numpy())
        final_logits = np.concatenate(logits_parts, axis=0)
        final_cardinality_logits = np.concatenate(cardinality_parts, axis=0)

    assert first_logits is not None
    assert first_cardinality_logits is not None
    assert final_logits is not None
    assert final_cardinality_logits is not None
    predicted_cardinality = final_cardinality_logits.argmax(axis=1).astype(np.int64)
    one_step_cardinality = first_cardinality_logits.argmax(axis=1).astype(np.int64)
    standalone = tuple(
        topk_set(row, int(cardinality))
        for row, cardinality in zip(final_logits, predicted_cardinality, strict=True)
    )
    one_step = tuple(
        topk_set(row, int(cardinality))
        for row, cardinality in zip(first_logits, one_step_cardinality, strict=True)
    )
    base = backbone_sets(scores)
    same_k = tuple(
        topk_set(row, len(base_set)) for row, base_set in zip(final_logits, base, strict=True)
    )
    return {
        "final_logits": final_logits,
        "one_step_logits": first_logits,
        "predicted_cardinality": predicted_cardinality,
        "standalone_predictions": standalone,
        "same_k_predictions": same_k,
        "one_step_predictions": one_step,
        "reverse_states": tuple(states),
        "mean_membership_flips_per_reverse_step": sum(flip_counts) / len(flip_counts),
        "flips_per_reverse_step": tuple(flip_counts),
    }


def _metrics(
    targets: np.ndarray,
    predictions: tuple[frozenset[int], ...],
    scores: np.ndarray,
    ddi: np.ndarray,
) -> dict[str, float]:
    return evaluate_sets(_target_sets(targets), predictions, scores, ddi)


def _load_graph_refine_metrics(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    try:
        metrics = payload["diagnostic_same_k"]["GraphRefine-SameK"]
    except (KeyError, TypeError) as error:
        raise RuntimeError("GraphRefine-SameK aggregate result is missing") from error
    required = {"jaccard", "f1", "prauc", "ddi", "mean_medication_count"}
    if not required.issubset(metrics):
        raise RuntimeError("GraphRefine-SameK aggregate result is incomplete")
    return {key: float(metrics[key]) for key in required}


def _reverse_change_summary(states: tuple[np.ndarray, ...]) -> dict[str, Any]:
    if len(states) < 2:
        raise RuntimeError("reverse trace did not contain enough states")
    changed_any = np.zeros(states[0].shape[0], dtype=bool)
    for before, after in pairwise(states):
        changed_any |= np.any(before != after, axis=1)
    return {
        "changed_fraction_initial_to_final": float(np.any(states[0] != states[-1], axis=1).mean()),
        "changed_any_fraction": float(changed_any.mean()),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    graph_refine_result = args.graph_refine_result.resolve()
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    ehr = np.asarray(dill.load((snapshot / "ehr_adj_final.pkl").open("rb")), dtype=np.float32)
    if ddi.shape != (CANDIDATE_COUNT, CANDIDATE_COUNT):
        raise RuntimeError("the canonical DDI matrix is not 131 by 131")
    if ehr.shape != ddi.shape:
        raise RuntimeError("the canonical EHR co-prescription matrix is not 131 by 131")

    split_point = int(len(records) * 2 / 3)
    train_patient_indices = tuple(range(split_point))
    dev_patient_indices = tuple(
        patient_id for patient_id in range(split_point, len(records)) if gate01_dev(patient_id)
    )
    train_contexts = build_visit_contexts(records, train_patient_indices)
    dev_contexts = build_visit_contexts(records, dev_patient_indices)
    train_scores = _load_array(train_dev_root, "train_scores.npy")
    train_embeddings = _load_array(train_dev_root, "train_embeddings.npy")
    train_targets = _load_array(train_dev_root, "train_targets.npy")
    dev_scores = _load_array(train_dev_root, "dev_scores.npy")
    dev_embeddings = _load_array(train_dev_root, "dev_embeddings.npy")
    dev_targets = _load_array(train_dev_root, "dev_targets.npy")
    for name, value in (
        ("train_scores", train_scores),
        ("train_targets", train_targets),
        ("dev_scores", dev_scores),
        ("dev_targets", dev_targets),
    ):
        if value.ndim != 2 or value.shape[1] != CANDIDATE_COUNT:
            raise RuntimeError(f"{name} does not have the frozen [visits, 131] shape")
    for name, value, reference in (
        ("train_embeddings", train_embeddings, train_scores),
        ("dev_embeddings", dev_embeddings, dev_scores),
    ):
        if value.ndim != 3 or value.shape[:2] != reference.shape:
            raise RuntimeError(f"{name} is not aligned with its frozen score matrix")
    _assert_alignment(train_contexts, train_targets)
    _assert_alignment(dev_contexts, dev_targets)

    train_embeddings = np.nan_to_num(train_embeddings, nan=0.0, posinf=0.0, neginf=0.0)
    dev_embeddings = np.nan_to_num(dev_embeddings, nan=0.0, posinf=0.0, neginf=0.0)
    prevalence = np.clip(train_targets.mean(axis=0), 1e-5, 1.0 - 1e-5).astype(np.float32)
    relation_features = build_relation_features(ehr, ddi)
    max_train_cardinality = int(np.clip(train_targets.sum(axis=1).max(), 1, CANDIDATE_COUNT))
    alpha_bars = tuple(float(value) for value in args.alpha_bars)
    if len(alpha_bars) != args.noise_levels:
        raise RuntimeError("alpha-bar count must match the configured noise levels")

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RxDiffSetModel(
        embedding_dim=int(train_embeddings.shape[-1]),
        relation_features=relation_features,
        max_cardinality=max_train_cardinality,
        hidden_dim=args.hidden_dim,
        attention_heads=args.attention_heads,
        blocks=args.blocks,
        noise_levels=args.noise_levels,
    ).to(device)
    train_detail = _train(
        model,
        train_embeddings,
        train_scores,
        train_targets,
        prevalence,
        alpha_bars,
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        cardinality_weight=args.cardinality_weight,
        device=device,
    )
    prediction = _predict(
        model,
        dev_embeddings,
        dev_scores,
        prevalence,
        alpha_bars,
        batch_size=args.batch_size,
        seed=args.seed,
        device=device,
    )

    base_predictions = backbone_sets(dev_scores)
    graph_refine_metrics = _load_graph_refine_metrics(graph_refine_result)
    metrics = {
        "MoleRec": _metrics(dev_targets, base_predictions, dev_scores, ddi),
        "GraphRefine-SameK": graph_refine_metrics,
        "RxDiffSet standalone": _metrics(
            dev_targets, prediction["standalone_predictions"], prediction["final_logits"], ddi
        ),
        "RxDiffSet-SameK": _metrics(
            dev_targets, prediction["same_k_predictions"], prediction["final_logits"], ddi
        ),
        "RxDiffSet one-step": _metrics(
            dev_targets, prediction["one_step_predictions"], prediction["one_step_logits"], ddi
        ),
    }
    target_counts = dev_targets.sum(axis=1)
    predicted_counts = prediction["predicted_cardinality"]
    standalone_change = set_change_summary(base_predictions, prediction["standalone_predictions"])
    same_k_change = set_change_summary(base_predictions, prediction["same_k_predictions"])
    one_step_change = set_change_summary(base_predictions, prediction["one_step_predictions"])
    reverse_change = _reverse_change_summary(prediction["reverse_states"])
    standalone = metrics["RxDiffSet standalone"]
    same_k = metrics["RxDiffSet-SameK"]
    standalone_survives = standalone["jaccard"] >= 0.537 or (
        standalone["jaccard"] >= 0.534 and standalone["ddi"] <= 0.068
    )
    same_k_survives = same_k["jaccard"] >= 0.537 or (
        same_k["jaccard"] >= 0.534 and same_k["ddi"] <= 0.068
    )
    decision = "STRONG_SURVIVE_RXDIFFSET" if standalone_survives else "STOP_RXDIFFSET_V0"
    return {
        "working_name": "RxDiffSet-v0",
        "source_revision": args.source_revision,
        "device": str(device),
        "seed": args.seed,
        "config": {
            "embedding_dim": int(train_embeddings.shape[-1]),
            "hidden_dim": args.hidden_dim,
            "attention_heads": args.attention_heads,
            "interaction_blocks": args.blocks,
            "noise_levels": args.noise_levels,
            "alpha_bars": list(alpha_bars),
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "cardinality_weight": args.cardinality_weight,
            "train_prevalence_only": True,
        },
        "split": {
            "train_patients": split_point,
            "train_visits": len(train_contexts),
            "dev_patients": len(dev_patient_indices),
            "dev_visits": len(dev_contexts),
            "held_out_resources_read": False,
        },
        "architecture": {
            "tokens": "131 per-visit patient-specific MoleRec medication embeddings + frozen scores + noisy membership + noise embedding",
            "interaction": "two relation-biased permutation-equivariant self-attention blocks over medication tokens",
            "relations": "normalized EHR co-prescription and DDI adjacency channels",
            "denoiser": "binary clean-membership reconstruction from prevalence-preserving discrete corruption",
            "cardinality": f"categorical Train-derived K=0..{max_train_cardinality} head",
            "inference": "seeded reverse denoising with bounded 7 transitions; final Top-K uses predicted K",
        },
        "metrics": metrics,
        "cardinality_mae": float(np.abs(predicted_counts - target_counts).mean()),
        "mean_predicted_cardinality": float(predicted_counts.mean()),
        "exact_same_k_cardinality": all(
            len(base) == len(prediction["same_k_predictions"][index])
            for index, base in enumerate(base_predictions)
        ),
        "set_change_fraction": standalone_change["changed_fraction"],
        "mean_symmetric_difference": standalone_change["mean_symmetric_difference"],
        "same_k_set_change_fraction": same_k_change["changed_fraction"],
        "same_k_mean_symmetric_difference": same_k_change["mean_symmetric_difference"],
        "one_step_set_change_fraction": one_step_change["changed_fraction"],
        "reverse_changed_fraction": reverse_change["changed_fraction_initial_to_final"],
        "reverse_changed_any_fraction": reverse_change["changed_any_fraction"],
        "mean_membership_flips_per_reverse_step": prediction[
            "mean_membership_flips_per_reverse_step"
        ],
        "flips_per_reverse_step": prediction["flips_per_reverse_step"],
        "same_k_survival_signal": same_k_survives,
        "observed_effect": "strong" if standalone_survives else "weak",
        "decision": decision,
        "last_train_loss": train_detail,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--graph-refine-result", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default=DEFAULT_SOURCE_REVISION)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--hidden-dim", type=int, default=DEFAULT_HIDDEN_DIM)
    parser.add_argument("--attention-heads", type=int, default=DEFAULT_ATTENTION_HEADS)
    parser.add_argument("--blocks", type=int, default=DEFAULT_BLOCKS)
    parser.add_argument("--noise-levels", type=int, default=DEFAULT_NOISE_LEVELS)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--weight-decay", type=float, default=DEFAULT_WEIGHT_DECAY)
    parser.add_argument("--cardinality-weight", type=float, default=DEFAULT_CARDINALITY_WEIGHT)
    parser.add_argument(
        "--alpha-bars",
        type=float,
        nargs="+",
        default=list(DEFAULT_ALPHA_BARS),
    )
    args = parser.parse_args()
    result = run(args)
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
