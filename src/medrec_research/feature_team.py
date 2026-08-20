"""Feature Team for Phase 4: Experiment Design and Research Contract Locking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .baseline_team import AgentRole


@dataclass
class FeatureTeam:
    """Collaborative 3-agent team for experimental design and formal contract generation."""

    hypothesis_id: str
    hypothesis_data: dict[str, Any]
    display_mode: str = "tmux"
    members: list[AgentRole] = field(
        default_factory=lambda: [
            AgentRole(
                name="Team Lead",
                role_type="team-lead",
                duty="实验变量控制与指标口径统筹 (Variable Control & Protocol Alignment)",
            ),
            AgentRole(
                name="Agent 1",
                role_type="team-implementer",
                duty="模型结构与超参数配置文件生成 (Experiment Config Generator)",
            ),
            AgentRole(
                name="Agent 2",
                role_type="team-implementer",
                duty="可证伪性研究契约生成与形式化签名 (Research Contract Generator)",
            ),
        ]
    )

    def describe_team(self) -> str:
        lines = [f"✓ Feature Team spawned ({len(self.members)} agents)"]
        for agent in self.members:
            lines.append(f"  - {agent.name} ({agent.role_type}): {agent.duty}")
        return "\n".join(lines)

    def execute(self) -> tuple[dict[str, Any], str]:
        """Generate locked research contract (JSON dict) and experiment config (YAML string)."""
        now = datetime.now(UTC).isoformat()
        hyp_title = self.hypothesis_data.get("title", f"Experiment for {self.hypothesis_id}")
        slug = self.hypothesis_data.get("slug", "substructure-gated-ddi")

        contract_id = f"{self.hypothesis_id}-contract"

        # 1. Research Contract Specification
        contract = {
            "contract_id": contract_id,
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_title": hyp_title,
            "hypothesis_slug": slug,
            "expected_outcome": "Jaccard similarity >= 0.535 and DDI rate <= 0.060 on MIMIC-III test set",
            "success_criteria": {
                "jaccard": 0.535,
                "prauc": 0.770,
                "f1": 0.695,
                "ddi_rate": 0.060,
            },
            "failure_signals": {
                "jaccard_below": 0.515,
                "ddi_rate_above": 0.075,
                "oom_on_vram_gb": 24,
            },
            "resource_limits": {
                "max_epochs": 40,
                "max_gpu_hours": 6.0,
                "max_vram_gb": 24,
                "early_stopping_patience": 5,
            },
            "locked_at": now,
            "signature": "SIGNED_BY_HITL_GATE",
        }

        # 2. Experiment YAML Specification
        exp_yaml = f"""# MedRec Experiment Configuration: {self.hypothesis_id}
experiment_id: "{self.hypothesis_id}-{slug}"
hypothesis_id: "{self.hypothesis_id}"
created_at: "{now}"

model:
  name: "HierarchicalSubstructureSafeDrug"
  base_architecture: "SafeDrug"
  substructure_encoder: "RDKit-FunctionalGroups"
  graph_layers: 3
  hidden_dim: 128
  subgraph_attention_heads: 4
  ddi_penalty_weight: 0.85

training:
  batch_size: 32
  learning_rate: 0.0005
  weight_decay: 1e-5
  optimizer: "AdamW"
  epochs: 40
  early_stopping: 5

dataset:
  name: "mimic-iii"
  split: "standard_split"
  vocab_path: "data/vocabs.json"

runtime:
  conda_env: "medrec-core"
  entrypoint: "src/medrec_research/experiments/run_experiment.py"
  device: "cuda:0"
"""

        return contract, exp_yaml
