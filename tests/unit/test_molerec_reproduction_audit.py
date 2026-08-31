from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from medrec_research.errors import ProtocolValidationError
from medrec_research.reproduction.molerec_reproduction_audit import (
    EXPECTED_DATASET_COUNTS,
    REQUIRED_MOLEREC_BASELINES,
    SUMMARY_METRICS,
    audit_molerec_table1,
    load_molerec_table1_reference,
)
from medrec_research.reproduction.reproduction_evidence import finalize_evidence_pair
from medrec_research.reproduction.safedrug_selection import (
    select_safedrug_candidate,
    write_selection,
)

PROJECT_ROOT = Path(__file__).parents[2]
REFERENCE_PATH = PROJECT_ROOT / "research" / "baseline-preflight" / "molerec-table1-reference.json"
ENVIRONMENT_SHA = "d" * 64
HARNESS_REVISION = "a" * 40
PREPROCESSING_REVISION = "c" * 40


def _ledger() -> dict[str, Any]:
    lane_specs = {
        "molerec-retain": ("retain", "safedrug-archived", "retain", "b" * 40),
        "molerec-leap": (
            "leap-safedrug",
            "safedrug-archived",
            "leap-safedrug",
            "b" * 40,
        ),
        "molerec-gamenet": ("gamenet", "safedrug-archived", "gamenet", "b" * 40),
        "molerec-safedrug-lr-1e-5": ("safedrug", "safedrug-archived", "safedrug", "b" * 40),
        "molerec-safedrug-lr-1e-4": ("safedrug", "safedrug-archived", "safedrug", "b" * 40),
        "molerec-safedrug-lr-5e-4": ("safedrug", "safedrug-archived", "safedrug", "b" * 40),
        "molerec-embedding": ("molerec", "molerec", "molerec-embedding", "e" * 40),
    }
    return {
        "schema_version": 2,
        "kind": "molerec_table1_attempt_ledger_v2",
        "attempt_id": "attempt-1",
        "harness_revision": HARNESS_REVISION,
        "preprocessing_revision": PREPROCESSING_REVISION,
        "snapshot_id": "snapshots/molerec-table1-c721-www23",
        "environment_sha256": ENVIRONMENT_SHA,
        "test_lane_ids": {
            "retain": "molerec-retain",
            "leap": "molerec-leap",
            "gamenet": "molerec-gamenet",
            "safedrug": "molerec-safedrug-lr-1e-4",
            "molerec": "molerec-embedding",
        },
        "lanes": {
            lane_id: {
                "scientific_baseline_id": baseline_id,
                "program_id": program_id,
                "profile_id": profile_id,
                "model_source_revision": model_revision,
                "active_submission_id": f"submission-{lane_id}",
                "state": "completed",
            }
            for lane_id, (baseline_id, program_id, profile_id, model_revision) in lane_specs.items()
        },
    }


def _identity(ledger: dict[str, Any], lane_id: str) -> dict[str, str]:
    lane = ledger["lanes"][lane_id]
    return {
        "attempt_id": ledger["attempt_id"],
        "lane_id": lane_id,
        "scientific_baseline_id": lane["scientific_baseline_id"],
        "program_id": lane["program_id"],
        "profile_id": lane["profile_id"],
        "harness_revision": ledger["harness_revision"],
        "model_source_revision": lane["model_source_revision"],
        "preprocessing_revision": ledger["preprocessing_revision"],
        "snapshot_id": ledger["snapshot_id"],
        "environment_sha256": ledger["environment_sha256"],
        "mode": "formal",
        "submission_id": lane["active_submission_id"],
    }


