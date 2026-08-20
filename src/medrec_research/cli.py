"""Unified Command-Line Interface for MedRec Research & the Idea Loop System."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from ._validation import (
    parse_json_object,
    require_single_line_public_string,
    strict_fields,
)
from .dataset import DatasetManifest, SplitName
from .errors import ProtocolValidationError
from .evaluation import evaluate_predictions
from .prediction import PredictionRecord
from .reference import ReferenceConfig, run_reference_slice
from .registry import BaselineRegistry
from .remote_executor import SSHConfig
from .research_orchestrator import ResearchOrchestrator
from .run_record import ArtifactChecksum, RunParameter, RunRecord

Clock = Callable[[], datetime]


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


def _load_user_config() -> SSHConfig:
    """Load SSH and execution config from ~/.medrec/config.yaml or fallback."""
    config_file = Path("~/.medrec/config.yaml").expanduser()
    if config_file.exists():
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "ssh" in data:
                return SSHConfig.from_dict(data["ssh"])
        except Exception:
            pass
    return SSHConfig()


def _create_orchestrator(args: argparse.Namespace) -> ResearchOrchestrator:
    ssh_cfg = _load_user_config()
    root = getattr(args, "root", None) or Path.cwd()
    interactive = not getattr(args, "non_interactive", False)
    return ResearchOrchestrator(
        root=root,
        ssh_config=ssh_cfg,
        interactive=interactive,
    )


# -----------------------------------------------------------------------------
# Idea Loop Handlers
# -----------------------------------------------------------------------------
def _establish_baseline(args: argparse.Namespace) -> int:
    orchestrator = _create_orchestrator(args)
    orchestrator.establish_baseline(args.baseline_id, dry_run=args.dry_run)
    return 0


def _discover_ideas(args: argparse.Namespace) -> int:
    orchestrator = _create_orchestrator(args)
    orchestrator.discover_ideas(args.baseline_id)
    return 0


def _review_idea(args: argparse.Namespace) -> int:
    orchestrator = _create_orchestrator(args)
    orchestrator.review_idea(args.hypothesis_id)
    return 0


def _design_experiment(args: argparse.Namespace) -> int:
    orchestrator = _create_orchestrator(args)
    orchestrator.design_experiment(args.hypothesis_id)
    return 0


def _run_experiment(args: argparse.Namespace) -> int:
    orchestrator = _create_orchestrator(args)
    orchestrator.run_experiment(args.experiment_id, dry_run=args.dry_run)
    return 0


def _analyze_evidence(args: argparse.Namespace) -> int:
    orchestrator = _create_orchestrator(args)
    orchestrator.analyze_evidence(args.experiment_id)
    return 0


def _run_loop(args: argparse.Namespace) -> int:
    orchestrator = _create_orchestrator(args)
    orchestrator.run_loop(args.baseline_id, dry_run=args.dry_run)
    return 0


# -----------------------------------------------------------------------------
# Comparison Protocol & Reference Handlers
# -----------------------------------------------------------------------------
def _reference(args: argparse.Namespace, *, clock: Clock = lambda: datetime.now(UTC)) -> int:
    manifest = DatasetManifest.from_json(args.manifest.read_text(encoding="utf-8"))
    config = ReferenceConfig(top_k=args.top_k, seed=args.seed)
    record = run_reference_slice(
        manifest=manifest,
        visits_path=args.visits,
        config=config,
        clock=clock,
    )
    record.to_file(args.output)
    return 0


def _accept_comparison(
    args: argparse.Namespace, *, clock: Clock = lambda: datetime.now(UTC)
) -> int:
    manifest = DatasetManifest.from_json(args.manifest.read_text(encoding="utf-8"))
    registry = BaselineRegistry.from_toml(args.registry.read_text(encoding="utf-8"))
    baseline = registry.get(args.baseline_id)
    raw_predictions = parse_json_object(
        args.predictions.read_text(encoding="utf-8"),
        context="predictions file",
    )
    strict_fields(
        raw_predictions, required=("schema_version", "predictions"), context="predictions file"
    )
    if raw_predictions.get("schema_version") != 1:
        raise ProtocolValidationError("predictions schema_version must be 1")
    prediction_items = raw_predictions.get("predictions")
    if not isinstance(prediction_items, list):
        raise ProtocolValidationError("predictions must be a list")
    records = tuple(PredictionRecord.from_dict(item) for item in prediction_items)

    raw_config = parse_json_object(
        args.run_config.read_text(encoding="utf-8"),
        context="comparison run config",
    )
    strict_fields(
        raw_config,
        required=(
            "schema_version",
            "protocol_version",
            "seed",
            "selection_split",
            "evaluation_split",
            "parameters",
        ),
        context="comparison run config",
    )

    budget_bytes = args.adaptation_budget.read_bytes()
    protocol_version = require_single_line_public_string(
        raw_config.get("protocol_version"), field="protocol_version"
    )
    dataset_manifest_sha256 = manifest.manifest_sha256
    adaptation_budget_sha256 = sha256(budget_bytes).hexdigest()

    matching_qualification = next(
        (
            q
            for q in baseline.comparison_qualifications
            if q.matches(
                protocol_version=protocol_version,
                dataset_manifest_sha256=dataset_manifest_sha256,
                adaptation_budget_sha256=adaptation_budget_sha256,
            )
        ),
        None,
    )
    if matching_qualification is None:
        raise ProtocolValidationError(
            f"baseline '{args.baseline_id}' is not qualified for comparison under the provided protocol/dataset/budget"
        )

    vocab_lines = [
        line.strip()
        for line in args.medication_vocabulary.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    vocab = tuple(vocab_lines)
    if vocab != tuple(sorted(vocab)):
        raise ProtocolValidationError("medication vocabulary must be in canonical sorted order")

    eval_result = evaluate_predictions(records)

    parameters = tuple(
        RunParameter(name=p["name"], value=p["value"]) for p in raw_config.get("parameters", [])
    )
    checksums = (
        ArtifactChecksum(
            name="prediction-records",
            sha256=sha256(args.predictions.read_bytes()).hexdigest(),
        ),
    )

    run_record = RunRecord.create(
        mode="comparison",
        protocol_version=protocol_version,
        baseline=baseline,
        dataset=manifest,
        seed=int(raw_config["seed"]),
        selection_split=raw_config["selection_split"],
        evaluation_split=raw_config["evaluation_split"],
        parameters=parameters,
        evaluation=eval_result,
        adaptation_budget_sha256=adaptation_budget_sha256,
        artifact_checksums=checksums,
        evaluation_visit_membership_digest=manifest.split(SplitName.TEST).visit_membership_digest,
    )
    run_record.write(args.output)
    return 0


# -----------------------------------------------------------------------------
# Parser Construction
# -----------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="medrec",
        description="MedRec Research: Unified Medication Recommendation Research & Idea Loop Platform",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run without interactive prompts (auto-select default choice at HITL gates)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Project root directory (default: current working directory)",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    # 1. Baseline Subcommands
    baseline_parser = commands.add_parser("baseline", help="Phase 1: Baseline operations")
    baseline_sub = baseline_parser.add_subparsers(dest="baseline_action", required=True)
    establish_p = baseline_sub.add_parser("establish", help="Establish and verify a baseline")
    establish_p.add_argument("baseline_id", help="Baseline identifier (e.g. safedrug, gamenet)")
    establish_p.add_argument(
        "--dry-run", action="store_true", help="Validate without remote GPU run"
    )
    establish_p.set_defaults(handler=_establish_baseline)

    # 2. Idea Subcommands
    idea_parser = commands.add_parser(
        "idea", help="Phase 2/3: Scientific hypothesis generation & review"
    )
    idea_sub = idea_parser.add_subparsers(dest="idea_action", required=True)
    discover_p = idea_sub.add_parser(
        "discover", help="Discover hypotheses from baseline failure analysis"
    )
    discover_p.add_argument("baseline_id", help="Baseline identifier")
    discover_p.set_defaults(handler=_discover_ideas)

    review_p = idea_sub.add_parser("review", help="Conduct 3-dimension peer review on a hypothesis")
    review_p.add_argument("hypothesis_id", help="Hypothesis identifier (e.g. H001)")
    review_p.set_defaults(handler=_review_idea)

    # 3. Experiment Subcommands
    exp_parser = commands.add_parser("experiment", help="Phase 4/5: Experiment design & execution")
    exp_sub = exp_parser.add_subparsers(dest="experiment_action", required=True)
    design_p = exp_sub.add_parser(
        "design", help="Design experiment matrix and lock research contract"
    )
    design_p.add_argument("hypothesis_id", help="Hypothesis identifier")
    design_p.set_defaults(handler=_design_experiment)

    run_p = exp_sub.add_parser("run", help="Run experiment on GPU host or local harness")
    run_p.add_argument("experiment_id", help="Experiment identifier (e.g. H001-substructure)")
    run_p.add_argument(
        "--dry-run", action="store_true", help="Simulate run without remote GPU allocation"
    )
    run_p.set_defaults(handler=_run_experiment)

    # 4. Evidence Subcommands
    evidence_parser = commands.add_parser(
        "evidence", help="Phase 6: Empirical evidence audit & decision"
    )
    evidence_sub = evidence_parser.add_subparsers(dest="evidence_action", required=True)
    analyze_p = evidence_sub.add_parser(
        "analyze", help="Audit experiment outcome against locked contract"
    )
    analyze_p.add_argument("experiment_id", help="Experiment identifier")
    analyze_p.set_defaults(handler=_analyze_evidence)

    # 5. Full Loop Automation
    loop_parser = commands.add_parser("loop", help="End-to-end Idea Loop orchestrator")
    loop_sub = loop_parser.add_subparsers(dest="loop_action", required=True)
    start_p = loop_sub.add_parser(
        "start", help="Start full idea loop with HITL decision checkpoints"
    )
    start_p.add_argument("baseline_id", help="Target baseline identifier")
    start_p.add_argument("--dry-run", action="store_true", help="Execute in dry-run mode")
    start_p.set_defaults(handler=_run_loop)

    # 6. Legacy / Protocol Utilities
    reference = commands.add_parser("reference", help="Run baseline reference slice")
    reference.add_argument("--manifest", type=Path, required=True)
    reference.add_argument("--visits", type=Path, required=True)
    reference.add_argument("--output", type=Path, required=True)
    reference.add_argument("--top-k", type=_positive_integer, default=2)
    reference.add_argument("--seed", type=_nonnegative_integer, default=0)
    reference.set_defaults(handler=_reference)

    acceptance = commands.add_parser("accept-comparison", help="Accept and record comparison run")
    acceptance.add_argument("--manifest", type=Path, required=True)
    acceptance.add_argument("--registry", type=Path, required=True)
    acceptance.add_argument("--baseline-id", type=str, required=True)
    acceptance.add_argument("--predictions", type=Path, required=True)
    acceptance.add_argument("--medication-vocabulary", type=Path, required=True)
    acceptance.add_argument("--run-config", type=Path, required=True)
    acceptance.add_argument("--adaptation-budget", type=Path, required=True)
    acceptance.add_argument("--output", type=Path, required=True)
    acceptance.set_defaults(handler=_accept_comparison)

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
