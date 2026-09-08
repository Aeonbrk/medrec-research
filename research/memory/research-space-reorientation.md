<!-- markdownlint-disable MD013 -->

# Research-Space Reorientation

## Current workflow state

**Stage**: `PRE_IDEA_PRIVILEGED_RESPONSE_REQUIRED_REVISIONS`

**Paper objective**: first formal **method paper**, targeting at least a CCF-A Data/Mining/AI venue family. A genuinely new model is allowed. Pure benchmark/measurement work, indefinite diagnostics, and feature fishing are not acceptable terminal outcomes.

**Current active Idea**: none.

**Idea 007**: not created / not authorized.

**Current method family**: privileged physiological response supervision.

**Strict review verdict**: `ACCEPT_WITH_REQUIRED_REVISIONS_BEFORE_IDEA_007` (`3.89 / 5.00`).

**Next owner**: strict `ccf-idea-reviewer` after the bounded R1--R3 optimizer revision.

No local scientific execution is authorized. MIMIC-IV G3/G4 future groups, R0 Holdout, and the historical project test split remain quarantined.

## Cumulative failure landscape

### F1 — post-hoc same-information routes are compressed

Ideas 001--004 and EGSF showed that low-dimensional transformations/selectors over frozen information do not establish incremental value after strong controls.

### F2 — statistical structure is not clinical action semantics

Idea 005 found reproducible ATC output structure but failed therapeutic-substitution admission.

### F3 — equal information/rule entitlement is mandatory

EG-TER and Idea 006 require the strongest direct control to receive the same external rule/state/risk information as a learned method.

### F4 — certification is a separate burden

CRC-PS showed empirical feasibility does not imply finite-sample certifiability.

### F5 — medication cardinality is not normalized interaction propensity

B0 changed medication count without producing the required normalized-DDI trade-off.

### F6 — latent acceptable-treatment supervision is not identified

The selective-prescription-supervision reset could not distinguish hidden clinically valid alternatives from ordinary retrospective label uncertainty.

### F7 — new state semantics do not imply learned-method value

Idea 006 established a real exposure-state mismatch, but the learned method lost to an equal-entitlement direct reranker.

### F8 — chronology does not imply harmful deployment shift

S0 found no forward degradation; the later target era had higher Recall@5 than the source audit era, and medication-prior bias improved it further.

### F9 — workflow action labels do not automatically define regimen edits

M0 had abundant `New / Change / D/C` support, but the frozen pre-order state-consistency floors failed badly:

- `Change = 0.17228553254342177` active-before;
- `D/C = 0.15933081187948597` active-before;
- required floor: `0.70` for each.

No model was trained.

### F10 — privileged future access does not identify the semantics of the privileged signal

The 2026-09-08 strict privileged-response review did not empirically fail the direction. It established a pre-Idea admission constraint:

> future-only supervision may legally improve a causal-input student while the gain still comes from generic future-state regularization, medication identity/static prototypes, monitoring policy, or support/sample reweighting rather than the claimed response semantics.

The route therefore remains live only after matched mechanism-identification controls are frozen.

Record:

[`failures/privileged-response-preidea--response-specificity-not-yet-identified.md`](failures/privileged-response-preidea--response-specificity-not-yet-identified.md).

## Higher-order reusable constraints

### C1 — cosmetic post-hoc resurrection is closed

A new statistic/function over an already failed frozen information premise is not a new research direction.

### C2 — semantic admission precedes clinical interpretation

Therapeutic alternatives, hidden positives, treatment obligations, clinical appropriateness, or action semantics require independent evidence.

### C3 — direct-use sufficiency must be challenged first

A new signal/state semantic supports a learned method only if learning adds value beyond direct use of the same signal.

### C4 — certification follows mechanism evidence

Do not make guarantees the first novelty investment.

### C5 — separate count effects from normalized interaction propensity

Absolute pair burden can move mechanically with output size.

### C6 — admitted resource fact: hospitalization DDI co-membership is not current execution overlap

R0 remains reusable infrastructure/evidence, not the target paper.

### C7 — deployment adaptation requires actual degradation

Do not build adaptation because periods differ; first establish a material deployment loss.

### C8 — a new model must encode a new scientific object

Transformer/Mamba/GNN/point-process architectures are allowed only when they instantiate a new falsifiable decision object, supervision structure, state transition, or information flow.

### C9 — workflow labels must survive state-semantic admission

Action-like database fields cannot be promoted into state transitions merely because they are frequent and named `Change` or `D/C`.

### C10 — privileged-response semantics require subtraction, not only leakage safety

Strictly pre-order deployment is necessary but insufficient. A response-specific method claim must also show that its benefit depends on:

- focal-medication conditioning beyond generic future-state supervision;
- patient-medication-response correspondence beyond shuffle/static prototypes;
- physiological values beyond monitoring availability/frequency;
- equal support/sample entitlement rather than positive-event reweighting.

