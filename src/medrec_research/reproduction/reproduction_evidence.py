"""Shared v2 identity and finalization rules for Reproduction Mode evidence."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from .._validation import (
    canonical_json,
    parse_json_object,
    require_int,
    require_probability,
    require_sha256,
    require_string,
    strict_fields,
    write_json_atomic,
)
from ..errors import ProtocolValidationError

EVIDENCE_SCHEMA_VERSION = 2
FINALIZATION_SCHEMA_VERSION = 1
IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40}")
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
RECOVERY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_revision(value: object, *, field: str) -> str:
    result = require_string(value, field=field)
    if not IMMUTABLE_REVISION.fullmatch(result):
        raise ProtocolValidationError(f"{field} must be an immutable Git revision")
    return result


def validate_identity(value: object, *, context: str = "evidence identity") -> dict[str, str]:
    """Validate and normalize the identity bound to both sibling artifacts."""
    payload = strict_fields(value, required=IDENTITY_FIELDS, context=context)
    identity = {
        "attempt_id": require_string(payload["attempt_id"], field=f"{context}.attempt_id"),
        "lane_id": require_string(payload["lane_id"], field=f"{context}.lane_id"),
        "scientific_baseline_id": require_string(
            payload["scientific_baseline_id"], field=f"{context}.scientific_baseline_id"
        ),
        "program_id": require_string(payload["program_id"], field=f"{context}.program_id"),
        "profile_id": require_string(payload["profile_id"], field=f"{context}.profile_id"),
        "harness_revision": _require_revision(
            payload["harness_revision"], field=f"{context}.harness_revision"
        ),
        "model_source_revision": _require_revision(
            payload["model_source_revision"], field=f"{context}.model_source_revision"
        ),
        "preprocessing_revision": _require_revision(
            payload["preprocessing_revision"], field=f"{context}.preprocessing_revision"
        ),
        "snapshot_id": require_string(payload["snapshot_id"], field=f"{context}.snapshot_id"),
        "environment_sha256": require_sha256(
            payload["environment_sha256"], field=f"{context}.environment_sha256"
        ),
        "mode": require_string(payload["mode"], field=f"{context}.mode"),
        "submission_id": require_string(payload["submission_id"], field=f"{context}.submission_id"),
    }
    if identity["mode"] not in ("formal", "smoke"):
        raise ProtocolValidationError(f"{context}.mode must be 'formal' or 'smoke'")
    return identity


def validate_status_result_pair(
    status: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    expected_identity: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate the shared v2 identity and terminal state of sibling artifacts."""
    if not isinstance(status, Mapping) or not isinstance(result, Mapping):
        raise ProtocolValidationError("status and result artifacts must be objects")
    if status.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise ProtocolValidationError("status artifact must use schema_version 2")
    if result.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise ProtocolValidationError("result artifact must use schema_version 2")
    if status.get("kind") != "reproduction_status_v2":
        raise ProtocolValidationError("status artifact has invalid kind")
    if result.get("kind") != "reproduction_result_v2":
        raise ProtocolValidationError("result artifact has invalid kind")

    status_identity = validate_identity(status.get("identity"), context="status identity")
    result_identity = validate_identity(result.get("identity"), context="result identity")
    if status_identity != result_identity:
        raise ProtocolValidationError("status and result identities do not match")
    if expected_identity is not None:
        expected = validate_identity(expected_identity, context="expected identity")
        if status_identity != expected:
            raise ProtocolValidationError("evidence identity does not match the active submission")

    if (
        status.get("mode") != status_identity["mode"]
        or result.get("mode") != status_identity["mode"]
    ):
        raise ProtocolValidationError("evidence mode does not match its identity")
    if status.get("stage") != "terminal":
        raise ProtocolValidationError("status artifact is not terminal")
    state = status.get("state")
    if state not in TERMINAL_STATES or result.get("state") != state:
        raise ProtocolValidationError("status and result terminal states do not match")
    if type(status.get("non_evidence")) is not bool or type(result.get("non_evidence")) is not bool:
        raise ProtocolValidationError("evidence non_evidence fields must be boolean")
    if status["non_evidence"] != result["non_evidence"]:
        raise ProtocolValidationError("status and result non_evidence fields do not match")
    if status_identity["mode"] == "formal" and status["non_evidence"]:
        raise ProtocolValidationError("formal evidence cannot be marked non_evidence")
    return status_identity, dict(result)


