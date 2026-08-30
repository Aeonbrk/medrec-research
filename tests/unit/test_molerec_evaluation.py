from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import medrec_research.molerec_evaluation as molerec_evaluation
from medrec_research import BaselineRegistry
from medrec_research.errors import ProtocolValidationError
from medrec_research.evaluation_queue import (
    load_evaluation_queue,
    write_evaluation_queue,
)
from medrec_research.molerec_evaluation import (
    claim_table1_evaluation,
    finalize_table1_evaluation,
    prepare_table1_evaluation,
)
from medrec_research.reproduction_evidence import finalize_evidence_pair

PROJECT_ROOT = Path(__file__).parents[2]
ATTEMPT_ID = "formal-20260828-a09fcab-u8-b"
SOURCE_HARNESS = "a" * 40
CONTINUATION_HARNESS = "b" * 40
PREPROCESSING_REVISION = "c7218d0976e5ee5588aeaf5bdbc86b338126bba5"
SNAPSHOT_ID = "snapshots/molerec-table1-c721-www23"
ENVIRONMENT_SHA256 = "6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda"


def _write_training(
    root: Path,
    *,
    identity: dict[str, str],
    learning_rate: float | None = None,
    jaccard: float = 0.5,
    ddi_rate: float = 0.07,
) -> None:
    checkpoint_bytes = identity["lane_id"].encode()
    checkpoint_path = root / "work" / "checkpoint.model"
    checkpoint_path.parent.mkdir(parents=True)
    checkpoint_path.write_bytes(checkpoint_bytes)
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
        "started_at": "2026-08-29T00:00:00+00:00",
        "finished_at": "2026-08-29T00:01:00+00:00",
        "failure_code": None,
    }
    result = {
        **common,
        "kind": "reproduction_result_v2",
        "artifact_type": "training",
        "epochs_requested": 50,
        "epochs_observed": 50,
        "best_epoch": 0,
        "validation_jaccard": jaccard,
        "validation_ddi_rate": ddi_rate,
        "checkpoint": {
            "best_epoch": 0,
            "relative_path": "work/checkpoint.model",
            "sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
            "size_bytes": len(checkpoint_bytes),
        },
    }
    if learning_rate is not None:
        result["learning_rate"] = learning_rate
    finalize_evidence_pair(root, status=status, result=result)


def _prepare_state(tmp_path: Path) -> tuple[BaselineRegistry, Path, Path]:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    attempt_root = tmp_path / "attempt"
    artifact_ids: dict[str, str] = {}
    safedrug_jaccard = {
        "molerec-safedrug-lr-1e-5": 0.51,
        "molerec-safedrug-lr-1e-4": 0.53,
        "molerec-safedrug-lr-5e-4": 0.52,
    }
    for lane in registry.reproduction_lanes:
        baseline = registry.get(lane.scientific_baseline_id)
        identity = {
            "attempt_id": ATTEMPT_ID,
            "lane_id": lane.lane_id,
            "scientific_baseline_id": lane.scientific_baseline_id,
            "program_id": lane.program_id,
            "profile_id": lane.profile_id,
            "harness_revision": SOURCE_HARNESS,
            "model_source_revision": baseline.source.revision,
            "preprocessing_revision": PREPROCESSING_REVISION,
            "snapshot_id": SNAPSHOT_ID,
            "environment_sha256": ENVIRONMENT_SHA256,
            "mode": "formal",
            "submission_id": f"training-{lane.lane_id}",
        }
        run_root = attempt_root / "lanes" / lane.lane_id
        _write_training(
            run_root,
            identity=identity,
            learning_rate=lane.learning_rate,
            jaccard=safedrug_jaccard.get(lane.lane_id, 0.5),
        )
        artifact_ids[lane.lane_id] = f"lanes/{lane.lane_id}/result.json"

    state_root = tmp_path / "evaluation-state"
    prepared = prepare_table1_evaluation(
        state_root=state_root,
        registry=registry,
        attempt_root=attempt_root,
        attempt_id=ATTEMPT_ID,
        training_artifact_ids=artifact_ids,
        training_harness_revision=SOURCE_HARNESS,
        harness_revision=CONTINUATION_HARNESS,
        preprocessing_revision=PREPROCESSING_REVISION,
        snapshot_id=SNAPSHOT_ID,
        environment_sha256=ENVIRONMENT_SHA256,
    )
    assert prepared["selected_safedrug_lane"] == "molerec-safedrug-lr-1e-4"
    return registry, attempt_root, state_root


