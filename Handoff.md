# Handoff: Privileged Physiological Response Required Revisions

## Current state

Ideas 001--006 are terminated. There is currently no active Idea.

- **Current Stage**: `PRE_IDEA_PRIVILEGED_RESPONSE_REQUIRED_REVISIONS`
- **Current active Idea**: none
- **Idea 007**: not created / not authorized
- **Paper objective**: first formal method paper, targeting at least a CCF-A Data/Mining/AI venue family
- **Current method family**: `PRIVILEGED_PHYSIOLOGICAL_RESPONSE_SUPERVISION`
- **Strict review verdict**: `ACCEPT_WITH_REQUIRED_REVISIONS_BEFORE_IDEA_007`
- **Strict review score**: `3.89 / 5.00`
- **Next CCFA owner**: bounded `ccf-idea-optimizer`, then return to strict `ccf-idea-reviewer`
- **Local scientific execution**: not authorized
- **G3/G4 future reserve**: quarantined / uninspected
- **R0 Holdout**: quarantined / uninspected
- **Historical project test split**: untouched / uninspected

## Current packet

`research/memory/model-reset-20260908-privileged-physiological-response/`

Authoritative artifacts:

- `README.md`
- `idea-grounding.md`
- `idea-optimization.md`
- `idea-review.md`
- `closest-work-review.md`

Reusable admission constraint:

`research/memory/failures/privileged-response-preidea--response-specificity-not-yet-identified.md`.

## Strict review result

The family is not rejected. No exact general-MedRec work was found in the bounded 2023--2026 search whose central mechanism is realized post-administration physiology used only during training to supervise a strictly pre-order candidate-medication student.

However, the information-flow primitive itself is not novel. Current prior work separately covers:

- lab-response and monitoring-aware MedRec — REFINE, ChainCare;
- joint medication recommendation and lab-response prediction — MedGCN / Bhoi et al.;
- downstream historical response evidence — DrugDoctor;
- MedRec knowledge distillation — LEADER;
- clinical training-time privileged-modality distillation — OC-Distill;
- medication-aware physiological-response representations — Wu et al. EMBC 2025;
- generic future-observation teacher to current-only student distillation — Privileged Foresight Distillation 2026.

The search-scoped surviving delta is therefore only:

> medication-in-context post-administration physiological **values** as training-only privileged supervision for a strictly pre-order MedRec student, with mechanism controls proving that the gain depends on focal-medication conditioning and patient-medication-response correspondence rather than generic future prediction, monitoring policy, static medication priors, sample weighting, or KD mechanics.

## Three required revisions before Idea 007

### R1 — Medication-specificity subtraction

Freeze a matched medication-ablated future / Generic Future-State Auxiliary control. It must use the same supported events, future window, student, and comparable capacity while removing focal-medication-specific response construction.

If removing focal medication identity does not materially weaken the gain, terminate the response-specific mechanism.

### R2 — Monitoring-policy separation

Make `Monitoring-Mask-Only` mandatory and freeze response-value versus response-availability separation.

If monitoring availability/frequency alone performs comparably to the privileged-response method, terminate the physiological-response interpretation.

### R3 — Equal-support and deployment entitlement

Freeze the following semantics:

- response supervision applies only to observed administered positive events with valid linked future monitoring;
- unchosen medications receive no invented counterfactual response;
- all privileged controls use the same support mask and recommendation examples;
- unsupported examples remain in the recommendation objective rather than being silently dropped/reweighted;
- the student and its feature/normalization path use strictly pre-order information only;
- future/post-order/discharge information is confined to the training-only privileged branch.

Any deployment-path future leakage or unmatched sample-selection difference invalidates the later Gate result.

## Killer controls reserved for a later Gate 01

If a subsequent strict review admits Idea 007, Gate 01 must at least include:

- Strict Pre-Order Base;
- Base + Pre-Order Physiology;
- Generic Future-State Auxiliary / Medication-Ablated Future;
- Static Medication Response Prototype;
- Response Shuffle;
- Monitoring-Mask-Only;
- Proposed privileged-response method;
- Generic KD only if needed to isolate distillation mechanics.

Immediate stop conditions include any of the simple controls performing comparably to the proposed method, insufficient/disproportionately concentrated privileged-response support, or any deployment leakage.

Do not rescue a failed mechanism with a deeper Transformer/Mamba/GNN, larger teacher, wider response window, extra modalities, subgroup mining, or a second response definition under the same Idea.

## Latest empirical failure closure

The latest completed empirical reset remains Event-Sourced Regimen Editing M0:

`FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`.

`Change` and `D/C` raw workflow actions failed the frozen active-before consistency floors (`0.1723` and `0.1593` versus `0.70`). No model was trained.

This result remains separate from the privileged-response pre-Idea review.

## Routing

Authorized next sequence:

```text
ccf-idea-optimizer (bounded R1--R3 only)
-> strict ccf-idea-reviewer
```

Only a later reviewer verdict of `ACCEPT_TO_CREATE_IDEA_007` may authorize:

```text
ccf-pipeline-orchestrator
-> Idea 007 creation
-> ccf-experiment-designer
-> Gate 01 design
```

No Idea 007, Gate 01, response-coverage diagnostic, or local Agent experiment is authorized now.
