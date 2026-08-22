"""Fail-closed SSH and tmux submission for approved 319 baseline runs."""

from __future__ import annotations

import hashlib
import re
import secrets
import shlex
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from ._validation import require_int
from .errors import ProtocolValidationError
from .registry import BaselineDefinition, ResearchMode, SourceStatus

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
    required_data_subdirectory: str
    command: tuple[str, ...]
    adapter_files: tuple[str, ...] = ()
    required_inputs: tuple[str, ...] = ()


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


_SAFEDRUG_FAMILY_ADAPTER_FILES = (
    "baselines/scripts/run_safedrug_family_319.sh",
    "baselines/scripts/parse_safedrug_family_results.py",
)

_SAFEDRUG_FAMILY_REQUIRED_INPUTS_COMMON = (
    "data/output/records_final.pkl",
    "data/output/voc_final.pkl",
    "data/output/ddi_A_final.pkl",
)

_SAFEDRUG_REQUIRED_INPUTS = (
    "data/output/records_final.pkl",
    "data/output/voc_final.pkl",
    "data/output/ddi_A_final.pkl",
    "data/output/ddi_mask_H.pkl",
    "data/output/atc3toSMILES.pkl",
)


_LAUNCHERS = {
    "gamenet": BaselineLauncher(
        baseline_id="gamenet",
        conda_environment="medrec-gamenet",
        upstream_root="/root/zhb/SafeDrug",
        required_data_subdirectory="mimic-iii",
        command=("bash", "baselines/scripts/run_gamenet_319.sh", "gamenet"),
        adapter_files=("baselines/scripts/run_gamenet_319.sh",),
        required_inputs=(),
    ),
    "safedrug": BaselineLauncher(
        baseline_id="safedrug",
        conda_environment="medrec-gamenet",
        upstream_root="/root/zhb/SafeDrug",
        required_data_subdirectory="mimic-iii",
        command=("bash", "baselines/scripts/run_safedrug_family_319.sh", "safedrug"),
        adapter_files=_SAFEDRUG_FAMILY_ADAPTER_FILES,
        required_inputs=_SAFEDRUG_REQUIRED_INPUTS,
    ),
    "retain": BaselineLauncher(
        baseline_id="retain",
        conda_environment="medrec-gamenet",
        upstream_root="/root/zhb/SafeDrug",
        required_data_subdirectory="mimic-iii",
        command=("bash", "baselines/scripts/run_safedrug_family_319.sh", "retain"),
        adapter_files=_SAFEDRUG_FAMILY_ADAPTER_FILES,
        required_inputs=_SAFEDRUG_FAMILY_REQUIRED_INPUTS_COMMON,
    ),
    "leap-safedrug": BaselineLauncher(
        baseline_id="leap-safedrug",
        conda_environment="medrec-gamenet",
        upstream_root="/root/zhb/SafeDrug",
        required_data_subdirectory="mimic-iii",
        command=("bash", "baselines/scripts/run_safedrug_family_319.sh", "leap-safedrug"),
        adapter_files=_SAFEDRUG_FAMILY_ADAPTER_FILES,
        required_inputs=_SAFEDRUG_FAMILY_REQUIRED_INPUTS_COMMON,
    ),
}


