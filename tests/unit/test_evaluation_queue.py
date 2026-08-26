from __future__ import annotations

import json
from pathlib import Path

import pytest

from medrec_research.errors import ProtocolValidationError
from medrec_research.evaluation_queue import (
    admit_evaluation,
    claim_next_evaluation,
    create_evaluation_queue,
    finalize_evaluation,
    load_evaluation_queue,
    requeue_interrupted_evaluations,
)
from medrec_research.safedrug_selection import SAFE_DRUG_LANE_IDS, select_safedrug_candidate


def _selection() -> dict[str, object]:
    return select_safedrug_candidate(
        [
            {
                "lane_id": lane_id,
                "learning_rate": learning_rate,
                "checkpoint_identity": f"{lane_id}-checkpoint",
                "validation_jaccard": jaccard,
                "validation_ddi_rate": ddi_rate,
            }
            for lane_id, learning_rate, jaccard, ddi_rate in (
                (SAFE_DRUG_LANE_IDS[0], 1e-5, 0.51, 0.07),
                (SAFE_DRUG_LANE_IDS[1], 1e-4, 0.52, 0.08),
                (SAFE_DRUG_LANE_IDS[2], 5e-4, 0.52, 0.06),
            )
        ]
    )


def test_queue_enforces_safe_drug_selection_and_fifo(tmp_path: Path) -> None:
    path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(path, attempt_id="attempt-1")

    admit_evaluation(
        path,
        lane_id="molerec-retain",
        scientific_baseline_id="retain",
        training_artifact_id="runs/retain/result.json",
        test_submission_id="test-retain",
    )
    with pytest.raises(ProtocolValidationError, match=r"selection\.json"):
        admit_evaluation(
            path,
            lane_id=SAFE_DRUG_LANE_IDS[2],
            scientific_baseline_id="safedrug",
            training_artifact_id="runs/safedrug/result.json",
            test_submission_id="test-safedrug",
        )

    admit_evaluation(
        path,
        lane_id=SAFE_DRUG_LANE_IDS[2],
        scientific_baseline_id="safedrug",
        training_artifact_id="runs/safedrug/result.json",
        test_submission_id="test-safedrug",
        selection=_selection(),
    )

    first = claim_next_evaluation(path)
    assert first is not None
    assert first["lane_id"] == "molerec-retain"
    finalize_evaluation(
        path,
        lane_id="molerec-retain",
        state="completed",
        result_artifact_id="runs/retain/test/result.json",
    )
    second = claim_next_evaluation(path)
    assert second is not None
    assert second["lane_id"] == SAFE_DRUG_LANE_IDS[2]

    with pytest.raises(ProtocolValidationError, match="already queued"):
        admit_evaluation(
            path,
            lane_id=SAFE_DRUG_LANE_IDS[2],
            scientific_baseline_id="safedrug",
            training_artifact_id="runs/safedrug/result.json",
            test_submission_id="test-safedrug-duplicate",
            selection=_selection(),
        )


def test_terminal_queue_entries_are_not_replayed_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(path, attempt_id="attempt-1")
    admit_evaluation(
        path,
        lane_id="molerec-gamenet",
        scientific_baseline_id="gamenet",
        training_artifact_id="runs/gamenet/result.json",
        test_submission_id="test-gamenet",
    )
    assert claim_next_evaluation(path)["state"] == "running"
    finalize_evaluation(
        path,
        lane_id="molerec-gamenet",
        state="completed",
        result_artifact_id="runs/gamenet/test/result.json",
    )
    assert claim_next_evaluation(path) is None
    assert load_evaluation_queue(path)["entries"][0]["state"] == "completed"


def test_interrupted_running_entry_can_be_explicitly_requeued(tmp_path: Path) -> None:
    path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(path, attempt_id="attempt-1")
    admit_evaluation(
        path,
        lane_id="molerec-leap",
        scientific_baseline_id="leap",
        training_artifact_id="runs/leap/result.json",
        test_submission_id="test-leap",
    )
    assert claim_next_evaluation(path)["state"] == "running"
    assert requeue_interrupted_evaluations(path) == 1
    assert claim_next_evaluation(path)["lane_id"] == "molerec-leap"
    assert requeue_interrupted_evaluations(path) == 1


def test_queue_rejects_duplicate_lanes_in_persisted_json(tmp_path: Path) -> None:
    path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(path, attempt_id="attempt-1")
    queue = json.loads(path.read_text(encoding="utf-8"))
    entry = {
        "lane_id": "molerec-retain",
        "scientific_baseline_id": "retain",
        "training_artifact_id": "runs/retain/result.json",
        "test_submission_id": "test-retain",
        "state": "queued",
    }
    queue["entries"] = [entry, {**entry, "test_submission_id": "test-retain-2"}]
    path.write_text(json.dumps(queue), encoding="utf-8")

    with pytest.raises(ProtocolValidationError, match="duplicate lanes"):
        load_evaluation_queue(path)
