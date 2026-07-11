"""Public-safe, non-authoritative project status snapshots."""

from __future__ import annotations

import ipaddress
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qsl, unquote, urlsplit

from ._validation import (
    canonical_json,
    content_sha256,
    parse_json_object,
    require_identifier,
    require_int,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
    write_json_atomic,
)
from .baseline_audit import CLASSIC_SIX, LINEAGE_LAYERS, BaselineAudit, BaselineProgram
from .benchmark_program import (
    ReproductionCharacterization,
    SelectionResult,
    StabilityStatus,
)
from .benchmark_state import (
    BenchmarkState,
    HumanReviewState,
    program_registry_authority_sha256,
)
from .errors import ProtocolValidationError
from .registry import BaselineRegistry

Clock = Callable[[], datetime]

_APPROVED_EVIDENCE_HOSTS = frozenset(
    {
        "aclanthology.org",
        "arxiv.org",
        "dl.acm.org",
        "doi.org",
        "github.com",
        "ieeexplore.ieee.org",
        "openreview.net",
        "proceedings.mlr.press",
        "pubmed.ncbi.nlm.nih.gov",
        "raw.githubusercontent.com",
    }
)
_CREDENTIAL_QUERY_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "credential",
        "key",
        "password",
        "passwd",
        "secret",
        "sig",
        "signature",
        "token",
    }
)
_READINESS = frozenset({"registered", "smoke_ready", "comparison_ready"})
_DISPOSITIONS = frozenset({"pass", "fail", "unresolved"})


def _objects(value: object, *, field: str) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ProtocolValidationError(f"{field} must be a list of objects")
    return tuple(value)


