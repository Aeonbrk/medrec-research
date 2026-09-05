<!-- markdownlint-disable MD013 -->

# Idea Grounding — Exposure-Conditional Medication Recommendation

## Status

`SELECT_FOR_RESOURCE_ADMISSION_ONLY`

No Idea 006 is created by this document.

Target assumption: first formal method paper; generic CCF-A AI/data-mining venue family (KDD / WWW / AAAI / IJCAI style lens), with a healthcare method contribution rather than a benchmark-only paper.

## Problem

Most current MedRec benchmarks represent one hospitalization/visit as a medication set and evaluate safety with a static DDI relation over pairs inside that set. This implicitly treats interaction risk as a property of visit-level co-membership.

Hospital medication safety is stateful. At a provider order time, some medications have been administered and remain operationally active, some have stopped, and some medications appearing later in the same hospitalization have not yet been ordered or administered. Contextual DDI systems explicitly use concomitant exposure, administration timing, route, treatment course, laboratory state, and stopped-medication status to determine alert applicability.

The proposed paper does not claim to predict actual ADEs. It asks a narrower algorithmic question:

> Can medication-order recommendation preserve treatment fidelity better when DDI pressure is conditioned on the currently executed active regimen instead of the union of all medications in an encounter?

## Root challenge

The usual safe-MedRec abstraction collapses two axes:

1. **what medication is relevant**;
2. **whether a known pairwise interaction is applicable now**.

A static visit-level DDI graph provides the pair relation but not its current exposure applicability.

The current repository cannot test this because its processed 131-medication snapshot has visit-level diagnosis/procedure/medication sets and no raw order/administration timeline.

## Resource change

Use raw MIMIC-IV medication request/order and administration resources:

- medication requests/orders: `prescriptions`, `pharmacy`, `poe`;
- administration evidence: `emar`, `emar_detail`; `inputevents` can be considered later for ICU-specific completeness;
- optional later patient-state channels: prior time-stamped labs/vitals and earlier hospital history.

At first access, create a deterministic patient-level Discovery/Dev/Holdout partition. R0 reads scientific aggregates only from Discovery. The new Holdout is quarantined before hypothesis-selection experiments.

## Optimizer candidate family

### Candidate A — Static visit-set DDI reweighting

Operation: `refine`.

Rejected. It remains inside the already crowded SafeDrug/KATMed/HeteroMed family and does not use the new resource.

### Candidate B — Predict medication plus administration time

Operation: `combine`.

Rejected. Actual administration time is heavily influenced by workflow and is not a defensible normative safety target.

### Candidate C — Exposure-conditioned next-order recommendation

Operation: `combine`.

Retained as strongest route.

At each provider medication-order decision point $t$:

- input: only information available before $t$;
- target: medication order(s) placed in the next short order window, following the established order-time prediction precedent;
- dynamic safety state: medications with execution-confirmed active orders before $t$;
- candidate risk: known DDI relation between a candidate medication and the currently executed active regimen;
- optimization: medication prediction objective plus exposure-conditional DDI regularization.

The future administration record is never an inference input. eMAR only contributes past execution evidence when defining the current active regimen.

### Candidate D — Learned DDI applicability classifier

Operation: `transfer`.

Not selected. Without clinician adjudication or outcome labels, an applicability classifier would risk learning hospital practice rather than clinical interaction relevance.

## Strongest mechanism

Working mechanism: **Exposure-Conditional DDI Regularization (ECDR)**.

Let $A_t$ denote the set of medications whose orders are active at time $t$ and have evidence of execution before $t$. For candidate medication $m$, define an exposure-localized interaction pressure from the existing DDI relation $D$:

$$
r_t(m) = \operatorname{Agg}_{a \in A_t} D(m,a).
$$

A medication-order model outputs $p_t(m)$. The method adds a differentiable expected active-regimen interaction term rather than penalizing all pairs in the full hospitalization medication union.

The exact aggregation and optimization form are **not frozen** before R0. The central mechanism is the conditioning of DDI pressure on pre-order executed-active state.

Causal chain:

`executed-active state -> fewer temporally inapplicable DDI penalties -> different training gradients/ranking -> better medication-order fidelity at matched exposure-localized DDI surrogate`.

## Strongest simple controls

The paper is not viable unless it beats all of these:

1. order-time predictor without DDI objective;
2. standard static-DDI training objective;
3. **direct exposure-aware post-hoc scalar reranker** using the same $r_t(m)$;
4. **direct exposure-aware hard filter** using the same DDI entitlement;
5. matched-risk threshold / Lagrangian control so a gain cannot be explained by simply tolerating more DDI pressure.

This explicitly imports the project's C1a/C3 lessons. The learned method does not receive a safety relation that controls are denied.

## Novelty delta after closest-work subtraction

Not novel:

- order-time medication prediction;
- temporal EHR encoding;
- static DDI regularization;
- ATC-L4 or ingredient-level recommendation;
- contextual DDI CDS rules in general.

Potentially novel intersection:

> **A safe medication-recommendation objective in which pairwise DDI pressure is conditioned on an execution-confirmed active medication state at provider order time, with explicit comparison against the same dynamic risk signal used as a direct reranker/filter.**

The searched literature did not reveal a 2023--2026 MedRec paper centered on this exact interaction. Novelty remains provisional until the resource gate and a final pre-Idea search are complete.

## Evidence package if the resource gate passes

A method paper would need:

- patient-level leakage-safe Discovery/Dev/Holdout splits;
- no post-order features in any model input;
- order-time medication prediction fidelity;
- exposure-localized DDI surrogate metrics;
- static visit-union DDI as a secondary comparator, not the primary safety truth;
- direct exposure-aware reranker and hard-filter controls;
- ablation of execution confirmation versus active-order-only state;
- at least two model backbones or one architecture-agnostic objective demonstrated across materially different predictors;
- failure analysis for interacting ground-truth orders, because some known DDIs are clinically justified or managed.

Clinical ADE reduction, optimal prescribing, or clinical safety should not be claimed from this evidence alone.

## Main risks

1. Raw MIMIC-IV order-to-administration linkage may be too incomplete or heterogeneous for a stable executed-active state.
2. Medication normalization to a shared action/DDI vocabulary may consume disproportionate infrastructure time.
3. The static-versus-exposure semantic mismatch may be small in this cohort, eliminating the method motivation.
4. A direct exposure-aware reranker/filter may absorb the entire benefit, reproducing the project's prior baseline trap.
5. The eventual method may still look like a simple state-dependent DDI loss unless the empirical interaction with end-to-end learning is decisive.

These risks justify one resource/premise admission gate before Idea creation.
