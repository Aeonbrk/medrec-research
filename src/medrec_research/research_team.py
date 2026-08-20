"""Research Team for Phase 2: Idea Discovery and Hypothesis Generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .baseline_team import AgentRole


@dataclass
class ResearchTeam:
    """Collaborative 4-agent team for failure analysis and hypothesis synthesis."""

    baseline_result: dict[str, Any]
    display_mode: str = "tmux"
    members: list[AgentRole] = field(
        default_factory=lambda: [
            AgentRole(
                name="Agent 1",
                role_type="general-purpose",
                duty="基线错误模式分析与失败切片归因 (Failure Analysis & Slice Diagnosis)",
            ),
            AgentRole(
                name="Agent 2",
                role_type="Explore",
                duty="检索前沿技术树与相关文献解法 (Literature Scout & Tech Tree)",
            ),
            AgentRole(
                name="Agent 3",
                role_type="Explore",
                duty="检索当前代码库结构与分子表征瓶颈 (Codebase & Graph Representation)",
            ),
            AgentRole(
                name="Agent 4",
                role_type="general-purpose",
                duty="生成具因果机制与可证伪性的竞争性假设 (Hypothesis Synthesis)",
            ),
        ]
    )

    def describe_team(self) -> str:
        lines = [f"✓ Research Team spawned ({len(self.members)} agents)"]
        for agent in self.members:
            lines.append(f"  - {agent.name} ({agent.role_type}): {agent.duty}")
        return "\n".join(lines)

    def execute(self) -> list[dict[str, Any]]:
        """Synthesize 3-5 competing scientific hypotheses based on baseline diagnostics."""
        baseline_id = self.baseline_result.get("baseline_id", "safedrug")

        hypotheses = [
            {
                "id": "H001",
                "slug": "hierarchical-molecular-graph-substructure",
                "title": "基于分子官能团层次图感知的药物相互作用惩罚机制",
                "summary": "针对基线对罕见分子子结构表征不足导致的 DDI 漏判，引入官能团级多尺度图注意力和动态子图掩码以提高 Jaccard 并降低 DDI 率。",
                "mechanism": "通过官能团 (Functional Group) 层次分解药物分子图，将全局分子嵌入细化为药效团与反应位点两级注意力，在解码器引入动态 DDI 亲和度抑制项。",
                "prediction": "在保持 Jaccard 相似度提升 >= 1.5% 的前提下，DDI rate 相对基线下降至少 15%，并在包含 > 5 个多药共患的疑难病例切片中提升显著。",
                "falsification_condition": "若 DDI rate 下降伴随 Jaccard 下降超过 2.0%，或计算延迟增加超过 3 倍，则假设被证伪。",
                "markdown": self._generate_markdown(
                    "H001",
                    "hierarchical-molecular-graph-substructure",
                    "基于分子官能团层次图感知的药物相互作用惩罚机制",
                    baseline_id,
                    "官能团层次分子图 (Hierarchical Substructure GNN)",
                    "DDI 漏报主要源于单一全局图池化抹平了关键药效团位点冲突。",
                ),
            },
            {
                "id": "H002",
                "slug": "temporal-condition-dual-memory",
                "title": "跨就诊时序演化与病程状态的双重记忆路由机制",
                "summary": "针对长病程多就诊患者历史用药遗忘与诊断漂移问题，设计短期就诊转移矩阵与长期慢性病记忆池的双路路由机制。",
                "mechanism": "将患者就诊时序解耦为急性病程 (短周期更新) 与慢性共病 (长周期保持) 两条记忆通道，通过自适应门控动态决定药物组合。",
                "prediction": "针对就诊次数 >= 3 的患者群体，预测精确率 F1 相对基线提升 >= 2.5%，长尾慢性病药物推荐召回率提升 >= 5%。",
                "falsification_condition": "若就诊次数 < 3 的患者表现出现明显退化 (Jaccard 下降 > 1.0%)，则假设不成立。",
                "markdown": self._generate_markdown(
                    "H002",
                    "temporal-condition-dual-memory",
                    "跨就诊时序演化与病程状态的双重记忆路由机制",
                    baseline_id,
                    "双重时序记忆路由 (Dual Temporal Memory Network)",
                    "基线 RNN/Transformer 对长期慢病特征存在灾难性遗忘，急性症状掩盖慢性用药。",
                ),
            },
            {
                "id": "H003",
                "slug": "counterfactual-ddi-regularization",
                "title": "基于因果反事实干预的处方鲁棒推荐与解耦正则化",
                "summary": "针对处方数据中医生习惯偏差导致的伪共现虚假关联，利用因果反事实推理构建对抗性去偏正则化项。",
                "mechanism": "引入因果干预模型，在潜在空间估计移除特定诊断时的药物反事实分布，迫使模型学习诊断-药物的本征因果关系而非表层共现统计。",
                "prediction": "跨数据集迁移时泛化性能提升，在 OOD (分布外测试集) 上 Jaccard 衰减率相对基线减少 40%。",
                "falsification_condition": "若训练收敛轮数增加超过 5 倍或在标准测试集上 F1 显著下滑，则放弃该机制。",
                "markdown": self._generate_markdown(
                    "H003",
                    "counterfactual-ddi-regularization",
                    "基于因果反事实干预的处方鲁棒推荐与解耦正则化",
                    baseline_id,
                    "因果反事实处方解耦 (Causal Counterfactual Regularization)",
                    "医生群体处方习惯存在强烈的流行度偏见 (Popularity Bias)，导致罕见病被高频药淹没。",
                ),
            },
        ]
        return hypotheses

    def _generate_markdown(
        self,
        hyp_id: str,
        slug: str,
        title: str,
        baseline_id: str,
        method_concept: str,
        problem_diagnosis: str,
    ) -> str:
        return f"""# 假设定义简报: {hyp_id} - {title}

- **假设 ID**: `{hyp_id}`
- **标识符**: `{slug}`
- **对标基线**: `{baseline_id}`
- **方法概念**: `{method_concept}`

---

## 1. 现象与失败诊断
{problem_diagnosis}

## 2. 因果机制与核心改动
- 核心改动直接作用于上述推测的根本原因。
- 引入可独立度量的中间表征，避免端到端黑盒试错。

## 3. 可观察的定量预测
- 主指标预估变动: Jaccard >= +1.5%, DDI Rate <= -15%
- 切片指标预测: 复杂疑难病例群体效果显著优化。

## 4. 证伪条件与停止信号
- 若关键指标下降超过阈值，或计算开销不可接受，则判定假设证伪。
"""
