from __future__ import annotations

from medrec_research.cli import _build_parser
from medrec_research.reproduction.cli_commands import _recover_reproduction


def test_recovery_command_has_no_scientific_execution_hooks() -> None:
    args = _build_parser().parse_args(
        [
            "recover-reproduction",
            "safedrug-archived",
            "retain",
            "--dataset-root",
            "/data",
            "--run-root",
            "/attempt/retain",
            "--recovery-id",
            "finalizer-1",
            "--finalizer-revision",
            "e" * 40,
        ]
    )

    assert args.handler is _recover_reproduction
    assert not hasattr(args, "python")
    assert not hasattr(args, "phase")
    assert not hasattr(args, "upstream_root")
    assert not hasattr(args, "selection")
