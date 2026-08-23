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


def paper_values() -> tuple[list[list[None]], dict[str, object], list[list[int]], list[list[int]]]:
    records = [[None] * 2 for _ in range(6_349)] + [[None] * 2_297]
    vocabulary = {"med_voc": SimpleNamespace(idx2word=list(range(131)))}
    ddi = [[0] * 131 for _ in range(131)]
    pairs = ((row, column) for row in range(131) for column in range(row + 1, 131))
    for row, column in list(pairs)[:448]:
        ddi[row][column] = ddi[column][row] = 1
    ddi_mask = [[0] * 491 for _ in range(131)]
    return records, vocabulary, ddi, ddi_mask


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


def test_test_mode_default_rejects_ambiguous_source() -> None:
    with pytest.raises(adapter.ReproductionError, match="determine"):
        adapter.test_mode_default("no declaration")


def test_paper_dataset_counts_pass_exact_gate() -> None:
    counts = adapter.count_dataset(*paper_values())

    assert counts == adapter.EXPECTED_COUNTS
    adapter.require_paper_counts(counts)


def test_dataset_gate_uses_upper_triangle_and_rejects_count_drift() -> None:
    records, vocabulary, ddi, ddi_mask = paper_values()
    ddi[0][1] = ddi[1][0] = 0
    counts = adapter.count_dataset(records, vocabulary, ddi, ddi_mask)

    assert counts["ddi_pairs"] == 447
    with pytest.raises(adapter.ReproductionError, match="ddi_pairs"):
        adapter.require_paper_counts(counts)


def test_dataset_gate_rejects_matrix_shape_drift() -> None:
    records, vocabulary, ddi, ddi_mask = paper_values()

    with pytest.raises(adapter.ReproductionError, match="ddi_A_final shape"):
        adapter.count_dataset(records, vocabulary, ddi[:-1], ddi_mask)
    with pytest.raises(adapter.ReproductionError, match="ddi_mask_H rows"):
        adapter.count_dataset(records, vocabulary, ddi, ddi_mask[:-1])


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
