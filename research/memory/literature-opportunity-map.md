<!-- markdownlint-disable MD013 -->

# Literature Opportunity Map

## Current status

Refresh date: 2026-09-05.

Current project state: `NO_HIGH_VALUE_DIRECTION_YET`.

The earlier B0 premise has been executed and failed. The single bounded post-B0 exploratory reset has also been completed. No literature-backed route is currently admitted for method implementation or Idea 006 creation.

Detailed reset folder: [`literature-search-20260905-prescription-supervision-reset/`](literature-search-20260905-prescription-supervision-reset/).

The user-maintained `xray-papers-innovation-summary.md` 64-paper map remains the primary supplied literature prior; this file records only the decision-relevant current opportunity state.

## Closed or strongly compressed spaces

### Count-mediated treatment-preserving safety

`CLOSED under B0`.

B0 showed that oracle reference-count matching slightly improves retrospective fidelity but leaves pair-normalized DDI rate essentially unchanged. The required count-mediated safety trade-off is absent under frozen MoleRec.

### Generic longitudinal/history modeling

`CROWDED / LOW PRIOR`.

MR-DTR, DrugDoctor, HeteroMed, DMRNet, HypeMed and related work already cover time-aware treatment regimes, historical condition matching, medication inheritance/expansion, history recalibration, and visit-conditioned retrieval. A new method needs a more specific learning mechanism than 'use history better'.

### Generic rule/KG/RAG/agent safety

`CROWDED / LOW PRIOR`.

KATMed, RES-MR, SafeRx-Agent, ATLAS and related work already cover contraindication-aware learning, personalized safety boundaries, knowledge-grounded verification, and patient-specific conflict reasoning. A rule-conditioned method must also survive the repository's rule-entitlement control.

### Generic fine-grained diagnosis/action mapping

`CROWDED`.

FineMed already supplies diagnosis-level medication supervision; SafeRx-Agent, GRAIN, RxEval and related work push medication/action resolution toward ATC-L4, active ingredients, and prescription-level units. Action-space remapping remains scientifically open but high-cost and highly collision-prone.

## Bounded reset: prescription supervision semantics

### Source-supported problem boundary

Current evaluation work provides direct evidence that a single historical prescription set is not equivalent to a complete clinically acceptable therapy set:

- Physician-RAG uses expert `CORE`, `ALT`, and `AVOID` medication categories.
- SafeRx-Agent includes a case where an out-of-current-ground-truth continuation is interpreted as clinically reasonable.

This supports a narrow statement:

> An unprescribed medication is not automatically a proven clinical negative.

It does **not** support treating arbitrary zero labels as hidden positives.

### Closest method pressure

- **KRAM (ESWA 2026)**: MedRec label-noise robustness via co-denoising and label refinement; closest domain-specific collision.
- **DMRNet (Neural Networks 2026)**: medication-frequency imbalance and historical recurrence; killer collision for popularity/history explanations.
- **FineMed (Information Sciences 2026)**: diagnosis-level supervision; generic 'better supervision' is not novel.
- **WSDM 2020 MNAR implicit feedback** and **NeurIPS 2025 Counterfactual Implicit Feedback Modeling**: generic PU/MNAR observation correction is established prior art.
- **Correct-and-Weight 2026**: current simple uncertain-negative / false-negative correction baseline family.

### Optimizer route

The strongest nontrivial route was refined to **trajectory-privileged negative reliability**: future longitudinal context would be available only during training to identify zero labels inconsistent with surrounding trajectories; a deployable student would remain current/past-only and would attenuate rather than flip low-reliability negative gradients.

### Strict review result

`PIVOT_WITH_RESCUE_ROUTE / DO_NOT_CREATE_IDEA_006`

Weighted score: `3.54/5`.

The decisive blockers are:

1. future prescription does not establish earlier clinical appropriateness;
2. the current MIMIC target cannot validate a latent acceptable-treatment set;
3. if the claim is narrowed to fitting the same observed prescription labels, the route risks becoming generic PU/noisy-label regularization;
4. KRAM, DMRNet, and generic PU/MNAR methods form strong simple and closest-work controls.

See [`literature-search-20260905-prescription-supervision-reset/idea-admission-review.md`](literature-search-20260905-prescription-supervision-reset/idea-admission-review.md).

## Current opportunity judgment

| Research axis | Judgment | Why it is not the current method route |
| --- | --- | --- |
| Post-hoc score/context routing | `CLOSED` | Repeated project-local failures under strong controls |
| Count-mediated safety/coverage | `CLOSED` | B0 normalized-DDI attribution failed |
| ATC sibling substitution | `CLOSED` | Semantic admission failed |
| Generic longitudinal modeling | `CROWDED / LOW PRIOR` | Heavy recent method collision |
| Generic KG/RAG/agent safety | `CROWDED / LOW PRIOR` | Heavy recent method collision plus rule-entitlement baseline risk |
| Generic fine-grained action mapping | `CROWDED / HIGH COST` | FineMed/GRAIN/SafeRx-Agent/RxEval pressure and action-space rebuild cost |
| Selective prescription supervision | `NOT ADMITTED` | Interesting problem, but latent target is not identifiable/evaluable under current labels |

## What would reopen method search

A new reset should occur only when a binding scientific resource changes. The highest-value reopen conditions are:

1. **supervision semantics**: an independently grounded multi-valid treatment / reliable-negative target at useful scale;
2. **patient state**: clinically richer state variables sufficient to support a mechanism that current diagnosis/procedure codes cannot identify;
3. **action resolution**: a feasible remapping with evidence that current 131-label granularity destroys a material decision relation, not merely a finer taxonomy.

These are resource-changing pivots, not invitations to another feature search.

## Stable source links for the latest reset

- KRAM: https://doi.org/10.1016/j.eswa.2026.131330
- DMRNet: https://doi.org/10.1016/j.neunet.2026.109168
- FineMed: https://doi.org/10.1016/j.ins.2026.123930
- Physician-RAG: https://doi.org/10.1016/j.ijmedinf.2026.106598
- SafeRx-Agent: https://arxiv.org/abs/2605.29146
- WSDM 2020 MNAR implicit-feedback learning: https://doi.org/10.1145/3336191.3371783
- Counterfactual Implicit Feedback Modeling: https://proceedings.neurips.cc/paper_files/paper/2025/hash/1436e87a58b3e6ac177450bd10721726-Abstract-Conference.html
- Correct-and-Weight: https://arxiv.org/abs/2601.04291
