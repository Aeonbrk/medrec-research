<!-- markdownlint-disable MD013 -->

# Research-Space Reorientation

## Current workflow state

**Stage**: `IDEA_007_GATE_01_DESIGN_FROZEN_AUDITED_TRAINING_NOT_AUTHORIZED`

**Paper objective**: first formal **method paper**, targeting at least a CCF-A Data/Mining/AI venue family. A genuinely new model is allowed. Pure benchmark/measurement work, indefinite diagnostics, and feature fishing are not acceptable terminal outcomes.

**Current active Idea**: `007-privileged-physiological-response-supervision`.

**Idea 007**: created/admitted.

**Current method family**: privileged physiological response supervision.

**Strict re-review verdict**: `ACCEPT_TO_CREATE_IDEA_007` (`4.17 / 5.00`, medium-high confidence).

**Admission/design owners**: `ccf-pipeline-orchestrator` (admission complete) ->
`ccf-experiment-designer` (teacher-objective domain closed; exact V7 Generic
Pre-Order KD frozen) -> `ccf-integrity-auditor` (`DESIGN_INTEGRITY_PASS`) ->
`ccf-pipeline-orchestrator` (next owner).

No local scientific execution or training is authorized by the current state.
MIMIC-IV G3/G4 future groups, R0 Holdout, and the historical project test split
remain quarantined.

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

### F10 — privileged future access does not identify privileged semantics

A future-only clinical signal may be a legal predictive target while the gain still comes from generic future-state regularization, medication identity/static prototypes, monitoring policy, or positive-event sample weighting.

This remains a reusable rule rather than an unresolved blocker. The current R1--R3 contract now supplies the prospective subtraction required to test it.

Record:

[`failures/privileged-response-preidea--response-specificity-not-yet-identified.md`](failures/privileged-response-preidea--response-specificity-not-yet-identified.md).

## Higher-order reusable constraints

### C1 — cosmetic post-hoc resurrection is closed

A new statistic/function over an already failed frozen information premise is not a new research direction.

### C2 — semantic admission precedes clinical interpretation

Therapeutic alternatives, hidden positives, treatment obligations, clinical appropriateness, or action semantics require independent evidence.

### C3 — direct-use or semantic-ablation sufficiency must be challenged first

A new signal/state semantic supports a learned method only if the proposed mechanism adds value beyond the strongest equal-entitlement direct use or semantic-ablation control available for that information-flow setting.

### C4 — certification follows mechanism evidence

Do not make guarantees the first novelty investment.

### C5 — separate count effects from normalized interaction propensity

Absolute pair burden can move mechanically with output size.

### C6 — hospitalization DDI co-membership is not current execution overlap

R0 remains reusable infrastructure/evidence, not the target paper.

### C7 — deployment adaptation requires actual degradation

Do not build adaptation because periods differ; first establish a material deployment loss.

### C8 — a new model must encode a new scientific object

Transformer/Mamba/GNN/point-process architectures are allowed only when they instantiate a new falsifiable decision object, supervision structure, state transition, or information flow.

### C9 — workflow labels must survive state-semantic admission

Action-like database fields cannot be promoted into state transitions merely because they are frequent and named `Change` or `D/C`.

### C10 — privileged-response semantics require subtraction, not only leakage safety

Strictly pre-order deployment is necessary but insufficient. A response-specific method claim must show that its benefit depends on:

- focal-medication conditioning beyond generic future-state supervision;
- patient-medication-response correspondence beyond shuffle/static prototypes;
- physiological values beyond monitoring availability/frequency;
- equal support/sample entitlement rather than positive-event reweighting;
- privileged future-response information beyond ordinary pre-order KD mechanics.

The current bounded optimizer revision now freezes these requirements strongly enough for Idea admission.

## Research-space boundary map

