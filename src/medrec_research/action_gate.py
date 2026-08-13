"""Pure, fail-closed action-request gate for public project status."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    parse_json_object,
    require_identifier,
    require_sha256,
    strict_fields,
)
from .errors import ProtocolValidationError
from .project_status import AuthorityDigest, ProjectStatus, SnapshotCondition

_IMMUTABLE_REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


def _authorities(
    value: Iterable[AuthorityDigest | Mapping[str, object]],
) -> tuple[AuthorityDigest, ...]:
    try:
        result = tuple(
            item if isinstance(item, AuthorityDigest) else AuthorityDigest.from_dict(item)
            for item in value
        )
    except TypeError as error:
        raise ProtocolValidationError("authorities must be a collection") from error
    result = tuple(sorted(result, key=lambda item: item.authority_id))
    if not result or len({item.authority_id for item in result}) != len(result):
        raise ProtocolValidationError("authorities must be non-empty and unique")
    return result


def _authority_objects(value: object) -> tuple[AuthorityDigest, ...]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ProtocolValidationError("authorities must be a list of objects")
    return _authorities(value)


def _authority_sha256(authorities: tuple[AuthorityDigest, ...], authority_id: str) -> str | None:
    return next(
        (item.sha256 for item in authorities if item.authority_id == authority_id),
        None,
    )


def _timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtocolValidationError(f"{field} must be a canonical UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ProtocolValidationError(f"{field} must be a canonical UTC timestamp") from error
    canonical = parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    if canonical != value:
        raise ProtocolValidationError(f"{field} must be a canonical UTC timestamp")
    return parsed


def _time_bounds(issued_at: object, expires_at: object) -> tuple[datetime, datetime]:
    issued = _timestamp(issued_at, field="issued_at")
    expires = _timestamp(expires_at, field="expires_at")
    if expires <= issued:
        raise ProtocolValidationError("expires_at must be after issued_at")
    return issued, expires


def _now(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ProtocolValidationError("now must be a UTC datetime")
    return value.astimezone(UTC)


def _immutable_revision(value: object) -> str:
    if not isinstance(value, str) or _IMMUTABLE_REVISION.fullmatch(value) is None:
        raise ProtocolValidationError("remote_revision must be an immutable full revision")
    return value


@dataclass(frozen=True, slots=True)
class ActionRequestInput:
    """Opaque caller input for one action-request evaluation."""

    request_id: str

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.request_id, field="request_id")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "action_request_input",
            "request_id": self.request_id,
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def from_dict(cls, value: object) -> ActionRequestInput:
        payload = strict_fields(
            value,
            required=("schema_version", "kind", "request_id"),
            context="ActionRequestInput",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("ActionRequestInput schema_version must be 1")
        if payload.pop("kind") != "action_request_input":
            raise ProtocolValidationError("ActionRequestInput kind must be action_request_input")
        return cls(**payload)


def _authorization_content(
    *,
    issuer_id: str,
    source_id: str,
    project_id: str,
    target_id: str,
    action_id: str,
    snapshot_sha256: str,
    scope_sha256: str,
    authorities: tuple[AuthorityDigest, ...],
    issued_at: str,
    expires_at: str,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "authorities": [item.to_dict() for item in authorities],
        "expires_at": expires_at,
        "issued_at": issued_at,
        "issuer_id": issuer_id,
        "kind": "action_authorization",
        "project_id": project_id,
        "schema_version": ActionAuthorization.SCHEMA_VERSION,
        "scope_sha256": scope_sha256,
        "snapshot_sha256": snapshot_sha256,
        "source_id": source_id,
        "target_id": target_id,
    }


@dataclass(frozen=True, slots=True)
class ActionAuthorization:
    issuer_id: str
    source_id: str
    project_id: str
    target_id: str
    action_id: str
    snapshot_sha256: str
    scope_sha256: str
    authorities: tuple[AuthorityDigest, ...]
    issued_at: str
    expires_at: str
    authorization_sha256: str

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        for field in ("issuer_id", "source_id", "project_id", "target_id", "action_id"):
            require_identifier(getattr(self, field), field=field)
        require_sha256(self.snapshot_sha256, field="snapshot_sha256")
        require_sha256(self.scope_sha256, field="scope_sha256")
        authorities = _authorities(self.authorities)
        object.__setattr__(self, "authorities", authorities)
        _time_bounds(self.issued_at, self.expires_at)
        require_sha256(self.authorization_sha256, field="authorization_sha256")
        if self.authorization_sha256 != content_sha256(self._content()):
            raise ProtocolValidationError("authorization_sha256 does not match record content")

    def _content(self) -> dict[str, object]:
        return _authorization_content(
            issuer_id=self.issuer_id,
            source_id=self.source_id,
            project_id=self.project_id,
            target_id=self.target_id,
            action_id=self.action_id,
            snapshot_sha256=self.snapshot_sha256,
            scope_sha256=self.scope_sha256,
            authorities=self.authorities,
            issued_at=self.issued_at,
            expires_at=self.expires_at,
        )

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "authorization_sha256": self.authorization_sha256}

    @classmethod
    def create(cls, **values: object) -> ActionAuthorization:
        authorities = _authorities(values["authorities"])
        normalized = {**values, "authorities": authorities}
        digest = content_sha256(_authorization_content(**normalized))
        return cls(authorization_sha256=digest, **normalized)

    @classmethod
    def from_dict(cls, value: object) -> ActionAuthorization:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "issuer_id",
                "source_id",
                "project_id",
                "target_id",
                "action_id",
                "snapshot_sha256",
                "scope_sha256",
                "authorities",
                "issued_at",
                "expires_at",
                "authorization_sha256",
            ),
            context="ActionAuthorization",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("ActionAuthorization schema_version must be 1")
        if payload.pop("kind") != "action_authorization":
            raise ProtocolValidationError("ActionAuthorization kind must be action_authorization")
        payload["authorities"] = _authority_objects(payload["authorities"])
        return cls(**payload)


def _preflight_content(
    *,
    issuer_id: str,
    source_id: str,
    project_id: str,
    target_id: str,
    action_id: str,
    snapshot_sha256: str,
    scope_sha256: str,
    authorities: tuple[AuthorityDigest, ...],
    remote_revision: str,
    issued_at: str,
    expires_at: str,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "authorities": [item.to_dict() for item in authorities],
        "expires_at": expires_at,
        "issued_at": issued_at,
        "issuer_id": issuer_id,
        "kind": "remote_preflight",
        "project_id": project_id,
        "remote_revision": remote_revision,
        "schema_version": RemotePreflight.SCHEMA_VERSION,
        "scope_sha256": scope_sha256,
        "snapshot_sha256": snapshot_sha256,
        "source_id": source_id,
        "target_id": target_id,
    }


@dataclass(frozen=True, slots=True)
class RemotePreflight:
    issuer_id: str
    source_id: str
    project_id: str
    target_id: str
    action_id: str
    snapshot_sha256: str
    scope_sha256: str
    authorities: tuple[AuthorityDigest, ...]
    remote_revision: str
    issued_at: str
    expires_at: str
    preflight_sha256: str

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        for field in ("issuer_id", "source_id", "project_id", "target_id", "action_id"):
            require_identifier(getattr(self, field), field=field)
        require_sha256(self.snapshot_sha256, field="snapshot_sha256")
        require_sha256(self.scope_sha256, field="scope_sha256")
        authorities = _authorities(self.authorities)
        object.__setattr__(self, "authorities", authorities)
        _immutable_revision(self.remote_revision)
        _time_bounds(self.issued_at, self.expires_at)
        require_sha256(self.preflight_sha256, field="preflight_sha256")
        if self.preflight_sha256 != content_sha256(self._content()):
            raise ProtocolValidationError("preflight_sha256 does not match record content")

    def _content(self) -> dict[str, object]:
        return _preflight_content(
            issuer_id=self.issuer_id,
            source_id=self.source_id,
            project_id=self.project_id,
            target_id=self.target_id,
            action_id=self.action_id,
            snapshot_sha256=self.snapshot_sha256,
            scope_sha256=self.scope_sha256,
            authorities=self.authorities,
            remote_revision=self.remote_revision,
            issued_at=self.issued_at,
            expires_at=self.expires_at,
        )

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "preflight_sha256": self.preflight_sha256}

    @classmethod
    def create(cls, **values: object) -> RemotePreflight:
        authorities = _authorities(values["authorities"])
        normalized = {**values, "authorities": authorities}
        digest = content_sha256(_preflight_content(**normalized))
        return cls(preflight_sha256=digest, **normalized)

    @classmethod
    def from_dict(cls, value: object) -> RemotePreflight:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "issuer_id",
                "source_id",
                "project_id",
                "target_id",
                "action_id",
                "snapshot_sha256",
                "scope_sha256",
                "authorities",
                "remote_revision",
                "issued_at",
                "expires_at",
                "preflight_sha256",
            ),
            context="RemotePreflight",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("RemotePreflight schema_version must be 1")
        if payload.pop("kind") != "remote_preflight":
            raise ProtocolValidationError("RemotePreflight kind must be remote_preflight")
        payload["authorities"] = _authority_objects(payload["authorities"])
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class AuthorityBundle:
    """Explicitly injected current authority; never loaded by the gate."""

    current_authorities: tuple[AuthorityDigest, ...]
    current_remote_profile_id: str
    current_remote_revision: str
    authorization_issuer_id: str
    authorization_source_id: str
    preflight_issuer_id: str
    preflight_source_id: str
    authorizations: tuple[ActionAuthorization, ...]
    preflights: tuple[RemotePreflight, ...]

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "current_authorities", _authorities(self.current_authorities))
        for field in (
            "current_remote_profile_id",
            "authorization_issuer_id",
            "authorization_source_id",
            "preflight_issuer_id",
            "preflight_source_id",
        ):
            require_identifier(getattr(self, field), field=field)
        _immutable_revision(self.current_remote_revision)
        authorizations = tuple(self.authorizations)
        preflights = tuple(self.preflights)
        if any(not isinstance(item, ActionAuthorization) for item in authorizations):
            raise ProtocolValidationError("authorizations must contain ActionAuthorization records")
        if any(not isinstance(item, RemotePreflight) for item in preflights):
            raise ProtocolValidationError("preflights must contain RemotePreflight records")
        object.__setattr__(self, "authorizations", authorizations)
        object.__setattr__(self, "preflights", preflights)

    def to_dict(self) -> dict[str, object]:
        return {
            "authorization_issuer_id": self.authorization_issuer_id,
            "authorization_source_id": self.authorization_source_id,
            "authorizations": [item.to_dict() for item in self.authorizations],
            "current_authorities": [item.to_dict() for item in self.current_authorities],
            "current_remote_profile_id": self.current_remote_profile_id,
            "current_remote_revision": self.current_remote_revision,
            "kind": "authority_bundle",
            "preflight_issuer_id": self.preflight_issuer_id,
            "preflight_source_id": self.preflight_source_id,
            "preflights": [item.to_dict() for item in self.preflights],
            "schema_version": self.SCHEMA_VERSION,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, value: object) -> AuthorityBundle:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "current_authorities",
                "current_remote_profile_id",
                "current_remote_revision",
                "authorization_issuer_id",
                "authorization_source_id",
                "preflight_issuer_id",
                "preflight_source_id",
                "authorizations",
                "preflights",
            ),
            context="AuthorityBundle",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("AuthorityBundle schema_version must be 1")
        if payload.pop("kind") != "authority_bundle":
            raise ProtocolValidationError("AuthorityBundle kind must be authority_bundle")
        authorizations = payload.pop("authorizations")
        preflights = payload.pop("preflights")
        if not isinstance(authorizations, list) or not all(
            isinstance(item, Mapping) for item in authorizations
        ):
            raise ProtocolValidationError("authorizations must be a list of objects")
        if not isinstance(preflights, list) or not all(
            isinstance(item, Mapping) for item in preflights
        ):
            raise ProtocolValidationError("preflights must be a list of objects")
        return cls(
            current_authorities=_authority_objects(payload.pop("current_authorities")),
            authorizations=tuple(ActionAuthorization.from_dict(item) for item in authorizations),
            preflights=tuple(RemotePreflight.from_dict(item) for item in preflights),
            **payload,
        )

    @classmethod
    def from_json(cls, text: str) -> AuthorityBundle:
        return cls.from_dict(parse_json_object(text, context="AuthorityBundle"))

    @classmethod
    def load(cls, path: str | Path) -> AuthorityBundle:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class ActionContext:
    """Current action binding resolved from status and injected authority."""

    available: bool
    reason_code: str
    action_id: str | None = None
    target_id: str | None = None
    snapshot_sha256: str | None = None
    scope_sha256: str | None = None
    authorities: tuple[AuthorityDigest, ...] = ()
    authorization_sha256: str | None = None
    preflight_sha256: str | None = None
    remote_revision: str | None = None

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        if type(self.available) is not bool:
            raise ProtocolValidationError("action context availability must be boolean")
        require_identifier(self.reason_code, field="action_context.reason_code")
        bindings = (
            self.action_id,
            self.target_id,
            self.snapshot_sha256,
            self.scope_sha256,
            self.authorization_sha256,
            self.preflight_sha256,
            self.remote_revision,
        )
        if not self.available:
            if any(value is not None for value in bindings) or self.authorities:
                raise ProtocolValidationError("unavailable action context cannot contain bindings")
            return
        for field in ("action_id", "target_id"):
            require_identifier(getattr(self, field), field=f"action_context.{field}")
        for field in (
            "snapshot_sha256",
            "scope_sha256",
            "authorization_sha256",
            "preflight_sha256",
        ):
            require_sha256(getattr(self, field), field=f"action_context.{field}")
        object.__setattr__(self, "authorities", _authorities(self.authorities))
        _immutable_revision(self.remote_revision)

    @classmethod
    def unavailable(cls, reason_code: str) -> ActionContext:
        return cls(available=False, reason_code=reason_code)

    @classmethod
    def resolved(
        cls,
        *,
        action_id: str,
        target_id: str,
        snapshot_sha256: str,
        scope_sha256: str,
        authorities: tuple[AuthorityDigest, ...],
        authorization_sha256: str,
        preflight_sha256: str,
        remote_revision: str,
    ) -> ActionContext:
        return cls(
            available=True,
            reason_code="action_context_resolved",
            action_id=action_id,
            target_id=target_id,
            snapshot_sha256=snapshot_sha256,
            scope_sha256=scope_sha256,
            authorities=authorities,
            authorization_sha256=authorization_sha256,
            preflight_sha256=preflight_sha256,
            remote_revision=remote_revision,
        )

    @property
    def request_id(self) -> str | None:
        if not self.available:
            return None
        assert self.action_id is not None
        assert self.target_id is not None
        assert self.snapshot_sha256 is not None
        assert self.scope_sha256 is not None
        assert self.authorization_sha256 is not None
        assert self.preflight_sha256 is not None
        assert self.remote_revision is not None
        content = {
            "action_id": self.action_id,
            "authorities": [item.to_dict() for item in self.authorities],
            "authorization_sha256": self.authorization_sha256,
            "kind": "action_context",
            "preflight_sha256": self.preflight_sha256,
            "remote_revision": self.remote_revision,
            "schema_version": self.SCHEMA_VERSION,
            "scope_sha256": self.scope_sha256,
            "snapshot_sha256": self.snapshot_sha256,
            "target_id": self.target_id,
        }
        return f"action-context-{content_sha256(content)[:20]}"

    def to_public_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "enabled": self.available,
            "kind": "action_context",
            "schema_version": self.SCHEMA_VERSION,
        }
        if self.request_id is not None:
            payload["request_id"] = self.request_id
        return payload


def _request_content(
    *,
    request_id: str,
    project_id: str,
    target_id: str,
    action_id: str,
    snapshot_sha256: str,
    scope_sha256: str,
    authorities: tuple[AuthorityDigest, ...],
    authorization_sha256: str,
    preflight_sha256: str,
    remote_revision: str,
) -> dict[str, object]:
    return {
        "action_id": action_id,
        "authorities": [item.to_dict() for item in authorities],
        "authorization_sha256": authorization_sha256,
        "kind": "action_request",
        "preflight_sha256": preflight_sha256,
        "project_id": project_id,
        "remote_revision": remote_revision,
        "request_id": request_id,
        "schema_version": ActionRequest.SCHEMA_VERSION,
        "scope_sha256": scope_sha256,
        "snapshot_sha256": snapshot_sha256,
        "target_id": target_id,
    }


@dataclass(frozen=True, slots=True)
class ActionRequest:
    request_id: str
    project_id: str
    target_id: str
    action_id: str
    snapshot_sha256: str
    scope_sha256: str
    authorities: tuple[AuthorityDigest, ...]
    authorization_sha256: str
    preflight_sha256: str
    remote_revision: str
    request_sha256: str

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        for field in ("request_id", "project_id", "target_id", "action_id"):
            require_identifier(getattr(self, field), field=field)
        for field in (
            "snapshot_sha256",
            "scope_sha256",
            "authorization_sha256",
            "preflight_sha256",
            "request_sha256",
        ):
            require_sha256(getattr(self, field), field=field)
        object.__setattr__(self, "authorities", _authorities(self.authorities))
        _immutable_revision(self.remote_revision)
        if self.request_sha256 != content_sha256(self._content()):
            raise ProtocolValidationError("request_sha256 does not match request content")

    def _content(self) -> dict[str, object]:
        return _request_content(
            request_id=self.request_id,
            project_id=self.project_id,
            target_id=self.target_id,
            action_id=self.action_id,
            snapshot_sha256=self.snapshot_sha256,
            scope_sha256=self.scope_sha256,
            authorities=self.authorities,
            authorization_sha256=self.authorization_sha256,
            preflight_sha256=self.preflight_sha256,
            remote_revision=self.remote_revision,
        )

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "request_sha256": self.request_sha256}

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def create(cls, **values: object) -> ActionRequest:
        authorities = _authorities(values["authorities"])
        normalized = {**values, "authorities": authorities}
        digest = content_sha256(_request_content(**normalized))
        return cls(request_sha256=digest, **normalized)

    @classmethod
    def from_dict(cls, value: object) -> ActionRequest:
        payload = strict_fields(
            value,
            required=(
                "action_id",
                "authorities",
                "authorization_sha256",
                "kind",
                "preflight_sha256",
                "project_id",
                "remote_revision",
                "request_id",
                "request_sha256",
                "schema_version",
                "scope_sha256",
                "snapshot_sha256",
                "target_id",
            ),
            context="ActionRequest",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("ActionRequest schema_version must be 1")
        if payload.pop("kind") != "action_request":
            raise ProtocolValidationError("ActionRequest kind must be action_request")
        payload["authorities"] = _authority_objects(payload["authorities"])
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> ActionRequest:
        return cls.from_dict(parse_json_object(text, context="ActionRequest"))


@dataclass(frozen=True, slots=True)
class ActionDecision:
    status: str
    reason_code: str
    request: ActionRequest | None = None

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        if self.status not in {"allowed", "blocked"}:
            raise ProtocolValidationError("action decision status must be allowed or blocked")
        require_identifier(self.reason_code, field="reason_code")
        if (self.status == "allowed") != isinstance(self.request, ActionRequest):
            raise ProtocolValidationError("only an allowed decision may contain an action request")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "action_decision",
            "reason_code": self.reason_code,
            "request": self.request.to_dict() if self.request else None,
            "schema_version": self.SCHEMA_VERSION,
            "status": self.status,
        }


def _blocked(reason_code: str) -> ActionDecision:
    return ActionDecision(status="blocked", reason_code=reason_code)


def _is_current(record: ActionAuthorization | RemotePreflight, now: datetime) -> bool:
    issued, expires = _time_bounds(record.issued_at, record.expires_at)
    return issued <= now < expires


def _bindings_match(
    record: ActionAuthorization | RemotePreflight,
    *,
    action_id: str,
    target_id: str,
    snapshot: ProjectStatus,
    scope_sha256: str,
    authorities: tuple[AuthorityDigest, ...],
) -> bool:
    return (
        record.project_id == snapshot.project_id
        and record.target_id == target_id
        and record.action_id == action_id
        and record.snapshot_sha256 == snapshot.snapshot_sha256
        and record.scope_sha256 == scope_sha256
        and record.authorities == authorities
    )


def _resolve_record(
    records: tuple[ActionAuthorization | RemotePreflight, ...],
    *,
    issuer_id: str,
    source_id: str,
    action_id: str,
    target_id: str,
    snapshot: ProjectStatus,
    scope_sha256: str,
    authorities: tuple[AuthorityDigest, ...],
    now: datetime,
    name: str,
) -> tuple[ActionAuthorization | RemotePreflight | None, str]:
    has_matching_record = False
    has_trusted_record = False
    current_record: ActionAuthorization | RemotePreflight | None = None
    for record in records:
        if not _bindings_match(
            record,
            action_id=action_id,
            target_id=target_id,
            snapshot=snapshot,
            scope_sha256=scope_sha256,
            authorities=authorities,
        ):
            continue
        has_matching_record = True
        if record.issuer_id != issuer_id or record.source_id != source_id:
            continue
        has_trusted_record = True
        if not _is_current(record, now):
            continue
        if current_record is not None:
            return None, f"{name}_duplicate"
        current_record = record
    if not has_matching_record:
        return None, f"{name}_missing"
    if not has_trusted_record:
        return None, f"{name}_untrusted"
    if current_record is None:
        return None, f"{name}_not_current"
    return current_record, "action_context_resolved"


def resolve_action_context(
    *,
    snapshot: ProjectStatus,
    authority_bundle: AuthorityBundle | None,
    now: datetime,
) -> ActionContext:
    """Resolve one current action binding without side effects or ambient authority."""

    if authority_bundle is None:
        return ActionContext.unavailable("authority_bundle_missing")
    usable = snapshot.for_use(
        clock=lambda: now,
        expected_authorities=authority_bundle.current_authorities,
    )
    if usable.condition is not SnapshotCondition.CURRENT:
        reason = usable.primary_blocker.reason_code if usable.primary_blocker else ""
        if reason == "authority_mismatch":
            return ActionContext.unavailable("authority_drift")
        if reason == "snapshot_stale":
            return ActionContext.unavailable("snapshot_expired")
        return ActionContext.unavailable("snapshot_invalid")

    try:
        current_now = _now(now)
    except ProtocolValidationError:
        return ActionContext.unavailable("snapshot_invalid")
    scope_sha256 = _authority_sha256(authority_bundle.current_authorities, "scope")
    if scope_sha256 is None:
        return ActionContext.unavailable("authority_drift")
    if len(usable.permitted_actions) != 1:
        return ActionContext.unavailable(
            "action_not_permitted" if not usable.permitted_actions else "action_context_ambiguous"
        )
    action_id = usable.permitted_actions[0].action_id
    target_id = authority_bundle.current_remote_profile_id
    authorization, reason = _resolve_record(
        authority_bundle.authorizations,
        issuer_id=authority_bundle.authorization_issuer_id,
        source_id=authority_bundle.authorization_source_id,
        action_id=action_id,
        target_id=target_id,
        snapshot=usable,
        scope_sha256=scope_sha256,
        authorities=authority_bundle.current_authorities,
        now=current_now,
        name="authorization",
    )
    if authorization is None:
        return ActionContext.unavailable(reason)
    preflight, reason = _resolve_record(
        authority_bundle.preflights,
        issuer_id=authority_bundle.preflight_issuer_id,
        source_id=authority_bundle.preflight_source_id,
        action_id=action_id,
        target_id=target_id,
        snapshot=usable,
        scope_sha256=scope_sha256,
        authorities=authority_bundle.current_authorities,
        now=current_now,
        name="preflight",
    )
    if preflight is None:
        return ActionContext.unavailable(reason)
    if preflight.remote_revision != authority_bundle.current_remote_revision:
        return ActionContext.unavailable("remote_target_drift")
    assert isinstance(authorization, ActionAuthorization)
    assert isinstance(preflight, RemotePreflight)
    return ActionContext.resolved(
        action_id=action_id,
        target_id=target_id,
        snapshot_sha256=usable.snapshot_sha256,
        scope_sha256=scope_sha256,
        authorities=authority_bundle.current_authorities,
        authorization_sha256=authorization.authorization_sha256,
        preflight_sha256=preflight.preflight_sha256,
        remote_revision=preflight.remote_revision,
    )


def evaluate_action(
    *,
    request: ActionRequestInput,
    snapshot: ProjectStatus,
    authority_bundle: AuthorityBundle | None,
    now: datetime,
) -> ActionDecision:
    """Return a deterministic request or blocked decision without side effects."""

    context = resolve_action_context(
        snapshot=snapshot,
        authority_bundle=authority_bundle,
        now=now,
    )
    if not context.available:
        return _blocked(context.reason_code)
    context_request_id = context.request_id
    assert context_request_id is not None
    if request.request_id != context_request_id:
        return _blocked("action_context_stale")

    action_request = ActionRequest.create(
        request_id=request.request_id,
        project_id=snapshot.project_id,
        target_id=context.target_id,
        action_id=context.action_id,
        snapshot_sha256=context.snapshot_sha256,
        scope_sha256=context.scope_sha256,
        authorities=context.authorities,
        authorization_sha256=context.authorization_sha256,
        preflight_sha256=context.preflight_sha256,
        remote_revision=context.remote_revision,
    )
    return ActionDecision(
        status="allowed",
        reason_code="action_request_created",
        request=action_request,
    )


__all__ = (
    "ActionAuthorization",
    "ActionContext",
    "ActionDecision",
    "ActionRequest",
    "ActionRequestInput",
    "AuthorityBundle",
    "RemotePreflight",
    "evaluate_action",
    "resolve_action_context",
)
