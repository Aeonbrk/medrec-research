<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `ADMITTED / GATE_01_DESIGN_INTEGRITY_FAIL`
- **Stage**: `IDEA_008_GATE_01_DESIGN_INTEGRITY_FAIL_PENDING_PROTOCOL_CORRECTION`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md), v1.0 failed pre-execution integrity audit
- **Integrity audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md)
- **Implementation**: `NOT_STARTED`
- **Training**: `NOT_AUTHORIZED`
- **Execution**: `NOT_AUTHORIZED`
- **Quarantine**: intact
- **Next owner**: `ccf-experiment-designer / design`

Idea 008 remains admitted for one bounded kill-first method cycle. No Gate-01 experiment has been executed. Protocol v1.0 is not execution-ready and may only receive the bounded corrections identified by the integrity audit before independent re-audit.

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

For a patient-specific fixed cardinality `K_x`, define the hard-set DDI rate

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

with the admitted explicit frozen-score residual anchor

$$
z_i^{(t+1)}=s_i+\Delta_i^{(t)}.
$$

The final hard prescription preserves exact cardinality:

$$
S_b=\operatorname{TopK}_{K_x}(z^{(T)}).
$$

For symmetric `D`,

$$
\frac{\partial R_{DDI}(q)}{\partial q_i}=\frac{2}{K_x}c_i(q).
$$

`rho` is surrogate residual slack on relaxed `q`; it is not a hard DDI or clinical safety guarantee. Final hard-set achieved DDI is the operating-point quantity.

Protocol v1.0 omitted the explicit `+s_i` residual anchor in its learned update. The integrity audit classifies that as scientific drift, not an accepted redefinition of the Idea.

## Gate 01 v1.0 integrity result

`DESIGN_INTEGRITY_FAIL`.

Execution is blocked only by the seven bounded protocol-definition findings recorded in the authoritative audit:

1. restore the admitted explicit frozen-score residual anchor for both learned families;
2. freeze the exact pinned MoleRec representation used as `e_i` and its extraction point;
3. freeze the exact patient-only Dev/Audit hash formula;
4. define Greedy+1Swap for `K_x=0` and `K_x=1`;
5. freeze checkpoint-selection and patience semantics;
6. freeze target/composition aggregation, frontier bootstrap, and seed semantics;
7. freeze one primary terminal-verdict precedence order.

These are execution-readiness corrections only. They do not authorize new methods, extra solvers, losses, targets, seeds, datasets, encoders, or backbone changes.

## Frozen killer roles

### Killer 1 — Fixed-K Budget-Aware Greedy + 1-Swap

This deterministic solver must receive the same frozen scores, DDI matrix, complete candidate pool, requested target, and exact `K_x` as BudgetSet.

```text
Greedy+1Swap comparable to or better than BudgetSet
-> KILL_BUDGETSET
```

No exact-solver zoo is part of Gate 01.

### Killer 2 — Budget-Conditioned Independent Scorer

This learned control must receive the same frozen patient-conditioned score and the same frozen medication representation plus requested `b` and Train-only static DDI summaries, with comparable learned capacity but no provisional-set composition, current-set marginal DDI, residual relaxed slack, or iterative feedback.

```text
Independent Conditional Scorer comparable to or better than BudgetSet
-> KILL_JOINT_SET_INTERACTION
```

### Fixed-lambda family

The six-value fixed-lambda family remains supporting evidence for conditional amortization versus separately calibrated fixed operating points. It is not a third primary killer.

## Gate 01 pass boundary

A future corrected and re-audited Gate may return `PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES` only under the frozen all-conditions logic: exact cardinality, all-target compliance, material DDI responsiveness, hard-set composition response, two separated frontier wins against both killers, and non-one-seed-only support.

A single isolated operating-point win does not pass. Inconclusive practical evidence does not authorize protocol rescue.

## Authorization boundary

Current authorization is protocol correction only. Do not perform:

- model implementation for Gate execution;
- model training or Gate execution;
- G3/G4, R0 Holdout, or historical project test access;
- subgroup mining or feature fishing;
- new patient, drug, ingredient, or molecular encoders;
- Transformer, Mamba, MoE, RL, LLM, retrieval, or unrelated architecture expansion;
- exact-solver families;
- new losses, targets, seeds, or budget sweeps;
- paper-level SOTA benchmarking.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.0: DESIGN_INTEGRITY_FAIL / NOT EXECUTED
Stage: IDEA_008_GATE_01_DESIGN_INTEGRITY_FAIL_PENDING_PROTOCOL_CORRECTION
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Quarantine: intact
Next owner: ccf-experiment-designer / design
Next task: bounded protocol correction for audit blockers B1-B7 only
After correction: ccf-integrity-auditor re-audit
After a future integrity pass only: ccf-pipeline-orchestrator may decide execution authorization
```