def compute_adapter_digest(repo_root: Path | str, files: tuple[str, ...]) -> str:
    """Compute deterministic SHA-256 digest for adapter files."""
    root = Path(repo_root)
    if len(files) == 1:
        hasher = hashlib.sha256()
        hasher.update((root / files[0]).read_bytes())
        return f"sha256:{hasher.hexdigest()}"
    hasher = hashlib.sha256()
    for rel_path in files:
        file_path = root / rel_path
        hasher.update(rel_path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(file_path.read_bytes())
        hasher.update(b"\0")
    return f"sha256:{hasher.hexdigest()}"


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

        required_data_path = PurePosixPath(data_root) / launcher.required_data_subdirectory
        if (
            self.ssh(
                host,
                f"test -d {shlex.quote(str(required_data_path))} && printf ok",
                gate="data-input",
            )
            != "ok"
        ):
            raise ProtocolValidationError("remote data-input check failed")

        # Verify adapter files exist on remote and match declared adapter_revision digest
        adapter_check_cmd = (
            " && ".join(
                f"test -f {shlex.quote(str(PurePosixPath(remote_root) / f))}"
                for f in launcher.adapter_files
            )
            + " && printf ok"
        )
        if self.ssh(host, adapter_check_cmd, gate="launcher") != "ok":
            raise ProtocolValidationError("remote launcher check failed")

        recompute_script = (
            "import hashlib, sys; from pathlib import Path; "
            "root = Path(sys.argv[1]); files = sys.argv[2:]; hasher = hashlib.sha256(); "
            "[hasher.update((root / files[0]).read_bytes())] if len(files) == 1 else "
            "[(hasher.update(rel.encode('utf-8')), hasher.update(b'\\x00'), hasher.update((root / rel).read_bytes()), hasher.update(b'\\x00')) for rel in files]; "
            "print('sha256:' + hasher.hexdigest())"
        )
        cmd_parts = ["python3", "-c", recompute_script, remote_root, *launcher.adapter_files]
        remote_adapter_digest = self.ssh(host, shlex.join(cmd_parts), gate="launcher-digest").strip()
        if remote_adapter_digest != baseline.adapter_revision:
            raise ProtocolValidationError(
                "remote adapter digest does not match declared adapter_revision"
            )

        quoted_upstream_root = shlex.quote(launcher.upstream_root)
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

        if launcher.required_inputs:
            inputs_check_cmd = (
                " && ".join(
                    f"test -f {shlex.quote(str(PurePosixPath(launcher.upstream_root) / f))} && ! test -L {shlex.quote(str(PurePosixPath(launcher.upstream_root) / f))}"
                    for f in launcher.required_inputs
                )
                + " && printf ok"
            )
            if self.ssh(host, inputs_check_cmd, gate="baseline-inputs") != "ok":
                raise ProtocolValidationError("remote baseline required input files check failed")

        environment_command = (
            "source /root/anaconda3/etc/profile.d/conda.sh && "
            f"conda list --explicit -n {shlex.quote(launcher.conda_environment)} | "
            "sha256sum | awk '{print $1}'"
        )
        observed_environment = self.ssh(host, environment_command, gate="environment")
        if observed_environment != baseline.environment_sha256:
            raise ProtocolValidationError("remote environment check failed")

        import_probe_cmd = (
            "source /root/anaconda3/etc/profile.d/conda.sh && "
            f"conda activate {shlex.quote(launcher.conda_environment)} && "
            f"CUDA_VISIBLE_DEVICES={gpu_index} python -c "
            + shlex.quote(
                f"import sys; sys.path.insert(0, '{launcher.upstream_root}/src'); "
                "import torch, dnc, rdkit, pandas, dill, sklearn, models, util; "
                "assert torch.cuda.is_available(), 'CUDA not available'; "
                "assert torch.cuda.device_count() == 1, 'Expected exactly 1 visible CUDA device'; "
                "print('ok')"
            )
        )
        if self.ssh(host, import_probe_cmd, gate="environment-imports") != "ok":
            raise ProtocolValidationError("remote environment import probe failed")

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
        session_id = (
            f"medrec-baseline-{baseline.baseline_id}-{self._timestamp()}-{secrets.token_hex(4)}"
        )
        command = self._launch_command(
            launcher,
            remote_root=remote_root,
            data_root=data_root,
            gpu_index=gpu_index,
            run_id=session_id,
        )
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
        try:
            self.ssh(
                result.host,
                f"tmux new-session -d -s {shlex.quote(session_id)} {shlex.quote(command)}",
                gate="tmux-launch",
            )
        except ProtocolValidationError:
            self.cleanup_session(session_id, host=result.host)
            raise
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
        self._validate_declaration(baseline, launcher)
        return launcher, remote_root, data_root

    @staticmethod
    def _validate_declaration(baseline: BaselineDefinition, launcher: BaselineLauncher) -> None:
        if baseline.source.status is not SourceStatus.PINNED or not baseline.source.revision:
            raise ProtocolValidationError("reproduction launch requires a pinned baseline source")
        if not _IMMUTABLE_REVISION.fullmatch(baseline.source.revision):
            raise ProtocolValidationError(
                "baseline source revision must be an immutable Git revision"
            )
        if not baseline.adapter_command or baseline.adapter_command != launcher.command:
            raise ProtocolValidationError(
                "baseline adapter_command does not match declared launcher"
            )
        if not baseline.adapter_revision or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", baseline.adapter_revision
        ):
            raise ProtocolValidationError(
                "baseline adapter_revision must be an immutable sha256 digest"
            )
        if not baseline.environment_sha256 or not re.fullmatch(
            r"[0-9a-f]{64}", baseline.environment_sha256
        ):
            raise ProtocolValidationError(
                "baseline environment_sha256 must be a valid 64-hex digest"
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
        launcher: BaselineLauncher,
        *,
        remote_root: str,
        data_root: str,
        gpu_index: int,
        run_id: str,
    ) -> str:
        command = shlex.join(
            (
                "env",
                f"MEDREC_RUN_ID={run_id}",
                f"MEDREC_DATA_ROOT={data_root}",
                f"SAFEDRUG_ROOT={launcher.upstream_root}",
                f"CUDA_VISIBLE_DEVICES={gpu_index}",
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
