# Handoff: Idea 008 Gate 01 Train/Dev Authorized / Not Yet Executed

## Current state

- **Current Stage**: `IDEA_008_GATE_01_TRAIN_DEV_AUTHORIZED_PENDING_EXECUTION`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.2`
- **Protocol state**: `DESIGNED_NOT_EXECUTED / DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`
- **Implementation integrity**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Runner integrity**: `RUNNER_INTEGRITY_PASS`
- **Formal Gate 01 execution phase**: `AUTHORIZED`
- **Gate01-Train + Gate01-Dev execution**: `AUTHORIZED_NOT_RUN`
- **Gate01-Audit**: `UNOPENED / NOT_AUTHORIZED`
- **G3/G4**: `UNTOUCHED`
- **R0 Holdout**: `UNTOUCHED`
- **Historical project test**: `UNTOUCHED`
- **Quarantine**: intact
- **Next owner**: local execution agent

## Runner integrity result

The corrected runner at `4c3ac46365ade339f307be449b8a7dca3c8bb16c` passes the narrow re-verification recorded in:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-runner-integrity-reverification.md`

The previous R1 and R2 blockers are closed without changing Gate 01 protocol v1.2:

1. learned execution owns one device and materializes detached scores, embeddings, budgets, DDI inputs, labels, `K_x`, and Independent static summaries on that device;
2. `train_learned_family` owns the exact `4 configurations × 3 seeds` graph, derives configuration-level Dev quantities from retained seed checkpoints, applies the frozen selection key, and returns only the selected configuration's three retained checkpoints.

The committed verification record includes the approved 319 synthetic evidence: `44 passed` across the execution-runner and mechanical-preflight targeted files, with the CUDA device path executed and no PyTorch-dependent skips. GitHub has no separate CI status attached to the verified revision.

## Training authorization boundary

The Train/Dev activation is frozen in:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-training-authorization.md`

Authorized now:

- Gate01-Train for frozen MoleRec feature/logit extraction, `r_train`/budget calibration, Train-only Independent static summaries, Train-only fixed-lambda selection, and BudgetSet/Independent training;
- Gate01-Dev for epoch/checkpoint/configuration selection exactly under protocol v1.2.

Not authorized now:

- Gate01-Audit;
- any Audit-derived metric, bootstrap, frontier result, seed-robustness result, or terminal Gate verdict;
- G3/G4, R0 Holdout, historical project test, or paper-level SOTA expansion.

After both learned families have one Dev-selected configuration and exactly three retained checkpoints, and all Train-only selections are frozen, execution must stop and return to the pipeline coordinator for a separate Gate01-Audit authorization.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / DESIGNED_NOT_EXECUTED
Mechanical preflight: MECHANICAL_PREFLIGHT_PASS
Implementation integrity: IMPLEMENTATION_INTEGRITY_PASS
Runner integrity: RUNNER_INTEGRITY_PASS
Formal Gate execution phase: AUTHORIZED
Gate01-Train + Gate01-Dev: AUTHORIZED_NOT_RUN
Gate01-Audit: UNOPENED / NOT_AUTHORIZED
Quarantine: intact
Stage: IDEA_008_GATE_01_TRAIN_DEV_AUTHORIZED_PENDING_EXECUTION
Next owner: local execution agent
Next task: execute only the frozen Train/Dev phase, freeze all selections, then stop before Gate01-Audit
```
