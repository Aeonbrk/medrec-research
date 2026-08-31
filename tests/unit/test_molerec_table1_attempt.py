from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from medrec_research import BaselineRegistry, ProtocolValidationError
from medrec_research.reproduction.molerec_table1_attempt import (
    TABLE1_DECLARATION_KIND,
    TABLE1_DECLARATION_SCHEMA_VERSION,
    TABLE1_PREPROCESSING_REVISION,
    FrozenSchedule,
    ReproductionAttemptDeclaration,
    build_table1_test_launch_command,
    validate_reproduction_continuation,
    validate_table1_frozen_schedule,
)

PROJECT_ROOT = Path(__file__).parents[2]
LOCAL_REVISION = "a" * 40
ATTEMPT_ID = "formal-20260828-a09fcab-u8-b"
CONTINUATION_ID = "continuation-20260830-pathfix-1"
SOURCE_HARNESS = "a" * 40
CONTINUATION_HARNESS = "b" * 40
ENVIRONMENT_SHA256 = "6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda"
SNAPSHOT_ID = "snapshots/molerec-table1-c721-www23"
PROJECT_SOURCE_REVISIONS = {
    "safedrug_archived": "8deee38cfdb2a38882377ff95cce5922d6d9e8d6",
    "molerec": "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a",
}

SUCCESSOR_LANES = (
    "molerec-retain",
    "molerec-leap",
    "molerec-gamenet",
    "molerec-safedrug-lr-1e-5",
    "molerec-safedrug-lr-1e-4",
    "molerec-safedrug-lr-5e-4",
    "molerec-embedding",
)
SUCCESSOR_MAPPING = {
    "molerec-retain": (3, "12-15,44-47", 0),
    "molerec-leap": (4, "16-19,48-51", 1),
    "molerec-gamenet": (5, "20-23,52-55", 1),
    "molerec-safedrug-lr-1e-5": (6, "24-27,56-59", 1),
    "molerec-safedrug-lr-1e-4": (1, "4-7,36-39", 0),
    "molerec-safedrug-lr-5e-4": (2, "8-11,40-43", 0),
    "molerec-embedding": (0, "0-3,32-35", 0),
}


def _project_schedule(*, harness_revision: str = LOCAL_REVISION) -> FrozenSchedule:
    return FrozenSchedule.from_dict(
        {
            "schema_version": 1,
            "stage": "u7-measured-gpu-schedule",
            "schedule_state": "frozen",
            "harness_revision": harness_revision,
            "environment_sha256": ENVIRONMENT_SHA256,
            "preprocessing_revision": TABLE1_PREPROCESSING_REVISION,
            "snapshot_id": SNAPSHOT_ID,
            "model_source_revisions": PROJECT_SOURCE_REVISIONS,
            "selected_mapping": "balanced-numa",
            "gpu7_reserved": True,
            "reserved_gpu": 7,
            "formal_execution": {
                "mode": "formal",
                "reserved_gpu": 7,
                "gpu_order": [SUCCESSOR_MAPPING[lane][0] for lane in SUCCESSOR_LANES],
                "cpu_set_order": [SUCCESSOR_MAPPING[lane][1] for lane in SUCCESSOR_LANES],
            },
            "mapping": {
                lane: {
                    "gpu": SUCCESSOR_MAPPING[lane][0],
                    "cpu_set": SUCCESSOR_MAPPING[lane][1],
                    "numa": SUCCESSOR_MAPPING[lane][2],
                }
                for lane in SUCCESSOR_LANES
            },
        },
        expected_lane_ids=SUCCESSOR_LANES,
    )


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
    from medrec_research.reproduction.reproduction_evidence import finalize_evidence_pair

    finalize_evidence_pair(root, status=status, result=result)


def test_declaration_creation_from_registry() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)

    assert declaration.attempt_id == ATTEMPT_ID
    assert declaration.schema_version == TABLE1_DECLARATION_SCHEMA_VERSION
    assert declaration.kind == TABLE1_DECLARATION_KIND
    assert declaration.lane_ids == SUCCESSOR_LANES
    assert len(declaration.lanes) == 7

    lane = declaration.get_lane("molerec-safedrug-lr-1e-4")
    assert lane.scientific_baseline_id == "safedrug"
    assert lane.program_id == "safedrug-archived"
    assert lane.profile_id == "safedrug"
    assert lane.learning_rate == 0.0001
    assert lane.formal_test == "only_if_selected"
    assert lane.model_source_revision == "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"


def test_declaration_roundtrip_dict_and_json(tmp_path: Path) -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)
    decl_dict = declaration.to_dict()
    reparsed = ReproductionAttemptDeclaration.from_dict(decl_dict)
    assert reparsed == declaration

    json_path = tmp_path / "attempt_declaration.json"
    declaration.write_atomic(json_path)
    loaded = ReproductionAttemptDeclaration.from_json(json_path)
    assert loaded == declaration


