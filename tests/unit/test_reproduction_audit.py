from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from medrec_research import ProtocolValidationError
from medrec_research.reproduction_audit import (
    ARCHIVED_SOURCE_REVISION,
    EXPECTED_DATASET_COUNTS,
    REQUIRED_BASELINES,
    SUMMARY_METRICS,
    audit_safedrug_table2,
    load_table2_reference,
)

PROJECT_ROOT = Path(__file__).parents[2]
REFERENCE_PATH = PROJECT_ROOT / "research" / "baseline-preflight" / "safedrug-table2-reference.json"
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
            "formal_id": "formal-20260825-test",
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
    source_rev: str = ARCHIVED_SOURCE_REVISION,
    counts_override: dict[str, int] | None = None,
    rounds_count: int = 10,
    status_state: str = "completed",
) -> dict[str, Any]:
    ref = load_table2_reference(REFERENCE_PATH)[baseline_id]
    summary: dict[str, dict[str, float]] = {}
    for metric in SUMMARY_METRICS:
        mean_val = ref[metric]["mean"]
        if metrics_override and metric in metrics_override:
            mean_val = metrics_override[metric]
        summary[metric] = {"mean": mean_val, "std": ref[metric]["std"]}

    rounds: list[dict[str, float]] = []
    for _ in range(rounds_count):
        rounds.append({m: summary[m]["mean"] for m in SUMMARY_METRICS})

    return {
        "schema_version": 1,
        "baseline_id": baseline_id,
        "source_revision": source_rev,
        "dataset_counts": counts_override or EXPECTED_DATASET_COUNTS,
        "environment": {"conda_explicit_sha256": env_sha, "python": "3.11.9"},
        "adaptation": {"change": "adapted"},
        "checkpoint": {"best_epoch": 40, "sha256": "e" * 64, "size_bytes": 1024},
        "test_rounds": rounds,
        "harness_summary": summary,
        "upstream_summary": summary,
        "status": {"state": status_state, "stage": "terminal"},
    }


def test_reference_file_loads_and_has_all_baselines_and_metrics() -> None:
    ref = load_table2_reference(REFERENCE_PATH)
    assert set(ref.keys()) == set(REQUIRED_BASELINES)
    for b in REQUIRED_BASELINES:
        assert set(ref[b].keys()) == set(SUMMARY_METRICS)
        for m in SUMMARY_METRICS:
            assert ref[b][m]["std"] >= 0


def test_audit_happy_path_all_match(tmp_path: Path) -> None:
    ledger_file = tmp_path / "state.json"
    ledger_file.write_text(json.dumps(make_valid_ledger()))

    result_paths: dict[str, Path] = {}
    for b in REQUIRED_BASELINES:
        p = tmp_path / f"result_{b}.json"
        p.write_text(json.dumps(make_valid_result(b)))
        result_paths[b] = p

    out_file = tmp_path / "table2-audit.json"
    packet = audit_safedrug_table2(
        ledger_path=ledger_file,
        result_paths=result_paths,
        output_path=out_file,
        reference_path=REFERENCE_PATH,
    )

    assert packet["schema_version"] == 1
    assert packet["kind"] == "safedrug_table2_audit"
    assert packet["verdict"] == "completed_match"
    assert packet["interval_checks_passed"] == 20
    assert packet["relationship_checks_passed"] == 3
    assert out_file.exists()


def test_audit_boundary_inclusive_pass(tmp_path: Path) -> None:
    ref = load_table2_reference(REFERENCE_PATH)
    # Set safedrug jaccard exactly to upper bound (mean + 2*std)
    target = ref["safedrug"]["jaccard"]
    upper = target["mean"] + 2.0 * target["std"]

    ledger_file = tmp_path / "state.json"
    ledger_file.write_text(json.dumps(make_valid_ledger()))

    result_paths: dict[str, Path] = {}
    for b in REQUIRED_BASELINES:
        override = {"jaccard": upper} if b == "safedrug" else None
        p = tmp_path / f"result_{b}.json"
        p.write_text(json.dumps(make_valid_result(b, metrics_override=override)))
        result_paths[b] = p

    out_file = tmp_path / "table2-audit.json"
    packet = audit_safedrug_table2(
        ledger_path=ledger_file,
        result_paths=result_paths,
        output_path=out_file,
        reference_path=REFERENCE_PATH,
    )
    assert packet["verdict"] == "completed_match"
    assert packet["interval_checks_passed"] == 20


def test_audit_mismatch_path(tmp_path: Path) -> None:
    ref = load_table2_reference(REFERENCE_PATH)
    # Set retain DDI rate far outside interval
    target = ref["retain"]["ddi_rate"]
    outside_val = target["mean"] + 5.0 * target["std"]

    ledger_file = tmp_path / "state.json"
    ledger_file.write_text(json.dumps(make_valid_ledger()))

    result_paths: dict[str, Path] = {}
    for b in REQUIRED_BASELINES:
        override = {"ddi_rate": outside_val} if b == "retain" else None
        p = tmp_path / f"result_{b}.json"
        p.write_text(json.dumps(make_valid_result(b, metrics_override=override)))
        result_paths[b] = p

    out_file = tmp_path / "table2-audit.json"
    packet = audit_safedrug_table2(
        ledger_path=ledger_file,
        result_paths=result_paths,
        output_path=out_file,
        reference_path=REFERENCE_PATH,
    )
    assert packet["verdict"] == "completed_mismatch"
    assert packet["interval_checks_passed"] == 19
    failed_check = next(c for c in packet["checks"]["intervals"] if not c["passed"])
    assert failed_check["baseline_id"] == "retain"
    assert failed_check["metric"] == "ddi_rate"
    assert failed_check["observed_mean"] == pytest.approx(outside_val)


