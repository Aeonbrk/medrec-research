# Handoff: Idea 008 Gate 01 Audit Blocked / Controller Fix Required

## Current state

- **Current Stage**: `IDEA_008_GATE_01_AUDIT_BLOCKED_PENDING_CONTROLLER_FIX_AND_REVERIFICATION`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.2`, unchanged
- **Gate01-Train + Gate01-Dev**: `COMPLETE`
- **Gate01-Audit**: `OPENED_BLOCKED_AT_FIRST_VISIT / NO_RESULT`
- **Scientific Gate verdict**: none
- **G3/G4**: `UNTOUCHED`
- **R0 Holdout**: `UNTOUCHED`
- **Historical project test**: `UNTOUCHED`
- **Next owner**: local implementation agent

## Frozen scientific state

Train/Dev selections remain frozen exactly as before the Audit attempt:

- `r_train = 0.07728988868497694`;
- `b_L = 0.04637393321098616`;
- `b_M = 0.06183191094798155`;
- `b_H = 0.07728988868497694`;
- fixed lambda `b_L -> 1.0`, `b_M -> 0.5`, `b_H -> 0.0`;
- BudgetSet: LR `0.001`, eta `5.0`, epochs `{2002: 6, 2003: 10, 2004: 6}`;
- Independent: LR `0.001`, eta `5.0`, epochs `{2002: 7, 2003: 6, 2004: 6}`.

The frozen MoleRec source, checkpoint, dataset, environment, candidate vocabulary, protocol, controls, and learned artifacts remain unchanged.

## Audit blocker

The first authorized Audit attempt reached the first Audit visit and stopped before a successful MoleRec forward. No Audit prediction, aggregate metric, operating point, bootstrap result, killer comparison, seed-robustness result, or terminal verdict was produced.

The pinned MoleRec forward signature begins with `substruct_data, mol_data, patient_data`. The failed controller supplied `patient_data` positionally and also supplied `substruct_data` by keyword, producing `TypeError: forward() got multiple values for argument 'substruct_data'`.

This is an execution-controller integration defect, not a scientific result.

## Authorized correction

The bounded correction is defined in:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-audit-controller-fix-authorization.md`

Only the formal MoleRec visit-invocation path and its direct regression tests may change. The corrected path must pass all six pinned MoleRec forward inputs by keyword and no forward input positionally.

Gate01-Audit is not authorized for another attempt during the correction or re-verification phase. One narrow real-model contract smoke may use a previously authorized Gate01-Train visit; it may verify only successful frozen score/embedding extraction.

After the correction passes its required tests, stop at `IDEA_008_GATE_01_AUDIT_CONTROLLER_FIXED_PENDING_REVERIFICATION` for independent integrity re-verification. A fresh Audit attempt requires a new pipeline authorization after that pass.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / TRAIN_DEV_COMPLETE
Gate01-Train + Gate01-Dev: COMPLETE
Gate01-Audit: OPENED_BLOCKED_AT_FIRST_VISIT / NO_RESULT
Scientific Gate verdict: NONE
Quarantine: intact
Stage: IDEA_008_GATE_01_AUDIT_BLOCKED_PENDING_CONTROLLER_FIX_AND_REVERIFICATION
Next owner: local implementation agent
Next task: apply only the authorized controller invocation correction, verify it, and stop before Audit
```
