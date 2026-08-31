"""Persistent GPU 7 evaluation queue for the MoleRec Table 1 attempt."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .._validation import (
    parse_json_object,
    require_identifier,
    require_int,
    require_string,
    strict_fields,
    write_json_atomic,
)
from ..errors import ProtocolValidationError
from .molerec_table1_attempt import ReproductionAttemptDeclaration
from .reproduction_evidence import (
    canonical_training_artifact_id,
    reopen_training_evidence,
    resolve_training_artifact,
)
from .safedrug_selection import SAFE_DRUG_LANE_IDS, require_selected_safedrug_lane

QUEUE_SCHEMA_VERSION = 1
QUEUE_KIND = "molerec_table1_evaluation_queue_v1"
EVALUATION_GPU_INDEX = 7
QUEUE_STATES = ("queued", "running", "completed", "failed", "blocked")
TERMINAL_QUEUE_STATES = ("completed", "failed", "blocked")


def new_evaluation_queue(attempt_id: str) -> dict[str, Any]:
    """Return an empty queue reserved for serial evaluation on GPU 7."""
    return {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "kind": QUEUE_KIND,
        "attempt_id": require_identifier(attempt_id, field="attempt_id"),
        "evaluation_gpu_index": EVALUATION_GPU_INDEX,
        "entries": [],
    }


def _validate_entry(
    value: object,
    *,
    index: int,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> dict[str, Any]:
    payload = strict_fields(
        value,
        required=(
            "lane_id",
            "scientific_baseline_id",
            "training_artifact_id",
            "test_submission_id",
            "state",
        ),
        optional=("selection_lane_id", "result_artifact_id"),
        context=f"evaluation queue entry {index}",
    )
    lane_id = require_identifier(payload["lane_id"], field=f"queue entry {index}.lane_id")
    scientific_baseline_id = require_identifier(
        payload["scientific_baseline_id"],
        field=f"queue entry {index}.scientific_baseline_id",
    )
    if declaration is not None:
        if not declaration.has_lane(lane_id):
            raise ProtocolValidationError(
                f"evaluation queue entry {index} names an undeclared lane: {lane_id}"
            )
        lane_decl = declaration.get_lane(lane_id)
        if scientific_baseline_id != lane_decl.scientific_baseline_id:
            raise ProtocolValidationError(
                f"evaluation queue entry {index} has the wrong scientific baseline"
            )
        is_safedrug = lane_decl.scientific_baseline_id == "safedrug"
    else:
        is_safedrug = lane_id in SAFE_DRUG_LANE_IDS

    state = require_identifier(payload["state"], field=f"queue entry {index}.state")
    if state not in QUEUE_STATES:
        raise ProtocolValidationError(f"queue entry {index}.state is not a valid queue state")
    training_artifact_id = require_string(
        payload["training_artifact_id"],
        field=f"queue entry {index}.training_artifact_id",
    )
    test_submission_id = require_identifier(
        payload["test_submission_id"],
        field=f"queue entry {index}.test_submission_id",
    )

    selection_lane_id = payload.get("selection_lane_id")
    if selection_lane_id is not None:
        selection_lane_id = require_identifier(
            selection_lane_id,
            field=f"queue entry {index}.selection_lane_id",
        )
    if is_safedrug and selection_lane_id != lane_id:
        raise ProtocolValidationError(f"SafeDrug queue entry {index} must record its selected lane")
    if not is_safedrug and selection_lane_id is not None:
        raise ProtocolValidationError(
            f"non-SafeDrug queue entry {index} must not contain selection_lane_id"
        )

    result_artifact_id = payload.get("result_artifact_id")
    if result_artifact_id is not None:
        result_artifact_id = require_string(
            result_artifact_id,
            field=f"queue entry {index}.result_artifact_id",
        )
    if state == "completed" and result_artifact_id is None:
        raise ProtocolValidationError(
            f"completed queue entry {index} must identify its result artifact"
        )

    entry: dict[str, Any] = {
        "lane_id": lane_id,
        "scientific_baseline_id": scientific_baseline_id,
        "training_artifact_id": training_artifact_id,
        "test_submission_id": test_submission_id,
        "state": state,
    }
    if selection_lane_id is not None:
        entry["selection_lane_id"] = selection_lane_id
    if result_artifact_id is not None:
        entry["result_artifact_id"] = result_artifact_id
    return entry


def validate_evaluation_queue(
    value: object,
    *,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> dict[str, Any]:
    """Validate and normalize a persisted queue without changing its order."""
    payload = strict_fields(
        value,
        required=("schema_version", "kind", "attempt_id", "evaluation_gpu_index", "entries"),
        context="MoleRec evaluation queue",
    )
    if payload["schema_version"] != QUEUE_SCHEMA_VERSION or payload["kind"] != QUEUE_KIND:
        raise ProtocolValidationError("MoleRec evaluation queue has an unsupported schema")
    attempt_id = require_identifier(payload["attempt_id"], field="queue.attempt_id")
    if declaration is not None and declaration.attempt_id != attempt_id:
        raise ProtocolValidationError("queue attempt_id does not match declaration attempt_id")
    evaluation_gpu_index = require_int(
        payload["evaluation_gpu_index"],
        field="queue.evaluation_gpu_index",
        minimum=0,
    )
    if evaluation_gpu_index != EVALUATION_GPU_INDEX:
        raise ProtocolValidationError("MoleRec evaluation queue must reserve GPU 7")
    raw_entries = payload["entries"]
    if not isinstance(raw_entries, list):
        raise ProtocolValidationError("MoleRec evaluation queue entries must be a list")

    entries = [
        _validate_entry(entry, index=index, declaration=declaration)
        for index, entry in enumerate(raw_entries)
    ]
    lane_ids = [entry["lane_id"] for entry in entries]
    if len(lane_ids) != len(set(lane_ids)):
        raise ProtocolValidationError("MoleRec evaluation queue cannot contain duplicate lanes")
    submission_ids = [entry["test_submission_id"] for entry in entries]
    if len(submission_ids) != len(set(submission_ids)):
        raise ProtocolValidationError(
            "MoleRec evaluation queue cannot contain duplicate test submissions"
        )
    if sum(entry["state"] == "running" for entry in entries) > 1:
        raise ProtocolValidationError("MoleRec evaluation queue can run only one GPU 7 test")
    return {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "kind": QUEUE_KIND,
        "attempt_id": attempt_id,
        "evaluation_gpu_index": EVALUATION_GPU_INDEX,
        "entries": entries,
    }


def load_evaluation_queue(
    path: str | Path,
    *,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> dict[str, Any]:
    """Read and validate a queue file."""
    queue_path = Path(path)
    try:
        value = parse_json_object(
            queue_path.read_text(encoding="utf-8"),
            context="MoleRec evaluation queue",
        )
    except OSError as error:
        raise ProtocolValidationError(f"failed to read evaluation queue: {error}") from error
    if declaration is None:
        decl_path = queue_path.parent / "attempt_declaration.json"
        if decl_path.is_file():
            declaration = ReproductionAttemptDeclaration.from_json(decl_path)
    return validate_evaluation_queue(value, declaration=declaration)


def write_evaluation_queue(
    path: str | Path,
    queue: Mapping[str, Any],
    *,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> dict[str, Any]:
    """Validate and atomically write a queue, returning its normalized form."""
    normalized = validate_evaluation_queue(queue, declaration=declaration)
    write_json_atomic(path, normalized)
    return normalized


def create_evaluation_queue(
    path: str | Path,
    *,
    attempt_id: str,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> dict[str, Any]:
    """Create a queue exactly once."""
    queue_path = Path(path)
    if queue_path.exists():
        raise ProtocolValidationError(f"evaluation queue already exists: {queue_path}")
    if declaration is not None and declaration.attempt_id != attempt_id:
        raise ProtocolValidationError("queue attempt_id does not match declaration attempt_id")
    return write_evaluation_queue(
        queue_path,
        new_evaluation_queue(attempt_id),
        declaration=declaration,
    )


def admit_evaluation(
    path: str | Path,
    *,
    lane_id: str,
    scientific_baseline_id: str,
    training_artifact_id: str,
    test_submission_id: str,
    selection: Mapping[str, Any] | None = None,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> dict[str, Any]:
    """Append one eligible test to the FIFO queue, failing closed on duplicates."""
    queue = load_evaluation_queue(path, declaration=declaration)
    lane_id = require_identifier(lane_id, field="lane_id")
    scientific_baseline_id = require_identifier(
        scientific_baseline_id,
        field="scientific_baseline_id",
    )
    if declaration is not None:
        if not declaration.has_lane(lane_id):
            raise ProtocolValidationError(
                f"evaluation queue cannot admit undeclared lane: {lane_id}"
            )
        lane_decl = declaration.get_lane(lane_id)
        if scientific_baseline_id != lane_decl.scientific_baseline_id:
            raise ProtocolValidationError("evaluation admission has the wrong scientific baseline")
        is_safedrug = lane_decl.scientific_baseline_id == "safedrug"
    else:
        is_safedrug = lane_id in SAFE_DRUG_LANE_IDS
    if any(entry["lane_id"] == lane_id for entry in queue["entries"]):
        raise ProtocolValidationError(f"evaluation for lane '{lane_id}' is already queued")
    test_submission_id = require_identifier(test_submission_id, field="test_submission_id")
    if any(entry["test_submission_id"] == test_submission_id for entry in queue["entries"]):
        raise ProtocolValidationError(f"test submission '{test_submission_id}' is already queued")

    entry: dict[str, Any] = {
        "lane_id": lane_id,
        "scientific_baseline_id": scientific_baseline_id,
        "training_artifact_id": require_string(
            training_artifact_id,
            field="training_artifact_id",
        ),
        "test_submission_id": test_submission_id,
        "state": "queued",
    }
    if is_safedrug:
        if selection is None:
            raise ProtocolValidationError(
                "SafeDrug evaluation admission requires a valid selection.json"
            )
        require_selected_safedrug_lane(selection, lane_id)
        entry["selection_lane_id"] = lane_id

    entry = _validate_entry(entry, index=len(queue["entries"]), declaration=declaration)
    queue["entries"].append(entry)
    write_evaluation_queue(path, queue, declaration=declaration)
    return entry


def admit_validated_training_evaluation(
    path: str | Path,
    *,
    attempt_root: str | Path,
    lane_id: str,
    scientific_baseline_id: str,
    training_artifact_id: str,
    test_submission_id: str,
    expected_identity: Mapping[str, Any] | None = None,
    selection: Mapping[str, Any] | None = None,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> dict[str, Any]:
    """Validate terminal training evidence before admitting one GPU 7 evaluation."""
    if declaration is None:
        decl_path = Path(path).parent / "attempt_declaration.json"
        if decl_path.is_file():
            declaration = ReproductionAttemptDeclaration.from_json(decl_path)
        else:
            attempt_decl_path = Path(attempt_root) / "attempt_declaration.json"
            if attempt_decl_path.is_file():
                declaration = ReproductionAttemptDeclaration.from_json(attempt_decl_path)

    queue = load_evaluation_queue(path, declaration=declaration)
    lane_id = require_identifier(lane_id, field="lane_id")
    scientific_baseline_id = require_identifier(
        scientific_baseline_id,
        field="scientific_baseline_id",
    )
    if declaration is not None:
        if not declaration.has_lane(lane_id):
            raise ProtocolValidationError(
                f"evaluation queue cannot admit undeclared lane: {lane_id}"
            )
        lane_decl = declaration.get_lane(lane_id)
        if scientific_baseline_id != lane_decl.scientific_baseline_id:
            raise ProtocolValidationError("evaluation admission has the wrong scientific baseline")
        is_safedrug = lane_decl.scientific_baseline_id == "safedrug"
    else:
        is_safedrug = lane_id in SAFE_DRUG_LANE_IDS

    if any(entry["state"] == "running" for entry in queue["entries"]):
        raise ProtocolValidationError("GPU 7 evaluation is already active")

    training_root, source_root, _ = resolve_training_artifact(
        attempt_root,
        training_artifact_id,
    )
    evidence = reopen_training_evidence(
        training_root,
        source_run_root=source_root,
        expected_identity=expected_identity,
    )
    identity = evidence["identity"]
    if identity["attempt_id"] != queue["attempt_id"]:
        raise ProtocolValidationError("training evidence belongs to a different queue attempt")
    if declaration is not None:
        lane_decl = declaration.get_lane(lane_id)
        if (
            identity["lane_id"] != lane_id
            or identity["scientific_baseline_id"] != scientific_baseline_id
            or identity["program_id"] != lane_decl.program_id
            or identity["profile_id"] != lane_decl.profile_id
            or identity["mode"] != "formal"
        ):
            raise ProtocolValidationError("training evidence does not name the admitted lane")
    elif (
        identity["lane_id"] != lane_id
        or identity["scientific_baseline_id"] != scientific_baseline_id
        or identity["mode"] != "formal"
    ):
        raise ProtocolValidationError("training evidence does not name the admitted lane")

    if is_safedrug:
        if selection is None:
            raise ProtocolValidationError(
                "SafeDrug evaluation admission requires a valid selection.json"
            )
        if selection.get("selected_lane_id") != lane_id:
            raise ProtocolValidationError(f"SafeDrug lane '{lane_id}' remains not_tested_by_design")
        selected_candidate = require_selected_safedrug_lane(selection, lane_id)
        result = evidence["result"]
        selected_evidence = selected_candidate["training_evidence"]
        if (
            selected_evidence["identity"] != identity
            or selected_evidence["checkpoint"] != evidence["checkpoint"]
            or selected_evidence["recovery"] != result.get("recovery")
            or selected_candidate["checkpoint_identity"] != evidence["checkpoint"]["sha256"]
            or selected_candidate["learning_rate"] != result.get("learning_rate")
            or selected_candidate["validation_jaccard"] != evidence["validation_jaccard"]
            or selected_candidate["validation_ddi_rate"] != evidence["validation_ddi_rate"]
        ):
            raise ProtocolValidationError(
                "SafeDrug selection does not match the admitted training evidence"
            )

    canonical_id = canonical_training_artifact_id(attempt_root, training_root)
    return admit_evaluation(
        path,
        lane_id=lane_id,
        scientific_baseline_id=scientific_baseline_id,
        training_artifact_id=canonical_id,
        test_submission_id=test_submission_id,
        selection=selection,
        declaration=declaration,
    )


def claim_next_evaluation(
    path: str | Path,
    *,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> dict[str, Any] | None:
    """Claim the oldest queued evaluation; terminal entries are never replayed."""
    queue = load_evaluation_queue(path, declaration=declaration)
    if any(entry["state"] == "running" for entry in queue["entries"]):
        return None
    for entry in queue["entries"]:
        if entry["state"] == "queued":
            entry["state"] = "running"
            write_evaluation_queue(path, queue, declaration=declaration)
            return dict(entry)
    return None


def finalize_evaluation(
    path: str | Path,
    *,
    lane_id: str,
    state: str,
    result_artifact_id: str | None = None,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> dict[str, Any]:
    """Mark one claimed evaluation terminal without allowing a second submission."""
    lane_id = require_identifier(lane_id, field="lane_id")
    state = require_identifier(state, field="state")
    if state not in TERMINAL_QUEUE_STATES:
        raise ProtocolValidationError("evaluation final state must be terminal")
    queue = load_evaluation_queue(path, declaration=declaration)
    for entry in queue["entries"]:
        if entry["lane_id"] != lane_id:
            continue
        if entry["state"] in TERMINAL_QUEUE_STATES:
            if entry["state"] == state and entry.get("result_artifact_id") == result_artifact_id:
                return dict(entry)
            raise ProtocolValidationError(f"evaluation for lane '{lane_id}' is already terminal")
        if entry["state"] != "running":
            raise ProtocolValidationError(f"evaluation for lane '{lane_id}' is not running")
        if state == "completed" or result_artifact_id is not None:
            entry["result_artifact_id"] = require_string(
                result_artifact_id,
                field="result_artifact_id",
            )
        entry["state"] = state
        write_evaluation_queue(path, queue, declaration=declaration)
        return dict(entry)
    raise ProtocolValidationError(f"evaluation for lane '{lane_id}' is not queued")


def requeue_interrupted_evaluations(
    path: str | Path,
    *,
    declaration: ReproductionAttemptDeclaration | None = None,
) -> int:
    """Return non-terminal running entries to FIFO after an operator-verified interruption."""
    queue = load_evaluation_queue(path, declaration=declaration)
    changed = 0
    for entry in queue["entries"]:
        if entry["state"] == "running":
            entry["state"] = "queued"
            changed += 1
    if changed:
        write_evaluation_queue(path, queue, declaration=declaration)
    return changed


__all__ = (
    "EVALUATION_GPU_INDEX",
    "QUEUE_KIND",
    "QUEUE_SCHEMA_VERSION",
    "QUEUE_STATES",
    "TERMINAL_QUEUE_STATES",
    "admit_evaluation",
    "admit_validated_training_evaluation",
    "claim_next_evaluation",
    "create_evaluation_queue",
    "finalize_evaluation",
    "load_evaluation_queue",
    "new_evaluation_queue",
    "requeue_interrupted_evaluations",
    "resolve_training_artifact",
    "validate_evaluation_queue",
    "write_evaluation_queue",
)
