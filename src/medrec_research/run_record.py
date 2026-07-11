"""Immutable public-safe records for accepted Comparison Mode runs."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    enum_member,
    parse_json_object,
    require_identifier,
    require_int,
    require_public_string,
    require_sha256,
    strict_fields,
)
from .dataset import DatasetManifest, SplitName
from .errors import ProtocolValidationError
from .evaluation import EvaluationResult
from .registry import (
    BaselineDefinition,
    BaselineReadiness,
    ResearchMode,
    SourceIdentity,
    SourceStatus,
)

RunParameterValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class RunParameter:
    """One public scalar configuration value."""

    name: str
    value: RunParameterValue

    def __post_init__(self) -> None:
        require_identifier(self.name, field="parameter.name")
        if isinstance(self.value, str):
            object.__setattr__(
                self,
                "value",
                require_public_string(self.value, field=f"parameter {self.name}"),
            )
        elif isinstance(self.value, (bool, int)):
            pass
        elif not isinstance(self.value, float) or not math.isfinite(self.value):
            raise ProtocolValidationError("run parameter values must be finite JSON scalars")

    def to_dict(self) -> dict[str, RunParameterValue]:
        return {"name": self.name, "value": self.value}

    @classmethod
    def from_dict(cls, value: object) -> RunParameter:
        payload = strict_fields(value, required=("name", "value"), context="RunParameter")
        return cls(name=payload["name"], value=payload["value"])


@dataclass(frozen=True, slots=True)
class ArtifactChecksum:
    """Public identity of one restricted or public run artifact."""

    name: str
    sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.name, field="artifact.name")
        require_sha256(self.sha256, field=f"artifact {self.name}.sha256")

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, value: object) -> ArtifactChecksum:
        payload = strict_fields(
            value,
            required=("name", "sha256"),
            context="ArtifactChecksum",
        )
        return cls(name=payload["name"], sha256=payload["sha256"])


def _configuration_dict(
    seed: int,
    selection_split: SplitName,
    evaluation_split: SplitName,
    adaptation_budget_sha256: str,
    parameters: tuple[RunParameter, ...],
) -> dict[str, object]:
    return {
        "adaptation_budget_sha256": adaptation_budget_sha256,
        "evaluation_split": evaluation_split.value,
        "parameters": [parameter.to_dict() for parameter in parameters],
        "seed": seed,
        "selection_split": selection_split.value,
    }


def _record_payload(
    *,
    protocol_version: str,
    baseline_id: str,
    baseline_source: SourceIdentity,
    baseline_readiness: BaselineReadiness,
    baseline_definition_sha256: str,
    adapter_revision: str,
    environment_sha256: str,
    dataset_id: str,
    dataset_snapshot_id: str,
    dataset_checksum_sha256: str,
    dataset_medication_vocabulary_sha256: str,
    dataset_manifest_sha256: str,
    evaluation_visit_membership_digest: str,
    seed: int,
    selection_split: SplitName,
    evaluation_split: SplitName,
    adaptation_budget_sha256: str,
    parameters: tuple[RunParameter, ...],
    evaluation: EvaluationResult,
    artifact_checksums: tuple[ArtifactChecksum, ...],
) -> dict[str, object]:
    configuration = _configuration_dict(
        seed,
        selection_split,
        evaluation_split,
        adaptation_budget_sha256,
        parameters,
    )
    return {
        "artifacts": [artifact.to_dict() for artifact in artifact_checksums],
        "baseline": {
            "adapter_revision": adapter_revision,
            "baseline_definition_sha256": baseline_definition_sha256,
            "baseline_id": baseline_id,
            "environment_sha256": environment_sha256,
            "readiness": baseline_readiness.value,
            "source": baseline_source.to_dict(),
        },
        "configuration": configuration,
        "configuration_sha256": content_sha256(configuration),
        "dataset": {
            "checksum_sha256": dataset_checksum_sha256,
            "dataset_id": dataset_id,
            "evaluation_visit_membership_digest": evaluation_visit_membership_digest,
            "manifest_sha256": dataset_manifest_sha256,
            "medication_vocabulary_sha256": dataset_medication_vocabulary_sha256,
            "snapshot_id": dataset_snapshot_id,
        },
        "evaluation": evaluation.to_dict(),
        "mode": ResearchMode.COMPARISON.value,
        "protocol_version": protocol_version,
        "schema_version": RunRecord.SCHEMA_VERSION,
    }


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Content-addressed aggregate evidence accepted under Comparison Mode."""

    SCHEMA_VERSION: ClassVar[int] = 2

    run_id: str
    mode: ResearchMode | str
    protocol_version: str
    baseline_id: str
    baseline_source: SourceIdentity
    baseline_readiness: BaselineReadiness | str
    baseline_definition_sha256: str
    adapter_revision: str
    environment_sha256: str
    dataset_id: str
    dataset_snapshot_id: str
    dataset_checksum_sha256: str
    dataset_medication_vocabulary_sha256: str
    dataset_manifest_sha256: str
    evaluation_visit_membership_digest: str
    seed: int
    selection_split: SplitName | str
    evaluation_split: SplitName | str
    adaptation_budget_sha256: str
    parameters: tuple[RunParameter, ...]
    evaluation: EvaluationResult
    artifact_checksums: tuple[ArtifactChecksum, ...]

    def __post_init__(self) -> None:
        mode = enum_member(ResearchMode, self.mode, field="mode")
        if mode is not ResearchMode.COMPARISON:
            raise ProtocolValidationError("RunRecord accepts Comparison Mode evidence only")
        object.__setattr__(self, "mode", mode)
        require_public_string(self.protocol_version, field="protocol_version")
        require_identifier(self.baseline_id, field="baseline_id")
        if not isinstance(self.baseline_source, SourceIdentity):
            raise ProtocolValidationError("baseline_source must be a SourceIdentity")
        if self.baseline_source.status is not SourceStatus.PINNED:
            raise ProtocolValidationError("RunRecord baseline source must be pinned")
        readiness = enum_member(
            BaselineReadiness,
            self.baseline_readiness,
            field="baseline_readiness",
        )
        if readiness is not BaselineReadiness.COMPARISON_READY:
            raise ProtocolValidationError("RunRecord baseline must be comparison-ready")
        object.__setattr__(self, "baseline_readiness", readiness)
        require_sha256(self.baseline_definition_sha256, field="baseline_definition_sha256")
        require_public_string(self.adapter_revision, field="adapter_revision")
        require_sha256(self.environment_sha256, field="environment_sha256")
        require_identifier(self.dataset_id, field="dataset_id")
        require_public_string(self.dataset_snapshot_id, field="dataset_snapshot_id")
        for field in (
            "dataset_checksum_sha256",
            "dataset_medication_vocabulary_sha256",
            "dataset_manifest_sha256",
            "evaluation_visit_membership_digest",
            "adaptation_budget_sha256",
        ):
            require_sha256(getattr(self, field), field=field)
        require_int(self.seed, field="seed")
        selection_split = enum_member(SplitName, self.selection_split, field="selection_split")
        evaluation_split = enum_member(SplitName, self.evaluation_split, field="evaluation_split")
        if selection_split is not SplitName.VALIDATION:
            raise ProtocolValidationError("selection_split must be validation")
        if evaluation_split is not SplitName.TEST:
            raise ProtocolValidationError("evaluation_split must be test")
        object.__setattr__(self, "selection_split", selection_split)
        object.__setattr__(self, "evaluation_split", evaluation_split)
        parameters = tuple(
            parameter if isinstance(parameter, RunParameter) else RunParameter.from_dict(parameter)
            for parameter in self.parameters
        )
        parameters = tuple(sorted(parameters, key=lambda parameter: parameter.name))
        if len(parameters) != len({parameter.name for parameter in parameters}):
            raise ProtocolValidationError("RunParameter names must be unique")
        object.__setattr__(self, "parameters", parameters)
        if not isinstance(self.evaluation, EvaluationResult):
            raise ProtocolValidationError("evaluation must be an EvaluationResult")
        artifacts = tuple(
            artifact
            if isinstance(artifact, ArtifactChecksum)
            else ArtifactChecksum.from_dict(artifact)
            for artifact in self.artifact_checksums
        )
        artifacts = tuple(sorted(artifacts, key=lambda artifact: artifact.name))
        if not artifacts:
            raise ProtocolValidationError("RunRecord requires artifact checksums")
        if len(artifacts) != len({artifact.name for artifact in artifacts}):
            raise ProtocolValidationError("artifact names must be unique")
        object.__setattr__(self, "artifact_checksums", artifacts)
        expected_run_id = self._expected_run_id()
        if self.run_id != expected_run_id:
            raise ProtocolValidationError(
                f"run_id does not match record content; expected {expected_run_id}"
            )

    def _payload(self) -> dict[str, object]:
        return _record_payload(
            protocol_version=self.protocol_version,
            baseline_id=self.baseline_id,
            baseline_source=self.baseline_source,
            baseline_readiness=self.baseline_readiness,
            baseline_definition_sha256=self.baseline_definition_sha256,
            adapter_revision=self.adapter_revision,
            environment_sha256=self.environment_sha256,
            dataset_id=self.dataset_id,
            dataset_snapshot_id=self.dataset_snapshot_id,
            dataset_checksum_sha256=self.dataset_checksum_sha256,
            dataset_medication_vocabulary_sha256=self.dataset_medication_vocabulary_sha256,
            dataset_manifest_sha256=self.dataset_manifest_sha256,
            evaluation_visit_membership_digest=self.evaluation_visit_membership_digest,
            seed=self.seed,
            selection_split=self.selection_split,
            evaluation_split=self.evaluation_split,
            adaptation_budget_sha256=self.adaptation_budget_sha256,
            parameters=self.parameters,
            evaluation=self.evaluation,
            artifact_checksums=self.artifact_checksums,
        )

    def _expected_run_id(self) -> str:
        return f"run-{content_sha256(self._payload())[:20]}"

    @property
    def configuration_sha256(self) -> str:
        return content_sha256(
            _configuration_dict(
                self.seed,
                self.selection_split,
                self.evaluation_split,
                self.adaptation_budget_sha256,
                self.parameters,
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {"run_id": self.run_id, **self._payload()}

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    def write(self, path: str | Path) -> None:
        Path(path).write_text(f"{self.to_json(indent=2)}\n", encoding="utf-8")

    def _validate_authorities(
        self,
        *,
        baseline: BaselineDefinition,
        dataset: DatasetManifest,
    ) -> None:
        if not baseline.qualifies_for(
            protocol_version=self.protocol_version,
            dataset_manifest_sha256=dataset.manifest_sha256,
            adaptation_budget_sha256=self.adaptation_budget_sha256,
        ) or (
            self.baseline_id != baseline.baseline_id
            or self.baseline_source != baseline.source
            or self.baseline_readiness is not baseline.readiness
            or self.baseline_definition_sha256 != baseline.definition_sha256
            or self.adapter_revision != baseline.adapter_revision
            or self.environment_sha256 != baseline.environment_sha256
        ):
            raise ProtocolValidationError(
                "RunRecord does not match the authoritative baseline definition"
            )
        test_split = dataset.split(SplitName.TEST)
        if (
            self.dataset_id != dataset.dataset_id
            or self.dataset_snapshot_id != dataset.snapshot_id
            or self.dataset_checksum_sha256 != dataset.checksum_sha256
            or self.dataset_medication_vocabulary_sha256 != dataset.medication_vocabulary_sha256
            or self.dataset_manifest_sha256 != dataset.manifest_sha256
            or self.evaluation_visit_membership_digest != test_split.visit_membership_digest
            or self.evaluation.visit_count != test_split.visit_count
        ):
            raise ProtocolValidationError(
                "RunRecord does not match the authoritative Dataset Manifest"
            )

    @classmethod
    def create(
        cls,
        *,
        mode: ResearchMode | str,
        protocol_version: str,
        baseline: BaselineDefinition,
        dataset: DatasetManifest,
        seed: int,
        selection_split: SplitName | str,
        evaluation_split: SplitName | str,
        parameters: Iterable[RunParameter],
        evaluation: EvaluationResult,
        adaptation_budget_sha256: str,
        artifact_checksums: Iterable[ArtifactChecksum],
        evaluation_visit_membership_digest: str,
    ) -> RunRecord:
        research_mode = enum_member(ResearchMode, mode, field="mode")
        if research_mode is not ResearchMode.COMPARISON:
            raise ProtocolValidationError("RunRecord accepts Comparison Mode evidence only")
        require_sha256(adaptation_budget_sha256, field="adaptation_budget_sha256")
        if research_mode not in baseline.supported_modes or not baseline.qualifies_for(
            protocol_version=protocol_version,
            dataset_manifest_sha256=dataset.manifest_sha256,
            adaptation_budget_sha256=adaptation_budget_sha256,
        ):
            raise ProtocolValidationError(
                "comparison run requires a matching Comparison Qualification"
            )
        selected = enum_member(SplitName, selection_split, field="selection_split")
        evaluated = enum_member(SplitName, evaluation_split, field="evaluation_split")
        if evaluation.visit_count != dataset.split(evaluated).visit_count:
            raise ProtocolValidationError(
                "evaluation visit_count must match the Dataset Manifest test split"
            )
        require_sha256(
            evaluation_visit_membership_digest,
            field="evaluation_visit_membership_digest",
        )
        if evaluation_visit_membership_digest != dataset.split(evaluated).visit_membership_digest:
            raise ProtocolValidationError(
                "evaluation must match the Dataset Manifest eligible test-visit digest"
            )
        normalized_parameters = tuple(
            sorted(
                (
                    parameter
                    if isinstance(parameter, RunParameter)
                    else RunParameter.from_dict(parameter)
                    for parameter in parameters
                ),
                key=lambda parameter: parameter.name,
            )
        )
        normalized_artifacts = tuple(
            sorted(
                (
                    artifact
                    if isinstance(artifact, ArtifactChecksum)
                    else ArtifactChecksum.from_dict(artifact)
                    for artifact in artifact_checksums
                ),
                key=lambda artifact: artifact.name,
            )
        )
        adapter_revision = baseline.adapter_revision
        environment_sha256 = baseline.environment_sha256
        if adapter_revision is None or environment_sha256 is None:
            raise ProtocolValidationError("comparison-ready baseline identity is incomplete")
        payload = _record_payload(
            protocol_version=protocol_version,
            baseline_id=baseline.baseline_id,
            baseline_source=baseline.source,
            baseline_readiness=baseline.readiness,
            baseline_definition_sha256=baseline.definition_sha256,
            adapter_revision=adapter_revision,
            environment_sha256=environment_sha256,
            dataset_id=dataset.dataset_id,
            dataset_snapshot_id=dataset.snapshot_id,
            dataset_checksum_sha256=dataset.checksum_sha256,
            dataset_medication_vocabulary_sha256=dataset.medication_vocabulary_sha256,
            dataset_manifest_sha256=dataset.manifest_sha256,
            evaluation_visit_membership_digest=evaluation_visit_membership_digest,
            seed=seed,
            selection_split=selected,
            evaluation_split=evaluated,
            adaptation_budget_sha256=adaptation_budget_sha256,
            parameters=normalized_parameters,
            evaluation=evaluation,
            artifact_checksums=normalized_artifacts,
        )
        record = cls(
            run_id=f"run-{content_sha256(payload)[:20]}",
            mode=research_mode,
            protocol_version=protocol_version,
            baseline_id=baseline.baseline_id,
            baseline_source=baseline.source,
            baseline_readiness=baseline.readiness,
            baseline_definition_sha256=baseline.definition_sha256,
            adapter_revision=adapter_revision,
            environment_sha256=environment_sha256,
            dataset_id=dataset.dataset_id,
            dataset_snapshot_id=dataset.snapshot_id,
            dataset_checksum_sha256=dataset.checksum_sha256,
            dataset_medication_vocabulary_sha256=dataset.medication_vocabulary_sha256,
            dataset_manifest_sha256=dataset.manifest_sha256,
            evaluation_visit_membership_digest=evaluation_visit_membership_digest,
            seed=seed,
            selection_split=selected,
            evaluation_split=evaluated,
            adaptation_budget_sha256=adaptation_budget_sha256,
            parameters=normalized_parameters,
            evaluation=evaluation,
            artifact_checksums=normalized_artifacts,
        )
        record._validate_authorities(baseline=baseline, dataset=dataset)
        return record

    @classmethod
    def from_dict(
        cls,
        value: object,
        *,
        baseline: BaselineDefinition,
        dataset: DatasetManifest,
    ) -> RunRecord:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "run_id",
                "mode",
                "protocol_version",
                "baseline",
                "dataset",
                "configuration",
                "configuration_sha256",
                "evaluation",
                "artifacts",
            ),
            context="RunRecord",
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ProtocolValidationError(f"RunRecord schema_version must be {cls.SCHEMA_VERSION}")
        baseline_payload = strict_fields(
            payload["baseline"],
            required=(
                "baseline_id",
                "source",
                "readiness",
                "baseline_definition_sha256",
                "adapter_revision",
                "environment_sha256",
            ),
            context="RunRecord.baseline",
        )
        dataset_payload = strict_fields(
            payload["dataset"],
            required=(
                "dataset_id",
                "snapshot_id",
                "checksum_sha256",
                "medication_vocabulary_sha256",
                "manifest_sha256",
                "evaluation_visit_membership_digest",
            ),
            context="RunRecord.dataset",
        )
        configuration = strict_fields(
            payload["configuration"],
            required=(
                "seed",
                "selection_split",
                "evaluation_split",
                "adaptation_budget_sha256",
                "parameters",
            ),
            context="RunRecord.configuration",
        )
        if content_sha256(configuration) != payload["configuration_sha256"]:
            raise ProtocolValidationError("RunRecord configuration_sha256 does not match")
        parameters = configuration["parameters"]
        artifacts = payload["artifacts"]
        if not isinstance(parameters, list):
            raise ProtocolValidationError("RunRecord parameters must be a list")
        if not isinstance(artifacts, list):
            raise ProtocolValidationError("RunRecord artifacts must be a list")
        record = cls(
            run_id=payload["run_id"],
            mode=payload["mode"],
            protocol_version=payload["protocol_version"],
            baseline_id=baseline_payload["baseline_id"],
            baseline_source=SourceIdentity.from_dict(baseline_payload["source"]),
            baseline_readiness=baseline_payload["readiness"],
            baseline_definition_sha256=baseline_payload["baseline_definition_sha256"],
            adapter_revision=baseline_payload["adapter_revision"],
            environment_sha256=baseline_payload["environment_sha256"],
            dataset_id=dataset_payload["dataset_id"],
            dataset_snapshot_id=dataset_payload["snapshot_id"],
            dataset_checksum_sha256=dataset_payload["checksum_sha256"],
            dataset_medication_vocabulary_sha256=dataset_payload["medication_vocabulary_sha256"],
            dataset_manifest_sha256=dataset_payload["manifest_sha256"],
            evaluation_visit_membership_digest=dataset_payload[
                "evaluation_visit_membership_digest"
            ],
            seed=configuration["seed"],
            selection_split=configuration["selection_split"],
            evaluation_split=configuration["evaluation_split"],
            adaptation_budget_sha256=configuration["adaptation_budget_sha256"],
            parameters=tuple(RunParameter.from_dict(item) for item in parameters),
            evaluation=EvaluationResult.from_dict(payload["evaluation"]),
            artifact_checksums=tuple(ArtifactChecksum.from_dict(item) for item in artifacts),
        )
        record._validate_authorities(baseline=baseline, dataset=dataset)
        return record

    @classmethod
    def from_json(
        cls,
        text: str,
        *,
        baseline: BaselineDefinition,
        dataset: DatasetManifest,
    ) -> RunRecord:
        return cls.from_dict(
            parse_json_object(text, context="RunRecord"),
            baseline=baseline,
            dataset=dataset,
        )

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        baseline: BaselineDefinition,
        dataset: DatasetManifest,
    ) -> RunRecord:
        return cls.from_json(
            Path(path).read_text(encoding="utf-8"),
            baseline=baseline,
            dataset=dataset,
        )


__all__ = ("ArtifactChecksum", "RunParameter", "RunParameterValue", "RunRecord")
