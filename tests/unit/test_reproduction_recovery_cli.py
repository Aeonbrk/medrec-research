from __future__ import annotations

import pytest

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


def test_recover_reproduction_translates_reproduction_error_to_cli_error(
    tmp_path, monkeypatch, capsys
) -> None:
    from baselines import safedrug_archived
    from medrec_research.cli import main
    from medrec_research.errors import ProtocolValidationError

    dataset = tmp_path / "data"
    dataset.mkdir()
    run = tmp_path / "run"
    run.mkdir()

    def mock_execute_failure(request):
        raise safedrug_archived.ReproductionError("source run has not failed")

    monkeypatch.setattr(safedrug_archived, "execute", mock_execute_failure)

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

    # 1. Handler translates domain failure to ProtocolValidationError
    with pytest.raises(ProtocolValidationError, match="source run has not failed"):
        args.handler(args)

    # 2. CLI main suppresses traceback, emits error message to stderr, and exits with 2
    exit_code = main(
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
    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "medrec: error: source run has not failed" in captured.err
    assert "Traceback" not in captured.err


def test_recover_reproduction_does_not_catch_unexpected_value_error(tmp_path, monkeypatch) -> None:
    from baselines import safedrug_archived

    dataset = tmp_path / "data"
    dataset.mkdir()
    run = tmp_path / "run"
    run.mkdir()

    def mock_execute_unexpected_error(request):
        raise ValueError("unexpected path computation defect")

    monkeypatch.setattr(safedrug_archived, "execute", mock_execute_unexpected_error)

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

    with pytest.raises(ValueError, match="unexpected path computation defect"):
        args.handler(args)


def test_recover_reproduction_dispatches_to_molerec_program(tmp_path, monkeypatch) -> None:
    from baselines import molerec

    dataset = tmp_path / "data"
    dataset.mkdir()
    run = tmp_path / "run"
    run.mkdir()

    calls = []

    def mock_execute(request):
        calls.append(request)
        return {"marker_path": str(run / "recovery.json")}

    monkeypatch.setattr(molerec, "execute", mock_execute)

    args = _build_parser().parse_args(
        [
            "recover-reproduction",
            "molerec",
            "molerec",
            "--dataset-root",
            str(dataset),
            "--run-root",
            str(run),
            "--recovery-id",
            "finalizer-molerec",
            "--finalizer-revision",
            "f" * 40,
        ]
    )

    exit_code = args.handler(args)
    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0]["baseline_id"] == "molerec"
    assert calls[0]["recovery_id"] == "finalizer-molerec"
