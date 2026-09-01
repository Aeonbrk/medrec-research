<!-- markdownlint-disable MD001 MD013 -->

# Idea 001: Tension-Guided Verification

- **Idea ID**: `001-tension-guided-verification`
- **Status**: Active
- **Core Hypothesis**: Under limited verification resources, medication transitions subjected to simultaneously high predictive model support and high external constraint pressure yield a superior Pareto frontier than standard predictive uncertainty or boundary triggers.
- **Key Uncertainty**: Whether apparent tension gains survive control for medication count, drug frequency, and global scalar reranking (competing simple explanations).
- **Next Minimal Experiment**: S-1 (Task timestamp semantics audit) and S0/S0.5 (Action decomposition and coverage profiler).
- **Current Verdict**: Active (Proceed to S-1 / S0 minimal pilot).

> We use the tension between predictive support and external constraint pressure to identify medication decisions with high marginal value of verification.

# MedRec Research Roadmap v2

## 0. 整条路线到底研究什么

传统 MedRec 通常写成：

$$
f(X_t)\rightarrow M_t
$$

其中 $X_t$ 是当前及历史 EHR 信息，$M_t$ 是第 $t$ 次就诊观察到的 medication set。

这一定义把三个本来不同的问题压在了一起：

$$
\text{患者状态}
\rightarrow
\text{处方变化}
\rightarrow
\text{为什么模型做出该预测}
\rightarrow
\text{外部安全规则是否反对该预测}
$$

本路线不再声称“medication action 是临床决策的真实原子单位”，而提出一个更弱但可以被直接证伪的母假设：

$$
\boxed{
\begin{aligned}
&\text{Representing visit-level prescriptions as observable medication transitions,}\
&\text{and auditing model-supporting evidence and external constraints at the}\
&\text{transition level, can reveal decision tensions hidden by set-level evaluation.}
\end{aligned}
}
$$

中文即：

$$
\boxed{
\text{将处方集合分解为可观测药物转移，并在转移层分别审计模型支持证据和外部约束，}
}
$$

$$
\boxed{
\text{可能揭示传统 set-level MedRec 指标所掩盖的决策张力。}
}
$$

注意这里有三个严格的 claim boundary：

第一，我们研究的是 observed prescription transition，不宣称知道医生真实意图。

第二，我们研究的是 model-faithful evidence，不宣称发现了临床因果上的充分证据。

第三，我们研究的是 external constraint adherence，不把 DrugBank / TWOSIDES / contraindication relation 等同于患者真实 harm probability。

最终真正需要成立的核心假设不是：

$$
Conflict\uparrow\Rightarrow Error\uparrow
$$

而是：

$$
\boxed{
\text{transition-level tension 能否比 uncertainty / boundary 更有效地分配有限 verification budget？}
}
$$

最后验证：

$$
\boxed{
\mathcal F_{\text{Tension}}(B)
\succ
\mathcal F_{\text{Boundary/Uncertainty}}(B)
}
$$

并且最好是在非平凡预算区间 $B\in[B_1,B_2]$ 上持续成立，而不是某个单点阈值偶然获胜。

---

# 1. Task Ontology：先把研究对象定义合法

## 1.1 可观测输入

对于第 $t$ 次 visit，定义全部历史：

$$
H_t=
{
D_{\leq t},
P_{\leq t},
M_{<t},
L_{\leq t},
V_{\leq t},
\dots
}
$$

但实际能进入模型的输入必须经过 S-1 决策时间审计，因此真正使用的是：

$$
X_t\subseteq H_t
$$

其中每个事件必须满足任务定义要求的 temporal availability。

不要默认：

$$
P(M_t\mid H_t)
==============

P(M_t\mid M_{t-1})
$$

因此本路线不是 Markov formulation。

$M_{t-1}\rightarrow M_t$ 只是构造 observable transition 的手段。

---

## 1.2 Action 定义

对于药物 $m$：

### Add

$$
m\notin M_{t-1},
\qquad
m\in M_t
$$

### Retain

$$
m\in M_{t-1},
\qquad
m\in M_t
$$

### Observed-Remove

$$
m\in M_{t-1},
\qquad
m\notin M_t
$$

这里只能说“下一次处方未观察到”，不能解释成 clinician actively stopped the medication。

### Not-Added

对于预先定义的 candidate space $\mathcal K_t$：

$$
m\in\mathcal K_t,
\quad
m\notin M_{t-1},
\quad
m\notin M_t
$$

只能叫 Not-Added。

绝不叫 Reject。

因为：

$$
m\notin M_t
\not\Rightarrow
\text{clinician rejected }m
$$

因此统一动作空间为：

$$
a_{t,m}\in
{
\text{Add},
\text{Retain},
\text{Observed-Remove},
\text{Not-Added}
}
$$

但主论文是否使用 Observed-Remove / Not-Added，取决于 S0.5 的 observability 与 coverage 结果。

---

# 2. 最终优化问题：不是“最大准确率 + 最小 DDI”

首先定义经验处方模仿目标：

$$
F(f)=\operatorname{ActionFidelity}(f)
$$

它表示模型与观察处方的匹配程度。

再定义外部约束违规：

$$
V(f)=\operatorname{ConstraintViolation}(f;C)
$$

其中 $C$ 是明确来源的 external constraint set，例如 DDI、drug-disease contraindication 等。

因此我们研究的不是：

