# Handoff: Privileged Physiological Response Method Reset

## Current state

Ideas 001--006 are terminated. There is currently no active Idea.

- **Current Stage**: `PRE_IDEA_PRIVILEGED_RESPONSE_OPTIMIZATION`
- **Current active Idea**: none
- **Idea 007**: not created / not authorized
- **Paper objective**: first formal method paper, targeting at least a CCF-A Data/Mining/AI venue family
- **New-model policy**: a genuinely new model is allowed when it encodes a new falsifiable supervision, decision, state, or information-flow mechanism
- **Current method family**: `PRIVILEGED_PHYSIOLOGICAL_RESPONSE_SUPERVISION`
- **Optimizer status**: completed / strict review pending
- **Local scientific execution**: not authorized
- **G3/G4 future reserve**: quarantined / uninspected
- **R0 Holdout**: quarantined / uninspected
- **Historical project test split**: untouched / uninspected

## Latest failure closure — Event-Sourced Regimen Editing M0

M0 returned:

`FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`.

The labels were abundant, but the state-semantic admission failed:

- `Change` active-before: `0.17228553254342177` versus frozen floor `0.70`;
- `D/C` active-before: `0.15933081187948597` versus frozen floor `0.70`.

No model was trained and EditAudit was not accessed.

Failure memory:

`research/memory/failures/event-sourced-regimen-editing-m0--workflow-action-state-inconsistency.md`.

Reusable constraint:

> A workflow transaction label is not automatically a valid regimen-state transition label. High support does not repair semantic inconsistency.

Do not run M0b or rescue the raw `New / Change / D/C` target with a deeper encoder.

## Current method reset

Packet:

`research/memory/model-reset-20260908-privileged-physiological-response/`

Key artifacts:

- `README.md`
- `idea-grounding.md`
- `idea-optimization.md`

### Working hypothesis

At medication decision time, a deployable model can observe only pre-order state. During training, however, some realized medication events are followed by high-frequency physiological monitoring.

The candidate mechanism uses that **post-administration physiology only as privileged training supervision**:

1. a teacher receives pre-order state, realized medication/treatment context, and a bounded post-administration monitoring window;
2. it learns a response-associated patient-medication representation;
3. a deployable student learns to anticipate that representation from pre-order state plus candidate medication;
4. inference never sees future physiology or the teacher.

This is predictive privileged learning, not causal treatment-effect estimation.

### Closest-work boundary

The route must not claim novelty from any of the following individually:

- lab-response/titration modeling in MedRec — REFINE;
- lab/injection event chains — ChainCare;
- joint MedRec/lab prediction — MedGCN and prior AAAI Symposium work;
- downstream historical condition after medication — DrugDoctor;
- medication-recommendation knowledge distillation — LEADER;
- generic training-time privileged multimodal distillation — OC-Distill;
- medication-conditioned physiological-response representation — Wu et al. EMBC 2025.

The current search-scoped delta is narrowly:

> medication-in-context post-administration physiology as training-only privileged supervision for a strictly pre-order candidate-medication student, with controls proving that response semantics add value beyond generic future-state regularization.

### Mandatory killer controls for any later Gate 01

A future protocol must at least challenge the candidate against:

- causal Base with identical deployment inputs;
- Base + pre-order physiology;
- capacity-matched generic future-state auxiliary learning;
- static train-only medication-response prototypes;
- response-shuffle/misalignment control;
- compatible monitoring-aware MedRec baselines;
- a KD control if needed to isolate the response knowledge source from distillation mechanics.

The route is not admitted if generic future-state supervision or shuffled responses explain the gain.

## Routing

The optimizer has completed a standard method-level formulation. **Do not create Idea 007 yet.**

Next owner:

`ccf-idea-reviewer`

The strict review must decide whether the residual novelty, non-causal soundness, support feasibility, and evidence package justify creating Idea 007.

If admitted:

`ccf-pipeline-orchestrator -> Idea 007 -> ccf-experiment-designer -> Gate 01`.

If rejected:

return to `NO_HIGH_VALUE_DIRECTION_YET` without a new response-diagnostic series.

No local Agent work is authorized before strict review.