def test_declaration_isolation_from_future_registry_edits() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)

    # Construct a modified registry with different source revision or missing lanes
    modified_toml = (PROJECT_ROOT / "baselines" / "registry.toml").read_text(encoding="utf-8")
    modified_toml = modified_toml.replace("8deee38cfdb2a38882377ff95cce5922d6d9e8d6", "f" * 40)
    modified_registry = BaselineRegistry.from_toml(modified_toml)

    # Original declaration retains its frozen identity
    assert (
        declaration.get_lane("molerec-safedrug-lr-1e-4").model_source_revision
        == "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
    )
    # The modified registry has the new value
    assert modified_registry.get("safedrug").source.revision == "f" * 40


def test_validate_table1_frozen_schedule() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)
    schedule = _project_schedule(harness_revision=LOCAL_REVISION)

    cpu_sets = validate_table1_frozen_schedule(
        schedule,
        source_revision=LOCAL_REVISION,
        attempt_id=ATTEMPT_ID,
        declaration=declaration,
        requested_lanes=tuple((lane, SUCCESSOR_MAPPING[lane][0]) for lane in SUCCESSOR_LANES),
    )
    assert len(cpu_sets) == 7
    assert cpu_sets[0] == SUCCESSOR_MAPPING[SUCCESSOR_LANES[0]][1]


def test_validate_table1_frozen_schedule_rejects_gpu7_training() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)

    # Mutate schedule to assign GPU 7 to a training lane
    bad_dict = _project_schedule().to_dict()
    bad_dict["mapping"]["molerec-retain"]["gpu"] = 7
    bad_dict["formal_execution"]["gpu_order"][0] = 7

    # from_dict or validate should reject
    with pytest.raises(ProtocolValidationError, match=r"reserve GPU 7|assigns reserved GPU 7"):
        bad_schedule = FrozenSchedule.from_dict(bad_dict, declaration=declaration)
        validate_table1_frozen_schedule(
            bad_schedule,
            source_revision=LOCAL_REVISION,
            attempt_id=ATTEMPT_ID,
            declaration=declaration,
        )


def test_validate_table1_frozen_schedule_rejects_mismatched_model_source() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)

    bad_dict = _project_schedule().to_dict()
    bad_dict["model_source_revisions"]["safedrug_archived"] = "0" * 40
    bad_schedule = FrozenSchedule.from_dict(bad_dict, declaration=declaration)

    with pytest.raises(
        ProtocolValidationError, match=r"model source revision for .* is mismatched"
    ):
        validate_table1_frozen_schedule(
            bad_schedule,
            source_revision=LOCAL_REVISION,
            attempt_id=ATTEMPT_ID,
            declaration=declaration,
        )


def test_reaccept_and_validate_reproduction_continuation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)
    source_schedule = _project_schedule(harness_revision=SOURCE_HARNESS)

    attempt_root = tmp_path / "attempt"
    artifact_ids: dict[str, str] = {}
    identities: dict[str, dict[str, str]] = {}
    for lane in declaration.lanes:
        run_root = attempt_root / "lanes" / lane.lane_id
        recovery_root = run_root / "recoveries" / f"rec-{lane.lane_id}"
        recovery_root.mkdir(parents=True)
        artifact_ids[lane.lane_id] = str((recovery_root / "result.json").relative_to(attempt_root))
        identities[lane.lane_id] = {
            "attempt_id": ATTEMPT_ID,
            "lane_id": lane.lane_id,
            "scientific_baseline_id": lane.scientific_baseline_id,
            "program_id": lane.program_id,
            "profile_id": lane.profile_id,
            "harness_revision": SOURCE_HARNESS,
            "model_source_revision": lane.model_source_revision,
            "preprocessing_revision": TABLE1_PREPROCESSING_REVISION,
            "snapshot_id": SNAPSHOT_ID,
            "environment_sha256": ENVIRONMENT_SHA256,
            "mode": "formal",
            "submission_id": f"training-{lane.lane_id}",
        }

    def mock_reopen(training_root: Path, **_: object) -> dict[str, object]:
        lane_id = training_root.parent.parent.name
        return {"identity": identities[lane_id], "result": {"recovery": {}}}

    monkeypatch.setattr(
        "medrec_research.reproduction.molerec_table1_attempt.reopen_training_evidence",
        mock_reopen,
    )

    continuation = validate_reproduction_continuation(
        declaration=declaration,
        source_schedule=source_schedule,
        source_schedule_id="sched-source-1",
        attempt_root=attempt_root,
        attempt_id=ATTEMPT_ID,
        training_artifact_ids=artifact_ids,
        harness_revision=CONTINUATION_HARNESS,
    )
    assert continuation.owner_attempt_id == ATTEMPT_ID
    assert continuation.source_schedule_id == "sched-source-1"
    assert continuation.harness_revision == CONTINUATION_HARNESS
    assert continuation.source_harness_revision == SOURCE_HARNESS


