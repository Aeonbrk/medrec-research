"""Bounded local Codex bridge for contract drafting and challenge prompts."""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ._validation import canonical_json, require_identifier
from .errors import ProtocolValidationError

BridgeStatus = Literal["unavailable", "ready", "error"]
_OPERATIONS = frozenset({"draft", "challenge"})
_EXECUTABLE = "/opt/homebrew/bin/codex"
_MAX_OUTPUT = 12_000

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True, slots=True)
class LocalAIResult:
    status: BridgeStatus
    operation: str
    request_id: str
    reason_code: str
    output: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "h1_written": False,
            "kind": "contract_ai_result",
            "operation": self.operation,
            "output": self.output,
            "reason_code": self.reason_code,
            "request_id": self.request_id,
            "schema_version": 1,
            "status": self.status,
        }


class LocalAIBridge:
    """Invoke only the fixed, read-only local Codex command when explicitly enabled."""

    def __init__(
        self,
        root: Path,
        *,
        enabled: bool | None = None,
        runner: Runner = subprocess.run,
        executable: str = _EXECUTABLE,
        timeout_seconds: int = 20,
    ) -> None:
        self.root = root.resolve()
        self.enabled = (
            os.environ.get("MEDREC_LOCAL_AI_BRIDGE") == "1" if enabled is None else enabled
        )
        self.runner = runner
        if executable != _EXECUTABLE:
            raise ValueError("local AI executable is fixed")
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 60:
            raise ValueError("local AI timeout must be between 1 and 60 seconds")
        self.timeout_seconds = timeout_seconds

    def availability(self) -> tuple[Literal["unavailable", "ready"], str]:
        if not self.enabled:
            return "unavailable", "local-ai-bridge-not-configured"
        if self.runner is subprocess.run and not (
            Path(_EXECUTABLE).is_file() and os.access(_EXECUTABLE, os.X_OK)
        ):
            return "unavailable", "local-ai-executable-unavailable"
        return "ready", "local-ai-bridge-ready"

    def run(
        self,
        *,
        operation: str,
        request_id: str,
        questionnaire: list[dict[str, str]],
    ) -> LocalAIResult:
        if not isinstance(operation, str) or operation not in _OPERATIONS:
            raise ProtocolValidationError("contract AI operation is not permitted")
        require_identifier(request_id, field="request_id")
        if len(request_id) > 128:
            raise ProtocolValidationError("request_id is too long")
        if not isinstance(questionnaire, list) or any(
            not isinstance(item, dict)
            or set(item) != {"id", "label", "provenance", "value"}
            or any(not isinstance(value, str) for value in item.values())
            for item in questionnaire
        ):
            raise ProtocolValidationError("contract AI questionnaire is invalid")
        availability, reason_code = self.availability()
        if availability == "unavailable":
            return LocalAIResult(
                status="unavailable",
                operation=operation,
                request_id=request_id,
                reason_code=reason_code,
            )
        prompt = canonical_json(
            {
                "instruction": (
                    "Review the registered research contract. Return a bounded plain-text "
                    "draft or challenge. Do not approve H1, change scientific semantics, "
                    "invent evidence, or request secrets."
                ),
                "operation": operation,
                "questionnaire": questionnaire,
            }
        )
        try:
            with tempfile.TemporaryDirectory(prefix="medrec-local-ai-") as directory:
                output_path = Path(directory) / "response.txt"
                result = self.runner(
                    [
                        _EXECUTABLE,
                        "exec",
                        "--ephemeral",
                        "--sandbox",
                        "read-only",
                        "--ask-for-approval",
                        "never",
                        "--skip-git-repo-check",
                        "-C",
                        str(self.root),
                        "-o",
                        str(output_path),
                        "-",
                    ],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                if result.returncode != 0:
                    return LocalAIResult(
                        status="error",
                        operation=operation,
                        request_id=request_id,
                        reason_code="local-ai-command-failed",
                    )
                output = output_path.read_text(encoding="utf-8").strip()
        except subprocess.TimeoutExpired:
            return LocalAIResult(
                status="error",
                operation=operation,
                request_id=request_id,
                reason_code="local-ai-timeout",
            )
        except (OSError, UnicodeError, subprocess.SubprocessError):
            return LocalAIResult(
                status="error",
                operation=operation,
                request_id=request_id,
                reason_code="local-ai-transport-failure",
            )
        if not output:
            return LocalAIResult(
                status="error",
                operation=operation,
                request_id=request_id,
                reason_code="local-ai-empty-output",
            )
        if len(output) > _MAX_OUTPUT or any(
            ord(character) < 32 and character not in "\n\r\t" for character in output
        ):
            return LocalAIResult(
                status="error",
                operation=operation,
                request_id=request_id,
                reason_code="local-ai-output-invalid",
            )
        return LocalAIResult(
            status="ready",
            operation=operation,
            request_id=request_id,
            reason_code="local-ai-complete",
            output=output,
        )


__all__ = ("LocalAIBridge", "LocalAIResult")
