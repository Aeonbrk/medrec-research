"""Validated baseline identities and monotonic readiness state."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from ._validation import (
    content_sha256,
    enum_member,
    require_identifier,
    require_public_string,
    require_sha256,
    strict_fields,
)
from .comparison_scope import ComparisonScope
from .errors import ProtocolValidationError


class ResearchMode(StrEnum):
    """Scientific semantics under which a baseline runs."""

    REPRODUCTION = "reproduction"
    COMPARISON = "comparison"


class SourceStatus(StrEnum):
    """Whether an external source has an immutable revision."""

    PINNED = "pinned"
    NEEDS_PIN = "needs_pin"


class BaselineReadiness(StrEnum):
    """Monotonic baseline integration state."""

    REGISTERED = "registered"
    SMOKE_READY = "smoke_ready"
    COMPARISON_READY = "comparison_ready"


class ReadinessGate(StrEnum):
    """Protocol evidence required before a readiness claim is accepted."""

    ADAPTER_SMOKE = "adapter_smoke"
    ENVIRONMENT_LOCK = "environment_lock"
    ADAPTATION_BUDGET = "adaptation_budget"
    COHORT_IDENTITY = "cohort_identity"
    CORE_INTEGRITY = "core_integrity"
    DETERMINISTIC_ADAPTER = "deterministic_adapter"
    INDEPENDENT_EVALUATION = "independent_evaluation"


_SMOKE_GATES = frozenset(
    {
        ReadinessGate.ADAPTER_SMOKE,
        ReadinessGate.ENVIRONMENT_LOCK,
    }
)
_QUALIFICATION_GATES = frozenset(
    {
        ReadinessGate.ADAPTATION_BUDGET,
        ReadinessGate.COHORT_IDENTITY,
        ReadinessGate.CORE_INTEGRITY,
        ReadinessGate.DETERMINISTIC_ADAPTER,
        ReadinessGate.INDEPENDENT_EVALUATION,
    }
)


_NEXT_READINESS = {
    BaselineReadiness.REGISTERED: BaselineReadiness.SMOKE_READY,
    BaselineReadiness.SMOKE_READY: BaselineReadiness.COMPARISON_READY,
}


@dataclass(frozen=True, slots=True)
class ReadinessEvidence:
    """Content-addressed artifact proving one readiness gate."""

    gate: ReadinessGate | str
    artifact_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "gate", enum_member(ReadinessGate, self.gate, field="gate"))
        require_sha256(self.artifact_sha256, field="artifact_sha256")

    def to_dict(self) -> dict[str, str]:
        return {"artifact_sha256": self.artifact_sha256, "gate": self.gate.value}

    @classmethod
    def from_dict(cls, value: object) -> ReadinessEvidence:
        payload = strict_fields(
            value,
            required=("gate", "artifact_sha256"),
            context="readiness evidence",
        )
        return cls(gate=payload["gate"], artifact_sha256=payload["artifact_sha256"])


@dataclass(frozen=True, slots=True)
class ComparisonQualification:
    """Evidence that one baseline is comparable in one declared research scope."""

    protocol_version: str
    dataset_manifest_sha256: str
    adaptation_budget_sha256: str
    evidence: tuple[ReadinessEvidence, ...]

    def __post_init__(self) -> None:
        require_public_string(self.protocol_version, field="protocol_version")
        require_sha256(
            self.dataset_manifest_sha256,
            field="dataset_manifest_sha256",
        )
        require_sha256(
            self.adaptation_budget_sha256,
            field="adaptation_budget_sha256",
        )
        evidence = tuple(
            item if isinstance(item, ReadinessEvidence) else ReadinessEvidence.from_dict(item)
            for item in self.evidence
        )
        if len(evidence) != len({item.gate for item in evidence}):
            raise ProtocolValidationError("qualification evidence gates must be unique")
        evidence_by_gate = {item.gate: item for item in evidence}
        unexpected = sorted(gate.value for gate in evidence_by_gate.keys() - _QUALIFICATION_GATES)
        if unexpected:
            raise ProtocolValidationError(
                "Comparison Qualification has invalid evidence gate(s): " + ", ".join(unexpected)
            )
        missing = sorted(gate.value for gate in _QUALIFICATION_GATES - evidence_by_gate.keys())
        if missing:
            raise ProtocolValidationError(
                "Comparison Qualification missing evidence gate(s): " + ", ".join(missing)
            )
        if (
            evidence_by_gate[ReadinessGate.ADAPTATION_BUDGET].artifact_sha256
            != self.adaptation_budget_sha256
        ):
            raise ProtocolValidationError(
                "Adaptation Budget evidence must match adaptation_budget_sha256"
            )
        object.__setattr__(self, "evidence", evidence)

    @property
    def qualification_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def matches(
        self,
        *,
        protocol_version: str,
        dataset_manifest_sha256: str,
        adaptation_budget_sha256: str,
    ) -> bool:
        return ComparisonScope(
            protocol_version=self.protocol_version,
            dataset_manifest_sha256=self.dataset_manifest_sha256,
            adaptation_budget_sha256=self.adaptation_budget_sha256,
        ).matches(
            protocol_version=protocol_version,
            dataset_manifest_sha256=dataset_manifest_sha256,
            adaptation_budget_sha256=adaptation_budget_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "adaptation_budget_sha256": self.adaptation_budget_sha256,
            "dataset_manifest_sha256": self.dataset_manifest_sha256,
            "evidence": [item.to_dict() for item in self.evidence],
            "protocol_version": self.protocol_version,
        }

    @classmethod
    def from_dict(cls, value: object) -> ComparisonQualification:
        payload = strict_fields(
            value,
            required=(
                "protocol_version",
                "dataset_manifest_sha256",
                "adaptation_budget_sha256",
                "evidence",
            ),
            context="Comparison Qualification",
        )
        evidence = payload["evidence"]
        if not isinstance(evidence, list):
            raise ProtocolValidationError("Comparison Qualification evidence must be a list")
        return cls(
            protocol_version=payload["protocol_version"],
            dataset_manifest_sha256=payload["dataset_manifest_sha256"],
            adaptation_budget_sha256=payload["adaptation_budget_sha256"],
            evidence=tuple(ReadinessEvidence.from_dict(item) for item in evidence),
        )


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    """Public upstream identity without a local checkout path."""

    repository: str | None
    revision: str | None
    status: SourceStatus | str

    def __post_init__(self) -> None:
        status = enum_member(SourceStatus, self.status, field="source.status")
        object.__setattr__(self, "status", status)
        if status is SourceStatus.PINNED:
            repository = require_public_string(self.repository, field="source.repository")
            revision = require_public_string(self.revision, field="source.revision")
            if revision.lower() in {"head", "latest", "main", "master", "unknown"}:
                raise ProtocolValidationError("pinned source.revision must be immutable")
            object.__setattr__(self, "repository", repository)
            object.__setattr__(self, "revision", revision)
        else:
            if self.repository is not None:
                object.__setattr__(
                    self,
                    "repository",
                    require_public_string(self.repository, field="source.repository"),
                )
            if self.revision is not None:
                raise ProtocolValidationError("needs_pin source must not claim a revision")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"status": self.status.value}
        if self.repository is not None:
            payload["repository"] = self.repository
        if self.revision is not None:
            payload["revision"] = self.revision
        return payload

    @classmethod
    def from_dict(cls, value: object) -> SourceIdentity:
        payload = strict_fields(
            value,
            required=("status",),
            optional=("repository", "revision"),
            context="source identity",
        )
        return cls(
            repository=payload.get("repository"),
            revision=payload.get("revision"),
            status=payload["status"],
        )


@dataclass(frozen=True, slots=True)
class BaselineDefinition:
    """One baseline's source, modes, adapter, and verified readiness."""

    baseline_id: str
    display_name: str
    source: SourceIdentity
    supported_modes: tuple[ResearchMode, ...]
    readiness: BaselineReadiness | str
    adapter_command: tuple[str, ...] = ()
    adapter_revision: str | None = None
    environment_sha256: str | None = None
    readiness_evidence: tuple[ReadinessEvidence, ...] = ()
    comparison_qualifications: tuple[ComparisonQualification, ...] = ()
    archive_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_identifier(self.baseline_id, field="baseline_id")
        require_public_string(self.display_name, field="display_name")
        if not isinstance(self.source, SourceIdentity):
            raise ProtocolValidationError("baseline source must be a SourceIdentity")
        modes = tuple(
            enum_member(ResearchMode, mode, field="supported_modes")
            for mode in self.supported_modes
        )
        if not modes or len(modes) != len(set(modes)):
            raise ProtocolValidationError("supported_modes must contain unique scientific modes")
        object.__setattr__(self, "supported_modes", modes)
        readiness = enum_member(BaselineReadiness, self.readiness, field="readiness")
        object.__setattr__(self, "readiness", readiness)
        command = tuple(
            require_public_string(part, field="adapter_command") for part in self.adapter_command
        )
        object.__setattr__(self, "adapter_command", command)
        adapter_revision = self.adapter_revision
        if adapter_revision is not None:
            adapter_revision = require_public_string(
                adapter_revision,
                field="adapter_revision",
            )
            if adapter_revision.lower() in {
                "head",
                "latest",
                "main",
                "master",
                "unknown",
            }:
                raise ProtocolValidationError("adapter_revision must be immutable")
        object.__setattr__(self, "adapter_revision", adapter_revision)
        if self.environment_sha256 is not None:
            require_sha256(self.environment_sha256, field="environment_sha256")
        evidence = tuple(
            item if isinstance(item, ReadinessEvidence) else ReadinessEvidence.from_dict(item)
            for item in self.readiness_evidence
        )
        if len(evidence) != len({item.gate for item in evidence}):
            raise ProtocolValidationError("readiness evidence gates must be unique")
        object.__setattr__(self, "readiness_evidence", evidence)
        qualifications = tuple(
            item
            if isinstance(item, ComparisonQualification)
            else ComparisonQualification.from_dict(item)
            for item in self.comparison_qualifications
        )
        qualification_scopes = {
            (
                item.protocol_version,
                item.dataset_manifest_sha256,
                item.adaptation_budget_sha256,
            )
            for item in qualifications
        }
        if len(qualification_scopes) != len(qualifications):
            raise ProtocolValidationError("Comparison Qualification scopes must be unique")
        object.__setattr__(self, "comparison_qualifications", qualifications)
        archive_evidence = tuple(
            require_public_string(item, field="archive_evidence") for item in self.archive_evidence
        )
        if len(archive_evidence) != len(set(archive_evidence)):
            raise ProtocolValidationError("archive_evidence entries must be unique")
        object.__setattr__(self, "archive_evidence", archive_evidence)
        evidence_gates = {item.gate for item in evidence}
        if readiness is BaselineReadiness.REGISTERED and (evidence or qualifications):
            raise ProtocolValidationError("registered baseline must not claim readiness evidence")
        if readiness is not BaselineReadiness.REGISTERED:
            if self.source.status is not SourceStatus.PINNED:
                raise ProtocolValidationError("ready baseline source must be pinned")
            if not command:
                raise ProtocolValidationError("ready baseline must declare an adapter_command")
            if adapter_revision is None:
                raise ProtocolValidationError("ready baseline must pin adapter_revision")
            if self.environment_sha256 is None:
                raise ProtocolValidationError("ready baseline must pin environment_sha256")
            missing_gates = sorted(gate.value for gate in _SMOKE_GATES - evidence_gates)
            if missing_gates:
                raise ProtocolValidationError(
                    "missing readiness evidence gate(s): " + ", ".join(missing_gates)
                )
            unexpected_gates = sorted(gate.value for gate in evidence_gates - _SMOKE_GATES)
            if unexpected_gates:
                raise ProtocolValidationError(
                    "baseline readiness has invalid evidence gate(s): "
                    + ", ".join(unexpected_gates)
                )
        if readiness is BaselineReadiness.SMOKE_READY and qualifications:
            raise ProtocolValidationError(
                "smoke-ready baseline must not claim Comparison Qualifications"
            )
        if readiness is BaselineReadiness.COMPARISON_READY:
            if ResearchMode.COMPARISON not in modes:
                raise ProtocolValidationError(
                    "comparison-ready baseline must support comparison mode"
                )
            if not qualifications:
                raise ProtocolValidationError(
                    "comparison-ready baseline requires a Comparison Qualification"
                )

    @property
    def is_comparable(self) -> bool:
        return (
            self.readiness is BaselineReadiness.COMPARISON_READY
            and self.source.status is SourceStatus.PINNED
            and ResearchMode.COMPARISON in self.supported_modes
            and self.adapter_revision is not None
            and self.environment_sha256 is not None
            and bool(self.comparison_qualifications)
        )

    def qualifies_for(
        self,
        *,
        protocol_version: str,
        dataset_manifest_sha256: str,
        adaptation_budget_sha256: str,
    ) -> bool:
        return self.is_comparable and any(
            qualification.matches(
                protocol_version=protocol_version,
                dataset_manifest_sha256=dataset_manifest_sha256,
                adaptation_budget_sha256=adaptation_budget_sha256,
            )
            for qualification in self.comparison_qualifications
        )

    def add_comparison_qualification(
        self,
        qualification: ComparisonQualification,
    ) -> BaselineDefinition:
        if self.readiness is not BaselineReadiness.COMPARISON_READY:
            raise ProtocolValidationError(
                "new Comparison Qualifications require a comparison-ready baseline"
            )
        return replace(
            self,
            comparison_qualifications=(*self.comparison_qualifications, qualification),
        )

    @property
    def definition_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def advance_readiness(
        self,
        target: BaselineReadiness | str,
        *,
        evidence: tuple[ReadinessEvidence, ...] = (),
        qualifications: tuple[ComparisonQualification, ...] = (),
    ) -> BaselineDefinition:
        next_readiness = enum_member(BaselineReadiness, target, field="readiness")
        expected = _NEXT_READINESS.get(self.readiness)
        if next_readiness is not expected:
            expected_name = expected.value if expected is not None else "no further state"
            raise ProtocolValidationError(
                f"invalid readiness transition: {self.readiness.value} may advance only to "
                f"{expected_name}"
            )
        if next_readiness is BaselineReadiness.SMOKE_READY:
            if not evidence or qualifications:
                raise ProtocolValidationError(
                    "smoke readiness transition requires new readiness evidence"
                )
            new_evidence = (*self.readiness_evidence, *evidence)
            new_qualifications = self.comparison_qualifications
        else:
            if evidence or not qualifications:
                raise ProtocolValidationError(
                    "comparison readiness transition requires Comparison Qualifications"
                )
            new_evidence = self.readiness_evidence
            new_qualifications = (*self.comparison_qualifications, *qualifications)
        return replace(
            self,
            readiness=next_readiness,
            readiness_evidence=new_evidence,
            comparison_qualifications=new_qualifications,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "adapter_command": list(self.adapter_command),
            "archive_evidence": list(self.archive_evidence),
            "baseline_id": self.baseline_id,
            "comparison_qualifications": [
                item.to_dict() for item in self.comparison_qualifications
            ],
            "display_name": self.display_name,
            "readiness": self.readiness.value,
            "readiness_evidence": [item.to_dict() for item in self.readiness_evidence],
            "source": self.source.to_dict(),
            "supported_modes": [mode.value for mode in self.supported_modes],
        }
        if self.adapter_revision is not None:
            payload["adapter_revision"] = self.adapter_revision
        if self.environment_sha256 is not None:
            payload["environment_sha256"] = self.environment_sha256
        return payload

    @classmethod
    def from_dict(cls, value: object) -> BaselineDefinition:
        payload = strict_fields(
            value,
            required=(
                "baseline_id",
                "display_name",
                "source",
                "supported_modes",
                "readiness",
            ),
            optional=(
                "adapter_command",
                "adapter_revision",
                "archive_evidence",
                "comparison_qualifications",
                "environment_sha256",
                "readiness_evidence",
            ),
            context="baseline",
        )
        modes = payload["supported_modes"]
        command = payload.get("adapter_command", [])
        evidence = payload.get("readiness_evidence", [])
        qualifications = payload.get("comparison_qualifications", [])
        archive_evidence = payload.get("archive_evidence", [])
        if not isinstance(modes, list):
            raise ProtocolValidationError("supported_modes must be a list")
        if not isinstance(command, list):
            raise ProtocolValidationError("adapter_command must be a list")
        if not isinstance(evidence, list):
            raise ProtocolValidationError("readiness_evidence must be a list")
        if not isinstance(qualifications, list):
            raise ProtocolValidationError("comparison_qualifications must be a list")
        if not isinstance(archive_evidence, list):
            raise ProtocolValidationError("archive_evidence must be a list")
        return cls(
            baseline_id=payload["baseline_id"],
            display_name=payload["display_name"],
            source=SourceIdentity.from_dict(payload["source"]),
            supported_modes=tuple(modes),
            readiness=payload["readiness"],
            adapter_command=tuple(command),
            adapter_revision=payload.get("adapter_revision"),
            environment_sha256=payload.get("environment_sha256"),
            readiness_evidence=tuple(ReadinessEvidence.from_dict(item) for item in evidence),
            comparison_qualifications=tuple(
                ComparisonQualification.from_dict(item) for item in qualifications
            ),
            archive_evidence=tuple(archive_evidence),
        )


