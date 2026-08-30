from __future__ import annotations

import hashlib
import json
import pickle
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from baselines import (
    molerec as molerec_program,
)
from baselines import (
    molerec_runner,
    safedrug_archived_runner,
)
from baselines import (
    safedrug_archived as safedrug_archived_program,
)
from baselines.reproduction_artifacts import reopen_recovered_v2_pair, reopen_v2_pair
from baselines.reproduction_runner import (
    _run_logged_with_progress,
    recover_training_lane_v2,
    run_smoke_lane_v2,
    run_test_lane_v2,
    run_training_lane_v2,
)
from medrec_research.reproduction_evidence import reopen_recovered_finalized_pair

IDENTITY = {
    "attempt_id": "attempt-1",
    "lane_id": "molerec-safedrug-lr-1e-4",
    "scientific_baseline_id": "safedrug",
    "program_id": "safedrug-archived",
    "profile_id": "safedrug",
    "harness_revision": "a" * 40,
    "model_source_revision": "b" * 40,
    "preprocessing_revision": "c" * 40,
    "snapshot_id": "snapshots/molerec-table1-c721-www23",
    "environment_sha256": "d" * 64,
    "mode": "formal",
    "submission_id": "submission-1",
}
COUNTS = {
    "patients": 6350,
    "visits": 15032,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}


def _module(tmp_path: Path, *, mode: str = "formal") -> SimpleNamespace:
    profile = SimpleNamespace(
        baseline_id="safedrug",
        entrypoint="main.py",
        model_name="SafeDrug",
        learning_rate=1e-4,
        required_inputs=("records_final.pkl",),
        checkpoint_pattern=None,
        test_uses_basename=False,
    )
    commands: list[list[str]] = []

    def write_json(path: Path, value: dict[str, object]) -> None:
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def run_logged(command: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
        del env
        commands.append(list(command))
        epoch_count = 1 if mode == "smoke" else 50
        log_path.write_text(
            "\n".join(f"epoch {index}" for index in range(epoch_count)),
            encoding="utf-8",
        )
        checkpoint_parent = cwd.parent if profile.baseline_id.startswith("molerec") else cwd
        checkpoint_dir = (
            checkpoint_parent / "saved" / f"{profile.model_name}_{log_path.parent.name}"
        )
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        (checkpoint_dir / "Epoch_0_TARGET_0.0_JA_0.5200_DDI_0.0600.model").write_bytes(
            b"checkpoint"
        )
        history = {
            "ja": [0.52, *([0.1] * (epoch_count - 1))],
            "ddi_rate": [0.06] * epoch_count,
            "avg_p": [0.1] * epoch_count,
            "avg_r": [0.1] * epoch_count,
            "avg_f1": [0.1] * epoch_count,
            "prauc": [0.1] * epoch_count,
            "med": [10.0] * epoch_count,
        }
        history_name = (
            "history.pkl"
            if profile.baseline_id.startswith("molerec")
            else f"history_{checkpoint_dir.name}.pkl"
        )
        with (checkpoint_dir / history_name).open("wb") as stream:
            pickle.dump(history, stream)

    def select_checkpoint(checkpoint_dir: Path, selected_profile: object, best_epoch: int) -> Path:
        del selected_profile
        return next(checkpoint_dir.glob(f"Epoch_{best_epoch}_*.model"))

    def adapt(source: str, *, target_lr: float | None = None) -> str:
        del target_lr
        return source

    def parse_training_log(log_text: str, expected_epochs: int = 50) -> int:
        assert len(log_text.splitlines()) == expected_epochs
        return 0

    def environment_summary() -> dict[str, str]:
        return {"conda_explicit_sha256": "d" * 64}

    return SimpleNamespace(
        profile=profile,
        commands=commands,
        verify_upstream_source=lambda root: None,
        load_and_validate_canonical_inputs=lambda root: ([], COUNTS, {}, [], []),
        environment_summary=environment_summary,
        adapt_training_source=adapt,
        adapt_smoke_source=adapt,
        sha256=lambda path: hashlib.sha256(path.read_bytes()).hexdigest(),
        write_json=write_json,
        run_logged=run_logged,
        training_command=lambda python, entrypoint, model_name: [
            python,
            str(entrypoint),
            model_name,
        ],
        parse_training_log=parse_training_log,
        parse_validation_metrics=lambda text: {
            "validation_jaccard": 0.52,
            "validation_ddi_rate": 0.06,
        },
        select_checkpoint=select_checkpoint,
        native_history_path=lambda checkpoint_dir, model_name: (
            checkpoint_dir / f"history_{model_name}.pkl"
        ),
        test_command=lambda *args, **kwargs: ["test"],
    )


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    upstream = tmp_path / "upstream"
    (upstream / "src").mkdir(parents=True)
    (upstream / "src" / "main.py").write_text("main", encoding="utf-8")
    data = tmp_path / "data"
    data.mkdir()
    (data / "records_final.pkl").write_bytes(b"records")
    return upstream, data


def test_direct_script_dispatch_uses_the_facade_main_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facade = object()
    for name in (
        "molerec_program",
        "baselines.molerec",
        "molerec",
        "safedrug_archived_program",
        "baselines.safedrug_archived",
        "safedrug_archived",
    ):
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setitem(sys.modules, "__main__", facade)

    assert molerec_runner._dispatch_module(None) is facade
    assert safedrug_archived_runner._dispatch_module(None) is facade


def test_training_lane_finalizes_v2_training_artifact(tmp_path: Path) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path)
    run_root = tmp_path / "training"

    run_training_lane_v2(
        module=module,
        profile=module.profile,
        upstream_root=upstream,
        data_dir=data,
        run_root=run_root,
        python="python",
        learning_rate=1e-4,
        identity=IDENTITY,
        program_id="safedrug-archived",
        source_revision="b" * 40,
        gate_inputs=(),
        error_type=ValueError,
    )

    status, result = reopen_v2_pair(run_root, expected_identity=IDENTITY, error_type=ValueError)
    assert status["state"] == "completed"
    assert result["artifact_type"] == "training"
    assert result["validation_jaccard"] == 0.52
    assert json.loads((run_root / "status.running.json").read_text())["heartbeat"] == 50
    assert "heartbeat" not in status
    assert "heartbeat" not in result
    assert not (run_root / "test.log").exists()


