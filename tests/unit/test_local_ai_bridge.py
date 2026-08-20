from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from medrec_research.errors import ProtocolValidationError
from medrec_research.local_ai_bridge import LocalAIBridge

QUESTIONNAIRE = [{"id": "problem", "label": "Problem", "provenance": "derived", "value": "bounded"}]


def test_bridge_is_honestly_unavailable_by_default(tmp_path: Path) -> None:
    bridge = LocalAIBridge(tmp_path, enabled=False)

    result = bridge.run(operation="draft", request_id="req-123", questionnaire=QUESTIONNAIRE)

    assert result.status == "unavailable"
    assert result.reason_code == "local-ai-bridge-not-configured"
    assert result.output is None


def test_bridge_rejects_unbounded_operation(tmp_path: Path) -> None:
    bridge = LocalAIBridge(tmp_path, enabled=False)

    with pytest.raises(ProtocolValidationError, match="operation"):
        bridge.run(operation="shell", request_id="req-123", questionnaire=QUESTIONNAIRE)


def test_configured_bridge_uses_fixed_command_and_bounds_output(tmp_path: Path) -> None:
    calls: list[tuple[list[str], str]] = []

    def runner(command: list[str], *, input: str, **_: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, input))
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text("draft text", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    bridge = LocalAIBridge(tmp_path, enabled=True, runner=runner)
    result = bridge.run(operation="challenge", request_id="req-123", questionnaire=QUESTIONNAIRE)

    assert result.status == "ready"
    assert result.output == "draft text"
    assert calls and calls[0][0][:4] == [
        "/opt/homebrew/bin/codex",
        "exec",
        "--ephemeral",
        "--sandbox",
    ]


@pytest.mark.parametrize(
    ("exception", "returncode", "reason_code"),
    [
        (subprocess.TimeoutExpired("codex", 1), 0, "local-ai-timeout"),
        (None, 1, "local-ai-command-failed"),
    ],
)
def test_bridge_reports_command_failures(
    tmp_path: Path,
    exception: BaseException | None,
    returncode: int,
    reason_code: str,
) -> None:
    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if exception is not None:
            raise exception
        return subprocess.CompletedProcess(command, returncode, "", "")

    result = LocalAIBridge(tmp_path, enabled=True, runner=runner).run(
        operation="draft", request_id="req-123", questionnaire=QUESTIONNAIRE
    )

    assert result.status == "error"
    assert result.reason_code == reason_code