@dataclass(frozen=True, slots=True)
class BaselineRegistry:
    """Validated lookup table loaded from the versioned TOML registry."""

    SCHEMA_VERSION: ClassVar[int] = 1

    baselines: tuple[BaselineDefinition, ...]

    def __post_init__(self) -> None:
        baselines = tuple(
            baseline
            if isinstance(baseline, BaselineDefinition)
            else BaselineDefinition.from_dict(baseline)
            for baseline in self.baselines
        )
        if len({baseline.baseline_id for baseline in baselines}) != len(baselines):
            raise ProtocolValidationError("baseline_id values must be unique")
        object.__setattr__(self, "baselines", baselines)

    def get(self, baseline_id: str) -> BaselineDefinition:
        for baseline in self.baselines:
            if baseline.baseline_id == baseline_id:
                return baseline
        raise KeyError(baseline_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "baselines": [baseline.to_dict() for baseline in self.baselines],
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def from_dict(cls, value: object) -> BaselineRegistry:
        payload = strict_fields(
            value,
            required=("schema_version", "baselines"),
            context="BaselineRegistry",
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ProtocolValidationError(
                f"BaselineRegistry schema_version must be {cls.SCHEMA_VERSION}"
            )
        baselines = payload["baselines"]
        if not isinstance(baselines, list):
            raise ProtocolValidationError("BaselineRegistry.baselines must be a list")
        return cls(tuple(BaselineDefinition.from_dict(item) for item in baselines))

    @classmethod
    def from_toml(cls, text: str) -> BaselineRegistry:
        try:
            return cls.from_dict(tomllib.loads(text))
        except tomllib.TOMLDecodeError as error:
            raise ProtocolValidationError("BaselineRegistry must be valid TOML") from error

    @classmethod
    def load(cls, path: str | Path) -> BaselineRegistry:
        with Path(path).open("rb") as stream:
            try:
                return cls.from_dict(tomllib.load(stream))
            except tomllib.TOMLDecodeError as error:
                raise ProtocolValidationError("BaselineRegistry must be valid TOML") from error


__all__ = (
    "BaselineDefinition",
    "BaselineReadiness",
    "BaselineRegistry",
    "ComparisonQualification",
    "ReadinessEvidence",
    "ReadinessGate",
    "ResearchMode",
    "SourceIdentity",
    "SourceStatus",
)
