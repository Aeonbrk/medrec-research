# Handoff: Idea 008 Gate 01 Audit Executed / Pending Integrity Audit

## Current state

- **Current Stage**: `IDEA_008_GATE_01_AUDIT_EXECUTED_PENDING_INTEGRITY_AUDIT`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Gate 01 protocol**: v1.2, unchanged
- **Gate01-Train + Gate01-Dev**: `COMPLETE`
- **First Gate01-Audit attempt**: `OPENED_BLOCKED_AT_FIRST_VISIT / NO_RESULT`
- **Controller corrections**: MoleRec invocation correction verified at `25888b954d8f27b7c03a759790b25f93afcd6982`; Bundle ownership correction committed at `134d293dcdadd767eba0a5d121039110c1c47f3e`
- **Controller re-verification**: `CONTROLLER_REVERIFICATION_PASS`
- **Fresh Gate01-Audit attempt**: `COMPLETE`
- **Runner-produced terminal classification**: `KILL_TARGET_SEMANTICS`
- **Scientific Gate verdict**: none; decision pending integrity audit
- **G3/G4**: `UNTOUCHED`
- **R0 Holdout**: `UNTOUCHED`
- **Historical project test**: `UNTOUCHED`
- **Next owner**: `ccf-integrity-auditor`

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

The run covered 1,113 Audit patients and 2,413 Audit visits, used 1,000 patient-clustered bootstrap replicates with seed 80081, and produced exactly one protocol classification: `KILL_TARGET_SEMANTICS`. No research continuation or termination decision has been made.

No training, reselection, protocol change, new control, or post-hoc rescue is authorized. If another implementation/runtime change is required, stop and return to the pipeline coordinator.

## Routing

```text
Idea 008: ADMITTED
Gate01-Train + Gate01-Dev: COMPLETE
First Gate01-Audit attempt: BLOCKED_NO_RESULT
Controller re-verification: CONTROLLER_REVERIFICATION_PASS
Fresh Gate01-Audit attempt: COMPLETE
Runner-produced terminal classification: KILL_TARGET_SEMANTICS
Scientific Gate verdict: NONE
Quarantine: intact
Stage: IDEA_008_GATE_01_AUDIT_EXECUTED_PENDING_INTEGRITY_AUDIT
Next owner: ccf-integrity-auditor
Next task: independently audit the public-safe Gate01 result against protocol v1.2 and frozen identities
```
