"""Immutable MoleRec artifact bundles and stage evidence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    parse_json_object,
    require_identifier,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
)
from .comparison_protocol import (
    MOLEREC_REPOSITORY,
    MOLEREC_REVISION,
    MOLEREC_SAFEDRUG_LINEAGE_REVISION,
)
from .errors import ProtocolValidationError


class Stage(StrEnum):
    """The three separately attributable MoleRec evidence stages."""

    CHECKPOINT_REPLAY = "checkpoint_replay"
    TRAINING_REPRODUCTION = "training_reproduction"
    COMPARISON_QUALIFICATION = "comparison_qualification"

    REPLAY = "checkpoint_replay"
    TRAINING = "training_reproduction"
    COMPARISON = "comparison_qualification"


@dataclass(frozen=True, slots=True)
class MoleRecArtifactBundle:
    """One exact MoleRec checkpoint/preprocessing artifact identity."""

    variant: str
    checkpoint_sha256: str
    vocabulary_order_sha256: str
    preprocessing_artifact_sha256: str
    ddi_artifact_sha256: str
    brics_artifact_sha256: str
    source_repository: str = MOLEREC_REPOSITORY
    source_revision: str = MOLEREC_REVISION
    preprocessing_lineage_revision: str = MOLEREC_SAFEDRUG_LINEAGE_REVISION
    bundle_sha256: str = ""
    display_name: str | None = None
    notes: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.variant, field="molerec.variant")
        for field in (
            "checkpoint_sha256",
            "vocabulary_order_sha256",
            "preprocessing_artifact_sha256",
            "ddi_artifact_sha256",
            "brics_artifact_sha256",
        ):
            require_sha256(getattr(self, field), field=f"molerec.{field}")
        if self.source_repository != MOLEREC_REPOSITORY:
            raise ProtocolValidationError("MoleRec bundle source repository is not pinned")
        if self.source_revision != MOLEREC_REVISION:
            raise ProtocolValidationError("MoleRec bundle source revision is not pinned")
        if self.preprocessing_lineage_revision != MOLEREC_SAFEDRUG_LINEAGE_REVISION:
            raise ProtocolValidationError(
                "MoleRec bundle must record SafeDrug c7218d0 preprocessing lineage"
            )
        require_single_line_public_string(self.source_repository, field="molerec.source_repository")
        require_identifier(self.source_revision, field="molerec.source_revision")
        require_identifier(
            self.preprocessing_lineage_revision,
            field="molerec.preprocessing_lineage_revision",
        )
        if self.display_name is not None:
            require_single_line_public_string(self.display_name, field="molerec.display_name")
        if self.notes:
            require_single_line_public_string(self.notes, field="molerec.notes")
        expected = content_sha256(self._protected_payload())
        if self.bundle_sha256:
            require_sha256(self.bundle_sha256, field="molerec.bundle_sha256")
            if self.bundle_sha256 != expected:
                raise ProtocolValidationError(
                    "MoleRec bundle_sha256 does not match artifact identity"
                )
        else:
            object.__setattr__(self, "bundle_sha256", expected)

    @property
    def vocabulary_sha256(self) -> str:
        return self.vocabulary_order_sha256

    @property
    def preprocessing_sha256(self) -> str:
        return self.preprocessing_artifact_sha256

    @property
    def ddi_sha256(self) -> str:
        return self.ddi_artifact_sha256

    @property
    def brics_sha256(self) -> str:
        return self.brics_artifact_sha256

    def _protected_payload(self) -> dict[str, object]:
        return {
            "brics_artifact_sha256": self.brics_artifact_sha256,
            "checkpoint_sha256": self.checkpoint_sha256,
            "ddi_artifact_sha256": self.ddi_artifact_sha256,
            "preprocessing_artifact_sha256": self.preprocessing_artifact_sha256,
            "preprocessing_lineage_revision": self.preprocessing_lineage_revision,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "variant": self.variant,
            "vocabulary_order_sha256": self.vocabulary_order_sha256,
        }

    def is_current(self) -> bool:
        return self.bundle_sha256 == content_sha256(self._protected_payload())

    def to_dict(self) -> dict[str, object]:
        return {
            **self._protected_payload(),
            "bundle_sha256": self.bundle_sha256,
            "display_name": self.display_name,
            "kind": "molerec_artifact_bundle",
            "notes": self.notes,
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def create(cls, **kwargs: object) -> MoleRecArtifactBundle:
        aliases = {
            "vocabulary_sha256": "vocabulary_order_sha256",
            "preprocessing_sha256": "preprocessing_artifact_sha256",
            "ddi_sha256": "ddi_artifact_sha256",
            "brics_sha256": "brics_artifact_sha256",
            "checkpoint_digest": "checkpoint_sha256",
        }
        normalized = dict(kwargs)
        for alias, target in aliases.items():
            if alias in normalized and target not in normalized:
                normalized[target] = normalized.pop(alias)
        return cls(**normalized)

    @classmethod
    def from_dict(cls, value: object) -> MoleRecArtifactBundle:
        payload = strict_fields(
            value,
            required=(
                "brics_artifact_sha256",
                "bundle_sha256",
                "checkpoint_sha256",
                "ddi_artifact_sha256",
                "display_name",
                "kind",
                "notes",
                "preprocessing_artifact_sha256",
                "preprocessing_lineage_revision",
                "schema_version",
                "source_repository",
                "source_revision",
                "variant",
                "vocabulary_order_sha256",
            ),
            context="MoleRecArtifactBundle",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "molerec_artifact_bundle"
        ):
            raise ProtocolValidationError("MoleRecArtifactBundle schema or kind is invalid")
        return cls(**payload)

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> MoleRecArtifactBundle:
        return cls.from_dict(parse_json_object(text, context="MoleRecArtifactBundle"))


def require_bundle_for_stage(
    stage: Stage | str,
    *,
    bundle: MoleRecArtifactBundle,
    bundle_sha256: str,
) -> None:
    """Validate exact bundle identity before opening any MoleRec stage."""

    if not isinstance(bundle, MoleRecArtifactBundle) or not bundle.is_current():
        raise ProtocolValidationError("MoleRec stage requires a current artifact bundle")
    if bundle.bundle_sha256 != bundle_sha256:
        raise ProtocolValidationError("MoleRec stage artifact bundle digest does not match")
    if not isinstance(stage, Stage):
        try:
            stage = Stage(stage)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError("MoleRec stage is invalid") from error
    if stage not in {
        Stage.CHECKPOINT_REPLAY,
        Stage.TRAINING_REPRODUCTION,
        Stage.COMPARISON_QUALIFICATION,
    }:
        raise ProtocolValidationError("MoleRec stage is invalid")


__all__ = ("MoleRecArtifactBundle", "require_bundle_for_stage")
