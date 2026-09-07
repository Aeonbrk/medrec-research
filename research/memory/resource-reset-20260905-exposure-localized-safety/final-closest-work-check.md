<!-- markdownlint-disable MD013 -->

# Final Closest-Work Delta Check — Exposure-Localized Medication Safety

## Search status

- **Mode**: `ccf-literature-searcher / quick`
- **Search date**: 2026-09-07
- **Purpose**: final pre-Idea novelty subtraction after `PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE`
- **Target family**: generic CCF-A Data/Mining/AI venue family; likely 2027 cycle because the 2026 KDD/SIGIR cycle has already occurred
- **Search confidence**: medium-high for the central combination; no universal novelty claim is made

## Frozen candidate after R0

The candidate is not generic temporal medication recommendation and not generic DDI-aware learning.

The exact scientific tuple is:

> **At a provider medication-order decision point, predict the next medication action from strictly pre-order information while defining DDI pressure against an execution-confirmed active medication state derived from prior administrations, and test whether end-to-end exposure-conditioned learning adds value beyond direct use of the same exposure-risk signal.**

R0 supplies project-local evidence that the time scope matters: 21.0521% of eMAR-observed visit-union DDI episodes in Discovery were `static-only`, despite both medications having real administration records in the same hospitalization.

## Closest-work subtraction

| Work | What it already covers | What it does **not** cover relative to the candidate |
| --- | --- | --- |
| Rough et al., *Clinical Pharmacology & Therapeutics* 2020, DOI `10.1002/cpt.1826` | Patient-specific medication prediction at each provider order event using only EHR information available before the order; 990 normalized medications | No DDI-aware recommendation objective, no eMAR-confirmed active regimen, and no comparison of static versus exposure-localized safety semantics |
| Wasylewicz et al., *Clinical Pharmacology & Therapeutics* 2022, DOI `10.1002/cpt.2624` | Contextualized DDI management at medication-order time; suppresses or changes alerts based on stopped medications, administration timing, route/dose/context, and other clinical factors | Clinical decision-support filtering, not learned medication recommendation; does not optimize recommendation fidelity against an exposure-localized risk objective |
| Wong et al., *JAMIA Open* 2021, DOI `10.1093/jamiaopen/ooab023` | Computable patient-context algorithms for selected high-priority DDIs | Rule-based alert contextualization for eight DDIs, not general medication recommendation or eMAR-conditioned end-to-end learning |
| Li et al., *Methods* 2023, DOI `10.1016/j.ymeth.2023.06.005` (PIMNet) | Uses medication-order and patient-condition evolution to model current core medications and reduce standard DDI rate | Visit-level recommendation semantics; no actual administration-derived active exposure and no order-time exposure-risk objective |
| Qiao et al., *Journal of Biomedical Informatics* 2026, DOI `10.1016/j.jbi.2026.104991` (KATMed) | Knowledge-augmented medication recommendation with drug-disease contraindication rules as differentiable constraints | Contraindication-aware safety, but not administration-time DDI applicability or active-regimen-conditioned DDI optimization |
| Wang et al., SIGIR 2026, DOI `10.1145/3805712.3809604` (RES-MR) | Personalized risk-aware medication reasoning and safety boundaries | Personalized risk tolerance rather than execution-confirmed temporal applicability of pairwise DDI pressure |
| Fan et al., arXiv `2608.00098` (GRAIN) | Active-ingredient-level modeling and ingredient/drug DDI objectives | Improves pharmacological granularity but retains set-level DDI semantics rather than order-time active exposure |
| Wang et al., arXiv `2605.29146` (SafeRx-Agent) | Fine-grained ATC-L4 medication generation, knowledge grounding, DDI/contraindication verification | Fine-grained safety verification but no eMAR-derived active regimen or learned exposure-localized DDI objective |

## Search-scoped novelty delta

No direct work was found in the final search that jointly establishes all of the following:

1. provider-order-time medication recommendation;
2. strictly pre-order causal input semantics;
3. actual administration evidence used to construct the currently active medication state;
4. DDI optimization against that active state rather than hospitalization/visit medication co-membership alone;
5. end-to-end learned recommendation evaluated against direct exposure-aware reranking/filtering controls that receive the identical DDI signal.

The first item is clearly prior art from Rough et al. The third and fourth items are clinically motivated by contextualized DDI-CDS work. Recent MedRec methods cover static DDI objectives, contraindications, personalized safety, and finer medication granularity. The remaining delta is therefore the **interaction between order-time recommendation and execution-localized DDI applicability**, not either ingredient by itself.

## Strongest novelty-collapse objection

A reviewer can reasonably say:

> "This is Rough 2020 order prediction plus a contextual DDI penalty that clinical CDS systems already know how to compute."

This objection is fatal unless the learned method demonstrates value beyond a direct exposure-aware control.

Therefore the first method gate must give the same active-exposure DDI signal to:

- direct greedy reranking;
- a deterministic hard exposure constraint;
- the end-to-end method.

If direct use of the signal matches the learned method, the method story terminates even though the resource/premise remains scientifically valid.

## Final search verdict

`NOVELTY_DELTA_SURVIVES_FOR_IDEA_CREATION`

The surviving delta is narrow but method-capable. It is sufficiently separated from the closest searched work to create one bounded Idea, provided the Idea claims only exposure-localized safety semantics and not generic order-time prediction, temporal modeling, DDI knowledge, or medication granularity as novel.

## Stable source links

- Rough et al. 2020: https://doi.org/10.1002/cpt.1826
- Contextualized DDI management 2022: https://doi.org/10.1002/cpt.2624
- Contextualized DDI algorithms 2021: https://doi.org/10.1093/jamiaopen/ooab023
- PIMNet: https://doi.org/10.1016/j.ymeth.2023.06.005
- KATMed: https://doi.org/10.1016/j.jbi.2026.104991
- RES-MR: https://doi.org/10.1145/3805712.3809604
- GRAIN: https://arxiv.org/abs/2608.00098
- SafeRx-Agent: https://arxiv.org/abs/2605.29146
