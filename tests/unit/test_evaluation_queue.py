from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from medrec_research import BaselineRegistry
from medrec_research.errors import ProtocolValidationError
from medrec_research.reproduction.evaluation_queue import (
    admit_evaluation,
    admit_validated_training_evaluation,
    claim_next_evaluation,
    create_evaluation_queue,
    finalize_evaluation,
    load_evaluation_queue,
    requeue_interrupted_evaluations,
)
from medrec_research.reproduction.molerec_table1_attempt import (
    ReproductionAttemptDeclaration,
)
from medrec_research.reproduction.reproduction_evidence import finalize_evidence_pair
from medrec_research.reproduction.safedrug_selection import (
    SAFE_DRUG_LANE_IDS,
    candidate_from_training_evidence,
    select_safedrug_candidate,
)

REGISTRY = BaselineRegistry.load(Path(__file__).parents[2] / "baselines" / "registry.toml")


def _declaration(attempt_id: str = "attempt-1") -> ReproductionAttemptDeclaration:
    return ReproductionAttemptDeclaration.from_registry(REGISTRY, attempt_id)


def _selection() -> dict[str, object]:
    return select_safedrug_candidate(
        [
            _selection_candidate(
                lane_id,
                learning_rate=learning_rate,
                jaccard=jaccard,
                ddi_rate=ddi_rate,
            )
            for lane_id, learning_rate, jaccard, ddi_rate in (
                (SAFE_DRUG_LANE_IDS[0], 1e-5, 0.51, 0.07),
                (SAFE_DRUG_LANE_IDS[1], 1e-4, 0.52, 0.08),
                (SAFE_DRUG_LANE_IDS[2], 5e-4, 0.52, 0.06),
            )
        ]
    )


def _selection_candidate(
    lane_id: str,
    *,
    learning_rate: float,
    jaccard: float,
    ddi_rate: float,
) -> dict[str, object]:
    checkpoint_bytes = f"{lane_id}-checkpoint".encode()
    checkpoint_identity = hashlib.sha256(checkpoint_bytes).hexdigest()
    return {
        "lane_id": lane_id,
        "learning_rate": learning_rate,
        "checkpoint_identity": checkpoint_identity,
        "validation_jaccard": jaccard,
        "validation_ddi_rate": ddi_rate,
        "training_evidence": {
            "state": "completed",
            "artifact_type": "training",
            "identity": {
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
            },
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


def _training_identity(
    lane_id: str,
    *,
    scientific_baseline_id: str,
    profile_id: str,
    program_id: str = "safedrug-archived",
    submission_id: str | None = None,
) -> dict[str, str]:
    return {
        "attempt_id": "attempt-1",
        "lane_id": lane_id,
        "scientific_baseline_id": scientific_baseline_id,
        "program_id": program_id,
        "profile_id": profile_id,
        "harness_revision": "a" * 40,
        "model_source_revision": "b" * 40,
        "preprocessing_revision": "c" * 40,
        "snapshot_id": "snapshots/molerec-table1-c721-www23",
        "environment_sha256": "d" * 64,
        "mode": "formal",
        "submission_id": submission_id or f"submission-{lane_id}",
    }


def _write_training_pair(
    root: Path,
    *,
    identity: dict[str, str],
    learning_rate: float | None = None,
    validation_jaccard: float = 0.5,
    validation_ddi_rate: float = 0.07,
    checkpoint_bytes: bytes | None = None,
) -> None:
    checkpoint_bytes = checkpoint_bytes or f"{identity['lane_id']}-checkpoint".encode()
    checkpoint_path = root / "work" / "checkpoint.model"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_bytes(checkpoint_bytes)
    checkpoint = {
        "best_epoch": 0,
        "relative_path": "work/checkpoint.model",
        "sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
        "size_bytes": len(checkpoint_bytes),
    }
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
        "validation_jaccard": validation_jaccard,
        "validation_ddi_rate": validation_ddi_rate,
        "checkpoint": checkpoint,
    }
    if learning_rate is not None:
        result["learning_rate"] = learning_rate
    finalize_evidence_pair(root, status=status, result=result)


def test_queue_enforces_safe_drug_selection_and_fifo(tmp_path: Path) -> None:
    declaration = _declaration("attempt-1")
    path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(path, attempt_id="attempt-1", declaration=declaration)

    admit_evaluation(
        path,
        lane_id="molerec-retain",
        scientific_baseline_id="retain",
        training_artifact_id="runs/retain/result.json",
        test_submission_id="test-retain",
        declaration=declaration,
    )
    with pytest.raises(ProtocolValidationError, match=r"selection\.json"):
        admit_evaluation(
            path,
            lane_id=SAFE_DRUG_LANE_IDS[2],
            scientific_baseline_id="safedrug",
            training_artifact_id="runs/safedrug/result.json",
            test_submission_id="test-safedrug",
            declaration=declaration,
        )

    admit_evaluation(
        path,
        lane_id=SAFE_DRUG_LANE_IDS[2],
        scientific_baseline_id="safedrug",
        training_artifact_id="runs/safedrug/result.json",
        test_submission_id="test-safedrug",
        selection=_selection(),
        declaration=declaration,
    )

    first = claim_next_evaluation(path, declaration=declaration)
    assert first is not None
    assert first["lane_id"] == "molerec-retain"
    finalize_evaluation(
        path,
        lane_id="molerec-retain",
        state="completed",
        result_artifact_id="runs/retain/test/result.json",
        declaration=declaration,
    )
    second = claim_next_evaluation(path, declaration=declaration)
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
            declaration=declaration,
        )