$$
P(\text{harm}\mid patient,m_i,m_j)
$$

而是：

$$
\operatorname{Violation}(f;C).
$$

核心优化可写成：

$$
\max_f F(f)
\qquad
\text{s.t.}
\qquad
V(f)\leq\epsilon
$$

但 $\epsilon$ 是研究者或部署者给出的 operating point，并不存在唯一自然值。

所以论文不能只报告一个人为挑选的 $\epsilon$。

真正应该比较的是：

$$
\boxed{
F\text{--}V\text{ Pareto Frontier}
}
$$

加入 verification cost 后：

$$
\mathcal F_\pi(B)
=================

\left{
(F,V,C):
C\leq B
\right}
$$

其中 $\pi$ 是决定“哪些 candidate 值得再次审核”的 trigger policy。

这就是最终主线。

---

# 3. S-1：Decision-Time / Leakage Audit

这是所有 Setting 之前必须完成的零号条件。

## 科学问题

我们使用的 $X_t$ 是否真的在预测目标 $M_t$ 形成之前可获得？

如果答案是否定的，就不能把任务描述为 prospective medication decision。

---

## 3.1 为什么必须先做

很多 MIMIC-style MedRec 数据预处理把一次 admission 中：

- diagnosis；
- procedure；
- medication；

统一聚合成 visit-level set。

但一个 procedure 完全可能发生在药物使用之后。

如果仍然写：

$$
Procedure_t\rightarrow Medication_t
$$

模型可能实际利用的是 downstream information。

最终 S1 即使找到了极高 fidelity 的 procedure evidence，也只能说明：

> 这个 retrospective feature 对模型有预测作用。

不能说：

> 这是医生开该药时使用的 evidence。

---

## 3.2 最小实验

为每类变量建立：

$$
\text{event timestamp}
----------------------

\text{decision/reference timestamp}
$$

分布。

变量至少包括：

- diagnosis；
- procedure；
- medication；
- lab；
- vital；
- note，如果使用。

然后定义每种 task configuration 的合法输入窗口。

例如：

$$
X_t^{pre}
=========

{e:\operatorname{time}(e)<T_{\text{decision}}}.
$$

如果现有 benchmark 无法恢复真实 decision timestamp，则必须显式降级任务 claim：

$$
\boxed{
\text{visit-level prescription prediction}
}
$$

而不是：

$$
\boxed{
\text{prospective treatment recommendation}.
}
$$

---

## 3.3 Gate

如果发现当前 baseline pipeline 存在明显未来信息：

先修数据。

不能进入任何方法实验。

这是 hard gate。

---

# 4. S0：Observable Action Surface

通过 S-1 后，第一步仍然不设计模型。

冻结所有 baseline。

原研究框架强调先建立 instrumentation，而不是先写 `ours.py`，这一原则继续保留。

建议 baseline 至少覆盖：

SafeDrug、MoleRec、VITA、ARMR、FLAME、KEHGCN、HypeMed。

因为这些模型分别代表 DDI-aware、molecular、visit selection、temporal responsiveness、sequential action、KG/hypergraph 和 retrieval 等不同范式。

---

## 4.1 研究问题

传统：

$$
Jaccard,\ PRAUC,\ F1,\ DDI
$$

是否掩盖了不同 prescription transitions 的行为差异？

---

## 4.2 指标

分别报告：

$$
Precision_{\text{Add}},
\quad
Recall_{\text{Add}},
\quad
F1_{\text{Add}}
$$

$$
Precision_{\text{Retain}},
\quad
Recall_{\text{Retain}},
\quad
F1_{\text{Retain}}
$$

以及可观测条件允许时：

$$
F1_{\text{Observed-Remove}}.
$$

另外至少包括：

$$
CopyRate
========

P(\hat m_t=1\mid m_{t-1}=1)
$$

和：

$$
NovelDrugRecall
===============

P(\hat m_t=1\mid
m_t=1,m_{t-1}=0).
$$

还必须报告 predicted medication count：

$$
|\hat M_t|
$$

与真实：

$$
|M_t|.
$$

因为处方数量本身会同时改变 F1 与 DDI。现有工作已经显示 drug-count normalization 本身就可能明显改变 accuracy–safety trade-off，因此这是后续所有 safety comparison 的必要混杂控制。

---

## 4.3 S0 的目的

不是证明：

> 某 action 是共同 failure mode。

而是得到 empirical action landscape。

可能发现：

- 某些模型主要靠 Retain；
- 某些模型 Add 很强但复制不足；
- 某些模型通过减少处方数降低 DDI；
- 某些模型整体 F1 一样，但 transition composition 完全不同。

这些都是后续假设的地基。

---

# 5. S0.5：Observability + Coverage Audit

原来的 Observability Audit 必须与 Coverage 合并。

因为 action 粒度越细，统计支持越容易崩掉。

---

## 5.1 Observability

分别统计：

$$
N_{\text{Add}},
\quad
N_{\text{Retain}},
\quad
N_{\text{Observed-Remove}},
\quad
N_{\text{Not-Added}}.
$$

检查：

- 患者间支持；
- visit 间支持；
- train/validation/test 稳定性；
- drug-frequency strata；
- 不同 medication-count strata。

如果 Observed-Remove 极不稳定：

$$
\boxed{
\text{主线只保留 Add + Retain}
}
$$

Observed-Remove 降级为 exploratory analysis。

---

## 5.2 Coverage

