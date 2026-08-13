from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from medrec_research.action_gate import ActionRequest
from medrec_research.errors import ProtocolValidationError
from medrec_research.execution_control import (
    STATUS_ACTION_IDS,
    DurableExecutionQueue,
    ExecutionDeclarationRegistry,
    ExecutionState,
)
from medrec_research.project_status import AuthorityDigest, StatusAction

ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)
CONTRACT_SHA256 = "1" * 64
H1_APPROVAL_SHA256 = "2" * 64


def _request(*, action_id: str = "request_reproduction", suffix: str = "a") -> ActionRequest:
    return ActionRequest.create(
        request_id=f"action-context-{suffix * 20}",
        project_id="medrec-research",
        target_id="319-wild",
        action_id=action_id,
        snapshot_sha256="a" * 64,
        scope_sha256="b" * 64,
        authorities=(AuthorityDigest("scope", "b" * 64),),
        authorization_sha256="c" * 64,
        preflight_sha256="d" * 64,
        remote_revision="e" * 40,
    )


def _enqueue(
    queue: DurableExecutionQueue,
    registry: ExecutionDeclarationRegistry,
    request: ActionRequest,
    *,
    lane_id: str = "gamenet",
    dependency_request_sha256s: tuple[str, ...] = (),
):
    return queue.enqueue(
        request=request,
        declaration=registry.get(lane_id, request.action_id),
        contract_sha256=CONTRACT_SHA256,
        h1_approval_sha256=H1_APPROVAL_SHA256,
        dependency_request_sha256s=dependency_request_sha256s,
    )


def test_registry_covers_final_five_by_closed_nine_action_set() -> None:
    registry = ExecutionDeclarationRegistry.load_package()

    assert len(registry.lane_ids) == 5
    assert registry.initial_lane_id == "gamenet"
    assert len(registry.declarations) == 45
    assert (
        tuple(StatusAction.named(action).action_id for action in STATUS_ACTION_IDS)
        == STATUS_ACTION_IDS
    )
    assert registry.get("gamenet", "request_reproduction").blockers == (
        "license-unresolved",
        "environment-lock-unverified",
        "adapter-smoke-missing",
        "remote-revision-unverified",
        "data-root-unverified",
    )
    assert "source_path_id" not in registry.get("gamenet", "request_reproduction").to_public_dict()


def test_remote_enqueue_is_idempotent_and_blocked_without_authorization(tmp_path: Path) -> None:
    registry = ExecutionDeclarationRegistry.load_package()
    queue = DurableExecutionQueue(tmp_path, clock=lambda: NOW)
    request = _request()
    declaration = registry.get("gamenet", request.action_id)

    first = queue.enqueue(
        request=request,
        declaration=declaration,
        contract_sha256=CONTRACT_SHA256,
        h1_approval_sha256=H1_APPROVAL_SHA256,
    )
    second = queue.enqueue(
        request=request,
        declaration=declaration,
        contract_sha256=CONTRACT_SHA256,
        h1_approval_sha256=H1_APPROVAL_SHA256,
    )

    assert first == second
    assert first.state is ExecutionState.BLOCKED
    assert "remote-authorization-required" in first.blockers
    assert len(tuple(tmp_path.glob("*.json"))) == 1


def test_failed_or_stuck_dependency_blocks_downstream(tmp_path: Path) -> None:
    registry = ExecutionDeclarationRegistry.load_package()
    moments = iter((NOW, NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)))
    queue = DurableExecutionQueue(tmp_path, clock=lambda: next(moments))
    dependency = _enqueue(
        queue,
        registry,
        _request(action_id="resolve_source_license"),
    )
    queue.transition(
        dependency.request_sha256,
        state=ExecutionState.BLOCKED,
        reason_code="license-evidence-insufficient",
    )
    downstream = _enqueue(
        queue,
        registry,
        _request(action_id="advance_readiness", suffix="b"),
        dependency_request_sha256s=(dependency.request_sha256,),
    )

    assert downstream.state is ExecutionState.BLOCKED
    assert "dependency-not-successful" in downstream.blockers


def test_completed_dependency_allows_downstream_manual_review(tmp_path: Path) -> None:
    registry = ExecutionDeclarationRegistry.load_package()
    moments = iter((NOW, NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)))
    queue = DurableExecutionQueue(tmp_path, clock=lambda: next(moments))
    dependency = _enqueue(
        queue,
        registry,
        _request(action_id="resolve_source_license"),
    )
    dependency = queue.transition(
        dependency.request_sha256,
        state=ExecutionState.COMPLETED,
        reason_code="human-review-accepted",
    )
    downstream = _enqueue(
        queue,
        registry,
        _request(action_id="advance_readiness", suffix="b"),
        dependency_request_sha256s=(dependency.request_sha256,),
    )

    assert downstream.state is ExecutionState.REVIEW_PENDING
    assert downstream.blockers == ()


def test_invalid_transition_and_conflicting_duplicate_fail_closed(tmp_path: Path) -> None:
    registry = ExecutionDeclarationRegistry.load_package()
    queue = DurableExecutionQueue(tmp_path, clock=lambda: NOW)
    request = _request(action_id="resolve_source_license")
    record = _enqueue(queue, registry, request)

    with pytest.raises(ProtocolValidationError, match="transition"):
        queue.transition(
            record.request_sha256,
            state=ExecutionState.RUNNING,
            reason_code="invalid-skip",
        )
    with pytest.raises(ProtocolValidationError, match="conflicts"):
        queue.enqueue(
            request=request,
            declaration=registry.get("retain", request.action_id),
            contract_sha256=CONTRACT_SHA256,
            h1_approval_sha256=H1_APPROVAL_SHA256,
        )


def test_event_cursor_replays_only_newer_events(tmp_path: Path) -> None:
    registry = ExecutionDeclarationRegistry.load_package()
    moments = iter((NOW, NOW + timedelta(seconds=1)))
    queue = DurableExecutionQueue(tmp_path, clock=lambda: next(moments))
    record = _enqueue(
        queue,
        registry,
        _request(action_id="resolve_source_license"),
    )
    queue.transition(
        record.request_sha256,
        state=ExecutionState.COMPLETED,
        reason_code="human-review-accepted",
    )

    assert [item["event_id"] for item in queue.events_after()] == [
        "1",
        "2",
    ]
    assert [item["event_id"] for item in queue.events_after("1")] == ["2"]


def test_event_cursor_survives_restart_and_cross_request_updates(tmp_path: Path) -> None:
    registry = ExecutionDeclarationRegistry.load_package()
    moments = iter(
        (
            NOW,
            NOW + timedelta(seconds=1),
            NOW + timedelta(seconds=2),
        )
    )
    queue = DurableExecutionQueue(tmp_path, clock=lambda: next(moments))
    first = _enqueue(
        queue,
        registry,
        _request(action_id="resolve_source_license", suffix="a"),
    )
    second = _enqueue(
        queue,
        registry,
        _request(action_id="resolve_source_license", suffix="b"),
    )
    cursor = queue.events_after()[-1]["event_id"]

    restarted = DurableExecutionQueue(tmp_path, clock=lambda: next(moments))
    restarted.transition(
        first.request_sha256,
        state=ExecutionState.COMPLETED,
        reason_code="human-review-accepted",
    )

    replay = restarted.events_after(cursor)
    assert [item["event_id"] for item in replay] == ["3"]
    assert replay[0]["request_sha256"] == first.request_sha256
    assert restarted.load(second.request_sha256).events[0].journal_sequence == 2


def test_action_request_json_round_trip() -> None:
    request = _request()

    assert ActionRequest.from_json(request.to_json()) == request
