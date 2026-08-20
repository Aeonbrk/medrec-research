"""Declaration-bound dispatch envelopes for the durable execution queue."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, Literal

from ._validation import (
    content_sha256,
    parse_json_object,
    require_identifier,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
    write_json_atomic,
)
from .action_gate import ActionRequest
from .aris_bridge import ArisRevisionRecord
from .errors import ProtocolValidationError
from .execution_control import (
    DeclarationKind,
    DurableExecutionQueue,
    ExecutionDeclaration,
    ExecutionRecord,
    ExecutionState,
)

Clock = Callable[[], datetime]
DispatchStatus = Literal["blocked", "awaiting-aris-bridge", "awaiting-local-dispatch", "ready"]


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ProtocolValidationError("execution worker clock must return an aware datetime")
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ExecutionSubmission:
    """A public-safe, declaration-derived submission envelope."""

    request_sha256: str
    declaration_sha256: str
    lane_id: str
    action_id: str
    target_id: str
    source_revision: str
    environment_id: str
    resource_profile_id: str
    command_template_id: str
    launch_template_id: str
    evidence_schema_id: str
    status: DispatchStatus | str
    blockers: tuple[str, ...]
    created_at: str
    submission_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_sha256(self.request_sha256, field="submission.request_sha256")
        require_sha256(self.declaration_sha256, field="submission.declaration_sha256")
        for name in (
            "lane_id",
            "action_id",
            "target_id",
            "environment_id",
            "resource_profile_id",
            "command_template_id",
            "launch_template_id",
            "evidence_schema_id",
        ):
            require_identifier(getattr(self, name), field=f"submission.{name}")
        if (
            not isinstance(self.source_revision, str)
            or len(self.source_revision) != 40
            or any(character not in "0123456789abcdef" for character in self.source_revision)
        ):
            raise ProtocolValidationError("submission.source_revision must be immutable")
        if self.status not in {
            "blocked",
            "awaiting-aris-bridge",
            "awaiting-local-dispatch",
            "ready",
        }:
            raise ProtocolValidationError("submission status is invalid")
        blockers = tuple(dict.fromkeys(self.blockers))
        for blocker in blockers:
            require_identifier(blocker, field="submission.blockers")
        object.__setattr__(self, "blockers", blockers)
        require_single_line_public_string(self.created_at, field="submission.created_at")
        expected = content_sha256(self._content())
        if self.submission_sha256:
            require_sha256(self.submission_sha256, field="submission.submission_sha256")
            if self.submission_sha256 != expected:
                raise ProtocolValidationError("submission digest does not match content")
        object.__setattr__(self, "submission_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "blockers": list(self.blockers),
            "command_template_id": self.command_template_id,
            "created_at": self.created_at,
            "declaration_sha256": self.declaration_sha256,
            "environment_id": self.environment_id,
            "evidence_schema_id": self.evidence_schema_id,
            "kind": "execution_submission",
            "lane_id": self.lane_id,
            "launch_template_id": self.launch_template_id,
            "request_sha256": self.request_sha256,
            "resource_profile_id": self.resource_profile_id,
            "schema_version": self.SCHEMA_VERSION,
            "source_revision": self.source_revision,
            "status": self.status,
            "target_id": self.target_id,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "submission_sha256": self.submission_sha256}

    @classmethod
    def from_dict(cls, value: object) -> ExecutionSubmission:
        payload = strict_fields(
            value,
            required=(
                "action_id",
                "blockers",
                "command_template_id",
                "created_at",
                "declaration_sha256",
                "environment_id",
                "evidence_schema_id",
                "kind",
                "lane_id",
                "launch_template_id",
                "request_sha256",
                "resource_profile_id",
                "schema_version",
                "source_revision",
                "status",
                "submission_sha256",
                "target_id",
            ),
            context="execution submission",
        )
        if payload.pop("kind") != "execution_submission" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("execution submission schema or kind is invalid")
        blockers = payload.pop("blockers")
        if not isinstance(blockers, list):
            raise ProtocolValidationError("execution submission blockers must be a list")
        payload["blockers"] = tuple(blockers)
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> ExecutionSubmission:
        return cls.from_dict(parse_json_object(text, context="execution submission"))


class DeclarationBoundWorker:
    """Persist fixed submission envelopes without inventing a remote fallback."""

    def __init__(
        self,
        queue: DurableExecutionQueue,
        request_dir: Path,
        submission_dir: Path,
        *,
        clock: Clock,
    ) -> None:
        self.queue = queue
        self.request_dir = request_dir
        self.submission_dir = submission_dir
        self.clock = clock

    def _path(self, request_sha256: str) -> Path:
        return self.submission_dir / f"{request_sha256}.json"

    def _request(self, request_sha256: str) -> ActionRequest:
        try:
            return ActionRequest.from_json(
                (self.request_dir / f"{request_sha256}.json").read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, ProtocolValidationError) as error:
            raise ProtocolValidationError("execution request is unavailable") from error

    def prepare(
        self,
        record: ExecutionRecord,
        declaration: ExecutionDeclaration,
        *,
        aris_revision: ArisRevisionRecord | None,
    ) -> ExecutionSubmission:
        if record.declaration_sha256 != declaration.declaration_sha256:
            raise ProtocolValidationError("execution declaration binding changed")
        path = self._path(record.request_sha256)
        existing = None
        if path.is_file():
            existing = ExecutionSubmission.from_json(path.read_text(encoding="utf-8"))
            if (
                existing.request_sha256 != record.request_sha256
                or existing.declaration_sha256 != declaration.declaration_sha256
                or existing.lane_id != declaration.lane_id
                or existing.action_id != declaration.action_id
                or existing.target_id != declaration.target_id
                or existing.source_revision != declaration.source_revision
                or existing.environment_id != declaration.environment_id
                or existing.resource_profile_id != declaration.resource_profile_id
                or existing.command_template_id != declaration.command_template_id
                or existing.launch_template_id != declaration.launch_template_id
                or existing.evidence_schema_id != declaration.evidence_schema_id
            ):
                raise ProtocolValidationError("execution submission conflicts with history")
        request = self._request(record.request_sha256)
        if request.action_id != declaration.action_id or request.target_id != declaration.target_id:
            raise ProtocolValidationError("execution request binding changed")
        blockers = list(record.blockers)
        if aris_revision is None or not aris_revision.candidate_valid:
            blockers.append("aris-candidate-unverified")
        blockers = list(dict.fromkeys(blockers))
        if blockers:
            status: DispatchStatus = "blocked"
        elif declaration.kind is DeclarationKind.REMOTE:
            status = "awaiting-aris-bridge"
        elif declaration.kind is DeclarationKind.LOCAL:
            status = "awaiting-local-dispatch"
        else:
            status = "ready"
        submission = ExecutionSubmission(
            request_sha256=record.request_sha256,
            declaration_sha256=declaration.declaration_sha256,
            lane_id=declaration.lane_id,
            action_id=declaration.action_id,
            target_id=declaration.target_id,
            source_revision=declaration.source_revision,
            environment_id=declaration.environment_id,
            resource_profile_id=declaration.resource_profile_id,
            command_template_id=declaration.command_template_id,
            launch_template_id=declaration.launch_template_id,
            evidence_schema_id=declaration.evidence_schema_id,
            status=status,
            blockers=tuple(blockers),
            created_at=existing.created_at if existing is not None else _timestamp(self.clock()),
        )
        if submission.status == "blocked":
            return submission
        if existing is not None:
            if existing.to_dict() == submission.to_dict():
                return existing
            if existing.status != "blocked":
                raise ProtocolValidationError("execution submission conflicts with history")
        self.submission_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, submission.to_dict())
        return submission

    def prepare_pending(
        self,
        declarations: Callable[[str, str], ExecutionDeclaration],
        *,
        aris_revision: ArisRevisionRecord | None,
    ) -> tuple[ExecutionSubmission, ...]:
        prepared: list[ExecutionSubmission] = []
        for record in self.queue.records():
            if record.state is not ExecutionState.QUEUED:
                continue
            declaration = declarations(record.lane_id, record.action_id)
            prepared.append(self.prepare(record, declaration, aris_revision=aris_revision))
        return tuple(prepared)

    def records(self) -> tuple[ExecutionSubmission, ...]:
        if not self.submission_dir.is_dir():
            return ()
        records: list[ExecutionSubmission] = []
        for path in sorted(self.submission_dir.glob("*.json")):
            try:
                records.append(ExecutionSubmission.from_json(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeError, ProtocolValidationError) as error:
                raise ProtocolValidationError(
                    f"execution submission is invalid: {path.name}"
                ) from error
        return tuple(records)


__all__ = ("DeclarationBoundWorker", "ExecutionSubmission")
