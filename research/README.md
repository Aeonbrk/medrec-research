<!-- markdownlint-disable MD013 -->

# Research Organization

This directory manages the core scientific lifecycle for early-stage research:

`bounded pre-Idea admission (when needed) -> Idea -> Minimal Experiment -> Evidence -> Decision -> revise / kill / continue -> Paper`.

## Directory structure

- **`premise-audit/`**: bounded historical/project-local premise audits. These are decision gates, not a standing exploratory lane or publication contribution.
- **`ideas/`**: the fundamental unit of admitted early-stage method research. Each Idea must expose a core hypothesis, strongest simple alternative, next minimal falsification experiment, evidence, and current verdict.
- **`baselines/`**: baseline reproduction and comparison infrastructure, separate from scientific idea failures.
- **`memory/`**: cross-Idea reusable constraints, failure records, literature maps, and bounded pre-Idea reset packets.

## Workflow: premise to paper

0. **Bounded pre-Idea admission**: use only when a candidate method family depends on a cheap project-local fact or structural premise that literature cannot establish. One gate must produce one pass/fail decision. Serial rescue diagnostics are prohibited.
1. **Idea Stage (`ideas/<idea-name>/`)**: create an Idea only after its premise is admitted and its literature delta is credible.
2. **Minimal Experiment**: test the strongest uncertainty using the cheapest decisive experiment. The strongest simple/equal-entitlement control precedes method storytelling.
3. **Evidence & Decision**: audited evidence produces a clear revise/kill/continue verdict.
4. **Failure & Lesson Preservation**: idea-local failures remain with the Idea; cross-Idea constraints are distilled into `memory/`.
5. **Mature to Paper (`papers/<paper-name>/`)**: only an Idea with a demonstrated method contribution and credible claim-support plan graduates to a paper lifecycle.

A genuinely new model/architecture is allowed. It is not sufficient merely to replace a backbone: the new model must instantiate a new, falsifiable decision object, supervision structure, state transition, or information-flow mechanism.

## Source boundary

Historical memory is based on `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. Archive paths retain that provenance. Current live routing is defined by the files under `research/memory/` and `Handoff.md`.

## Navigation

- [Research-Space Reorientation](memory/research-space-reorientation.md): current cross-Idea SSOT.
- [Literature Opportunity Map](memory/literature-opportunity-map.md): current closest-work and opportunity boundary.
- [Event-Sourced Regimen Editing reset](memory/model-reset-20260908-event-sourced-regimen-editing/): active bounded pre-Idea model reset and frozen M0 protocol.
- [Medication Practice-Shift packet](memory/literature-search-20260908-medication-practice-shift/): completed S0 reset; terminal failure evidence.
- [Cross-Idea Memory](memory/README.md): live memory navigation.
- [Accumulated Experience](memory/accumulated-experience.md): historical synthesis; not live routing state.
- [Reusable Lessons](memory/reusable-lessons.md): durable control and claim-limit rules.
- [Ideas Index](ideas/README.md): authoritative Idea lifecycle index.

## Current scientific state

- **Stage**: `PRE_IDEA_EVENT_EDIT_M0`.
- **Active Idea**: none.
- **Ideas 001--006**: terminated.
- **Idea 007**: not created / not authorized.
- **Paper objective**: first formal method paper, target at least a CCF-A Data/Mining/AI venue family.
- **Excluded terminal outcomes**: pure benchmark/measurement/survey, indefinite exploratory diagnostics, and months of feature fishing.

### Latest completed gate: Medication Practice-Shift S0

S0 returned:

`FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`.

The frozen source-era predictor did not suffer forward degradation on the G2 target era:

- `R_source = 0.4310427829`;
- `R_target_base = 0.4403698933`;
- `G_base = -0.0093271104`, 95% CI `[-0.0145853913, -0.0035238892]`.

Target-prior correction increased target Recall@5 further to `0.4441638446`.

Therefore the temporal-adaptation family is closed under its frozen setting. No S0b, alternative year split, eICU rescue, feature expansion, or weakened prior control is authorized.

### Current bounded reset: Event-Sourced Regimen Editing

The raw order-time infrastructure records `New`, `Change`, and `D/C` provider-order transactions and reconstructs a strictly pre-order medication state. The existing supervised target nevertheless collapses current `New` and `Change` orders to medication-only labels and excludes current `D/C` as a target.

The current reset asks whether explicit `(action, medication)` marks create a genuinely useful decision structure at provider-order time.

Only one local gate is authorized:

`M0_EVENT_SOURCED_EDIT_ADMISSION`.

Protocol:

[`memory/model-reset-20260908-event-sourced-regimen-editing/m0-event-edit-admission-protocol.md`](memory/model-reset-20260908-event-sourced-regimen-editing/m0-event-edit-admission-protocol.md).

M0 first tests action support/state consistency. Only if that passes does it compare a fixed structured `StateEditProbe` against the mandatory equal-entitlement `SeparateHeads + DirectStateMask` control under a shared lightweight causal encoder.

No architecture grid is permitted. M0 is designed to answer whether the structural premise deserves a full new model.

### M0 routing

On `PASS_M0_EVENT_EDIT_STRUCTURE`:

1. return to `ccf-pipeline-orchestrator`;
2. run `ccf-idea-optimizer` on the single surviving event-edit family;
3. run strict `ccf-idea-reviewer` against the closest change-aware/order-time/marked-event work;
4. create Idea 007 only if the method delta survives review.

On `FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`:

return to `NO_HIGH_VALUE_DIRECTION_YET` with no M0b or deeper-encoder rescue.

## Quarantine

Until an explicitly frozen later stage authorizes otherwise, do not inspect:

- MIMIC-IV G3/G4 future groups;
- R0 Holdout;
- the historical project test split.

## Reuse policy

Reusing infrastructure, metrics, controls, or failure taxonomies does not reactivate their parent route. Every new method family must earn its own premise admission, current literature check, strongest simple control, and falsification gate.

## Claim limits

Existing failures and pre-Idea gates do not establish clinical safety, therapeutic equivalence, causal treatment effects, or universal impossibility claims. Every closure is conditional on its recorded data, task, semantics, and comparison boundary.
