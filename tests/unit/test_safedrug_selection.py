from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from medrec_research.errors import ProtocolValidationError
from medrec_research.reproduction_evidence import finalize_evidence_pair
from medrec_research.safedrug_selection import (
    SAFE_DRUG_LANE_IDS,
    candidate_from_training_evidence,
    require_selected_safedrug_lane,
    select_safedrug_candidate,
    write_selection,
)


def _identity(lane_id: str) -> dict[str, str]:
    return {
        "attempt_id": "attempt-1",
        "lane_id": lane_id,
        "scientific_baseline_id": "safedrug",
        "program_id": "safedrug-archived",
        "profile_id": "safedrug",
        "harness_revision": "a" * 40,
        "model_source_revision": "b" * 40,
        "preprocessing_revision": "c" * 40,
        "snapshot_id": "snapshots/molerec-table1-c721-www23",
        "environment_sha256": "d" * 64,
        "mode": "formal",
        "submission_id": f"submission-{lane_id}",
    }


def _training_evidence(
    lane_id: str,
    *,
    learning_rate: float,
    jaccard: float,
    ddi_rate: float,
    recovery: dict[str, object] | None = None,
) -> dict[str, object]:
    checkpoint_bytes = f"{lane_id}-checkpoint".encode()
    checkpoint_path = "work/saved/SafeDrug_run/Epoch_0_TARGET_0.06_JA_0.5_DDI_0.06.model"
    return {
        "state": "completed",
        "artifact_type": "training",
        "identity": _identity(lane_id),
        "learning_rate": learning_rate,
        "best_epoch": 0,
        "validation_jaccard": jaccard,
        "validation_ddi_rate": ddi_rate,
        "checkpoint": {
            "best_epoch": 0,
            "relative_path": checkpoint_path,
            "sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
            "size_bytes": len(checkpoint_bytes),
        },
        "recovery": recovery,
    }


def _candidate(
    lane_id: str,
    *,
    learning_rate: float,
    jaccard: float,
    ddi_rate: float,
) -> dict[str, object]:
    checkpoint_identity = hashlib.sha256(f"{lane_id}-checkpoint".encode()).hexdigest()
    return {
        "lane_id": lane_id,
        "learning_rate": learning_rate,
        "checkpoint_identity": checkpoint_identity,
        "validation_jaccard": jaccard,
        "validation_ddi_rate": ddi_rate,
        "training_evidence": _training_evidence(
            lane_id,
            learning_rate=learning_rate,
            jaccard=jaccard,
            ddi_rate=ddi_rate,
        ),
    }


def _candidates() -> list[dict[str, object]]:
    return [
        _candidate(SAFE_DRUG_LANE_IDS[0], learning_rate=1e-5, jaccard=0.51, ddi_rate=0.07),
        _candidate(SAFE_DRUG_LANE_IDS[1], learning_rate=1e-4, jaccard=0.52, ddi_rate=0.08),
        _candidate(SAFE_DRUG_LANE_IDS[2], learning_rate=5e-4, jaccard=0.52, ddi_rate=0.06),
    ]


def test_selection_uses_validation_ties_and_is_order_independent() -> None:
    first = select_safedrug_candidate(_candidates())
    second = select_safedrug_candidate(list(reversed(_candidates())))

    assert first["state"] == "selection_ready"
    assert first["selected_lane_id"] == SAFE_DRUG_LANE_IDS[2]
    assert first["comparison_decisions"] == second["comparison_decisions"]
    assert first["test_metrics_available"] is False


def test_selection_marks_missing_candidate_incomplete() -> None:
    selection = select_safedrug_candidate(_candidates()[:-1])

    assert selection["state"] == "selection_incomplete"
    assert selection["selected_lane_id"] is None
    assert any(SAFE_DRUG_LANE_IDS[2] in error for error in selection["errors"])


