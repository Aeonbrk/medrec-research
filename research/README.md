<!-- markdownlint-disable MD013 -->

# Research Organization

This directory manages the scientific lifecycle:

`bounded pre-Idea admission when necessary -> idea optimization/review -> Idea -> Minimal Experiment -> Evidence -> Decision -> Paper`.

## Core policy

The project targets its first formal **method paper** at at least a CCF-A Data/Mining/AI venue family.

Allowed:

- genuinely new models/architectures;
- new supervision, representation, decision, state-transition, or information-flow mechanisms;
- bounded pre-Idea checks when a method premise cannot be established from literature alone.

Not acceptable as terminal outcomes:

- pure benchmark/measurement/survey work;
- indefinite diagnostic chains;
- months of feature fishing;
- swapping backbones over a failed scientific premise.

The strongest simple/equal-entitlement control precedes method storytelling.

## Directory structure

- `ideas/`: admitted method hypotheses and their bounded hypothesis-selection experiments.
- `memory/`: cross-Idea failure constraints, literature maps, and pre-Idea resets.
- `premise-audit/`: historical bounded premise tests; not a standing exploratory lane.
- `baselines/`: reproduction/comparison infrastructure, separate from scientific Idea failures.

## Current scientific state

- **Stage**: `IDEA_007_GATE_01_DESIGN_FROZEN_IMPLEMENTABILITY_CLOSED_TRAINING_NOT_AUTHORIZED`.
- **Active Idea**: `007-privileged-physiological-response-supervision`.
- **Ideas 001--006**: terminated.
- **Idea 007**: created/admitted.
- **Current family**: privileged physiological response supervision for medication recommendation.
- **Strict re-review verdict**: `ACCEPT_TO_CREATE_IDEA_007` (`4.17 / 5.00`).
- **Reviewer confidence**: medium-high.
- **Admission owner**: `ccf-pipeline-orchestrator` (completed).
- **Gate 01 design owner**: `ccf-experiment-designer` (completed).
- **Gate 01 design audit**: `DESIGN_INTEGRITY_PASS` after implementability closure.
- **Local scientific execution / training**: not authorized by this state.

Current packet:

[`memory/model-reset-20260908-privileged-physiological-response/`](memory/model-reset-20260908-privileged-physiological-response/).

Authoritative strict admission review:

[`memory/model-reset-20260908-privileged-physiological-response/idea-review.md`](memory/model-reset-20260908-privileged-physiological-response/idea-review.md).

Latest closest-work provenance:

[`memory/model-reset-20260908-privileged-physiological-response/closest-work-review.md`](memory/model-reset-20260908-privileged-physiological-response/closest-work-review.md).

## Admitted Idea 007 boundary

The exact search-scoped contribution is limited to:

> medication-in-context realized post-administration physiological **values** used only as positive-event, training-time privileged supervision for a strictly pre-order candidate-medication student, with matched controls proving that the gain is medication-specific and not explained by generic future-state learning, monitoring policy, static medication priors, individualized-pairing artifacts, response-independent regularization, sample weighting, or KD mechanics.

The generic primitive is not novel. Current prior art covers response-aware MedRec, monitoring chains, MedRec KD, clinical privileged-modality KD, clinical future-aware teacher/student transfer, and medication-aware physiological-response representation. The remaining novelty is the MedRec-specific response-supervision object plus mechanism identification.

## Frozen Gate 01 controls

Before any training, the audited Gate 01 protocol preserves:

1. **Medication specificity**: matched Generic Future-State Auxiliary / Medication-Ablated Future.
2. **Monitoring separation**: mandatory Monitoring-Mask-Only and physiological-value versus response-availability separation.
3. **Equal entitlement**: positive-only observed response, identical privileged support/sample mask, unsupported examples retained in the recommendation objective, and strictly pre-order student features/normalization.

Future killer controls also include Static Medication Response Prototype, Response Shuffle, richer Pre-Order Physiology, and Generic KD only when KD mechanics remain a plausible explanation.

Any simple matched control performing comparably to Proposed terminates the response-specific mechanism. Deployment leakage or unequal support invalidates the Gate. The protocol freezes practical/statistical rules for `materially`, `comparable`, and `≈` before training. No architecture, response-window, modality, subgroup, feature, favorable-seed, or split rescue follows those outcomes.

Canonical Idea and Gate-01 artifacts:

- [`ideas/007-privileged-physiological-response-supervision/`](ideas/007-privileged-physiological-response-supervision/)
- [`ideas/007-privileged-physiological-response-supervision/experiments/gate-01-protocol.md`](ideas/007-privileged-physiological-response-supervision/experiments/gate-01-protocol.md)
- [`ideas/007-privileged-physiological-response-supervision/experiments/gate-01-design-integrity-audit.md`](ideas/007-privileged-physiological-response-supervision/experiments/gate-01-design-integrity-audit.md)

## Claim boundary

Observed post-administration physiology may support a predictive response-associated representation under the historical care policy. It does not identify treatment effect, causal response, medication efficacy, therapeutic benefit, counterfactual outcome, clinical optimality, or individualized causal benefit.

## Latest completed empirical failures

### Event-Sourced Regimen Editing M0

Verdict:

`FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`.

`Change` and `D/C` raw workflow actions failed the frozen active-before consistency floors (`0.1723` and `0.1593` versus `0.70`). No model was trained.

### Medication Practice-Shift S0

Verdict:

`FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`.

The source-era predictor did not degrade on the target era; target-era Recall@5 was higher, and a medication-prior logit correction improved it further.

### Idea 006

Verdict:

`STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`.

A real exposure-state semantic existed, but the learned method failed against an equal-entitlement direct reranker.

These scoped failures constrain the current design but do not imply that future information, labs/vitals, or new models are universally useless.

## Routing

Current authorized terminal state:

```text
Idea 007 created/admitted
Gate 01 design frozen / implementability closed / independently audited
Training not authorized
STOP
```

No response-coverage run, Gate execution, or local training is authorized by this
state. A future execution transition must be explicit and must consume the audited
protocol unchanged.

## Quarantine

Until explicitly authorized by a later frozen claim-support protocol, do not inspect:

- MIMIC-IV G3/G4 future reserve;
- R0 Holdout;
- historical project test split.

## Navigation

- [Research-Space Reorientation](memory/research-space-reorientation.md)
- [Literature Opportunity Map](memory/literature-opportunity-map.md)
- [Current Privileged-Response Reset](memory/model-reset-20260908-privileged-physiological-response/)
- [Idea 007](ideas/007-privileged-physiological-response-supervision/)
- [Cross-Idea Memory](memory/README.md)
- [Reusable Lessons](memory/reusable-lessons.md)
- [Ideas Index](ideas/README.md)
