#!/usr/bin/env python3
"""Strict result and log parser for SafeDrug-family Reproduction runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

# Delimiter-anchored checkpoint patterns per profile
CHECKPOINT_PATTERNS = {
    "safedrug": r"^Epoch_{epoch}_TARGET_.*\.model$",
    "retain": r"^Epoch_{epoch}_JA_.*\.model$",
    "leap-safedrug": r"^Epoch_{epoch}_JA_.*\.model$",
    "leap": r"^Epoch_{epoch}_JA_.*\.model$",
}

# Profile input file lists (relative to upstream root)
PROFILE_INPUTS = {
    "safedrug": [
        "data/output/records_final.pkl",
        "data/output/voc_final.pkl",
        "data/output/ddi_A_final.pkl",
        "data/output/ddi_mask_H.pkl",
        "data/output/atc3toSMILES.pkl",
    ],
    "retain": [
        "data/output/records_final.pkl",
        "data/output/voc_final.pkl",
        "data/output/ddi_A_final.pkl",
    ],
    "leap-safedrug": [
        "data/output/records_final.pkl",
        "data/output/voc_final.pkl",
        "data/output/ddi_A_final.pkl",
    ],
    "leap": [
        "data/output/records_final.pkl",
        "data/output/voc_final.pkl",
        "data/output/ddi_A_final.pkl",
    ],
}


class ResultValidationError(ValueError):
    """Raised when log parsing or result validation fails."""


def compute_sha256(file_path: Path) -> str:
    """Compute lowercase hex SHA-256 for a regular file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_train_log(log_text: str, expected_epochs: int = 50) -> dict[str, Any]:
    """Parse and validate 50-epoch training log."""
    epoch_matches = re.findall(r"(?:^|\n)epoch\s+(\d+)\s*-+", log_text)
    if not epoch_matches:
        raise ResultValidationError("Training log contains no epoch headers")

    observed_epochs = [int(ep) for ep in epoch_matches]
    expected_sequence = list(range(1, expected_epochs + 1))

    seq_idx = 0
    for ep in observed_epochs:
        if seq_idx < len(expected_sequence) and ep == expected_sequence[seq_idx]:
            seq_idx += 1

    if seq_idx < len(expected_sequence):
        raise ResultValidationError(
            f"Training log incomplete: observed {seq_idx}/{expected_epochs} ordered epoch headers"
        )

    best_epoch_matches = re.findall(r"best_epoch:\s*(\d+)", log_text)
    if not best_epoch_matches:
        raise ResultValidationError("Training log contains no 'best_epoch:' lines")

    final_best_epoch = int(best_epoch_matches[-1])
    if final_best_epoch <= 0:
        raise ResultValidationError(
            f"Invalid best_epoch {final_best_epoch}: best_epoch must be > 0"
        )
    if final_best_epoch >= expected_epochs:
        raise ResultValidationError(
            f"Invalid best_epoch {final_best_epoch}: best_epoch must be < {expected_epochs}"
        )

    return {
        "epochs_expected": expected_epochs,
        "epochs_completed": expected_epochs,
        "best_epoch": final_best_epoch,
    }


def select_checkpoint(
    checkpoint_dir: Path,
    best_epoch: int,
    profile: str,
    model_name: str,
) -> dict[str, Any]:
    """Select the unique checkpoint matching the best epoch in checkpoint_dir."""
    pattern_tmpl = CHECKPOINT_PATTERNS.get(profile)
    if not pattern_tmpl:
        raise ResultValidationError(f"Unknown profile '{profile}' for checkpoint selection")

    regex = re.compile(pattern_tmpl.format(epoch=best_epoch))

    if not checkpoint_dir.is_dir():
        raise ResultValidationError(f"Checkpoint directory '{checkpoint_dir}' does not exist")

    matching_files = [
        f
        for f in checkpoint_dir.iterdir()
        if f.is_file() and not f.is_symlink() and regex.fullmatch(f.name)
    ]

    if not matching_files:
        raise ResultValidationError(
            f"No checkpoint found matching epoch {best_epoch} (pattern {regex.pattern}) in {checkpoint_dir}"
        )
    if len(matching_files) > 1:
        names = [f.name for f in matching_files]
        raise ResultValidationError(
            f"Multiple checkpoints found matching epoch {best_epoch}: {names}"
        )

    selected_file = matching_files[0]
    sha256 = compute_sha256(selected_file)
    size_bytes = selected_file.stat().st_size

    return {
        "path": str(selected_file),
        "basename": selected_file.name,
        "relative_path": f"saved/{model_name}/{selected_file.name}",
        "sha256": sha256,
        "size_bytes": size_bytes,
        "best_epoch": best_epoch,
    }


