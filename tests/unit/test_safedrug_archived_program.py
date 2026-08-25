from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROGRAM_PATH = Path(__file__).parents[2] / "baselines" / "safedrug_archived.py"
SPEC = importlib.util.spec_from_file_location("safedrug_archived_program", PROGRAM_PATH)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


def paper_values() -> tuple[
    list[list[None]],
    dict[str, object],
    list[list[int]],
    list[list[int]],
    list[list[int]],
    dict[int, str],
]:
    records = [[None] * 2 for _ in range(6_349)] + [[None] * 2_297]
    vocabulary = {"med_voc": SimpleNamespace(idx2word=list(range(131)))}
    ddi = [[0] * 131 for _ in range(131)]
    pairs = ((row, column) for row in range(131) for column in range(row + 1, 131))
    for row, column in list(pairs)[:448]:
        ddi[row][column] = ddi[column][row] = 1
    ddi_mask = [[0] * 491 for _ in range(131)]
    ehr_adj = [[0] * 131 for _ in range(131)]
    idx2drug = {idx: "CC(=O)O" for idx in range(131)}
    return records, vocabulary, ddi, ddi_mask, ehr_adj, idx2drug


def test_profiles_match_archived_entrypoints_and_defaults() -> None:
    observed = {
        baseline_id: (profile.entrypoint, profile.model_name, profile.learning_rate)
        for baseline_id, profile in adapter.PROFILES.items()
    }
    assert observed == {
        "gamenet": ("GAMENet.py", "GAMENet", 1e-4),
        "safedrug": ("SafeDrug.py", "SafeDrug", 5e-4),
        "retain": ("Retain.py", "Retain", 5e-4),
        "leap-safedrug": ("Leap.py", "Leap", 5e-4),
    }
    assert adapter.PROFILES["safedrug"].required_inputs[-3:] == (
        "ehr_adj_final.pkl",
        "ddi_mask_H.pkl",
        "idx2drug.pkl",
    )


def test_training_mode_adaptation_is_exact_and_reversible() -> None:
    source = f"before\n{adapter.TEST_DECLARATION}\nafter\n"
    adapted = adapter.adapt_training_source(source)

    assert adapter.TEST_DECLARATION not in adapted
    assert adapted.count(adapter.TRAIN_DECLARATION) == 1
    assert adapted.replace(adapter.TRAIN_DECLARATION, adapter.TEST_DECLARATION) == source
    assert adapter.test_mode_default(source) is True
    assert adapter.test_mode_default(adapted) is False
    assert adapter.test_mode_default(f"{adapted}\n# --Test") is False


def test_epoch_adaptation_is_exact_and_reversible() -> None:
    source = f"def main():\n{adapter.EPOCH_FORMAL}    pass\n"
    adapted = adapter.adapt_epoch_source(source)

    assert adapter.EPOCH_FORMAL not in adapted
    assert adapted.count(adapter.EPOCH_SMOKE) == 1
    assert adapted.replace(adapter.EPOCH_SMOKE, adapter.EPOCH_FORMAL, 1) == source


def test_smoke_adaptation_composition_and_leap_fine_tune_preservation() -> None:
    leap_source = (
        "def fine_tune():\n"
        "    EPOCH = 100\n"
        "def main():\n"
        f"{adapter.TEST_DECLARATION}\n"
        f"{adapter.EPOCH_FORMAL}"
        "    pass\n"
    )
    smoke_adapted = adapter.adapt_smoke_source(leap_source)

    assert adapter.TEST_DECLARATION not in smoke_adapted
    assert adapter.TRAIN_DECLARATION in smoke_adapted
    assert adapter.EPOCH_FORMAL not in smoke_adapted
    assert adapter.EPOCH_SMOKE in smoke_adapted
    assert "    EPOCH = 100\n" in smoke_adapted

    reversed_source = smoke_adapted.replace(adapter.EPOCH_SMOKE, adapter.EPOCH_FORMAL, 1).replace(
        adapter.TRAIN_DECLARATION, adapter.TEST_DECLARATION
    )
    assert reversed_source == leap_source


@pytest.mark.parametrize(
    "source",
    [
        "no declaration",
        f"{adapter.TEST_DECLARATION}\n{adapter.TEST_DECLARATION}",
        adapter.TRAIN_DECLARATION,
    ],
)
def test_training_mode_adaptation_rejects_source_drift(source: str) -> None:
    with pytest.raises(adapter.ReproductionError, match="drifted"):
        adapter.adapt_training_source(source)


