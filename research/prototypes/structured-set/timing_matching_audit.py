#!/usr/bin/env python3
"""Measure the Full matching objective cost without changing the formal run."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import dill
import numpy as np
import torch
from run_structured_set import (
    BATCH_SIZE,
    PROFILE_ID,
    SEED,
    SNAPSHOT_ID,
    _build_rows,
    _is_dev,
    _load_array,
    _model_rows,
    _seed_everything,
    _validate_data,
    _validate_profile,
)
from structured_set import StructuredSetModel, matching_cross_entropy, pack_inputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    snapshot = args.snapshot_root.resolve()
    train_dev = args.train_dev_root.resolve()
    _validate_profile(snapshot, train_dev)
    records = dill.load((snapshot / "records_final.pkl").open("rb"))
    voc = dill.load((snapshot / "voc_final.pkl").open("rb"))
    ddi = np.asarray(dill.load((snapshot / "ddi_A_final.pkl").open("rb")), dtype=np.float32)
    split = int(len(records) * 2 / 3)
    train_rows = _build_rows(records, tuple(range(split)))
    dev_rows = _build_rows(records, tuple(i for i in range(split, len(records)) if _is_dev(i)))
    train_targets = _load_array(train_dev, "train_targets.npy")
    dev_targets = _load_array(train_dev, "dev_targets.npy")
    dx_count, proc_count, _ = _validate_data(
        records,
        voc,
        train_rows,
        dev_rows,
        train_targets,
        dev_targets,
        ddi,
    )
    _seed_everything(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise RuntimeError("CUDA is required for the matching timing audit")
    model = StructuredSetModel(dx_count, proc_count).to(device)
    model.train()
    rows = _model_rows(train_rows[:BATCH_SIZE])
    packed = {
        key: value.to(device) for key, value in pack_inputs(rows, dx_count, proc_count).items()
    }
    target_sets = [
        tuple(int(i) for i in np.flatnonzero(row > 0.5)) for row in train_targets[:BATCH_SIZE]
    ]
    torch.cuda.synchronize()
    start = time.perf_counter()
    outputs = model(packed)
    loss, _labels = matching_cross_entropy(outputs, target_sets, 131, 131)
    if not torch.isfinite(loss):
        raise RuntimeError("matching loss is non-finite")
    loss.backward()
    torch.cuda.synchronize()
    seconds = time.perf_counter() - start
    args.output.resolve().write_text(
        json.dumps(
            {
                "status": "POST_RUN_MATCHING_TIMING_AUDIT_PASS",
                "profile_id": PROFILE_ID,
                "snapshot_id": SNAPSHOT_ID,
                "batch_size_visits": BATCH_SIZE,
                "matching_objective": "categorical CE after Hungarian matching with cost -u",
                "forward_backward_matching_batch_seconds": seconds,
                "loss_finite": True,
                "device": torch.cuda.get_device_name(0),
                "test_accessed": False,
                "timing_is_execution_check_only": True,
                "schedule_authority": "formal schedule was frozen before training; this audit is supplementary",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
