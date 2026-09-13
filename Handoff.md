# Handoff: Idea 008 Gate 01 Audit Authorized / Not Yet Executed

## Current state

- **Current Stage**: `IDEA_008_GATE_01_AUDIT_AUTHORIZED_PENDING_EXECUTION`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.2`
- **Protocol state**: `DESIGN_INTEGRITY_PASS / TRAIN_DEV_COMPLETE / AUDIT_AUTHORIZED_NOT_RUN`
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`
- **Implementation integrity**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Runner integrity**: `RUNNER_INTEGRITY_PASS`
- **Formal Gate 01 execution phase**: `AUTHORIZED`
- **Gate01-Train + Gate01-Dev execution**: `COMPLETE`
- **Gate01-Audit**: `AUTHORIZED_NOT_RUN`
- **G3/G4**: `UNTOUCHED`
- **R0 Holdout**: `UNTOUCHED`
- **Historical project test**: `UNTOUCHED`
- **Quarantine**: intact
- **Next owner**: local execution agent

## Frozen Train/Dev execution record

The completed Train/Dev phase preserved the frozen MoleRec identity: upstream revision
`dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, profile `molerec-embedding`,
checkpoint SHA-256
`5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`,
dataset `molerec-table1-comparison-v1-1`, and 131 candidate medications. No MoleRec
retraining or checkpoint substitution occurred.

Train-only calibration is frozen as:

- `r_train = 0.07728988868497694`;
- `b_L = 0.04637393321098616`;
- `b_M = 0.06183191094798155`;
- `b_H = 0.07728988868497694`;
- fixed-lambda choices `b_L -> 1.0`, `b_M -> 0.5`, `b_H -> 0.0`.

BudgetSet is frozen at learning rate `0.001`, `eta = 5.0`, with retained
checkpoint epochs `{2002: 6, 2003: 10, 2004: 6}`. Independent is frozen at
learning rate `0.001`, `eta = 5.0`, with retained checkpoint epochs
`{2002: 7, 2003: 6, 2004: 6}`. Independent static summaries remain the
Train-only frozen values used during training.

No Audit quantity entered any of these selections.

## Audit authorization boundary

Gate01-Audit is now authorized by:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-audit-authorization.md`

The authorization permits only terminal evaluation under protocol v1.2 using the already-frozen Train/Dev selections. Audit may compute the frozen operating-point metrics, both primary-killer comparisons, fixed-lambda supporting evidence, budget/composition-response checks, the patient-clustered bootstrap, seed robustness, and the protocol-defined terminal classification.

Audit must not select or change checkpoints, hyperparameters, budgets, fixed lambdas, controls, seeds, thresholds, architecture, objective, or data partitions. Any runtime problem requiring an implementation or protocol change stops execution and returns to the pipeline coordinator.

G3/G4, R0 Holdout, and the historical project test remain outside Gate 01.

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
Next task: execute the frozen Gate01-Audit once, generate the protocol terminal verdict, then stop for independent integrity audit
```
