# Handoff: Medication-Transition Practice Shift Premise Admission

## Current state

Ideas 001--006 are terminated. The latest method route, Idea 006, ended at its frozen equal-entitlement Gate 01.

- **Idea 006 verdict**: `STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`
- **Idea 006 execution commit**: `3e51887a570bf8c4ef9503f7ffb852881c931130`
- **Idea 006 integrity audit**: `INTEGRITY_AUDIT_PASS`
- **Current active Idea**: none
- **Idea 007**: not created / not authorized
- **Current Stage**: `PRE_IDEA_PRACTICE_SHIFT_S0`
- **Selected reset premise**: `MEDICATION_TRANSITION_PRACTICE_SHIFT`
- **Paper objective**: first formal method paper, targeting at least a CCF-A Data/Mining/AI venue family
- **R0 Holdout**: quarantined / uninspected
- **Historical project test split**: untouched / uninspected

## Idea 006 closure

R0 remains valid: raw MIMIC-IV order/eMAR data established a material mismatch between hospitalization-level DDI pair co-membership and execution-confirmed temporal overlap.

Gate 01 nevertheless falsified the learned-method claim.

On frozen Dev at `K=5`:

| Method | Recall@5 | IncrementalExposureDDI@5 |
| --- | ---: | ---: |
| Base | 0.510442 | 0.098269 |
| DirectExposureRerank | 0.509797 | 0.087302 |
| ExposureConditional | 0.505470 | 0.074756 |

`ExposureConditional` reduced the operational DDI surrogate substantially, but its Recall@5 was lower than the equal-entitlement direct reranker by approximately `0.004327`, with 95% CI `[-0.005315, -0.003362]`. The preregistered method-admission condition required at least `+0.005` Recall@5 with CI lower bound above zero.

The route is therefore closed. Do not rescue it with a richer safety model, personalized risk network, new DDI source, dose/route, labs/vitals, LLM, subgroup mining, or a second backbone.

Formal closure:

- `research/ideas/006-exposure-conditional-medication-recommendation/research-decision.md`
- `research/memory/failures/exposure-conditioned-learning-gate-01--direct-control-sufficiency.md`

Reusable lesson:

> A new state/risk semantic can be empirically real without creating incremental learned-method value. New information semantics must survive direct-use controls before they support a learned method claim.

## Bounded post-Idea-006 reset

One non-safety research-space reset was performed with `ccf-literature-searcher / exploratory`.

Packet:

`research/memory/literature-search-20260908-medication-practice-shift/`

The search explicitly excluded Idea-006 safety rescue.

### Literature result

Current general MedRec increasingly reports MIMIC-III/MIMIC-IV/eICU results and sometimes describes eICU as cross-institutional generalization. A narrow schizophrenia medication recommender also reports real temporal and geographic validation degradation.

However, within the retained search, no close general MedRec method was found whose central question is:

> adapt a source-trained medication recommender to a later prescribing-practice environment while separating simple medication marginal-prior drift from residual conditional medication-transition shift.

This is a search-scoped opportunity, not a novelty proof.

Multi-dataset evaluation, temporal validation, external validation, order-time prediction, medication-frequency debiasing, and generic domain adaptation are not novelty claims.

## Why S0 is required before Idea 007

A future-period performance drop is scientifically trivial if it is mostly explained by changed medication frequencies.

Therefore the strongest simple null is tested before any adaptation method:

> A target-era per-medication logit-bias adjustment, estimated on patient-disjoint target-era adaptation patients, recovers most of the source-to-future degradation.

If that null is sufficient, the method-paper premise is terminated.

## S0 — only authorized local scientific execution

Protocol SSOT:

`research/memory/literature-search-20260908-medication-practice-shift/s0-practice-shift-admission-protocol.md`

S0 uses raw MIMIC-IV 3.1 and the already available leakage-safe medication-order task infrastructure.

It does **not** use DDI/safety as a scientific objective.

### Temporal groups

Only order bursts satisfying:

`year(decision_time) == patient.anchor_year`

are retained, so the burst's approximate real period is unambiguously the patient's `anchor_year_group`.

- `2008 - 2010` + `2011 - 2013`: source era
- `2014 - 2016`: target adaptation/evaluation era
- `2017 - 2019` + `2020 - 2022`: quarantined future reserve

### Source/target evidence hierarchy

Source era:

- SourceTrain 80%
- SourceTune 10%
- SourceAudit 10%

Target `2014 - 2016`:

- TargetPriorBuild 10%
- TargetBiasTune 10%
- TargetAudit 80%

All partitions are patient-disjoint by frozen subject-only hashes.

No model weights may train on target-era patients.

### Strong simple control

`TargetPriorBias` adjusts frozen SourceOnly logits by the smoothed medication-marginal logit difference between SourceTrain and TargetPriorBuild.

Only one scalar `alpha` is selected on TargetBiasTune from:

`{0.0, 0.25, 0.5, 1.0, 2.0}`.

TargetAudit is accessed only after the source checkpoint, target priors, alpha, metrics, and gate logic are frozen.

### Frozen PASS rule

S0 returns `PASS_S0_RESIDUAL_MEDICATION_PRACTICE_SHIFT` only if:

1. all cohort support floors pass;
2. source-to-target SourceOnly Recall@5 gap is at least `0.020`, with 95% CI lower bound above `0.010`;
3. TargetPriorBias recovers at most 50% of that gap;
4. residual Recall@5 gap after bias adjustment is at least `0.010`, with 95% CI lower bound above zero.

Otherwise:

`FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`.

## Routing

### S0 PASS

Stop local execution and return to `ccf-pipeline-orchestrator`.

Next:

1. `ccf-idea-optimizer` on the single practice-shift family;
2. strict `ccf-idea-reviewer` against generic fine-tuning/domain adaptation/continual learning;
3. Idea 007 may be created only if that review admits a genuine MedRec-specific method contribution.

Do not inspect the 2017--2022 future reserve, R0 Holdout, or historical test split.

### S0 FAIL

Return to:

`NO_HIGH_VALUE_DIRECTION_YET`.

Do not:

- change temporal groups;
- remove anchor-year matching;
- add diagnoses/procedures/labs/vitals;
- switch to eICU as a rescue;
- weaken the bias control;
- run S0b;
- create Idea 007.

## Next owner

Local repository Agent executes S0 exactly from the frozen protocol, followed by `ccf-integrity-auditor`.

No other scientific execution is authorized in the same run.
