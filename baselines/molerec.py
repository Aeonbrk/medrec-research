#!/usr/bin/env python3
"""MoleRec Reproduction Program.

This module is the deep owner of MoleRec Table 1 baseline lifecycle, source adaptation,
validation, and execution on 319 under Python 3.8.16.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc  # noqa: UP017 -- archived environments may use Python 3.8.

if __package__:
    from .molerec_data import (
        COMMON_INPUTS,
        EXPECTED_COUNTS,
        EXPECTED_STATISTICS,
        GATE_INPUTS,
        REPORTED_PAPER_METADATA,
        ReproductionError,
        count_dataset,
        load_and_validate_canonical_inputs,
        matrix_shape,
        require_executable_counts,
    )
    from .molerec_logs import (
        parse_formal_test_log,
        parse_test_log,
        parse_training_log,
        parse_validation_metrics,
        select_checkpoint,
    )
    from .molerec_probe import (
        PYG_EXTENSION_MODULES,
        REGISTRY_IMPORT_MODULES,
        check_cuda_tensor,
        check_imports,
        check_pyg_extensions,
        check_rdkit,
        environment_summary,
        probe_environment_details,
        run_probe,
    )
    from .reproduction_artifacts import identity_from_environment
    from .reproduction_runner import (
        recover_training_lane_v2,
        run_smoke_lane_v2,
        run_test_lane_v2,
        run_training_lane_v2,
    )
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from molerec_data import (
        COMMON_INPUTS,
        EXPECTED_COUNTS,
        EXPECTED_STATISTICS,
        GATE_INPUTS,
        REPORTED_PAPER_METADATA,
        ReproductionError,
        count_dataset,
        load_and_validate_canonical_inputs,
        matrix_shape,
        require_executable_counts,
    )
    from molerec_logs import (
        parse_formal_test_log,
        parse_test_log,
        parse_training_log,
        parse_validation_metrics,
        select_checkpoint,
    )
    from molerec_probe import (
        PYG_EXTENSION_MODULES,
        REGISTRY_IMPORT_MODULES,
        check_cuda_tensor,
        check_imports,
        check_pyg_extensions,
        check_rdkit,
        environment_summary,
        probe_environment_details,
        run_probe,
    )
    from reproduction_artifacts import identity_from_environment
    from reproduction_runner import (
        recover_training_lane_v2,
        run_smoke_lane_v2,
        run_test_lane_v2,
        run_training_lane_v2,
    )

ARCHIVED_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"

__all__ = (
    "ARCHIVED_REVISION",
    "COMMON_INPUTS",
    "EPOCH_FORMAL",
    "EPOCH_SMOKE",
    "EXPECTED_COUNTS",
    "EXPECTED_STATISTICS",
    "GATE_INPUTS",
    "PROFILES",
    "PYG_EXTENSION_MODULES",
    "REGISTRY_IMPORT_MODULES",
    "REPORTED_PAPER_METADATA",
    "ROUND_PATTERN",
    "TEST_DECLARATION",
    "TRAIN_DECLARATION",
    "Profile",
    "ReproductionError",
    "adapt_epoch_source",
    "adapt_learning_rate_source",
    "adapt_smoke_source",
    "adapt_training_source",
    "build_parser",
    "check_cuda_tensor",
    "check_imports",
    "check_pyg_extensions",
    "check_rdkit",
    "checkpoint_directory",
    "count_dataset",
    "environment_summary",
    "execute",
    "finalize_result",
    "load_and_validate_canonical_inputs",
    "main",
    "matrix_shape",
    "native_history_path",
    "parse_formal_test_log",
    "parse_test_log",
    "parse_training_log",
    "parse_validation_metrics",
    "probe",
    "probe_environment_details",
    "profile_for",
    "recover_formal_lane",
    "require_executable_counts",
    "run_formal_lane",
    "run_logged",
    "run_probe",
    "run_smoke_lane",
    "run_test_lane",
    "select_checkpoint",
    "sha256",
    "test_command",
    "test_mode_default",
    "training_command",
    "verify_upstream_source",
    "write_json",
)

TEST_DECLARATION = (
    "    parser.add_argument('--Test', action='store_true', help=\"evaluating mode\")\n"
)
TRAIN_DECLARATION = TEST_DECLARATION
EPOCH_FORMAL = "        '--epochs', default=50, type=int,\n"
EPOCH_SMOKE = "        '--epochs', default=1, type=int,\n"
ROUND_PATTERN = re.compile(r"^\s*([A-Za-z0-9_]+)\s*:\s*([0-9.]+)\s*$")


@dataclass(frozen=True)
class Profile:
    baseline_id: str
    entrypoint: str
    model_name: str
    learning_rate: float
    required_inputs: tuple[str, ...]
    checkpoint_pattern: re.Pattern[str]
    scientific_baseline_id: str = "molerec"
    test_uses_basename: bool = False
    training_args: tuple[str, ...] = ()


PROFILES = {
    "molerec": Profile(
        "molerec",
        "main.py",
        "MoleRec",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_TARGET_.*_JA_.*_DDI_.*\.model$"),
        scientific_baseline_id="molerec",
    ),
    "molerec-embedding": Profile(
        "molerec-embedding",
        "main.py",
        "MoleRec",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_TARGET_.*_JA_.*_DDI_.*\.model$"),
        scientific_baseline_id="molerec",
        training_args=("--embedding",),
    ),
}


def profile_for(baseline_id: str) -> Profile:
    try:
        return PROFILES[baseline_id]
    except KeyError as error:
        raise ReproductionError(f"unknown MoleRec baseline '{baseline_id}'") from error


def _format_lr(lr: float) -> str:
    if lr == 5e-4:
        return "5e-4"
    if lr == 1e-4:
        return "1e-4"
    if lr == 1e-5:
        return "1e-5"
    return f"{lr:g}"


def _lr_literals(lr: float) -> tuple[str, ...]:
    return tuple(dict.fromkeys((_format_lr(lr), str(lr))))


def _find_lr_declaration(source: str, literals: tuple[str, ...]) -> re.Match[str] | None:
    value_pattern = "|".join(re.escape(literal) for literal in literals)
    patterns = (
        re.compile(
            rf"(?m)(?P<prefix>parser\.add_argument\(\s*['\"]--lr['\"][^\n]*?"
            rf"\bdefault\s*=\s*)(?P<value>{value_pattern})"
        ),
        re.compile(rf"(?P<prefix>\blr\s*=\s*)(?P<value>{value_pattern})"),
    )
    matches = [match for pattern in patterns for match in pattern.finditer(source)]
    return matches[0] if len(matches) == 1 else None


def adapt_learning_rate_source(source: str, target_lr: float, original_lr: float = 5e-4) -> str:
    """Adapt the learning rate in training source code with byte-reversibility check."""
    if target_lr == original_lr:
        return source
    target_lr_str = _format_lr(target_lr)
    match = _find_lr_declaration(source, _lr_literals(original_lr))
    if not match:
        if _find_lr_declaration(source, _lr_literals(target_lr)) is not None:
            return source
        raise ReproductionError("MoleRec learning rate declaration drifted from audited source")
    original_literal = match.group("value")
    adapted = source[: match.start("value")] + target_lr_str + source[match.end("value") :]
    if original_literal in adapted or adapted.replace(target_lr_str, original_literal, 1) != source:
        raise ReproductionError("learning rate adaptation is not byte-reversible")
    return adapted


def adapt_training_source(source: str, target_lr: float | None = None) -> str:
    """Prepare training source code and optionally adapt learning rate."""
    if target_lr is not None and target_lr != 5e-4:
        return adapt_learning_rate_source(source, target_lr)
    return source


def adapt_epoch_source(source: str) -> str:
    """Select one training epoch for non-evidence smoke testing."""
    if source.count(EPOCH_FORMAL) != 1 or EPOCH_SMOKE in source:
        raise ReproductionError("MoleRec EPOCH declaration drifted from audited source")
    adapted = source.replace(EPOCH_FORMAL, EPOCH_SMOKE, 1)
    if adapted.replace(EPOCH_SMOKE, EPOCH_FORMAL, 1) != source:
        raise ReproductionError("epoch adaptation changed unexpected source bytes")
    return adapted


def adapt_smoke_source(source: str, target_lr: float | None = None) -> str:
    """Compose training-mode and 1-epoch adaptations with joint reversibility."""
    train_adapted = adapt_training_source(source, target_lr=target_lr)
    rate_was_adapted = train_adapted != source
    smoke_adapted = adapt_epoch_source(train_adapted)
    reversed_epoch = smoke_adapted.replace(EPOCH_SMOKE, EPOCH_FORMAL, 1)
    if rate_was_adapted and target_lr is not None:
        reversed_source = adapt_learning_rate_source(reversed_epoch, 5e-4, original_lr=target_lr)
    else:
        reversed_source = reversed_epoch
    if reversed_source != source:
        raise ReproductionError("smoke adaptation is not byte-reversible")
    return smoke_adapted


def test_mode_default(source: str) -> bool:
    del source
    return False


def checkpoint_directory(work_src: Path, model_name: str) -> Path:
    """Return the checkpoint directory for MoleRec models."""
    return work_src.parent / "saved" / model_name


def native_history_path(checkpoint_dir: Path, model_name: str) -> Path:
    """Return the frozen MoleRec history written beside checkpoints."""
    del model_name
    return checkpoint_dir / "history.pkl"


def training_command(python: str, entrypoint: Path, model_name: str) -> list[str]:
    return [
        python,
        str(entrypoint),
        "--model_name",
        model_name,
    ]


def test_command(
    python: str,
    entrypoint: Path,
    profile: Profile,
    model_name: str,
    checkpoint: Path,
    *,
    lane_id: str | None = None,
    selection_path: Path | None = None,
    **kwargs: Any,
) -> list[str]:
    del lane_id, selection_path, kwargs
    resume_target = checkpoint.name if profile.test_uses_basename else str(checkpoint)
    return [
        python,
        str(entrypoint),
        "--Test",
        "--model_name",
        model_name,
        "--resume_path",
        resume_target,
    ]


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def finalize_result(
    run_root: Path,
    status: dict[str, Any],
    result: dict[str, Any],
    dispatch_module: Any = None,
) -> None:
    """Publish terminal status before embedding it in result.json."""
    mod = dispatch_module or sys.modules[__name__]
    do_write_json = getattr(mod, "write_json", write_json)
    do_write_json(run_root / "status.json", status)
    do_write_json(run_root / "result.json", {**result, "status": status})


def verify_upstream_source(upstream_root: Path) -> None:
    source_dir = upstream_root / "src"
    if not source_dir.is_dir():
        raise ReproductionError(f"archived upstream missing src directory: {source_dir}")
    entrypoints = {profile.entrypoint for profile in PROFILES.values()}
    for entrypoint in entrypoints:
        path = source_dir / entrypoint
        if not path.is_file():
            raise ReproductionError(f"archived upstream missing entrypoint: {path}")


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
    mod = dispatch_module or sys.modules[__name__]

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
    checkpoint_dir = work_src.parent / "saved" / model_name
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
            "kind": "molerec_smoke_status",
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
            [*train_cmd(python, adapted_entrypoint, model_name), *profile.training_args],
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
            "kind": "molerec_smoke_status",
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
            "kind": "molerec_smoke",
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
                "kind": "molerec_smoke_status",
                "state": "failed",
                "stage": "terminal",
                "learning_rate": active_lr,
                "started_at": started_at,
                "finished_at": datetime.now(UTC).isoformat(),
                "failure_code": "smoke_failed",
            },
        )
        raise


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
    training_source_root: Path | None = None,
    test_root: Path | None = None,
) -> None:
    """Run the controller-identified training or serial test phase."""
    if phase not in ("training", "test"):
        raise ReproductionError("formal phase must be 'training' or 'test'")
    identity = identity_from_environment(mode="formal", error_type=ReproductionError)
    if identity is None:
        raise ReproductionError("formal execution requires a controller-issued v2 identity")
    module = dispatch_module or sys.modules[__name__]
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
            program_id="molerec",
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
            program_id="molerec",
            source_revision=ARCHIVED_REVISION,
            gate_inputs=GATE_INPUTS,
            error_type=ReproductionError,
            selection_path=selection_path,
            training_source_root=training_source_root,
            test_root=test_root,
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


def recover_formal_lane(
    *,
    profile: Profile,
    data_dir: Path,
    run_root: Path,
    recovery_id: str,
    finalizer_revision: str,
    dispatch_module: Any = None,
) -> Path:
    """Recover one controller-identified terminal training finalization failure."""
    identity = identity_from_environment(mode="formal", error_type=ReproductionError)
    if identity is None:
        raise ReproductionError("recovery requires a controller-issued v2 identity")
    return recover_training_lane_v2(
        module=dispatch_module or sys.modules[__name__],
        profile=profile,
        data_dir=data_dir,
        run_root=run_root,
        recovery_id=recovery_id,
        finalizer_revision=finalizer_revision,
        identity=identity,
        program_id="molerec",
        source_revision=ARCHIVED_REVISION,
        gate_inputs=GATE_INPUTS,
        error_type=ReproductionError,
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
        module=dispatch_module or sys.modules[__name__],
        profile=profile,
        upstream_root=upstream_root,
        data_dir=data_dir,
        run_root=run_root,
        python=python,
        learning_rate=learning_rate,
        identity=identity,
        program_id="molerec",
        source_revision=ARCHIVED_REVISION,
        gate_inputs=GATE_INPUTS,
        error_type=ReproductionError,
    )


def probe(request: Mapping[str, Any]) -> dict[str, Any]:
    """Execute a Program-level probe request."""
    baseline_id = str(request["baseline_id"])
    upstream_root = Path(request["upstream_root"])
    data_dir = Path(request["dataset_root"]) if request.get("dataset_root") else None
    scope = str(request.get("scope", "full"))
    return run_probe(
        baseline_id=baseline_id,
        upstream_root=upstream_root,
        data_dir=data_dir,
        scope=scope,
        dispatch_module=sys.modules[__name__],
    )


def execute(request: Mapping[str, Any]) -> dict[str, Any]:
    """Execute a Program-level reproduction request (smoke, formal, or recovery)."""
    mode = str(request.get("mode", "formal"))
    baseline_id = str(request["baseline_id"])
    upstream_root = Path(request["upstream_root"]) if request.get("upstream_root") else Path(".")
    data_dir = Path(request["dataset_root"])
    run_root = Path(request["run_root"])
    python = str(request.get("python", sys.executable))
    learning_rate = (
        float(request["learning_rate"]) if request.get("learning_rate") is not None else None
    )
    profile = profile_for(baseline_id)

    if mode == "smoke":
        run_smoke_lane(
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            learning_rate=learning_rate,
            dispatch_module=sys.modules[__name__],
        )
        return {"state": "completed", "mode": "smoke", "run_root": str(run_root)}
    elif mode == "formal":
        phase = str(request.get("phase", "training"))
        selection_path = Path(request["selection_path"]) if request.get("selection_path") else None
        training_source_root = (
            Path(request["training_source_root"]) if request.get("training_source_root") else None
        )
        test_root = Path(request["test_root"]) if request.get("test_root") else None
        run_formal_lane(
            profile=profile,
            upstream_root=upstream_root,
            data_dir=data_dir,
            run_root=run_root,
            python=python,
            learning_rate=learning_rate,
            dispatch_module=sys.modules[__name__],
            phase=phase,
            selection_path=selection_path,
            training_source_root=training_source_root,
            test_root=test_root,
        )
        return {"state": "completed", "mode": "formal", "phase": phase, "run_root": str(run_root)}
    elif mode == "recovery":
        recovery_id = str(request["recovery_id"])
        finalizer_revision = str(request["finalizer_revision"])
        marker_path = recover_formal_lane(
            profile=profile,
            data_dir=data_dir,
            run_root=run_root,
            recovery_id=recovery_id,
            finalizer_revision=finalizer_revision,
            dispatch_module=sys.modules[__name__],
        )
        return {"state": "completed", "mode": "recovery", "marker_path": str(marker_path)}
    else:
        raise ReproductionError(f"unknown execution mode '{mode}'")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run MoleRec Table 1 reproduction program lanes or probe environment on 319."
    )
    parser.add_argument(
        "baseline_id",
        nargs="?",
        default=None,
        choices=sorted(PROFILES.keys()),
        help="Scientific baseline or hyperparameter profile to run",
    )
    parser.add_argument(
        "--baseline-id",
        dest="baseline_id_opt",
        choices=sorted(PROFILES.keys()),
        help="Scientific baseline or hyperparameter profile to run",
    )
    parser.add_argument(
        "--mode",
        choices=["probe", "smoke", "formal"],
        default="formal",
        help="Execution mode: probe environment/dataset, smoke test (1 epoch), or formal lane",
    )
    parser.add_argument(
        "--upstream-root",
        type=Path,
        required=True,
        help="Path to the archived MoleRec upstream repository",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        help="Path to the prepared dataset directory containing final pickle inputs",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        help="Path to the directory where run outputs, logs, and markers will be written",
    )
    parser.add_argument(
        "--python",
        default="python",
        help="Python executable to invoke for training/testing",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        help="Override the profile default learning rate",
    )
    parser.add_argument(
        "--scope",
        choices=["environment", "full"],
        default="full",
        help="Probe scope (probe mode only)",
    )
    parser.add_argument(
        "--phase",
        choices=["training", "test"],
        default="training",
        help="Formal reproduction phase (formal mode only)",
    )
    parser.add_argument(
        "--selection",
        type=Path,
        help="Path to selection.json artifact (formal test phase only)",
    )
    parser.add_argument(
        "--training-source-root",
        type=Path,
        help="Path to training run root to copy checkpoint from (formal test phase only)",
    )
    parser.add_argument(
        "--test-root",
        type=Path,
        help="Path to test output directory where artifacts will be finalized (formal test phase only)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    baseline_id = args.baseline_id or args.baseline_id_opt
    if not baseline_id:
        parser.error("baseline_id is required")

    if args.mode == "probe":
        result = run_probe(
            baseline_id=baseline_id,
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve() if args.dataset_root else None,
            scope=args.scope,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    if args.dataset_root is None:
        parser.error("--dataset-root is required for smoke and formal modes")
    if args.run_root is None:
        parser.error("--run-root is required for smoke and formal modes")

    if args.mode == "smoke":
        run_smoke_lane(
            profile=profile_for(baseline_id),
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve(),
            run_root=args.run_root.resolve(),
            python=args.python,
            learning_rate=args.learning_rate,
        )
    else:
        run_formal_lane(
            profile=profile_for(baseline_id),
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve(),
            run_root=args.run_root.resolve(),
            python=args.python,
            learning_rate=args.learning_rate,
            phase=args.phase,
            selection_path=args.selection,
            training_source_root=(
                args.training_source_root.resolve() if args.training_source_root else None
            ),
            test_root=args.test_root.resolve() if args.test_root else None,
        )


if __name__ == "__main__":
    main()
