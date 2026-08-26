#!/usr/bin/env python3
"""Log parsing and checkpoint selection for MoleRec Table 1 reproduction."""

from __future__ import annotations

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
