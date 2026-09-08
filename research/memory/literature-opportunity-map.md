<!-- markdownlint-disable MD013 -->

# Literature Opportunity Map

## Current status

Refresh date: 2026-09-08.

Current project stage:

`PRE_IDEA_PRIVILEGED_RESPONSE_OPTIMIZATION`

There is no active Idea. Ideas 001--006 are terminated. Idea 007 is not created or authorized.

Current packet:

[`model-reset-20260908-privileged-physiological-response/`](model-reset-20260908-privileged-physiological-response/).

## Closed or compressed spaces

| Space | Current judgment | Main reason |
| --- | --- | --- |
| Frozen-output feature/routing variants | `CLOSED` | Ideas 001--004 + EGSF; strong-control absorption |
| ATC sibling therapeutic substitution | `CLOSED` | Idea 005 semantic admission failure |
| Count-mediated safety/coverage | `CLOSED` | B0 normalized-DDI result |
| Selective prescription supervision | `NOT ADMITTED` | latent acceptable-treatment target not identifiable |
| Exposure-conditioned DDI learning | `CLOSED under Idea 006` | learned method failed equal-entitlement direct-reranker challenge |
| Residual temporal-practice adaptation | `CLOSED under S0` | no material forward degradation |
| Raw `New / Change / D/C` regimen-edit supervision | `NOT ADMITTED under M0` | action marks were inconsistent with frozen causal regimen state |
| Generic longitudinal modeling | `CROWDED` | MR-DTR, DrugDoctor, HeteroMed, ChainCare, DMRNet |
| Generic KG/RAG/agent safety | `CROWDED` | KATMed, RES-MR, SafeRx-Agent, ATLAS |
| Generic finer action granularity | `CROWDED / HIGH COST` | FineMed, GRAIN, SafeRx-Agent, RxEval |
| Generic labs/vitals fusion | `CROWDED` | REFINE, ChainCare, HIFINet, MedGCN |
| Joint MedRec + lab prediction | `PRIOR ART` | MedGCN; Bhoi et al. AAAI Symposium 2023 |
| Knowledge distillation for MedRec | `PRIOR ART` | LEADER |
| Training-time privileged multimodal distillation | `PRIOR ART outside MedRec` | OC-Distill and broader LUPI/KD literature |

## Current selected opportunity

**Privileged physiological response supervision for medication recommendation.**

### Source-backed boundary

#### REFINE — NeurIPS 2023

REFINE uses dosage-titration trends and lab-test responses to characterize patient health and perform fine-grained medication recommendation.

Therefore `use lab response in MedRec` is not novel.

Stable source:
https://papers.nips.cc/paper_files/paper/2023/hash/4b7439a4ab0b8e4bcb4e2412c6a10a58-Abstract-Conference.html

#### ChainCare — IPM 2026

DOI: `10.1016/j.ipm.2026.104739`

ChainCare models bidirectional lab-test / medication-injection event chains and uses them for medication recommendation and disease prediction.

Therefore monitoring execution chains are current prior art.

#### MedGCN and integrated lab-response prediction

MedGCN couples medication recommendation with lab-test imputation. Bhoi et al. 2023 explicitly integrate medication recommendation and lab-test response prediction.

Therefore generic lab auxiliary/multitask learning is prior art.

Stable sources:

- https://arxiv.org/abs/1904.00326
- https://doi.org/10.1609/aaaiss.v1i1.27489

#### DrugDoctor — BIB 2024

DOI: `10.1093/bib/bbae464`

DrugDoctor uses historical medications and the nearest downstream historical health condition to form effectiveness-aware historical information.

Therefore using a later health state after prior medication as ordinary history is covered.

#### LEADER — 2024

Stable source: https://arxiv.org/abs/2402.02803

LEADER uses feature-level knowledge distillation for medication recommendation.

Therefore `KD for MedRec` is not a novelty claim.

#### OC-Distill — 2026

Stable source: https://arxiv.org/abs/2604.16878

OC-Distill transfers training-time multimodal information into a deployable reduced-modality student for ICU risk prediction.

Therefore generic privileged-information distillation is an established mechanism primitive.

#### Wu et al. — EMBC 2025

DOI: `10.1109/EMBC58623.2025.11254154`

This work learns patient representations from transient physiological responses to vasoactive infusions.

Therefore medication-conditioned physiological-response representation is also an established primitive, though not a general MedRec method.

## Search-scoped residual delta

Within the retained search, no close general MedRec method was found whose central mechanism is:

> use realized post-administration physiological monitoring only during training to supervise a strictly pre-order candidate-medication student, then deploy without future physiology.

The candidate is differentiated only if the future information is **medication-in-context response supervision**, not generic future-state prediction, and if mechanism controls demonstrate that the association matters.

Novelty confidence:

`MODERATE / STRICT REVIEW REQUIRED`.

This is not a novelty proof.

## Mandatory strongest alternatives

Any later method gate must include:

- same-input causal Base;
- Base + pre-order labs/vitals;
- capacity-matched generic future-state auxiliary task;
- static medication response prototype;
- response-shuffle/misalignment control;
- compatible monitoring-aware MedRec baseline;
- KD-mechanics control if needed.

A response-specific method story is rejected if generic future-state auxiliary learning or shuffled response information performs comparably.

## Claim boundary

Post-administration physiology is observational and confounded by severity, co-medications, procedures, monitoring policy, and other interventions.

Allowed framing:

- response-associated physiological signature;
- medication-in-context monitoring trajectory;
- privileged response supervision.

Disallowed without stronger evidence:

- causal drug response;
- individual treatment effect;
- drug efficacy;
- counterfactual outcome.

## Current routing

The optimizer has completed the current method formulation in:

[`model-reset-20260908-privileged-physiological-response/idea-optimization.md`](model-reset-20260908-privileged-physiological-response/idea-optimization.md).

Next owner: strict `ccf-idea-reviewer`.

Idea 007 is created only if that review admits the residual novelty, method soundness, feasibility, and evidence path. No local experiment is authorized before review.
