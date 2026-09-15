#!/usr/bin/env python3
"""Run the fixed MICA attribution Train/Dev screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch

try:
    from mica import (
        DIM,
        FF_DIM,
        HEADS,
        LAYERS,
        MEDICATIONS,
        MICA,
        THRESHOLD,
        configure_numeric_policy,
        objective,
        pack_inputs,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from mica import (
        DIM,
        FF_DIM,
        HEADS,
        LAYERS,
        MEDICATIONS,
        MICA,
        THRESHOLD,
        configure_numeric_policy,
        objective,
        pack_inputs,
    )

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "needcover"))
from needcover import evaluate_surface, target_sets_from_matrix

SEED = 20260914
EPOCHS = 60
BATCH_SIZE = 16
LR = 3e-4
WEIGHT_DECAY = 1e-4
DDI_WEIGHT = 0.05
GRADIENT_CLIP = 5.0
GATE_NAMESPACE = "idea008-gate01-v1"
SNAPSHOT_IDENTITY = "molerec-table1-c721-www23"
TRAIN_DEV_IDENTITY = "gate01-train-dev-5752596a-20260913a"
LOGIT_THRESHOLD = float(np.log(THRESHOLD / (1.0 - THRESHOLD)))
PROGRESS_SCHEMA_VERSION = 1


def gate01_dev(patient_id: int) -> bool:
    value = int.from_bytes(
        hashlib.sha256((GATE_NAMESPACE + ":" + str(patient_id)).encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    configure_numeric_policy()


def _load(root: Path, name: str) -> np.ndarray:
    return np.array(np.load(root / name, mmap_mode="r"), dtype=np.float32, copy=True)


def _rows(records: Sequence[Any], patients: Sequence[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for patient in patients:
        history: list[tuple[list[int], list[int], list[int]]] = []
        for admission in records[int(patient)]:
            rows.append(
                {
                    "diagnoses": list(admission[0]),
                    "procedures": list(admission[1]),
                    "history": list(history),
                    "_medications": list(admission[2]),
                }
            )
            history.append((list(admission[0]), list(admission[1]), list(admission[2])))
    return rows


def _validate_vocab(
    records: Sequence[Any], voc: dict[str, Any], ddi: np.ndarray, patients: Sequence[int]
) -> tuple[int, int]:
    dx = voc["diag_voc"]
    proc = voc["pro_voc"]
    med = voc["med_voc"]
    med_ids = set(int(k) for k in med.idx2word)
    if med_ids != set(range(MEDICATIONS)):
        raise RuntimeError("medication vocabulary IDs are not the exact canonical 131 IDs")
    dx_ids = set(int(k) for k in dx.idx2word)
    proc_ids = set(int(k) for k in proc.idx2word)
    if dx_ids != set(range(len(dx_ids))) or proc_ids != set(range(len(proc_ids))):
        raise RuntimeError("diagnosis/procedure vocabulary IDs are not contiguous canonical IDs")
    for patient_index in patients:
        patient = records[int(patient_index)]
        for visit in patient:
            if any(int(x) not in dx_ids for x in visit[0]) or any(
                int(x) not in proc_ids for x in visit[1]
            ):
                raise RuntimeError(
                    "record contains a diagnosis/procedure ID absent from exact vocabulary"
                )
            if any(int(x) < 0 or int(x) >= MEDICATIONS for x in visit[2]):
                raise RuntimeError(
                    "record contains medication ID outside exact 131-item vocabulary"
                )
    ddi = np.asarray(ddi, dtype=np.float32)
    if (
        ddi.shape != (MEDICATIONS, MEDICATIONS)
        or not np.isfinite(ddi).all()
        or not np.array_equal(ddi, ddi.T)
        or np.any(np.diag(ddi) != 0)
    ):
        raise RuntimeError("DDI must be finite, symmetric, and zero-diagonal 131 by 131")
    return len(dx_ids), len(proc_ids)


def _align(rows: Sequence[dict[str, Any]], targets: np.ndarray, name: str) -> None:
    if targets.ndim != 2 or targets.shape[1] != MEDICATIONS or len(rows) != targets.shape[0]:
        raise RuntimeError(name + " targets are not aligned with canonical [visits,131] data")
    if not np.isfinite(targets).all() or not np.isin(targets, (0.0, 1.0)).all():
        raise RuntimeError(name + " targets are not finite binary values")
    for index, row in enumerate(rows):
        expected = np.zeros(MEDICATIONS, dtype=np.float32)
        expected[[int(x) for x in row["_medications"]]] = 1.0
        if not np.array_equal(expected, targets[index]):
            raise RuntimeError(name + " target mismatch at row " + str(index))


def _metric_jaccard(targets: np.ndarray, logits: np.ndarray) -> float:
    predictions = [set(np.flatnonzero(row >= LOGIT_THRESHOLD)) for row in logits]
    total = 0.0
    target_sets = target_sets_from_matrix(targets)
    for index, pred in enumerate(predictions):
        target = target_sets[index]
        union = target | pred
        total += 1.0 if not union else len(target & pred) / len(union)
    return total / len(predictions)


def _predict(
    model: torch.nn.Module,
    rows: Sequence[dict[str, Any]],
    targets: np.ndarray,
    ddi: np.ndarray,
    dx: int,
    proc: int,
    device: torch.device,
    full_metrics: bool = True,
) -> tuple[np.ndarray, dict[str, float]]:
    model.eval()
    output: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch = pack_inputs(rows[start : start + BATCH_SIZE], dx, proc)
            batch = {key: value.to(device) for key, value in batch.items()}
            output.append(model(batch).cpu().numpy())
    logits = np.concatenate(output, axis=0)
    if not np.isfinite(logits).all():
        raise RuntimeError("non-finite model logits")
    if not full_metrics:
        with torch.no_grad():
            bce = torch.nn.functional.binary_cross_entropy_with_logits(
                torch.from_numpy(logits), torch.from_numpy(targets)
            )
        return logits, {"jaccard": _metric_jaccard(targets, logits), "bce": float(bce.item())}
    preds = [set(np.flatnonzero(row >= LOGIT_THRESHOLD)) for row in logits]
    metrics = evaluate_surface(target_sets_from_matrix(targets), preds, logits, ddi)
    metrics["nll"] = float(
        torch.nn.functional.binary_cross_entropy_with_logits(
            torch.from_numpy(logits), torch.from_numpy(targets)
        ).item()
    )
    return logits, metrics


def _git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path(__file__).resolve().parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def _git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _require_clean_source(source_revision: str) -> Path:
    root = _git_root()
    actual_revision = _git_revision(root)
    if actual_revision != source_revision:
        raise RuntimeError("source revision does not match git HEAD")
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise RuntimeError("run checkout is not clean")
    return root


def _scientific_config(variant: str, numeric_policy: dict[str, object]) -> dict[str, Any]:
    del variant
    return {
        "medications": MEDICATIONS,
        "hidden_dim": DIM,
        "clinical_attention_blocks": LAYERS,
        "heads": HEADS,
        "ffn_dim": FF_DIM,
        "batch_size_visits": BATCH_SIZE,
        "epochs": EPOCHS,
        "seed": SEED,
        "optimizer": "AdamW",
        "learning_rate": LR,
        "weight_decay": WEIGHT_DECAY,
        "betas": [0.9, 0.999],
        "eps": 1e-8,
        "gradient_clip": GRADIENT_CLIP,
        "decoder": "sigmoid probability >= 0.35",
        "decoder_threshold": THRESHOLD,
        "loss": "BCE + 0.05 * normalized DDI penalty",
        "ddi_weight": DDI_WEIGHT,
        "numeric_policy": numeric_policy,
    }


def _write_progress(output: Path, state: dict[str, Any]) -> None:
    temporary = output / "progress.json.tmp"
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temporary, output / "progress.json")


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.source_revision:
        raise RuntimeError("--source-revision is required")
    git_root = _require_clean_source(args.source_revision)
    snapshot = args.snapshot_root.resolve()
    root = args.train_dev_root.resolve()
    out = args.output_dir.resolve()
    if git_root == out or git_root in out.parents:
        raise RuntimeError("output directory must be outside the run checkout")
    if snapshot.name != SNAPSHOT_IDENTITY:
        raise RuntimeError("snapshot root identity does not match the canonical MICA snapshot")
    if root.name != TRAIN_DEV_IDENTITY:
        raise RuntimeError("Train/Dev root identity does not match the canonical MICA split")
    if not snapshot.is_dir() or not root.is_dir():
        raise RuntimeError("snapshot and Train/Dev roots must exist")

    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    train_patients = tuple(range(split))
    dev_patients = tuple(i for i in range(split, len(records)) if gate01_dev(i))
    if (len(records), len(train_patients), len(dev_patients)) != (6350, 4233, 1004):
        raise RuntimeError("canonical patient split counts are not 6350/4233/1004")
    dx, proc = _validate_vocab(records, voc, ddi, (*train_patients, *dev_patients))
    train = _rows(records, train_patients)
    dev = _rows(records, dev_patients)
    train_targets = _load(root, "train_targets.npy")
    dev_targets = _load(root, "dev_targets.npy")
    dev_scores = _load(root, "dev_scores.npy")
    _align(train, train_targets, "Train")
    _align(dev, dev_targets, "Dev")
    if (len(train), len(dev)) != (10489, 2130):
        raise RuntimeError("canonical visit counts are not 10489/2130")
    if dev_scores.shape != dev_targets.shape or not np.isfinite(dev_scores).all():
        raise RuntimeError("dev_scores is not a finite canonical [visits,131] array")
    split_info = {
        "train_patients": len(train_patients),
        "dev_patients": len(dev_patients),
        "train_visits": len(train),
        "dev_visits": len(dev),
    }
    for row in train + dev:
        row.pop("_medications", None)

    numeric_policy = configure_numeric_policy()
    config = _scientific_config(args.variant, numeric_policy)
    progress: list[dict[str, Any]] = []
    progress_state: dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "status": "preflight_complete",
        "variant": args.variant,
        "source_revision": args.source_revision,
        "config": config,
        "split": split_info,
        "completed_epochs": 0,
        "selected_epoch": None,
        "selected_dev_jaccard": None,
        "epoch_60_dev_metrics": None,
        "epochs": progress,
    }
    if args.preflight_only:
        return {
            "preflight_only": True,
            "source_revision": args.source_revision,
            "config": config,
            "split": split_info,
        }
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output directory is not empty")
    out.mkdir(parents=True, exist_ok=True)
    _write_progress(out, progress_state)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for MICA experiment execution")

    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    _seed(SEED)
    model = MICA(dx, proc, args.variant).to(device)
    model.initialize_prevalence(torch.from_numpy(train_targets.mean(0)).to(device))
    ddi_tensor = torch.from_numpy(ddi).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LR,
        weight_decay=WEIGHT_DECAY,
        betas=(0.9, 0.999),
        eps=1e-8,
    )
    best_j = float("-inf")
    best_epoch = None
    best_state = None
    best_dev_logits = None
    best_dev_metrics = None
    start_time = time.time()
    generator = np.random.RandomState(SEED)
    progress_state["status"] = "running"
    _write_progress(out, progress_state)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = generator.permutation(len(train))
        totals = [0.0, 0.0, 0.0, 0]
        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start : start + BATCH_SIZE]
            batch = {
                key: value.to(device)
                for key, value in pack_inputs([train[int(i)] for i in indices], dx, proc).items()
            }
            target = torch.from_numpy(train_targets[indices]).to(device)
            optimizer.zero_grad(set_to_none=True)
            loss, bce, ddi_loss = objective(model(batch), target, ddi_tensor)
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            size = len(indices)
            totals[0] += float(loss.item()) * size
            totals[1] += float(bce.item()) * size
            totals[2] += float(ddi_loss.item()) * size
            totals[3] += size
        dev_logits, dev_metrics = _predict(model, dev, dev_targets, ddi, dx, proc, device)
        jaccard = float(dev_metrics["jaccard"])
        entry = {
            "epoch": epoch,
            "train_loss": totals[0] / totals[3],
            "train_bce": totals[1] / totals[3],
            "train_ddi": totals[2] / totals[3],
            "dev_metrics": dev_metrics,
            "elapsed_seconds": time.time() - start_time,
            "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        }
        progress.append(entry)
        if jaccard > best_j:
            best_j = jaccard
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            best_dev_logits = dev_logits.copy()
            best_dev_metrics = dict(dev_metrics)
            torch.save(best_state, out / "selected_checkpoint.pt")
        progress_state["completed_epochs"] = epoch
        progress_state["selected_epoch"] = best_epoch
        progress_state["selected_dev_jaccard"] = best_j
        progress_state["epoch_60_dev_metrics"] = dev_metrics if epoch == EPOCHS else None
        _write_progress(out, progress_state)

    if (
        best_state is None
        or best_epoch is None
        or best_dev_logits is None
        or best_dev_metrics is None
    ):
        raise RuntimeError("no complete Dev checkpoint was selected")
    model.load_state_dict(best_state)
    train_logits, train_metrics = _predict(model, train, train_targets, ddi, dx, proc, device)
    dev_logits = best_dev_logits
    dev_metrics = best_dev_metrics
    np.savez_compressed(
        out / "selected_predictions.npz",
        train_logits=train_logits,
        train_probabilities=1.0 / (1.0 + np.exp(-train_logits)),
        train_targets=train_targets,
        dev_logits=dev_logits,
        dev_probabilities=1.0 / (1.0 + np.exp(-dev_logits)),
        dev_targets=dev_targets,
    )
    epoch_60_dev_metrics = progress[-1]["dev_metrics"]
    result = {
        "schema_version": 1,
        "status": "complete",
        "variant": args.variant,
        "source_revision": args.source_revision,
        "config": config,
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "split": split_info,
        "completed_epochs": len(progress),
        "selected_epoch": best_epoch,
        "selected_checkpoint": {"Train": train_metrics, "Dev": dev_metrics},
        "epoch_60": {"Dev": epoch_60_dev_metrics},
        "metrics": {"Train": train_metrics, "Dev": dev_metrics},
        "progress": progress,
        "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        "wall_time_seconds": time.time() - start_time,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "numeric_policy": numeric_policy,
        },
        "frozen_molerec_dev": evaluate_surface(
            target_sets_from_matrix(dev_targets),
            [set(np.flatnonzero(x >= 0.0)) for x in dev_scores],
            dev_scores,
            ddi,
        ),
        "historical_graphrefine_samek": {
            "jaccard": 0.533650,
            "f1": 0.687394,
            "prauc": 0.784240,
            "ddi_rate": 0.073328,
            "mean_medication_count": 21.5451,
            "diagnostic_only": True,
        },
        "source_bound_references": {
            "snapshot": SNAPSHOT_IDENTITY,
            "train_dev": TRAIN_DEV_IDENTITY,
        },
    }
    progress_state["status"] = "complete"
    progress_state["epoch_60_dev_metrics"] = epoch_60_dev_metrics
    _write_progress(out, progress_state)
    (out / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=MICA.VARIANTS, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
