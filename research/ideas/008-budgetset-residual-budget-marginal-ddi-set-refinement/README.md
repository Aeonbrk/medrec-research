<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `ADMITTED / GATE_01_DESIGN_FROZEN`
- **Stage**: `IDEA_008_GATE_01_DESIGN_FROZEN_PENDING_INTEGRITY_AUDIT`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 owner**: `ccf-experiment-designer / design`
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md)
- **Gate 01 design verdict**: `DESIGN_READY`
- **Training**: `NOT_AUTHORIZED`
- **Quarantine**: intact
- **Next owner**: `ccf-integrity-auditor`

Idea 008 remains one bounded kill-first method cycle. The Gate 01 design is frozen, but no experiment has been executed and no recommendation-model training is authorized until independent design/integrity audit and subsequent pipeline authorization.

## Scientific question

At exact per-patient prescription cardinality, does an iterative joint-set refiner obtain utility–DDI frontier value that cannot be absorbed by an equal-information deterministic fixed-K solver or by a budget-conditioned independent medication scorer?

The admitted claim remains:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The surviving scientific interaction is:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

Generic joint set prediction, Pareto medication recommendation, DDI-aware loss, a DDI target by itself, one-model/many-objectives, list-wise refinement, training-time safety coefficients, and generic preference conditioning are not novelty claims.

## Mechanism

For a patient-specific fixed cardinality `K_x`, the hard-set DDI rate is

$$
R_{DDI}(S)=\frac{\sum_{i<j}D_{ij}\mathbf{1}[i\in S]\mathbf{1}[j\in S]}{\binom{K_x}{2}}.
$$

For relaxed iterate `q^(t)`:

$$
R_{DDI}(q)=\frac{\sum_{i<j}D_{ij}q_iq_j}{\binom{K_x}{2}},
$$

$$
c_i^{(t)}=\frac{1}{K_x-1}\sum_{j\ne i}D_{ij}q_j^{(t)},
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
z_i^{(t+1)}=u_i-\lambda_i^{(t)}c_i^{(t)}.
$$

The frozen Gate uses `T=2`, the smallest value that creates one actual composition-feedback cycle. The final hard prescription is

$$
S_b=\operatorname{TopK}_{K_x}(z^{(2)}).
$$

For symmetric `D`,

$$
\frac{\partial R_{DDI}(q)}{\partial q_i}=\frac{2}{K_x}c_i(q).
$$

`rho` is surrogate residual slack on relaxed `q`; it is not a hard DDI or clinical safety guarantee. Final hard-set achieved DDI is the operating-point quantity.

## Frozen Gate 01 design

The authoritative protocol is [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md). Its central choices are:

- frozen backbone: `MoleRec / molerec-embedding`;
- candidate pool: complete 131-medication vocabulary for every method;
- `K_x`: frozen MoleRec threshold-0.5 output cardinality, not ground-truth count;
- `K_x < 2`: pairwise DDI risk and candidate marginal DDI are both zero;
- deterministic initialization: `z^(0)=s`, `q^(0)=sigmoid(s)`;
- refinement depth: `T=2`, no depth sweep;
- budgets: Train-calibrated `{0.60, 0.80, 1.00} * r_train`, with no extra targets;
- conditional training support: uniform over those three targets;
- primary utility metric: Jaccard; F1 and PRAUC are supporting;
- learned seeds: `{2002, 2003, 2004}`;
- patient-clustered Audit bootstrap: 1000 resamples, seed `80081`;
- practical margins: `0.005` absolute Jaccard and `0.005` absolute hard-set DDI rate;
- exact fixed-cardinality compliance: `100%`.

### Killer 1 — Fixed-K Budget-Aware Greedy + 1-Swap

This deterministic solver receives the same frozen scores, DDI matrix, candidate pool, requested target, and exact `K_x`. It constructs a budget-aware fixed-K set, repairs budget violation with deterministic 1-swaps, then performs feasible utility-improving 1-swaps until no improving feasible swap remains.

```text
Greedy+1Swap comparable to or better than BudgetSet
-> KILL_BUDGETSET
```

No exact-solver zoo is part of Gate 01.

### Killer 2 — Budget-Conditioned Independent Scorer

This learned control receives the same frozen patient-conditioned score `s_i`, medication embedding `e_i`, requested `b`, and Train-only static DDI summaries. It has comparable learned head capacity but cannot access provisional set composition, `q^(t)`, candidate-to-current-set marginal DDI, residual relaxed slack, or iterative feedback.

```text
Independent Conditional Scorer comparable to or better than BudgetSet
-> KILL_JOINT_SET_INTERACTION
```

### Fixed-lambda family

A six-value deterministic fixed-lambda support is calibrated on Gate01-Train to the three requested targets. It is supporting evidence for conditional amortization versus separately tuned fixed operating points and is not a third primary killer.

## Gate 01 pass boundary

`PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES` requires all of the following:

1. exact `|S_b|=K_x` for every method and visit;
2. BudgetSet target compliance at all three requested budgets;
3. materially ordered hard-set achieved DDI across the three budgets;
4. actual hard-set medication substitutions across adjacent budgets;
5. BudgetSet materially outside the Greedy+1Swap frontier at both primary regions;
6. BudgetSet materially outside the Independent Conditional frontier at both primary regions;
7. neither required effect is carried by one favorable seed only.

A single isolated operating-point win does not pass. Inconclusive practical intervals stop the route; they do not authorize more seeds, more budgets, a different `T`, additional losses, another backbone, or architecture rescue.

## Authorization boundary

Current authorization is design only. Do not perform:

- model training or Gate execution;
- G3/G4, R0 Holdout, or historical test access;
- subgroup mining or feature fishing;
- new patient, drug, ingredient, or molecular encoders;
- Transformer, Mamba, MoE, RL, LLM, retrieval, or unrelated architecture expansion;
- exact-solver families;
- paper-level SOTA benchmarking;
- a second formulation rescue.

## Routing

```text
Idea 008: ADMITTED / GATE_01_DESIGN_FROZEN
Stage: IDEA_008_GATE_01_DESIGN_FROZEN_PENDING_INTEGRITY_AUDIT
Gate 01 protocol: DESIGN_READY / NOT EXECUTED
Training: NOT_AUTHORIZED
Quarantine: intact
Next owner: ccf-integrity-auditor
Next task: independent Gate-01 design/integrity audit
```
