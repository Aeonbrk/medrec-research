#!/usr/bin/env python3
"""Run the pinned MoleRec model on the common-131 Train/Dev surfaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

SOURCE_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"
MIII_SNAPSHOT = "molerec-table1-c721-www23"
MIII_TRAIN_DEV = "gate01-train-dev-5752596a-20260913a"
MIV_COMMON_ROOT = "mimiciv-medrec-common131-stage-1g-20260916"
SEED = 1203
MEDICATIONS = 131
EMB_DIM = 64
DROPOUT = 0.7
LEARNING_RATE = 5e-4
COEF = 2.5
TARGET_DDI = 0.06
EPOCHS = 50
BATCH_SIZE = 32
EVAL_BATCH_SIZE = 128
THRESHOLD = 0.5


@dataclass
class Sample:
    key: str
    sequence: list[tuple[list[int], list[int], list[int]]]
    target: list[int]


class ListDataset:
    def __init__(self, samples: list[Sample]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def get_batch(self, indices: list[int]) -> list[Sample]:
        return [self.samples[int(index)] for index in indices]

    def close(self) -> None:
        return None


class JsonlDataset:
    def __init__(self, root: Path, role: str, dx: dict[str, int], proc: dict[str, int], med: dict[str, int]):
        self.root = root
        self.path = root / (role + "_examples.private.jsonl")
        self.offsets = np.asarray(
            np.load(str(root / (role + "_examples.private.offsets.npy")), allow_pickle=False),
            dtype=np.int64,
        )
        self.dx = dx
        self.proc = proc
        self.med = med
        self.handle = self.path.open("rb")

    def __len__(self) -> int:
        return int(self.offsets.shape[0])

    def get_batch(self, indices: list[int]) -> list[Sample]:
        output = []
        for index in indices:
            self.handle.seek(int(self.offsets[int(index)]))
            example = json.loads(self.handle.readline().decode("utf-8"))
            inp = example["input"]
            target = example["target"]
            target_ids = sorted({int(self.med[str(token)]) for token in target["medications"]})
            history = []
            for entry in inp["history"]:
                history.append(
                    (
                        sorted({int(self.dx[str(token)]) for token in entry["diagnoses"]}),
                        sorted({int(self.proc[str(token)]) for token in entry["procedures"]}),
                        sorted({int(self.med[str(token)]) for token in entry["medications"]}),
                    )
                )
            history.append(
                (
                    sorted({int(self.dx[str(token)]) for token in inp["diagnoses"]}),
                    sorted({int(self.proc[str(token)]) for token in inp["procedures"]}),
                    [],
                )
            )
            key = str(example["subject_id"]) + ":" + str(example["current_visit_order"])
            output.append(Sample(key, history, target_ids))
        return output

    def close(self) -> None:
        self.handle.close()


def _gate01_dev(patient_id: int) -> bool:
    value = int.from_bytes(
        hashlib.sha256(("idea008-gate01-v1:" + str(patient_id)).encode()).digest()[:8], "big"
    )
    return value / float(2**64) < 0.5


def _load_miii(snapshot: Path) -> tuple[ListDataset, ListDataset, int, int, np.ndarray, list[str]]:
    import dill

    if snapshot.name != MIII_SNAPSHOT:
        raise RuntimeError("MIMIC-III snapshot identity mismatch")
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    med_order = [str(voc["med_voc"].idx2word[index]) for index in range(MEDICATIONS)]
    split = int(len(records) * 2 / 3)
    dev_patients = [index for index in range(split, len(records)) if _gate01_dev(index)]
    train, dev = [], []
    for patient_index in range(split):
        history = []
        for visit_index, visit in enumerate(records[patient_index]):
            sequence = [*history, (
                (list(map(int, visit[0])), list(map(int, visit[1])), [])
            )]
            train.append(Sample(str(patient_index) + ":" + str(visit_index), sequence, list(map(int, visit[2]))))
            history.append((list(map(int, visit[0])), list(map(int, visit[1])), list(map(int, visit[2]))))
    for patient_index in dev_patients:
        history = []
        for visit_index, visit in enumerate(records[patient_index]):
            sequence = [*history, (
                (list(map(int, visit[0])), list(map(int, visit[1])), [])
            )]
            dev.append(Sample(str(patient_index) + ":" + str(visit_index), sequence, list(map(int, visit[2]))))
            history.append((list(map(int, visit[0])), list(map(int, visit[1])), list(map(int, visit[2]))))
    if (len(records), len(train), len(dev)) != (6350, 10489, 2130):
        raise RuntimeError("MIMIC-III common131 Train/Dev counts changed")
    return ListDataset(train), ListDataset(dev), len(voc["diag_voc"].idx2word), len(voc["pro_voc"].idx2word), ddi, med_order


def _load_miv(root: Path) -> tuple[JsonlDataset, JsonlDataset, int, int, np.ndarray, list[str]]:
    if root.name != MIV_COMMON_ROOT:
        raise RuntimeError("MIMIC-IV common131 root identity mismatch")
    payload = json.loads((root / "vocabularies.private.json").read_text(encoding="utf-8"))
    dx = {str(key): int(value) for key, value in payload["diagnosis"].items()}
    proc = {str(key): int(value) for key, value in payload["procedure"].items()}
    med = {str(key): int(value) for key, value in payload["medication"].items()}
    ddi_payload = json.loads((root / "ddi_matrix.private.json").read_text(encoding="utf-8"))
    ddi = np.asarray(ddi_payload["matrix"], dtype=np.float32)
    if len(med) != MEDICATIONS or ddi.shape != (MEDICATIONS, MEDICATIONS):
        raise RuntimeError("MIMIC-IV common131 medication/DDI shape changed")
    med_order = [code for code, _index in sorted(med.items(), key=lambda item: item[1])]
    train = JsonlDataset(root, "train", dx, proc, med)
    dev = JsonlDataset(root, "dev", dx, proc, med)
    if (len(train), len(dev)) != (308474, 76443):
        raise RuntimeError("MIMIC-IV common131 Train/Dev counts changed")
    return train, dev, len(dx), len(proc), ddi, med_order


def _load_samples(dataset: str, args: argparse.Namespace):
    if dataset == "mimic_iii":
        return _load_miii(args.snapshot_root.resolve())
    return _load_miv(args.common_root.resolve())


def _build_batch(samples: list[Sample], model: torch.nn.Module, device: torch.device):
    ordered = sorted(enumerate(samples), key=lambda pair: len(pair[1].sequence), reverse=True)
    positions = [position for position, _sample in ordered]
    values = [sample for _position, sample in ordered]
    lengths = torch.tensor([len(sample.sequence) for sample in values], dtype=torch.long)
    batch_size = len(values)
    width = int(lengths.max().item())
    dim = EMB_DIM
    dx_flat, dx_rows, proc_flat, proc_rows = [], [], [], []
    for row, sample in enumerate(values):
        for col, (diagnoses, procedures, _medications) in enumerate(sample.sequence):
            visit_id = row * width + col
            dx_flat.extend(diagnoses)
            dx_rows.extend([visit_id] * len(diagnoses))
            proc_flat.extend(procedures)
            proc_rows.extend([visit_id] * len(procedures))

    def pool(codes: list[int], rows: list[int], embedding: torch.nn.Embedding) -> torch.Tensor:
        pooled = torch.zeros((batch_size * width, dim), device=device)
        if codes:
            indices = torch.tensor(codes, dtype=torch.long, device=device)
            row_ids = torch.tensor(rows, dtype=torch.long, device=device)
            encoded = model.rnn_dropout(embedding(indices))
            pooled.index_add_(0, row_ids, encoded)
        return pooled.view(batch_size, width, dim)

    diag = pool(dx_flat, dx_rows, model.embeddings[0])
    proc = pool(proc_flat, proc_rows, model.embeddings[1])
    return diag, proc, values, positions, lengths


def _forward_batch(model: torch.nn.Module, samples: list[Sample], drug_data: dict[str, Any], device: torch.device):
    diag, proc, ordered, positions, lengths = _build_batch(samples, model, device)
    packed_diag = pack_padded_sequence(diag, lengths.cpu(), batch_first=True, enforce_sorted=True)
    packed_proc = pack_padded_sequence(proc, lengths.cpu(), batch_first=True, enforce_sorted=True)
    output1, hidden1 = model.seq_encoders[0](packed_diag)
    output2, hidden2 = model.seq_encoders[1](packed_proc)
    output1, _ = pad_packed_sequence(output1, batch_first=True, total_length=diag.shape[1])
    output2, _ = pad_packed_sequence(output2, batch_first=True, total_length=proc.shape[1])
    row_ids = torch.arange(len(ordered), device=device)
    last_ids = lengths.to(device) - 1
    last1 = output1[row_ids, last_ids]
    last2 = output2[row_ids, last_ids]
    patient_repr = torch.cat([hidden1.squeeze(0), hidden2.squeeze(0), last1, last2], dim=-1)
    query = model.query(patient_repr)
    substruct_weight = torch.sigmoid(model.substruct_rela(query))
    global_embeddings = model.global_encoder(**drug_data["mol_data"])
    global_embeddings = torch.mm(drug_data["average_projection"], global_embeddings)
    if model.use_embedding:
        substruct_base = model.substruct_emb.unsqueeze(0)
    else:
        substruct_base = model.substruct_encoder(**drug_data["substruct_data"]).unsqueeze(0)
    substruct_embeddings = model.sab(substruct_base).squeeze(0)
    aggregator = model.aggregator
    q = aggregator.Qdense(global_embeddings)
    k = aggregator.Kdense(substruct_embeddings)
    allowed = drug_data["ddi_mask_H"] > 0
    attention_scores = q.mm(k.t()) / math.sqrt(aggregator.model_dim)
    attention_scores = attention_scores.masked_fill(~allowed, -(1 << 32))
    attention = torch.softmax(attention_scores, dim=-1)
    weighted_substructures = substruct_weight.unsqueeze(-1) * substruct_embeddings.unsqueeze(0)
    molecule_embeddings = torch.einsum("ms,bse->bme", attention, weighted_substructures)
    score = model.score_extractor(molecule_embeddings).squeeze(-1)
    probability = torch.sigmoid(score)
    batch_neg = 0.0005 * torch.einsum("bi,ij,bj->b", probability, drug_data["tensor_ddi_adj"], probability)
    inverse = np.argsort(positions)
    return score[inverse], batch_neg[inverse], [ordered[index] for index in inverse]


def _metrics(targets: np.ndarray, logits: np.ndarray, ddi: np.ndarray) -> dict[str, float]:
    predictions = logits >= math.log(THRESHOLD / (1.0 - THRESHOLD))
    jaccard = f1 = prauc = 0.0
    ddi_count = pair_count = 0
    medication_counts = []
    for target_row, logit_row, pred_row in zip(targets, logits, predictions):  # noqa: B905
        target = set(int(index) for index in np.flatnonzero(target_row > 0.5))
        pred = set(int(index) for index in np.flatnonzero(pred_row))
        inter = len(target & pred)
        union = len(target | pred)
        precision = inter / len(pred) if pred else 0.0
        recall = inter / len(target) if target else 0.0
        jaccard += inter / union if union else 1.0
        f1 += 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
        ranked = sorted(range(len(logit_row)), key=lambda index: (-float(logit_row[index]), index))
        found = total = 0.0
        for rank, index in enumerate(ranked, 1):
            if index in target:
                found += 1.0
                total += found / rank
        prauc += total / len(target) if target else 0.0
        medication_counts.append(len(pred))
        ordered = sorted(pred)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                pair_count += 1
                ddi_count += int(bool(ddi[left, right]))
    if not len(targets):
        raise RuntimeError("MoleRec evaluation is empty")
    stable_nll = np.maximum(logits, 0.0) - logits * targets + np.logaddexp(0.0, -np.abs(logits))
    return {
        "jaccard": jaccard / len(targets),
        "f1": f1 / len(targets),
        "prauc": prauc / len(targets),
        "ddi_rate": 0.0 if pair_count == 0 else ddi_count / pair_count,
        "mean_medication_count": float(np.mean(medication_counts)),
        "nll": float(stable_nll.mean()),
        "visit_count": float(len(targets)),
    }


def _evaluate(model, dataset, drug_data, dx_count, proc_count, device, batch_size):
    scores = np.zeros((len(dataset), MEDICATIONS), dtype=np.float32)
    targets = np.zeros_like(scores)
    keys = [""] * len(dataset)
    model.eval()
    with torch.no_grad():
        for start in range(0, len(dataset), batch_size):
            indices = list(range(start, min(start + batch_size, len(dataset))))
            samples = dataset.get_batch(indices)
            logits, _ddi, ordered = _forward_batch(model, samples, drug_data, device)
            for local, sample in enumerate(ordered):
                destination = start + local
                scores[destination] = logits[local].detach().cpu().numpy()
                targets[destination, sample.target] = 1.0
                keys[destination] = sample.key
    return targets, scores, keys


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.source_revision != SOURCE_REVISION:
        raise RuntimeError("MoleRec source revision does not match the pinned official revision")
    source_root = args.source_root.resolve()
    if not (source_root / "modules" / "MoleRec.py").is_file():
        raise RuntimeError("pinned MoleRec source tree is incomplete")
    sys.path.insert(0, str(source_root))
    from modules import MoleRecModel
    from modules.gnn import graph_batch_from_smile
    from util import buildPrjSmiles

    train, dev, dx_count, proc_count, ddi, med_order = _load_samples(args.dataset, args)
    data_root = source_root.parent / "data"
    import dill

    molecule = dill.load((data_root / "idx2SMILES.pkl").open("rb"))
    ddi_mask = np.asarray(dill.load((data_root / "ddi_mask_H.pkl").open("rb")), dtype=np.float32)
    substructure_smiles = dill.load((data_root / "substructure_smiles.pkl").open("rb"))
    if ddi_mask.shape != (131, 491) or set(molecule) - {"seperator", "decoder_point"} != set(med_order):
        raise RuntimeError("MoleRec molecular assets do not align to common131")
    ddi_asset = data_root / "ddi_A_final.pkl"
    if not ddi_asset.is_file() and args.dataset == "mimic_iii" and args.snapshot_root:
        ddi_asset = args.snapshot_root.resolve() / "ddi_A_final.pkl"
    if not ddi_asset.is_file() and args.dataset == "mimic_iv" and args.common_root:
        ddi_asset = args.common_root.resolve() / "ddi_matrix.private.json"
    if ddi_asset.suffix == ".json":
        source_ddi = np.asarray(json.loads(ddi_asset.read_text(encoding="utf-8"))["matrix"], dtype=np.float32)
    elif ddi_asset.is_file():
        source_ddi = np.asarray(dill.load(ddi_asset.open("rb")), dtype=np.float32)
    else:
        raise RuntimeError("MoleRec DDI asset is unavailable")
    if source_ddi.shape != (131, 131) or not np.array_equal(source_ddi, ddi):
        raise RuntimeError("MoleRec DDI asset is not the canonical common131 matrix")
    device = torch.device("cuda:0")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for MoleRec training")
    random.seed(SEED)
    np.random.seed(2048)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    average_projection, smiles_list = buildPrjSmiles(
        molecule, {index: code for index, code in enumerate(med_order)}
    )
    average_projection = average_projection.to(device)
    molecule_graphs = graph_batch_from_smile(smiles_list).to(device)
    substruct_graphs = graph_batch_from_smile(substructure_smiles).to(device)
    molecule_para = {
        "num_layer": 4,
        "emb_dim": EMB_DIM,
        "graph_pooling": "mean",
        "drop_ratio": DROPOUT,
        "gnn_type": "gin",
        "virtual_node": False,
    }
    model = MoleRecModel(
        global_para=molecule_para,
        substruct_para=molecule_para,
        emb_dim=EMB_DIM,
        global_dim=EMB_DIM,
        substruct_dim=EMB_DIM,
        substruct_num=491,
        voc_size=(dx_count, proc_count, 131),
        use_embedding=False,
        device=device,
        dropout=DROPOUT,
    ).to(device)
    drug_data = {
        "substruct_data": {"batched_data": substruct_graphs},
        "mol_data": {"batched_data": molecule_graphs},
        "ddi_mask_H": torch.from_numpy(ddi_mask).to(device),
        "tensor_ddi_adj": torch.from_numpy(ddi).to(device),
        "average_projection": average_projection,
    }
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("MoleRec output directory is not empty")
    best_state = None
    best_j = -float("inf")
    best_epoch = 0
    evaluations = []
    rng = np.random.RandomState(SEED)
    start_time = time.time()
    torch.cuda.set_device(device)
    torch.cuda.reset_peak_memory_stats(device)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        indices = rng.permutation(len(train))
        loss_sum = 0.0
        for start in range(0, len(indices), BATCH_SIZE):
            samples = train.get_batch([int(index) for index in indices[start : start + BATCH_SIZE]])
            logits, ddi_loss, ordered = _forward_batch(model, samples, drug_data, device)
            target = torch.zeros((len(ordered), 131), device=device)
            margin = torch.full((len(ordered), 131), -1, dtype=torch.long, device=device)
            for row, sample in enumerate(ordered):
                target[row, sample.target] = 1.0
                margin[row, : len(sample.target)] = torch.tensor(sample.target, dtype=torch.long, device=device)
            sigmoid = torch.sigmoid(logits)
            bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none").mean(dim=1)
            multi = F.multilabel_margin_loss(sigmoid, margin)
            binary_pred = (sigmoid.detach().cpu().numpy() >= 0.5)
            current_ddi = []
            for row in binary_pred:
                chosen = np.flatnonzero(row)
                pairs = [(left, right) for left_index, left in enumerate(chosen) for right in chosen[left_index + 1 :]]
                current_ddi.append(sum(int(ddi[left, right]) for left, right in pairs) / len(pairs) if pairs else 0.0)
            current_ddi = torch.tensor(current_ddi, dtype=torch.float32, device=device)
            base = 0.95 * bce + 0.05 * multi
            beta = COEF * (1.0 - current_ddi / TARGET_DDI)
            beta = torch.minimum(torch.exp(beta), torch.ones_like(beta))
            loss = torch.where(current_ddi <= TARGET_DDI, base, beta * base + (1.0 - beta) * ddi_loss)
            loss = loss.mean()
            if not torch.isfinite(loss):
                raise RuntimeError("MoleRec training loss is not finite")
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.item()) * len(ordered)
        dev_target, dev_score, dev_keys = _evaluate(model, dev, drug_data, dx_count, proc_count, device, EVAL_BATCH_SIZE)
        dev_metrics = _metrics(dev_target, dev_score, ddi)
        evaluations.append({"epoch": epoch, "train_loss": loss_sum / len(train), "dev": dev_metrics})
        print(json.dumps({"epoch": epoch, "dev": dev_metrics}, sort_keys=True), flush=True)
        if dev_metrics["jaccard"] > best_j + 1e-12:
            best_j = dev_metrics["jaccard"]
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            torch.save(best_state, output / "selected_checkpoint.pt")
            np.save(output / "dev_logits.npy", dev_score)
            np.save(output / "dev_targets.npy", dev_target)
            np.save(output / "dev_patient_keys.npy", np.asarray(dev_keys, dtype="U128"))
    if best_state is None:
        raise RuntimeError("MoleRec did not select a Dev checkpoint")
    model.load_state_dict(best_state)
    train_target, train_score, _ = _evaluate(model, train, drug_data, dx_count, proc_count, device, EVAL_BATCH_SIZE)
    dev_target, dev_score, dev_keys = _evaluate(model, dev, drug_data, dx_count, proc_count, device, EVAL_BATCH_SIZE)
    np.save(output / "dev_logits.npy", dev_score)
    np.save(output / "dev_targets.npy", dev_target)
    np.save(output / "dev_patient_keys.npy", np.asarray(dev_keys, dtype="U128"))
    result = {
        "schema_version": 1,
        "status": "complete",
        "stage": "STAGE -1G",
        "baseline": "MoleRec",
        "dataset": args.dataset,
        "surface": "canonical131" if args.dataset == "mimic_iii" else "common131",
        "source_revision": args.source_revision,
        "dataset_sizes": {"diagnosis": dx_count, "procedure": proc_count, "medication": 131},
        "config": {
            "seed": SEED,
            "numpy_seed": 2048,
            "batch_size": BATCH_SIZE,
            "eval_batch_size": EVAL_BATCH_SIZE,
            "epochs": EPOCHS,
            "optimizer": "Adam",
            "learning_rate": LEARNING_RATE,
            "dropout": DROPOUT,
            "coef": COEF,
            "target_ddi": TARGET_DDI,
            "threshold": THRESHOLD,
            "checkpoint_rule": "highest Dev Jaccard",
            "loss": "official MoleRec BCE/multilabel/DDI annealing",
        },
        "parameter_count": int(sum(parameter.numel() for parameter in model.parameters())),
        "best_epoch": best_epoch,
        "metrics": {"Train": _metrics(train_target, train_score, ddi), "Dev": _metrics(dev_target, dev_score, ddi)},
        "evaluations": evaluations,
        "resource": {
            "wall_time_seconds": time.time() - start_time,
            "peak_gpu_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
        },
        "test_loaded": False,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    train.close()
    dev.close()
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=("mimic_iii", "mimic_iv"), required=True)
    parser.add_argument("--snapshot-root", type=Path)
    parser.add_argument("--common-root", type=Path)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args(argv)
    if args.dataset == "mimic_iii" and args.snapshot_root is None:
        parser.error("MIMIC-III requires --snapshot-root")
    if args.dataset == "mimic_iv" and args.common_root is None:
        parser.error("MIMIC-IV requires --common-root")
    return args


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), sort_keys=True))
