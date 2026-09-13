<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `ADMITTED / IDEA_008_GATE_01_RUNNER_IMPLEMENTED_PENDING_INTEGRITY_VERIFICATION`
- **Stage**: `IDEA_008_GATE_01_RUNNER_IMPLEMENTED_PENDING_INTEGRITY_VERIFICATION`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md), v1.2 designed and not executed
- **Design integrity**: [`experiments/gate-01-design-integrity-reaudit-v1.2.md`](experiments/gate-01-design-integrity-reaudit-v1.2.md), verdict `DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: [`experiments/gate-01-mechanical-preflight.json`](experiments/gate-01-mechanical-preflight.json), verdict `MECHANICAL_PREFLIGHT_PASS`
- **Independent implementation verification**: [`experiments/gate-01-implementation-integrity-verification.md`](experiments/gate-01-implementation-integrity-verification.md), verdict `IMPLEMENTATION_INTEGRITY_PASS`
- **Formal execution authorization**: [`experiments/gate-01-execution-authorization.md`](experiments/gate-01-execution-authorization.md), verdict `FORMAL_GATE_01_EXECUTION_AUTHORIZED`
- **Execution-specific learned runner**: `IMPLEMENTED_PENDING_INTEGRITY_VERIFICATION`
- **Runner implementation**: `IMPLEMENTED_PENDING_INTEGRITY_VERIFICATION`
- **Formal training**: `NOT_YET_AUTHORIZED`
- **Implementation authorization**: [`experiments/gate-01-implementation-authorization.md`](experiments/gate-01-implementation-authorization.md)
- **Historical v1.0 audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md), verdict `DESIGN_INTEGRITY_FAIL`
- **Historical v1.1 re-audit**: [`experiments/gate-01-design-integrity-reaudit-v1.1.md`](experiments/gate-01-design-integrity-reaudit-v1.1.md), verdict `DESIGN_INTEGRITY_FAIL`
- **v1.2 re-audit**: [`experiments/gate-01-design-integrity-reaudit-v1.2.md`](experiments/gate-01-design-integrity-reaudit-v1.2.md), verdict `DESIGN_INTEGRITY_PASS`
- **Integrity state**: `DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`
- **Formal training**: `NOT_YET_AUTHORIZED`
- **Formal Gate execution**: `AUTHORIZED / RUNNER_INTEGRITY_PENDING`
- **Gate01-Audit**: unopened
- **Quarantine**: intact
- **Next owner**: independent runner-integrity verifier / pipeline coordinator

Idea 008 remains admitted for one bounded kill-first method cycle. No Gate-01 scientific experiment has been executed. Protocol v1.2, the existing mechanical-preflight implementation surface, and the formal execution authorization are integrity-approved. The bounded Idea-local runner and targeted tests are implemented; independent runner-integrity verification is now pending under the exact scope in `experiments/gate-01-execution-authorization.md`. Recommendation-model training and Gate01-Audit access remain unauthorized.

## Scientific question

At exact per-patient prescription cardinality, does an iterative joint-set refiner obtain utility–DDI frontier value that cannot be absorbed by an equal-information deterministic fixed-K solver or by a budget-conditioned independent medication scorer?

The admitted claim is:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate's composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The scientific interaction under test is:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

Generic joint set prediction, Pareto medication recommendation, DDI-aware loss, a DDI target by itself, one-model/many-objectives, list-wise refinement, training-time safety coefficients, and generic preference conditioning are not novelty claims.

## Admitted mechanism identity

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
z_i^{(t+1)}=s_i+u_\phi(s_i,e_i)
-\operatorname{softplus}(g_\phi(s_i,e_i,\rho^{(t)}))c_i^{(t)}.
$$

Freeze `T=2`:

```text
q0
-> c0, rho0
-> z1, q1
-> c1, rho1
-> z2
-> exact TopK(K_x)
```

The final hard prescription preserves exact cardinality. `rho` is relaxed surrogate slack, not a clinical guarantee; final hard-set achieved DDI is the operating-point quantity.

## Frozen Gate 01 identity

The authoritative scientific source of truth is [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md). Frozen choices include:

- backbone `MoleRec / molerec-embedding` at `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`;
- frozen checkpoint SHA-256 `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`;
- dataset identity `molerec-table1-comparison-v1-1`;
- complete `131`-medication candidate vocabulary;
- `K_x` from Frozen Base probability threshold `0.5`;
- `q^(0)=sigmoid(s)` and `T=2`;
- budgets `0.60`, `0.80`, `1.00` times `r_train`;
- learned seeds `{2002, 2003, 2004}`;
- LR `{3e-4, 1e-3}`, `eta` `{5, 10}`, `gamma=1e-3`;
- AdamW with weight decay `1e-4`, maximum `30` epochs, patience `5`;
- primary utility Jaccard, supporting F1 and PRAUC;
- primary killers Fixed-K Budget-Aware Greedy + 1-Swap and Budget-Conditioned Independent Scorer;
- fixed-lambda support `{0, 0.25, 0.5, 1, 2, 4}`;
- practical margins `delta_U=0.005`, `delta_R=0.005`;
- `1000` patient-clustered bootstrap resamples with seed `80081`.

## Primary killer roles

### Fixed-K Budget-Aware Greedy + 1-Swap

This deterministic solver receives the same frozen scores, DDI matrix, complete candidate pool, requested target, and exact `K_x` as BudgetSet. Comparable or better frontier performance at either required primary region kills BudgetSet.

### Budget-Conditioned Independent Scorer

This learned control receives the same frozen `s_i(x)`, the same patient/visit-conditioned MoleRec `e_i(x)`, requested `b`, Train-only static DDI summaries, identical training/tuning entitlement, and the same explicit `+s_i` residual anchor, but no provisional-set composition, current-set marginal DDI, relaxed residual slack, or iterative feedback. Comparable or better frontier performance at either required primary region kills the claimed joint-set interaction.

The six-value fixed-lambda family remains supporting evidence rather than a third primary killer.

## Execution authorization boundary

The execution contract is frozen in [`experiments/gate-01-execution-authorization.md`](experiments/gate-01-execution-authorization.md).

The Idea-local `gate01_execution.py` runner and targeted unit tests now realize the already-frozen BudgetSet and Independent MLPs, objective, optimizer, seed/LR/eta grid, checkpoint selection, configuration selection, deterministic controls, metrics, bootstrap, seed-robustness rule, and terminal precedence. It reuses `gate01_mechanical_preflight.py` for verified protocol semantics; it does not redesign the protocol.

Formal learned-family training is not yet authorized. After the new runner passes a narrow independent runner-integrity check, the pipeline may separately activate training on `Gate01-Train` and Dev-only selection on `Gate01-Dev`.

`Gate01-Audit` remains unopened until all Train/Dev selections are frozen. When later opened, it is evaluation-only and may not influence epoch, seed, checkpoint, configuration, or hyperparameter selection.

## Quarantine

Do not access:

- G3/G4;
- R0 Holdout;
- historical project test;
- paper-level SOTA benchmarking.

Do not add new backbones, encoders, architectures, seeds, budgets, losses, solvers, tuning dimensions, or post-hoc rescue logic.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / DESIGNED_NOT_EXECUTED
Mechanical preflight: MECHANICAL_PREFLIGHT_PASS
Implementation integrity: IMPLEMENTATION_INTEGRITY_PASS
Formal Gate execution phase: AUTHORIZED
Execution-specific learned runner: IMPLEMENTED_PENDING_INTEGRITY_VERIFICATION
Runner implementation: IMPLEMENTED_PENDING_INTEGRITY_VERIFICATION
Formal training: NOT_YET_AUTHORIZED
Integrity state: DESIGN_INTEGRITY_PASS
Implementation: IMPLEMENTED_PENDING_INTEGRITY_VERIFICATION
Gate01-Audit: UNOPENED
Quarantine: intact
Stage: IDEA_008_GATE_01_RUNNER_IMPLEMENTED_PENDING_INTEGRITY_VERIFICATION
Next owner: independent runner-integrity verifier / pipeline coordinator
```
