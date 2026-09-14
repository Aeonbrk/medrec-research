#!/usr/bin/env python3
"""Run the bounded HypeMed -> HypeInteract Train/Gate01-Dev screen.

The runner intentionally materializes only the canonical Train and Gate01-Dev
partitions.  It is suitable for the existing ``medrec-molerec-table1`` Conda
environment on 319 and writes its JSON result to a caller-supplied scratch
path; no patient-level predictions or model weights belong in Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch

try:
    from hypeinteract import (
        CANDIDATE_COUNT,
        DEFAULT_DIM,
        DEFAULT_DROPOUT,
        DEFAULT_HEADS,
        DEFAULT_HISTORY_WINDOW,
        DEFAULT_LAYERS,
        DEFAULT_RETRIEVAL_K,
        HypeMedScorer,
        HypergraphEncoder,
        PatientConditionedInteraction,
        build_domain_hypergraph,
        build_knowledge_bias,
        build_visit_examples,
        contrastive_pretrain_step,
        evaluate_sets,
        set_change_summary,
        threshold_sets,
        topk_sets,
    )
except ModuleNotFoundError:  # Running this file directly from the prototype directory.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hypeinteract import (
        CANDIDATE_COUNT,
        DEFAULT_DIM,
        DEFAULT_DROPOUT,
        DEFAULT_HEADS,
        DEFAULT_HISTORY_WINDOW,
        DEFAULT_LAYERS,
        DEFAULT_RETRIEVAL_K,
        HypeMedScorer,
        HypergraphEncoder,
        PatientConditionedInteraction,
        build_domain_hypergraph,
        build_knowledge_bias,
        build_visit_examples,
        contrastive_pretrain_step,
        evaluate_sets,
        set_change_summary,
        threshold_sets,
        topk_sets,
    )


GATE01_SPLIT_NAMESPACE = "idea008-gate01-v1"
DEFAULT_SOURCE_REVISION = "33339ea973fd1d72908b3f6ae34b578d98fb4ba3"
DEFAULT_SEED = 20260914
DEFAULT_PRETRAIN_EPOCHS = 3
DEFAULT_RECOMMENDATION_EPOCHS = 8
DEFAULT_BATCH_SIZE = 128
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_WEIGHT_DECAY = 1e-5
DEFAULT_DDI_WEIGHT = 0.05


def gate01_dev(patient_id: int) -> bool:
    """Return the existing Gate01-Dev half split for a patient index."""

    value = int.from_bytes(
        hashlib.sha256(f"{GATE01_SPLIT_NAMESPACE}:{patient_id}".encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _load_array(root: Path, name: str) -> np.ndarray:
    return np.array(np.load(root / name, mmap_mode="r"), dtype=np.float32, copy=True)


def _idx2word(vocabulary: Any) -> list[Any]:
    values = getattr(vocabulary, "idx2word", vocabulary)
    if isinstance(values, dict):
        return [values[index] for index in sorted(values)]
    return list(values)


def _assert_alignment(examples: Sequence[Any], targets: np.ndarray) -> None:
    if len(examples) != targets.shape[0]:
        raise RuntimeError("record order does not align with the frozen MoleRec target array")
    for row, example in enumerate(examples):
        expected = set(int(value) for value in example.target_medications)
        observed = set(int(index) for index in np.flatnonzero(targets[row] > 0.5))
        if expected != observed:
            raise RuntimeError(f"target mismatch at visit row {row}")


def _batch_tensor(array: np.ndarray, rows: np.ndarray, device: torch.device) -> torch.Tensor:
    return torch.from_numpy(np.ascontiguousarray(array[rows])).to(device=device)


def _event_matrix(
    node_embeddings: np.ndarray,
    examples: Sequence[Any],
    attribute: str,
) -> np.ndarray:
    """Mean-pool current-event nodes, matching HypeMed's node-to-edge channel."""

    result = np.zeros((len(examples), node_embeddings.shape[1]), dtype=np.float32)
    for row, example in enumerate(examples):
        codes = getattr(example, attribute)
        if not codes:
            continue
        indices = np.asarray(sorted(set(int(value) for value in codes)), dtype=np.int64)
        indices = np.clip(indices, 0, node_embeddings.shape[0] - 1)
        result[row] = node_embeddings[indices].mean(axis=0)
    return result