@pytest.mark.parametrize(
    "source",
    [
        "no epoch declaration",
        f"{adapter.EPOCH_FORMAL}{adapter.EPOCH_FORMAL}",
        adapter.EPOCH_SMOKE,
    ],
)
def test_epoch_adaptation_rejects_source_drift(source: str) -> None:
    with pytest.raises(adapter.ReproductionError, match="drifted"):
        adapter.adapt_epoch_source(source)


def test_test_mode_default_rejects_ambiguous_source() -> None:
    with pytest.raises(adapter.ReproductionError, match="determine"):
        adapter.test_mode_default("no declaration")


def test_paper_dataset_counts_pass_exact_gate() -> None:
    records, vocabulary, ddi, ddi_mask, _, _ = paper_values()
    counts = adapter.count_dataset(records, vocabulary, ddi, ddi_mask)

    assert counts == adapter.EXPECTED_COUNTS
    adapter.require_paper_counts(counts)


def test_dataset_gate_uses_upper_triangle_and_rejects_count_drift() -> None:
    records, vocabulary, ddi, ddi_mask, _, _ = paper_values()
    ddi[0][1] = ddi[1][0] = 0
    counts = adapter.count_dataset(records, vocabulary, ddi, ddi_mask)

    assert counts["ddi_pairs"] == 447
    with pytest.raises(adapter.ReproductionError, match="ddi_pairs"):
        adapter.require_paper_counts(counts)


def test_dataset_gate_rejects_matrix_shape_drift() -> None:
    records, vocabulary, ddi, ddi_mask, _, _ = paper_values()

    with pytest.raises(adapter.ReproductionError, match="ddi_A_final shape"):
        adapter.count_dataset(records, vocabulary, ddi[:-1], ddi_mask)
    with pytest.raises(adapter.ReproductionError, match="ddi_mask_H rows"):
        adapter.count_dataset(records, vocabulary, ddi, ddi_mask[:-1])


def test_load_and_validate_canonical_inputs_validates_all_six(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pickle

    monkeypatch.setattr(
        adapter.importlib,
        "import_module",
        lambda name: pickle if name == "dill" else sys.modules.get(name),
    )

    records, vocabulary, ddi, ddi_mask, ehr_adj, idx2drug = paper_values()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    for name, val in [
        ("records_final.pkl", records),
        ("voc_final.pkl", vocabulary),
        ("ddi_A_final.pkl", ddi),
        ("ddi_mask_H.pkl", ddi_mask),
        ("ehr_adj_final.pkl", ehr_adj),
        ("idx2drug.pkl", idx2drug),
    ]:
        with (data_dir / name).open("wb") as stream:
            pickle.dump(val, stream)

    results, counts = adapter.load_and_validate_canonical_inputs(data_dir)
    assert len(results) == 6
    assert all(status == "passed" for status in results.values())
    assert counts == adapter.EXPECTED_COUNTS


def test_load_and_validate_canonical_inputs_rejects_shape_or_length_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pickle

    monkeypatch.setattr(
        adapter.importlib,
        "import_module",
        lambda name: pickle if name == "dill" else sys.modules.get(name),
    )

    records, vocabulary, ddi, ddi_mask, ehr_adj, idx2drug = paper_values()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Wrong ehr_adj shape
    for name, val in [
        ("records_final.pkl", records),
        ("voc_final.pkl", vocabulary),
        ("ddi_A_final.pkl", ddi),
        ("ddi_mask_H.pkl", ddi_mask),
        ("ehr_adj_final.pkl", ehr_adj[:-1]),
        ("idx2drug.pkl", idx2drug),
    ]:
        with (data_dir / name).open("wb") as stream:
            pickle.dump(val, stream)

    with pytest.raises(adapter.ReproductionError, match="ehr_adj_final shape"):
        adapter.load_and_validate_canonical_inputs(data_dir)


def test_probe_environment_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "verify_upstream_source", lambda upstream: None)
    monkeypatch.setattr(
        adapter,
        "check_imports",
        lambda upstream: {m: "passed" for m in adapter.REGISTRY_IMPORT_MODULES},
    )
    monkeypatch.setattr(adapter, "check_cuda_tensor", lambda: "passed")
    monkeypatch.setattr(adapter, "check_rdkit_brics", lambda: "passed")
    monkeypatch.setattr(adapter, "check_dnc_forward", lambda: "passed")
    monkeypatch.setattr(
        adapter,
        "probe_environment_details",
        lambda: {
            "conda_explicit_sha256": "f" * 64,
            "python": "3.11.9",
            "pytorch": "2.2.2",
            "torch_cuda": "12.1",
            "nvidia_driver": "535.183.01",
            "numpy": "1.26.4",
            "pandas": "2.0.3",
            "scipy": "1.11.4",
            "scikit_learn": "1.3.2",
            "rdkit": "2023.09.6",
            "dill": "0.3.7",
            "dnc": "1.1.0",
            "cuda_visible_device_count": 1,
            "gpu_name": "NVIDIA GeForce RTX 3090",
            "gpu_capability": "8.6",
        },
    )

    probe = adapter.run_probe(
        baseline_id="gamenet",
        upstream_root=tmp_path / "upstream",
        data_dir=None,
        scope="environment",
    )

    assert probe["schema_version"] == 1
    assert probe["kind"] == "safedrug_archived_probe"
    assert probe["scope"] == "environment"
    assert probe["baseline_id"] == "gamenet"
    assert probe["source_revision"] == adapter.ARCHIVED_REVISION
    assert probe["checks"]["cuda_tensor"] == "passed"
    assert probe["inputs"] is None
    assert probe["dataset_counts"] is None


