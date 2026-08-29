from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pytest

from medrec_research import BaselineRegistry, ProtocolValidationError
from medrec_research.cli import (
    _admit_reproduction_continuation,
    _build_parser,
    _local_source_revision,
    _reproduce,
    _reproduce_smoke,
)
from medrec_research.remote_executor import RemoteSubmission

PROJECT_ROOT = Path(__file__).parents[2]
REGISTRY_PATH = PROJECT_ROOT / "baselines" / "registry.toml"
SUCCESSOR_LANES = (
    "molerec-retain",
    "molerec-leap",
    "molerec-gamenet",
    "molerec-safedrug-lr-1e-5",
    "molerec-safedrug-lr-1e-4",
    "molerec-safedrug-lr-5e-4",
    "molerec-embedding",
)
SUCCESSOR_MAPPING = {
    "molerec-retain": (3, "12-15,44-47", 0),
    "molerec-leap": (4, "16-19,48-51", 1),
    "molerec-gamenet": (5, "20-23,52-55", 1),
    "molerec-safedrug-lr-1e-5": (6, "24-27,56-59", 1),
    "molerec-safedrug-lr-1e-4": (1, "4-7,36-39", 0),
    "molerec-safedrug-lr-5e-4": (2, "8-11,40-43", 0),
    "molerec-embedding": (0, "0-3,32-35", 0),
}


def _write_schedule(path: Path) -> Path:
    revision = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "stage": "u7-measured-gpu-schedule",
                "schedule_state": "frozen",
                "harness_revision": revision,
                "environment_sha256": (
                    "6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda"
                ),
                "preprocessing_revision": ("c7218d0976e5ee5588aeaf5bdbc86b338126bba5"),
                "snapshot_id": "snapshots/molerec-table1-c721-www23",
                "model_source_revisions": {
                    "safedrug_archived": "8deee38cfdb2a38882377ff95cce5922d6d9e8d6",
                    "molerec": "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a",
                },
                "selected_mapping": "B",
                "gpu7_reserved": True,
                "formal_execution": {
                    "mode": "formal",
                    "reserved_gpu": 7,
                    "gpu_order": [SUCCESSOR_MAPPING[lane][0] for lane in SUCCESSOR_LANES],
                    "cpu_set_order": [SUCCESSOR_MAPPING[lane][1] for lane in SUCCESSOR_LANES],
                },
                "mapping": {
                    lane: {
                        "gpu": gpu,
                        "cpu_set": cpu_set,
                        "numa": numa,
                    }
                    for lane, (gpu, cpu_set, numa) in SUCCESSOR_MAPPING.items()
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _cli(subcommand: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, "-m", "medrec_research.cli", subcommand, *args),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _args(*, baseline_id: str = "gamenet", dry_run: bool = True) -> argparse.Namespace:
    return argparse.Namespace(
        baseline_id=baseline_id,
        gpu=0 if baseline_id != "all" else None,
        gpus=(0, 1, 2, 3) if baseline_id == "all" else None,
        min_free_gpu_mib=20000,
        min_free_disk_gib=100,
        registry=REGISTRY_PATH,
        remote_root="/root/zhb/medrec-research",
        data_root="/root/zhb/medrec-data",
        dry_run=dry_run,
    )


def test_reproduce_dry_run_prints_complete_archived_command() -> None:
    completed = _cli("reproduce", "gamenet", "--gpu", "0", "--dry-run")

    assert completed.returncode == 0
    result = json.loads(completed.stdout)["results"][0]
    assert result["state"] == "planned"
    assert result["attempt_id"].startswith("attempt-")
    assert "baselines/safedrug_archived.py gamenet" in result["command"]
    assert "--upstream-root /root/zhb/SafeDrug" in result["command"]
    assert (
        "--dataset-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23"
        in result["command"]
    )
    assert "--mode smoke" not in result["command"]
    assert completed.stderr == ""


def test_reproduce_smoke_dry_run_prints_complete_smoke_command() -> None:
    completed = _cli("reproduce-smoke", "safedrug", "--gpu", "1", "--dry-run")

    assert completed.returncode == 0
    parsed = json.loads(completed.stdout)
    assert parsed["mode"] == "smoke"
    result = parsed["results"][0]
    assert result["state"] == "planned"
    assert result["session_id"].startswith("medrec-smoke-safedrug-")
    assert "--mode smoke" in result["command"]
    assert "CUDA_VISIBLE_DEVICES=1" in result["command"]
    assert completed.stderr == ""


def test_reproduce_all_dry_run_maps_four_independent_lanes() -> None:
    completed = _cli("reproduce", "all", "--gpus", "2,3,4,5", "--dry-run")

    assert completed.returncode == 0
    results = json.loads(completed.stdout)["results"]
    assert [(item["baseline_id"], item["gpu"]) for item in results] == [
        ("gamenet", 2),
        ("safedrug", 3),
        ("retain", 4),
        ("leap-safedrug", 5),
    ]
    assert all(item["state"] == "planned" for item in results)


def test_reproduce_smoke_all_dry_run_maps_four_independent_lanes() -> None:
    completed = _cli("reproduce-smoke", "all", "--gpus", "0,1,2,3", "--dry-run")

    assert completed.returncode == 0
    parsed = json.loads(completed.stdout)
    assert parsed["mode"] == "smoke"
    results = parsed["results"]
    assert [(item["baseline_id"], item["gpu"]) for item in results] == [
        ("gamenet", 0),
        ("safedrug", 1),
        ("retain", 2),
        ("leap-safedrug", 3),
    ]
    assert all(item["state"] == "planned" for item in results)
    assert all("--mode smoke" in item["command"] for item in results)


def test_reproduce_smoke_all_dry_run_maps_cpu_sets_to_successor_lanes() -> None:
    cpu_sets = ";".join(
        (
            "0-3,32-35",
            "4-7,36-39",
            "8-11,40-43",
            "12-15,44-47",
            "16-19,48-51",
            "20-23,52-55",
            "24-27,56-59",
        )
    )
    completed = _cli(
        "reproduce-smoke",
        "all",
        "--gpus",
        "0,1,2,3,4,5,6",
        "--cpu-sets",
        cpu_sets,
        "--dry-run",
    )

    assert completed.returncode == 0, completed.stderr
    results = json.loads(completed.stdout)["results"]
    assert [item["cpu_set"] for item in results] == cpu_sets.split(";")
    assert all("taskset --cpu-list" in item["command"] for item in results)


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("all", "--gpu", "0", "--dry-run"), "four unique --gpus"),
        (("gamenet", "--gpus", "0,1", "--dry-run"), "requires --gpu"),
    ],
)
def test_reproduce_rejects_incoherent_gpu_selection(
    arguments: tuple[str, ...], message: str
) -> None:
    completed = _cli("reproduce", *arguments)

    assert completed.returncode == 2
    assert message in completed.stderr


