"""Fixed server-only transport contract for declaration-bound ARIS work."""

from __future__ import annotations

import subprocess
import tomllib
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from fcntl import LOCK_EX, LOCK_UN, flock
from hashlib import sha256
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import BinaryIO, ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    enum_member,
    parse_json_object,
    require_identifier,
    require_int,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
    write_json_atomic,
)
from .errors import ProtocolValidationError

Clock = Callable[[], datetime]
Runner = Callable[..., subprocess.CompletedProcess[str]]


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ProtocolValidationError("ARIS transport clock must return an aware datetime")
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ProtocolValidationError(f"transport artifact is unavailable: {path.name}") from error


def transport_package_sha256() -> str:
    """Bind the two fixed-wrapper modules without exposing their filesystem paths."""

    root = Path(__file__).resolve().parent
    return content_sha256(
        {
            name: _sha256_file(root / name)
            for name in ("aris_transport.py", "aris_transport_remote.py")
        }
    )


@contextmanager
def _exclusive_file_lock(path: Path) -> Iterator[BinaryIO]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        flock(stream.fileno(), LOCK_EX)
        try:
            yield stream
        finally:
            flock(stream.fileno(), LOCK_UN)


def _revision(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ProtocolValidationError(f"{field} must be an immutable Git revision")
    return value


def _relative_path(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ProtocolValidationError(f"{field} must be a nonempty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProtocolValidationError(f"{field} must be a normalized POSIX relative path")
    return value


def _absolute_path(value: object, *, field: str) -> str:
    if not isinstance(value, str) or "\\" in value:
        raise ProtocolValidationError(f"{field} must be an absolute POSIX path")
    path = PurePosixPath(value)
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise ProtocolValidationError(f"{field} must be an absolute POSIX path")
    return value


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ProtocolValidationError(f"{field} must be a nonempty list")
    result = tuple(value)
    for item in result:
        require_single_line_public_string(item, field=field)
    return result


@dataclass(frozen=True, slots=True)
class ArisResourceProfile:
    profile_id: str
    gpu_pool: tuple[int, ...]
    gpu_count: int
    max_parallel: int
    oom_retry_delay_seconds: int
    oom_retry_max_attempts: int

    def __post_init__(self) -> None:
        require_identifier(self.profile_id, field="transport.resource_profile_id")
        if not self.gpu_pool or any(type(item) is not int or item < 0 for item in self.gpu_pool):
            raise ProtocolValidationError("transport GPU pool must contain nonnegative integers")
        if len(set(self.gpu_pool)) != len(self.gpu_pool):
            raise ProtocolValidationError("transport GPU pool must not contain duplicates")
        require_int(self.gpu_count, field="transport.gpu_count", minimum=1)
        require_int(self.max_parallel, field="transport.max_parallel", minimum=1)
        require_int(
            self.oom_retry_delay_seconds,
            field="transport.oom_retry_delay_seconds",
            minimum=1,
        )
        require_int(
            self.oom_retry_max_attempts,
            field="transport.oom_retry_max_attempts",
            minimum=1,
        )
        if self.gpu_count > len(self.gpu_pool) or self.max_parallel > self.gpu_count:
            raise ProtocolValidationError("transport resource profile exceeds its GPU pool")


@dataclass(frozen=True, slots=True)
class ArisLaunchTemplate:
    launch_template_id: str
    enabled: bool
    blocker: str | None = None
    environment_id: str | None = None
    source_relative: str | None = None
    data_relative: str | None = None
    workdir_relative: str | None = None
    output_relative: str | None = None
    command: tuple[str, ...] = ()
    expected_output_relative: str | None = None

    def __post_init__(self) -> None:
        require_identifier(self.launch_template_id, field="transport.launch_template_id")
        if type(self.enabled) is not bool:
            raise ProtocolValidationError("transport launch enabled must be a boolean")
        if not self.enabled:
            if self.blocker is None:
                raise ProtocolValidationError("disabled transport launch must declare a blocker")
            require_identifier(self.blocker, field="transport.launch.blocker")
            if (
                any(
                    value is not None
                    for value in (
                        self.environment_id,
                        self.source_relative,
                        self.data_relative,
                        self.workdir_relative,
                        self.output_relative,
                        self.expected_output_relative,
                    )
                )
                or self.command
            ):
                raise ProtocolValidationError(
                    "disabled transport launch must not carry execution data"
                )
            return
        if self.blocker is not None:
            raise ProtocolValidationError("enabled transport launch must not declare a blocker")
        require_identifier(self.environment_id, field="transport.launch.environment_id")
        for name in (
            "source_relative",
            "data_relative",
            "workdir_relative",
            "output_relative",
            "expected_output_relative",
        ):
            _relative_path(getattr(self, name), field=f"transport.launch.{name}")
        if not self.command:
            raise ProtocolValidationError("enabled transport launch requires a fixed command")
        for item in self.command:
            require_single_line_public_string(item, field="transport.launch.command")


class ArisTransportRegistry:
    """Package-owned transport data that never crosses the browser boundary."""

    def __init__(
        self,
        *,
        project_id: str,
        target_id: str,
        ssh_profiles: Sequence[str],
        remote_python: str,
        remote_module: str,
        runtime_relative: str,
        queue_manager_relative: str,
        poll_seconds: int,
        resource_profiles: Sequence[ArisResourceProfile],
        launch_templates: Sequence[ArisLaunchTemplate],
        policy_sha256: str,
    ) -> None:
        require_identifier(project_id, field="transport.project_id")
        require_identifier(target_id, field="transport.target_id")
        profiles = tuple(ssh_profiles)
        if len(profiles) != 2 or len(set(profiles)) != 2:
            raise ProtocolValidationError(
                "transport must declare primary and fallback SSH profiles"
            )
        for profile in profiles:
            require_identifier(profile, field="transport.ssh_profile")
        _absolute_path(remote_python, field="transport.remote_python")
        require_identifier(remote_module, field="transport.remote_module")
        _relative_path(runtime_relative, field="transport.runtime_relative")
        _relative_path(queue_manager_relative, field="transport.queue_manager_relative")
        require_int(poll_seconds, field="transport.poll_seconds", minimum=5)
        require_sha256(policy_sha256, field="transport.policy_sha256")
        profiles_by_id = {item.profile_id: item for item in resource_profiles}
        launches_by_id = {item.launch_template_id: item for item in launch_templates}
        if len(profiles_by_id) != len(tuple(resource_profiles)) or not profiles_by_id:
            raise ProtocolValidationError("transport resource profiles must be unique and nonempty")
        if len(launches_by_id) != len(tuple(launch_templates)) or not launches_by_id:
            raise ProtocolValidationError("transport launch templates must be unique and nonempty")
        self.project_id = project_id
        self.target_id = target_id
        self.ssh_profiles = profiles
        self.remote_python = remote_python
        self.remote_module = remote_module
        self.runtime_relative = runtime_relative
        self.queue_manager_relative = queue_manager_relative
        self.poll_seconds = poll_seconds
        self.policy_sha256 = policy_sha256
        self._resource_profiles = profiles_by_id
        self._launch_templates = launches_by_id

    @classmethod
    def load_package(cls) -> ArisTransportRegistry:
        resource = files("medrec_research.resources").joinpath("aris-transport.toml")
        return cls._from_payload(tomllib.loads(resource.read_text(encoding="utf-8")))

    @classmethod
    def _from_payload(cls, value: object) -> ArisTransportRegistry:
        payload = strict_fields(
            value,
            required=(
                "launch_templates",
                "poll_seconds",
                "project_id",
                "queue_manager_relative",
                "remote_module",
                "remote_python",
                "resource_profiles",
                "runtime_relative",
                "schema_version",
                "ssh_profiles",
                "target_id",
            ),
            context="ARIS transport registry",
        )
        policy_sha256 = content_sha256(payload)
        if payload.pop("schema_version") != 1:
            raise ProtocolValidationError("ARIS transport registry version must be 1")
        resource_values = payload.pop("resource_profiles")
        if not isinstance(resource_values, Mapping):
            raise ProtocolValidationError("transport resource_profiles must be a table")
        resource_profiles = []
        for profile_id, item in resource_values.items():
            require_identifier(profile_id, field="transport.resource_profile_id")
            fields = strict_fields(
                item,
                required=(
                    "gpu_count",
                    "gpu_pool",
                    "max_parallel",
                    "oom_retry_delay_seconds",
                    "oom_retry_max_attempts",
                ),
                context="ARIS resource profile",
            )
            gpu_pool = fields.pop("gpu_pool")
            if not isinstance(gpu_pool, list):
                raise ProtocolValidationError("transport gpu_pool must be a list")
            resource_profiles.append(
                ArisResourceProfile(profile_id=profile_id, gpu_pool=tuple(gpu_pool), **fields)
            )
        launch_values = payload.pop("launch_templates")
        if not isinstance(launch_values, list):
            raise ProtocolValidationError("transport launch_templates must be a list")
        launch_templates = []
        for item in launch_values:
            base = strict_fields(
                item,
                required=("enabled", "launch_template_id"),
                optional=(
                    "blocker",
                    "command",
                    "data_relative",
                    "environment_id",
                    "expected_output_relative",
                    "output_relative",
                    "source_relative",
                    "workdir_relative",
                ),
                context="ARIS launch template",
            )
            command = base.pop("command", [])
            if not isinstance(command, list):
                raise ProtocolValidationError("transport launch command must be a list")
            launch_templates.append(ArisLaunchTemplate(command=tuple(command), **base))
        ssh_profiles = payload.pop("ssh_profiles")
        if not isinstance(ssh_profiles, list):
            raise ProtocolValidationError("transport ssh_profiles must be a list")
        return cls(
            ssh_profiles=tuple(ssh_profiles),
            resource_profiles=tuple(resource_profiles),
            launch_templates=tuple(launch_templates),
            policy_sha256=policy_sha256,
            **payload,
        )

    def resource_profile(self, profile_id: str) -> ArisResourceProfile:
        try:
            return self._resource_profiles[profile_id]
        except KeyError as error:
            raise ProtocolValidationError("transport resource profile is not registered") from error

    def launch_template(self, launch_template_id: str) -> ArisLaunchTemplate:
        try:
            return self._launch_templates[launch_template_id]
        except KeyError as error:
            raise ProtocolValidationError("transport launch template is not registered") from error

    def require_enabled_launch(self, launch_template_id: str) -> ArisLaunchTemplate:
        template = self.launch_template(launch_template_id)
        if not template.enabled:
            raise ProtocolValidationError(template.blocker or "transport-launch-disabled")
        return template

    def ssh_profile(self, *, fallback_used: bool) -> str:
        if type(fallback_used) is not bool:
            raise ProtocolValidationError("transport fallback flag must be boolean")
        return self.ssh_profiles[1 if fallback_used else 0]


@dataclass(frozen=True, slots=True)
class ArisTransportManifest:
    request_sha256: str
    submission_sha256: str
    declaration_sha256: str
    contract_sha256: str
    h1_approval_sha256: str
    preflight_sha256: str
    transport_policy_sha256: str
    transport_package_sha256: str
    queue_manager_sha256: str
    aris_revision: str
    project_id: str
    target_id: str
    lane_id: str
    action_id: str
    source_revision: str
    environment_id: str
    resource_profile_id: str
    command_template_id: str
    launch_template_id: str
    evidence_schema_id: str
    source_path_id: str
    data_path_id: str
    output_path_id: str
    max_attempts: int
    gpu_count: int
    manifest_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 2

    def __post_init__(self) -> None:
        for name in (
            "request_sha256",
            "submission_sha256",
            "declaration_sha256",
            "contract_sha256",
            "h1_approval_sha256",
            "preflight_sha256",
            "transport_policy_sha256",
            "transport_package_sha256",
            "queue_manager_sha256",
        ):
            require_sha256(getattr(self, name), field=f"transport_manifest.{name}")
        _revision(self.aris_revision, field="transport_manifest.aris_revision")
        _revision(self.source_revision, field="transport_manifest.source_revision")
        for name in (
            "project_id",
            "target_id",
            "lane_id",
            "action_id",
            "environment_id",
            "resource_profile_id",
            "command_template_id",
            "launch_template_id",
            "evidence_schema_id",
            "source_path_id",
            "data_path_id",
            "output_path_id",
        ):
            require_identifier(getattr(self, name), field=f"transport_manifest.{name}")
        require_int(self.max_attempts, field="transport_manifest.max_attempts", minimum=1)
        require_int(self.gpu_count, field="transport_manifest.gpu_count", minimum=1)
        expected = content_sha256(self._content())
        if self.manifest_sha256:
            require_sha256(self.manifest_sha256, field="transport_manifest.manifest_sha256")
            if self.manifest_sha256 != expected:
                raise ProtocolValidationError(
                    "ARIS transport manifest digest does not match content"
                )
        object.__setattr__(self, "manifest_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "aris_revision": self.aris_revision,
            "command_template_id": self.command_template_id,
            "contract_sha256": self.contract_sha256,
            "data_path_id": self.data_path_id,
            "declaration_sha256": self.declaration_sha256,
            "environment_id": self.environment_id,
            "evidence_schema_id": self.evidence_schema_id,
            "gpu_count": self.gpu_count,
            "h1_approval_sha256": self.h1_approval_sha256,
            "kind": "aris_transport_manifest",
            "lane_id": self.lane_id,
            "launch_template_id": self.launch_template_id,
            "max_attempts": self.max_attempts,
            "output_path_id": self.output_path_id,
            "preflight_sha256": self.preflight_sha256,
            "project_id": self.project_id,
            "queue_manager_sha256": self.queue_manager_sha256,
            "request_sha256": self.request_sha256,
            "resource_profile_id": self.resource_profile_id,
            "schema_version": self.SCHEMA_VERSION,
            "source_path_id": self.source_path_id,
            "source_revision": self.source_revision,
            "submission_sha256": self.submission_sha256,
            "target_id": self.target_id,
            "transport_package_sha256": self.transport_package_sha256,
            "transport_policy_sha256": self.transport_policy_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "manifest_sha256": self.manifest_sha256}

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> ArisTransportManifest:
        payload = strict_fields(
            value,
            required=(
                "action_id",
                "aris_revision",
                "command_template_id",
                "contract_sha256",
                "data_path_id",
                "declaration_sha256",
                "environment_id",
                "evidence_schema_id",
                "gpu_count",
                "h1_approval_sha256",
                "kind",
                "lane_id",
                "launch_template_id",
                "manifest_sha256",
                "max_attempts",
                "output_path_id",
                "preflight_sha256",
                "project_id",
                "queue_manager_sha256",
                "request_sha256",
                "resource_profile_id",
                "schema_version",
                "source_path_id",
                "source_revision",
                "submission_sha256",
                "target_id",
                "transport_package_sha256",
                "transport_policy_sha256",
            ),
            context="ARIS transport manifest",
        )
        if payload.pop("kind") != "aris_transport_manifest" or payload.pop("schema_version") != 2:
            raise ProtocolValidationError("ARIS transport manifest schema or kind is invalid")
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> ArisTransportManifest:
        return cls.from_dict(parse_json_object(text, context="ARIS transport manifest"))


class ArisTransportStatus(StrEnum):
    ACCEPTED = "accepted"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STUCK = "stuck"
    CANCELLED = "cancelled"
    TRANSPORT_FAILURE = "transport_failure"


_TERMINAL_TRANSPORT_STATUSES = frozenset(
    {
        ArisTransportStatus.COMPLETED,
        ArisTransportStatus.FAILED,
        ArisTransportStatus.STUCK,
        ArisTransportStatus.CANCELLED,
    }
)


@dataclass(frozen=True, slots=True)
class ArisTransportReceipt:
    request_sha256: str
    manifest_sha256: str
    aris_revision: str
    attempt: int
    status: ArisTransportStatus | str
    reason_code: str
    observed_at: str
    scheduler_job_id: str | None = None
    receipt_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_sha256(self.request_sha256, field="transport_receipt.request_sha256")
        require_sha256(self.manifest_sha256, field="transport_receipt.manifest_sha256")
        _revision(self.aris_revision, field="transport_receipt.aris_revision")
        require_int(self.attempt, field="transport_receipt.attempt", minimum=1)
        object.__setattr__(
            self,
            "status",
            enum_member(ArisTransportStatus, self.status, field="transport_receipt.status"),
        )
        require_identifier(self.reason_code, field="transport_receipt.reason_code")
        require_single_line_public_string(self.observed_at, field="transport_receipt.observed_at")
        if self.scheduler_job_id is not None:
            require_identifier(self.scheduler_job_id, field="transport_receipt.scheduler_job_id")
        expected = content_sha256(self._content())
        if self.receipt_sha256:
            require_sha256(self.receipt_sha256, field="transport_receipt.receipt_sha256")
            if self.receipt_sha256 != expected:
                raise ProtocolValidationError(
                    "ARIS transport receipt digest does not match content"
                )
        object.__setattr__(self, "receipt_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "aris_revision": self.aris_revision,
            "attempt": self.attempt,
            "kind": "aris_transport_receipt",
            "manifest_sha256": self.manifest_sha256,
            "observed_at": self.observed_at,
            "reason_code": self.reason_code,
            "request_sha256": self.request_sha256,
            "scheduler_job_id": self.scheduler_job_id,
            "schema_version": self.SCHEMA_VERSION,
            "status": self.status.value,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "receipt_sha256": self.receipt_sha256}

    @classmethod
    def from_dict(cls, value: object) -> ArisTransportReceipt:
        payload = strict_fields(
            value,
            required=(
                "aris_revision",
                "attempt",
                "kind",
                "manifest_sha256",
                "observed_at",
                "reason_code",
                "receipt_sha256",
                "request_sha256",
                "scheduler_job_id",
                "schema_version",
                "status",
            ),
            context="ARIS transport receipt",
        )
        if payload.pop("kind") != "aris_transport_receipt" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("ARIS transport receipt schema or kind is invalid")
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> ArisTransportReceipt:
        return cls.from_dict(parse_json_object(text, context="ARIS transport receipt"))


class FixedArisTransport:
    """Invoke one fixed remote module; no caller can supply host, argv, or paths."""

    def __init__(
        self,
        receipt_dir: Path,
        *,
        clock: Clock,
        registry: ArisTransportRegistry | None = None,
        runner: Runner = subprocess.run,
        timeout_seconds: int = 20,
    ) -> None:
        self.receipt_dir = receipt_dir
        self.clock = clock
        self.registry = registry or ArisTransportRegistry.load_package()
        self.runner = runner
        self.timeout_seconds = timeout_seconds

    def _path(self, request_sha256: str) -> Path:
        require_sha256(request_sha256, field="transport.request_sha256")
        return self.receipt_dir / f"{request_sha256}.json"

    def _lock_path(self, request_sha256: str) -> Path:
        require_sha256(request_sha256, field="transport.request_sha256")
        return self.receipt_dir / ".locks" / f"{request_sha256}.lock"

    def _validate_policy(self, manifest: ArisTransportManifest) -> None:
        if manifest.transport_policy_sha256 != self.registry.policy_sha256:
            raise ProtocolValidationError("ARIS transport policy binding changed")
        if manifest.transport_package_sha256 != transport_package_sha256():
            raise ProtocolValidationError("ARIS transport package binding changed")

    def load(self, request_sha256: str) -> ArisTransportReceipt | None:
        path = self._path(request_sha256)
        if not path.is_file():
            return None
        try:
            return ArisTransportReceipt.from_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ProtocolValidationError) as error:
            raise ProtocolValidationError("ARIS transport receipt is invalid") from error

    def records(self) -> tuple[ArisTransportReceipt, ...]:
        if not self.receipt_dir.is_dir():
            return ()
        records = []
        for path in sorted(self.receipt_dir.glob("*.json")):
            try:
                records.append(ArisTransportReceipt.from_json(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeError, ProtocolValidationError) as error:
                raise ProtocolValidationError(
                    f"ARIS transport receipt is invalid: {path.name}"
                ) from error
        return tuple(records)

    def _failure(self, manifest: ArisTransportManifest, reason_code: str) -> ArisTransportReceipt:
        return ArisTransportReceipt(
            request_sha256=manifest.request_sha256,
            manifest_sha256=manifest.manifest_sha256,
            aris_revision=manifest.aris_revision,
            attempt=max((self.load(manifest.request_sha256) or _EMPTY_RECEIPT).attempt, 1),
            status=ArisTransportStatus.TRANSPORT_FAILURE,
            reason_code=reason_code,
            observed_at=_timestamp(self.clock()),
        )

    def _invoke(
        self,
        operation: str,
        manifest: ArisTransportManifest,
        *,
        fallback_used: bool,
    ) -> ArisTransportReceipt:
        if operation not in {"submit", "monitor", "cancel", "resume"}:
            raise ProtocolValidationError("ARIS transport operation is not fixed")
        profile = self.registry.ssh_profile(fallback_used=fallback_used)
        command = [
            "rtk",
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={self.timeout_seconds}",
            profile,
            self.registry.remote_python,
            "-m",
            self.registry.remote_module,
            operation,
        ]
        try:
            result = self.runner(
                command,
                input=manifest.to_json(),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds + 5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return self._failure(manifest, "aris-transport-unreachable")
        if result.returncode != 0:
            return self._failure(manifest, "aris-transport-command-failed")
        if len(result.stdout.encode("utf-8")) > 64 * 1024:
            return self._failure(manifest, "aris-transport-output-oversized")
        try:
            receipt = ArisTransportReceipt.from_json(result.stdout)
        except (UnicodeError, ProtocolValidationError):
            return self._failure(manifest, "aris-transport-output-invalid")
        if (
            receipt.request_sha256 != manifest.request_sha256
            or receipt.manifest_sha256 != manifest.manifest_sha256
            or receipt.aris_revision != manifest.aris_revision
        ):
            return self._failure(manifest, "aris-transport-binding-mismatch")
        return receipt

    def _persist(self, receipt: ArisTransportReceipt) -> ArisTransportReceipt:
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(self._path(receipt.request_sha256), receipt.to_dict())
        return receipt

    def submit(
        self,
        manifest: ArisTransportManifest,
        *,
        fallback_used: bool,
    ) -> ArisTransportReceipt:
        with _exclusive_file_lock(self._lock_path(manifest.request_sha256)):
            self._validate_policy(manifest)
            existing = self.load(manifest.request_sha256)
            if existing is not None:
                if existing.manifest_sha256 != manifest.manifest_sha256:
                    raise ProtocolValidationError(
                        "ARIS transport submission conflicts with history"
                    )
                return existing
            self.registry.require_enabled_launch(manifest.launch_template_id)
            profile = self.registry.resource_profile(manifest.resource_profile_id)
            if manifest.gpu_count > profile.gpu_count:
                raise ProtocolValidationError("ARIS transport manifest exceeds resource profile")
            if manifest.max_attempts > profile.oom_retry_max_attempts:
                raise ProtocolValidationError("ARIS transport manifest exceeds retry profile")
            return self._persist(self._invoke("submit", manifest, fallback_used=fallback_used))

    def monitor(
        self,
        manifest: ArisTransportManifest,
        *,
        fallback_used: bool,
    ) -> ArisTransportReceipt:
        with _exclusive_file_lock(self._lock_path(manifest.request_sha256)):
            self._validate_policy(manifest)
            existing = self.load(manifest.request_sha256)
            if existing is None or existing.manifest_sha256 != manifest.manifest_sha256:
                raise ProtocolValidationError("ARIS transport monitor requires a bound submission")
            if existing.status in _TERMINAL_TRANSPORT_STATUSES or (
                existing.status is ArisTransportStatus.TRANSPORT_FAILURE
            ):
                return existing
            return self._persist(self._invoke("monitor", manifest, fallback_used=fallback_used))

    def cancel(
        self,
        manifest: ArisTransportManifest,
        *,
        fallback_used: bool,
    ) -> ArisTransportReceipt:
        with _exclusive_file_lock(self._lock_path(manifest.request_sha256)):
            self._validate_policy(manifest)
            existing = self.load(manifest.request_sha256)
            if existing is None or existing.manifest_sha256 != manifest.manifest_sha256:
                raise ProtocolValidationError("ARIS transport cancel requires a bound submission")
            if existing.status in _TERMINAL_TRANSPORT_STATUSES:
                return existing
            return self._persist(self._invoke("cancel", manifest, fallback_used=fallback_used))

    def resume(
        self,
        manifest: ArisTransportManifest,
        *,
        fallback_used: bool,
    ) -> ArisTransportReceipt:
        with _exclusive_file_lock(self._lock_path(manifest.request_sha256)):
            self._validate_policy(manifest)
            existing = self.load(manifest.request_sha256)
            if existing is None or existing.manifest_sha256 != manifest.manifest_sha256:
                raise ProtocolValidationError("ARIS transport resume requires a bound submission")
            if existing.status is not ArisTransportStatus.TRANSPORT_FAILURE:
                raise ProtocolValidationError(
                    "ARIS transport resume requires explicit recovery state"
                )
            return self._persist(self._invoke("resume", manifest, fallback_used=fallback_used))


_EMPTY_RECEIPT = ArisTransportReceipt(
    request_sha256="0" * 64,
    manifest_sha256="0" * 64,
    aris_revision="0" * 40,
    attempt=1,
    status=ArisTransportStatus.TRANSPORT_FAILURE,
    reason_code="transport-uninitialized",
    observed_at="1970-01-01T00:00:00Z",
)


__all__ = (
    "ArisLaunchTemplate",
    "ArisResourceProfile",
    "ArisTransportManifest",
    "ArisTransportReceipt",
    "ArisTransportRegistry",
    "ArisTransportStatus",
    "FixedArisTransport",
    "transport_package_sha256",
)
