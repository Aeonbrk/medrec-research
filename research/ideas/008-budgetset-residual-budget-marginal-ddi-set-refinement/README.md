<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `ADMITTED / GATE_01_V1_2_IMPLEMENTATION_INTEGRITY_PASS`
- **Stage**: `IDEA_008_GATE_01_IMPLEMENTATION_INTEGRITY_PASS_PENDING_PIPELINE_ROUTING`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md), v1.2 designed and not executed
- **Implementation authorization**: [`experiments/gate-01-implementation-authorization.md`](experiments/gate-01-implementation-authorization.md)
- **Mechanical preflight**: [`experiments/gate-01-mechanical-preflight.json`](experiments/gate-01-mechanical-preflight.json), verdict `MECHANICAL_PREFLIGHT_PASS`
- **Independent implementation verification**: [`experiments/gate-01-implementation-integrity-verification.md`](experiments/gate-01-implementation-integrity-verification.md), verdict `IMPLEMENTATION_INTEGRITY_PASS`
- **Historical v1.0 audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md), verdict `DESIGN_INTEGRITY_FAIL`
- **Historical v1.1 re-audit**: [`experiments/gate-01-design-integrity-reaudit-v1.1.md`](experiments/gate-01-design-integrity-reaudit-v1.1.md), verdict `DESIGN_INTEGRITY_FAIL`
- **v1.2 re-audit**: [`experiments/gate-01-design-integrity-reaudit-v1.2.md`](experiments/gate-01-design-integrity-reaudit-v1.2.md), verdict `DESIGN_INTEGRITY_PASS`
- **Formal training**: `NOT_AUTHORIZED`
- **Formal Gate execution**: `NOT_AUTHORIZED`
- **Gate01-Audit**: unopened
- **Quarantine**: intact
- **Next owner**: `ccf-pipeline-orchestrator`

Idea 008 remains admitted for one bounded kill-first method cycle. Protocol v1.2 is independently design-integrity approved. The authorized implementation/mechanical-preflight surface is complete and independently verified, including the real frozen-MoleRec Train-only extraction check. No scientific Gate result exists, and recommendation-model training, Gate01-Audit access, and formal Gate execution remain unauthorized.

## Scientific question

At exact per-patient prescription cardinality, does an iterative joint-set refiner obtain utility–DDI frontier value that cannot be absorbed by an equal-information deterministic fixed-K solver or by a budget-conditioned independent medication scorer?

The admitted claim is:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The scientific interaction under test is:

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
z_i^{(t+1)}=s_i+u_i-\lambda_i^{(t)}c_i^{(t)}.
$$

The final hard prescription preserves exact cardinality:

$$
S_b=\operatorname{TopK}_{K_x}(z^{(T)}).
$$

`rho` is relaxed surrogate slack, not a clinical guarantee. Final hard-set achieved DDI is the operating-point quantity.

## Gate 01 protocol v1.2

The authoritative scientific protocol is [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md). Frozen choices include:

- backbone `MoleRec / molerec-embedding` at `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`;
- complete `131`-medication candidate vocabulary;
- `K_x` from Frozen Base probability threshold `0.5`;
- `q^(0)=sigmoid(s)` and `T=2`;
- budgets `0.60`, `0.80`, `1.00` times `r_train`;
- learned seeds `{2002, 2003, 2004}`;
- LR `{3e-4, 1e-3}`, `eta` `{5, 10}`, `gamma=1e-3`;
- primary utility Jaccard, supporting F1 and PRAUC;
- primary killers Fixed-K Budget-Aware Greedy + 1-Swap and Budget-Conditioned Independent Scorer;
- fixed-lambda support `{0, 0.25, 0.5, 1, 2, 4}`;
- practical margins `delta_U=0.005`, `delta_R=0.005`;
- `1000` patient-clustered bootstrap resamples with seed `80081`.

The v1.2 design re-audit passes B1–B7: scientific identity, MoleRec representation, deterministic patient split, low-cardinality execution, checkpoint/patience/configuration selection, aggregation/frontier/bootstrap/seed semantics, and terminal precedence.

