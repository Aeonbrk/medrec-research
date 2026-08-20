"""Multi-agent team bridge implementing team-composition-patterns for research workflows."""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Literal

from ._validation import require_identifier
from .errors import ProtocolValidationError

BridgeStatus = Literal["unavailable", "ready", "error"]
DisplayMode = Literal["tmux", "iterm2", "in-process"]
_MAX_OUTPUT = 32_000
_EXECUTABLE = "/opt/homebrew/bin/codex"

Runner = Callable[..., subprocess.CompletedProcess[str]]


class TeamCompositionPreset(StrEnum):
    REVIEW_TEAM = "review_team"
    DEBUG_TEAM = "debug_team"
    FEATURE_TEAM = "feature_team"
    FULLSTACK_TEAM = "fullstack_team"
    RESEARCH_TEAM = "research_team"
    SECURITY_TEAM = "security_team"
    MIGRATION_TEAM = "migration_team"


class AgentRole(StrEnum):
    TEAM_LEAD = "team-lead"
    TEAM_REVIEWER = "team-reviewer"
    TEAM_DEBUGGER = "team-debugger"
    TEAM_IMPLEMENTER = "team-implementer"
    GENERAL_PURPOSE = "general-purpose"
    EXPLORE = "Explore"
    PLAN = "Plan"


@dataclass(frozen=True, slots=True)
class TeammateSpec:
    role: AgentRole | str
    focus_dimension: str
    read_only: bool
    agent_id: str


@dataclass(frozen=True, slots=True)
class TeamCompositionConfig:
    preset: TeamCompositionPreset | str
    team_size: int
    display_mode: DisplayMode
    teammates: tuple[TeammateSpec, ...]
    complexity: Literal["simple", "moderate", "complex", "very_complex"]

    SCHEMA_VERSION: ClassVar[int] = 1

    @classmethod
    def create_preset(
        cls,
        preset: TeamCompositionPreset | str,
        *,
        display_mode: DisplayMode = "in-process",
    ) -> TeamCompositionConfig:
        preset_str = preset.value if isinstance(preset, TeamCompositionPreset) else str(preset)
        if preset_str == TeamCompositionPreset.REVIEW_TEAM.value:
            teammates = (
                TeammateSpec(
                    AgentRole.TEAM_REVIEWER, "Security & EHR Privacy", True, "reviewer-sec"
                ),
                TeammateSpec(
                    AgentRole.TEAM_REVIEWER, "Methodology & Performance", True, "reviewer-perf"
                ),
                TeammateSpec(
                    AgentRole.TEAM_REVIEWER, "Architecture & Lineage", True, "reviewer-arch"
                ),
            )
            return cls(preset_str, 3, display_mode, teammates, "moderate")
        if preset_str == TeamCompositionPreset.DEBUG_TEAM.value:
            teammates = (
                TeammateSpec(
                    AgentRole.TEAM_DEBUGGER, "CUDA / Resource OOM Hypothesis", True, "debug-h1"
                ),
                TeammateSpec(
                    AgentRole.TEAM_DEBUGGER, "Loss Divergence / NaN Hypothesis", True, "debug-h2"
                ),
                TeammateSpec(
                    AgentRole.TEAM_DEBUGGER, "Environment / Dependency Drift", True, "debug-h3"
                ),
            )
            return cls(preset_str, 3, display_mode, teammates, "moderate")
        if preset_str == TeamCompositionPreset.FEATURE_TEAM.value:
            teammates = (
                TeammateSpec(AgentRole.TEAM_LEAD, "Task Decomposition & Ownership", False, "lead"),
                TeammateSpec(
                    AgentRole.TEAM_IMPLEMENTER, "Adapter Wire Implementation", False, "impl-wire"
                ),
                TeammateSpec(
                    AgentRole.TEAM_IMPLEMENTER, "Evaluator & Invariant Tests", False, "impl-eval"
                ),
            )
            return cls(preset_str, 3, display_mode, teammates, "complex")
        if preset_str == TeamCompositionPreset.FULLSTACK_TEAM.value:
            teammates = (
                TeammateSpec(AgentRole.TEAM_LEAD, "Coordination", False, "lead"),
                TeammateSpec(AgentRole.TEAM_IMPLEMENTER, "Frontend Components", False, "frontend"),
                TeammateSpec(AgentRole.TEAM_IMPLEMENTER, "Backend Subsystems", False, "backend"),
                TeammateSpec(AgentRole.TEAM_IMPLEMENTER, "Test & Invariants", False, "tester"),
            )
            return cls(preset_str, 4, display_mode, teammates, "very_complex")
        if preset_str == TeamCompositionPreset.RESEARCH_TEAM.value:
            teammates = (
                TeammateSpec(AgentRole.EXPLORE, "PubMed & Clinical Prior Art", True, "res-pubmed"),
                TeammateSpec(
                    AgentRole.EXPLORE, "Benchmark Codebases & Upstream", True, "res-upstream"
                ),
                TeammateSpec(AgentRole.EXPLORE, "Method Novelty Matrix", True, "res-novelty"),
            )
            return cls(preset_str, 3, display_mode, teammates, "moderate")
        if preset_str == TeamCompositionPreset.SECURITY_TEAM.value:
            teammates = (
                TeammateSpec(
                    AgentRole.TEAM_REVIEWER, "EHR Privacy & De-identification", True, "sec-privacy"
                ),
                TeammateSpec(
                    AgentRole.TEAM_REVIEWER, "Token / Credential Leakage", True, "sec-creds"
                ),
                TeammateSpec(
                    AgentRole.TEAM_REVIEWER, "Supply Chain & Conda Locks", True, "sec-supply"
                ),
                TeammateSpec(
                    AgentRole.TEAM_REVIEWER, "Fail-closed Gate Invariants", True, "sec-gates"
                ),
            )
            return cls(preset_str, 4, display_mode, teammates, "very_complex")
        if preset_str == TeamCompositionPreset.MIGRATION_TEAM.value:
            teammates = (
                TeammateSpec(AgentRole.TEAM_LEAD, "Migration Plan Coordinator", False, "lead"),
                TeammateSpec(AgentRole.TEAM_IMPLEMENTER, "Core Migration", False, "impl-core"),
                TeammateSpec(
                    AgentRole.TEAM_IMPLEMENTER, "Adapter Compatibility", False, "impl-adapter"
                ),
                TeammateSpec(
                    AgentRole.TEAM_REVIEWER, "Verification & Regressions", True, "reviewer"
                ),
            )
            return cls(preset_str, 4, display_mode, teammates, "very_complex")
        raise ProtocolValidationError(f"unknown team composition preset: {preset}")

    def to_dict(self) -> dict[str, object]:
        return {
            "complexity": self.complexity,
            "display_mode": self.display_mode,
            "kind": "team_composition_config",
            "preset": str(self.preset),
            "schema_version": self.SCHEMA_VERSION,
            "team_size": self.team_size,
            "teammates": [
                {
                    "agent_id": item.agent_id,
                    "focus_dimension": item.focus_dimension,
                    "read_only": item.read_only,
                    "role": str(item.role),
                }
                for item in self.teammates
            ],
        }


