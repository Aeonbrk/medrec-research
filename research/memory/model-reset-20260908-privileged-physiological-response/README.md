<!-- markdownlint-disable MD013 -->

# Model Reset: Privileged Physiological Response Supervision

## Status

- Stage: `PRE_IDEA_PRIVILEGED_RESPONSE_REQUIRED_REVISIONS`
- Current active Idea: none
- Idea 007: not created / not authorized
- Paper objective: first formal method paper, target at least a CCF-A Data/Mining/AI venue family
- Reset class: method-level supervision / information-flow reset
- Optimizer formulation: completed
- Strict review: completed
- Strict review verdict: `ACCEPT_WITH_REQUIRED_REVISIONS_BEFORE_IDEA_007`
- Strict review score: `3.89 / 5.00`
- Next owner: strict `ccf-idea-reviewer` (bounded R1--R3 optimizer revision completed)
- Local scientific execution: **not authorized**

The Event-Sourced Regimen Editing M0 gate remains closed. Raw `New / Change / D/C` workflow marks are not reused as regimen-edit supervision.

## Working research family

**Privileged physiological response supervision for medication recommendation.**

Working shorthand `RPD-MR` remains provisional and is not a novelty claim.

## Central scientific question

Can post-administration physiological monitoring that is available only during training provide **medication-specific response-associated supervision** that improves a strictly pre-order deployable medication recommender beyond ordinary pre-order physiology, generic future-state supervision, monitoring-policy signals, static medication response priors, response-independent regularization, and generic distillation?

The method must never require post-order/post-administration physiology at inference.

## Core mechanism

At a medication-order decision point `t`:

1. a deployable student observes only strictly pre-order information;
2. for training examples with a linked observed medication administration and valid bounded future monitoring, a privileged teacher additionally observes the realized medication-in-context and post-administration physiological window;
3. the teacher encodes a response-associated patient-medication representation;
4. the student learns to anticipate that representation from pre-order state and candidate medication;
5. recommendation remains the downstream task.

This is predictive privileged supervision, not causal treatment-effect estimation.

## Closest-work subtraction

The route cannot claim novelty from any of the following individually:

- lab-response/titration modeling in MedRec — REFINE;
- lab/injection monitoring event chains — ChainCare;
- joint MedRec/lab-response or lab-prediction tasks — MedGCN and Bhoi et al. 2023;
- downstream historical health-state evidence after prior medications — DrugDoctor;
- MedRec knowledge distillation — LEADER;
- generic clinical training-time privileged-modality distillation — OC-Distill;
- medication-aware physiological-response representation — Wu et al. EMBC 2025;
- generic true-future-observation teacher to current-only student distillation — Privileged Foresight Distillation 2026.

The search-scoped residual delta is narrower:

> paired medication-in-context post-administration physiological **values** as training-only privileged supervision for a strictly pre-order candidate-medication student, with matched controls proving that response semantics matter beyond generic future-state learning, medication identity/prototypes, monitoring availability, sample weighting, and KD mechanics.

Detailed provenance:

[`closest-work-review.md`](closest-work-review.md).

## Strict review

Authoritative review:

[`idea-review.md`](idea-review.md).

Verdict:

`ACCEPT_WITH_REQUIRED_REVISIONS_BEFORE_IDEA_007`

The family is preserved because no exact direct general-MedRec collision was found and the hypothesis has a cheap decisive falsification path. It was not yet an Idea at strict review time because the formulation did not fully isolate the claimed medication-specific physiological-response mechanism; the bounded optimizer pass has now frozen that formulation contract, pending strict re-review.

## Required revisions before Idea 007 (now frozen pending strict re-review)

### R1 — Medication-specificity subtraction

Freeze a matched Generic Future-State Auxiliary / Medication-Ablated Future control that removes focal-medication-specific response construction while matching support, future window, student, and capacity closely enough to isolate medication specificity.

### R2 — Monitoring-policy separation

Make `Monitoring-Mask-Only` mandatory and freeze response-value versus response-availability separation. Physiological values must show incremental value beyond whether/how often measurements occur.

### R3 — Equal-support and deployment entitlement

Freeze positive-only observed-response semantics and identical support/sample entitlement across privileged controls. Unsupported examples remain in the recommendation objective. Student features and normalization remain strictly pre-order, and future/post-order/discharge information is confined to the training-only privileged branch.

Reusable constraint:

[`../failures/privileged-response-preidea--response-specificity-not-yet-identified.md`](../failures/privileged-response-preidea--response-specificity-not-yet-identified.md).

## Future killer controls after re-review only

Any later Gate 01 must at least include:

- Strict Pre-Order Base;
- Base + Pre-Order Physiology;
- Generic Future-State Auxiliary / Medication-Ablated Future;
- Static Medication Response Prototype;
- Response Shuffle;
- Monitoring-Mask-Only;
- Proposed privileged-response method;
- Generic KD only if needed to isolate distillation mechanics.

A compatible monitoring-aware MedRec baseline should be included when task alignment makes it scientifically valid.

The mechanism terminates if a simple control performs comparably, if privileged-response support is insufficient/materially concentrated, or if deployment leakage is detected. Do not respond with architecture scaling or response-definition fishing.

## Non-causal boundary

Observed post-administration physiology is influenced by disease severity, concurrent medications, fluids, procedures, ventilation, dose/route, clinician actions, spontaneous progression, monitoring policy, and selective measurement.

Allowed language:

- `response-associated physiological signature`;
- `medication-in-context physiological trajectory`;
- `privileged physiological supervision`.

Disallowed without independent causal identification:

- treatment effect;
- drug efficacy;
- therapeutic benefit;
- counterfactual outcome;
- clinically optimal medication.

## Routing

Completed bounded owner and current next owner:

```text
ccf-idea-optimizer (bounded R1--R3 only)
-> strict ccf-idea-reviewer
```

Idea 007 may be created only if the subsequent strict review returns `ACCEPT_TO_CREATE_IDEA_007`.

No standalone response-coverage audit, P0/P1 diagnostic chain, Gate 01, or local Agent run is authorized now. Response coverage/linkage remains a future Gate-01 mechanical preflight if the Idea is later admitted.

## Quarantine

Keep untouched until a later frozen protocol explicitly authorizes use:

- MIMIC-IV G3/G4 future reserve;
- R0 Holdout;
- historical project test split.
