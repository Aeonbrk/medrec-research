#!/usr/bin/env python3
"""Log parsing and checkpoint selection for MoleRec Table 1 reproduction."""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .molerec_contract import Profile, ReproductionError
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from molerec_contract import Profile, ReproductionError


_FORMAL_ROUND_PATTERN = re.compile(
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
    epochs = [int(v) for v in re.findall(r"(?:epoch|Epoch)\s*:?\s*(\d+)", log_text)]
    if not epochs:
        raise ReproductionError("training log contains no epoch lines")
    if len(set(epochs)) < expected_epochs:
        raise ReproductionError(
            f"training log has fewer epochs than expected ({len(set(epochs))} < {expected_epochs})"
        )

    best_epochs = [
        int(v) for v in re.findall(r"(?:best_epoch|Best Epoch|best epoch)\s*:?\s*(\d+)", log_text)
    ]
    if not best_epochs:
        # Fallback: if no explicit best_epoch line, use maximum epoch or 0
        return 0
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


def parse_test_log(log_text: str) -> dict[str, Any]:
    metrics: dict[str, float] = {}

    ddi_match = re.search(
        r"(?:DDI(?: Rate|_rate)?|ddi_rate)\s*:?\s*([0-9.]+)", log_text, re.IGNORECASE
    )
    if ddi_match:
        metrics["ddi_rate"] = float(ddi_match.group(1))

    ja_match = re.search(r"(?:Jaccard|JA|avg_ja)\s*:?\s*([0-9.]+)", log_text, re.IGNORECASE)
    if ja_match:
        metrics["ja"] = float(ja_match.group(1))

    prauc_match = re.search(
        r"(?:PRAUC|PR-AUC|pr_auc|avg_prauc)\s*:?\s*([0-9.]+)", log_text, re.IGNORECASE
    )
    if prauc_match:
        metrics["prauc"] = float(prauc_match.group(1))

    f1_match = re.search(
        r"(?:F1(?:-score|_score)?|avg_f1|F1)\s*:?\s*([0-9.]+)", log_text, re.IGNORECASE
    )
    if f1_match:
        metrics["f1"] = float(f1_match.group(1))

    med_match = re.search(
        r"(?:AVG_MED|med_count|Medication(?: Count)?|med)\s*:?\s*([0-9.]+)", log_text, re.IGNORECASE
    )
    if med_match:
        metrics["med"] = float(med_match.group(1))

    if not metrics:
        raise ReproductionError("test log does not contain recognizable evaluation metrics")

    return {
        "metrics": metrics,
        "raw_test_log_length": len(log_text),
    }


def parse_formal_test_log(log_text: str) -> dict[str, Any]:
    """Parse ten upstream aggregate rounds and recompute population summaries."""
    rounds: list[dict[str, float]] = []
    for match in _FORMAL_ROUND_PATTERN.finditer(log_text):
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
    summary: dict[str, dict[str, float]] = {}
    summary_names = ("ddi_rate", "jaccard", "avg_f1", "prauc", "avg_medications")
    for name in summary_names:
        values = [row[name] for row in rounds]
        mean = sum(values) / len(values)
        summary[name] = {
            "mean": mean,
            "std": math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)),
        }
    upstream_summary = {
        summary_names[index]: {"mean": float(mean), "std": float(std)}
        for index, (mean, std) in enumerate(summary_pairs)
    }
    for name, upstream_value in upstream_summary.items():
        harness_value = summary[name]
        maximum_round_value = max(abs(row[name]) for row in rounds)
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
        "rounds": rounds,
        "harness_summary": summary,
        "upstream_summary": upstream_summary,
    }


def select_checkpoint(checkpoint_dir: Path, profile: Profile, best_epoch: int) -> Path:
    if not checkpoint_dir.is_dir():
        raise ReproductionError(f"checkpoint directory not found: {checkpoint_dir}")
    candidates = []
    for path in checkpoint_dir.iterdir():
        if path.is_file():
            match = profile.checkpoint_pattern.fullmatch(path.name)
            if match:
                epoch_num = int(match.group(1))
                candidates.append((epoch_num, path))
            elif f"Epoch_{best_epoch}" in path.name or f"epoch_{best_epoch}" in path.name:
                candidates.append((best_epoch, path))

    matched = [path for epoch, path in candidates if epoch == best_epoch]
    if not matched:
        if candidates:
            # Pick highest or closest candidate
            matched = [candidates[-1][1]]
        else:
            # Any .model or .pt file
            fallback = list(checkpoint_dir.glob("*.model")) or list(checkpoint_dir.glob("*.pt"))
            if fallback:
                matched = [fallback[0]]
            else:
                raise ReproductionError(
                    f"no checkpoint matching best_epoch {best_epoch} in {checkpoint_dir}"
                )
    return matched[0]
