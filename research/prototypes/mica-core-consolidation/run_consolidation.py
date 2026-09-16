#!/usr/bin/env python3
"""Run the frozen Stage -1B recipe arms or Stage -1C intrinsic controls.

This runner is intentionally additive.  It imports the historical MICA data
contract and evaluator, and writes private run outputs only to the caller's
directory (which must be outside the repository checkout).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any

import dill
import numpy as np
import torch

MICA_DIR = Path(__file__).resolve().parents[1] / "mica"
sys.path.insert(0, str(MICA_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from consolidation import ConsolidationMICA  # noqa: E402
from mica import (  # noqa: E402
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
from run_mica import (  # noqa: E402
    _align,
    _load,
    _predict,
    _require_clean_source,
    _rows,
    _validate_vocab,
)

SEED = 20260914
EPOCHS = 60
BATCH_SIZE = 16
ANCHOR_LR = 3e-4
LOWER_LR = 1e-4
COSINE_ETA_MIN = 3e-6
WEIGHT_DECAY = 1e-4
DDI_WEIGHT = 0.05
GRADIENT_CLIP = 5.0
SNAPSHOT_IDENTITY = "molerec-table1-c721-www23"
TRAIN_DEV_IDENTITY = "gate01-train-dev-5752596a-20260913a"
PROGRESS_SCHEMA_VERSION = 1
RECIPES = ("t0_current_anchor", "t1_lower_constant", "t2_cosine_decay")
CONTROLS = ConsolidationMICA.CONTROLS


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    configure_numeric_policy()


def _gate01_dev(patient_id: int) -> bool:
    # Keep the same patient-level Train/Dev surface as the historical runner.
    import hashlib

    value = int.from_bytes(
        hashlib.sha256(("idea008-gate01-v1:" + str(patient_id)).encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _load_data(
    snapshot: Path, train_dev: Path
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
]:
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    train_patients = tuple(range(split))
    dev_patients = tuple(i for i in range(split, len(records)) if _gate01_dev(i))
    if (len(records), len(train_patients), len(dev_patients)) != (6350, 4233, 1004):
        raise RuntimeError("canonical patient split counts are not 6350/4233/1004")
    dx, proc = _validate_vocab(records, voc, ddi, (*train_patients, *dev_patients))
    train = _rows(records, train_patients)
    dev = _rows(records, dev_patients)
    train_targets = _load(train_dev, "train_targets.npy")
    dev_targets = _load(train_dev, "dev_targets.npy")
    dev_scores = _load(train_dev, "dev_scores.npy")
    _align(train, train_targets, "Train")
    _align(dev, dev_targets, "Dev")
    if (len(train), len(dev)) != (10489, 2130):
        raise RuntimeError("canonical visit counts are not 10489/2130")
    if dev_scores.shape != dev_targets.shape or not np.isfinite(dev_scores).all():
        raise RuntimeError("dev_scores is not a finite canonical [visits,131] array")
    for row in train + dev:
        row.pop("_medications", None)
    split_info = {
        "train_patients": len(train_patients),
        "dev_patients": len(dev_patients),
        "train_visits": len(train),
        "dev_visits": len(dev),
    }
    return train, dev, train_targets, dev_targets, dev_scores, ddi, dx, proc, split_info


def _config(recipe: str, control: str) -> dict[str, Any]:
    if recipe not in RECIPES:
        raise ValueError(f"recipe must be one of {RECIPES}")
    if control not in CONTROLS:
        raise ValueError(f"control must be one of {CONTROLS}")
    if recipe == "t0_current_anchor":
        lr = ANCHOR_LR
        schedule = "constant"
    elif recipe == "t1_lower_constant":
        lr = LOWER_LR
        schedule = "constant"
    else:
        lr = ANCHOR_LR
        schedule = "cosine_decay"
    return {
        "stage": "STAGE -1B" if control == "core" else "STAGE -1C",
        "recipe": recipe,
        "control": control,
        "medications": MEDICATIONS,
        "hidden_dim": DIM,
        "clinical_attention_blocks": LAYERS if control != "one_clinical_block" else 1,
        "heads": HEADS,
        "ffn_dim": FF_DIM,
        "batch_size_visits": BATCH_SIZE,
        "epochs": EPOCHS,
        "seed": SEED,
        "optimizer": "AdamW",
        "learning_rate": lr,
        "schedule": schedule,
        "cosine_eta_min": COSINE_ETA_MIN if schedule == "cosine_decay" else None,
        "weight_decay": WEIGHT_DECAY,
        "betas": [0.9, 0.999],
        "eps": 1e-8,
        "gradient_clip": GRADIENT_CLIP,
        "decoder": "sigmoid probability >= 0.35",
        "decoder_threshold": THRESHOLD,
        "loss": "BCE + 0.05 * normalized DDI penalty",
        "ddi_weight": DDI_WEIGHT,
    }


def _write_progress(output: Path, state: dict[str, Any]) -> None:
    temporary = output / "progress.json.tmp"
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, output / "progress.json")


def _model(control: str, dx: int, proc: int) -> torch.nn.Module:
    if control == "core":
        return MICA(dx, proc, "drug_query")
    return ConsolidationMICA(dx, proc, control)


def _preflight(
    *,
    snapshot: Path,
    train_dev: Path,
    control: str,
    recipe: str,
    source_revision: str,
) -> dict[str, Any]:
    _require_clean_source(source_revision)
    if snapshot.name != SNAPSHOT_IDENTITY:
        raise RuntimeError("snapshot root identity does not match the canonical MICA snapshot")
    if train_dev.name != TRAIN_DEV_IDENTITY:
        raise RuntimeError("Train/Dev root identity does not match the canonical MICA split")
    train, _dev, train_targets, _dev_targets, _scores, ddi, dx, proc, split = _load_data(
        snapshot, train_dev
    )
    _seed(SEED)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for MICA experiment execution")
    device = torch.device("cuda")
    model = _model(control, dx, proc).to(device)
    model.initialize_prevalence(torch.from_numpy(train_targets.mean(0)).to(device))
    rows = train[: min(BATCH_SIZE, len(train))]
    batch = {key: value.to(device) for key, value in pack_inputs(rows, dx, proc).items()}
    target = torch.from_numpy(train_targets[: len(rows)]).to(device)
    ddi_tensor = torch.from_numpy(ddi).to(device)
    logits = model(batch)
    loss, _bce, _ddi_loss = objective(logits, target, ddi_tensor)
    if not torch.isfinite(logits).all() or not torch.isfinite(loss):
        raise RuntimeError("preflight produced non-finite logits or loss")
    loss.backward()
    if not any(
        param.grad is not None and torch.isfinite(param.grad).all() for param in model.parameters()
    ):
        raise RuntimeError("preflight produced no finite parameter gradient")
    return {
        "preflight_only": True,
        "source_revision": source_revision,
        "config": _config(recipe, control),
        "split": split,
        "parameter_count": sum(param.numel() for param in model.parameters()),
        "cuda_device": torch.cuda.current_device(),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.source_revision:
        raise RuntimeError("--source-revision is required")
    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    output = args.output_dir.resolve()
    git_root = _require_clean_source(args.source_revision)
    if git_root == output or git_root in output.parents:
        raise RuntimeError("output directory must be outside the run checkout")
    if not snapshot.is_dir() or not train_dev.is_dir():
        raise RuntimeError("snapshot and Train/Dev roots must exist")
    if snapshot.name != SNAPSHOT_IDENTITY:
        raise RuntimeError("snapshot root identity does not match the canonical MICA snapshot")
    if train_dev.name != TRAIN_DEV_IDENTITY:
        raise RuntimeError("Train/Dev root identity does not match the canonical MICA split")
    if args.preflight_only:
        return _preflight(
            snapshot=snapshot,
            train_dev=train_dev,
            control=args.control,
            recipe=args.recipe,
            source_revision=args.source_revision,
        )
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("output directory is not empty")
    output.mkdir(parents=True, exist_ok=True)
    train, dev, train_targets, dev_targets, _dev_scores, ddi, dx, proc, split = _load_data(
        snapshot, train_dev
    )
    numeric_policy = configure_numeric_policy()
    config = _config(args.recipe, args.control)
    config["numeric_policy"] = numeric_policy
    state: dict[str, Any] = {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "status": "preflight_complete",
        "variant": "drug_query",
        "control": args.control,
        "recipe": args.recipe,
        "source_revision": args.source_revision,
        "config": config,
        "split": split,
        "completed_epochs": 0,
        "selected_epoch": None,
        "selected_dev_jaccard": None,
        "epoch_60_dev_metrics": None,
        "epochs": [],
    }
    _write_progress(output, state)
    _seed(SEED)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for MICA experiment execution")
    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    model = _model(args.control, dx, proc).to(device)
    model.initialize_prevalence(torch.from_numpy(train_targets.mean(0)).to(device))
    ddi_tensor = torch.from_numpy(ddi).to(device)
    lr = float(config["learning_rate"])
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY, betas=(0.9, 0.999), eps=1e-8
    )
    scheduler = (
        torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=COSINE_ETA_MIN)
        if args.recipe == "t2_cosine_decay"
        else None
    )
    best_j = float("-inf")
    best_epoch: int | None = None
    best_state: dict[str, torch.Tensor] | None = None
    best_dev_logits: np.ndarray | None = None
    best_dev_metrics: dict[str, float] | None = None
    generator = np.random.RandomState(SEED)
    start_time = time.time()
    state["status"] = "running"
    _write_progress(output, state)
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = generator.permutation(len(train))
        totals = [0.0, 0.0, 0.0, 0]
        epoch_lr = float(optimizer.param_groups[0]["lr"])
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
        if scheduler is not None:
            scheduler.step()
        entry = {
            "epoch": epoch,
            "learning_rate": epoch_lr,
            "train_loss": totals[0] / totals[3],
            "train_bce": totals[1] / totals[3],
            "train_ddi": totals[2] / totals[3],
            "dev_metrics": dev_metrics,
            "elapsed_seconds": time.time() - start_time,
            "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        }
        state["epochs"].append(entry)
        jaccard = float(dev_metrics["jaccard"])
        if jaccard > best_j:
            best_j = jaccard
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }
            best_dev_logits = dev_logits.copy()
            best_dev_metrics = dict(dev_metrics)
            torch.save(best_state, output / "selected_checkpoint.pt")
        state["completed_epochs"] = epoch
        state["selected_epoch"] = best_epoch
        state["selected_dev_jaccard"] = best_j
        state["epoch_60_dev_metrics"] = dev_metrics if epoch == EPOCHS else None
        _write_progress(output, state)
    if (
        best_state is None
        or best_epoch is None
        or best_dev_logits is None
        or best_dev_metrics is None
    ):
        raise RuntimeError("no complete Dev checkpoint was selected")
    model.load_state_dict(best_state)
    train_logits, train_metrics = _predict(model, train, train_targets, ddi, dx, proc, device)
    np.savez_compressed(
        output / "selected_predictions.npz",
        train_logits=train_logits,
        train_targets=train_targets,
        dev_logits=best_dev_logits,
        dev_targets=dev_targets,
    )
    result = {
        "schema_version": 1,
        "status": "complete",
        "variant": "drug_query",
        "control": args.control,
        "recipe": args.recipe,
        "source_revision": args.source_revision,
        "config": config,
        "parameter_count": sum(param.numel() for param in model.parameters()),
        "split": split,
        "completed_epochs": len(state["epochs"]),
        "selected_epoch": best_epoch,
        "selected_checkpoint": {"Train": train_metrics, "Dev": best_dev_metrics},
        "epoch_60": {"Dev": state["epochs"][-1]["dev_metrics"]},
        "metrics": {"Train": train_metrics, "Dev": best_dev_metrics},
        "progress": state["epochs"],
        "cuda_peak_memory_mb": torch.cuda.max_memory_allocated(device) / 1048576.0,
        "wall_time_seconds": time.time() - start_time,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "numeric_policy": numeric_policy,
        },
        "source_bound_references": {
            "snapshot": SNAPSHOT_IDENTITY,
            "train_dev": TRAIN_DEV_IDENTITY,
        },
    }
    state["status"] = "complete"
    (output / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    _write_progress(output, state)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", choices=RECIPES, required=True)
    parser.add_argument("--control", choices=CONTROLS, default="core")
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
