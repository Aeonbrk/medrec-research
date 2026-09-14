#!/usr/bin/env python3
"""Run the official HypeMed semantics on the canonical Train/Dev boundary.

The script imports the official source tree without copying it into this
repository.  ``--official-root`` points at the pinned checkout and
``--compat-root`` contains only import/runtime shims required by the existing
PyTorch 1.9 environment.  The data boundary is the only scientific adaptation:
the first 2/3 patients are Train and the existing Gate01-Dev patient hash is
the validation set.  No project Audit/test resource is loaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

GATE01_SPLIT_NAMESPACE = "idea008-gate01-v1"
DEFAULT_SEED = 20260914
DEFAULT_PRETRAIN_EPOCH = 3
DEFAULT_EPOCHS = 75
DEFAULT_BATCH_SIZE = 16
DEFAULT_EVAL_BATCH_SIZE = 1
DEFAULT_DIM = 64
DEFAULT_HEADS = 4
DEFAULT_LAYERS = 2
DEFAULT_DROPOUT = 0.3
DEFAULT_TOP_N = 10
DEFAULT_WIN_SZ = 3
DEFAULT_LR = 1e-3
DEFAULT_WEIGHT_DECAY = 1e-5
DEFAULT_MULTI_WEIGHT = 0.05
DEFAULT_DDI_WEIGHT = 0.5
DEFAULT_SSL_WEIGHT = 0.01
DEFAULT_TARGET_DDI = 0.06
DEFAULT_KP = 0.05


def gate01_dev(patient_id: int) -> bool:
    value = int.from_bytes(
        hashlib.sha256(f"{GATE01_SPLIT_NAMESPACE}:{patient_id}".encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _official_imports(official_root: Path, compat_root: Path) -> dict[str, Any]:
    """Import official modules after isolating their argparse side effect."""

    sys.path.insert(0, str(compat_root))
    sys.path.insert(0, str(official_root))
    # dataloader.py calls config.parse_args() at import time.  Keep its
    # defaults (med_sz=131, win_sz=3) while allowing this runner's arguments.
    sys.argv = [sys.argv[0]]
    import torch
    import torch.nn.functional as F
    from dataloader import MIMICDataset, collate_fn
    from graph_construction import construct_graphs
    from layers import HGTDecoder
    from layers.ehr_memory_attn import EHRMemoryAttention
    from torch.optim import Adam
    from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
    from torch.utils.data import DataLoader
    from util import multihot2idx, replace_with_padding_woken, seed_torch

    return {
        "torch": torch,
        "F": F,
        "Adam": Adam,
        "CosineAnnealingWarmRestarts": CosineAnnealingWarmRestarts,
        "DataLoader": DataLoader,
        "MIMICDataset": MIMICDataset,
        "collate_fn": collate_fn,
        "construct_graphs": construct_graphs,
        "HGTDecoder": HGTDecoder,
        "EHRMemoryAttention": EHRMemoryAttention,
        "multihot2idx": multihot2idx,
        "replace_with_padding_woken": replace_with_padding_woken,
        "seed_torch": seed_torch,
    }


def _load(path: Path, dill: Any) -> Any:
    with path.open("rb") as handle:
        return dill.load(handle)


def _idx2word(vocabulary: Any) -> list[Any]:
    values = getattr(vocabulary, "idx2word", vocabulary)
    if isinstance(values, dict):
        return [values[index] for index in sorted(values)]
    return list(values)


def _ddi_rate(labels: list[np.ndarray], ddi: np.ndarray) -> float:
    pairs = 0
    hits = 0
    for visit in labels:
        ordered = sorted(int(value) for value in visit)
        for left, first in enumerate(ordered):
            for second in ordered[left + 1 :]:
                pairs += 1
                hits += int(bool(ddi[first, second]))
    return 0.0 if pairs == 0 else hits / float(pairs)


def _average_precision(target: set[int], scores: np.ndarray) -> float:
    if not target:
        return 0.0
    ranking = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    found = 0
    total = 0.0
    for rank, index in enumerate(ranking, start=1):
        if index in target:
            found += 1
            total += found / float(rank)
    return total / float(len(target))


def metrics(targets: np.ndarray, logits: np.ndarray, ddi: np.ndarray) -> dict[str, float]:
    """Visit-macro metrics matching the project prototype surfaces."""

    if targets.shape != logits.shape or targets.ndim != 2 or targets.shape[1] != 131:
        raise ValueError("target/logit arrays must both have shape [visits, 131]")
    probabilities = 1.0 / (1.0 + np.exp(-np.asarray(logits, dtype=np.float64)))
    predictions = [np.flatnonzero(row >= 0.5) for row in probabilities]
    jaccard = 0.0
    f1 = 0.0
    prauc = 0.0
    for target_row, prediction, score_row in zip(targets, predictions, probabilities, strict=True):
        target = set(int(index) for index in np.flatnonzero(target_row > 0.5))
        predicted = set(int(index) for index in prediction)
        intersection = len(target & predicted)
        union = len(target | predicted)
        jaccard += 1.0 if union == 0 else intersection / float(union)
        precision = intersection / float(len(predicted)) if predicted else 0.0
        recall = intersection / float(len(target)) if target else 0.0
        f1 += 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)
        prauc += _average_precision(target, score_row)
    count = float(len(predictions))
    return {
        "jaccard": jaccard / count,
        "f1": f1 / count,
        "prauc": prauc / count,
        "ddi": _ddi_rate(predictions, ddi),
        "mean_medication_count": sum(len(prediction) for prediction in predictions) / count,
    }


class RetrievalAudit:
    """Collect FAISS neighbor identities from the official memory module."""

    def __init__(self, train_edge_patient: np.ndarray) -> None:
        self.train_edge_patient = train_edge_patient
        self.records: dict[str, dict[str, int]] = {
            "train": {
                "queries": 0,
                "top1_exact_self": 0,
                "top10_exact_self": 0,
                "top10_same_patient": 0,
            },
            "dev": {
                "queries": 0,
                "top1_exact_self": 0,
                "top10_exact_self": 0,
                "top10_same_patient": 0,
            },
        }

    def observe(
        self,
        split: str,
        query_edges: np.ndarray,
        query_patients: np.ndarray,
        neighbors: np.ndarray,
    ) -> None:
        if split not in self.records:
            raise ValueError(f"unknown retrieval split: {split}")
        if neighbors.shape[0] != len(query_edges):
            raise RuntimeError("official retrieval returned a different number of rows")
        stats = self.records[split]
        for query_edge, patient, row in zip(query_edges, query_patients, neighbors, strict=True):
            row = np.asarray(row, dtype=np.int64)
            stats["queries"] += 1
            stats["top1_exact_self"] += int(len(row) > 0 and int(row[0]) == int(query_edge))
            stats["top10_exact_self"] += int(np.any(row == int(query_edge)))
            valid = row[(row >= 0) & (row < len(self.train_edge_patient))]
            stats["top10_same_patient"] += int(
                len(valid) > 0 and np.any(self.train_edge_patient[valid] == int(patient))
            )

    def summary(self) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for split, stats in self.records.items():
            queries = max(1, stats["queries"])
            result[split] = {
                key: (float(value) / queries if key != "queries" else float(value))
                for key, value in stats.items()
            }
        return result


def install_retrieval_hook(EHRMemoryAttention: Any, audit: RetrievalAudit) -> None:
    original = EHRMemoryAttention.neighbour_search

    def wrapped(self: Any, visit_rep: Any, memory: Any, k: int = 10) -> Any:
        query_edges = getattr(self, "_audit_query_edges", None)
        exclude_self = bool(getattr(self, "_exclude_exact_self", False))
        search_k = k + 1 if exclude_self else k
        distances, indices = original(self, visit_rep, memory, k=search_k)
        if exclude_self:
            if query_edges is None:
                raise RuntimeError("exact-self exclusion requires query edge identities")
            torch = __import__("torch")
            if not torch.is_tensor(indices):
                indices = torch.as_tensor(indices)
            if not torch.is_tensor(distances):
                distances = torch.as_tensor(distances)
            kept_distances = []
            kept_indices = []
            for row_number, query_edge in enumerate(query_edges):
                valid = indices[row_number] != int(query_edge)
                selected_indices = indices[row_number][valid][:k]
                selected_distances = distances[row_number][valid][:k]
                if selected_indices.shape[0] != k:
                    raise RuntimeError("official retrieval returned too few non-self neighbors")
                kept_indices.append(selected_indices)
                kept_distances.append(selected_distances)
            indices = torch.stack(kept_indices, dim=0)
            distances = torch.stack(kept_distances, dim=0)
        split = getattr(self, "_audit_split", None)
        query_patients = getattr(self, "_audit_query_patients", None)
        if split is not None and query_edges is not None and query_patients is not None:
            index_array = (
                indices.detach().cpu().numpy()
                if hasattr(indices, "detach")
                else np.asarray(indices)
            )
            audit.observe(split, np.asarray(query_edges), np.asarray(query_patients), index_array)
        return distances, indices

    EHRMemoryAttention.neighbour_search = wrapped


def _prepare_batch(
    batch: Any, modules: dict[str, Any], device: Any, padding: dict[str, int]
) -> tuple[Any, ...]:
    replace = modules["replace_with_padding_woken"]
    records, masks, targets, visit2edge = batch
    records = {key: replace(value, -1, padding[key]).to(device) for key, value in records.items()}
    masks = {key: value.to(device) for key, value in masks.items()}
    targets = {key: value.to(device) for key, value in targets.items()}
    visit2edge = visit2edge.to(device)
    bsz, max_visit, _ = targets["loss_bce_target"].shape
    valid = (~masks["key_padding_mask"]).reshape(bsz * max_visit)
    return records, masks, targets, visit2edge, valid, bsz, max_visit


def _set_audit_context(
    model: Any,
    split: str,
    visit2edge: Any,
    edge_to_patient: np.ndarray,
) -> None:
    attention = model.ehr_level_attn
    edge_ids = visit2edge.detach().cpu().numpy().astype(np.int64, copy=False)
    attention._audit_split = split
    attention._audit_query_edges = edge_ids
    attention._audit_query_patients = edge_to_patient[edge_ids]


def evaluate_split(
    model: Any,
    loader: Any,
    modules: dict[str, Any],
    device: Any,
    padding: dict[str, int],
    edge_to_patient: np.ndarray,
    split: str,
    ddi: np.ndarray,
    record_audit: bool = True,
) -> tuple[dict[str, float], np.ndarray, np.ndarray]:
    torch = modules["torch"]
    outputs: list[np.ndarray] = []
    targets_out: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            records, masks, targets, visit2edge, valid, bsz, max_visit = _prepare_batch(
                batch, modules, device, padding
            )
            if record_audit:
                _set_audit_context(model, split, visit2edge, edge_to_patient)
                model.ehr_level_attn._exclude_exact_self = bool(
                    split == "train" and getattr(model, "_exclude_exact_self_control", False)
                )
            else:
                model.ehr_level_attn._audit_split = None
                model.ehr_level_attn._audit_query_edges = None
                model.ehr_level_attn._audit_query_patients = None
                model.ehr_level_attn._exclude_exact_self = False
            result, _side = model(records, masks, valid, visit2edge)
            outputs.append(result.detach().cpu().numpy())
            target = targets["loss_bce_target"].reshape(bsz * max_visit, -1)[valid]
            targets_out.append(target.detach().cpu().numpy())
    score_array = np.concatenate(outputs, axis=0)
    target_array = np.concatenate(targets_out, axis=0)
    return metrics(target_array, score_array, ddi), score_array, target_array


def _batch_ddi(labels: list[np.ndarray], ddi: np.ndarray) -> float:
    return _ddi_rate(labels, ddi)


def train_recommendation(
    model: Any,
    train_loader: Any,
    eval_loader: Any,
    modules: dict[str, Any],
    device: Any,
    padding: dict[str, int],
    train_edge_patient: np.ndarray,
    dev_edge_patient: np.ndarray,
    ddi: np.ndarray,
    ddi_path: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    torch = modules["torch"]
    F = modules["F"]
    Adam = modules["Adam"]
    Scheduler = modules["CosineAnnealingWarmRestarts"]
    multihot2idx = modules["multihot2idx"]
    optimizer = Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = Scheduler(optimizer, T_0=25, T_mult=2, eta_min=0.0)
    best_jaccard = -1.0
    best_epoch = 0
    history: list[dict[str, Any]] = []
    checkpoints = {8, 20, 40, 60, 75}

    for epoch in range(1, args.epochs + 1):
        started = time.time()
        model.train()
        losses = {"bce": 0.0, "multi": 0.0, "ddi": 0.0, "ssl": 0.0, "total": 0.0}
        steps = 0
        for batch in train_loader:
            records, masks, targets, visit2edge, valid, bsz, max_visit = _prepare_batch(
                batch, modules, device, padding
            )
            # Retrieval identities are audited in one deterministic pass after
            # training.  Avoid transferring edge ids to the host for every
            # optimization batch.
            model.ehr_level_attn._audit_split = None
            model.ehr_level_attn._audit_query_edges = None
            model.ehr_level_attn._audit_query_patients = None
            model.ehr_level_attn._exclude_exact_self = False
            if args.exclude_exact_self:
                edge_ids = visit2edge.detach().cpu().numpy().astype(np.int64, copy=False)
                model.ehr_level_attn._audit_query_edges = edge_ids
                model.ehr_level_attn._audit_query_patients = train_edge_patient[edge_ids]
                model.ehr_level_attn._exclude_exact_self = True
            result, side_loss = model(records, masks, valid, visit2edge)
            target_bce = targets["loss_bce_target"].reshape(bsz * max_visit, -1)[valid]
            target_multi = targets["loss_multi_target"].reshape(bsz * max_visit, -1)[valid]
            loss_bce = F.binary_cross_entropy_with_logits(
                result, target_bce, reduction="none"
            ).mean()
            loss_multi = (
                F.multilabel_margin_loss(
                    torch.sigmoid(result), target_multi, reduction="none"
                ).mean()
                * args.multi_weight
            )
            probabilities = torch.sigmoid(result).detach().cpu().numpy()
            labels = multihot2idx((probabilities >= 0.5).astype(np.float32))
            current_ddi = _batch_ddi(labels, ddi)
            loss_ddi = side_loss["ddi"]
            if current_ddi <= args.target_ddi:
                loss_ddi = loss_ddi * 0.0
            else:
                loss_ddi = loss_ddi * (
                    ((current_ddi - args.target_ddi) / args.kp) * args.ddi_weight
                )
            loss_ssl = side_loss["ssl"] * args.ssl_weight
            loss = loss_bce + loss_multi + loss_ssl + loss_ddi
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses["bce"] += float(loss_bce.detach().cpu())
            losses["multi"] += float(loss_multi.detach().cpu())
            losses["ddi"] += float(loss_ddi.detach().cpu())
            losses["ssl"] += float(loss_ssl.detach().cpu())
            losses["total"] += float(loss.detach().cpu())
            steps += 1
            if args.progress_steps > 0 and steps % args.progress_steps == 0:
                print(
                    json.dumps(
                        {"epoch": epoch, "step": steps, "steps_total": len(train_loader)},
                        sort_keys=True,
                    ),
                    flush=True,
                )
            if args.max_train_batches > 0 and steps >= args.max_train_batches:
                break
        scheduler.step()

        if epoch in checkpoints or epoch == args.epochs:
            dev_metrics, _scores, _targets = evaluate_split(
                model,
                eval_loader,
                modules,
                device,
                padding,
                dev_edge_patient,
                "dev",
                ddi,
                record_audit=False,
            )
            record = {
                "epoch": epoch,
                "metrics": dev_metrics,
                "loss": {key: value / max(1, steps) for key, value in losses.items()},
                "seconds": time.time() - started,
            }
            history.append(record)
            if dev_metrics["jaccard"] > best_jaccard:
                best_jaccard = dev_metrics["jaccard"]
                best_epoch = epoch
        if epoch % 5 == 0 or epoch in checkpoints or epoch == args.epochs:
            latest = history[-1]["metrics"] if history and history[-1]["epoch"] == epoch else None
            print(
                json.dumps(
                    {
                        "epoch": epoch,
                        "latest_dev": latest,
                        "loss": {key: value / max(1, steps) for key, value in losses.items()},
                        "seconds": time.time() - started,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    # A final pass after training is used for the required retrieval audit and
    # for the final aggregate metrics.  It is also the checkpoint-independent
    # surface reported by the README.
    return {
        "history": history,
        "best_epoch": best_epoch,
        "best_jaccard": best_jaccard,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    modules = _official_imports(args.official_root.resolve(), args.compat_root.resolve())
    torch = modules["torch"]
    torch.set_num_threads(args.torch_threads)
    torch.set_num_interop_threads(1)
    dill = __import__("dill")
    modules["seed_torch"](args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)

    snapshot = args.snapshot_root.resolve()
    data = _load(snapshot / "records_final.pkl", dill)
    vocabulary = _load(snapshot / "voc_final.pkl", dill)
    ddi = np.asarray(_load(snapshot / "ddi_A_final.pkl", dill), dtype=np.float32)
    if ddi.shape != (131, 131):
        raise RuntimeError("canonical DDI matrix must be 131 by 131")

    split_point = int(len(data) * 2 / 3)
    train_patient_ids = tuple(range(split_point))
    dev_patient_ids = tuple(
        patient_id for patient_id in range(split_point, len(data)) if gate01_dev(patient_id)
    )
    train_data = [data[patient_id] for patient_id in train_patient_ids]
    dev_data = [data[patient_id] for patient_id in dev_patient_ids]
    train_visits = sum(len(visits) for visits in train_data)
    dev_visits = sum(len(visits) for visits in dev_data)
    train_edge_patient = np.asarray(
        [
            patient_id
            for patient_id, visits in zip(train_patient_ids, train_data, strict=True)
            for _ in visits
        ],
        dtype=np.int64,
    )
    dev_edge_patient = np.asarray(
        [
            patient_id
            for patient_id, visits in zip(dev_patient_ids, dev_data, strict=True)
            for _ in visits
        ],
        dtype=np.int64,
    )
    if len(train_edge_patient) != train_visits or len(dev_edge_patient) != dev_visits:
        raise RuntimeError("visit-to-patient audit mapping is misaligned")

    name_lst = ("diag", "proc", "med")
    voc_size_dict = {
        "diag": len(_idx2word(vocabulary["diag_voc"])),
        "proc": len(_idx2word(vocabulary["pro_voc"])),
        "med": len(_idx2word(vocabulary["med_voc"])),
    }
    if voc_size_dict["med"] != 131:
        raise RuntimeError("canonical medication vocabulary is not 131 entries")
    idx2word_dict = {
        name: _idx2word(vocabulary[f"{name}_voc"])
        if name != "proc"
        else _idx2word(vocabulary["pro_voc"])
        for name in name_lst
    }
    idx2word_dict["diag"] = _idx2word(vocabulary["diag_voc"])
    idx2word_dict["proc"] = _idx2word(vocabulary["pro_voc"])
    idx2word_dict["med"] = _idx2word(vocabulary["med_voc"])

    adj_dict = modules["construct_graphs"](train_data, nums_dict=voc_size_dict)
    n_ehr_edges = int(adj_dict["diag"].shape[1])
    if n_ehr_edges != train_visits:
        raise RuntimeError("official graph edge count does not match Train visits")

    embedding_path = (
        args.official_root.resolve()
        / "pretrain"
        / "embed"
        / "hgt"
        / f"hgt_embed_mimic_3_{args.pretrain_epoch}.pkl"
    )
    if not embedding_path.exists():
        raise FileNotFoundError(
            f"official pretraining checkpoint is missing: {embedding_path}; run HypeMed.py --pretrain first"
        )
    result = torch.load(str(embedding_path), map_location="cpu")
    X_hat = result["X"]
    E_mem = result["E"]
    device = torch.device(f"cuda:{args.cuda}" if torch.cuda.is_available() else "cpu")
    ddi_tensor = torch.from_numpy(ddi)
    model = modules["HGTDecoder"](
        embedding_dim=args.dim,
        n_heads=args.heads,
        dropout=args.dropout,
        n_ehr_edges=n_ehr_edges,
        voc_size_dict=voc_size_dict,
        padding_dict=voc_size_dict,
        device=device,
        X_hat=X_hat,
        E_mem=E_mem,
        ddi_adj=ddi_tensor,
        channel_ablation=None,
        embed_ablation=None,
        top_n=args.top_n,
        act="relu",
    ).to(device)
    model._exclude_exact_self_control = bool(args.exclude_exact_self)

    train_set = modules["MIMICDataset"](train_data)
    dev_set = modules["MIMICDataset"](dev_data)
    train_loader = modules["DataLoader"](
        train_set,
        batch_size=args.batch_size,
        collate_fn=modules["collate_fn"],
        shuffle=False,
        pin_memory=True,
    )
    eval_loader = modules["DataLoader"](
        dev_set,
        batch_size=args.eval_batch_size,
        collate_fn=modules["collate_fn"],
        shuffle=False,
        pin_memory=True,
    )
    audit = RetrievalAudit(train_edge_patient)
    install_retrieval_hook(modules["EHRMemoryAttention"], audit)
    padding = voc_size_dict
    training = train_recommendation(
        model,
        train_loader,
        eval_loader,
        modules,
        device,
        padding,
        train_edge_patient,
        # MIMICDataset enumerates each supplied partition locally; dev edge
        # ids therefore index this local edge-to-patient table.
        dev_edge_patient,
        ddi,
        snapshot / "ddi_A_final.pkl",
        args,
    )
    final_metrics, _final_scores, _final_targets = evaluate_split(
        model,
        eval_loader,
        modules,
        device,
        padding,
        dev_edge_patient,
        "dev",
        ddi,
        record_audit=True,
    )
    # The final evaluate_split above already populated the Dev audit.  Run one
    # Train pass as the required official-memory leakage diagnostic.
    _train_metrics, _train_scores, _train_targets = evaluate_split(
        model, train_loader, modules, device, padding, train_edge_patient, "train", ddi
    )
    retrieval = audit.summary()

    result_payload: dict[str, Any] = {
        "source_revision": args.source_revision,
        "official_source": "https://github.com/xansar/HypeMed",
        "seed": args.seed,
        "device": str(device),
        "config": {
            "mimic": 3,
            "dim": args.dim,
            "heads": args.heads,
            "layers": args.layers,
            "dropout": args.dropout,
            "pretrain_epochs": args.pretrain_epoch,
            "recommendation_epochs": args.epochs,
            "batch_size": args.batch_size,
            "eval_batch_size": args.eval_batch_size,
            "learning_rate": args.lr,
            "weight_decay": args.weight_decay,
            "scheduler": "CosineAnnealingWarmRestarts(T_0=25,T_mult=2,eta_min=0)",
            "top_n": args.top_n,
            "win_sz": args.win_sz,
            "multi_weight": args.multi_weight,
            "ddi_weight": args.ddi_weight,
            "ssl_weight": args.ssl_weight,
            "target_ddi": args.target_ddi,
            "kp": args.kp,
        },
        "split": {
            "train_patients": len(train_patient_ids),
            "train_visits": train_visits,
            "dev_patients": len(dev_patient_ids),
            "dev_visits": dev_visits,
            "held_out_resources_read": False,
            "retrieval_memory": "Train-only",
        },
        "parameter_count": int(sum(parameter.numel() for parameter in model.parameters())),
        "pretraining_checkpoint": str(embedding_path),
        "retrieval_control": {
            "exclude_exact_self": bool(args.exclude_exact_self),
        },
        "recommendation": {
            "history": training["history"],
            "best_epoch": training["best_epoch"],
            "best_jaccard": training["best_jaccard"],
            "final_metrics": final_metrics,
        },
        "retrieval_audit": retrieval,
    }
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(result_payload, sort_keys=True), flush=True)
    return result_payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--compat-root", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision", default="33339ea973fd1d72908b3f6ae34b578d98fb4ba3")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--pretrain-epoch", type=int, default=DEFAULT_PRETRAIN_EPOCH)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--eval-batch-size", type=int, default=DEFAULT_EVAL_BATCH_SIZE)
    parser.add_argument("--dim", type=int, default=DEFAULT_DIM)
    parser.add_argument("--heads", type=int, default=DEFAULT_HEADS)
    parser.add_argument("--layers", type=int, default=DEFAULT_LAYERS)
    parser.add_argument("--dropout", type=float, default=DEFAULT_DROPOUT)
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--win-sz", type=int, default=DEFAULT_WIN_SZ)
    parser.add_argument("--lr", type=float, default=DEFAULT_LR)
    parser.add_argument("--weight-decay", type=float, default=DEFAULT_WEIGHT_DECAY)
    parser.add_argument("--multi-weight", type=float, default=DEFAULT_MULTI_WEIGHT)
    parser.add_argument("--ddi-weight", type=float, default=DEFAULT_DDI_WEIGHT)
    parser.add_argument("--ssl-weight", type=float, default=DEFAULT_SSL_WEIGHT)
    parser.add_argument("--target-ddi", type=float, default=DEFAULT_TARGET_DDI)
    parser.add_argument("--kp", type=float, default=DEFAULT_KP)
    parser.add_argument("--cuda", type=int, default=0)
    parser.add_argument("--torch-threads", type=int, default=8)
    parser.add_argument("--progress-steps", type=int, default=50)
    parser.add_argument("--max-train-batches", type=int, default=0)
    parser.add_argument(
        "--exclude-exact-self",
        action="store_true",
        help="matched control: exclude the query visit from Train retrieval memory",
    )
    args = parser.parse_args()
    if args.epochs <= 0 or args.batch_size <= 0 or args.eval_batch_size <= 0:
        raise SystemExit("epochs and batch sizes must be positive")
    run(args)


if __name__ == "__main__":
    main()