def test_progress_heartbeat_advances_then_stalls_without_terminal_mutation(
    tmp_path: Path,
) -> None:
    status_path = tmp_path / "status.running.json"
    status_path.write_text(json.dumps({"heartbeat": 0}), encoding="utf-8")
    log_path = tmp_path / "train.log"
    started = threading.Event()
    release = threading.Event()

    def stalled_run_logged(
        command: list[str], *, cwd: Path, env: dict[str, str], log_path: Path
    ) -> None:
        del command, cwd, env
        with log_path.open("w", encoding="utf-8") as stream:
            stream.write("epoch 0\n")
            stream.flush()
            started.set()
            release.wait(timeout=5)

    worker = threading.Thread(
        target=_run_logged_with_progress,
        kwargs={
            "run_logged": stalled_run_logged,
            "command": ["python", "train.py"],
            "cwd": tmp_path,
            "env": {},
            "log_path": log_path,
        },
    )
    worker.start()
    assert started.wait(timeout=2)

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        heartbeat = json.loads(status_path.read_text(encoding="utf-8"))["heartbeat"]
        if heartbeat >= 1:
            break
        time.sleep(0.02)
    else:
        pytest.fail("progress heartbeat did not advance while the log was written")

    time.sleep(0.35)
    stalled_heartbeat = json.loads(status_path.read_text(encoding="utf-8"))["heartbeat"]
    time.sleep(0.35)
    assert json.loads(status_path.read_text(encoding="utf-8"))["heartbeat"] == stalled_heartbeat

    release.set()
    worker.join(timeout=2)
    assert not worker.is_alive()