def _history_matrix(med_event: np.ndarray, examples: Sequence[Any]) -> np.ndarray:
    result = np.zeros((len(examples), med_event.shape[1]), dtype=np.float32)
    for row, example in enumerate(examples):
        indices = tuple(
            int(value) for value in example.prior_visit_indices[-DEFAULT_HISTORY_WINDOW:]
        )
        if indices:
            result[row] = med_event[list(indices)].mean(axis=0)
    return result


def _historical_indicator(examples: Sequence[Any]) -> np.ndarray:
    result = np.zeros((len(examples), CANDIDATE_COUNT), dtype=np.float32)
    for row, example in enumerate(examples):
        for medication in example.historical_medications:
            if 0 <= int(medication) < CANDIDATE_COUNT:
                result[row, int(medication)] = 1.0
    return result


def _retrieval_channels(
    query_health: np.ndarray,
    query_examples: Sequence[Any],
    train_health: np.ndarray,
    train_med_event: np.ndarray,
    train_examples: Sequence[Any],
    *,
    top_k: int,
) -> tuple[np.ndarray, tuple[tuple[int, ...], ...]]:
    """Retrieve medication visit evidence from Train-only, other-patient visits."""

    if top_k <= 0:
        raise ValueError("retrieval K must be positive")
    query = query_health / np.maximum(np.linalg.norm(query_health, axis=1, keepdims=True), 1e-6)
    memory = train_health / np.maximum(np.linalg.norm(train_health, axis=1, keepdims=True), 1e-6)
    similarities = query @ memory.T
    patient_ids = np.asarray(
        [int(example.patient_id) for example in train_examples], dtype=np.int64
    )
    output = np.zeros((len(query_examples), train_med_event.shape[1]), dtype=np.float32)
    neighbors: list[tuple[int, ...]] = []
    for row, example in enumerate(query_examples):
        scores = similarities[row].copy()
        scores[patient_ids == int(example.patient_id)] = -np.inf
        ranked = np.argsort(-scores, kind="mergesort")
        selected = tuple(
            int(value) for value in ranked[: min(top_k, len(ranked))] if np.isfinite(scores[value])
        )
        neighbors.append(selected)
        if not selected:
            continue
        selected_scores = scores[list(selected)]
        # A temperature close to the official EHR-memory attention keeps the
        # channel smooth while still emphasizing the closest visits.
        weights = np.exp((selected_scores - np.max(selected_scores)) / 0.10)
        weights /= np.maximum(weights.sum(), 1e-6)
        output[row] = weights.astype(np.float32) @ train_med_event[list(selected)]
    return output, tuple(neighbors)


