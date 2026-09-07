<!-- markdownlint-disable MD013 -->

# Idea 006 Optimization — Exposure-Conditional Medication Recommendation

## Optimizer status

- **Owner**: `ccf-idea-optimizer`
- **Mode**: standard
- **Target family**: CCF-A Data/Mining/AI; likely 2027 cycle, final venue not frozen
- **Input evidence**: R0 PASS plus final closest-work delta check
- **Optimization verdict**: `SELECT_EXPOSURE_CONDITIONAL_OBJECTIVE_FOR_STRICT_REVIEW`

## Normalized idea

### Task

At each provider medication-order decision time $t$, recommend the medications likely to be ordered in the next short order burst using only information available strictly before $t$.

### Problem

Standard safe medication recommendation usually evaluates or penalizes DDI relations over a visit-level predicted medication set. In an inpatient order-time setting, that time scope is too coarse: medications that appear in the same hospitalization are not necessarily concurrently active.

R0 directly supports the premise in MIMIC-IV 3.1 Discovery: among DDI pairs where both medications were actually administered in the same hospitalization, 21.0521% were `static-only` under the frozen execution-overlap definition.

### Root challenge

DDI knowledge is pairwise and static, but **DDI applicability is state-dependent**. The relevant safety question when recommending a new medication is not only whether two medication codes can interact, but whether the interacting medication is part of the currently executed regimen when the new order is being considered.

### Core insight

Safety should be formulated as **incremental interaction pressure at the decision boundary**:

$$
\text{candidate medication} \times \text{pre-order active exposure state},
$$

rather than as unconditional co-membership anywhere in the hospitalization.

### Candidate mechanism

Let $V$ be the 131-concept medication vocabulary and let $A_t\subseteq V$ denote the strictly pre-order, execution-confirmed active regimen.

A common order-time predictor produces medication probabilities $p_t(m)$.

Define the candidate-to-active expected DDI term:

$$
L_{active}(t)
=
\frac{1}{|V|\max(1,|A_t|)}
\sum_{m\in V}\sum_{a\in A_t}p_t(m)D_{ma}.
$$

Retain a conventional predicted-new-set pairwise term:

$$
L_{new}(t)
=
\frac{2}{|V|(|V|-1)}
\sum_{i<j}p_t(i)p_t(j)D_{ij}.
$$

The optimized candidate objective is deliberately simple:

$$
L
=
L_{pred}
+
\lambda\left(L_{active}+L_{new}\right).
$$

The scientific novelty is **not** this algebra by itself. The contribution is the decision semantics that determines which DDI relations are active at recommendation time, plus evidence that end-to-end optimization under those semantics contributes beyond direct use of the identical risk signal.

### Innovation type

Primary: **problem/formulation + learning objective**.

Secondary: **data-semantic alignment** between medication ordering and actual administration.

Not claimed as novelty:

- a new sequence encoder;
- medication-order-time prediction;
- generic temporal EHR modeling;
- DDI knowledge;
- active-ingredient granularity;
- contextual DDI alerting.

## Why this route survives the project failure landscape

### It is not another frozen-output feature

The active regimen $A_t$ changes the training objective and the decision state before prediction. It is not a scalar derived after a frozen visit-level recommender has already emitted a prescription.

### It does not require therapeutic substitution semantics

The mechanism uses only whether a known DDI relation applies to the current active exposure state. It does not infer that one medication is a therapeutic substitute for another.

### It respects rule entitlement

The same $A_t$ and DDI matrix must be supplied to direct greedy reranking and hard constraints. Learned value must remain after that leveling.

### It avoids the B0 cardinality premise

The primary safety metric is pair-normalized incremental exposure risk at fixed $K$, not absolute DDI-pair count or medication-count shrinkage.

## Closest-work subtraction

The final search packet is:

`research/memory/resource-reset-20260905-exposure-localized-safety/final-closest-work-check.md`

The strongest overlap challenge is the combination of:

1. Rough et al. 2020: pre-order medication prediction;
2. contextualized DDI-CDS work: timing/stopped-medication-dependent DDI applicability;
3. SafeDrug/KATMed/GRAIN/RES-MR/SafeRx-Agent: safe medication recommendation objectives and finer/personalized safety.

The route survives only because no direct searched work was found that uses actual prior administration to define the active regimen for order-time recommendation and then requires end-to-end learning to beat direct exposure-aware controls.

## Overlap challenge

### Challenge

Could the entire method be replaced by:

$$
z'_t(m)=z_t(m)-\gamma r_t(m),
$$

where $z_t(m)$ is the base logit and $r_t(m)$ is the known incremental DDI risk against $A_t$?

### Optimizer response

This is the decisive method question, not an implementation detail. The idea is admitted only for a Gate 01 in which the direct exposure-aware reranker receives identical risk information.

If direct reranking matches the end-to-end objective at matched exposure risk, terminate Idea 006. Do not replace the failed loss with a GNN, personalized controller, LLM, or more elaborate risk network.

## Evidence challenge

### Challenge

Actual administration confirms operational exposure, not clinical appropriateness or harm.

### Optimizer response

The paper must claim only **exposure-localized DDI surrogate optimization**. It must not claim ADE reduction, clinical optimality, or that static-only DDI pairs are harmless.

The prediction target remains observed provider medication orders; the DDI signal is a safety regularizer and evaluation surrogate, not a clinical outcome label.

## Strongest development route

`Exposure-Conditional Medication Recommendation`

One simple causal order-time backbone is sufficient for Gate 01. Method novelty is evaluated through the objective and controls, not through encoder complexity.

## Fallback route

There is no authorized architecture-heavy fallback. If exposure-conditioned end-to-end learning fails against direct controls, the resource result remains a useful research observation but does not become this project's first method paper.

## Minimum convincing next evidence

One patient-disjoint Gate 01 must establish all of the following on the fresh R0 Dev partition:

1. exposure-conditioned learning materially reduces active-exposure DDI pressure versus prediction-only training;
2. fidelity loss remains bounded;
3. the learned method beats a direct exposure-aware greedy reranker under equal DDI entitlement and comparable risk;
4. the result is not explained by a conventional static predicted-set DDI loss.

Only a Gate 01 PASS justifies cross-backbone expansion.

## Handoff

Next owner: `ccf-idea-reviewer`.
