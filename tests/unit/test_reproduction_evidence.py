from __future__ import annotations

from pathlib import Path

import pytest

from medrec_research.errors import ProtocolValidationError
from medrec_research.reproduction_evidence import (
    finalize_evidence_pair,
    reopen_finalized_pair,
    validate_status_result_pair,
)


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
