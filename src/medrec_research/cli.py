"""Clean and simple Command-Line Interface for MedRec Research."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path

from ._validation import parse_json_object
from .commands import (
    accept_comparison_command,
    format_baseline_table,
    parse_prediction_records,
)
from .dataset import DatasetManifest
from .errors import ProtocolValidationError
from .evaluation import evaluate_predictions
from .reference import ReferenceConfig, run_reference_slice
from .registry import BaselineRegistry
from .reproduction.cli_commands import register_reproduction_commands


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

    # 5. Reproduction Commands
    register_reproduction_commands(commands)

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
