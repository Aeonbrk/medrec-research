<!-- markdownlint-disable MD013 -->

# Model Reset: Privileged Physiological Response Supervision

## Status

- Stage: `IDEA_007_GATE_01_DESIGN_FROZEN_IMPLEMENTABILITY_CLOSED_TRAINING_NOT_AUTHORIZED`
- Current active Idea: `007-privileged-physiological-response-supervision`
- Idea 007: created/admitted
- Paper objective: first formal method paper, target at least a CCF-A Data/Mining/AI venue family
- Reset class: method-level supervision / information-flow reset
- Optimizer formulation: completed
- Strict re-review verdict: `ACCEPT_TO_CREATE_IDEA_007`
- Strict re-review score: `4.17 / 5.00`
- Reviewer confidence: medium-high
- Admission owner: `ccf-pipeline-orchestrator` (completed)
- Gate 01 design owner: `ccf-experiment-designer` (completed)
- Gate 01 design audit: `DESIGN_INTEGRITY_PASS` after teacher-objective domain closure and exact V7 Generic Pre-Order KD freeze
- Local scientific execution / training: **not authorized**

The Event-Sourced Regimen Editing M0 gate remains closed. Raw `New / Change / D/C` workflow marks are not reused as regimen-edit supervision.

## Admitted scientific family and Idea 007

**Privileged physiological response supervision for medication recommendation.**

Working shorthand `RPD-MR` remains provisional and is not a novelty claim.

Canonical Idea-007 artifacts:

- [`../../ideas/007-privileged-physiological-response-supervision/`](../../ideas/007-privileged-physiological-response-supervision/)
- [`../../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-protocol.md`](../../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-protocol.md)
- [`../../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-design-integrity-audit.md`](../../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-design-integrity-audit.md)

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
- student recommendation covers full `E_rec`, while teacher recommendation and
  alignment both use exactly the common `A(e)=1` support;
- `A(e)=0` constructs no teacher input, latent, loss, or synthetic response, and
  unsupported examples remain in the student objective without deletion,
  reweighting, or resampling;
- student features and normalization are strictly pre-order;
- post-order medication, administration, future labs/vitals, future masks, discharge-coded information, and other future-derived statistics are forbidden on the student path;
- the teacher and privileged targets are absent at inference.

Deployment leakage or unmatched support/reweighting invalidates the future Gate.

## Future Gate 01 killer family

The audited Gate 01 protocol covers:

- Strict Pre-Order Base;
- Base + Pre-Order Physiology;
- Generic Future-State Auxiliary / Medication-Ablated Future;
- Static Medication Response Prototype;
- Response Shuffle;
- Monitoring-Mask-Only;
- Proposed privileged-response method;
- Generic Pre-Order KD with a parameter-independent teacher exactly isomorphic to
  `S_pre`, using only the same strict pre-order schema and no privileged future
  information (included because the proposed method has a live
  teacher/student-alignment alternative).

A compatible REFINE/ChainCare-style comparison may be included when task alignment is scientifically valid.

The mechanism terminates if a simple matched control performs comparably, if
privileged-response support is insufficient/materially concentrated, if the
statistical rule is inconclusive, or if deployment leakage or unequal entitlement
is detected. Do not respond with architecture scaling, response-window search,
additional modalities, subgroup mining, post-hoc feature expansion, favorable-seed
selection, a new split, or a second response definition.

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

Current authorized terminal state:

```text
Idea 007: created/admitted
Gate 01: design frozen / objective-domain closed / V7 executable / independently audited
Mechanical preflight: NOT RUN
Implementation: NOT STARTED
Training: NOT AUTHORIZED
Quarantine: intact
Next owner: ccf-pipeline-orchestrator
```

This historical packet records the admission inputs. The current Idea-007 artifacts
record the frozen protocol and audit. Neither artifact authorizes response-coverage
execution, Gate execution, Audit access, or local training.

## Quarantine

Keep untouched until a later frozen protocol explicitly authorizes use:

- MIMIC-IV G3/G4 future reserve;
- R0 Holdout;
- historical project test split.
