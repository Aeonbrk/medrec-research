<!-- markdownlint-disable MD013 -->

# Literature Opportunity Map

## Current status

Refresh date: 2026-09-08.

Current project stage:

`PRE_IDEA_PRIVILEGED_RESPONSE_REQUIRED_REVISIONS`

There is no active Idea. Ideas 001--006 are terminated. Idea 007 is not created or authorized.

Current packet:

[`model-reset-20260908-privileged-physiological-response/`](model-reset-20260908-privileged-physiological-response/).

Strict review:

[`model-reset-20260908-privileged-physiological-response/idea-review.md`](model-reset-20260908-privileged-physiological-response/idea-review.md).

Latest closest-work provenance:

[`model-reset-20260908-privileged-physiological-response/closest-work-review.md`](model-reset-20260908-privileged-physiological-response/closest-work-review.md).

Reviewer verdict:

`ACCEPT_WITH_REQUIRED_REVISIONS_BEFORE_IDEA_007` (`3.89 / 5.00`).

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
| Joint MedRec + lab prediction | `PRIOR ART` | MedGCN; Bhoi et al. 2023 |
| Knowledge distillation for MedRec | `PRIOR ART` | LEADER |
| Training-time privileged multimodal distillation | `PRIOR ART outside MedRec` | OC-Distill and broader LUPI/KD literature |
| True-future-observation teacher to current-only student | `PRIOR ART outside MedRec` | Privileged Foresight Distillation 2026 |
| Medication-aware physiological-response representation | `PRIOR ART outside general MedRec` | Wu et al. EMBC 2025 |

## Current selected opportunity

**Privileged physiological response supervision for medication recommendation.**

The family survives strict review only conditionally. It is not yet an admitted Idea.

### REFINE — NeurIPS 2023

DOI: `10.52202/075280-1043`.

REFINE uses dosage-titration trends and lab-test responses to characterize patient health and perform fine-grained medication recommendation.

Therefore `use lab response in MedRec` is not novel.

### ChainCare — Information Processing & Management 2026

DOI: `10.1016/j.ipm.2026.104739`.

ChainCare models bidirectional lab-test / medication-injection event chains, explicitly including injection-first sequences where physiological effects of medications are associated with follow-up laboratory tests, and uses the resulting monitoring-level representations for medication recommendation and disease prediction.

Therefore medication-administration / follow-up-monitoring structure is current MedRec prior art.

### MedGCN and integrated lab-response prediction

MedGCN couples medication recommendation with lab-test imputation (`10.1016/j.jbi.2022.104000`). Bhoi et al. 2023 explicitly integrate medication recommendation and lab-test response prediction (`10.1609/aaaiss.v1i1.27489`).

Therefore generic lab auxiliary/multitask and future/lab-response prediction are prior art and form a primary killer baseline family.

### DrugDoctor — Briefings in Bioinformatics 2024

DOI: `10.1093/bib/bbae464`.

DrugDoctor uses historical medications and the nearest downstream historical health condition to form effectiveness-aware historical information.

Therefore using a later health state after prior medication as ordinary historical response evidence is covered.

### MR-DTR — WWW 2025

DOI: `10.1145/3696410.3714533`.

MR-DTR establishes current time-aware/dynamic-treatment-regime medication recommendation work. Generic treatment-dynamics framing is therefore crowded; no collision was identified with current-instance future physiology used only during training.

### LEADER — 2024

arXiv: `2402.02803`.

LEADER uses feature-level knowledge distillation for medication recommendation.

Therefore `KD for MedRec` is not a novelty claim.

### OC-Distill — 2026

arXiv: `2604.16878`.

OC-Distill transfers training-time multimodal information into a deployable reduced-modality student for ICU risk prediction.

Therefore generic clinical privileged-information distillation is an established mechanism primitive.

### Wu et al. — IEEE EMBC 2025

DOI: `10.1109/EMBC58623.2025.11254154`; PMID `41336312`.

This work learns medicine-aware patient representations from transient physiological responses to vasoactive infusions.

Therefore medication-conditioned physiological-response representation itself is also established, though not as a general MedRec privileged-student method.

### Privileged Foresight Distillation — 2026

arXiv: `2604.25859`.

Privileged Foresight Distillation uses true future observations in a training-time teacher and distills a future-conditioned correction into a current-only student, while explicitly testing against generic regularization explanations.

Therefore `future observation teacher -> current-only deployable student` is now a generic prior-art pattern. Future-only information flow cannot carry the candidate's novelty by itself.

## Search-scoped residual delta

Within the retained 2023--2026 search, no direct general-MedRec method was found whose central mechanism is exactly:

> use paired realized post-administration physiological **values** only during training to supervise a strictly pre-order candidate-medication student, then deploy without future physiology.

However, this is a narrow composition of established primitives. The contribution is differentiated only if mechanism controls establish that the incremental signal is specifically carried by medication-in-context physiological values and pairing.

The necessary surviving delta is:

> medication-in-context post-administration physiological values as privileged response-associated supervision, with evidence that focal-medication conditioning, individualized patient-medication-response correspondence, and physiological values matter beyond generic future-state prediction, static medication priors, monitoring availability, sample weighting, and KD mechanics.

Novelty status:

`MODERATE / SEARCH-SCOPED / REQUIRED_REVISIONS_BEFORE_IDEA`.

This is not a novelty proof.

## Mandatory strongest alternatives (R1--R3 frozen)

The bounded optimizer pass freezes before Idea creation:

- a matched Generic Future-State Auxiliary / Medication-Ablated Future control;
- Monitoring-Mask-Only plus physiological-value versus response-availability separation;
- equal-support positive-only response semantics and strictly pre-order deployment entitlement.

If a later Idea is admitted, Gate 01 must additionally include:

- Strict Pre-Order Base;
- Base + Pre-Order Physiology;
- Static Medication Response Prototype;
- Response Shuffle;
- Generic KD when needed to isolate distillation mechanics;
- a compatible monitoring-aware MedRec baseline when task alignment supports a fair comparison.

A response-specific method story terminates if Generic Future-State Auxiliary, Medication-Ablated Future, Response Shuffle, Monitoring-Mask-Only, Static Response Prototype, or richer pre-order physiology performs comparably.

## Claim boundary

Post-administration physiology is observational and confounded by severity, co-medications, procedures, fluids, ventilation, dose/route, clinician actions, spontaneous progression, monitoring policy, and selective measurement.

Allowed framing:

- response-associated physiological signature;
- medication-in-context monitoring trajectory;
- privileged response supervision.

Disallowed without independent causal identification:

- causal drug response;
- individual treatment effect;
- drug efficacy;
- therapeutic benefit;
- counterfactual outcome;
- clinically optimal medication.

## Current routing

Next owner:

strict `ccf-idea-reviewer` for re-review of the three frozen revisions.

Idea 007 is created only if the subsequent strict review explicitly returns `ACCEPT_TO_CREATE_IDEA_007`.

No local experiment, response-coverage diagnostic, Gate 01, or architecture work is authorized now.
