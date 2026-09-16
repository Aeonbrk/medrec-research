<!-- markdownlint-disable MD013 -->

# Gate 01 audit controller fix authorization: Idea 008

## Authorization status

- **Authoritative revision before correction**: `c98562958792c5ff23a7413322e2c87113acb024`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Protocol revision**: `v1.2`, unchanged
- **Gate01-Train + Gate01-Dev**: `COMPLETE`
- **Gate01-Audit**: `OPENED_BLOCKED_AT_FIRST_VISIT / NO_RESULT`
- **Scientific Gate verdict**: none
- **Quarantine**: intact
- **Next owner**: local implementation agent

The first authorized Audit attempt stopped on the first Audit visit before a successful frozen MoleRec forward. No Audit prediction, aggregate metric, operating point, bootstrap result, killer comparison, seed-robustness result, or terminal verdict was produced.

## 1. Confirmed invocation defect

The pinned upstream MoleRec revision `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` defines:

```text
forward(
    substruct_data,
    mol_data,
    patient_data,
    ddi_mask_H,
    tensor_ddi_adj,
    average_projection,
)
```

The failed Audit controller supplied `patient_data` positionally while also supplying `substruct_data` by keyword. The positional value therefore occupied `substruct_data`, and Python raised:

```text
TypeError: forward() got multiple values for argument 'substruct_data'
```

The already-qualified Comparison adapter calls the same pinned model with `patient_data` and all drug inputs by keyword. This is the required integration contract for the correction.

## 2. Authorized implementation correction

Fix only the formal Idea 008 MoleRec visit-invocation path used by Gate01-Audit.

The corrected call must pass no positional MoleRec forward arguments. It must supply exactly the existing six pinned forward inputs by keyword:

```text
substruct_data
mol_data
patient_data
ddi_mask_H
tensor_ddi_adj
average_projection
```

When using `extract_frozen_molerec_features`, the formal path must therefore use an empty `forward_args` sequence and a `forward_kwargs` mapping containing those six values.

Do not change the values, preprocessing, model source, checkpoint, feature semantics, hook location, score extraction, embedding extraction, partitioning, or protocol logic.

If the failed controller logic is not repository-owned, move only this call assembly into the existing Idea-local execution surface so the corrected formal path is versioned and mechanically testable. Do not create a second execution framework or a general adapter layer.

## 3. Required regression proof

Add a focused test with a signature-faithful MoleRec fake whose forward signature is exactly:

```text
(substruct_data, mol_data, patient_data, ddi_mask_H, tensor_ddi_adj, average_projection)
```

The test must prove that the formal Idea 008 invocation:

- passes all six inputs by keyword;
- executes exactly one frozen forward;
- reaches `score_extractor` so the existing pre/post hooks capture the same-forward embeddings and scores;
- remains `eval()` and no-gradient;
- does not change the 131-candidate contract.

Retain the existing runner and mechanical-preflight tests. Run the focused tests, the existing targeted suites, the full local regression suite, Ruff check/format, and Markdown lint.

## 4. Real-model contract smoke

After local tests pass, one narrow 319 contract smoke is authorized against the exact frozen MoleRec source/checkpoint/environment using a previously authorized Gate01-Train visit only.

The smoke may verify that the corrected all-keyword invocation completes and returns the expected 131 scores plus candidate-aligned embeddings. It must not compute utility/DDI metrics, change any frozen Train/Dev selection, open Gate01-Audit, or produce scientific evidence.

## 5. Audit boundary during correction

Gate01-Audit is not authorized for another execution attempt during this correction phase.

Do not read another Audit visit, compute an Audit prediction, resume from the failed visit, or run any Audit aggregate analysis. The next Audit attempt requires a new pipeline authorization after independent re-verification of the corrected controller.

G3/G4, R0 Holdout, and the historical project test remain untouched.

## 6. Frozen scientific state

The following remain unchanged:

```text
r_train = 0.07728988868497694
b_L = 0.04637393321098616
b_M = 0.06183191094798155
b_H = 0.07728988868497694

fixed lambda at b_L = 1.0
fixed lambda at b_M = 0.5
fixed lambda at b_H = 0.0

BudgetSet: LR 0.001, eta 5.0, epochs {2002: 6, 2003: 10, 2004: 6}
Independent: LR 0.001, eta 5.0, epochs {2002: 7, 2003: 6, 2004: 6}
```

No retraining, reselection, new seed, new budget, new control, new metric, or protocol change is authorized.

## 7. Completion boundary

After the correction and required tests/smoke pass, stop without reopening Audit and propose:

```text
IDEA_008_GATE_01_AUDIT_CONTROLLER_FIXED_PENDING_REVERIFICATION
```

Next owner:

```text
ccf-integrity-auditor
```

The independent re-verification must confirm that the diff is limited to the actual invocation defect and its tests, that the pinned model receives the exact all-keyword contract, and that no scientific choice changed. Only after that pass may `ccf-pipeline-orchestrator` authorize a fresh Audit execution attempt from the beginning.
