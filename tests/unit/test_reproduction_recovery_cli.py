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


def test_recover_reproduction_handler_executes_via_program_execute(
    tmp_path, monkeypatch, capsys
) -> None:
    from baselines import safedrug_archived

    dataset = tmp_path / "data"
    dataset.mkdir()
    run = tmp_path / "run"
    run.mkdir()

    calls = []

    def mock_execute(request):
        calls.append(request)
        return {"marker_path": str(run / "recovery.json")}

    monkeypatch.setattr(safedrug_archived, "execute", mock_execute)

    args = _build_parser().parse_args(
        [
            "recover-reproduction",
            "safedrug-archived",
            "retain",
            "--dataset-root",
            str(dataset),
            "--run-root",
            str(run),
            "--recovery-id",
            "finalizer-1",
            "--finalizer-revision",
            "e" * 40,
        ]
    )

    exit_code = args.handler(args)
    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0]["mode"] == "recovery"
    assert calls[0]["baseline_id"] == "retain"
    assert calls[0]["recovery_id"] == "finalizer-1"
    captured = capsys.readouterr()
    assert "recovery_root" in captured.out
