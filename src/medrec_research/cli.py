"""Clean and simple Command-Line Interface for MedRec Research."""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
from collections.abc import Callable, Sequence
from hashlib import sha256
from pathlib import Path

from ._validation import parse_json_object, write_json_atomic
from .commands import (
    accept_comparison_command,
    format_baseline_table,
    parse_prediction_records,
)
from .dataset import DatasetManifest
from .errors import ProtocolValidationError
from .evaluation import evaluate_predictions
from .molerec_evaluation import (
    audit_prepared_table1_evaluation,
    claim_table1_evaluation,
    finalize_table1_evaluation,
    prepare_table1_evaluation,
)
from .reference import ReferenceConfig, run_reference_slice
from .registry import BaselineRegistry
from .remote_executor import (
    FrozenSchedule,
    RemoteExecutor,
    validate_reproduction_continuation,
)

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _nonnegative_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return parsed


# -----------------------------------------------------------------------------
# Handlers
# -----------------------------------------------------------------------------
def _reference(args: argparse.Namespace) -> int:
    """Run baseline reference slice."""
    config = ReferenceConfig(top_k=args.top_k, seed=args.seed)
    record = run_reference_slice(
        manifest_path=args.manifest,
        visits_path=args.visits,
        config=config,
    )
    record.write(args.output)
    return 0