后面会出现：

$$
(action,drug,constraint,evidence)
$$

这种高维状态。

因此必须监控：

$$
N(x)
$$

并给出最小支持阈值 $\tau$。

例如只有：

$$
N(x)\geq\tau
$$

的 strata 才进入 subgroup conclusion。

还需要统计：

$$
N_{\text{patient}}(x)
$$

避免所谓 500 个 action 实际来自两个病人反复出现。

---

## 5.3 Long-tail audit

按 drug frequency 划分：

$$
G_0,G_1,\dots,G_k.
$$

因为 Add / safety constraint 很可能集中在长尾药。

如果后面 conflict 结果实际上只是：

$$
Conflict\approx RareDrug
$$

则整个机制解释会失效。

---

# 6. S1：Action-Conditioned Model Evidence Sufficiency

这是原 S1 的修正版。

名字必须加 `Model`。

我们问的是：

$$
\boxed{
\text{哪些观测输入足以维持某模型对某次 medication transition 的预测？}
}
$$

不是：

$$
\boxed{
\text{什么临床证据足以证明医生应该开这个药？}
}
$$

原研究框架已经强调要用 evidence removal 而不是 attention visualization 来测试 faithfulness；这一部分仍然是非常有价值的研究资产。

---

## 6.1 定义

给定冻结模型 $f$、action $a$ 与 drug $m$，寻找：

$$
\hat E^*_{a,m}
==============

\operatorname{ApproxSearch}(X_t,a,m,b)
$$

使得在 budget $b$ 下：

$$
|s_f(a,m\mid X_t)
-----------------

s_f(a,m\mid E)|
$$

尽可能小。

注意写 $\hat E^*$，不能声称找到了全局最优。

---

## 6.2 Evidence atom 不能混粒度

原框架把 diagnosis、procedure、medication、visit 放进同一预算，这不公平。

因为：

$$
1\ visit
\gg
1\ code
$$

的信息量。

因此建议分两个实验。

Code-level：

$$
E^{code}
========

{
diagnosis,
procedure,
medication
}.
$$

Visit-level：

$$
E^{visit}
=========

{
v_1,\dots,v_t
}.
$$

不要把二者直接放进同一个 $K$。

预算至少做三种：

$$
b_{\text{atom}}
$$

$$
b_{\text{codes}}
$$

$$
b_{\text{tokens}}.
$$

只有同预算比较才有意义。

---

## 6.3 三个指标

### Sufficiency

$$
L_{\text{suf}}
==============

## |s_f(a,m\mid X_t)

s_f(a,m\mid E)|.
$$

越低越好。

### Comprehensiveness / Necessity

$$
L_{\text{comp}}
===============

## s_f(a,m\mid X_t)

s_f(a,m\mid X_t\setminus E).
$$

对于正向 action，越大说明被选 evidence 越重要。

### Semantic Replacement

构造频率、时间位置相似但语义不同的 $\tilde E$：

$$
s_f(a,m\mid E)

>

s_f(a,m\mid\tilde E).
$$

这样才能排除 selector 只是偏爱“最近”“高频”等 shortcut。

---

# 7. S1 的关键反事实：先剥离 trivial transition signal

这是修正版里非常重要的一步。

对于 Retain：

$$
m\in M_{t-1}
$$

本身就是巨大的 predictive signal。

如果最后发现：

$$
E^*_{\text{Retain}}
===================

{m\in M_{t-1}},
$$

没有什么新科学发现。

因此把 Evidence 拆为：

$$
E=
E_{\text{transition}}
\cup
E_{\text{clinical}}.
$$

先 condition on transition state，再问：

$$
\boxed{
E_{\text{clinical}}
\text{ 是否还有 action-specific incremental contribution？}
}
$$

例如真正有价值的结果应类似：

在控制 `previous medication present` 后，Retain 还依赖 persistent longitudinal diagnoses；

而 Add 更多依赖 current-state change。

这才值得进入后续 temporal analysis。

---

## 7.1 Strong controls

S1 至少击败：

- random；
- recent-only；
- frequency-only；
- attention top-$k$；
- gradient top-$k$；
- VITA-style relevant visit；
- full context compression。

如果：

$$
Fidelity_{\text{ours}}
\approx
Fidelity_{\text{Attention}}
$$

在相同 budget 下成立：

复杂 selector 直接死亡。

---

# 8. S1.5：Evidence Lifecycle

只有 S1 发现稳定 action-conditioned structure 后才进入。

这是观察性 setting，不先训练 temporal gate。

定义：

$$
Age(e)=T_t-T_e.
$$

按数据实际分布分桶，而不是机械固定日数。

研究：

$$
P(e\in E^*_{a,m}\mid Age(e),a).
$$

同时控制：

- drug frequency；
- visit count；
- evidence type；
- transition status；
- patient history length。

真正有意义的是：

$$
P(E_{\text{clinical}}\mid Add,\Delta t)
\neq
P(E_{\text{clinical}}\mid Retain,\Delta t).
$$

而不是简单发现“最近的信息更重要”。

---

# 9. S2：Transition-Level Constraint Audit

这是整条路线另一个非常扎实的基础 Setting。

X-Ray 总结显示，安全 MedRec 已经从 post-hoc DDI 统计逐渐转向训练内生约束、验证链和更细粒度药物表示；因此再做一个 static DDI penalty 本身没有创新。

真正要改变的是 measurement unit：