@dataclass(frozen=True, slots=True)
class LocalAIResult:
    status: BridgeStatus
    operation: str
    request_id: str
    reason_code: str
    output: str | None = None
    team_config: TeamCompositionConfig | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "h1_written": False,
            "kind": "contract_ai_result",
            "operation": self.operation,
            "output": self.output,
            "reason_code": self.reason_code,
            "request_id": self.request_id,
            "schema_version": 1,
            "status": self.status,
        }
        if self.team_config is not None:
            payload["team_config"] = self.team_config.to_dict()
        return payload


class AgentTeamBridge:
    """Multi-agent supervisor bridging team composition patterns with the research console."""

    def __init__(
        self,
        root: Path,
        *,
        enabled: bool | None = None,
        runner: Runner = subprocess.run,
        executable: str = _EXECUTABLE,
        timeout_seconds: int = 30,
        default_display_mode: DisplayMode = "in-process",
    ) -> None:
        self.root = root.resolve()
        self.enabled = (
            os.environ.get("MEDREC_LOCAL_AI_BRIDGE") == "1" if enabled is None else enabled
        )
        self.runner = runner
        if executable != _EXECUTABLE:
            raise ValueError("local AI executable is fixed")
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 120:
            raise ValueError("local AI timeout must be between 1 and 120 seconds")
        self.timeout_seconds = timeout_seconds
        self.default_display_mode = default_display_mode

    def availability(self) -> tuple[Literal["unavailable", "ready"], str]:
        if not self.enabled:
            return "unavailable", "local-ai-bridge-not-configured"
        if self.runner is subprocess.run and not (
            Path(_EXECUTABLE).is_file() and os.access(_EXECUTABLE, os.X_OK)
        ):
            return "unavailable", "local-ai-executable-unavailable"
        return "ready", "local-ai-bridge-ready"

    def compose_team(
        self,
        preset: TeamCompositionPreset | str,
        *,
        display_mode: DisplayMode | None = None,
    ) -> TeamCompositionConfig:
        """Compose an optimal multi-agent team configuration with sizing heuristics."""
        mode = display_mode or self.default_display_mode
        return TeamCompositionConfig.create_preset(preset, display_mode=mode)

    def run(
        self,
        *,
        operation: str,
        request_id: str,
        questionnaire: list[dict[str, str]],
        preset: TeamCompositionPreset | str | None = None,
    ) -> LocalAIResult:
        """Execute intent-driven multi-agent research analysis with fail-closed human gates."""
        if not isinstance(operation, str) or operation not in {
            "draft",
            "challenge",
            "review_team",
            "debug_team",
        }:
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

        team_preset = preset or (
            TeamCompositionPreset.REVIEW_TEAM
            if operation in {"challenge", "review_team"}
            else TeamCompositionPreset.RESEARCH_TEAM
        )
        team_config = self.compose_team(team_preset)

        rendered_sections = [
            f"## {item['label']} ({item['id']})\nProvenance: {item['provenance']}\n{item['value']}"
            for item in questionnaire
        ]
        context_text = "\n\n".join(rendered_sections)

        if operation == "draft":
            prompt = (
                "You are an expert research assistant. "
                "Draft a concise research contract and H1 hypothesis based on:\n\n"
                f"{context_text}\n\n"
                "Return markdown with problem, hypotheses, acceptance boundaries, and budget."
            )
        elif operation in {"challenge", "review_team"}:
            teammates_text = "\n".join(
                f"- {item.agent_id} ({item.role}): Focus on {item.focus_dimension}"
                for item in team_config.teammates
            )
            prompt = (
                "You are leading a multi-agent Review Team with specialized reviewers:\n"
                f"{teammates_text}\n\n"
                "Review the following research contract from all three distinct perspectives:\n\n"
                f"{context_text}\n\n"
                "Generate a challenge memo: identify unstated assumptions, baseline risks, "
                "and metric ambiguity. Format as a multi-reviewer report."
            )
        else:
            prompt = (
                "You are leading a Debug Team investigating anomalies. "
                f"Context:\n{context_text}\n\n"
                "Evaluate 3 hypotheses (Resource, Loss/NaN, Drift) and propose diagnostic probes."
            )

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir) / "output.txt"
                result = self.runner(
                    [
                        _EXECUTABLE,
                        "exec",
                        "--model",
                        "gpt-5.6-sol",
                        "--effort",
                        "low",
                        "--no-git",
                        "-C",
                        str(self.root),
                        "-o",
                        str(output_path),
                        "-p",
                        prompt,
                    ],
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
                        team_config=team_config,
                    )
                output = output_path.read_text(encoding="utf-8").strip()
        except subprocess.TimeoutExpired:
            return LocalAIResult(
                status="error",
                operation=operation,
                request_id=request_id,
                reason_code="local-ai-timeout",
                team_config=team_config,
            )
        except (OSError, UnicodeError, subprocess.SubprocessError):
            return LocalAIResult(
                status="error",
                operation=operation,
                request_id=request_id,
                reason_code="local-ai-transport-failure",
                team_config=team_config,
            )

        if not output:
            return LocalAIResult(
                status="error",
                operation=operation,
                request_id=request_id,
                reason_code="local-ai-empty-output",
                team_config=team_config,
            )
        if len(output) > _MAX_OUTPUT or any(
            ord(character) < 32 and character not in "\n\r\t" for character in output
        ):
            return LocalAIResult(
                status="error",
                operation=operation,
                request_id=request_id,
                reason_code="local-ai-output-invalid",
                team_config=team_config,
            )

        return LocalAIResult(
            status="ready",
            operation=operation,
            request_id=request_id,
            reason_code="local-ai-complete",
            output=output,
            team_config=team_config,
        )


__all__ = (
    "AgentRole",
    "AgentTeamBridge",
    "DisplayMode",
    "LocalAIResult",
    "TeamCompositionConfig",
    "TeamCompositionPreset",
    "TeammateSpec",
)
