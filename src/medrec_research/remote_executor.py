"""Fail-closed SSH and tmux submission for approved 319 baseline runs."""

from __future__ import annotations

import re
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from ._validation import require_int
from .errors import ProtocolValidationError
from .registry import BaselineDefinition, BaselineReadiness, ResearchMode

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
class BaselineLauncher:
    """Repository-owned launcher details for one supported baseline."""

    baseline_id: str
    conda_environment: str
    upstream_root: str
    command: tuple[str, ...]


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


@dataclass(frozen=True, slots=True)
class JobStatus:
    """Status snapshot of a remote background tmux job."""

    job_id: str
    status: str
    progress: str
    log_tail: str


_LAUNCHERS = {
    "gamenet": BaselineLauncher(
        baseline_id="gamenet",
        conda_environment="medrec-gamenet",
        upstream_root="/root/zhb/SafeDrug",
        command=("bash", "baselines/scripts/run_gamenet_319.sh", "gamenet"),
    )
}


class RemoteExecutor:
    """Preflight and submit declared baselines on the approved 319 host."""

    def __init__(
        self,
        ssh_config: SSHConfig | None = None,
        *,
        runner: Runner = subprocess.run,
    ) -> None:
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
        baseline: BaselineDefinition,
        *,
        source_revision: str,
        gpu_index: int,
        remote_root: str,
        data_root: str,
        min_free_gpu_mib: int,
        min_free_disk_gib: int,
    ) -> PreflightResult:
        """Run every required read-only check and return verified identifiers."""
        launcher, remote_root, data_root = self._validate_launch_inputs(
            baseline,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
        )
        self._require_readiness(baseline)
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

        launcher_path = PurePosixPath(remote_root) / launcher.command[1]
        if (
            self.ssh(
                host,
                f"test -f {shlex.quote(str(launcher_path))} && printf ok",
                gate="launcher",
            )
            != "ok"
        ):
            raise ProtocolValidationError("remote launcher check failed")

        quoted_upstream_root = shlex.quote(launcher.upstream_root)
        if self.ssh(
            host,
            f"git -C {quoted_upstream_root} status --porcelain --untracked-files=all",
            gate="baseline-source-clean",
        ):
            raise ProtocolValidationError("remote baseline-source-clean check failed")
        observed_baseline_revision = self.ssh(
            host,
            f"git -C {quoted_upstream_root} rev-parse HEAD",
            gate="baseline-source-revision",
        )
        if observed_baseline_revision != baseline.source.revision:
            raise ProtocolValidationError("remote baseline-source-revision check failed")

        environment_command = (
            "source /root/anaconda3/etc/profile.d/conda.sh && "
            f"conda list --explicit -n {shlex.quote(launcher.conda_environment)} | "
            "sha256sum | awk '{print $1}'"
        )
        observed_environment = self.ssh(host, environment_command, gate="environment")
        if observed_environment != baseline.environment_sha256:
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
            free_disk_kib = int(disk_output)
        except ValueError as error:
            raise ProtocolValidationError("remote disk report is invalid") from error
        if free_disk_kib < min_free_disk_gib * 1024 * 1024:
            raise ProtocolValidationError("remote disk capacity is insufficient")

        return PreflightResult(
            host=host,
            baseline_id=baseline.baseline_id,
            source_revision=source_revision,
            environment_sha256=observed_environment,
            gpu_index=gpu_index,
        )

    def run_baseline(
        self,
        baseline: BaselineDefinition,
        *,
        source_revision: str,
        gpu_index: int,
        remote_root: str,
        data_root: str,
        min_free_gpu_mib: int,
        min_free_disk_gib: int,
        dry_run: bool = False,
    ) -> RemoteSubmission:
        """Validate, preflight, and submit one declared Reproduction Mode run."""
        launcher, remote_root, data_root = self._validate_launch_inputs(
            baseline,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
        )
        command = self._launch_command(
            launcher,
            remote_root=remote_root,
            data_root=data_root,
            gpu_index=gpu_index,
        )
        session_id = f"medrec-baseline-{baseline.baseline_id}-{self._timestamp()}"
        if dry_run:
            return RemoteSubmission(
                baseline_id=baseline.baseline_id,
                host=None,
                session_id=session_id,
                command=command,
                preflight_performed=False,
            )

        result = self.preflight(
            baseline,
            source_revision=source_revision,
            gpu_index=gpu_index,
            remote_root=remote_root,
            data_root=data_root,
            min_free_gpu_mib=min_free_gpu_mib,
            min_free_disk_gib=min_free_disk_gib,
        )
        self.ssh(
            result.host,
            f"tmux new-session -d -s {shlex.quote(session_id)} {shlex.quote(command)}",
            gate="tmux-launch",
        )
        return RemoteSubmission(
            baseline_id=baseline.baseline_id,
            host=result.host,
            session_id=session_id,
            command=command,
            preflight_performed=True,
        )

    def check_status(self, job_id: str, *, host: str) -> JobStatus:
        """Check a previously submitted tmux session without changing it."""
        self._validate_job_id(job_id)
        try:
            self.ssh(
                host,
                f"tmux has-session -t {shlex.quote(job_id)}",
                gate="status",
            )
            status = "running"
        except ProtocolValidationError:
            status = "unknown"
        log_tail = ""
        if status == "running":
            try:
                log_tail = self.ssh(
                    host,
                    f"tmux capture-pane -t {shlex.quote(job_id)} -p | tail -n 20",
                    gate="status",
                )
            except ProtocolValidationError:
                status = "unknown"
        return JobStatus(
            job_id=job_id,
            status=status,
            progress=self._parse_progress(log_tail),
            log_tail=log_tail,
        )

    def collect_results(
        self,
        job_id: str,
        remote_path: str,
        local_dest: Path,
        *,
        host: str,
    ) -> Path:
        """Copy an explicitly selected remote artifact through an approved alias."""
        self._validate_job_id(job_id)
        if host not in self.ssh_config.hosts or host not in APPROVED_319_HOSTS:
            raise ProtocolValidationError("remote host must use an approved 319 alias")
        remote_path = self._remote_path(remote_path, field="remote_path")
        local_dest.parent.mkdir(parents=True, exist_ok=True)
        argv = [
            "scp",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={self.ssh_config.connect_timeout_seconds}",
            "-o",
            "StrictHostKeyChecking=yes",
            f"{host}:{remote_path}",
            str(local_dest),
        ]
        try:
            self._runner(
                argv,
                capture_output=True,
                text=True,
                timeout=self.ssh_config.command_timeout_seconds,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise ProtocolValidationError("remote result collection failed") from error
        return local_dest

    def cleanup_session(self, session_id: str, *, host: str) -> bool:
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

    def _validate_launch_inputs(
        self,
        baseline: BaselineDefinition,
        *,
        source_revision: str,
        gpu_index: int,
        remote_root: str,
        data_root: str,
        min_free_gpu_mib: int,
        min_free_disk_gib: int,
    ) -> tuple[BaselineLauncher, str, str]:
        launcher = _LAUNCHERS.get(baseline.baseline_id)
        if launcher is None:
            raise ProtocolValidationError(
                f"baseline '{baseline.baseline_id}' has no declared remote launcher"
            )
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
        return launcher, remote_root, data_root

    @staticmethod
    def _require_readiness(baseline: BaselineDefinition) -> None:
        if baseline.readiness not in {
            BaselineReadiness.SMOKE_READY,
            BaselineReadiness.COMPARISON_READY,
        }:
            raise ProtocolValidationError("remote submission requires a smoke_ready baseline")

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
        launcher: BaselineLauncher,
        *,
        remote_root: str,
        data_root: str,
        gpu_index: int,
    ) -> str:
        command = shlex.join(
            (
                "env",
                f"MEDREC_DATA_ROOT={data_root}",
                f"GPU_ID={gpu_index}",
                f"CONDA_ENV={launcher.conda_environment}",
                *launcher.command,
            )
        )
        return f"cd {shlex.quote(remote_root)} && {command}"

    @staticmethod
    def _validate_job_id(job_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", job_id):
            raise ProtocolValidationError("job_id must be a safe identifier")

    @staticmethod
    def _parse_progress(log_tail: str) -> str:
        if not log_tail:
            return "Idle / Not started"
        matches = re.findall(
            r"(Epoch\s+\d+/\d+|\b\d+%\b|\d+%|Step\s+\[?\d+/\d+\]?)",
            log_tail,
        )
        return matches[-1] if matches else "Executing"

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


__all__ = (
    "APPROVED_319_HOSTS",
    "BaselineLauncher",
    "JobStatus",
    "PreflightResult",
    "RemoteExecutor",
    "RemoteSubmission",
    "SSHConfig",
)
