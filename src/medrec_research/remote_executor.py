"""Fail-closed SSH and tmux submission for approved 319 baseline runs."""

from __future__ import annotations

import json
import re
import secrets
import shlex
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from ._validation import require_int
from .errors import ProtocolValidationError
from .evaluation_queue import resolve_training_artifact
from .registry import (
    BaselineDefinition,
    BaselineRegistry,
    ReproductionProgram,
    ResearchMode,
    SourceStatus,
)
from .reproduction_evidence import reopen_training_evidence

APPROVED_319_HOSTS = ("319-lab", "319-lab-via-server")
PREPROCESSING_REVISION = "c7218d0976e5ee5588aeaf5bdbc86b338126bba5"
MAX_SHARED_GPU_UTILIZATION_PERCENT = 10.0
_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40,64}")
_PUBLIC_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")
_GPU_UUID = re.compile(r"GPU-[A-Za-z0-9-]+")
_CPU_SET = re.compile(r"(?:[0-9]+(?:-[0-9]+)?)(?:,(?:[0-9]+(?:-[0-9]+)?))*")

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class SSHConfig:
    """Fixed OpenSSH policy for the approved 319 aliases."""

    hosts: tuple[str, ...] = APPROVED_319_HOSTS
    connect_timeout_seconds: int = 10
    command_timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if not self.hosts or any(host not in APPROVED_319_HOSTS for host in self.hosts):
            raise ProtocolValidationError("SSH hosts must use an approved 319 alias")
        require_int(
            self.connect_timeout_seconds,
            field="connect_timeout_seconds",
            minimum=1,
        )
        require_int(
            self.command_timeout_seconds,
            field="command_timeout_seconds",
            minimum=1,
        )


@dataclass(frozen=True, slots=True)
class PreflightResult:
    """Public-safe identifiers verified immediately before submission."""

    host: str
    baseline_id: str
    source_revision: str
    environment_sha256: str
    gpu_index: int
    cpu_set: str | None = None


