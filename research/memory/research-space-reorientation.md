<!-- markdownlint-disable MD013 -->

# Research-Space Reorientation

## Current workflow state

**Stage**: `PRE_IDEA_PRIVILEGED_RESPONSE_OPTIMIZATION`

**Paper objective**: first formal **method paper**, targeting at least a CCF-A Data/Mining/AI venue family. A genuinely new model is allowed. Pure benchmark/measurement work, indefinite diagnostics, and feature fishing are not acceptable terminal outcomes.

**Current active Idea**: none.

**Idea 007**: not created / not authorized.

**Current method family**: privileged physiological response supervision.

**Next owner**: strict `ccf-idea-reviewer` after completed optimizer formulation.

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

Failure memory: [`failures/event-sourced-regimen-editing-m0--workflow-action-state-inconsistency.md`](failures/event-sourced-regimen-editing-m0--workflow-action-state-inconsistency.md).

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

## Research-space boundary map

| Route / premise | Status | Evidence boundary | Reopen / advance condition |
| --- | --- | --- | --- |
| Frozen-output feature/routing families | `CLOSED` | Ideas 001--004 + EGSF | genuinely new information/objective |
| ATC sibling substitution | `CLOSED` | Idea 005 | new action resolution + admitted therapeutic semantics |
| Count-mediated safety/coverage | `CLOSED` | B0 | different mechanism |
| Selective prescription supervision | `NOT ADMITTED` | supervision reset | identifiable multi-valid target |
| Exposure-conditioned DDI learning | `CLOSED` | Idea 006 | different safety target/action problem |
| Residual medication-practice adaptation | `CLOSED` | S0 | actual material degradation in a different deployment setting |
| Event-sourced `New/Change/D/C` regimen editing | `NOT ADMITTED` | M0 | independently valid action semantics / different decision object |
| Generic longitudinal modeling | `CROWDED / LOW PRIOR` | MR-DTR, DrugDoctor, HeteroMed, ChainCare | specific non-generic mechanism |
| Generic labs/vitals fusion | `CROWDED` | REFINE, ChainCare, HIFINet, MedGCN | different information-flow role |
| Generic KD in MedRec | `PRIOR ART` | LEADER | different knowledge source + mechanism evidence |
| **Privileged physiological response supervision** | **`SELECTED FOR STRICT REVIEW`** | current optimizer reset | reviewer admits novelty/soundness/evidence feasibility |

`CLOSED` is conditional on the recorded premise, not a universal ban on the noun.

## Current selected method family

Packet:

[`model-reset-20260908-privileged-physiological-response/`](model-reset-20260908-privileged-physiological-response/).

### Problem

Physiological evidence observed after medication administration can be informative about the joint patient/treatment context, but it is unavailable at medication decision time and is observationally confounded.

### Optimized insight

Use future post-administration physiology only as **privileged training supervision**. A teacher learns a response-associated patient–medication representation from realized treatment context and post-administration monitoring. A deployable student must anticipate that representation from strictly pre-order state and candidate medication.

Future monitoring never enters inference.

### Closest-work subtraction

The route does not claim novelty from labs, response modeling, event chains, auxiliary lab prediction, or knowledge distillation individually. REFINE, ChainCare, MedGCN, DrugDoctor, LEADER, OC-Distill, and physiological-response representation work already cover those primitives.

The search-scoped residual delta is:

> medication-in-context post-administration physiology as training-only privileged supervision for a causal pre-order candidate-medication student, with mechanism controls proving that response semantics matter beyond generic future-state regularization.

### Non-causal boundary

Observed post-administration physiology is not an individual medication effect. It may reflect severity, co-medications, procedures, fluids, monitoring policy, and selective measurement.

Use `response-associated signature`, not `treatment effect`, `efficacy`, or `causal response`.

### Mandatory future killer controls

Any Gate 01 admitted after strict review must include:

- same-input causal Base;
- Base + pre-order physiology;
- capacity-matched generic future-state auxiliary learning;
- static medication response prototype;
- response-shuffle/misalignment control;
- compatible monitoring-aware MedRec baselines;
- KD-mechanics control where needed.

If generic future-state learning or shuffled responses explain the gain, terminate the mechanism rather than add architecture.

## Publication boundary

This optimizer result is not an Idea and not publication evidence. The first paper remains method-first.

Next owner: `ccf-idea-reviewer`.

Idea 007 may be created only if strict review admits the residual method delta and evidence path. No local Agent run or response-coverage research stage is authorized before that review.
