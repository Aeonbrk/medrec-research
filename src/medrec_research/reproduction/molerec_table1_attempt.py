"""Attempt-owned frozen declaration, schedule, continuation, and test command policy."""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .._validation import (
    parse_json_object,
    require_identifier,
    require_string,
    strict_fields,
    write_json_atomic,
)
from ..errors import ProtocolValidationError
from ..registry import BaselineRegistry
from .reproduction_evidence import reopen_training_evidence, resolve_training_artifact

TABLE1_PREPROCESSING_REVISION = "c7218d0976e5ee5588aeaf5bdbc86b338126bba5"
TABLE1_DECLARATION_SCHEMA_VERSION = 1
TABLE1_DECLARATION_KIND = "molerec_table1_attempt_declaration_v1"
TABLE1_RESERVED_GPU = 7
TABLE1_TEST_CPU_SET = "28-31,60-63"
TABLE1_FIXED_TEST_LANES = (
    "molerec-retain",
    "molerec-leap",
    "molerec-gamenet",
    "molerec-embedding",
)
TABLE1_PAPER_BASELINES = ("retain", "leap", "gamenet", "safedrug", "molerec")

_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40,64}")
_PUBLIC_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")
_CPU_SET = re.compile(r"(?:[0-9]+(?:-[0-9]+)?)(?:,(?:[0-9]+(?:-[0-9]+)?))*")


def _validate_cpu_set_syntax(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _CPU_SET.fullmatch(value):
        raise ProtocolValidationError("cpu_set must be a comma-separated CPU list or range")
    values: list[int] = []
    for item in value.split(","):
        bounds = [int(bound) for bound in item.split("-")]
        if len(bounds) == 1:
            values.append(bounds[0])
        elif len(bounds) == 2:
            if bounds[0] > bounds[1]:
                raise ProtocolValidationError("cpu_set ranges must be ascending")
            values.extend(range(bounds[0], bounds[1] + 1))
        else:
            raise ProtocolValidationError("cpu_set range format is invalid")
    if len(values) != len(set(values)):
        raise ProtocolValidationError("cpu_set must not repeat a CPU")
    return value


def _remote_posix_path(path: str | Path, *, field: str) -> str:
    rendered = str(path).strip()
    if not rendered:
        raise ProtocolValidationError(f"{field} must not be empty")
    pure = PurePosixPath(rendered)
    if not pure.is_absolute():
        raise ProtocolValidationError(f"{field} must be an absolute remote POSIX path")
    if any(part in ("..", ".") for part in pure.parts):
        raise ProtocolValidationError(f"{field} contains relative path components")
    return str(pure)


@dataclass(frozen=True, slots=True)
class ReproductionLaneDeclaration:
    """Frozen scientific identity facts for one reproduction lane."""

    lane_id: str
    scientific_baseline_id: str
    program_id: str
    profile_id: str
    formal_test: str
    learning_rate: float | None
    default_gpu_index: int | None
    model_source_revision: str
    environment_sha256: str
    entrypoint: str
    upstream_root: str
    dataset_subdirectory: str
    run_subdirectory: str
    required_inputs: tuple[str, ...]

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
        if not _IMMUTABLE_REVISION.fullmatch(self.model_source_revision):
            raise ProtocolValidationError("model_source_revision must be an immutable revision")
        require_string(self.entrypoint, field="entrypoint")
        require_string(self.upstream_root, field="upstream_root")
        require_string(self.dataset_subdirectory, field="dataset_subdirectory")
        require_string(self.run_subdirectory, field="run_subdirectory")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "lane_id": self.lane_id,
            "scientific_baseline_id": self.scientific_baseline_id,
            "program_id": self.program_id,
            "profile_id": self.profile_id,
            "formal_test": self.formal_test,
            "model_source_revision": self.model_source_revision,
            "environment_sha256": self.environment_sha256,
            "entrypoint": self.entrypoint,
            "upstream_root": self.upstream_root,
            "dataset_subdirectory": self.dataset_subdirectory,
            "run_subdirectory": self.run_subdirectory,
            "required_inputs": list(self.required_inputs),
        }
        if self.learning_rate is not None:
            payload["learning_rate"] = self.learning_rate
        if self.default_gpu_index is not None:
            payload["default_gpu_index"] = self.default_gpu_index
        return payload

    @classmethod
    def from_dict(cls, value: object) -> ReproductionLaneDeclaration:
        payload = strict_fields(
            value,
            required=(
                "lane_id",
                "scientific_baseline_id",
                "program_id",
                "profile_id",
                "formal_test",
                "model_source_revision",
                "environment_sha256",
                "entrypoint",
                "upstream_root",
                "dataset_subdirectory",
                "run_subdirectory",
                "required_inputs",
            ),
            optional=("learning_rate", "default_gpu_index"),
            context="reproduction lane declaration",
        )
        required_inputs = payload["required_inputs"]
        if not isinstance(required_inputs, (list, tuple)) or not all(
            isinstance(i, str) for i in required_inputs
        ):
            raise ProtocolValidationError("required_inputs must be a list of strings")
        return cls(
            lane_id=payload["lane_id"],
            scientific_baseline_id=payload["scientific_baseline_id"],
            program_id=payload["program_id"],
            profile_id=payload["profile_id"],
            formal_test=payload["formal_test"],
            learning_rate=payload.get("learning_rate"),
            default_gpu_index=payload.get("default_gpu_index"),
            model_source_revision=payload["model_source_revision"],
            environment_sha256=payload["environment_sha256"],
            entrypoint=payload["entrypoint"],
            upstream_root=payload["upstream_root"],
            dataset_subdirectory=payload["dataset_subdirectory"],
            run_subdirectory=payload["run_subdirectory"],
            required_inputs=tuple(required_inputs),
        )