def _utc_now(clock: Clock) -> datetime:
    try:
        value = clock()
    except Exception as error:  # pragma: no cover - defensive boundary
        raise ProtocolValidationError("clock must return a UTC datetime") from error
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ProtocolValidationError("clock must return a UTC datetime")
    return value.astimezone(UTC).replace(microsecond=0)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtocolValidationError(f"{field} must be a canonical UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ProtocolValidationError(f"{field} must be a canonical UTC timestamp") from error
    if _timestamp(parsed) != value:
        raise ProtocolValidationError(f"{field} must be a canonical UTC timestamp")
    return parsed


def validate_evidence_url(value: object) -> str:
    """Return an approved public evidence URL without resolving any hostname."""

    message = "evidence URL must be an approved absolute public HTTPS URL"
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProtocolValidationError(message)
    decoded = unquote(value)
    if any(ord(character) < 32 or ord(character) == 127 for character in decoded):
        raise ProtocolValidationError(message)
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ProtocolValidationError(message) from error
    hostname = parsed.hostname
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or hostname not in _APPROVED_EVIDENCE_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
    ):
        raise ProtocolValidationError(message)
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ProtocolValidationError(message)
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ProtocolValidationError(message)
    query_keys = {key.casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if query_keys & _CREDENTIAL_QUERY_KEYS:
        raise ProtocolValidationError(message)
    return value


class SnapshotCondition(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    DEGRADED = "degraded"


class BlockerCategory(StrEnum):
    STATUS_INTEGRITY = "status_integrity"
    PRIVACY = "privacy"
    AUTHORIZATION = "authorization"
    SOURCE_LICENSE = "source_license"
    READINESS = "readiness"
    REMOTE_PREFLIGHT = "remote_preflight"


class ProjectStage(StrEnum):
    AUDIT_BLOCKED = "audit_blocked"
    BENCHMARK_IN_PROGRESS = "benchmark_in_progress"
    LANE_PROPOSED = "lane_proposed"
    LANE_CHARACTERIZING = "lane_characterizing"
    PARALLEL_ELIGIBLE = "parallel_eligible"
    REVIEW_PENDING = "review_pending"
    DISCOVERY_ELIGIBLE = "discovery_eligible"


_BLOCKER_PRIORITY = {
    BlockerCategory.STATUS_INTEGRITY: 0,
    BlockerCategory.PRIVACY: 0,
    BlockerCategory.AUTHORIZATION: 1,
    BlockerCategory.SOURCE_LICENSE: 2,
    BlockerCategory.READINESS: 3,
    BlockerCategory.REMOTE_PREFLIGHT: 4,
}


@dataclass(frozen=True, slots=True)
class AuthorityDigest:
    authority_id: str
    sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.authority_id, field="authority_id")
        require_sha256(self.sha256, field="authority.sha256")

    def to_dict(self) -> dict[str, str]:
        return {"authority_id": self.authority_id, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, value: object) -> AuthorityDigest:
        return cls(
            **strict_fields(
                value,
                required=("authority_id", "sha256"),
                context="AuthorityDigest",
            )
        )


@dataclass(frozen=True, slots=True)
class StatusBlocker:
    category: BlockerCategory | str
    reason_code: str
    candidate_id: str | None = None

    def __post_init__(self) -> None:
        try:
            category = BlockerCategory(self.category)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError("blocker category is invalid") from error
        object.__setattr__(self, "category", category)
        require_identifier(self.reason_code, field="blocker.reason_code")
        if self.candidate_id is not None:
            require_identifier(self.candidate_id, field="blocker.candidate_id")

    @property
    def sort_key(self) -> tuple[int, str, str]:
        return (
            _BLOCKER_PRIORITY[self.category],
            self.reason_code,
            self.candidate_id or "",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "category": self.category.value,
            "reason_code": self.reason_code,
        }

    @classmethod
    def from_dict(cls, value: object) -> StatusBlocker:
        return cls(
            **strict_fields(
                value,
                required=("category", "reason_code", "candidate_id"),
                context="StatusBlocker",
            )
        )


_ACTION_LABELS = {
    "refresh_authorization": "Refresh action authorization",
    "resolve_source_license": "Resolve source and license evidence",
    "advance_readiness": "Advance the blocked readiness gate",
    "refresh_remote_preflight": "Refresh remote preflight",
    "request_reproduction": "Request reproduction work",
    "submit_reproduction_evidence": "Submit reproduction evidence",
    "request_next_lane": "Request the next reproduction lane",
    "submit_human_review": "Submit comparison-scope review",
    "begin_discovery": "Begin new-method discovery",
}


@dataclass(frozen=True, slots=True)
class StatusAction:
    action_id: str
    label: str

    def __post_init__(self) -> None:
        require_identifier(self.action_id, field="action_id")
        if _ACTION_LABELS.get(self.action_id) != self.label:
            raise ProtocolValidationError("status action must use the closed action descriptor set")

    @classmethod
    def named(cls, action_id: str) -> StatusAction:
        try:
            return cls(action_id, _ACTION_LABELS[action_id])
        except KeyError as error:
            raise ProtocolValidationError("status action is invalid") from error

    def to_dict(self) -> dict[str, str]:
        return {"action_id": self.action_id, "label": self.label}

    @classmethod
    def from_dict(cls, value: object) -> StatusAction:
        return cls(
            **strict_fields(
                value,
                required=("action_id", "label"),
                context="StatusAction",
            )
        )


def _action_for_blocker(blocker: StatusBlocker) -> StatusAction | None:
    if blocker.reason_code == "comparison_review_pending":
        return StatusAction.named("submit_human_review")
    action_ids = {
        BlockerCategory.AUTHORIZATION: "refresh_authorization",
        BlockerCategory.SOURCE_LICENSE: "resolve_source_license",
        BlockerCategory.READINESS: "advance_readiness",
        BlockerCategory.REMOTE_PREFLIGHT: "refresh_remote_preflight",
    }
    action_id = action_ids.get(blocker.category)
    return StatusAction.named(action_id) if action_id else None


def _action_for_stage(stage: ProjectStage) -> StatusAction | None:
    action_ids = {
        ProjectStage.LANE_PROPOSED: "request_reproduction",
        ProjectStage.LANE_CHARACTERIZING: "submit_reproduction_evidence",
        ProjectStage.PARALLEL_ELIGIBLE: "request_next_lane",
        ProjectStage.REVIEW_PENDING: "submit_human_review",
        ProjectStage.DISCOVERY_ELIGIBLE: "begin_discovery",
    }
    action_id = action_ids.get(stage)
    return StatusAction.named(action_id) if action_id else None


@dataclass(frozen=True, slots=True)
class EvidenceLink:
    label: str
    url: str

    def __post_init__(self) -> None:
        require_single_line_public_string(self.label, field="evidence.label")
        object.__setattr__(self, "url", validate_evidence_url(self.url))

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "url": self.url}

    @classmethod
    def from_dict(cls, value: object) -> EvidenceLink:
        return cls(
            **strict_fields(
                value,
                required=("label", "url"),
                context="EvidenceLink",
            )
        )