def _running_test_context(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, dict[str, Any], dict[str, str]]:
    _, attempt_root, state_root = _prepare_state(tmp_path)
    queue_path = state_root / "evaluation-queue.json"
    queue = load_evaluation_queue(queue_path)
    entry = queue["entries"][0]
    entry["state"] = "running"
    write_evaluation_queue(queue_path, queue)

    ledger_path = state_root / "ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    lane = ledger["lanes"][entry["lane_id"]]
    identity = {
        "attempt_id": ledger["attempt_id"],
        "lane_id": entry["lane_id"],
        "scientific_baseline_id": lane["scientific_baseline_id"],
        "program_id": lane["program_id"],
        "profile_id": lane["profile_id"],
        "harness_revision": ledger["harness_revision"],
        "model_source_revision": lane["model_source_revision"],
        "preprocessing_revision": ledger["preprocessing_revision"],
        "snapshot_id": ledger["snapshot_id"],
        "environment_sha256": ledger["environment_sha256"],
        "mode": "formal",
        "submission_id": entry["test_submission_id"],
    }
    return attempt_root, state_root, queue_path, ledger_path, entry, identity


def _write_completed_test_pair(
    attempt_root: Path,
    entry: dict[str, Any],
    identity: dict[str, str],
) -> None:
    common = {
        "schema_version": 2,
        "identity": identity,
        "mode": "formal",
        "state": "completed",
        "non_evidence": False,
    }
    finalize_evidence_pair(
        attempt_root / "lanes" / entry["lane_id"] / "test",
        status={
            **common,
            "kind": "reproduction_status_v2",
            "stage": "terminal",
            "started_at": "2026-08-29T00:00:00+00:00",
            "finished_at": "2026-08-29T00:01:00+00:00",
            "failure_code": None,
        },
        result={
            **common,
            "kind": "reproduction_result_v2",
            "artifact_type": "test",
        },
    )


def test_prepare_table1_evaluation_selects_and_publishes_exact_five_lane_state(
    tmp_path: Path,
) -> None:
    registry, attempt_root, state_root = _prepare_state(tmp_path)

    queue = json.loads((state_root / "evaluation-queue.json").read_text(encoding="utf-8"))
    assert [entry["lane_id"] for entry in queue["entries"]] == [
        "molerec-retain",
        "molerec-leap",
        "molerec-gamenet",
        "molerec-safedrug-lr-1e-4",
        "molerec-embedding",
    ]
    ledger = json.loads((state_root / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["lanes"]["molerec-safedrug-lr-1e-5"]["state"] == ("not_tested_by_design")
    assert ledger["lanes"]["molerec-safedrug-lr-5e-4"]["state"] == ("not_tested_by_design")
    preregistration = json.loads(
        (state_root / "five-model-comparison-preregistration.json").read_text(encoding="utf-8")
    )
    assert preregistration["selected_safedrug_lane"] == "molerec-safedrug-lr-1e-4"
    assert not any(attempt_root.rglob("test"))

    queue["entries"][0]["state"] = "failed"
    (state_root / "evaluation-queue.json").write_text(json.dumps(queue), encoding="utf-8")
    with pytest.raises(ProtocolValidationError, match="terminal after a failed"):
        claim_table1_evaluation(
            state_root=state_root,
            registry=registry,
            attempt_root=attempt_root,
            remote_root="/root/zhb/medrec-research",
            data_root="/root/zhb/medrec-data",
        )


def test_finalize_table1_evaluation_recovers_after_queue_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt_root, state_root, queue_path, ledger_path, entry, identity = _running_test_context(
        tmp_path
    )
    _write_completed_test_pair(attempt_root, entry, identity)

    original_finalize = molerec_evaluation.finalize_evaluation

    def fail_queue_write(*args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        raise OSError("simulated queue write failure")

    monkeypatch.setattr(molerec_evaluation, "finalize_evaluation", fail_queue_write)
    with pytest.raises(OSError, match="simulated queue write failure"):
        finalize_table1_evaluation(state_root=state_root, attempt_root=attempt_root)

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["lanes"][entry["lane_id"]]["state"] == "completed"
    assert load_evaluation_queue(queue_path)["entries"][0]["state"] == "running"

    monkeypatch.setattr(molerec_evaluation, "finalize_evaluation", original_finalize)
    finalized = finalize_table1_evaluation(state_root=state_root, attempt_root=attempt_root)
    assert finalized["state"] == "completed"
    assert load_evaluation_queue(queue_path)["entries"][0]["state"] == "completed"


def test_finalize_table1_evaluation_rejects_wrong_test_identity(tmp_path: Path) -> None:
    attempt_root, state_root, queue_path, ledger_path, entry, identity = _running_test_context(
        tmp_path
    )
    _write_completed_test_pair(
        attempt_root,
        entry,
        {**identity, "submission_id": "wrong-test-submission"},
    )

    with pytest.raises(ProtocolValidationError, match="active submission"):
        finalize_table1_evaluation(state_root=state_root, attempt_root=attempt_root)

    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["lanes"][entry["lane_id"]]["state"] == "queued"
    assert load_evaluation_queue(queue_path)["entries"][0]["state"] == "running"
