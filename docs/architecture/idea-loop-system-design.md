# Idea Loop System Design

> **Document Version**: 1.0.0  
> **Author**: MedRec Research Team  
> **Date**: 2026-08-20  
> **Status**: Historical Architecture Reference (Lessons absorbed into core toolkit in ce2e71f)  
> **Methodological Foundation**: [First-Principles Research Practice](file:///Users/oian/Codes/master/medrec-research/docs/guides/first-principles-research-practice.md)

---

## 1. 概述与目标

MedRec Research 系统的核心目标不是单纯执行基线脚本，而是构建一个支持**端到端科学发现循环（Idea Loop）**的半自动化科研系统。系统以第一性原理（First Principles）为指引，通过多智能体协作（Multi-Agent Teams）与人机协同决策门（Human-in-the-Loop Decision Gates），将科研过程形式化为：

$$\text{Baseline} \xrightarrow{} \text{Failure Analysis} \xrightarrow{} \text{Hypotheses} \xrightarrow{} \text{Review} \xrightarrow{} \text{Contract} \xrightarrow{} \text{Experiment} \xrightarrow{} \text{Evidence} \xrightarrow{} \text{Decision}$$

---

## 2. 总体架构

### 2.1 三层架构模型

```text
┌─────────────────────────────────────────────────────────────┐
│               Human-in-the-Loop Layer (HITL)                │
│  - 5 个结构化决策点 (Baseline / Hypo / Review / Exp / Evid)   │
│  - 结构化决策存证记录于 research/decisions/                  │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Human Choices & Directives)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Research Orchestrator Layer                 │
│  - ResearchOrchestrator 核心调度器                           │
│  - 状态机与工作区目录管理 (research/ & experiments/)         │
│  - 编排 6 大研究 Phase 并驱动多智能体协作                    │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────┐┌─────────────────────────────┐
│      Multi-Agent Teams       ││     Execution & Remote      │
│ - Baseline Team   (3 agents) ││ - RemoteExecutor (SSH/tmux) │
│ - Research Team   (4 agents) ││ - Conda Env Isolation       │
│ - Review Team     (3 agents) ││ - Remote Data & GPU Host    │
│ - Feature Team    (3 agents) ││ - Result Collector (SCP)    │
│ - Execution Team  (2 agents) ││ - Protocol Validation       │
└──────────────────────────────┘└─────────────────────────────┘
```

### 2.2 数据流与产物契约

| Phase | 输入 | 协同团队 | 产出物 | HITL 决策选项 |
| --- | --- | --- | --- | --- |
| **Phase 1: Baseline Establishment** | `baselines/registry.toml`, 数据集声明 | Baseline Team (3) | `research/baselines/{id}/result.json`, `analysis.md` | [1] 继续分析失败<br>[2] 先跑其他基线<br>[3] 接受偏差标记 ready |
| **Phase 2: Idea Discovery** | 基线结果与偏差剖析 | Research Team (4) | `research/hypotheses/H{NNN}-{slug}.md` (3-5个竞争性假设) | [1..N] 选择假设验证<br>[+] 重新生成假设<br>[-] 放弃方向 |
| **Phase 3: Idea Review** | 候选假设 | Review Team (3) | `research/reviews/H{NNN}-review.md` (三维度打分与判词) | [1] Go (通过立项)<br>[2] Revise (修改假设)<br>[3] Kill (终止并记录) |
| **Phase 4: Experiment Design** | 通过的假设 | Feature Team (3) | `research/contracts/H{NNN}-contract.json`<br>`experiments/H{NNN}-exp.yaml` | [1] 签署并锁定研究契约<br>[2] 调整实验设计 |
| **Phase 5: Execution** | 研究契约与实验配置 | Execution Team (2) | 远程运行记录、中间指标日志、`results.json` | 自动化执行；异常或断言触发时熔断 |
| **Phase 6: Evidence Analysis** | 实验原始结果与预测指标 | Review Team (3) | `research/evidence/H{NNN}-evidence.md` (归因与证据链) | [1] 证据充分，撰写交付<br>[2] 补充区分性实验<br>[3] 修正假设<br>[4] 记录经验并归档 |

### 2.3 工作目录与文件布局

```text
medrec-research/
├── baselines/                    # 基线注册与配置
│   ├── registry.toml
│   └── programs/
├── experiments/                  # 实验配置与规范
│   └── H{NNN}-{slug}.yaml
├── research/                     # 科学发现全过程沉淀
│   ├── baselines/                # Phase 1: 基线运行与分析
│   │   └── {baseline-id}/
│   │       ├── result.json
│   │       └── analysis.md
│   ├── hypotheses/               # Phase 2: 竞争性原因假设
│   │   └── H{NNN}-{slug}.md
│   ├── reviews/                  # Phase 3: 独立同行评审报告
│   │   └── H{NNN}-review.md
│   ├── contracts/                # Phase 4: 锁定的研究契约
│   │   └── H{NNN}-contract.json
│   ├── evidence/                 # Phase 6: 证据链分析
│   │   └── H{NNN}-evidence.md
│   ├── decisions/                # HITL 人类决策记录
│   │   └── {timestamp}-{phase}-decision.json
│   ├── failures/                 # 证伪与失败经验库
│   └── accumulated-experience.md # 领域经验提炼
└── src/medrec_research/          # 核心代码包
    ├── research_orchestrator.py  # 核心协调器
    ├── team_spawner.py           # 团队生成器
    ├── hitl_decision.py          # HITL 决策门
    ├── remote_executor.py        # 远程 SSH/tmux 执行器
    ├── baseline_team.py          # 基线团队
    ├── research_team.py          # 假设团队
    ├── review_team.py            # 评审团队
    ├── feature_team.py           # 实验设计团队
    ├── execution_team.py         # 执行监控团队
    ├── cli.py                    # 统一 CLI
    └── ...                       # 科学评估与数据流模块
```

---

## 3. Phase 详细设计与团队职责

### 3.1 Phase 1: Baseline Establishment (基线确立)

- **目标**: 在统一数据口径与指标规约下建立真实基线，定位复现偏差与关键瓶颈。
- **团队构成 (Baseline Team - 3 agents)**:
  1. `team-implementer`: 负责在远程计算卡 (319-wild) 部署与运行指定基线。
  2. `team-reviewer`: 校验参数配置、数据切分与科学评估口径的一致性。
  3. `Explore`: 检索已知的实现陷阱、超参敏感点及公开复现差异。
- **输出产物**:
  - `research/baselines/{baseline-id}/result.json`
  - `research/baselines/{baseline-id}/analysis.md`
- **HITL 决策点 #1**:
  - 选项: `继续分析这个失败` / `先跑其他基线` / `这个偏差可接受，标记为 baseline-ready`

### 3.2 Phase 2: Idea Discovery (假设发现)

- **目标**: 基于基线失败模式剖析根本原因，提出 3-5 个具因果机制的竞争性假设。
- **团队构成 (Research Team - 4 agents)**:
  1. `general-purpose` (Failure Analyst): 剖析基线在哪些子群体或分子结构上表现不佳。
  2. `Explore` (Literature Scout): 检索针对同类失败机理的外部文献与技术树。
  3. `Explore` (Codebase Scout): 检索当前架构中的表征与计算瓶颈。
  4. `general-purpose` (Hypothesis Generator): 形式化生成 3-5 个满足可证伪性要求的假设。
- **输出产物**:
  - `research/hypotheses/H001-{slug}.md` ~ `H005-{slug}.md`
- **HITL 决策点 #2**:
  - 选项: 选定特定假设 `[H001]...` / `重新生成假设` / `放弃该方向`

### 3.3 Phase 3: Idea Review (独立评审)

- **目标**: 针对选定假设进行独立三维度盲审，严格防范过早乐观与虚假创新。
- **团队构成 (Review Team - 3 reviewers)**:
  1. `Reviewer 1 (Novelty)`: 评估新颖性，核查是否是已有工作的简单变体。
  2. `Reviewer 2 (Feasibility)`: 评估实验可行性、算力预算与实现复杂度。
  3. `Reviewer 3 (Evidence Strength)`: 评估所设计假设的预测可区分性与证伪门槛。
- **输出产物**:
  - `research/reviews/H{NNN}-review.md` (包含 Go/Revise/Kill 综合判词与建议)
- **HITL 决策点 #3**:
  - 选项: `Go (通过立项)` / `Revise (修改假设)` / `Kill (终止方向)`

### 3.4 Phase 4: Experiment Design & Contract Locking (实验设计与研究契约)

- **目标**: 固化最小可区分实验设计，锁定不可篡改的“研究契约（Research Contract）”。
- **团队构成 (Feature Team - 3 agents)**:
  1. `Team Lead`: 统筹实验变量控制与指标口径。
  2. `team-implementer` (Config Engineer): 编写可复现的实验配置文件 `experiments/H{NNN}-exp.yaml`。
  3. `team-implementer` (Contract Generator): 生成包含明确成功标准与失败信号的研究契约。
- **输出产物**:
  - `research/contracts/H{NNN}-contract.json`
  - `experiments/H{NNN}-exp.yaml`
- **HITL 决策点 #4**:
  - 选项: `确认签署并锁定研究契约` / `调整实验配置`

### 3.5 Phase 5: Execution & Monitoring (实验执行与监控)

- **目标**: 在远程环境稳健执行实验并采集全量运行轨迹与指标。
- **团队构成 (Execution Team - 2 agents)**:
  1. `team-implementer`: 远程任务提交、环境管理与 GPU 调度。
  2. `team-reviewer`: 日志实时监控、早停/异常诊断与完整性核查。
- **输出产物**:
  - 远程运行作业日志、中间 Checkpoint、最终评测指标。

### 3.6 Phase 6: Evidence Analysis & Decision (证据分析与行动决策)

- **目标**: 对照研究契约检验实验结果，判断假设成立程度，规划下一步科研路径。
- **团队构成 (Review Team - 3 agents)**:
  1. `Reviewer 1`: 假设支持度与效应量检验。
  2. `Reviewer 2`: 混淆因素与实验边界排查。
  3. `Reviewer 3`: 后续学术价值与下一步迭代建议。
- **输出产物**:
  - `research/evidence/H{NNN}-evidence.md`
- **HITL 决策点 #5**:
  - 选项: `证据充分，进入论文写作` / `补充区分性实验` / `修正假设进入下一轮` / `记录经验并结题`

---

## 4. 核心类接口定义

### 4.1 RemoteExecutor

```python
@dataclass
class SSHConfig:
    host: str = "319-wild"
    user: str = "oian"
    key_path: Path = Path("~/.ssh/id_rsa").expanduser()
    remote_data_root: str = "/data/medrec"
    port: int = 22

@dataclass
class JobStatus:
    job_id: str
    status: str  # "running" | "completed" | "failed" | "stopped"
    progress: str
    log_tail: str

class RemoteExecutor:
    def __init__(self, config: SSHConfig): ...
    def ssh(self, command: str, timeout: int = 60) -> str: ...
    def run_baseline(self, baseline_id: str, config: dict, dry_run: bool = False) -> str: ...
    def run_experiment(self, experiment_id: str, exp_config: dict, dry_run: bool = False) -> str: ...
    def check_status(self, job_id: str) -> JobStatus: ...
    def collect_results(self, job_id: str, remote_path: str, local_dest: Path) -> Path: ...
```

### 4.2 HITLDecisionGate

```python
@dataclass
class Decision:
    decision_id: str
    timestamp: datetime
    phase: str
    context: dict[str, Any]
    options: list[str]
    chosen: str
    notes: str = ""

class HITLDecisionGate:
    def __init__(self, decisions_dir: Path): ...
    def wait_for_choice(
        self,
        phase: str,
        prompt: str,
        options: list[str],
        context: dict[str, Any],
        auto_choice: str | None = None
    ) -> str: ...
    def record_decision(self, decision: Decision) -> Path: ...
```

### 4.3 TeamSpawner & Teams

```python
class Team(Protocol):
    def execute(self, **kwargs) -> dict[str, Any]: ...

class TeamSpawner:
    def __init__(self, display_mode: str = "tmux"): ...
    def spawn_baseline_team(self, baseline_id: str, config: dict) -> BaselineTeam: ...
    def spawn_research_team(self, baseline_result: dict) -> ResearchTeam: ...
    def spawn_review_team(self, hypothesis_id: str, hypothesis_text: str) -> ReviewTeam: ...
    def spawn_feature_team(self, hypothesis_id: str, hypothesis_data: dict) -> FeatureTeam: ...
    def spawn_execution_team(self, experiment_id: str, exp_config: dict) -> ExecutionTeam: ...
```

### 4.4 ResearchOrchestrator

```python
class ResearchOrchestrator:
    def __init__(self, root: Path, ssh_config: SSHConfig, clock: Callable[[], datetime] | None = None): ...
    def establish_baseline(self, baseline_id: str, dry_run: bool = False) -> dict[str, Any] | None: ...
    def discover_ideas(self, baseline_id: str) -> list[dict[str, Any]] | None: ...
    def review_idea(self, hypothesis_id: str) -> dict[str, Any] | None: ...
    def design_experiment(self, hypothesis_id: str) -> dict[str, Any] | None: ...
    def run_experiment(self, experiment_id: str, dry_run: bool = False) -> dict[str, Any] | None: ...
    def analyze_evidence(self, experiment_id: str) -> dict[str, Any] | None: ...
    def run_loop(self, baseline_id: str, dry_run: bool = False): ...
```

---

## 5. CLI 命令接口

```bash
# 阶段 1: 建立基线
medrec baseline establish <baseline-id> [--dry-run]

# 阶段 2: 发现 Idea / 提出假设
medrec idea discover <baseline-id>

# 阶段 3: 评审假设
medrec idea review <hypothesis-id>

# 阶段 4: 设计实验与生成契约
medrec experiment design <hypothesis-id>

# 阶段 5: 执行实验
medrec experiment run <experiment-id> [--dry-run]

# 阶段 6: 证据分析
medrec evidence analyze <experiment-id>

# 快捷命令: 启动全流程循环 (在各决策门自动暂停等待人类抉择)
medrec loop start <baseline-id> [--dry-run]
```

---

## 6. 配置规范与模板 (`~/.medrec/config.yaml`)

```yaml
ssh:
  host: 319-wild
  user: oian
  key_path: ~/.ssh/id_rsa
  remote_data_root: /data/medrec
  port: 22

conda:
  base_env: medrec-core
  baseline_envs:
    safedrug: safedrug-env
    gamenet: gamenet-env
    micor: micor-env
    molerec: molerec-env

teams:
  display_mode: tmux # tmux | in-process | subagent

hitl:
  interactive: true
  auto_choice_on_non_interactive: 1
```

---

## 7. 验收与质量验证标准

1. **Dry-Run 基准验收**:

   ```bash
   medrec baseline establish safedrug --dry-run
   ```

   输出包含：
   - `✓ Team spawned (3 agents)`
   - `✓ Baseline config validated`
   - `✓ Execution plan generated`
   - `→ Would run on 319, but dry-run mode`

2. **决策链完整性**: 每次 HITL 操作均在 `research/decisions/` 留下包含时间戳与决策上下文的结构化 JSON。
3. **单元与集成测试覆盖**: `pytest` 跑通核心调度器、远程执行器、团队生成器与决策门逻辑。
