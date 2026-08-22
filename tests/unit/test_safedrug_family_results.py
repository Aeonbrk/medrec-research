"""Unit tests for SafeDrug family log parser and result generator."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "baselines" / "scripts"))

from parse_safedrug_family_results import (  # noqa: E402
    ResultValidationError,
    build_result,
    compute_sha256,
    parse_test_log,
    parse_train_log,
    select_checkpoint,
)


def _generate_synthetic_train_log(num_epochs: int = 50, best_epoch: int = 17) -> str:
    lines = []
    current_best = 0
    for ep in range(1, num_epochs + 1):
        lines.append(f"epoch {ep} --------------------------")
        lines.append(f"Train loss: 0.{ep:02d}12")
        if ep == best_epoch or (ep <= best_epoch and ep % 5 == 0):
            current_best = ep
        lines.append(f"best_epoch: {current_best}")
    return "\n".join(lines)


def _generate_synthetic_test_log(
    num_rounds: int = 10,
    include_summary: bool = True,
    summary_count: int = 1,
) -> str:
    lines = []
    for r in range(num_rounds):
        lines.append(
            f"DDI Rate: 0.07{r:02d}, Jaccard: 0.51{r:02d},  PRAUC: 0.74{r:02d}, "
            f"AVG_PRC: 0.65{r:02d}, AVG_RECALL: 0.62{r:02d}, AVG_F1: 0.64{r:02d}, AVG_MED: 18.2{r:02d}"
        )
    if include_summary:
        for _ in range(summary_count):
            lines.append(
                "0.0745 $\\pm$ 0.0028 & 0.5145 $\\pm$ 0.0028 & 0.6445 $\\pm$ 0.0028 & "
                "0.7445 $\\pm$ 0.0028 & 18.2450 $\\pm$ 0.0280 & "
            )
        lines.append("test time: 42.123")
    return "\n".join(lines)


def test_parse_train_log_valid():
    log = _generate_synthetic_train_log(50, best_epoch=23)
    res = parse_train_log(log)
    assert res["epochs_expected"] == 50
    assert res["epochs_completed"] == 50
    assert res["best_epoch"] == 23


def test_parse_train_log_incomplete_epochs():
    log = _generate_synthetic_train_log(49, best_epoch=23)
    with pytest.raises(ResultValidationError, match="Training log incomplete"):
        parse_train_log(log)


def test_parse_train_log_zero_best_epoch():
    log = _generate_synthetic_train_log(50, best_epoch=0)
    with pytest.raises(ResultValidationError, match="best_epoch must be > 0"):
        parse_train_log(log)


def test_parse_train_log_no_epoch_headers():
    with pytest.raises(ResultValidationError, match="Training log contains no epoch headers"):
        parse_train_log("some random output without headers")


def test_select_checkpoint_safedrug(tmp_path: Path):
    model_name = "SafeDrug_test_run"
    ckpt_dir = tmp_path / "saved"
    ckpt_dir.mkdir()

    # Create matching and non-matching checkpoints
    target_ckpt = ckpt_dir / "Epoch_17_TARGET_0.06_JA_0.5200_DDI_0.0700.model"
    target_ckpt.write_text("model_bytes_17")

    other_ckpt = ckpt_dir / "Epoch_16_TARGET_0.06_JA_0.5100_DDI_0.0710.model"
    other_ckpt.write_text("model_bytes_16")

    res = select_checkpoint(ckpt_dir, best_epoch=17, profile="safedrug", model_name=model_name)
    assert res["basename"] == target_ckpt.name
    assert res["best_epoch"] == 17
    assert res["relative_path"] == f"saved/{model_name}/{target_ckpt.name}"
    assert res["sha256"] == compute_sha256(target_ckpt)


def test_select_checkpoint_delimiter_anchoring(tmp_path: Path):
    """Ensure epoch 1 does not match epoch 10-19."""
    model_name = "Retain_test_run"
    ckpt_dir = tmp_path / "saved"
    ckpt_dir.mkdir()

    epoch_10 = ckpt_dir / "Epoch_10_JA_0.4500_DDI_0.0750.model"
    epoch_10.write_text("model_10")
    epoch_19 = ckpt_dir / "Epoch_19_JA_0.4600_DDI_0.0740.model"
    epoch_19.write_text("model_19")

    # Search for epoch 1 when only epoch 10 and 19 exist -> should fail with no match
    with pytest.raises(ResultValidationError, match="No checkpoint found"):
        select_checkpoint(ckpt_dir, best_epoch=1, profile="retain", model_name=model_name)

    # Now add epoch 1
    epoch_1 = ckpt_dir / "Epoch_1_JA_0.4000_DDI_0.0800.model"
    epoch_1.write_text("model_1")

    res = select_checkpoint(ckpt_dir, best_epoch=1, profile="retain", model_name=model_name)
    assert res["basename"] == epoch_1.name


def test_select_checkpoint_multiple_matches_error(tmp_path: Path):
    model_name = "Leap_test_run"
    ckpt_dir = tmp_path / "saved"
    ckpt_dir.mkdir()

    ckpt_a = ckpt_dir / "Epoch_5_JA_0.4100_DDI_0.0700.model"
    ckpt_a.write_text("model_a")
    ckpt_b = ckpt_dir / "Epoch_5_JA_0.4200_DDI_0.0710.model"
    ckpt_b.write_text("model_b")

    with pytest.raises(ResultValidationError, match="Multiple checkpoints found"):
        select_checkpoint(ckpt_dir, best_epoch=5, profile="leap-safedrug", model_name=model_name)


def test_parse_test_log_valid():
    log = _generate_synthetic_test_log(10)
    res = parse_test_log(log)

    assert len(res["test_rounds"]) == 10
    for r in res["test_rounds"]:
        assert set(r.keys()) == {
            "ddi_rate",
            "jaccard",
            "prauc",
            "avg_precision",
            "avg_recall",
            "avg_f1",
            "avg_medications",
        }
        for v in r.values():
            assert math.isfinite(v)

    # Check harness summary
    h_sum = res["harness_summary"]
    assert len(h_sum) == 7
    for k in [
        "ddi_rate",
        "jaccard",
        "prauc",
        "avg_precision",
        "avg_recall",
        "avg_f1",
        "avg_medications",
    ]:
        assert "mean" in h_sum[k]
        assert "std" in h_sum[k]
        assert math.isfinite(h_sum[k]["mean"])
        assert math.isfinite(h_sum[k]["std"])

    # Check upstream summary
    up_sum = res["upstream_summary"]
    assert "raw_line" in up_sum
    assert len(up_sum["metrics"]) == 5
    assert set(up_sum["metrics"].keys()) == {
        "ddi_rate",
        "jaccard",
        "avg_f1",
        "prauc",
        "avg_medications",
    }


def test_parse_test_log_fewer_rounds():
    log = _generate_synthetic_test_log(9)
    with pytest.raises(ResultValidationError, match="Expected exactly 10 Test rounds, observed 9"):
        parse_test_log(log)


def test_parse_test_log_more_rounds():
    log = _generate_synthetic_test_log(11)
    with pytest.raises(ResultValidationError, match="Expected exactly 10 Test rounds, observed 11"):
        parse_test_log(log)


def test_parse_test_log_missing_summary():
    log = _generate_synthetic_test_log(10, include_summary=False)
    with pytest.raises(ResultValidationError, match="No upstream 5-metric summary line"):
        parse_test_log(log)


def test_parse_test_log_multiple_summaries():
    log = _generate_synthetic_test_log(10, include_summary=True, summary_count=2)
    with pytest.raises(ResultValidationError, match=r"Multiple .* upstream summary lines"):
        parse_test_log(log)


def test_build_result_schema(tmp_path: Path):
    status_data = {
        "schema_version": 1,
        "baseline_id": "safedrug",
        "run_id": "run123",
        "attempt": 1,
        "model_name": "SafeDrug_run123",
        "state": "completed",
        "stage": "terminal",
        "exit_code": 0,
        "started_at": "2026-08-22T10:00:00Z",
        "training_started_at": "2026-08-22T10:01:00Z",
        "training_ended_at": "2026-08-22T11:00:00Z",
        "finished_at": "2026-08-22T11:05:00Z",
        "physical_gpu": 0,
        "logical_cuda_device": 0,
    }
    input_sha256 = {
        "data/output/records_final.pkl": "a" * 64,
        "data/output/voc_final.pkl": "b" * 64,
        "data/output/ddi_A_final.pkl": "c" * 64,
        "data/output/ddi_mask_H.pkl": "d" * 64,
        "data/output/atc3toSMILES.pkl": "e" * 64,
    }
    training_data = {
        "epochs_expected": 50,
        "epochs_completed": 50,
        "best_epoch": 17,
    }
    checkpoint_data = {
        "relative_path": "saved/SafeDrug_run123/Epoch_17_TARGET_0.06_JA_0.52_DDI_0.07.model",
        "sha256": "f" * 64,
        "size_bytes": 10240,
        "best_epoch": 17,
    }
    test_data = parse_test_log(_generate_synthetic_test_log(10))

    result = build_result(
        baseline_id="safedrug",
        status_data=status_data,
        source_revision="1" * 40,
        adapter_revision="sha256:" + "2" * 64,
        environment_sha256="3" * 64,
        input_sha256=input_sha256,
        training_data=training_data,
        checkpoint_data=checkpoint_data,
        test_data=test_data,
    )

    assert result["schema_version"] == 1
    assert result["baseline_id"] == "safedrug"
    assert result["training"]["best_epoch"] == 17
    assert len(result["test_rounds"]) == 10
    assert result["checkpoint"]["size_bytes"] == 10240


def test_cli_parser_execution(tmp_path: Path):
    train_log = tmp_path / "train.log"
    train_log.write_text(_generate_synthetic_train_log(50, best_epoch=12))

    test_log = tmp_path / "test.log"
    test_log.write_text(_generate_synthetic_test_log(10))

    ckpt_dir = tmp_path / "saved"
    ckpt_dir.mkdir()
    ckpt_file = ckpt_dir / "Epoch_12_TARGET_0.06_JA_0.5211_DDI_0.0711.model"
    ckpt_file.write_text("fake_model_data")

    status_file = tmp_path / "status.json"
    status_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "baseline_id": "safedrug",
                "run_id": "run_test_cli",
                "attempt": 1,
                "model_name": "SafeDrug_run_test_cli",
                "state": "running",
                "stage": "parsing",
                "exit_code": None,
                "started_at": "2026-08-22T10:00:00Z",
                "training_started_at": "2026-08-22T10:01:00Z",
                "training_ended_at": "2026-08-22T11:00:00Z",
                "finished_at": None,
                "physical_gpu": 1,
                "logical_cuda_device": 0,
            }
        )
    )

    input_hashes_file = tmp_path / "input_hashes.json"
    input_hashes_file.write_text(json.dumps({"data/output/records_final.pkl": "a" * 64}))

    output_json = tmp_path / "result.json"

    script_path = Path("baselines/scripts/parse_safedrug_family_results.py").resolve()
    cmd = [
        sys.executable,
        str(script_path),
        "--baseline-id",
        "safedrug",
        "--model-name",
        "SafeDrug_run_test_cli",
        "--train-log",
        str(train_log),
        "--test-log",
        str(test_log),
        "--status-json",
        str(status_file),
        "--checkpoint-dir",
        str(ckpt_dir),
        "--output-json",
        str(output_json),
        "--source-revision",
        "88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a",
        "--adapter-revision",
        "sha256:" + "0" * 64,
        "--environment-sha256",
        "971ad2bfd7309cd3d7af4aae26187ad4e00bc806ad3714188e854c657f5b45fe",
        "--input-hashes-json",
        str(input_hashes_file),
    ]

    completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert completed.returncode == 0
    assert output_json.exists()

    result_data = json.loads(output_json.read_text())
    assert result_data["training"]["best_epoch"] == 12
    assert (
        result_data["checkpoint"]["basename"] == ckpt_file.name
        if "basename" in result_data["checkpoint"]
        else True
    )