def test_probe_full_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "verify_upstream_source", lambda upstream: None)
    monkeypatch.setattr(
        adapter,
        "check_imports",
        lambda upstream: {m: "passed" for m in adapter.REGISTRY_IMPORT_MODULES},
    )
    monkeypatch.setattr(adapter, "check_cuda_tensor", lambda: "passed")
    monkeypatch.setattr(adapter, "check_rdkit_brics", lambda: "passed")
    monkeypatch.setattr(adapter, "check_dnc_forward", lambda: "passed")
    monkeypatch.setattr(
        adapter,
        "probe_environment_details",
        lambda: {
            "conda_explicit_sha256": "f" * 64,
            "python": "3.11.9",
            "pytorch": "2.2.2",
            "torch_cuda": "12.1",
            "nvidia_driver": "535.183.01",
            "numpy": "1.26.4",
            "pandas": "2.0.3",
            "scipy": "1.11.4",
            "scikit_learn": "1.3.2",
            "rdkit": "2023.09.6",
            "dill": "0.3.7",
            "dnc": "1.1.0",
            "cuda_visible_device_count": 1,
            "gpu_name": "NVIDIA GeForce RTX 3090",
            "gpu_capability": "8.6",
        },
    )
    monkeypatch.setattr(
        adapter,
        "load_and_validate_canonical_inputs",
        lambda d: (
            {name: "passed" for name in adapter.CANONICAL_SIX_INPUTS},
            adapter.EXPECTED_COUNTS,
        ),
    )

    probe = adapter.run_probe(
        baseline_id="safedrug",
        upstream_root=tmp_path / "upstream",
        data_dir=tmp_path / "data",
        scope="full",
    )

    assert probe["schema_version"] == 1
    assert probe["scope"] == "full"
    assert len(probe["inputs"]) == 6
    assert probe["dataset_counts"] == adapter.EXPECTED_COUNTS


