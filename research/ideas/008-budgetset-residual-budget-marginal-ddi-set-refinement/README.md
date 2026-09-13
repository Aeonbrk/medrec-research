<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `TRAIN_DEV_COMPLETE / AUDIT_AUTHORIZED_NOT_RUN`
- **Stage**: `IDEA_008_GATE_01_AUDIT_AUTHORIZED_PENDING_EXECUTION`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md), revision v1.2
- **Design integrity**: [`experiments/gate-01-design-integrity-reaudit-v1.2.md`](experiments/gate-01-design-integrity-reaudit-v1.2.md), verdict `DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: [`experiments/gate-01-mechanical-preflight.json`](experiments/gate-01-mechanical-preflight.json), verdict `MECHANICAL_PREFLIGHT_PASS`
- **Independent implementation verification**: [`experiments/gate-01-implementation-integrity-verification.md`](experiments/gate-01-implementation-integrity-verification.md), verdict `IMPLEMENTATION_INTEGRITY_PASS`
- **Runner integrity re-verification**: [`experiments/gate-01-runner-integrity-reverification.md`](experiments/gate-01-runner-integrity-reverification.md), verdict `RUNNER_INTEGRITY_PASS`
- **Train/Dev authorization**: [`experiments/gate-01-training-authorization.md`](experiments/gate-01-training-authorization.md), execution `COMPLETE`
- **Audit authorization**: [`experiments/gate-01-audit-authorization.md`](experiments/gate-01-audit-authorization.md), state `AUTHORIZED_NOT_RUN`
- **Quarantine**: intact
- **Next owner**: local execution agent

Idea 008 remains admitted for one bounded kill-first method cycle. The Train/Dev phase is complete and every selection is frozen. Gate01-Audit is now authorized only for terminal evaluation under protocol v1.2; no new training, tuning, or rescue is permitted.

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

## Frozen Train/Dev selections

The authorized Train/Dev execution preserved the exact frozen backbone/checkpoint/dataset identity and stopped before Audit.

Train-only calibration:

- `r_train = 0.07728988868497694`;
- `b_L = 0.04637393321098616`;
- `b_M = 0.06183191094798155`;
- `b_H = 0.07728988868497694`;
- fixed lambda: `b_L -> 1.0`, `b_M -> 0.5`, `b_H -> 0.0`.

Learned selections:

- BudgetSet: LR `0.001`, `eta = 5.0`, retained epochs `{2002: 6, 2003: 10, 2004: 6}`;
- Independent: LR `0.001`, `eta = 5.0`, retained epochs `{2002: 7, 2003: 6, 2004: 6}`.

Each family completed exactly four configurations by three seeds. Independent static summaries are the frozen Gate01-Train-only summaries. No Audit quantity entered any selection.

## Audit execution boundary

Gate01-Audit is authorized by [`experiments/gate-01-audit-authorization.md`](experiments/gate-01-audit-authorization.md).

Audit may evaluate only the frozen models and controls, compute the protocol-defined operating-point metrics, budget/composition-response checks, killer frontiers, clustered bootstrap, seed robustness, and terminal classification. It cannot change any Train/Dev selection or scientific choice.

After terminal Audit execution, stop and route the public-safe result to `ccf-integrity-auditor` before any research decision or manuscript work.

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
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / TRAIN_DEV_COMPLETE / AUDIT_AUTHORIZED_NOT_RUN
Mechanical preflight: MECHANICAL_PREFLIGHT_PASS
Implementation integrity: IMPLEMENTATION_INTEGRITY_PASS
Runner integrity: RUNNER_INTEGRITY_PASS
Gate01-Train + Gate01-Dev: COMPLETE
Gate01-Audit: AUTHORIZED_NOT_RUN
Quarantine: intact
Stage: IDEA_008_GATE_01_AUDIT_AUTHORIZED_PENDING_EXECUTION
Next owner: local execution agent
```
