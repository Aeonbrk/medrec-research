"""Standalone identity, selection, and atomic finalization helpers for 319 programs."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

IDENTITY_FIELDS = (
    "attempt_id",
    "lane_id",
    "scientific_baseline_id",
    "program_id",
    "profile_id",
    "harness_revision",
    "model_source_revision",
    "preprocessing_revision",
    "snapshot_id",
    "environment_sha256",
    "mode",
    "submission_id",
)
IDENTITY_ENVIRONMENT_FIELDS = {
    "attempt_id": "MEDREC_ATTEMPT_ID",
    "lane_id": "MEDREC_LANE_ID",
    "scientific_baseline_id": "MEDREC_BASELINE_ID",
    "program_id": "MEDREC_PROGRAM_ID",
    "profile_id": "MEDREC_PROFILE_ID",
    "harness_revision": "MEDREC_HARNESS_REVISION",
    "model_source_revision": "MEDREC_MODEL_SOURCE_REVISION",
    "preprocessing_revision": "MEDREC_PREPROCESSING_REVISION",
    "snapshot_id": "MEDREC_SNAPSHOT_ID",
    "environment_sha256": "MEDREC_ENVIRONMENT_SHA256",
    "mode": "MEDREC_MODE",
    "submission_id": "MEDREC_SUBMISSION_ID",
}
TERMINAL_STATES = ("completed", "failed", "blocked", "stale_rejected")
SAFE_DRUG_LANE_IDS = (
    "molerec-safedrug-lr-1e-5",
    "molerec-safedrug-lr-1e-4",
    "molerec-safedrug-lr-5e-4",
)
SAFE_DRUG_SELECTION_RULE = (
    "maximize validation_jaccard",
    "minimize validation_ddi_rate",
    "minimize learning_rate",
    "minimize lane_id",
)
_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SAFE_VALUE = re.compile(r"[^\x00-\x1f\x7f\s]+")


def _fail(message: str, error_type: type[Exception]) -> None:
    raise error_type(message)


def _validate_identity(
    identity: object,
    *,
    error_type: type[Exception],
) -> dict[str, str]:
    if not isinstance(identity, Mapping) or set(identity) != set(IDENTITY_FIELDS):
        _fail("evidence identity must contain exactly the v2 identity fields", error_type)
    normalized: dict[str, str] = {}
    for field in IDENTITY_FIELDS:
        value = identity[field]
        if not isinstance(value, str) or not _SAFE_VALUE.fullmatch(value):
            _fail(f"evidence identity field '{field}' is invalid", error_type)
        normalized[field] = value
    for field in (
        "harness_revision",
        "model_source_revision",
        "preprocessing_revision",
    ):
        if not _IMMUTABLE_REVISION.fullmatch(normalized[field]):
            _fail(f"evidence identity field '{field}' is not an immutable revision", error_type)
    if not _SHA256.fullmatch(normalized["environment_sha256"]):
        _fail("evidence identity environment_sha256 is invalid", error_type)
    if normalized["mode"] not in ("formal", "smoke"):
        _fail("evidence identity mode must be formal or smoke", error_type)
    return normalized


def identity_from_environment(
    *,
    mode: str,
    environ: Mapping[str, str] | None = None,
    error_type: type[Exception] = RuntimeError,
) -> dict[str, str] | None:
    """Read the controller-issued identity, rejecting partial or unverified values."""
    values = os.environ if environ is None else environ
    names = tuple(IDENTITY_ENVIRONMENT_FIELDS.values())
    present = [name in values for name in names]
    if not any(present):
        return None
    if not all(present):
        _fail("controller-issued reproduction identity is incomplete", error_type)
    identity = {
        field: values[environment_name]
        for field, environment_name in IDENTITY_ENVIRONMENT_FIELDS.items()
    }
    normalized = _validate_identity(identity, error_type=error_type)
    if normalized["mode"] != mode:
        _fail("controller-issued reproduction mode does not match the requested mode", error_type)
    return normalized


def require_selected_safedrug_selection(
    selection_path: str | Path | None,
    *,
    lane_id: str,
    error_type: type[Exception] = RuntimeError,
) -> dict[str, Any]:
    """Validate the selector artifact before constructing a SafeDrug test command."""
    if selection_path is None:
        _fail("SafeDrug test admission requires selection.json", error_type)
    path = Path(selection_path)
    try:
        selection = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"SafeDrug selection.json cannot be read: {error}", error_type)
    if not isinstance(selection, Mapping):
        _fail("SafeDrug selection.json must contain an object", error_type)
    required = {
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
    }
    if set(selection) != required:
        _fail("SafeDrug selection.json has an invalid schema", error_type)
    if (
        selection["schema_version"] != 1
        or selection["kind"] != "safedrug_selection"
        or selection["state"] != "selection_ready"
        or selection["selected_lane_id"] != lane_id
        or selection["test_metrics_available"] is not False
        or selection["errors"]
        or selection["candidate_lane_ids"] != list(SAFE_DRUG_LANE_IDS)
        or selection["selection_rule"] != list(SAFE_DRUG_SELECTION_RULE)
    ):
        _fail("SafeDrug selection.json does not authorize this lane", error_type)
    candidate_lane_ids = selection["candidate_lane_ids"]
    candidates = selection["candidates"]
    if (
        not isinstance(candidate_lane_ids, list)
        or not isinstance(candidates, list)
        or len(candidates) != len(SAFE_DRUG_LANE_IDS)
        or set(
            candidate.get("lane_id") for candidate in candidates if isinstance(candidate, Mapping)
        )
        != set(SAFE_DRUG_LANE_IDS)
    ):
        _fail("SafeDrug selection.json has no evidence for the selected lane", error_type)
    for candidate in candidates:
        if not isinstance(candidate, Mapping) or set(candidate) != {
            "lane_id",
            "learning_rate",
            "checkpoint_identity",
            "validation_jaccard",
            "validation_ddi_rate",
        }:
            _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
        learning_rate = candidate["learning_rate"]
        checkpoint_identity = candidate["checkpoint_identity"]
        if (
            not isinstance(learning_rate, (int, float))
            or isinstance(learning_rate, bool)
            or not math.isfinite(float(learning_rate))
            or float(learning_rate) <= 0
            or not isinstance(checkpoint_identity, str)
            or not checkpoint_identity
        ):
            _fail("SafeDrug selection.json contains invalid candidate evidence", error_type)
        for metric in ("validation_jaccard", "validation_ddi_rate"):
            value = candidate[metric]
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                or not 0 <= float(value) <= 1
            ):
                _fail("SafeDrug selection.json contains invalid validation evidence", error_type)
    return dict(selection)


def _write_pending(path: Path, value: Mapping[str, Any]) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".pending",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _write_marker(path: Path, value: Mapping[str, Any]) -> None:
    pending = _write_pending(path, value)
    try:
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def finalize_v2_pair(
    run_root: str | Path,
    *,
    status: Mapping[str, Any],
    result: Mapping[str, Any],
    error_type: type[Exception] = RuntimeError,
) -> None:
    """Atomically publish v2 sibling artifacts and a marker written last."""
    root = Path(run_root)
    root.mkdir(parents=True, exist_ok=True)
    status_path = root / "status.json"
    result_path = root / "result.json"
    marker_path = root / "finalization.json"
    if status_path.exists() or result_path.exists() or marker_path.exists():
        _fail("evidence pair has already been finalized", error_type)

    status_identity = _validate_terminal_pair(status, result, error_type=error_type)

    pending: list[Path] = []
    try:
        pending_status = _write_pending(status_path, status)
        pending.append(pending_status)
        pending_result = _write_pending(result_path, result)
        pending.append(pending_result)
        os.replace(pending_status, status_path)
        pending.remove(pending_status)
        os.replace(pending_result, result_path)
        pending.remove(pending_result)
        _write_marker(
            marker_path,
            {
                "schema_version": 1,
                "kind": "reproduction_finalization",
                "status": "finalized",
                "identity": status_identity,
            },
        )
    except BaseException:
        for path in pending:
            path.unlink(missing_ok=True)
        raise


def _validate_terminal_pair(
    status: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    error_type: type[Exception],
) -> dict[str, str]:
    if status.get("schema_version") != 2 or status.get("kind") != "reproduction_status_v2":
        _fail("status artifact must use v2", error_type)
    if result.get("schema_version") != 2 or result.get("kind") != "reproduction_result_v2":
        _fail("result artifact must use v2", error_type)
    status_identity = _validate_identity(status.get("identity"), error_type=error_type)
    result_identity = _validate_identity(result.get("identity"), error_type=error_type)
    if status_identity != result_identity:
        _fail("status and result identities do not match", error_type)
    if (
        status.get("mode") != status_identity["mode"]
        or result.get("mode") != status_identity["mode"]
    ):
        _fail("status and result modes do not match their identity", error_type)
    if status.get("stage") != "terminal" or status.get("state") not in TERMINAL_STATES:
        _fail("status artifact is not a terminal v2 state", error_type)
    if result.get("state") != status.get("state"):
        _fail("status and result terminal states do not match", error_type)
    if type(status.get("non_evidence")) is not bool or type(result.get("non_evidence")) is not bool:
        _fail("status and result non_evidence values must be boolean", error_type)
    if status["non_evidence"] != result["non_evidence"]:
        _fail("status and result non_evidence values do not match", error_type)
    if status_identity["mode"] == "formal" and status["non_evidence"]:
        _fail("formal v2 evidence cannot be non-evidence", error_type)
    return status_identity


def reopen_v2_pair(
    run_root: str | Path,
    *,
    expected_identity: Mapping[str, Any] | None = None,
    error_type: type[Exception] = RuntimeError,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reopen a finalized pair and reject a stale or mismatched submission."""
    root = Path(run_root)
    try:
        marker = json.loads((root / "finalization.json").read_text(encoding="utf-8"))
        status = json.loads((root / "status.json").read_text(encoding="utf-8"))
        result = json.loads((root / "result.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"finalized v2 evidence cannot be reopened: {error}", error_type)
    if (
        not isinstance(marker, Mapping)
        or set(marker) != {"schema_version", "kind", "status", "identity"}
        or marker["schema_version"] != 1
        or marker["kind"] != "reproduction_finalization"
        or marker["status"] != "finalized"
    ):
        _fail("finalization marker is invalid", error_type)
    if not isinstance(status, Mapping) or not isinstance(result, Mapping):
        _fail("finalized v2 status/result must be objects", error_type)
    identity = _validate_terminal_pair(status, result, error_type=error_type)
    marker_identity = _validate_identity(marker["identity"], error_type=error_type)
    if marker_identity != identity:
        _fail("finalization marker identity does not match evidence", error_type)
    if expected_identity is not None:
        expected = _validate_identity(expected_identity, error_type=error_type)
        if expected != identity:
            _fail("evidence identity does not match active submission", error_type)
    return dict(status), dict(result)


def terminal_status(
    identity: Mapping[str, Any],
    *,
    state: str,
    started_at: str,
    finished_at: str,
    non_evidence: bool,
    failure_code: str | None = None,
) -> dict[str, Any]:
    """Build the small shared status envelope used by both explicit programs."""
    return {
        "schema_version": 2,
        "kind": "reproduction_status_v2",
        "identity": dict(identity),
        "mode": identity["mode"],
        "state": state,
        "stage": "terminal",
        "started_at": started_at,
        "finished_at": finished_at,
        "failure_code": failure_code,
        "non_evidence": non_evidence,
    }


def terminal_result(
    identity: Mapping[str, Any],
    *,
    state: str,
    non_evidence: bool,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the shared result envelope while retaining program-specific fields."""
    return {
        "schema_version": 2,
        "kind": "reproduction_result_v2",
        "identity": dict(identity),
        "mode": identity["mode"],
        "state": state,
        "non_evidence": non_evidence,
        **dict(payload),
    }


__all__ = (
    "IDENTITY_ENVIRONMENT_FIELDS",
    "IDENTITY_FIELDS",
    "SAFE_DRUG_LANE_IDS",
    "SAFE_DRUG_SELECTION_RULE",
    "TERMINAL_STATES",
    "finalize_v2_pair",
    "identity_from_environment",
    "reopen_v2_pair",
    "require_selected_safedrug_selection",
    "terminal_result",
    "terminal_status",
)
