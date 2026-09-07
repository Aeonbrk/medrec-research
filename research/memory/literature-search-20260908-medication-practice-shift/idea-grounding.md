<!-- markdownlint-disable MD013 -->

# Idea Grounding — Medication-Transition Practice Shift

## Current verdict

`PROMISING_PREMISE / NOT_READY_FOR_IDEA_007`

The literature gap is sufficiently specific to justify one project-local premise gate, but not yet sufficient to create a method Idea.

## Problem candidate

Medication recommendation is usually evaluated under random patient splits or by training/evaluating separately on several EHR datasets. Real deployment instead faces a forward shift in prescribing practice, medication marginals, workflow, and medication-transition behavior.

The method-capable question is not:

> Does performance change over time?

That phenomenon is already plausible and narrow temporal/external validation evidence exists.

The question that could support a method is:

> **Does a medication recommender face residual forward conditional shift after the strongest trivial explanation — changed medication marginal frequencies — is given a fair opportunity to adapt?**

## Why this is independent of Idea 006

Idea 006 asked whether a known active-exposure DDI signal requires end-to-end learning. It failed because direct use of the same signal preserved more medication fidelity.

The current candidate:

- has no DDI objective;
- does not optimize safety;
- does not reuse the failed exposure-conditioned loss;
- treats calendar/practice environment as the changed resource;
- asks about prediction robustness/adaptation under future prescribing behavior.

The existing order/eMAR pipeline is reusable infrastructure only.

## Source-supported facts

1. MIMIC-IV provides `anchor_year_group` specifically to enable analyses of changes in medical practice over time.
2. HypeMed, KATMed, Rx-Expert, and NLA-MMR show that multi-dataset evaluation is already a crowded claim space.
3. KATMed explicitly recognizes cross-hospital practice-pattern/case-mix/coding variation.
4. A narrow schizophrenia medication recommender shows material temporal/geographic degradation under actual external validation.
5. DMRNet establishes medication-frequency skew as a meaningful MedRec confound.
6. Recent critical appraisal in JBI makes patient-level and temporal leakage a direct validity concern for MedRec.

## Search-scoped inference

No retained close work makes the following interaction its central general-MedRec method problem:

```text
source-era causal medication model
        ↓
future prescribing environment
        ↓
separate marginal medication-prior shift
from residual conditional medication-transition shift
        ↓
adapt only if the residual is material
```

This is an inference from the retained search, not a universal literature claim.

## Strongest simple explanation

Before designing any adaptation network, test:

> The apparent future degradation is mostly a medication-label marginal shift; a per-medication logit-bias adjustment estimated from a small patient-disjoint target-era adaptation cohort recovers most of it.

This is the killer control for premise admission.

If that control recovers at least half of the source-to-future gap or leaves no material residual gap, terminate the route.

## Why order-time data is used

The existing Idea-006 raw MIMIC-IV infrastructure provides a leakage-safe, high-volume medication-order decision task without relying on current-hospitalization discharge-coded diagnoses/procedures.

Using it here is an infrastructure reuse decision, not a novelty claim.

The temporal gate must not use DDI/eMAR active-exposure information as a scientific feature. The common predictor may retain the already-frozen medication-order history representation, but the current question is prediction shift, not safety.

## Required local evidence before Idea creation

One bounded gate, `S0 — Medication Practice-Shift Admission`, must establish all of the following:

1. source-era and target-era cohorts are large enough under a conservative MIMIC-IV temporal assignment;
2. a source-trained model suffers a material forward Recall@5 degradation;
3. the degradation remains material after a target-era medication-prior/logit-bias control estimated from a disjoint adaptation cohort;
4. later periods remain quarantined for future claim support;
5. no DDI/safety or architecture search is used to rescue the premise.

## Possible method space only if S0 passes

A future optimizer may consider separating:

- stable patient/medication-transition representation;
- environment-specific prescribing-practice adaptation.

But it must reject any candidate that is merely:

- generic fine-tuning;
- generic domain adversarial training;
- generic continual learning;
- a learned medication bias that cannot beat the frozen bias-only control.

Expected later killer baselines include source-only, target-prior bias adjustment, last-layer/adapter tuning, and full fine-tuning with matched target labels.

No such method is authorized now.

## Stop boundary

S0 is the only authorized empirical premise test for this reset.

- `PASS_S0_RESIDUAL_MEDICATION_PRACTICE_SHIFT` -> `ccf-idea-optimizer`.
- `FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT` -> `NO_HIGH_VALUE_DIRECTION_YET`.

A failure does not authorize another temporal feature, a different time split, an eICU rescue, or Idea 007.
