"""Shared reproduction execution primitives.

This module provides baseline-agnostic mechanical execution helpers (process execution,
progress heartbeat, atomic artifact writing, failure finalization, and layout validation).
It does not contain baseline identities, profile rules, or scientific lifecycle logic.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import threading
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .reproduction_artifacts import (
        finalize_v2_pair,
        terminal_result,
        terminal_status,
    )
except ImportError:  # Direct execution keeps the baselines directory on sys.path.
    from reproduction_artifacts import (
        finalize_v2_pair,
        terminal_result,
        terminal_status,
    )


UTC = timezone.utc  # noqa: UP017 -- archived environments may use Python 3.8.
_PROGRESS_MAX_HEARTBEAT = 50
_PROGRESS_POLL_SECONDS = 0.25
_SHA256 = re.compile(r"[0-9a-f]{64}")
_ADAPTATION_FIELDS = {
    "archived_revision",
    "entrypoint",
    "learning_rate",
    "original_sha256",
    "adapted_sha256",
    "reverse_verification",
    "phase",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    """Write value as JSON to a temporary file and atomically replace path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_progress_status(status_path: Path) -> dict[str, Any] | None:
    """Load and validate the current heartbeat status dictionary."""
    target = status_path / "status.running.json" if status_path.is_dir() else status_path
    try:
        status = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(status, dict):
        return None
    heartbeat = status.get("heartbeat", 0)
    if (
        isinstance(heartbeat, bool)
        or not isinstance(heartbeat, int)
        or not 0 <= heartbeat <= _PROGRESS_MAX_HEARTBEAT
    ):
        return None
    return status


def advance_progress_heartbeat(status_path: Path, heartbeat: int) -> None:
    """Advance the progress heartbeat monotonically."""
    target = status_path / "status.running.json" if status_path.is_dir() else status_path
    if not 0 <= heartbeat <= _PROGRESS_MAX_HEARTBEAT:
        return
    status = load_progress_status(target)
    if status is None or heartbeat <= status.get("heartbeat", 0):
        return
    status["heartbeat"] = heartbeat
    try:
        write_json_atomic(target, status)
    except OSError:
        return


def heartbeat_from_log_text(log_text: str) -> int:
    """Derive progress heartbeat integer from training log line count."""
    line_count = log_text.count("\n")
    if log_text and not log_text.endswith("\n"):
        line_count += 1
    return min(line_count, _PROGRESS_MAX_HEARTBEAT)


def _monitor_progress(
    *,
    status_path: Path,
    log_path: Path,
    stop_event: threading.Event,
) -> None:
    status = load_progress_status(status_path)
    if status is None:
        return
    last_size = -1
    heartbeat = status.get("heartbeat", 0)
    while not stop_event.is_set():
        try:
            size = log_path.stat().st_size
        except OSError:
            size = -1
        if size > last_size:
            last_size = size
            try:
                content = log_path.read_text(encoding="utf-8", errors="replace")
                observed = heartbeat_from_log_text(content)
                if observed > heartbeat:
                    heartbeat = observed
                    advance_progress_heartbeat(status_path, heartbeat)
            except OSError:
                pass
        stop_event.wait(timeout=_PROGRESS_POLL_SECONDS)


