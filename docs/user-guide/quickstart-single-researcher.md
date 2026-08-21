# MedRec Idea Loop - 快速上手指南（单人科研版）

> **状态**: Phase 1 和 Phase 5 需要手动执行，其他阶段自动化  
> **原因**: 避免假数据，保持简单可控  
> **时间**: 全流程约 1-2 天（取决于实验运行时间）

---

## 工作流程

### Phase 1: Baseline Establishment（手动 + 自动）

1. **生成执行计划（自动）**
   ```bash
   medrec baseline establish safedrug --dry-run
   ```
   输出：
   - ✓ Team spawned (3 agents)
   - ✓ Baseline config validated
   - ✓ Execution plan generated

2. **在 319-wild 上运行 baseline（手动）**
   ```bash
   ssh 319-wild
   conda activate safedrug-env
   cd /data/medrec
   python baselines/safedrug/run.py --data-root /data/medrec --output result.json
   ```

3. **拷贝结果到本地（手动）**
   ```bash
   # 在本地 Mac 上
   scp 319-wild:/data/medrec/result.json \
       research/baselines/safedrug/result.json
   ```

4. **系统分析偏差并触发 HITL 决策（自动）**
   ```bash
   # 重新运行（会检测到 result.json 已存在）
   medrec baseline establish safedrug
   ```
   
   HITL 决策点 #1：
   ```
   📋 可选行动:
     [1] 继续分析这个失败 (Proceed to Phase 2: Idea Discovery)
     [2] 先跑其他基线 (Pause loop to run other baselines)
     [3] 这个偏差可接受，标记为 baseline-ready
   
   👉 你的选择: 1
   ```

---

### Phase 2: Idea Discovery（自动）

```bash
medrec idea discover safedrug
```

系统自动：
- ✓ 分析 baseline 失败模式
- ✓ 生成 3-5 个竞争性假设
- ✓ 保存到 `research/hypotheses/H001-*.md` ~ `H005-*.md`

HITL 决策点 #2：
```
📋 可选行动:
  [1] [H001] 基于分子官能团层次图感知的药物相互作用惩罚机制
  [2] [H002] 跨就诊时序演化与病程状态的双重记忆路由机制
  [3] [H003] 基于因果反事实干预的处方鲁棒推荐与解耦正则化
  [4] 修改假设 (重新生成)
  [5] 放弃这个方向

👉 你的选择: 1
```

---

### Phase 3: Idea Review（自动）

```bash
medrec idea review H001
```

系统自动：
- ✓ 3 个 reviewer 独立盲审（新颖性、可行性、证据强度）
- ✓ 生成综合评分和建议
- ✓ 保存到 `research/reviews/H001-review.md`

HITL 决策点 #3：
```
假设 【H001】 同行评审完成，综合判定: Go (8.5/10)

📋 可选行动:
  [1] Go (通过立项，进入实验设计)
  [2] Revise (修改假设与机制描述)
  [3] Kill (终止该方向并记录经验)

👉 你的选择: 1
```

---

### Phase 4: Experiment Design（自动）

```bash
medrec experiment design H001
```

系统自动：
- ✓ 生成实验配置 YAML
- ✓ 锁定研究契约（success criteria, failure signals）
- ✓ 保存到 `research/contracts/H001-contract.json` 和 `experiments/H001-exp.yaml`

HITL 决策点 #4：
```
已生成实验配置与研究契约 【H001-contract】

📋 可选行动:
  [1] 确认签署并锁定研究契约 (Lock Contract & Proceed)
  [2] 调整实验设计与超参配置 (Adjust Experiment Config)

👉 你的选择: 1
```

---

### Phase 5: Experiment Execution（手动 + 自动）

1. **查看实验配置**
   ```bash
   cat experiments/H001-hierarchical-molecular-graph-substructure-exp.yaml
   ```

2. **在 319-wild 上运行实验（手动）**
   ```bash
   ssh 319-wild
   conda activate medrec-core
   cd /data/medrec
   python src/medrec_research/experiments/run_experiment.py \
       --config experiments/H001-*.yaml \
       --output results.json
   ```

3. **监控进度（手动）**
   ```bash
   # 在 319-wild 上
   tail -f logs/H001.log
   # 或用 tmux 查看
   ```

4. **拷贝结果回本地（手动）**
   ```bash
   # 在本地 Mac 上
   scp 319-wild:/data/medrec/results.json \
       experiments/H001/results.json
   ```

---

### Phase 6: Evidence Analysis（自动）

```bash
medrec evidence analyze H001
```

系统自动：
- ✓ 对照研究契约检验结果
- ✓ 判定假设支持度
- ✓ 生成证据链分析报告
- ✓ 保存到 `research/evidence/H001-evidence.md`

HITL 决策点 #5：
```
实验 【H001】 证据链评估完成: Hypothesis Strongly Supported

📋 可选行动:
  [1] 证据充分，进入论文撰写 (Evidence Supported -> Paper Writing)
  [2] 补充区分性实验 (Supplementary Ablations)
  [3] 修正假设进入下一轮迭代 (Refine Hypothesis)
  [4] 记录经验并结题归档 (Archive & Log Lessons)

👉 你的选择: 1
```

---

## 完整循环快捷命令

```bash
# 一键运行完整循环（会在 5 个 HITL 决策点暂停）
medrec loop start safedrug --dry-run

# 注意：Phase 1 和 Phase 5 会报错提示手动执行
```

---

## 文件结构

```
research/
├── baselines/
│   └── safedrug/
│       ├── result.json           # 你手动放置
│       └── analysis.md           # 系统生成
├── hypotheses/
│   ├── H001-hierarchical-*.md    # 系统生成
│   ├── H002-temporal-*.md
│   └── H003-counterfactual-*.md
├── reviews/
│   └── H001-review.md            # 系统生成
├── contracts/
│   └── H001-contract.json        # 系统生成（锁定）
├── evidence/
│   └── H001-evidence.md          # 系统生成
└── decisions/
    ├── 20260821-143052-baseline-established.json
    ├── 20260821-150623-hypothesis-selection.json
    ├── 20260821-152145-hypothesis-review.json
    ├── 20260821-153012-contract-locking.json
    └── 20260821-180345-evidence-decision.json

experiments/
└── H001-hierarchical-molecular-graph-substructure-exp.yaml  # 系统生成
```

---

## 常见问题

### Q: 为什么 Phase 1 和 Phase 5 不自动化？
A: 避免假数据风险。当前实现会返回硬编码的模拟指标，可能导致你基于虚假数据做决策。手动执行确保所有指标都是真实的。

### Q: HITL 决策超时怎么办？
A: 系统会抛出异常并停止，不会自动批准任何决策。重新运行命令继续。

### Q: 我可以修改系统生成的假设吗？
A: 可以。在 Phase 2 后，直接编辑 `research/hypotheses/H001-*.md`，然后继续 Phase 3。

### Q: 研究契约锁定后可以修改吗？
A: 不建议。契约的目的是防止 p-hacking（看到结果后改成功标准）。如果必须修改，删除契约文件并重新运行 Phase 4。

### Q: 如何查看所有决策记录？
```bash
ls -lt research/decisions/
cat research/decisions/20260821-143052-baseline-established.json
```

---

## 下一步优化（可选）

当验证流程有价值后，可以考虑自动化 Phase 1 和 Phase 5：

1. **实现真实的 RemoteExecutor 调用**（4-6 小时）
2. **添加进度监控和早停**（2-3 小时）
3. **自动结果收集**（1-2 小时）

但现在不需要 - 手动执行更简单、更可控。
