<!-- markdownlint-disable MD013 -->

# Gate 01 audit Re-authorization: Idea 008

## Authorization status

- **Controller correction revision**: `25888b954d8f27b7c03a759790b25f93afcd6982`
- **Controller re-verification**: `CONTROLLER_REVERIFICATION_PASS`
- **Protocol revision**: v1.2, unchanged
- **Train/Dev**: complete; all selections frozen
- **Prior Audit attempt**: blocked at first visit before a successful MoleRec forward; zero scientific evidence
- **Fresh Gate01-Audit attempt**: `AUTHORIZED_NOT_RUN`
- **Next owner**: local execution agent

The prior failed attempt is discarded as execution evidence. Do not resume it, pool it, or use it in any metric. The newly authorized attempt starts from the beginning of Gate01-Audit under the corrected controller and the same frozen scientific state.

## Mandatory corrected invocation path

Every frozen MoleRec visit extraction in the formal Audit must use the repository-owned:

```text
extract_gate01_molerec_features(...)
```

Do not assemble `forward_args` / `forward_kwargs` externally and do not call the pinned MoleRec model with positional forward inputs. The helper fixes the exact verified invocation contract and preserves the existing frozen extraction semantics.

## Frozen identity and selections

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

No Audit result may change any of these values.

## Authorized audit operations

Execute the terminal Gate01-Audit exactly under protocol v1.2 using only the frozen selections. Evaluate Frozen Base, Fixed-K Budget-Aware Greedy + 1-Swap, the Train-selected fixed-lambda supporting control, the three retained BudgetSet seeds, and the three retained Independent seeds at `b_L`, `b_M`, and `b_H`.

Compute only protocol-defined quantities: primary Jaccard, supporting F1/PRAUC, hard-set DDI, compliance/violation quantities, budget response, composition response, primary killer frontiers, 1000 patient-clustered bootstrap resamples with seed 80081, matched-seed robustness, and exactly one terminal classification under the frozen precedence.

## Frozen terminal precedence

```text
1. STOP_INVALID_GATE_IMPLEMENTATION
2. STOP_NO_BASE_DDI_HEADROOM
3. KILL_TARGET_SEMANTICS
4. KILL_BUDGET_RESPONSE
5. KILL_COMPOSITION_RESPONSE
6. KILL_BUDGETSET
7. KILL_JOINT_SET_INTERACTION
8. KILL_SEED_FRAGILITY
9. INCONCLUSIVE_STOP
10. PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES
```

## Restrictions

No retraining, checkpoint/configuration reselection, new hyperparameter, seed, budget, fixed lambda, control, solver, metric, threshold, frontier definition, bootstrap setting, protocol change, data-partition change, or post-hoc rescue is authorized.

Do not access G3/G4, R0 Holdout, the historical project test, or paper-level SOTA benchmarking.

If a runtime or implementation defect requires code or protocol changes, stop without patching and return to the pipeline coordinator.

## Completion boundary

After the fresh Audit attempt produces all required protocol evidence and exactly one terminal classification, stop at:

```text
IDEA_008_GATE_01_AUDIT_EXECUTED_PENDING_INTEGRITY_AUDIT
```

Next owner:

```text
ccf-integrity-auditor
```
