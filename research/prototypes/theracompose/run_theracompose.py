#!/usr/bin/env python3
"""Run the one-seed TheraCompose Train/Dev architecture screen on 319."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch
from hyperedit import backbone_sets, build_visit_contexts, evaluate_sets
from run_hyperedit import gate01_dev
from theracompose import (
    CANDIDATE_COUNT,
    DEFAULT_CODE_HASH_WIDTH,
    DEFAULT_HISTORY_LENGTH,
    DEFAULT_SEARCH_CANDIDATE_POOL,
    DEFAULT_SEARCH_ITERATIONS,
    DEFAULT_SLOT_ITERATIONS,
    HARD_NEGATIVE_TYPES,
    TheraComposeModel,
    build_patient_event_sequences,
    hard_negative_masks,
    intent_coverage_diagnostic,
    set_change_summary,
    structured_set_search,
    target_sets_from_matrix,
    theracompose_loss,
    topk_set,
)

DEFAULT_SEED = 20260914
DEFAULT_EPOCHS = 8
DEFAULT_BATCH_SIZE = 64
DEFAULT_HIDDEN_DIM = 96
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_WEIGHT_DECAY = 1e-4
DEFAULT_MARGIN = 0.5
DEFAULT_LAMBDA_UNARY = 0.5
DEFAULT_LAMBDA_CARDINALITY = 0.5


def _load_array(root: Path, name: str) -> np.ndarray:
    value = np.load(root / name, mmap_mode="r")
    return np.asarray(value, dtype=np.float32)


def _assert_alignment(contexts: tuple[Any, ...], targets: np.ndarray) -> None:
    if len(contexts) != targets.shape[0]:
        raise RuntimeError("record order does not align with the frozen MoleRec target array")
    for row, context in enumerate(contexts):
        expected = set(int(value) for value in context.target_medications)
        observed = set(int(index) for index in np.flatnonzero(targets[row] > 0.5))
        if expected != observed:
            raise RuntimeError(f"target mismatch at visit row {row}")


def _sequence_mask(events: np.ndarray) -> np.ndarray:
    """Use the signed event marker to exclude left-padding rows."""

    return np.abs(events[:, :, -2]) > 0.5


def _metrics(
    targets: np.ndarray,
    predictions: tuple[frozenset[int], ...],
    scores: np.ndarray,
    ddi: np.ndarray,
) -> dict[str, float]:
    return evaluate_sets(target_sets_from_matrix(targets), predictions, scores, ddi)


def _train(
    model: TheraComposeModel,
    events: np.ndarray,
    sequence_mask: np.ndarray,
    base_scores: np.ndarray,
    targets: np.ndarray,
    negatives: np.ndarray,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    learning_rate: float,
    weight_decay: float,
    margin: float,
    lambda_unary: float,
    lambda_cardinality: float,
    device: torch.device,
) -> dict[str, float]:
    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch size must be positive")
    generator = np.random.default_rng(seed)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    model.train()
    last: dict[str, float] = {}
    for _ in range(epochs):
        order = generator.permutation(len(events))
        totals = {
            "energy_margin": 0.0,
            "unary_bce": 0.0,
            "cardinality_ce": 0.0,
            "total": 0.0,
        }
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            event_batch = torch.from_numpy(events[rows]).to(device=device)
            mask_batch = torch.from_numpy(sequence_mask[rows]).to(device=device)
            score_batch = torch.from_numpy(base_scores[rows]).to(device=device)
            target_batch = torch.from_numpy(targets[rows]).to(device=device)
            negative_batch = torch.from_numpy(negatives[rows]).to(device=device)
            optimizer.zero_grad(set_to_none=True)
            output = model(event_batch, mask_batch, score_batch)
            loss, detail = theracompose_loss(
                model,
                output,
                target_batch,
                negative_batch,
                margin=margin,
                lambda_unary=lambda_unary,
                lambda_cardinality=lambda_cardinality,
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
    model: TheraComposeModel,
    events: np.ndarray,
    sequence_mask: np.ndarray,
    base_scores: np.ndarray,
    *,
    batch_size: int,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    outputs: dict[str, list[np.ndarray]] = {
        "unary_logits": [],
        "cardinality_logits": [],
        "expected_cardinality": [],
        "activity": [],
        "intent_support": [],
        "compatibility": [],
        "risk": [],
    }
    with torch.no_grad():
        for start in range(0, len(events), batch_size):
            stop = min(start + batch_size, len(events))
            event_batch = torch.from_numpy(events[start:stop]).to(device=device)
            mask_batch = torch.from_numpy(sequence_mask[start:stop]).to(device=device)
            score_batch = torch.from_numpy(base_scores[start:stop]).to(device=device)
            output = model(event_batch, mask_batch, score_batch)
            outputs["unary_logits"].append(output.unary_logits.cpu().numpy())
            outputs["cardinality_logits"].append(output.cardinality_logits.cpu().numpy())
            outputs["expected_cardinality"].append(output.expected_cardinality.cpu().numpy())
            outputs["activity"].append(output.activity.cpu().numpy())
            outputs["intent_support"].append(output.intent_support.cpu().numpy())
            outputs["compatibility"].append(output.compatibility.cpu().numpy())
            outputs["risk"].append(output.risk.cpu().numpy())
    arrays = {key: np.concatenate(value, axis=0) for key, value in outputs.items()}
    predicted_cardinality = arrays["cardinality_logits"].argmax(axis=1).astype(np.int64)
    unary_predictions = tuple(
        topk_set(row, int(cardinality))
        for row, cardinality in zip(arrays["unary_logits"], predicted_cardinality)  # noqa: B905
    )
    full_predictions = structured_set_search(
        arrays["unary_logits"],
        arrays["compatibility"],
        arrays["risk"],
        arrays["intent_support"],
        arrays["activity"],
        arrays["expected_cardinality"],
        unary_predictions,
        max_iterations=DEFAULT_SEARCH_ITERATIONS,
        candidate_pool=DEFAULT_SEARCH_CANDIDATE_POOL,
    )
    arrays["predicted_cardinality"] = predicted_cardinality
    arrays["unary_predictions"] = unary_predictions
    arrays["full_predictions"] = full_predictions
    return arrays


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
    ehr = np.maximum(ehr, 0.0)
    np.fill_diagonal(ehr, 0.0)
    if float(ehr.max()) > 0.0:
        ehr /= float(ehr.max())
    ddi = np.maximum(ddi, 0.0)

    split_point = int(len(records) * 2 / 3)
    train_indices = tuple(range(split_point))
    dev_patient_indices = tuple(
        patient_id for patient_id in range(split_point, len(records)) if gate01_dev(patient_id)
    )
    train_contexts = build_visit_contexts(records, train_indices)
    dev_contexts = build_visit_contexts(records, dev_patient_indices)
    train_scores = _load_array(train_dev_root, "train_scores.npy")
    train_embeddings = _load_array(train_dev_root, "train_embeddings.npy")
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
    if train_embeddings.ndim != 3 or train_embeddings.shape[:2] != train_scores.shape:
        raise RuntimeError("train embeddings are not aligned with train scores")
    _assert_alignment(train_contexts, train_targets)
    _assert_alignment(dev_contexts, dev_targets)

    train_events = build_patient_event_sequences(
        records,
        train_indices,
        code_hash_width=args.code_hash_width,
        history_length=args.history_length,
    )
    dev_events = build_patient_event_sequences(
        records,
        dev_patient_indices,
        code_hash_width=args.code_hash_width,
        history_length=args.history_length,
    )
    if train_events.shape[0] != train_scores.shape[0] or dev_events.shape[0] != dev_scores.shape[0]:
        raise RuntimeError("patient event sequences are not aligned with MoleRec arrays")
    train_masks = _sequence_mask(train_events)
    dev_masks = _sequence_mask(dev_events)
    train_target_sets = target_sets_from_matrix(train_targets)
    train_negative_masks = hard_negative_masks(train_target_sets, train_scores, ddi)
    max_train_cardinality = max((len(item) for item in train_target_sets), default=1)
    max_train_cardinality = min(CANDIDATE_COUNT, max(1, max_train_cardinality))
    medication_embeddings = np.nan_to_num(train_embeddings, nan=0.0, posinf=0.0, neginf=0.0).mean(
        axis=0
    )
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TheraComposeModel(
        event_features=int(train_events.shape[-1]),
        medication_embeddings=medication_embeddings,
        ehr_adjacency=ehr,
        ddi_adjacency=ddi,
        hidden_dim=args.hidden_dim,
        max_cardinality=max_train_cardinality,
        slot_iterations=args.slot_iterations,
    ).to(device)
    train_detail = _train(
        model,
        train_events,
        train_masks,
        train_scores,
        train_targets,
        train_negative_masks,
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        margin=args.margin,
        lambda_unary=args.lambda_unary,
        lambda_cardinality=args.lambda_cardinality,
        device=device,
    )
    prediction = _predict(
        model,
        dev_events,
        dev_masks,
        dev_scores,
        batch_size=args.batch_size,
        device=device,
    )
    dev_target_sets = target_sets_from_matrix(dev_targets)
    molerec_predictions = backbone_sets(dev_scores)
    graph_refine_metrics = _load_graph_refine_metrics(graph_refine_result)
    unary_metrics = _metrics(
        dev_targets, prediction["unary_predictions"], prediction["unary_logits"], ddi
    )
    full_metrics = _metrics(
        dev_targets, prediction["full_predictions"], prediction["unary_logits"], ddi
    )
    baseline_metrics = _metrics(dev_targets, molerec_predictions, dev_scores, ddi)
    target_counts = np.asarray([len(item) for item in dev_target_sets], dtype=np.float32)
    predicted_counts = prediction["predicted_cardinality"].astype(np.float32)
    full_change = set_change_summary(molerec_predictions, prediction["full_predictions"])
    unary_change = set_change_summary(molerec_predictions, prediction["unary_predictions"])
    structured_change = set_change_summary(
        prediction["unary_predictions"], prediction["full_predictions"]
    )
    full_jaccard = full_metrics["jaccard"]
    full_ddi = full_metrics["ddi"]
    if full_jaccard >= 0.537 or (full_jaccard >= 0.534 and full_ddi <= 0.068):
        observed_effect = "strong"
        decision = "STRONG_SURVIVE"
    else:
        observed_effect = "weak"
        decision = "STOP_THERACOMPOSE_V0"
    return {
        "working_name": "TheraCompose",
        "source_revision": args.source_revision,
        "device": str(device),
        "seed": args.seed,
        "config": {
            "event_code_hash_width": args.code_hash_width,
            "history_length": args.history_length,
            "intent_slots": 4,
            "slot_iterations": args.slot_iterations,
            "hidden_dim": args.hidden_dim,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "margin": args.margin,
            "lambda_unary": args.lambda_unary,
            "lambda_cardinality": args.lambda_cardinality,
            "search_iterations": DEFAULT_SEARCH_ITERATIONS,
            "search_candidate_pool": DEFAULT_SEARCH_CANDIDATE_POOL,
        },
        "split": {
            "train_patients": split_point,
            "train_visits": len(train_contexts),
            "dev_patients": len(dev_patient_indices),
            "dev_visits": len(dev_contexts),
            "held_out_resources_read": False,
        },
        "architecture": {
            "patient_encoder": "hashed current diagnosis/procedure set plus four-event GRU history",
            "intent_slots": 4,
            "interaction_model": "two-layer patient-conditioned medication message passing",
            "cardinality_model": f"categorical head over Train-derived K=0..{max_train_cardinality}",
            "energy": "unary - compatibility + DDI risk + intent coverage + cardinality consistency",
            "negative_construction": list(HARD_NEGATIVE_TYPES),
        },
        "metrics": {
            "MoleRec": baseline_metrics,
            "GraphRefine-SameK": graph_refine_metrics,
            "TheraCompose unary-only": unary_metrics,
            "TheraCompose full structured set": full_metrics,
        },
        "cardinality_mae": float(np.abs(predicted_counts - target_counts).mean()),
        "mean_active_intent_slots": float((prediction["activity"] >= 0.5).sum(axis=1).mean()),
        "mean_intent_activity": float(prediction["activity"].mean()),
        "intent_coverage_diagnostic": intent_coverage_diagnostic(
            prediction["full_predictions"], prediction["intent_support"], prediction["activity"]
        ),
        "set_change_fraction": full_change["changed_fraction"],
        "mean_symmetric_difference": full_change["mean_symmetric_difference"],
        "unary_set_change_fraction": unary_change["changed_fraction"],
        "unary_mean_symmetric_difference": unary_change["mean_symmetric_difference"],
        "structured_inference_changed_fraction": structured_change["changed_fraction"],
        "structured_inference_mean_symmetric_difference": structured_change[
            "mean_symmetric_difference"
        ],
        "observed_effect": observed_effect,
        "decision": decision,
        "last_train_loss": train_detail,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--graph-refine-result", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default="6b818fa04c4f40657fafc962832ae1dc083e86f8")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--code-hash-width", type=int, default=DEFAULT_CODE_HASH_WIDTH)
    parser.add_argument("--history-length", type=int, default=DEFAULT_HISTORY_LENGTH)
    parser.add_argument("--slot-iterations", type=int, default=DEFAULT_SLOT_ITERATIONS)
    parser.add_argument("--hidden-dim", type=int, default=DEFAULT_HIDDEN_DIM)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--weight-decay", type=float, default=DEFAULT_WEIGHT_DECAY)
    parser.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    parser.add_argument("--lambda-unary", type=float, default=DEFAULT_LAMBDA_UNARY)
    parser.add_argument("--lambda-cardinality", type=float, default=DEFAULT_LAMBDA_CARDINALITY)
    args = parser.parse_args()
    result = run(args)
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