def parse_test_log(log_text: str) -> dict[str, Any]:
    """Parse and validate 10-round Test log and upstream summary."""
    round_pattern = re.compile(
        r"DDI Rate:\s*([0-9.]+),\s*Jaccard:\s*([0-9.]+),\s*PRAUC:\s*([0-9.]+),\s*"
        r"AVG_PRC:\s*([0-9.]+),\s*AVG_RECALL:\s*([0-9.]+),\s*AVG_F1:\s*([0-9.]+),\s*AVG_MED:\s*([0-9.]+)"
    )

    test_rounds: list[dict[str, float]] = []
    for line in log_text.splitlines():
        match = round_pattern.search(line)
        if match:
            ddi_rate = float(match.group(1))
            jaccard = float(match.group(2))
            prauc = float(match.group(3))
            avg_p = float(match.group(4))
            avg_r = float(match.group(5))
            avg_f1 = float(match.group(6))
            avg_med = float(match.group(7))

            round_metrics = {
                "ddi_rate": ddi_rate,
                "jaccard": jaccard,
                "prauc": prauc,
                "avg_precision": avg_p,
                "avg_recall": avg_r,
                "avg_f1": avg_f1,
                "avg_medications": avg_med,
            }

            for k, v in round_metrics.items():
                if not math.isfinite(v):
                    raise ResultValidationError(f"Non-finite metric value for {k}: {v}")

            test_rounds.append(round_metrics)

    if len(test_rounds) != 10:
        raise ResultValidationError(f"Expected exactly 10 Test rounds, observed {len(test_rounds)}")

    metric_keys = [
        "ddi_rate",
        "jaccard",
        "prauc",
        "avg_precision",
        "avg_recall",
        "avg_f1",
        "avg_medications",
    ]
    harness_summary: dict[str, dict[str, float]] = {}
    for key in metric_keys:
        values = [r[key] for r in test_rounds]
        mean_val = sum(values) / len(values)
        std_val = math.sqrt(sum((x - mean_val) ** 2 for x in values) / len(values))
        harness_summary[key] = {
            "mean": mean_val,
            "std": std_val,
        }

    summary_pair_pattern = re.compile(r"([0-9.]+)\s*(?:\$\\pm\$|\\pm|\±)\s*([0-9.]+)\s*&")

    matching_summary_lines: list[tuple[str, list[tuple[str, str]]]] = []
    for line in log_text.splitlines():
        pairs = summary_pair_pattern.findall(line)
        if len(pairs) == 5:
            matching_summary_lines.append((line.strip(), pairs))

    if not matching_summary_lines:
        raise ResultValidationError("No upstream 5-metric summary line found in Test log")
    if len(matching_summary_lines) > 1:
        raise ResultValidationError(
            f"Multiple ({len(matching_summary_lines)}) upstream summary lines found in Test log"
        )

    raw_line, pairs = matching_summary_lines[0]
    summary_keys = ["ddi_rate", "jaccard", "avg_f1", "prauc", "avg_medications"]
    upstream_metrics: dict[str, dict[str, float]] = {}
    for key, (mean_str, std_str) in zip(summary_keys, pairs):
        m_val = float(mean_str)
        s_val = float(std_str)
        if not math.isfinite(m_val) or not math.isfinite(s_val):
            raise ResultValidationError(
                f"Non-finite summary value for {key}: {mean_str} +- {std_str}"
            )
        upstream_metrics[key] = {
            "mean": m_val,
            "std": s_val,
        }

    upstream_summary = {
        "raw_line": raw_line,
        "metrics": upstream_metrics,
    }

    return {
        "test_rounds": test_rounds,
        "upstream_summary": upstream_summary,
        "harness_summary": harness_summary,
    }


