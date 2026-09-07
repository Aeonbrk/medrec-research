# Handoff: Idea 006 — Exposure-Conditional Medication Recommendation

## Current state

The project has completed Ideas 001--005, B0 Cardinality Attribution, the rejected selective-prescription-supervision reset, and the exposure-localized resource reset.

- **R0**: `PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE`
- **R0 execution commit**: `ea134b7e75583186242bc72bc71eb2975b812edc`
- **Final closest-work verdict**: `NOVELTY_DELTA_SURVIVES_FOR_IDEA_CREATION`
- **Current Stage**: `IDEA_006_GATE_01`
- **Current Active Idea**: `006-exposure-conditional-medication-recommendation`
- **Idea review**: `ACCEPT_TO_DEVELOP / SELECT_FOR_GATE_01_ONLY`, weighted score `4.30/5`
- **Paper Objective**: first formal method paper, targeting at least a CCF-A Data/Mining/AI venue family; likely 2027 cycle, final venue not frozen
- **Gate 01 protocol**: `research/ideas/006-exposure-conditional-medication-recommendation/experiments/gate-01-exposure-conditioned-learning.md`
- **R0 Dev**: authorized for one frozen Gate-01 outer evaluation only
- **R0 Holdout**: quarantined and not authorized
- **Existing project test split**: untouched and not authorized

## R0 evidence now admitted

R0 used raw MIMIC-IV 3.1 Discovery only and passed all seven frozen resource/premise floors.

Key project-local evidence:

- order normalization coverage: 81.9248%;
- administration normalization coverage: 81.8875%;
- shared vocabulary: 131 ATC-L4 concepts, 91 represented in the frozen DDI asset;
- eMAR-observed visit-union DDI episodes: 1,050,523;
- execution-confirmed overlapping episodes: 829,366;
- static-only episodes: 221,157;
- `static_only_fraction = 21.0521%`;
- 391 unique DDI relations and 68,695 contributing patients;
- 280 relations each contribute at least 20 static-only episodes;
- strictly pre-order execution-confirmed medication state: feasible;
- integrity audit: `PASS_ALL_AUDITS`.

R0 therefore establishes a material operational mismatch between hospitalization-level pair co-membership and execution-confirmed temporal overlap. It does **not** establish ADE reduction, clinical appropriateness, or method superiority.

## Final novelty boundary

The final closest-work check explicitly subtracts:

- Rough et al. 2020: provider-order-time, pre-order-only medication prediction;
- contextualized DDI-CDS: stopped-medication and administration-time-dependent alert applicability;
- SafeDrug/PIMNet/KATMed/RES-MR: safe medication-recommendation objectives and contextual safety;
- GRAIN/SafeRx-Agent: finer medication/safety granularity.

Do **not** claim any of those ingredients individually as novel.

The surviving search-scoped delta is:

> **At provider-order time, condition DDI optimization on a strictly pre-order, execution-confirmed active regimen derived from actual administration evidence, and require the learned method to beat direct controls receiving the identical exposure-risk signal.**

Final literature packet:

`research/memory/resource-reset-20260905-exposure-localized-safety/final-closest-work-check.md`

## Idea 006 scientific question

The first learned method question is deliberately narrow:

> Does end-to-end exposure-conditioned DDI learning create a reproducible active-exposure safety/fidelity advantage beyond direct exposure-aware reranking when both receive the same active-regimen state and the same DDI matrix?

The first candidate method is a simple common causal order-time predictor trained with:

`prediction loss + conventional new-set DDI term + active-regimen DDI term`.

The method is not allowed a richer architecture or richer information than the controls.

## Primary killer control

The strongest null is:

> The dynamic exposure signal is useful, but learning is unnecessary; direct greedy reranking of Base logits with the same active-regimen DDI signal is sufficient.

Gate 01 gives the identical `A_t` and frozen DDI matrix to:

- `ExposureConditional`;
- `DirectExposureRerank`;
- `ExposureHardConstraint`.

It also includes `Base` and conventional `StaticLoss`.

If the direct reranker absorbs the learned gain, Idea 006 terminates. Do not rescue the route with a GNN, Transformer, personalized risk network, LLM, labs/vitals, dose/route, a new DDI database, subgroup mining, or extra hyperparameter searches.

## Gate 01 — only authorized local execution

Protocol SSOT:

`research/ideas/006-exposure-conditional-medication-recommendation/experiments/gate-01-exposure-conditioned-learning.md`

Gate 01 freezes:

- non-overlapping 10-minute medication-order bursts;
- strict feature timestamps `< decision time`;
- causal pre-order active-regimen construction using prior administration and pre-order D/C transactions only;
- R0 Discovery -> patient-disjoint InnerTrain/InnerTune;
- R0 Dev -> one frozen outer evaluation;
- one small GRU backbone shared by all learned variants;
- fixed `K=5` primary ranking evaluation;
- `IncrementalExposureDDI@5` as primary safety surrogate;
- `Recall@5` as primary fidelity metric;
- a common InnerTune safety budget equal to 90% of Base risk;
- fixed lambda/gamma grids;
- 2,000-replicate paired patient-clustered bootstrap, seed `260907`;
- an all-conditions PASS rule.

No Holdout/test access is authorized.

## Frozen decision routing

### PASS

`PASS_GATE01_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`

Only then return to `ccf-pipeline-orchestrator` to design broader claim-support evidence. Do not automatically consume Holdout or test. A later stage should add at least one materially different causal predictor family before final claim support.

### FAIL

`STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`

Terminate Idea 006's current method route. Preserve R0 as a valid resource/semantic result, but do not turn that measurement into the target paper and do not add a rescue model in the same premise family.

## Publication boundary

Even on Gate-01 PASS, the project may claim only exposure-localized DDI **surrogate** optimization and medication-order fidelity. eMAR administration is not proof of appropriate treatment, static-only is not proof of safety, and DDI overlap is not an ADE label.

## Next owner

Local repository Agent executes Gate 01 exactly from the frozen protocol, then runs `ccf-integrity-auditor`.

No other scientific execution is authorized in the same run.
