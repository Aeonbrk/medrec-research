#!/usr/bin/env python3
"""Run one of the six bounded MICA-v2 Train/Dev screening lanes."""

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mica_v2 import (
    DIM,
    FF_DIM,
    HEADS,
    LAYERS,
    MEDICATIONS,
    SAFE_RATE,
    VARIANTS,
    MICAv2,
    base_objective,
    coarse_pack_inputs,
    configure_numeric_policy,
    pack_dual_evidence,
    pack_fine_history,
    parameter_count,
    safe_rank_objective,
    safe_swap,
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
LOGIT_THRESHOLD = float(np.log(0.35 / (1.0 - 0.35)))
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
    med_ids = set(int(key) for key in med.idx2word)
    if med_ids != set(range(MEDICATIONS)):
        raise RuntimeError("medication vocabulary IDs are not the exact canonical 131 IDs")
    dx_ids = set(int(key) for key in dx.idx2word)
    proc_ids = set(int(key) for key in proc.idx2word)
    if dx_ids != set(range(len(dx_ids))) or proc_ids != set(range(len(proc_ids))):
        raise RuntimeError("diagnosis/procedure vocabulary IDs are not contiguous canonical IDs")
    for patient_index in patients:
        for visit in records[int(patient_index)]:
            if any(int(code) not in dx_ids for code in visit[0]) or any(
                int(code) not in proc_ids for code in visit[1]
            ):
                raise RuntimeError(
                    "record contains a diagnosis/procedure ID absent from exact vocabulary"
                )
            if any(int(code) < 0 or int(code) >= MEDICATIONS for code in visit[2]):
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
        expected[[int(code) for code in row["_medications"]]] = 1.0
        if not np.array_equal(expected, targets[index]):
            raise RuntimeError(name + " target mismatch at row " + str(index))


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
    if _git_revision(root) != source_revision:
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
    mechanisms = {
        "core": "MICA-Core DrugQuery anchor",
        "fine_history": "per-code historical D/P/M tokens, no truncation",
        "dual_evidence": "tied T on separate current/history streams with one shared gate",
        "safe_rank": "Core base loss plus detached SafeSwap candidate pair ranking",
        "self_only": "medication context block with self-only attention mask",
        "set_context": "medication context block with full all-to-all attention",
    }
    return {
        "variant": variant,
        "mechanism": mechanisms[variant],
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
        "decoder": "SafeSwap" if variant in {"safe_rank"} else "sigmoid probability >= 0.35",
        "decoder_threshold": 0.35,
        "loss": "BCE + 0.05 * normalized DDI penalty"
        if variant != "safe_rank"
        else "BCE + 0.05 * normalized DDI penalty + 0.1 * SafeSwap candidate ranking",
        "ddi_weight": DDI_WEIGHT,
        "safe_rate": SAFE_RATE if variant == "safe_rank" else None,
        "rank_weight": 0.1 if variant == "safe_rank" else None,
        "numeric_policy": numeric_policy,
    }


def _write_progress(output: Path, state: dict[str, Any]) -> None:
    temporary = output / "progress.json.tmp"
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temporary, output / "progress.json")


def _move_to_device(batch: Any, device: torch.device) -> Any:
    if isinstance(batch, dict):
        return {key: _move_to_device(value, device) for key, value in batch.items()}
    if isinstance(batch, torch.Tensor):
        return batch.to(device)
    return batch


def _pack(rows: Sequence[dict[str, Any]], dx: int, proc: int, variant: str) -> dict[str, Any]:
    if variant == "fine_history":
        return pack_fine_history(rows, dx, proc)
    if variant == "dual_evidence":
        return pack_dual_evidence(rows, dx, proc)
    return coarse_pack_inputs(rows, dx, proc)


def _decode(logits: np.ndarray, decoder: str, ddi: np.ndarray) -> list[set[int]]:
    if decoder == "SafeSwap":
        return [set(safe_swap(row.tolist(), ddi)) for row in logits]
    return [set(int(index) for index in np.flatnonzero(row >= LOGIT_THRESHOLD)) for row in logits]


def _surface(
    logits: np.ndarray,
    targets: np.ndarray,
    ddi: np.ndarray,
    decoder: str,
) -> dict[str, float]:
    predictions = _decode(logits, decoder, ddi)
    metrics = evaluate_surface(target_sets_from_matrix(targets), predictions, logits, ddi)
    metrics["nll"] = float(
        torch.nn.functional.binary_cross_entropy_with_logits(
            torch.from_numpy(logits), torch.from_numpy(targets)
        ).item()
    )
    return metrics


def _predict(
    model: torch.nn.Module,
    rows: Sequence[dict[str, Any]],
    targets: np.ndarray,
    ddi: np.ndarray,
    dx: int,
    proc: int,
    device: torch.device,
    variant: str,
) -> tuple[np.ndarray, dict[str, float]]:
    model.eval()
    output: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(rows), BATCH_SIZE):
            batch = _move_to_device(
                _pack(rows[start : start + BATCH_SIZE], dx, proc, variant), device
            )
            output.append(model(batch).cpu().numpy())
    logits = np.concatenate(output, axis=0)
    if not np.isfinite(logits).all():
        raise RuntimeError("non-finite model logits")
    decoder = "SafeSwap" if variant == "safe_rank" else "ordinary"
    return logits, _surface(logits, targets, ddi, decoder)