def test_selection_rejects_test_fields_by_failing_closed() -> None:
    candidates = _candidates()
    candidates[0]["test_metrics"] = {"jaccard": 0.99}

    selection = select_safedrug_candidate(candidates)

    assert selection["state"] == "selection_incomplete"
    assert selection["selected_lane_id"] is None


def test_selected_lane_is_the_only_test_admission() -> None:
    selection = select_safedrug_candidate(_candidates())

    selected = require_selected_safedrug_lane(selection, SAFE_DRUG_LANE_IDS[2])
    assert selected["lane_id"] == SAFE_DRUG_LANE_IDS[2]
    with pytest.raises(ProtocolValidationError, match="was not selected"):
        require_selected_safedrug_lane(selection, SAFE_DRUG_LANE_IDS[0])


def test_test_fields_are_rejected_when_reopening_selection() -> None:
    selection = select_safedrug_candidate(_candidates())
    selection["candidates"][0]["test_metrics"] = {"jaccard": 0.99}

    with pytest.raises(ProtocolValidationError, match="unknown field"):
        require_selected_safedrug_lane(selection, SAFE_DRUG_LANE_IDS[2])


def test_selection_requires_terminal_training_evidence() -> None:
    candidates = _candidates()
    candidates[0]["training_evidence"]["state"] = "failed"  # type: ignore[index]

    selection = select_safedrug_candidate(candidates)

    assert selection["state"] == "selection_incomplete"
    assert selection["selected_lane_id"] is None
    assert any("completed training evidence" in error for error in selection["errors"])


def test_selection_rejects_tampered_comparison_and_winner() -> None:
    selection = select_safedrug_candidate(_candidates())
    selection["comparison_decisions"][0]["validation_jaccard"] += 1e-12  # type: ignore[index]

    with pytest.raises(ProtocolValidationError, match="comparison decisions"):
        require_selected_safedrug_lane(selection, SAFE_DRUG_LANE_IDS[2])

    selection = select_safedrug_candidate(_candidates())
    selection["selected_lane_id"] = SAFE_DRUG_LANE_IDS[0]

    with pytest.raises(ProtocolValidationError, match="winner"):
        require_selected_safedrug_lane(selection, SAFE_DRUG_LANE_IDS[2])


def test_recovered_candidate_reopens_source_aware_evidence(tmp_path: Path) -> None:
    lane_id = SAFE_DRUG_LANE_IDS[0]
    identity = _identity(lane_id)
    source_root = tmp_path / "source"
    recovery_root = source_root / "recoveries" / "recovery-1"
    checkpoint_relative_path = "work/saved/SafeDrug_run/Epoch_0_TARGET_0.06_JA_0.5_DDI_0.06.model"
    checkpoint_bytes = b"preserved-checkpoint"
    checkpoint_path = source_root / checkpoint_relative_path
    checkpoint_path.parent.mkdir(parents=True)
    checkpoint_path.write_bytes(checkpoint_bytes)
    common = {
        "schema_version": 2,
        "identity": identity,
        "mode": "formal",
        "non_evidence": False,
    }
    source_status = {
        **common,
        "kind": "reproduction_status_v2",
        "stage": "terminal",
        "state": "failed",
        "started_at": "2026-08-26T00:00:00+00:00",
        "finished_at": "2026-08-26T01:00:00+00:00",
        "failure_code": "training_failed",
    }
    source_result = {
        **common,
        "kind": "reproduction_result_v2",
        "state": "failed",
        "artifact_type": "training",
        "failure_code": "training_failed",
    }
    recovery = {
        "schema_version": 1,
        "kind": "training_finalization_recovery",
        "recovery_id": "recovery-1",
        "finalizer_revision": "e" * 40,
        "source_relative_path": "../..",
        "source_terminal_state": "failed",
        "source_failure_code": "training_failed",
        "parser_classification": "validation_metrics_unlabeled",
        "selected_epoch": 0,
        "checkpoint_relative_path": checkpoint_relative_path,
        "validation_jaccard": 0.512345678901,
        "validation_ddi_rate": 0.067891234567,
    }
    recovered_status = {
        **common,
        "kind": "reproduction_status_v2",
        "stage": "terminal",
        "state": "completed",
        "started_at": "2026-08-29T00:00:00+00:00",
        "finished_at": "2026-08-29T00:00:01+00:00",
        "failure_code": None,
        "recovery": recovery,
    }
    recovered_result = {
        **common,
        "kind": "reproduction_result_v2",
        "state": "completed",
        "artifact_type": "training",
        "epochs_requested": 50,
        "epochs_observed": 50,
        "learning_rate": 1e-5,
        "best_epoch": 0,
        "validation_jaccard": recovery["validation_jaccard"],
        "validation_ddi_rate": recovery["validation_ddi_rate"],
        "checkpoint": {
            "best_epoch": 0,
            "relative_path": checkpoint_relative_path,
            "sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
            "size_bytes": len(checkpoint_bytes),
        },
        "recovery": recovery,
    }
    finalize_evidence_pair(source_root, status=source_status, result=source_result)
    finalize_evidence_pair(recovery_root, status=recovered_status, result=recovered_result)

    candidate = candidate_from_training_evidence(
        lane_id=lane_id,
        training_run_root=recovery_root,
        source_run_root=source_root,
        expected_identity=identity,
    )

    assert candidate["checkpoint_identity"] == hashlib.sha256(checkpoint_bytes).hexdigest()
    assert candidate["training_evidence"]["recovery"]["recovery_id"] == "recovery-1"  # type: ignore[index]
    assert candidate["validation_jaccard"] == 0.512345678901