| Route / premise | Status | Evidence boundary | Reopen / advance condition |
| --- | --- | --- | --- |
| Frozen-output feature/routing families | `CLOSED` | Ideas 001--004 + EGSF | genuinely new information/objective |
| ATC sibling substitution | `CLOSED` | Idea 005 | new action resolution + admitted therapeutic semantics |
| Count-mediated safety/coverage | `CLOSED` | B0 | different mechanism |
| Selective prescription supervision | `NOT ADMITTED` | supervision reset | identifiable multi-valid target |
| Exposure-conditioned DDI learning | `CLOSED under Idea 006` | direct-control sufficiency | different safety target/action problem |
| Residual temporal-practice adaptation | `CLOSED under S0` | no material forward degradation | actual degradation in a different deployment setting |
| Event-sourced `New/Change/D/C` regimen editing | `NOT ADMITTED under M0` | workflow/state inconsistency | independently valid action semantics / different decision object |
| Generic longitudinal modeling | `CROWDED / LOW PRIOR` | MR-DTR, DrugDoctor, HeteroMed, ChainCare | specific non-generic mechanism |
| Generic labs/vitals fusion | `CROWDED` | REFINE, ChainCare, HIFINet, MedGCN | different information-flow role |
| Joint MedRec + lab prediction | `PRIOR ART` | MedGCN; Bhoi et al. 2023 | response-specific mechanism beyond generic auxiliary learning |
| Knowledge distillation for MedRec | `PRIOR ART` | LEADER; IJCAI-ECAI 2026 dual-channel KD | different knowledge source + mechanism evidence |
| Training-time privileged clinical modalities | `PRIOR ART outside MedRec` | OC-Distill and broader LUPI/KD | MedRec-specific scientific object |
| Clinical future-information teacher → history-only student | `PRIOR ART outside MedRec` | 2026 future-aware blood-glucose forecasting | future access itself cannot carry novelty |
| Generic future-observation distillation | `PRIOR ART outside MedRec` | Privileged Foresight Distillation 2026 | future access itself cannot carry novelty |
| Medication-aware physiological-response representation | `PRIOR ART outside general MedRec` | Wu et al. EMBC 2025 | response-supervision role + MedRec-specific evidence |
| **Privileged physiological response supervision** | **`IDEA 007 ACTIVE / OBJECTIVE DOMAIN CLOSED / V7 EXECUTABLE / AUDITED`** | strict re-review 2026-09-09; protocol and audit in `research/ideas/007-privileged-physiological-response-supervision/` | next owner `ccf-pipeline-orchestrator`; stop before training; any execution requires separate explicit authorization |

`CLOSED` is conditional on the recorded premise, not a universal ban on the noun.

## Current admitted method family: Idea 007

Packet:

[`model-reset-20260908-privileged-physiological-response/`](model-reset-20260908-privileged-physiological-response/).

Canonical Idea-007 protocol and audit:

[`../ideas/007-privileged-physiological-response-supervision/`](../ideas/007-privileged-physiological-response-supervision/),
[`../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-protocol.md`](../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-protocol.md),
and
[`../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-design-integrity-audit.md`](../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-design-integrity-audit.md).

Strict review:

[`model-reset-20260908-privileged-physiological-response/idea-review.md`](model-reset-20260908-privileged-physiological-response/idea-review.md).

Closest-work provenance:

[`model-reset-20260908-privileged-physiological-response/closest-work-review.md`](model-reset-20260908-privileged-physiological-response/closest-work-review.md).

### Problem

Physiological evidence observed after medication administration can be informative about the joint patient/treatment context, but it is unavailable at medication decision time and is observationally confounded.

### Admitted insight

Use future post-administration physiology only as **privileged training supervision**. A teacher learns a response-associated patient-medication representation from realized treatment context and post-administration monitoring. A deployable student must anticipate that representation from strictly pre-order state and candidate medication.

The scientific contribution survives closest-work subtraction only if paired physiological **values** create incremental medication-specific information beyond generic future supervision and monitoring policy.

### R1--R3 admission contract

1. **Medication specificity**: matched Generic Future-State Auxiliary / Medication-Ablated Future.
2. **Monitoring separation**: Monitoring-Mask-Only plus physiology-value versus response-availability separation.
3. **Equal entitlement**: positive-only observed response, same support/sample mask across privileged variants, unsupported examples retained in the recommendation objective, and strictly pre-order student features/normalization.

### Gate 01 kill conditions

Terminate the response-specific family if any of the following occurs:

- GenericFutureAux or MedicationAblatedFuture performs comparably;
- ResponseShuffle performs comparably;
- MonitoringMaskOnly performs comparably;
- StaticResponsePrototype performs comparably;
- richer pre-order physiology performs comparably;
- response support is insufficient or materially concentrated;
- deployment leakage or unmatched support/reweighting is detected.

No architecture, response-window, modality, subgroup, post-hoc feature, favorable
seed, split, or response-definition rescue follows these outcomes under the same
Idea.

The audited protocol operationalizes `materially` / `comparable` / `≈` with fixed
practical and statistical rules before training. An inconclusive interval is also
a stop; it cannot be rescued by changing the threshold.

### Non-causal boundary

Observed post-administration physiology is not an individual medication effect. It may reflect severity, co-medications, procedures, fluids, ventilation, dose/route, clinician actions, spontaneous progression, treatment timing, monitoring policy, and selective measurement.

Use `response-associated signature`, not treatment-effect, efficacy, therapeutic-benefit, counterfactual, clinical-optimality, or individualized-causal-benefit language.

## Publication boundary

This admission is not an empirical result and not publication evidence. The first paper remains method-first.

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