def _train_batch_objective(
    variant: str,
    logits: torch.Tensor,
    target: torch.Tensor,
    ddi: torch.Tensor,
    ddi_rows: Sequence[Sequence[float]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    if variant == "safe_rank":
        return safe_rank_objective(logits, target, ddi, ddi_rows)
    loss, bce, ddi_loss = base_objective(logits, target, ddi)
    return loss, bce, ddi_loss, logits.sum() * 0.0


def _load_data(
    snapshot: Path, root: Path
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    int,
    int,
    dict[str, int],
    dict[str, Any],
]:
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
    return train, dev, train_targets, dev_targets, dev_scores, ddi, dx, proc, split_info, voc


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.variant not in VARIANTS:
        raise RuntimeError("unknown MICA-v2 variant")
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

    train, dev, train_targets, dev_targets, dev_scores, ddi, dx, proc, split_info, _voc = (
        _load_data(snapshot, root)
    )
    numeric_policy = configure_numeric_policy()
    config = _scientific_config(args.variant, numeric_policy)
    model = MICAv2(dx, proc, args.variant)
    count = parameter_count(model)
    if args.preflight_only:
        return {
            "preflight_only": True,
            "source_revision": args.source_revision,
            "variant": args.variant,
            "config": config,
            "parameter_count": count,
            "split": split_info,
            "medication_vocabulary": "voc_final.pkl: med_voc IDs 0..130",
        }
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("output directory is not empty")
    out.mkdir(parents=True, exist_ok=True)
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
    _write_progress(out, progress_state)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for MICA-v2 experiment execution")

    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    _seed(SEED)
    model = MICAv2(dx, proc, args.variant).to(device)
    model.initialize_prevalence(torch.from_numpy(train_targets.mean(0)).to(device))
    ddi_tensor = torch.from_numpy(ddi).to(device)
    ddi_rows = tuple(tuple(int(bool(value)) for value in row) for row in ddi.tolist())
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
    epoch_60_dev_logits = None
    start_time = time.time()
    generator = np.random.RandomState(SEED)
    progress_state["status"] = "running"
    _write_progress(out, progress_state)

    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = generator.permutation(len(train))
        totals = [0.0, 0.0, 0.0, 0.0, 0]
        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start : start + BATCH_SIZE]
            batch = _move_to_device(
                _pack([train[int(index)] for index in indices], dx, proc, args.variant), device
            )
            target = torch.from_numpy(train_targets[indices]).to(device)
            optimizer.zero_grad(set_to_none=True)
            loss, bce, ddi_loss, rank_loss = _train_batch_objective(
                args.variant, model(batch), target, ddi_tensor, ddi_rows
            )
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            size = len(indices)
            totals[0] += float(loss.item()) * size
            totals[1] += float(bce.item()) * size
            totals[2] += float(ddi_loss.item()) * size
            totals[3] += float(rank_loss.item()) * size
            totals[4] += size
        dev_logits, dev_metrics = _predict(
            model, dev, dev_targets, ddi, dx, proc, device, args.variant
        )
        jaccard = float(dev_metrics["jaccard"])
        entry = {
            "epoch": epoch,
            "train_loss": totals[0] / totals[4],
            "train_bce": totals[1] / totals[4],
            "train_ddi": totals[2] / totals[4],
            "train_rank": totals[3] / totals[4],
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
        if epoch == EPOCHS:
            epoch_60_dev_logits = dev_logits.copy()
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
    if epoch_60_dev_logits is None:
        raise RuntimeError("epoch-60 Dev logits were not captured")
    model.load_state_dict(best_state)
    train_logits, train_metrics = _predict(
        model, train, train_targets, ddi, dx, proc, device, args.variant
    )
    dev_logits = best_dev_logits
    dev_metrics = best_dev_metrics
    np.savez_compressed(
        out / "selected_predictions.npz",
        train_logits=train_logits,
        train_targets=train_targets,
        dev_logits=dev_logits,
        dev_targets=dev_targets,
    )
    epoch_60_dev_metrics = progress[-1]["dev_metrics"]
    safe_pto = None
    if args.variant == "core":
        safe_pto = {
            "selected_epoch": best_epoch,
            "Train": _surface(train_logits, train_targets, ddi, "SafeSwap"),
            "Dev": _surface(dev_logits, dev_targets, ddi, "SafeSwap"),
            "epoch_60_Dev": _surface(epoch_60_dev_logits, dev_targets, ddi, "SafeSwap"),
        }
    result = {
        "schema_version": 1,
        "status": "complete",
        "variant": args.variant,
        "source_revision": args.source_revision,
        "config": config,
        "parameter_count": count,
        "split": split_info,
        "completed_epochs": len(progress),
        "selected_epoch": best_epoch,
        "selected_checkpoint": {"Train": train_metrics, "Dev": dev_metrics},
        "epoch_60": {"Dev": epoch_60_dev_metrics},
        "metrics": {"Train": train_metrics, "Dev": dev_metrics},
        "safe_pto": safe_pto,
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
            [set(np.flatnonzero(row >= 0.0)) for row in dev_scores],
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
            "medication_vocabulary": "voc_final.pkl: med_voc IDs 0..130",
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
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
