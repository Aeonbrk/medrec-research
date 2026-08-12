"""Deterministic, public-safe scheduling contracts for reproduction lanes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ._validation import (
    canonical_json,
    content_sha256,
    enum_member,
    parse_json_object,
    require_identifier,
    require_int,
    require_single_line_public_string,
    strict_fields,
)
from .errors import ProtocolValidationError


def _nonnegative(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ProtocolValidationError(f"{field} must be a finite non-negative number")
    result = float(value)
    if result != result or result in {float("inf"), float("-inf")}:
        raise ProtocolValidationError(f"{field} must be a finite non-negative number")
    return result


class LaneStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    INVALID = "invalid"


class ExceptionKind(StrEnum):
    AUTHORITY = "authority"
    PRIVACY = "privacy"
    LEGALITY = "legality"
    RESOURCE = "resource"
    SCIENTIFIC = "scientific"
    DEPENDENCY = "dependency"
    ENDPOINT = "endpoint"


class ExceptionDisposition(StrEnum):
    BLOCK = "block"
    REPAIR = "repair"
    CONTINUE = "continue"


@dataclass(frozen=True, slots=True)
class ResourceCeiling:
    cpu_hours: float = 0.0
    gpu_count: int = 0
    memory_gb: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "cpu_hours", _nonnegative(self.cpu_hours, field="resources.cpu_hours")
        )
        require_int(self.gpu_count, field="resources.gpu_count", minimum=0)
        object.__setattr__(
            self, "memory_gb", _nonnegative(self.memory_gb, field="resources.memory_gb")
        )

    def can_fit(self, lane: LaneSpec) -> bool:
        return (
            lane.cpu_hours <= self.cpu_hours
            and lane.gpu_count <= self.gpu_count
            and lane.memory_gb <= self.memory_gb
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "cpu_hours": self.cpu_hours,
            "gpu_count": self.gpu_count,
            "memory_gb": self.memory_gb,
        }

    @classmethod
    def from_dict(cls, value: object) -> ResourceCeiling:
        return cls(
            **strict_fields(
                value,
                required=("cpu_hours", "gpu_count", "memory_gb"),
                context="ResourceCeiling",
            )
        )


@dataclass(frozen=True, slots=True)
class LaneSpec:
    lane_id: str
    model_id: str
    ordinal: int
    cpu_hours: float
    gpu_count: int
    memory_gb: float
    status: LaneStatus | str = LaneStatus.QUEUED
    contract_sha256: str | None = None

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, field="lane.lane_id")
        require_identifier(self.model_id, field="lane.model_id")
        require_int(self.ordinal, field="lane.ordinal", minimum=0)
        object.__setattr__(self, "cpu_hours", _nonnegative(self.cpu_hours, field="lane.cpu_hours"))
        require_int(self.gpu_count, field="lane.gpu_count", minimum=0)
        object.__setattr__(self, "memory_gb", _nonnegative(self.memory_gb, field="lane.memory_gb"))
        object.__setattr__(
            self, "status", enum_member(LaneStatus, self.status, field="lane.status")
        )
        if self.contract_sha256 is not None and (
            len(self.contract_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.contract_sha256)
        ):
            raise ProtocolValidationError("lane.contract_sha256 must be a lowercase SHA-256 digest")

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_sha256": self.contract_sha256,
            "cpu_hours": self.cpu_hours,
            "gpu_count": self.gpu_count,
            "lane_id": self.lane_id,
            "memory_gb": self.memory_gb,
            "model_id": self.model_id,
            "ordinal": self.ordinal,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> LaneSpec:
        return cls(
            **strict_fields(
                value,
                required=(
                    "contract_sha256",
                    "cpu_hours",
                    "gpu_count",
                    "lane_id",
                    "memory_gb",
                    "model_id",
                    "ordinal",
                    "status",
                ),
                context="LaneSpec",
            )
        )


@dataclass(frozen=True, slots=True)
class RepairBudget:
    max_units: int = 0
    used_units: int = 0

    def __post_init__(self) -> None:
        require_int(self.max_units, field="repair.max_units", minimum=0)
        require_int(self.used_units, field="repair.used_units", minimum=0)
        if self.used_units > self.max_units:
            raise ProtocolValidationError("repair budget is exhausted")

    @property
    def remaining_units(self) -> int:
        return self.max_units - self.used_units

    def consume(self, units: int) -> RepairBudget:
        require_int(units, field="repair.units", minimum=1)
        if units > self.remaining_units:
            raise ProtocolValidationError("repair budget is exhausted")
        return RepairBudget(max_units=self.max_units, used_units=self.used_units + units)

    def to_dict(self) -> dict[str, int]:
        return {"max_units": self.max_units, "used_units": self.used_units}

    @classmethod
    def from_dict(cls, value: object) -> RepairBudget:
        return cls(
            **strict_fields(value, required=("max_units", "used_units"), context="RepairBudget")
        )


@dataclass(frozen=True, slots=True)
class ExceptionRecord:
    exception_id: str
    kind: ExceptionKind | str
    description: str
    repair_units: int = 0
    artifact_changed: bool = False
    equivalence_evidence: bool = False

    def __post_init__(self) -> None:
        require_identifier(self.exception_id, field="exception.exception_id")
        object.__setattr__(
            self, "kind", enum_member(ExceptionKind, self.kind, field="exception.kind")
        )
        require_single_line_public_string(self.description, field="exception.description")
        require_int(self.repair_units, field="exception.repair_units", minimum=0)
        if type(self.artifact_changed) is not bool or type(self.equivalence_evidence) is not bool:
            raise ProtocolValidationError("exception artifact/equivalence flags must be boolean")
        if self.artifact_changed and self.repair_units == 0:
            raise ProtocolValidationError("artifact-changing exception requires repair units")

    @property
    def non_waivable(self) -> bool:
        return self.kind in {
            ExceptionKind.AUTHORITY,
            ExceptionKind.PRIVACY,
            ExceptionKind.LEGALITY,
            ExceptionKind.RESOURCE,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_changed": self.artifact_changed,
            "description": self.description,
            "equivalence_evidence": self.equivalence_evidence,
            "exception_id": self.exception_id,
            "kind": self.kind.value,
            "repair_units": self.repair_units,
        }

    @classmethod
    def from_dict(cls, value: object) -> ExceptionRecord:
        return cls(
            **strict_fields(
                value,
                required=(
                    "artifact_changed",
                    "description",
                    "equivalence_evidence",
                    "exception_id",
                    "kind",
                    "repair_units",
                ),
                context="ExceptionRecord",
            )
        )


@dataclass(frozen=True, slots=True)
class ScheduleDecision:
    logical_lane_ids: tuple[str, ...]
    ready_lane_ids: tuple[str, ...]
    blocked_lane_ids: tuple[str, ...]
    next_lane_id: str | None
    resource_ceiling: ResourceCeiling
    admitted_resources: ResourceCeiling
    repair_budget: RepairBudget
    exception_dispositions: tuple[tuple[str, ExceptionDisposition], ...] = ()
    reason: str = ""
    decision_sha256: str = ""

    def __post_init__(self) -> None:
        for field in ("logical_lane_ids", "ready_lane_ids", "blocked_lane_ids"):
            values = tuple(
                require_identifier(item, field=f"schedule.{field}") for item in getattr(self, field)
            )
            if len(values) != len(set(values)):
                raise ProtocolValidationError(f"schedule.{field} entries must be unique")
            object.__setattr__(self, field, values)
        if set(self.ready_lane_ids) - set(self.logical_lane_ids):
            raise ProtocolValidationError("ready lanes must be logical lanes")
        if set(self.blocked_lane_ids) - set(self.logical_lane_ids):
            raise ProtocolValidationError("blocked lanes must be logical lanes")
        if self.next_lane_id is not None:
            require_identifier(self.next_lane_id, field="schedule.next_lane_id")
            if self.next_lane_id not in self.ready_lane_ids:
                raise ProtocolValidationError("next lane must be ready")
        if not isinstance(self.resource_ceiling, ResourceCeiling) or not isinstance(
            self.admitted_resources, ResourceCeiling
        ):
            raise ProtocolValidationError("schedule resources must be ResourceCeiling records")
        if (
            self.admitted_resources.cpu_hours > self.resource_ceiling.cpu_hours
            or self.admitted_resources.gpu_count > self.resource_ceiling.gpu_count
            or self.admitted_resources.memory_gb > self.resource_ceiling.memory_gb
        ):
            raise ProtocolValidationError("schedule exceeds resource ceiling")
        if not isinstance(self.repair_budget, RepairBudget):
            raise ProtocolValidationError("schedule.repair_budget must be a RepairBudget")
        dispositions = tuple(
            (
                require_identifier(exception_id, field="schedule.exception_id"),
                enum_member(ExceptionDisposition, disposition, field="schedule.disposition"),
            )
            for exception_id, disposition in self.exception_dispositions
        )
        object.__setattr__(self, "exception_dispositions", dispositions)
        if self.reason:
            require_single_line_public_string(self.reason, field="schedule.reason")
        expected = content_sha256(self._protected_payload())
        if self.decision_sha256:
            if len(self.decision_sha256) != 64 or any(
                char not in "0123456789abcdef" for char in self.decision_sha256
            ):
                raise ProtocolValidationError("schedule.decision_sha256 must be a SHA-256 digest")
            if self.decision_sha256 != expected:
                raise ProtocolValidationError(
                    "schedule.decision_sha256 does not match schedule content"
                )
        else:
            object.__setattr__(self, "decision_sha256", expected)

    def _protected_payload(self) -> dict[str, object]:
        return {
            "admitted_resources": self.admitted_resources.to_dict(),
            "blocked_lane_ids": list(self.blocked_lane_ids),
            "exception_dispositions": [
                {"exception_id": key, "disposition": value.value}
                for key, value in self.exception_dispositions
            ],
            "logical_lane_ids": list(self.logical_lane_ids),
            "next_lane_id": self.next_lane_id,
            "ready_lane_ids": list(self.ready_lane_ids),
            "repair_budget": self.repair_budget.to_dict(),
            "resource_ceiling": self.resource_ceiling.to_dict(),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._protected_payload(),
            "decision_sha256": self.decision_sha256,
            "kind": "schedule_decision",
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: object) -> ScheduleDecision:
        payload = strict_fields(
            value,
            required=(
                "admitted_resources",
                "blocked_lane_ids",
                "decision_sha256",
                "exception_dispositions",
                "kind",
                "logical_lane_ids",
                "next_lane_id",
                "ready_lane_ids",
                "reason",
                "repair_budget",
                "resource_ceiling",
            ),
            context="ScheduleDecision",
        )
        if payload.pop("kind") != "schedule_decision":
            raise ProtocolValidationError("ScheduleDecision kind is invalid")
        dispositions = payload.pop("exception_dispositions")
        if not isinstance(dispositions, list):
            raise ProtocolValidationError("schedule exception_dispositions must be a list")
        payload["exception_dispositions"] = tuple(
            (item["exception_id"], item["disposition"]) for item in dispositions
        )
        payload["resource_ceiling"] = ResourceCeiling.from_dict(payload["resource_ceiling"])
        payload["admitted_resources"] = ResourceCeiling.from_dict(payload["admitted_resources"])
        payload["repair_budget"] = RepairBudget.from_dict(payload["repair_budget"])
        return cls(**payload)

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> ScheduleDecision:
        return cls.from_dict(parse_json_object(text, context="ScheduleDecision"))


def route_exception(
    exception: ExceptionRecord,
    budget: RepairBudget,
) -> tuple[ExceptionDisposition, RepairBudget]:
    """Route one exception without waiving non-waivable boundaries."""

    if exception.non_waivable:
        return ExceptionDisposition.BLOCK, budget
    if exception.kind is ExceptionKind.ENDPOINT and not exception.artifact_changed:
        return ExceptionDisposition.CONTINUE, budget
    if exception.repair_units <= 0:
        return ExceptionDisposition.BLOCK, budget
    try:
        remaining = budget.consume(exception.repair_units)
    except ProtocolValidationError:
        return ExceptionDisposition.BLOCK, budget
    return ExceptionDisposition.REPAIR, remaining


def schedule_lanes(
    lanes: Iterable[LaneSpec],
    *,
    resource_ceiling: ResourceCeiling,
    repair_budget: RepairBudget | None = None,
    exceptions: Iterable[ExceptionRecord] = (),
) -> ScheduleDecision:
    """Produce a stable logical schedule; no process or remote side effect occurs."""

    ordered = tuple(sorted(lanes, key=lambda lane: (lane.ordinal, lane.lane_id)))
    if not ordered:
        raise ProtocolValidationError("schedule requires at least one lane")
    lane_ids = {lane.lane_id for lane in ordered}
    if len(lane_ids) != len(ordered):
        raise ProtocolValidationError("lane IDs must be unique")
    budget = repair_budget or RepairBudget()
    dispositions: list[tuple[str, ExceptionDisposition]] = []
    blocked_by_exception: set[str] = set()
    for exception in exceptions:
        disposition, budget = route_exception(exception, budget)
        dispositions.append((exception.exception_id, disposition))
        if disposition is ExceptionDisposition.BLOCK:
            blocked_by_exception.add(exception.exception_id)
    ready: list[LaneSpec] = []
    blocked: list[LaneSpec] = []
    for lane in ordered:
        if lane.status in {LaneStatus.COMPLETED, LaneStatus.FAILED, LaneStatus.INVALID}:
            continue
        if not resource_ceiling.can_fit(lane):
            blocked.append(lane)
        else:
            ready.append(lane)
    if blocked_by_exception and ready:
        if blocked_by_exception - lane_ids:
            blocked.extend(ready)
            ready = []
        else:
            ready = [lane for lane in ready if lane.lane_id not in blocked_by_exception]
    next_lane = ready[0] if ready else None
    admitted = (
        ResourceCeiling(
            cpu_hours=next_lane.cpu_hours,
            gpu_count=next_lane.gpu_count,
            memory_gb=next_lane.memory_gb,
        )
        if next_lane is not None
        else ResourceCeiling()
    )
    logical_ids = tuple(lane.lane_id for lane in ordered)
    return ScheduleDecision(
        logical_lane_ids=logical_ids,
        ready_lane_ids=tuple(lane.lane_id for lane in ready),
        blocked_lane_ids=tuple(
            dict.fromkeys(
                lane.lane_id
                for lane in (
                    *blocked,
                    *[lane for lane in ordered if lane.lane_id in blocked_by_exception],
                )
            )
        ),
        next_lane_id=next_lane.lane_id if next_lane else None,
        resource_ceiling=resource_ceiling,
        admitted_resources=admitted,
        repair_budget=budget,
        exception_dispositions=tuple(dispositions),
        reason="stable-annex-order",
    )


deterministic_schedule = schedule_lanes
LaneResource = ResourceCeiling


__all__ = (
    "ExceptionDisposition",
    "ExceptionKind",
    "ExceptionRecord",
    "LaneResource",
    "LaneSpec",
    "LaneStatus",
    "RepairBudget",
    "ResourceCeiling",
    "ScheduleDecision",
    "deterministic_schedule",
    "route_exception",
    "schedule_lanes",
)
