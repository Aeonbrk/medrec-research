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
    protocol_amendment_sha256: str | None = None
    method_profile_sha256: str | None = None

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
        for field in ("protocol_amendment_sha256", "method_profile_sha256"):
            value = getattr(self, field)
            if value is not None:
                require_sha256(value, field=f"scope.{field}")

    @property
    def scope_sha256(self) -> str:
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
        return (
            self.protocol_version == protocol_version
            and self.dataset_manifest_sha256 == dataset_manifest_sha256
            and self.adaptation_budget_sha256 == adaptation_budget_sha256
            and self.protocol_amendment_sha256 == protocol_amendment_sha256
            and self.method_profile_sha256 == method_profile_sha256
        )

    @property
    def amendment_sha256(self) -> str | None:
        return self.protocol_amendment_sha256

    @property
    def profile_sha256(self) -> str | None:
        return self.method_profile_sha256

    def to_dict(self) -> dict[str, str]:
        payload: dict[str, str] = {
            "adaptation_budget_sha256": self.adaptation_budget_sha256,
            "dataset_manifest_sha256": self.dataset_manifest_sha256,
            "protocol_version": self.protocol_version,
        }
        if self.protocol_amendment_sha256 is not None:
            payload["protocol_amendment_sha256"] = self.protocol_amendment_sha256
        if self.method_profile_sha256 is not None:
            payload["method_profile_sha256"] = self.method_profile_sha256
        return payload

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
                optional=("method_profile_sha256", "protocol_amendment_sha256"),
                context="ComparisonScope",
            )
        )


__all__ = ("ComparisonScope",)