## Frozen killer roles

### Killer 1 — Fixed-K Budget-Aware Greedy + 1-Swap

This deterministic solver receives the same frozen scores, DDI matrix, complete candidate pool, requested target, and exact `K_x` as BudgetSet.

```text
Greedy+1Swap comparable to or better than BudgetSet
-> KILL_BUDGETSET
```

### Killer 2 — Budget-Conditioned Independent Scorer

This learned control receives the same frozen patient-conditioned score, the same frozen patient/visit-conditioned MoleRec `e_i(x)`, requested `b`, Train-only static DDI summaries, identical training/tuning entitlement, and the same explicit `+s_i` residual anchor, but no provisional-set composition, current-set marginal DDI, relaxed residual slack, or iterative feedback.

```text
Independent Conditional Scorer comparable to or better than BudgetSet
-> KILL_JOINT_SET_INTERACTION
```

### Fixed-lambda family

The six-value fixed-lambda family is supporting evidence for conditional amortization versus separately calibrated fixed operating points. It is not a third primary killer.

## Implementation / mechanical-preflight verification

The verified Idea-local implementation preserves:

```text
q0
-> c0, rho0
-> z1, q1
-> c1, rho1
-> z2
-> exact TopK(K_x)
```

The synthetic-only self-check cannot emit PASS; it returns `MECHANICAL_PREFLIGHT_INCOMPLETE` without validated real frozen-MoleRec evidence. The canonical public-safe record establishes a Train-only pinned integration with `eval()` / no-gradient execution, same-forward score/representation provenance, 131 score candidates, and a `[131, 64]` candidate-representation tensor immediately before `score_extractor`.

The independent verifier also confirmed exact-cardinality and `K_x=0/1` behavior, deterministic Greedy+1Swap and fixed-lambda controls, Independent no-current-set-feedback semantics, ordinary and empty-frontier comparators, matched Independent seeds, deterministic-control seed handling, patient-cluster bootstrap multiplicity/frontier recomputation, learned-selection ordering, and terminal precedence.

Mechanical success means only:

```text
MECHANICAL_PREFLIGHT_PASS
```

It is not `PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES`.

## Gate 01 pass boundary

A future explicitly authorized Gate may return `PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES` only under the frozen all-conditions logic: exact cardinality, all-target compliance, material DDI responsiveness, both hard-set composition transitions, frontier wins against both killers at both `b_L` and `b_M`, and the required `>=2/3` favorable-seed support for every killer-region comparison.

A single isolated operating-point win does not pass. Inconclusive evidence does not authorize protocol rescue.

## Authorization boundary

Do not perform formal Gate execution or recommendation-model training, and do not open Gate01-Audit until a later route explicitly authorizes those actions.

Also do not access:

- G3/G4, R0 Holdout, or historical project test;
- subgroup mining or feature fishing;
- new patient, drug, ingredient, or molecular encoders;
- Transformer, Mamba, MoE, RL, LLM, retrieval, or unrelated architecture expansion;
- exact-solver families;
- new losses, targets, seeds, budgets, or tuning dimensions;
- paper-level SOTA benchmarking.

If a later formal-execution phase introduces execution-specific training runner code beyond the mechanically verified surface, that code must satisfy protocol v1.2 before it is used for Gate evidence.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / DESIGNED_NOT_EXECUTED
Integrity state: DESIGN_INTEGRITY_PASS
Stage: IDEA_008_GATE_01_IMPLEMENTATION_INTEGRITY_PASS_PENDING_PIPELINE_ROUTING
Implementation/mechanical preflight: COMPLETE / MECHANICAL_PREFLIGHT_PASS
Independent implementation verification: IMPLEMENTATION_INTEGRITY_PASS
Formal training: NOT_AUTHORIZED
Formal Gate execution: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Next owner: ccf-pipeline-orchestrator
Next task: decide formal Gate-execution authorization only; do not execute Gate 01 automatically
```
