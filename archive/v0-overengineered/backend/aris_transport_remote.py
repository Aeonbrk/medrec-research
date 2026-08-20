"""Remote half of the fixed ARIS transport contract.

This module is invoked only through :mod:`medrec_research.aris_transport`. It
accepts a content-addressed manifest on stdin and never accepts caller-provided
paths, commands, environments, or GPU identifiers.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from ._validation import parse_json_object, write_json_atomic
from .aris_transport import (
    ArisTransportManifest,
    ArisTransportReceipt,
    ArisTransportRegistry,
    ArisTransportStatus,
    _exclusive_file_lock,
    _sha256_file,
    transport_package_sha256,
)
from .errors import ProtocolValidationError


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _required_root(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise ProtocolValidationError(f"{name} is unavailable")
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        raise ProtocolValidationError(f"{name} is invalid")
    return path.resolve()


def _git_revision(repository: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 else None


def _git_clean(repository: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and not result.stdout.strip()


def _contained(root: Path, relative: str | Path, *, field: str) -> Path:
    lexical = root / relative
    _reject_symlink_components(root, lexical, field=field)
    candidate = lexical.resolve(strict=False)
    if candidate != root and not candidate.is_relative_to(root):
        raise ProtocolValidationError(f"{field} escaped its authority")
    return candidate


def _reject_symlink_components(root: Path, candidate: Path, *, field: str) -> None:
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise ProtocolValidationError(f"{field} escaped its authority") from error
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ProtocolValidationError(f"{field} contains a symlink component")


def _command_sha256(command: list[str]) -> str:
    return sha256(b"\0".join(os.fsencode(item) for item in command) + b"\0").hexdigest()


class RemoteArisRun:
    def __init__(
        self,
        manifest: ArisTransportManifest,
        registry: ArisTransportRegistry,
    ) -> None:
        if manifest.project_id != registry.project_id or manifest.target_id != registry.target_id:
            raise ProtocolValidationError("remote transport target binding changed")
        if manifest.transport_policy_sha256 != registry.policy_sha256:
            raise ProtocolValidationError("remote transport policy binding changed")
        if manifest.transport_package_sha256 != transport_package_sha256():
            raise ProtocolValidationError("remote transport package binding changed")
        self.manifest = manifest
        self.registry = registry
        self.template = registry.require_enabled_launch(manifest.launch_template_id)
        self.profile = registry.resource_profile(manifest.resource_profile_id)
        if self.template.environment_id != manifest.environment_id:
            raise ProtocolValidationError("remote transport environment binding changed")
        if manifest.gpu_count > self.profile.gpu_count:
            raise ProtocolValidationError("remote transport GPU request exceeds profile")
        if manifest.max_attempts > self.profile.oom_retry_max_attempts:
            raise ProtocolValidationError("remote transport retry request exceeds profile")

        self.data_root = _required_root("MEDREC_DATA_ROOT")
        self.aris_root = _required_root("ARIS_REPO")
        runtime_root = _contained(
            self.data_root,
            registry.runtime_relative,
            field="remote transport runtime root",
        )
        _reject_symlink_components(
            self.data_root,
            runtime_root,
            field="remote transport runtime root",
        )
        self.run_root = runtime_root / manifest.request_sha256
        _reject_symlink_components(
            runtime_root,
            self.run_root,
            field="remote transport run root",
        )
        self.manifest_path = self.run_root / "transport-manifest.json"
        self.queue_manifest_path = self.run_root / "queue-manifest.json"
        self.queue_state_path = self.run_root / "queue-state.json"
        self.log_dir = self.run_root / "logs"
        self.pid_path = self.run_root / "scheduler.json"
        self.receipt_path = self.run_root / "receipt.json"
        self.cancel_path = self.run_root / "cancelled.json"
        self.lock_path = self.run_root / ".operation.lock"
        self.workspace = self.run_root / "workspace"
        self.output_dir = _contained(
            self.run_root,
            Path("output") / (self.template.output_relative or "output"),
            field="remote transport output directory",
        )
        _reject_symlink_components(
            self.run_root,
            self.output_dir,
            field="remote transport output directory",
        )
        self.source_root = _contained(
            self.data_root,
            self.template.source_relative or "missing",
            field="remote transport source root",
        )
        self.private_data = _contained(
            self.data_root,
            self.template.data_relative or "missing",
            field="remote transport data root",
        )
        self.queue_manager = _contained(
            self.aris_root,
            registry.queue_manager_relative,
            field="remote ARIS queue manager",
        )
        self.job_id = f"{manifest.lane_id}-{manifest.request_sha256[:12]}"

    def _operation_lock(self):
        self.run_root.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(
            self.run_root.parent,
            self.run_root,
            field="remote transport run root",
        )
        return _exclusive_file_lock(self.lock_path)

    def _receipt(
        self,
        status: ArisTransportStatus,
        reason_code: str,
        *,
        attempt: int | None = None,
    ) -> ArisTransportReceipt:
        existing = self._load_receipt()
        receipt = ArisTransportReceipt(
            request_sha256=self.manifest.request_sha256,
            manifest_sha256=self.manifest.manifest_sha256,
            aris_revision=self.manifest.aris_revision,
            attempt=attempt or (existing.attempt if existing is not None else 1),
            status=status,
            reason_code=reason_code,
            observed_at=_timestamp(),
            scheduler_job_id=self.job_id,
        )
        self.run_root.mkdir(parents=True, exist_ok=True)
        write_json_atomic(self.receipt_path, receipt.to_dict())
        return receipt

    def _load_receipt(self) -> ArisTransportReceipt | None:
        if not self.receipt_path.is_file():
            return None
        receipt = ArisTransportReceipt.from_json(self.receipt_path.read_text(encoding="utf-8"))
        if (
            receipt.request_sha256 != self.manifest.request_sha256
            or receipt.manifest_sha256 != self.manifest.manifest_sha256
            or receipt.aris_revision != self.manifest.aris_revision
        ):
            raise ProtocolValidationError("remote transport receipt binding changed")
        return receipt

    def _verify_authorities(self) -> None:
        if _git_revision(self.aris_root) != self.manifest.aris_revision:
            raise ProtocolValidationError("remote ARIS revision is not current")
        if not _git_clean(self.aris_root):
            raise ProtocolValidationError("remote ARIS checkout is not clean")
        if not self.queue_manager.is_file():
            raise ProtocolValidationError("remote ARIS queue manager is unavailable")
        if _sha256_file(self.queue_manager) != self.manifest.queue_manager_sha256:
            raise ProtocolValidationError("remote ARIS queue manager binding changed")
        if _git_revision(self.source_root) != self.manifest.source_revision:
            raise ProtocolValidationError("remote baseline source revision is not current")
        if not _git_clean(self.source_root):
            raise ProtocolValidationError("remote baseline source checkout is not clean")
        if not self.private_data.is_dir():
            raise ProtocolValidationError("remote declared data layout is unavailable")

    def _persist_manifest(self) -> None:
        self.run_root.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(
            self.run_root.parent,
            self.run_root,
            field="remote transport run root",
        )
        if self.manifest_path.is_file():
            existing = ArisTransportManifest.from_json(
                self.manifest_path.read_text(encoding="utf-8")
            )
            if existing.to_dict() != self.manifest.to_dict():
                raise ProtocolValidationError("remote transport manifest conflicts with history")
            return
        write_json_atomic(self.manifest_path, self.manifest.to_dict())

    @staticmethod
    def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".git", "__pycache__", "output", "saved"}}

    def _stage_workspace(self) -> Path:
        marker = self.workspace / ".transport-source.json"
        _reject_symlink_components(
            self.run_root,
            self.workspace,
            field="remote transport workspace",
        )
        if self.workspace.exists():
            if not marker.is_file():
                raise ProtocolValidationError("remote transport workspace is incomplete")
            value = parse_json_object(marker.read_text(encoding="utf-8"), context="workspace")
            if value != {
                "manifest_sha256": self.manifest.manifest_sha256,
                "source_revision": self.manifest.source_revision,
            }:
                raise ProtocolValidationError("remote transport workspace conflicts with history")
        else:
            shutil.copytree(self.source_root, self.workspace, ignore=self._copy_ignore)
            write_json_atomic(
                marker,
                {
                    "manifest_sha256": self.manifest.manifest_sha256,
                    "source_revision": self.manifest.source_revision,
                },
            )
        data_parent = self.workspace / "data"
        data_parent.mkdir(exist_ok=True)
        data_link = data_parent / "output"
        if not data_link.exists():
            data_link.symlink_to(self.private_data, target_is_directory=True)
        elif not data_link.is_symlink() or data_link.resolve() != self.private_data.resolve():
            raise ProtocolValidationError("remote transport data binding conflicts with workspace")
        saved_root = self.workspace / (self.template.workdir_relative or "src") / "saved"
        saved_root.mkdir(parents=True, exist_ok=True)
        output_link = saved_root / (self.template.output_relative or "output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if not output_link.exists():
            output_link.symlink_to(self.output_dir, target_is_directory=True)
        elif not output_link.is_symlink() or output_link.resolve() != self.output_dir.resolve():
            raise ProtocolValidationError(
                "remote transport output binding conflicts with workspace"
            )
        return _contained(
            self.workspace,
            self.template.workdir_relative or "src",
            field="remote transport work directory",
        )

    def _queue_manifest(self, cwd: Path) -> dict[str, object]:
        expected_output = self.output_dir / (self.template.expected_output_relative or "missing")
        command = shlex.join(self.template.command)
        return {
            "project": self.registry.project_id,
            "cwd": str(cwd),
            "conda": self.manifest.environment_id,
            "gpus": list(self.profile.gpu_pool),
            "max_parallel": min(self.profile.max_parallel, self.manifest.gpu_count),
            "oom_retry": {
                "delay": self.profile.oom_retry_delay_seconds,
                "max_attempts": min(
                    self.profile.oom_retry_max_attempts,
                    self.manifest.max_attempts,
                ),
            },
            "phases": [
                {
                    "name": "source-native-reproduction",
                    "depends_on": [],
                    "jobs": [
                        {
                            "id": self.job_id,
                            "cmd": command,
                            "expected_output": str(expected_output),
                        }
                    ],
                }
            ],
        }

    def _scheduler_command(self) -> list[str]:
        return [
            sys.executable,
            str(self.queue_manager),
            "--manifest",
            str(self.queue_manifest_path),
            "--state",
            str(self.queue_state_path),
            "--log-dir",
            str(self.log_dir),
            "--poll",
            str(self.registry.poll_seconds),
        ]

    def _load_scheduler(self) -> dict[str, object] | None:
        if not self.pid_path.is_file():
            return None
        value = parse_json_object(self.pid_path.read_text(encoding="utf-8"), context="scheduler")
        if set(value) != {
            "command_sha256",
            "kind",
            "manifest_sha256",
            "pid",
            "process_group_id",
            "schema_version",
            "start_time_ticks",
        }:
            raise ProtocolValidationError("remote scheduler record is invalid")
        if (
            value["kind"] != "aris_transport_scheduler"
            or value["schema_version"] != 1
            or value["manifest_sha256"] != self.manifest.manifest_sha256
        ):
            raise ProtocolValidationError("remote scheduler binding changed")
        for field in ("pid", "process_group_id", "start_time_ticks"):
            if type(value[field]) is not int or value[field] < 1:
                raise ProtocolValidationError("remote scheduler process identity is invalid")
        command_digest = value["command_sha256"]
        if (
            not isinstance(command_digest, str)
            or len(command_digest) != 64
            or any(character not in "0123456789abcdef" for character in command_digest)
        ):
            raise ProtocolValidationError("remote scheduler command identity is invalid")
        return value

    @staticmethod
    def _process_identity(pid: int) -> tuple[int, int, str] | None:
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
            command = Path(f"/proc/{pid}/cmdline").read_bytes()
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError) as error:
            raise ProtocolValidationError("remote scheduler identity is unavailable") from error
        closing = stat.rfind(")")
        fields = stat[closing + 2 :].split() if closing > 0 else []
        if len(fields) < 20 or fields[0] == "Z":
            return None
        try:
            process_group_id = int(fields[2])
            start_time_ticks = int(fields[19])
        except ValueError as error:
            raise ProtocolValidationError("remote scheduler process identity is invalid") from error
        return start_time_ticks, process_group_id, sha256(command).hexdigest()

    def _scheduler_running(self, scheduler: dict[str, object] | None) -> bool:
        if scheduler is None:
            return False
        pid = scheduler["pid"]
        if type(pid) is not int:
            raise ProtocolValidationError("remote scheduler PID is invalid")
        identity = self._process_identity(pid)
        if identity is None:
            return False
        expected = (
            scheduler["start_time_ticks"],
            scheduler["process_group_id"],
            scheduler["command_sha256"],
        )
        if identity != expected:
            raise ProtocolValidationError("remote scheduler process identity changed")
        return True

    def _start_scheduler(self) -> tuple[int, bool]:
        scheduler = self._load_scheduler()
        if self._scheduler_running(scheduler):
            return int(scheduler["pid"]), False
        self.log_dir.mkdir(parents=True, exist_ok=True)
        control_log = self.log_dir / "queue-manager.log"
        command = self._scheduler_command()
        with control_log.open("ab") as stream:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        identity = self._process_identity(process.pid)
        expected_command_sha256 = _command_sha256(command)
        if identity is None or identity[1] != process.pid or identity[2] != expected_command_sha256:
            raise ProtocolValidationError("remote scheduler failed identity verification")
        write_json_atomic(
            self.pid_path,
            {
                "command_sha256": expected_command_sha256,
                "kind": "aris_transport_scheduler",
                "manifest_sha256": self.manifest.manifest_sha256,
                "pid": process.pid,
                "process_group_id": identity[1],
                "schema_version": 1,
                "start_time_ticks": identity[0],
            },
        )
        return process.pid, True

    def submit(self) -> ArisTransportReceipt:
        with self._operation_lock():
            self._verify_authorities()
            existing = self._load_receipt()
            if existing is not None:
                return existing
            self._persist_manifest()
            cwd = self._stage_workspace()
            write_json_atomic(self.queue_manifest_path, self._queue_manifest(cwd))
            self._start_scheduler()
            return self._receipt(ArisTransportStatus.ACCEPTED, "aris-submission-accepted")

    def _job_state(self) -> str | None:
        if not self.queue_state_path.is_file():
            return None
        value = parse_json_object(
            self.queue_state_path.read_text(encoding="utf-8"),
            context="ARIS queue state",
        )
        jobs = value.get("jobs")
        if not isinstance(jobs, list):
            raise ProtocolValidationError("ARIS queue state jobs are invalid")
        matches = [
            item for item in jobs if isinstance(item, dict) and item.get("id") == self.job_id
        ]
        if len(matches) != 1 or not isinstance(matches[0].get("status"), str):
            raise ProtocolValidationError("ARIS queue state job binding is invalid")
        return matches[0]["status"]

    def _monitor_unlocked(self) -> ArisTransportReceipt:
        self._persist_manifest()
        if self.cancel_path.is_file():
            return self._receipt(ArisTransportStatus.CANCELLED, "aris-run-cancelled")
        state = self._job_state()
        if state is None:
            scheduler = self._load_scheduler()
            if scheduler is not None and not self._scheduler_running(scheduler):
                return self._receipt(
                    ArisTransportStatus.STUCK,
                    "aris-scheduler-not-running",
                )
        mapping = {
            None: (ArisTransportStatus.PENDING, "aris-scheduler-pending"),
            "pending": (ArisTransportStatus.PENDING, "aris-job-pending"),
            "running": (ArisTransportStatus.RUNNING, "aris-job-running"),
            "completed": (ArisTransportStatus.COMPLETED, "aris-job-completed"),
            "failed_oom": (ArisTransportStatus.FAILED, "aris-job-oom"),
            "failed_other": (ArisTransportStatus.FAILED, "aris-job-failed"),
            "stuck": (ArisTransportStatus.STUCK, "aris-job-stuck"),
        }
        try:
            status, reason = mapping[state]
        except KeyError as error:
            raise ProtocolValidationError("ARIS queue state is unsupported") from error
        return self._receipt(status, reason)

    def monitor(self) -> ArisTransportReceipt:
        with self._operation_lock():
            return self._monitor_unlocked()

    def cancel(self) -> ArisTransportReceipt:
        with self._operation_lock():
            existing = self._monitor_unlocked()
            if existing.status in {
                ArisTransportStatus.COMPLETED,
                ArisTransportStatus.CANCELLED,
            }:
                return existing
            scheduler = self._load_scheduler()
            if self._scheduler_running(scheduler):
                os.killpg(int(scheduler["process_group_id"]), signal.SIGTERM)
            if self.queue_state_path.is_file():
                state = parse_json_object(
                    self.queue_state_path.read_text(encoding="utf-8"),
                    context="ARIS queue state",
                )
                jobs = state.get("jobs", [])
                if isinstance(jobs, list):
                    for item in jobs:
                        screen_name = item.get("screen_name") if isinstance(item, dict) else None
                        if isinstance(screen_name, str) and screen_name == f"EQ_{self.job_id}":
                            subprocess.run(
                                ["screen", "-S", screen_name, "-X", "quit"],
                                capture_output=True,
                                timeout=5,
                                check=False,
                            )
            write_json_atomic(
                self.cancel_path,
                {
                    "kind": "aris_transport_cancellation",
                    "manifest_sha256": self.manifest.manifest_sha256,
                    "schema_version": 1,
                },
            )
            return self._receipt(ArisTransportStatus.CANCELLED, "aris-run-cancelled")

    def resume(self) -> ArisTransportReceipt:
        with self._operation_lock():
            if self._load_receipt() is None:
                self._verify_authorities()
                self._persist_manifest()
                cwd = self._stage_workspace()
                write_json_atomic(self.queue_manifest_path, self._queue_manifest(cwd))
                self._start_scheduler()
                return self._receipt(
                    ArisTransportStatus.ACCEPTED,
                    "aris-submission-recovered",
                )
            existing = self._monitor_unlocked()
            if existing.status in {
                ArisTransportStatus.PENDING,
                ArisTransportStatus.RUNNING,
                ArisTransportStatus.COMPLETED,
                ArisTransportStatus.CANCELLED,
                ArisTransportStatus.FAILED,
            }:
                return existing
            if (
                existing.status is not ArisTransportStatus.STUCK
                or existing.reason_code != "aris-scheduler-not-running"
            ):
                return existing
            self._verify_authorities()
            self._start_scheduler()
            return self._receipt(
                ArisTransportStatus.ACCEPTED,
                "aris-scheduler-resumed",
                attempt=existing.attempt,
            )


def _run(operation: str, manifest: ArisTransportManifest) -> ArisTransportReceipt:
    run = RemoteArisRun(manifest, ArisTransportRegistry.load_package())
    if operation == "submit":
        return run.submit()
    if operation == "monitor":
        return run.monitor()
    if operation == "cancel":
        return run.cancel()
    if operation == "resume":
        return run.resume()
    raise ProtocolValidationError("remote ARIS transport operation is invalid")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1 or arguments[0] not in {"submit", "monitor", "cancel", "resume"}:
        return 2
    try:
        raw = sys.stdin.read(128 * 1024 + 1)
        if len(raw.encode("utf-8")) > 128 * 1024:
            raise ProtocolValidationError("remote ARIS manifest is oversized")
        manifest = ArisTransportManifest.from_json(raw)
        receipt = _run(arguments[0], manifest)
    except (OSError, UnicodeError, ProtocolValidationError, subprocess.SubprocessError):
        return 2
    sys.stdout.write(json.dumps(receipt.to_dict(), allow_nan=False, sort_keys=True))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
