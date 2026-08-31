#!/usr/bin/env python3
"""Reproduction program facade for MoleRec Table 1 reproduction."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

if __package__:
    from .molerec_contract import (
        ARCHIVED_REVISION,
        COMMON_INPUTS,
        EPOCH_FORMAL,
        EPOCH_SMOKE,
        EXPECTED_COUNTS,
        EXPECTED_STATISTICS,
        GATE_INPUTS,
        PROFILES,
        REGISTRY_IMPORT_MODULES,
        REPORTED_PAPER_METADATA,
        ROUND_PATTERN,
        TEST_DECLARATION,
        TRAIN_DECLARATION,
        Profile,
        ReproductionError,
        _format_lr,
        adapt_epoch_source,
        adapt_learning_rate_source,
        adapt_smoke_source,
        adapt_training_source,
        checkpoint_directory,
        finalize_result,
        native_history_path,
        profile_for,
        sha256,
        test_command,
        test_mode_default,
        training_command,
        verify_upstream_source,
        write_json,
    )
    from .molerec_data import (
        _validate_binary_symmetric_matrix,
        _validate_ddi_mask,
        _validate_records_statistics,
        _validate_records_structure,
        _validate_vocabulary_bijections,
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
        _nvidia_driver_version,
        _package_version,
        check_cuda_tensor,
        check_imports,
        check_pyg_extensions,
        check_rdkit,
        environment_summary,
        probe_environment_details,
        run_probe,
    )
    from .molerec_runner import (
        UTC,
        recover_formal_lane,
        run_formal_lane,
        run_logged,
        run_smoke_lane,
        run_test_lane,
    )
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from molerec_contract import (
        ARCHIVED_REVISION,
        COMMON_INPUTS,
        EPOCH_FORMAL,
        EPOCH_SMOKE,
        EXPECTED_COUNTS,
        EXPECTED_STATISTICS,
        GATE_INPUTS,
        PROFILES,
        REGISTRY_IMPORT_MODULES,
        REPORTED_PAPER_METADATA,
        ROUND_PATTERN,
        TEST_DECLARATION,
        TRAIN_DECLARATION,
        Profile,
        ReproductionError,
        _format_lr,
        adapt_epoch_source,
        adapt_learning_rate_source,
        adapt_smoke_source,
        adapt_training_source,
        checkpoint_directory,
        finalize_result,
        native_history_path,
        profile_for,
        sha256,
        test_command,
        test_mode_default,
        training_command,
        verify_upstream_source,
        write_json,
    )
    from molerec_data import (
        _validate_binary_symmetric_matrix,
        _validate_ddi_mask,
        _validate_records_statistics,
        _validate_records_structure,
        _validate_vocabulary_bijections,
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
        _nvidia_driver_version,
        _package_version,
        check_cuda_tensor,
        check_imports,
        check_pyg_extensions,
        check_rdkit,
        environment_summary,
        probe_environment_details,
        run_probe,
    )
    from molerec_runner import (
        UTC,
        recover_formal_lane,
        run_formal_lane,
        run_logged,
        run_smoke_lane,
        run_test_lane,
    )

__all__ = [
    "ARCHIVED_REVISION",
    "COMMON_INPUTS",
    "EPOCH_FORMAL",
    "EPOCH_SMOKE",
    "EXPECTED_COUNTS",
    "EXPECTED_STATISTICS",
    "GATE_INPUTS",
    "PROFILES",
    "REGISTRY_IMPORT_MODULES",
    "REPORTED_PAPER_METADATA",
    "ROUND_PATTERN",
    "TEST_DECLARATION",
    "TRAIN_DECLARATION",
    "UTC",
    "Profile",
    "ReproductionError",
    "_format_lr",
    "_nvidia_driver_version",
    "_package_version",
    "_validate_binary_symmetric_matrix",
    "_validate_ddi_mask",
    "_validate_records_statistics",
    "_validate_records_structure",
    "_validate_vocabulary_bijections",
    "adapt_epoch_source",
    "adapt_learning_rate_source",
    "adapt_smoke_source",
    "adapt_training_source",
    "check_cuda_tensor",
    "check_imports",
    "check_pyg_extensions",
    "check_rdkit",
    "count_dataset",
    "environment_summary",
    "finalize_result",
    "importlib",
    "load_and_validate_canonical_inputs",
    "main",
    "matrix_shape",
    "native_history_path",
    "parse_formal_test_log",
    "parse_test_log",
    "parse_training_log",
    "parse_validation_metrics",
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
    "subprocess",
    "test_command",
    "test_mode_default",
    "training_command",
    "verify_upstream_source",
    "write_json",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_id", choices=tuple(PROFILES))
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=None,
        help="Override learning rate",
    )
    parser.add_argument(
        "--mode",
        choices=("formal", "smoke", "probe"),
        default="formal",
        help="Reproduction execution mode (default: formal)",
    )
    parser.add_argument(
        "--phase",
        choices=("training", "test"),
        default="training",
        help="Formal phase; training is the only default admission phase",
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=None,
        help="Validation-only SafeDrug selection.json for a test phase",
    )
    parser.add_argument(
        "--training-source-root",
        type=Path,
        default=None,
        help="Failed source run that owns a recovered training checkpoint",
    )
    parser.add_argument(
        "--test-root",
        type=Path,
        default=None,
        help="Additive continuation directory for test evidence",
    )
    parser.add_argument(
        "--probe-scope",
        choices=("environment", "full"),
        default="full",
        help="Probe scope when --mode probe (default: full)",
    )
    args = parser.parse_args()

    if args.mode != "probe" and "--probe-scope" in sys.argv:
        parser.error("--probe-scope is only supported when --mode probe")
    if args.mode != "formal" and args.phase != "training":
        parser.error("--phase test is only supported when --mode formal")
    if args.training_source_root is not None and args.phase != "test":
        parser.error("--training-source-root is only supported for --phase test")
    if args.test_root is not None and args.phase != "test":
        parser.error("--test-root is only supported for --phase test")

    if args.mode == "probe":
        probe_result = run_probe(
            baseline_id=args.baseline_id,
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve() if args.dataset_root else None,
            scope=args.probe_scope,
        )
        print(json.dumps(probe_result, indent=None, separators=(",", ":")))
        return

    if args.dataset_root is None:
        parser.error("--dataset-root is required for smoke and formal modes")
    if args.run_root is None:
        parser.error("--run-root is required for smoke and formal modes")

    if args.mode == "smoke":
        run_smoke_lane(
            profile=profile_for(args.baseline_id),
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve(),
            run_root=args.run_root.resolve(),
            python=args.python,
            learning_rate=args.learning_rate,
        )
    else:
        run_formal_lane(
            profile=profile_for(args.baseline_id),
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

__all__ = (
    "ARCHIVED_REVISION",
    "COMMON_INPUTS",
    "EPOCH_FORMAL",
    "EPOCH_SMOKE",
    "EXPECTED_COUNTS",
    "EXPECTED_STATISTICS",
    "GATE_INPUTS",
    "PROFILES",
    "REGISTRY_IMPORT_MODULES",
    "REPORTED_PAPER_METADATA",
    "ROUND_PATTERN",
    "TEST_DECLARATION",
    "TRAIN_DECLARATION",
    "Profile",
    "ReproductionError",
    "_format_lr",
    "_nvidia_driver_version",
    "_package_version",
    "_validate_binary_symmetric_matrix",
    "_validate_ddi_mask",
    "_validate_records_statistics",
    "_validate_records_structure",
    "_validate_vocabulary_bijections",
    "adapt_epoch_source",
    "adapt_learning_rate_source",
    "adapt_smoke_source",
    "adapt_training_source",
    "check_cuda_tensor",
    "check_imports",
    "check_pyg_extensions",
    "check_rdkit",
    "checkpoint_directory",
    "count_dataset",
    "environment_summary",
    "finalize_result",
    "load_and_validate_canonical_inputs",
    "main",
    "matrix_shape",
    "native_history_path",
    "parse_formal_test_log",
    "parse_test_log",
    "parse_training_log",
    "parse_validation_metrics",
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
