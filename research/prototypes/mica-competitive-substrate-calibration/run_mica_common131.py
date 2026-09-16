#!/usr/bin/env python3
"""Run the frozen MICA variants on the additive MIMIC-IV common-131 surface."""

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
from pathlib import Path
from typing import Any

import numpy as np
import torch

MICA_SOURCE_REVISION = "ffdaec8a6c0cdc20d071ad00eca8bb025f336ef0"
COMMON_ROOT_NAME = "mimiciv-medrec-common131-stage-1g-20260916"
COMMON_MEDICATIONS = 131
SEED = 20260914
BATCH_SIZE = 16
EVAL_BATCH_SIZE = 256
UPDATE_CAP = 39_360
EVAL_EVERY = 3_280
LR = 1e-4
WEIGHT_DECAY = 1e-4
GRADIENT_CLIP = 5.0
THRESHOLD = 0.35
LOGIT_THRESHOLD = float(np.log(THRESHOLD / (1.0 - THRESHOLD)))

MICA_DIR = Path(__file__).resolve().parents[1] / "mica-cross-dataset-replication"
if str(MICA_DIR) not in sys.path:
    sys.path.insert(0, str(MICA_DIR))
from mica import MICA, configure_numeric_policy, objective, pack_inputs  # noqa: E402


def _seed() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
    configure_numeric_policy()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_vocab(root: Path) -> tuple[dict[str, int], dict[str, int], dict[str, int], np.ndarray]:
    vocab = json.loads((root / "vocabularies.private.json").read_text(encoding="utf-8"))
    ddi_payload = json.loads((root / "ddi_matrix.private.json").read_text(encoding="utf-8"))
    diagnosis = {str(key): int(value) for key, value in vocab["diagnosis"].items()}
    procedure = {str(key): int(value) for key, value in vocab["procedure"].items()}
    medication = {str(key): int(value) for key, value in vocab["medication"].items()}
    if len(medication) != COMMON_MEDICATIONS or set(medication.values()) != set(range(131)):
        raise RuntimeError("common131 medication vocabulary is not the frozen 131-axis")
    ddi = np.asarray(ddi_payload["matrix"], dtype=np.float32)
    if ddi.shape != (131, 131) or ddi_payload.get("vocabulary") != medication:
        raise RuntimeError("common131 DDI vocabulary/shape mismatch")
    if not np.array_equal(ddi, ddi.T) or np.any(np.diag(ddi) != 0):
        raise RuntimeError("common131 DDI matrix is not symmetric zero-diagonal")
    return diagnosis, procedure, medication, ddi


def _project(values: Iterable[Any], vocab: dict[str, int]) -> list[int]:
    return sorted({int(vocab[str(value)]) for value in values})


def _validate(
    example: dict[str, Any], dx: dict[str, int], proc: dict[str, int], med: dict[str, int]
):
    required = {
        "schema_version",
        "subject_id",
        "current_visit_order",
        "input",
        "target",
        "provenance",
    }
    if set(example) != required or int(example["schema_version"]) != 1:
        raise RuntimeError("common131 example schema mismatch")
    inp = example["input"]
    if set(inp) != {"diagnoses", "procedures", "history"}:
        raise RuntimeError("common131 input contains an unexpected medication-bearing field")
    target = example["target"]
    if set(target) != {"medications", "known_medications", "oov_medications"}:
        raise RuntimeError("common131 target schema mismatch")
    target_tokens = [str(value) for value in target["medications"]]
    if target["oov_medications"] or set(target_tokens) != {
        str(value) for value in target["known_medications"]
    }:
        raise RuntimeError("common131 target is not closed")
    target_ids = sorted({int(med[token]) for token in target_tokens})
    if not target_ids:
        raise RuntimeError("common131 loader received an empty target")
    current_order = int(example["current_visit_order"])
    provenance = example["provenance"]
    current_hadm = str(provenance["current_hadm_id"])
    history_ids = [str(value) for value in provenance["history_hadm_ids"]]
    history = inp["history"]
    if len(history) != len(history_ids) or current_hadm in history_ids:
        raise RuntimeError("common131 current admission appears in history")
    sequence = []
    previous_order = -1
    for entry, hadm_id in zip(history, history_ids):  # noqa: B905 -- Python 3.8 remote
        if str(entry["hadm_id"]) != hadm_id:
            raise RuntimeError("common131 history provenance mismatch")
        order = int(entry["visit_order"])
        if order >= current_order or order <= previous_order:
            raise RuntimeError("common131 strict history invariant failed")
        previous_order = order
        history_meds = [int(med[str(token)]) for token in entry["medications"]]
        sequence.append(
            (
                _project(entry["diagnoses"], dx),
                _project(entry["procedures"], proc),
                sorted(set(history_meds)),
            )
        )
    sequence.append((_project(inp["diagnoses"], dx), _project(inp["procedures"], proc), []))
    return sequence, target_ids, str(example["subject_id"])


