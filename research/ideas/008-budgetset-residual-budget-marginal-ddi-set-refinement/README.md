<!-- markdownlint-disable MD013 -->

# Idea 008: BudgetSet — Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement

- **Idea ID**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Status**: `TRAIN_DEV_COMPLETE / AUDIT_BLOCKED_NO_RESULT`
- **Stage**: `IDEA_008_GATE_01_AUDIT_BLOCKED_PENDING_CONTROLLER_FIX_AND_REVERIFICATION`
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`
- **Reviewer confidence**: medium-high
- **Gate 01 protocol**: [`experiments/gate-01-protocol.md`](experiments/gate-01-protocol.md), revision v1.2
- **Design integrity**: `DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`
- **Implementation integrity before Audit attempt**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Runner integrity before Audit attempt**: `RUNNER_INTEGRITY_PASS`
- **Train/Dev**: complete with all selections frozen
- **Audit controller correction**: [`experiments/gate-01-audit-controller-fix-authorization.md`](experiments/gate-01-audit-controller-fix-authorization.md)
- **Quarantine**: intact
- **Next owner**: local implementation agent

Idea 008 remains admitted for the same bounded kill-first method cycle. The first Audit attempt stopped at the first Audit visit before a successful frozen MoleRec forward. No Audit prediction, metric, operating point, bootstrap result, killer comparison, seed-robustness result, or scientific Gate verdict exists.

## Scientific question

At exact per-patient prescription cardinality, does an iterative joint-set refiner obtain utility–DDI frontier value that cannot be absorbed by an equal-information deterministic fixed-K solver or by a budget-conditioned independent medication scorer?

The admitted interaction remains:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

## Frozen scientific identity

The protocol, model, checkpoint, dataset, candidate vocabulary, budgets, controls, learned configurations, and retained checkpoints remain unchanged.

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

## Confirmed controller blocker

The pinned upstream MoleRec forward contract is:

```text
forward(substruct_data, mol_data, patient_data, ddi_mask_H, tensor_ddi_adj, average_projection)
```

The failed formal controller supplied `patient_data` positionally while also supplying `substruct_data` by keyword. The positional value therefore occupied `substruct_data`, producing the runtime error `forward() got multiple values for argument 'substruct_data'`.

The correction is implementation-local: the formal Idea 008 path must supply all six pinned forward inputs by keyword, matching the already-qualified Comparison invocation semantics. No protocol or scientific change is authorized.

## Correction and re-verification boundary

The controller-fix authorization permits only the actual invocation correction, direct regression tests, the existing targeted/full software checks, and one narrow real-model contract smoke on a previously authorized Gate01-Train visit.

Gate01-Audit is not authorized for another execution attempt during this phase. After the fix, stop at `IDEA_008_GATE_01_AUDIT_CONTROLLER_FIXED_PENDING_REVERIFICATION`. Independent re-verification must pass before the pipeline coordinator can authorize a fresh Audit attempt from the beginning.

## Quarantine

G3/G4, R0 Holdout, the historical project test, and paper-level SOTA benchmarking remain outside this work.

## Routing

```text
Idea 008: ADMITTED
Gate01-Train + Gate01-Dev: COMPLETE
Gate01-Audit: OPENED_BLOCKED_AT_FIRST_VISIT / NO_RESULT
Protocol revision: v1.2 unchanged
Scientific Gate verdict: NONE
Stage: IDEA_008_GATE_01_AUDIT_BLOCKED_PENDING_CONTROLLER_FIX_AND_REVERIFICATION
Next owner: local implementation agent
```