$$
\boxed{
\text{final prescription safety}
\rightarrow
\text{transition-level constraint change}
}
$$

---

## 9.1 External constraint

设：

$$
C_{\text{DDI}}(m_i,m_j)\in{0,1}.
$$

或者 disease-drug：

$$
C_{\text{contra}}(d,m)\in{0,1}.
$$

注意：

$$
C=1
$$

只意味着知识库记录了某种 relation。

绝不解释为：

$$
P(\text{patient harm})=1.
$$

---

## 9.2 Introduced constraint

若当前 Add $m_i$：

$$
m_i\notin M_{t-1},
\quad
m_i\in M_t
$$

并且已有药 $m_j$ 满足：

$$
m_j\in M_{t-1},
\qquad
C_{\text{DDI}}(m_i,m_j)=1,
$$

则称：

$$
C^{intro}_{t}(m_i,m_j)=1.
$$

它回答：

> 这一次可观测 medication transition 是否新引入了某条 external constraint？

---

## 9.3 Persistent constraint

若 interaction pair 在前后处方中都存在：

$$
m_i,m_j\in M_{t-1}\cap M_t,
$$

则：

$$
C^{persist}_{t}(m_i,m_j)=1.
$$

---

## 9.4 Observed-Resolved constraint

如果前一次 interaction 存在，而下一次因为某药不再出现在 prescription 中而消失，只能叫：

$$
C^{obs-resolved}.
$$

绝不能声称：

> 医生主动为了安全问题解除该 interaction。

---

## 9.5 需要报告什么

不是只报告：

$$
DDI(M_t).
$$

而是：

$$
Rate_{\text{introduced}}
$$

$$
Rate_{\text{persistent}}
$$

$$
Rate_{\text{obs-resolved}}
$$

以及对应：

$$
ActionFidelity_{\text{constraint}}
$$

与 non-constraint subgroup 的差异。

---

# 10. S2 的最危险简单解释

任何所谓 contextual safety improvement 都必须先击败：

$$
L
=

L_{\text{rec}}
+
\lambda L_{\text{DDI}}.
$$

还要击败：

- static DDI mask；
- global $\lambda$；
- medication-count matching；
- risk-only reranking；
- KEHGCN-style negative relation；
- simple post-hoc filter。

尤其是 medication count。

如果 ours 只是：

$$
|\hat M_t|\downarrow
\Rightarrow
DDI\downarrow,
$$

则安全贡献基本死亡。

---

# 11. S2.5：Contextual Constraint Relevance

这一 Setting 降级成 exploratory。

不能再采用：

$$
e^{-\gamma\Delta t}
$$

失败就 kill hypothesis 的逻辑。

因为 chronic 与 acute condition 的时间语义不同。

真正可能需要的是：

$$
R_c
===

f(
\text{constraint type},
\text{condition persistence},
\Delta t,
X_t
).
$$

但这一步面临很大的 supervision 问题。

因此：

Simple decay 只是 baseline。

它失败只能说明：

> 单纯 recency 不足。

不能说明：

> contextual constraint relevance 不存在。

如果没有可靠 supervision，S2.5 不进入毕业主线。

---

# 12. S3：Dual-Evidence Tension Audit

这是整个修订最重要的变化。

S3 不再问：

$$
Conflict\uparrow
\Rightarrow
Error\uparrow?
$$

因为 ground-truth prescription 与 external safety constraint 本身可能发生冲突。

一个模型偏离真实 prescription，可能降低了 external violation；此时不能简单叫“错误”。

S3 真正研究：

$$
\boxed{
\text{Prediction-support 与 constraint-pressure 是否形成稳定的二维 tension surface？}
}
$$

---

## 12.1 两个轴

定义 predictive-support coordinate：

$$
S^+_{a,m}.
$$

它描述：

> 当前 base predictor 对 action $(a,m)$ 的支持有多强。

第一版可使用校准后的 action score：

$$
S^+_{a,m}
=========

\operatorname{Calibrate}
(
s_f(a,m\mid X_t)
).
$$

也可以加入 S1 得到的 evidence fidelity 作为辅助变量，但不要一开始全部混成复杂网络。

外部 constraint coordinate：

$$
S^-_{a,m}
=========

\operatorname{ConstraintPressure}(a,m;C).
$$

第一版尽量保持简单、可审计。

例如：

- 是否引入 DDI；
- DDI 数量；
- contraindication presence；
- 如果有可靠 severity，才进一步加权。

---

# 13. S3 第一版不要急着定义一个 Conflict Score

不要先写：

$$
Conflict=S^+S^-.
$$

先保留二维结构：

$$
\mathcal T_{a,m}
================

(S^+*{a,m},S^-*{a,m}).
$$

划成四个区域：

|              | Low Constraint | High Constraint |
| ------------ | -------------: | --------------: |
| Low Support  |             LL |              LH |
| High Support |             HL |              HH |

真正感兴趣的是：

$$
\boxed{
HH:
S^+\uparrow
\land
S^-\uparrow
}
$$

即：

> base model 很想做这个 action，但 external constraint 同时很强。

这才叫 tension。

---

## 13.1 S3 要证明什么

不是证明 HH 的 F1 更差。

而是证明：

### Tension prevalence

$$
P(HH)>0
$$

且不是极端稀有事件。

### Stability

HH 在：

