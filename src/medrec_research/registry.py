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
    require_int,
    require_public_string,
    require_sha256,
    require_string,
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
    protocol_amendment_sha256: str | None = None
    method_profile_sha256: str | None = None

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
        for field in ("protocol_amendment_sha256", "method_profile_sha256"):
            value = getattr(self, field)
            if value is not None:
                require_sha256(value, field=field)
        if self.protocol_version == "1.1" and (
            self.protocol_amendment_sha256 is None or self.method_profile_sha256 is None
        ):
            raise ProtocolValidationError(
                "Comparison Protocol v1.1 requires amendment and method profile digests"
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
        protocol_amendment_sha256: str | None = None,
        method_profile_sha256: str | None = None,
    ) -> bool:
        return ComparisonScope(
            protocol_version=self.protocol_version,
            dataset_manifest_sha256=self.dataset_manifest_sha256,
            adaptation_budget_sha256=self.adaptation_budget_sha256,
            protocol_amendment_sha256=self.protocol_amendment_sha256,
            method_profile_sha256=self.method_profile_sha256,
        ).matches(
            protocol_version=protocol_version,
            dataset_manifest_sha256=dataset_manifest_sha256,
            adaptation_budget_sha256=adaptation_budget_sha256,
            protocol_amendment_sha256=protocol_amendment_sha256,
            method_profile_sha256=method_profile_sha256,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "adaptation_budget_sha256": self.adaptation_budget_sha256,
            "dataset_manifest_sha256": self.dataset_manifest_sha256,
            "evidence": [item.to_dict() for item in self.evidence],
            "protocol_version": self.protocol_version,
        }
        if self.protocol_amendment_sha256 is not None:
            payload["protocol_amendment_sha256"] = self.protocol_amendment_sha256
        if self.method_profile_sha256 is not None:
            payload["method_profile_sha256"] = self.method_profile_sha256
        return payload

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
            optional=("method_profile_sha256", "protocol_amendment_sha256"),
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
            protocol_amendment_sha256=payload.get("protocol_amendment_sha256"),
            method_profile_sha256=payload.get("method_profile_sha256"),
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
class ReproductionProgram:
    """One executable upstream-semantics program shared by baseline lanes."""

    program_id: str
    entrypoint: str
    conda_environment: str
    upstream_root: str
    dataset_subdirectory: str
    run_subdirectory: str
    required_inputs: tuple[str, ...]
    import_modules: tuple[str, ...]
    environment_sha256: str | None = None
    probe_contract: str = "generic"
    required_probe_checks: tuple[str, ...] = ()
    expected_dataset_counts: tuple[tuple[str, tuple[int, ...]], ...] = ()

    def __post_init__(self) -> None:
        require_identifier(self.program_id, field="program_id")
        for field in (
            "entrypoint",
            "conda_environment",
            "upstream_root",
            "dataset_subdirectory",
            "run_subdirectory",
        ):
            require_string(getattr(self, field), field=field)
        entrypoint = Path(self.entrypoint)
        if entrypoint.is_absolute() or ".." in entrypoint.parts:
            raise ProtocolValidationError("entrypoint must be a repository-relative path")
        upstream_root = Path(self.upstream_root)
        if not upstream_root.is_absolute() or ".." in upstream_root.parts:
            raise ProtocolValidationError("upstream_root must be an absolute normalized path")
        for field in ("dataset_subdirectory", "run_subdirectory"):
            path = Path(getattr(self, field))
            if path.is_absolute() or ".." in path.parts:
                raise ProtocolValidationError(f"{field} must be a relative normalized path")
        for field in ("required_inputs", "import_modules"):
            values = tuple(require_string(value, field=field) for value in getattr(self, field))
            if not values or len(values) != len(set(values)):
                raise ProtocolValidationError(f"{field} must contain unique values")
            object.__setattr__(self, field, values)
        if self.environment_sha256 is not None:
            require_sha256(self.environment_sha256, field="environment_sha256")
        require_identifier(self.probe_contract, field="probe_contract")
        probe_checks = tuple(
            require_identifier(value, field="required_probe_checks")
            for value in self.required_probe_checks
        )
        if len(probe_checks) != len(set(probe_checks)):
            raise ProtocolValidationError("required_probe_checks must contain unique values")
        object.__setattr__(self, "required_probe_checks", probe_checks)

        count_constraints: list[tuple[str, tuple[int, ...]]] = []
        for constraint in self.expected_dataset_counts:
            if not isinstance(constraint, tuple) or len(constraint) != 2:
                raise ProtocolValidationError(
                    "expected_dataset_counts must contain (name, allowed_values) pairs"
                )
            name, allowed_values = constraint
            require_identifier(name, field="expected_dataset_counts name")
            if not isinstance(allowed_values, tuple) or not allowed_values:
                raise ProtocolValidationError(
                    "expected_dataset_counts allowed_values must be a non-empty tuple"
                )
            values = tuple(
                require_int(
                    value,
                    field=f"expected_dataset_counts.{name}",
                    minimum=0,
                )
                for value in allowed_values
            )
            if len(values) != len(set(values)):
                raise ProtocolValidationError(
                    f"expected_dataset_counts.{name} must contain unique values"
                )
            count_constraints.append((name, values))
        if len({name for name, _ in count_constraints}) != len(count_constraints):
            raise ProtocolValidationError("expected_dataset_counts names must be unique")
        object.__setattr__(self, "expected_dataset_counts", tuple(count_constraints))
        if self.probe_contract != "generic" and (
            not self.required_probe_checks or not self.expected_dataset_counts
        ):
            raise ProtocolValidationError(
                "non-generic probe contracts must declare runtime checks and dataset counts"
            )

    @property
    def is_319_verified(self) -> bool:
        return self.environment_sha256 is not None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "conda_environment": self.conda_environment,
            "dataset_subdirectory": self.dataset_subdirectory,
            "entrypoint": self.entrypoint,
            "import_modules": list(self.import_modules),
            "program_id": self.program_id,
            "required_inputs": list(self.required_inputs),
            "run_subdirectory": self.run_subdirectory,
            "upstream_root": self.upstream_root,
        }
        if self.environment_sha256 is not None:
            payload["environment_sha256"] = self.environment_sha256
        payload["probe_contract"] = self.probe_contract
        payload["required_probe_checks"] = list(self.required_probe_checks)
        payload["expected_dataset_counts"] = {
            name: list(values) for name, values in self.expected_dataset_counts
        }
        return payload

    @classmethod
    def from_dict(cls, value: object) -> ReproductionProgram:
        payload = strict_fields(
            value,
            required=(
                "program_id",
                "entrypoint",
                "conda_environment",
                "upstream_root",
                "dataset_subdirectory",
                "run_subdirectory",
                "required_inputs",
                "import_modules",
            ),
            optional=(
                "environment_sha256",
                "expected_dataset_counts",
                "probe_contract",
                "required_probe_checks",
            ),
            context="Reproduction Program",
        )
        required_inputs = payload["required_inputs"]
        import_modules = payload["import_modules"]
        if not isinstance(required_inputs, list) or not isinstance(import_modules, list):
            raise ProtocolValidationError("Reproduction Program inputs and imports must be lists")
        required_probe_checks = payload.get("required_probe_checks", [])
        expected_dataset_counts = payload.get("expected_dataset_counts", {})
        if not isinstance(required_probe_checks, list):
            raise ProtocolValidationError(
                "Reproduction Program required_probe_checks must be a list"
            )
        if not isinstance(expected_dataset_counts, dict):
            raise ProtocolValidationError(
                "Reproduction Program expected_dataset_counts must be a table"
            )
        count_constraints = []
        for name, values in expected_dataset_counts.items():
            if not isinstance(values, list):
                raise ProtocolValidationError(
                    f"Reproduction Program expected_dataset_counts.{name} must be a list"
                )
            count_constraints.append((name, tuple(values)))
        return cls(
            program_id=payload["program_id"],
            entrypoint=payload["entrypoint"],
            conda_environment=payload["conda_environment"],
            upstream_root=payload["upstream_root"],
            dataset_subdirectory=payload["dataset_subdirectory"],
            run_subdirectory=payload["run_subdirectory"],
            required_inputs=tuple(required_inputs),
            import_modules=tuple(import_modules),
            environment_sha256=payload.get("environment_sha256"),
            probe_contract=payload.get("probe_contract", "generic"),
            required_probe_checks=tuple(required_probe_checks),
            expected_dataset_counts=tuple(count_constraints),
        )


