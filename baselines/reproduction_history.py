"""Trusted program-native validation history parsing for reproduction recovery."""

from __future__ import annotations

import importlib
import math
import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from numbers import Real
from pathlib import Path
from typing import Any

HISTORY_KEYS = ("ja", "ddi_rate", "avg_p", "avg_r", "avg_f1", "prauc", "med")
_CHECKPOINT_PATTERN = re.compile(
    r"^Epoch_(?P<epoch>\d+)(?:_TARGET_[^_]+)?_JA_(?P<ja>[0-9.eE+-]+)"
    r"_DDI_(?P<ddi>[0-9.eE+-]+)\.model$"
)


def _fail(message: str, error_type: type[Exception]) -> None:
    raise error_type(message)


def _load_history(path: Path, *, error_type: type[Exception]) -> object:
    if not path.is_file():
        _fail(f"native validation history not found: {path}", error_type)
    try:
        dill = importlib.import_module("dill")
        with path.open("rb") as stream:
            return dill.load(stream)
    except Exception as error:
        raise error_type(f"native validation history cannot be loaded: {path}") from error


def load_native_validation_history(
    path: str | Path,
    *,
    expected_epochs: int,
    error_type: type[Exception] = RuntimeError,
) -> dict[str, int | float]:
    """Load the frozen seven-list history and select the first Jaccard maximum."""
    history = _load_history(Path(path), error_type=error_type)
    if not isinstance(history, Mapping) or set(history) != set(HISTORY_KEYS):
        _fail("native validation history must contain exactly the seven declared lists", error_type)

    normalized: dict[str, list[float]] = {}
    for key in HISTORY_KEYS:
        raw_values = history[key]
        if not isinstance(raw_values, list) or len(raw_values) != expected_epochs:
            _fail(
                f"native validation history '{key}' must contain exactly {expected_epochs} epochs",
                error_type,
            )
        values: list[float] = []
        for value in raw_values:
            if isinstance(value, bool) or not isinstance(value, Real):
                _fail("native validation history values must be finite numeric values", error_type)
            numeric = float(value)
            if not math.isfinite(numeric):
                _fail("native validation history values must be finite numeric values", error_type)
            values.append(numeric)
        normalized[key] = values

    for key in ("ja", "ddi_rate"):
        if any(not 0 <= value <= 1 for value in normalized[key]):
            _fail(f"native validation history '{key}' must contain proportions", error_type)

    jaccard = normalized["ja"]
    best_epoch = jaccard.index(max(jaccard))
    return {
        "epochs_observed": expected_epochs,
        "best_epoch": best_epoch,
        "validation_jaccard": jaccard[best_epoch],
        "validation_ddi_rate": normalized["ddi_rate"][best_epoch],
    }


def _display_value_agrees(literal: str, value: float) -> bool:
    try:
        displayed = Decimal(literal)
        actual = Decimal(str(value))
    except InvalidOperation:
        return False
    unit = Decimal(1).scaleb(displayed.as_tuple().exponent)
    return abs(actual - displayed) <= abs(unit) / 2


def reconcile_history_checkpoint(
    checkpoint: str | Path,
    validation: Mapping[str, Any],
    *,
    error_type: type[Exception] = RuntimeError,
) -> None:
    """Cross-check history authority against the checkpoint's rounded filename fields."""
    path = Path(checkpoint)
    match = _CHECKPOINT_PATTERN.fullmatch(path.name)
    if match is None:
        _fail("selected checkpoint filename does not expose epoch, Jaccard, and DDI", error_type)

    epoch = validation.get("best_epoch")
    if isinstance(epoch, bool) or not isinstance(epoch, int) or int(match["epoch"]) != epoch:
        _fail("checkpoint epoch disagrees with native validation history", error_type)

    fields = (
        ("ja", "validation_jaccard", "Jaccard"),
        ("ddi", "validation_ddi_rate", "DDI"),
    )
    for group, field, label in fields:
        value = validation.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(float(value))
            or not _display_value_agrees(match[group], float(value))
        ):
            _fail(f"checkpoint {label} disagrees with native validation history", error_type)


__all__ = (
    "HISTORY_KEYS",
    "load_native_validation_history",
    "reconcile_history_checkpoint",
)