class JsonlDataset:
    def __init__(
        self, root: Path, role: str, dx: dict[str, int], proc: dict[str, int], med: dict[str, int]
    ):
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

    def get_batch(self, indices: Sequence[int]):
        rows = []
        targets = np.zeros((len(indices), len(self.med)), dtype=np.float32)
        patients = []
        for output_index, index in enumerate(indices):
            self.handle.seek(int(self.offsets[int(index)]))
            line = self.handle.readline()
            if not line:
                raise RuntimeError("common131 offset points past EOF")
            example = json.loads(line.decode("utf-8"))
            row, target_ids, patient = _validate(example, self.dx, self.proc, self.med)
            rows.append({"diagnoses": row[-1][0], "procedures": row[-1][1], "history": row[:-1]})
            targets[output_index, target_ids] = 1.0
            patients.append(patient)
        return rows, targets, patients

    def target_sum(self) -> np.ndarray:
        total = np.zeros(len(self.med), dtype=np.float64)
        for start in range(0, len(self), EVAL_BATCH_SIZE):
            _rows, targets, _patients = self.get_batch(
                list(range(start, min(start + EVAL_BATCH_SIZE, len(self))))
            )
            total += targets.sum(axis=0)
        return total

    def close(self) -> None:
        self.handle.close()


def _average_precision(target: np.ndarray, scores: np.ndarray) -> float:
    target_set = set(int(index) for index in np.flatnonzero(target > 0.5))
    if not target_set:
        return 0.0
    order = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    found = total = 0.0
    for rank, index in enumerate(order, 1):
        if index in target_set:
            found += 1.0
            total += found / rank
    return total / len(target_set)


def surface_metrics(targets: np.ndarray, logits: np.ndarray, ddi: np.ndarray) -> dict[str, float]:
    if targets.shape != logits.shape or logits.ndim != 2:
        raise RuntimeError("common131 targets and logits are not aligned")
    jaccard = f1 = prauc = 0.0
    ddi_count = pair_count = 0
    medication_counts = []
    for target_row, logit_row in zip(targets, logits):  # noqa: B905 -- Python 3.8 remote
        target = set(int(index) for index in np.flatnonzero(target_row > 0.5))
        prediction = set(int(index) for index in np.flatnonzero(logit_row >= LOGIT_THRESHOLD))
        intersection = len(target & prediction)
        union = len(target | prediction)
        precision = intersection / len(prediction) if prediction else 0.0
        recall = intersection / len(target) if target else 0.0
        f1 += 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
        jaccard += intersection / union if union else 1.0
        prauc += _average_precision(target_row, logit_row)
        medication_counts.append(len(prediction))
        ordered = sorted(prediction)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                pair_count += 1
                ddi_count += int(bool(ddi[left, right]))
    count = len(targets)
    if not count:
        raise RuntimeError("common131 evaluation is empty")
    stable_nll = np.maximum(logits, 0.0) - logits * targets + np.logaddexp(0.0, -np.abs(logits))
    return {
        "jaccard": jaccard / count,
        "f1": f1 / count,
        "prauc": prauc / count,
        "ddi_rate": 0.0 if pair_count == 0 else ddi_count / pair_count,
        "mean_medication_count": float(np.mean(medication_counts)),
        "nll": float(stable_nll.mean()),
        "visit_count": float(count),
    }


