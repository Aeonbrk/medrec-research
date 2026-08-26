#!/usr/bin/env python3
"""Run one pinned SafeDrug archived Baseline Program lane on 319.

This module serves as the façade and CLI entrypoint for the SafeDrug archived
Reproduction Program, decomposing responsibility across:
- safedrug_archived_contract
- safedrug_archived_data
- safedrug_archived_logs
- safedrug_archived_probe
- safedrug_archived_runner
"""

from __future__ import annotations

import argparse
import importlib as importlib
import json
import subprocess as subprocess
import sys
from datetime import timezone
from pathlib import Path

UTC = timezone.utc  # noqa: UP017 -- archived environments may use Python 3.8.

# Support both relative imports (package) and direct script execution
if __package__:
    from .safedrug_archived_contract import (
        ARCHIVED_REVISION,
        CANONICAL_SIX_INPUTS,
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
        adapt_epoch_source,
        adapt_smoke_source,
        adapt_training_source,
        finalize_result,
        profile_for,
        sha256,
        test_command,
        test_mode_default,
        training_command,
        verify_upstream_source,
        write_json,
    )
    from .safedrug_archived_data import (
        _validate_binary_symmetric_matrix,
        _validate_ddi_mask,
        _validate_idx2drug_contract,
        _validate_records_statistics,
        _validate_records_structure,
        _validate_vocabulary_bijections,
        count_dataset,
        load_and_validate_canonical_inputs,
        matrix_shape,
        require_executable_counts,
    )
    from .safedrug_archived_logs import (
        parse_test_log,
        parse_training_log,
        select_checkpoint,
    )
    from .safedrug_archived_probe import (
        _nvidia_driver_version,
        _package_version,
        check_cuda_tensor,
        check_dnc_forward,
        check_imports,
        check_rdkit_brics,
        environment_summary,
        probe_environment_details,
        run_probe,
    )
    from .safedrug_archived_runner import (
        run_formal_lane,
        run_logged,
        run_smoke_lane,
    )
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from safedrug_archived_contract import (
        ARCHIVED_REVISION,
        CANONICAL_SIX_INPUTS,
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
        adapt_epoch_source,
        adapt_smoke_source,
        adapt_training_source,
        finalize_result,
        profile_for,
        sha256,
        test_command,
        test_mode_default,
        training_command,
        verify_upstream_source,
        write_json,
    )
    from safedrug_archived_data import (
        _validate_binary_symmetric_matrix,
        _validate_ddi_mask,
        _validate_idx2drug_contract,
        _validate_records_statistics,
        _validate_records_structure,
        _validate_vocabulary_bijections,
        count_dataset,
        load_and_validate_canonical_inputs,
        matrix_shape,
        require_executable_counts,
    )
    from safedrug_archived_logs import (
        parse_test_log,
        parse_training_log,
        select_checkpoint,
    )
    from safedrug_archived_probe import (
        _nvidia_driver_version,
        _package_version,
        check_cuda_tensor,
        check_dnc_forward,
        check_imports,
        check_rdkit_brics,
        environment_summary,
        probe_environment_details,
        run_probe,
    )
    from safedrug_archived_runner import (
        run_formal_lane,
        run_logged,
        run_smoke_lane,
    )

__all__ = [
    "ARCHIVED_REVISION",
    "CANONICAL_SIX_INPUTS",
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
    "_nvidia_driver_version",
    "_package_version",
    "_validate_binary_symmetric_matrix",
    "_validate_ddi_mask",
    "_validate_idx2drug_contract",
    "_validate_records_statistics",
    "_validate_records_structure",
    "_validate_vocabulary_bijections",
    "adapt_epoch_source",
    "adapt_smoke_source",
    "adapt_training_source",
    "check_cuda_tensor",
    "check_dnc_forward",
    "check_imports",
    "check_rdkit_brics",
    "count_dataset",
    "environment_summary",
    "finalize_result",
    "importlib",
    "load_and_validate_canonical_inputs",
    "main",
    "matrix_shape",
    "parse_test_log",
    "parse_training_log",
    "probe_environment_details",
    "profile_for",
    "require_executable_counts",
    "run_formal_lane",
    "run_logged",
    "run_probe",
    "run_smoke_lane",
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
        "--mode",
        choices=("formal", "smoke", "probe"),
        default="formal",
        help="Reproduction execution mode (default: formal)",
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
        )
    else:
        run_formal_lane(
            profile=profile_for(args.baseline_id),
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve(),
            run_root=args.run_root.resolve(),
            python=args.python,
        )


if __name__ == "__main__":
    main()
