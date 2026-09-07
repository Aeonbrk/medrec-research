<!-- markdownlint-disable MD013 -->

# Idea 006: Exposure-Conditional Medication Recommendation

- **Idea ID**: `006-exposure-conditional-medication-recommendation`
- **Status**: `ACTIVE / GATE_01_DESIGNED / NOT_EXECUTED`
- **Scientific stage**: Idea / hypothesis selection
- **Target venue assumption**: CCF-A Data/Mining/AI venue family, likely 2027 cycle; final venue not frozen
- **R0 resource gate**: `PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE`
- **R0 execution commit**: `ea134b7e75583186242bc72bc71eb2975b812edc`
- **Final closest-work verdict**: `NOVELTY_DELTA_SURVIVES_FOR_IDEA_CREATION`
- **Optimizer**: [`idea-optimization.md`](idea-optimization.md)
- **Strict idea review**: [`idea-review.md`](idea-review.md) (`ACCEPT_TO_DEVELOP / SELECT_FOR_GATE_01_ONLY`, `4.30/5`)
- **Gate 01 protocol**: [`experiments/gate-01-exposure-conditioned-learning.md`](experiments/gate-01-exposure-conditioned-learning.md)
- **New R0 Dev**: authorized for Gate 01 evaluation only under the frozen protocol
- **New R0 Holdout**: quarantined and not authorized
- **Existing project test split**: untouched and not authorized

## Scientific question

At an inpatient medication-order decision point, should DDI pressure be conditioned on the medications that are **actually execution-confirmed and still active before that order**, rather than treating every medication associated with the hospitalization or predicted set as equally relevant to the current safety state?

The method-level question is stricter:

$$
\boxed{\begin{aligned}
&\text{Does end-to-end exposure-conditioned DDI learning improve the safety--fidelity frontier}\\
&\text{beyond direct exposure-aware reranking when both receive the same active-regimen DDI signal?}
\end{aligned}}
$$

## Empirical premise from R0

On MIMIC-IV 3.1 Discovery, R0 admitted the new resource and minimum semantic premise:

- all required order/eMAR tables were available and linkable;
- order and administration normalization both exceeded 81%;
- the shared action space retained all 131 ATC-L4 concepts and 91 DDI-represented concepts;
- 1,050,523 eMAR-observed visit-union DDI patient-pair episodes were available;
- 221,157 episodes were `static-only`;
- `static_only_fraction = 21.0521%`;
- 280 DDI relations independently exceeded the distributed-support floor;
- a strictly pre-order state was feasible without current-visit discharge coding or future administration events.

R0 does not establish clinical harm, clinical appropriateness, or model superiority.

## Problem formulation

### Decision unit

A prediction is made immediately before a provider medication-order burst at time $t$.

The target is the normalized medication set ordered in the following frozen short window. Inputs are restricted to information available strictly before $t$.

### Active exposure state

Let $A_t$ be the set of normalized medications with at least one pre-$t$ execution-confirmed administration attached to an order that has not been causally discontinued by a pre-$t$ provider D/C transaction.

The construction may use the prior discontinuation transaction itself (`transaction_type = D/C` with `discontinue_of_poe_id`) because it is an event that occurred before $t$.

It must not use:

- `discontinued_by_poe_id` as a future pointer;
- final `order_status` to reconstruct historical status;
- prescription `stoptime` unless a later protocol proves that the stop time was known at the decision point;
- any post-$t$ administration;
- discharge-coded current-visit diagnosis/procedure information.

This is an operational active-order/execution state, not a pharmacokinetic concentration model.

## Candidate method mechanism

All Gate 01 variants use the same causal order-time backbone and the same active-state input.

The prediction-only objective is $L_{pred}$.

A conventional new-set DDI term is:

$$
L_{new}(t)
=
\frac{2}{|V|(|V|-1)}
\sum_{i<j}p_t(i)p_t(j)D_{ij}.
$$

The exposure-specific term is:

$$
L_{active}(t)
=
\frac{1}{|V|\max(1,|A_t|)}
\sum_{m\in V}\sum_{a\in A_t}p_t(m)D_{ma}.
$$

The candidate exposure-conditioned objective is:

$$
L=L_{pred}+\lambda\left(L_{new}+L_{active}\right).
$$

The method contribution is not the existence of a DDI matrix or a temporal encoder. It is the change in **which DDI relations are applicable at the decision point**, and whether learning under that state produces value beyond direct application of the same risk signal.

## Closest-work boundary

Do not claim as novel:

- order-time medication prediction — Rough et al. 2020 already establishes it;
- contextual DDI alerting — established in clinical CDS literature;
- temporal patient modeling — heavily covered;
- static DDI loss — SafeDrug-family prior art;
- contraindication-aware safety — KATMed;
- personalized risk boundary — RES-MR;
- fine medication granularity — GRAIN/SafeRx-Agent and related work.

Final search packet:

[`../../memory/resource-reset-20260905-exposure-localized-safety/final-closest-work-check.md`](../../memory/resource-reset-20260905-exposure-localized-safety/final-closest-work-check.md).

## Strongest simple killer control

The learned route receives no privileged DDI information.

The primary killer control takes the prediction-only model's logits and performs deterministic greedy exposure-aware reranking with the **same** $A_t$ and DDI matrix.

If the direct reranker reaches the same or better exposure-risk/fidelity point, Idea 006 terminates.

A deterministic hard exposure constraint and a conventional static predicted-set DDI loss are additional required controls.

## Gate 01

Only Gate 01 is authorized.

Gate 01 asks whether a simple end-to-end exposure-conditioned objective produces reproducible incremental value over:

1. prediction-only training;
2. conventional static new-set DDI regularization;
3. direct exposure-aware greedy reranking;
4. deterministic exposure-aware hard constraint.

The protocol freezes the task, patient partitions, backbone, tuning boundary, safety budget, metrics, bootstrap, and pass/fail logic before training.

## PASS semantics

A Gate 01 PASS means only:

> Under the frozen MIMIC-IV order-time task, exposure-conditioned end-to-end DDI learning creates a reproducible active-exposure safety/fidelity advantage that is not absorbed by direct exposure-aware controls receiving the same DDI information.

A PASS does not establish ADE reduction, prospective clinical safety, universal generalization, or final CCF-A readiness.

## FAIL semantics

A Gate 01 FAIL terminates the current method route.

In particular, if direct reranking absorbs the gain, do not rescue the route with:

- GNN risk encoders;
- personalized risk-tolerance networks;
- LLM agents;
- new DDI databases;
- subgroup mining;
- labs/vitals;
- dose/route modeling;
- additional hidden gates on the same premise.

## Publication path if Gate 01 passes

Only after Gate 01 PASS may the project design broader claim-support evidence, likely including:

- a second materially different causal predictor family;
- full safety/fidelity frontiers;
- robustness to active-state construction;
- efficiency/scale reporting;
- preserved quarantined Holdout for later claim support.

No paper project is created at Idea selection.

## Next owner

Local repository Agent executes the frozen Gate 01 protocol. No other scientific execution is authorized in the same run.
