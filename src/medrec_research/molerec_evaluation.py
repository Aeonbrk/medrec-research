"""Attempt-owned preparation for the five MoleRec Table 1 evaluations."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ._validation import parse_json_object, require_identifier, write_json_atomic
from .errors import ProtocolValidationError
from .evaluation_queue import (
    admit_validated_training_evaluation,
    claim_next_evaluation,
    create_evaluation_queue,
    finalize_evaluation,
    load_evaluation_queue,
    resolve_training_artifact,
)
from .molerec_reproduction_audit import audit_molerec_table1
from .registry import BaselineRegistry
from .remote_executor import RemoteExecutor
from .reproduction_evidence import reopen_finalized_pair, reopen_training_evidence
from .safedrug_selection import (
    SAFE_DRUG_LANE_IDS,
    candidate_from_training_evidence,
    require_selected_safedrug_lane,
    select_safedrug_candidate,
    write_selection,
)

_FIXED_TEST_LANES = (
    "molerec-retain",
    "molerec-leap",
    "molerec-gamenet",
    "molerec-embedding",
)
_PAPER_BASELINES = ("retain", "leap", "gamenet", "safedrug", "molerec")


def _test_submission_id(continuation_id: str, lane_id: str) -> str:
    return f"{continuation_id}-test-{lane_id}"


def prepare_table1_evaluation(
    *,
    state_root: str | Path,
    registry: BaselineRegistry,
    attempt_root: str | Path,
    attempt_id: str,
    continuation_id: str,
    training_artifact_ids: Mapping[str, str],
    training_harness_revision: str,
    harness_revision: str,
    preprocessing_revision: str,
    snapshot_id: str,
    environment_sha256: str,
) -> dict[str, Any]:
    """Select SafeDrug and atomically publish the exact five-test controller state."""
    destination = Path(state_root)
    if destination.exists():
        raise ProtocolValidationError(f"evaluation state already exists: {destination}")
    continuation_id = require_identifier(continuation_id, field="continuation_id")
    lanes = tuple(registry.reproduction_lanes)
    lane_ids = tuple(lane.lane_id for lane in lanes)
    if set(training_artifact_ids) != set(lane_ids):
        raise ProtocolValidationError(
            "evaluation preparation requires exactly seven training artifacts"
        )
    if len(set(training_artifact_ids.values())) != len(lane_ids):
        raise ProtocolValidationError("evaluation training artifacts must be unique")

    evidence_by_lane: dict[str, dict[str, Any]] = {}
    roots_by_lane: dict[str, tuple[Path, Path | None]] = {}
    for lane in lanes:
        training_root, source_root, _ = resolve_training_artifact(
            attempt_root,
            training_artifact_ids[lane.lane_id],
        )
        evidence = reopen_training_evidence(
            training_root,
            source_run_root=source_root,
        )
        identity = evidence["identity"]
        baseline = registry.get(lane.scientific_baseline_id)
        expected = {
            "attempt_id": attempt_id,
            "lane_id": lane.lane_id,
            "scientific_baseline_id": lane.scientific_baseline_id,
            "program_id": lane.program_id,
            "profile_id": lane.profile_id,
            "harness_revision": training_harness_revision,
            "model_source_revision": baseline.source.revision,
            "preprocessing_revision": preprocessing_revision,
            "snapshot_id": snapshot_id,
            "environment_sha256": environment_sha256,
            "mode": "formal",
        }
        if any(identity.get(field) != value for field, value in expected.items()):
            raise ProtocolValidationError(
                f"evaluation lane '{lane.lane_id}' training identity is not authoritative"
            )
        evidence_by_lane[lane.lane_id] = evidence
        roots_by_lane[lane.lane_id] = (training_root, source_root)

    candidates = [
        candidate_from_training_evidence(
            lane_id,
            training_run_root=roots_by_lane[lane_id][0],
            source_run_root=roots_by_lane[lane_id][1],
            expected_identity=evidence_by_lane[lane_id]["identity"],
        )
        for lane_id in SAFE_DRUG_LANE_IDS
    ]
    selection = select_safedrug_candidate(candidates)
    selected_lane = selection.get("selected_lane_id")
    if not isinstance(selected_lane, str):
        raise ProtocolValidationError("SafeDrug selection is incomplete")
    selected_candidate = require_selected_safedrug_lane(selection, selected_lane)
    test_lanes = (*_FIXED_TEST_LANES[:3], selected_lane, _FIXED_TEST_LANES[3])
    lane_by_id = {lane.lane_id: lane for lane in lanes}
    test_lane_ids = dict(zip(_PAPER_BASELINES, test_lanes, strict=True))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        dir=destination.parent,
        prefix=f".{destination.name}.",
    ) as temporary:
        staging = Path(temporary) / "state"
        staging.mkdir()
        selection_path = staging / "selection.json"
        queue_path = staging / "evaluation-queue.json"
        write_selection(selection_path, selection)
        create_evaluation_queue(queue_path, attempt_id=attempt_id)
        for lane_id in test_lanes:
            lane = lane_by_id[lane_id]
            admit_validated_training_evaluation(
                queue_path,
                attempt_root=attempt_root,
                lane_id=lane_id,
                scientific_baseline_id=lane.scientific_baseline_id,
                training_artifact_id=training_artifact_ids[lane_id],
                test_submission_id=_test_submission_id(continuation_id, lane_id),
                expected_identity=evidence_by_lane[lane_id]["identity"],
                selection=selection if lane_id == selected_lane else None,
            )

        ledger_lanes: dict[str, dict[str, Any]] = {}
        for lane in lanes:
            is_test_lane = lane.lane_id in test_lanes
            baseline = registry.get(lane.scientific_baseline_id)
            ledger_lanes[lane.lane_id] = {
                "scientific_baseline_id": lane.scientific_baseline_id,
                "program_id": lane.program_id,
                "profile_id": lane.profile_id,
                "model_source_revision": baseline.source.revision,
                "active_submission_id": (
                    _test_submission_id(continuation_id, lane.lane_id)
                    if is_test_lane
                    else evidence_by_lane[lane.lane_id]["identity"]["submission_id"]
                ),
                "state": "queued" if is_test_lane else "not_tested_by_design",
            }
        write_json_atomic(
            staging / "ledger.json",
            {
                "schema_version": 2,
                "kind": "molerec_table1_attempt_ledger_v2",
                "attempt_id": attempt_id,
                "continuation_id": continuation_id,
                "harness_revision": harness_revision,
                "preprocessing_revision": preprocessing_revision,
                "snapshot_id": snapshot_id,
                "environment_sha256": environment_sha256,
                "test_lane_ids": test_lane_ids,
                "lanes": ledger_lanes,
            },
        )
        write_json_atomic(
            staging / "five-model-comparison-preregistration.json",
            {
                "schema_version": 1,
                "kind": "five_model_comparison_preregistration",
                "attempt_id": attempt_id,
                "continuation_id": continuation_id,
                "harness_revision": harness_revision,
                "protocol_version": "1.1",
                "selected_safedrug_lane": selected_lane,
                "selected_safedrug_learning_rate": selected_candidate["learning_rate"],
                "adaptation_budget_rule": (
                    "Baseline Core unchanged; only representation, invocation, and identifier "
                    "translation are admissible"
                ),
                "scope_derivation": (
                    "derive one runtime Comparison Scope from the accepted Dataset Manifest "
                    "before any Comparison test evaluation"
                ),
                "models": [
                    {
                        "lane_id": lane_id,
                        "scientific_baseline_id": lane_by_id[lane_id].scientific_baseline_id,
                        "program_id": lane_by_id[lane_id].program_id,
                        "profile_id": lane_by_id[lane_id].profile_id,
                        "model_source_revision": registry.get(
                            lane_by_id[lane_id].scientific_baseline_id
                        ).source.revision,
                        "training_artifact_id": training_artifact_ids[lane_id],
                        "test_submission_id": _test_submission_id(continuation_id, lane_id),
                        "seed_declaration": "upstream source default; no controller override",
                        "decoder_declaration": (
                            "source-native prediction and frozen upstream ten-round evaluation"
                        ),
                    }
                    for lane_id in test_lanes
                ],
            },
        )
        os.replace(staging, destination)

    return {
        "attempt_id": attempt_id,
        "continuation_id": continuation_id,
        "selected_safedrug_lane": selected_lane,
        "test_lane_ids": test_lane_ids,
        "state_root": destination,
    }


def _load_ledger(state_root: str | Path) -> tuple[Path, dict[str, Any]]:
    path = Path(state_root) / "ledger.json"
    try:
        ledger = parse_json_object(path.read_text(encoding="utf-8"), context="attempt ledger")
    except OSError as error:
        raise ProtocolValidationError("attempt ledger could not be read") from error
    if ledger.get("schema_version") != 2 or ledger.get("kind") != (
        "molerec_table1_attempt_ledger_v2"
    ):
        raise ProtocolValidationError("attempt ledger contract is invalid")
    return path, ledger


def _continuation_test_root(
    attempt_root: str | Path,
    ledger: Mapping[str, Any],
    lane_id: str,
) -> Path:
    continuation_id = require_identifier(
        ledger.get("continuation_id"),
        field="ledger.continuation_id",
    )
    return Path(attempt_root) / "continuations" / continuation_id / "tests" / lane_id


def claim_table1_evaluation(
    *,
    state_root: str | Path,
    registry: BaselineRegistry,
    attempt_root: str | Path,
    remote_root: str,
    data_root: str,
) -> dict[str, Any] | None:
    """Claim one queued lane and return its frozen recovered-test command."""
    state = Path(state_root)
    if not (state / "five-model-comparison-preregistration.json").is_file():
        raise ProtocolValidationError("Comparison preregistration must exist before test claim")
    queue_path = state / "evaluation-queue.json"
    queue = load_evaluation_queue(queue_path)
    if any(entry["state"] in ("failed", "blocked") for entry in queue["entries"]):
        raise ProtocolValidationError(
            "evaluation attempt is terminal after a failed or blocked lane"
        )
    if any(entry["state"] == "running" for entry in queue["entries"]):
        return None
    entry = next((item for item in queue["entries"] if item["state"] == "queued"), None)
    if entry is None:
        return None
    _, ledger = _load_ledger(state)
    if ledger.get("attempt_id") != queue["attempt_id"]:
        raise ProtocolValidationError("queue and ledger attempts do not match")
    training_root, source_root, _ = resolve_training_artifact(
        attempt_root,
        entry["training_artifact_id"],
    )
    if source_root is None:
        raise ProtocolValidationError("formal continuation test requires recovered evidence")
    test_root = _continuation_test_root(attempt_root, ledger, entry["lane_id"])
    selection_path = (
        str((state / "selection.json").resolve())
        if entry["lane_id"].startswith("molerec-safedrug")
        else None
    )
    command = RemoteExecutor(registry).test_launch_command(
        entry["lane_id"],
        attempt_id=queue["attempt_id"],
        submission_id=entry["test_submission_id"],
        harness_revision=ledger["harness_revision"],
        remote_root=remote_root,
        data_root=data_root,
        recovery_run_root=str(training_root.resolve()),
        training_source_root=str(source_root.resolve()),
        test_root=str(test_root.resolve()),
        selection_path=selection_path,
    )
    claimed = claim_next_evaluation(queue_path)
    if claimed is None or claimed["test_submission_id"] != entry["test_submission_id"]:
        raise ProtocolValidationError("evaluation queue claim changed unexpectedly")
    return {"command": command, "entry": claimed}


def finalize_table1_evaluation(
    *,
    state_root: str | Path,
    attempt_root: str | Path,
) -> dict[str, Any]:
    """Reopen one running terminal pair before advancing queue and ledger state."""
    state = Path(state_root)
    queue_path = state / "evaluation-queue.json"
    queue = load_evaluation_queue(queue_path)
    running = [entry for entry in queue["entries"] if entry["state"] == "running"]
    if len(running) != 1:
        raise ProtocolValidationError("exactly one running evaluation is required")
    entry = running[0]
    ledger_path, ledger = _load_ledger(state)
    lane = ledger["lanes"][entry["lane_id"]]
    expected_identity = {
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
    resolve_training_artifact(
        attempt_root,
        entry["training_artifact_id"],
    )
    test_root = _continuation_test_root(attempt_root, ledger, entry["lane_id"])
    status, result = reopen_finalized_pair(
        test_root,
        expected_identity=expected_identity,
    )
    state_value = "completed" if status["state"] == "completed" else "failed"
    if result.get("artifact_type") != "test":
        raise ProtocolValidationError("terminal evaluation pair is not a test artifact")
    try:
        result_artifact_id = (
            (test_root / "result.json")
            .resolve()
            .relative_to(Path(attempt_root).resolve())
            .as_posix()
        )
    except ValueError as error:
        raise ProtocolValidationError("test result is outside the attempt root") from error
    ledger["lanes"][entry["lane_id"]]["state"] = state_value
    write_json_atomic(ledger_path, ledger)
    return finalize_evaluation(
        queue_path,
        lane_id=entry["lane_id"],
        state=state_value,
        result_artifact_id=result_artifact_id,
    )


def audit_prepared_table1_evaluation(
    *,
    state_root: str | Path,
    attempt_root: str | Path,
    output_path: str | Path,
    reference_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the four-axis audit only after five validated completed queue entries."""
    state = Path(state_root)
    queue = load_evaluation_queue(state / "evaluation-queue.json")
    if len(queue["entries"]) != 5 or any(
        entry["state"] != "completed" for entry in queue["entries"]
    ):
        raise ProtocolValidationError("five completed evaluation pairs are required for audit")
    _, ledger = _load_ledger(state)
    entry_by_lane = {entry["lane_id"]: entry for entry in queue["entries"]}
    result_paths: dict[str, Path] = {}
    for baseline_id, lane_id in ledger["test_lane_ids"].items():
        entry = entry_by_lane.get(lane_id)
        if entry is None or "result_artifact_id" not in entry:
            raise ProtocolValidationError("audit queue and ledger lane identities do not match")
        result_paths[baseline_id] = Path(attempt_root) / entry["result_artifact_id"]
    return audit_molerec_table1(
        ledger_path=state / "ledger.json",
        result_paths=result_paths,
        output_path=Path(output_path),
        reference_path=Path(reference_path) if reference_path is not None else None,
        selection_path=state / "selection.json",
    )


__all__ = (
    "audit_prepared_table1_evaluation",
    "claim_table1_evaluation",
    "finalize_table1_evaluation",
    "prepare_table1_evaluation",
)