@dataclass(frozen=True, slots=True)
class CandidateStatus:
    candidate_id: str
    display_name: str
    readiness: str
    source_gate: str
    license_gate: str
    evidence: tuple[EvidenceLink, ...]

    def __post_init__(self) -> None:
        require_identifier(self.candidate_id, field="candidate_id")
        require_single_line_public_string(self.display_name, field="candidate.display_name")
        if self.readiness not in _READINESS:
            raise ProtocolValidationError("candidate readiness is invalid")
        if self.source_gate not in _DISPOSITIONS or self.license_gate not in _DISPOSITIONS:
            raise ProtocolValidationError("candidate source and license gates are invalid")
        evidence = tuple(
            item if isinstance(item, EvidenceLink) else EvidenceLink.from_dict(item)
            for item in self.evidence
        )
        if not evidence or len(evidence) != len(set(evidence)):
            raise ProtocolValidationError("candidate evidence must be non-empty and unique")
        object.__setattr__(self, "evidence", evidence)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "display_name": self.display_name,
            "evidence": [item.to_dict() for item in self.evidence],
            "license_gate": self.license_gate,
            "readiness": self.readiness,
            "source_gate": self.source_gate,
        }

    @classmethod
    def from_dict(cls, value: object) -> CandidateStatus:
        payload = strict_fields(
            value,
            required=(
                "candidate_id",
                "display_name",
                "readiness",
                "source_gate",
                "license_gate",
                "evidence",
            ),
            context="CandidateStatus",
        )
        return cls(
            evidence=tuple(
                EvidenceLink.from_dict(item)
                for item in _objects(payload.pop("evidence"), field="candidate.evidence")
            ),
            **payload,
        )


@dataclass(frozen=True, slots=True)
class LineageStatus:
    layer: str
    upstream_repository: str
    candidate_ids: tuple[str, ...]
    evidence: tuple[EvidenceLink, ...]

    def __post_init__(self) -> None:
        if self.layer not in LINEAGE_LAYERS:
            raise ProtocolValidationError("lineage layer is invalid")
        object.__setattr__(
            self,
            "upstream_repository",
            validate_evidence_url(self.upstream_repository),
        )
        candidates = tuple(
            require_identifier(item, field="lineage.candidate_ids") for item in self.candidate_ids
        )
        if not candidates or len(candidates) != len(set(candidates)):
            raise ProtocolValidationError("lineage candidate_ids must be non-empty and unique")
        evidence = tuple(
            item if isinstance(item, EvidenceLink) else EvidenceLink.from_dict(item)
            for item in self.evidence
        )
        if not evidence or len(evidence) != len(set(evidence)):
            raise ProtocolValidationError("lineage evidence must be non-empty and unique")
        object.__setattr__(self, "candidate_ids", candidates)
        object.__setattr__(self, "evidence", evidence)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_ids": list(self.candidate_ids),
            "evidence": [item.to_dict() for item in self.evidence],
            "layer": self.layer,
            "upstream_repository": self.upstream_repository,
        }

    @classmethod
    def from_dict(cls, value: object) -> LineageStatus:
        payload = strict_fields(
            value,
            required=("layer", "upstream_repository", "candidate_ids", "evidence"),
            context="LineageStatus",
        )
        candidates = payload.pop("candidate_ids")
        if not isinstance(candidates, list):
            raise ProtocolValidationError("lineage candidate_ids must be a list")
        return cls(
            candidate_ids=tuple(candidates),
            evidence=tuple(
                EvidenceLink.from_dict(item)
                for item in _objects(payload.pop("evidence"), field="lineage.evidence")
            ),
            **payload,
        )


