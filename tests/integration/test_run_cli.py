from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pytest

from medrec_research import ProtocolValidationError
from medrec_research.cli import _build_parser, _local_source_revision, _run
from medrec_research.remote_executor import RemoteSubmission

PROJECT_ROOT = Path(__file__).parents[2]
REGISTRY_PATH = PROJECT_ROOT / "baselines" / "registry.toml"


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, "-m", "medrec_research.cli", "run", *args),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_args(*, dry_run: bool) -> argparse.Namespace:
    return argparse.Namespace(
        mode="reproduction",
        baseline_id="gamenet",
        gpu=0,
        min_free_gpu_mib=20000,
        min_free_disk_gib=100,
        registry=REGISTRY_PATH,
        remote_root="/root/zhb/medrec-research",
        data_root="/root/zhb/medrec-data",
        dry_run=dry_run,
    )


def test_run_cli_dry_run_rejects_archived_baselines_without_adapters() -> None:
    for baseline_id in ("gamenet", "safedrug", "retain", "leap-safedrug"):
        completed = _cli(
            "--mode",
            "reproduction",
            "--baseline-id",
            baseline_id,
            "--gpu",
            "0",
            "--min-free-gpu-mib",
            "20000",
            "--min-free-disk-gib",
            "100",
            "--dry-run",
        )

        assert completed.returncode == 2
        assert "adapter_command" in completed.stderr
        assert completed.stdout == ""


def test_run_parser_uses_documented_319_data_root() -> None:
    args = _build_parser().parse_args(
        [
            "run",
            "--mode",
            "reproduction",
            "--baseline-id",
            "gamenet",
            "--gpu",
            "0",
            "--min-free-gpu-mib",
            "20000",
            "--min-free-disk-gib",
            "100",
        ]
    )

    assert args.data_root == "/root/zhb/medrec-data"


def test_run_cli_rejects_comparison_and_unknown_baseline() -> None:
    comparison = _cli(
        "--mode",
        "comparison",
        "--baseline-id",
        "gamenet",
        "--gpu",
        "0",
        "--min-free-gpu-mib",
        "20000",
        "--min-free-disk-gib",
        "100",
        "--dry-run",
    )
    assert comparison.returncode == 2
    assert "invalid choice" in comparison.stderr

    unknown = _cli(
        "--mode",
        "reproduction",
        "--baseline-id",
        "unknown",
        "--gpu",
        "0",
        "--min-free-gpu-mib",
        "20000",
        "--min-free-disk-gib",
        "100",
        "--dry-run",
    )
    assert unknown.returncode == 2
    assert "not registered" in unknown.stderr
    assert "Traceback" not in unknown.stderr


def test_non_dry_handler_passes_clean_revision_to_executor(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class RecordingExecutor:
        def __init__(self) -> None:
            self.source_revision: str | None = None

        def run_baseline(self, baseline, **kwargs):
            self.source_revision = kwargs["source_revision"]
            return RemoteSubmission(
                baseline_id=baseline.baseline_id,
                host="319-lab",
                session_id="medrec-baseline-gamenet-20260822-120000",
                command="remote command",
                preflight_performed=True,
            )

    def git_runner(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        command = argv[-1]
        if command == "--show-toplevel":
            stdout = f"{PROJECT_ROOT}\n"
        elif command == "HEAD":
            stdout = f"{'a' * 40}\n"
        else:
            stdout = ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    executor = RecordingExecutor()
    assert _run(_run_args(dry_run=False), executor=executor, git_runner=git_runner) == 0

    assert executor.source_revision == "a" * 40
    payload = json.loads(capsys.readouterr().out)
    assert payload["preflight"] == "passed"
    assert payload["host"] == "319-lab"


def test_local_source_revision_rejects_dirty_worktree_without_exposing_output() -> None:
    def git_runner(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        command = argv[-1]
        if command == "--show-toplevel":
            stdout = f"{PROJECT_ROOT}\n"
        elif command == "--untracked-files=all":
            stdout = " M private-patient-notes.txt\n"
        else:
            stdout = f"{'a' * 40}\n"
        return subprocess.CompletedProcess(argv, 0, stdout, "secret stderr")

    with pytest.raises(ProtocolValidationError, match="clean Git worktree") as caught:
        _local_source_revision(PROJECT_ROOT, require_clean=True, runner=git_runner)

    assert "private-patient-notes" not in str(caught.value)
    assert "secret stderr" not in str(caught.value)