def test_reproduce_parser_uses_documented_319_roots() -> None:
    args = _build_parser().parse_args(["reproduce", "gamenet", "--gpu", "0"])

    assert args.data_root == "/root/zhb/medrec-data"
    assert args.remote_root == "/root/zhb/medrec-research"


def test_reproduce_smoke_parser_uses_documented_319_roots() -> None:
    args = _build_parser().parse_args(["reproduce-smoke", "gamenet", "--gpu", "0"])

    assert args.data_root == "/root/zhb/medrec-data"
    assert args.remote_root == "/root/zhb/medrec-research"


def test_batch_continues_after_one_lane_is_blocked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class RecordingExecutor:
        def __init__(self) -> None:
            self.baseline_ids: list[str] = []

        def run_baseline(self, baseline_id, **kwargs):
            self.baseline_ids.append(baseline_id)
            if baseline_id == "safedrug":
                raise ProtocolValidationError("synthetic lane failure")
            return RemoteSubmission(
                baseline_id=baseline_id,
                host=None,
                session_id=f"medrec-baseline-{baseline_id}-test",
                command=f"command {baseline_id}",
                preflight_performed=False,
            )

    executor = RecordingExecutor()
    assert _reproduce(_args(baseline_id="all"), executor=executor) == 2

    assert executor.baseline_ids == ["gamenet", "safedrug", "retain", "leap-safedrug"]
    results = json.loads(capsys.readouterr().out)["results"]
    assert [item["state"] for item in results] == [
        "planned",
        "blocked",
        "planned",
        "planned",
    ]


def test_smoke_batch_continues_after_one_lane_is_blocked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class RecordingExecutor:
        def __init__(self) -> None:
            self.baseline_ids: list[str] = []

        def run_smoke(self, baseline_id, **kwargs):
            self.baseline_ids.append(baseline_id)
            if baseline_id == "safedrug":
                raise ProtocolValidationError("synthetic lane failure")
            return RemoteSubmission(
                baseline_id=baseline_id,
                host=None,
                session_id=f"medrec-smoke-{baseline_id}-test",
                command=f"command {baseline_id} --mode smoke",
                preflight_performed=False,
            )

    executor = RecordingExecutor()
    assert _reproduce_smoke(_args(baseline_id="all"), executor=executor) == 2

    assert executor.baseline_ids == ["gamenet", "safedrug", "retain", "leap-safedrug"]
    results = json.loads(capsys.readouterr().out)["results"]
    assert [item["state"] for item in results] == [
        "planned",
        "blocked",
        "planned",
        "planned",
    ]