def test_orchestrated_admission_reopens_training(
    tmp_path: Path,
) -> None:
    declaration = _declaration("attempt-1")
    attempt_root = tmp_path / "attempt"
    queue_path = attempt_root / "evaluation-queue.json"
    create_evaluation_queue(queue_path, attempt_id="attempt-1", declaration=declaration)
    training_root = attempt_root / "lanes" / "molerec-retain"
    identity = _training_identity(
        "molerec-retain",
        scientific_baseline_id="retain",
        profile_id="retain",
    )
    _write_training_pair(training_root, identity=identity)

    entry = admit_validated_training_evaluation(
        queue_path,
        attempt_root=attempt_root,
        lane_id="molerec-retain",
        scientific_baseline_id="retain",
        training_artifact_id="lanes/molerec-retain/result.json",
        test_submission_id="test-retain",
        expected_identity=identity,
        declaration=declaration,
    )
    assert entry["training_artifact_id"] == "lanes/molerec-retain/result.json"
    assert claim_next_evaluation(queue_path, declaration=declaration)["lane_id"] == "molerec-retain"


def test_orchestrated_admission_resolves_recovered_checkpoint_from_source_root(
    tmp_path: Path,
) -> None:
    declaration = _declaration("attempt-1")
    attempt_root = tmp_path / "attempt"
    queue_path = attempt_root / "evaluation-queue.json"
    create_evaluation_queue(queue_path, attempt_id="attempt-1", declaration=declaration)
    source_root = attempt_root / "lanes" / "molerec-retain"
    recovery_root = source_root / "recoveries" / "recovery-1"
    identity = _training_identity(
        "molerec-retain",
        scientific_baseline_id="retain",
        profile_id="retain",
    )
    checkpoint_bytes = b"recovered-checkpoint"
    checkpoint_path = source_root / "work" / "checkpoint.model"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_bytes(checkpoint_bytes)
    failed_common = {
        "schema_version": 2,
        "identity": identity,
        "mode": "formal",
        "state": "failed",
        "non_evidence": False,
    }
    finalize_evidence_pair(
        source_root,
        status={
            **failed_common,
            "kind": "reproduction_status_v2",
            "stage": "terminal",
            "started_at": "2026-08-29T00:00:00+00:00",
            "finished_at": "2026-08-29T00:01:00+00:00",
            "failure_code": "training_failed",
        },
        result={
            **failed_common,
            "kind": "reproduction_result_v2",
            "artifact_type": "training",
            "failure_code": "training_failed",
        },
    )
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
        "checkpoint_relative_path": "work/checkpoint.model",
        "validation_jaccard": 0.5,
        "validation_ddi_rate": 0.07,
    }
    recovered_common = {
        "schema_version": 2,
        "identity": identity,
        "mode": "formal",
        "state": "completed",
        "non_evidence": False,
        "recovery": recovery,
    }
    checkpoint = {
        "best_epoch": 0,
        "relative_path": "work/checkpoint.model",
        "sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
        "size_bytes": len(checkpoint_bytes),
    }
    finalize_evidence_pair(
        recovery_root,
        status={
            **recovered_common,
            "kind": "reproduction_status_v2",
            "stage": "terminal",
            "started_at": "2026-08-29T00:02:00+00:00",
            "finished_at": "2026-08-29T00:03:00+00:00",
            "failure_code": None,
        },
        result={
            **recovered_common,
            "kind": "reproduction_result_v2",
            "artifact_type": "training",
            "epochs_requested": 50,
            "epochs_observed": 50,
            "best_epoch": 0,
            "validation_jaccard": 0.5,
            "validation_ddi_rate": 0.07,
            "checkpoint": checkpoint,
        },
    )

    entry = admit_validated_training_evaluation(
        queue_path,
        attempt_root=attempt_root,
        lane_id="molerec-retain",
        scientific_baseline_id="retain",
        training_artifact_id=("lanes/molerec-retain/recoveries/recovery-1/result.json"),
        test_submission_id="test-retain-recovered",
        expected_identity=identity,
        declaration=declaration,
    )

    assert entry["training_artifact_id"] == (
        "lanes/molerec-retain/recoveries/recovery-1/result.json"
    )