- 不同 random seed；
- 不同 split；
- 不同 backbone；
- MIMIC-III / IV，如果可行；

上稳定存在。

### Non-triviality

HH 不能完全被下面变量解释：

$$
\text{drug frequency}
$$

$$
\text{medication count}
$$

$$
\text{patient complexity}
$$

$$
\text{DDI graph degree}
$$

$$
\text{history length}
$$

$$
\text{candidate rank}.
$$

可以做 matching / stratification / regression control。

---

# 14. S3 的真正输出不是模型，而是一张 Tension Map

最理想的核心图不是：

> Conflict 越高，error 越高。

而是：

横轴：

$$
S^+
$$

纵轴：

$$
S^-.
$$

每个区域展示：

- sample mass；
- observed Add/Retain composition；
- base score；
- external violation；
- medication count；
- drug-frequency distribution；
- backbone agreement/disagreement。

然后证明：

$$
\boxed{
\text{HH 是一个稳定、非平凡、无法由简单复杂度变量解释的 action region。}
}
$$

如果 HH 几乎不存在：

S4 主线直接死亡。

如果 HH 完全等于“多药患者”：

Tension hypothesis 也死亡。

---

# 15. S4：Budgeted Tension-Aware Verification & Revision

这是整条路线真正的方法学核心。

X-Ray 文献已经明确形成 Candidate → Verify → Revise 的趋势，SafeRx-Agent、PharmGraph-Auditor 等都在把生成和验证分开，因此“增加一个 verifier”本身不是 novelty。

GiantMed 等也已经说明 boundary medication refinement 是邻近 occupied space。

所以我们的核心问题必须是：

$$
\boxed{
\text{有限 verification budget 应该花在哪些 action 上？}
}
$$

---

## 15.1 系统定义

Base predictor：

$$
f(X_t)\rightarrow
{s_{t,m}}_{m\in\mathcal K_t}.
$$

Audit layer 计算：

$$
\mathcal T_{t,m}
================

(S^+*{t,m},S^-*{t,m}).
$$

Trigger：

$$
\pi(a,m)\in{0,1}.
$$

当：

$$
\pi(a,m)=1
$$

时，action 进入额外 verifier / refiner $R$：

$$
\hat a'_{t,m}
=============

R(X_t,a,m,E,C).
$$

否则：

$$
\hat a'_{t,m}
=============

\hat a_{t,m}.
$$

整体预算：

$$
\sum_{t,m}\pi(a,m)
\leq B.
$$

---

# 16. Tension Trigger 第一版不要复杂

最开始可以使用：

$$
T(a,m)
======

g(S^+,S^-)
$$

其中 $g$ 可以非常简单。

例如：

$$
T_{\min}
========

\min(S^+,S^-)
$$

或：

$$
T_{\times}
==========

S^+S^-.
$$

或者只选 HH quadrant。

如果简单 rule 已经强，不要急着训练 trigger network。

只有 simple tension trigger 有稳定信号以后，才值得研究 learnable allocation policy。

---

# 17. S4 必须比较的 Trigger

原研究框架的 same-budget design 必须保留，而且要加强。

至少比较：

### Random

随机挑 $B$ 个。

### Confidence

低置信度：

$$
|p-0.5|
$$

小的 candidate 优先。

### Uncertainty

如果模型有 uncertainty estimator：

$$
U(a,m).
$$

### Boundary

最接近 decision boundary 的 candidate。

### Risk-only

只按照：

$$
S^-.
$$

### Support-only

只按照：

$$
S^+.
$$

### Medication-complexity

优先复杂 polypharmacy visit。

### Tension

同时使用：

$$
S^+,\ S^-.
$$

这样才能证明真正有价值的是二者交互，而不是：

> 直接挑风险最高的药重新审核。

---

# 18. Revision Budget 必须完全匹配

对于所有 trigger：

$$
N_{\text{revised}}=B.
$$

如果 verifier 调用成本不同，则进一步控制：

$$
\operatorname{ComputeCost}=B_c.
$$

不能：

> Tension Trigger 审 20% candidate，Boundary 只审 5%。

然后说 Tension 更好。

同样 verifier、同样候选池、同样 backbone、同样 revision 次数。

唯一变化：

$$
\boxed{\text{谁被选中审核？}}
$$

这才是最干净的因果实验。

---

# 19. S4 不再用单点 F1 判断胜负

设在预算 $B$ 下：

$$
F_\pi(B)
========

\operatorname{ActionFidelity}.
$$

$$
V_\pi(B)
========

\operatorname{ConstraintViolation}.
$$

$$
C_\pi(B)
========

\operatorname{VerificationCost}.
$$

固定 $B$ 时，我们主要比较：

$$
(F_\pi(B),V_\pi(B)).
$$

一个 operating point $A$ Pareto dominate $B$，需要：

$$
F_A\geq F_B
$$

且：

$$
V_A\leq V_B
$$

并至少一项严格不等。

最终目标不是：

$$
F_{\text{Tension}}

>

F_{\text{Boundary}}.
$$

而是：

$$
\boxed{
\mathcal F_{\text{Tension}}(B)
\succ
\mathcal F_{\text{Boundary}}(B)
}
$$

以及：

$$
\boxed{
\mathcal F_{\text{Tension}}(B)
\succ
\mathcal F_{\text{Uncertainty}}(B).
}
$$

---

# 20. 真正强的 S4 结果应该长什么样

不是：