## Research-space boundary map

| Route / premise | Status | Evidence boundary | Reopen / advance condition |
| --- | --- | --- | --- |
| Frozen-output feature/routing families | `CLOSED` | Ideas 001--004 + EGSF | genuinely new information/objective |
| ATC sibling substitution | `CLOSED` | Idea 005 | new action resolution + admitted therapeutic semantics |
| Count-mediated safety/coverage | `CLOSED` | B0 | different mechanism |
| Selective prescription supervision | `NOT ADMITTED` | supervision reset | identifiable multi-valid target |
| Exposure-conditioned DDI learning | `CLOSED under Idea 006` | direct-control sufficiency | different safety target/action problem |
| Residual medication-practice adaptation | `CLOSED under S0` | no material forward degradation | actual degradation in a different deployment setting |
| Event-sourced `New/Change/D/C` regimen editing | `NOT ADMITTED under M0` | workflow/state inconsistency | independently valid action semantics / different decision object |
| Generic longitudinal modeling | `CROWDED / LOW PRIOR` | MR-DTR, DrugDoctor, HeteroMed, ChainCare | specific non-generic mechanism |
| Generic labs/vitals fusion | `CROWDED` | REFINE, ChainCare, HIFINet, MedGCN | different information-flow role |
| Joint MedRec + lab prediction | `PRIOR ART` | MedGCN; Bhoi et al. 2023 | response-specific mechanism beyond generic auxiliary learning |
| Knowledge distillation for MedRec | `PRIOR ART` | LEADER | different knowledge source + mechanism evidence |
| Training-time privileged multimodal distillation | `PRIOR ART outside MedRec` | OC-Distill + LUPI/KD | MedRec-specific scientific object |
| Generic future-observation distillation | `PRIOR ART outside MedRec` | Privileged Foresight Distillation 2026 | future access itself cannot carry novelty |
| **Privileged physiological response supervision** | **`REQUIRED REVISIONS BEFORE IDEA 007`** | strict review 2026-09-08 | freeze R1 medication specificity, R2 monitoring separation, R3 equal-support/deployment contract, then re-review |

`CLOSED` is conditional on the recorded premise, not a universal ban on the noun.

## Current selected method family

Packet:

[`model-reset-20260908-privileged-physiological-response/`](model-reset-20260908-privileged-physiological-response/).

Strict review:

[`model-reset-20260908-privileged-physiological-response/idea-review.md`](model-reset-20260908-privileged-physiological-response/idea-review.md).

Closest-work provenance:

[`model-reset-20260908-privileged-physiological-response/closest-work-review.md`](model-reset-20260908-privileged-physiological-response/closest-work-review.md).

### Problem

Physiological evidence observed after medication administration can be informative about the joint patient/treatment context, but it is unavailable at medication decision time and is observationally confounded.

### Surviving insight

Use future post-administration physiology only as **privileged training supervision**. A teacher learns a response-associated patient-medication representation from realized treatment context and post-administration monitoring. A deployable student must anticipate that representation from strictly pre-order state and candidate medication.

The scientific contribution survives closest-work subtraction only if the paired physiological **values** create incremental medication-specific information beyond generic future supervision and monitoring policy.

### Non-causal boundary

Observed post-administration physiology is not an individual medication effect. It may reflect severity, co-medications, procedures, fluids, ventilation, dose/route, clinician actions, spontaneous progression, monitoring policy, and selective measurement.

Use `response-associated signature`, not `treatment effect`, `efficacy`, `benefit`, or `counterfactual outcome`.

### Required pre-Idea revisions (frozen by the bounded optimizer pass)

1. **Medication specificity**: matched Generic Future-State Auxiliary / Medication-Ablated Future control.
2. **Monitoring separation**: Monitoring-Mask-Only plus physiology-value versus response-availability separation.
3. **Equal entitlement**: positive-only observed response, same support/sample mask across privileged variants, unsupported examples retained in the recommendation objective, and strictly pre-order student features/normalization.

No experiment is authorized during this revision cycle.

### Future Gate 01 kill conditions after admission only

If later admitted, terminate the response-specific family if any of the following occurs:

- GenericFutureAux or MedicationAblatedFuture performs comparably;
- ResponseShuffle performs comparably;
- MonitoringMaskOnly performs comparably;
- StaticResponsePrototype performs comparably;
- richer pre-order physiology performs comparably;
- response support is insufficient or materially concentrated;
- deployment leakage or unmatched support/reweighting is detected.

No architecture rescue follows these outcomes under the same Idea.

## Publication boundary

This strict review result is not an Idea and not publication evidence. The first paper remains method-first.

Next owner: strict `ccf-idea-reviewer`.

Idea 007 may be created only after a later explicit `ACCEPT_TO_CREATE_IDEA_007` verdict. No local Agent run or response-coverage research stage is authorized now.
