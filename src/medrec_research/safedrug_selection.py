"""Validation-only SafeDrug candidate selection for the MoleRec Table 1 attempt."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ._validation import (
    require_int,
    require_probability,
    require_sha256,
    require_string,
    strict_fields,
    write_json_atomic,
)
from .errors import ProtocolValidationError
from .reproduction_evidence import (
    RECOVERY_FIELDS,
    reopen_training_evidence,
    validate_identity,
)

SAFE_DRUG_LANE_IDS = (
    "molerec-safedrug-lr-1e-5",
    "molerec-safedrug-lr-1e-4",
    "molerec-safedrug-lr-5e-4",
)
SAFE_DRUG_LEARNING_RATES = {
    "molerec-safedrug-lr-1e-5": 1e-5,
    "molerec-safedrug-lr-1e-4": 1e-4,
    "molerec-safedrug-lr-5e-4": 5e-4,
}
SELECTION_SCHEMA_VERSION = 1
SELECTION_RULE = (
    "maximize validation_jaccard",
    "minimize validation_ddi_rate",
    "minimize learning_rate",
    "minimize lane_id",
)

_CHECKPOINT_FIELDS = ("best_epoch", "relative_path", "sha256", "size_bytes")
_TRAINING_EVIDENCE_FIELDS = (
    "state",
    "artifact_type",
    "identity",
    "learning_rate",
    "best_epoch",
    "validation_jaccard",
    "validation_ddi_rate",
    "checkpoint",
    "recovery",
)


def _require_learning_rate(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a finite positive number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ProtocolValidationError(f"{field} must be a finite positive number")
    return result


def _recovery_fields(value: object, *, index: int) -> dict[str, Any]:
    recovery = strict_fields(
        value,
        required=RECOVERY_FIELDS,
        context=f"SafeDrug candidate {index}.training_evidence.recovery",
    )
    if recovery["schema_version"] != 1 or recovery["kind"] != "training_finalization_recovery":
        raise ProtocolValidationError(f"candidate {index}.recovery is not training recovery")
    recovery_id = require_string(recovery["recovery_id"], field=f"candidate {index}.recovery_id")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", recovery_id):
        raise ProtocolValidationError(f"candidate {index}.recovery_id is invalid")
    finalizer_revision = require_string(
        recovery["finalizer_revision"],
        field=f"candidate {index}.recovery.finalizer_revision",
    )
    if not re.fullmatch(r"[0-9a-f]{40}", finalizer_revision):
        raise ProtocolValidationError(f"candidate {index}.recovery.finalizer_revision is invalid")
    if (
        recovery["source_terminal_state"] != "failed"
        or recovery["source_failure_code"] != "training_failed"
        or recovery["parser_classification"] != "validation_metrics_unlabeled"
    ):
        raise ProtocolValidationError(
            f"candidate {index}.recovery source classification is invalid"
        )
    source_relative_path = require_string(
        recovery["source_relative_path"],
        field=f"candidate {index}.recovery.source_relative_path",
    )
    checkpoint_relative_path = require_string(
        recovery["checkpoint_relative_path"],
        field=f"candidate {index}.recovery.checkpoint_relative_path",
    )
    checkpoint_path = Path(checkpoint_relative_path)
    if checkpoint_path.is_absolute() or ".." in checkpoint_path.parts:
        raise ProtocolValidationError(f"candidate {index}.recovery checkpoint path is invalid")
    selected_epoch = require_int(
        recovery["selected_epoch"],
        field=f"candidate {index}.recovery.selected_epoch",
    )
    validation_jaccard = require_probability(
        recovery["validation_jaccard"],
        field=f"candidate {index}.recovery.validation_jaccard",
    )
    validation_ddi_rate = require_probability(
        recovery["validation_ddi_rate"],
        field=f"candidate {index}.recovery.validation_ddi_rate",
    )
    return {
        "schema_version": 1,
        "kind": "training_finalization_recovery",
        "recovery_id": recovery_id,
        "finalizer_revision": finalizer_revision,
        "source_relative_path": source_relative_path,
        "source_terminal_state": "failed",
        "source_failure_code": "training_failed",
        "parser_classification": "validation_metrics_unlabeled",
        "selected_epoch": selected_epoch,
        "checkpoint_relative_path": checkpoint_relative_path,
        "validation_jaccard": validation_jaccard,
        "validation_ddi_rate": validation_ddi_rate,
    }


def _training_evidence_fields(
    value: object,
    *,
    index: int,
    lane_id: str,
) -> dict[str, Any]:
    evidence = strict_fields(
        value,
        required=_TRAINING_EVIDENCE_FIELDS,
        context=f"SafeDrug candidate {index}.training_evidence",
    )
    if evidence["state"] != "completed" or evidence["artifact_type"] != "training":
        raise ProtocolValidationError(
            f"candidate {index}.training_evidence must be completed training evidence"
        )
    identity = validate_identity(
        evidence["identity"],
        context=f"SafeDrug candidate {index}.training_evidence.identity",
    )
    if (
        identity["lane_id"] != lane_id
        or identity["scientific_baseline_id"] != "safedrug"
        or identity["program_id"] != "safedrug-archived"
        or identity["profile_id"] != "safedrug"
        or identity["mode"] != "formal"
    ):
        raise ProtocolValidationError(
            f"candidate {index}.training_evidence identity does not name this SafeDrug lane"
        )
    learning_rate = _require_learning_rate(
        evidence["learning_rate"],
        field=f"candidate {index}.training_evidence.learning_rate",
    )
    expected_learning_rate = SAFE_DRUG_LEARNING_RATES.get(lane_id)
    if expected_learning_rate is not None and learning_rate != expected_learning_rate:
        raise ProtocolValidationError(f"candidate {index} has the wrong SafeDrug learning rate")
    best_epoch = require_int(
        evidence["best_epoch"],
        field=f"candidate {index}.training_evidence.best_epoch",
    )
    validation_jaccard = require_probability(
        evidence["validation_jaccard"],
        field=f"candidate {index}.training_evidence.validation_jaccard",
    )
    validation_ddi_rate = require_probability(
        evidence["validation_ddi_rate"],
        field=f"candidate {index}.training_evidence.validation_ddi_rate",
    )
    checkpoint = strict_fields(
        evidence["checkpoint"],
        required=_CHECKPOINT_FIELDS,
        context=f"SafeDrug candidate {index}.training_evidence.checkpoint",
    )
    checkpoint_best_epoch = require_int(
        checkpoint["best_epoch"],
        field=f"candidate {index}.training_evidence.checkpoint.best_epoch",
    )
    if checkpoint_best_epoch != best_epoch:
        raise ProtocolValidationError(f"candidate {index} checkpoint epoch disagrees with evidence")
    checkpoint_relative_path = require_string(
        checkpoint["relative_path"],
        field=f"candidate {index}.training_evidence.checkpoint.relative_path",
    )
    checkpoint_path = Path(checkpoint_relative_path)
    if checkpoint_path.is_absolute() or ".." in checkpoint_path.parts:
        raise ProtocolValidationError(f"candidate {index} checkpoint path is invalid")
    checkpoint_sha256 = require_sha256(
        checkpoint["sha256"],
        field=f"candidate {index}.training_evidence.checkpoint.sha256",
    )
    checkpoint_size = require_int(
        checkpoint["size_bytes"],
        field=f"candidate {index}.training_evidence.checkpoint.size_bytes",
    )
    recovery_value = evidence["recovery"]
    recovery = None if recovery_value is None else _recovery_fields(recovery_value, index=index)
    if recovery is not None and (
        recovery["selected_epoch"] != best_epoch
        or recovery["checkpoint_relative_path"] != checkpoint_relative_path
        or recovery["validation_jaccard"] != validation_jaccard
        or recovery["validation_ddi_rate"] != validation_ddi_rate
    ):
        raise ProtocolValidationError(
            f"candidate {index} recovery provenance disagrees with training evidence"
        )
    return {
        "state": "completed",
        "artifact_type": "training",
        "identity": identity,
        "learning_rate": learning_rate,
        "best_epoch": best_epoch,
        "validation_jaccard": validation_jaccard,
        "validation_ddi_rate": validation_ddi_rate,
        "checkpoint": {
            "best_epoch": best_epoch,
            "relative_path": checkpoint_relative_path,
            "sha256": checkpoint_sha256,
            "size_bytes": checkpoint_size,
        },
        "recovery": recovery,
    }


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
        optional=("training_evidence",),
        context=f"SafeDrug candidate {index}",
    )
    lane_id = require_string(candidate["lane_id"], field=f"candidate {index}.lane_id")
    learning_rate = _require_learning_rate(
        candidate["learning_rate"], field=f"candidate {index}.learning_rate"
    )
    expected_learning_rate = SAFE_DRUG_LEARNING_RATES.get(lane_id)
    if expected_learning_rate is not None and learning_rate != expected_learning_rate:
        raise ProtocolValidationError(f"candidate {index} has the wrong SafeDrug learning rate")
    checkpoint_identity = require_sha256(
        candidate["checkpoint_identity"],
        field=f"candidate {index}.checkpoint_identity",
    )
    validation_jaccard = require_probability(
        candidate["validation_jaccard"],
        field=f"candidate {index}.validation_jaccard",
    )
    validation_ddi_rate = require_probability(
        candidate["validation_ddi_rate"],
        field=f"candidate {index}.validation_ddi_rate",
    )
    training_evidence = _training_evidence_fields(
        candidate.get("training_evidence"),
        index=index,
        lane_id=lane_id,
    )
    if (
        training_evidence["learning_rate"] != learning_rate
        or training_evidence["validation_jaccard"] != validation_jaccard
        or training_evidence["validation_ddi_rate"] != validation_ddi_rate
        or training_evidence["checkpoint"]["sha256"] != checkpoint_identity
    ):
        raise ProtocolValidationError(f"candidate {index} disagrees with its terminal evidence")

    return {
        "lane_id": lane_id,
        "learning_rate": learning_rate,
        "checkpoint_identity": checkpoint_identity,
        "validation_jaccard": validation_jaccard,
        "validation_ddi_rate": validation_ddi_rate,
        "training_evidence": training_evidence,
    }


def _base_selection(
    candidates: list[dict[str, Any]],
    *,
    state: str,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "kind": "safedrug_selection",
        "state": state,
        "candidate_lane_ids": list(SAFE_DRUG_LANE_IDS),
        "candidates": sorted(candidates, key=lambda value: value["lane_id"]),
        "selection_rule": list(SELECTION_RULE),
        "comparison_decisions": [],
        "selected_lane_id": None,
        "test_metrics_available": False,
        "errors": sorted(errors),
    }


def _comparison_decisions(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -candidate["validation_jaccard"],
            candidate["validation_ddi_rate"],
            candidate["learning_rate"],
            candidate["lane_id"],
        ),
    )
    return [
        {
            "rank": rank,
            "lane_id": candidate["lane_id"],
            "validation_jaccard": candidate["validation_jaccard"],
            "validation_ddi_rate": candidate["validation_ddi_rate"],
            "learning_rate": candidate["learning_rate"],
        }
        for rank, candidate in enumerate(ranked, start=1)
    ]


def candidate_from_training_evidence(
    lane_id: str,
    *,
    training_run_root: str | Path,
    source_run_root: str | Path | None = None,
    expected_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one selection candidate from a reopened terminal training pair."""
    lane_id = require_string(lane_id, field="SafeDrug lane_id")
    if lane_id not in SAFE_DRUG_LANE_IDS:
        raise ProtocolValidationError(f"undeclared SafeDrug lane: {lane_id}")
    evidence = reopen_training_evidence(
        training_run_root,
        source_run_root=source_run_root,
        expected_identity=expected_identity,
    )
    result = evidence["result"]
    identity = evidence["identity"]
    if identity["lane_id"] != lane_id:
        raise ProtocolValidationError("SafeDrug candidate evidence names a different lane")
    checkpoint = evidence["checkpoint"]
    checkpoint_sha256 = checkpoint["sha256"]
    best_epoch = checkpoint["best_epoch"]
    learning_rate = _require_learning_rate(
        result.get("learning_rate"),
        field="SafeDrug candidate learning_rate",
    )
    validation_jaccard = require_probability(
        evidence["validation_jaccard"],
        field="SafeDrug candidate validation_jaccard",
    )
    validation_ddi_rate = require_probability(
        evidence["validation_ddi_rate"],
        field="SafeDrug candidate validation_ddi_rate",
    )
    training_evidence = {
        "state": "completed",
        "artifact_type": "training",
        "identity": identity,
        "learning_rate": learning_rate,
        "best_epoch": best_epoch,
        "validation_jaccard": validation_jaccard,
        "validation_ddi_rate": validation_ddi_rate,
        "checkpoint": {
            "best_epoch": best_epoch,
            "relative_path": require_string(
                checkpoint["relative_path"],
                field="SafeDrug candidate checkpoint.relative_path",
            ),
            "sha256": checkpoint_sha256,
            "size_bytes": checkpoint["size_bytes"],
        },
        "recovery": result.get("recovery"),
    }
    candidate = {
        "lane_id": lane_id,
        "learning_rate": learning_rate,
        "checkpoint_identity": checkpoint_sha256,
        "validation_jaccard": validation_jaccard,
        "validation_ddi_rate": validation_ddi_rate,
        "training_evidence": training_evidence,
    }
    return _candidate_fields(candidate, index=0)


