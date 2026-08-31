"""Standalone identity and atomic finalization helpers for 319 programs."""

from __future__ import annotations

import hashlib
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
RECOVERY_FIELDS = (
    "schema_version",
    "kind",
    "recovery_id",
    "finalizer_revision",
    "source_relative_path",
    "source_terminal_state",
    "source_failure_code",
    "parser_classification",
    "selected_epoch",
    "checkpoint_relative_path",
    "validation_jaccard",
    "validation_ddi_rate",
)
_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SAFE_VALUE = re.compile(r"[^\x00-\x1f\x7f\s]+")
_RECOVERY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def _fail(message: str, error_type: type[Exception]) -> None:
    raise error_type(message)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _validate_recovery(
    value: object,
    *,
    error_type: type[Exception],
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(RECOVERY_FIELDS):
        _fail("recovery provenance has an invalid schema", error_type)
    recovery = dict(value)
    if recovery["schema_version"] != 1 or recovery["kind"] != "training_finalization_recovery":
        _fail("recovery provenance has an invalid contract", error_type)
    recovery_id = recovery["recovery_id"]
    if (
        not isinstance(recovery_id, str)
        or not _RECOVERY_ID.fullmatch(recovery_id)
        or recovery_id in (".", "..")
    ):
        _fail("recovery ID is invalid", error_type)
    if not isinstance(recovery["finalizer_revision"], str) or not _IMMUTABLE_REVISION.fullmatch(
        recovery["finalizer_revision"]
    ):
        _fail("recovery finalizer revision is invalid", error_type)
    if (
        recovery["source_terminal_state"] != "failed"
        or recovery["source_failure_code"] != "training_failed"
        or recovery["parser_classification"] != "validation_metrics_unlabeled"
    ):
        _fail("recovery source classification is invalid", error_type)
    source_relative_path = recovery["source_relative_path"]
    if not isinstance(source_relative_path, str) or not source_relative_path:
        _fail("recovery source path is invalid", error_type)
    checkpoint_relative_path = recovery["checkpoint_relative_path"]
    if not isinstance(checkpoint_relative_path, str) or not checkpoint_relative_path:
        _fail("recovery checkpoint path is invalid", error_type)
    checkpoint_path = Path(checkpoint_relative_path)
    if checkpoint_path.is_absolute() or ".." in checkpoint_path.parts:
        _fail("recovery checkpoint path is invalid", error_type)
    selected_epoch = recovery["selected_epoch"]
    if (
        isinstance(selected_epoch, bool)
        or not isinstance(selected_epoch, int)
        or selected_epoch < 0
    ):
        _fail("recovery selected epoch is invalid", error_type)
    for field in ("validation_jaccard", "validation_ddi_rate"):
        metric = recovery[field]
        if (
            isinstance(metric, bool)
            or not isinstance(metric, (int, float))
            or not math.isfinite(float(metric))
            or not 0 <= float(metric) <= 1
        ):
            _fail("recovery validation metrics are invalid", error_type)
    return recovery


def reopen_recovered_v2_pair(
    source_run_root: str | Path,
    recovery_run_root: str | Path,
    *,
    expected_identity: Mapping[str, Any] | None = None,
    error_type: type[Exception] = RuntimeError,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reopen a recovery sibling together with its unchanged failed source pair."""
    source_root = Path(source_run_root)
    recovery_root = Path(recovery_run_root)
    source_status, source_result = reopen_v2_pair(
        source_root,
        expected_identity=expected_identity,
        error_type=error_type,
    )
    recovered_status, recovered_result = reopen_v2_pair(
        recovery_root,
        expected_identity=expected_identity,
        error_type=error_type,
    )
    if source_status["identity"] != recovered_status["identity"]:
        _fail("source and recovery identities do not match", error_type)
    if (
        source_status.get("state") != "failed"
        or source_status.get("failure_code") != "training_failed"
        or source_result.get("artifact_type") != "training"
        or source_result.get("failure_code") != "training_failed"
    ):
        _fail("recovery source is not the eligible terminal training failure", error_type)
    if (
        recovered_status.get("state") != "completed"
        or recovered_result.get("artifact_type") != "training"
    ):
        _fail("recovery sibling is not completed training evidence", error_type)

    status_recovery = _validate_recovery(
        recovered_status.get("recovery"),
        error_type=error_type,
    )
    result_recovery = _validate_recovery(
        recovered_result.get("recovery"),
        error_type=error_type,
    )
    if status_recovery != result_recovery:
        _fail("status and result recovery provenance do not match", error_type)
    expected_root = source_root / "recoveries" / status_recovery["recovery_id"]
    if recovery_root.absolute() != expected_root.absolute():
        _fail("recovery sibling is outside its source attempt namespace", error_type)
    expected_source_path = Path(os.path.relpath(source_root, recovery_root)).as_posix()
    if status_recovery["source_relative_path"] != expected_source_path:
        _fail("recovery source path does not match its sibling layout", error_type)

    checkpoint = recovered_result.get("checkpoint")
    checkpoint_relative_path = (
        checkpoint.get("relative_path") if isinstance(checkpoint, Mapping) else None
    )
    if checkpoint_relative_path != status_recovery["checkpoint_relative_path"]:
        _fail("recovery checkpoint provenance does not match its result", error_type)
    checkpoint_path = source_root / checkpoint_relative_path
    if not checkpoint_path.is_file() or checkpoint_path.is_symlink():
        _fail("recovery checkpoint is missing or is not a regular file", error_type)
    checkpoint_size = checkpoint.get("size_bytes")
    if (
        isinstance(checkpoint_size, bool)
        or not isinstance(checkpoint_size, int)
        or checkpoint_size < 0
        or checkpoint_path.stat().st_size != checkpoint_size
    ):
        _fail("recovery checkpoint size does not match its result", error_type)
    checkpoint_sha256 = checkpoint.get("sha256")
    if (
        not isinstance(checkpoint_sha256, str)
        or not _SHA256.fullmatch(checkpoint_sha256)
        or _file_sha256(checkpoint_path) != checkpoint_sha256
    ):
        _fail("recovery checkpoint identity does not match its result", error_type)
    if (
        recovered_result.get("best_epoch") != status_recovery["selected_epoch"]
        or checkpoint.get("best_epoch") != status_recovery["selected_epoch"]
        or recovered_result.get("validation_jaccard") != status_recovery["validation_jaccard"]
        or recovered_result.get("validation_ddi_rate") != status_recovery["validation_ddi_rate"]
    ):
        _fail("recovery metric provenance does not match its result", error_type)
    return recovered_status, recovered_result


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
    "RECOVERY_FIELDS",
    "TERMINAL_STATES",
    "finalize_v2_pair",
    "identity_from_environment",
    "reopen_recovered_v2_pair",
    "reopen_v2_pair",
    "terminal_result",
    "terminal_status",
)