@dataclass(frozen=True, slots=True)
class RemoteSubmission:
    """Public-safe description of a planned or submitted baseline run."""

    baseline_id: str
    host: str | None
    session_id: str
    command: str
    preflight_performed: bool
    attempt_id: str | None = None
    lane_id: str | None = None
    submission_id: str | None = None
    cpu_set: str | None = None


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
        if self.reserved_gpu != 7:
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
        expected_lane_ids: Sequence[str],
    ) -> FrozenSchedule:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ProtocolValidationError("frozen schedule artifact could not be read") from error
        return cls.from_dict(payload, expected_lane_ids=expected_lane_ids)

    @classmethod
    def from_dict(
        cls,
        value: object,
        *,
        expected_lane_ids: Sequence[str],
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

        expected_lane_ids = tuple(expected_lane_ids)
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
        if reserved_gpu != 7 or value.get("reserved_gpu", reserved_gpu) != 7:
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

    def to_dict(self) -> dict[str, object]:
        """Return the canonical public-safe schedule representation."""
        payload: dict[str, object] = {
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


def validate_reproduction_continuation(
    *,
    registry: BaselineRegistry,
    source_schedule: FrozenSchedule,
    source_schedule_id: str,
    attempt_root: str | Path,
    attempt_id: str,
    training_artifact_ids: Mapping[str, str],
    harness_revision: str,
) -> FrozenSchedule:
    """Prove recovered training evidence before reaccepting one frozen schedule."""
    executor = RemoteExecutor(registry)
    lane_ids = tuple(lane.lane_id for lane in registry.reproduction_lanes)
    if set(training_artifact_ids) != set(lane_ids):
        raise ProtocolValidationError(
            "continuation admission requires exactly the seven declared training artifacts"
        )
    if len(set(training_artifact_ids.values())) != len(lane_ids):
        raise ProtocolValidationError("continuation training artifacts must be unique")

    requested_lanes = tuple(
        (allocation.lane_id, allocation.gpu_index) for allocation in source_schedule.allocations
    )
    executor.validate_frozen_schedule(
        source_schedule,
        source_revision=source_schedule.harness_revision,
        attempt_id=attempt_id,
        requested_lanes=requested_lanes,
        requested_cpu_sets=tuple(allocation.cpu_set for allocation in source_schedule.allocations),
        require_complete=True,
    )

    submission_ids: set[str] = set()
    for lane in registry.reproduction_lanes:
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
        baseline = registry.get(lane.scientific_baseline_id)
        expected = {
            "attempt_id": attempt_id,
            "lane_id": lane.lane_id,
            "scientific_baseline_id": lane.scientific_baseline_id,
            "program_id": lane.program_id,
            "profile_id": lane.profile_id,
            "harness_revision": source_schedule.harness_revision,
            "model_source_revision": baseline.source.revision,
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
    executor.validate_frozen_schedule(
        continuation,
        source_revision=harness_revision,
        attempt_id=attempt_id,
        requested_lanes=requested_lanes,
        requested_cpu_sets=tuple(allocation.cpu_set for allocation in continuation.allocations),
        require_complete=True,
    )
    return continuation


class RemoteExecutor:
    """Preflight and submit declared baselines on the approved 319 host."""

    def __init__(
        self,
        registry: BaselineRegistry,
        ssh_config: SSHConfig | None = None,
        *,
        runner: Runner = subprocess.run,
    ) -> None:
        self.registry = registry
        self.ssh_config = ssh_config or SSHConfig()
        self._runner = runner

    def ssh(self, host: str, command: str, *, gate: str) -> str:
        """Run one public-safe preflight or tmux command through OpenSSH."""
        if host not in self.ssh_config.hosts or host not in APPROVED_319_HOSTS:
            raise ProtocolValidationError("remote host must use an approved 319 alias")
        argv = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={self.ssh_config.connect_timeout_seconds}",
            "-o",
            "StrictHostKeyChecking=yes",
            host,
            command,
        ]
        try:
            completed = self._runner(
                argv,
                capture_output=True,
                text=True,
                timeout=self.ssh_config.command_timeout_seconds,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise ProtocolValidationError(f"remote {gate} check failed") from error
        if completed.returncode != 0:
            raise ProtocolValidationError(f"remote {gate} check failed")
        return completed.stdout.strip()

    def preflight(
        self,
        baseline_id: str,
        *,
        source_revision: str,
        gpu_index: int,
        remote_root: str,
        data_root: str,
        min_free_gpu_mib: int,
        min_free_disk_gib: int,
        cpu_set: str | None = None,
    ) -> PreflightResult:
        """Run every required read-only check and return verified identifiers."""
        cpu_set = self._validate_cpu_set(cpu_set)
        baseline, program, profile_id, _, _ = self._resolve_target(baseline_id)
        remote_root, data_root = self._validate_launch_paths(
            baseline,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
        )
        host = self._select_host()

        quoted_remote_root = shlex.quote(remote_root)
        if self.ssh(
            host,
            f"git -C {quoted_remote_root} status --porcelain --untracked-files=all",
            gate="source-clean",
        ):
            raise ProtocolValidationError("remote source-clean check failed")
        observed_revision = self.ssh(
            host,
            f"git -C {quoted_remote_root} rev-parse HEAD",
            gate="source-revision",
        )
        if observed_revision != source_revision:
            raise ProtocolValidationError("remote source-revision check failed")

        quoted_data_root = shlex.quote(data_root)
        data_check = (
            f"test -d {quoted_data_root} && "
            f"data_real=$(realpath -- {quoted_data_root}) && "
            f"repo_real=$(realpath -- {quoted_remote_root}) && "
            'case "$data_real/" in "$repo_real/"*) exit 1;; esac && printf ok'
        )
        if self.ssh(host, data_check, gate="data-root") != "ok":
            raise ProtocolValidationError("remote data-root check failed")

        dataset_root = PurePosixPath(data_root) / program.dataset_subdirectory
        if (
            self.ssh(
                host,
                f"test -d {shlex.quote(str(dataset_root))} && printf ok",
                gate="data-input",
            )
            != "ok"
        ):
            raise ProtocolValidationError("remote data-input check failed")

        program_path = PurePosixPath(remote_root) / program.entrypoint
        if (
            self.ssh(
                host,
                f"test -f {shlex.quote(str(program_path))} && printf ok",
                gate="program",
            )
            != "ok"
        ):
            raise ProtocolValidationError("remote Reproduction Program check failed")
        quoted_upstream_root = shlex.quote(program.upstream_root)
        upstream_clean_cmd = f"git -c safe.directory={quoted_upstream_root} -C {quoted_upstream_root} status --porcelain --untracked-files=no"
        if self.ssh(
            host,
            upstream_clean_cmd,
            gate="baseline-source-clean",
        ):
            raise ProtocolValidationError("remote baseline-source-clean check failed")
        observed_baseline_revision = self.ssh(
            host,
            f"git -c safe.directory={quoted_upstream_root} -C {quoted_upstream_root} rev-parse HEAD",
            gate="baseline-source-revision",
        )
        if observed_baseline_revision != baseline.source.revision:
            raise ProtocolValidationError("remote baseline-source-revision check failed")

        inputs_check_cmd = (
            " && ".join(
                f"test -f {shlex.quote(str(dataset_root / name))} && "
                f"! test -L {shlex.quote(str(dataset_root / name))}"
                for name in program.required_inputs
            )
            + " && printf ok"
        )
        if self.ssh(host, inputs_check_cmd, gate="baseline-inputs") != "ok":
            raise ProtocolValidationError("remote baseline required input files check failed")

        environment_command = (
            "source /root/anaconda3/etc/profile.d/conda.sh && "
            f"conda list --explicit -n {shlex.quote(program.conda_environment)} | "
            "sha256sum | awk '{print $1}'"
        )
        observed_environment = self.ssh(host, environment_command, gate="environment")
        if observed_environment != program.environment_sha256:
            raise ProtocolValidationError("remote environment check failed")

        gpu_output = self.ssh(
            host,
            f"nvidia-smi --id={gpu_index} "
            "--query-gpu=index,uuid,memory.free,utilization.gpu "
            "--format=csv,noheader,nounits",
            gate="gpu",
        )
        self._validate_gpu(
            gpu_output,
            gpu_index=gpu_index,
            min_free_gpu_mib=min_free_gpu_mib,
        )

        disk_output = self.ssh(
            host,
            f"df -Pk {quoted_data_root} | awk 'NR==2 {{print $4}}'",
            gate="disk",
        )
        try:
            free_disk_kib = int(disk_output.strip())
        except ValueError as error:
            raise ProtocolValidationError("remote disk report is invalid") from error
        if free_disk_kib < min_free_disk_gib * 1024 * 1024:
            raise ProtocolValidationError("remote disk capacity is insufficient")

        program_invocation = (
            f"taskset --cpu-list {shlex.quote(cpu_set)} env " if cpu_set is not None else ""
        )
        program_probe_cmd = (
            "source /root/anaconda3/etc/profile.d/conda.sh && "
            f"conda activate {shlex.quote(program.conda_environment)} && "
            f"{program_invocation}CUDA_VISIBLE_DEVICES={gpu_index} python {shlex.quote(str(program_path))} "
            f"{shlex.quote(profile_id)} "
            f"--upstream-root {quoted_upstream_root} "
            f"--dataset-root {shlex.quote(str(dataset_root))} "
            "--mode probe --probe-scope full"
        )
        probe_raw = self.ssh(host, program_probe_cmd, gate="program-probe")
        self._validate_program_probe(
            probe_raw,
            baseline=baseline,
            program=program,
            expected_environment_sha256=observed_environment,
            profile_id=profile_id,
        )

        return PreflightResult(
            host=host,
            baseline_id=baseline.baseline_id,
            source_revision=source_revision,
            environment_sha256=observed_environment,
            gpu_index=gpu_index,
            cpu_set=cpu_set,
        )

    def run_baseline(
        self,
        baseline_id: str,
        *,
        source_revision: str,
        gpu_index: int,
        remote_root: str,
        data_root: str,
        min_free_gpu_mib: int,
        min_free_disk_gib: int,
        dry_run: bool = False,
        attempt_id: str | None = None,
        cpu_set: str | None = None,
        schedule: FrozenSchedule | None = None,
    ) -> RemoteSubmission:
        """Validate, preflight, and submit one declared Reproduction Mode formal run."""
        cpu_set = self._validate_cpu_set(cpu_set)
        baseline, program, profile_id, learning_rate, lane_id = self._resolve_target(baseline_id)
        successor_lane_ids = {lane.lane_id for lane in self.registry.reproduction_lanes}
        active_attempt_id = attempt_id or f"attempt-{self._timestamp()}-{secrets.token_hex(4)}"
        self._validate_job_id(active_attempt_id)
        if lane_id in successor_lane_ids:
            if schedule is None:
                raise ProtocolValidationError(
                    "formal successor reproduction lanes require a frozen schedule"
                )
            cpu_set = self.validate_frozen_schedule(
                schedule,
                source_revision=source_revision,
                attempt_id=active_attempt_id,
                requested_lanes=((lane_id, gpu_index),),
                requested_cpu_sets=(cpu_set,),
                require_complete=False,
            )[0]
        elif schedule is not None:
            raise ProtocolValidationError("frozen schedule applies only to successor lanes")
        remote_root, data_root = self._validate_launch_paths(
            baseline,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
            require_verified=not dry_run,
            program=program,
        )
        session_id = f"medrec-baseline-{baseline_id}-{self._timestamp()}-{secrets.token_hex(4)}"
        command = self._launch_command(
            program,
            baseline_id=baseline.baseline_id,
            profile_id=profile_id,
            learning_rate=learning_rate,
            remote_root=remote_root,
            data_root=data_root,
            gpu_index=gpu_index,
            run_id=session_id,
            mode="formal",
            attempt_id=active_attempt_id,
            lane_id=lane_id,
            harness_revision=source_revision,
            model_source_revision=baseline.source.revision,
            environment_sha256=program.environment_sha256 or "unverified",
            cpu_set=cpu_set,
        )
        if dry_run:
            return RemoteSubmission(
                baseline_id=baseline_id,
                host=None,
                session_id=session_id,
                command=command,
                preflight_performed=False,
                attempt_id=active_attempt_id,
                lane_id=lane_id,
                submission_id=session_id,
                cpu_set=cpu_set,
            )

        result = self.preflight(
            baseline_id,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
            cpu_set=cpu_set,
        )

        command = self._launch_command(
            program,
            baseline_id=baseline.baseline_id,
            profile_id=profile_id,
            learning_rate=learning_rate,
            remote_root=remote_root,
            data_root=data_root,
            gpu_index=gpu_index,
            run_id=session_id,
            mode="formal",
            attempt_id=active_attempt_id,
            lane_id=lane_id,
            harness_revision=source_revision,
            model_source_revision=baseline.source.revision,
            environment_sha256=result.environment_sha256,
            cpu_set=cpu_set,
        )
        try:
            self.ssh(
                result.host,
                f"tmux new-session -d -s {shlex.quote(session_id)} {shlex.quote(command)}",
                gate="tmux-launch",
            )
        except ProtocolValidationError:
            self._cleanup_session(session_id, host=result.host)
            raise
        return RemoteSubmission(
            baseline_id=baseline_id,
            host=result.host,
            session_id=session_id,
            command=command,
            preflight_performed=True,
            attempt_id=active_attempt_id,
            lane_id=lane_id,
            submission_id=session_id,
            cpu_set=cpu_set,
        )

    def test_launch_command(
        self,
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
        """Build one source-native GPU 7 test command for a recovered lane."""
        declared_lanes = {lane.lane_id for lane in self.registry.reproduction_lanes}
        if lane_id not in declared_lanes:
            raise ProtocolValidationError("formal test requires a declared successor lane")
        baseline, program, profile_id, learning_rate, _ = self._resolve_target(lane_id)
        self._validate_job_id(attempt_id)
        self._validate_job_id(submission_id)
        if not _IMMUTABLE_REVISION.fullmatch(harness_revision):
            raise ProtocolValidationError("formal test harness revision is invalid")
        remote_root = self._remote_path(remote_root, field="remote_root")
        data_root = self._remote_path(data_root, field="data_root")
        recovery_run_root = self._remote_path(
            recovery_run_root,
            field="recovery_run_root",
        )
        training_source_root = self._remote_path(
            training_source_root,
            field="training_source_root",
        )
        test_root = self._remote_path(test_root, field="test_root")
        if lane_id.startswith("molerec-safedrug"):
            if selection_path is None:
                raise ProtocolValidationError("SafeDrug formal test requires selection.json")
            selection_path = self._remote_path(selection_path, field="selection_path")
        elif selection_path is not None:
            raise ProtocolValidationError("only SafeDrug formal test accepts selection.json")
        return self._launch_command(
            program,
            baseline_id=baseline.baseline_id,
            profile_id=profile_id,
            learning_rate=learning_rate,
            remote_root=remote_root,
            data_root=data_root,
            gpu_index=7,
            run_id=submission_id,
            mode="formal",
            phase="test",
            attempt_id=attempt_id,
            lane_id=lane_id,
            harness_revision=harness_revision,
            model_source_revision=baseline.source.revision,
            environment_sha256=program.environment_sha256 or "unverified",
            cpu_set="28-31,60-63",
            run_root_override=recovery_run_root,
            training_source_root=training_source_root,
            test_root=test_root,
            selection_path=selection_path,
        )

    def validate_frozen_schedule(
        self,
        schedule: FrozenSchedule,
        *,
        source_revision: str,
        attempt_id: str,
        requested_lanes: Sequence[tuple[str, int]],
        requested_cpu_sets: Sequence[str | None],
        require_complete: bool,
    ) -> tuple[str, ...]:
        """Validate an accepted schedule and resolve requested CPU affinities."""
        if not isinstance(schedule, FrozenSchedule):
            raise ProtocolValidationError("frozen schedule must be a validated artifact")
        if schedule.reserved_gpu != 7:
            raise ProtocolValidationError("frozen schedule must reserve GPU 7")
        expected_lanes = tuple(lane.lane_id for lane in self.registry.reproduction_lanes)
        if not expected_lanes or len(expected_lanes) != len(set(expected_lanes)):
            raise ProtocolValidationError("registry must declare unique successor lanes")
        if tuple(allocation.lane_id for allocation in schedule.allocations) != expected_lanes:
            raise ProtocolValidationError("frozen schedule lane order does not match the registry")
        if schedule.owner_attempt_id is not None and schedule.owner_attempt_id != attempt_id:
            raise ProtocolValidationError("frozen schedule belongs to a different attempt")
        if schedule.harness_revision != source_revision:
            raise ProtocolValidationError("frozen schedule harness revision does not match attempt")
        if schedule.preprocessing_revision != PREPROCESSING_REVISION:
            raise ProtocolValidationError("frozen schedule preprocessing revision is not accepted")

        expected_environment: str | None = None
        expected_snapshot: str | None = None
        expected_sources: dict[str, str] = {}
        for lane in self.registry.reproduction_lanes:
            baseline = self.registry.get(lane.scientific_baseline_id)
            program = self.registry.get_program(lane.program_id)
            if program.environment_sha256 is None or baseline.source.revision is None:
                raise ProtocolValidationError("frozen schedule requires verified lane identities")
            if expected_environment is None:
                expected_environment = program.environment_sha256
            elif program.environment_sha256 != expected_environment:
                raise ProtocolValidationError(
                    "frozen schedule requires one environment identity for all lanes"
                )
            if expected_snapshot is None:
                expected_snapshot = program.dataset_subdirectory
            elif program.dataset_subdirectory != expected_snapshot:
                raise ProtocolValidationError(
                    "frozen schedule requires one dataset snapshot for all lanes"
                )
            source_key = (
                "safedrug_archived"
                if program.program_id == "safedrug-archived"
                else "molerec"
                if program.program_id == "molerec"
                else program.program_id
            )
            previous_revision = expected_sources.setdefault(source_key, baseline.source.revision)
            if previous_revision != baseline.source.revision:
                raise ProtocolValidationError(
                    "frozen schedule model source revisions are ambiguous"
                )
        if schedule.environment_sha256 != expected_environment:
            raise ProtocolValidationError(
                "frozen schedule environment hash does not match registry"
            )
        if schedule.snapshot_id != expected_snapshot:
            raise ProtocolValidationError("frozen schedule snapshot does not match registry")
        if schedule.model_source_revisions != tuple(sorted(expected_sources.items())):
            raise ProtocolValidationError("frozen schedule model sources do not match registry")

        seen_gpus: set[int] = set()
        seen_cpus: set[int] = set()
        for allocation in schedule.allocations:
            if allocation.gpu_index == schedule.reserved_gpu:
                raise ProtocolValidationError("frozen schedule assigns the reserved GPU")
            if allocation.gpu_index in seen_gpus:
                raise ProtocolValidationError("frozen schedule assigns a GPU more than once")
            seen_gpus.add(allocation.gpu_index)
            self._validate_cpu_set(allocation.cpu_set)
            cpu_values = self._cpu_set_values(allocation.cpu_set)
            if seen_cpus.intersection(cpu_values):
                raise ProtocolValidationError("frozen schedule CPU sets overlap")
            seen_cpus.update(cpu_values)

        if len(requested_lanes) != len(requested_cpu_sets):
            raise ProtocolValidationError("requested schedule lanes and CPU sets must align")
        requested_ids = tuple(lane_id for lane_id, _ in requested_lanes)
        if len(requested_ids) != len(set(requested_ids)):
            raise ProtocolValidationError("formal submission contains duplicate lanes")
        requested_gpus = tuple(gpu for _, gpu in requested_lanes)
        if len(requested_gpus) != len(set(requested_gpus)):
            raise ProtocolValidationError("formal submission contains duplicate GPUs")
        if require_complete and set(requested_ids) != set(expected_lanes):
            raise ProtocolValidationError(
                "formal submission must include every frozen schedule lane"
            )

        resolved_cpu_sets: list[str] = []
        for (lane_id, gpu_index), requested_cpu_set in zip(
            requested_lanes, requested_cpu_sets, strict=True
        ):
            allocation = schedule.allocation_for(lane_id)
            if gpu_index != allocation.gpu_index:
                raise ProtocolValidationError(
                    f"GPU allocation for lane '{lane_id}' differs from frozen schedule"
                )
            if requested_cpu_set is not None:
                self._validate_cpu_set(requested_cpu_set)
                if requested_cpu_set != allocation.cpu_set:
                    raise ProtocolValidationError(
                        f"CPU allocation for lane '{lane_id}' differs from frozen schedule"
                    )
            resolved_cpu_sets.append(allocation.cpu_set)
        return tuple(resolved_cpu_sets)

    def run_smoke(
        self,
        baseline_id: str,
        *,
        source_revision: str,
        gpu_index: int,
        remote_root: str,
        data_root: str,
        min_free_gpu_mib: int,
        min_free_disk_gib: int,
        dry_run: bool = False,
        attempt_id: str | None = None,
        cpu_set: str | None = None,
    ) -> RemoteSubmission:
        """Validate, preflight, and submit one declared Reproduction Mode smoke run."""
        cpu_set = self._validate_cpu_set(cpu_set)
        baseline, program, profile_id, learning_rate, lane_id = self._resolve_target(baseline_id)
        remote_root, data_root = self._validate_launch_paths(
            baseline,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
            require_verified=not dry_run,
            program=program,
        )
        active_attempt_id = attempt_id or f"attempt-{self._timestamp()}-{secrets.token_hex(4)}"
        self._validate_job_id(active_attempt_id)
        session_id = f"medrec-smoke-{baseline_id}-{self._timestamp()}-{secrets.token_hex(4)}"
        command = self._launch_command(
            program,
            baseline_id=baseline.baseline_id,
            profile_id=profile_id,
            learning_rate=learning_rate,
            remote_root=remote_root,
            data_root=data_root,
            gpu_index=gpu_index,
            run_id=session_id,
            mode="smoke",
            attempt_id=active_attempt_id,
            lane_id=lane_id,
            harness_revision=source_revision,
            model_source_revision=baseline.source.revision,
            environment_sha256=program.environment_sha256 or "unverified",
            cpu_set=cpu_set,
        )
        if dry_run:
            return RemoteSubmission(
                baseline_id=baseline_id,
                host=None,
                session_id=session_id,
                command=command,
                preflight_performed=False,
                attempt_id=active_attempt_id,
                lane_id=lane_id,
                submission_id=session_id,
                cpu_set=cpu_set,
            )

        result = self.preflight(
            baseline_id,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
            cpu_set=cpu_set,
        )
        command = self._launch_command(
            program,
            baseline_id=baseline.baseline_id,
            profile_id=profile_id,
            learning_rate=learning_rate,
            remote_root=remote_root,
            data_root=data_root,
            gpu_index=gpu_index,
            run_id=session_id,
            mode="smoke",
            attempt_id=active_attempt_id,
            lane_id=lane_id,
            harness_revision=source_revision,
            model_source_revision=baseline.source.revision,
            environment_sha256=result.environment_sha256,
            cpu_set=cpu_set,
        )
        try:
            self.ssh(
                result.host,
                f"tmux new-session -d -s {shlex.quote(session_id)} {shlex.quote(command)}",
                gate="tmux-launch",
            )
        except ProtocolValidationError:
            self._cleanup_session(session_id, host=result.host)
            raise
        return RemoteSubmission(
            baseline_id=baseline_id,
            host=result.host,
            session_id=session_id,
            command=command,
            preflight_performed=True,
            attempt_id=active_attempt_id,
            lane_id=lane_id,
            submission_id=session_id,
            cpu_set=cpu_set,
        )

    def _resolve_target(
        self, baseline_or_lane_id: str
    ) -> tuple[BaselineDefinition, ReproductionProgram, str, float | None, str]:
        try:
            lane = self.registry.get_lane(baseline_or_lane_id)
            baseline = self.registry.get(lane.scientific_baseline_id)
            program = self.registry.get_program(lane.program_id)
            return baseline, program, lane.profile_id, lane.learning_rate, lane.lane_id
        except KeyError:
            pass
        baseline = self._baseline(baseline_or_lane_id)
        program = self.registry.reproduction_program_for(baseline)
        return baseline, program, baseline.baseline_id, None, baseline.baseline_id

    def _baseline(self, baseline_id: str) -> BaselineDefinition:
        try:
            return self.registry.get(baseline_id)
        except KeyError as error:
            raise ProtocolValidationError(f"baseline '{baseline_id}' is not registered") from error

    def _cleanup_session(self, session_id: str, *, host: str) -> bool:
        """Best-effort cleanup when a newly created session fails to launch."""
        self._validate_job_id(session_id)
        try:
            self.ssh(
                host,
                f"tmux kill-session -t {shlex.quote(session_id)}",
                gate="tmux-cleanup",
            )
        except ProtocolValidationError:
            return False
        return True

    def _select_host(self) -> str:
        for host in self.ssh_config.hosts:
            try:
                identity = self.ssh(host, "id -un", gate="identity")
            except ProtocolValidationError:
                continue
            if identity == "root":
                return host
        raise ProtocolValidationError("remote identity check failed for approved 319 aliases")

    def _validate_launch_paths(
        self,
        baseline: BaselineDefinition,
        *,
        source_revision: str,
        gpu_index: int,
        remote_root: str,
        data_root: str,
        min_free_gpu_mib: int,
        min_free_disk_gib: int,
        require_verified: bool = True,
        program: ReproductionProgram | None = None,
    ) -> tuple[str, str]:
        prog = program or self.registry.reproduction_program_for(baseline)
        if ResearchMode.REPRODUCTION not in baseline.supported_modes:
            raise ProtocolValidationError("remote submission supports Reproduction Mode only")
        if not _IMMUTABLE_REVISION.fullmatch(source_revision):
            raise ProtocolValidationError("source_revision must be an immutable Git revision")
        require_int(gpu_index, field="gpu_index")
        require_int(min_free_gpu_mib, field="min_free_gpu_mib", minimum=1)
        require_int(min_free_disk_gib, field="min_free_disk_gib", minimum=1)
        remote_root = self._remote_path(remote_root, field="remote_root")
        data_root = self._remote_path(data_root, field="data_root")
        repository_path = PurePosixPath(remote_root)
        data_path = PurePosixPath(data_root)
        if data_path == repository_path or repository_path in data_path.parents:
            raise ProtocolValidationError("data_root must be outside remote_root")
        self._validate_declaration(baseline, prog, require_verified=require_verified)
        return remote_root, data_root

    @staticmethod
    def _validate_declaration(
        baseline: BaselineDefinition,
        program: ReproductionProgram,
        *,
        require_verified: bool,
    ) -> None:
        if baseline.source.status is not SourceStatus.PINNED or not baseline.source.revision:
            raise ProtocolValidationError("reproduction launch requires a pinned baseline source")
        if not _IMMUTABLE_REVISION.fullmatch(baseline.source.revision):
            raise ProtocolValidationError(
                "baseline source revision must be an immutable Git revision"
            )
        if require_verified and not program.is_319_verified:
            raise ProtocolValidationError(
                "real reproduction requires a verified environment_sha256"
            )

    @staticmethod
    def _validate_program_probe(
        probe_raw: str,
        *,
        baseline: BaselineDefinition,
        program: ReproductionProgram,
        expected_environment_sha256: str,
        profile_id: str | None = None,
    ) -> None:
        try:
            data = json.loads(probe_raw)
        except (json.JSONDecodeError, TypeError) as error:
            raise ProtocolValidationError(
                "remote program probe output is not valid JSON"
            ) from error
        if not isinstance(data, dict):
            raise ProtocolValidationError("remote program probe output must be a JSON object")
        expected_kind = None if program.probe_contract == "generic" else program.probe_contract
        if data.get("schema_version") != 1 or (
            expected_kind is not None and data.get("kind") != expected_kind
        ):
            raise ProtocolValidationError("remote program probe returned invalid schema or kind")
        expected_baseline_id = profile_id or baseline.baseline_id
        if data.get("scope") != "full" or data.get("baseline_id") not in (
            baseline.baseline_id,
            expected_baseline_id,
        ):
            raise ProtocolValidationError(
                "remote program probe returned mismatched scope or baseline"
            )
        if data.get("source_revision") != baseline.source.revision:
            raise ProtocolValidationError(
                "remote program probe returned mismatched source revision"
            )
        env = data.get("environment")
        if (
            not isinstance(env, dict)
            or env.get("conda_explicit_sha256") != expected_environment_sha256
        ):
            raise ProtocolValidationError(
                "remote program probe returned mismatched environment hash"
            )
        if env.get("cuda_visible_device_count") != 1:
            raise ProtocolValidationError(
                "remote program probe requires exactly 1 visible CUDA device"
            )
        checks = data.get("checks")
        if not isinstance(checks, dict):
            raise ProtocolValidationError("remote program probe returned invalid checks structure")
        if any(checks.get(name) != "passed" for name in program.required_probe_checks):
            raise ProtocolValidationError("remote program probe failed runtime checks")
        imports = checks.get("imports")
        if not isinstance(imports, dict) or any(
            imports.get(m) != "passed" for m in program.import_modules
        ):
            raise ProtocolValidationError("remote program probe failed module imports")
        inputs = data.get("inputs")
        if not isinstance(inputs, dict) or any(
            inputs.get(name) != "passed" for name in program.required_inputs
        ):
            raise ProtocolValidationError("remote program probe failed input verification")
        counts = data.get("dataset_counts")
        if not isinstance(counts, dict):
            raise ProtocolValidationError("remote program probe returned invalid dataset counts")
        if any(
            counts.get(name) not in allowed_values
            for name, allowed_values in program.expected_dataset_counts
        ):
            raise ProtocolValidationError(
                "remote program probe dataset counts do not match expected B0"
            )

    @staticmethod
    def _remote_path(value: str, *, field: str) -> str:
        if (
            not isinstance(value, str)
            or not value
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
        ):
            raise ProtocolValidationError(f"{field} must be an absolute normalized remote path")
        path = PurePosixPath(value)
        if not path.is_absolute() or ".." in path.parts or str(path) != value:
            raise ProtocolValidationError(f"{field} must be an absolute normalized remote path")
        return value

    @staticmethod
    def _validate_gpu(output: str, *, gpu_index: int, min_free_gpu_mib: int) -> str:
        fields = [field.strip() for field in output.split(",")]
        if len(fields) != 4:
            raise ProtocolValidationError("remote GPU report is invalid")
        try:
            observed_index = int(fields[0])
            free_memory_mib = int(fields[2])
            utilization = float(fields[3])
        except ValueError as error:
            raise ProtocolValidationError("remote GPU report is invalid") from error
        gpu_uuid = fields[1]
        if observed_index != gpu_index or not _GPU_UUID.fullmatch(gpu_uuid):
            raise ProtocolValidationError("remote GPU report is invalid")
        if not 0 <= utilization <= MAX_SHARED_GPU_UTILIZATION_PERCENT:
            raise ProtocolValidationError("remote GPU is busy")
        if free_memory_mib < min_free_gpu_mib:
            raise ProtocolValidationError("remote GPU capacity is insufficient")
        return gpu_uuid

    @staticmethod
    def _launch_command(
        program: ReproductionProgram,
        *,
        baseline_id: str,
        remote_root: str,
        data_root: str,
        gpu_index: int,
        run_id: str,
        mode: str = "formal",
        phase: str = "training",
        profile_id: str | None = None,
        learning_rate: float | None = None,
        attempt_id: str | None = None,
        lane_id: str | None = None,
        harness_revision: str | None = None,
        model_source_revision: str | None = None,
        environment_sha256: str | None = None,
        preprocessing_revision: str = PREPROCESSING_REVISION,
        cpu_set: str | None = None,
        run_root_override: str | None = None,
        training_source_root: str | None = None,
        test_root: str | None = None,
        selection_path: str | None = None,
    ) -> str:
        cpu_set = RemoteExecutor._validate_cpu_set(cpu_set)
        dataset_root = str(PurePosixPath(data_root) / program.dataset_subdirectory)
        run_root = run_root_override or str(
            PurePosixPath(data_root) / program.run_subdirectory / run_id
        )
        program_path = str(PurePosixPath(remote_root) / program.entrypoint)
        target_profile = profile_id or baseline_id
        argv = [
            *(["taskset", "--cpu-list", cpu_set] if cpu_set is not None else []),
            "env",
            f"MEDREC_RUN_ID={run_id}",
            f"MEDREC_ATTEMPT_ID={attempt_id or run_id}",
            f"MEDREC_LANE_ID={lane_id or baseline_id}",
            f"MEDREC_BASELINE_ID={baseline_id}",
            f"MEDREC_PROGRAM_ID={program.program_id}",
            f"MEDREC_PROFILE_ID={target_profile}",
            f"MEDREC_HARNESS_REVISION={harness_revision or 'unverified'}",
            f"MEDREC_MODEL_SOURCE_REVISION={model_source_revision or 'unverified'}",
            f"MEDREC_PREPROCESSING_REVISION={preprocessing_revision}",
            f"MEDREC_SNAPSHOT_ID={program.dataset_subdirectory}",
            f"MEDREC_ENVIRONMENT_SHA256={environment_sha256 or 'unverified'}",
            f"MEDREC_SUBMISSION_ID={run_id}",
            "MEDREC_MODE=" + mode,
            f"MEDREC_DATA_ROOT={data_root}",
            f"SAFEDRUG_ROOT={program.upstream_root}",
            f"CUDA_VISIBLE_DEVICES={gpu_index}",
            f"CONDA_ENV={program.conda_environment}",
            "/root/anaconda3/bin/conda",
            "run",
            "--no-capture-output",
            "-n",
            program.conda_environment,
            "python",
            program_path,
            target_profile,
            "--upstream-root",
            program.upstream_root,
            "--dataset-root",
            dataset_root,
            "--run-root",
            run_root,
        ]
        if learning_rate is not None:
            argv.extend(["--learning-rate", str(learning_rate)])
        if mode == "formal":
            if phase not in ("training", "test"):
                raise ProtocolValidationError("formal reproduction phase is invalid")
            argv.extend(["--phase", phase])
            if phase == "test":
                if run_root_override is None or training_source_root is None or test_root is None:
                    raise ProtocolValidationError(
                        "formal test requires recovered, source, and continuation test roots"
                    )
                argv.extend(
                    ["--training-source-root", training_source_root, "--test-root", test_root]
                )
                if selection_path is not None:
                    argv.extend(["--selection", selection_path])
            elif any(
                value is not None
                for value in (run_root_override, training_source_root, test_root, selection_path)
            ):
                raise ProtocolValidationError("formal training cannot use test continuation paths")
        if mode == "smoke":
            argv.extend(["--mode", "smoke"])
        command = shlex.join(argv)
        return f"cd {shlex.quote(remote_root)} && {command}"

    @staticmethod
    def _validate_cpu_set(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not _CPU_SET.fullmatch(value):
            raise ProtocolValidationError("cpu_set must be a comma-separated CPU list or range")
        values = RemoteExecutor._cpu_set_values(value)
        if len(values) != len(set(values)):
            raise ProtocolValidationError("cpu_set must not repeat a CPU")
        for item in value.split(","):
            bounds = [int(bound) for bound in item.split("-")]
            if len(bounds) == 2 and bounds[0] > bounds[1]:
                raise ProtocolValidationError("cpu_set ranges must be ascending")
        return value

    @staticmethod
    def _cpu_set_values(value: str) -> tuple[int, ...]:
        values: list[int] = []
        for item in value.split(","):
            bounds = [int(bound) for bound in item.split("-")]
            if len(bounds) == 1:
                values.append(bounds[0])
            else:
                values.extend(range(bounds[0], bounds[1] + 1))
        return tuple(values)

    @staticmethod
    def _validate_job_id(job_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", job_id):
            raise ProtocolValidationError("job_id must be a safe identifier")

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


__all__ = (
    "APPROVED_319_HOSTS",
    "PREPROCESSING_REVISION",
    "FrozenSchedule",
    "PreflightResult",
    "RemoteExecutor",
    "RemoteSubmission",
    "SSHConfig",
    "ScheduleAllocation",
)
