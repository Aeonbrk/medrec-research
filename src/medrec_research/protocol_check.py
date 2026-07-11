"""Public-safe synthetic harness checks that are not research evidence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    parse_json_object,
    require_identifier,
    require_public_string,
    require_sha256,
    strict_fields,
)
from .dataset import DatasetManifest
from .errors import ProtocolValidationError
from .evaluation import EvaluationResult
from .run_record import ArtifactChecksum, RunParameter


def _payload(
    *,
    protocol_version: str,
    dataset_id: str,
    dataset_snapshot_id: str,
    dataset_manifest_sha256: str,
    dataset_checksum_sha256: str,
    medication_vocabulary_sha256: str,
    parameters: tuple[RunParameter, ...],
    evaluation: EvaluationResult,
    artifact_checksums: tuple[ArtifactChecksum, ...],
    checks: tuple[str, ...],
) -> dict[str, object]:
    return {
        "artifacts": [artifact.to_dict() for artifact in artifact_checksums],
        "checks": list(checks),
        "dataset": {
            "checksum_sha256": dataset_checksum_sha256,
            "dataset_id": dataset_id,
            "manifest_sha256": dataset_manifest_sha256,
            "medication_vocabulary_sha256": medication_vocabulary_sha256,
            "snapshot_id": dataset_snapshot_id,
        },
        "evaluation": evaluation.to_dict(),
        "kind": "protocol_check",
        "parameters": [parameter.to_dict() for parameter in parameters],
        "protocol_version": protocol_version,
        "schema_version": ProtocolCheckRecord.SCHEMA_VERSION,
    }


@dataclass(frozen=True, slots=True)
class ProtocolCheckRecord:
    """Content-addressed result from a public synthetic protocol check."""

    SCHEMA_VERSION: ClassVar[int] = 1

    check_id: str
    protocol_version: str
    dataset_id: str
    dataset_snapshot_id: str
    dataset_manifest_sha256: str
    dataset_checksum_sha256: str
    medication_vocabulary_sha256: str
    parameters: tuple[RunParameter, ...]
    evaluation: EvaluationResult
    artifact_checksums: tuple[ArtifactChecksum, ...]
    checks: tuple[str, ...]

    def __post_init__(self) -> None:
        require_public_string(self.protocol_version, field="protocol_version")
        require_identifier(self.dataset_id, field="dataset_id")
        require_public_string(self.dataset_snapshot_id, field="dataset_snapshot_id")
        for field in (
            "dataset_manifest_sha256",
            "dataset_checksum_sha256",
            "medication_vocabulary_sha256",
        ):
            require_sha256(getattr(self, field), field=field)
        parameters = tuple(
            parameter if isinstance(parameter, RunParameter) else RunParameter.from_dict(parameter)
            for parameter in self.parameters
        )
        parameters = tuple(sorted(parameters, key=lambda parameter: parameter.name))
        if len(parameters) != len({parameter.name for parameter in parameters}):
            raise ProtocolValidationError("ProtocolCheckRecord parameter names must be unique")
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
        if not artifacts or len(artifacts) != len({artifact.name for artifact in artifacts}):
            raise ProtocolValidationError("ProtocolCheckRecord requires unique artifact checksums")
        object.__setattr__(self, "artifact_checksums", artifacts)
        checks = tuple(sorted(require_identifier(check, field="check") for check in self.checks))
        if not checks or len(checks) != len(set(checks)):
            raise ProtocolValidationError("ProtocolCheckRecord requires unique checks")
        object.__setattr__(self, "checks", checks)
        expected = f"check-{content_sha256(self._payload())[:20]}"
        if self.check_id != expected:
            raise ProtocolValidationError(
                f"check_id does not match record content; expected {expected}"
            )

    def _payload(self) -> dict[str, object]:
        return _payload(
            protocol_version=self.protocol_version,
            dataset_id=self.dataset_id,
            dataset_snapshot_id=self.dataset_snapshot_id,
            dataset_manifest_sha256=self.dataset_manifest_sha256,
            dataset_checksum_sha256=self.dataset_checksum_sha256,
            medication_vocabulary_sha256=self.medication_vocabulary_sha256,
            parameters=self.parameters,
            evaluation=self.evaluation,
            artifact_checksums=self.artifact_checksums,
            checks=self.checks,
        )

    def to_dict(self) -> dict[str, object]:
        return {"check_id": self.check_id, **self._payload()}

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    def write(self, path: str | Path) -> None:
        Path(path).write_text(f"{self.to_json(indent=2)}\n", encoding="utf-8")

    @classmethod
    def create(
        cls,
        *,
        protocol_version: str,
        dataset: DatasetManifest,
        parameters: Iterable[RunParameter],
        evaluation: EvaluationResult,
        artifact_checksums: Iterable[ArtifactChecksum],
        checks: Iterable[str],
    ) -> ProtocolCheckRecord:
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
        normalized_checks = tuple(sorted(tuple(checks)))
        payload = _payload(
            protocol_version=protocol_version,
            dataset_id=dataset.dataset_id,
            dataset_snapshot_id=dataset.snapshot_id,
            dataset_manifest_sha256=dataset.manifest_sha256,
            dataset_checksum_sha256=dataset.checksum_sha256,
            medication_vocabulary_sha256=dataset.medication_vocabulary_sha256,
            parameters=normalized_parameters,
            evaluation=evaluation,
            artifact_checksums=normalized_artifacts,
            checks=normalized_checks,
        )
        return cls(
            check_id=f"check-{content_sha256(payload)[:20]}",
            protocol_version=protocol_version,
            dataset_id=dataset.dataset_id,
            dataset_snapshot_id=dataset.snapshot_id,
            dataset_manifest_sha256=dataset.manifest_sha256,
            dataset_checksum_sha256=dataset.checksum_sha256,
            medication_vocabulary_sha256=dataset.medication_vocabulary_sha256,
            parameters=normalized_parameters,
            evaluation=evaluation,
            artifact_checksums=normalized_artifacts,
            checks=normalized_checks,
        )

    @classmethod
    def from_dict(cls, value: object) -> ProtocolCheckRecord:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "kind",
                "check_id",
                "protocol_version",
                "dataset",
                "parameters",
                "evaluation",
                "artifacts",
                "checks",
            ),
            context="ProtocolCheckRecord",
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ProtocolValidationError(
                f"ProtocolCheckRecord schema_version must be {cls.SCHEMA_VERSION}"
            )
        if payload["kind"] != "protocol_check":
            raise ProtocolValidationError("ProtocolCheckRecord kind must be protocol_check")
        dataset = strict_fields(
            payload["dataset"],
            required=(
                "dataset_id",
                "snapshot_id",
                "manifest_sha256",
                "checksum_sha256",
                "medication_vocabulary_sha256",
            ),
            context="ProtocolCheckRecord.dataset",
        )
        parameters = payload["parameters"]
        artifacts = payload["artifacts"]
        checks = payload["checks"]
        if not isinstance(parameters, list):
            raise ProtocolValidationError("ProtocolCheckRecord parameters must be a list")
        if not isinstance(artifacts, list):
            raise ProtocolValidationError("ProtocolCheckRecord artifacts must be a list")
        if not isinstance(checks, list):
            raise ProtocolValidationError("ProtocolCheckRecord checks must be a list")
        return cls(
            check_id=payload["check_id"],
            protocol_version=payload["protocol_version"],
            dataset_id=dataset["dataset_id"],
            dataset_snapshot_id=dataset["snapshot_id"],
            dataset_manifest_sha256=dataset["manifest_sha256"],
            dataset_checksum_sha256=dataset["checksum_sha256"],
            medication_vocabulary_sha256=dataset["medication_vocabulary_sha256"],
            parameters=tuple(RunParameter.from_dict(item) for item in parameters),
            evaluation=EvaluationResult.from_dict(payload["evaluation"]),
            artifact_checksums=tuple(ArtifactChecksum.from_dict(item) for item in artifacts),
            checks=tuple(checks),
        )

    @classmethod
    def from_json(cls, text: str) -> ProtocolCheckRecord:
        return cls.from_dict(parse_json_object(text, context="ProtocolCheckRecord"))


__all__ = ("ProtocolCheckRecord",)