def test_complete_unlabeled_training_is_preserved_as_terminal_failure(tmp_path: Path) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path)

    def reject_unlabeled_metrics(text: str) -> dict[str, float]:
        del text
        raise ValueError("training log must contain validation Jaccard and DDI metrics")

    module.parse_validation_metrics = reject_unlabeled_metrics
    run_root = tmp_path / "unlabeled-training"

    with pytest.raises(ValueError, match="validation Jaccard"):
        run_training_lane_v2(
            module=module,
            profile=module.profile,
            upstream_root=upstream,
            data_dir=data,
            run_root=run_root,
            python="python",
            learning_rate=1e-4,
            identity=IDENTITY,
            program_id="safedrug-archived",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )

    status, result = reopen_v2_pair(run_root, expected_identity=IDENTITY, error_type=ValueError)
    assert status["state"] == "failed"
    assert status["failure_code"] == "training_failed"
    assert result == {
        "schema_version": 2,
        "kind": "reproduction_result_v2",
        "identity": IDENTITY,
        "mode": "formal",
        "state": "failed",
        "non_evidence": False,
        "artifact_type": "training",
        "failure_code": "training_failed",
    }
    assert (run_root / "train.log").is_file()
    assert not (run_root / "test.log").exists()


def test_recovery_finalizes_immutable_sibling_without_scientific_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path)

    def reject_unlabeled_metrics(text: str) -> dict[str, float]:
        del text
        raise ValueError("training log must contain validation Jaccard and DDI metrics")

    module.parse_validation_metrics = reject_unlabeled_metrics
    run_root = tmp_path / "recoverable-training"
    with pytest.raises(ValueError, match="validation Jaccard"):
        run_training_lane_v2(
            module=module,
            profile=module.profile,
            upstream_root=upstream,
            data_dir=data,
            run_root=run_root,
            python="python",
            learning_rate=1e-4,
            identity=IDENTITY,
            program_id="safedrug-archived",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )

    source_files = {
        path.relative_to(run_root): path.read_bytes()
        for path in run_root.rglob("*")
        if path.is_file()
    }
    commands_before = list(module.commands)
    monkeypatch.setitem(sys.modules, "dill", pickle)

    recovery_root = recover_training_lane_v2(
        module=module,
        profile=module.profile,
        data_dir=data,
        run_root=run_root,
        recovery_id="finalizer-1",
        finalizer_revision="e" * 40,
        identity=IDENTITY,
        program_id="safedrug-archived",
        source_revision="b" * 40,
        gate_inputs=(),
        error_type=ValueError,
    )

    status, result = reopen_recovered_v2_pair(
        run_root,
        recovery_root,
        expected_identity=IDENTITY,
        error_type=ValueError,
    )
    assert status["state"] == "completed"
    assert result["artifact_type"] == "training"
    assert result["best_epoch"] == 0
    assert result["validation_jaccard"] == 0.52
    assert result["recovery"]["finalizer_revision"] == "e" * 40
    assert result["identity"]["harness_revision"] == "a" * 40
    public_status, public_result = reopen_recovered_finalized_pair(
        run_root,
        recovery_root,
        expected_identity=IDENTITY,
    )
    assert public_status == status
    assert public_result == result
    assert module.commands == commands_before
    assert not (run_root / "test.log").exists()
    assert {path: (run_root / path).read_bytes() for path in source_files} == source_files

    checkpoint_path = run_root / result["checkpoint"]["relative_path"]
    checkpoint_path.write_bytes(b"substitute")
    with pytest.raises(ValueError, match="checkpoint identity"):
        reopen_recovered_v2_pair(
            run_root,
            recovery_root,
            expected_identity=IDENTITY,
            error_type=ValueError,
        )

    with pytest.raises(ValueError, match="already exists"):
        recover_training_lane_v2(
            module=module,
            profile=module.profile,
            data_dir=data,
            run_root=run_root,
            recovery_id="finalizer-1",
            finalizer_revision="e" * 40,
            identity=IDENTITY,
            program_id="safedrug-archived",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )


