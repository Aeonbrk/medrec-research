"""Protocol-owned identity for comparable research evidence."""

from __future__ import annotations

from dataclasses import dataclass

from ._validation import (
    content_sha256,
    require_public_string,
    require_sha256,
    strict_fields,
)


@dataclass(frozen=True, slots=True)
class ComparisonScope:
    """Immutable protocol, Dataset Manifest, and Adaptation Budget identity."""

    protocol_version: str
    dataset_manifest_sha256: str
    adaptation_budget_sha256: str

    def __post_init__(self) -> None:
        require_public_string(self.protocol_version, field="scope.protocol_version")
        require_sha256(
            self.dataset_manifest_sha256,
            field="scope.dataset_manifest_sha256",
        )
        require_sha256(
            self.adaptation_budget_sha256,
            field="scope.adaptation_budget_sha256",
        )

    @property
    def scope_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def matches(
        self,
        *,
        protocol_version: str,
        dataset_manifest_sha256: str,
        adaptation_budget_sha256: str,
    ) -> bool:
        return (
            self.protocol_version == protocol_version
            and self.dataset_manifest_sha256 == dataset_manifest_sha256
            and self.adaptation_budget_sha256 == adaptation_budget_sha256
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "adaptation_budget_sha256": self.adaptation_budget_sha256,
            "dataset_manifest_sha256": self.dataset_manifest_sha256,
            "protocol_version": self.protocol_version,
        }

    @classmethod
    def from_dict(cls, value: object) -> ComparisonScope:
        return cls(
            **strict_fields(
                value,
                required=(
                    "protocol_version",
                    "dataset_manifest_sha256",
                    "adaptation_budget_sha256",
                ),
                context="ComparisonScope",
            )
        )


__all__ = ("ComparisonScope",)
