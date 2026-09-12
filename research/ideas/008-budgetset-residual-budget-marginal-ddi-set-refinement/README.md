<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `ADMITTED / GATE_01_PROTOCOL_CORRECTED_PENDING_INTEGRITY_REAUDIT`
- **Stage**: `IDEA_008_GATE_01_PROTOCOL_CORRECTED_PENDING_INTEGRITY_REAUDIT`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md), v1.1 corrected and not executed
- **Historical integrity audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md), verdict `DESIGN_INTEGRITY_FAIL` on v1.0
- **Implementation**: `NOT_STARTED`
- **Training**: `NOT_AUTHORIZED`
- **Execution**: `NOT_AUTHORIZED`
- **Gate01-Audit**: unopened
- **Quarantine**: intact
- **Next owner**: `ccf-integrity-auditor`

Idea 008 remains admitted for one bounded kill-first method cycle. No Gate-01 experiment has been executed. Protocol v1.1 is corrected but not integrity-approved; implementation, training, and execution remain blocked until independent re-audit and subsequent pipeline authorization.

## Scientific question

At exact per-patient prescription cardinality, does an iterative joint-set refiner obtain utility–DDI frontier value that cannot be absorbed by an equal-information deterministic fixed-K solver or by a budget-conditioned independent medication scorer?

The admitted claim remains:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The surviving scientific interaction remains:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

Generic joint set prediction, Pareto medication recommendation, DDI-aware loss, a DDI target by itself, one-model/many-objectives, list-wise refinement, training-time safety coefficients, and generic preference conditioning are not novelty claims.

## Admitted mechanism identity

For patient-specific fixed cardinality `K_x`, define hard-set DDI rate

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
\Delta_i^{(t)}=u_i-\lambda_i^{(t)}c_i^{(t)},
$$

with the explicit frozen-score residual anchor

$$
z_i^{(t+1)}=s_i+\Delta_i^{(t)}.
$$

The final hard prescription preserves exact cardinality:

$$
S_b=\operatorname{TopK}_{K_x}(z^{(T)}).
$$

For symmetric `D`:

$$
\frac{\partial R_{DDI}(q)}{\partial q_i}=\frac{2}{K_x}c_i(q).
$$

`rho` is surrogate residual slack on relaxed `q`; it is not a hard DDI or clinical safety guarantee. Final hard-set achieved DDI is the operating-point quantity.

## Gate 01 protocol v1.1

The authoritative protocol is [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md). Its frozen scientific choices remain:

- backbone: `MoleRec / molerec-embedding` at `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`;
- candidate pool: complete `131` medication vocabulary;
- `K_x`: count of Frozen Base probabilities `>= 0.5`;
- initialization: `q^(0)=sigmoid(s)`;
- `T=2`;
- budgets: `0.60`, `0.80`, and `1.00` times `r_train`;
- learned seeds: `{2002, 2003, 2004}`;
- LR: `{3e-4, 1e-3}`;
- `eta`: `{5, 10}`;
- `gamma=1e-3`;
- primary utility: Jaccard; supporting F1 and PRAUC;
- primary killers: Fixed-K Budget-Aware Greedy + 1-Swap and Budget-Conditioned Independent Scorer;
- fixed-lambda support: `{0, 0.25, 0.5, 1, 2, 4}`;
- practical margins: `delta_U=0.005`, `delta_R=0.005`;
- bootstrap: `1000` patient-clustered resamples, seed `80081`.

Protocol v1.1 uniquely specifies the admitted residual anchor, exact patient-conditioned MoleRec `e_i(x)`, deterministic Idea-local split, low-cardinality Greedy branches, learned checkpoint/configuration selection, visit/seed/bootstrap/frontier semantics, favorable-seed rule, and terminal precedence. No scientific design choice has been expanded.

## Frozen killer roles

### Killer 1 — Fixed-K Budget-Aware Greedy + 1-Swap

This deterministic solver receives the same frozen scores, DDI matrix, complete candidate pool, requested target, and exact `K_x` as BudgetSet.

```text
Greedy+1Swap comparable to or better than BudgetSet
-> KILL_BUDGETSET
```

No exact-solver zoo is part of Gate 01.

### Killer 2 — Budget-Conditioned Independent Scorer

This learned control receives the same frozen patient-conditioned score, the same frozen patient/visit-conditioned MoleRec `e_i(x)`, requested `b`, Train-only static DDI summaries, identical training/tuning entitlement, and the same explicit `+s_i` residual anchor, but no provisional-set composition, current-set marginal DDI, relaxed residual slack, or iterative feedback.

```text
Independent Conditional Scorer comparable to or better than BudgetSet
-> KILL_JOINT_SET_INTERACTION
```

### Fixed-lambda family

The six-value fixed-lambda family remains supporting evidence for conditional amortization versus separately calibrated fixed operating points. It is not a third primary killer.

## Gate 01 pass boundary

A future re-audited and explicitly authorized Gate may return `PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES` only under the frozen all-conditions logic: exact cardinality, all-target compliance, material DDI responsiveness, both hard-set composition transitions, frontier wins against both killers at both `b_L` and `b_M`, and the required `>=2/3` favorable-seed support for every killer-region comparison.

A single isolated operating-point win does not pass. Inconclusive evidence does not authorize protocol rescue.

## Authorization boundary

Current authorization is integrity re-audit only. Do not perform:

- Gate implementation;
- model training or Gate execution;
- Gate01-Audit access;
- G3/G4, R0 Holdout, or historical project test access;
- subgroup mining or feature fishing;
- new patient, drug, ingredient, or molecular encoders;
- Transformer, Mamba, MoE, RL, LLM, retrieval, or unrelated architecture expansion;
- exact-solver families;
- new losses, targets, seeds, budgets, or tuning dimensions;
- paper-level SOTA benchmarking.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.1: CORRECTED / DESIGNED_NOT_EXECUTED
Integrity state: PENDING_REAUDIT
Stage: IDEA_008_GATE_01_PROTOCOL_CORRECTED_PENDING_INTEGRITY_REAUDIT
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Next owner: ccf-integrity-auditor
After a future integrity pass only: ccf-pipeline-orchestrator may decide execution authorization
```