def atomic_write_json(file_path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON data via temporary file and replace."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_name(f"{file_path.name}.tmp.{os.getpid()}")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        temp_path.replace(file_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def build_result(
    *,
    baseline_id: str,
    status_data: dict[str, Any],
    source_revision: str,
    adapter_revision: str,
    environment_sha256: str,
    input_sha256: dict[str, str],
    training_data: dict[str, Any],
    checkpoint_data: dict[str, Any],
    test_data: dict[str, Any],
) -> dict[str, Any]:
    """Assemble complete schema_version: 1 result.json dictionary."""
    return {
        "schema_version": 1,
        "baseline_id": baseline_id,
        "status": status_data,
        "identity": {
            "source_revision": source_revision,
            "adapter_revision": adapter_revision,
            "environment_sha256": environment_sha256,
            "input_sha256": input_sha256,
        },
        "training": {
            "epochs_expected": training_data["epochs_expected"],
            "epochs_completed": training_data["epochs_completed"],
            "best_epoch": training_data["best_epoch"],
        },
        "checkpoint": {
            "relative_path": checkpoint_data["relative_path"],
            "sha256": checkpoint_data["sha256"],
            "size_bytes": checkpoint_data["size_bytes"],
            "best_epoch": checkpoint_data["best_epoch"],
        },
        "test_rounds": test_data["test_rounds"],
        "upstream_summary": test_data["upstream_summary"],
        "harness_summary": test_data["harness_summary"],
    }


def main() -> None:
    """CLI entrypoint for log parsing and result assembly."""
    parser = argparse.ArgumentParser(description="Parse SafeDrug family logs into result.json")
    parser.add_argument("--baseline-id", required=True, help="Baseline identifier")
    parser.add_argument("--model-name", required=True, help="Upstream model name")
    parser.add_argument("--train-log", type=Path, required=True, help="Path to training log")
    parser.add_argument("--test-log", type=Path, required=True, help="Path to test log")
    parser.add_argument("--status-json", type=Path, required=True, help="Path to status.json")
    parser.add_argument("--checkpoint-dir", type=Path, required=True, help="Checkpoint directory")
    parser.add_argument(
        "--output-json", type=Path, required=True, help="Path to output result.json"
    )
    parser.add_argument("--source-revision", required=True, help="Source git revision")
    parser.add_argument("--adapter-revision", required=True, help="Adapter revision")
    parser.add_argument("--environment-sha256", required=True, help="Environment SHA-256")
    parser.add_argument(
        "--input-hashes-json", type=Path, required=True, help="JSON file with input hashes"
    )

    args = parser.parse_args()

    try:
        with open(args.train_log, encoding="utf-8", errors="replace") as f:
            train_text = f.read()
        training_data = parse_train_log(train_text)

        checkpoint_data = select_checkpoint(
            args.checkpoint_dir,
            best_epoch=training_data["best_epoch"],
            profile=args.baseline_id,
            model_name=args.model_name,
        )

        with open(args.test_log, encoding="utf-8", errors="replace") as f:
            test_text = f.read()
        test_data = parse_test_log(test_text)

        with open(args.status_json, encoding="utf-8") as f:
            status_data = json.load(f)

        with open(args.input_hashes_json, encoding="utf-8") as f:
            input_sha256 = json.load(f)

        result = build_result(
            baseline_id=args.baseline_id,
            status_data=status_data,
            source_revision=args.source_revision,
            adapter_revision=args.adapter_revision,
            environment_sha256=args.environment_sha256,
            input_sha256=input_sha256,
            training_data=training_data,
            checkpoint_data=checkpoint_data,
            test_data=test_data,
        )

        atomic_write_json(args.output_json, result)
        print(f"Successfully generated {args.output_json}")

    except Exception as e:
        print(f"Error parsing results: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
