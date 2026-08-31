from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from baselines.reproduction_runner import (
    advance_progress_heartbeat,
    heartbeat_from_log_text,
    load_progress_status,
    read_and_validate_adaptation,
    run_logged,
    run_logged_with_progress,
    validate_identity_binding,
    validate_run_layout,
    write_failure_pair,
    write_json_atomic,
)


class CustomReproductionError(Exception):
    pass


def _calc_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_write_json_atomic_creates_valid_json(tmp_path: Path) -> None:
    target = tmp_path / "subdir" / "output.json"
    data = {"key": "value", "count": 42}
    write_json_atomic(target, data)

    assert target.is_file()
    assert json.loads(target.read_text(encoding="utf-8")) == data
    # Verify no temp files left behind
    assert [p.name for p in target.parent.iterdir()] == ["output.json"]


def test_run_logged_executes_and_writes_log(tmp_path: Path) -> None:
    log_file = tmp_path / "test.log"
    command = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.write('hello stdout\\n'); sys.stderr.write('hello stderr\\n')",
    ]

    run_logged(command, cwd=tmp_path, env={}, log_path=log_file)

    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "hello stdout" in content
    assert "hello stderr" in content


def test_run_logged_raises_on_command_failure(tmp_path: Path) -> None:
    log_file = tmp_path / "fail.log"
    command = [sys.executable, "-c", "import sys; sys.stderr.write('error msg\\n'); sys.exit(42)"]

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        run_logged(command, cwd=tmp_path, env={}, log_path=log_file)
    assert exc_info.value.returncode == 42
    assert "error msg" in log_file.read_text(encoding="utf-8")