def run_logged(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
) -> str:
    """Execute command synchronously, stream stdout/stderr to log_path, and return log text."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            log_file.write(line)
            log_file.flush()
        returncode = process.wait()
    if returncode != 0:
        raise subprocess.CalledProcessError(returncode, command)
    return log_path.read_text(encoding="utf-8", errors="replace")


def run_logged_with_progress(
    command: list[str] | None = None,
    *,
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
    runner: Callable[..., Any] | None = None,
    poll_interval_seconds: float = _PROGRESS_POLL_SECONDS,
    **kwargs: Any,
) -> str:
    """Execute command with a background thread updating status.running.json heartbeat."""
    cmd = command if command is not None else kwargs.get("command")
    if cmd is None:
        raise ValueError("command is required")
    stop_event = threading.Event()
    status_path = log_path.parent / "status.running.json"
    monitor = threading.Thread(
        target=_monitor_progress,
        kwargs={
            "status_path": status_path,
            "log_path": log_path,
            "stop_event": stop_event,
        },
        name="reproduction-progress",
        daemon=True,
    )
    monitor.start()
    execute_fn = runner or run_logged
    try:
        execute_fn(cmd, cwd=cwd, env=env, log_path=log_path)
    finally:
        stop_event.set()
        monitor.join()
    train_log = log_path.read_text(errors="replace")
    advance_progress_heartbeat(
        status_path,
        heartbeat_from_log_text(train_log),
    )
    return train_log


def write_failure_pair(
    root: Path,
    *,
    identity: Mapping[str, str],
    started_at: str,
    artifact_type: str,
    error_type: type[Exception],
    non_evidence: bool = False,
) -> None:
    """Write terminal failed status.json and result.json if neither exists."""
    if not root.is_dir() or any(
        (root / name).exists() for name in ("status.json", "result.json", "finalization.json")
    ):
        return
    status = terminal_status(
        identity,
        state="failed",
        started_at=started_at,
        finished_at=_now(),
        non_evidence=non_evidence,
        failure_code=f"{artifact_type}_failed",
    )
    result = terminal_result(
        identity,
        state="failed",
        non_evidence=non_evidence,
        payload={"artifact_type": artifact_type, "failure_code": f"{artifact_type}_failed"},
    )
    try:
        finalize_v2_pair(root, status=status, result=result, error_type=error_type)
    except Exception:
        return


def validate_run_layout(
    *,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    error_type: type[Exception],
) -> None:
    """Validate that execution run_root does not pre-exist and directories are disjoint."""
    if run_root.exists():
        raise error_type(f"run root already exists: {run_root}")
    if (
        upstream_root == data_dir
        or upstream_root in data_dir.parents
        or data_dir in upstream_root.parents
    ):
        raise error_type("dataset root must be outside archived upstream source")
    if (
        upstream_root == run_root
        or upstream_root in run_root.parents
        or run_root in upstream_root.parents
    ):
        raise error_type("run root must be outside archived upstream source")


def validate_identity_binding(
    identity: Mapping[str, str],
    *,
    program_id: str,
    source_revision: str,
    expected_baseline_id: str | None = None,
    error_type: type[Exception],
) -> None:
    """Validate that controller identity matches program ID and source revision."""
    if identity["program_id"] != program_id:
        raise error_type("controller identity names a different Reproduction Program")
    if identity["model_source_revision"] != source_revision:
        raise error_type("controller identity names a different model source revision")
    if (
        expected_baseline_id is not None
        and identity["scientific_baseline_id"] != expected_baseline_id
    ):
        raise error_type("controller identity names a different scientific baseline")


def read_and_validate_adaptation(
    run_root: Path,
    *,
    entrypoint: str,
    source_revision: str,
    calc_sha256: Callable[[Path], str],
    error_type: type[Exception],
) -> dict[str, Any]:
    """Read and validate adaptation.json against expected entrypoint and revision."""
    try:
        adaptation = json.loads((run_root / "adaptation.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise error_type("source adaptation artifact cannot be read") from error
    if not isinstance(adaptation, Mapping) or set(adaptation) != _ADAPTATION_FIELDS:
        raise error_type("source adaptation artifact has an invalid training schema")
    normalized = dict(adaptation)
    if (
        normalized["archived_revision"] != source_revision
        or normalized["entrypoint"] != entrypoint
        or normalized["reverse_verification"] != "byte-identical"
        or normalized["phase"] != "training"
    ):
        raise error_type("source adaptation artifact does not match the training lane")
    for field in ("original_sha256", "adapted_sha256"):
        value = normalized[field]
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise error_type("source adaptation artifact has an invalid source identity")
    learning_rate = normalized["learning_rate"]
    if (
        isinstance(learning_rate, bool)
        or not isinstance(learning_rate, (int, float))
        or not math.isfinite(float(learning_rate))
        or float(learning_rate) <= 0
    ):
        raise error_type("source adaptation learning rate is invalid")
    adapted_entrypoint = run_root / "work" / "src" / entrypoint
    if not adapted_entrypoint.is_file() or adapted_entrypoint.is_symlink():
        raise error_type("source adapted entrypoint is missing or is not a regular file")
    if calc_sha256(adapted_entrypoint) != normalized["adapted_sha256"]:
        raise error_type("source adaptation identity does not match the adapted entrypoint")
    return normalized


__all__ = (
    "advance_progress_heartbeat",
    "heartbeat_from_log_text",
    "load_progress_status",
    "read_and_validate_adaptation",
    "run_logged",
    "run_logged_with_progress",
    "validate_identity_binding",
    "validate_run_layout",
    "write_failure_pair",
    "write_json_atomic",
)
