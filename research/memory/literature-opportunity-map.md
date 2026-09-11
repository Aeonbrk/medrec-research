<!-- markdownlint-disable MD013 -->

# Literature Opportunity Map

## Current status

Refresh date: 2026-09-09.

Current update: 2026-09-11, using the existing strict semantic-admission,
supportability, and Pair/Context execution records; no new literature search was
run.

Current project stage:

`PRE_IDEA_AFTER_PAIR_CONTEXT_INCREMENTAL_VALUE_TERMINATION`

**Active Idea**: none. Ideas 001--007 are terminated. Idea 007 was formally
created/admitted and then closed at Gate 01 P1.

Current packet:

[`model-reset-20260910-strict-drug-changing-order-revision/`](model-reset-20260910-strict-drug-changing-order-revision/).

Strict admission review:

[`model-reset-20260908-privileged-physiological-response/idea-review.md`](model-reset-20260908-privileged-physiological-response/idea-review.md).

Closest-work provenance:

[`model-reset-20260908-privileged-physiological-response/closest-work-review.md`](model-reset-20260908-privileged-physiological-response/closest-work-review.md).

Reviewer verdict:

`ACCEPT_TO_CREATE_IDEA_007` (`4.17 / 5.00`, medium-high confidence).

Gate-01 protocol and independent design audit:

[`../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-protocol.md`](../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-protocol.md),
[`../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-design-integrity-audit.md`](../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-design-integrity-audit.md).

P1 closure evidence:

[`../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-mechanical-preflight.json`](../ideas/007-privileged-physiological-response-supervision/experiments/gate-01-mechanical-preflight.json),
[`failures/privileged-physiological-response-gate-01-p1--insufficient-support.md`](failures/privileged-physiological-response-gate-01-p1--insufficient-support.md).

Current frozen packet:

[`model-reset-20260910-strict-drug-changing-order-revision/`](model-reset-20260910-strict-drug-changing-order-revision/).

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
| Knowledge distillation for MedRec | `PRIOR ART` | LEADER; IJCAI-ECAI 2026 dual-channel MedRec KD |
| Training-time privileged multimodal distillation | `PRIOR ART outside MedRec` | OC-Distill and broader LUPI/KD |
| Clinical future-information teacher → history-only student | `PRIOR ART outside MedRec` | 2026 future-aware blood-glucose forecasting |
| True-future-observation teacher → current-only student | `PRIOR ART outside MedRec` | Privileged Foresight Distillation 2026 |
| Medication-aware physiological-response representation | `PRIOR ART outside general MedRec` | Wu et al. EMBC 2025 |
| **Privileged physiological response supervision** | **`CLOSED UNDER IDEA 007 / GATE 01 P1 SUPPORT TERMINATION`** | frozen six-channel administered-positive formulation failed supportability before training; P1 report and integrity audit are canonical |
| **Strict drug-changing order-revision Pair/Context value** | **`CLOSED UNDER PRE-IDEA INCREMENTAL-VALUE FAILURE`** | strict identity re-materialized, but all five frozen control comparisons failed; no rescue |

## Strict Pair/Context closure

The frozen strict trace contained `1,040` events with zero semantic or execution-
integrity violations. PairContext did not meet the preregistered relative-gain,
patient-cluster bootstrap, and per-seed NLL conditions against any of the five
controls. This closes the tested context-dependent incremental-value route; it
does not establish a universal claim about workflow or longitudinal information.

Record:

[`failures/strict-drug-changing-pair-context--no-incremental-value.md`](failures/strict-drug-changing-pair-context--no-incremental-value.md).

## Closed Idea-007 opportunity record

**Privileged physiological response supervision for medication recommendation** was
the bounded Idea-007 opportunity; it is now closed before training.

The generic future-privileged KD mechanism was not the opportunity. The tested
MedRec-specific scientific object was:

> use medication-in-context realized post-administration physiological **values** only as positive-event training supervision for a strictly pre-order candidate-medication student, then require matched evidence that focal medication conditioning, individualized response pairing, and physiological values matter beyond generic future supervision, monitoring policy, static medication priors, response-independent regularization, positive-event weighting, and KD mechanics.

The frozen formulation did not have sufficient, sufficiently distributed support
for Gate-01 mechanism learning. This closes the formulation under Idea 007; it does
not establish that physiology or response supervision is universally uninformative.

## Closest-work subtraction

### REFINE — NeurIPS 2023

REFINE models dosage-titration trends and lab-test responses to characterize patient health for fine-grained medication recommendation.

Therefore `use lab response in MedRec` is not novel.

### ChainCare — Information Processing & Management 2026

ChainCare models bidirectional lab-test / medication-injection event chains, including injection-first sequences where medication physiological effects are associated with follow-up lab tests, and uses the resulting monitoring representations for medication recommendation and disease prediction.

Therefore medication-administration / follow-up-monitoring structure is prior art.

### MedGCN and Bhoi et al. 2023

MedGCN couples medication recommendation with lab-test imputation. Bhoi et al. explicitly integrate medication recommendation and lab-test response prediction.

