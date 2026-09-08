<!-- markdownlint-disable MD013 -->

# Failure Memory — Event-Sourced Regimen Editing M0: Workflow-Action State Inconsistency

## Failure class

`WORKFLOW_ACTION_LABELS_NOT_STATE_SEMANTICALLY_ADMISSIBLE`

## Source

- Gate: `M0_EVENT_SOURCED_EDIT_ADMISSION`
- Verdict: `FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`
- Execution HEAD: `509b71df8b00d91f3034592e4b10f7250dae984c`
- Integrity audit: `INTEGRITY_AUDIT_PASS`
- MIMIC-IV: `3.1`

## Decisive evidence

Raw `poe.transaction_type` marks were abundant and distributed, but the two action classes that require an already active medication were not consistent with the frozen strictly pre-order execution-confirmed regimen state.

- overall mapped events / patients: `2807706 / 88076`;
- `New`: `2064107 / 88052`;
- `Change`: `278259 / 54519`;
- `D/C`: `465340 / 60517`;
- distributed concepts meeting the frozen support rule: `103`.

State consistency:

- `Change` active-before: `47940 / 278259 = 0.17228553254342177`;
- `D/C` active-before: `74143 / 465340 = 0.15933081187948597`;
- frozen floor for each: `>= 0.70`.

Phase A therefore failed before model training. No structural probe, EditAudit evaluation, bootstrap, or Idea 007 was executed.

## Reusable lesson

> **A workflow transaction label is not automatically a clinically or operationally valid state-transition label.**

Even when a database exposes action-like fields such as `New`, `Change`, or `D/C`, a method may interpret them as explicit regimen edits only after those marks are compatible with the causal state representation used by the model.

High label frequency does not repair state-semantic inconsistency.

## Interpretation boundary

This result does **not** prove that MIMIC-IV transaction types are erroneous or useless. The mismatch may reflect CPOE workflow semantics, renewals/replacements, order linkage, medication normalization, administration timing, or differences between an order-state concept and the project's execution-confirmed regimen state.

The failure is narrower:

> Under the frozen 131-ATC-L4 mapping and the project's strictly pre-order execution-confirmed active-state semantics, raw `Change` and `D/C` cannot be promoted directly into reliable regimen-edit supervision.

## Closed resurrection patterns

Do not rescue the recorded route by:

- lowering the `0.70` consistency floors after observing the result;
- redefining the active state to make the labels fit;
- discarding inconsistent action events until a favorable subset remains;
- training a deeper Transformer/Mamba/GNN/point-process model on the same marks;
- adding DDI, KG, LLM, labs, vitals, or subgroup selection to compensate for the semantic failure;
- running an M0b under the same scientific claim.

## Reopen condition

A related action-modeling route may reopen only with a genuinely different decision object or independently validated action semantics, for example a transaction/state definition whose causal compatibility is established before model development.

The raw M0 labels themselves are not an admitted target for Idea 007.