def test_recovered_training_uses_source_checkpoint_and_new_test_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path)
    module.parse_validation_metrics = lambda text: (_ for _ in ()).throw(
        ValueError("training log must contain validation Jaccard and DDI metrics")
    )
    source_root = tmp_path / "recoverable-test"
    with pytest.raises(ValueError, match="validation Jaccard"):
        run_training_lane_v2(
            module=module,
            profile=module.profile,
            upstream_root=upstream,
            data_dir=data,
            run_root=source_root,
            python="python",
            learning_rate=1e-4,
            identity=IDENTITY,
            program_id="safedrug-archived",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )
    monkeypatch.setitem(sys.modules, "dill", pickle)
    recovery_root = recover_training_lane_v2(
        module=module,
        profile=module.profile,
        data_dir=data,
        run_root=source_root,
        recovery_id="finalizer-test",
        finalizer_revision="e" * 40,
        identity=IDENTITY,
        program_id="safedrug-archived",
        source_revision="b" * 40,
        gate_inputs=(),
        error_type=ValueError,
    )
    checkpoint = (
        source_root
        / json.loads((recovery_root / "result.json").read_text(encoding="utf-8"))["checkpoint"][
            "relative_path"
        ]
    )
    checkpoint_bytes = checkpoint.read_bytes()
    module.profile.test_uses_basename = True
    module.parse_test_log = lambda text: {
        "rounds": [{"jaccard": 0.5}] * 10,
        "harness_summary": {
            "ddi_rate": {"mean": 0.06, "std": 0.0},
            "jaccard": {"mean": 0.5, "std": 0.0},
            "avg_f1": {"mean": 0.5, "std": 0.0},
            "prauc": {"mean": 0.5, "std": 0.0},
            "avg_medications": {"mean": 10.0, "std": 0.0},
        },
    }
    model_names: list[str] = []

    def test_command(
        python: str,
        entrypoint: Path,
        profile: object,
        model_name: str,
        checkpoint_path: Path,
        **kwargs: object,
    ) -> list[str]:
        del python, entrypoint, profile, checkpoint_path, kwargs
        model_names.append(model_name)
        return ["test"]

    module.test_command = test_command

    def run_logged(command: list[str], cwd: Path, env: object, log_path: Path) -> None:
        del command, env
        staged_checkpoint = cwd / "saved" / f"SafeDrug_{source_root.name}" / checkpoint.name
        assert staged_checkpoint.is_symlink()
        assert staged_checkpoint.resolve() == checkpoint.resolve()
        log_path.write_text("test", encoding="utf-8")

    module.run_logged = run_logged
    test_identity = {
        **IDENTITY,
        "harness_revision": "f" * 40,
        "submission_id": "test-submission-1",
    }
    continuation_test_root = tmp_path / "continuation-test"

    with pytest.raises(ValueError, match="does not continue the recovered training lane"):
        run_test_lane_v2(
            module=module,
            profile=module.profile,
            upstream_root=upstream,
            data_dir=data,
            run_root=recovery_root,
            training_source_root=source_root,
            test_root=continuation_test_root,
            python="python",
            identity={**test_identity, "attempt_id": "wrong-attempt"},
            program_id="safedrug-archived",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )
    assert not continuation_test_root.exists()

    run_test_lane_v2(
        module=module,
        profile=module.profile,
        upstream_root=upstream,
        data_dir=data,
        run_root=recovery_root,
        training_source_root=source_root,
        test_root=continuation_test_root,
        python="python",
        identity=test_identity,
        program_id="safedrug-archived",
        source_revision="b" * 40,
        gate_inputs=(),
        error_type=ValueError,
    )

    status, result = reopen_v2_pair(
        continuation_test_root,
        expected_identity=test_identity,
        error_type=ValueError,
    )
    assert status["state"] == "completed"
    assert result["artifact_type"] == "test"
    assert len(result["rounds"]) == 10
    assert checkpoint.read_bytes() == checkpoint_bytes
    assert model_names == [f"SafeDrug_{source_root.name}"]
    assert not (recovery_root / "test").exists()