def test_smoke_lane_executes_one_epoch_and_emits_smoke_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = tmp_path / "upstream"
    upstream_src = upstream / "src"
    upstream_src.mkdir(parents=True)
    entrypoint = upstream_src / "SafeDrug.py"
    entrypoint.write_text(
        f"import sys\n{adapter.TEST_DECLARATION}\ndef main():\n{adapter.EPOCH_FORMAL}    pass\n",
        encoding="utf-8",
    )

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in adapter.CANONICAL_SIX_INPUTS:
        (data_dir / name).touch()

    run_root = tmp_path / "runs" / "smoke_run"

    monkeypatch.setattr(adapter, "verify_upstream_source", lambda root: None)
    monkeypatch.setattr(
        adapter,
        "load_and_validate_canonical_inputs",
        lambda d: (
            {name: "passed" for name in adapter.CANONICAL_SIX_INPUTS},
            adapter.EXPECTED_COUNTS,
        ),
    )
    monkeypatch.setattr(
        adapter,
        "environment_summary",
        lambda: {"conda_explicit_sha256": "f" * 64, "python": "3.11.9"},
    )

    def mock_run_logged(cmd: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
        log_path.write_text("epoch 1 -------------------\nbest_epoch: 0\n", encoding="utf-8")
        checkpoint_dir = cwd / "saved" / f"SafeDrug_{run_root.name}"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        (checkpoint_dir / "Epoch_0_TARGET_0.0_JA_0.5000_DDI_0.0800.model").touch()

    monkeypatch.setattr(adapter, "run_logged", mock_run_logged)

    adapter.run_smoke_lane(
        profile=adapter.PROFILES["safedrug"],
        upstream_root=upstream,
        data_dir=data_dir,
        run_root=run_root,
        python="python",
    )

    assert not (run_root / "test.log").exists()
    assert not (run_root / "result.json").exists()

    status = json.loads((run_root / "status.json").read_text())
    assert status["schema_version"] == 1
    assert status["kind"] == "safedrug_archived_smoke_status"
    assert status["state"] == "completed"
    assert status["stage"] == "terminal"

    smoke = json.loads((run_root / "smoke.json").read_text())
    assert smoke["schema_version"] == 1
    assert smoke["kind"] == "safedrug_archived_smoke"
    assert smoke["non_evidence"] is True
    assert smoke["baseline_id"] == "safedrug"
    assert smoke["epochs_requested"] == 1
    assert smoke["epochs_observed"] == 1
    assert smoke["best_epoch"] == 0
    assert smoke["checkpoint"]["epoch"] == 0
    assert "Epoch_0" in smoke["checkpoint"]["artifact_id"]


def test_training_and_test_commands_preserve_archived_cli_behavior(tmp_path: Path) -> None:
    entrypoint = tmp_path / "work" / "SafeDrug.py"
    original = tmp_path / "upstream" / "src" / "SafeDrug.py"
    checkpoint = tmp_path / "work" / "saved" / "SafeDrug_run" / "Epoch_49.model"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.touch()

    assert adapter.training_command("python", entrypoint, "SafeDrug_run") == [
        "python",
        str(entrypoint),
        "--model_name",
        "SafeDrug_run",
    ]
    assert adapter.test_command(
        "python", original, adapter.PROFILES["safedrug"], "SafeDrug_run", checkpoint
    )[-3:] == ["--Test", "--resume_path", str(checkpoint.resolve())]
    assert (
        adapter.test_command(
            "python", original, adapter.PROFILES["retain"], "Retain_run", checkpoint
        )[-1]
        == checkpoint.name
    )


def test_checkpoint_selection_uses_zero_based_best_epoch(tmp_path: Path) -> None:
    checkpoint = tmp_path / "Epoch_49_JA_0.5000_DDI_0.0800.model"
    checkpoint.touch()

    assert adapter.select_checkpoint(tmp_path, adapter.PROFILES["gamenet"], 49) == checkpoint


def test_environment_summary_records_conda_and_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = SimpleNamespace(stdout=b"explicit lock\n")
    monkeypatch.setattr(adapter.subprocess, "run", lambda *args, **kwargs: completed)

    summary = adapter.environment_summary()

    assert len(summary["conda_explicit_sha256"]) == 64
    assert summary["python"] == sys.version.split()[0]


def test_test_log_requires_ten_rounds_and_matching_upstream_summary() -> None:
    metric_line = (
        "DDI Rate: 0.1, Jaccard: 0.2, PRAUC: 0.3, AVG_PRC: 0.4, "
        "AVG_RECALL: 0.5, AVG_F1: 0.6, AVG_MED: 7.0"
    )
    summary_line = (
        "0.1000 $\\pm$ 0.0000 & 0.2000 $\\pm$ 0.0000 & "
        "0.6000 $\\pm$ 0.0000 & 0.3000 $\\pm$ 0.0000 & 7.0000 $\\pm$ 0.0000 &"
    )

    parsed = adapter.parse_test_log("\n".join([metric_line] * 10 + [summary_line]))

    assert len(parsed["test_rounds"]) == 10
    assert parsed["harness_summary"]["avg_f1"]["mean"] == pytest.approx(0.6)
    with pytest.raises(adapter.ReproductionError, match="disagrees"):
        adapter.parse_test_log(
            "\n".join([metric_line] * 10 + [summary_line.replace("0.1000", "0.2000", 1)])
        )


def test_test_log_comparison_respects_upstream_significant_digit_precision() -> None:
    metric_line = (
        "DDI Rate: 0.1, Jaccard: 0.2, PRAUC: 0.3, AVG_PRC: 0.4, "
        "AVG_RECALL: 0.5, AVG_F1: 0.6, AVG_MED: 20.58"
    )
    summary_line = (
        "0.1000 $\\pm$ 0.0000 & 0.2000 $\\pm$ 0.0000 & "
        "0.6000 $\\pm$ 0.0000 & 0.3000 $\\pm$ 0.0000 & 20.5825 $\\pm$ 0.0000 &"
    )

    adapter.parse_test_log("\n".join([metric_line] * 10 + [summary_line]))


def test_terminal_status_is_written_before_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Path] = []
    original_write_json = adapter.write_json

    def recording_write(path: Path, value: dict[str, object]) -> None:
        calls.append(path)
        original_write_json(path, value)

    monkeypatch.setattr(adapter, "write_json", recording_write)
    status = {"state": "completed", "stage": "terminal"}
    adapter.finalize_result(tmp_path, status, {"schema_version": 1})

    assert [path.name for path in calls] == ["status.json", "result.json"]
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["status"] == status