def test_orchestrated_admission_keeps_nonselected_safedrug_lane_out_of_queue(
    tmp_path: Path,
) -> None:
    declaration = _declaration("attempt-1")
    attempt_root = tmp_path / "attempt"
    queue_path = attempt_root / "evaluation-queue.json"
    create_evaluation_queue(queue_path, attempt_id="attempt-1", declaration=declaration)
    candidates = []
    roots: dict[str, tuple[Path, dict[str, str]]] = {}
    for index, lane_id in enumerate(SAFE_DRUG_LANE_IDS):
        identity = _training_identity(
            lane_id,
            scientific_baseline_id="safedrug",
            profile_id="safedrug",
        )
        root = attempt_root / "lanes" / lane_id
        _write_training_pair(
            root,
            identity=identity,
            learning_rate=(1e-5, 1e-4, 5e-4)[index],
            validation_jaccard=(0.51, 0.53, 0.52)[index],
            validation_ddi_rate=(0.07, 0.08, 0.06)[index],
        )
        roots[lane_id] = (root, identity)
        candidates.append(
            candidate_from_training_evidence(
                lane_id,
                training_run_root=root,
                expected_identity=identity,
            )
        )
    selection = select_safedrug_candidate(candidates)
    selected_lane = selection["selected_lane_id"]
    assert selected_lane == SAFE_DRUG_LANE_IDS[1]

    nonselected_lane = SAFE_DRUG_LANE_IDS[0]
    _, nonselected_identity = roots[nonselected_lane]
    with pytest.raises(ProtocolValidationError, match="not_tested_by_design"):
        admit_validated_training_evaluation(
            queue_path,
            attempt_root=attempt_root,
            lane_id=nonselected_lane,
            scientific_baseline_id="safedrug",
            training_artifact_id=f"lanes/{nonselected_lane}/result.json",
            test_submission_id="test-safedrug-nonselected",
            expected_identity=nonselected_identity,
            selection=selection,
            declaration=declaration,
        )

    _, selected_identity = roots[selected_lane]
    entry = admit_validated_training_evaluation(
        queue_path,
        attempt_root=attempt_root,
        lane_id=selected_lane,
        scientific_baseline_id="safedrug",
        training_artifact_id=f"lanes/{selected_lane}/result.json",
        test_submission_id="test-safedrug-selected",
        expected_identity=selected_identity,
        selection=selection,
        declaration=declaration,
    )
    assert entry["selection_lane_id"] == selected_lane
    assert entry["training_artifact_id"] == f"lanes/{selected_lane}/result.json"