@pytest.mark.parametrize(
    ("program", "baseline_id"),
    (
        (safedrug_archived_program, "retain"),
        (molerec_program, "molerec-embedding"),
    ),
)
def test_program_main_forwards_continuation_test_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    program: object,
    baseline_id: str,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(program, "run_formal_lane", lambda **kwargs: captured.update(kwargs))
    test_root = tmp_path / "continuation-test"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "program",
            baseline_id,
            "--upstream-root",
            str(tmp_path / "upstream"),
            "--dataset-root",
            str(tmp_path / "data"),
            "--run-root",
            str(tmp_path / "recovery"),
            "--phase",
            "test",
            "--training-source-root",
            str(tmp_path / "source"),
            "--test-root",
            str(test_root),
        ],
    )

    program.main()

    assert captured["test_root"] == test_root.resolve()


def test_recovery_rejects_near_miss_parser_failure_without_creating_sibling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path)
    module.parse_validation_metrics = lambda text: (_ for _ in ()).throw(
        ValueError("training log must contain validation Jaccard and DDI metrics")
    )
    run_root = tmp_path / "near-miss-training"
    with pytest.raises(ValueError, match="validation Jaccard"):
        run_training_lane_v2(
            module=module,
            profile=module.profile,
            upstream_root=upstream,
            data_dir=data,
            run_root=run_root,
            python="python",
            learning_rate=1e-4,
            identity=IDENTITY,
            program_id="safedrug-archived",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )
    module.parse_validation_metrics = lambda text: (_ for _ in ()).throw(
        ValueError("training log contains no validation labels")
    )
    monkeypatch.setitem(sys.modules, "dill", pickle)

    with pytest.raises(ValueError, match="not recoverable"):
        recover_training_lane_v2(
            module=module,
            profile=module.profile,
            data_dir=data,
            run_root=run_root,
            recovery_id="near-miss",
            finalizer_revision="e" * 40,
            identity=IDENTITY,
            program_id="safedrug-archived",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )
    assert not (run_root / "recoveries").exists()


def test_molerec_recovery_uses_archived_saved_history_layout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path)
    module.profile.baseline_id = "molerec"
    module.profile.model_name = "MoleRec"
    module.native_history_path = lambda checkpoint_dir, model_name: checkpoint_dir / "history.pkl"
    module.parse_validation_metrics = lambda text: (_ for _ in ()).throw(
        ValueError("training log must contain validation Jaccard and DDI metrics")
    )
    identity = {
        **IDENTITY,
        "lane_id": "molerec-embedding",
        "scientific_baseline_id": "molerec",
        "program_id": "molerec",
        "profile_id": "molerec-embedding",
    }
    run_root = tmp_path / "molerec-recoverable"
    with pytest.raises(ValueError, match="validation Jaccard"):
        run_training_lane_v2(
            module=module,
            profile=module.profile,
            upstream_root=upstream,
            data_dir=data,
            run_root=run_root,
            python="python",
            learning_rate=1e-4,
            identity=identity,
            program_id="molerec",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )
    commands_before = list(module.commands)
    monkeypatch.setitem(sys.modules, "dill", pickle)

    recovery_root = recover_training_lane_v2(
        module=module,
        profile=module.profile,
        data_dir=data,
        run_root=run_root,
        recovery_id="molerec-finalizer-1",
        finalizer_revision="e" * 40,
        identity=identity,
        program_id="molerec",
        source_revision="b" * 40,
        gate_inputs=(),
        error_type=ValueError,
    )

    _, result = reopen_recovered_v2_pair(
        run_root,
        recovery_root,
        expected_identity=identity,
        error_type=ValueError,
    )
    checkpoint_dir = run_root / "work" / "saved" / f"MoleRec_{run_root.name}"
    assert (checkpoint_dir / "history.pkl").is_file()
    assert result["checkpoint"]["relative_path"].startswith("work/saved/MoleRec_")
    assert module.commands == commands_before
    assert not (run_root / "test.log").exists()


