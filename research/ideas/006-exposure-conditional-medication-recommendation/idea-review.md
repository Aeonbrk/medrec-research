<!-- markdownlint-disable MD013 -->

# Idea 006 Strict Review — Exposure-Conditional Medication Recommendation

## Verdict

`ACCEPT_TO_DEVELOP / SELECT_FOR_GATE_01_ONLY`

**Weighted score**: `4.30 / 5.00`.

**Current conference readiness**: medium. The problem, resource, and novelty delta are admitted; no learned result exists yet.

**Development potential**: high if and only if end-to-end exposure-conditioned learning beats direct exposure-aware controls.

**Confidence**: medium-high. The final closest-work check covers the main task, contextual DDI-CDS, current safe MedRec, and granularity/safety lines. A universal novelty claim is not warranted.

## Target venue and assumptions

Target: a CCF-A Data/Mining/AI venue family in the 2027 cycle; final venue is not frozen.

The review evaluates a **method paper** direction, not a benchmark or measurement paper.

## Normalized idea

At each provider medication-order decision time, recommend the next short-burst medication set from strictly pre-order information. Define safety pressure against the execution-confirmed active regimen available before that order rather than against every medication that appears anywhere in the hospitalization.

The proposed first mechanism is a simple exposure-conditioned DDI regularizer on a common causal order-time predictor. The same active-exposure DDI signal is also given to direct greedy reranking and hard-constraint controls.

## Search basis

Final search packet:

`research/memory/resource-reset-20260905-exposure-localized-safety/final-closest-work-check.md`

Key closest work:

- Rough et al. 2020: order-time, pre-order-only medication prediction;
- Wong et al. 2021 and Wasylewicz et al. 2022: context-dependent DDI alert applicability, including stopped medication and administration timing;
- PIMNet 2023: patient/order evolution for safe medication recommendation;
- KATMed 2026: contraindication-aware learning;
- RES-MR 2026: personalized safety boundaries;
- GRAIN and SafeRx-Agent 2026: finer medication/safety granularity.

## Novelty delta after subtraction

The defensible delta is not any single component. It is:

> **A medication-order recommender whose DDI objective is conditioned on a strictly pre-order, execution-confirmed active regimen derived from actual administration evidence, and whose learned value is tested against direct controls with identical exposure-risk entitlement.**

R0 materially strengthens this delta by showing that the resource is usable and that 21.0521% of eMAR-observed visit-union DDI episodes are static-only under the frozen operational definition.

## Independent reviewer panel

### Field expert

**Best argument**: Current safe MedRec commonly treats DDI as a static property of a predicted visit-level set. R0 shows that this time scope collapses a material amount of non-concurrent inpatient treatment into one safety state.

**Strict rejection-grade concern**: Clinical DDI risk can depend on dose, route, pharmacokinetics, and interaction type; active order/eMAR overlap is still a surrogate.

**Anchor**: contextual DDI-CDS literature and the R0 interpretation boundary.

**Most valuable repair**: keep the primary claim at exposure-localized pairwise DDI applicability and explicitly defer ADE/PK claims. Add route/dose only if later evidence makes them necessary, not to rescue Gate 01.

**Score tendency**: 4–5.

### Method expert

**Best argument**: The method changes the support of the safety objective at the actual decision point rather than adding a new encoder or post-hoc feature.

**Strict rejection-grade concern**: A one-line dynamic penalty may be fully equivalent in practice to direct logit reranking with the same known DDI risk.

**Anchor**: the repository's EG-TER/rule-entitlement lesson.

**Most valuable repair**: none at design time. Gate 01 must test this objection directly. If reranking matches the learned objective, terminate the Idea.

**Score tendency**: 4.

### Experiment expert

**Best argument**: The R0 split provides a large fresh Dev partition and a quarantined Holdout. The mechanism has unusually clear killer controls.

**Strict rejection-grade concern**: The task reconstruction is new, and apparent gains could be caused by prediction-count or safety-budget mismatch rather than learning.

**Anchor**: B0 cardinality failure and prior strong-control lessons.

