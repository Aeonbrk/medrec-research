<!-- markdownlint-disable MD013 -->

# Literature Opportunity Map

## Current status

Refresh date: 2026-09-07.

Current project state: `IDEA_006_GATE_01`.

R0 Exposure Resource & Premise Admission passed on raw MIMIC-IV 3.1, the final closest-work delta check returned `NOVELTY_DELTA_SURVIVES_FOR_IDEA_CREATION`, and Idea 006 is now active under a single frozen learned-vs-direct-control gate.

Active Idea:

[`../ideas/006-exposure-conditional-medication-recommendation/README.md`](../ideas/006-exposure-conditional-medication-recommendation/README.md).

Detailed reset/search packet:

[`resource-reset-20260905-exposure-localized-safety/`](resource-reset-20260905-exposure-localized-safety/).

The user-maintained `xray-papers-innovation-summary.md` remains the primary supplied 64-paper prior. This file records the current decision-relevant opportunity map after the resource reset.

## Spaces already closed or compressed

| Research family | Current judgment | Why |
| --- | --- | --- |
| frozen-output score/rank/DDI/co-selection routing | `CLOSED` | Ideas 001--004 and EGSF failed under stronger simple controls |
| count-mediated safety/coverage | `CLOSED` | B0 left pair-normalized DDI essentially unchanged under oracle count |
| ATC sibling substitution | `CLOSED` | Idea 005 strict therapeutic semantic admission failed |
| selective prescription supervision / uncertain negatives | `NOT ADMITTED` | latent acceptable-treatment target remains unidentifiable; strong KRAM/PU collision |
| generic longitudinal/history modeling | `CROWDED / LOW PRIOR` | MR-DTR, DrugDoctor, HeteroMed, DMRNet, ChainCare and related work |
| generic KG/RAG/agent safety | `CROWDED / LOW PRIOR` | KATMed, RES-MR, SafeRx-Agent, ATLAS and related work |
| generic finer action mapping | `CROWDED / HIGH COST` | FineMed, GRAIN, SafeRx-Agent, RxEval and related work |
| order-time medication prediction alone | `PRIOR ART` | Rough et al. 2020 already uses pre-order EHR and a 10-minute medication-order target |

## R0 evidence that changed the opportunity map

R0 passed all frozen resource/premise floors on MIMIC-IV 3.1 Discovery:

- order normalization: 81.9248%;
- administration normalization: 81.8875%;
- action vocabulary: 131 ATC-L4 concepts;
- DDI-represented concepts: 91;
- eMAR-observed visit-union DDI episodes: 1,050,523;
- execution-confirmed overlap episodes: 829,366;
- static-only episodes: 221,157;
- `static_only_fraction = 21.0521%`;
- contributing patients: 68,695;
- unique DDI relations: 391;
- relations with at least 20 static-only episodes: 280;
- strictly pre-order active state: feasible.

This makes the time scope of DDI applicability a project-local mechanism premise rather than a literature-only motivation.

Boundary: R0 does not establish clinical harm, medication appropriateness, or learned value.

## Final closest-work subtraction

Final packet:

[`resource-reset-20260905-exposure-localized-safety/final-closest-work-check.md`](resource-reset-20260905-exposure-localized-safety/final-closest-work-check.md).

| Closest work | Already covered | Remaining delta |
| --- | --- | --- |
| Rough et al. 2020, DOI `10.1002/cpt.1826` | provider-order-time medication prediction using only pre-order EHR; 10-minute target | no execution-confirmed active-regimen DDI learning |
| Wong et al. 2021, DOI `10.1093/jamiaopen/ooab023` | computable patient-context algorithms for selected DDIs | clinical alert contextualization, not general medication recommendation |
| Wasylewicz et al. 2022, DOI `10.1002/cpt.2624` | contextualized DDI management using stopped medications, administration timing, route/dose/context | alert suppression/management, not learned order-time recommendation |
| PIMNet 2023, DOI `10.1016/j.ymeth.2023.06.005` | medication-order/patient-condition evolution and conventional DDI rate | no actual-administration-derived active exposure objective |
| KATMed 2026, DOI `10.1016/j.jbi.2026.104991` | drug-disease contraindication constraints in MedRec | rule applicability, not temporal pairwise exposure state |
| RES-MR 2026, DOI `10.1145/3805712.3809604` | personalized safety boundaries | risk tolerance, not execution-confirmed DDI applicability |
| GRAIN 2026, arXiv `2608.00098` | active-ingredient granularity and DDI objectives | finer identity, not order-time active exposure |
| SafeRx-Agent 2026, arXiv `2605.29146` | fine-grained knowledge-grounded safety verification | no eMAR-derived active-regimen learning |

A final focused search did not find a direct medication-recommendation method jointly establishing:

1. provider-order-time prediction;
2. strict pre-order feature semantics;
3. actual prior administration used to define the currently active medication state;
4. DDI optimization against that state rather than hospitalization/visit co-membership;
5. end-to-end learned value evaluated against direct controls receiving the identical exposure-risk signal.

This is search-scoped evidence, not a universal novelty proof.

## Surviving novelty delta

The defensible delta is the interaction:

> **order-time medication recommendation whose DDI objective is conditioned on a strictly pre-order, execution-confirmed active regimen derived from actual administration evidence, with learned value required to survive direct equal-entitlement exposure-aware controls.**

Do not claim as novel:

- order-time prediction;
- causal masking;
- temporal EHR modeling;
- static DDI regularization;
- contextual DDI alerts;
- ATC-L4/ingredient granularity.

## Strongest novelty-collapse objection

A strict reviewer can characterize the route as:

> `Rough 2020 + contextual DDI CDS + SafeDrug-style regularization`.

This objection remains fatal unless the learned exposure-conditioned objective beats a direct exposure-aware greedy reranker/hard constraint that receives the same active-regimen state and DDI matrix.

Therefore the novelty question has moved from literature search to the frozen Idea-006 Gate 01.

## Current opportunity judgment

| Research axis | Judgment | Current action |
| --- | --- | --- |
| prior post-hoc families | `CLOSED` | none |
| count-mediated safety | `CLOSED` | none |
| substitution structure | `CLOSED` | none |
| selective prescription supervision | `NOT ADMITTED` | none without changed supervision resource |
| generic longitudinal/KG/finer-action directions | `CROWDED` | not current route |
| **exposure-localized order-time DDI learning** | **`ACTIVE / IDEA 006`** | execute frozen Gate 01 only |

## Current review status

Idea-006 strict review:

`ACCEPT_TO_DEVELOP / SELECT_FOR_GATE_01_ONLY`

Weighted development score: `4.30/5`.

Current conference readiness remains medium because no learned result exists yet. The score is an investment judgment, not an acceptance probability.

## Stable source links

- Rough et al. 2020: https://doi.org/10.1002/cpt.1826
- Contextualized DDI algorithms: https://doi.org/10.1093/jamiaopen/ooab023
- Contextualized DDI management: https://doi.org/10.1002/cpt.2624
- PIMNet: https://doi.org/10.1016/j.ymeth.2023.06.005
- KATMed: https://doi.org/10.1016/j.jbi.2026.104991
- RES-MR: https://doi.org/10.1145/3805712.3809604
- GRAIN: https://arxiv.org/abs/2608.00098
- SafeRx-Agent: https://arxiv.org/abs/2605.29146
