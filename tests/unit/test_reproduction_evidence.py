from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from medrec_research.errors import ProtocolValidationError
from medrec_research.reproduction.reproduction_evidence import (
    finalize_evidence_pair,
    reopen_finalized_pair,
    reopen_recovered_finalized_pair,
    validate_status_result_pair,
)

CHECKPOINT_BYTES = b"checkpoint"


def _identity(*, submission_id: str = "submission-1") -> dict[str, str]:
    return {
        "attempt_id": "attempt-1",
        "lane_id": "molerec-retain",
        "scientific_baseline_id": "retain",
        "program_id": "safedrug-archived",
        "profile_id": "retain",
        "harness_revision": "a" * 40,
        "model_source_revision": "b" * 40,
        "preprocessing_revision": "c" * 40,
        "snapshot_id": "snapshots/molerec-table1-c721-www23",
        "environment_sha256": "d" * 64,
        "mode": "formal",
        "submission_id": submission_id,
    }


def _pair(*, identity: dict[str, str] | None = None) -> tuple[dict[str, object], dict[str, object]]:
    bound_identity = identity or _identity()
    common = {
        "schema_version": 2,
        "identity": bound_identity,
        "mode": "formal",
        "state": "completed",
        "non_evidence": False,
    }
    return (
        {
            **common,
            "kind": "reproduction_status_v2",
            "stage": "terminal",
            "started_at": "2026-08-26T00:00:00+00:00",
            "finished_at": "2026-08-26T01:00:00+00:00",
            "failure_code": None,
        },
        {
            **common,
            "kind": "reproduction_result_v2",
            "metrics": {"jaccard": 0.5},
        },
    )


def _failed_training_pair() -> tuple[dict[str, object], dict[str, object]]:
    status, result = _pair()
    status.update(state="failed", failure_code="training_failed")
    result.update(
        state="failed",
        artifact_type="training",
        failure_code="training_failed",
    )
    return status, result


def _recovered_training_pair() -> tuple[dict[str, object], dict[str, object]]:
    status, result = _pair()
    recovery = {
        "schema_version": 1,
        "kind": "training_finalization_recovery",
        "recovery_id": "finalizer-1",
        "finalizer_revision": "e" * 40,
        "source_relative_path": "../..",
        "source_terminal_state": "failed",
        "source_failure_code": "training_failed",
        "parser_classification": "validation_metrics_unlabeled",
        "selected_epoch": 49,
        "checkpoint_relative_path": "work/src/saved/Retain_run/Epoch_49.model",
        "validation_jaccard": 0.49294228538649887,
        "validation_ddi_rate": 0.08670317294583788,
    }
    status["recovery"] = recovery
    result.update(
        artifact_type="training",
        best_epoch=49,
        validation_jaccard=recovery["validation_jaccard"],
        validation_ddi_rate=recovery["validation_ddi_rate"],
        checkpoint={
            "best_epoch": 49,
            "relative_path": recovery["checkpoint_relative_path"],
            "sha256": hashlib.sha256(CHECKPOINT_BYTES).hexdigest(),
            "size_bytes": len(CHECKPOINT_BYTES),
        },
        recovery=recovery,
    )
    return status, result


def test_finalization_reopens_only_matching_sibling_pair(tmp_path: Path) -> None:
    status, result = _pair()

    finalize_evidence_pair(tmp_path, status=status, result=result)

    reopened_status, reopened_result = reopen_finalized_pair(
        tmp_path,
        expected_identity=_identity(),
    )
    assert reopened_status == status
    assert reopened_result == result
    assert (tmp_path / "finalization.json").is_file()


def test_finalization_rejects_mismatched_identity() -> None:
    status, result = _pair()
    result["identity"] = _identity(submission_id="submission-2")

    with pytest.raises(ProtocolValidationError, match="identities do not match"):
        validate_status_result_pair(status, result)


def test_reopen_rejects_status_result_without_finalization_marker(tmp_path: Path) -> None:
    (tmp_path / "status.json").write_text("{}", encoding="utf-8")
    (tmp_path / "result.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ProtocolValidationError, match="finalization marker"):
        reopen_finalized_pair(tmp_path)


def test_reopen_rejects_active_submission_mismatch(tmp_path: Path) -> None:
    status, result = _pair()
    finalize_evidence_pair(tmp_path, status=status, result=result)

    with pytest.raises(ProtocolValidationError, match="active submission"):
        reopen_finalized_pair(tmp_path, expected_identity=_identity(submission_id="recovered"))


def test_recovered_training_evidence_reopens_with_its_failed_source(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    recovery_root = source_root / "recoveries" / "finalizer-1"
    source_status, source_result = _failed_training_pair()
    recovered_status, recovered_result = _recovered_training_pair()
    finalize_evidence_pair(source_root, status=source_status, result=source_result)
    finalize_evidence_pair(recovery_root, status=recovered_status, result=recovered_result)
    checkpoint_path = source_root / recovered_result["checkpoint"]["relative_path"]
    checkpoint_path.parent.mkdir(parents=True)
    checkpoint_path.write_bytes(CHECKPOINT_BYTES)

    status, result = reopen_recovered_finalized_pair(
        source_root,
        recovery_root,
        expected_identity=_identity(),
    )

    assert status["state"] == "completed"
    assert result["artifact_type"] == "training"
    assert result["recovery"]["finalizer_revision"] == "e" * 40
    assert "rounds" not in result
    assert "test_metrics" not in result


def test_recovered_training_evidence_rejects_checkpoint_replacement(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    recovery_root = source_root / "recoveries" / "finalizer-1"
    source_status, source_result = _failed_training_pair()
    recovered_status, recovered_result = _recovered_training_pair()
    finalize_evidence_pair(source_root, status=source_status, result=source_result)
    finalize_evidence_pair(recovery_root, status=recovered_status, result=recovered_result)
    checkpoint_path = source_root / recovered_result["checkpoint"]["relative_path"]
    checkpoint_path.parent.mkdir(parents=True)
    checkpoint_path.write_bytes(b"substitute")

    with pytest.raises(ProtocolValidationError, match="checkpoint identity"):
        reopen_recovered_finalized_pair(source_root, recovery_root)


def test_recovered_training_evidence_rejects_provenance_tampering(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    recovery_root = source_root / "recoveries" / "finalizer-1"
    source_status, source_result = _failed_training_pair()
    recovered_status, recovered_result = _recovered_training_pair()
    recovered_status["recovery"] = {
        **recovered_status["recovery"],
        "finalizer_revision": "d" * 40,
    }
    finalize_evidence_pair(source_root, status=source_status, result=source_result)
    finalize_evidence_pair(recovery_root, status=recovered_status, result=recovered_result)

    with pytest.raises(ProtocolValidationError, match="provenance do not match"):
        reopen_recovered_finalized_pair(source_root, recovery_root)


def test_recovered_training_evidence_rejects_source_identity_tampering(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    recovery_root = source_root / "recoveries" / "finalizer-1"
    source_status, source_result = _failed_training_pair()
    recovered_status, recovered_result = _recovered_training_pair()
    finalize_evidence_pair(source_root, status=source_status, result=source_result)
    finalize_evidence_pair(recovery_root, status=recovered_status, result=recovered_result)
    source_result["identity"] = _identity(submission_id="tampered")
    (source_root / "result.json").write_text(json.dumps(source_result), encoding="utf-8")

    with pytest.raises(ProtocolValidationError, match="identities do not match"):
        reopen_recovered_finalized_pair(source_root, recovery_root)
