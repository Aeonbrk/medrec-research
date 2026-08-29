"""Shared v2 training and evaluation flow used by the explicit programs."""

from __future__ import annotations

import json
import math
import os
import re
import threading
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .reproduction_artifacts import (
        finalize_v2_pair,
        reopen_recovered_v2_pair,
        reopen_v2_pair,
        terminal_result,
        terminal_status,
    )
except ImportError:  # Direct execution keeps the baselines directory on sys.path.
    from reproduction_artifacts import (
        finalize_v2_pair,
        reopen_recovered_v2_pair,
        reopen_v2_pair,
        terminal_result,
        terminal_status,
    )

try:
    from .reproduction_history import (
        load_native_validation_history,
        reconcile_history_checkpoint,
    )
except ImportError:  # Direct execution keeps the baselines directory on sys.path.
    from reproduction_history import (
        load_native_validation_history,
        reconcile_history_checkpoint,
    )


_MISSING_VALIDATION_METRICS = "training log must contain validation Jaccard and DDI metrics"
_RECOVERY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_PROGRESS_MAX_HEARTBEAT = 50
_PROGRESS_POLL_SECONDS = 0.25
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
    return datetime.now().astimezone().isoformat()


def _module_value(module: Any, name: str) -> Any:
    try:
        return getattr(module, name)
    except AttributeError as error:
        raise RuntimeError(
            f"Reproduction Program is missing required runtime hook: {name}"
        ) from error


def _validate_layout(
    *,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    error_type: type[Exception],
) -> None:
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


def _validate_identity_binding(
    identity: Mapping[str, str],
    *,
    program_id: str,
    source_revision: str,
    profile: Any,
    error_type: type[Exception],
) -> None:
    if identity["program_id"] != program_id:
        raise error_type("controller identity names a different Reproduction Program")
    if identity["model_source_revision"] != source_revision:
        raise error_type("controller identity names a different model source revision")
    expected_baseline = profile.baseline_id
    if expected_baseline.startswith("molerec"):
        expected_baseline = "molerec"
    elif expected_baseline.startswith("safedrug"):
        expected_baseline = "safedrug"
    if identity["scientific_baseline_id"] != expected_baseline:
        raise error_type("controller identity names a different scientific baseline")


def _required_inputs(profile: Any, gate_inputs: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*profile.required_inputs, *gate_inputs)))


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
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


def _load_progress_status(status_path: Path) -> dict[str, Any] | None:
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
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


def _advance_progress_heartbeat(status_path: Path, heartbeat: int) -> None:
    if not 0 <= heartbeat <= _PROGRESS_MAX_HEARTBEAT:
        return
    status = _load_progress_status(status_path)
    if status is None or heartbeat <= status["heartbeat"]:
        return
    status["heartbeat"] = heartbeat
    try:
        _write_json_atomic(status_path, status)
    except OSError:
        return


def _heartbeat_from_log_text(log_text: str) -> int:
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
    status = _load_progress_status(status_path)
    if status is None:
        return
    last_size = -1
    heartbeat = status["heartbeat"]
    while not stop_event.is_set():
        try:
            size = log_path.stat().st_size
        except OSError:
            size = -1
        if size > last_size:
            last_size = size
            if heartbeat < _PROGRESS_MAX_HEARTBEAT:
                heartbeat += 1
                status["heartbeat"] = heartbeat
                try:
                    _write_json_atomic(status_path, status)
                except OSError:
                    return
        if stop_event.wait(_PROGRESS_POLL_SECONDS):
            return


def _run_logged_with_progress(
    *,
    run_logged: Any,
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
) -> str:
    stop_event = threading.Event()
    monitor = threading.Thread(
        target=_monitor_progress,
        kwargs={
            "status_path": log_path.parent / "status.running.json",
            "log_path": log_path,
            "stop_event": stop_event,
        },
        name="reproduction-progress",
        daemon=True,
    )
    monitor.start()
    try:
        run_logged(command, cwd=cwd, env=env, log_path=log_path)
    finally:
        stop_event.set()
        monitor.join()
    train_log = log_path.read_text(errors="replace")
    _advance_progress_heartbeat(
        log_path.parent / "status.running.json",
        _heartbeat_from_log_text(train_log),
    )
    return train_log


