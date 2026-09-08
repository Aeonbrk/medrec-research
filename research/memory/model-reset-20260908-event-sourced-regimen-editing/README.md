<!-- markdownlint-disable MD013 -->

# Model Reset: Event-Sourced Regimen Editing

## Status

- Stage: `PRE_IDEA_EVENT_EDIT_M0`
- Current active Idea: none
- Idea 007: not created / not authorized
- Paper objective: first formal method paper, target at least a CCF-A Data/Mining/AI venue family
- Reset class: architecture/model-level reset, not a feature-fishing continuation
- Only authorized local scientific execution: `M0_EVENT_SOURCED_EDIT_ADMISSION`

This reset follows S0's terminal verdict `FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`. The temporal-adaptation route is closed under its frozen boundary.

## Selected research question

Can medication recommendation be reformulated as a strictly causal sequence of explicit regimen-edit actions at provider order time, and does learned action-state structure add predictive value beyond a flat action classifier with the same state-validity mask?

The candidate decision object is the observed medication-order action mark:

`(transaction_type, medication)`

with transaction types:

- `New`;
- `Change`;
- `D/C`.

The scientific distinction is important. Generic visit-level medication-set prediction and visit-to-visit change prediction are already crowded. The project instead asks whether raw event-sourced order actions and the current regimen state define a distinct, learnable decision problem.

## Why this route survives prior failures

This route does not reuse the failed Idea-006 safety claim. It uses neither DDI nor exposure-risk optimization.

It also does not add another post-hoc scalar to frozen medication scores. The target itself changes from a medication-only label to an explicit action-medication mark derived from raw provider-order transactions.

The existing Gate-01 infrastructure already contains the required ingredients:

- causal order history;
- transaction types in history;
- current pre-order regimen state;
- 10-minute order bursts;
- a 131-concept ATC-L4 vocabulary.

The current Gate-01 target construction, however, collapses current `New` and `Change` events into medication-only labels and excludes `D/C` from the target. M0 tests whether preserving the action semantics is materially useful.

## Closest-work boundary

The route must remain distinct from:

- MICRON: visit-level medication addition/removal prediction from residual health changes;
- ARMR: visit-level adaptive weighting between new and existing drugs;
- HeteroMed: visit-level collaborative drug expansion/inheritance;
- Rough et al.: order-time medication prediction within a 10-minute horizon, but without explicit regimen-edit action modeling.

Therefore the publishable delta cannot be "medication changes matter" or "predict at order time". It must be the combination of event-sourced action marks, causal regimen state, state-valid decoding, and a learned event-edit mechanism that beats equal-entitlement direct controls.

## M0 routing

Protocol SSOT:

[`m0-event-edit-admission-protocol.md`](m0-event-edit-admission-protocol.md)

Grounding:

[`idea-grounding.md`](idea-grounding.md)

### PASS

`PASS_M0_EVENT_EDIT_STRUCTURE`

Then return to `ccf-pipeline-orchestrator` and route to:

1. `ccf-idea-optimizer` on this single event-sourced editing family;
2. strict `ccf-idea-reviewer` against MICRON, ARMR, HeteroMed, Rough et al., COGNet, and generic marked temporal point-process baselines;
3. Idea 007 may be created only if the final method delta survives that review.

### FAIL

`FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`

Then return to `NO_HIGH_VALUE_DIRECTION_YET`.

Do not run M0b, add DDI/safety, add LLM/KG, ingest labs/vitals, change the action vocabulary, or rescue the route with a deeper encoder.

## Quarantine

M0 must not inspect:

- MIMIC-IV G3/G4 future reserve (`2017 - 2022` under the anchor-year protocol);
- R0 Holdout;
- the historical project test split.