> 在 $B=10%$ 时 F1 +0.7%。

而是：

当：

$$
B\in[B_1,B_2]
$$

时，大多数预算点均出现：

$$
F_{\text{Tension}}(B)
\geq
F_{\text{Boundary}}(B)
$$

同时：

$$
V_{\text{Tension}}(B)
\leq
V_{\text{Boundary}}(B).
$$

也就是 Tension Trigger 改变整个 envelope。

这才能支持真正独立的 claim：

$$
\boxed{
\text{Tension is a superior allocation signal for scarce verification resources.}
}
$$

---

# 21. S4 的 Kill Criteria

以下任意一种出现，都应该主动杀掉复杂方法。

### Kill 1

$$
\mathcal F_{\text{Tension}}
\approx
\mathcal F_{\text{Uncertainty}}.
$$

说明 uncertainty 已经足够。

### Kill 2

$$
\mathcal F_{\text{Tension}}
\approx
\mathcal F_{\text{Risk-only}}.
$$

说明 predictive support 没有增量价值。

### Kill 3

$$
\mathcal F_{\text{Tension}}
\approx
\mathcal F_{\text{MedCount}}.
$$

说明所谓 tension 只是 polypharmacy proxy。

### Kill 4

只在某一个 $B$ 上赢。

说明可能只是 threshold tuning。

### Kill 5

只在某一个 backbone 有效。

说明不是通用 allocation mechanism。

---

# 22. S5：Counterfactual / Perturbation Stress Tests

S5 不负责证明现实中存在某种临床机制。

它只验证：

$$
\boxed{
\text{已经提出的方法是否真的按声称的机制响应。}
}
$$

这一点保留原研究框架。

---

## 22.1 Evidence deletion

对于 S1 找到的 $E^+$：

$$
X
\rightarrow
X\setminus E^+.
$$

应该看到相关 action support 定向下降。

---

## 22.2 Matched irrelevant deletion

删除相同数量、相似频率，但无关的 $\tilde E$：

$$
X
\rightarrow
X\setminus\tilde E.
$$

应该明显小于删除真正 evidence 的影响。

---

## 22.3 Semantic replacement

$$
E^+
\rightarrow
\tilde E^+.
$$

$\tilde E^+$ 控制 frequency / position，只改变语义。

用于检测 shortcut。

---

## 22.4 Temporal corruption

$$
t_e
\rightarrow
t'_e.
$$

只在 S1.5 已经发现 temporal mechanism 后使用。

---

## 22.5 Constraint injection/removal

加入一条相关 external constraint：

$$
C
\rightarrow
C\cup c_r.
$$

Tension 应该：

$$
T\uparrow.
$$

删除相关 constraint：

$$
C
\rightarrow
C\setminus c_r.
$$

Tension 应：

$$
T\downarrow.
$$

---

## 22.6 Synthetic data 的严格边界

LLM 可以用作：

- stress-case generator；
- paraphrase generator；
- adversarial perturbation generator。

但 synthetic result 不能作为主要 clinical evidence。

X-Ray 中 GenRxR 已经暴露出反事实合成数据真实性和跨环境迁移的边界，因此合成实验只能作为 mechanism stress test。

---

# 23. 六个统一 Research Gates

这部分直接继承原来的科研框架，因为它本身是正确的。

## Gate A：Problem / Phenomenon Exists

先冻结模型。

先观察。

例如 S3 必须先证明 HH tension region：

- 有足够质量；
- 跨 split 稳定；
- 跨 backbone 存在；
- 不是简单 confound。

没有：

$$
\boxed{STOP}
$$

---

## Gate B：Minimal Intervention

任何新 idea 先做最小版本。

例如：

不要：

```text
new GNN
+ Transformer
+ LLM
+ KG
+ RL
+ evidence selector
+ verifier
```

先做：

```text
Frozen baseline
+ simple tension trigger
+ fixed verifier
```

如果最小机制都没有信号：

$$
\boxed{STOP}
$$

---

## Gate C：Strongest Simple Control

这是整个项目最重要的 Gate。

每个复杂模块都必须先问：

> 两行代码能不能解释收益？

Evidence：

$$
\rightarrow
AttentionTopK.
$$

Safety：

$$
\rightarrow
Global\ \lambda.
$$

Tension：

$$
\rightarrow
RiskOnly.
$$

Selective revision：

$$
\rightarrow
Uncertainty/Boundary.
$$

Safety gain：

$$
\rightarrow
MedicationCountMatching.
$$

如果简单 control 已经解释掉结果：

复杂方法死亡。

---

## Gate D：Mechanism Test

如果 claim 是 Tension-based allocation：

不能只展示：

$$
F1_{\text{ours}}>F1_{\text{base}}.
$$

必须展示：

$$
\Delta_{\text{HH}}

>

\Delta_{\text{non-HH}}
$$

或者更重要：

在相同 $B$ 下，Tension policy 的 frontier 改善来自它更准确地选中了“值得 revision 的 action”。

---

## Gate E：Backbone Independence

至少选三个结构差异明显的 backbone。

例如：

SafeDrug：

代表 classic DDI-aware。

ARMR：

代表 temporal / medication transition modeling。

HypeMed：

代表 high-order patient/visit retrieval。

然后研究：

$$
B_i+\pi_{\text{Tension}}.
$$

如果：

$$
\Delta_i>0
$$

在多个 backbone 都成立，才能把 claim 从：