def _predict(
    model: torch.nn.Module,
    dataset: JsonlDataset,
    dx_count: int,
    proc_count: int,
    device: torch.device,
):
    model.eval()
    logits = []
    targets = []
    patients = []
    with torch.no_grad():
        for start in range(0, len(dataset), EVAL_BATCH_SIZE):
            rows, target, patient = dataset.get_batch(
                list(range(start, min(start + EVAL_BATCH_SIZE, len(dataset))))
            )
            batch = {
                key: value.to(device)
                for key, value in pack_inputs(rows, dx_count, proc_count).items()
            }
            logits.append(model(batch).detach().cpu().numpy())
            targets.append(target)
            patients.extend(patient)
    return np.concatenate(logits), np.concatenate(targets), patients


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.source_revision != MICA_SOURCE_REVISION:
        raise RuntimeError(
            "common131 MICA source revision does not match the frozen Stage -1F source"
        )
    root = args.common_root.resolve()
    if root.name != COMMON_ROOT_NAME:
        raise RuntimeError("common131 private root identity mismatch")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for common131 MICA training")
    dx, proc, med, ddi = _load_vocab(root)
    train = JsonlDataset(root, "train", dx, proc, med)
    dev = JsonlDataset(root, "dev", dx, proc, med)
    if (len(train), len(dev)) != (308474, 76443):
        raise RuntimeError("common131 Train/Dev counts changed")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("common131 MICA output directory is not empty")
    _seed()
    device = torch.device("cuda:0")
    torch.cuda.set_device(device)
    torch.cuda.reset_peak_memory_stats(device)
    model = MICA(len(dx), len(proc), args.variant, medication_count=131).to(device)
    prevalence = train.target_sum().astype(np.float32) / float(len(train))
    model.initialize_prevalence(torch.from_numpy(prevalence).to(device))
    ddi_tensor = torch.from_numpy(ddi).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY, betas=(0.9, 0.999), eps=1e-8
    )
    rng = np.random.RandomState(SEED)
    updates_per_epoch = math.ceil(len(train) / float(BATCH_SIZE))
    total_updates = UPDATE_CAP
    evaluations = []
    best_j = -float("inf")
    best_update = None
    best_state = None
    best_dev_metrics = None
    update = 0
    epoch = 0
    next_eval = EVAL_EVERY
    start_time = time.time()
    while update < total_updates:
        epoch += 1
        order = rng.permutation(len(train))
        for start in range(0, len(order), BATCH_SIZE):
            if update >= total_updates:
                break
            indices = order[start : start + BATCH_SIZE]
            rows, target, _patients = train.get_batch(indices)
            batch = {
                key: value.to(device)
                for key, value in pack_inputs(rows, len(dx), len(proc)).items()
            }
            target_tensor = torch.from_numpy(target).to(device)
            optimizer.zero_grad(set_to_none=True)
            loss, bce, ddi_loss = objective(
                model(batch), target_tensor, ddi_tensor, medication_count=131
            )
            if not torch.isfinite(loss):
                raise RuntimeError("common131 MICA training loss is not finite")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            update += 1
            if update < next_eval and update < total_updates:
                continue
            dev_logits, dev_targets, dev_patients = _predict(model, dev, len(dx), len(proc), device)
            metrics = surface_metrics(dev_targets, dev_logits, ddi)
            entry = {
                "update": update,
                "epoch_equivalent": update / float(updates_per_epoch),
                "train_loss": float(loss.item()),
                "train_bce": float(bce.item()),
                "train_ddi": float(ddi_loss.item()),
                "dev_metrics": metrics,
                "elapsed_seconds": time.time() - start_time,
                "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
            }
            evaluations.append(entry)
            if metrics["jaccard"] > best_j + 1e-12:
                best_j = float(metrics["jaccard"])
                best_update = update
                best_state = {
                    key: value.detach().cpu().clone() for key, value in model.state_dict().items()
                }
                best_dev_metrics = dict(metrics)
                np.save(output / "selected_dev_logits.npy", dev_logits.astype(np.float32))
                np.save(output / "dev_targets.npy", dev_targets.astype(np.float32))
                np.save(output / "dev_patient_keys.npy", np.asarray(dev_patients, dtype="U64"))
                torch.save(best_state, output / "selected_checkpoint.pt")
            next_eval += EVAL_EVERY
    if best_state is None or best_dev_metrics is None or best_update is None:
        raise RuntimeError("common131 MICA did not select a Dev checkpoint")
    model.load_state_dict(best_state)
    train_logits, train_targets, _ = _predict(model, train, len(dx), len(proc), device)
    final_train_metrics = surface_metrics(train_targets, train_logits, ddi)
    dev_logits, dev_targets, dev_patients = _predict(model, dev, len(dx), len(proc), device)
    final_dev_metrics = surface_metrics(dev_targets, dev_logits, ddi)
    np.save(output / "selected_dev_logits.npy", dev_logits.astype(np.float32))
    np.save(output / "dev_targets.npy", dev_targets.astype(np.float32))
    np.save(output / "dev_patient_keys.npy", np.asarray(dev_patients, dtype="U64"))
    result = {
        "schema_version": 1,
        "status": "complete",
        "stage": "STAGE -1G",
        "dataset": "mimic_iv",
        "surface": "common131",
        "variant": args.variant,
        "source_revision": args.source_revision,
        "dataset_manifest_sha256": _sha256(root / "manifest.json"),
        "dataset_sizes": {"diagnosis": len(dx), "procedure": len(proc), "medication": 131},
        "config": {
            "seed": SEED,
            "batch_size_visits": BATCH_SIZE,
            "eval_batch_size_visits": EVAL_BATCH_SIZE,
            "update_cap": UPDATE_CAP,
            "eval_every_updates": EVAL_EVERY,
            "optimizer": "AdamW",
            "learning_rate": LR,
            "weight_decay": WEIGHT_DECAY,
            "betas": [0.9, 0.999],
            "eps": 1e-8,
            "gradient_clip": GRADIENT_CLIP,
            "decoder_threshold": THRESHOLD,
            "loss": "BCE + 0.05 * normalized DDI penalty",
        },
        "parameter_count": int(sum(parameter.numel() for parameter in model.parameters())),
        "updates_per_epoch": updates_per_epoch,
        "completed_updates": update,
        "completed_epoch_equivalent": update / float(updates_per_epoch),
        "selected_update": best_update,
        "selected_checkpoint": {"Dev": final_dev_metrics, "Train": final_train_metrics},
        "terminal_dev_metrics": final_dev_metrics,
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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("shared_pool", "drug_query"), required=True)
    parser.add_argument("--common-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), sort_keys=True))
