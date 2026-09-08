<!-- markdownlint-disable MD013 -->

# Model Reset: Privileged Physiological Response Supervision

## Status

- Stage: `PRE_IDEA_PRIVILEGED_RESPONSE_OPTIMIZATION`
- Current active Idea: none
- Idea 007: not created / not authorized
- Paper objective: first formal method paper, target at least a CCF-A Data/Mining/AI venue family
- Reset class: method-level supervision / information-flow reset
- Current owner: `ccf-idea-optimizer`
- Next owner: strict `ccf-idea-reviewer`
- Local scientific execution: **not authorized yet**

The Event-Sourced Regimen Editing M0 gate is closed. Raw `New / Change / D/C` workflow marks are not reused as regimen-edit supervision.

## Working research family

**Privileged physiological response supervision for medication recommendation.**

Working shorthand: `RPD-MR` (Response-Privileged Distillation for Medication Recommendation). The name is provisional and is not a novelty claim.

## Central scientific question

Can post-administration physiological monitoring that is available only during training provide medication-specific response-associated supervision that improves a strictly pre-order deployable medication recommender beyond both ordinary high-frequency state modeling and generic future-state auxiliary learning?

The method must never require post-order/post-administration physiology at inference.

## Core mechanism

At a causal medication decision point `t`:

1. a deployable student observes only information available before `t`;
2. for training examples with observable post-administration monitoring, a privileged teacher additionally observes the realized medication-in-context and a bounded post-administration physiological window;
3. the teacher encodes a **response-associated patient–medication representation**;
4. the student learns to predict/align with that representation from pre-order state and candidate medication;
5. recommendation remains the downstream task.

This is predictive privileged supervision, not causal treatment-effect estimation.

## Why this is not simply "add labs"

Recent MedRec already uses laboratory and monitoring information directly. REFINE models lab responses and dosage-titration trends; ChainCare jointly models lab-test and medication-injection event chains; MedGCN couples medication recommendation with lab imputation; DrugDoctor uses downstream historical conditions after previous prescriptions.

The candidate delta is narrower:

> future post-administration physiology is used only as training-time privileged supervision to shape a deployable candidate-medication representation; the inference model remains strictly pre-order.

Knowledge distillation itself is also prior art in MedRec through LEADER. Therefore the novelty cannot be "we distill a teacher". The proposed teacher knowledge source and the response-specific falsification controls must create the method delta.

## Mandatory overlap challenge

The route is invalid if its gains can be explained by any of the following:

- simply adding pre-order labs/vitals to the inference model;
- a generic future-state auxiliary prediction task with matched capacity;
- static train-only medication response prototypes;
- shuffled/misaligned post-administration responses;
- ordinary feature-level knowledge distillation without medication-response structure.

## Main non-causal boundary

Observed physiology after administration is influenced by disease severity, co-medications, monitoring policy, procedures, and other interventions. It must be described as a **response-associated signature**, not an individual medication effect, clinical efficacy label, or counterfactual outcome.

The model may condition the privileged teacher on active/co-administered treatment context to reduce obvious attribution error, but this does not convert observational data into causal evidence.

## Development routing

Optimizer artifact:

[`idea-optimization.md`](idea-optimization.md)

Literature grounding:

[`idea-grounding.md`](idea-grounding.md)

Current routing:

1. `ccf-idea-optimizer` completes the method-level formulation;
2. strict `ccf-idea-reviewer` challenges novelty, identifiability, feasibility, and evidence design;
3. Idea 007 may be created only if the reviewer admits a method-level contribution;
4. only after Idea creation may `ccf-experiment-designer` freeze Gate 01.

No standalone response-coverage audit, P0/P1 diagnostic chain, or local Agent run is authorized at this stage. Data coverage/linkage is a future Gate-01 mechanical preflight and must stop the Idea before training if inadequate.

## Quarantine

Until a later frozen protocol explicitly authorizes use, keep untouched:

- MIMIC-IV G3/G4 future reserve;
- R0 Holdout;
- historical project test split.
