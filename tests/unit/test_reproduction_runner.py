from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from baselines import molerec_runner, safedrug_archived_runner
from baselines.reproduction_artifacts import reopen_v2_pair
from baselines.reproduction_runner import run_smoke_lane_v2, run_training_lane_v2

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
        (checkpoint_dir / "checkpoint.model").write_bytes(b"checkpoint")

    def select_checkpoint(checkpoint_dir: Path, selected_profile: object, best_epoch: int) -> Path:
        del selected_profile, best_epoch
        return checkpoint_dir / "checkpoint.model"

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
