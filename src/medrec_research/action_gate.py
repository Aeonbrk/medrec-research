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
class ActionIntent:
    """Closed request shape accepted from CLI or Web."""

    request_id: str
    action_id: str
    target_id: str
    snapshot_sha256: str
    scope_sha256: str
    authorization_sha256: str
    preflight_sha256: str

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        for field in ("request_id", "action_id", "target_id"):
            require_identifier(getattr(self, field), field=field)
        for field in (
            "snapshot_sha256",
            "scope_sha256",
            "authorization_sha256",
            "preflight_sha256",
        ):
            require_sha256(getattr(self, field), field=field)

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "authorization_sha256": self.authorization_sha256,
            "kind": "action_intent",
            "preflight_sha256": self.preflight_sha256,
            "request_id": self.request_id,
            "schema_version": self.SCHEMA_VERSION,
            "scope_sha256": self.scope_sha256,
            "snapshot_sha256": self.snapshot_sha256,
            "target_id": self.target_id,
        }

    @classmethod
    def from_dict(cls, value: object) -> ActionIntent:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "request_id",
                "action_id",
                "target_id",
                "snapshot_sha256",
                "scope_sha256",
                "authorization_sha256",
                "preflight_sha256",
            ),
            context="ActionIntent",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("ActionIntent schema_version must be 1")
        if payload.pop("kind") != "action_intent":
            raise ProtocolValidationError("ActionIntent kind must be action_intent")
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

    @classmethod
    def create(cls, **values: object) -> ActionRequest:
        authorities = _authorities(values["authorities"])
        normalized = {**values, "authorities": authorities}
        digest = content_sha256(_request_content(**normalized))
        return cls(request_sha256=digest, **normalized)


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
    intent: ActionIntent,
    snapshot: ProjectStatus,
    authorities: tuple[AuthorityDigest, ...],
) -> bool:
    return (
        record.project_id == snapshot.project_id
        and record.target_id == intent.target_id
        and record.action_id == intent.action_id
        and record.snapshot_sha256 == intent.snapshot_sha256
        and record.scope_sha256 == intent.scope_sha256
        and record.authorities == authorities
    )


def evaluate_action(
    *,
    intent: ActionIntent,
    snapshot: ProjectStatus,
    authority_bundle: AuthorityBundle | None,
    now: datetime,
) -> ActionDecision:
    """Return a deterministic request or blocked decision without side effects."""

    expected_authorities = (
        authority_bundle.current_authorities if authority_bundle is not None else ()
    )
    usable = snapshot.for_use(clock=lambda: now, expected_authorities=expected_authorities)
    if authority_bundle is None:
        return _blocked("authority_bundle_missing")
    if usable.condition is not SnapshotCondition.CURRENT:
        reason = usable.primary_blocker.reason_code if usable.primary_blocker else ""
        if reason == "authority_mismatch":
            return _blocked("authority_drift")
        if reason == "snapshot_stale":
            return _blocked("snapshot_expired")
        return _blocked("snapshot_invalid")

    try:
        current_now = _now(now)
    except ProtocolValidationError:
        return _blocked("snapshot_invalid")
    scope_sha256 = _authority_sha256(authority_bundle.current_authorities, "scope")
    if scope_sha256 is None or intent.scope_sha256 != scope_sha256:
        return _blocked("authority_drift")
    if intent.snapshot_sha256 != snapshot.snapshot_sha256:
        return _blocked("snapshot_invalid")
    if intent.action_id not in {item.action_id for item in usable.permitted_actions}:
        return _blocked("action_not_permitted")
    if intent.target_id != authority_bundle.current_remote_profile_id:
        return _blocked("remote_target_drift")

    authorizations = tuple(
        item
        for item in authority_bundle.authorizations
        if item.authorization_sha256 == intent.authorization_sha256
    )
    if not authorizations:
        return _blocked("authorization_missing")
    if len(authorizations) != 1:
        return _blocked("authorization_duplicate")
    authorization = authorizations[0]
    if (
        authorization.issuer_id != authority_bundle.authorization_issuer_id
        or authorization.source_id != authority_bundle.authorization_source_id
    ):
        return _blocked("authorization_untrusted")
    if not _is_current(authorization, current_now):
        return _blocked("authorization_not_current")
    if not _bindings_match(
        authorization,
        intent=intent,
        snapshot=snapshot,
        authorities=authority_bundle.current_authorities,
    ):
        return _blocked("authorization_mismatch")

    preflights = tuple(
        item
        for item in authority_bundle.preflights
        if item.preflight_sha256 == intent.preflight_sha256
    )
    if not preflights:
        return _blocked("preflight_missing")
    if len(preflights) != 1:
        return _blocked("preflight_duplicate")
    preflight = preflights[0]
    if (
        preflight.issuer_id != authority_bundle.preflight_issuer_id
        or preflight.source_id != authority_bundle.preflight_source_id
    ):
        return _blocked("preflight_untrusted")
    if not _is_current(preflight, current_now):
        return _blocked("preflight_not_current")
    if not _bindings_match(
        preflight,
        intent=intent,
        snapshot=snapshot,
        authorities=authority_bundle.current_authorities,
    ):
        return _blocked("preflight_mismatch")
    if preflight.remote_revision != authority_bundle.current_remote_revision:
        return _blocked("remote_target_drift")

    request = ActionRequest.create(
        request_id=intent.request_id,
        project_id=snapshot.project_id,
        target_id=intent.target_id,
        action_id=intent.action_id,
        snapshot_sha256=intent.snapshot_sha256,
        scope_sha256=intent.scope_sha256,
        authorities=authority_bundle.current_authorities,
        authorization_sha256=intent.authorization_sha256,
        preflight_sha256=intent.preflight_sha256,
        remote_revision=preflight.remote_revision,
    )
    return ActionDecision(
        status="allowed",
        reason_code="action_request_created",
        request=request,
    )


__all__ = (
    "ActionAuthorization",
    "ActionDecision",
    "ActionIntent",
    "ActionRequest",
    "AuthorityBundle",
    "RemotePreflight",
    "evaluate_action",
)
