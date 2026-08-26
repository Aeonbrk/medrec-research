"""Shared v2 identity and finalization rules for Reproduction Mode evidence."""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ._validation import (
    canonical_json,
    parse_json_object,
    require_sha256,
    require_string,
    strict_fields,
    write_json_atomic,
)
from .errors import ProtocolValidationError

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


__all__ = (
    "EVIDENCE_SCHEMA_VERSION",
    "FINALIZATION_SCHEMA_VERSION",
    "IDENTITY_FIELDS",
    "TERMINAL_STATES",
    "finalize_evidence_pair",
    "reopen_finalized_pair",
    "validate_identity",
    "validate_status_result_pair",
)
