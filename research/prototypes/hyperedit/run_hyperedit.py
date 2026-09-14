#!/usr/bin/env python3
"""Run the one-seed HyperEdit-MR Train/Dev prototype screen on 319."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch
from hyperedit import (
    CANDIDATE_COUNT,
    DEFAULT_MAX_STEPS,
    DEFAULT_TOP_K,
    HyperEditMR,
    backbone_sets,
    build_node_features,
    build_retrieval_index,
    build_visit_contexts,
    edit_trajectory,
    evaluate_sets,
    historical_support,
    hyperedit_loss,
    retrieval_fusion_scores,
    retrieve_features,
    same_cardinality_topk,
    set_change_summary,
)

GATE01_SPLIT_NAMESPACE = "idea008-gate01-v1"
DEFAULT_SEED = 20260914
DEFAULT_EPOCHS = 10
DEFAULT_BATCH_SIZE = 64
DEFAULT_HIDDEN_DIM = 96
DEFAULT_LAMBDA_SET = 1.0
DEFAULT_LAMBDA_DDI = 0.05
DEFAULT_FUSION_ALPHA = 1.0


def gate01_dev(patient_id: int) -> bool:
    """Return the existing Gate 01 Dev half split for a zero-based patient id."""

    value = int.from_bytes(
        hashlib.sha256(f"{GATE01_SPLIT_NAMESPACE}:{patient_id}".encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _target_sets(target_matrix: np.ndarray) -> tuple[frozenset[int], ...]:
    return tuple(
        frozenset(int(index) for index in np.flatnonzero(row > 0.5)) for row in target_matrix
    )


def _actions(
    base_sets: tuple[frozenset[int], ...],
    target_sets: tuple[frozenset[int], ...],
    max_steps: int,
) -> np.ndarray:
    stop = 2 * CANDIDATE_COUNT
    actions = np.full((len(base_sets), max_steps), stop, dtype=np.int64)
    for row, (base, target) in enumerate(zip(base_sets, target_sets)):  # noqa: B905
        trajectory = edit_trajectory(base, target)
        if len(trajectory) > max_steps:
            trajectory = (*trajectory[: max_steps - 1], stop)
        actions[row, : len(trajectory)] = trajectory
    return actions


def _load_array(root: Path, name: str) -> np.ndarray:
    value = np.load(root / name, mmap_mode="r")
    return np.asarray(value, dtype=np.float32)


def _assert_alignment(contexts: tuple[Any, ...], targets: np.ndarray) -> None:
    if len(contexts) != targets.shape[0]:
        raise RuntimeError("record order does not align with the frozen MoleRec target array")
    for row, context in enumerate(contexts):
        expected = set(context.target_medications)
        observed = set(int(index) for index in np.flatnonzero(targets[row] > 0.5))
        if expected != observed:
            raise RuntimeError(f"target mismatch at visit row {row}")


def _train(
    model: HyperEditMR,
    node_features: np.ndarray,
    initial_sets: np.ndarray,
    actions: np.ndarray,
    targets: np.ndarray,
    ddi: np.ndarray,
    co_support: np.ndarray,
    ehr: np.ndarray,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    lambda_set: float,
    lambda_ddi: float,
    device: torch.device,
) -> dict[str, float]:
    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch_size must be positive")
    generator = np.random.default_rng(seed)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    model.train()
    last: dict[str, float] = {}
    for _ in range(epochs):
        order = generator.permutation(len(node_features))
        totals: dict[str, float] = {
            "action_ce": 0.0,
            "set_bce": 0.0,
            "ddi_penalty": 0.0,
            "total": 0.0,
        }
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            node = torch.from_numpy(node_features[rows]).to(device=device)
            initial = torch.from_numpy(initial_sets[rows]).to(device=device)
            action_targets = torch.from_numpy(actions[rows]).to(device=device)
            target = torch.from_numpy(targets[rows]).to(device=device)
            co = torch.from_numpy(co_support[rows]).to(device=device)
            optimizer.zero_grad(set_to_none=True)
            action_logits, set_logits = model.forward_sequence(
                node,
                initial,
                ddi,
                co,
                ehr,
                teacher_actions=action_targets,
            )
            loss, detail = hyperedit_loss(
                action_logits,
                action_targets,
                set_logits,
                target,
                ddi,
                lambda_set=lambda_set,
                lambda_ddi=lambda_ddi,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            for key in totals:
                totals[key] += detail[key]
            batches += 1
        last = {key: value / batches for key, value in totals.items()}
    return last


def _metrics(
    targets: np.ndarray,
    predictions: tuple[frozenset[int], ...],
    scores: np.ndarray,
    ddi: np.ndarray,
) -> dict[str, float]:
    return evaluate_sets(_target_sets(targets), predictions, scores, ddi)


def run(args: argparse.Namespace) -> dict[str, Any]:
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
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

    split_point = int(len(records) * 2 / 3)
    train_contexts = build_visit_contexts(records, range(split_point))
    dev_patient_indices = tuple(
        patient_id for patient_id in range(split_point, len(records)) if gate01_dev(patient_id)
    )
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
    if train_embeddings.ndim != 3 or train_embeddings.shape[:2] != train_scores.shape:
        raise RuntimeError("train embeddings are not aligned with train scores")
    if dev_embeddings.ndim != 3 or dev_embeddings.shape[:2] != dev_scores.shape:
        raise RuntimeError("dev embeddings are not aligned with dev scores")
    _assert_alignment(train_contexts, train_targets)
    _assert_alignment(dev_contexts, dev_targets)

    retrieval_index = build_retrieval_index(train_contexts)
    train_retrieval = retrieve_features(train_contexts, retrieval_index, top_k=args.top_k)
    dev_retrieval = retrieve_features(dev_contexts, retrieval_index, top_k=args.top_k)
    train_history = historical_support(train_contexts)
    dev_history = historical_support(dev_contexts)
    train_nodes = build_node_features(
        train_scores, train_embeddings, train_retrieval.support, train_history
    )
    dev_nodes = build_node_features(dev_scores, dev_embeddings, dev_retrieval.support, dev_history)
    train_base = backbone_sets(train_scores)
    dev_base = backbone_sets(dev_scores)
    train_target_sets = _target_sets(train_targets)
    actions = _actions(train_base, train_target_sets, args.max_steps)

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = HyperEditMR(
        node_features=int(train_nodes.shape[-1]),
        hidden_dim=args.hidden_dim,
        max_steps=args.max_steps,
    ).to(device)
    train_detail = _train(
        model,
        train_nodes,
        (train_scores >= 0.0).astype(np.float32),
        actions,
        train_targets,
        ddi,
        train_retrieval.co_support,
        ehr,
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        lambda_set=args.lambda_set,
        lambda_ddi=args.lambda_ddi,
        device=device,
    )
    model.eval()
    with torch.no_grad():
        hyper_predictions, hyper_set_logits, _ = model.predict(
            torch.from_numpy(dev_nodes).to(device=device),
            torch.from_numpy((dev_scores >= 0.0).astype(np.float32)).to(device=device),
            ddi,
            torch.from_numpy(dev_retrieval.co_support).to(device=device),
            ehr,
        )
    hyper_scores = hyper_set_logits.detach().cpu().numpy()
    fusion_scores = retrieval_fusion_scores(
        dev_scores, dev_retrieval.support, alpha=args.fusion_alpha
    )
    retrieval_predictions = backbone_sets(fusion_scores)
    diagnostic_same_k = bool(getattr(args, "diagnostic_same_k", False))
    graph_same_k_predictions: tuple[frozenset[int], ...] = ()
    retrieval_same_k_predictions: tuple[frozenset[int], ...] = ()
    if diagnostic_same_k:
        graph_same_k_predictions = tuple(
            same_cardinality_topk(score_row, base_set)
            for score_row, base_set in zip(hyper_scores, dev_base)  # noqa: B905
        )
        retrieval_same_k_predictions = tuple(
            same_cardinality_topk(score_row, base_set)
            for score_row, base_set in zip(fusion_scores, dev_base)  # noqa: B905
        )
    results = {
        "Frozen MoleRec": _metrics(dev_targets, dev_base, dev_scores, ddi),
        "MoleRec + retrieval-only score fusion": _metrics(
            dev_targets, retrieval_predictions, fusion_scores, ddi
        ),
        "HyperEdit-MR": _metrics(dev_targets, hyper_predictions, hyper_scores, ddi),
    }
    change = set_change_summary(dev_base, hyper_predictions)
    baseline = results["Frozen MoleRec"]
    hyper = results["HyperEdit-MR"]
    jaccard_gain = hyper["jaccard"] - baseline["jaccard"]
    ddi_gain = hyper["ddi"] - baseline["ddi"]
    if jaccard_gain >= 0.010 or (ddi_gain <= -0.010 and jaccard_gain >= -0.005):
        observed_effect = "strong"
    elif jaccard_gain >= 0.005 and ddi_gain <= -0.005:
        observed_effect = "moderate"
    else:
        observed_effect = "weak"
    result: dict[str, Any] = {
        "working_name": "HyperEdit-MR",
        "source_revision": args.source_revision,
        "device": str(device),
        "seed": args.seed,
        "config": {
            "retrieval_top_k": args.top_k,
            "retrieval_width": int(retrieval_index.projections.shape[1]),
            "hidden_dim": args.hidden_dim,
            "graph_layers": 2,
            "max_editor_steps": args.max_steps,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": 1e-3,
            "weight_decay": 1e-4,
            "lambda_set": args.lambda_set,
            "lambda_ddi": args.lambda_ddi,
            "fusion_alpha": args.fusion_alpha,
        },
        "split": {
            "train_patients": split_point,
            "train_visits": len(train_contexts),
            "dev_patients": len(dev_patient_indices),
            "dev_visits": len(dev_contexts),
            "held_out_resources_read": False,
        },
        "metrics": results,
        "set_change_fraction": change["changed_fraction"],
        "mean_symmetric_difference": change["mean_symmetric_difference"],
        "observed_effect": observed_effect,
        "recommendation": "CONTINUE_HYPEREDIT"
        if observed_effect in {"strong", "moderate"}
        else "STOP_HYPEREDIT",
        "last_train_loss": train_detail,
    }
    if diagnostic_same_k:
        graph_same_k_metrics = _metrics(dev_targets, graph_same_k_predictions, hyper_scores, ddi)
        retrieval_same_k_metrics = _metrics(
            dev_targets, retrieval_same_k_predictions, fusion_scores, ddi
        )
        base_cardinalities = tuple(len(item) for item in dev_base)
        graph_cardinalities = tuple(len(item) for item in graph_same_k_predictions)
        result["diagnostic_same_k"] = {
            "graph_logits_source": "HyperEditMR.set_head output before sequential editing",
            "GraphRefine-SameK": graph_same_k_metrics,
            "Optional retrieval-pregraph SameK": retrieval_same_k_metrics,
            "exact_molerec_cardinality_preserved": base_cardinalities == graph_cardinalities,
            "graph_refine_change": set_change_summary(dev_base, graph_same_k_predictions),
            "retrieval_pregraph_change": set_change_summary(dev_base, retrieval_same_k_predictions),
            "mean_cardinality_difference": (
                sum(
                    abs(left - right)
                    for left, right in zip(base_cardinalities, graph_cardinalities)  # noqa: B905
                )
                / len(base_cardinalities)
            ),
        }
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default="e2fee74481760a4c0691c3231101182646d77e6a")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument("--hidden-dim", type=int, default=DEFAULT_HIDDEN_DIM)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--lambda-set", type=float, default=DEFAULT_LAMBDA_SET)
    parser.add_argument("--lambda-ddi", type=float, default=DEFAULT_LAMBDA_DDI)
    parser.add_argument("--fusion-alpha", type=float, default=DEFAULT_FUSION_ALPHA)
    parser.add_argument(
        "--diagnostic-same-k",
        action="store_true",
        help="also decode graph and retrieval logits at the frozen MoleRec cardinality",
    )
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
