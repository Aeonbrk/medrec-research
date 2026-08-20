"""Read-only ARIS revision validation and last-known-good activation."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import ClassVar

from ._validation import (
    content_sha256,
    parse_json_object,
    require_identifier,
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
        raise ProtocolValidationError("ARIS clock must return an aware datetime")
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _revision(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ProtocolValidationError(f"{field} must be an immutable Git revision")
    return value


@dataclass(frozen=True, slots=True)
class ArisRevisionRecord:
    """Public-safe record of the revision selected for the current session."""

    observed_at: str
    candidate_revision: str | None
    active_revision: str | None
    last_known_good_revision: str | None
    candidate_valid: bool
    fallback_used: bool
    blockers: tuple[str, ...]
    manifest_sha256: str
    revision_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_single_line_public_string(self.observed_at, field="aris.observed_at")
        for name in ("candidate_revision", "active_revision", "last_known_good_revision"):
            _revision(getattr(self, name), field=f"aris.{name}")
        if type(self.candidate_valid) is not bool or type(self.fallback_used) is not bool:
            raise ProtocolValidationError("ARIS revision flags must be booleans")
        if self.candidate_valid and self.candidate_revision is None:
            raise ProtocolValidationError("valid ARIS candidate must have a revision")
        if self.fallback_used and self.last_known_good_revision is None:
            raise ProtocolValidationError("ARIS fallback must retain a last-known-good revision")
        if not self.candidate_valid and self.active_revision == self.candidate_revision:
            raise ProtocolValidationError("invalid ARIS candidate cannot be active")
        blockers = tuple(dict.fromkeys(self.blockers))
        for blocker in blockers:
            require_identifier(blocker, field="aris.blockers")
        object.__setattr__(self, "blockers", blockers)
        require_sha256(self.manifest_sha256, field="aris.manifest_sha256")
        expected = content_sha256(self._content())
        if self.revision_sha256:
            require_sha256(self.revision_sha256, field="aris.revision_sha256")
            if self.revision_sha256 != expected:
                raise ProtocolValidationError("ARIS revision digest does not match content")
        object.__setattr__(self, "revision_sha256", expected)

    def _content(self) -> dict[str, object]:
        return {
            "active_revision": self.active_revision,
            "blockers": list(self.blockers),
            "candidate_revision": self.candidate_revision,
            "candidate_valid": self.candidate_valid,
            "fallback_used": self.fallback_used,
            "kind": "aris_revision",
            "last_known_good_revision": self.last_known_good_revision,
            "manifest_sha256": self.manifest_sha256,
            "observed_at": self.observed_at,
            "schema_version": self.SCHEMA_VERSION,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._content(), "revision_sha256": self.revision_sha256}

    @classmethod
    def from_dict(cls, value: object) -> ArisRevisionRecord:
        payload = strict_fields(
            value,
            required=(
                "active_revision",
                "blockers",
                "candidate_revision",
                "candidate_valid",
                "fallback_used",
                "kind",
                "last_known_good_revision",
                "manifest_sha256",
                "observed_at",
                "revision_sha256",
                "schema_version",
            ),
            context="ARIS revision",
        )
        if payload.pop("kind") != "aris_revision" or payload.pop("schema_version") != 1:
            raise ProtocolValidationError("ARIS revision schema or kind is invalid")
        blockers = payload.pop("blockers")
        if not isinstance(blockers, list):
            raise ProtocolValidationError("ARIS revision blockers must be a list")
        payload["blockers"] = tuple(blockers)
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> ArisRevisionRecord:
        return cls.from_dict(parse_json_object(text, context="ARIS revision"))


class ArisBridge:
    """Validate and activate a local ARIS checkout without executing ARIS work."""

    def __init__(
        self,
        repository: Path,
        state_path: Path,
        *,
        clock: Clock,
        manifest_path: Path | None = None,
        runner: Runner = subprocess.run,
    ) -> None:
        self.repository = repository.resolve()
        self.state_path = state_path
        self.clock = clock
        self.manifest_path = manifest_path
        self.runner = runner

    def _git(self, *arguments: str) -> str | None:
        try:
            result = self.runner(
                ["git", "-C", str(self.repository), *arguments],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def _manifest_sha256(self) -> str:
        manifest = self.manifest_path or (
            self.repository / ".." / "medrec-research" / ".aris" / "installed-skills-codex.txt"
        )
        try:
            return sha256(manifest.resolve().read_bytes()).hexdigest()
        except (OSError, UnicodeError):
            return sha256(b"missing-aris-manifest").hexdigest()

    def _load_previous(self) -> ArisRevisionRecord | None:
        try:
            return ArisRevisionRecord.from_json(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ProtocolValidationError):
            return None

    def inspect(self) -> tuple[str | None, tuple[str, ...]]:
        blockers: list[str] = []
        if not self.repository.exists() or not (self.repository / ".git").exists():
            blockers.append("aris-checkout-missing")
            return None, tuple(blockers)
        branch = self._git("branch", "--show-current")
        if branch is None:
            blockers.append("aris-branch-unavailable")
        elif branch != "main":
            blockers.append("aris-not-on-main")
        status = self._git("status", "--porcelain")
        if status is None:
            blockers.append("aris-status-unavailable")
        elif status:
            blockers.append("aris-checkout-dirty")
        revision = self._git("rev-parse", "--verify", "HEAD^{commit}")
        try:
            revision = _revision(revision, field="aris.candidate_revision")
        except ProtocolValidationError:
            revision = None
        if revision is None:
            blockers.append("aris-revision-unavailable")
        latest = self._git("rev-parse", "--verify", "origin/main^{commit}")
        if latest is not None and revision is not None and latest != revision:
            blockers.append("aris-latest-candidate-mismatch")
        return revision, tuple(dict.fromkeys(blockers))

    def activate(self) -> ArisRevisionRecord:
        candidate, blockers = self.inspect()
        manifest_sha256 = self._manifest_sha256()
        previous = self._load_previous()
        candidate_valid = candidate is not None and not blockers
        if candidate_valid:
            active = candidate
            last_known_good = candidate
            fallback_used = False
        else:
            last_known_good = previous.last_known_good_revision if previous else None
            active = None
            fallback_used = last_known_good is not None
            if fallback_used:
                blockers = (*blockers, "aris-candidate-fallback")
            else:
                blockers = (*blockers, "aris-active-revision-missing")
        record = ArisRevisionRecord(
            observed_at=_timestamp(self.clock()),
            candidate_revision=candidate,
            active_revision=active,
            last_known_good_revision=last_known_good,
            candidate_valid=candidate_valid,
            fallback_used=fallback_used,
            blockers=tuple(dict.fromkeys(blockers)),
            manifest_sha256=manifest_sha256,
        )
        write_json_atomic(self.state_path, record.to_dict())
        return record


__all__ = ("ArisBridge", "ArisRevisionRecord")
