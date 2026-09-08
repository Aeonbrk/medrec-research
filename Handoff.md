# Handoff: Event-Sourced Regimen-Edit Premise Admission

## Current state

Ideas 001--006 are terminated. There is currently no active Idea.

- **Current Stage**: `NO_HIGH_VALUE_DIRECTION_YET`
- **Current active Idea**: none
- **Idea 007**: not created / not authorized
- **Paper objective**: first formal method paper, targeting at least a CCF-A Data/Mining/AI venue family
- **New-model policy**: a genuinely new model/architecture is allowed, but only after its decision/mechanism premise survives the strongest simple same-information control
- **Completed local scientific execution**: `M0_EVENT_SOURCED_EDIT_ADMISSION` → `FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`
- **G3/G4 future reserve**: quarantined / uninspected
- **R0 Holdout**: quarantined / uninspected
- **Historical project test split**: untouched / uninspected

## Latest completed reset: Medication Practice Shift S0

Packet:

`research/memory/literature-search-20260908-medication-practice-shift/`

Final verdict:

`FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`.

The temporal-adaptation premise failed more fundamentally than simple prior-drift sufficiency: the frozen SourceOnly model did not degrade on the G2 target era.

- `R_source = 0.4310427829`;
- `R_target_base = 0.4403698933`;
- `G_base = R_source - R_target_base = -0.0093271104`;
- 95% CI `[-0.0145853913, -0.0035238892]`.

The target-prior logit-bias control improved target Recall@5 further:

- selected `alpha = 1.0`;
- `R_target_bias = 0.4441638446`;
- `G_bias = -0.0131210617`;
- 95% CI `[-0.0183542549, -0.0074505314]`.

Therefore do not rescue this route by changing temporal groups, removing anchor-year matching, adding features, switching to eICU, weakening the bias control, or running S0b.

Failure memory:

`research/memory/failures/medication-practice-shift-s0--no-material-forward-degradation.md`.

## Current bounded model reset

Packet:

`research/memory/model-reset-20260908-event-sourced-regimen-editing/`

Selected family:

`EVENT_SOURCED_REGIMEN_EDITING`.

### Scientific premise

The existing raw order-time pipeline already observes historical medication transaction types and a causal pre-order regimen state. However, its current supervised target collapses present `New` and `Change` orders to medication-only labels and excludes present `D/C` as a target.

M0 asks whether preserving the actual provider-order action mark:

`(transaction_type, medication)`

with `transaction_type in {New, Change, D/C}` creates incremental learnable structure beyond a simple equal-entitlement control.

This is an architecture/model-level reset because it changes the decision object and decoder structure. It is not another feature over frozen medication scores.

### Closest-work boundary

Do not claim novelty from medication changes or order-time prediction alone.

- MICRON already predicts medication additions/removals across visits.
- ARMR already distinguishes historical reuse from new medications at the visit level.
- HeteroMed already models medication expansion/inheritance across visits.
- Rough et al. already predict inpatient medication identity at order time with a 10-minute horizon.

The candidate delta is narrowly the event-sourced intersection: explicit raw order-action marks + strictly causal regimen state + state-valid decoding + a learned structured action-medication mechanism that must beat an equal-entitlement direct state-mask control.

Grounding:

`research/memory/model-reset-20260908-event-sourced-regimen-editing/idea-grounding.md`.

## M0 — only authorized local scientific execution

Protocol SSOT:

`research/memory/model-reset-20260908-event-sourced-regimen-editing/m0-event-edit-admission-protocol.md`.

M0 is one bounded gate with two phases.

### Phase A — semantic/support admission

Before model training, verify that mapped `New / Change / D/C` targets are sufficiently supported and that `Change`/`D/C` are sufficiently consistent with the strictly pre-order regimen state.

If Phase A fails, stop without model training.

### Phase B — fixed structural probe

Only on Phase-A PASS, compare three fixed variants under one common lightweight causal encoder:

1. `FlatMark`;
2. `SeparateHeads + DirectStateMask` — strongest simple control;
3. `StateEditProbe` — fixed rank-32 structured action-medication decoder using the same state-validity mask.

No architecture grid is allowed.

The primary learned-value comparison is:

`StateEditProbe - (SeparateHeads + DirectStateMask)`.

The frozen M0 PASS rule requires all preregistered support conditions, at least `+0.010` MacroActionRecall@5 with CI lower bound above zero, at least `+0.005` JointMarkRecall@5 with CI lower bound above zero, medication-level non-inferiority, no material action-specific regression, and integrity-audit PASS.

## Routing

### M0 PASS

Return to `ccf-pipeline-orchestrator`.

Then:

1. run `ccf-idea-optimizer` on the single event-sourced regimen-editing family;
2. run strict `ccf-idea-reviewer` against the closest change-aware/order-time/marked-event baselines;
3. create Idea 007 only if that review admits a genuine method contribution.

A PASS does not itself create Idea 007.

### M0 FAIL

Return to:

`NO_HIGH_VALUE_DIRECTION_YET`.

Do not run M0b or rescue with a deeper encoder, DDI/safety, KG/LLM, labs/vitals, another vocabulary, or subgroup mining.

Recorded result:

`research/memory/model-reset-20260908-event-sourced-regimen-editing/m0-decision.md`

The Phase-A state-consistency floors failed for both `Change` and `D/C`. No model was trained, no freeze manifest was written, and EditAudit was not accessed.

## Next owner

Next owner is `ccf-pipeline-orchestrator`. No further scientific execution is authorized until it routes a new, independently admitted direction.

No other scientific execution is authorized in the same run.