@dataclass(frozen=True, slots=True)
class MedRecStatus:
    stage: ProjectStage | str
    qualified_count: int
    review_state: HumanReviewState | str
    discovery_eligible: bool
    candidates: tuple[CandidateStatus, ...]
    shared_lineage: tuple[LineageStatus, ...]

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        try:
            stage = ProjectStage(self.stage)
            review_state = HumanReviewState(self.review_state)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError(
                "MedRec status stage or review state is invalid"
            ) from error
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "review_state", review_state)
        require_int(self.qualified_count, field="qualified_count")
        if self.qualified_count > len(CLASSIC_SIX):
            raise ProtocolValidationError("qualified_count exceeds the classic-six program")
        if type(self.discovery_eligible) is not bool:
            raise ProtocolValidationError("discovery_eligible must be a boolean")
        candidates = tuple(
            item if isinstance(item, CandidateStatus) else CandidateStatus.from_dict(item)
            for item in self.candidates
        )
        if tuple(item.candidate_id for item in candidates) != CLASSIC_SIX:
            raise ProtocolValidationError("MedRec candidates must be the ordered classic-six")
        lineage = tuple(
            item if isinstance(item, LineageStatus) else LineageStatus.from_dict(item)
            for item in self.shared_lineage
        )
        if {item.layer for item in lineage} != LINEAGE_LAYERS:
            raise ProtocolValidationError("MedRec lineage must project all four layers")
        if any(not set(item.candidate_ids) <= set(CLASSIC_SIX) for item in lineage):
            raise ProtocolValidationError("lineage references an unknown candidate")
        if self.discovery_eligible != (
            self.qualified_count == len(CLASSIC_SIX) and review_state is HumanReviewState.ACCEPTED
        ):
            raise ProtocolValidationError("discovery eligibility does not match scoped readiness")
        if stage is ProjectStage.DISCOVERY_ELIGIBLE and not self.discovery_eligible:
            raise ProtocolValidationError("discovery stage requires discovery eligibility")
        if stage is ProjectStage.REVIEW_PENDING and review_state is not HumanReviewState.PENDING:
            raise ProtocolValidationError("review-pending stage requires a pending review")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "shared_lineage", lineage)

    @classmethod
    def create(
        cls,
        *,
        qualified_count: int,
        review_state: HumanReviewState | str,
        discovery_eligible: bool,
        candidates: tuple[CandidateStatus, ...],
        shared_lineage: tuple[LineageStatus, ...],
        stage: ProjectStage | str | None = None,
    ) -> MedRecStatus:
        normalized_review = HumanReviewState(review_state)
        if stage is None:
            if discovery_eligible:
                stage = ProjectStage.DISCOVERY_ELIGIBLE
            elif normalized_review is HumanReviewState.PENDING:
                stage = ProjectStage.REVIEW_PENDING
            else:
                stage = ProjectStage.BENCHMARK_IN_PROGRESS
        return cls(
            stage=stage,
            qualified_count=qualified_count,
            review_state=normalized_review,
            discovery_eligible=discovery_eligible,
            candidates=candidates,
            shared_lineage=shared_lineage,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "candidates": [item.to_dict() for item in self.candidates],
            "discovery_eligible": self.discovery_eligible,
            "kind": "medrec",
            "qualified_count": self.qualified_count,
            "review_state": self.review_state.value,
            "schema_version": self.SCHEMA_VERSION,
            "shared_lineage": [item.to_dict() for item in self.shared_lineage],
            "stage": self.stage.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> MedRecStatus:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "stage",
                "qualified_count",
                "review_state",
                "discovery_eligible",
                "candidates",
                "shared_lineage",
            ),
            context="MedRecStatus",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("MedRecStatus schema_version must be 1")
        if payload.pop("kind") != "medrec":
            raise ProtocolValidationError("MedRecStatus kind must be medrec")
        return cls(
            candidates=tuple(
                CandidateStatus.from_dict(item)
                for item in _objects(payload.pop("candidates"), field="payload.candidates")
            ),
            shared_lineage=tuple(
                LineageStatus.from_dict(item)
                for item in _objects(payload.pop("shared_lineage"), field="payload.shared_lineage")
            ),
            **payload,
        )