> 我们设计了一个更好的模型

升级为：

> 当前 MedRec 系统普遍缺少一个更好的 verification-budget allocation mechanism。

FLAME、KEHGCN 可以作为完整系统 comparison，而不一定强行插件化。

---

## Gate F：Scale Up

只有 A–E 通过以后才扩规模：

- MIMIC-III；
- MIMIC-IV；
- 更多 baseline；
- 多 random seed；
- statistical test；
- robustness；
- efficiency；
- case study；
- external dataset，如果数据映射允许。

不要 idea 还没站稳就开始跑十个数据集。

---

# 24. 最终科研顺序

修正后的顺序应该是：

$$
\boxed{
S{-}1
\rightarrow
S0
\rightarrow
S0.5
\rightarrow
S1/S2
\rightarrow
S1.5
\rightarrow
S3
\rightarrow
S4
\rightarrow
S5
}
$$

其中 S2.5 是可选支线，不作为主线依赖。

更抽象地说：

$$
\boxed{
\text{Legal Observation}
\rightarrow
\text{Empirical Structure}
\rightarrow
\text{Model Evidence}
\rightarrow
\text{External Constraint}
\rightarrow
\text{Decision Tension}
\rightarrow
\text{Budgeted Intervention}
}
$$

---

# 25. 整条路线哪些是“基础设施”，哪些是真正论文贡献

这一点必须分清。

S-1、S0、S0.5：

$$
\boxed{\text{Research validity infrastructure}}
$$

没有它们论文不可信，但本身不一定是 novelty。

S1：

$$
\boxed{\text{model-faithful diagnostic layer}}
$$

可能独立形成 paper，也可能只作为 S3/S4 instrumentation。

S2：

$$
\boxed{\text{transition-level constraint semantics}}
$$

有一定独立 novelty，尤其如果最终证明传统 final-set DDI 掩盖了不同 transition 对 safety state 的贡献。

S3：

$$
\boxed{\text{scientific phenomenon}}
$$

证明存在稳定的 decision-tension surface。

S4：

$$
\boxed{\text{main algorithmic contribution}}
$$

证明 tension 是比 boundary / uncertainty 更有效的 limited-budget allocation signal。

S5：

$$
\boxed{\text{mechanism validation}}
$$

防止结果只是 shortcut。

---

# 26. Idea Ledger：现在应该这样维护

| Setting | Hypothesis                                                     | 最危险解释                          | 最小实验                      | Survive 条件                    | Fail 后怎么办              |
| ------- | -------------------------------------------------------------- | ----------------------------------- | ----------------------------- | ------------------------------- | -------------------------- |
| S-1     | 当前输入满足任务时序语义                                       | future leakage                      | timestamp audit               | 输入合法或任务 claim 降级后合法 | 修数据，不做模型           |
| S0      | set-level 指标掩盖 transition behavior                         | threshold / med count               | frozen baseline decomposition | transition 行为存在稳定差异     | 保留 instrumentation       |
| S0.5    | action / subgroup 有足够观测支持                               | label noise / long tail             | observability + coverage      | support 稳定                    | 缩小 action space          |
| S1      | action prediction 依赖稀疏且 action-specific 的 model evidence | recency / attention / previous drug | frozen evidence search        | same-budget fidelity 更强       | 不训练 selector            |
| S1.5    | clinical incremental evidence 有 action-specific lifecycle     | generic recency                     | stratified temporal audit     | 控制 confound 后仍成立          | 删除 temporal contribution |
| S2      | transition-level constraint 比 final-set DDI 更有信息          | global $\lambda$ / med count        | introduced/persistent audit   | 能解释静态 DDI 不能解释的差异   | safety 退回静态基线        |
| S3      | support × constraint 构成稳定 tension region                   | polypharmacy / rarity / degree      | 2D tension map                | HH 稳定且非 trivial             | 主线终止或重定义           |
| S4      | tension 比 uncertainty/boundary 更适合分配 revision budget     | risk-only / uncertainty / med count | fixed verifier + same budget  | frontier 在区间内 Pareto 改善   | complex trigger 死亡       |
| S5      | 方法对相关 evidence/constraint 有定向响应                      | generic sensitivity                 | controlled perturbation       | relevant perturbation 明显更强  | mechanism claim 降级       |

---

# 27. 不同实验结果，对应不同论文路线

这部分也继承最初框架“结果决定论文，而不是先决定论文再解释结果”的原则。

### 路线 A：S1 很强，S2/S3 弱

那么不要硬写 safety/conflict。

主线变成：

$$
\boxed{
\text{Action-Conditioned Model Evidence for Medication Recommendation}
}
$$

贡献是 action-level faithful evidence。

---

### 路线 B：S1 一般，但 S2 很强

说明真正有价值的是：

$$
\boxed{
\text{Transition-Level Safety Constraint Modeling}
}
$$

围绕 introduced / persistent / observed-resolved constraint 展开。

---

### 路线 C：S3 明显，但 S4 不赢

说明：

> tension phenomenon 是真的，但 tension 不是更好的 allocation signal。

此时不能硬做“Conflict-Aware Revision”。

可能形成 diagnostic / benchmark 型工作，但主模型故事结束。

---

### 路线 D：S3 + S4 全部成立

这是最理想主论文。

逻辑链：

$$
\text{Set-level MedRec}
$$

$$
\Downarrow
$$

$$
\text{Observable Transitions}
$$

