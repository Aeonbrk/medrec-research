# Paper Evaluator Specification

Version: `1.0`
Status: `CURRENT CORE EVALUATOR CONTRACT`
Effective date: `2026-09-17`

This specification defines common metric semantics for paper-facing Medication Recommendation experiments. Dataset-specific benchmark profiles bind the exact eligible example set, vocabulary, target mapping, and feedback status.

## 1. Evaluation unit and eligibility

The atomic prediction unit is one benchmark-declared eligible visit. The independent split unit is the patient.

A dataset profile must state:

- whether first visits are eligible;
- the exact recommendation-example rule;
- whether visits with empty mapped targets are excluded from recommendation evaluation and whether they remain in longitudinal history;
- the exact patient/visit membership identity or public-safe digest;
- the target vocabulary and any projection rule.

Do not change sample eligibility after observing Test results.

Patients with zero eligible evaluation visits are excluded from patient-macro denominators and their count must be reported.

For the current MIMIC-IV native materialization, visits without a mapped medication target remain available in the chronological prefix but are not recommendation examples. For the current common-131 projection, projected-empty recommendation targets are excluded from recommendation examples but the underlying visits remain part of chronology. These are benchmark-task definitions, not model-specific filters.

## 2. Prediction representation

For each eligible visit, a method must emit:

- a deterministic medication set for set metrics; and
- when PRAUC/AP is reported, one finite continuous score per declared output medication.

The continuous score need not be a calibrated probability. It must be a predeclared medication-ranking score whose semantics are stable across Dev and Test.

Duplicate predicted medications are removed by the method/decoder before evaluation; duplicate emission is an implementation error when the declared decoder requires uniqueness.

## 3. Primary accuracy metric: patient-macro Jaccard

For target set `T` and prediction set `P` at one visit:

```text
Jaccard = |P intersection T| / |P union T|
```

Edge cases:

- both `P` and `T` empty: `1.0`;
- exactly one empty: `0.0`.

For each patient, average Jaccard over that patient's eligible visits. Then average those patient means equally across eligible patients.

Patient-macro is chosen so each eligible patient receives equal weight. Patient-level splitting or bootstrap does not mathematically force patient-macro; visit-macro is reported separately as a different estimand.

## 4. F1

At each visit:

```text
precision = |P intersection T| / |P|
recall    = |P intersection T| / |T|
F1        = 2 * precision * recall / (precision + recall)
```

Edge cases:

- both sets empty: precision = recall = F1 = `1.0`;
- one set empty: precision = recall = F1 = `0.0`.

Primary F1 uses the same patient-macro aggregation as Jaccard. Visit-macro F1 is supplementary.

## 5. PRAUC / average precision

Project metric label `PRAUC` means per-visit **average precision** over the declared medication output space using the method's continuous medication scores and binary target vector.

For each eligible visit:

1. evaluate average precision over all declared medication coordinates;
2. average visit AP within each patient;
3. average equally across eligible patients.

Visit-macro AP is supplementary.

If a method cannot produce a predeclared continuous medication score with stable semantics, report PRAUC/AP as unsupported rather than inventing a score after observing results.

Do not interpret PRAUC/AP as probability calibration. NLL or calibration claims require probability semantics that support those quantities.

## 6. Medication count

For each visit, predicted medication count is `|P|`; target medication count is `|T|`.

Paper-facing `AvgMed` uses the same patient weighting as primary accuracy:

1. average visit counts within each patient;
2. average equally across eligible patients.

Target AvgMed is a benchmark reference and can be reported once per benchmark rather than repeated in every method row.

## 7. DDI rate

Primary DDI is the pooled predicted-pair rate over eligible visits.

For every predicted set, enumerate each unique unordered pair of distinct medications exactly once. Self-pairs are excluded.

```text
DDI rate = total predicted interacting unordered pairs
           / total predicted unordered medication pairs
```

If the denominator is zero over the entire evaluation population, DDI rate is defined as `0.0` and the report must also show `predicted_pair_count = 0`.

For patient-cluster bootstrap, recompute the pooled numerator and denominator from the resampled patients; do not average precomputed global DDI ratios.

Patient-macro DDI may be reported as a supplementary estimand, with the same zero-pair convention stated explicitly.

DDI is an interaction proxy. It does not establish treatment safety, clinical benefit, or causality.

## 8. Vocabulary, OOV, and zero-support coordinates

A benchmark profile defines the output vocabulary before evaluation.

- A target token outside the declared vocabulary is a benchmark/profile error unless the benchmark explicitly defines a deterministic projection that removes or maps it before the target set is formed.
- Dropped/projected target counts must be reported by the benchmark profile.
- Output coordinates with zero positive support remain part of the declared output space if the benchmark profile includes them. They are not silently removed after results are observed.
- Predicting a zero-support coordinate counts as a false positive under set metrics.
- Per-visit AP/PRAUC uses the full declared output space, including zero-support coordinates, unless the benchmark profile was frozen with a different rule before model evaluation.

The MIMIC-IV common-131 surface currently retains two canonical zero-support medication coordinates. Their existence must remain explicit in any paper-facing common-131 profile.

## 9. Visit-macro supplementary metrics

For visit-macro Jaccard/F1/PRAUC, each eligible visit contributes one equal-weight metric value regardless of patient visit count.

Visit-macro and patient-macro answer different estimands. Neither should be substituted post hoc because it gives a more favorable ranking.

## 10. Joint Dev selection evaluator

The same metric implementation used for paper reporting must be used in Dev checkpoint/operating-point selection.

For each predeclared validation checkpoint and operating point:

- produce predictions with the frozen decoder rule;
- compute Dev patient-macro Jaccard;
- apply the joint selection and tie-break procedure defined in `PAPER_EXPERIMENT_CONTRACT.md`.

Do not select a checkpoint with one aggregation and report a different aggregation as if it were the selection target.

## 11. Synthetic evaluator checks

Before a new evaluator implementation is admitted for paper-facing use, verify a small deterministic synthetic fixture covering at least:

- exact set match;
- disjoint non-empty sets;
- empty prediction;
- both sets empty;
- multi-visit patients with unequal visit counts to distinguish patient-macro from visit-macro;
- duplicate-pair prevention and zero DDI denominator;
- continuous-score ranking for AP/PRAUC;
- OOV rejection and zero-support-coordinate handling.

These checks verify metric implementation only. They do not validate a model or benchmark.

## 12. Dataset-profile requirements before final-table use

A benchmark is not paper-final merely because this core evaluator is frozen. Its paper-facing profile must also record:

- eligible patients/visits and membership identity;
- target mapping/projection and OOV counts;
- first-visit policy;
- empty-target policy;
- output vocabulary and zero-support coordinates;
- DDI matrix identity/coverage;
- feedback history status;
- whether cross-population patient/record overlap is known, absent, present, or unknown.