def _status_content(
    *,
    project_id: str,
    condition: SnapshotCondition,
    generated_at: str,
    valid_until: str,
    authorities: tuple[AuthorityDigest, ...],
    blockers: tuple[StatusBlocker, ...],
    primary_blocker: StatusBlocker | None,
    next_action: StatusAction | None,
    permitted_actions: tuple[StatusAction, ...],
    payload: MedRecStatus,
) -> dict[str, object]:
    return {
        "authorities": [item.to_dict() for item in authorities],
        "blockers": [item.to_dict() for item in blockers],
        "condition": condition.value,
        "generated_at": generated_at,
        "kind": "project_status",
        "next_action": next_action.to_dict() if next_action else None,
        "payload": payload.to_dict(),
        "permitted_actions": [item.to_dict() for item in permitted_actions],
        "primary_blocker": primary_blocker.to_dict() if primary_blocker else None,
        "project_id": project_id,
        "schema_version": ProjectStatus.SCHEMA_VERSION,
        "valid_until": valid_until,
    }


@dataclass(frozen=True, slots=True)
class ProjectStatus:
    project_id: str
    condition: SnapshotCondition | str
    generated_at: str
    valid_until: str
    authorities: tuple[AuthorityDigest, ...]
    blockers: tuple[StatusBlocker, ...]
    primary_blocker: StatusBlocker | None
    next_action: StatusAction | None
    permitted_actions: tuple[StatusAction, ...]
    payload: MedRecStatus
    snapshot_sha256: str

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.project_id, field="project_id")
        try:
            condition = SnapshotCondition(self.condition)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError("snapshot condition is invalid") from error
        object.__setattr__(self, "condition", condition)
        generated = _parse_timestamp(self.generated_at, field="generated_at")
        valid_until = _parse_timestamp(self.valid_until, field="valid_until")
        if valid_until <= generated:
            raise ProtocolValidationError("valid_until must be after generated_at")
        authorities = tuple(
            item if isinstance(item, AuthorityDigest) else AuthorityDigest.from_dict(item)
            for item in self.authorities
        )
        authorities = tuple(sorted(authorities, key=lambda item: item.authority_id))
        if not authorities or len({item.authority_id for item in authorities}) != len(authorities):
            raise ProtocolValidationError("authorities must be non-empty and unique")
        blockers = tuple(
            item if isinstance(item, StatusBlocker) else StatusBlocker.from_dict(item)
            for item in self.blockers
        )
        blockers = tuple(sorted(blockers, key=lambda item: item.sort_key))
        if len(blockers) != len(set(blockers)):
            raise ProtocolValidationError("status blockers must be unique")
        if self.primary_blocker is not None and not isinstance(self.primary_blocker, StatusBlocker):
            object.__setattr__(
                self, "primary_blocker", StatusBlocker.from_dict(self.primary_blocker)
            )
        if self.next_action is not None and not isinstance(self.next_action, StatusAction):
            object.__setattr__(self, "next_action", StatusAction.from_dict(self.next_action))
        actions = tuple(
            item if isinstance(item, StatusAction) else StatusAction.from_dict(item)
            for item in self.permitted_actions
        )
        if not isinstance(self.payload, MedRecStatus):
            object.__setattr__(self, "payload", MedRecStatus.from_dict(self.payload))
        object.__setattr__(self, "authorities", authorities)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "permitted_actions", actions)
        expected_primary = blockers[0] if blockers else None
        if self.primary_blocker != expected_primary:
            raise ProtocolValidationError("primary blocker does not match deterministic order")
        if condition is SnapshotCondition.CURRENT:
            expected_action = (
                _action_for_blocker(expected_primary)
                if expected_primary is not None
                else _action_for_stage(self.payload.stage)
            )
            expected_actions = (expected_action,) if expected_action is not None else ()
            if self.next_action != expected_action or actions != expected_actions:
                raise ProtocolValidationError("status actions do not match the primary blocker")
        elif self.next_action is not None or actions:
            raise ProtocolValidationError("stale or degraded status must deny all actions")
        require_sha256(self.snapshot_sha256, field="snapshot_sha256")
        if self.snapshot_sha256 != content_sha256(self._content()):
            raise ProtocolValidationError("snapshot_sha256 does not match status content")

    def _content(self) -> dict[str, object]:
        return _status_content(
            project_id=self.project_id,
            condition=self.condition,
            generated_at=self.generated_at,
            valid_until=self.valid_until,
            authorities=self.authorities,
            blockers=self.blockers,
            primary_blocker=self.primary_blocker,
            next_action=self.next_action,
            permitted_actions=self.permitted_actions,
            payload=self.payload,
        )

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        authorities: Iterable[AuthorityDigest],
        blockers: Iterable[StatusBlocker],
        payload: MedRecStatus,
        clock: Clock,
        freshness: timedelta = timedelta(minutes=5),
    ) -> ProjectStatus:
        now = _utc_now(clock)
        if freshness <= timedelta(0):
            raise ProtocolValidationError("freshness must be greater than zero")
        normalized_authorities = tuple(
            sorted(tuple(authorities), key=lambda item: item.authority_id)
        )
        normalized_blockers = tuple(sorted(tuple(blockers), key=lambda item: item.sort_key))
        primary = normalized_blockers[0] if normalized_blockers else None
        action = _action_for_blocker(primary) if primary else _action_for_stage(payload.stage)
        actions = (action,) if action else ()
        values = {
            "project_id": project_id,
            "condition": SnapshotCondition.CURRENT,
            "generated_at": _timestamp(now),
            "valid_until": _timestamp(now + freshness),
            "authorities": normalized_authorities,
            "blockers": normalized_blockers,
            "primary_blocker": primary,
            "next_action": action,
            "permitted_actions": actions,
            "payload": payload,
        }
        return cls(snapshot_sha256=content_sha256(_status_content(**values)), **values)

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "snapshot_sha256": self.snapshot_sha256}

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, value: object) -> ProjectStatus:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "project_id",
                "condition",
                "generated_at",
                "valid_until",
                "authorities",
                "blockers",
                "primary_blocker",
                "next_action",
                "permitted_actions",
                "payload",
                "snapshot_sha256",
            ),
            context="ProjectStatus",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("ProjectStatus schema_version must be 1")
        if payload.pop("kind") != "project_status":
            raise ProtocolValidationError("ProjectStatus kind must be project_status")
        primary = payload.pop("primary_blocker")
        action = payload.pop("next_action")
        return cls(
            authorities=tuple(
                AuthorityDigest.from_dict(item)
                for item in _objects(payload.pop("authorities"), field="authorities")
            ),
            blockers=tuple(
                StatusBlocker.from_dict(item)
                for item in _objects(payload.pop("blockers"), field="blockers")
            ),
            primary_blocker=StatusBlocker.from_dict(primary) if primary is not None else None,
            next_action=StatusAction.from_dict(action) if action is not None else None,
            permitted_actions=tuple(
                StatusAction.from_dict(item)
                for item in _objects(payload.pop("permitted_actions"), field="permitted_actions")
            ),
            payload=MedRecStatus.from_dict(payload.pop("payload")),
            **payload,
        )

    @classmethod
    def from_json(cls, text: str) -> ProjectStatus:
        return cls.from_dict(parse_json_object(text, context="ProjectStatus"))

    def _fail_closed(self, condition: SnapshotCondition, reason_code: str) -> ProjectStatus:
        blocker = StatusBlocker(BlockerCategory.STATUS_INTEGRITY, reason_code)
        values = {
            "project_id": self.project_id,
            "condition": condition,
            "generated_at": self.generated_at,
            "valid_until": self.valid_until,
            "authorities": self.authorities,
            "blockers": (blocker,),
            "primary_blocker": blocker,
            "next_action": None,
            "permitted_actions": (),
            "payload": self.payload,
        }
        return ProjectStatus(snapshot_sha256=content_sha256(_status_content(**values)), **values)

    def for_use(
        self,
        *,
        clock: Clock,
        expected_authorities: Iterable[AuthorityDigest],
    ) -> ProjectStatus:
        if self.condition is not SnapshotCondition.CURRENT:
            return self
        try:
            now = _utc_now(clock)
        except ProtocolValidationError:
            return self._fail_closed(SnapshotCondition.DEGRADED, "clock_invalid")
        expected = tuple(sorted(tuple(expected_authorities), key=lambda item: item.authority_id))
        if expected != self.authorities:
            return self._fail_closed(SnapshotCondition.DEGRADED, "authority_mismatch")
        if now >= _parse_timestamp(self.valid_until, field="valid_until"):
            return self._fail_closed(SnapshotCondition.STALE, "snapshot_stale")
        return self

    def write_atomic(self, path: str | Path) -> None:
        write_json_atomic(path, self.to_dict())