def test_audit_relationship_failure(tmp_path: Path) -> None:
    # Set safedrug Jaccard lower than GAMENet Jaccard, while both within individual intervals
    # safedrug target is 0.5213 +- 2*0.0030 = [0.5153, 0.5273]
    # gamenet target is 0.5067 +- 2*0.0025 = [0.5017, 0.5117]
    # If safedrug is 0.5155 and gamenet is 0.5110 -> rel1 still passes.
    # But if gamenet is 0.5115 and safedrug is 0.5110 (which is outside interval),
    # Let's say safedrug jaccard = 0.5050 (fails interval and relationship)
    # Or let's test DDI: SafeDrug DDI < LEAP DDI.
    # safedrug DDI target: 0.0589 +- 0.0010. leap DDI target: 0.0731 +- 0.0016.
    # If safedrug DDI = 0.0600 and leap DDI = 0.0590 (within leap interval [0.0715, 0.0747] is false),
    # If safedrug DDI = 0.0740, rel3 fails.
    ledger_file = tmp_path / "state.json"
    ledger_file.write_text(json.dumps(make_valid_ledger()))

    result_paths: dict[str, Path] = {}
    for b in REQUIRED_BASELINES:
        override = {"ddi_rate": 0.0800} if b == "safedrug" else None
        p = tmp_path / f"result_{b}.json"
        p.write_text(json.dumps(make_valid_result(b, metrics_override=override)))
        result_paths[b] = p

    out_file = tmp_path / "table2-audit.json"
    packet = audit_safedrug_table2(
        ledger_path=ledger_file,
        result_paths=result_paths,
        output_path=out_file,
        reference_path=REFERENCE_PATH,
    )
    assert packet["verdict"] == "completed_mismatch"
    rel3 = next(r for r in packet["checks"]["relationships"] if r["relationship_id"] == 3)
    assert rel3["passed"] is False


@pytest.mark.parametrize(
    ("corrupt_key", "corrupt_value", "err_match"),
    [
        ("source_revision", "bad_rev", "source_revision"),
        ("status", {"state": "failed", "stage": "terminal"}, "state 'completed'"),
        ("test_rounds", [], "test_rounds"),
    ],
)
def test_audit_rejects_corrupted_result_files(
    tmp_path: Path, corrupt_key: str, corrupt_value: Any, err_match: str
) -> None:
    ledger_file = tmp_path / "state.json"
    ledger_file.write_text(json.dumps(make_valid_ledger()))

    result_paths: dict[str, Path] = {}
    for b in REQUIRED_BASELINES:
        res = make_valid_result(b)
        if b == "safedrug":
            res[corrupt_key] = corrupt_value
        p = tmp_path / f"result_{b}.json"
        p.write_text(json.dumps(res))
        result_paths[b] = p

    out_file = tmp_path / "table2-audit.json"
    with pytest.raises(ProtocolValidationError, match=err_match):
        audit_safedrug_table2(
            ledger_path=ledger_file,
            result_paths=result_paths,
            output_path=out_file,
            reference_path=REFERENCE_PATH,
        )


def test_audit_rejects_environment_mismatch(tmp_path: Path) -> None:
    ledger_file = tmp_path / "state.json"
    ledger_file.write_text(json.dumps(make_valid_ledger()))

    result_paths: dict[str, Path] = {}
    for b in REQUIRED_BASELINES:
        res = make_valid_result(b, env_sha="f" * 64 if b == "safedrug" else TEST_ENV_SHA)
        p = tmp_path / f"result_{b}.json"
        p.write_text(json.dumps(res))
        result_paths[b] = p

    out_file = tmp_path / "table2-audit.json"
    with pytest.raises(ProtocolValidationError, match="environment sha256"):
        audit_safedrug_table2(
            ledger_path=ledger_file,
            result_paths=result_paths,
            output_path=out_file,
            reference_path=REFERENCE_PATH,
        )


def test_audit_output_preserves_privacy_allowlist(tmp_path: Path) -> None:
    ledger_file = tmp_path / "state.json"
    ledger_file.write_text(json.dumps(make_valid_ledger()))

    result_paths: dict[str, Path] = {}
    for b in REQUIRED_BASELINES:
        res = make_valid_result(b)
        p = tmp_path / f"result_{b}.json"
        p.write_text(json.dumps(res))
        result_paths[b] = p

    out_file = tmp_path / "table2-audit.json"
    audit_safedrug_table2(
        ledger_path=ledger_file,
        result_paths=result_paths,
        output_path=out_file,
        reference_path=REFERENCE_PATH,
    )
    raw_output_text = out_file.read_text()
    assert "test_rounds" not in raw_output_text
    assert "adaptation" not in raw_output_text
    assert "checkpoint" not in raw_output_text

    # Unknown/sensitive fields in result are rejected fail-closed
    with pytest.raises(ProtocolValidationError, match="unknown field"):
        res = make_valid_result("safedrug")
        res["private_patient_records"] = [{"id": 123}]
        p_corrupt = tmp_path / "result_safedrug_corrupt.json"
        p_corrupt.write_text(json.dumps(res))
        corrupt_paths = {**result_paths, "safedrug": p_corrupt}
        audit_safedrug_table2(
            ledger_path=ledger_file,
            result_paths=corrupt_paths,
            output_path=out_file,
            reference_path=REFERENCE_PATH,
        )