$$
\Downarrow
$$

$$
\text{Model Evidence + External Constraints}
$$

$$
\Downarrow
$$

$$
\text{Decision Tension}
$$

$$
\Downarrow
$$

$$
\text{Budgeted Tension-Aware Verification}
$$

$$
\Downarrow
$$

$$
\boxed{
\text{Better Fidelity--Constraint Pareto Frontier}
}
$$

这时论文真正的贡献就不是“双塔”“KG”“LLM agent”或者“又一个 safety loss”。

而是：

> 在有限 verification budget 下，transition-level evidence tension 是比传统 predictive uncertainty 更有效的 intervention-allocation signal。

---

# 28. 代码库应该围绕科研假设，而不是围绕模型名字组织

最初研究框架里“失败的方法死掉，但 instrumentation 留下”的思想非常重要。

建议最终结构：

```text
baselines/
    safedrug/
    molerec/
    vita/
    armr/
    flame/
    kehgcn/
    hypemed/

data_audit/
    decision_time_audit.py
    action_observability.py
    coverage_profiler.py
    leakage_report.py

instrumentation/
    action_decomposition.py
    candidate_builder.py
    medication_count_profiler.py

evidence/
    evidence_atoms.py
    evidence_search.py
    sufficiency.py
    comprehensiveness.py
    semantic_replacement.py
    evidence_lifecycle.py

constraints/
    ddi_matcher.py
    contraindication_matcher.py
    transition_constraints.py
    constraint_provenance.py

tension/
    support_axis.py
    constraint_axis.py
    tension_surface.py
    confound_analysis.py

revision/
    fixed_verifier.py
    random_trigger.py
    uncertainty_trigger.py
    boundary_trigger.py
    risk_trigger.py
    tension_trigger.py

evaluation/
    standard_medrec.py
    action_metrics.py
    evidence_metrics.py
    constraint_metrics.py
    pareto_frontier.py
    budget_curves.py
    bootstrap_ci.py

stress_tests/
    evidence_delete.py
    evidence_replace.py
    temporal_corrupt.py
    constraint_inject.py

experiments/
    s_minus_1/
    s0/
    s1/
    s2/
    s3/
    s4/
    s5/

ledger/
    hypotheses.md
    failed_ideas.md
    experiment_registry.csv
```

核心目的不是代码整洁，而是：

$$
\boxed{
\text{每提出一个新 hypothesis，其边际实验成本持续下降。}
}
$$

---

# 29. 当前最先应该执行什么

不是建 Tension Network。

不是写 Conflict Refiner。

甚至不是训练 Evidence Selector。

第一阶段只需要完成四件事：

1. S-1：锁死 task timestamp semantics。
2. S0/S0.5：完成 action decomposition + observability + coverage。
3. 冻结至少 3 个不同范式 backbone，缓存 candidate-level logits。
4. 完成 S2 transition constraint profiler。

完成以后，代码库应该能对任意一个 $(t,m)$ 输出类似：

```text
patient_id
visit_id
drug_id

previous_state:
    present / absent

observed_transition:
    Add / Retain / Observed-Remove / Not-Added

baseline:
    score
    calibrated_score
    predicted_action

coverage:
    drug_frequency
    patient_support
    subgroup_support

constraint:
    introduced_ddi
    persistent_ddi
    contraindication
    constraint_count

prescription:
    true_set_size
    predicted_set_size
```

有了这个表，才能开始真正研究 S1 和 S3。

---

# 30. 整条路线最后只押一个核心问题

最开始我们的母问题是：

> 什么 evidence 支持一个 medication action？什么 evidence 激活安全约束？两者冲突怎么办？

经过这轮修复后，可以进一步压成：

$$
\boxed{
\textbf{Given limited verification resources, which medication transitions deserve additional review?}
}
$$

而我们真正需要验证的候选答案是：

$$
\boxed{
\textbf{Transitions under simultaneously high predictive support and high external constraint pressure.}
}
$$

最终论文成败不由故事决定，只由下面这个实验决定：

$$
\boxed{
\mathcal F_{\text{Tension}}(B)
\succ
\mathcal F_{\text{Uncertainty}}(B),
\quad
\mathcal F_{\text{Tension}}(B)
\succ
\mathcal F_{\text{Boundary}}(B)
}
$$

在：

$$
B\in[B_1,B_2]
$$

的非平凡区间、多 backbone、严格 medication-count / drug-frequency / complexity controls 下仍成立。

如果成立，这条路线得到的是一个与具体 encoder 解耦的 decision mechanism。

如果不成立，就删除 Tension Trigger，但 S-1、action decomposition、model-faithful evidence、transition constraint audit、coverage profiler 和 Pareto evaluation 全部留下，下一轮 hypothesis 继续建立在这些资产上。

这正是最初那个科研框架真正应该保留下来的核心：

$$
\boxed{
\text{Codebase}
\rightarrow
\text{Observation}
\rightarrow
\text{Hypothesis}
\rightarrow
\text{Minimal Intervention}
\rightarrow
\text{Falsification}
}
$$

$$
\boxed{
\rightarrow
\begin{cases}
\text{Scale Up / Paper}, & \text{if survives}\
\text{Failure Knowledge}\rightarrow\text{New Hypothesis}, & \text{if fails}
\end{cases}
}
$$

而不是先给方法取名字，再努力寻找一个能够证明它有效的问题。