def _project_lineage(
    program: BaselineProgram,
    audits: tuple[BaselineAudit, ...],
) -> tuple[LineageStatus, ...]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for audit in audits:
        sources = {item.source_id: item.repository for item in audit.sources}
        evidence = {item.evidence_id: item for item in audit.evidence}
        fallback_repository = audit.sources[0].repository
        for edge in audit.lineage:
            repository = sources.get(edge.upstream, fallback_repository)
            group = grouped.setdefault(
                (edge.layer, repository),
                {"candidate_ids": [], "evidence": {}},
            )
            candidate_ids = group["candidate_ids"]
            links = group["evidence"]
            assert isinstance(candidate_ids, list) and isinstance(links, dict)
            if audit.baseline_id not in candidate_ids:
                candidate_ids.append(audit.baseline_id)
            for evidence_id in edge.evidence_ids:
                item = evidence[evidence_id]
                links[evidence_id] = EvidenceLink(evidence_id, item.immutable_url)
    order = {candidate_id: ordinal for ordinal, candidate_id in enumerate(program.candidate_ids)}
    result = []
    for (layer, repository), group in grouped.items():
        candidate_ids = group["candidate_ids"]
        links = group["evidence"]
        assert isinstance(candidate_ids, list) and isinstance(links, dict)
        result.append(
            LineageStatus(
                layer=layer,
                upstream_repository=repository,
                candidate_ids=tuple(sorted(candidate_ids, key=order.__getitem__)),
                evidence=tuple(links[key] for key in sorted(links)),
            )
        )
    return tuple(sorted(result, key=lambda item: (item.layer, item.upstream_repository)))


