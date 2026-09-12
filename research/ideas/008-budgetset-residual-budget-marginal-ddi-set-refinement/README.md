<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `ADMITTED`
- **Stage**: `IDEA_008_ADMITTED_PENDING_GATE_01_DESIGN`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Admission owner**: `ccf-pipeline-orchestrator`
- **Admission source revision**: `0be7c5c30762b232cd47a0c2ccf9b08aee1b23b5`
- **Gate 01 owner**: `ccf-experiment-designer / design`
- **Gate 01 protocol**: not yet designed/frozen
- **Training**: `NOT_AUTHORIZED`
- **Quarantine**: intact

Idea 008 is admitted for one bounded kill-first method cycle. Admission is not empirical evidence and does not authorize model training.

## Scientific question

At exact per-patient prescription cardinality, does an iterative joint-set refiner obtain utility–DDI frontier value that cannot be absorbed by an equal-information deterministic fixed-K solver or by a budget-conditioned independent medication scorer?

The admitted claim is deliberately narrow:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

## Mechanism

For a patient-specific fixed cardinality `K_x`, define the hard-set DDI rate

$$
R_{DDI}(S)=\frac{\sum_{i<j}D_{ij}\mathbf{1}[i\in S]\mathbf{1}[j\in S]}{\binom{K_x}{2}}.
$$

For the relaxed iterate `q^(t)`, candidate `i` receives a composition-dependent marginal DDI cost

$$
c_i^{(t)}=\frac{1}{K_x-1}\sum_{j\neq i}D_{ij}q_j^{(t)}.
$$

The requested target `b` induces relaxed residual constraint slack

$$
\rho^{(t)}=b-R_{DDI}(q^{(t)}).
$$

Candidate utility and residual-conditioned price are

$$
u_i=u_\phi(s_i,e_i),
$$

$$
\lambda_i^{(t)}=\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)})),
$$

with refinement score

$$
\Delta_i^{(t)}=u_i-\lambda_i^{(t)}c_i^{(t)}.
$$

The final prescription preserves exact cardinality:

$$
S_b=\operatorname{TopK}_{K_x}(z^{(T)}).
$$

For symmetric `D` under the current normalization,

$$
\frac{\partial R_{DDI}(q)}{\partial q_i}=\frac{2}{K_x}c_i(q).
$$

This identity motivates `c_i(q)` as the composition-dependent marginal interaction term. It does not create a clinical guarantee.

## Claim and novelty boundary

The surviving scientific interaction is:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

The following are explicitly not novelty claims:

- joint set prediction;
- Pareto medication recommendation;
- DDI-aware loss;
- DDI target alone;
- one model / many objectives;
- list-wise refinement;
- training-time safety coefficients;
- generic preference conditioning.

`rho` is defined on the relaxed iterate and is only a surrogate residual-constraint slack. Final hard-set achieved DDI is the operating-point quantity. The Idea does not claim a clinical safety guarantee, treatment effect, causal benefit, or clinical optimality.

The pair-risk domain for `K_x < 2` is intentionally left to the Gate 01 protocol. It must be defined before execution and may not be selected after seeing results.

## Strongest simple alternatives

### Killer 1 — Fixed-K Budget-Aware Greedy + 1-Swap

This control receives the same frozen recommendation scores, DDI matrix, candidate pool, requested DDI target, and exact per-patient cardinality as BudgetSet. It is the first direct test of whether learned iterative joint-set refinement adds value beyond a strong deterministic solver.

Kill rule:

```text
Greedy+1Swap ≈ BudgetSet
→ KILL_BUDGETSET
```

Exact MILP/MIQP does not replace this control at Gate 01. An exact solver may be added later for paper-level efficiency/optimality comparison only if BudgetSet survives the first gate.

### Killer 2 — Budget-Conditioned Independent Scorer

This control receives the same patient/candidate information and requested target but scores medications independently rather than through composition-dependent set interaction.

Kill rule:

```text
Independent Conditional Scorer ≈ BudgetSet
→ KILL JOINT-SET INTERACTION CLAIM
```

## Gate 01 hypothesis

The next owner must freeze the cheapest falsifiable test of exactly this statement:

> Under identical frozen recommendation scores, DDI information, candidate pool, requested DDI target, and exact per-patient cardinality, a residual-budget marginal-DDI joint set refiner provides incremental utility–DDI frontier value beyond an equal-information deterministic fixed-K direct solver and a budget-conditioned independent scorer.

The gate must be designed before any model training or numerical execution. Admission does not freeze a budget grid, training recipe, model width/depth, or evaluation threshold.

## Authorization boundary

The current stage authorizes design only.

Do not perform:

- recommendation-model training;
- experiment execution;
- budget-grid tuning;
- access to G3/G4, R0 Holdout, or the historical project test split;
- architecture expansion;
- a new patient encoder, molecular encoder, or ingredient module;
- RL, MoE, LLM, or retrieval additions;
- IngSet review;
- new candidate search;
- another BudgetSet strict review.

## Historical constraints retained

Ideas 001--007 remain terminated. Idea 007 remains `TERMINATED_AT_GATE_01_P1`. The strict drug-changing Pair/Context route remains `ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE`. Idea 008 neither reopens nor depends on those failed mechanisms.

Reusable project rules still apply: the strongest equal-information direct control comes first; fixed-cardinality evaluation must not confuse medication count with normalized DDI interaction propensity; and a learned method survives only if it adds value beyond direct use of the same information.

## Current state

```text
Idea 008: ADMITTED
Active Idea: 008-budgetset-residual-budget-marginal-ddi-set-refinement
Stage: IDEA_008_ADMITTED_PENDING_GATE_01_DESIGN
Gate 01: NOT YET DESIGNED / NOT FROZEN
Training: NOT_AUTHORIZED
Quarantine: intact
Next owner: ccf-experiment-designer / design
Next task: freeze cheapest falsifiable Gate 01
```