def test_recovery_rejects_adaptation_identity_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path)
    module.parse_validation_metrics = lambda text: (_ for _ in ()).throw(
        ValueError("training log must contain validation Jaccard and DDI metrics")
    )
    run_root = tmp_path / "tampered-adaptation"
    with pytest.raises(ValueError, match="validation Jaccard"):
        run_training_lane_v2(
            module=module,
            profile=module.profile,
            upstream_root=upstream,
            data_dir=data,
            run_root=run_root,
            python="python",
            learning_rate=1e-4,
            identity=IDENTITY,
            program_id="safedrug-archived",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )
    adaptation_path = run_root / "adaptation.json"
    adaptation = json.loads(adaptation_path.read_text(encoding="utf-8"))
    adaptation["adapted_sha256"] = "0" * 64
    adaptation_path.write_text(json.dumps(adaptation), encoding="utf-8")
    monkeypatch.setitem(sys.modules, "dill", pickle)

    with pytest.raises(ValueError, match="does not match the adapted entrypoint"):
        recover_training_lane_v2(
            module=module,
            profile=module.profile,
            data_dir=data,
            run_root=run_root,
            recovery_id="tampered-adaptation",
            finalizer_revision="e" * 40,
            identity=IDENTITY,
            program_id="safedrug-archived",
            source_revision="b" * 40,
            gate_inputs=(),
            error_type=ValueError,
        )
    assert not (run_root / "recoveries").exists()


def test_smoke_lane_finalizes_non_evidence_without_test_artifact(tmp_path: Path) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path, mode="smoke")
    identity = {**IDENTITY, "mode": "smoke"}
    run_root = tmp_path / "smoke"

    run_smoke_lane_v2(
        module=module,
        profile=module.profile,
        upstream_root=upstream,
        data_dir=data,
        run_root=run_root,
        python="python",
        learning_rate=1e-4,
        identity=identity,
        program_id="safedrug-archived",
        source_revision="b" * 40,
        gate_inputs=(),
        error_type=ValueError,
    )

    status, result = reopen_v2_pair(run_root, expected_identity=identity, error_type=ValueError)
    assert status["non_evidence"] is True
    assert result["non_evidence"] is True
    assert result["artifact_type"] == "smoke"
    assert not (run_root / "test.log").exists()


def test_profile_training_args_are_appended_to_smoke_command(tmp_path: Path) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path, mode="smoke")
    module.profile.training_args = ("--embedding",)
    identity = {**IDENTITY, "mode": "smoke"}

    run_smoke_lane_v2(
        module=module,
        profile=module.profile,
        upstream_root=upstream,
        data_dir=data,
        run_root=tmp_path / "smoke-with-args",
        python="python",
        learning_rate=1e-4,
        identity=identity,
        program_id="safedrug-archived",
        source_revision="b" * 40,
        gate_inputs=(),
        error_type=ValueError,
    )

    assert module.commands[0][-1] == "--embedding"


def test_molerec_smoke_admits_checkpoint_from_archived_parent_saved_layout(
    tmp_path: Path,
) -> None:
    upstream, data = _roots(tmp_path)
    module = _module(tmp_path, mode="smoke")
    module.profile.baseline_id = "molerec"
    module.profile.model_name = "MoleRec"
    identity = {
        **IDENTITY,
        "lane_id": "molerec-embedding",
        "scientific_baseline_id": "molerec",
        "program_id": "molerec",
        "profile_id": "molerec-embedding",
        "mode": "smoke",
    }
    run_root = tmp_path / "molerec-smoke"

    run_smoke_lane_v2(
        module=module,
        profile=module.profile,
        upstream_root=upstream,
        data_dir=data,
        run_root=run_root,
        python="python",
        learning_rate=1e-4,
        identity=identity,
        program_id="molerec",
        source_revision="b" * 40,
        gate_inputs=(),
        error_type=ValueError,
    )

    assert (run_root / "work" / "saved" / f"MoleRec_{run_root.name}").is_dir()
    assert not (run_root / "work" / "src" / "saved").exists()