def _accept_comparison(args: argparse.Namespace) -> int:
    """Accept and record comparison run."""
    manifest = DatasetManifest.from_json(args.manifest.read_text(encoding="utf-8"))
    registry = BaselineRegistry.from_toml(args.registry.read_text(encoding="utf-8"))
    baseline = registry.get(args.baseline_id)
    prediction_bytes = args.predictions.read_bytes()
    raw_predictions = parse_json_object(
        prediction_bytes.decode("utf-8"),
        context="predictions file",
    )
    records = parse_prediction_records(raw_predictions)

    raw_config = parse_json_object(
        args.run_config.read_text(encoding="utf-8"),
        context="comparison run config",
    )
    budget_bytes = args.adaptation_budget.read_bytes()
    adaptation_budget_sha256 = sha256(budget_bytes).hexdigest()

    vocab_lines = [
        line.strip()
        for line in args.medication_vocabulary.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    run_record = accept_comparison_command(
        baseline=baseline,
        manifest=manifest,
        predictions=records,
        run_config=raw_config,
        medication_vocabulary=tuple(vocab_lines),
        adaptation_budget_sha256=adaptation_budget_sha256,
        prediction_artifact_sha256=sha256(prediction_bytes).hexdigest(),
    )
    run_record.write(args.output)
    return 0


def _evaluate(args: argparse.Namespace) -> int:
    """Evaluate predictions file."""
    raw_predictions = parse_json_object(
        args.predictions.read_text(encoding="utf-8"),
        context="predictions file",
    )
    records = parse_prediction_records(raw_predictions)
    eval_result = evaluate_predictions(records)
    output_dict = eval_result.to_dict()
    if args.output:
        args.output.write_text(json.dumps(output_dict, indent=2), encoding="utf-8")
    else:
        print(json.dumps(output_dict, indent=2))
    return 0


def _baseline_list(args: argparse.Namespace) -> int:
    """List registered baselines."""
    registry_path = args.registry
    if not registry_path.exists():
        print(f"medrec: error: registry file not found: {registry_path}", file=sys.stderr)
        return 1
    registry = BaselineRegistry.from_toml(registry_path.read_text(encoding="utf-8"))
    print(format_baseline_table(registry))
    return 0


def _local_source_revision(
    repository: Path,
    *,
    require_clean: bool,
    runner: Runner = subprocess.run,
) -> str:
    """Return the immutable local revision without exposing Git output."""

    def git(*arguments: str) -> str:
        try:
            completed = runner(
                ["git", "-C", str(repository), *arguments],
                capture_output=True,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise ProtocolValidationError("local Git source check failed") from error
        if completed.returncode != 0:
            raise ProtocolValidationError("local Git source check failed")
        return completed.stdout.strip()

    if require_clean and git("status", "--porcelain", "--untracked-files=all"):
        raise ProtocolValidationError("remote submission requires a clean Git worktree")
    return git("rev-parse", "HEAD")


def _gpu_list(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(item) for item in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be comma-separated nonnegative integers") from error
    if not parsed or any(item < 0 for item in parsed) or len(parsed) != len(set(parsed)):
        raise argparse.ArgumentTypeError("must be unique comma-separated nonnegative integers")
    return parsed


def _cpu_set_list(value: str) -> tuple[str, ...]:
    parsed = tuple(item.strip() for item in value.split(";"))
    if not parsed or any(not item for item in parsed):
        raise argparse.ArgumentTypeError("must be semicolon-separated CPU lists or ranges")
    return parsed


def _lane_artifact(value: str) -> tuple[str, str]:
    lane_id, separator, artifact_id = value.partition("=")
    if not separator or not lane_id or not artifact_id:
        raise argparse.ArgumentTypeError("must be LANE_ID=RELATIVE_RESULT_JSON")
    return lane_id, artifact_id


def _reproduction_cpu_sets(
    args: argparse.Namespace,
    lanes: tuple[tuple[str, int], ...],
) -> tuple[str | None, ...]:
    cpu_set = getattr(args, "cpu_set", None)
    cpu_sets = getattr(args, "cpu_sets", None)
    if cpu_set is not None and cpu_sets is not None:
        raise ProtocolValidationError("use only one of --cpu-set and --cpu-sets")
    if len(lanes) == 1:
        if cpu_sets is not None:
            raise ProtocolValidationError("one baseline requires --cpu-set")
        return (cpu_set,)
    if cpu_set is not None:
        raise ProtocolValidationError("a batch requires --cpu-sets")
    if cpu_sets is None:
        return (None,) * len(lanes)
    if len(cpu_sets) != len(lanes):
        raise ProtocolValidationError(
            f"--cpu-sets requires one CPU set per lane ({len(lanes)} expected)"
        )
    return tuple(cpu_sets)


def _legacy_archived_baselines(registry: BaselineRegistry) -> tuple[str, ...]:
    """Derive the preserved four-baseline selector from the registry."""
    baseline_ids = tuple(
        baseline.baseline_id
        for baseline in registry.baselines
        if baseline.reproduction_program == "safedrug-archived"
    )
    if len(baseline_ids) != 4:
        raise ProtocolValidationError(
            "registry must declare exactly four archived baselines for the legacy selector"
        )
    return baseline_ids


def _reproduction_lanes(
    args: argparse.Namespace, registry: BaselineRegistry | None = None
) -> tuple[tuple[str, int], ...]:
    if args.baseline_id == "all":
        if args.gpu is not None or args.gpus is None:
            raise ProtocolValidationError(
                "'all' requires four unique --gpus for the legacy batch or seven for "
                "successor lanes, and no --gpu"
            )
        if registry is None:
            raise ProtocolValidationError("'all' requires a loaded baseline registry")
        legacy_baselines = _legacy_archived_baselines(registry)
        if len(args.gpus) == len(legacy_baselines):
            return tuple(zip(legacy_baselines, args.gpus, strict=True))
        successor_lanes = registry.reproduction_lanes
        if successor_lanes and len(args.gpus) == len(successor_lanes):
            lane_ids = tuple(lane.lane_id for lane in successor_lanes)
            return tuple(zip(lane_ids, args.gpus, strict=True))
        raise ProtocolValidationError(
            f"'all' requires unique --gpus matching either the {len(legacy_baselines)} archived baselines or {len(successor_lanes)} reproduction lanes"
        )
    if args.gpu is None or args.gpus is not None:
        raise ProtocolValidationError("one baseline requires --gpu and no --gpus")
    return ((args.baseline_id, args.gpu),)


def _reproduce(
    args: argparse.Namespace,
    *,
    executor: RemoteExecutor | None = None,
    git_runner: Runner = subprocess.run,
) -> int:
    """Plan or submit one or a declared batch of Reproduction Mode lanes."""
    try:
        registry = BaselineRegistry.load(args.registry)
    except FileNotFoundError as error:
        raise ProtocolValidationError("baseline registry file not found") from error
    lanes = _reproduction_lanes(args, registry)
    cpu_sets = _reproduction_cpu_sets(args, lanes)
    source_revision = _local_source_revision(
        Path.cwd(),
        require_clean=not args.dry_run,
        runner=git_runner,
    )
    attempt_id = getattr(args, "attempt_id", None) or (
        f"attempt-{source_revision[:12]}-{secrets.token_hex(4)}"
    )
    active_executor = executor or RemoteExecutor(registry)
    successor_lane_ids = {lane.lane_id for lane in registry.reproduction_lanes}
    schedule: FrozenSchedule | None = None
    if any(baseline_id in successor_lane_ids for baseline_id, _ in lanes):
        schedule_path = getattr(args, "schedule", None)
        if schedule_path is None:
            raise ProtocolValidationError(
                "successor formal reproduction requires an accepted frozen schedule artifact"
            )
        schedule = FrozenSchedule.from_json(
            schedule_path,
            expected_lane_ids=tuple(lane.lane_id for lane in registry.reproduction_lanes),
        )
        cpu_sets = active_executor.validate_frozen_schedule(
            schedule,
            source_revision=source_revision,
            attempt_id=attempt_id,
            requested_lanes=lanes,
            requested_cpu_sets=cpu_sets,
            require_complete=args.baseline_id == "all",
        )
    results: list[dict[str, object]] = []
    failed = False
    for (baseline_id, gpu_index), cpu_set in zip(lanes, cpu_sets, strict=True):
        try:
            submission = active_executor.run_baseline(
                baseline_id,
                source_revision=source_revision,
                gpu_index=gpu_index,
                remote_root=args.remote_root,
                data_root=args.data_root,
                min_free_gpu_mib=args.min_free_gpu_mib,
                min_free_disk_gib=args.min_free_disk_gib,
                cpu_set=cpu_set,
                dry_run=args.dry_run,
                attempt_id=attempt_id,
                schedule=schedule,
            )
            results.append(
                {
                    "baseline_id": submission.baseline_id,
                    "attempt_id": submission.attempt_id or attempt_id,
                    "command": submission.command,
                    "gpu": gpu_index,
                    "cpu_set": cpu_set,
                    "host": submission.host,
                    "preflight": (
                        "passed" if submission.preflight_performed else "not_run_dry_run"
                    ),
                    "session_id": submission.session_id,
                    "state": "submitted" if submission.preflight_performed else "planned",
                }
            )
        except ProtocolValidationError as error:
            failed = True
            results.append(
                {
                    "baseline_id": baseline_id,
                    "error": str(error),
                    "gpu": gpu_index,
                    "state": "blocked",
                }
            )
    print(
        json.dumps(
            {"mode": "reproduction", "results": results},
            indent=2,
            sort_keys=True,
        )
    )
    return 2 if failed else 0


def _reproduce_smoke(
    args: argparse.Namespace,
    *,
    executor: RemoteExecutor | None = None,
    git_runner: Runner = subprocess.run,
) -> int:
    """Plan or submit one or a declared batch of Reproduction Mode smoke lanes."""
    try:
        registry = BaselineRegistry.load(args.registry)
    except FileNotFoundError as error:
        raise ProtocolValidationError("baseline registry file not found") from error
    lanes = _reproduction_lanes(args, registry)
    cpu_sets = _reproduction_cpu_sets(args, lanes)

    source_revision = _local_source_revision(
        Path.cwd(),
        require_clean=not args.dry_run,
        runner=git_runner,
    )
    attempt_id = getattr(args, "attempt_id", None) or (
        f"attempt-{source_revision[:12]}-{secrets.token_hex(4)}"
    )
    active_executor = executor or RemoteExecutor(registry)
    results: list[dict[str, object]] = []
    failed = False
    for (baseline_id, gpu_index), cpu_set in zip(lanes, cpu_sets, strict=True):
        try:
            submission = active_executor.run_smoke(
                baseline_id,
                source_revision=source_revision,
                gpu_index=gpu_index,
                remote_root=args.remote_root,
                data_root=args.data_root,
                min_free_gpu_mib=args.min_free_gpu_mib,
                min_free_disk_gib=args.min_free_disk_gib,
                cpu_set=cpu_set,
                dry_run=args.dry_run,
                attempt_id=attempt_id,
            )
            results.append(
                {
                    "baseline_id": submission.baseline_id,
                    "attempt_id": submission.attempt_id or attempt_id,
                    "command": submission.command,
                    "gpu": gpu_index,
                    "cpu_set": cpu_set,
                    "host": submission.host,
                    "preflight": (
                        "passed" if submission.preflight_performed else "not_run_dry_run"
                    ),
                    "session_id": submission.session_id,
                    "state": "submitted" if submission.preflight_performed else "planned",
                }
            )
        except ProtocolValidationError as error:
            failed = True
            results.append(
                {
                    "baseline_id": baseline_id,
                    "error": str(error),
                    "gpu": gpu_index,
                    "state": "blocked",
                }
            )
    print(
        json.dumps(
            {"mode": "smoke", "results": results},
            indent=2,
            sort_keys=True,
        )
    )
    return 2 if failed else 0


def _stage_safedrug_c721(args: argparse.Namespace) -> int:
    """Stage SafeDrug c721 dataset into staging directory."""
    from .safedrug_c721 import stage_safedrug_c721

    proof = stage_safedrug_c721(
        preprocessing_checkout=args.preprocessing_checkout,
        prescriptions_path=args.prescriptions,
        diagnoses_path=args.diagnoses,
        procedures_path=args.procedures,
        ddi_path=args.drug_ddi,
        staging_directory=args.staging_directory,
        python=args.python,
        input_manifest_path=args.input_manifest,
    )
    print(
        json.dumps(
            {
                "status": "staged",
                "source_revision": proof["source_revision"],
                "outputs": proof["outputs"],
                "staging_directory": str(args.staging_directory),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _stage_molerec_snapshot(args: argparse.Namespace) -> int:
    """Build and atomically publish the additive MoleRec eight-file snapshot."""
    from .molerec_snapshot import build_molerec_snapshot, publish_molerec_snapshot

    build_molerec_snapshot(
        common_snapshot=args.common_snapshot,
        molerec_data_directory=args.molerec_data_directory,
        staging_directory=args.staging_directory,
    )
    proof = publish_molerec_snapshot(
        staging_directory=args.staging_directory,
        snapshot_directory=args.snapshot_directory,
        proof_path=args.proof,
    )
    print(
        json.dumps(
            {
                "status": "published",
                "proof": proof,
                "snapshot_directory": str(args.snapshot_directory),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _audit_safedrug_table2(args: argparse.Namespace) -> int:
    """Audit four formal reproduction results against Table 2 and emit public-safe packet."""
    from .reproduction_audit import audit_safedrug_table2

    result_paths = {
        "gamenet": args.gamenet_result,
        "safedrug": args.safedrug_result,
        "retain": args.retain_result,
        "leap-safedrug": args.leap_result,
    }
    packet = audit_safedrug_table2(
        ledger_path=args.ledger,
        result_paths=result_paths,
        output_path=args.output,
        reference_path=args.reference,
        data_root=args.data_root,
    )
    print(
        json.dumps(
            {
                "verdict": packet["verdict"],
                "interval_checks_passed": packet["interval_checks_passed"],
                "relationship_checks_passed": packet["relationship_checks_passed"],
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _audit_molerec_table1(args: argparse.Namespace) -> int:
    """Audit five formal reproduction results against MoleRec Table 1 and emit public-safe packet."""
    from .molerec_reproduction_audit import audit_molerec_table1

    result_paths = {
        "retain": args.retain_result,
        "leap": args.leap_result,
        "gamenet": args.gamenet_result,
        "safedrug": args.safedrug_result,
        "molerec": args.molerec_result,
    }
    packet = audit_molerec_table1(
        ledger_path=args.ledger,
        result_paths=result_paths,
        output_path=args.output,
        reference_path=args.reference,
        selection_path=args.selection,
        data_root=args.data_root,
    )
    print(
        json.dumps(
            {
                "verdict": packet["verdict"],
                "interval_checks_passed": packet["interval_checks_passed"],
                "relationship_checks_passed": packet["relationship_checks_passed"],
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _recover_reproduction(args: argparse.Namespace) -> int:
    """Recover an eligible training finalization failure without scientific execution."""
    if args.program_id == "safedrug-archived":
        from baselines import safedrug_archived as program
    else:
        from baselines import molerec as program

    try:
        recovery_root = program.recover_formal_lane(
            profile=program.profile_for(args.profile_id),
            data_dir=args.dataset_root.resolve(),
            run_root=args.run_root.resolve(),
            recovery_id=args.recovery_id,
            finalizer_revision=args.finalizer_revision,
        )
    except program.ReproductionError as error:
        raise ProtocolValidationError(str(error)) from error
    print(json.dumps({"recovery_root": str(recovery_root)}, sort_keys=True))
    return 0


def _admit_evaluation(args: argparse.Namespace) -> int:
    """Validate terminal training evidence before queueing one GPU 7 evaluation."""
    from .evaluation_queue import admit_validated_training_evaluation

    selection = None
    if args.selection is not None:
        selection = parse_json_object(
            args.selection.read_text(encoding="utf-8"),
            context="SafeDrug selection",
        )
    expected_identity = None
    if args.expected_identity is not None:
        expected_identity = parse_json_object(
            args.expected_identity.read_text(encoding="utf-8"),
            context="expected training identity",
        )
    entry = admit_validated_training_evaluation(
        args.queue,
        attempt_root=args.attempt_root,
        lane_id=args.lane_id,
        scientific_baseline_id=args.scientific_baseline_id,
        training_artifact_id=args.training_artifact_id,
        test_submission_id=args.test_submission_id,
        expected_identity=expected_identity,
        selection=selection,
    )
    print(json.dumps(entry, indent=2, sort_keys=True))
    return 0


def _admit_reproduction_continuation(
    args: argparse.Namespace,
    *,
    git_runner: Runner = subprocess.run,
) -> int:
    """Validate recovered lanes and publish one additive continuation schedule."""
    if args.output.exists():
        raise ProtocolValidationError(f"continuation schedule already exists: {args.output}")
    artifacts: dict[str, str] = {}
    for lane_id, artifact_id in args.training_artifact:
        if lane_id in artifacts:
            raise ProtocolValidationError(
                f"continuation training artifact repeats lane '{lane_id}'"
            )
        artifacts[lane_id] = artifact_id

    registry = BaselineRegistry.load(args.registry)
    lane_ids = tuple(lane.lane_id for lane in registry.reproduction_lanes)
    source_schedule = FrozenSchedule.from_json(
        args.source_schedule,
        expected_lane_ids=lane_ids,
    )
    harness_revision = _local_source_revision(
        Path.cwd(),
        require_clean=not args.dry_run,
        runner=git_runner,
    )
    continuation = validate_reproduction_continuation(
        registry=registry,
        source_schedule=source_schedule,
        source_schedule_id=args.source_schedule_id,
        attempt_root=args.attempt_root,
        attempt_id=args.attempt_id,
        training_artifact_ids=artifacts,
        harness_revision=harness_revision,
    )
    if not args.dry_run:
        write_json_atomic(args.output, continuation.to_dict())
    print(
        json.dumps(
            {
                "attempt_id": args.attempt_id,
                "harness_revision": harness_revision,
                "source_schedule_id": args.source_schedule_id,
                "state": "validated" if args.dry_run else "admitted",
                "training_lanes_validated": len(artifacts),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _prepare_molerec_evaluation(args: argparse.Namespace) -> int:
    """Select SafeDrug and publish the immutable five-test controller state."""
    registry = BaselineRegistry.load(args.registry)
    lane_ids = tuple(lane.lane_id for lane in registry.reproduction_lanes)
    schedule = FrozenSchedule.from_json(args.schedule, expected_lane_ids=lane_ids)
    if schedule.owner_attempt_id != args.attempt_id or schedule.source_harness_revision is None:
        raise ProtocolValidationError(
            "evaluation preparation requires the exact attempt-owned continuation schedule"
        )
    artifacts: dict[str, str] = {}
    for lane_id, artifact_id in args.training_artifact:
        if lane_id in artifacts:
            raise ProtocolValidationError(f"evaluation training artifact repeats lane '{lane_id}'")
        artifacts[lane_id] = artifact_id
    prepared = prepare_table1_evaluation(
        state_root=args.state_root,
        registry=registry,
        attempt_root=args.attempt_root,
        attempt_id=args.attempt_id,
        training_artifact_ids=artifacts,
        training_harness_revision=schedule.source_harness_revision,
        harness_revision=schedule.harness_revision,
        preprocessing_revision=schedule.preprocessing_revision,
        snapshot_id=schedule.snapshot_id,
        environment_sha256=schedule.environment_sha256,
    )
    print(
        json.dumps(
            {
                "attempt_id": prepared["attempt_id"],
                "selected_safedrug_lane": prepared["selected_safedrug_lane"],
                "state": "evaluation_prepared",
                "test_lane_ids": prepared["test_lane_ids"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _claim_molerec_evaluation(args: argparse.Namespace) -> int:
    """Claim one test and print its exact GPU 7 launch command."""
    claimed = claim_table1_evaluation(
        state_root=args.state_root,
        registry=BaselineRegistry.load(args.registry),
        attempt_root=args.attempt_root,
        remote_root=args.remote_root,
        data_root=args.data_root,
    )
    print(json.dumps(claimed or {"state": "no_queued_evaluation"}, indent=2, sort_keys=True))
    return 0


def _finalize_molerec_evaluation(args: argparse.Namespace) -> int:
    """Validate one terminal test pair and advance its queue entry."""
    finalized = finalize_table1_evaluation(
        state_root=args.state_root,
        attempt_root=args.attempt_root,
    )
    print(json.dumps(finalized, indent=2, sort_keys=True))
    return 0


def _audit_prepared_molerec_evaluation(args: argparse.Namespace) -> int:
    """Audit the prepared attempt after all five queue entries validate."""
    packet = audit_prepared_table1_evaluation(
        state_root=args.state_root,
        attempt_root=args.attempt_root,
        output_path=args.output,
        reference_path=args.reference,
    )
    print(
        json.dumps(
            {
                "axes": packet["axes"],
                "output": str(args.output),
                "verdict": packet["verdict"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


# -----------------------------------------------------------------------------
# Parser Construction
# -----------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="medrec",
        description="MedRec Research: Unified Medication Recommendation Research Toolkit",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    # 1. Reference Slice
    reference = commands.add_parser("reference", help="Run baseline reference slice")
    reference.add_argument(
        "--manifest", type=Path, required=True, help="Path to DatasetManifest JSON"
    )
    reference.add_argument(
        "--visits", type=Path, required=True, help="Path to synthetic visits JSON"
    )
    reference.add_argument(
        "--output", type=Path, required=True, help="Output path for ProtocolCheckRecord"
    )
    reference.add_argument(
        "--top-k", type=_positive_integer, default=2, help="Top-K recommendations (default: 2)"
    )
    reference.add_argument(
        "--seed", type=_nonnegative_integer, default=0, help="Random seed (default: 0)"
    )
    reference.set_defaults(handler=_reference)

    # 2. Accept Comparison
    acceptance = commands.add_parser("accept-comparison", help="Accept and record comparison run")
    acceptance.add_argument(
        "--manifest", type=Path, required=True, help="Path to DatasetManifest JSON"
    )
    acceptance.add_argument(
        "--registry", type=Path, required=True, help="Path to BaselineRegistry TOML"
    )
    acceptance.add_argument("--baseline-id", type=str, required=True, help="Baseline ID")
    acceptance.add_argument(
        "--predictions", type=Path, required=True, help="Path to predictions JSON"
    )
    acceptance.add_argument(
        "--medication-vocabulary", type=Path, required=True, help="Path to vocabulary file"
    )
    acceptance.add_argument(
        "--run-config", type=Path, required=True, help="Path to run-config JSON"
    )
    acceptance.add_argument(
        "--adaptation-budget", type=Path, required=True, help="Path to adaptation budget JSON"
    )
    acceptance.add_argument(
        "--output", type=Path, required=True, help="Output path for RunRecord JSON"
    )
    acceptance.set_defaults(handler=_accept_comparison)

    # 3. Evaluate Predictions
    eval_p = commands.add_parser("evaluate", help="Evaluate predictions JSON file")
    eval_p.add_argument("--predictions", type=Path, required=True, help="Path to predictions JSON")
    eval_p.add_argument(
        "--output", type=Path, default=None, help="Optional output path for evaluation metrics JSON"
    )
    eval_p.set_defaults(handler=_evaluate)

    # 4. Baseline Operations
    baseline_p = commands.add_parser("baseline", help="Baseline registry operations")
    baseline_sub = baseline_p.add_subparsers(dest="baseline_action", required=True)
    list_p = baseline_sub.add_parser("list", help="List registered baselines")
    list_p.add_argument(
        "--registry",
        type=Path,
        default=Path("baselines/registry.toml"),
        help="Path to registry.toml (default: baselines/registry.toml)",
    )
    list_p.set_defaults(handler=_baseline_list)

    # 5. Remote Reproduction Submission
    reproduce = commands.add_parser(
        "reproduce", help="Plan or submit archived baseline reproduction on 319"
    )
    reproduce.add_argument("baseline_id", type=str, help="Baseline ID, lane ID, or 'all'")
    reproduce.add_argument("--gpu", type=_nonnegative_integer)
    reproduce.add_argument("--gpus", type=_gpu_list)
    reproduce.add_argument("--cpu-set", type=str)
    reproduce.add_argument("--cpu-sets", type=_cpu_set_list)
    reproduce.add_argument("--min-free-gpu-mib", type=_positive_integer, default=20000)
    reproduce.add_argument("--min-free-disk-gib", type=_positive_integer, default=100)
    reproduce.add_argument(
        "--registry",
        type=Path,
        default=Path("baselines/registry.toml"),
        help="Path to registry.toml (default: baselines/registry.toml)",
    )
    reproduce.add_argument(
        "--remote-root",
        default="/root/zhb/medrec-research",
        help="Verified 319 checkout root",
    )
    reproduce.add_argument(
        "--data-root",
        default="/root/zhb/medrec-data",
        help="External 319 data root",
    )
    reproduce.add_argument(
        "--schedule",
        type=Path,
        default=None,
        help="Accepted frozen seven-lane schedule artifact",
    )
    reproduce.add_argument("--dry-run", action="store_true")
    reproduce.add_argument(
        "--attempt-id",
        default=None,
        help="Optional stable attempt identity shared by a batch",
    )
    reproduce.set_defaults(handler=_reproduce)

    # 6. Remote Reproduction Smoke Submission
    smoke = commands.add_parser(
        "reproduce-smoke", help="Plan or submit archived baseline one-epoch smoke on 319"
    )
    smoke.add_argument("baseline_id", type=str, help="Baseline ID, lane ID, or 'all'")
    smoke.add_argument("--gpu", type=_nonnegative_integer)
    smoke.add_argument("--gpus", type=_gpu_list)
    smoke.add_argument("--cpu-set", type=str)
    smoke.add_argument("--cpu-sets", type=_cpu_set_list)

    smoke.add_argument("--min-free-gpu-mib", type=_positive_integer, default=20000)
    smoke.add_argument("--min-free-disk-gib", type=_positive_integer, default=100)
    smoke.add_argument(
        "--registry",
        type=Path,
        default=Path("baselines/registry.toml"),
        help="Path to registry.toml (default: baselines/registry.toml)",
    )
    smoke.add_argument(
        "--remote-root",
        default="/root/zhb/medrec-research",
        help="Verified 319 checkout root",
    )
    smoke.add_argument(
        "--data-root",
        default="/root/zhb/medrec-data",
        help="External 319 data root",
    )
    smoke.add_argument("--dry-run", action="store_true")
    smoke.add_argument(
        "--attempt-id",
        default=None,
        help="Optional stable attempt identity shared by a batch",
    )
    smoke.set_defaults(handler=_reproduce_smoke)

    recovery = commands.add_parser(
        "recover-reproduction",
        help="Finalize one eligible preserved training output without rerunning it",
    )
    recovery.add_argument(
        "program_id",
        choices=("safedrug-archived", "molerec"),
        help="Frozen Reproduction Program that produced the source lane",
    )
    recovery.add_argument("profile_id", help="Program profile used by the source lane")
    recovery.add_argument("--dataset-root", type=Path, required=True)
    recovery.add_argument("--run-root", type=Path, required=True)
    recovery.add_argument("--recovery-id", required=True)
    recovery.add_argument("--finalizer-revision", required=True)
    recovery.set_defaults(handler=_recover_reproduction)

    admission = commands.add_parser(
        "admit-evaluation",
        help="Validate terminal training evidence before queueing a serial GPU 7 test",
    )
    admission.add_argument("--queue", type=Path, required=True)
    admission.add_argument("--attempt-root", type=Path, required=True)
    admission.add_argument("--lane-id", required=True)
    admission.add_argument("--scientific-baseline-id", required=True)
    admission.add_argument("--training-artifact-id", required=True)
    admission.add_argument("--test-submission-id", required=True)
    admission.add_argument(
        "--selection",
        type=Path,
        default=None,
        help="Required for the selected SafeDrug lane",
    )
    admission.add_argument(
        "--expected-identity",
        type=Path,
        default=None,
        help="Optional full v2 identity JSON to bind the training artifact",
    )
    admission.set_defaults(handler=_admit_evaluation)

    continuation = commands.add_parser(
        "admit-reproduction-continuation",
        help="Validate seven recovered lanes and reaccept the frozen schedule",
    )
    continuation.add_argument(
        "--registry",
        type=Path,
        default=Path("baselines/registry.toml"),
    )
    continuation.add_argument("--source-schedule", type=Path, required=True)
    continuation.add_argument("--source-schedule-id", required=True)
    continuation.add_argument("--attempt-root", type=Path, required=True)
    continuation.add_argument("--attempt-id", required=True)
    continuation.add_argument(
        "--training-artifact",
        type=_lane_artifact,
        action="append",
        required=True,
        help="Repeat exactly once per lane as LANE_ID=RELATIVE_RESULT_JSON",
    )
    continuation.add_argument("--output", type=Path, required=True)
    continuation.add_argument("--dry-run", action="store_true")
    continuation.set_defaults(handler=_admit_reproduction_continuation)

    prepare_evaluation = commands.add_parser(
        "prepare-molerec-table1-evaluation",
        help="Select SafeDrug and publish the exact five-test queue",
    )
    prepare_evaluation.add_argument(
        "--registry",
        type=Path,
        default=Path("baselines/registry.toml"),
    )
    prepare_evaluation.add_argument("--schedule", type=Path, required=True)
    prepare_evaluation.add_argument("--attempt-root", type=Path, required=True)
    prepare_evaluation.add_argument("--attempt-id", required=True)
    prepare_evaluation.add_argument(
        "--training-artifact",
        type=_lane_artifact,
        action="append",
        required=True,
        help="Repeat exactly once per lane as LANE_ID=RELATIVE_RESULT_JSON",
    )
    prepare_evaluation.add_argument("--state-root", type=Path, required=True)
    prepare_evaluation.set_defaults(handler=_prepare_molerec_evaluation)

    claim_evaluation = commands.add_parser(
        "claim-molerec-table1-evaluation",
        help="Claim the next queued test and print its exact GPU 7 command",
    )
    claim_evaluation.add_argument("--registry", type=Path, default=Path("baselines/registry.toml"))
    claim_evaluation.add_argument("--state-root", type=Path, required=True)
    claim_evaluation.add_argument("--attempt-root", type=Path, required=True)
    claim_evaluation.add_argument("--remote-root", default="/root/zhb/medrec-research")
    claim_evaluation.add_argument("--data-root", default="/root/zhb/medrec-data")
    claim_evaluation.set_defaults(handler=_claim_molerec_evaluation)

    finalize_evaluation_parser = commands.add_parser(
        "finalize-molerec-table1-evaluation",
        help="Validate the running terminal pair and advance the queue",
    )
    finalize_evaluation_parser.add_argument("--state-root", type=Path, required=True)
    finalize_evaluation_parser.add_argument("--attempt-root", type=Path, required=True)
    finalize_evaluation_parser.set_defaults(handler=_finalize_molerec_evaluation)

    prepared_audit = commands.add_parser(
        "audit-prepared-molerec-table1",
        help="Run the four-axis audit after five completed queue entries",
    )
    prepared_audit.add_argument("--state-root", type=Path, required=True)
    prepared_audit.add_argument("--attempt-root", type=Path, required=True)
    prepared_audit.add_argument("--output", type=Path, required=True)
    prepared_audit.add_argument(
        "--reference",
        type=Path,
        default=Path("research/baseline-preflight/molerec-table1-reference.json"),
    )
    prepared_audit.set_defaults(handler=_audit_prepared_molerec_evaluation)

    # 7. Stage SafeDrug c721 Dataset
    stage_c721 = commands.add_parser(
        "stage-safedrug-c721",
        help="Stage SafeDrug c7218d0 paper-lineage dataset on 319",
    )
    stage_c721.add_argument(
        "--preprocessing-checkout",
        type=Path,
        required=True,
        help="Path to clean SafeDrug c7218d0 checkout",
    )
    stage_c721.add_argument(
        "--prescriptions",
        type=Path,
        required=True,
        help="Path to PRESCRIPTIONS.csv.gz",
    )
    stage_c721.add_argument(
        "--diagnoses",
        type=Path,
        required=True,
        help="Path to DIAGNOSES_ICD.csv.gz",
    )
    stage_c721.add_argument(
        "--procedures",
        type=Path,
        required=True,
        help="Path to PROCEDURES_ICD.csv.gz",
    )
    stage_c721.add_argument(
        "--drug-ddi",
        type=Path,
        required=True,
        help="Path to drug-DDI.csv",
    )
    stage_c721.add_argument(
        "--staging-directory",
        type=Path,
        required=True,
        help="Path to candidate staging directory (must not exist)",
    )
    stage_c721.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to run preprocessing script",
    )
    stage_c721.add_argument(
        "--input-manifest",
        type=Path,
        default=None,
        help="Optional path to input-manifest.json",
    )
    stage_c721.set_defaults(handler=_stage_safedrug_c721)

    # 8. Stage MoleRec Table 1 Dataset
    stage_molerec = commands.add_parser(
        "stage-molerec-snapshot",
        help="Build and publish the additive MoleRec eight-file snapshot",
    )
    stage_molerec.add_argument(
        "--common-snapshot",
        type=Path,
        required=True,
        help="Accepted c721 snapshot containing the four common inputs",
    )
    stage_molerec.add_argument(
        "--molerec-data-directory",
        type=Path,
        required=True,
        help="Frozen MoleRec data directory containing paired molecular assets",
    )
    stage_molerec.add_argument(
        "--staging-directory",
        type=Path,
        required=True,
        help="Candidate staging directory (must not exist)",
    )
    stage_molerec.add_argument(
        "--snapshot-directory",
        type=Path,
        required=True,
        help="Published snapshot directory (must not exist)",
    )
    stage_molerec.add_argument(
        "--proof",
        type=Path,
        default=None,
        help="Optional proof JSON path outside the eight-file snapshot",
    )
    stage_molerec.set_defaults(handler=_stage_molerec_snapshot)

    # 9. SafeDrug Table 2 Reproduction Audit
    audit = commands.add_parser(
        "audit-safedrug-table2",
        help="Audit four formal reproduction results against IJCAI 2021 Table 2",
    )
    audit.add_argument(
        "--ledger",
        type=Path,
        required=True,
        help="Path to reproduction state ledger JSON",
    )
    audit.add_argument(
        "--gamenet-result",
        type=Path,
        required=True,
        help="Path to gamenet formal result.json",
    )
    audit.add_argument(
        "--safedrug-result",
        type=Path,
        required=True,
        help="Path to safedrug formal result.json",
    )
    audit.add_argument(
        "--retain-result",
        type=Path,
        required=True,
        help="Path to retain formal result.json",
    )
    audit.add_argument(
        "--leap-result",
        type=Path,
        required=True,
        help="Path to leap-safedrug formal result.json",
    )
    audit.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for Table 2 audit packet JSON",
    )
    audit.add_argument(
        "--reference",
        type=Path,
        default=Path("research/baseline-preflight/safedrug-table2-reference.json"),
        help="Optional path to Table 2 reference JSON",
    )
    audit.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Optional external data root to verify result artifact IDs",
    )
    audit.set_defaults(handler=_audit_safedrug_table2)

    # 10. MoleRec Table 1 Reproduction Audit
    audit_molerec = commands.add_parser(
        "audit-molerec-table1",
        help="Audit five formal reproduction results against MoleRec Table 1",
    )
    audit_molerec.add_argument(
        "--ledger",
        type=Path,
        required=True,
        help="Path to reproduction state ledger JSON",
    )
    audit_molerec.add_argument(
        "--retain-result",
        type=Path,
        required=True,
        help="Path to retain formal result.json",
    )
    audit_molerec.add_argument(
        "--leap-result",
        type=Path,
        required=True,
        help="Path to leap formal result.json",
    )
    audit_molerec.add_argument(
        "--gamenet-result",
        type=Path,
        required=True,
        help="Path to gamenet formal result.json",
    )
    audit_molerec.add_argument(
        "--safedrug-result",
        type=Path,
        required=True,
        help="Path to safedrug formal result.json",
    )
    audit_molerec.add_argument(
        "--molerec-result",
        type=Path,
        required=True,
        help="Path to molerec formal result.json",
    )
    audit_molerec.add_argument(
        "--selection",
        type=Path,
        required=True,
        help="Path to validation-only SafeDrug selection.json",
    )
    audit_molerec.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for Table 1 audit packet JSON",
    )
    audit_molerec.add_argument(
        "--reference",
        type=Path,
        default=Path("research/baseline-preflight/molerec-table1-reference.json"),
        help="Optional path to Table 1 reference JSON",
    )
    audit_molerec.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Optional external data root to verify result artifact IDs",
    )
    audit_molerec.set_defaults(handler=_audit_molerec_table1)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if not handler:
        parser.print_help()
        return 1
    try:
        return handler(args)
    except ProtocolValidationError as error:
        print(f"medrec: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
