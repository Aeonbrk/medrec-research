"""Read-only remote execution plane preflight probe and observation records."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar

from ._validation import (
    content_sha256,
)
from .errors import ProtocolValidationError

Clock = Callable[[], datetime]
RunCommand = Callable[..., subprocess.CompletedProcess[str]]

_REMOTE_PROBE = r"""set -eu
printf 'identity=%s\n' "$(id -un)"
if test -d /root/zhb/medrec-research/.git; then
  printf 'checkout_exists=1\n'
  revision=$(git -C /root/zhb/medrec-research rev-parse HEAD 2>/dev/null || true)
  printf 'revision=%s\n' "$revision"
  if test -z "$(git -C /root/zhb/medrec-research status --porcelain 2>/dev/null)"; then
    printf 'checkout_clean=1\n'
  else
    printf 'checkout_clean=0\n'
  fi
else
  printf 'checkout_exists=0\nrevision=\ncheckout_clean=0\n'
fi
if test -n "${MEDREC_DATA_ROOT:-}" && test -d "$MEDREC_DATA_ROOT"; then
  printf 'data_root_ready=1\n'
else
  printf 'data_root_ready=0\n'
fi
if test -x /root/anaconda3/bin/conda; then
  printf 'conda_available=1\n'
else
  printf 'conda_available=0\n'
fi
if command -v nvidia-smi >/dev/null 2>&1; then
  gpu_rows=$(nvidia-smi \
    --query-gpu=memory.free,utilization.gpu \
    --format=csv,noheader,nounits 2>/dev/null || true)
  gpu_count=$(printf '%s\n' "$gpu_rows" | awk 'NF{count++} END{print count+0}')
  gpu_available=$(printf '%s\n' "$gpu_rows" | \
    awk -F',' '($1+0)>=20000 && ($2+0)<=10{count++} END{print count+0}')
  printf 'gpu_count=%s\ngpu_available=%s\n' "$gpu_count" "$gpu_available"
else
  printf 'gpu_count=0\ngpu_available=0\n'
