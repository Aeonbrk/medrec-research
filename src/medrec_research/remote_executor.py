"""Fail-closed SSH and tmux submission for approved 319 baseline runs."""

from __future__ import annotations

import json
import re
import secrets
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath

from ._validation import require_int
from .errors import ProtocolValidationError
from .registry import (
    BaselineDefinition,
    BaselineRegistry,
    ReproductionProgram,
    ResearchMode,
    SourceStatus,
)

APPROVED_319_HOSTS = ("319-lab", "319-lab-via-server")
_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40,64}")
_GPU_UUID = re.compile(r"GPU-[A-Za-z0-9-]+")

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


@dataclass(frozen=True, slots=True)
class RemoteSubmission:
    """Public-safe description of a planned or submitted baseline run."""

    baseline_id: str
    host: str | None
    session_id: str
    command: str
    preflight_performed: bool


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
    ) -> PreflightResult:
        """Run every required read-only check and return verified identifiers."""
        baseline, program, profile_id, _ = self._resolve_target(baseline_id)
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
        gpu_uuid = self._validate_gpu(
            gpu_output,
            gpu_index=gpu_index,
            min_free_gpu_mib=min_free_gpu_mib,
        )
        process_output = self.ssh(
            host,
            "nvidia-smi --query-compute-apps=gpu_uuid --format=csv,noheader",
            gate="gpu-processes",
        )
        process_uuids = (
            set()
            if process_output.strip() == "No running processes found"
            else {line.strip() for line in process_output.splitlines() if line.strip()}
        )
        if any(not _GPU_UUID.fullmatch(value) for value in process_uuids):
            raise ProtocolValidationError("remote GPU process report is invalid")
        if gpu_uuid in process_uuids:
            raise ProtocolValidationError("remote GPU is busy")

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

        program_probe_cmd = (
            "source /root/anaconda3/etc/profile.d/conda.sh && "
            f"conda activate {shlex.quote(program.conda_environment)} && "
            f"CUDA_VISIBLE_DEVICES={gpu_index} python {shlex.quote(str(program_path))} "
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
    ) -> RemoteSubmission:
        """Validate, preflight, and submit one declared Reproduction Mode formal run."""
        baseline, program, profile_id, learning_rate = self._resolve_target(baseline_id)
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
        )
        if dry_run:
            return RemoteSubmission(
                baseline_id=baseline_id,
                host=None,
                session_id=session_id,
                command=command,
                preflight_performed=False,
            )

        result = self.preflight(
            baseline_id,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
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
        )

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
    ) -> RemoteSubmission:
        """Validate, preflight, and submit one declared Reproduction Mode smoke run."""
        baseline, program, profile_id, learning_rate = self._resolve_target(baseline_id)
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
        )
        if dry_run:
            return RemoteSubmission(
                baseline_id=baseline_id,
                host=None,
                session_id=session_id,
                command=command,
                preflight_performed=False,
            )

        result = self.preflight(
            baseline_id,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
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
        )

    def _resolve_target(
        self, baseline_or_lane_id: str
    ) -> tuple[BaselineDefinition, ReproductionProgram, str, float | None]:
        try:
            lane = self.registry.get_lane(baseline_or_lane_id)
            baseline = self.registry.get(lane.scientific_baseline_id)
            program = self.registry.get_program(lane.program_id)
            return baseline, program, lane.profile_id, lane.learning_rate
        except KeyError:
            pass
        baseline = self._baseline(baseline_or_lane_id)
        program = self.registry.reproduction_program_for(baseline)
        return baseline, program, baseline.baseline_id, None

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
        if data.get("schema_version") != 1 or data.get("kind") not in (
            "safedrug_archived_probe",
            "molerec_probe",
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
        for check_name in ("cuda_tensor", "rdkit_brics", "dnc_forward"):
            if check_name in checks and checks[check_name] != "passed":
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
        if (
            counts.get("patients") != 6_350
            or counts.get("visits") not in (15_032, 14_995)
            or counts.get("medications") != 131
            or counts.get("ddi_pairs") != 448
        ):
            raise ProtocolValidationError(
                "remote program probe dataset counts do not match expected B0"
            )
        if (
            program.program_id == "safedrug-archived"
            and counts.get("molecular_substructures") != 491
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
        if utilization != 0:
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
        profile_id: str | None = None,
        learning_rate: float | None = None,
    ) -> str:
        dataset_root = str(PurePosixPath(data_root) / program.dataset_subdirectory)
        run_root = str(PurePosixPath(data_root) / program.run_subdirectory / run_id)
        program_path = str(PurePosixPath(remote_root) / program.entrypoint)
        target_profile = profile_id or baseline_id
        argv = [
            "env",
            f"MEDREC_RUN_ID={run_id}",
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
        if mode == "smoke":
            argv.extend(["--mode", "smoke"])
        command = shlex.join(argv)
        return f"cd {shlex.quote(remote_root)} && {command}"

    @staticmethod
    def _validate_job_id(job_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", job_id):
            raise ProtocolValidationError("job_id must be a safe identifier")

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


__all__ = (
    "APPROVED_319_HOSTS",
    "PreflightResult",
    "RemoteExecutor",
    "RemoteSubmission",
    "SSHConfig",
)
