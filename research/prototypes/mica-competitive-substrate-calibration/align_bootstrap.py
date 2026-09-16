#!/usr/bin/env python3
"""Align a completed external Dev lane to source visit order and bootstrap it.

External runners that use packed recurrent batches may emit Dev rows sorted by
sequence length.  This private-plane utility reconstructs the frozen source
order, validates the target matrix, and emits only aggregate paired-bootstrap
evidence.  No patient-level arrays are written by the utility.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from stage1g_bootstrap import _aggregate, _bootstrap_delta, _metrics


def _gate01_dev(patient_id: int) -> bool:
    value = int.from_bytes(
        hashlib.sha256(("idea008-gate01-v1:" + str(patient_id)).encode()).digest()[:8],
        "big",
    )
    return value / float(2**64) < 0.5


def _miii_source(snapshot_root: Path, train_dev_root: Path) -> tuple[list[str], np.ndarray, np.ndarray]:
    import dill

    records = dill.load((snapshot_root / "records_final.pkl").open("rb"))
    split = int(len(records) * 2 / 3)
    patients = [index for index in range(split, len(records)) if _gate01_dev(index)]
    keys = [
        str(patient) + ":" + str(visit)
        for patient in patients
        for visit in range(len(records[patient]))
    ]
    target = np.asarray(np.load(train_dev_root / "dev_targets.npy"), dtype=np.float32)
    lengths = np.asarray(
        [visit + 1 for patient in patients for visit in range(len(records[patient]))],
        dtype=np.int64,
    )
    if len(keys) != 2130 or target.shape != (2130, 131):
        raise RuntimeError("MIMIC-III source Dev shape changed")
    return keys, target, lengths


def _miv_source(common_root: Path, mica_dir: Path) -> tuple[list[str], np.ndarray, np.ndarray]:
    keys: list[str] = []
    lengths: list[int] = []
    with (common_root / "dev_examples.private.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            example = json.loads(line)
            keys.append(str(example["subject_id"]) + ":" + str(example["current_visit_order"]))
            lengths.append(1 + len(example["input"]["history"]))
    target = np.asarray(np.load(mica_dir / "dev_targets.npy"), dtype=np.float32)
    if len(keys) != 76443 or target.shape != (76443, 131):
        raise RuntimeError("MIMIC-IV common131 source Dev shape changed")
    return keys, target, np.asarray(lengths, dtype=np.int64)


def _aligned_baseline(
    baseline_dir: Path, source_keys: list[str], source_lengths: np.ndarray
) -> tuple[np.ndarray, np.ndarray, str]:
    result = json.loads((baseline_dir / "result.json").read_text(encoding="utf-8"))
    raw_target = np.asarray(np.load(baseline_dir / "dev_targets.npy"), dtype=np.float32)
    raw_logits = np.asarray(np.load(baseline_dir / "dev_logits.npy"), dtype=np.float32)
    if raw_target.shape != raw_logits.shape or raw_logits.shape[1] != 131:
        raise RuntimeError("external Dev arrays have inconsistent shape")
    if raw_logits.shape[0] != len(source_keys):
        raise RuntimeError("external/source Dev visit counts differ")
    baseline = str(result["baseline"]).lower()
    if baseline == "molerec":
        order = np.arange(len(source_keys), dtype=np.int64)
        ordering = "source_order"
    elif baseline in {"armr", "gamenet", "retain"}:
        order = np.argsort(source_lengths, kind="stable")
        ordering = "global_stable_sequence_length_sort"
    else:
        raise RuntimeError("baseline ordering is not frozen for this family")
    target = np.empty_like(raw_target)
    logits = np.empty_like(raw_logits)
    target[order] = raw_target
    logits[order] = raw_logits
    return target, logits, ordering


def _load_ddi(path: Path) -> np.ndarray:
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return np.asarray(payload["matrix"], dtype=np.float32)
    import dill

    return np.asarray(dill.load(path.open("rb")), dtype=np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=("mimic_iii", "mimic_iv"), required=True)
    parser.add_argument("--mica-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--snapshot-root", type=Path)
    parser.add_argument("--train-dev-root", type=Path)
    parser.add_argument("--common-root", type=Path)
    parser.add_argument("--ddi", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260916)
    args = parser.parse_args()
    if args.dataset == "mimic_iii":
        if args.snapshot_root is None or args.train_dev_root is None:
            parser.error("MIMIC-III requires --snapshot-root and --train-dev-root")
        source_keys, target, lengths = _miii_source(
            args.snapshot_root.resolve(), args.train_dev_root.resolve()
        )
    else:
        if args.common_root is None:
            parser.error("MIMIC-IV requires --common-root")
        source_keys, target, lengths = _miv_source(args.common_root.resolve(), args.mica_dir.resolve())
    baseline_target, baseline_logits, ordering = _aligned_baseline(
        args.baseline_dir.resolve(), source_keys, lengths
    )
    mica_logits = np.asarray(
        np.load(args.mica_dir.resolve() / "selected_dev_logits.npy"), dtype=np.float32
    )
    if mica_logits.shape != target.shape or not np.array_equal(target, baseline_target):
        raise RuntimeError("MICA, baseline, and source targets are not exactly aligned")
    ddi = _load_ddi(args.ddi.resolve())
    mica_per_visit = _metrics(target, mica_logits, ddi, 0.35)
    baseline_result = json.loads(
        (args.baseline_dir.resolve() / "result.json").read_text(encoding="utf-8")
    )
    threshold = float(baseline_result["config"]["threshold"])
    baseline_per_visit = _metrics(target, baseline_logits, ddi, threshold)
    indices = np.arange(target.shape[0])
    output: dict[str, Any] = {
        "schema_version": 1,
        "dataset": args.dataset,
        "baseline_id": baseline_result["baseline"],
        "surface": "canonical131" if args.dataset == "mimic_iii" else "common131",
        "ordering_correction": ordering,
        "source_visit_count": int(target.shape[0]),
        "mica": _aggregate(mica_per_visit, indices),
        "baseline": _aggregate(baseline_per_visit, indices),
        "bootstrap": _bootstrap_delta(
            mica_per_visit, baseline_per_visit,
            np.asarray([key.split(":", 1)[0] for key in source_keys], dtype="U128"),
            args.resamples,
            args.seed,
        ),
        "test_loaded": False,
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
