#!/usr/bin/env python3
"""Run the fixed MICA early/late Train/Dev prototype screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import dill
import numpy as np
import torch

try:
    from mica import DIM, FF_DIM, HEADS, LAYERS, MEDICATIONS, MICA, objective, pack_inputs
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mica import DIM, FF_DIM, HEADS, LAYERS, MEDICATIONS, MICA, objective, pack_inputs

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "needcover"))
from needcover import evaluate_surface, target_sets_from_matrix

SEED = 20260914
EPOCHS = 60
BATCH_SIZE = 16
LR = 3e-4
WEIGHT_DECAY = 1e-4
GATE_NAMESPACE = "idea008-gate01-v1"
LOGIT_THRESHOLD = float(np.log(0.35 / 0.65))


def gate01_dev(patient_id: int) -> bool:
    value = int.from_bytes(hashlib.sha256((GATE_NAMESPACE + ":" + str(patient_id)).encode()).digest()[:8], "big")
    return value / float(2 ** 64) < 0.5


def _seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False


def _load(root: Path, name: str) -> np.ndarray:
    return np.array(np.load(root / name, mmap_mode="r"), dtype=np.float32, copy=True)


def _rows(records: Sequence[Any], patients: Sequence[int]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for patient in patients:
        history: List[Tuple[List[int], List[int], List[int]]] = []
        for admission in records[int(patient)]:
            rows.append({"diagnoses": list(admission[0]), "procedures": list(admission[1]), "history": list(history), "_medications": list(admission[2])})
            history.append((list(admission[0]), list(admission[1]), list(admission[2])))
    return rows


def _validate_vocab(records: Sequence[Any], voc: Dict[str, Any], ddi: np.ndarray, patients: Sequence[int]) -> Tuple[int, int]:
    dx = voc["diag_voc"]; proc = voc["pro_voc"]; med = voc["med_voc"]
    med_ids = set(int(k) for k in med.idx2word.keys())
    if med_ids != set(range(MEDICATIONS)):
        raise RuntimeError("medication vocabulary IDs are not the exact canonical 131 IDs")
    dx_ids = set(int(k) for k in dx.idx2word.keys()); proc_ids = set(int(k) for k in proc.idx2word.keys())
    if dx_ids != set(range(len(dx_ids))) or proc_ids != set(range(len(proc_ids))):
        raise RuntimeError("diagnosis/procedure vocabulary IDs are not contiguous canonical IDs")
    for patient_index in patients:
        patient = records[int(patient_index)]
        for visit in patient:
            if any(int(x) not in dx_ids for x in visit[0]) or any(int(x) not in proc_ids for x in visit[1]):
                raise RuntimeError("record contains a diagnosis/procedure ID absent from exact vocabulary")
            if any(int(x) < 0 or int(x) >= MEDICATIONS for x in visit[2]):
                raise RuntimeError("record contains medication ID outside exact 131-item vocabulary")
    ddi = np.asarray(ddi, dtype=np.float32)
    if ddi.shape != (MEDICATIONS, MEDICATIONS) or not np.isfinite(ddi).all() or not np.array_equal(ddi, ddi.T) or np.any(np.diag(ddi) != 0):
        raise RuntimeError("DDI must be finite, symmetric, and zero-diagonal 131 by 131")
    return len(dx_ids), len(proc_ids)


def _align(rows: Sequence[Dict[str, Any]], targets: np.ndarray, name: str) -> None:
    if targets.ndim != 2 or targets.shape[1] != MEDICATIONS or len(rows) != targets.shape[0]:
        raise RuntimeError(name + " targets are not aligned with canonical [visits,131] data")
    if not np.isfinite(targets).all() or not np.isin(targets, (0.0, 1.0)).all():
        raise RuntimeError(name + " targets are not finite binary values")
    for index, row in enumerate(rows):
        expected = np.zeros(MEDICATIONS, dtype=np.float32)
        expected[[int(x) for x in row["_medications"]]] = 1.0
        if not np.array_equal(expected, targets[index]): raise RuntimeError(name + " target mismatch at row " + str(index))


def _metric_jaccard(targets: np.ndarray, logits: np.ndarray) -> float:
    predictions = [set(np.flatnonzero(row >= LOGIT_THRESHOLD)) for row in logits]
    total = 0.0
    for target, pred in zip(target_sets_from_matrix(targets), predictions):
        union = target | pred; total += 1.0 if not union else len(target & pred) / len(union)
    return total / len(predictions)


def _predict(model: torch.nn.Module, rows: Sequence[Dict[str, Any]], targets: np.ndarray, ddi: np.ndarray, dx: int, proc: int, device: torch.device, full_metrics: bool = True) -> Tuple[np.ndarray, Dict[str, float]]:
    model.eval(); output: List[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch = pack_inputs(rows[start:start + BATCH_SIZE], dx, proc)
            batch = {key: value.to(device) for key, value in batch.items()}
            output.append(model(batch).cpu().numpy())
    logits = np.concatenate(output, axis=0)
    if not np.isfinite(logits).all(): raise RuntimeError("non-finite model logits")
    if not full_metrics:
        with torch.no_grad():
            bce = torch.nn.functional.binary_cross_entropy_with_logits(torch.from_numpy(logits), torch.from_numpy(targets))
        return logits, {"jaccard": _metric_jaccard(targets, logits), "bce": float(bce.item())}
    preds = [set(np.flatnonzero(row >= LOGIT_THRESHOLD)) for row in logits]
    metrics = evaluate_surface(target_sets_from_matrix(targets), preds, logits, ddi)
    metrics["nll"] = float(torch.nn.functional.binary_cross_entropy_with_logits(torch.from_numpy(logits), torch.from_numpy(targets)).item())
    return logits, metrics


def run(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.source_revision:
        raise RuntimeError("--source-revision is required")
    actual_revision = _git_revision()
    if actual_revision != args.source_revision:
        raise RuntimeError("source revision does not match git HEAD")
    status = subprocess.run(["git", "status", "--porcelain", "--", str(Path(__file__).resolve()), str(Path(__file__).resolve().parent / "mica.py"), str(Path(__file__).resolve().parent / "preflight_mica.py")], check=True, capture_output=True, text=True).stdout.strip()
    if status:
        raise RuntimeError("tracked MICA experiment source is not clean")
    snapshot = args.snapshot_root.resolve(); root = args.train_dev_root.resolve(); out = args.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    records = dill.load((snapshot / "records_final.pkl").open("rb")); voc = dill.load((snapshot / "voc_final.pkl").open("rb")); ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3); train_patients = tuple(range(split)); dev_patients = tuple(i for i in range(split, len(records)) if gate01_dev(i))
    if (len(records), len(train_patients), len(dev_patients)) != (6350, 4233, 1004): raise RuntimeError("canonical patient split counts are not 6350/4233/1004")
    dx, proc = _validate_vocab(records, voc, ddi, (*train_patients, *dev_patients))
    train = _rows(records, train_patients); dev = _rows(records, dev_patients)
    train_targets = _load(root, "train_targets.npy"); dev_targets = _load(root, "dev_targets.npy"); dev_scores = _load(root, "dev_scores.npy")
    _align(train, train_targets, "Train"); _align(dev, dev_targets, "Dev")
    if (len(train), len(dev)) != (10489, 2130): raise RuntimeError("canonical visit counts are not 10489/2130")
    for row in train + dev: row.pop("_medications", None)
    if dev_scores.shape != dev_targets.shape or not np.isfinite(dev_scores).all(): raise RuntimeError("dev_scores is not a finite canonical [visits,131] array")
    if args.preflight_only: return {"preflight_only": True, "source_revision": args.source_revision}
    if not torch.cuda.is_available(): raise RuntimeError("CUDA is required for MICA experiment execution")
    device = torch.device("cuda"); torch.cuda.reset_peak_memory_stats(device); _seed(SEED)
    model = MICA(dx, proc, args.variant).to(device); model.initialize_prevalence(torch.from_numpy(train_targets.mean(0)).to(device)); ddi_tensor = torch.from_numpy(ddi).to(device); optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY, betas=(.9, .999), eps=1e-8)
    best_j = -1.0; best_epoch = 0; best_state = None; best_dev_logits = None; best_dev_metrics = None; progress = []
    start_time = time.time(); generator = np.random.RandomState(SEED)
    for epoch in range(1, EPOCHS + 1):
        model.train(); order = generator.permutation(len(train)); totals = [0.0, 0.0, 0.0, 0]
        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start:start + BATCH_SIZE]; batch = {k: v.to(device) for k, v in pack_inputs([train[int(i)] for i in indices], dx, proc).items()}; target = torch.from_numpy(train_targets[indices]).to(device)
            optimizer.zero_grad(set_to_none=True); loss, bce, ddi_loss = objective(model(batch), target, ddi_tensor)
            if not torch.isfinite(loss): raise RuntimeError("non-finite training loss")
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0); optimizer.step(); size = len(indices); totals[0] += float(loss.item()) * size; totals[1] += float(bce.item()) * size; totals[2] += float(ddi_loss.item()) * size; totals[3] += size
        dev_logits, dev_metrics = _predict(model, dev, dev_targets, ddi, dx, proc, device); j = float(dev_metrics["jaccard"])
        entry = {"epoch": epoch, "train_loss": totals[0] / totals[3], "train_bce": totals[1] / totals[3], "train_ddi": totals[2] / totals[3], "dev_metrics": dev_metrics, "elapsed_seconds": time.time() - start_time, "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0}; progress.append(entry)
        tmp = out / "progress.json.tmp"; tmp.write_text(json.dumps({"variant": args.variant, "source_revision": args.source_revision, "config": {"epochs": EPOCHS, "batch_size_visits": BATCH_SIZE}, "epochs": progress}, indent=2) + "\n"); os.replace(tmp, out / "progress.json")
        if j > best_j + 1e-12:
            best_j, best_epoch, best_state, best_dev_logits, best_dev_metrics = j, epoch, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, dev_logits.copy(), dict(dev_metrics)
            torch.save(best_state, out / "selected_checkpoint.pt")
    model.load_state_dict(best_state); train_logits, train_metrics = _predict(model, train, train_targets, ddi, dx, proc, device); dev_logits, dev_metrics = best_dev_logits, best_dev_metrics
    np.savez_compressed(out / "selected_predictions.npz", train_logits=train_logits, train_probabilities=1.0 / (1.0 + np.exp(-train_logits)), train_targets=train_targets, dev_logits=dev_logits, dev_probabilities=1.0 / (1.0 + np.exp(-dev_logits)), dev_targets=dev_targets)
    config = {"variant": args.variant, "seed": SEED, "dim": DIM, "heads": HEADS, "ff_dim": FF_DIM, "layers": LAYERS, "input_dropout": .1, "output_dropout": .1, "conditioner": "linear 128 -> 256, tanh scale/shift", "epochs": EPOCHS, "batch_size_visits": BATCH_SIZE, "optimizer": "AdamW", "learning_rate": LR, "weight_decay": WEIGHT_DECAY, "betas": [.9, .999], "eps": 1e-8, "gradient_clip": 5.0, "decoder": "sigmoid >= 0.35", "loss": "BCE + 0.05 DDI / 131", "dtype": "float32"}
    result = {"variant": args.variant, "source_revision": args.source_revision, "config": config, "parameter_count": sum(p.numel() for p in model.parameters()), "split": {"train_patients": len(train_patients), "dev_patients": len(dev_patients), "train_visits": len(train), "dev_visits": len(dev)}, "selected_epoch": best_epoch, "metrics": {"Train": train_metrics, "Dev": dev_metrics}, "progress": progress, "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0, "runtime": {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__}, "frozen_molerec_dev": evaluate_surface(target_sets_from_matrix(dev_targets), [set(np.flatnonzero(x >= 0.0)) for x in dev_scores], dev_scores, ddi), "historical_graphrefine_samek": {"jaccard": .533650, "f1": .687394, "prauc": .784240, "ddi_rate": .073328, "mean_medication_count": 21.5451, "diagnostic_only": True}, "source_bound_references": {"snapshot": "molerec-table1-c721-www23", "train_dev": "idea008-gate01-train-dev-5752596a-20260913a"}}
    (out / "progress.json").write_text(json.dumps({"variant": args.variant, "selected_epoch": best_epoch, "epochs": progress}, indent=2) + "\n"); (out / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n"); return result


def _git_revision() -> str:
    try: return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError): return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--variant", choices=("early", "late"), required=True); parser.add_argument("--snapshot-root", type=Path, required=True); parser.add_argument("--train-dev-root", type=Path, required=True); parser.add_argument("--output-dir", type=Path, required=True); parser.add_argument("--source-revision", default=""); parser.add_argument("--preflight-only", action="store_true"); args = parser.parse_args(); print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__": main()
