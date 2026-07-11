"""Public-safe, content-addressed baseline audit authorities."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlsplit

from ._validation import (
    content_sha256,
    require_identifier,
    require_public_string,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
)
from .errors import ProtocolValidationError

_REVISION = re.compile(r"[0-9a-f]{40}")
_CLAIMS = frozenset({"source", "license", "task", "split", "evaluation"})
LINEAGE_LAYERS = frozenset(
    {"model_core", "data_processing", "split_selection", "evaluation_reporting"}
)
_SOURCE_ROLES = frozenset({"canonical_model", "medication_comparison", "lineage_reference"})
CLASSIC_SIX = (
    "gamenet",
    "safedrug",
    "micron",
    "molerec",
    "retain",
    "leap-safedrug",
)


class Disposition(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNRESOLVED = "unresolved"


def _tuple_of_dicts(value: object, *, field: str) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ProtocolValidationError(f"{field} must be a list of objects")
    return tuple(value)


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ProtocolValidationError(f"{field} must be a list")
    result = tuple(require_identifier(item, field=field) for item in value)
    if len(result) != len(set(result)):
        raise ProtocolValidationError(f"{field} entries must be unique")
    return result


@dataclass(frozen=True, slots=True)
class AuditSource:
    source_id: str
    role: str
    repository: str
    revision: str

    def __post_init__(self) -> None:
        require_identifier(self.source_id, field="source_id")
        if self.role not in _SOURCE_ROLES:
            raise ProtocolValidationError("source role is invalid")
        repository = require_single_line_public_string(self.repository, field="repository")
        parsed = urlsplit(repository)
        try:
            port = parsed.port
        except ValueError as error:
            raise ProtocolValidationError("repository must be a public GitHub HTTPS URL") from error
        repository_parts = parsed.path.strip("/").split("/")
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username
            or parsed.password
            or port is not None
            or parsed.query
            or parsed.fragment
            or len(repository_parts) != 2
            or not all(repository_parts)
        ):
            raise ProtocolValidationError("repository must be a public GitHub HTTPS URL")
        if not _REVISION.fullmatch(self.revision):
            raise ProtocolValidationError("source revision must be an immutable commit")

    def to_dict(self) -> dict[str, str]:
        return {
            "repository": self.repository,
            "revision": self.revision,
            "role": self.role,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, value: object) -> AuditSource:
        payload = strict_fields(
            value,
            required=("source_id", "role", "repository", "revision"),
            context="audit source",
        )
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class AuditEvidence:
    evidence_id: str
    claims: tuple[str, ...]
    source_id: str
    repository: str
    revision: str
    retrieved_at: str
    immutable_url: str
    content: str
    content_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.evidence_id, field="evidence_id")
        claims = tuple(require_public_string(item, field="evidence.claims") for item in self.claims)
        allowed = _CLAIMS | {f"lineage.{layer}" for layer in LINEAGE_LAYERS}
        if not claims or len(claims) != len(set(claims)) or not set(claims) <= allowed:
            raise ProtocolValidationError("evidence claims must be unique known claims")
        object.__setattr__(self, "claims", claims)
        require_identifier(self.source_id, field="evidence.source_id")
        require_public_string(self.repository, field="evidence.repository")
        if not _REVISION.fullmatch(self.revision):
            raise ProtocolValidationError("evidence revision must be immutable")
        try:
            timestamp = datetime.fromisoformat(self.retrieved_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as error:
            raise ProtocolValidationError("retrieved_at must be an ISO-8601 timestamp") from error
        if timestamp.tzinfo is None:
            raise ProtocolValidationError("retrieved_at must include a timezone")
        content = require_single_line_public_string(self.content, field="evidence.content")
        require_sha256(self.content_sha256, field="evidence.content_sha256")
        expected = sha256(content.encode("utf-8")).hexdigest()
        if self.content_sha256 != expected:
            raise ProtocolValidationError("evidence content_sha256 does not match content")
        self._validate_immutable_url()

    def _validate_immutable_url(self) -> None:
        parsed = urlsplit(self.immutable_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"github.com", "raw.githubusercontent.com"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ProtocolValidationError(
                "evidence immutable_url must be a public immutable HTTPS URL"
            )
        repository = urlsplit(self.repository)
        repository_parts = repository.path.strip("/").split("/")
        url_parts = parsed.path.strip("/").split("/")
        if len(repository_parts) != 2 or url_parts[:2] != repository_parts:
            raise ProtocolValidationError("evidence URL does not match repository identity")
        if self.revision not in url_parts:
            raise ProtocolValidationError("evidence URL must contain its immutable revision")

    def to_dict(self) -> dict[str, object]:
        return {
            "claims": list(self.claims),
            "content": self.content,
            "content_sha256": self.content_sha256,
            "evidence_id": self.evidence_id,
            "immutable_url": self.immutable_url,
            "repository": self.repository,
            "retrieved_at": self.retrieved_at,
            "revision": self.revision,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, value: object) -> AuditEvidence:
        payload = strict_fields(
            value,
            required=(
                "evidence_id",
                "claims",
                "source_id",
                "repository",
                "revision",
                "retrieved_at",
                "immutable_url",
                "content",
                "content_sha256",
            ),
            context="audit evidence",
        )
        claims = _string_tuple(payload.pop("claims"), field="evidence.claims")
        return cls(claims=claims, **payload)


@dataclass(frozen=True, slots=True)
class AuditClaim:
    name: str
    disposition: Disposition | str
    evidence_ids: tuple[str, ...]
    rationale: str

    def __post_init__(self) -> None:
        if self.name not in _CLAIMS:
            raise ProtocolValidationError("audit claim name is invalid")
        try:
            disposition = Disposition(self.disposition)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError("audit claim disposition is invalid") from error
        object.__setattr__(self, "disposition", disposition)
        evidence_ids = tuple(
            require_identifier(item, field="claim.evidence_ids") for item in self.evidence_ids
        )
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ProtocolValidationError("claim evidence_ids must be unique")
        if disposition is not Disposition.UNRESOLVED and not evidence_ids:
            raise ProtocolValidationError("resolved audit claims require evidence")
        object.__setattr__(self, "evidence_ids", evidence_ids)
        require_single_line_public_string(self.rationale, field="claim.rationale")

    def to_dict(self) -> dict[str, object]:
        return {
            "disposition": self.disposition.value,
            "evidence_ids": list(self.evidence_ids),
            "name": self.name,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, value: object) -> AuditClaim:
        payload = strict_fields(
            value,
            required=("name", "disposition", "evidence_ids", "rationale"),
            context="audit claim",
        )
        evidence_ids = _string_tuple(payload.pop("evidence_ids"), field="claim.evidence_ids")
        return cls(evidence_ids=evidence_ids, **payload)


@dataclass(frozen=True, slots=True)
class LineageEdge:
    layer: str
    upstream: str
    downstream: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.layer not in LINEAGE_LAYERS:
            raise ProtocolValidationError("lineage layer is invalid")
        require_identifier(self.upstream, field="lineage.upstream")
        require_identifier(self.downstream, field="lineage.downstream")
        if self.upstream == self.downstream:
            raise ProtocolValidationError("circular lineage edge is forbidden")
        evidence_ids = tuple(
            require_identifier(item, field="lineage.evidence_ids") for item in self.evidence_ids
        )
        if not evidence_ids:
            raise ProtocolValidationError("evidence-free lineage edge is forbidden")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ProtocolValidationError("lineage evidence_ids must be unique")
        object.__setattr__(self, "evidence_ids", evidence_ids)

    def to_dict(self) -> dict[str, object]:
        return {
            "downstream": self.downstream,
            "evidence_ids": list(self.evidence_ids),
            "layer": self.layer,
            "upstream": self.upstream,
        }

    @classmethod
    def from_dict(cls, value: object) -> LineageEdge:
        payload = strict_fields(
            value,
            required=("layer", "upstream", "downstream", "evidence_ids"),
            context="lineage edge",
        )
        evidence_ids = _string_tuple(payload.pop("evidence_ids"), field="lineage.evidence_ids")
        return cls(evidence_ids=evidence_ids, **payload)


@dataclass(frozen=True, slots=True)
class BaselineAudit:
    baseline_id: str
    display_name: str
    identity_kind: str
    derivative_of: str | None
    sources: tuple[AuditSource, ...]
    evidence: tuple[AuditEvidence, ...]
    claims: tuple[AuditClaim, ...]
    lineage: tuple[LineageEdge, ...]

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.baseline_id, field="baseline_id")
        require_public_string(self.display_name, field="display_name")
        if self.identity_kind not in {"canonical", "derivative"}:
            raise ProtocolValidationError("identity_kind must be canonical or derivative")
        if self.identity_kind == "derivative":
            require_identifier(self.derivative_of, field="derivative_of")
        elif self.derivative_of is not None:
            raise ProtocolValidationError("canonical audit must not declare derivative_of")
        if self.baseline_id == "leap-safedrug" and (
            self.identity_kind != "derivative" or self.derivative_of != "safedrug"
        ):
            raise ProtocolValidationError("leap-safedrug must remain a SafeDrug derivative")
        sources = tuple(
            item if isinstance(item, AuditSource) else AuditSource.from_dict(item)
            for item in self.sources
        )
        evidence = tuple(
            item if isinstance(item, AuditEvidence) else AuditEvidence.from_dict(item)
            for item in self.evidence
        )
        claims = tuple(
            item if isinstance(item, AuditClaim) else AuditClaim.from_dict(item)
            for item in self.claims
        )
        lineage = tuple(
            item if isinstance(item, LineageEdge) else LineageEdge.from_dict(item)
            for item in self.lineage
        )
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "claims", claims)
        object.__setattr__(self, "lineage", lineage)
        self._validate_relations()

    def _validate_relations(self) -> None:
        source_by_id = {item.source_id: item for item in self.sources}
        if not source_by_id or len(source_by_id) != len(self.sources):
            raise ProtocolValidationError("audit source IDs must be non-empty and unique")
        evidence_by_id = {item.evidence_id: item for item in self.evidence}
        if not evidence_by_id or len(evidence_by_id) != len(self.evidence):
            raise ProtocolValidationError("audit evidence IDs must be non-empty and unique")
        for item in self.evidence:
            source = source_by_id.get(item.source_id)
            if source is None:
                raise ProtocolValidationError("evidence references an unknown source")
            if item.repository != source.repository or item.revision != source.revision:
                raise ProtocolValidationError("evidence does not match its source revision")
        claim_by_name = {item.name: item for item in self.claims}
        if set(claim_by_name) != _CLAIMS or len(claim_by_name) != len(self.claims):
            raise ProtocolValidationError(
                "audit must contain the required audit claims exactly once"
            )
        for claim in self.claims:
            for evidence_id in claim.evidence_ids:
                item = evidence_by_id.get(evidence_id)
                if item is None or claim.name not in item.claims:
                    raise ProtocolValidationError("claim references missing or mismatched evidence")
        layers = {edge.layer for edge in self.lineage}
        if layers != LINEAGE_LAYERS:
            raise ProtocolValidationError("audit must cover all four lineage layers")
        known_nodes = {self.baseline_id, *source_by_id}
        keys: set[tuple[str, str, str]] = set()
        for edge in self.lineage:
            if edge.upstream not in known_nodes or edge.downstream not in known_nodes:
                raise ProtocolValidationError("unknown lineage target")
            key = (edge.layer, edge.upstream, edge.downstream)
            if key in keys:
                raise ProtocolValidationError("duplicate lineage edge")
            keys.add(key)
            for evidence_id in edge.evidence_ids:
                item = evidence_by_id.get(evidence_id)
                if item is None or f"lineage.{edge.layer}" not in item.claims:
                    raise ProtocolValidationError(
                        "lineage references missing or mismatched evidence"
                    )
        for layer in LINEAGE_LAYERS:
            graph = {edge.upstream: edge.downstream for edge in self.lineage if edge.layer == layer}
            for start in graph:
                seen: set[str] = set()
                node = start
                while node in graph:
                    if node in seen:
                        raise ProtocolValidationError("circular lineage is forbidden")
                    seen.add(node)
                    node = graph[node]

    @property
    def is_complete(self) -> bool:
        return True

    @property
    def audit_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def claim(self, name: str) -> AuditClaim:
        return next(item for item in self.claims if item.name == name)

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_id": self.baseline_id,
            "claims": [item.to_dict() for item in self.claims],
            "derivative_of": self.derivative_of,
            "display_name": self.display_name,
            "evidence": [item.to_dict() for item in self.evidence],
            "identity_kind": self.identity_kind,
            "lineage": [item.to_dict() for item in self.lineage],
            "schema_version": self.SCHEMA_VERSION,
            "sources": [item.to_dict() for item in self.sources],
        }

    @classmethod
    def from_dict(cls, value: object) -> BaselineAudit:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "baseline_id",
                "display_name",
                "identity_kind",
                "sources",
                "evidence",
                "claims",
                "lineage",
            ),
            optional=("derivative_of",),
            context="BaselineAudit",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("BaselineAudit schema_version must be 1")
        return cls(
            sources=tuple(
                AuditSource.from_dict(item)
                for item in _tuple_of_dicts(payload.pop("sources"), field="sources")
            ),
            evidence=tuple(
                AuditEvidence.from_dict(item)
                for item in _tuple_of_dicts(payload.pop("evidence"), field="evidence")
            ),
            claims=tuple(
                AuditClaim.from_dict(item)
                for item in _tuple_of_dicts(payload.pop("claims"), field="claims")
            ),
            lineage=tuple(
                LineageEdge.from_dict(item)
                for item in _tuple_of_dicts(payload.pop("lineage"), field="lineage")
            ),
            derivative_of=payload.pop("derivative_of", None),
            **payload,
        )

    @classmethod
    def from_toml(cls, text: str) -> BaselineAudit:
        try:
            return cls.from_dict(tomllib.loads(text))
        except tomllib.TOMLDecodeError as error:
            raise ProtocolValidationError("BaselineAudit must be valid TOML") from error

    @classmethod
    def load(cls, path: str | Path) -> BaselineAudit:
        return cls.from_toml(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class BaselineProgram:
    program_id: str
    candidate_ids: tuple[str, ...]

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.program_id, field="program_id")
        candidates = tuple(
            require_identifier(item, field="candidate_ids") for item in self.candidate_ids
        )
        object.__setattr__(self, "candidate_ids", candidates)
        if self.program_id != "classic-six" or candidates != CLASSIC_SIX:
            raise ProtocolValidationError("program must contain the exact classic-six candidates")

    @property
    def program_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def validate_audits(self, audits: tuple[BaselineAudit, ...]) -> None:
        ids = tuple(audit.baseline_id for audit in audits)
        if ids != self.candidate_ids:
            raise ProtocolValidationError("audits must match the exact classic-six candidates")

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_ids": list(self.candidate_ids),
            "program_id": self.program_id,
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def from_dict(cls, value: object) -> BaselineProgram:
        payload = strict_fields(
            value,
            required=("schema_version", "program_id", "candidate_ids"),
            context="BaselineProgram",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("BaselineProgram schema_version must be 1")
        candidates = _string_tuple(payload.pop("candidate_ids"), field="candidate_ids")
        return cls(candidate_ids=candidates, **payload)

    @classmethod
    def from_toml(cls, text: str) -> BaselineProgram:
        try:
            return cls.from_dict(tomllib.loads(text))
        except tomllib.TOMLDecodeError as error:
            raise ProtocolValidationError("BaselineProgram must be valid TOML") from error

    @classmethod
    def load(cls, path: str | Path) -> BaselineProgram:
        return cls.from_toml(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class AuditReview:
    candidate_id: str
    audit_sha256: str
    reviewed_claims: tuple[str, ...]
    reviewer: str
    decision: str
    issued_at: str
    content_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.candidate_id, field="review.candidate_id")
        require_sha256(self.audit_sha256, field="review.audit_sha256")
        if not self.reviewed_claims or not set(self.reviewed_claims) <= {"source", "license"}:
            raise ProtocolValidationError("reviewed_claims must contain source or license")
        require_identifier(self.reviewer, field="review.reviewer")
        if self.decision not in {"pass", "fail"}:
            raise ProtocolValidationError("review decision must be pass or fail")
        require_single_line_public_string(self.issued_at, field="review.issued_at")
        require_sha256(self.content_sha256, field="review.content_sha256")
        if self.content_sha256 != content_sha256(self._content()):
            raise ProtocolValidationError("review content_sha256 does not match content")

    def _content(self) -> dict[str, object]:
        return {
            "audit_sha256": self.audit_sha256,
            "candidate_id": self.candidate_id,
            "decision": self.decision,
            "issued_at": self.issued_at,
            "reviewed_claims": list(self.reviewed_claims),
            "reviewer": self.reviewer,
        }

    @property
    def review_sha256(self) -> str:
        return self.content_sha256

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "content_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: object) -> AuditReview:
        payload = strict_fields(
            value,
            required=(
                "candidate_id",
                "audit_sha256",
                "reviewed_claims",
                "reviewer",
                "decision",
                "issued_at",
                "content_sha256",
            ),
            context="AuditReview",
        )
        claims = _string_tuple(payload.pop("reviewed_claims"), field="reviewed_claims")
        return cls(reviewed_claims=claims, **payload)


@dataclass(frozen=True, slots=True)
class AuditReviewSet:
    reviews: tuple[AuditReview, ...]

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        reviews = tuple(
            item if isinstance(item, AuditReview) else AuditReview.from_dict(item)
            for item in self.reviews
        )
        if len({item.content_sha256 for item in reviews}) != len(reviews):
            raise ProtocolValidationError("audit reviews must be unique")
        object.__setattr__(self, "reviews", reviews)

    def matching_review(self, audit: BaselineAudit, claim: str) -> AuditReview | None:
        audit_claim = audit.claim(claim)
        if audit_claim.disposition is not Disposition.PASS:
            return None
        return next(
            (
                review
                for review in self.reviews
                if review.candidate_id == audit.baseline_id
                and review.audit_sha256 == audit.audit_sha256
                and claim in review.reviewed_claims
                and review.decision == "pass"
            ),
            None,
        )

    def accepts(self, audit: BaselineAudit, claim: str) -> bool:
        return self.matching_review(audit, claim) is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "reviews": [review.to_dict() for review in self.reviews],
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def from_dict(cls, value: object) -> AuditReviewSet:
        payload = strict_fields(
            value,
            required=("schema_version", "reviews"),
            context="AuditReviewSet",
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("AuditReviewSet schema_version must be 1")
        reviews = _tuple_of_dicts(payload["reviews"], field="reviews")
        return cls(tuple(AuditReview.from_dict(item) for item in reviews))

    @classmethod
    def from_json(cls, text: str) -> AuditReviewSet:
        try:
            return cls.from_dict(json.loads(text))
        except (json.JSONDecodeError, TypeError) as error:
            raise ProtocolValidationError("AuditReviewSet must be valid JSON") from error

    @classmethod
    def load(cls, path: str | Path) -> AuditReviewSet:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


__all__ = (
    "CLASSIC_SIX",
    "LINEAGE_LAYERS",
    "AuditReview",
    "AuditReviewSet",
    "BaselineAudit",
    "BaselineProgram",
    "Disposition",
)
