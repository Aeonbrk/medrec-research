# Handoff: Idea 008 BudgetSet Admission

## Current state

- **Current Stage**: `IDEA_008_ADMITTED_PENDING_GATE_01_DESIGN`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Admission owner**: `ccf-pipeline-orchestrator`
- **Admission source revision**: `0be7c5c30762b232cd47a0c2ccf9b08aee1b23b5`
- **Ideas 001--007**: terminated
- **Idea 007**: `TERMINATED_AT_GATE_01_P1`
- **Pair/Context**: `ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE`
- **Formal recommendation-model training**: `NOT_AUTHORIZED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical test remain uninspected
- **Next owner**: `ccf-experiment-designer / design`
- **Next task**: freeze the cheapest falsifiable Gate 01; do not train

Idea 008 is formally admitted as one bounded kill-first method cycle. Admission is not empirical evidence and does not authorize recommendation-model training.

## Idea 008

Working name:

**BudgetSet: Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement**

Canonical path:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/`

The admitted scientific claim is deliberately narrow:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

For exact per-patient cardinality `K_x`, the admitted mechanism is based on

$$
R_{DDI}(S)=\frac{\sum_{i<j}D_{ij}\mathbf{1}[i\in S]\mathbf{1}[j\in S]}{\binom{K_x}{2}},
$$

$$
c_i^{(t)}=\frac{1}{K_x-1}\sum_{j\neq i}D_{ij}q_j^{(t)},
$$

$$
\rho^{(t)}=b-R_{DDI}(q^{(t)}),
$$

$$
u_i=u_\phi(s_i,e_i),
$$

$$
\lambda_i^{(t)}=\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)})),
$$

$$
\Delta_i^{(t)}=u_i-\lambda_i^{(t)}c_i^{(t)},
$$

and the final hard set is

$$
S_b=\operatorname{TopK}_{K_x}(z^{(T)}).
$$

With a symmetric DDI matrix and the current normalization,

$$
\frac{\partial R_{DDI}(q)}{\partial q_i}=\frac{2}{K_x}c_i(q).
$$

## Claim boundary

- `\rho` is a surrogate residual-constraint slack defined on relaxed `q`; it is not a clinical safety guarantee.
- The achieved DDI of the final hard set is the operating-point quantity.
- The pair-risk domain for `K_x < 2` is not decided at admission and must be frozen by the Gate 01 protocol before execution.
- Admission does not claim clinical optimality, safety certification, treatment effect, or causal benefit.

The following are not novelty claims:

- joint set prediction;
- Pareto medication recommendation;
- DDI-aware loss;
- DDI target alone;
- one model / many objectives;
- list-wise refinement;
- training-time safety coefficients;
- generic preference conditioning.

The surviving interaction is:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

## Frozen killer controls

Gate 01 must include these equal-information controls:

1. **Fixed-K Budget-Aware Greedy + 1-Swap**.
   If `Greedy+1Swap ≈ BudgetSet`, terminate with `KILL_BUDGETSET`.
2. **Budget-Conditioned Independent Scorer**.
   If the independent conditional scorer is comparable to BudgetSet, terminate the joint-set interaction claim.

The first killer remains a deterministic fixed-K direct solver. Exact MILP/MIQP is not a substitute for this first killer; an exact solver may be considered later for paper-level efficiency or optimality comparison only if the Idea survives Gate 01.

## Gate 01 hypothesis to freeze next

> Under identical frozen recommendation scores, DDI information, candidate pool, requested DDI target, and exact per-patient cardinality, a residual-budget marginal-DDI joint set refiner provides incremental utility–DDI frontier value beyond an equal-information deterministic fixed-K direct solver and a budget-conditioned independent scorer.

`ccf-experiment-designer / design` owns the next stage. Its job is to freeze the cheapest falsifiable protocol, not to execute it.

## Authorization boundary

Until Gate 01 is frozen, do not perform:

- recommendation-model training or experiment execution;
- budget-grid tuning;
- quarantine access, including G3/G4, R0 Holdout, or historical test;
- architecture expansion or new patient/molecular/ingredient encoders;
- RL, MoE, LLM, retrieval, or unrelated candidate search;
- new BudgetSet strict review or alternate-Idea brainstorming.

## Routing

```text
Idea 008: ADMITTED
Active Idea: 008-budgetset-residual-budget-marginal-ddi-set-refinement
Stage: IDEA_008_ADMITTED_PENDING_GATE_01_DESIGN
Training: NOT_AUTHORIZED
Quarantine: intact
Next owner: ccf-experiment-designer / design
Next task: freeze cheapest falsifiable Gate 01
```
