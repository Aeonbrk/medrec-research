from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from medrec_research.cli import main
from medrec_research.reproduction_audit import (
    ARCHIVED_SOURCE_REVISION,
    EXPECTED_DATASET_COUNTS,
    REQUIRED_MOLEREC_BASELINES,
    SUMMARY_METRICS,
    audit_molerec_table1,
    load_molerec_table1_reference,
)

PROJECT_ROOT = Path(__file__).parents[2]
MOLEREC_REF_PATH = (
    PROJECT_ROOT / "research" / "baseline-preflight" / "molerec-table1-reference.json"
)
TEST_ENV_SHA = "c" * 64
TEST_HARNESS_SHA = "a" * 64
TEST_PREPROC_SHA = "c7218d0976e5ee5588aeaf5bdbc86b338126bba5"


def make_valid_ledger(
    *,
    harness_revision: str = TEST_HARNESS_SHA,
    preprocessing_revision: str = TEST_PREPROC_SHA,
    archived_model_revision: str = ARCHIVED_SOURCE_REVISION,
    environment_sha256: str = TEST_ENV_SHA,
    snapshot_subdirectory: str = "snapshots/safedrug-paper-c721-ijcai21",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "safedrug_archived_formal_reproduction_state",
        "attempt": {
            "formal_id": "formal-20260826-molerec-test",
            "state": "audit_ready",
        },
        "authorities": {
            "harness_revision": harness_revision,
            "preprocessing_revision": preprocessing_revision,
            "archived_model_revision": archived_model_revision,
            "environment_sha256": environment_sha256,
            "snapshot_subdirectory": snapshot_subdirectory,
        },
    }


def make_valid_result(
    baseline_id: str,
    *,
    metrics_override: dict[str, float] | None = None,
    env_sha: str = TEST_ENV_SHA,
    counts_override: dict[str, int] | None = None,
) -> dict[str, Any]:
    ref = load_molerec_table1_reference(MOLEREC_REF_PATH)[baseline_id]
    summary: dict[str, dict[str, float]] = {}
    for metric in SUMMARY_METRICS:
        mean_val = ref[metric]["mean"]
        if metrics_override and metric in metrics_override:
            mean_val = metrics_override[metric]
        summary[metric] = {"mean": mean_val, "std": ref[metric]["std"]}

    return {
        "schema_version": 1,
        "baseline_id": baseline_id,
        "source_revision": ARCHIVED_SOURCE_REVISION,
        "dataset_counts": counts_override or EXPECTED_DATASET_COUNTS,
        "environment": {"conda_explicit_sha256": env_sha, "python": "3.8.16"},
        "adaptation": {"change": "adapted"},
        "checkpoint": {"best_epoch": 40, "sha256": "e" * 64, "size_bytes": 1024},
        "harness_summary": summary,
        "metrics": {m: summary[m]["mean"] for m in SUMMARY_METRICS},
        "status": {
            "schema_version": 1,
            "kind": "molerec_formal_status",
            "baseline_id": baseline_id,
            "state": "completed",
            "stage": "terminal",
        },
    }


def test_molerec_reference_loads_all_five_baselines_and_metrics() -> None:
    ref = load_molerec_table1_reference(MOLEREC_REF_PATH)
    assert set(ref.keys()) == set(REQUIRED_MOLEREC_BASELINES)
    for b in REQUIRED_MOLEREC_BASELINES:
        assert set(ref[b].keys()) == set(SUMMARY_METRICS)
        for m in SUMMARY_METRICS:
            assert ref[b][m]["std"] >= 0


def test_audit_molerec_table1_happy_path_completed_match(tmp_path: Path) -> None:
    ledger_file = tmp_path / "ledger.json"
    ledger_file.write_text(json.dumps(make_valid_ledger()), encoding="utf-8")

    result_files: dict[str, Path] = {}
    for b in REQUIRED_MOLEREC_BASELINES:
        res_file = tmp_path / f"{b}_result.json"
        res_file.write_text(json.dumps(make_valid_result(b)), encoding="utf-8")
        result_files[b] = res_file

    output_file = tmp_path / "audit_packet.json"
    packet = audit_molerec_table1(
        ledger_path=ledger_file,
        result_paths=result_files,
        output_path=output_file,
        reference_path=MOLEREC_REF_PATH,
    )

    assert packet["schema_version"] == 1
    assert packet["kind"] == "molerec_table1_audit"
    assert packet["verdict"] == "completed_match"
    assert packet["interval_checks_passed"] == 25
    assert packet["interval_checks_total"] == 25
    assert packet["relationship_checks_passed"] == 4
    assert packet["relationship_checks_total"] == 4
    assert output_file.is_file()


def test_audit_molerec_table1_mismatch_on_interval_failure(tmp_path: Path) -> None:
    ledger_file = tmp_path / "ledger.json"
    ledger_file.write_text(json.dumps(make_valid_ledger()), encoding="utf-8")

    result_files: dict[str, Path] = {}
    for b in REQUIRED_MOLEREC_BASELINES:
        res_file = tmp_path / f"{b}_result.json"
        if b == "molerec":
            # Set Jaccard far below interval
            res_file.write_text(
                json.dumps(make_valid_result(b, metrics_override={"jaccard": 0.20})),
                encoding="utf-8",
            )
        else:
            res_file.write_text(json.dumps(make_valid_result(b)), encoding="utf-8")
        result_files[b] = res_file

    output_file = tmp_path / "audit_packet.json"
    packet = audit_molerec_table1(
        ledger_path=ledger_file,
        result_paths=result_files,
        output_path=output_file,
        reference_path=MOLEREC_REF_PATH,
    )

    assert packet["verdict"] == "completed_mismatch"
    assert packet["interval_checks_passed"] < 25


def test_audit_molerec_table1_cli_invocation(tmp_path: Path) -> None:
    from tests.unit.test_molerec_reproduction_audit import _write_artifacts

    ledger_file, result_files, selection_file = _write_artifacts(tmp_path)

    output_file = tmp_path / "audit_packet.json"
    argv = [
        "audit-molerec-table1",
        "--ledger",
        str(ledger_file),
        "--retain-result",
        str(result_files["retain"]),
        "--leap-result",
        str(result_files["leap"]),
        "--gamenet-result",
        str(result_files["gamenet"]),
        "--safedrug-result",
        str(result_files["safedrug"]),
        "--molerec-result",
        str(result_files["molerec"]),
        "--selection",
        str(selection_file),
        "--output",
        str(output_file),
        "--reference",
        str(MOLEREC_REF_PATH),
    ]

    ret = main(argv)
    assert ret == 0
    assert output_file.is_file()
    packet = json.loads(output_file.read_text(encoding="utf-8"))
    assert packet["verdict"] == "completed_match"
