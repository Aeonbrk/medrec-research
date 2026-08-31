#!/usr/bin/env python3
"""Log parsing and checkpoint selection for archived SafeDrug."""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .safedrug_archived_data import ReproductionError
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from safedrug_archived_data import ReproductionError


ROUND_PATTERN = re.compile(
    r"DDI Rate:\s*([0-9.]+),\s*Jaccard:\s*([0-9.]+),\s*PRAUC:\s*([0-9.]+),\s*"
    r"AVG_PRC:\s*([0-9.]+),\s*AVG_RECALL:\s*([0-9.]+),\s*AVG_F1:\s*([0-9.]+),\s*"
    r"AVG_MED:\s*([0-9.]+)"
)


_VALIDATION_JACCARD_PATTERN = re.compile(
    r"(?i)(?:validation|valid|val)[^\n]{0,100}?(?:jaccard|ja)\s*[:=]\s*([0-9.eE+-]+)"
)
_VALIDATION_DDI_PATTERN = re.compile(
    r"(?i)(?:validation|valid|val)[^\n]{0,100}?(?:ddi(?:[ _-]*(?:rate|ratio))?)\s*[:=]\s*([0-9.eE+-]+)"
)


def parse_training_log(log_text: str, expected_epochs: int = 50) -> int:
    observed = [int(value) for value in re.findall(r"(?:^|\n)epoch\s+(\d+)\s*-+", log_text)]
    if observed != list(range(1, expected_epochs + 1)):
        raise ReproductionError(
            f"training log must contain exactly epochs 1-{expected_epochs}, observed {observed}"
        )
    best_epochs = [int(value) for value in re.findall(r"best_epoch:\s*(\d+)", log_text)]
    if len(best_epochs) != expected_epochs or not 0 <= best_epochs[-1] < expected_epochs:
        raise ReproductionError("training log has invalid best_epoch evidence")
    return best_epochs[-1]


def parse_validation_metrics(log_text: str) -> dict[str, float]:
    """Extract full-precision validation values for administrative selection."""
    jaccard = _VALIDATION_JACCARD_PATTERN.findall(log_text)
    ddi_rate = _VALIDATION_DDI_PATTERN.findall(log_text)
    if not jaccard or not ddi_rate:
        raise ReproductionError("training log must contain validation Jaccard and DDI metrics")
    values = {
        "validation_jaccard": float(jaccard[-1]),
        "validation_ddi_rate": float(ddi_rate[-1]),
    }
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values.values()):
        raise ReproductionError("validation metrics must be finite proportions")
    return values


def select_checkpoint(checkpoint_dir: Path, profile: Any, best_epoch: int) -> Path:
    matches = [
        path
        for path in checkpoint_dir.iterdir()
        if path.is_file()
        and not path.is_symlink()
        and (match := profile.checkpoint_pattern.fullmatch(path.name))
        and int(match.group(1)) == best_epoch
    ]
    if len(matches) != 1:
        raise ReproductionError(
            f"expected one {profile.baseline_id} checkpoint for epoch {best_epoch}, "
            f"observed {[path.name for path in matches]}"
        )
    return matches[0]


def parse_test_log(log_text: str) -> dict[str, Any]:
    rounds = []
    for match in ROUND_PATTERN.finditer(log_text):
        values = [float(value) for value in match.groups()]
        if not all(math.isfinite(value) for value in values):
            raise ReproductionError("test log contains a non-finite metric")
        rounds.append(
            {
                "ddi_rate": values[0],
                "jaccard": values[1],
                "prauc": values[2],
                "avg_precision": values[3],
                "avg_recall": values[4],
                "avg_f1": values[5],
                "avg_medications": values[6],
            }
        )
    if len(rounds) != 10:
        raise ReproductionError(f"expected exactly 10 test rounds, observed {len(rounds)}")
    summary_pairs = re.findall(r"([0-9.]+)\s*\$\\pm\$\s*([0-9.]+)\s*&", log_text)
    if len(summary_pairs) != 5:
        raise ReproductionError(
            f"expected one upstream 5-metric summary, observed {len(summary_pairs)} pairs"
        )
    summary = {}
    for name in ("ddi_rate", "jaccard", "avg_f1", "prauc", "avg_medications"):
        values = [round_data[name] for round_data in rounds]
        mean = sum(values) / len(values)
        summary[name] = {
            "mean": mean,
            "std": math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)),
        }
    summary_names = ("ddi_rate", "jaccard", "avg_f1", "prauc", "avg_medications")
    upstream_summary = {
        summary_names[index]: {"mean": float(mean), "std": float(std)}
        for index, (mean, std) in enumerate(summary_pairs)
    }
    for name, upstream_value in upstream_summary.items():
        harness_value = summary[name]
        maximum_round_value = max(abs(round_data[name]) for round_data in rounds)
        round_precision = (
            5e-5
            if maximum_round_value == 0
            else 0.5 * 10 ** (math.floor(math.log10(maximum_round_value)) - 3)
        )
        tolerance = round_precision + 5e-5 + 1e-12
        if (
            abs(upstream_value["mean"] - harness_value["mean"]) > tolerance
            or abs(upstream_value["std"] - harness_value["std"]) > tolerance
        ):
            raise ReproductionError(f"upstream summary disagrees with parsed rounds for {name}")
    return {
        "test_rounds": rounds,
        "harness_summary": summary,
        "upstream_summary": upstream_summary,
    }
