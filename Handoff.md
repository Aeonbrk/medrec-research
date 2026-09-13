# Handoff: Idea 008 Gate 01 Train/Dev Complete / Audit Not Authorized

## Current state

- **Current Stage**: `IDEA_008_GATE_01_TRAIN_DEV_COMPLETE_PENDING_AUDIT_AUTHORIZATION`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.2`
- **Protocol state**: `DESIGN_INTEGRITY_PASS / TRAIN_DEV_COMPLETE / AUDIT_NOT_EXECUTED`
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`
- **Implementation integrity**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Runner integrity**: `RUNNER_INTEGRITY_PASS`
- **Formal Gate 01 execution phase**: `AUTHORIZED`
- **Gate01-Train + Gate01-Dev execution**: `COMPLETE`
- **Gate01-Audit**: `UNOPENED / NOT_AUTHORIZED`
- **G3/G4**: `UNTOUCHED`
- **R0 Holdout**: `UNTOUCHED`
- **Historical project test**: `UNTOUCHED`
- **Quarantine**: intact
- **Next owner**: ccf-pipeline-orchestrator

## Frozen Train/Dev execution record

The authorized Train/Dev phase completed on harness revision
`5752596a16a57390dffe96538fa39f7b82fd051f` in the approved
`medrec-molerec-table1` environment on `cuda:0`. The exact frozen MoleRec
identity was preserved: upstream revision
`dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, profile `molerec-embedding`,
checkpoint SHA-256
`5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`,
dataset `molerec-table1-comparison-v1-1`, and 131 candidate medications.
The historical recovery identity was `formal-20260828-a09fcab-u8-b` /
`molerec-embedding` / `u5-recover-20260829-molerec-embedding`, selected
backbone epoch 44; no MoleRec retraining or checkpoint substitution occurred.

Train-only calibration froze:

- `r_train = 0.07728988868497694`;
- `b_L = 0.04637393321098616`, `b_M = 0.06183191094798155`,
  `b_H = 0.07728988868497694`;
- fixed-lambda choices `b_L -> 1.0`, `b_M -> 0.5`, `b_H -> 0.0`.

BudgetSet selected learning rate `0.001`, `eta = 5.0`, with retained
checkpoint epochs `{2002: 6, 2003: 10, 2004: 6}`. Independent selected
learning rate `0.001`, `eta = 5.0`, with retained checkpoint epochs
`{2002: 7, 2003: 6, 2004: 6}`. Each family completed exactly 12 runs
(`4 configurations x 3 seeds`) and retained exactly one Dev checkpoint for
each of the three learned seeds. Independent static summaries were frozen
from Gate01-Train only.

No scientific Gate verdict was generated. Gate01-Audit was not opened.

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
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / TRAIN_DEV_COMPLETE / AUDIT_NOT_EXECUTED
Mechanical preflight: MECHANICAL_PREFLIGHT_PASS
Implementation integrity: IMPLEMENTATION_INTEGRITY_PASS
Runner integrity: RUNNER_INTEGRITY_PASS
Formal Gate execution phase: AUTHORIZED
Gate01-Train + Gate01-Dev: COMPLETE
Gate01-Audit: UNOPENED / NOT_AUTHORIZED
Quarantine: intact
Stage: IDEA_008_GATE_01_TRAIN_DEV_COMPLETE_PENDING_AUDIT_AUTHORIZATION
Next owner: ccf-pipeline-orchestrator
Next task: obtain separate Gate01-Audit authorization; do not open Audit in this state
```
