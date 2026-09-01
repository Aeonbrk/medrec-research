from __future__ import annotations

from pathlib import Path

import pytest

from baselines.reproduction_artifacts import (
    IDENTITY_ENVIRONMENT_FIELDS,
    finalize_v2_pair,
    identity_from_environment,
    reopen_v2_pair,
)


def _identity(*, mode: str = "formal", submission_id: str = "submission-1") -> dict[str, str]:
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
        "mode": mode,
        "submission_id": submission_id,
    }


def test_controller_identity_rejects_partial_and_wrong_mode() -> None:
    environment = {
        name: (
            "formal"
            if name == "MEDREC_MODE"
            else "d" * 64
            if name == "MEDREC_ENVIRONMENT_SHA256"
            else "a" * 40
            if "REVISION" in name
            else name.lower().replace("medrec_", "")
        )
        for name in IDENTITY_ENVIRONMENT_FIELDS.values()
    }
    identity = identity_from_environment(mode="formal", environ=environment, error_type=ValueError)
    assert identity is not None
    assert identity["lane_id"] == "lane_id"

    partial = dict(environment)
    del partial["MEDREC_SUBMISSION_ID"]
    with pytest.raises(ValueError, match="incomplete"):
        identity_from_environment(mode="formal", environ=partial, error_type=ValueError)

    wrong_mode = dict(environment)
    wrong_mode["MEDREC_MODE"] = "smoke"
    with pytest.raises(ValueError, match="mode"):
        identity_from_environment(mode="formal", environ=wrong_mode, error_type=ValueError)


def test_v2_pair_marker_is_required_for_reopen(tmp_path: Path) -> None:
    identity = _identity()
    common = {
        "schema_version": 2,
        "identity": identity,
        "mode": "formal",
        "state": "completed",
        "non_evidence": False,
    }
    status = {**common, "kind": "reproduction_status_v2", "stage": "terminal"}
    result = {**common, "kind": "reproduction_result_v2", "artifact_type": "training"}
    finalize_v2_pair(tmp_path, status=status, result=result, error_type=ValueError)

    reopened_status, reopened_result = reopen_v2_pair(
        tmp_path,
        expected_identity=identity,
        error_type=ValueError,
    )
    assert reopened_status == status
    assert reopened_result == result

    recovered_identity = _identity(submission_id="submission-2")
    with pytest.raises(ValueError, match="active submission"):
        reopen_v2_pair(
            tmp_path,
            expected_identity=recovered_identity,
            error_type=ValueError,
        )
