#!/usr/bin/env python3
"""Execution runner for archived SafeDrug smoke and formal training/testing lanes."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc  # noqa: UP017 -- archived environments may use Python 3.8.

# Support both relative import and path-based import
if __package__:
    from .reproduction_artifacts import identity_from_environment
    from .reproduction_runner import (
        run_smoke_lane_v2,
        run_test_lane_v2,
        run_training_lane_v2,
    )
    from .safedrug_archived_contract import (
        ARCHIVED_REVISION,
        EPOCH_FORMAL,
        EPOCH_SMOKE,
        GATE_INPUTS,
        TEST_DECLARATION,
        TRAIN_DECLARATION,
        Profile,
        ReproductionError,
        adapt_smoke_source,
        adapt_training_source,
        finalize_result,
        sha256,
        test_command,
        training_command,
        verify_upstream_source,
        write_json,
    )
    from .safedrug_archived_data import load_and_validate_canonical_inputs
    from .safedrug_archived_logs import (
        parse_test_log,
        parse_training_log,
        select_checkpoint,
    )
    from .safedrug_archived_probe import environment_summary
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from reproduction_artifacts import identity_from_environment
    from reproduction_runner import (
        run_smoke_lane_v2,
        run_test_lane_v2,
        run_training_lane_v2,
    )
    from safedrug_archived_contract import (
        ARCHIVED_REVISION,
        EPOCH_FORMAL,
        EPOCH_SMOKE,
        GATE_INPUTS,
        TEST_DECLARATION,
        TRAIN_DECLARATION,
        Profile,
        ReproductionError,
        adapt_smoke_source,
        adapt_training_source,
        finalize_result,
        sha256,
        test_command,
        training_command,
        verify_upstream_source,
        write_json,
    )
    from safedrug_archived_data import load_and_validate_canonical_inputs
    from safedrug_archived_logs import (
        parse_test_log,
        parse_training_log,
        select_checkpoint,
    )
    from safedrug_archived_probe import environment_summary


def run_logged(command: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if completed.returncode != 0:
        raise ReproductionError(
            f"command failed with exit code {completed.returncode}: {command[1]}"
        )


def _run_legacy_smoke_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None = None,
    dispatch_module: Any = None,
) -> None:
    if run_root.exists():
        raise ReproductionError(f"run root already exists: {run_root}")
    if (
        upstream_root == data_dir
        or upstream_root in data_dir.parents
        or data_dir in upstream_root.parents
    ):
        raise ReproductionError("dataset root must be outside archived upstream source")
    if (
        upstream_root == run_root
        or upstream_root in run_root.parents
        or run_root in upstream_root.parents
    ):
        raise ReproductionError("run root must be outside archived upstream source")

    active_lr = learning_rate if learning_rate is not None else profile.learning_rate

    mod = (
        dispatch_module
        or sys.modules.get("safedrug_archived_program")
        or sys.modules.get("baselines.safedrug_archived")
        or sys.modules.get("safedrug_archived")
        or sys.modules[__name__]
    )

    verify_src = getattr(mod, "verify_upstream_source", verify_upstream_source)
    verify_src(upstream_root)

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"archived dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("archived dataset inputs must be regular files, not symlinks")

    load_inputs = getattr(
        mod, "load_and_validate_canonical_inputs", load_and_validate_canonical_inputs
    )
    _, counts, _, _, _ = load_inputs(data_dir)

    get_env_summary = getattr(mod, "environment_summary", environment_summary)
    environment_identity = get_env_summary()

    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")

    adapt_smoke = getattr(mod, "adapt_smoke_source", adapt_smoke_source)
    adapted_source = adapt_smoke(original_source, target_lr=active_lr)

    run_root.mkdir(parents=True)
    work_src = run_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    adapted_entrypoint = work_src / profile.entrypoint
    adapted_entrypoint.write_text(adapted_source, encoding="utf-8")
    data_link = work_src.parent / "data"
    data_link.symlink_to(data_dir, target_is_directory=True)

    model_name = f"{profile.model_name}_{run_root.name}"
    checkpoint_dir = work_src / "saved" / model_name
    checkpoint_dir.mkdir(parents=True)
    started_at = datetime.now(UTC).isoformat()

    calc_sha256 = getattr(mod, "sha256", sha256)
    adaptation: dict[str, Any] = {
        "archived_revision": ARCHIVED_REVISION,
        "entrypoint": profile.entrypoint,
        "learning_rate": active_lr,
        "original_sha256": calc_sha256(original_entrypoint),
        "adapted_sha256": calc_sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "training_default": {
            "from": TEST_DECLARATION,
            "to": TRAIN_DECLARATION,
            "occurrences": 1,
            "reverse_verification": "byte-identical",
        },
        "epoch_limit": {
            "from": EPOCH_FORMAL,
            "to": EPOCH_SMOKE,
            "occurrences": 1,
            "reverse_verification": "byte-identical",
        },
    }
    do_write_json = getattr(mod, "write_json", write_json)
    do_write_json(run_root / "adaptation.json", adaptation)
    do_write_json(
        run_root / "status.json",
        {
            "schema_version": 1,
            "kind": "safedrug_archived_smoke_status",
            "state": "running",
            "stage": "training",
            "learning_rate": active_lr,
            "started_at": started_at,
            "finished_at": None,
            "failure_code": None,
        },
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    run_log = getattr(mod, "run_logged", run_logged)
    train_cmd = getattr(mod, "training_command", training_command)
    parse_train = getattr(mod, "parse_training_log", parse_training_log)
    sel_ckpt = getattr(mod, "select_checkpoint", select_checkpoint)

    try:
        run_log(
            train_cmd(python, adapted_entrypoint, model_name),
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        best_epoch = parse_train(
            (run_root / "train.log").read_text(errors="replace"), expected_epochs=1
        )
        if best_epoch != 0:
            raise ReproductionError(f"smoke mode requires best_epoch 0, observed {best_epoch}")
        checkpoint = sel_ckpt(checkpoint_dir, profile, best_epoch=0)
        finished_at = datetime.now(UTC).isoformat()
        terminal_status = {
            "schema_version": 1,
            "kind": "safedrug_archived_smoke_status",
            "state": "completed",
            "stage": "terminal",
            "learning_rate": active_lr,
            "started_at": started_at,
            "finished_at": finished_at,
            "failure_code": None,
        }
        do_write_json(run_root / "status.json", terminal_status)
        smoke_record = {
            "schema_version": 1,
            "kind": "safedrug_archived_smoke",
            "non_evidence": True,
            "baseline_id": profile.baseline_id,
            "learning_rate": active_lr,
            "source_revision": ARCHIVED_REVISION,
            "environment_sha256": environment_identity["conda_explicit_sha256"],
            "dataset_counts": counts,
            "epochs_requested": 1,
            "epochs_observed": 1,
            "best_epoch": 0,
            "adaptation": {
                "reverse_verification": "byte-identical",
                "training_default": adaptation["training_default"],
                "epoch_limit": adaptation["epoch_limit"],
            },
            "checkpoint": {
                "best_epoch": 0,
                "sha256": calc_sha256(checkpoint),
                "size_bytes": checkpoint.stat().st_size,
            },
            "status": terminal_status,
        }
        do_write_json(run_root / "smoke.json", smoke_record)
    except Exception:
        do_write_json(
            run_root / "status.json",
            {
                "schema_version": 1,
                "kind": "safedrug_archived_smoke_status",
                "state": "failed",
                "stage": "terminal",
                "learning_rate": active_lr,
                "started_at": started_at,
                "finished_at": datetime.now(UTC).isoformat(),
                "failure_code": "smoke_failed",
            },
        )
        raise


def _run_legacy_formal_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None = None,
    dispatch_module: Any = None,
) -> None:
    if run_root.exists():
        raise ReproductionError(f"run root already exists: {run_root}")
    if (
        upstream_root == data_dir
        or upstream_root in data_dir.parents
        or data_dir in upstream_root.parents
    ):
        raise ReproductionError("dataset root must be outside archived upstream source")
    if (
        upstream_root == run_root
        or upstream_root in run_root.parents
        or run_root in upstream_root.parents
    ):
        raise ReproductionError("run root must be outside archived upstream source")

    active_lr = learning_rate if learning_rate is not None else profile.learning_rate

    mod = (
        dispatch_module
        or sys.modules.get("safedrug_archived_program")
        or sys.modules.get("baselines.safedrug_archived")
        or sys.modules.get("safedrug_archived")
        or sys.modules[__name__]
    )

    verify_src = getattr(mod, "verify_upstream_source", verify_upstream_source)
    verify_src(upstream_root)

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"archived dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("archived dataset inputs must be regular files, not symlinks")

    load_inputs = getattr(
        mod, "load_and_validate_canonical_inputs", load_and_validate_canonical_inputs
    )
    _, counts, _, _, _ = load_inputs(data_dir)

    get_env_summary = getattr(mod, "environment_summary", environment_summary)
    environment_identity = get_env_summary()

    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")

    adapt_training = getattr(mod, "adapt_training_source", adapt_training_source)
    adapted_source = adapt_training(original_source, target_lr=active_lr)

    run_root.mkdir(parents=True)
    work_src = run_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    adapted_entrypoint = work_src / profile.entrypoint
    adapted_entrypoint.write_text(adapted_source, encoding="utf-8")
    data_link = work_src.parent / "data"
    data_link.symlink_to(data_dir, target_is_directory=True)

    model_name = f"{profile.model_name}_{run_root.name}"
    checkpoint_dir = work_src / "saved" / model_name
    checkpoint_dir.mkdir(parents=True)
    started_at = datetime.now(UTC).isoformat()

    calc_sha256 = getattr(mod, "sha256", sha256)
    adaptation: dict[str, Any] = {
        "archived_revision": ARCHIVED_REVISION,
        "entrypoint": profile.entrypoint,
        "learning_rate": active_lr,
        "original_sha256": calc_sha256(original_entrypoint),
        "adapted_sha256": calc_sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "change": {"from": TEST_DECLARATION, "to": TRAIN_DECLARATION},
    }
    do_write_json = getattr(mod, "write_json", write_json)
    do_write_json(run_root / "adaptation.json", adaptation)

    status: dict[str, Any] = {
        "schema_version": 1,
        "kind": "safedrug_archived_formal_status",
        "baseline_id": profile.baseline_id,
        "learning_rate": active_lr,
        "state": "running",
        "stage": "training",
        "started_at": started_at,
        "finished_at": None,
        "failure_code": None,
    }
    do_write_json(run_root / "status.json", status)

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )

    run_log = getattr(mod, "run_logged", run_logged)
    train_cmd = getattr(mod, "training_command", training_command)
    parse_train = getattr(mod, "parse_training_log", parse_training_log)
    sel_ckpt = getattr(mod, "select_checkpoint", select_checkpoint)
    tst_cmd = getattr(mod, "test_command", test_command)
    parse_tst = getattr(mod, "parse_test_log", parse_test_log)
    fin_result = getattr(mod, "finalize_result", finalize_result)

    try:
        run_log(
            train_cmd(python, adapted_entrypoint, model_name),
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        best_epoch = parse_train((run_root / "train.log").read_text(errors="replace"))
        checkpoint = sel_ckpt(checkpoint_dir, profile, best_epoch)
        status["stage"] = "testing"
        do_write_json(run_root / "status.json", status)
        run_log(
            tst_cmd(python, original_entrypoint, profile, model_name, checkpoint),
            cwd=work_src,
            env=environment,
            log_path=run_root / "test.log",
        )
        test_data = parse_tst((run_root / "test.log").read_text(errors="replace"))
        terminal_status = {
            "schema_version": 1,
            "kind": "safedrug_archived_formal_status",
            "baseline_id": profile.baseline_id,
            "learning_rate": active_lr,
            "state": "completed",
            "stage": "terminal",
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
            "failure_code": None,
        }
        fin_result(
            run_root,
            terminal_status,
            {
                "schema_version": 1,
                "baseline_id": profile.baseline_id,
                "source_revision": ARCHIVED_REVISION,
                "archived_learning_rate": active_lr,
                "dataset_counts": counts,
                "environment": environment_identity,
                "adaptation": adaptation,
                "checkpoint": {
                    "best_epoch": best_epoch,
                    "sha256": calc_sha256(checkpoint),
                    "size_bytes": checkpoint.stat().st_size,
                },
                **test_data,
            },
        )
    except Exception:
        do_write_json(
            run_root / "status.json",
            {
                "schema_version": 1,
                "kind": "safedrug_archived_formal_status",
                "baseline_id": profile.baseline_id,
                "learning_rate": active_lr,
                "state": "failed",
                "stage": "terminal",
                "started_at": started_at,
                "finished_at": datetime.now(UTC).isoformat(),
                "failure_code": "formal_failed",
            },
        )
        raise


def _dispatch_module(dispatch_module: Any) -> Any:
    return (
        dispatch_module
        or sys.modules.get("safedrug_archived_program")
        or sys.modules.get("baselines.safedrug_archived")
        or sys.modules.get("safedrug_archived")
        or sys.modules.get("__main__")
        or sys.modules[__name__]
    )


def run_formal_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None = None,
    dispatch_module: Any = None,
    phase: str = "training",
    selection_path: Path | None = None,
) -> None:
    """Run the controller-identified training or serial test phase."""
    if phase not in ("training", "test"):
        raise ReproductionError("formal phase must be 'training' or 'test'")
    identity = identity_from_environment(mode="formal", error_type=ReproductionError)
    if identity is None:
        raise ReproductionError("formal execution requires a controller-issued v2 identity")
    module = _dispatch_module(dispatch_module)
    if phase == "training":
        run_training_lane_v2(
            module=module,
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            learning_rate=learning_rate,
            identity=identity,
            program_id="safedrug-archived",
            source_revision=ARCHIVED_REVISION,
            gate_inputs=GATE_INPUTS,
            error_type=ReproductionError,
        )
    else:
        run_test_lane_v2(
            module=module,
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            identity=identity,
            program_id="safedrug-archived",
            source_revision=ARCHIVED_REVISION,
            gate_inputs=GATE_INPUTS,
            error_type=ReproductionError,
            selection_path=selection_path,
        )


def run_test_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    dispatch_module: Any = None,
    selection_path: Path | None = None,
) -> None:
    """Run the test phase against a finalized training lane."""
    run_formal_lane(
        profile=profile,
        upstream_root=upstream_root,
        data_dir=data_dir,
        run_root=run_root,
        python=python,
        dispatch_module=dispatch_module,
        phase="test",
        selection_path=selection_path,
    )


def run_smoke_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
    learning_rate: float | None = None,
    dispatch_module: Any = None,
) -> None:
    """Run a v2 controller-identified smoke or the preserved local legacy smoke."""
    identity = identity_from_environment(mode="smoke", error_type=ReproductionError)
    if identity is None:
        return _run_legacy_smoke_lane(
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            learning_rate=learning_rate,
            dispatch_module=dispatch_module,
        )
    run_smoke_lane_v2(
        module=_dispatch_module(dispatch_module),
        profile=profile,
        upstream_root=upstream_root,
        data_dir=data_dir,
        run_root=run_root,
        python=python,
        learning_rate=learning_rate,
        identity=identity,
        program_id="safedrug-archived",
        source_revision=ARCHIVED_REVISION,
        gate_inputs=GATE_INPUTS,
        error_type=ReproductionError,
    )


__all__ = (
    "run_formal_lane",
    "run_logged",
    "run_smoke_lane",
    "run_test_lane",
)
