<!-- markdownlint-disable MD013 -->

# Gate 01 audit controller reverification: Idea 008

## Verdict

`CONTROLLER_REVERIFICATION_PASS`

- **Audited revision**: `25888b954d8f27b7c03a759790b25f93afcd6982`
- **Correction base**: `f9ba4669069dff9d8f6da82b800ca9db6411b04a`
- **Protocol**: Gate 01 v1.2, unchanged
- **Scientific Gate verdict**: none
- **Gate01-Audit after failed attempt**: `OPENED_BLOCKED_AT_FIRST_VISIT / NO_RESULT`

## Findings

1. **Change surface, PASS.** Relative to the correction base, the implementation change is limited to the Idea-local MoleRec call assembly, its direct regression proof, and public-safe routing documents. No scientific choice changed.
2. **Pinned invocation contract, PASS.** `extract_gate01_molerec_features` supplies `forward_args=()` and exactly the six pinned inputs through `forward_kwargs`: `substruct_data`, `mol_data`, `patient_data`, `ddi_mask_H`, `tensor_ddi_adj`, and `average_projection`.
3. **Regression proof, PASS.** The signature-faithful regression reproduces the original duplicate-`substruct_data` TypeError and then verifies one eval/no-grad forward, one `score_extractor` execution, same-forward score/embedding capture, and 131 candidate-aligned outputs. The final correction revision explicitly asserts the pinned forward parameter order.
4. **Real-model contract evidence, PASS.** The bounded correction record reports the authorized 319 Train-side real-model contract smoke as passing under the frozen MoleRec source/checkpoint/environment, with no scientific metric computed.
5. **Scientific freeze and quarantine, PASS.** Train/Dev selections remain frozen; no second Audit access, Audit metric, retraining, post-hoc selection, or scientific Gate verdict was produced. G3/G4, R0 Holdout, and the historical project test remain untouched.

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

## Decision

The controller correction is implementation-local, mechanically covered, consistent with the pinned upstream contract, and does not alter the scientific experiment. The confirmed runtime blocker is closed.

A fresh Gate01-Audit execution may be considered by `ccf-pipeline-orchestrator`. The failed first attempt contributes zero scientific evidence and must not be resumed or pooled with the fresh attempt.

```text
Verdict: CONTROLLER_REVERIFICATION_PASS
Next owner: ccf-pipeline-orchestrator
```
