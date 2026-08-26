"""Validation-only SafeDrug candidate selection for the MoleRec Table 1 attempt."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from ._validation import (
    require_probability,
    require_string,
    strict_fields,
    write_json_atomic,
)
from .errors import ProtocolValidationError

SAFE_DRUG_LANE_IDS = (
    "molerec-safedrug-lr-1e-5",
    "molerec-safedrug-lr-1e-4",
    "molerec-safedrug-lr-5e-4",
)
SELECTION_SCHEMA_VERSION = 1
SELECTION_RULE = (
    "maximize validation_jaccard",
    "minimize validation_ddi_rate",
    "minimize learning_rate",
    "minimize lane_id",
)


def _candidate_fields(value: object, *, index: int) -> dict[str, Any]:
    candidate = strict_fields(
        value,
        required=(
            "lane_id",
            "learning_rate",
            "checkpoint_identity",
            "validation_jaccard",
            "validation_ddi_rate",
        ),
        context=f"SafeDrug candidate {index}",
    )
    lane_id = require_string(candidate["lane_id"], field=f"candidate {index}.lane_id")
    learning_rate = candidate["learning_rate"]
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
        raise ProtocolValidationError(
            f"candidate {index}.learning_rate must be a finite positive number"
        )
    learning_rate = float(learning_rate)
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ProtocolValidationError(
            f"candidate {index}.learning_rate must be a finite positive number"
        )

    return {
        "lane_id": lane_id,
        "learning_rate": learning_rate,
        "checkpoint_identity": require_string(
            candidate["checkpoint_identity"],
            field=f"candidate {index}.checkpoint_identity",
        ),
        "validation_jaccard": require_probability(
            candidate["validation_jaccard"],
            field=f"candidate {index}.validation_jaccard",
        ),
        "validation_ddi_rate": require_probability(
            candidate["validation_ddi_rate"],
            field=f"candidate {index}.validation_ddi_rate",
        ),
    }


def _base_selection(
    expected_lane_ids: Sequence[str],
    candidates: list[dict[str, Any]],
    *,
    state: str,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "kind": "safedrug_selection",
        "state": state,
        "candidate_lane_ids": list(expected_lane_ids),
        "candidates": sorted(candidates, key=lambda value: value["lane_id"]),
        "selection_rule": list(SELECTION_RULE),
        "comparison_decisions": [],
        "selected_lane_id": None,
        "test_metrics_available": False,
        "errors": sorted(errors),
    }


def select_safedrug_candidate(
    candidates: Iterable[Mapping[str, Any]],
    *,
    expected_lane_ids: Sequence[str] = SAFE_DRUG_LANE_IDS,
) -> dict[str, Any]:
    """Select one SafeDrug lane from validation evidence, failing closed on gaps."""
    expected = tuple(expected_lane_ids)
    if len(set(expected)) != len(expected):
        raise ProtocolValidationError("expected SafeDrug lane IDs must be unique")

    parsed: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    try:
        raw_candidates = list(candidates)
    except TypeError as error:
        raise ProtocolValidationError("SafeDrug candidates must be iterable") from error

    for index, raw_candidate in enumerate(raw_candidates):
        try:
            candidate = _candidate_fields(raw_candidate, index=index)
        except ProtocolValidationError as error:
            errors.append(str(error))
            continue
        lane_id = candidate["lane_id"]
        if lane_id in seen:
            errors.append(f"duplicate SafeDrug candidate lane_id: {lane_id}")
            continue
        seen.add(lane_id)
        if lane_id not in expected:
            errors.append(f"unexpected SafeDrug candidate lane_id: {lane_id}")
            continue
        parsed.append(candidate)

    missing = sorted(set(expected) - seen)
    errors.extend(f"missing SafeDrug candidate lane_id: {lane_id}" for lane_id in missing)
    if errors or len(parsed) != len(expected):
        return _base_selection(expected, parsed, state="selection_incomplete", errors=errors)

    ranked = sorted(
        parsed,
        key=lambda candidate: (
            -candidate["validation_jaccard"],
            candidate["validation_ddi_rate"],
            candidate["learning_rate"],
            candidate["lane_id"],
        ),
    )
    selection = _base_selection(expected, parsed, state="selection_ready", errors=[])
    selection["comparison_decisions"] = [
        {
            "rank": rank,
            "lane_id": candidate["lane_id"],
            "validation_jaccard": candidate["validation_jaccard"],
            "validation_ddi_rate": candidate["validation_ddi_rate"],
            "learning_rate": candidate["learning_rate"],
        }
        for rank, candidate in enumerate(ranked, start=1)
    ]
    selection["selected_lane_id"] = ranked[0]["lane_id"]
    return selection


def write_selection(path: str, selection: Mapping[str, Any]) -> None:
    """Atomically publish a selector-produced artifact."""
    write_json_atomic(path, dict(selection))


def require_selected_safedrug_lane(
    selection: Mapping[str, Any],
    lane_id: str,
) -> dict[str, Any]:
    """Return the selected candidate or reject a SafeDrug test admission."""
    payload = strict_fields(
        selection,
        required=(
            "schema_version",
            "kind",
            "state",
            "candidate_lane_ids",
            "candidates",
            "selection_rule",
            "comparison_decisions",
            "selected_lane_id",
            "test_metrics_available",
            "errors",
        ),
        context="SafeDrug selection",
    )
    if payload["schema_version"] != SELECTION_SCHEMA_VERSION:
        raise ProtocolValidationError("SafeDrug selection schema version is unsupported")
    if payload["kind"] != "safedrug_selection":
        raise ProtocolValidationError("artifact is not a SafeDrug selection")
    if payload["state"] != "selection_ready":
        raise ProtocolValidationError("SafeDrug selection is not complete")
    if payload["test_metrics_available"] is not False:
        raise ProtocolValidationError("SafeDrug selection must not contain test metrics")
    if payload["errors"]:
        raise ProtocolValidationError("SafeDrug selection contains errors")
    if payload["selected_lane_id"] != lane_id:
        raise ProtocolValidationError(f"SafeDrug lane '{lane_id}' was not selected")

    candidate_rows = payload["candidates"]
    if not isinstance(candidate_rows, list):
        raise ProtocolValidationError("SafeDrug selection candidates must be a list")
    for index, candidate in enumerate(candidate_rows):
        parsed = _candidate_fields(candidate, index=index)
        if parsed["lane_id"] == lane_id:
            return parsed
    raise ProtocolValidationError(f"selected SafeDrug lane '{lane_id}' has no candidate evidence")


__all__ = (
    "SAFE_DRUG_LANE_IDS",
    "SELECTION_RULE",
    "SELECTION_SCHEMA_VERSION",
    "require_selected_safedrug_lane",
    "select_safedrug_candidate",
    "write_selection",
)
