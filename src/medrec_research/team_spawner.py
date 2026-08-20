"""Team Spawner for dynamic Multi-Agent research team composition."""

from __future__ import annotations

from typing import Any

from .baseline_team import BaselineTeam
from .execution_team import ExecutionTeam
from .feature_team import FeatureTeam
from .research_team import ResearchTeam
from .review_team import ReviewTeam


class TeamSpawner:
    """Factory for multi-agent teams across the 6 research phases."""

    def __init__(self, display_mode: str = "tmux"):
        self.display_mode = display_mode

    def spawn_baseline_team(
        self, baseline_id: str, config: dict[str, Any] | None = None
    ) -> BaselineTeam:
        """Spawn Phase 1 Baseline Team (3 agents: implementer, reviewer, explore)."""
        cfg = config or {}
        return BaselineTeam(
            baseline_id=baseline_id,
            config=cfg,
            display_mode=self.display_mode,
        )

    def spawn_research_team(self, baseline_result: dict[str, Any]) -> ResearchTeam:
        """Spawn Phase 2 Research Team (4 agents: failure analyst, literature, codebase, hypothesis)."""
        return ResearchTeam(
            baseline_result=baseline_result,
            display_mode=self.display_mode,
        )

    def spawn_review_team(self, target_id: str, target_type: str = "hypothesis") -> ReviewTeam:
        """Spawn Phase 3/6 Review Team (3 reviewers: novelty, feasibility, evidence)."""
        return ReviewTeam(
            target_id=target_id,
            target_type=target_type,
            display_mode=self.display_mode,
        )

    def spawn_feature_team(
        self, hypothesis_id: str, hypothesis_data: dict[str, Any]
    ) -> FeatureTeam:
        """Spawn Phase 4 Feature Team (3 agents: lead, config engineer, contract generator)."""
        return FeatureTeam(
            hypothesis_id=hypothesis_id,
            hypothesis_data=hypothesis_data,
            display_mode=self.display_mode,
        )

    def spawn_execution_team(self, experiment_id: str, exp_config: dict[str, Any]) -> ExecutionTeam:
        """Spawn Phase 5 Execution Team (2 agents: deployer, telemetry monitor)."""
        return ExecutionTeam(
            experiment_id=experiment_id,
            exp_config=exp_config,
            display_mode=self.display_mode,
        )
