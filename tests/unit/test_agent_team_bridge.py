from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from medrec_research.agent_team_bridge import (
    AgentTeamBridge,
    TeamCompositionPreset,
)
from medrec_research.errors import ProtocolValidationError

QUESTIONNAIRE = [{"id": "problem", "label": "Problem", "provenance": "derived", "value": "bounded"}]


def test_team_bridge_preset_compositions(tmp_path: Path) -> None:
    bridge = AgentTeamBridge(tmp_path, enabled=True)

    review_team = bridge.compose_team(TeamCompositionPreset.REVIEW_TEAM)
    assert review_team.team_size == 3
    assert review_team.complexity == "moderate"
    assert len(review_team.teammates) == 3
    assert all(t.read_only for t in review_team.teammates)

    debug_team = bridge.compose_team(TeamCompositionPreset.DEBUG_TEAM)
    assert debug_team.team_size == 3
    assert any("Hypothesis" in t.focus_dimension for t in debug_team.teammates)

    feature_team = bridge.compose_team(TeamCompositionPreset.FEATURE_TEAM)
    assert feature_team.team_size == 3
    assert feature_team.complexity == "complex"

    fullstack_team = bridge.compose_team(TeamCompositionPreset.FULLSTACK_TEAM)
    assert fullstack_team.team_size == 4
    assert fullstack_team.complexity == "very_complex"


def test_team_bridge_run_team(tmp_path: Path) -> None:
    calls: list[tuple[list[str], str]] = []

    def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, ""))
        output_path = Path(command[command.index("-o") + 1])
        output_path.write_text("Team deliberation findings", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    bridge = AgentTeamBridge(tmp_path, enabled=True, runner=runner)
    result = bridge.run(
        operation="challenge",
        request_id="req-test-team",
        questionnaire=QUESTIONNAIRE,
    )

    assert result.status == "ready"
    assert result.output == "Team deliberation findings"
    assert result.team_config is not None
    assert result.team_config.preset == TeamCompositionPreset.REVIEW_TEAM.value
    assert calls and calls[0][0][:4] == [
        "/opt/homebrew/bin/codex",
        "exec",
        "--model",
        "gpt-5.6-sol",
    ]


def test_team_bridge_invalid_operation(tmp_path: Path) -> None:
    bridge = AgentTeamBridge(tmp_path, enabled=True)

    with pytest.raises(ProtocolValidationError, match="operation"):
        bridge.run(
            operation="unbounded_op",
            request_id="req-bad",
            questionnaire=QUESTIONNAIRE,
        )


def test_team_bridge_disabled_returns_honest_status(tmp_path: Path) -> None:
    bridge = AgentTeamBridge(tmp_path, enabled=False)
    result = bridge.run(
        operation="draft",
        request_id="req-disabled",
        questionnaire=QUESTIONNAIRE,
    )

    assert result.status == "unavailable"
    assert result.reason_code == "local-ai-bridge-not-configured"