@dataclass(frozen=True, slots=True)
class ReproductionLane:
    """One declared reproduction execution lane mapping a profile to a program."""

    lane_id: str
    scientific_baseline_id: str
    program_id: str
    profile_id: str
    formal_test: str = "yes"
    learning_rate: float | None = None
    default_gpu_index: int | None = None

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, field="lane_id")
        require_identifier(self.scientific_baseline_id, field="scientific_baseline_id")
        require_identifier(self.program_id, field="program_id")
        require_string(self.profile_id, field="profile_id")
        if self.formal_test not in ("yes", "only_if_selected", "no"):
            raise ProtocolValidationError("formal_test must be 'yes', 'only_if_selected', or 'no'")
        if self.learning_rate is not None and self.learning_rate <= 0:
            raise ProtocolValidationError("learning_rate must be a positive float")
        if self.default_gpu_index is not None and self.default_gpu_index < 0:
            raise ProtocolValidationError("default_gpu_index must be a non-negative integer")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "formal_test": self.formal_test,
            "lane_id": self.lane_id,
            "profile_id": self.profile_id,
            "program_id": self.program_id,
            "scientific_baseline_id": self.scientific_baseline_id,
        }
        if self.learning_rate is not None:
            payload["learning_rate"] = self.learning_rate
        if self.default_gpu_index is not None:
            payload["default_gpu_index"] = self.default_gpu_index
        return payload

    @classmethod
    def from_dict(cls, value: object) -> ReproductionLane:
        payload = strict_fields(
            value,
            required=(
                "lane_id",
                "scientific_baseline_id",
                "program_id",
                "profile_id",
            ),
            optional=("formal_test", "learning_rate", "default_gpu_index"),
            context="Reproduction Lane",
        )
        return cls(
            lane_id=payload["lane_id"],
            scientific_baseline_id=payload["scientific_baseline_id"],
            program_id=payload["program_id"],
            profile_id=payload["profile_id"],
            formal_test=payload.get("formal_test", "yes"),
            learning_rate=payload.get("learning_rate"),
            default_gpu_index=payload.get("default_gpu_index"),
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
    reproduction_program: str | None = None
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
        if self.reproduction_program is not None:
            require_identifier(self.reproduction_program, field="reproduction_program")
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
                item.protocol_amendment_sha256,
                item.method_profile_sha256,
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
        protocol_amendment_sha256: str | None = None,
        method_profile_sha256: str | None = None,
    ) -> bool:
        return self.is_comparable and any(
            qualification.matches(
                protocol_version=protocol_version,
                dataset_manifest_sha256=dataset_manifest_sha256,
                adaptation_budget_sha256=adaptation_budget_sha256,
                protocol_amendment_sha256=protocol_amendment_sha256,
                method_profile_sha256=method_profile_sha256,
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
        if self.reproduction_program is not None:
            payload["reproduction_program"] = self.reproduction_program
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
                "reproduction_program",
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
            reproduction_program=payload.get("reproduction_program"),
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
    reproduction_programs: tuple[ReproductionProgram, ...] = ()
    reproduction_lanes: tuple[ReproductionLane, ...] = ()

    def __post_init__(self) -> None:
        baselines = tuple(
            baseline
            if isinstance(baseline, BaselineDefinition)
            else BaselineDefinition.from_dict(baseline)
            for baseline in self.baselines
        )
        if len({baseline.baseline_id for baseline in baselines}) != len(baselines):
            raise ProtocolValidationError("baseline_id values must be unique")
        programs = tuple(
            program
            if isinstance(program, ReproductionProgram)
            else ReproductionProgram.from_dict(program)
            for program in self.reproduction_programs
        )
        if len({program.program_id for program in programs}) != len(programs):
            raise ProtocolValidationError("program_id values must be unique")
        program_ids = {program.program_id for program in programs}
        baseline_ids = {baseline.baseline_id for baseline in baselines}
        missing = sorted(
            {
                baseline.reproduction_program
                for baseline in baselines
                if baseline.reproduction_program is not None
                and baseline.reproduction_program not in program_ids
            }
        )
        if missing:
            raise ProtocolValidationError(
                "baseline references unknown Reproduction Program(s): " + ", ".join(missing)
            )
        lanes = tuple(
            lane if isinstance(lane, ReproductionLane) else ReproductionLane.from_dict(lane)
            for lane in self.reproduction_lanes
        )
        if len({lane.lane_id for lane in lanes}) != len(lanes):
            raise ProtocolValidationError("lane_id values must be unique")
        missing_lane_programs = sorted(
            {lane.program_id for lane in lanes if lane.program_id not in program_ids}
        )
        if missing_lane_programs:
            raise ProtocolValidationError(
                "reproduction lane references unknown Reproduction Program(s): "
                + ", ".join(missing_lane_programs)
            )
        missing_lane_baselines = sorted(
            {
                lane.scientific_baseline_id
                for lane in lanes
                if lane.scientific_baseline_id not in baseline_ids
            }
        )
        if missing_lane_baselines:
            raise ProtocolValidationError(
                "reproduction lane references unknown scientific baseline(s): "
                + ", ".join(missing_lane_baselines)
            )
        object.__setattr__(self, "baselines", baselines)
        object.__setattr__(self, "reproduction_programs", programs)
        object.__setattr__(self, "reproduction_lanes", lanes)

    def get(self, baseline_id: str) -> BaselineDefinition:
        for baseline in self.baselines:
            if baseline.baseline_id == baseline_id:
                return baseline
        raise KeyError(baseline_id)

    def get_program(self, program_id: str) -> ReproductionProgram:
        for program in self.reproduction_programs:
            if program.program_id == program_id:
                return program
        raise KeyError(program_id)

    def get_lane(self, lane_id: str) -> ReproductionLane:
        for lane in self.reproduction_lanes:
            if lane.lane_id == lane_id:
                return lane
        raise KeyError(lane_id)

    def reproduction_program_for(self, baseline: BaselineDefinition) -> ReproductionProgram:
        if baseline.reproduction_program is None:
            raise ProtocolValidationError(
                f"baseline '{baseline.baseline_id}' has no Reproduction Program"
            )
        for program in self.reproduction_programs:
            if program.program_id == baseline.reproduction_program:
                return program
        raise ProtocolValidationError(
            f"baseline '{baseline.baseline_id}' references an unknown Reproduction Program"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "baselines": [baseline.to_dict() for baseline in self.baselines],
            "reproduction_lanes": [lane.to_dict() for lane in self.reproduction_lanes],
            "reproduction_programs": [program.to_dict() for program in self.reproduction_programs],
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def from_dict(cls, value: object) -> BaselineRegistry:
        payload = strict_fields(
            value,
            required=("schema_version", "baselines"),
            optional=("reproduction_lanes", "reproduction_programs"),
            context="BaselineRegistry",
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ProtocolValidationError(
                f"BaselineRegistry schema_version must be {cls.SCHEMA_VERSION}"
            )
        baselines = payload["baselines"]
        if not isinstance(baselines, list):
            raise ProtocolValidationError("BaselineRegistry.baselines must be a list")
        programs = payload.get("reproduction_programs", [])
        if not isinstance(programs, list):
            raise ProtocolValidationError("BaselineRegistry.reproduction_programs must be a list")
        lanes = payload.get("reproduction_lanes", [])
        if not isinstance(lanes, list):
            raise ProtocolValidationError("BaselineRegistry.reproduction_lanes must be a list")
        return cls(
            tuple(BaselineDefinition.from_dict(item) for item in baselines),
            tuple(ReproductionProgram.from_dict(item) for item in programs),
            tuple(ReproductionLane.from_dict(item) for item in lanes),
        )

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
    "ReproductionLane",
    "ReproductionProgram",
    "ResearchMode",
    "SourceIdentity",
    "SourceStatus",
)
