"""Registered, durable, public-safe execution control for the HITL console."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import ClassVar

from ._validation import (
    content_sha256,
    enum_member,
    parse_json_object,
    require_identifier,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
    write_json_atomic,
)
from .action_gate import ActionRequest
from .errors import ProtocolValidationError

Clock = Callable[[], datetime]

STATUS_ACTION_IDS = (
    "refresh_authorization",
    "resolve_source_license",
    "advance_readiness",
    "refresh_remote_preflight",
    "request_reproduction",
    "submit_reproduction_evidence",
    "request_next_lane",
    "submit_human_review",
    "begin_discovery",
)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ProtocolValidationError("execution clock must return an aware datetime")
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _identifiers(value: Iterable[object], *, field: str) -> tuple[str, ...]:
    result = tuple(value)
    for item in result:
        require_identifier(item, field=field)
    if len(set(result)) != len(result):
        raise ProtocolValidationError(f"{field} must not contain duplicates")
    return result


class DeclarationKind(StrEnum):
    LOCAL = "local"
    MANUAL = "manual"
    REMOTE = "remote"


class ExecutionState(StrEnum):
    BLOCKED = "blocked"
    QUEUED = "queued"
    SUBMITTING = "submitting"
    RUNNING = "running"
    MONITORING = "monitoring"
    INTAKE = "intake"
    REVIEW_PENDING = "review_pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    STUCK = "stuck"


class ExecutionOutcome(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    STUCK = "stuck"
    CANCELLED = "cancelled"


_TERMINAL_STATES = frozenset(
    {
        ExecutionState.COMPLETED,
        ExecutionState.CANCELLED,
        ExecutionState.FAILED,
        ExecutionState.STUCK,
    }
)

_TRANSITIONS = {
    ExecutionState.BLOCKED: frozenset(
        {ExecutionState.QUEUED, ExecutionState.REVIEW_PENDING, ExecutionState.CANCELLED}
    ),
    ExecutionState.QUEUED: frozenset(
        {ExecutionState.SUBMITTING, ExecutionState.REVIEW_PENDING, ExecutionState.CANCELLED}
    ),
    ExecutionState.SUBMITTING: frozenset(
        {
            ExecutionState.RUNNING,
            ExecutionState.BLOCKED,
            ExecutionState.FAILED,
            ExecutionState.STUCK,
            ExecutionState.CANCELLED,
        }
    ),
    ExecutionState.RUNNING: frozenset(
        {
            ExecutionState.MONITORING,
            ExecutionState.FAILED,
            ExecutionState.STUCK,
            ExecutionState.CANCELLED,
        }
    ),
    ExecutionState.MONITORING: frozenset(
        {
            ExecutionState.INTAKE,
            ExecutionState.FAILED,
            ExecutionState.STUCK,
            ExecutionState.CANCELLED,
        }
    ),
    ExecutionState.INTAKE: frozenset(
        {
            ExecutionState.REVIEW_PENDING,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
        }
    ),
    ExecutionState.REVIEW_PENDING: frozenset(
        {ExecutionState.COMPLETED, ExecutionState.BLOCKED, ExecutionState.CANCELLED}
    ),
}


@dataclass(frozen=True, slots=True)
class ExecutionDeclaration:
    project_id: str
    target_id: str
    lane_id: str
    baseline_id: str
    action_id: str
    kind: DeclarationKind | str
    source_revision: str
    environment_id: str
    resource_profile_id: str
    command_template_id: str
    launch_template_id: str
    evidence_schema_id: str
    source_path_id: str
    data_path_id: str
    output_path_id: str
    dependencies: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    declaration_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        for field in (
            "project_id",
            "target_id",
            "lane_id",
            "baseline_id",
            "action_id",
            "environment_id",
            "resource_profile_id",
            "command_template_id",
            "launch_template_id",
            "evidence_schema_id",
            "source_path_id",
            "data_path_id",
            "output_path_id",
        ):
            require_identifier(getattr(self, field), field=f"declaration.{field}")
        if self.action_id not in STATUS_ACTION_IDS:
            raise ProtocolValidationError(
                "declaration action is outside the closed Action Gate set"
            )
        object.__setattr__(
            self,
            "kind",
            enum_member(DeclarationKind, self.kind, field="declaration.kind"),
        )
        if len(self.source_revision) != 40 or any(
            character not in "0123456789abcdef" for character in self.source_revision
        ):
            raise ProtocolValidationError("declaration source_revision must be immutable")
        object.__setattr__(
            self,
            "dependencies",
            _identifiers(self.dependencies, field="declaration.dependencies"),
        )
        object.__setattr__(
            self,
            "blockers",
            _identifiers(self.blockers, field="declaration.blockers"),
        )
        expected = content_sha256(self._protected_payload())
        if self.declaration_sha256:
            require_sha256(self.declaration_sha256, field="declaration_sha256")
            if self.declaration_sha256 != expected:
                raise ProtocolValidationError("declaration digest does not match protected content")
        else:
            object.__setattr__(self, "declaration_sha256", expected)

    @property
    def declaration_id(self) -> str:
        return f"{self.lane_id}-{self.action_id}"

    def _protected_payload(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "baseline_id": self.baseline_id,
            "blockers": list(self.blockers),
            "command_template_id": self.command_template_id,
            "data_path_id": self.data_path_id,
            "dependencies": list(self.dependencies),
            "environment_id": self.environment_id,
            "evidence_schema_id": self.evidence_schema_id,
            "kind": self.kind.value,
            "lane_id": self.lane_id,
            "launch_template_id": self.launch_template_id,
            "output_path_id": self.output_path_id,
            "project_id": self.project_id,
            "resource_profile_id": self.resource_profile_id,
            "schema_version": self.SCHEMA_VERSION,
            "source_path_id": self.source_path_id,
            "source_revision": self.source_revision,
            "target_id": self.target_id,
        }

    def to_public_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "baseline_id": self.baseline_id,
            "blockers": list(self.blockers),
            "declaration_id": self.declaration_id,
            "declaration_sha256": self.declaration_sha256,
            "environment_id": self.environment_id,
            "evidence_schema_id": self.evidence_schema_id,
            "kind": self.kind.value,
            "lane_id": self.lane_id,
            "resource_profile_id": self.resource_profile_id,
            "schema_version": self.SCHEMA_VERSION,
            "source_revision": self.source_revision,
        }


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    sequence: int
    journal_sequence: int
    state: ExecutionState | str
    outcome: ExecutionOutcome | str
    reason_code: str
    occurred_at: str
    event_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 1:
            raise ProtocolValidationError("execution event sequence must be positive")
        if type(self.journal_sequence) is not int or self.journal_sequence < 1:
            raise ProtocolValidationError("execution journal sequence must be positive")
        object.__setattr__(
            self,
            "state",
            enum_member(ExecutionState, self.state, field="event.state"),
        )
        object.__setattr__(
            self,
            "outcome",
            enum_member(ExecutionOutcome, self.outcome, field="event.outcome"),
        )
        require_identifier(self.reason_code, field="event.reason_code")
        require_single_line_public_string(self.occurred_at, field="event.occurred_at")
        expected = content_sha256(self._content())
        if self.event_sha256:
            require_sha256(self.event_sha256, field="event_sha256")
            if self.event_sha256 != expected:
                raise ProtocolValidationError("execution event digest does not match content")
        else:
            object.__setattr__(self, "event_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "kind": "execution_event",
            "journal_sequence": self.journal_sequence,
            "occurred_at": self.occurred_at,
            "outcome": self.outcome.value,
            "reason_code": self.reason_code,
            "schema_version": self.SCHEMA_VERSION,
            "sequence": self.sequence,
            "state": self.state.value,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "event_sha256": self.event_sha256}

    @classmethod
    def from_dict(cls, value: object) -> ExecutionEvent:
        payload = strict_fields(
            value,
            required=(
                "event_sha256",
                "journal_sequence",
                "kind",
                "occurred_at",
                "outcome",
                "reason_code",
                "schema_version",
                "sequence",
                "state",
            ),
            context="ExecutionEvent",
        )
        if payload.pop("kind") != "execution_event" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("ExecutionEvent schema or kind is invalid")
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    request_sha256: str
    request_id: str
    contract_sha256: str
    h1_approval_sha256: str
    h2_decision_sha256: str | None
    declaration_id: str
    declaration_sha256: str
    lane_id: str
    action_id: str
    dependency_request_sha256s: tuple[str, ...]
    blockers: tuple[str, ...]
    events: tuple[ExecutionEvent, ...]
    record_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_sha256(self.request_sha256, field="execution.request_sha256")
        require_identifier(self.request_id, field="execution.request_id")
        require_sha256(self.contract_sha256, field="execution.contract_sha256")
        require_sha256(self.h1_approval_sha256, field="execution.h1_approval_sha256")
        if self.h2_decision_sha256 is not None:
            require_sha256(self.h2_decision_sha256, field="execution.h2_decision_sha256")
        for field in ("declaration_id", "lane_id", "action_id"):
            require_identifier(getattr(self, field), field=f"execution.{field}")
        require_sha256(self.declaration_sha256, field="execution.declaration_sha256")
        dependencies = tuple(self.dependency_request_sha256s)
        for digest in dependencies:
            require_sha256(digest, field="execution.dependency_request_sha256")
        if len(set(dependencies)) != len(dependencies):
            raise ProtocolValidationError("execution dependencies must be unique")
        object.__setattr__(self, "dependency_request_sha256s", dependencies)
        object.__setattr__(
            self,
            "blockers",
            _identifiers(self.blockers, field="execution.blockers"),
        )
        events = tuple(
            item if isinstance(item, ExecutionEvent) else ExecutionEvent.from_dict(item)
            for item in self.events
        )
        if not events or tuple(item.sequence for item in events) != tuple(
            range(1, len(events) + 1)
        ):
            raise ProtocolValidationError("execution events must be contiguous and nonempty")
        object.__setattr__(self, "events", events)
        expected = content_sha256(self._content())
        if self.record_sha256:
            require_sha256(self.record_sha256, field="execution.record_sha256")
            if self.record_sha256 != expected:
                raise ProtocolValidationError("execution record digest does not match content")
        else:
            object.__setattr__(self, "record_sha256", expected)

    @property
    def state(self) -> ExecutionState:
        return self.events[-1].state

    @property
    def outcome(self) -> ExecutionOutcome:
        return self.events[-1].outcome

    @property
    def successful(self) -> bool:
        return self.state is ExecutionState.COMPLETED and self.outcome is ExecutionOutcome.SUCCEEDED

    def _content(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "blockers": list(self.blockers),
            "contract_sha256": self.contract_sha256,
            "declaration_id": self.declaration_id,
            "declaration_sha256": self.declaration_sha256,
            "dependency_request_sha256s": list(self.dependency_request_sha256s),
            "events": [item.to_dict() for item in self.events],
            "h1_approval_sha256": self.h1_approval_sha256,
            "h2_decision_sha256": self.h2_decision_sha256,
            "kind": "execution_record",
            "lane_id": self.lane_id,
            "request_id": self.request_id,
            "request_sha256": self.request_sha256,
            "schema_version": self.SCHEMA_VERSION,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "record_sha256": self.record_sha256}

    def to_public_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "blockers": list(self.blockers),
            "contract_sha256": self.contract_sha256,
            "declaration_id": self.declaration_id,
            "events": [item.to_dict() for item in self.events],
            "h1_approval_sha256": self.h1_approval_sha256,
            "h2_decision_sha256": self.h2_decision_sha256,
            "lane_id": self.lane_id,
            "outcome": self.outcome.value,
            "request_id": self.request_id,
            "request_sha256": self.request_sha256,
            "schema_version": self.SCHEMA_VERSION,
            "state": self.state.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> ExecutionRecord:
        payload = strict_fields(
            value,
            required=(
                "action_id",
                "blockers",
                "contract_sha256",
                "declaration_id",
                "declaration_sha256",
                "dependency_request_sha256s",
                "events",
                "h1_approval_sha256",
                "h2_decision_sha256",
                "kind",
                "lane_id",
                "record_sha256",
                "request_id",
                "request_sha256",
                "schema_version",
            ),
            context="ExecutionRecord",
        )
        if payload.pop("kind") != "execution_record" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("ExecutionRecord schema or kind is invalid")
        events = payload.pop("events")
        if not isinstance(events, list):
            raise ProtocolValidationError("ExecutionRecord events must be a list")
        payload["events"] = tuple(ExecutionEvent.from_dict(item) for item in events)
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> ExecutionRecord:
        return cls.from_dict(parse_json_object(text, context="ExecutionRecord"))


class ExecutionDeclarationRegistry:
    """Expand one versioned lane/action registry into a closed declaration matrix."""

    def __init__(
        self,
        declarations: Iterable[ExecutionDeclaration],
        *,
        initial_lane_id: str,
    ) -> None:
        items = tuple(declarations)
        by_key = {(item.lane_id, item.action_id): item for item in items}
        if len(by_key) != len(items):
            raise ProtocolValidationError("execution declarations must be unique")
        lanes = {item.lane_id for item in items}
        expected = {(lane, action) for lane in lanes for action in STATUS_ACTION_IDS}
        if set(by_key) != expected:
            raise ProtocolValidationError("execution declaration matrix is incomplete")
        require_identifier(initial_lane_id, field="registry.initial_lane_id")
        if initial_lane_id not in lanes:
            raise ProtocolValidationError("execution registry initial lane is not registered")
        self._items = items
        self._by_key = by_key
        self.initial_lane_id = initial_lane_id

    @classmethod
    def load(cls, path: str | Path) -> ExecutionDeclarationRegistry:
        with Path(path).open("rb") as handle:
            payload = tomllib.load(handle)
        return cls._from_payload(payload)

    @classmethod
    def load_package(cls) -> ExecutionDeclarationRegistry:
        from importlib.resources import files

        resource = files("medrec_research.resources").joinpath("execution-declarations.toml")
        return cls._from_payload(tomllib.loads(resource.read_text(encoding="utf-8")))

    @classmethod
    def _from_payload(cls, payload: Mapping[str, object]) -> ExecutionDeclarationRegistry:
        if payload.get("schema_version") != 1:
            raise ProtocolValidationError("execution declaration registry version must be 1")
        project_id = payload.get("project_id")
        target_id = payload.get("target_id")
        initial_lane_id = payload.get("initial_lane_id")
        require_identifier(project_id, field="registry.project_id")
        require_identifier(target_id, field="registry.target_id")
        require_identifier(initial_lane_id, field="registry.initial_lane_id")
        actions = payload.get("actions")
        lanes = payload.get("lanes")
        if not isinstance(actions, Mapping) or tuple(actions) != STATUS_ACTION_IDS:
            raise ProtocolValidationError("execution registry must declare the closed action set")
        if not isinstance(lanes, list) or not lanes:
            raise ProtocolValidationError("execution registry must contain lanes")
        declarations: list[ExecutionDeclaration] = []
        for lane in lanes:
            lane_values = strict_fields(
                lane,
                required=(
                    "baseline_id",
                    "blockers",
                    "data_path_id",
                    "environment_id",
                    "evidence_schema_id",
                    "lane_id",
                    "launch_template_id",
                    "output_path_id",
                    "resource_profile_id",
                    "source_path_id",
                    "source_revision",
                ),
                context="execution lane",
            )
            lane_blockers = tuple(lane_values.pop("blockers"))
            for action_id, action in actions.items():
                action_values = strict_fields(
                    action,
                    required=("command_template_id", "kind"),
                    context="execution action",
                )
                kind = DeclarationKind(action_values["kind"])
                blockers = lane_blockers if kind is DeclarationKind.REMOTE else ()
                declarations.append(
                    ExecutionDeclaration(
                        project_id=project_id,
                        target_id=target_id,
                        action_id=action_id,
                        kind=kind,
                        command_template_id=action_values["command_template_id"],
                        blockers=blockers,
                        dependencies=(),
                        **lane_values,
                    )
                )
        return cls(declarations, initial_lane_id=initial_lane_id)

    @property
    def declarations(self) -> tuple[ExecutionDeclaration, ...]:
        return self._items

    @property
    def lane_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.lane_id for item in self._items))

    def get(self, lane_id: str, action_id: str) -> ExecutionDeclaration:
        try:
            return self._by_key[(lane_id, action_id)]
        except KeyError as error:
            raise ProtocolValidationError("execution declaration is not registered") from error

    def to_public_dict(self) -> dict[str, object]:
        return {
            "action_ids": list(STATUS_ACTION_IDS),
            "declarations": [item.to_public_dict() for item in self._items],
            "initial_lane_id": self.initial_lane_id,
            "kind": "execution_declaration_registry",
            "lane_ids": list(self.lane_ids),
            "schema_version": 1,
        }


class DurableExecutionQueue:
    """Atomic execution records with idempotent enqueue and replayable events."""

    def __init__(self, root: str | Path, *, clock: Clock) -> None:
        self.root = Path(root)
        self.clock = clock
        self._lock = Lock()

    def _path(self, request_sha256: str) -> Path:
        require_sha256(request_sha256, field="request_sha256")
        return self.root / f"{request_sha256}.json"

    def _next_journal_sequence(self) -> int:
        self.root.mkdir(parents=True, exist_ok=True)
        latest = max(
            (event.journal_sequence for record in self.records() for event in record.events),
            default=0,
        )
        for marker in self.root.glob(".event-*"):
            sequence = marker.name.removeprefix(".event-")
            if sequence.isascii() and sequence.isdigit():
                latest = max(latest, int(sequence))
        while True:
            next_sequence = latest + 1
            marker = self.root / f".event-{next_sequence:020d}"
            try:
                descriptor = os.open(
                    marker,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                latest = next_sequence
                continue
            os.close(descriptor)
            return next_sequence

    def load(self, request_sha256: str) -> ExecutionRecord:
        return ExecutionRecord.from_json(self._path(request_sha256).read_text(encoding="utf-8"))

    def records(self) -> tuple[ExecutionRecord, ...]:
        if not self.root.is_dir():
            return ()
        records = []
        for path in sorted(self.root.glob("*.json")):
            try:
                records.append(ExecutionRecord.from_json(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeError, ProtocolValidationError):
                continue
        return tuple(records)

    def enqueue(
        self,
        *,
        request: ActionRequest,
        declaration: ExecutionDeclaration,
        contract_sha256: str,
        h1_approval_sha256: str,
        h2_decision_sha256: str | None = None,
        dependency_request_sha256s: Iterable[str] = (),
        blockers: Iterable[str] = (),
    ) -> ExecutionRecord:
        require_sha256(contract_sha256, field="execution.contract_sha256")
        require_sha256(h1_approval_sha256, field="execution.h1_approval_sha256")
        if h2_decision_sha256 is not None:
            require_sha256(h2_decision_sha256, field="execution.h2_decision_sha256")
        if request.project_id != declaration.project_id:
            raise ProtocolValidationError("Action Request project does not match declaration")
        if request.target_id != declaration.target_id:
            raise ProtocolValidationError("Action Request target does not match declaration")
        if request.action_id != declaration.action_id:
            raise ProtocolValidationError("Action Request action does not match declaration")
        dependencies = tuple(dependency_request_sha256s)
        dynamic_blockers = list(blockers)
        for digest in dependencies:
            try:
                dependency = self.load(digest)
            except (OSError, UnicodeError, ProtocolValidationError):
                dynamic_blockers.append("dependency-missing-or-invalid")
                continue
            if not dependency.successful:
                dynamic_blockers.append("dependency-not-successful")
        if declaration.kind is DeclarationKind.REMOTE:
            dynamic_blockers.append("remote-authorization-required")
        all_blockers = tuple(dict.fromkeys((*declaration.blockers, *dynamic_blockers)))
        if all_blockers:
            initial_state = ExecutionState.BLOCKED
            reason = all_blockers[0]
        elif declaration.kind is DeclarationKind.MANUAL:
            initial_state = ExecutionState.REVIEW_PENDING
            reason = "human-review-required"
        else:
            initial_state = ExecutionState.QUEUED
            reason = "execution-queued"
        path = self._path(request.request_sha256)
        with self._lock:
            if path.is_file():
                existing = ExecutionRecord.from_json(path.read_text(encoding="utf-8"))
                identity = (
                    existing.request_sha256,
                    existing.declaration_sha256,
                    existing.contract_sha256,
                    existing.h1_approval_sha256,
                    existing.h2_decision_sha256,
                    existing.dependency_request_sha256s,
                )
                expected = (
                    request.request_sha256,
                    declaration.declaration_sha256,
                    contract_sha256,
                    h1_approval_sha256,
                    h2_decision_sha256,
                    dependencies,
                )
                if identity != expected:
                    raise ProtocolValidationError("duplicate request conflicts with durable record")
                return existing
            event = ExecutionEvent(
                sequence=1,
                journal_sequence=self._next_journal_sequence(),
                state=initial_state,
                outcome=ExecutionOutcome.PENDING,
                reason_code=reason,
                occurred_at=_timestamp(self.clock()),
            )
            candidate = ExecutionRecord(
                request_sha256=request.request_sha256,
                request_id=request.request_id,
                contract_sha256=contract_sha256,
                h1_approval_sha256=h1_approval_sha256,
                h2_decision_sha256=h2_decision_sha256,
                declaration_id=declaration.declaration_id,
                declaration_sha256=declaration.declaration_sha256,
                lane_id=declaration.lane_id,
                action_id=declaration.action_id,
                dependency_request_sha256s=dependencies,
                blockers=all_blockers,
                events=(event,),
            )
            write_json_atomic(path, candidate.to_dict())
        return candidate

    def transition(
        self,
        request_sha256: str,
        *,
        state: ExecutionState | str,
        reason_code: str,
    ) -> ExecutionRecord:
        target = enum_member(ExecutionState, state, field="execution.state")
        require_identifier(reason_code, field="execution.reason_code")
        with self._lock:
            record = self.load(request_sha256)
            if record.state in _TERMINAL_STATES:
                if record.state is target:
                    return record
                raise ProtocolValidationError("terminal execution cannot transition")
            allowed = _TRANSITIONS.get(record.state, frozenset())
            if target not in allowed:
                raise ProtocolValidationError("execution transition is invalid")
            outcome = ExecutionOutcome.PENDING
            if target is ExecutionState.COMPLETED:
                outcome = ExecutionOutcome.SUCCEEDED
            elif target is ExecutionState.CANCELLED:
                outcome = ExecutionOutcome.CANCELLED
            elif target is ExecutionState.FAILED:
                outcome = ExecutionOutcome.FAILED
            elif target is ExecutionState.STUCK:
                outcome = ExecutionOutcome.STUCK
            event = ExecutionEvent(
                sequence=len(record.events) + 1,
                journal_sequence=self._next_journal_sequence(),
                state=target,
                outcome=outcome,
                reason_code=reason_code,
                occurred_at=_timestamp(self.clock()),
            )
            updated = ExecutionRecord(
                request_sha256=record.request_sha256,
                request_id=record.request_id,
                contract_sha256=record.contract_sha256,
                h1_approval_sha256=record.h1_approval_sha256,
                h2_decision_sha256=record.h2_decision_sha256,
                declaration_id=record.declaration_id,
                declaration_sha256=record.declaration_sha256,
                lane_id=record.lane_id,
                action_id=record.action_id,
                dependency_request_sha256s=record.dependency_request_sha256s,
                blockers=record.blockers,
                events=(*record.events, event),
            )
            write_json_atomic(self._path(request_sha256), updated.to_dict())
            return updated

    def to_public_dict(self) -> dict[str, object]:
        records = self.records()
        return {
            "kind": "execution_queue",
            "records": [item.to_public_dict() for item in records],
            "schema_version": 1,
        }

    def events_after(self, event_id: str | None = None) -> tuple[dict[str, object], ...]:
        cursor = 0
        if event_id:
            if not event_id.isascii() or not event_id.isdigit() or int(event_id) < 1:
                raise ProtocolValidationError("execution event cursor is invalid")
            cursor = int(event_id)
        events: list[dict[str, object]] = []
        for record in self.records():
            for event in record.events:
                if event.journal_sequence <= cursor:
                    continue
                events.append(
                    {
                        "event": event.to_dict(),
                        "event_id": str(event.journal_sequence),
                        "request_sha256": record.request_sha256,
                    }
                )
        return tuple(sorted(events, key=lambda item: int(item["event_id"])))


__all__ = (
    "STATUS_ACTION_IDS",
    "DeclarationKind",
    "DurableExecutionQueue",
    "ExecutionDeclaration",
    "ExecutionDeclarationRegistry",
    "ExecutionEvent",
    "ExecutionOutcome",
    "ExecutionRecord",
    "ExecutionState",
)
