"""Reproduction Mode stability evidence contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    parse_json_object,
    require_identifier,
    require_int,
    require_sha256,
    strict_fields,
)
from .errors import ProtocolValidationError
from .registry import BaselineDefinition, BaselineReadiness, ReadinessGate, SourceStatus

_IDENTITY_FIELDS = (
    "source_sha256",
    "environment_sha256",
    "adapter_sha256",
    "adapter_smoke_sha256",
    "input_manifest_sha256",
    "seed_policy_sha256",
)
_CONTROLLED_GAMENET_BASELINE_ID = "gamenet"
_CONTROLLED_GAMENET_DATASET_ID = "mimic-iii-v1.4"
_CONTROLLED_GAMENET_FULL_SEEDS = (7, 19, 31)
_CONTROLLED_GAMENET_SOURCE_REVISION = "da695b4fc9390882f3a681c82115e81291ae6380"


def _objects(value: object, *, field: str) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ProtocolValidationError(f"{field} must be a list of objects")
    return tuple(value)


def _optional_sha256(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    return require_sha256(value, field=field)


def _optional_nonnegative_int(value: object, *, field: str) -> int | None:
    if value is None:
        return None
    return require_int(value, field=field)


def _optional_nonnegative_number(value: object, *, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a finite non-negative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ProtocolValidationError(f"{field} must be a finite non-negative number")
    return result


class AttemptOutcome(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class StabilityStatus(StrEnum):
    UNRESOLVED = "unresolved"
    FAILED = "failed"
    STABLE = "stable"


@dataclass(frozen=True, slots=True)
class ReproductionAttempt:
    attempt_id: str
    outcome: AttemptOutcome | str
    source_sha256: str | None
    environment_sha256: str | None
    adapter_sha256: str | None
    adapter_smoke_sha256: str | None
    input_manifest_sha256: str | None
    seed_policy_sha256: str | None
    artifact_sha256: str | None
    seed: int | None = None
    source_revision: str | None = None
    dataset_id: str | None = None

    def __post_init__(self) -> None:
        require_identifier(self.attempt_id, field="attempt.attempt_id")
        try:
            outcome = AttemptOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError("attempt outcome must be completed or failed") from error
        object.__setattr__(self, "outcome", outcome)
        for field in (*_IDENTITY_FIELDS, "artifact_sha256"):
            object.__setattr__(
                self,
                field,
                _optional_sha256(getattr(self, field), field=f"attempt.{field}"),
            )
        object.__setattr__(self, "seed", _optional_nonnegative_int(self.seed, field="attempt.seed"))
        if self.source_revision is not None:
            object.__setattr__(
                self,
                "source_revision",
                require_identifier(self.source_revision, field="attempt.source_revision"),
            )
        if self.dataset_id is not None:
            object.__setattr__(
                self,
                "dataset_id",
                require_identifier(self.dataset_id, field="attempt.dataset_id"),
            )

    def to_dict(self, *, include_controlled_fields: bool = False) -> dict[str, object]:
        payload: dict[str, object] = {
            "adapter_sha256": self.adapter_sha256,
            "adapter_smoke_sha256": self.adapter_smoke_sha256,
            "artifact_sha256": self.artifact_sha256,
            "attempt_id": self.attempt_id,
            "environment_sha256": self.environment_sha256,
            "input_manifest_sha256": self.input_manifest_sha256,
            "outcome": self.outcome.value,
            "seed_policy_sha256": self.seed_policy_sha256,
            "source_sha256": self.source_sha256,
        }
        if include_controlled_fields:
            payload.update(
                {
                    "dataset_id": self.dataset_id,
                    "seed": self.seed,
                    "source_revision": self.source_revision,
                }
            )
        return payload

    @classmethod
    def from_dict(cls, value: object) -> ReproductionAttempt:
        payload = strict_fields(
            value,
            required=("attempt_id", "outcome"),
            optional=(
                *_IDENTITY_FIELDS,
                "artifact_sha256",
                "seed",
                "source_revision",
                "dataset_id",
            ),
            context="ReproductionAttempt",
        )
        for field in (*_IDENTITY_FIELDS, "artifact_sha256"):
            payload.setdefault(field, None)
        for field in ("seed", "source_revision", "dataset_id"):
            payload.setdefault(field, None)
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class VarianceCheck:
    check_id: str
    predeclared: bool | None
    tolerance: float | None
    observed_variance: float | None
    evidence_sha256: str | None

    def __post_init__(self) -> None:
        require_identifier(self.check_id, field="variance.check_id")
        if self.predeclared is not None and type(self.predeclared) is not bool:
            raise ProtocolValidationError("variance.predeclared must be boolean or null")
        object.__setattr__(
            self,
            "tolerance",
            _optional_nonnegative_number(self.tolerance, field="variance.tolerance"),
        )
        object.__setattr__(
            self,
            "observed_variance",
            _optional_nonnegative_number(
                self.observed_variance, field="variance.observed_variance"
            ),
        )
        object.__setattr__(
            self,
            "evidence_sha256",
            _optional_sha256(self.evidence_sha256, field="variance.evidence_sha256"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "evidence_sha256": self.evidence_sha256,
            "observed_variance": self.observed_variance,
            "predeclared": self.predeclared,
            "tolerance": self.tolerance,
        }

    @classmethod
    def from_dict(cls, value: object) -> VarianceCheck:
        payload = strict_fields(
            value,
            required=("check_id",),
            optional=("predeclared", "tolerance", "observed_variance", "evidence_sha256"),
            context="VarianceCheck",
        )
        for field in ("predeclared", "tolerance", "observed_variance", "evidence_sha256"):
            payload.setdefault(field, None)
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class ReproductionStabilityPolicy:
    version: int = 2
    minimum_completed_attempts: int | None = None
    maximum_failed_attempts: int = 0
    expected_output_ids: tuple[str, ...] | None = None
    expected_seeds: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        expected_attempts = 3 if self.version == 3 else 2
        if (
            self.minimum_completed_attempts not in {None, expected_attempts}
            or self.maximum_failed_attempts != 0
        ):
            raise ProtocolValidationError(
                "ReproductionStabilityPolicy attempt thresholds are fixed"
            )
        if self.expected_output_ids is None:
            provided_output_ids = None
        else:
            try:
                provided_output_ids = tuple(
                    require_identifier(item, field="policy.expected_output_ids")
                    for item in self.expected_output_ids
                )
            except TypeError as error:
                raise ProtocolValidationError(
                    "policy.expected_output_ids must be a collection"
                ) from error
        if self.expected_seeds is None:
            provided_seeds = None
        else:
            try:
                provided_seeds = tuple(
                    require_int(item, field="policy.expected_seeds") for item in self.expected_seeds
                )
            except TypeError as error:
                raise ProtocolValidationError(
                    "policy.expected_seeds must be a collection"
                ) from error
        if self.version == 1:
            expected_output_ids = ()
            if provided_output_ids not in {None, expected_output_ids} or provided_seeds is not None:
                raise ProtocolValidationError(
                    "ReproductionStabilityPolicy V1 has no controlled output or seed set"
                )
        elif self.version == 2:
            expected_output_ids = (
                "jaccard",
                "precision",
                "recall",
                "f1",
                "mean_medication_count",
            )
            if provided_output_ids not in {None, expected_output_ids} or provided_seeds is not None:
                raise ProtocolValidationError(
                    "ReproductionStabilityPolicy V2 must use canonical expected output IDs only"
                )
        elif self.version == 3:
            expected_output_ids = (
                "jaccard",
                "precision",
                "recall",
                "f1",
                "mean_medication_count",
            )
            expected_seeds = _CONTROLLED_GAMENET_FULL_SEEDS
            if provided_output_ids not in {None, expected_output_ids}:
                raise ProtocolValidationError(
                    "ReproductionStabilityPolicy V3 must use canonical expected output IDs"
                )
            if provided_seeds not in {None, expected_seeds}:
                raise ProtocolValidationError(
                    "ReproductionStabilityPolicy V3 must use controlled GAMENet seeds"
                )
        else:
            raise ProtocolValidationError("ReproductionStabilityPolicy version is unsupported")
        if self.version != 3:
            expected_seeds = ()
        object.__setattr__(self, "minimum_completed_attempts", expected_attempts)
        object.__setattr__(self, "expected_output_ids", expected_output_ids)
        object.__setattr__(self, "expected_seeds", expected_seeds)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "maximum_failed_attempts": self.maximum_failed_attempts,
            "minimum_completed_attempts": self.minimum_completed_attempts,
            "mode": "reproduction",
            "require_adapter_smoke_identity": True,
            "require_artifact_digest": True,
            "require_matching_attempt_identities": list(_IDENTITY_FIELDS),
            "require_predeclared_variance_check": True,
            "require_upstream_semantics": ["split", "selection", "evaluation"],
            "schema_version": 1,
            "version": self.version,
        }
        if self.version >= 2:
            payload["expected_output_ids"] = list(self.expected_output_ids)
        if self.version == 3:
            payload.update(
                {
                    "controlled_baseline_id": _CONTROLLED_GAMENET_BASELINE_ID,
                    "controlled_dataset_id": _CONTROLLED_GAMENET_DATASET_ID,
                    "controlled_source_revision": _CONTROLLED_GAMENET_SOURCE_REVISION,
                    "expected_seeds": list(self.expected_seeds),
                }
            )
        return payload

    @property
    def policy_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def evaluate(
        self,
        *,
        mode: str,
        selection_authority_sha256: str | None,
        planned_attempts: int | None,
        attempts: tuple[ReproductionAttempt, ...],
        protocol_violations: int | None,
        variance_checks: tuple[VarianceCheck, ...],
        upstream_fields: tuple[str | None, ...],
    ) -> StabilityStatus:
        if mode != "reproduction":
            return StabilityStatus.FAILED
        if planned_attempts is not None and planned_attempts != len(attempts):
            return StabilityStatus.FAILED
        if self.version == 3 and (
            planned_attempts not in {None, len(self.expected_seeds)}
            or len(attempts) != len(self.expected_seeds)
        ):
            return StabilityStatus.FAILED
        if any(item.outcome is AttemptOutcome.FAILED for item in attempts):
            return StabilityStatus.FAILED
        if protocol_violations is not None and protocol_violations > 0:
            return StabilityStatus.FAILED
        for field in _IDENTITY_FIELDS:
            observed = {getattr(attempt, field) for attempt in attempts if getattr(attempt, field)}
            if len(observed) > 1:
                return StabilityStatus.FAILED
        for check in variance_checks:
            if check.predeclared is False:
                return StabilityStatus.FAILED
            if (
                check.tolerance is not None
                and check.observed_variance is not None
                and check.observed_variance > check.tolerance
            ):
                return StabilityStatus.FAILED
        if self.version >= 2 and not set(self.expected_output_ids) <= {
            check.check_id for check in variance_checks
        }:
            return StabilityStatus.UNRESOLVED
        if (
            self.version == 3
            and all(
                attempt.seed is not None
                and attempt.source_revision is not None
                and attempt.dataset_id is not None
                for attempt in attempts
            )
            and (
                {attempt.seed for attempt in attempts} != set(self.expected_seeds)
                or any(
                    attempt.source_revision != _CONTROLLED_GAMENET_SOURCE_REVISION
                    or attempt.dataset_id != _CONTROLLED_GAMENET_DATASET_ID
                    for attempt in attempts
                )
            )
        ):
            return StabilityStatus.FAILED
        completed = sum(item.outcome is AttemptOutcome.COMPLETED for item in attempts)
        missing_attempt_evidence = any(
            any(
                getattr(attempt, field) is None
                for field in (
                    *_IDENTITY_FIELDS,
                    "artifact_sha256",
                    *(("seed", "source_revision", "dataset_id") if self.version == 3 else ()),
                )
            )
            for attempt in attempts
        )
        missing_variance_evidence = not variance_checks or any(
            check.predeclared is None
            or check.tolerance is None
            or check.observed_variance is None
            or check.evidence_sha256 is None
            for check in variance_checks
        )
        if (
            selection_authority_sha256 is None
            or planned_attempts is None
            or completed < self.minimum_completed_attempts
            or protocol_violations is None
            or missing_attempt_evidence
            or missing_variance_evidence
            or any(value is None for value in upstream_fields)
        ):
            return StabilityStatus.UNRESOLVED
        return StabilityStatus.STABLE


@dataclass(frozen=True, slots=True)
class ReproductionCharacterization:
    characterization_id: str
    baseline_id: str
    mode: str
    policy_version: int
    policy_sha256: str
    accepted_selection_sha256: str | None
    selection_acceptance_sha256: str | None
    planned_attempts: int | None
    attempts: tuple[ReproductionAttempt, ...]
    protocol_violations: int | None
    variance_checks: tuple[VarianceCheck, ...]
    upstream_reference_sha256: str | None
    split_semantics_sha256: str | None
    selection_semantics_sha256: str | None
    evaluation_semantics_sha256: str | None
    status: StabilityStatus | str

    SCHEMA_VERSION: ClassVar[int] = 3
    V2_SCHEMA_VERSION: ClassVar[int] = 2
    LEGACY_SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.baseline_id, field="characterization.baseline_id")
        policy = ReproductionStabilityPolicy(version=self.policy_version)
        if self.policy_sha256 != policy.policy_sha256:
            raise ProtocolValidationError("characterization policy does not match its version")
        if policy.version == 1:
            selection_authority_sha256 = self.accepted_selection_sha256
            if self.selection_acceptance_sha256 is not None:
                raise ProtocolValidationError(
                    "V1 characterization cannot bind a Selection Acceptance"
                )
        else:
            selection_authority_sha256 = self.selection_acceptance_sha256
            if self.accepted_selection_sha256 is not None:
                raise ProtocolValidationError("V2+ characterization must bind Selection Acceptance")
        attempts = tuple(
            item if isinstance(item, ReproductionAttempt) else ReproductionAttempt.from_dict(item)
            for item in self.attempts
        )
        if len({item.attempt_id for item in attempts}) != len(attempts):
            raise ProtocolValidationError("reproduction attempt IDs must be unique")
        checks = tuple(
            item if isinstance(item, VarianceCheck) else VarianceCheck.from_dict(item)
            for item in self.variance_checks
        )
        if len({item.check_id for item in checks}) != len(checks):
            raise ProtocolValidationError("variance check IDs must be unique")
        if policy.version >= 2:
            unexpected = sorted(
                {item.check_id for item in checks} - set(policy.expected_output_ids)
            )
            if unexpected:
                raise ProtocolValidationError("variance checks contain unexpected output IDs")
        planned = _optional_nonnegative_int(
            self.planned_attempts, field="characterization.planned_attempts"
        )
        violations = _optional_nonnegative_int(
            self.protocol_violations, field="characterization.protocol_violations"
        )
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "variance_checks", checks)
        object.__setattr__(self, "planned_attempts", planned)
        object.__setattr__(self, "protocol_violations", violations)
        if policy.version == 3 and self.baseline_id != _CONTROLLED_GAMENET_BASELINE_ID:
            raise ProtocolValidationError("V3 characterization is reserved for controlled GAMENet")
        for field in (
            "accepted_selection_sha256",
            "selection_acceptance_sha256",
            "upstream_reference_sha256",
            "split_semantics_sha256",
            "selection_semantics_sha256",
            "evaluation_semantics_sha256",
        ):
            object.__setattr__(
                self,
                field,
                _optional_sha256(getattr(self, field), field=f"characterization.{field}"),
            )
        expected_status = policy.evaluate(
            mode=self.mode,
            selection_authority_sha256=selection_authority_sha256,
            planned_attempts=planned,
            attempts=attempts,
            protocol_violations=violations,
            variance_checks=checks,
            upstream_fields=(
                self.upstream_reference_sha256,
                self.split_semantics_sha256,
                self.selection_semantics_sha256,
                self.evaluation_semantics_sha256,
            ),
        )
        try:
            status = StabilityStatus(self.status)
        except (TypeError, ValueError) as error:
            raise ProtocolValidationError("characterization status is invalid") from error
        if status is not expected_status:
            raise ProtocolValidationError("characterization status does not match its evidence")
        object.__setattr__(self, "status", status)
        expected_id = f"characterization-{content_sha256(self._payload())[:20]}"
        if self.characterization_id != expected_id:
            raise ProtocolValidationError(
                f"characterization_id does not match content; expected {expected_id}"
            )

    def evaluate(self) -> StabilityStatus:
        return self.status

    def matches_baseline_definition(self, baseline: BaselineDefinition) -> bool:
        if self.policy_version != 3 or baseline.baseline_id != self.baseline_id:
            return False
        if (
            baseline.source.status is not SourceStatus.PINNED
            or baseline.source.revision != _CONTROLLED_GAMENET_SOURCE_REVISION
            or baseline.adapter_revision is None
            or baseline.environment_sha256 is None
            or baseline.readiness
            not in {BaselineReadiness.SMOKE_READY, BaselineReadiness.COMPARISON_READY}
        ):
            return False
        readiness_evidence = {
            item.gate: item.artifact_sha256 for item in baseline.readiness_evidence
        }
        adapter_smoke_sha256 = readiness_evidence.get(ReadinessGate.ADAPTER_SMOKE)
        environment_lock_sha256 = readiness_evidence.get(ReadinessGate.ENVIRONMENT_LOCK)
        if (
            adapter_smoke_sha256 is None
            or environment_lock_sha256 is None
            or baseline.environment_sha256 != environment_lock_sha256
        ):
            return False
        return all(
            attempt.source_revision == baseline.source.revision
            and attempt.adapter_sha256 == baseline.adapter_revision
            and attempt.environment_sha256 == baseline.environment_sha256
            and attempt.adapter_smoke_sha256 == adapter_smoke_sha256
            for attempt in self.attempts
        )

    def _payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "attempts": [
                attempt.to_dict(include_controlled_fields=self.policy_version == 3)
                for attempt in self.attempts
            ],
            "baseline_id": self.baseline_id,
            "evaluation_semantics_sha256": self.evaluation_semantics_sha256,
            "kind": "reproduction_characterization",
            "mode": self.mode,
            "planned_attempts": self.planned_attempts,
            "policy_sha256": self.policy_sha256,
            "policy_version": self.policy_version,
            "protocol_violations": self.protocol_violations,
            "selection_semantics_sha256": self.selection_semantics_sha256,
            "split_semantics_sha256": self.split_semantics_sha256,
            "status": self.status.value,
            "upstream_reference_sha256": self.upstream_reference_sha256,
            "variance_checks": [check.to_dict() for check in self.variance_checks],
        }
        if self.policy_version == 1:
            payload["accepted_selection_sha256"] = self.accepted_selection_sha256
            payload["schema_version"] = self.LEGACY_SCHEMA_VERSION
        else:
            payload["schema_version"] = self.policy_version
            payload["selection_acceptance_sha256"] = self.selection_acceptance_sha256
        return payload

    def to_dict(self) -> dict[str, object]:
        return {"characterization_id": self.characterization_id, **self._payload()}

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def create(
        cls, policy: ReproductionStabilityPolicy, **evidence: object
    ) -> ReproductionCharacterization:
        attempts = tuple(evidence.pop("attempts"))
        checks = tuple(evidence.pop("variance_checks"))
        if policy.version == 1:
            accepted_selection_sha256 = evidence.pop("accepted_selection_sha256", None)
            selection_acceptance_sha256 = None
            if "selection_acceptance_sha256" in evidence:
                raise ProtocolValidationError(
                    "V1 characterization cannot bind Selection Acceptance"
                )
        else:
            accepted_selection_sha256 = None
            selection_acceptance_sha256 = evidence.pop("selection_acceptance_sha256", None)
            if "accepted_selection_sha256" in evidence:
                raise ProtocolValidationError("V2+ characterization must bind Selection Acceptance")
        status = policy.evaluate(
            mode=evidence["mode"],
            selection_authority_sha256=(
                accepted_selection_sha256 if policy.version == 1 else selection_acceptance_sha256
            ),
            planned_attempts=evidence["planned_attempts"],
            attempts=attempts,
            protocol_violations=evidence["protocol_violations"],
            variance_checks=checks,
            upstream_fields=(
                evidence["upstream_reference_sha256"],
                evidence["split_semantics_sha256"],
                evidence["selection_semantics_sha256"],
                evidence["evaluation_semantics_sha256"],
            ),
        )
        payload = {
            **evidence,
            "attempts": attempts,
            "variance_checks": checks,
            "policy_version": policy.version,
            "policy_sha256": policy.policy_sha256,
            "status": status,
        }
        canonical_payload: dict[str, object] = {
            "attempts": [
                attempt.to_dict(include_controlled_fields=policy.version == 3)
                for attempt in attempts
            ],
            "baseline_id": payload["baseline_id"],
            "evaluation_semantics_sha256": payload["evaluation_semantics_sha256"],
            "kind": "reproduction_characterization",
            "mode": payload["mode"],
            "planned_attempts": payload["planned_attempts"],
            "policy_sha256": payload["policy_sha256"],
            "policy_version": payload["policy_version"],
            "protocol_violations": payload["protocol_violations"],
            "selection_semantics_sha256": payload["selection_semantics_sha256"],
            "split_semantics_sha256": payload["split_semantics_sha256"],
            "status": status.value,
            "upstream_reference_sha256": payload["upstream_reference_sha256"],
            "variance_checks": [check.to_dict() for check in checks],
        }
        if policy.version == 1:
            canonical_payload["accepted_selection_sha256"] = accepted_selection_sha256
            canonical_payload["schema_version"] = cls.LEGACY_SCHEMA_VERSION
        else:
            canonical_payload["schema_version"] = policy.version
            canonical_payload["selection_acceptance_sha256"] = selection_acceptance_sha256
        return cls(
            characterization_id=f"characterization-{content_sha256(canonical_payload)[:20]}",
            accepted_selection_sha256=accepted_selection_sha256,
            selection_acceptance_sha256=selection_acceptance_sha256,
            **payload,
        )

    @classmethod
    def from_dict(cls, value: object) -> ReproductionCharacterization:
        if not isinstance(value, dict):
            raise ProtocolValidationError("ReproductionCharacterization must be an object")
        schema_version = value.get("schema_version")
        required = (
            "schema_version",
            "kind",
            "characterization_id",
            "baseline_id",
            "mode",
            "policy_version",
            "policy_sha256",
            "status",
            "attempts",
            "variance_checks",
        )
        optional = (
            "planned_attempts",
            "protocol_violations",
            "upstream_reference_sha256",
            "split_semantics_sha256",
            "selection_semantics_sha256",
            "evaluation_semantics_sha256",
        )
        if schema_version == cls.LEGACY_SCHEMA_VERSION:
            required_fields = required
            optional_fields = ("accepted_selection_sha256", *optional)
        elif schema_version in {cls.V2_SCHEMA_VERSION, cls.SCHEMA_VERSION}:
            required_fields = (*required, "selection_acceptance_sha256")
            optional_fields = optional
        else:
            raise ProtocolValidationError(
                "ReproductionCharacterization schema_version is unsupported"
            )
        payload = strict_fields(
            value,
            required=required_fields,
            optional=optional_fields,
            context="ReproductionCharacterization",
        )
        if payload.pop("schema_version") != schema_version:
            raise ProtocolValidationError("ReproductionCharacterization schema_version is invalid")
        if payload.pop("kind") != "reproduction_characterization":
            raise ProtocolValidationError(
                "ReproductionCharacterization kind must be reproduction_characterization"
            )
        if payload["policy_version"] != schema_version:
            raise ProtocolValidationError(
                "ReproductionCharacterization schema and policy versions must match"
            )
        attempts = _objects(payload.pop("attempts"), field="characterization.attempts")
        checks = _objects(payload.pop("variance_checks"), field="characterization.variance_checks")
        for field in optional:
            payload.setdefault(field, None)
        accepted_selection_sha256 = (
            payload.pop("accepted_selection_sha256", None)
            if schema_version == cls.LEGACY_SCHEMA_VERSION
            else None
        )
        selection_acceptance_sha256 = (
            payload.pop("selection_acceptance_sha256", None)
            if schema_version in {cls.V2_SCHEMA_VERSION, cls.SCHEMA_VERSION}
            else None
        )
        return cls(
            accepted_selection_sha256=accepted_selection_sha256,
            attempts=tuple(ReproductionAttempt.from_dict(item) for item in attempts),
            selection_acceptance_sha256=selection_acceptance_sha256,
            variance_checks=tuple(VarianceCheck.from_dict(item) for item in checks),
            **payload,
        )

    @classmethod
    def from_json(cls, text: str) -> ReproductionCharacterization:
        return cls.from_dict(parse_json_object(text, context="ReproductionCharacterization"))

    @classmethod
    def load(cls, path: str | Path) -> ReproductionCharacterization:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


__all__ = (
    "AttemptOutcome",
    "ReproductionAttempt",
    "ReproductionCharacterization",
    "ReproductionStabilityPolicy",
    "StabilityStatus",
    "VarianceCheck",
)