@dataclass(frozen=True, slots=True)
class ReproductionAttemptDeclaration:
    """Immutable per-attempt snapshot of Registry reproduction lane declarations."""

    attempt_id: str
    lanes: tuple[ReproductionLaneDeclaration, ...]
    schema_version: int = TABLE1_DECLARATION_SCHEMA_VERSION
    kind: str = TABLE1_DECLARATION_KIND

    def __post_init__(self) -> None:
        require_identifier(self.attempt_id, field="attempt_id")
        if not self.lanes:
            raise ProtocolValidationError("reproduction attempt declaration must not be empty")
        lane_ids = tuple(lane.lane_id for lane in self.lanes)
        if len(lane_ids) != len(set(lane_ids)):
            raise ProtocolValidationError(
                "reproduction attempt declaration lane IDs must be unique"
            )

    @property
    def lane_ids(self) -> tuple[str, ...]:
        return tuple(lane.lane_id for lane in self.lanes)

    def has_lane(self, lane_id: str) -> bool:
        return any(lane.lane_id == lane_id for lane in self.lanes)

    def get_lane(self, lane_id: str) -> ReproductionLaneDeclaration:
        for lane in self.lanes:
            if lane.lane_id == lane_id:
                return lane
        raise ProtocolValidationError(f"attempt declaration omits lane '{lane_id}'")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "attempt_id": self.attempt_id,
            "lane_order": [lane.lane_id for lane in self.lanes],
            "lanes": {lane.lane_id: lane.to_dict() for lane in self.lanes},
        }

    @classmethod
    def from_dict(cls, value: object) -> ReproductionAttemptDeclaration:
        payload = strict_fields(
            value,
            required=("schema_version", "kind", "attempt_id", "lanes"),
            optional=("lane_order",),
            context="reproduction attempt declaration",
        )
        if payload["schema_version"] != TABLE1_DECLARATION_SCHEMA_VERSION:
            raise ProtocolValidationError("unsupported attempt declaration schema version")
        if payload["kind"] not in (
            TABLE1_DECLARATION_KIND,
            "reproduction_attempt_declaration",
        ):
            raise ProtocolValidationError("invalid attempt declaration kind")
        raw_lanes = payload["lanes"]
        lane_order = payload.get("lane_order")
        if isinstance(raw_lanes, Mapping):
            if lane_order is not None and isinstance(lane_order, Sequence):
                lanes = tuple(
                    ReproductionLaneDeclaration.from_dict(raw_lanes[lane_id])
                    for lane_id in lane_order
                )
            else:
                lanes = tuple(
                    ReproductionLaneDeclaration.from_dict(raw_lanes[lane_id])
                    for lane_id in raw_lanes
                )
        elif isinstance(raw_lanes, Sequence):
            lanes = tuple(ReproductionLaneDeclaration.from_dict(item) for item in raw_lanes)
        else:
            raise ProtocolValidationError("attempt declaration lanes must be a mapping or sequence")
        return cls(
            attempt_id=payload["attempt_id"],
            lanes=lanes,
            schema_version=payload["schema_version"],
            kind=payload["kind"],
        )

    @classmethod
    def from_json(cls, path: str | Path) -> ReproductionAttemptDeclaration:
        try:
            payload = parse_json_object(
                Path(path).read_text(encoding="utf-8"),
                context="reproduction attempt declaration",
            )
        except OSError as error:
            raise ProtocolValidationError(
                f"attempt declaration could not be read: {error}"
            ) from error
        return cls.from_dict(payload)

    @classmethod
    def from_registry(
        cls,
        registry: BaselineRegistry,
        attempt_id: str,
    ) -> ReproductionAttemptDeclaration:
        """Freeze Registry reproduction lane declarations into an immutable attempt snapshot."""
        require_identifier(attempt_id, field="attempt_id")
        lanes_raw = registry.reproduction_lanes
        if not lanes_raw:
            raise ProtocolValidationError("registry declares no reproduction lanes")
        lane_ids = [lane.lane_id for lane in lanes_raw]
        if len(lane_ids) != len(set(lane_ids)):
            raise ProtocolValidationError("registry reproduction lanes must have unique IDs")

        declarations: list[ReproductionLaneDeclaration] = []
        for lane in lanes_raw:
            baseline = registry.get(lane.scientific_baseline_id)
            program = registry.get_program(lane.program_id)
            declarations.append(
                ReproductionLaneDeclaration(
                    lane_id=lane.lane_id,
                    scientific_baseline_id=lane.scientific_baseline_id,
                    program_id=lane.program_id,
                    profile_id=lane.profile_id,
                    formal_test=lane.formal_test,
                    learning_rate=lane.learning_rate,
                    default_gpu_index=lane.default_gpu_index,
                    model_source_revision=baseline.source.revision,
                    environment_sha256=program.environment_sha256 or "unverified",
                    entrypoint=program.entrypoint,
                    upstream_root=program.upstream_root,
                    dataset_subdirectory=program.dataset_subdirectory,
                    run_subdirectory=program.run_subdirectory,
                    required_inputs=tuple(program.required_inputs),
                )
            )
        return cls(attempt_id=attempt_id, lanes=tuple(declarations))

    def write_atomic(self, path: str | Path) -> None:
        write_json_atomic(Path(path), self.to_dict())