**Most valuable repair**: fixed-$K$ primary evaluation, patient-level bootstrap, Tune-only safety-budget selection, and identical active-DDI entitlement for all controls.

**Score tendency**: 4.

### AC / venue expert

**Best argument**: A clear formulation error in a widely used safety objective, backed by a large real EHR resource and a simple method, can fit KDD/WWW/AAAI-family audiences if the evidence is broad and leakage-safe.

**Strict rejection-grade concern**: Without learned value beyond a direct rule, reviewers will see this as task/evaluation engineering plus an obvious penalty.

**Most valuable repair**: Gate 01 must establish learned incremental value. Later claim support must include at least two materially different predictor families and transparent task-cost reporting.

**Score tendency**: 4.

### Skeptical prior-art expert

**Best argument**: The final search found the ingredients separately but no direct work joining actual administration-derived active state with order-time safe recommendation under direct-control leveling.

**Strict rejection-grade concern**: A reviewer may frame it as `Rough 2020 + contextual DDI CDS + SafeDrug-style loss`.

**Most valuable repair**: phrase novelty as the empirically validated **decision-time safety semantics**, then show that the interaction creates a nontrivial learned frontier unavailable to direct reranking.

**Score tendency**: 4.

## Rubric

| Dimension | Weight | Score | Confidence | Main basis | Repair condition |
| --- | ---: | ---: | ---: | --- | --- |
| Problem importance | 12 | 5 | 5 | Static visit-level DDI semantics are a consequential mismatch for inpatient order-time decisions | Preserve decision-level framing |
| Novelty against likely prior work | 14 | 4 | 4 | No direct searched collision for the full tuple; ingredients separately established | Maintain narrow novelty claim and monitor closest work |
| Conceptual innovation | 12 | 5 | 4 | Changes DDI applicability from visit-set membership to execution-localized decision state | Demonstrate the change matters to learning, not only measurement |
| Method soundness | 14 | 4 | 4 | Simple differentiable objective with strict causal state semantics | Do not overclaim the exposure surrogate |
| Elegance and simplicity | 8 | 4 | 5 | One state correction plus one objective, common backbone | Avoid architecture inflation |
| Feasibility under resources | 8 | 4 | 5 | R0 passes resource, mapping, support, and state-feasibility floors | Build one bounded order-time training pipeline |
| Experimental convincibility | 10 | 4 | 5 | Strong direct rerank/filter and static-loss controls are available | Gate 01 must use matched risk/count semantics |
| Venue and audience fit | 8 | 4 | 4 | Suitable for CCF-A data/mining/AI if method evidence survives | Later multi-backbone and scale evidence required |
| Timeliness and topic heat | 6 | 5 | 4 | 2026 MedRec emphasizes safety, finer granularity, and leakage validity | Avoid generic safety framing |
| Risk-adjusted acceptance potential | 8 | 4 | 4 | High upside with a single decisive method risk | Kill route if direct control absorbs gain |

Weighted score:

$$
\frac{430}{100}=4.30/5.00.
$$

## Fatal risks

No fatal gate is currently triggered.

One **conditional fatal risk** remains:

> If a direct exposure-aware reranker or deterministic constraint matches the learned method at comparable exposure risk, there is no sufficient learned-method contribution for this project's first CCF-A method paper.

Gate 01 is designed specifically to resolve this.

## Score-change conditions

The score rises materially only if Gate 01 shows a reproducible learned Pareto improvement over direct controls and conventional static-DDI learning.

The score falls to `pivot-with-rescue-route` or lower if:

- direct exposure-aware reranking matches the learned method;
- the result exists only through cardinality differences;
- the exposure-conditioned objective harms fidelity without a material active-DDI reduction;
- leakage-safe task construction cannot be reproduced on Dev.

## Recommendation

`CREATE_IDEA_006_AND_FREEZE_GATE_01`.

Do not start multi-backbone expansion, Holdout evaluation, test evaluation, richer labs/vitals, dose/route modeling, or manuscript work before Gate 01 passes.

## Next owner

`ccf-experiment-designer`.