def _train_pretrainer(
    encoders: dict[str, Any],
    domains: dict[str, Any],
    *,
    epochs: int,
    seed: int,
    device: torch.device,
) -> dict[str, dict[str, float]]:
    optimizers = {
        name: torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-5)
        for name, model in encoders.items()
    }
    history: dict[str, dict[str, float]] = {}
    for epoch in range(epochs):
        for name in ("diag", "proc", "med"):
            torch.manual_seed(seed + epoch * 17 + len(name))
            model = encoders[name]
            optimizer = optimizers[name]
            optimizer.zero_grad(set_to_none=True)
            loss, detail = contrastive_pretrain_step(
                model,
                domains[name].incidence.to(device=device),
                drop_incidence_rate=0.4,
                drop_feature_rate=0.4,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            history[name] = detail
    return history


def _encode_domains(
    encoders: dict[str, Any], domains: dict[str, Any], device: torch.device
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    node_embeddings: dict[str, np.ndarray] = {}
    edge_embeddings: dict[str, np.ndarray] = {}
    with torch.no_grad():
        for name in ("diag", "proc", "med"):
            nodes, edges = encoders[name](domains[name].incidence.to(device=device))
            node_embeddings[name] = nodes.detach().cpu().numpy().astype(np.float32)
            edge_embeddings[name] = edges.detach().cpu().numpy().astype(np.float32)
    return node_embeddings, edge_embeddings


def _make_channels(
    examples: Sequence[Any],
    node_embeddings: dict[str, np.ndarray],
    train_examples: Sequence[Any],
    train_node_embeddings: dict[str, np.ndarray],
    *,
    top_k: int,
) -> dict[str, Any]:
    current_diag = _event_matrix(node_embeddings["diag"], examples, "diagnoses")
    current_proc = _event_matrix(node_embeddings["proc"], examples, "procedures")
    current_context = 0.5 * (current_diag + current_proc)
    med_current = _event_matrix(node_embeddings["med"], examples, "target_medications")
    history = _history_matrix(med_current, examples)

    train_diag = _event_matrix(train_node_embeddings["diag"], train_examples, "diagnoses")
    train_proc = _event_matrix(train_node_embeddings["proc"], train_examples, "procedures")
    train_health = 0.5 * (train_diag + train_proc)
    train_med_event = _event_matrix(
        train_node_embeddings["med"], train_examples, "target_medications"
    )
    retrieval, neighbors = _retrieval_channels(
        current_context,
        examples,
        train_health,
        train_med_event,
        train_examples,
        top_k=top_k,
    )
    return {
        "context": current_context.astype(np.float32),
        "history": history.astype(np.float32),
        "retrieval": retrieval.astype(np.float32),
        "train_health": train_health.astype(np.float32),
        "train_med_event": train_med_event.astype(np.float32),
        "neighbors": neighbors,
        "med_current": med_current.astype(np.float32),
    }


def _train_scorer(
    model: Any,
    channels: dict[str, np.ndarray],
    targets: np.ndarray,
    ddi: np.ndarray,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    device: torch.device,
    ddi_weight: float,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=DEFAULT_LEARNING_RATE, weight_decay=DEFAULT_WEIGHT_DECAY
    )
    model.train()
    last = {"bce": 0.0, "ddi": 0.0, "total": 0.0}
    for _ in range(epochs):
        order = rng.permutation(len(targets))
        totals = {"bce": 0.0, "ddi": 0.0, "total": 0.0}
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            context = _batch_tensor(channels["context"], rows, device)
            history = _batch_tensor(channels["history"], rows, device)
            retrieval = _batch_tensor(channels["retrieval"], rows, device)
            target = _batch_tensor(targets, rows, device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(context, history, retrieval)
            bce = torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
            probabilities = torch.sigmoid(logits)
            ddi_tensor = torch.from_numpy(ddi).to(device=device, dtype=logits.dtype)
            pair_probability = probabilities.unsqueeze(2) * probabilities.unsqueeze(1)
            ddi_loss = (pair_probability * ddi_tensor.unsqueeze(0)).mean()
            loss = bce + float(ddi_weight) * ddi_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            totals["bce"] += float(bce.detach().cpu())
            totals["ddi"] += float(ddi_loss.detach().cpu())
            totals["total"] += float(loss.detach().cpu())
            batches += 1
        last = {key: value / max(1, batches) for key, value in totals.items()}
    return last


def _predict_scorer(
    model: Any, channels: dict[str, np.ndarray], *, batch_size: int, device: torch.device
) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    logits_parts: list[np.ndarray] = []
    context_parts: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(channels["context"]), batch_size):
            stop = min(start + batch_size, len(channels["context"]))
            rows = np.arange(start, stop, dtype=np.int64)
            context = _batch_tensor(channels["context"], rows, device)
            history = _batch_tensor(channels["history"], rows, device)
            retrieval = _batch_tensor(channels["retrieval"], rows, device)
            logits_parts.append(model(context, history, retrieval).cpu().numpy())
            context_parts.append(model.fuse_channels(context, history, retrieval).cpu().numpy())
    return np.concatenate(logits_parts, axis=0), np.concatenate(context_parts, axis=0)


def _interaction_train(
    model: Any,
    patient_context: np.ndarray,
    base_logits: np.ndarray,
    historical_indicator: np.ndarray,
    targets: np.ndarray,
    ehr: np.ndarray,
    ddi: np.ndarray,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    device: torch.device,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=DEFAULT_LEARNING_RATE, weight_decay=DEFAULT_WEIGHT_DECAY
    )
    ehr_tensor = torch.from_numpy(ehr).to(device=device)
    ddi_tensor = torch.from_numpy(ddi).to(device=device)
    last = {"bce": 0.0, "total": 0.0}
    model.train()
    for _ in range(epochs):
        totals = {"bce": 0.0, "total": 0.0}
        order = rng.permutation(len(targets))
        batches = 0
        for start in range(0, len(order), batch_size):
            rows = order[start : start + batch_size]
            context = _batch_tensor(patient_context, rows, device)
            logits = _batch_tensor(base_logits, rows, device)
            history = _batch_tensor(historical_indicator, rows, device)
            target = _batch_tensor(targets, rows, device)
            optimizer.zero_grad(set_to_none=True)
            output = model(context, logits, history, ehr_tensor, ddi_tensor)
            bce = torch.nn.functional.binary_cross_entropy_with_logits(output, target)
            bce.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            totals["bce"] += float(bce.detach().cpu())
            totals["total"] += float(bce.detach().cpu())
            batches += 1
        last = {key: value / max(1, batches) for key, value in totals.items()}
    return last


def _predict_interaction(
    model: Any,
    patient_context: np.ndarray,
    base_logits: np.ndarray,
    historical_indicator: np.ndarray,
    ehr: np.ndarray,
    ddi: np.ndarray,
    *,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    model.eval()
    ehr_tensor = torch.from_numpy(ehr).to(device=device)
    ddi_tensor = torch.from_numpy(ddi).to(device=device)
    parts: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(base_logits), batch_size):
            stop = min(start + batch_size, len(base_logits))
            rows = np.arange(start, stop, dtype=np.int64)
            output = model(
                _batch_tensor(patient_context, rows, device),
                _batch_tensor(base_logits, rows, device),
                _batch_tensor(historical_indicator, rows, device),
                ehr_tensor,
                ddi_tensor,
            )
            parts.append(output.cpu().numpy())
    return np.concatenate(parts, axis=0)


def _metrics(
    targets: np.ndarray, predictions: Sequence[Iterable[int]], scores: np.ndarray, ddi: np.ndarray
) -> dict[str, float]:
    return evaluate_sets(targets, predictions, scores, ddi)


def run(args: argparse.Namespace) -> dict[str, Any]:
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    snapshot = args.snapshot_root.resolve()
    train_dev_root = args.train_dev_root.resolve()
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    vocabulary = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    ehr = np.asarray(dill.load((snapshot / "ehr_adj_final.pkl").open("rb")), dtype=np.float32)
    if ddi.shape != (CANDIDATE_COUNT, CANDIDATE_COUNT) or ehr.shape != ddi.shape:
        raise RuntimeError("canonical DDI/EHR matrices must both be 131 by 131")
    ehr = np.maximum(ehr, 0.0)
    np.fill_diagonal(ehr, 0.0)
    if float(ehr.max()) > 0.0:
        ehr /= float(ehr.max())

    split_point = int(len(records) * 2 / 3)
    train_patient_indices = tuple(range(split_point))
    dev_patient_indices = tuple(
        patient_id for patient_id in range(split_point, len(records)) if gate01_dev(patient_id)
    )
    train_examples = build_visit_examples(records, train_patient_indices)
    dev_examples = build_visit_examples(records, dev_patient_indices)
    train_targets = _load_array(train_dev_root, "train_targets.npy")
    dev_targets = _load_array(train_dev_root, "dev_targets.npy")
    train_scores = _load_array(train_dev_root, "train_scores.npy")
    dev_scores = _load_array(train_dev_root, "dev_scores.npy")
    for name, values in (
        ("train_targets", train_targets),
        ("dev_targets", dev_targets),
        ("train_scores", train_scores),
        ("dev_scores", dev_scores),
    ):
        if values.ndim != 2 or values.shape[1] != CANDIDATE_COUNT:
            raise RuntimeError(name + " does not have shape [visits, 131]")
    _assert_alignment(train_examples, train_targets)
    _assert_alignment(dev_examples, dev_targets)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    num_nodes = {
        "diag": len(_idx2word(vocabulary["diag_voc"])),
        "proc": len(_idx2word(vocabulary["pro_voc"])),
        "med": CANDIDATE_COUNT,
    }
    labels = {
        "diag": _idx2word(vocabulary["diag_voc"]),
        "proc": _idx2word(vocabulary["pro_voc"]),
        "med": _idx2word(vocabulary["med_voc"]),
    }
    domains = {
        name: build_domain_hypergraph(
            records,
            train_patient_indices,
            domain=name,
            num_nodes=num_nodes[name],
        )
        for name in ("diag", "proc", "med")
    }
    encoders = {
        name: HypergraphEncoder(
            num_nodes[name],
            len(train_examples),
            dim=DEFAULT_DIM,
            heads=DEFAULT_HEADS,
            layers=DEFAULT_LAYERS,
            dropout=DEFAULT_DROPOUT,
            knowledge_bias=build_knowledge_bias(labels[name]),
        ).to(device)
        for name in ("diag", "proc", "med")
    }
    pretrain_losses = _train_pretrainer(
        encoders,
        domains,
        epochs=args.pretrain_epochs,
        seed=args.seed,
        device=device,
    )
    node_embeddings, edge_embeddings = _encode_domains(encoders, domains, device)

    train_channels = _make_channels(
        train_examples,
        node_embeddings,
        train_examples,
        node_embeddings,
        top_k=args.retrieval_k,
    )
    dev_channels = _make_channels(
        dev_examples,
        node_embeddings,
        train_examples,
        node_embeddings,
        top_k=args.retrieval_k,
    )
    scorer = HypeMedScorer(
        torch.from_numpy(node_embeddings["med"]), dim=DEFAULT_DIM, dropout=DEFAULT_DROPOUT
    ).to(device)
    recommendation_loss = _train_scorer(
        scorer,
        train_channels,
        train_targets,
        ddi,
        epochs=args.recommendation_epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        device=device,
        ddi_weight=args.ddi_weight,
    )
    dev_logits, dev_context = _predict_scorer(
        scorer, dev_channels, batch_size=args.batch_size, device=device
    )
    train_logits, _ = _predict_scorer(
        scorer, train_channels, batch_size=args.batch_size, device=device
    )
    hype_predictions = threshold_sets(dev_logits)
    hype_cardinalities = tuple(len(item) for item in hype_predictions)
    hype_same_k = topk_sets(dev_logits, hype_cardinalities)
    stage_a_metrics = {
        "HypeMed": _metrics(dev_targets, hype_predictions, dev_logits, ddi),
        "HypeMed-SameK": _metrics(dev_targets, hype_same_k, dev_logits, ddi),
    }
    # The split's medication targets are used only as labels.  Retrieval memory
    # is explicitly built from Train examples and excludes the query patient.
    retrieval_train_only = all(
        all(train_examples[index].patient_id != example.patient_id for index in neighbors)
        for example, neighbors in zip(train_examples, train_channels["neighbors"])  # noqa: B905
    ) and all(
        all(train_examples[index].patient_id != example.patient_id for index in neighbors)
        for example, neighbors in zip(dev_examples, dev_channels["neighbors"])  # noqa: B905
    )

    model_parameters = sum(
        int(parameter.numel()) for model in encoders.values() for parameter in model.parameters()
    ) + sum(int(parameter.numel()) for parameter in scorer.parameters())
    result: dict[str, Any] = {
        "working_name": "HypeInteract",
        "source_revision": args.source_revision,
        "official_source": "https://github.com/xansar/HypeMed",
        "device": str(device),
        "seed": args.seed,
        "config": {
            "dim": DEFAULT_DIM,
            "heads": DEFAULT_HEADS,
            "layers": DEFAULT_LAYERS,
            "dropout": DEFAULT_DROPOUT,
            "pretrain_epochs": args.pretrain_epochs,
            "recommendation_epochs": args.recommendation_epochs,
            "batch_size": args.batch_size,
            "learning_rate": DEFAULT_LEARNING_RATE,
            "weight_decay": DEFAULT_WEIGHT_DECAY,
            "retrieval_k": args.retrieval_k,
            "history_window": DEFAULT_HISTORY_WINDOW,
            "ddi_weight": args.ddi_weight,
        },
        "split": {
            "train_patients": len(train_patient_indices),
            "train_visits": len(train_examples),
            "dev_patients": len(dev_patient_indices),
            "dev_visits": len(dev_examples),
            "held_out_resources_read": False,
        },
        "retrieval": {
            "train_only": bool(retrieval_train_only),
            "same_patient_excluded": bool(retrieval_train_only),
            "top_k": args.retrieval_k,
        },
        "parameter_count": model_parameters,
        "pretrain_losses": pretrain_losses,
        "recommendation_loss": recommendation_loss,
        "stage_a": {
            "metrics": stage_a_metrics,
            "node_embeddings": {key: list(value.shape) for key, value in node_embeddings.items()},
            "edge_embeddings": {key: list(value.shape) for key, value in edge_embeddings.items()},
        },
    }
    stage_a = stage_a_metrics["HypeMed"]
    stage_a_pass = bool(
        stage_a["jaccard"] >= 0.540 and stage_a["prauc"] >= 0.73 and stage_a["ddi"] <= 0.12
    )
    result["stage_a"]["decision"] = (
        "HYPEMED_BACKBONE_HEALTHY" if stage_a_pass else "STOP_HYPEMED_BACKBONE_RESET"
    )
    if not stage_a_pass:
        result["decision"] = "STOP_HYPEMED_BACKBONE_RESET"
    else:
        historical_train = _historical_indicator(train_examples)
        historical_dev = _historical_indicator(dev_examples)
        interaction = PatientConditionedInteraction(
            torch.from_numpy(node_embeddings["med"]), dim=DEFAULT_DIM, hidden_dim=96
        ).to(device)
        _interaction_train(
            interaction,
            _predict_scorer(scorer, train_channels, batch_size=args.batch_size, device=device)[1],
            train_logits,
            historical_train,
            train_targets,
            ehr,
            ddi,
            epochs=args.recommendation_epochs,
            batch_size=args.batch_size,
            seed=args.seed,
            device=device,
        )
        interaction_logits = _predict_interaction(
            interaction,
            dev_context,
            dev_logits,
            historical_dev,
            ehr,
            ddi,
            batch_size=args.batch_size,
            device=device,
        )
        interaction_same_k = topk_sets(interaction_logits, hype_cardinalities)
        stage_b_metrics = {
            "HypeMed-SameK": stage_a_metrics["HypeMed-SameK"],
            "HypeInteract-SameK": _metrics(
                dev_targets, interaction_same_k, interaction_logits, ddi
            ),
            "HypeInteract": _metrics(
                dev_targets, threshold_sets(interaction_logits), interaction_logits, ddi
            ),
        }
        change = set_change_summary(hype_same_k, interaction_same_k)
        interaction_same = stage_b_metrics["HypeInteract-SameK"]
        baseline_same = stage_b_metrics["HypeMed-SameK"]
        jaccard_gain = interaction_same["jaccard"] - baseline_same["jaccard"]
        ddi_gain = interaction_same["ddi"] - baseline_same["ddi"]
        stage_b_pass = bool(jaccard_gain >= 0.005 or (jaccard_gain >= 0.003 and ddi_gain <= -0.005))
        result["stage_b"] = {
            "metrics": stage_b_metrics,
            "set_change": change,
            "jaccard_gain": jaccard_gain,
            "ddi_gain": ddi_gain,
            "decision": "SURVIVE_HYPEINTERACT"
            if stage_b_pass
            else "STOP_INTERACTION_NOT_GENERALIZABLE",
        }
        result["decision"] = result["stage_b"]["decision"]
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
    parser.add_argument("--source-revision", default=DEFAULT_SOURCE_REVISION)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--pretrain-epochs", type=int, default=DEFAULT_PRETRAIN_EPOCHS)
    parser.add_argument("--recommendation-epochs", type=int, default=DEFAULT_RECOMMENDATION_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--retrieval-k", type=int, default=DEFAULT_RETRIEVAL_K)
    parser.add_argument("--ddi-weight", type=float, default=DEFAULT_DDI_WEIGHT)
    args = parser.parse_args()
    if args.pretrain_epochs <= 0 or args.recommendation_epochs <= 0 or args.batch_size <= 0:
        raise SystemExit("epoch and batch-size arguments must be positive")
    result = run(args)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
