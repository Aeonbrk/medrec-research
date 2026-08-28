from __future__ import annotations

import hashlib
import json
import pickle
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from baselines import molerec_runner, safedrug_archived_runner
from baselines.reproduction_artifacts import reopen_recovered_v2_pair, reopen_v2_pair
from baselines.reproduction_runner import (
    recover_training_lane_v2,
    run_smoke_lane_v2,
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
    assert not (run_root / "test.log").exists()


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