def test_run_logged_with_progress_updates_status(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    log_path = run_root / "train.log"

    write_json_atomic(
        run_root / "status.running.json",
        {
            "schema_version": 2,
            "kind": "reproduction_progress_v2",
            "state": "training",
            "heartbeat": 0,
        },
    )

    command = [
        sys.executable,
        "-u",
        "-c",
        "import sys, time; sys.stdout.write('epoch 1 complete\\n'); sys.stdout.flush(); sys.stdout.write('epoch 2 complete\\n'); sys.stdout.flush()",
    ]

    output = run_logged_with_progress(
        command,
        cwd=run_root,
        env={},
        log_path=log_path,
        poll_interval_seconds=0.05,
    )

    assert "epoch 1 complete" in output
    assert "epoch 2 complete" in output

    status = load_progress_status(run_root)
    assert status is not None
    assert status.get("heartbeat", 0) >= 2


def test_validate_run_layout_checks(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    data = tmp_path / "data"
    run_root = tmp_path / "run"

    # run root already exists
    run_root.mkdir()
    with pytest.raises(CustomReproductionError, match="run root already exists"):
        validate_run_layout(
            upstream_root=upstream,
            data_dir=data,
            run_root=run_root,
            error_type=CustomReproductionError,
        )
    run_root.rmdir()

    # dataset inside upstream
    with pytest.raises(CustomReproductionError, match="dataset root must be outside"):
        validate_run_layout(
            upstream_root=upstream,
            data_dir=upstream / "subdata",
            run_root=run_root,
            error_type=CustomReproductionError,
        )

    # run root inside upstream
    with pytest.raises(CustomReproductionError, match="run root must be outside"):
        validate_run_layout(
            upstream_root=upstream,
            data_dir=data,
            run_root=upstream / "subrun",
            error_type=CustomReproductionError,
        )


VALID_IDENTITY = {
    "attempt_id": "attempt-1",
    "lane_id": "lane-1",
    "scientific_baseline_id": "safedrug",
    "program_id": "safedrug-archived",
    "profile_id": "safedrug",
    "harness_revision": "a" * 40,
    "model_source_revision": "b" * 40,
    "preprocessing_revision": "c" * 40,
    "snapshot_id": "safedrug-archived-ijcai21",
    "environment_sha256": "e" * 64,
    "mode": "formal",
    "submission_id": "sub-1",
}


def test_validate_identity_binding_checks() -> None:
    validate_identity_binding(
        VALID_IDENTITY,
        program_id="safedrug-archived",
        source_revision="b" * 40,
        expected_baseline_id="safedrug",
        error_type=CustomReproductionError,
    )

    # Wrong program id
    with pytest.raises(CustomReproductionError, match="different Reproduction Program"):
        validate_identity_binding(
            {**VALID_IDENTITY, "program_id": "other"},
            program_id="safedrug-archived",
            source_revision="b" * 40,
            error_type=CustomReproductionError,
        )

    # Wrong revision
    with pytest.raises(CustomReproductionError, match="different model source revision"):
        validate_identity_binding(
            {**VALID_IDENTITY, "model_source_revision": "other"},
            program_id="safedrug-archived",
            source_revision="b" * 40,
            error_type=CustomReproductionError,
        )

    # Wrong baseline id
    with pytest.raises(CustomReproductionError, match="different scientific baseline"):
        validate_identity_binding(
            VALID_IDENTITY,
            program_id="safedrug-archived",
            source_revision="b" * 40,
            expected_baseline_id="other-baseline",
            error_type=CustomReproductionError,
        )


def test_read_and_validate_adaptation(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()

    with pytest.raises(CustomReproductionError, match="source adaptation artifact cannot be read"):
        read_and_validate_adaptation(
            run_root,
            entrypoint="main.py",
            source_revision="rev-123",
            calc_sha256=_calc_sha256,
            error_type=CustomReproductionError,
        )

    entrypoint_file = run_root / "work" / "src" / "main.py"
    entrypoint_file.parent.mkdir(parents=True)
    entrypoint_file.write_text("print('hello')\n", encoding="utf-8")

    adaptation = {
        "archived_revision": "rev-123",
        "entrypoint": "main.py",
        "learning_rate": 0.001,
        "original_sha256": "0" * 64,
        "adapted_sha256": _calc_sha256(entrypoint_file),
        "reverse_verification": "byte-identical",
        "phase": "training",
    }
    write_json_atomic(run_root / "adaptation.json", adaptation)

    read_data = read_and_validate_adaptation(
        run_root,
        entrypoint="main.py",
        source_revision="rev-123",
        calc_sha256=_calc_sha256,
        error_type=CustomReproductionError,
    )
    assert read_data["learning_rate"] == 0.001

    # SHA mismatch
    entrypoint_file.write_text("print('tampered')\n", encoding="utf-8")
    with pytest.raises(CustomReproductionError, match="does not match the adapted entrypoint"):
        read_and_validate_adaptation(
            run_root,
            entrypoint="main.py",
            source_revision="rev-123",
            calc_sha256=_calc_sha256,
            error_type=CustomReproductionError,
        )


def test_write_failure_pair(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()

    write_failure_pair(
        run_root,
        identity=VALID_IDENTITY,
        started_at="2026-08-31T00:00:00Z",
        artifact_type="training",
        error_type=CustomReproductionError,
        non_evidence=False,
    )

    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    result = json.loads((run_root / "result.json").read_text(encoding="utf-8"))

    assert status["state"] == "failed"
    assert status["failure_code"] == "training_failed"
    assert result["state"] == "failed"
    assert result["artifact_type"] == "training"
    assert result["failure_code"] == "training_failed"


def test_heartbeat_helpers(tmp_path: Path) -> None:
    log_sample = "epoch 0\nepoch 1\n"
    assert heartbeat_from_log_text(log_sample) == 2
    assert heartbeat_from_log_text("") == 0

    run_root = tmp_path / "run"
    run_root.mkdir()
    write_json_atomic(
        run_root / "status.running.json",
        {"heartbeat": 0, "state": "training"},
    )

    advance_progress_heartbeat(run_root, 2)
    status = load_progress_status(run_root)
    assert status is not None
    assert status["heartbeat"] == 2