def publish_medrec_status(
    *,
    program: BaselineProgram,
    audits: tuple[BaselineAudit, ...],
    registry: BaselineRegistry,
    selection: SelectionResult,
    benchmark_state: BenchmarkState,
    clock: Clock,
    characterization: ReproductionCharacterization | None = None,
    freshness: timedelta = timedelta(minutes=5),
) -> ProjectStatus:
    """Project U1-U3 authorities into a public status without mutating them."""

    program.validate_audits(audits)
    program_sha256 = program.program_sha256
    selection_sha256 = content_sha256(selection.to_dict())
    audit_set_sha256 = content_sha256({"audits": [item.audit_sha256 for item in audits]})
    current_registry_sha256 = program_registry_authority_sha256(program, registry)
    if (
        selection.program_sha256 != program_sha256
        or selection.audit_set_sha256 != audit_set_sha256
        or benchmark_state.program_sha256 != program_sha256
        or benchmark_state.registry_authority_sha256 != current_registry_sha256
    ):
        raise ProtocolValidationError("status authorities do not match")
    audit_by_id = {item.baseline_id: item for item in audits}
    candidate_statuses = []
    for candidate_id in program.candidate_ids:
        audit = audit_by_id[candidate_id]
        definition = registry.get(candidate_id)
        candidate_statuses.append(
            CandidateStatus(
                candidate_id=candidate_id,
                display_name=audit.display_name,
                readiness=definition.readiness.value,
                source_gate=audit.claim("source").disposition.value,
                license_gate=audit.claim("license").disposition.value,
                evidence=tuple(
                    EvidenceLink(item.evidence_id, item.immutable_url) for item in audit.evidence
                ),
            )
        )

    blockers: list[StatusBlocker] = []
    if benchmark_state.discovery_eligible:
        stage = ProjectStage.DISCOVERY_ELIGIBLE
    elif benchmark_state.review_state is HumanReviewState.PENDING:
        stage = ProjectStage.REVIEW_PENDING
        blockers.append(StatusBlocker(BlockerCategory.READINESS, "comparison_review_pending"))
    elif selection.status == "blocked":
        stage = ProjectStage.AUDIT_BLOCKED
        for candidate in selection.candidates:
            blockers.extend(
                StatusBlocker(BlockerCategory.SOURCE_LICENSE, reason, candidate.baseline_id)
                for reason in candidate.blockers
            )
    elif characterization is None:
        stage = ProjectStage.LANE_PROPOSED
    else:
        if (
            characterization.baseline_id != selection.selected_candidate_id
            or characterization.accepted_selection_sha256 not in {None, selection_sha256}
        ):
            raise ProtocolValidationError("characterization does not match selected authority")
        if characterization.status is StabilityStatus.STABLE:
            stage = ProjectStage.PARALLEL_ELIGIBLE
        else:
            stage = ProjectStage.LANE_CHARACTERIZING
            if characterization.status is StabilityStatus.FAILED:
                blockers.append(
                    StatusBlocker(
                        BlockerCategory.READINESS,
                        "reproduction_stability_failed",
                        characterization.baseline_id,
                    )
                )

    payload = MedRecStatus.create(
        stage=stage,
        qualified_count=benchmark_state.qualified_count,
        review_state=benchmark_state.review_state,
        discovery_eligible=benchmark_state.discovery_eligible,
        candidates=tuple(candidate_statuses),
        shared_lineage=_project_lineage(program, audits),
    )
    authorities = [
        AuthorityDigest("audit-set", audit_set_sha256),
        AuthorityDigest("program", program_sha256),
        AuthorityDigest("registry", current_registry_sha256),
        AuthorityDigest("scope", benchmark_state.scope.scope_sha256),
        AuthorityDigest("selection", selection_sha256),
    ]
    if characterization is not None:
        authorities.append(
            AuthorityDigest("characterization", content_sha256(characterization.to_dict()))
        )
    return ProjectStatus.create(
        project_id="medrec-research",
        authorities=authorities,
        blockers=blockers,
        payload=payload,
        clock=clock,
        freshness=freshness,
    )


def load_status(
    path: str | Path,
    *,
    clock: Clock,
    expected_authorities: Iterable[AuthorityDigest],
    last_known_good: ProjectStatus | None = None,
) -> ProjectStatus:
    try:
        snapshot = ProjectStatus.from_json(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ProtocolValidationError):
        if last_known_good is None:
            raise
        return last_known_good._fail_closed(SnapshotCondition.DEGRADED, "snapshot_unavailable")
    return snapshot.for_use(clock=clock, expected_authorities=expected_authorities)


__all__ = (
    "AuthorityDigest",
    "BlockerCategory",
    "CandidateStatus",
    "EvidenceLink",
    "LineageStatus",
    "MedRecStatus",
    "ProjectStage",
    "ProjectStatus",
    "SnapshotCondition",
    "StatusAction",
    "StatusBlocker",
    "load_status",
    "publish_medrec_status",
    "validate_evidence_url",
)