def test_candidate_rejects_training_evidence_without_all_epochs(tmp_path: Path) -> None:
    lane_id = SAFE_DRUG_LANE_IDS[0]
    identity = _identity(lane_id)
    training_root = tmp_path / "training"
    checkpoint_relative_path = "work/saved/SafeDrug_run/Epoch_0.model"
    checkpoint_bytes = b"checkpoint"
    checkpoint_path = training_root / checkpoint_relative_path
    checkpoint_path.parent.mkdir(parents=True)
    checkpoint_path.write_bytes(checkpoint_bytes)
    common = {
        "schema_version": 2,
        "identity": identity,
        "mode": "formal",
        "non_evidence": False,
    }
    finalize_evidence_pair(
        training_root,
        status={
            **common,
            "kind": "reproduction_status_v2",
            "stage": "terminal",
            "state": "completed",
            "started_at": "2026-08-29T00:00:00+00:00",
            "finished_at": "2026-08-29T00:01:00+00:00",
            "failure_code": None,
        },
        result={
            **common,
            "kind": "reproduction_result_v2",
            "state": "completed",
            "artifact_type": "training",
            "epochs_requested": 49,
            "epochs_observed": 49,
            "learning_rate": 1e-5,
            "best_epoch": 0,
            "validation_jaccard": 0.5,
            "validation_ddi_rate": 0.07,
            "checkpoint": {
                "best_epoch": 0,
                "relative_path": checkpoint_relative_path,
                "sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
                "size_bytes": len(checkpoint_bytes),
            },
        },
    )

    with pytest.raises(ProtocolValidationError, match="all 50 epochs"):
        candidate_from_training_evidence(
            lane_id,
            training_run_root=training_root,
            expected_identity=identity,
        )


def test_selection_rejects_extra_candidate_even_with_custom_expected_ids() -> None:
    selection = select_safedrug_candidate(
        [*_candidates(), _candidate("extra-lane", learning_rate=1e-5, jaccard=0.1, ddi_rate=0.1)]
    )

    assert selection["state"] == "selection_incomplete"
    assert selection["selected_lane_id"] is None


def test_selection_is_atomically_written_as_json(tmp_path: Path) -> None:
    selection = select_safedrug_candidate(_candidates())
    path = tmp_path / "selection.json"

    write_selection(path, selection)

    assert json.loads(path.read_text(encoding="utf-8")) == selection