fi
disk_free_kib=$(df -Pk /root/zhb 2>/dev/null | awk 'NR==2{printf "%.0f", $4}')
printf 'disk_free_kib=%s\n' "${disk_free_kib:-0}"
"""


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _immutable_revision(value: str | None) -> str | None:
    if (
        value is None
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        return None
    return value


def _parse_probe(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or key in values:
            raise ProtocolValidationError("remote preflight returned an invalid public-safe record")
        values[key] = value
    expected = {
        "checkout_clean",
        "checkout_exists",
        "conda_available",
        "data_root_ready",
        "disk_free_kib",
        "gpu_available",
        "gpu_count",
        "identity",
        "revision",
    }
    if set(values) != expected:
        raise ProtocolValidationError("remote preflight returned an incomplete public-safe record")
    return values


def _probe_integer(value: str) -> int:
    if not value.isascii() or not value.isdigit() or len(value) > 20:
        raise ProtocolValidationError("remote preflight capacity is invalid")
    return int(value)


@dataclass(frozen=True, slots=True)
class RemoteSessionPreflight:
    """Public-safe observation of the real 319 execution plane."""

    observed_at: str
    reachable: bool
    fallback_used: bool
    identity_ok: bool
    checkout_exists: bool
    checkout_clean: bool
    local_revision: str | None
    remote_revision: str | None
    revision_matches: bool
    data_root_ready: bool
    conda_available: bool
    environment_verified: bool
    gpu_count: int
    gpu_available: int
    disk_free_gib: int
    blockers: tuple[str, ...]
    preflight_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        if self.local_revision is not None and _immutable_revision(self.local_revision) is None:
            raise ProtocolValidationError("local_revision must be an immutable Git revision")
        if self.remote_revision is not None and _immutable_revision(self.remote_revision) is None:
            raise ProtocolValidationError("remote_revision must be an immutable Git revision")
        for value in (
            self.reachable,
            self.fallback_used,
            self.identity_ok,
            self.checkout_exists,
            self.checkout_clean,
            self.revision_matches,
            self.data_root_ready,
            self.conda_available,
            self.environment_verified,
        ):
            if type(value) is not bool:
                raise ProtocolValidationError("remote preflight flags must be booleans")
        capacity = (self.gpu_count, self.gpu_available, self.disk_free_gib)
        if any(type(value) is not int or value < 0 for value in capacity):
            raise ProtocolValidationError("remote preflight capacity must be nonnegative integers")
        blockers = tuple(dict.fromkeys(self.blockers))
        object.__setattr__(self, "blockers", blockers)
        expected = content_sha256(self._content())
        if self.preflight_sha256 and self.preflight_sha256 != expected:
            raise ProtocolValidationError("remote preflight digest does not match content")
        object.__setattr__(self, "preflight_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "blockers": list(self.blockers),
            "checkout_clean": self.checkout_clean,
            "checkout_exists": self.checkout_exists,
            "conda_available": self.conda_available,
            "data_root_ready": self.data_root_ready,
            "disk_free_gib": self.disk_free_gib,
            "environment_verified": self.environment_verified,
            "fallback_used": self.fallback_used,
            "gpu_available": self.gpu_available,
            "gpu_count": self.gpu_count,
            "identity_ok": self.identity_ok,
            "local_revision": self.local_revision,
            "observed_at": self.observed_at,
            "reachable": self.reachable,
            "remote_revision": self.remote_revision,
            "revision_matches": self.revision_matches,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._content(),
            "kind": "remote_session_preflight",
            "preflight_sha256": self.preflight_sha256,
            "schema_version": self.SCHEMA_VERSION,
        }


def run_remote_preflight(
    *,
    local_revision: str | None,
    clock: Clock,
    runner: RunCommand = subprocess.run,
    timeout_seconds: int = 12,
) -> RemoteSessionPreflight:
    """Try the documented 319 aliases and run one fixed read-only probe."""

    values: dict[str, str] | None = None
    fallback_used = False
    for index, profile in enumerate(("319-lab", "319-lab-via-server")):
        try:
            result = runner(
                [
                    "rtk",
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    f"ConnectTimeout={timeout_seconds}",
                    profile,
                    "sh",
                    "-s",
                ],
                input=_REMOTE_PROBE,
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 3,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode != 0:
            continue
        try:
            candidate = _parse_probe(result.stdout)
        except ProtocolValidationError:
            continue
        if candidate["identity"] != "root":
            continue
        values = candidate
        fallback_used = index == 1
        break

    local = _immutable_revision(local_revision)
    if values is None:
        return RemoteSessionPreflight(
            observed_at=_timestamp(clock()),
            reachable=False,
            fallback_used=False,
            identity_ok=False,
            checkout_exists=False,
            checkout_clean=False,
            local_revision=local,
            remote_revision=None,
            revision_matches=False,
            data_root_ready=False,
            conda_available=False,
            environment_verified=False,
            gpu_count=0,
            gpu_available=0,
            disk_free_gib=0,
            blockers=("remote-unreachable",),
        )

    remote = _immutable_revision(values["revision"])
    checkout_exists = values["checkout_exists"] == "1"
    checkout_clean = values["checkout_clean"] == "1"
    data_root_ready = values["data_root_ready"] == "1"
    conda_available = values["conda_available"] == "1"
    try:
        gpu_count = _probe_integer(values["gpu_count"])
        gpu_available = _probe_integer(values["gpu_available"])
        disk_free_kib = _probe_integer(values["disk_free_kib"])
    except ProtocolValidationError:
        return RemoteSessionPreflight(
            observed_at=_timestamp(clock()),
            reachable=False,
            fallback_used=fallback_used,
            identity_ok=True,
            checkout_exists=checkout_exists,
            checkout_clean=checkout_clean,
            local_revision=local,
            remote_revision=remote,
            revision_matches=False,
            data_root_ready=False,
            conda_available=False,
            environment_verified=False,
            gpu_count=0,
            gpu_available=0,
            disk_free_gib=0,
            blockers=("remote-preflight-invalid",),
        )

    revision_matches = local is not None and remote == local
    blockers: list[str] = []
    if not checkout_exists:
        blockers.append("remote-checkout-missing")
    elif not checkout_clean:
        blockers.append("remote-checkout-dirty")
    if not revision_matches:
        blockers.append("remote-revision-mismatch")
    if not data_root_ready:
        blockers.append("remote-data-root-missing")
    if not conda_available:
        blockers.append("remote-conda-unavailable")
    blockers.append("remote-environment-unverified")
    if gpu_available < 1:
        blockers.append("remote-gpu-unavailable")
    if disk_free_kib < 100 * 1024 * 1024:
        blockers.append("remote-disk-headroom-low")

    return RemoteSessionPreflight(
        observed_at=_timestamp(clock()),
        reachable=True,
        fallback_used=fallback_used,
        identity_ok=True,
        checkout_exists=checkout_exists,
        checkout_clean=checkout_clean,
        local_revision=local,
        remote_revision=remote,
        revision_matches=revision_matches,
        data_root_ready=data_root_ready,
        conda_available=conda_available,
        environment_verified=False,
        gpu_count=gpu_count,
        gpu_available=gpu_available,
        disk_free_gib=disk_free_kib // (1024 * 1024),
        blockers=tuple(dict.fromkeys(blockers)),
    )


__all__ = ("RemoteSessionPreflight", "run_remote_preflight")
