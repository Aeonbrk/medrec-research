#!/usr/bin/env python3
"""Train one qualified Stage -1G external baseline on frozen Train/Dev data.

The runner is copied to the approved execution plane for the actual run.  It
keeps only aggregate metrics in the public result and writes visit-aligned
predictions to the restricted run directory for the paired bootstrap.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

MIII_SNAPSHOT = "molerec-table1-c721-www23"
MIII_TRAIN_DEV = "gate01-train-dev-5752596a-20260913a"
MIV_ROOT = "mimiciv-medrec-stage-1e-private-e87411be"
MIV_COMMON_ROOT = "mimiciv-medrec-common131-stage-1g-20260916"
SEED = 20260914


@dataclass
class Sample:
    patient: str
    key: str
    sequence: list[tuple[list[int], list[int], list[int]]]
    target: list[int]


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _gate01_dev(patient_id: int) -> bool:
    value = int.from_bytes(
        hashlib.sha256(("idea008-gate01-v1:" + str(patient_id)).encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _project(values: Iterable[Any], vocab: dict[str, int]) -> list[int]:
    return sorted({int(vocab.get(str(value), 0)) for value in values})


def _load_miii(
    root: Path, split_root: Path
) -> tuple[list[Sample], list[Sample], tuple[int, int, int], np.ndarray]:
    try:
        import dill as pickle_module
    except ImportError:
        import pickle as pickle_module

    if root.name != MIII_SNAPSHOT or split_root.name != MIII_TRAIN_DEV:
        raise RuntimeError("MIMIC-III roots do not match the frozen Stage -1F contract")
    records = pickle_module.load((root / "records_final.pkl").open("rb"))
    voc = pickle_module.load((root / "voc_final.pkl").open("rb"))
    ddi = np.asarray(pickle_module.load((root / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    med_count = len(voc["med_voc"].idx2word)
    dx_count = len(voc["diag_voc"].idx2word)
    proc_count = len(voc["pro_voc"].idx2word)
    split = int(len(records) * 2 / 3)
    train_patients = range(split)
    dev_patients = [idx for idx in range(split, len(records)) if _gate01_dev(idx)]
    if (len(records), len(dev_patients)) != (6350, 1004):
        raise RuntimeError("frozen MIMIC-III patient split counts changed")
    train: list[Sample] = []
    dev: list[Sample] = []
    for patient_index in train_patients:
        patient = records[patient_index]
        for visit_index, visit in enumerate(patient):
            sequence = [
                (list(map(int, item[0])), list(map(int, item[1])), list(map(int, item[2])))
                for item in patient[:visit_index]
            ]
            sequence.append((list(map(int, visit[0])), list(map(int, visit[1])), []))
            train.append(
                Sample(
                    str(patient_index),
                    str(patient_index) + ":" + str(visit_index),
                    sequence,
                    list(map(int, visit[2])),
                )
            )
    for patient_index in dev_patients:
        patient = records[patient_index]
        for visit_index, visit in enumerate(patient):
            sequence = [
                (list(map(int, item[0])), list(map(int, item[1])), list(map(int, item[2])))
                for item in patient[:visit_index]
            ]
            sequence.append((list(map(int, visit[0])), list(map(int, visit[1])), []))
            dev.append(
                Sample(
                    str(patient_index),
                    str(patient_index) + ":" + str(visit_index),
                    sequence,
                    list(map(int, visit[2])),
                )
            )
    if (len(train), len(dev)) != (10489, 2130):
        raise RuntimeError("frozen MIMIC-III Train/Dev visit counts changed")
    return train, dev, (dx_count, proc_count, med_count), ddi


def _validate_iv(
    example: dict[str, Any], dx: dict[str, int], proc: dict[str, int], med: dict[str, int]
) -> Sample:
    required = {
        "schema_version",
        "subject_id",
        "current_visit_order",
        "input",
        "target",
        "provenance",
    }
    if set(example) != required or int(example["schema_version"]) != 1:
        raise RuntimeError("MIMIC-IV example schema mismatch")
    inp = example["input"]
    if set(inp) != {"diagnoses", "procedures", "history"}:
        raise RuntimeError("MIMIC-IV input schema mismatch")
    target = example["target"]
    if set(target) != {"medications", "known_medications", "oov_medications"}:
        raise RuntimeError("MIMIC-IV target schema mismatch")
    provenance = example["provenance"]
    current_order = int(example["current_visit_order"])
    current_hadm = str(provenance["current_hadm_id"])
    history_ids = [str(value) for value in provenance["history_hadm_ids"]]
    if len(history_ids) != len(inp["history"]) or current_hadm in history_ids:
        raise RuntimeError("MIMIC-IV current visit appears in history")
    sequence: list[tuple[list[int], list[int], list[int]]] = []
    previous_order = -1
    for entry, hadm_id in zip(inp["history"], history_ids):  # noqa: B905 -- Python 3.8 execution env
        if str(entry["hadm_id"]) != hadm_id:
            raise RuntimeError("MIMIC-IV history provenance mismatch")
        order = int(entry["visit_order"])
        if order >= current_order or order <= previous_order:
            raise RuntimeError("MIMIC-IV history chronology invariant failed")
        previous_order = order
        history_meds = []
        for token in entry["medications"]:
            if str(token) not in med:
                raise RuntimeError("MIMIC-IV history medication is outside frozen vocabulary")
            history_meds.append(int(med[str(token)]))
        sequence.append(
            (
                _project(entry["diagnoses"], dx),
                _project(entry["procedures"], proc),
                sorted(set(history_meds)),
            )
        )
    target_tokens = [str(value) for value in target["medications"]]
    known_tokens = [str(value) for value in target["known_medications"]]
    if target["oov_medications"] or set(target_tokens) != set(known_tokens):
        raise RuntimeError("MIMIC-IV target contains an OOV medication")
    target_ids = sorted({int(med[token]) for token in known_tokens})
    sequence.append((_project(inp["diagnoses"], dx), _project(inp["procedures"], proc), []))
    return Sample(
        str(example["subject_id"]),
        str(example["subject_id"]) + ":" + str(example["current_visit_order"]),
        sequence,
        target_ids,
    )


def _load_miv(root: Path) -> tuple[list[Sample], list[Sample], tuple[int, int, int], np.ndarray]:
    if root.name not in {MIV_ROOT, MIV_COMMON_ROOT}:
        raise RuntimeError("MIMIC-IV root does not match a frozen Stage -1G identity")
    payload = json.loads((root / "vocabularies.private.json").read_text())
    ddi_payload = json.loads((root / "ddi_matrix.private.json").read_text())
    dx = {str(k): int(v) for k, v in payload["diagnosis"].items()}
    proc = {str(k): int(v) for k, v in payload["procedure"].items()}
    med = {str(k): int(v) for k, v in payload["medication"].items()}
    ddi = np.asarray(ddi_payload["matrix"], dtype=np.float32)
    if ddi.shape != (len(med), len(med)) or ddi_payload.get("vocabulary") != med:
        raise RuntimeError("MIMIC-IV DDI vocabulary/shape mismatch")
    result: list[list[Sample]] = []
    for role in ("train", "dev"):
        rows: list[Sample] = []
        with (root / f"{role}_examples.private.jsonl").open() as handle:
            for line in handle:
                rows.append(_validate_iv(json.loads(line), dx, proc, med))
        result.append(rows)
    expected = (308824, 76529) if root.name == MIV_ROOT else (308474, 76443)
    if (len(result[0]), len(result[1])) != expected:
        raise RuntimeError("frozen MIMIC-IV Train/Dev counts changed")
    return result[0], result[1], (len(dx), len(proc), len(med)), ddi


def load_data(
    dataset: str, paths: argparse.Namespace
) -> tuple[list[Sample], list[Sample], tuple[int, int, int], np.ndarray]:
    if dataset == "mimic_iii":
        return _load_miii(paths.snapshot_root.resolve(), paths.train_dev_root.resolve())
    return _load_miv(paths.iv_root.resolve())


def _batch(
    samples: Sequence[Sample], sizes: tuple[int, int, int], reverse: bool, device: torch.device
):
    dx_n, proc_n, med_n = sizes
    max_len = max(len(sample.sequence) for sample in samples)
    # Samples are sorted by sequence length; trailing zero padding is ignored by
    # the model's explicit lengths/mask path.  The medication at the current
    # position is already empty in every Sample.sequence entry.
    dx = np.zeros((len(samples), max_len, dx_n), dtype=np.float32)
    proc = np.zeros((len(samples), max_len, proc_n), dtype=np.float32)
    med = np.zeros((len(samples), max_len, med_n), dtype=np.float32)
    target = np.zeros((len(samples), med_n), dtype=np.float32)
    lengths = np.zeros(len(samples), dtype=np.int64)
    for row, sample in enumerate(samples):
        sequence = list(reversed(sample.sequence)) if reverse else sample.sequence
        lengths[row] = len(sequence)
        for col, (d, p, m) in enumerate(sequence):
            if d:
                dx[row, col, d] = 1.0
            if p:
                proc[row, col, p] = 1.0
            if m:
                med[row, col, m] = 1.0
        if sample.target:
            target[row, sample.target] = 1.0
    return (
        torch.from_numpy(dx).to(device),
        torch.from_numpy(proc).to(device),
        torch.from_numpy(med).to(device),
        torch.from_numpy(target).to(device),
        torch.from_numpy(lengths).to(device),
    )


class _GraphConvolution(nn.Module):
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(in_features, out_features))
        self.bias = nn.Parameter(torch.empty(out_features))
        stdv = 1.0 / math.sqrt(out_features)
        self.weight.data.uniform_(-stdv, stdv)
        self.bias.data.uniform_(-stdv, stdv)

    def forward(self, values: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        return adjacency.mm(values.mm(self.weight)) + self.bias


class _GCN(nn.Module):
    def __init__(self, adjacency: np.ndarray, dim: int, device: torch.device):
        super().__init__()
        n = int(adjacency.shape[0])
        matrix = np.asarray(adjacency, dtype=np.float32) + np.eye(n, dtype=np.float32)
        rows = matrix.sum(1)
        matrix = np.divide(
            matrix, rows[:, None], out=np.zeros_like(matrix), where=rows[:, None] != 0
        )
        self.register_buffer("adjacency", torch.from_numpy(matrix).to(device))
        self.register_buffer("identity", torch.eye(n, device=device))
        self.gcn1 = _GraphConvolution(n, dim)
        self.dropout = nn.Dropout(p=0.3)
        self.gcn2 = _GraphConvolution(dim, dim)

    def forward(self) -> torch.Tensor:
        values = F.relu(self.gcn1(self.identity, self.adjacency))
        return self.gcn2(self.dropout(values), self.adjacency)


class ProtocolGAMENet(nn.Module):
    """Batch-equivalent form of the official GAMENet memory computation."""

    def __init__(
        self,
        sizes: tuple[int, int, int],
        ehr: np.ndarray,
        ddi: np.ndarray,
        dim: int,
        device: torch.device,
        ddi_in_memory: bool = False,
    ):
        super().__init__()
        self.sizes = sizes
        self.device = device
        self.ddi_in_memory = ddi_in_memory
        self.embeddings = nn.ModuleList([nn.Embedding(sizes[i], dim) for i in range(2)])
        self.dropout = nn.Dropout(p=0.4)
        self.encoders = nn.ModuleList([nn.GRU(dim, dim * 2, batch_first=True) for _ in range(2)])
        self.query = nn.Sequential(nn.ReLU(), nn.Linear(dim * 4, dim))
        self.ehr_gcn = _GCN(ehr, dim, device)
        self.ddi_gcn = _GCN(ddi, dim, device)
        self.inter = nn.Parameter(torch.empty(1))
        self.output = nn.Sequential(
            nn.ReLU(), nn.Linear(dim * 3, dim * 2), nn.ReLU(), nn.Linear(dim * 2, sizes[2])
        )
        for embedding in self.embeddings:
            embedding.weight.data.uniform_(-0.1, 0.1)
        self.inter.data.uniform_(-0.1, 0.1)

    def _mean_embedding(self, values: torch.Tensor, embedding: nn.Embedding) -> torch.Tensor:
        counts = values.sum(dim=-1, keepdim=True)
        pooled = values.matmul(F.dropout(embedding.weight, p=0.4, training=self.training))
        return pooled / counts.clamp_min(1.0)

    def forward(
        self, diags: torch.Tensor, procs: torch.Tensor, meds: torch.Tensor, lengths: torch.Tensor
    ) -> torch.Tensor:
        diag_emb = self._mean_embedding(diags, self.embeddings[0])
        proc_emb = self._mean_embedding(procs, self.embeddings[1])
        diag_out, _ = self.encoders[0](self.dropout(diag_emb))
        proc_out, _ = self.encoders[1](self.dropout(proc_emb))
        queries = self.query(torch.cat([diag_out, proc_out], dim=-1))
        batch = queries.shape[0]
        query = queries[torch.arange(batch, device=self.device), lengths - 1]
        memory = self.ehr_gcn()
        if self.ddi_in_memory:
            memory = memory - self.ddi_gcn() * self.inter
        fact1 = F.softmax(query.mm(memory.t()), dim=-1).mm(memory)
        if queries.shape[1] <= 1:
            fact2 = fact1
        else:
            history_keys = queries[:, :-1, :]
            history_values = meds[:, :-1, :]
            history_count = (lengths - 1).clamp_min(0)
            mask = torch.arange(history_keys.shape[1], device=self.device).unsqueeze(
                0
            ) < history_count.unsqueeze(1)
            scores = query.unsqueeze(1).bmm(history_keys.transpose(1, 2)).squeeze(1)
            scores = scores.masked_fill(~mask, torch.finfo(scores.dtype).min)
            weights = F.softmax(scores, dim=-1)
            weights = weights * mask.float()
            denom = weights.sum(dim=-1, keepdim=True).clamp_min(1e-12)
            values = (weights / denom).unsqueeze(1).bmm(history_values).squeeze(1)
            fact2 = values.mm(memory)
            no_history = history_count == 0
            fact2 = torch.where(no_history.unsqueeze(1), fact1, fact2)
        return self.output(torch.cat([query, fact1, fact2], dim=-1))


class ProtocolRETAIN(nn.Module):
    """Batched form of the archived RETAIN implementation."""

    def __init__(self, sizes: tuple[int, int, int], dim: int, device: torch.device):
        super().__init__()
        self.sizes = sizes
        self.device = device
        dx_n, proc_n, med_n = sizes
        self.input_len = dx_n + proc_n + med_n
        self.embedding = nn.Embedding(self.input_len + 1, dim, padding_idx=self.input_len)
        self.dropout = nn.Dropout(0.3)
        self.alpha_gru = nn.GRU(dim, dim, batch_first=True)
        self.beta_gru = nn.GRU(dim, dim, batch_first=True)
        self.alpha_li = nn.Linear(dim, 1)
        self.beta_li = nn.Linear(dim, dim)
        self.output = nn.Linear(dim, med_n)

    def forward(
        self,
        diags: torch.Tensor,
        procs: torch.Tensor,
        meds: torch.Tensor,
        lengths: torch.Tensor,
    ) -> torch.Tensor:
        dx_n, proc_n, _med_n = self.sizes
        visit = self.embedding.weight[:dx_n].t().matmul(diags.transpose(1, 2)).transpose(1, 2)
        visit = visit + self.embedding.weight[dx_n : dx_n + proc_n].t().matmul(
            procs.transpose(1, 2)
        ).transpose(1, 2)
        visit = visit + self.embedding.weight[dx_n + proc_n : self.input_len].t().matmul(
            meds.transpose(1, 2)
        ).transpose(1, 2)
        visit = self.dropout(visit)
        g, _ = self.alpha_gru(visit)
        h, _ = self.beta_gru(visit)
        alpha = F.softmax(self.alpha_li(g), dim=-1)
        beta = torch.tanh(self.beta_li(h))
        context = alpha * beta * visit
        mask = torch.arange(visit.shape[1], device=self.device).unsqueeze(0) < lengths.unsqueeze(1)
        return self.output((context * mask.unsqueeze(-1).float()).sum(dim=1))


def _metrics(
    target: np.ndarray, score: np.ndarray, ddi: np.ndarray, threshold: float
) -> dict[str, float]:
    target = np.asarray(target, dtype=np.float32)
    logits = np.asarray(score, dtype=np.float32)
    probability = 1.0 / (1.0 + np.exp(-np.clip(logits, -80.0, 80.0)))
    pred = probability >= float(threshold)
    intersection = np.logical_and(target > 0.5, pred).sum(1)
    union = np.logical_or(target > 0.5, pred).sum(1)
    target_count = (target > 0.5).sum(1)
    pred_count = pred.sum(1)
    precision = np.divide(
        intersection,
        pred_count,
        out=np.zeros_like(intersection, dtype=np.float64),
        where=pred_count != 0,
    )
    recall = np.divide(
        intersection,
        target_count,
        out=np.zeros_like(intersection, dtype=np.float64),
        where=target_count != 0,
    )
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(precision),
        where=(precision + recall) != 0,
    )
    jaccard = np.divide(
        intersection, union, out=np.zeros_like(intersection, dtype=np.float64), where=union != 0
    )
    order = np.argsort(-logits, axis=1, kind="stable")
    ranked_target = np.take_along_axis(target > 0.5, order, axis=1)
    cumulative = np.cumsum(ranked_target, axis=1)
    ranks = np.arange(1, score.shape[1] + 1, dtype=np.float64)[None, :]
    ap_num = (cumulative / ranks * ranked_target).sum(1)
    prauc = np.divide(
        ap_num, target_count, out=np.zeros_like(ap_num, dtype=np.float64), where=target_count != 0
    )
    ddi_pair = np.einsum("bi,ij,bj->b", pred.astype(np.float32), ddi, pred.astype(np.float32)) / 2.0
    pair_total = pred_count * (pred_count - 1) / 2.0
    ddi_rate = np.divide(
        ddi_pair.sum(), pair_total.sum(), out=np.asarray(0.0), where=pair_total.sum() != 0
    )
    nll = np.maximum(logits, 0.0) - logits * target + np.logaddexp(0.0, -np.abs(logits))
    return {
        "jaccard": float(jaccard.mean()),
        "f1": float(f1.mean()),
        "prauc": float(prauc.mean()),
        "ddi_rate": float(ddi_rate),
        "mean_medication_count": float(pred_count.mean()),
        "nll": float(nll.mean()),
        "visit_count": float(score.shape[0]),
    }


def _ehr_from_targets(samples: Sequence[Sample], med_count: int) -> np.ndarray:
    matrix = np.zeros((med_count, med_count), dtype=np.float32)
    for sample in samples:
        meds = sample.target
        for left, med_left in enumerate(meds):
            for med_right in meds[left + 1 :]:
                matrix[med_left, med_right] = 1.0
                matrix[med_right, med_left] = 1.0
    return matrix


def _evaluate(
    model: nn.Module,
    samples: Sequence[Sample],
    sizes: tuple[int, int, int],
    baseline: str,
    device: torch.device,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    reverse = baseline == "armr"
    order = sorted(range(len(samples)), key=lambda idx: len(samples[idx].sequence))
    scores: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    patients: list[str] = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(order), batch_size):
            batch_samples = [samples[idx] for idx in order[start : start + batch_size]]
            diags, procs, meds, target, lengths = _batch(batch_samples, sizes, reverse, device)
            if baseline == "armr":
                logits = model(diags, procs, meds)
            else:
                logits = model(diags, procs, meds, lengths)
            scores.append(torch.sigmoid(logits).cpu().numpy())
            targets.append(target.cpu().numpy())
            patients.extend(sample.key for sample in batch_samples)
    return np.concatenate(targets), np.concatenate(scores), patients


def _train(args: argparse.Namespace) -> dict[str, Any]:
    seed_everything(args.seed)
    device = torch.device(
        args.device if args.device != "auto" else ("cuda:0" if torch.cuda.is_available() else "cpu")
    )
    if device.type != "cuda":
        raise RuntimeError("Stage -1G external training requires CUDA")
    train, dev, sizes, ddi = load_data(args.dataset, args)
    ehr = _ehr_from_targets(train, sizes[2])
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("output directory is not empty")
    torch.cuda.set_device(device)
    torch.cuda.reset_peak_memory_stats(device)
    if args.baseline == "armr":
        sys.path.insert(0, str(args.armr_source.resolve()))
        from net_mynet import MyNet

        model: nn.Module = MyNet(
            emb_dim=256,
            k=3,
            voc_size=sizes,
            ehr_adj=torch.tensor(ehr, dtype=torch.float32, device=device),
            ddi_adj=torch.tensor(ddi, dtype=torch.float32, device=device),
        ).to(device)
        optimizer = torch.optim.Adam(
            model.parameters(), lr=2e-4, betas=(0.9, 0.999), eps=1e-5, weight_decay=1e-6
        )
        threshold = 0.3
        epochs = (
            args.epochs if args.epochs is not None else (56 if args.dataset == "mimic_iii" else 14)
        )
    elif args.baseline == "gamenet":
        model = ProtocolGAMENet(sizes, ehr, ddi, 64, device).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=2e-4)
        threshold = 0.5
        epochs = args.epochs if args.epochs is not None else 40
    else:
        model = ProtocolRETAIN(sizes, 64, device).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=2e-4)
        threshold = 0.3
        epochs = args.epochs if args.epochs is not None else 40
    params = int(
        sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
    )
    best_state: dict[str, torch.Tensor] | None = None
    best_dev_j = -float("inf")
    best_epoch = 0
    evaluations: list[dict[str, Any]] = []
    start_time = time.time()
    rng = np.random.RandomState(args.seed)
    for epoch in range(int(epochs)):
        model.train()
        indices = rng.permutation(len(train))
        loss_sum = 0.0
        for start in range(0, len(indices), args.batch_size):
            batch_samples = [train[int(idx)] for idx in indices[start : start + args.batch_size]]
            batch_samples.sort(key=lambda item: len(item.sequence))
            diags, procs, meds, target, lengths = _batch(
                batch_samples, sizes, args.baseline == "armr", device
            )
            if args.baseline == "armr":
                logits = model(diags, procs, meds)
            else:
                logits = model(diags, procs, meds, lengths)
            if args.baseline == "gamenet":
                margin = torch.full_like(target, -1, dtype=torch.long)
                for row, sample in enumerate(batch_samples):
                    if sample.target:
                        margin[row, : len(sample.target)] = torch.tensor(
                            sample.target, dtype=torch.long, device=device
                        )
                loss = 0.9 * F.binary_cross_entropy_with_logits(
                    logits, target
                ) + 0.01 * F.multilabel_margin_loss(torch.sigmoid(logits), margin)
            else:
                loss = F.binary_cross_entropy_with_logits(logits, target)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.item()) * len(batch_samples)
        dev_target, dev_score, dev_patients = _evaluate(
            model, dev, sizes, args.baseline, device, args.eval_batch_size
        )
        dev_logits = np.log(
            np.clip(dev_score, 1e-7, 1.0 - 1e-7) / np.clip(1.0 - dev_score, 1e-7, None)
        )
        dev_metrics = _metrics(dev_target, dev_logits, ddi, threshold)
        evaluations.append(
            {"epoch": epoch + 1, "train_loss": loss_sum / len(train), "dev": dev_metrics}
        )
        print(
            json.dumps(
                {
                    "baseline": args.baseline,
                    "dataset": args.dataset,
                    "epoch": epoch + 1,
                    "dev": dev_metrics,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if dev_metrics["jaccard"] > best_dev_j + 1e-12:
            best_dev_j = dev_metrics["jaccard"]
            best_epoch = epoch + 1
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
    if best_state is None:
        raise RuntimeError("no Dev checkpoint selected")
    model.load_state_dict(best_state)
    dev_target, dev_score, dev_patients = _evaluate(
        model, dev, sizes, args.baseline, device, args.eval_batch_size
    )
    dev_logits = np.log(np.clip(dev_score, 1e-7, 1.0 - 1e-7) / np.clip(1.0 - dev_score, 1e-7, None))
    dev_metrics = _metrics(dev_target, dev_logits, ddi, threshold)
    train_target, train_score, _ = _evaluate(
        model, train, sizes, args.baseline, device, args.eval_batch_size
    )
    train_logits = np.log(
        np.clip(train_score, 1e-7, 1.0 - 1e-7) / np.clip(1.0 - train_score, 1e-7, None)
    )
    train_metrics = _metrics(train_target, train_logits, ddi, threshold)
    np.save(output / "dev_targets.npy", dev_target.astype(np.float32))
    np.save(output / "dev_logits.npy", dev_logits.astype(np.float32))
    np.save(output / "dev_patient_keys.npy", np.asarray(dev_patients, dtype="U64"))
    torch.save(best_state, output / "selected_checkpoint.pt")
    wall = time.time() - start_time
    result = {
        "schema_version": 1,
        "status": "complete",
        "stage": "STAGE -1G",
        "baseline": args.baseline,
        "dataset": args.dataset,
        "surface": "common131"
        if args.dataset == "mimic_iv" and args.iv_root.name == MIV_COMMON_ROOT
        else "native173"
        if args.dataset == "mimic_iv"
        else "canonical131",
        "source_revision": args.source_revision,
        "dataset_sizes": {"diagnosis": sizes[0], "procedure": sizes[1], "medication": sizes[2]},
        "config": {
            "seed": args.seed,
            "batch_size": args.batch_size,
            "eval_batch_size": args.eval_batch_size,
            "epochs": epochs,
            "optimizer": "Adam(lr=2e-4, betas=(0.9,0.999), eps=1e-5, weight_decay=1e-6)"
            if args.baseline == "armr"
            else "Adam(lr=2e-4)",
            "loss": "BCEWithLogitsLoss"
            if args.baseline in {"armr", "retain"}
            else "0.9*BCE + 0.01*multilabel_margin",
            "threshold": threshold,
            "checkpoint_rule": "best Dev Jaccard",
            "ehr_graph": "Train target co-occurrence only",
            "ddi_graph": "frozen dataset DDI matrix",
        },
        "parameter_count": params,
        "best_epoch": best_epoch,
        "metrics": {"Train": train_metrics, "Dev": dev_metrics},
        "evaluations": evaluations,
        "resource": {
            "wall_time_seconds": wall,
            "peak_gpu_memory_mb": float(torch.cuda.max_memory_allocated(device) / 1048576.0),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
        },
        "test_loaded": False,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", choices=("armr", "gamenet", "retain"), required=True)
    parser.add_argument("--dataset", choices=("mimic_iii", "mimic_iv"), required=True)
    parser.add_argument("--snapshot-root", type=Path)
    parser.add_argument("--train-dev-root", type=Path)
    parser.add_argument("--iv-root", type=Path)
    parser.add_argument("--armr-source", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--eval-batch-size", type=int, default=256)
    parser.add_argument("--epochs", type=int)
    args = parser.parse_args(argv)
    if args.dataset == "mimic_iii" and (args.snapshot_root is None or args.train_dev_root is None):
        parser.error("MIMIC-III requires --snapshot-root and --train-dev-root")
    if args.dataset == "mimic_iv" and args.iv_root is None:
        parser.error("MIMIC-IV requires --iv-root")
    return args


if __name__ == "__main__":
    _train(parse_args())