def test_build_table1_test_launch_command() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)

    cmd = build_table1_test_launch_command(
        declaration,
        "molerec-safedrug-lr-1e-4",
        attempt_id=ATTEMPT_ID,
        submission_id="test-submission-1",
        harness_revision=CONTINUATION_HARNESS,
        remote_root="/root/zhb/medrec-research",
        data_root="/root/zhb/medrec-data",
        recovery_run_root="/root/zhb/medrec-data/runs/rec-1",
        training_source_root="/root/zhb/medrec-data/runs/source-1",
        test_root="/root/zhb/medrec-data/runs/test-1",
        selection_path="/root/zhb/medrec-data/selection.json",
    )
    assert "CUDA_VISIBLE_DEVICES=7" in cmd
    assert "--cpu-list 28-31,60-63" in cmd
    assert "MEDREC_LANE_ID=molerec-safedrug-lr-1e-4" in cmd
    assert "--selection /root/zhb/medrec-data/selection.json" in cmd
    assert "--phase test" in cmd


def test_declaration_duplicate_lanes_fails() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)
    lanes = list(declaration.lanes)
    lanes.append(lanes[0])
    with pytest.raises(ProtocolValidationError, match="lane IDs must be unique"):
        ReproductionAttemptDeclaration(attempt_id=ATTEMPT_ID, lanes=tuple(lanes))


def test_validate_table1_frozen_schedule_rejects_missing_lane() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)

    bad_dict = _project_schedule().to_dict()
    del bad_dict["mapping"]["molerec-retain"]
    bad_dict["formal_execution"]["gpu_order"].pop(0)
    bad_dict["formal_execution"]["cpu_set_order"].pop(0)

    with pytest.raises(ProtocolValidationError, match="contain every declared lane"):
        bad_schedule = FrozenSchedule.from_dict(bad_dict, declaration=declaration)
        validate_table1_frozen_schedule(
            bad_schedule,
            source_revision=LOCAL_REVISION,
            attempt_id=ATTEMPT_ID,
            declaration=declaration,
        )


def test_validate_table1_frozen_schedule_rejects_overlapping_gpus() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)

    bad_dict = _project_schedule().to_dict()
    bad_dict["mapping"]["molerec-leap"]["gpu"] = bad_dict["mapping"]["molerec-retain"]["gpu"]
    bad_dict["formal_execution"]["gpu_order"][1] = bad_dict["formal_execution"]["gpu_order"][0]

    with pytest.raises(ProtocolValidationError, match="multiple lanes to the same GPU"):
        bad_schedule = FrozenSchedule.from_dict(bad_dict, declaration=declaration)
        validate_table1_frozen_schedule(
            bad_schedule,
            source_revision=LOCAL_REVISION,
            attempt_id=ATTEMPT_ID,
            declaration=declaration,
        )


def test_validate_table1_frozen_schedule_rejects_invalid_preprocessing_revision() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)

    bad_dict = _project_schedule().to_dict()
    bad_dict["preprocessing_revision"] = "e" * 40
    bad_schedule = FrozenSchedule.from_dict(bad_dict, declaration=declaration)

    with pytest.raises(ProtocolValidationError, match="preprocessing revision is invalid"):
        validate_table1_frozen_schedule(
            bad_schedule,
            source_revision=LOCAL_REVISION,
            attempt_id=ATTEMPT_ID,
            declaration=declaration,
        )


def test_molerec_evaluation_rejects_evidence_identity_mismatch_with_declaration(
    tmp_path: Path,
) -> None:
    from medrec_research.reproduction.molerec_evaluation import prepare_table1_evaluation

    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")
    declaration = ReproductionAttemptDeclaration.from_registry(registry, ATTEMPT_ID)
    attempt_root = tmp_path / "attempt"
    artifact_ids: dict[str, str] = {}
    for lane in declaration.lanes:
        identity = {
            "attempt_id": ATTEMPT_ID,
            "lane_id": lane.lane_id,
            "scientific_baseline_id": lane.scientific_baseline_id,
            "program_id": lane.program_id,
            "profile_id": lane.profile_id,
            "harness_revision": SOURCE_HARNESS,
            "model_source_revision": lane.model_source_revision
            if lane.lane_id != "molerec-retain"
            else "0" * 40,
            "preprocessing_revision": TABLE1_PREPROCESSING_REVISION,
            "snapshot_id": SNAPSHOT_ID,
            "environment_sha256": ENVIRONMENT_SHA256,
            "mode": "formal",
            "submission_id": f"training-{lane.lane_id}",
        }
        run_root = attempt_root / "lanes" / lane.lane_id
        _write_training(run_root, identity=identity, learning_rate=lane.learning_rate)
        artifact_ids[lane.lane_id] = f"lanes/{lane.lane_id}/result.json"

    state_root = tmp_path / "evaluation-state"
    with pytest.raises(ProtocolValidationError, match="training identity is not authoritative"):
        prepare_table1_evaluation(
            state_root=state_root,
            declaration=declaration,
            attempt_root=attempt_root,
            attempt_id=ATTEMPT_ID,
            continuation_id=CONTINUATION_ID,
            training_artifact_ids=artifact_ids,
            training_harness_revision=SOURCE_HARNESS,
            harness_revision=CONTINUATION_HARNESS,
            preprocessing_revision=TABLE1_PREPROCESSING_REVISION,
            snapshot_id=SNAPSHOT_ID,
            environment_sha256=ENVIRONMENT_SHA256,
        )