def test_terminal_queue_entries_are_not_replayed_after_restart(tmp_path: Path) -> None:
    declaration = _declaration("attempt-1")
    path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(path, attempt_id="attempt-1", declaration=declaration)
    admit_evaluation(
        path,
        lane_id="molerec-gamenet",
        scientific_baseline_id="gamenet",
        training_artifact_id="runs/gamenet/result.json",
        test_submission_id="test-gamenet",
        declaration=declaration,
    )
    assert claim_next_evaluation(path, declaration=declaration)["state"] == "running"
    finalize_evaluation(
        path,
        lane_id="molerec-gamenet",
        state="completed",
        result_artifact_id="runs/gamenet/test/result.json",
        declaration=declaration,
    )
    assert claim_next_evaluation(path, declaration=declaration) is None
    assert (
        load_evaluation_queue(path, declaration=declaration)["entries"][0]["state"] == "completed"
    )


def test_interrupted_running_entry_can_be_explicitly_requeued(tmp_path: Path) -> None:
    declaration = _declaration("attempt-1")
    path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(path, attempt_id="attempt-1", declaration=declaration)
    admit_evaluation(
        path,
        lane_id="molerec-leap",
        scientific_baseline_id="leap-safedrug",
        training_artifact_id="runs/leap/result.json",
        test_submission_id="test-leap",
        declaration=declaration,
    )
    assert claim_next_evaluation(path, declaration=declaration)["state"] == "running"
    assert requeue_interrupted_evaluations(path, declaration=declaration) == 1
    assert claim_next_evaluation(path, declaration=declaration)["lane_id"] == "molerec-leap"
    assert requeue_interrupted_evaluations(path, declaration=declaration) == 1


def test_queue_rejects_duplicate_lanes_in_persisted_json(tmp_path: Path) -> None:
    declaration = _declaration("attempt-1")
    path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(path, attempt_id="attempt-1", declaration=declaration)
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
        load_evaluation_queue(path, declaration=declaration)


def test_queue_validates_against_frozen_declaration(tmp_path: Path) -> None:
    declaration = _declaration("attempt-decl-1")
    path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(path, attempt_id="attempt-decl-1", declaration=declaration)

    # Valid admission
    admit_evaluation(
        path,
        lane_id="molerec-retain",
        scientific_baseline_id="retain",
        training_artifact_id="runs/retain/result.json",
        test_submission_id="test-retain",
        declaration=declaration,
    )

    # Reject undeclared lane
    with pytest.raises(ProtocolValidationError, match="undeclared lane"):
        admit_evaluation(
            path,
            lane_id="undeclared-lane",
            scientific_baseline_id="retain",
            training_artifact_id="runs/undeclared/result.json",
            test_submission_id="test-undeclared",
            declaration=declaration,
        )

    # Reject wrong scientific baseline
    with pytest.raises(ProtocolValidationError, match="wrong scientific baseline"):
        admit_evaluation(
            path,
            lane_id="molerec-leap",
            scientific_baseline_id="safedrug",
            training_artifact_id="runs/leap/result.json",
            test_submission_id="test-leap",
            declaration=declaration,
        )


def test_legacy_queue_without_sidecar_is_readable(tmp_path: Path) -> None:
    queue_path = tmp_path / "evaluation-queue.json"
    legacy_payload = {
        "schema_version": 1,
        "kind": "molerec_table1_evaluation_queue_v1",
        "attempt_id": "legacy-attempt-001",
        "evaluation_gpu_index": 7,
        "entries": [
            {
                "lane_id": "molerec-retain",
                "scientific_baseline_id": "retain",
                "training_artifact_id": "runs/retain/result.json",
                "test_submission_id": "test-retain",
                "result_artifact_id": "runs/retain/test/result.json",
                "state": "completed",
            }
        ],
    }
    queue_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

    loaded = load_evaluation_queue(queue_path)
    assert loaded["attempt_id"] == "legacy-attempt-001"
    assert len(loaded["entries"]) == 1
    assert loaded["entries"][0]["lane_id"] == "molerec-retain"