@dataclass(frozen=True, slots=True)
class ScheduleAllocation:
    """One immutable lane allocation from the accepted formal schedule."""

    lane_id: str
    gpu_index: int
    cpu_set: str
    numa_node: int


@dataclass(frozen=True, slots=True)
class FrozenSchedule:
    """Public-safe frozen schedule contract for the seven successor lanes."""

    harness_revision: str
    environment_sha256: str
    preprocessing_revision: str
    snapshot_id: str
    model_source_revisions: tuple[tuple[str, str], ...]
    allocations: tuple[ScheduleAllocation, ...]
    reserved_gpu: int
    selected_mapping: str
    owner_attempt_id: str | None = None
    source_schedule_id: str | None = None
    source_harness_revision: str | None = None

    def __post_init__(self) -> None:
        if self.reserved_gpu != TABLE1_RESERVED_GPU:
            raise ProtocolValidationError("frozen schedule must reserve GPU 7")
        lineage = (self.source_schedule_id, self.source_harness_revision)
        if any(value is not None for value in lineage) and (
            self.owner_attempt_id is None
            or not _PUBLIC_ID.fullmatch(self.owner_attempt_id)
            or self.source_schedule_id is None
            or not _PUBLIC_ID.fullmatch(self.source_schedule_id)
            or self.source_harness_revision is None
            or not _IMMUTABLE_REVISION.fullmatch(self.source_harness_revision)
        ):
            raise ProtocolValidationError(
                "reaccepted frozen schedule requires valid attempt and source identity"
            )

    @classmethod
    def from_json(
        cls,
        path: str | Path,
        *,
        expected_lane_ids: Sequence[str] | None = None,
        declaration: ReproductionAttemptDeclaration | None = None,
    ) -> FrozenSchedule:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ProtocolValidationError("frozen schedule artifact could not be read") from error
        return cls.from_dict(
            payload,
            expected_lane_ids=expected_lane_ids,
            declaration=declaration,
        )

    @classmethod
    def from_dict(
        cls,
        value: object,
        *,
        expected_lane_ids: Sequence[str] | None = None,
        declaration: ReproductionAttemptDeclaration | None = None,
    ) -> FrozenSchedule:
        if not isinstance(value, dict):
            raise ProtocolValidationError("frozen schedule artifact must be a JSON object")
        schema_version = value.get("schema_version")
        if schema_version not in (1, 2):
            raise ProtocolValidationError("frozen schedule schema_version must be 1 or 2")
        if value.get("stage") != "u7-measured-gpu-schedule":
            raise ProtocolValidationError("frozen schedule stage is invalid")
        if value.get("schedule_state") != "frozen":
            raise ProtocolValidationError("frozen schedule is not frozen")
        if value.get("gpu7_reserved") is not True:
            raise ProtocolValidationError("frozen schedule must reserve GPU 7")

        if declaration is not None:
            expected_lane_ids = declaration.lane_ids
        elif expected_lane_ids is not None:
            expected_lane_ids = tuple(expected_lane_ids)
        else:
            raw_mapping = value.get("mapping")
            if isinstance(raw_mapping, dict):
                expected_lane_ids = tuple(raw_mapping.keys())
            else:
                raise ProtocolValidationError("frozen schedule mapping is invalid")

        if not expected_lane_ids or len(expected_lane_ids) != len(set(expected_lane_ids)):
            raise ProtocolValidationError("frozen schedule expected lane IDs must be unique")

        harness_revision = value.get("harness_revision")
        environment_sha256 = value.get("environment_sha256")
        preprocessing_revision = value.get("preprocessing_revision")
        snapshot_id = value.get("snapshot_id")
        if not isinstance(harness_revision, str) or not _IMMUTABLE_REVISION.fullmatch(
            harness_revision
        ):
            raise ProtocolValidationError("frozen schedule harness revision is invalid")
        if not isinstance(environment_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", environment_sha256
        ):
            raise ProtocolValidationError("frozen schedule environment hash is invalid")
        if not isinstance(preprocessing_revision, str) or not _IMMUTABLE_REVISION.fullmatch(
            preprocessing_revision
        ):
            raise ProtocolValidationError("frozen schedule preprocessing revision is invalid")
        snapshot_path = PurePosixPath(snapshot_id) if isinstance(snapshot_id, str) else None
        if (
            not isinstance(snapshot_id, str)
            or not snapshot_id
            or snapshot_path is None
            or snapshot_path.is_absolute()
            or ".." in snapshot_path.parts
            or str(snapshot_path) != snapshot_id
        ):
            raise ProtocolValidationError("frozen schedule snapshot_id is invalid")

        owner_attempt_id = value.get("attempt_id")
        if owner_attempt_id is not None and (
            not isinstance(owner_attempt_id, str) or not _PUBLIC_ID.fullmatch(owner_attempt_id)
        ):
            raise ProtocolValidationError("frozen schedule attempt_id is invalid")
        source_schedule_id = value.get("source_schedule_id")
        source_harness_revision = value.get("source_harness_revision")
        if schema_version == 2 and (
            owner_attempt_id is None
            or not isinstance(source_schedule_id, str)
            or not _PUBLIC_ID.fullmatch(source_schedule_id)
            or not isinstance(source_harness_revision, str)
            or not _IMMUTABLE_REVISION.fullmatch(source_harness_revision)
        ):
            raise ProtocolValidationError(
                "reaccepted frozen schedule requires valid attempt and source identity"
            )

        formal_execution = value.get("formal_execution")
        if not isinstance(formal_execution, dict):
            raise ProtocolValidationError("frozen schedule formal_execution is invalid")
        if formal_execution.get("mode") != "formal":
            raise ProtocolValidationError("frozen schedule mode must be formal")
        reserved_gpu = formal_execution.get("reserved_gpu")
        if (
            reserved_gpu != TABLE1_RESERVED_GPU
            or value.get("reserved_gpu", reserved_gpu) != TABLE1_RESERVED_GPU
        ):
            raise ProtocolValidationError("frozen schedule must reserve GPU 7")
        gpu_order = formal_execution.get("gpu_order")
        cpu_set_order = formal_execution.get("cpu_set_order")
        if not isinstance(gpu_order, list) or not isinstance(cpu_set_order, list):
            raise ProtocolValidationError("frozen schedule execution order is invalid")

        raw_mapping = value.get("mapping")
        if not isinstance(raw_mapping, dict) or set(raw_mapping) != set(expected_lane_ids):
            raise ProtocolValidationError(
                "frozen schedule mapping must contain every declared lane"
            )
        allocations: list[ScheduleAllocation] = []
        for lane_id in expected_lane_ids:
            raw_allocation = raw_mapping.get(lane_id)
            if not isinstance(raw_allocation, dict):
                raise ProtocolValidationError("frozen schedule lane allocation is invalid")
            gpu_index = raw_allocation.get("gpu")
            cpu_set = raw_allocation.get("cpu_set")
            numa_node = raw_allocation.get("numa")
            if type(gpu_index) is not int or gpu_index < 0:
                raise ProtocolValidationError("frozen schedule GPU allocation is invalid")
            if not isinstance(cpu_set, str) or not _CPU_SET.fullmatch(cpu_set):
                raise ProtocolValidationError("frozen schedule CPU allocation is invalid")
            if type(numa_node) is not int or numa_node < 0:
                raise ProtocolValidationError("frozen schedule NUMA allocation is invalid")
            allocations.append(
                ScheduleAllocation(
                    lane_id=lane_id,
                    gpu_index=gpu_index,
                    cpu_set=cpu_set,
                    numa_node=numa_node,
                )
            )
        if gpu_order != [allocation.gpu_index for allocation in allocations] or cpu_set_order != [
            allocation.cpu_set for allocation in allocations
        ]:
            raise ProtocolValidationError("frozen schedule order does not match its lane mapping")

        raw_sources = value.get("model_source_revisions")
        if not isinstance(raw_sources, dict) or not raw_sources:
            raise ProtocolValidationError("frozen schedule model source revisions are invalid")
        model_source_revisions = []
        for name, revision in raw_sources.items():
            if (
                not isinstance(name, str)
                or not name
                or not isinstance(revision, str)
                or not _IMMUTABLE_REVISION.fullmatch(revision)
            ):
                raise ProtocolValidationError("frozen schedule model source revisions are invalid")
            model_source_revisions.append((name, revision))

        selected_mapping = value.get("selected_mapping")
        if not isinstance(selected_mapping, str) or not selected_mapping:
            raise ProtocolValidationError("frozen schedule selected_mapping is invalid")
        return cls(
            harness_revision=harness_revision,
            environment_sha256=environment_sha256,
            preprocessing_revision=preprocessing_revision,
            snapshot_id=snapshot_id,
            model_source_revisions=tuple(sorted(model_source_revisions)),
            allocations=tuple(allocations),
            reserved_gpu=reserved_gpu,
            selected_mapping=selected_mapping,
            owner_attempt_id=owner_attempt_id,
            source_schedule_id=source_schedule_id,
            source_harness_revision=source_harness_revision,
        )

    def reaccept(
        self,
        *,
        source_schedule_id: str,
        harness_revision: str,
        attempt_id: str,
    ) -> FrozenSchedule:
        """Bind an unchanged frozen schedule to a clean harness and attempt."""
        if not _IMMUTABLE_REVISION.fullmatch(harness_revision):
            raise ProtocolValidationError("reaccepted harness revision is invalid")
        return FrozenSchedule(
            harness_revision=harness_revision,
            environment_sha256=self.environment_sha256,
            preprocessing_revision=self.preprocessing_revision,
            snapshot_id=self.snapshot_id,
            model_source_revisions=self.model_source_revisions,
            allocations=self.allocations,
            reserved_gpu=self.reserved_gpu,
            selected_mapping=self.selected_mapping,
            owner_attempt_id=attempt_id,
            source_schedule_id=source_schedule_id,
            source_harness_revision=self.harness_revision,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical public-safe schedule representation."""
        payload: dict[str, Any] = {
            "schema_version": 2 if self.source_schedule_id is not None else 1,
            "stage": "u7-measured-gpu-schedule",
            "schedule_state": "frozen",
            "harness_revision": self.harness_revision,
            "environment_sha256": self.environment_sha256,
            "preprocessing_revision": self.preprocessing_revision,
            "snapshot_id": self.snapshot_id,
            "model_source_revisions": dict(self.model_source_revisions),
            "selected_mapping": self.selected_mapping,
            "gpu7_reserved": True,
            "reserved_gpu": self.reserved_gpu,
            "formal_execution": {
                "mode": "formal",
                "reserved_gpu": self.reserved_gpu,
                "gpu_order": [allocation.gpu_index for allocation in self.allocations],
                "cpu_set_order": [allocation.cpu_set for allocation in self.allocations],
            },
            "mapping": {
                allocation.lane_id: {
                    "gpu": allocation.gpu_index,
                    "cpu_set": allocation.cpu_set,
                    "numa": allocation.numa_node,
                }
                for allocation in self.allocations
            },
        }
        if self.owner_attempt_id is not None:
            payload["attempt_id"] = self.owner_attempt_id
        if self.source_schedule_id is not None:
            payload["source_schedule_id"] = self.source_schedule_id
            payload["source_harness_revision"] = self.source_harness_revision
        return payload

    def allocation_for(self, lane_id: str) -> ScheduleAllocation:
        for allocation in self.allocations:
            if allocation.lane_id == lane_id:
                return allocation
        raise ProtocolValidationError(f"frozen schedule omits lane '{lane_id}'")


def validate_table1_frozen_schedule(
    schedule: FrozenSchedule,
    *,
    source_revision: str,
    attempt_id: str,
    declaration: ReproductionAttemptDeclaration | None = None,
    requested_lanes: Sequence[tuple[str, int]] | None = None,
    requested_cpu_sets: Sequence[str | None] | None = None,
    require_complete: bool = False,
) -> tuple[str, ...]:
    """Validate one Table-1 schedule against attempt declaration, revisions, and GPU policy."""
    if not isinstance(schedule, FrozenSchedule):
        raise ProtocolValidationError("schedule must be an instance of FrozenSchedule")
    if not _IMMUTABLE_REVISION.fullmatch(source_revision):
        raise ProtocolValidationError("source revision is invalid")
    if schedule.harness_revision != source_revision:
        raise ProtocolValidationError("frozen schedule harness revision does not match source")
    if schedule.owner_attempt_id is not None and schedule.owner_attempt_id != attempt_id:
        raise ProtocolValidationError("frozen schedule attempt_id does not match caller attempt")
    if schedule.preprocessing_revision != TABLE1_PREPROCESSING_REVISION:
        raise ProtocolValidationError("frozen schedule preprocessing revision is invalid")
    if schedule.reserved_gpu != TABLE1_RESERVED_GPU:
        raise ProtocolValidationError("frozen schedule must reserve GPU 7")

    allocations_by_lane = {alloc.lane_id: alloc for alloc in schedule.allocations}

    # Verify no training allocation uses reserved GPU 7
    for alloc in schedule.allocations:
        if alloc.gpu_index == TABLE1_RESERVED_GPU:
            raise ProtocolValidationError(
                f"frozen schedule assigns reserved GPU 7 to training lane '{alloc.lane_id}'"
            )

    # Check distinct GPU allocation across lanes
    allocated_gpus = [alloc.gpu_index for alloc in schedule.allocations]
    if len(allocated_gpus) != len(set(allocated_gpus)):
        raise ProtocolValidationError("frozen schedule assigns multiple lanes to the same GPU")

    if declaration is not None:
        if set(allocations_by_lane.keys()) != set(declaration.lane_ids):
            raise ProtocolValidationError(
                "frozen schedule lanes do not match reproduction attempt declaration"
            )
        schedule_sources = dict(schedule.model_source_revisions)
        for lane in declaration.lanes:
            baseline_source = lane.model_source_revision
            source_key = (
                "safedrug_archived" if lane.program_id == "safedrug-archived" else "molerec"
            )
            if (
                source_key not in schedule_sources
                or schedule_sources[source_key] != baseline_source
            ):
                raise ProtocolValidationError(
                    f"frozen schedule model source revision for '{lane.lane_id}' is mismatched"
                )

    if requested_lanes is not None:
        requested_lanes = tuple(requested_lanes)
        if require_complete and len(requested_lanes) != len(schedule.allocations):
            raise ProtocolValidationError("formal run requires every frozen schedule lane")
        cpu_sets_input = (
            tuple(requested_cpu_sets)
            if requested_cpu_sets is not None
            else tuple(None for _ in requested_lanes)
        )
        if len(requested_lanes) != len(cpu_sets_input):
            raise ProtocolValidationError("requested lanes and cpu sets length mismatch")

        resolved_cpu_sets: list[str] = []
        for (lane_id, gpu_index), explicit_cpu_set in zip(
            requested_lanes, cpu_sets_input, strict=True
        ):
            if lane_id not in allocations_by_lane:
                raise ProtocolValidationError(f"frozen schedule omits requested lane '{lane_id}'")
            alloc = allocations_by_lane[lane_id]
            if gpu_index != alloc.gpu_index:
                raise ProtocolValidationError(
                    f"lane '{lane_id}' requested GPU {gpu_index} does not match schedule GPU {alloc.gpu_index}"
                )
            if gpu_index == TABLE1_RESERVED_GPU:
                raise ProtocolValidationError(
                    f"lane '{lane_id}' cannot run on reserved GPU {TABLE1_RESERVED_GPU}"
                )
            if explicit_cpu_set is not None:
                validated_explicit = _validate_cpu_set_syntax(explicit_cpu_set)
                if validated_explicit != alloc.cpu_set:
                    raise ProtocolValidationError(
                        f"lane '{lane_id}' CPU set '{explicit_cpu_set}' does not match schedule CPU set '{alloc.cpu_set}'"
                    )
            resolved_cpu_sets.append(alloc.cpu_set)
        return tuple(resolved_cpu_sets)

    return tuple(alloc.cpu_set for alloc in schedule.allocations)


def validate_reproduction_continuation(
    *,
    declaration: ReproductionAttemptDeclaration | None = None,
    registry: BaselineRegistry | None = None,
    source_schedule: FrozenSchedule,
    source_schedule_id: str,
    attempt_root: str | Path,
    attempt_id: str,
    training_artifact_ids: Mapping[str, str],
    harness_revision: str,
) -> FrozenSchedule:
    """Prove recovered training evidence before reaccepting one frozen schedule."""
    if declaration is None:
        if registry is None:
            raise ProtocolValidationError("either declaration or registry is required")
        declaration = ReproductionAttemptDeclaration.from_registry(registry, attempt_id)

    lane_ids = declaration.lane_ids
    if set(training_artifact_ids) != set(lane_ids):
        raise ProtocolValidationError(
            "continuation admission requires exactly the declared training artifacts"
        )
    if len(set(training_artifact_ids.values())) != len(lane_ids):
        raise ProtocolValidationError("continuation training artifacts must be unique")

    requested_lanes = tuple(
        (allocation.lane_id, allocation.gpu_index) for allocation in source_schedule.allocations
    )
    validate_table1_frozen_schedule(
        source_schedule,
        source_revision=source_schedule.harness_revision,
        attempt_id=attempt_id,
        declaration=declaration,
        requested_lanes=requested_lanes,
        requested_cpu_sets=tuple(allocation.cpu_set for allocation in source_schedule.allocations),
        require_complete=True,
    )

    submission_ids: set[str] = set()
    for lane in declaration.lanes:
        training_root, source_root, _ = resolve_training_artifact(
            attempt_root,
            training_artifact_ids[lane.lane_id],
        )
        if source_root is None:
            raise ProtocolValidationError(
                f"continuation lane '{lane.lane_id}' must use recovered training evidence"
            )
        try:
            recovery_roots = tuple(
                child.resolve()
                for child in source_root.joinpath("recoveries").iterdir()
                if child.is_dir()
            )
        except OSError as error:
            raise ProtocolValidationError(
                f"continuation lane '{lane.lane_id}' recovery namespace cannot be read"
            ) from error
        if recovery_roots != (training_root.resolve(),):
            raise ProtocolValidationError(
                f"continuation lane '{lane.lane_id}' must have exactly its declared recovery"
            )

        evidence = reopen_training_evidence(
            training_root,
            source_run_root=source_root,
        )
        identity = evidence["identity"]
        expected = {
            "attempt_id": attempt_id,
            "lane_id": lane.lane_id,
            "scientific_baseline_id": lane.scientific_baseline_id,
            "program_id": lane.program_id,
            "profile_id": lane.profile_id,
            "harness_revision": source_schedule.harness_revision,
            "model_source_revision": lane.model_source_revision,
            "preprocessing_revision": source_schedule.preprocessing_revision,
            "snapshot_id": source_schedule.snapshot_id,
            "environment_sha256": source_schedule.environment_sha256,
            "mode": "formal",
        }
        if any(identity.get(field) != value for field, value in expected.items()):
            raise ProtocolValidationError(
                f"continuation lane '{lane.lane_id}' evidence identity is not authoritative"
            )
        submission_id = identity["submission_id"]
        if submission_id in submission_ids:
            raise ProtocolValidationError("continuation training submissions must be unique")
        submission_ids.add(submission_id)

    continuation = source_schedule.reaccept(
        source_schedule_id=source_schedule_id,
        harness_revision=harness_revision,
        attempt_id=attempt_id,
    )
    validate_table1_frozen_schedule(
        continuation,
        source_revision=harness_revision,
        attempt_id=attempt_id,
        declaration=declaration,
        requested_lanes=requested_lanes,
        requested_cpu_sets=tuple(allocation.cpu_set for allocation in continuation.allocations),
        require_complete=True,
    )
    return continuation


def build_table1_test_launch_command(
    declaration: ReproductionAttemptDeclaration,
    lane_id: str,
    *,
    attempt_id: str,
    submission_id: str,
    harness_revision: str,
    remote_root: str,
    data_root: str,
    recovery_run_root: str,
    training_source_root: str,
    test_root: str,
    selection_path: str | None = None,
) -> str:
    """Build one source-native GPU 7 test command for a Table-1 recovered lane."""
    lane = declaration.get_lane(lane_id)
    require_identifier(attempt_id, field="attempt_id")
    require_identifier(submission_id, field="submission_id")
    if not _IMMUTABLE_REVISION.fullmatch(harness_revision):
        raise ProtocolValidationError("formal test harness revision is invalid")

    remote_root = _remote_posix_path(remote_root, field="remote_root")
    data_root = _remote_posix_path(data_root, field="data_root")
    recovery_run_root = _remote_posix_path(recovery_run_root, field="recovery_run_root")
    training_source_root = _remote_posix_path(training_source_root, field="training_source_root")
    test_root = _remote_posix_path(test_root, field="test_root")

    if lane_id.startswith("molerec-safedrug"):
        if selection_path is None:
            raise ProtocolValidationError("SafeDrug formal test requires selection.json")
        selection_path = _remote_posix_path(selection_path, field="selection_path")
    elif selection_path is not None:
        raise ProtocolValidationError("only SafeDrug formal test accepts selection.json")

    dataset_root = str(PurePosixPath(data_root) / lane.dataset_subdirectory)
    program_path = str(PurePosixPath(remote_root) / lane.entrypoint)
    conda_env = "medrec-molerec-table1"

    argv = [
        "taskset",
        "--cpu-list",
        TABLE1_TEST_CPU_SET,
        "env",
        f"MEDREC_RUN_ID={submission_id}",
        f"MEDREC_ATTEMPT_ID={attempt_id}",
        f"MEDREC_LANE_ID={lane.lane_id}",
        f"MEDREC_BASELINE_ID={lane.scientific_baseline_id}",
        f"MEDREC_PROGRAM_ID={lane.program_id}",
        f"MEDREC_PROFILE_ID={lane.profile_id}",
        f"MEDREC_HARNESS_REVISION={harness_revision}",
        f"MEDREC_MODEL_SOURCE_REVISION={lane.model_source_revision}",
        f"MEDREC_PREPROCESSING_REVISION={TABLE1_PREPROCESSING_REVISION}",
        f"MEDREC_SNAPSHOT_ID={lane.dataset_subdirectory}",
        f"MEDREC_ENVIRONMENT_SHA256={lane.environment_sha256}",
        f"MEDREC_SUBMISSION_ID={submission_id}",
        "MEDREC_MODE=formal",
        f"MEDREC_DATA_ROOT={data_root}",
        f"SAFEDRUG_ROOT={lane.upstream_root}",
        f"CUDA_VISIBLE_DEVICES={TABLE1_RESERVED_GPU}",
        f"CONDA_ENV={conda_env}",
        "/root/anaconda3/bin/conda",
        "run",
        "--no-capture-output",
        "-n",
        conda_env,
        "python",
        program_path,
        lane.profile_id,
        "--upstream-root",
        lane.upstream_root,
        "--dataset-root",
        dataset_root,
        "--run-root",
        recovery_run_root,
        "--phase",
        "test",
        "--training-source-root",
        training_source_root,
        "--test-root",
        test_root,
    ]
    if lane.learning_rate is not None:
        argv.extend(["--learning-rate", str(lane.learning_rate)])
    if selection_path is not None:
        argv.extend(["--selection", selection_path])

    command = shlex.join(argv)
    return f"cd {shlex.quote(remote_root)} && {command}"


__all__ = (
    "TABLE1_DECLARATION_KIND",
    "TABLE1_DECLARATION_SCHEMA_VERSION",
    "TABLE1_FIXED_TEST_LANES",
    "TABLE1_PAPER_BASELINES",
    "TABLE1_PREPROCESSING_REVISION",
    "TABLE1_RESERVED_GPU",
    "TABLE1_TEST_CPU_SET",
    "FrozenSchedule",
    "ReproductionAttemptDeclaration",
    "ReproductionLaneDeclaration",
    "ScheduleAllocation",
    "build_table1_test_launch_command",
    "validate_reproduction_continuation",
    "validate_table1_frozen_schedule",
)