def _failure_pair(
    *,
    root: Path,
    identity: Mapping[str, str],
    started_at: str,
    artifact_type: str,
    error_type: type[Exception],
    non_evidence: bool = False,
) -> None:
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
        # Preserve the original failure. The missing marker makes the partial pair inadmissible.
        return


def run_training_lane_v2(
    *,
    module: Any,
    profile: Any,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None,
    identity: Mapping[str, str],
    program_id: str,
    source_revision: str,
    gate_inputs: tuple[str, ...],
    error_type: type[Exception],
) -> None:
    """Run one formal training lane and finalize only a training artifact pair."""
    _validate_layout(
        upstream_root=upstream_root,
        data_dir=data_dir,
        run_root=run_root,
        error_type=error_type,
    )
    _validate_identity_binding(
        identity,
        program_id=program_id,
        source_revision=source_revision,
        profile=profile,
        error_type=error_type,
    )
    active_lr = learning_rate if learning_rate is not None else profile.learning_rate
    verify_source = _module_value(module, "verify_upstream_source")
    verify_source(upstream_root)

    required_inputs = _required_inputs(profile, gate_inputs)
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise error_type(f"dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise error_type("dataset inputs must be regular files, not symlinks")

    records, counts, _, _, _ = _module_value(module, "load_and_validate_canonical_inputs")(data_dir)
    environment_identity = _module_value(module, "environment_summary")()
    if environment_identity.get("conda_explicit_sha256") != identity["environment_sha256"]:
        raise error_type("runtime environment identity does not match controller identity")

    source_dir = upstream_root / "src"
    del records
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")
    adapted_source = _module_value(module, "adapt_training_source")(
        original_source,
        target_lr=active_lr,
    )

    run_root.mkdir(parents=True)
    work_src = run_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    adapted_entrypoint = work_src / profile.entrypoint
    adapted_entrypoint.write_text(adapted_source, encoding="utf-8")
    (work_src.parent / "data").symlink_to(data_dir, target_is_directory=True)

    model_name = f"{profile.model_name}_{run_root.name}"
    checkpoint_dir = (
        work_src.parent / "saved" / model_name
        if profile.baseline_id.startswith("molerec")
        else work_src / "saved" / model_name
    )
    checkpoint_dir.mkdir(parents=True)
    started_at = _now()
    calc_sha256 = _module_value(module, "sha256")
    adaptation = {
        "archived_revision": source_revision,
        "entrypoint": profile.entrypoint,
        "learning_rate": active_lr,
        "original_sha256": calc_sha256(original_entrypoint),
        "adapted_sha256": calc_sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "phase": "training",
    }
    write_json = _module_value(module, "write_json")
    write_json(run_root / "adaptation.json", adaptation)
    _write_json_atomic(
        run_root / "status.running.json",
        {
            "schema_version": 2,
            "kind": "reproduction_progress_v2",
            "identity": dict(identity),
            "mode": "formal",
            "state": "training",
            "stage": "training",
            "started_at": started_at,
            "finished_at": None,
            "non_evidence": False,
            "heartbeat": 0,
        },
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    run_logged = _module_value(module, "run_logged")
    try:
        train_log = _run_logged_with_progress(
            run_logged=run_logged,
            command=[
                *_module_value(module, "training_command")(python, adapted_entrypoint, model_name),
                *getattr(profile, "training_args", ()),
            ],
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        best_epoch = _module_value(module, "parse_training_log")(train_log, expected_epochs=50)
        checkpoint = _module_value(module, "select_checkpoint")(checkpoint_dir, profile, best_epoch)
        validation = _module_value(module, "parse_validation_metrics")(train_log)
        finished_at = _now()
        status = terminal_status(
            identity,
            state="completed",
            started_at=started_at,
            finished_at=finished_at,
            non_evidence=False,
        )
        result = terminal_result(
            identity,
            state="completed",
            non_evidence=False,
            payload={
                "artifact_type": "training",
                "scientific_baseline_id": identity["scientific_baseline_id"],
                "profile_id": identity["profile_id"],
                "learning_rate": active_lr,
                "dataset_counts": counts,
                "environment": environment_identity,
                "adaptation": adaptation,
                "epochs_requested": 50,
                "epochs_observed": 50,
                "best_epoch": best_epoch,
                "validation_jaccard": validation["validation_jaccard"],
                "validation_ddi_rate": validation["validation_ddi_rate"],
                "checkpoint": {
                    "best_epoch": best_epoch,
                    "sha256": calc_sha256(checkpoint),
                    "size_bytes": checkpoint.stat().st_size,
                    "relative_path": str(checkpoint.relative_to(run_root)),
                },
            },
        )
        finalize_v2_pair(run_root, status=status, result=result, error_type=error_type)
    except Exception:
        _failure_pair(
            root=run_root,
            identity=identity,
            started_at=started_at,
            artifact_type="training",
            error_type=error_type,
        )
        raise


def _read_adaptation(
    run_root: Path,
    *,
    profile: Any,
    source_revision: str,
    calc_sha256: Any,
    error_type: type[Exception],
) -> dict[str, Any]:
    try:
        adaptation = json.loads((run_root / "adaptation.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise error_type("source adaptation artifact cannot be read") from error
    if not isinstance(adaptation, Mapping) or set(adaptation) != _ADAPTATION_FIELDS:
        raise error_type("source adaptation artifact has an invalid training schema")
    normalized = dict(adaptation)
    if (
        normalized["archived_revision"] != source_revision
        or normalized["entrypoint"] != profile.entrypoint
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
    adapted_entrypoint = run_root / "work" / "src" / profile.entrypoint
    if not adapted_entrypoint.is_file() or adapted_entrypoint.is_symlink():
        raise error_type("source adapted entrypoint is missing or is not a regular file")
    if calc_sha256(adapted_entrypoint) != normalized["adapted_sha256"]:
        raise error_type("source adaptation identity does not match the adapted entrypoint")
    return normalized


def recover_training_lane_v2(
    *,
    module: Any,
    profile: Any,
    data_dir: Path,
    run_root: Path,
    recovery_id: str,
    finalizer_revision: str,
    identity: Mapping[str, str],
    program_id: str,
    source_revision: str,
    gate_inputs: tuple[str, ...],
    error_type: type[Exception],
) -> Path:
    """Finalize one eligible administrative failure without invoking scientific work."""
    if not _RECOVERY_ID.fullmatch(recovery_id) or recovery_id in (".", ".."):
        raise error_type("recovery ID is invalid")
    if not _IMMUTABLE_REVISION.fullmatch(finalizer_revision):
        raise error_type("finalizer revision must be an immutable Git revision")
    _validate_identity_binding(
        identity,
        program_id=program_id,
        source_revision=source_revision,
        profile=profile,
        error_type=error_type,
    )
    recovery_root = run_root / "recoveries" / recovery_id
    if recovery_root.exists():
        raise error_type(f"recovery root already exists: {recovery_root}")

    source_status, source_result = reopen_v2_pair(
        run_root,
        expected_identity=identity,
        error_type=error_type,
    )
    if (
        source_status.get("state") != "failed"
        or source_status.get("failure_code") != "training_failed"
        or source_result.get("artifact_type") != "training"
        or source_result.get("failure_code") != "training_failed"
    ):
        raise error_type("source pair is not an eligible terminal training failure")

    try:
        train_log = (run_root / "train.log").read_text(errors="replace")
    except OSError as error:
        raise error_type("source training log cannot be read") from error
    _module_value(module, "parse_training_log")(train_log, expected_epochs=50)
    try:
        _module_value(module, "parse_validation_metrics")(train_log)
    except error_type as error:
        if str(error) != _MISSING_VALIDATION_METRICS:
            raise error_type("source parser failure is not recoverable") from error
    else:
        raise error_type("source validation parser does not reproduce the recoverable failure")

    required_inputs = _required_inputs(profile, gate_inputs)
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise error_type(f"dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise error_type("dataset inputs must be regular files, not symlinks")
    records, counts, _, _, _ = _module_value(module, "load_and_validate_canonical_inputs")(data_dir)
    del records
    environment_identity = _module_value(module, "environment_summary")()
    if environment_identity.get("conda_explicit_sha256") != identity["environment_sha256"]:
        raise error_type("runtime environment identity does not match controller identity")

    calc_sha256 = _module_value(module, "sha256")
    adaptation = _read_adaptation(
        run_root,
        profile=profile,
        source_revision=source_revision,
        calc_sha256=calc_sha256,
        error_type=error_type,
    )
    learning_rate = adaptation["learning_rate"]

    model_name = f"{profile.model_name}_{run_root.name}"
    work_src = run_root / "work" / "src"
    checkpoint_dir = (
        work_src.parent / "saved" / model_name
        if profile.baseline_id.startswith("molerec")
        else work_src / "saved" / model_name
    )
    history_path = _module_value(module, "native_history_path")(checkpoint_dir, model_name)
    validation = load_native_validation_history(
        history_path,
        expected_epochs=50,
        error_type=error_type,
    )
    best_epoch = int(validation["best_epoch"])
    checkpoint = _module_value(module, "select_checkpoint")(
        checkpoint_dir,
        profile,
        best_epoch,
    )
    reconcile_history_checkpoint(checkpoint, validation, error_type=error_type)
    checkpoint_relative_path = str(checkpoint.relative_to(run_root))
    recovery = {
        "schema_version": 1,
        "kind": "training_finalization_recovery",
        "recovery_id": recovery_id,
        "finalizer_revision": finalizer_revision,
        "source_relative_path": Path(os.path.relpath(run_root, recovery_root)).as_posix(),
        "source_terminal_state": source_status["state"],
        "source_failure_code": source_status["failure_code"],
        "parser_classification": "validation_metrics_unlabeled",
        "selected_epoch": best_epoch,
        "checkpoint_relative_path": checkpoint_relative_path,
        "validation_jaccard": validation["validation_jaccard"],
        "validation_ddi_rate": validation["validation_ddi_rate"],
    }
    started_at = _now()
    status = terminal_status(
        identity,
        state="completed",
        started_at=started_at,
        finished_at=_now(),
        non_evidence=False,
    )
    status["recovery"] = recovery
    result = terminal_result(
        identity,
        state="completed",
        non_evidence=False,
        payload={
            "artifact_type": "training",
            "scientific_baseline_id": identity["scientific_baseline_id"],
            "profile_id": identity["profile_id"],
            "learning_rate": float(learning_rate),
            "dataset_counts": counts,
            "environment": environment_identity,
            "adaptation": adaptation,
            "epochs_requested": 50,
            "epochs_observed": validation["epochs_observed"],
            "best_epoch": best_epoch,
            "validation_jaccard": validation["validation_jaccard"],
            "validation_ddi_rate": validation["validation_ddi_rate"],
            "checkpoint": {
                "best_epoch": best_epoch,
                "sha256": calc_sha256(checkpoint),
                "size_bytes": checkpoint.stat().st_size,
                "relative_path": checkpoint_relative_path,
            },
            "recovery": recovery,
        },
    )
    finalize_v2_pair(recovery_root, status=status, result=result, error_type=error_type)
    reopen_recovered_v2_pair(
        run_root,
        recovery_root,
        expected_identity=identity,
        error_type=error_type,
    )
    return recovery_root


def run_smoke_lane_v2(
    *,
    module: Any,
    profile: Any,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None,
    identity: Mapping[str, str],
    program_id: str,
    source_revision: str,
    gate_inputs: tuple[str, ...],
    error_type: type[Exception],
) -> None:
    """Run one non-evidence smoke and finalize a non-evidence v2 pair."""
    _validate_layout(
        upstream_root=upstream_root,
        data_dir=data_dir,
        run_root=run_root,
        error_type=error_type,
    )
    _validate_identity_binding(
        identity,
        program_id=program_id,
        source_revision=source_revision,
        profile=profile,
        error_type=error_type,
    )
    active_lr = learning_rate if learning_rate is not None else profile.learning_rate
    _module_value(module, "verify_upstream_source")(upstream_root)
    required_inputs = _required_inputs(profile, gate_inputs)
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise error_type(f"dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise error_type("dataset inputs must be regular files, not symlinks")

    _, counts, _, _, _ = _module_value(module, "load_and_validate_canonical_inputs")(data_dir)
    environment_identity = _module_value(module, "environment_summary")()
    if environment_identity.get("conda_explicit_sha256") != identity["environment_sha256"]:
        raise error_type("runtime environment identity does not match controller identity")
    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")
    adapted_source = _module_value(module, "adapt_smoke_source")(
        original_source,
        target_lr=active_lr,
    )

    run_root.mkdir(parents=True)
    work_src = run_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    adapted_entrypoint = work_src / profile.entrypoint
    adapted_entrypoint.write_text(adapted_source, encoding="utf-8")
    (work_src.parent / "data").symlink_to(data_dir, target_is_directory=True)
    model_name = f"{profile.model_name}_{run_root.name}"
    checkpoint_dir = (
        work_src.parent / "saved" / model_name
        if profile.baseline_id.startswith("molerec")
        else work_src / "saved" / model_name
    )
    checkpoint_dir.mkdir(parents=True)
    started_at = _now()
    calc_sha256 = _module_value(module, "sha256")
    adaptation = {
        "archived_revision": source_revision,
        "entrypoint": profile.entrypoint,
        "learning_rate": active_lr,
        "original_sha256": calc_sha256(original_entrypoint),
        "adapted_sha256": calc_sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "phase": "smoke",
    }
    write_json = _module_value(module, "write_json")
    write_json(run_root / "adaptation.json", adaptation)
    _write_json_atomic(
        run_root / "status.running.json",
        {
            "schema_version": 2,
            "kind": "reproduction_progress_v2",
            "identity": dict(identity),
            "mode": "smoke",
            "state": "training",
            "stage": "training",
            "started_at": started_at,
            "finished_at": None,
            "non_evidence": True,
            "heartbeat": 0,
        },
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    try:
        train_log = _run_logged_with_progress(
            run_logged=_module_value(module, "run_logged"),
            command=[
                *_module_value(module, "training_command")(python, adapted_entrypoint, model_name),
                *getattr(profile, "training_args", ()),
            ],
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        best_epoch = _module_value(module, "parse_training_log")(train_log, expected_epochs=1)
        if best_epoch != 0:
            raise error_type(f"smoke mode requires best_epoch 0, observed {best_epoch}")
        checkpoint = _module_value(module, "select_checkpoint")(checkpoint_dir, profile, best_epoch)
        finished_at = _now()
        status = terminal_status(
            identity,
            state="completed",
            started_at=started_at,
            finished_at=finished_at,
            non_evidence=True,
        )
        result = terminal_result(
            identity,
            state="completed",
            non_evidence=True,
            payload={
                "artifact_type": "smoke",
                "scientific_baseline_id": identity["scientific_baseline_id"],
                "profile_id": identity["profile_id"],
                "learning_rate": active_lr,
                "dataset_counts": counts,
                "environment": environment_identity,
                "adaptation": adaptation,
                "epochs_requested": 1,
                "epochs_observed": 1,
                "best_epoch": 0,
                "checkpoint": {
                    "best_epoch": 0,
                    "sha256": calc_sha256(checkpoint),
                    "size_bytes": checkpoint.stat().st_size,
                    "relative_path": str(checkpoint.relative_to(run_root)),
                },
            },
        )
        finalize_v2_pair(run_root, status=status, result=result, error_type=error_type)
    except Exception:
        _failure_pair(
            root=run_root,
            identity=identity,
            started_at=started_at,
            artifact_type="smoke",
            error_type=error_type,
            non_evidence=True,
        )
        raise


def run_test_lane_v2(
    *,
    module: Any,
    profile: Any,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    training_source_root: Path | None = None,
    python: str,
    identity: Mapping[str, str],
    program_id: str,
    source_revision: str,
    gate_inputs: tuple[str, ...],
    error_type: type[Exception],
    selection_path: Path | None = None,
) -> None:
    """Run one serial formal test from a finalized training checkpoint."""
    if not run_root.is_dir():
        raise error_type(f"training run root not found: {run_root}")
    _validate_identity_binding(
        identity,
        program_id=program_id,
        source_revision=source_revision,
        profile=profile,
        error_type=error_type,
    )
    if training_source_root is None:
        checkpoint_root = run_root
        training_status, training_result = reopen_v2_pair(
            run_root,
            expected_identity=identity,
            error_type=error_type,
        )
    else:
        checkpoint_root = training_source_root
        training_status, training_result = reopen_recovered_v2_pair(
            training_source_root,
            run_root,
            error_type=error_type,
        )
        training_identity = training_result["identity"]
        _validate_identity_binding(
            training_identity,
            program_id=program_id,
            source_revision=source_revision,
            profile=profile,
            error_type=error_type,
        )
        shared_fields = (
            "attempt_id",
            "lane_id",
            "scientific_baseline_id",
            "program_id",
            "profile_id",
            "model_source_revision",
            "preprocessing_revision",
            "snapshot_id",
            "environment_sha256",
            "mode",
        )
        if any(training_identity[field] != identity[field] for field in shared_fields):
            raise error_type("test identity does not continue the recovered training lane")
    if (
        training_status["state"] != "completed"
        or training_result.get("artifact_type") != "training"
    ):
        raise error_type("test admission requires a completed training artifact")
    required_inputs = _required_inputs(profile, gate_inputs)
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise error_type(f"dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise error_type("dataset inputs must be regular files, not symlinks")
    _module_value(module, "verify_upstream_source")(upstream_root)

    checkpoint_data = training_result.get("checkpoint")
    relative_path = (
        checkpoint_data.get("relative_path") if isinstance(checkpoint_data, Mapping) else None
    )
    if (
        not isinstance(relative_path, str)
        or Path(relative_path).is_absolute()
        or ".." in Path(relative_path).parts
    ):
        raise error_type("training artifact has an invalid checkpoint path")
    checkpoint = checkpoint_root / relative_path
    if not checkpoint.is_file() or checkpoint.is_symlink():
        raise error_type("training checkpoint is missing or is not a regular file")
    calc_sha256 = _module_value(module, "sha256")
    if calc_sha256(checkpoint) != checkpoint_data.get("sha256"):
        raise error_type("training checkpoint identity does not match its artifact")

    test_root = run_root / "test"
    if test_root.exists():
        raise error_type(f"test run root already exists: {test_root}")
    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    model_name = f"{profile.model_name}_{run_root.name}"
    test_root.mkdir()
    work_src = test_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    (work_src.parent / "data").symlink_to(data_dir, target_is_directory=True)
    started_at = _now()
    write_json = _module_value(module, "write_json")
    write_json(
        test_root / "status.running.json",
        {
            "schema_version": 2,
            "kind": "reproduction_progress_v2",
            "identity": dict(identity),
            "mode": "formal",
            "state": "testing",
            "stage": "testing",
            "started_at": started_at,
            "finished_at": None,
            "non_evidence": False,
        },
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    try:
        test_builder = _module_value(module, "test_command")
        if profile.baseline_id.startswith("safedrug"):
            command = test_builder(
                python,
                original_entrypoint,
                profile,
                model_name,
                checkpoint,
                lane_id=identity["lane_id"],
                selection_path=selection_path,
            )
        else:
            command = test_builder(python, original_entrypoint, profile, model_name, checkpoint)
        command = [*command, *getattr(profile, "training_args", ())]
        _module_value(module, "run_logged")(
            command,
            cwd=work_src,
            env=environment,
            log_path=test_root / "test.log",
        )
        if profile.baseline_id.startswith("molerec"):
            parsed = _module_value(module, "parse_formal_test_log")(
                (test_root / "test.log").read_text(errors="replace")
            )
        else:
            parsed = _module_value(module, "parse_test_log")(
                (test_root / "test.log").read_text(errors="replace")
            )
        rounds = parsed.get("rounds", parsed.get("test_rounds"))
        summary = parsed.get("harness_summary")
        if not isinstance(rounds, list) or len(rounds) != 10:
            raise error_type("formal test parser did not produce exactly ten rounds")
        if not isinstance(summary, Mapping) or len(summary) != 5:
            raise error_type("formal test parser did not produce five summary metrics")
        environment_identity = _module_value(module, "environment_summary")()
        if environment_identity.get("conda_explicit_sha256") != identity["environment_sha256"]:
            raise error_type("runtime environment identity does not match controller identity")
        finished_at = _now()
        status = terminal_status(
            identity,
            state="completed",
            started_at=started_at,
            finished_at=finished_at,
            non_evidence=False,
        )
        result = terminal_result(
            identity,
            state="completed",
            non_evidence=False,
            payload={
                "artifact_type": "test",
                "scientific_baseline_id": identity["scientific_baseline_id"],
                "profile_id": identity["profile_id"],
                "dataset_counts": training_result["dataset_counts"],
                "environment": environment_identity,
                "epochs_requested": training_result["epochs_requested"],
                "epochs_observed": training_result["epochs_observed"],
                "checkpoint": checkpoint_data,
                "rounds": rounds,
                "harness_summary": dict(summary),
                "upstream_summary": parsed.get("upstream_summary"),
            },
        )
        finalize_v2_pair(test_root, status=status, result=result, error_type=error_type)
    except Exception:
        _failure_pair(
            root=test_root,
            identity=identity,
            started_at=started_at,
            artifact_type="test",
            error_type=error_type,
        )
        raise


__all__ = (
    "recover_training_lane_v2",
    "run_smoke_lane_v2",
    "run_test_lane_v2",
    "run_training_lane_v2",
)
