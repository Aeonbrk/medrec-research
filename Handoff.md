# Handoff: Idea 008 Terminated / HyperEdit-MR Screen Stopped

## Current state

- **Current Stage**: `TERMINATED_AT_GATE_01`
- **Active Idea**: none; HyperEdit-MR remains a prototype
- **Gate 01 protocol**: v1.2, unchanged
- **Gate01-Train + Gate01-Dev**: `COMPLETE`
- **First Gate01-Audit attempt**: `OPENED_BLOCKED_AT_FIRST_VISIT / NO_RESULT`
- **Controller corrections**: MoleRec invocation correction verified at `25888b954d8f27b7c03a759790b25f93afcd6982`; Bundle ownership correction committed at `134d293dcdadd767eba0a5d121039110c1c47f3e`
- **Controller re-verification**: `CONTROLLER_REVERIFICATION_PASS`
- **Fresh Gate01-Audit attempt**: `COMPLETE`
- **Runner-produced terminal classification**: `KILL_TARGET_SEMANTICS`
- **Scientific Gate verdict**: `KILL_TARGET_SEMANTICS`
- **G3/G4**: `UNTOUCHED`
- **R0 Holdout**: `UNTOUCHED`
- **Historical project test**: `UNTOUCHED`
- **Next owner**: none
- **Modern-backbone calibration**: [`research/memory/modern-backbone-calibration.md`](research/memory/modern-backbone-calibration.md), terminal state `MODERN_BACKBONE_CALIBRATION_COMPLETE`; comparison-only, with no Idea 009 or additional backbone hunting.

Idea 008:
TERMINATED_AT_GATE_01

Terminal result:
KILL_TARGET_SEMANTICS

Reusable observation:
Budget-conditioned learned refinement collapsed to nearly identical medication sets across requested budgets, while explicit optimization produced a visible utility–DDI trade-off.

HyperEdit-MR screen: `STOP_HYPEREDIT` (weak effect; Train/Dev only).

## Frozen scientific state

```text
r_train = 0.07728988868497694
b_L = 0.04637393321098616
b_M = 0.06183191094798155
b_H = 0.07728988868497694
fixed lambda: b_L -> 1.0, b_M -> 0.5, b_H -> 0.0
BudgetSet: LR 0.001, eta 5.0, epochs {2002: 6, 2003: 10, 2004: 6}
Independent: LR 0.001, eta 5.0, epochs {2002: 7, 2003: 6, 2004: 6}
```

The model source, checkpoint, dataset, candidate vocabulary, protocol, controls, and learned artifacts remain unchanged.

## Re-verification result

The bounded controller correction at `25888b954d8f27b7c03a759790b25f93afcd6982` passed independent re-verification. The repository-owned `extract_gate01_molerec_features(...)` path supplies no positional MoleRec forward arguments and passes exactly the six pinned inputs by keyword. The signature-faithful regression reproduces the original controller failure and verifies one eval/no-grad same-forward score/embedding extraction over all 131 candidates.

Record:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-audit-controller-reverification.md`

## Fresh Audit execution

The fresh Audit attempt was authorized by:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-audit-reauthorization.md`

The first failed attempt contributes zero scientific evidence and was not resumed or pooled. The fresh attempt started from the beginning, used `extract_gate01_molerec_features(...)` for every pinned MoleRec visit extraction, and completed the frozen Audit path.

Public-safe aggregate evidence is recorded in:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-audit-result.json`

The run covered 1,113 Audit patients and 2,413 Audit visits, used 1,000 patient-clustered bootstrap replicates with seed 80081, and produced exactly one protocol classification: `KILL_TARGET_SEMANTICS`. Idea 008 is terminated at Gate 01.

No training, reselection, protocol change, new control, or post-hoc rescue is authorized. If another implementation/runtime change is required, stop and return to the pipeline coordinator.

## Routing

```text
Idea 008: TERMINATED_AT_GATE_01
Gate01-Train + Gate01-Dev: COMPLETE
First Gate01-Audit attempt: BLOCKED_NO_RESULT
Controller re-verification: CONTROLLER_REVERIFICATION_PASS
Fresh Gate01-Audit attempt: COMPLETE
Runner-produced terminal classification: KILL_TARGET_SEMANTICS
Scientific Gate verdict: KILL_TARGET_SEMANTICS
Quarantine: intact
Stage: TERMINATED_AT_GATE_01
Next owner: none
```