def test_legacy_queue_mutation_without_declaration_fails(tmp_path: Path) -> None:
    queue_path = tmp_path / "evaluation-queue.json"
    legacy_payload = {
        "schema_version": 1,
        "kind": "molerec_table1_evaluation_queue_v1",
        "attempt_id": "legacy-attempt-001",
        "evaluation_gpu_index": 7,
        "entries": [
            {
                "lane_id": "molerec-retain",
                "scientific_baseline_id": "retain",
                "training_artifact_id": "runs/retain/result.json",
                "test_submission_id": "test-retain",
                "state": "queued",
            }
        ],
    }
    queue_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

    with pytest.raises(ProtocolValidationError, match="ReproductionAttemptDeclaration"):
        admit_evaluation(
            queue_path,
            lane_id="molerec-leap",
            scientific_baseline_id="leap-safedrug",
            training_artifact_id="runs/leap/result.json",
            test_submission_id="test-leap",
        )

    with pytest.raises(ProtocolValidationError, match="ReproductionAttemptDeclaration"):
        claim_next_evaluation(queue_path)

    with pytest.raises(ProtocolValidationError, match="ReproductionAttemptDeclaration"):
        finalize_evaluation(
            queue_path,
            lane_id="molerec-retain",
            state="completed",
            result_artifact_id="runs/retain/test/result.json",
        )


def test_create_queue_without_declaration_fails(tmp_path: Path) -> None:
    queue_path = tmp_path / "evaluation-queue.json"
    with pytest.raises(ProtocolValidationError, match="ReproductionAttemptDeclaration"):
        create_evaluation_queue(queue_path, attempt_id="attempt-no-decl")


def test_admit_evaluation_without_declaration_fails(tmp_path: Path) -> None:
    declaration = _declaration("attempt-1")
    queue_path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(queue_path, attempt_id="attempt-1", declaration=declaration)

    with pytest.raises(ProtocolValidationError, match="ReproductionAttemptDeclaration"):
        admit_evaluation(
            queue_path,
            lane_id="molerec-retain",
            scientific_baseline_id="retain",
            training_artifact_id="runs/retain/result.json",
            test_submission_id="test-retain",
        )


def test_active_mutation_with_correct_declaration_succeeds(tmp_path: Path) -> None:
    declaration = _declaration("attempt-1")
    queue_path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(queue_path, attempt_id="attempt-1", declaration=declaration)

    entry = admit_evaluation(
        queue_path,
        lane_id="molerec-retain",
        scientific_baseline_id="retain",
        training_artifact_id="runs/retain/result.json",
        test_submission_id="test-retain",
        declaration=declaration,
    )
    assert entry["state"] == "queued"

    claimed = claim_next_evaluation(queue_path, declaration=declaration)
    assert claimed is not None
    assert claimed["lane_id"] == "molerec-retain"
    assert claimed["state"] == "running"

    finalized = finalize_evaluation(
        queue_path,
        lane_id="molerec-retain",
        state="completed",
        result_artifact_id="runs/retain/test/result.json",
        declaration=declaration,
    )
    assert finalized["state"] == "completed"


def test_declaration_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    declaration = _declaration("attempt-1")
    queue_path = tmp_path / "evaluation-queue.json"
    create_evaluation_queue(queue_path, attempt_id="attempt-1", declaration=declaration)

    wrong_decl = _declaration("different-attempt-99")
    with pytest.raises(ProtocolValidationError, match="does not match declaration attempt_id"):
        admit_evaluation(
            queue_path,
            lane_id="molerec-retain",
            scientific_baseline_id="retain",
            training_artifact_id="runs/retain/result.json",
            test_submission_id="test-retain",
            declaration=wrong_decl,
        )
