"""SSH + tmux wrapper for remote baseline and experiment execution on 319-wild."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class SSHConfig:
    """SSH connection settings for remote execution host."""

    host: str = "319-wild"
    user: str = "oian"
    key_path: Path = field(default_factory=lambda: Path("~/.ssh/id_rsa").expanduser())
    remote_data_root: str = "/data/medrec"
    port: int = 22
    timeout: int = 60

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SSHConfig:
        key_raw = data.get("key_path") or data.get("key") or "~/.ssh/id_rsa"
        return cls(
            host=str(data.get("host", "319-wild")),
            user=str(data.get("user", "oian")),
            key_path=Path(str(key_raw)).expanduser(),
            remote_data_root=str(
                data.get("remote_data_root", data.get("data_root", "/data/medrec"))
            ),
            port=int(data.get("port", 22)),
            timeout=int(data.get("timeout", 60)),
        )


@dataclass
class JobStatus:
    """Status snapshot of a remote background tmux job."""

    job_id: str
    status: str  # "running" | "completed" | "failed" | "unknown"
    progress: str
    log_tail: str


class RemoteExecutor:
    """Manages remote execution on the GPU host via SSH and tmux."""

    def __init__(self, ssh_config: SSHConfig | None = None):
        self.ssh_config = ssh_config or SSHConfig()

    def ssh(self, command: str, timeout: int | None = None, check: bool = True) -> str:
        """Execute a remote shell command via OpenSSH."""
        cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-p",
            str(self.ssh_config.port),
        ]
        if self.ssh_config.key_path.exists():
            cmd.extend(["-i", str(self.ssh_config.key_path)])

        cmd.extend([f"{self.ssh_config.user}@{self.ssh_config.host}", command])

        effective_timeout = timeout or self.ssh_config.timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            check=check,
        )
        return result.stdout.strip()

    def run_baseline(self, baseline_id: str, config: dict[str, Any], dry_run: bool = False) -> str:
        """Run a baseline model in an isolated conda environment inside a tmux session."""
        session_name = f"medrec-baseline-{baseline_id}-{self._timestamp()}"
        if dry_run:
            return session_name

        conda_env = config.get("conda_env", f"{baseline_id}-env")
        run_cmd = self._generate_baseline_script(baseline_id, config)

        # 1. Start tmux session
        self.ssh(f"tmux new-session -d -s {session_name}")
        # 2. Activate conda env
        self.ssh(f"tmux send-keys -t {session_name} 'conda activate {conda_env}' C-m")
        # 3. Launch command
        self.ssh(f"tmux send-keys -t {session_name} '{run_cmd}' C-m")

        return session_name

    def run_experiment(
        self, experiment_id: str, exp_config: dict[str, Any], dry_run: bool = False
    ) -> str:
        """Run an idea experiment in a tmux session."""
        session_name = f"medrec-exp-{experiment_id}-{self._timestamp()}"
        if dry_run:
            return session_name

        conda_env = exp_config.get("conda_env", "medrec-core")
        run_cmd = self._generate_experiment_script(experiment_id, exp_config)

        self.ssh(f"tmux new-session -d -s {session_name}")
        self.ssh(f"tmux send-keys -t {session_name} 'conda activate {conda_env}' C-m")
        self.ssh(f"tmux send-keys -t {session_name} '{run_cmd}' C-m")

        return session_name

    def check_status(self, job_id: str) -> JobStatus:
        """Check status of a remote tmux job and extract log tail."""
        try:
            self.ssh(f"tmux has-session -t {job_id}", check=True)
            status = "running"
        except subprocess.CalledProcessError:
            status = "completed"
        except Exception:
            status = "unknown"

        log_tail = ""
        if status == "running":
            try:
                log_tail = self.ssh(f"tmux capture-pane -t {job_id} -p | tail -n 20", check=False)
            except Exception:
                log_tail = ""

        progress = self._parse_progress(log_tail)
        return JobStatus(
            job_id=job_id,
            status=status,
            progress=progress,
            log_tail=log_tail,
        )

    def collect_results(self, job_id: str, remote_path: str, local_dest: Path) -> Path:
        """SCP remote result artifact from 319-wild to local destination."""
        local_dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "scp",
            "-P",
            str(self.ssh_config.port),
        ]
        if self.ssh_config.key_path.exists():
            cmd.extend(["-i", str(self.ssh_config.key_path)])

        cmd.extend(
            [
                f"{self.ssh_config.user}@{self.ssh_config.host}:{remote_path}",
                str(local_dest),
            ]
        )

        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return local_dest

    def _generate_baseline_script(self, baseline_id: str, config: dict[str, Any]) -> str:
        remote_data = self.ssh_config.remote_data_root
        entrypoint = config.get("entrypoint", f"run_{baseline_id}.py")
        config_path = config.get("config_path", "")
        cmd = f"python {entrypoint} --data-root {remote_data}"
        if config_path:
            cmd += f" --config {config_path}"
        return cmd

    def _generate_experiment_script(self, experiment_id: str, config: dict[str, Any]) -> str:
        remote_data = self.ssh_config.remote_data_root
        entrypoint = config.get("entrypoint", "run_experiment.py")
        config_path = config.get("config_path", f"experiments/{experiment_id}.yaml")
        return f"python {entrypoint} --config {config_path} --data-root {remote_data}"

    def _parse_progress(self, log_tail: str) -> str:
        if not log_tail:
            return "Idle / Not started"
        # Match common training patterns like "Epoch 12/50", "Step [100/500]", "75%"
        epoch_match = re.findall(r"(Epoch\s+\d+/\d+|\b\d+%\b|\d+%|Step\s+\[?\d+/\d+\]?)", log_tail)
        if epoch_match:
            return epoch_match[-1]
        return "Executing"

    def _timestamp(self) -> str:
        return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