def _result(
    ledger: dict[str, Any],
    baseline_id: str,
    *,
    jaccard: float | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    lane_id = ledger["test_lane_ids"][baseline_id]
    reference = load_molerec_table1_reference(REFERENCE_PATH)[baseline_id]
    means = {metric: reference[metric]["mean"] for metric in SUMMARY_METRICS}
    if jaccard is not None:
        means["jaccard"] = jaccard
    summary = {metric: {"mean": value, "std": 0.0} for metric, value in means.items()}
    rounds = [{"metrics": dict(means)} for _ in range(10)]
    identity = _identity(ledger, lane_id)
    common = {
        "schema_version": 2,
        "identity": identity,
        "mode": "formal",
        "state": "completed",
        "non_evidence": False,
    }
    status = {
        **common,
        "kind": "reproduction_status_v2",
        "stage": "terminal",
        "started_at": "2026-08-26T00:00:00+00:00",
        "finished_at": "2026-08-26T01:00:00+00:00",
        "failure_code": None,
    }
    result = {
        **common,
        "kind": "reproduction_result_v2",
        "dataset_counts": dict(EXPECTED_DATASET_COUNTS),
        "epochs_requested": 50,
        "epochs_observed": 50,
        "checkpoint": {"sha256": "f" * 64, "best_epoch": 40},
        "harness_summary": summary,
        "rounds": rounds,
    }
    return status, result


def _write_artifacts(
    tmp_path: Path, *, molerec_jaccard: float | None = None
) -> tuple[Path, dict[str, Path], Path]:
    ledger = _ledger()
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    result_paths: dict[str, Path] = {}
    for baseline_id in REQUIRED_MOLEREC_BASELINES:
        run_root = tmp_path / baseline_id
        status, result = _result(
            ledger,
            baseline_id,
            jaccard=molerec_jaccard if baseline_id == "molerec" else None,
        )
        finalize_evidence_pair(run_root, status=status, result=result)
        result_paths[baseline_id] = run_root / "result.json"

    selection_path = tmp_path / "selection.json"
    selection = select_safedrug_candidate(
        [
            _selection_candidate(
                "molerec-safedrug-lr-1e-5",
                learning_rate=1e-5,
                jaccard=0.51,
                ddi_rate=0.07,
            ),
            _selection_candidate(
                "molerec-safedrug-lr-1e-4",
                learning_rate=1e-4,
                jaccard=0.52,
                ddi_rate=0.06,
            ),
            _selection_candidate(
                "molerec-safedrug-lr-5e-4",
                learning_rate=5e-4,
                jaccard=0.50,
                ddi_rate=0.08,
            ),
        ]
    )
    write_selection(str(selection_path), selection)
    return ledger_path, result_paths, selection_path


def _selection_candidate(
    lane_id: str,
    *,
    learning_rate: float,
    jaccard: float,
    ddi_rate: float,
) -> dict[str, object]:
    checkpoint_bytes = f"{lane_id}-checkpoint".encode()
    checkpoint_identity = hashlib.sha256(checkpoint_bytes).hexdigest()
    identity = {
        "attempt_id": "attempt-1",
        "lane_id": lane_id,
        "scientific_baseline_id": "safedrug",
        "program_id": "safedrug-archived",
        "profile_id": "safedrug",
        "harness_revision": HARNESS_REVISION,
        "model_source_revision": "b" * 40,
        "preprocessing_revision": PREPROCESSING_REVISION,
        "snapshot_id": "snapshots/molerec-table1-c721-www23",
        "environment_sha256": ENVIRONMENT_SHA,
        "mode": "formal",
        "submission_id": f"submission-{lane_id}",
    }
    return {
        "lane_id": lane_id,
        "learning_rate": learning_rate,
        "checkpoint_identity": checkpoint_identity,
        "validation_jaccard": jaccard,
        "validation_ddi_rate": ddi_rate,
        "training_evidence": {
            "state": "completed",
            "artifact_type": "training",
            "identity": identity,
            "learning_rate": learning_rate,
            "best_epoch": 0,
            "validation_jaccard": jaccard,
            "validation_ddi_rate": ddi_rate,
            "checkpoint": {
                "best_epoch": 0,
                "relative_path": "work/checkpoint.model",
                "sha256": checkpoint_identity,
                "size_bytes": len(checkpoint_bytes),
            },
            "recovery": None,
        },
    }


def test_reference_has_exact_plan_targets_and_coverage() -> None:
    reference = load_molerec_table1_reference(REFERENCE_PATH)

    assert reference["molerec"]["jaccard"] == {"mean": 0.5305, "std": 0.0033}
    assert set(reference) == set(REQUIRED_MOLEREC_BASELINES)


def test_audit_passes_all_four_axes_on_complete_artifacts(tmp_path: Path) -> None:
    ledger_path, result_paths, selection_path = _write_artifacts(tmp_path)

    packet = audit_molerec_table1(
        ledger_path=ledger_path,
        result_paths=result_paths,
        selection_path=selection_path,
        output_path=tmp_path / "audit.json",
        reference_path=REFERENCE_PATH,
    )

    assert packet["verdict"] == "completed_match"
    assert all(axis["passed"] for axis in packet["axes"].values())
    assert packet["interval_checks_passed"] == 25
    assert packet["relationship_checks_passed"] == 4


def test_complete_execution_with_point_miss_is_completed_mismatch(tmp_path: Path) -> None:
    ledger_path, result_paths, selection_path = _write_artifacts(
        tmp_path,
        molerec_jaccard=0.1,
    )

    packet = audit_molerec_table1(
        ledger_path=ledger_path,
        result_paths=result_paths,
        selection_path=selection_path,
        output_path=tmp_path / "audit.json",
        reference_path=REFERENCE_PATH,
    )

    assert packet["verdict"] == "completed_mismatch"
    assert packet["axes"]["execution_integrity"]["passed"] is True
    assert packet["axes"]["artifact_completeness"]["passed"] is True
    assert packet["axes"]["paper_point_fidelity"]["passed"] is False


def test_missing_selection_is_selection_incomplete(tmp_path: Path) -> None:
    ledger_path, result_paths, _ = _write_artifacts(tmp_path)

    packet = audit_molerec_table1(
        ledger_path=ledger_path,
        result_paths=result_paths,
        output_path=tmp_path / "audit.json",
        reference_path=REFERENCE_PATH,
    )

    assert packet["verdict"] == "selection_incomplete"
    assert packet["selection"]["selected_lane_id"] is None


def test_reference_rejects_extra_metric(tmp_path: Path) -> None:
    raw = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    raw["baselines"]["retain"]["unexpected"] = {"mean": 0.0, "std": 0.0}
    path = tmp_path / "reference-extra-metric.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ProtocolValidationError, match="exactly five metrics"):
        load_molerec_table1_reference(path)
