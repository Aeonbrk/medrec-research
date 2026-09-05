# Handoff: Exposure-Localized Safety Resource Admission

## Current state

The project completed Ideas 001--005, B0 Cardinality Attribution, and the rejected selective-prescription-supervision reset. A new resource-level reset has now identified one method-capable route that survives literature/optimizer/reviewer scrutiny **conditionally on raw-data admission**.

- **Previous Idea**: `005-safety-substitution-structure`
- **Previous Idea Status**: `TERMINATED / STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`
- **B0**: `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`
- **Rejected post-B0 seed**: selective prescription supervision / trajectory-privileged negative reliability
- **Current Stage**: `RESOURCE_ADMISSION_R0`
- **Selected resource route**: exposure-localized medication safety at provider order time
- **Paper Objective**: first formal method paper, targeting at least a CCF-A venue family
- **Current Active Idea**: none
- **Idea 006**: not created; creation is conditional on R0 PASS
- **Resource-reset folder**: `research/memory/resource-reset-20260905-exposure-localized-safety/`
- **R0 Protocol**: `research/memory/resource-reset-20260905-exposure-localized-safety/r0-resource-admission-protocol.md`
- **Strict pre-Idea review**: `ACCEPT_TO_DEVELOP / RESOURCE_ADMISSION_REQUIRED`, weighted score `4.04/5`
- **Existing project test split**: untouched and not authorized

## Why this reset is different

The route does not add another feature to the current 131-label visit-level benchmark.

It changes the scientific resource and the safety semantics:

> At a provider medication-order decision point, condition DDI pressure on the medications that are execution-confirmed and currently active before that order, rather than treating every medication that appears anywhere in the hospitalization as simultaneously relevant.

The new resource is raw MIMIC-IV medication request/order plus medication-administration data:

- `prescriptions` / `pharmacy` / `poe` for provider medication requests/orders;
- `emar` / `emar_detail` for actual medication administration.

MIMIC-IV explicitly separates requested medications from administered medications and supplies medication/order linkage fields. Clinical DDI decision-support literature independently shows that concomitant exposure, administration timing, stopped-medication status, and other context can change whether a pairwise DDI alert is applicable.

This route therefore changes **risk-state semantics**, not merely model architecture.

## What is already prior art

Do not claim any of the following as novelty:

- medication prediction at provider order time;
- pre-order-only causal masking;
- generic temporal EHR modeling;
- static DDI regularization;
- ATC-L4 or ingredient-level medication granularity;
- contextual DDI alerting in clinical decision support.

Rough et al. (2020) already predict inpatient medication orders from the EHR available before each order event. SafeDrug/KATMed/HeteroMed and related methods already provide static or rule-conditioned safety objectives. SafeRx-Agent/GRAIN/RxEval already increase action granularity.

The only currently defensible novelty delta is the interaction:

> **order-time medication recommendation whose DDI optimization is conditioned on a pre-order, execution-confirmed active medication state, with the same exposure-risk signal also given to direct reranking/filtering controls.**

This delta remains provisional until R0 passes and a final pre-Idea closest-work check is performed.

## Strict review result

`ACCEPT_TO_DEVELOP / RESOURCE_ADMISSION_REQUIRED`

Weighted score: `4.04 / 5.00`.

Development potential: high.

Current conference readiness: medium-low because the raw MIMIC-IV resource and premise have not yet been admitted.

The decisive reviewer risks are:

1. the raw order/eMAR linkage or medication normalization may be too incomplete or costly;
2. static visit-union DDI may not differ materially from execution-confirmed overlap in this cohort;
3. the eventual method may collapse to `Rough 2020 + dynamic SafeDrug loss`;
4. a direct exposure-aware scalar reranker or hard filter may absorb the entire gain.

The third and fourth risks are method-stage gates. R0 handles only the first two.

## R0 — only authorized local execution

Run exactly:

`R0 — Exposure Resource & Premise Admission`

Protocol SSOT:

`research/memory/resource-reset-20260905-exposure-localized-safety/r0-resource-admission-protocol.md`

R0 must not train a recommender.

It must:

1. verify local raw MIMIC-IV table availability and version;
2. immediately create the frozen patient-level Discovery/Dev/Holdout split from `subject_id` only;
3. use Discovery only for all scientific R0 aggregates;
4. establish deterministic order-to-administration linkage and medication normalization;
5. quantify eMAR-observed visit-union DDI episodes versus execution-confirmed overlapping DDI episodes;
6. apply the frozen R0 decision floors without post-result relaxation;
7. commit only aggregate public-safe artifacts.

The new Holdout is quarantined before hypothesis-selection experiments. Holdout membership may be assigned, but Holdout clinical/event aggregates are not inspected in R0.

This does not authorize any access to the existing project's untouched test split.

## Routing

### If R0 passes

Record:

`PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE`

Then:

1. return to `ccf-pipeline-orchestrator`;
2. perform one final closest-work delta check;
3. create Idea 006 around exposure-conditional medication recommendation;
4. run `ccf-experiment-designer` before any model training;
5. Gate 01 must pit end-to-end exposure-conditioned learning against the same exposure-risk signal used as a direct scalar reranker and hard filter.

R0 PASS does not authorize Holdout/test evaluation.

### If R0 fails

Record:

`FAIL_R0_EXPOSURE_RESOURCE_OR_PREMISE`

Then return to:

`NO_HIGH_VALUE_DIRECTION_YET`

Do not:

- relax mapping/mismatch floors;
- hand-curate a small medication subgroup;
- substitute inferred timing for missing eMAR only to save the route;
- add richer labs/vitals to rescue it;
- start R1/R2;
- create Idea 006.

## Publication boundary

Even if R0 passes, the eventual paper may claim only what its evidence supports. eMAR administration is not proof of clinical appropriateness. Execution-confirmed DDI overlap is an operational exposure surrogate, not an ADE label.

A CCF-A method paper would ultimately need:

- a leakage-safe order-time task;
- a simple architecture-agnostic exposure-conditioned mechanism;
- direct exposure-aware reranker/filter controls with equal DDI entitlement;
- matched-risk comparisons;
- more than one materially different predictor family;
- no clinical-safety overclaim;
- untouched claim-support evidence after hypothesis selection.

## Next owner

Local repository Agent executes R0 exactly from the frozen protocol.

No other experiment, model, Idea creation, or literature expansion is authorized in the same run.