Therefore generic lab auxiliary, multitask, and future/lab-response prediction are prior art and primary killer-control families.

### DrugDoctor — Briefings in Bioinformatics 2024

DrugDoctor considers the impact of historical prescriptions on downstream patient condition at visit level.

Therefore downstream response evidence after prior medication is already part of MedRec prior art.

### MR-DTR — WWW 2025

MR-DTR establishes time-aware/dynamic-treatment-regime medication recommendation. Generic treatment-dynamics framing is crowded.

### LEADER and IJCAI-ECAI 2026 MedRec KD

LEADER uses feature-level knowledge distillation for medication recommendation. An accepted IJCAI-ECAI 2026 paper, `Dual-Channel Semantic-Enhanced Combinatorial Medication Recommendation via Knowledge Distillation`, independently confirms that MedRec KD is a current CCF-A-level method family.

Therefore KD mechanics cannot carry novelty.

### OC-Distill — 2026

OC-Distill transfers complementary training-time clinical modality information into a reduced-modality ICU student.

Therefore generic clinical privileged-information distillation is established.

### Future-aware blood-glucose forecasting — Scientific Reports 2026

A teacher uses historical CGM plus future insulin/meal disturbances that are unavailable at deployment; a student learns from historical input only through knowledge distillation.

Therefore `clinical future information during training -> deployable history-only student` is already explicit prior art.

### Wu et al. — IEEE EMBC 2025

This work learns medicine-aware patient representations from transient physiological responses to vasoactive infusions.

Therefore medication-conditioned physiological-response representation itself is established outside general MedRec.

### Privileged Foresight Distillation — 2026

PFD uses true future observations in a training-time teacher and distills a future-conditioned correction into a current-only student while explicitly testing capacity/regularization explanations.

Therefore future observation access and future-to-current distillation are not novelty claims.

## Search-scoped residual delta

Within the retained 2023--2026 search, no direct general-MedRec method was found whose central mechanism is exactly:

> use paired realized post-administration physiological **values** only during training to supervise a strictly pre-order candidate-medication student, with response-specific mechanism subtraction.

This is a narrow composition of established primitives. It becomes a meaningful MedRec method contribution only if Gate 01 establishes that the signal is specifically carried by medication-in-context physiological values and pairing.

Novelty status at admission:

`MODERATE / SEARCH-SCOPED / ADMITTED_FOR_ONE_KILL_FIRST_GATE`.

Current status:

`CLOSED_UNDER_IDEA_007_P1_SUPPORT_TERMINATION`.

This is not a universal novelty proof.

## Mandatory future alternatives

The admitted R1--R3 contract freezes:

- matched Generic Future-State Auxiliary / Medication-Ablated Future;
- Monitoring-Mask-Only plus physiological-value versus response-availability separation;
- equal-support positive-only response semantics and strictly pre-order deployment entitlement.

Gate 01 must additionally cover:

- Strict Pre-Order Base;
- Base + Pre-Order Physiology;
- Static Medication Response Prototype;
- Response Shuffle;
- Generic KD (included because the proposed implementation has a live
  teacher/student-alignment alternative);
- Proposed privileged physiological response supervision.

A compatible monitoring-aware MedRec baseline may be included when task alignment supports a fair comparison.

The audited protocol fixes the practical/statistical meaning of `materially`,
`comparable`, and `≈` before any result. The response-specific story terminates if
Generic Future-State Auxiliary, Medication-Ablated Future, Response Shuffle,
Monitoring-Mask-Only, Static Response Prototype, or richer pre-order physiology
performs comparably, or if response support is insufficient/materially
concentrated, the interval is inconclusive, or deployment leakage/unequal
entitlement is detected.

## Claim boundary

Post-administration physiology is observational and confounded by severity, co-medications, procedures, fluids, ventilation, dose/route, clinician actions, spontaneous progression, treatment timing, monitoring policy, and selective measurement.

Allowed framing:

- response-associated physiological signature;
- medication-in-context physiological trajectory;
- privileged physiological response supervision;
- future physiological supervision.

Disallowed without independent causal identification:

- causal drug response;
- individual treatment effect;
- drug efficacy;
- therapeutic benefit;
- counterfactual outcome;
- clinically optimal medication;
- individualized causal benefit.

## Current routing

Current project state:

```text
Idea 007: TERMINATED_AT_GATE_01_P1
Decision: ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE
Active Idea: none
Stage: PRE_IDEA_AFTER_PAIR_CONTEXT_INCREMENTAL_VALUE_TERMINATION
New Idea: NOT CREATED
Experiment: PAIR/CONTEXT PRE-IDEA TERMINATED
Training: FORMAL TRAINING NOT AUTHORIZED; BOUNDED PRE-IDEA PROBES COMPLETE
Quarantine: intact
Next owner: ccf-pipeline-orchestrator
```

No Idea 008 creation, Gate 01, rescue, or work outside the closed Pair/Context
packet is authorized by this map. No new literature search was run for this
update.
