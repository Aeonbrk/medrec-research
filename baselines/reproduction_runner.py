"""Shared v2 training and evaluation flow used by the explicit programs."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .reproduction_artifacts import (
        finalize_v2_pair,
        reopen_v2_pair,
        terminal_result,
        terminal_status,
    )
except ImportError:  # Direct execution keeps the baselines directory on sys.path.
    from reproduction_artifacts import (
        finalize_v2_pair,
        reopen_v2_pair,
        terminal_result,
        terminal_status,
    )


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
    checkpoint_dir = work_src / "saved" / model_name
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
    write_json(
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
        },
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    run_logged = _module_value(module, "run_logged")
    try:
        run_logged(
            _module_value(module, "training_command")(python, adapted_entrypoint, model_name),
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        train_log = (run_root / "train.log").read_text(errors="replace")
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
    checkpoint_dir = work_src / "saved" / model_name
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
    write_json(
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
        },
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    try:
        _module_value(module, "run_logged")(
            _module_value(module, "training_command")(python, adapted_entrypoint, model_name),
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        train_log = (run_root / "train.log").read_text(errors="replace")
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
    training_status, training_result = reopen_v2_pair(
        run_root,
        expected_identity=identity,
        error_type=error_type,
    )
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
    checkpoint = run_root / relative_path
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


__all__ = ("run_smoke_lane_v2", "run_test_lane_v2", "run_training_lane_v2")
