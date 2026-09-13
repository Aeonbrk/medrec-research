<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `TRAIN_DEV_COMPLETE / AUDIT_PENDING_AUTHORIZATION`
- **Stage**: `IDEA_008_GATE_01_TRAIN_DEV_COMPLETE_PENDING_AUDIT_AUTHORIZATION`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md), v1.2 designed and not executed
- **Design integrity**: [`experiments/gate-01-design-integrity-reaudit-v1.2.md`](experiments/gate-01-design-integrity-reaudit-v1.2.md), verdict `DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: [`experiments/gate-01-mechanical-preflight.json`](experiments/gate-01-mechanical-preflight.json), verdict `MECHANICAL_PREFLIGHT_PASS`
- **Independent implementation verification**: [`experiments/gate-01-implementation-integrity-verification.md`](experiments/gate-01-implementation-integrity-verification.md), verdict `IMPLEMENTATION_INTEGRITY_PASS`
- **Formal execution authorization**: [`experiments/gate-01-execution-authorization.md`](experiments/gate-01-execution-authorization.md), verdict `FORMAL_GATE_01_EXECUTION_AUTHORIZED`
- **Historical runner integrity verification**: [`experiments/gate-01-runner-integrity-verification.md`](experiments/gate-01-runner-integrity-verification.md), verdict `RUNNER_INTEGRITY_FAIL`
- **Runner integrity re-verification**: [`experiments/gate-01-runner-integrity-reverification.md`](experiments/gate-01-runner-integrity-reverification.md), verdict `RUNNER_INTEGRITY_PASS`
- **Train/Dev authorization**: [`experiments/gate-01-training-authorization.md`](experiments/gate-01-training-authorization.md), execution `COMPLETE`
- **Gate01-Audit**: unopened / not authorized
- **Quarantine**: intact
- **Next owner**: ccf-pipeline-orchestrator

Idea 008 remains admitted for one bounded kill-first method cycle. The authorized Train/Dev phase is complete, all frozen selections are recorded below, and no Gate-01 scientific result has been generated. Protocol v1.2 and all pre-execution integrity gates remain unchanged; Gate01-Audit requires separate authorization.

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

## Runner integrity boundary

The corrected runner at `4c3ac46365ade339f307be449b8a7dca3c8bb16c` passes the narrow runner-integrity re-verification.

The prior blockers are closed:

1. one runner-owned device covers detached scores, embeddings, budgets, DDI inputs, labels, `K_x`, and Independent static summaries before learned execution;
2. the exact `4 configurations × 3 seeds` learned-family selection graph is runner-owned, with configuration quantities derived from the three retained seed checkpoints rather than injected by the caller.

Approved 319 synthetic targeted verification reports `44 passed` across the execution and mechanical-preflight files, including the CUDA device path with no PyTorch-dependent skips. This evidence does not constitute scientific Gate execution.

## Train/Dev execution boundary

Gate01-Train and Gate01-Dev are now authorized exactly under [`experiments/gate-01-training-authorization.md`](experiments/gate-01-training-authorization.md).

Gate01-Train may be used for:

- frozen MoleRec `s_i(x)` / `e_i(x)` extraction;
- `r_train` and the three frozen budget targets;
- Train-only Independent `d_i,p_i` summaries;
- Train-only fixed-lambda selection;
- BudgetSet and Independent training over exactly four configurations and three learned seeds.

Gate01-Dev may be used only for the frozen per-epoch checkpoint/patience rule and the frozen three-seed configuration selection. No Audit quantity may enter those decisions.

The authorized Train/Dev execution completed with the exact frozen identity and recovery path: harness revision `5752596a16a57390dffe96538fa39f7b82fd051f`, MoleRec upstream revision `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, profile `molerec-embedding`, checkpoint SHA-256 `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`, dataset `molerec-table1-comparison-v1-1`, environment `medrec-molerec-table1`, and 131 candidate medications. Historical recovery identity was `formal-20260828-a09fcab-u8-b` / `molerec-embedding` / `u5-recover-20260829-molerec-embedding`, selected backbone epoch 44. No MoleRec retraining or checkpoint substitution occurred.

Train-only calibration froze `r_train = 0.07728988868497694`, `b_L = 0.04637393321098616`, `b_M = 0.06183191094798155`, and `b_H = 0.07728988868497694`. Fixed-lambda choices were `b_L -> 1.0`, `b_M -> 0.5`, and `b_H -> 0.0`.

BudgetSet selected learning rate `0.001` and `eta = 5.0`; retained checkpoint epochs were `{2002: 6, 2003: 10, 2004: 6}`. Independent selected learning rate `0.001` and `eta = 5.0`; retained checkpoint epochs were `{2002: 7, 2003: 6, 2004: 6}`. Each family completed exactly 12 runs (`4 configurations x 3 seeds`) and retained exactly one Dev checkpoint for each seed. Independent static summaries were frozen from Gate01-Train only.

Execution stopped after Train/Dev. Gate01-Audit remains unopened and requires a separate pipeline authorization; no scientific Gate verdict was generated.

## Quarantine

Do not access:

- Gate01-Audit at the current stage;
- G3/G4;
- R0 Holdout;
- historical project test;
- paper-level SOTA benchmarking.

Do not add new backbones, encoders, architectures, seeds, budgets, losses, solvers, tuning dimensions, or post-hoc rescue logic.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / TRAIN_DEV_COMPLETE / AUDIT_NOT_EXECUTED
Mechanical preflight: MECHANICAL_PREFLIGHT_PASS
Implementation integrity: IMPLEMENTATION_INTEGRITY_PASS
Runner integrity: RUNNER_INTEGRITY_PASS
Gate01-Train + Gate01-Dev: COMPLETE
Gate01-Audit: UNOPENED / NOT_AUTHORIZED
Quarantine: intact
Stage: IDEA_008_GATE_01_TRAIN_DEV_COMPLETE_PENDING_AUDIT_AUTHORIZATION
Next owner: ccf-pipeline-orchestrator
```
