<!-- markdownlint-disable MD013 -->

# Model Reset: Privileged Physiological Response Supervision

## Status

- Stage: `PRE_IDEA_PRIVILEGED_RESPONSE_ADMITTED_FOR_IDEA_007`
- Current active Idea: none
- Idea 007: not created / creation explicitly authorized
- Paper objective: first formal method paper, target at least a CCF-A Data/Mining/AI venue family
- Reset class: method-level supervision / information-flow reset
- Optimizer formulation: completed
- Strict re-review verdict: `ACCEPT_TO_CREATE_IDEA_007`
- Strict re-review score: `4.17 / 5.00`
- Reviewer confidence: medium-high
- Next owner: `ccf-pipeline-orchestrator`
- Local scientific execution: **not authorized**

The Event-Sourced Regimen Editing M0 gate remains closed. Raw `New / Change / D/C` workflow marks are not reused as regimen-edit supervision.

## Admitted scientific family

**Privileged physiological response supervision for medication recommendation.**

Working shorthand `RPD-MR` remains provisional and is not a novelty claim.

## Central scientific question

Can post-administration physiological monitoring that is available only during training provide **medication-specific response-associated supervision** that improves a strictly pre-order deployable medication recommender beyond ordinary pre-order physiology, generic future-state supervision, monitoring-policy signals, static medication response priors, response-independent regularization, and generic distillation?

The method must never require post-order/post-administration physiology at inference.

## Scientific object

At a medication-order decision point `t`:

1. a deployable student observes only strictly pre-order information;
2. training examples with a linked observed administration and valid bounded future monitoring may receive privileged supervision;
3. the teacher represents the realized medication-in-context post-administration physiological trajectory;
4. the student must anticipate that representation from pre-order state and candidate medication;
5. recommendation remains the downstream task.

This is predictive privileged supervision, not causal treatment-effect estimation.

## Closest-work subtraction

The route cannot claim novelty from any of the following individually:

- lab-response/titration modeling in MedRec — REFINE;
- lab/injection monitoring event chains — ChainCare;
- joint MedRec/lab-response or lab-prediction tasks — MedGCN and Bhoi et al. 2023;
- downstream historical health-state evidence after prior medications — DrugDoctor;
- MedRec knowledge distillation — LEADER and an accepted IJCAI-ECAI 2026 dual-channel MedRec KD method;
- generic clinical training-time privileged-modality distillation — OC-Distill;
- clinical future-aware teacher/student transfer — 2026 future-aware blood-glucose forecasting;
- medication-aware physiological-response representation — Wu et al. EMBC 2025;
- generic true-future-observation teacher to current-only student distillation — Privileged Foresight Distillation 2026.

The search-scoped residual delta is narrower:

> paired medication-in-context post-administration physiological **values** as positive-event, training-only privileged supervision for a strictly pre-order candidate-medication student, with matched controls proving that response semantics matter beyond generic future-state learning, medication identity/prototypes, monitoring availability, sample weighting, individualized-pairing artifacts, and KD mechanics.

Detailed provenance:

[`closest-work-review.md`](closest-work-review.md).

## Strict admission review

Authoritative review:

[`idea-review.md`](idea-review.md).

Verdict:

`ACCEPT_TO_CREATE_IDEA_007`

The prior blocker was mechanism identification rather than empirical failure. The bounded optimizer pass has now frozen the required subtraction and deployment contracts strongly enough that one future Gate 01 can falsify the response-specific claim without post-hoc rescue.

This is scientifically admissible for Idea creation.

## Frozen R1--R3 admission contract

### R1 — Medication-specificity subtraction

Generic Future-State Auxiliary / Medication-Ablated Future must use the same recommendation examples, support, administration anchor, future window, future-value availability, student, latent dimensionality, comparable teacher capacity, auxiliary weight, and update entitlement while removing focal-medication identity and medication-specific construction from the privileged target branch.

If medication ablation is comparable to Proposed:

`STOP_NO_MEDICATION_SPECIFIC_RESPONSE_VALUE`.

### R2 — Monitoring-policy separation

Monitoring-Mask-Only must receive the same response-support mask, future window, measurement availability/frequency structure, student, capacity, and update entitlement but no physiological values or value-derived summary.

If Monitoring-Mask-Only is comparable to Proposed:

`STOP_MONITORING_POLICY_SUFFICIENCY`.

### R3 — Equal-support positive-only supervision and deployment entitlement

- response supervision exists only on actually administered positive medication events with valid linked future monitoring;
- unchosen medications receive no invented counterfactual response;
- all privileged variants use the same recommendation examples and response-support mask;
- unsupported examples remain in the recommendation objective;
- student features and normalization are strictly pre-order;
- post-order medication, administration, future labs/vitals, future masks, discharge-coded information, and other future-derived statistics are forbidden on the student path;
- the teacher and privileged targets are absent at inference.

Deployment leakage or unmatched support/reweighting invalidates the future Gate.

## Future Gate 01 killer family

After Idea 007 is created and only after `ccf-experiment-designer` freezes the protocol, Gate 01 must at least cover:

- Strict Pre-Order Base;
- Base + Pre-Order Physiology;
- Generic Future-State Auxiliary / Medication-Ablated Future;
- Static Medication Response Prototype;
- Response Shuffle;
- Monitoring-Mask-Only;
- Proposed privileged-response method;
- Generic KD only if needed to isolate KD mechanics.

A compatible REFINE/ChainCare-style comparison may be included when task alignment is scientifically valid.

The mechanism terminates if a simple matched control performs comparably, if privileged-response support is insufficient/materially concentrated, or if deployment leakage or unequal entitlement is detected. Do not respond with architecture scaling, response-window search, additional modalities, subgroup mining, or a second response definition.

## Non-causal boundary

Observed post-administration physiology is influenced by disease severity, concurrent medications, fluids, procedures, ventilation, dose/route, clinician actions, spontaneous progression, monitoring policy, and selective measurement.

Allowed language:

- `response-associated physiological signature`;
- `medication-in-context physiological trajectory`;
- `privileged physiological response supervision`;
- `future physiological supervision`.

Disallowed without independent causal identification:

- treatment effect;
- causal response;
- drug efficacy;
- therapeutic benefit;
- counterfactual outcome;
- clinically optimal medication;
- individualized causal benefit.

## Routing

Authorized next workflow:

```text
ccf-pipeline-orchestrator
-> create/admit Idea 007
-> ccf-experiment-designer
-> Gate 01 design-integrity audit
-> push
-> stop before training
```

This packet does not itself create Idea 007, inspect response coverage, design Gate 01, or authorize local training.

## Quarantine

Keep untouched until a later frozen protocol explicitly authorizes use:

- MIMIC-IV G3/G4 future reserve;
- R0 Holdout;
- historical project test split.