def test_real_handler_passes_clean_revision_to_executor(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class RecordingExecutor:
        def __init__(self) -> None:
            self.source_revision: str | None = None

        def run_baseline(self, baseline_id, **kwargs):
            self.source_revision = kwargs["source_revision"]
            return RemoteSubmission(
                baseline_id=baseline_id,
                host="319-lab",
                session_id="medrec-baseline-gamenet-test",
                command="remote command",
                preflight_performed=True,
            )

    def git_runner(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        stdout = f"{'a' * 40}\n" if argv[-1] == "HEAD" else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    executor = RecordingExecutor()
    assert _reproduce(_args(dry_run=False), executor=executor, git_runner=git_runner) == 0

    assert executor.source_revision == "a" * 40
    assert json.loads(capsys.readouterr().out)["results"][0]["state"] == "submitted"


def test_local_source_revision_rejects_dirty_worktree_without_exposing_output() -> None:
    def git_runner(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        stdout = (
            " M private-patient-notes.txt\n"
            if argv[-1] == "--untracked-files=all"
            else f"{'a' * 40}\n"
        )
        return subprocess.CompletedProcess(argv, 0, stdout, "secret stderr")

    with pytest.raises(ProtocolValidationError, match="clean Git worktree") as caught:
        _local_source_revision(PROJECT_ROOT, require_clean=True, runner=git_runner)

    assert "private-patient-notes" not in str(caught.value)
    assert "secret stderr" not in str(caught.value)


def test_project_registry_program_is_shared_by_all_archived_lanes() -> None:
    registry = BaselineRegistry.load(REGISTRY_PATH)

    assert {
        registry.reproduction_program_for(registry.get(baseline_id)).program_id
        for baseline_id in ("gamenet", "safedrug", "retain", "leap-safedrug")
    } == {"safedrug-archived"}


def test_stage_safedrug_c721_cli_missing_arg_fails() -> None:
    completed = _cli("stage-safedrug-c721")
    assert completed.returncode == 2
    assert "required" in completed.stderr


def test_audit_safedrug_table2_cli_missing_arg_fails() -> None:
    completed = _cli("audit-safedrug-table2")
    assert completed.returncode == 2
    assert "required" in completed.stderr


def test_reproduce_all_seven_lanes_dry_run_maps_frozen_schedule(tmp_path: Path) -> None:
    schedule = _write_schedule(tmp_path / "u7-schedule.json")
    completed = _cli(
        "reproduce",
        "all",
        "--gpus",
        "3,4,5,6,1,2,0",
        "--schedule",
        str(schedule),
        "--dry-run",
    )
    assert completed.returncode == 0
    results = json.loads(completed.stdout)["results"]
    assert len(results) == 7
    assert [(item["baseline_id"], item["gpu"]) for item in results] == [
        ("molerec-retain", 3),
        ("molerec-leap", 4),
        ("molerec-gamenet", 5),
        ("molerec-safedrug-lr-1e-5", 6),
        ("molerec-safedrug-lr-1e-4", 1),
        ("molerec-safedrug-lr-5e-4", 2),
        ("molerec-embedding", 0),
    ]


def test_reproduce_single_lane_id_dry_run(tmp_path: Path) -> None:
    schedule = _write_schedule(tmp_path / "u7-schedule.json")
    completed = _cli(
        "reproduce",
        "molerec-safedrug-lr-1e-5",
        "--gpu",
        "6",
        "--schedule",
        str(schedule),
        "--dry-run",
    )
    assert completed.returncode == 0
    result = json.loads(completed.stdout)["results"][0]
    assert result["state"] == "planned"
    assert (
        "SafeDrug.py safedrug" in result["command"]
        or "safedrug_archived.py safedrug" in result["command"]
    )
    assert "--learning-rate 1e-05" in result["command"]


def test_continuation_command_writes_only_reaccepted_schedule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_schedule(tmp_path / "u7-schedule.json")
    output = tmp_path / "continuation.json"
    parser = _build_parser()
    arguments = [
        "admit-reproduction-continuation",
        "--source-schedule",
        str(source_path),
        "--source-schedule-id",
        "u7-schedule",
        "--attempt-root",
        str(tmp_path),
        "--attempt-id",
        "formal-20260828-a09fcab-u8-b",
        "--output",
        str(output),
    ]
    for lane_id in SUCCESSOR_LANES:
        arguments.extend(
            [
                "--training-artifact",
                f"{lane_id}=runs/{lane_id}/recoveries/recovery-{lane_id}/result.json",
            ]
        )
    args = parser.parse_args(arguments)

    def admit(**kwargs: object):
        return kwargs["source_schedule"].reaccept(
            source_schedule_id=kwargs["source_schedule_id"],
            harness_revision=kwargs["harness_revision"],
            attempt_id=kwargs["attempt_id"],
        )

    def git_runner(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        stdout = "" if "status" in argv else "b" * 40 + "\n"
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    monkeypatch.setattr("medrec_research.cli.validate_reproduction_continuation", admit)
    assert _admit_reproduction_continuation(args, git_runner=git_runner) == 0

    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == 2
    assert persisted["attempt_id"] == "formal-20260828-a09fcab-u8-b"
    assert persisted["source_schedule_id"] == "u7-schedule"
    assert "command" not in json.loads(capsys.readouterr().out)
    assert not any(hasattr(args, field) for field in ("phase", "recovery_id", "checkpoint"))