def _write_pending(path: Path, value: Mapping[str, Any]) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".pending",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(canonical_json(dict(value), indent=2))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def finalize_evidence_pair(
    run_root: str | Path,
    *,
    status: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    """Commit sibling status/result files behind a finalization marker."""
    root = Path(run_root)
    root.mkdir(parents=True, exist_ok=True)
    status_path = root / "status.json"
    result_path = root / "result.json"
    marker_path = root / "finalization.json"
    if status_path.exists() or result_path.exists() or marker_path.exists():
        raise ProtocolValidationError("evidence pair has already been finalized")
    identity, _ = validate_status_result_pair(status, result)
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
        write_json_atomic(
            marker_path,
            {
                "schema_version": FINALIZATION_SCHEMA_VERSION,
                "kind": "reproduction_finalization",
                "status": "finalized",
                "identity": identity,
            },
        )
    finally:
        for path in pending:
            path.unlink(missing_ok=True)


def _read_object(path: Path, *, context: str) -> dict[str, Any]:
    try:
        return parse_json_object(path.read_text(encoding="utf-8"), context=context)
    except OSError as error:
        raise ProtocolValidationError(f"failed to read {context}: {path}") from error


def reopen_finalized_pair(
    run_root: str | Path,
    *,
    expected_identity: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reopen only a pair that has a matching finalization marker."""
    root = Path(run_root)
    marker = _read_object(root / "finalization.json", context="finalization marker")
    strict_fields(
        marker,
        required=("schema_version", "kind", "status", "identity"),
        context="finalization marker",
    )
    if (
        marker["schema_version"] != FINALIZATION_SCHEMA_VERSION
        or marker["kind"] != "reproduction_finalization"
        or marker["status"] != "finalized"
    ):
        raise ProtocolValidationError("finalization marker is invalid")
    status = _read_object(root / "status.json", context="status artifact")
    result = _read_object(root / "result.json", context="result artifact")
    identity, result = validate_status_result_pair(
        status,
        result,
        expected_identity=expected_identity,
    )
    if validate_identity(marker["identity"], context="finalization identity") != identity:
        raise ProtocolValidationError("finalization marker identity does not match evidence")
    return status, result


def _validate_recovery(value: object) -> dict[str, Any]:
    recovery = strict_fields(value, required=RECOVERY_FIELDS, context="recovery provenance")
    if recovery["schema_version"] != 1 or recovery["kind"] != "training_finalization_recovery":
        raise ProtocolValidationError("recovery provenance has an invalid contract")
    recovery_id = require_string(recovery["recovery_id"], field="recovery ID")
    if not RECOVERY_ID.fullmatch(recovery_id) or recovery_id in (".", ".."):
        raise ProtocolValidationError("recovery ID is invalid")
    finalizer_revision = _require_revision(
        recovery["finalizer_revision"],
        field="recovery finalizer revision",
    )
    source_relative_path = require_string(
        recovery["source_relative_path"],
        field="recovery source_relative_path",
    )
    checkpoint_relative_path = require_string(
        recovery["checkpoint_relative_path"],
        field="recovery checkpoint_relative_path",
    )
    checkpoint_path = Path(checkpoint_relative_path)
    if checkpoint_path.is_absolute() or ".." in checkpoint_path.parts:
        raise ProtocolValidationError("recovery checkpoint_relative_path is invalid")
    if (
        recovery["source_terminal_state"] != "failed"
        or recovery["source_failure_code"] != "training_failed"
        or recovery["parser_classification"] != "validation_metrics_unlabeled"
    ):
        raise ProtocolValidationError("recovery source classification is invalid")
    return {
        **recovery,
        "recovery_id": recovery_id,
        "finalizer_revision": finalizer_revision,
        "source_relative_path": source_relative_path,
        "selected_epoch": require_int(
            recovery["selected_epoch"],
            field="recovery selected_epoch",
        ),
        "checkpoint_relative_path": checkpoint_relative_path,
        "validation_jaccard": require_probability(
            recovery["validation_jaccard"],
            field="recovery validation_jaccard",
        ),
        "validation_ddi_rate": require_probability(
            recovery["validation_ddi_rate"],
            field="recovery validation_ddi_rate",
        ),
    }


def reopen_recovered_finalized_pair(
    source_run_root: str | Path,
    recovery_run_root: str | Path,
    *,
    expected_identity: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate recovered training evidence together with its failed source pair."""
    source_root = Path(source_run_root)
    recovery_root = Path(recovery_run_root)
    source_status, source_result = reopen_finalized_pair(
        source_root,
        expected_identity=expected_identity,
    )
    recovered_status, recovered_result = reopen_finalized_pair(
        recovery_root,
        expected_identity=expected_identity,
    )
    if source_status["identity"] != recovered_status["identity"]:
        raise ProtocolValidationError("source and recovery identities do not match")
    if (
        source_status.get("state") != "failed"
        or source_status.get("failure_code") != "training_failed"
        or source_result.get("artifact_type") != "training"
        or source_result.get("failure_code") != "training_failed"
    ):
        raise ProtocolValidationError(
            "recovery source is not the eligible terminal training failure"
        )
    if (
        recovered_status.get("state") != "completed"
        or recovered_result.get("artifact_type") != "training"
    ):
        raise ProtocolValidationError("recovery sibling is not completed training evidence")

    status_recovery = _validate_recovery(recovered_status.get("recovery"))
    result_recovery = _validate_recovery(recovered_result.get("recovery"))
    if status_recovery != result_recovery:
        raise ProtocolValidationError("status and result recovery provenance do not match")
    expected_recovery_root = source_root / "recoveries" / status_recovery["recovery_id"]
    if recovery_root.absolute() != expected_recovery_root.absolute():
        raise ProtocolValidationError("recovery sibling is outside its source attempt namespace")
    expected_source_path = Path(os.path.relpath(source_root, recovery_root)).as_posix()
    if status_recovery["source_relative_path"] != expected_source_path:
        raise ProtocolValidationError("recovery source path does not match its sibling layout")

    checkpoint = recovered_result.get("checkpoint")
    checkpoint_relative_path = (
        checkpoint.get("relative_path") if isinstance(checkpoint, Mapping) else None
    )
    if checkpoint_relative_path != status_recovery["checkpoint_relative_path"]:
        raise ProtocolValidationError("recovery checkpoint provenance does not match its result")
    checkpoint_path = source_root / checkpoint_relative_path
    if not checkpoint_path.is_file() or checkpoint_path.is_symlink():
        raise ProtocolValidationError("recovery checkpoint is missing or is not a regular file")
    checkpoint_size = require_int(
        checkpoint.get("size_bytes"),
        field="recovery checkpoint size_bytes",
    )
    if checkpoint_path.stat().st_size != checkpoint_size:
        raise ProtocolValidationError("recovery checkpoint size does not match its result")
    checkpoint_sha256 = require_sha256(
        checkpoint.get("sha256"),
        field="recovery checkpoint sha256",
    )
    if _file_sha256(checkpoint_path) != checkpoint_sha256:
        raise ProtocolValidationError("recovery checkpoint identity does not match its result")
    if (
        recovered_result.get("best_epoch") != status_recovery["selected_epoch"]
        or checkpoint.get("best_epoch") != status_recovery["selected_epoch"]
        or recovered_result.get("validation_jaccard") != status_recovery["validation_jaccard"]
        or recovered_result.get("validation_ddi_rate") != status_recovery["validation_ddi_rate"]
    ):
        raise ProtocolValidationError("recovery metric provenance does not match its result")
    return recovered_status, recovered_result


def reopen_training_evidence(
    training_run_root: str | Path,
    *,
    source_run_root: str | Path | None = None,
    expected_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reopen terminal formal training evidence and verify its checkpoint bytes."""
    training_root = Path(training_run_root)
    if source_run_root is None:
        status, result = reopen_finalized_pair(
            training_root,
            expected_identity=expected_identity,
        )
        checkpoint_root = training_root
        if result.get("recovery") is not None:
            raise ProtocolValidationError(
                "recovered training evidence requires its source run root"
            )
    else:
        checkpoint_root = Path(source_run_root)
        status, result = reopen_recovered_finalized_pair(
            checkpoint_root,
            training_root,
            expected_identity=expected_identity,
        )
        if result.get("recovery") is None:
            raise ProtocolValidationError("recovery training evidence is missing provenance")

    identity = validate_identity(result.get("identity"), context="training evidence identity")
    if (
        identity["mode"] != "formal"
        or status.get("state") != "completed"
        or status.get("failure_code") is not None
        or result.get("state") != "completed"
        or result.get("artifact_type") != "training"
    ):
        raise ProtocolValidationError("training evidence is not completed formal training")
    if "test_metrics" in result or "rounds" in result:
        raise ProtocolValidationError("training evidence must not contain test metrics")
    if result.get("epochs_requested") != 50 or result.get("epochs_observed") != 50:
        raise ProtocolValidationError("training evidence must record all 50 epochs")

    checkpoint = strict_fields(
        result.get("checkpoint"),
        required=("best_epoch", "relative_path", "sha256", "size_bytes"),
        context="training checkpoint",
    )
    best_epoch = require_int(result.get("best_epoch"), field="training best_epoch")
    checkpoint_best_epoch = require_int(
        checkpoint["best_epoch"],
        field="training checkpoint best_epoch",
    )
    if checkpoint_best_epoch != best_epoch:
        raise ProtocolValidationError("training checkpoint epoch disagrees with evidence")
    checkpoint_relative_path = require_string(
        checkpoint["relative_path"],
        field="training checkpoint relative_path",
    )
    checkpoint_path = Path(checkpoint_relative_path)
    if (
        checkpoint_path.is_absolute()
        or ".." in checkpoint_path.parts
        or str(checkpoint_path) != checkpoint_relative_path
    ):
        raise ProtocolValidationError("training checkpoint path is invalid")
    checkpoint_path = checkpoint_root / checkpoint_path
    try:
        checkpoint_path.resolve().relative_to(checkpoint_root.resolve())
    except ValueError as error:
        raise ProtocolValidationError("training checkpoint escapes its run root") from error
    if not checkpoint_path.is_file() or checkpoint_path.is_symlink():
        raise ProtocolValidationError("training checkpoint is missing or is not a regular file")
    checkpoint_size = require_int(
        checkpoint["size_bytes"],
        field="training checkpoint size_bytes",
    )
    if checkpoint_path.stat().st_size != checkpoint_size:
        raise ProtocolValidationError("training checkpoint size does not match its result")
    checkpoint_sha256 = require_sha256(
        checkpoint["sha256"],
        field="training checkpoint sha256",
    )
    if _file_sha256(checkpoint_path) != checkpoint_sha256:
        raise ProtocolValidationError("training checkpoint identity does not match its result")
    validation_jaccard = require_probability(
        result.get("validation_jaccard"),
        field="training validation_jaccard",
    )
    validation_ddi_rate = require_probability(
        result.get("validation_ddi_rate"),
        field="training validation_ddi_rate",
    )
    return {
        "identity": identity,
        "status": status,
        "result": result,
        "checkpoint": {
            "best_epoch": best_epoch,
            "relative_path": checkpoint_relative_path,
            "sha256": checkpoint_sha256,
            "size_bytes": checkpoint_size,
        },
        "checkpoint_path": checkpoint_path,
        "validation_jaccard": validation_jaccard,
        "validation_ddi_rate": validation_ddi_rate,
    }


def canonical_training_artifact_id(
    attempt_root: str | Path,
    training_run_root: str | Path,
) -> str:
    """Return the canonical attempt-relative ID of a validated training result."""
    root = Path(attempt_root).resolve()
    run_root = Path(training_run_root).resolve()
    artifact = run_root / "result.json"
    try:
        relative = artifact.relative_to(root)
    except ValueError as error:
        raise ProtocolValidationError("training artifact is outside its attempt root") from error
    if relative.name != "result.json" or any(part in ("", ".", "..") for part in relative.parts):
        raise ProtocolValidationError("training artifact ID is not canonical")
    return PurePosixPath(*relative.parts).as_posix()


__all__ = (
    "EVIDENCE_SCHEMA_VERSION",
    "FINALIZATION_SCHEMA_VERSION",
    "IDENTITY_FIELDS",
    "RECOVERY_FIELDS",
    "TERMINAL_STATES",
    "canonical_training_artifact_id",
    "finalize_evidence_pair",
    "reopen_finalized_pair",
    "reopen_recovered_finalized_pair",
    "reopen_training_evidence",
    "validate_identity",
    "validate_status_result_pair",
)
