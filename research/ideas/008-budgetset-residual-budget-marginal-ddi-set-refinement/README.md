<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `TRAIN_DEV_COMPLETE / AUDIT_EXECUTED_PENDING_INTEGRITY_AUDIT`
- **Stage**: `IDEA_008_GATE_01_AUDIT_EXECUTED_PENDING_INTEGRITY_AUDIT`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md), revision v1.2
- **Design integrity**: `DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`
- **Implementation integrity before Audit attempt**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Runner integrity before Audit attempt**: `RUNNER_INTEGRITY_PASS`
- **Train/Dev**: complete with all selections frozen
- **Controller corrections**: MoleRec invocation correction verified at `25888b954d8f27b7c03a759790b25f93afcd6982`; Bundle ownership correction committed at `134d293dcdadd767eba0a5d121039110c1c47f3e`
- **Controller re-verification**: [`experiments/gate-01-audit-controller-reverification.md`](experiments/gate-01-audit-controller-reverification.md), verdict `CONTROLLER_REVERIFICATION_PASS`
- **Fresh Audit execution**: [`experiments/gate-01-audit-result.json`](experiments/gate-01-audit-result.json), terminal classification `KILL_TARGET_SEMANTICS`
- **Quarantine**: intact
- **Next owner**: `ccf-integrity-auditor`

Idea 008 remains admitted for the same bounded kill-first method cycle. The first Audit attempt stopped before a successful frozen MoleRec forward and generated no scientific evidence. The corrected controller path was exercised end to end, and the fresh Audit completed under the unchanged protocol with terminal classification `KILL_TARGET_SEMANTICS`. The independent integrity audit must review the public-safe result before any research continuation or termination decision.

## Scientific question

At exact per-patient prescription cardinality, does an iterative joint-set refiner obtain utility–DDI frontier value that cannot be absorbed by an equal-information deterministic fixed-K solver or by a budget-conditioned independent medication scorer?

The admitted interaction remains:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

## Frozen scientific identity

```text
MoleRec revision = dd5afaf0a503fd3de3229f86ec7f26b345d10e3a
checkpoint SHA256 = 5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca
dataset = molerec-table1-comparison-v1-1
candidate count = 131

r_train = 0.07728988868497694
b_L = 0.04637393321098616
b_M = 0.06183191094798155
b_H = 0.07728988868497694

fixed lambda: b_L -> 1.0, b_M -> 0.5, b_H -> 0.0
BudgetSet: LR 0.001, eta 5.0, epochs {2002: 6, 2003: 10, 2004: 6}
Independent: LR 0.001, eta 5.0, epochs {2002: 7, 2003: 6, 2004: 6}
```

No Audit quantity may alter these values.

## Controller correction and integrity result

The pinned MoleRec contract is:

```text
forward(substruct_data, mol_data, patient_data, ddi_mask_H, tensor_ddi_adj, average_projection)
```

The repository-owned `extract_gate01_molerec_features(...)` path passes no positional forward arguments and supplies all six pinned inputs by keyword. The signature-faithful regression reproduces the original controller TypeError and verifies exactly one eval/no-grad same-forward score/embedding extraction with the full 131-candidate contract.

Independent re-verification found the correction bounded to the actual invocation defect and its tests, with no scientific change.

## Fresh Audit boundary

The failed first attempt contributes zero scientific evidence and must not be resumed or pooled. The fresh attempt starts from the beginning of Gate01-Audit and must use `extract_gate01_molerec_features(...)` for every pinned MoleRec visit extraction.

Only protocol-v1.2 terminal evaluation is authorized: frozen controls and learned checkpoints, operating-point metrics, budget/composition response, killer frontiers, 1000 patient-clustered bootstrap resamples with seed 80081, matched-seed robustness, and exactly one terminal classification under the frozen precedence.

No retraining, reselection, protocol change, new control, solver expansion, or post-hoc rescue is authorized.

## Fresh Audit result

The completed fresh Audit covered 1,113 patients and 2,413 visits, evaluated the frozen controls and retained checkpoints at all three budgets, and ran 1,000 patient-clustered bootstrap replicates with seed 80081. Public-safe aggregate metrics, frontier comparisons, compliance/response quantities, matched-seed counts, and the single runner-produced classification are recorded in [`experiments/gate-01-audit-result.json`](experiments/gate-01-audit-result.json). The classification is `KILL_TARGET_SEMANTICS`; no continuation or termination decision is recorded here.

## Quarantine

G3/G4, R0 Holdout, the historical project test, and paper-level SOTA benchmarking remain outside this work.

## Routing

```text
Idea 008: ADMITTED
Gate01-Train + Gate01-Dev: COMPLETE
First Gate01-Audit attempt: BLOCKED_NO_RESULT
Controller re-verification: CONTROLLER_REVERIFICATION_PASS
Fresh Gate01-Audit attempt: COMPLETE
Protocol revision: v1.2 unchanged
Runner-produced terminal classification: KILL_TARGET_SEMANTICS
Scientific Gate verdict: NONE
Stage: IDEA_008_GATE_01_AUDIT_EXECUTED_PENDING_INTEGRITY_AUDIT
Next owner: ccf-integrity-auditor
```