def select_safedrug_candidate(
    candidates: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Select one SafeDrug lane from validation evidence, failing closed on gaps."""
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
        if lane_id not in SAFE_DRUG_LANE_IDS:
            errors.append(f"unexpected SafeDrug candidate lane_id: {lane_id}")
            continue
        parsed.append(candidate)

    missing = sorted(set(SAFE_DRUG_LANE_IDS) - seen)
    errors.extend(f"missing SafeDrug candidate lane_id: {lane_id}" for lane_id in missing)
    if errors or len(parsed) != len(SAFE_DRUG_LANE_IDS):
        return _base_selection(parsed, state="selection_incomplete", errors=errors)

    comparison_decisions = _comparison_decisions(parsed)
    selection = _base_selection(parsed, state="selection_ready", errors=[])
    selection["comparison_decisions"] = comparison_decisions
    selection["selected_lane_id"] = comparison_decisions[0]["lane_id"]
    return selection


def write_selection(path: str | Path, selection: Mapping[str, Any]) -> None:
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
    if payload["errors"] != []:
        raise ProtocolValidationError("SafeDrug selection contains errors")
    if payload["candidate_lane_ids"] != list(SAFE_DRUG_LANE_IDS):
        raise ProtocolValidationError(
            "SafeDrug selection does not contain the exact declared lanes"
        )

    candidate_rows = payload["candidates"]
    if not isinstance(candidate_rows, list) or len(candidate_rows) != len(SAFE_DRUG_LANE_IDS):
        raise ProtocolValidationError("SafeDrug selection candidates must be a list")
    normalized_candidates = []
    for index, candidate in enumerate(candidate_rows):
        normalized_candidates.append(_candidate_fields(candidate, index=index))
    candidate_lane_ids = [candidate["lane_id"] for candidate in normalized_candidates]
    if set(candidate_lane_ids) != set(SAFE_DRUG_LANE_IDS) or len(set(candidate_lane_ids)) != len(
        SAFE_DRUG_LANE_IDS
    ):
        raise ProtocolValidationError(
            "SafeDrug selection does not contain exactly three unique lanes"
        )
    if candidate_lane_ids != sorted(SAFE_DRUG_LANE_IDS):
        raise ProtocolValidationError("SafeDrug selection candidates are not in canonical order")
    expected_comparison = _comparison_decisions(normalized_candidates)
    if payload["comparison_decisions"] != expected_comparison:
        raise ProtocolValidationError("SafeDrug selection comparison decisions are inconsistent")
    if payload["selected_lane_id"] != expected_comparison[0]["lane_id"]:
        raise ProtocolValidationError("SafeDrug selection winner is inconsistent")
    if payload["selected_lane_id"] != lane_id:
        raise ProtocolValidationError(f"SafeDrug lane '{lane_id}' was not selected")
    return next(candidate for candidate in normalized_candidates if candidate["lane_id"] == lane_id)


__all__ = (
    "SAFE_DRUG_LANE_IDS",
    "SAFE_DRUG_LEARNING_RATES",
    "SELECTION_RULE",
    "SELECTION_SCHEMA_VERSION",
    "candidate_from_training_evidence",
    "require_selected_safedrug_lane",
    "select_safedrug_candidate",
    "write_selection",
)
