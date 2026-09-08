<!-- markdownlint-disable MD013 -->

# Literature Opportunity Map

## Current status

Refresh date: 2026-09-08.

Current project stage:

`PRE_IDEA_EVENT_EDIT_M0`

There is no active Idea. Ideas 001--006 are terminated. Idea 007 is not created or authorized.

Current bounded reset packet:

[`model-reset-20260908-event-sourced-regimen-editing/`](model-reset-20260908-event-sourced-regimen-editing/).

## Closed or compressed spaces

| Space | Current judgment | Main reason |
| --- | --- | --- |
| Frozen-output feature/routing variants | `CLOSED` | Ideas 001--004 + EGSF; strong-control absorption |
| ATC sibling therapeutic substitution | `CLOSED` | Idea 005 semantic admission failure |
| Count-mediated safety/coverage | `CLOSED` | B0 normalized-DDI result |
| Selective prescription supervision | `NOT ADMITTED` | latent acceptable-treatment target not identifiable |
| Exposure-conditioned DDI learning | `CLOSED under Idea 006` | learned method failed equal-entitlement direct-reranker challenge |
| Residual temporal-practice adaptation | `CLOSED under S0` | no material forward degradation; target-era Recall was higher than source-era Recall |
| Generic longitudinal modeling | `CROWDED` | MR-DTR, DrugDoctor, HeteroMed, ChainCare, DMRNet and related work |
| Generic KG/RAG/agent safety | `CROWDED` | KATMed, RES-MR, SafeRx-Agent, ATLAS and related work |
| Generic finer action granularity | `CROWDED / HIGH COST` | FineMed, GRAIN, SafeRx-Agent, RxEval |
| Multi-dataset MIMIC/eICU results | `PRIOR ART` | HypeMed, KATMed, Rx-Expert, NLA-MMR |
| Temporal/external validation itself | `PRIOR ART` | prior clinical recommender studies already report it |
| Visit-level medication-change modeling | `PRIOR ART` | MICRON, ARMR, HeteroMed |
| Order-time medication-identity prediction | `PRIOR ART` | Rough et al. 2020 |

## S0 closure

The prior selected opportunity, residual medication-transition practice shift, did not survive its project-local admission gate.

Under the frozen source/target protocol:

- `R_source = 0.4310427829`;
- `R_target_base = 0.4403698933`;
- `G_base = -0.0093271104`, 95% CI `[-0.0145853913, -0.0035238892]`;
- `R_target_bias = 0.4441638446` after the frozen target-prior correction.

There was no positive forward-degradation gap to adapt to. The route is therefore closed under the frozen setting without S0b, alternative year groups, or eICU rescue.

Failure memory:

[`failures/medication-practice-shift-s0--no-material-forward-degradation.md`](failures/medication-practice-shift-s0--no-material-forward-degradation.md).

## Current selected opportunity: event-sourced regimen editing

### Project-local structural evidence

The existing raw order-time infrastructure already records provider-order transaction types `New`, `Change`, and `D/C`, reconstructs strictly pre-order medication state, and encodes transaction types in the historical sequence.

The current supervised target nevertheless collapses present `New` and `Change` orders to medication-only labels and excludes present `D/C` from the target.

This is a concrete candidate information/decision-structure loss rather than a request for a larger encoder.

### Closest work

#### Rough et al. 2020

Stable source: https://doi.org/10.1002/cpt.1826

Rough et al. predict inpatient medication orders at the moment an order is placed using a 10-minute multilabel horizon and only information available before the order. This already covers order-time medication-identity prediction.

It does not make explicit `New / Change / D/C` regimen-edit marks and causal state-valid action decoding the target method problem.

#### MICRON — Change Matters

Stable source: https://doi.org/10.24963/ijcai.2021/513

MICRON predicts medication additions and removals from changes between consecutive visits. Medication change prediction itself is therefore prior art.

Its change semantics are derived from visit snapshots rather than raw provider-order transaction marks, and the decision unit is visit-level rather than within-admission order-time.

#### ARMR

Stable source: https://doi.org/10.24963/ijcai.2025/871

ARMR adaptively balances new medications and reuse of historical medications at the visit level. New-versus-existing medication reasoning is therefore not a novelty claim by itself.

It does not make raw `Change / D/C` order marks or event-sourced regimen editing the supervised decision object.

#### HeteroMed

Stable source: https://doi.org/10.1007/s13755-026-00430-5

HeteroMed models collaborative drug expansion/inheritance and prescription increases/decreases across visits. Expansion/inheritance is therefore also prior art.

Its action semantics are inferred from prescription-set evolution rather than the raw within-admission order transaction stream.

### Search-scoped gap

The retained closest work covers either:

1. **visit-level medication changes**, or
2. **order-time medication identity**.

The under-tested intersection is:

> strictly causal, provider-order-time recommendation of explicit `(action, medication)` regimen edits from an event-sourced current medication state.

This is a search-scoped opportunity, not a final novelty proof. A strict final closest-work search is mandatory after M0 PASS and before Idea 007.

## Why a new model can be justified here

A new model is acceptable because the candidate contribution is not the backbone name. The potential method object is different:

- irregular medication-order event stream;
- explicit action-medication target marks;
- causal regimen state;
- state-valid action decoding;
- structured parameter sharing across action types and medications.

If that structure has incremental value, a later Idea may justify a purpose-built state-transition or marked-event architecture. If it does not, building such an architecture would be architecture fishing.

## Strongest trivial explanation

A deterministic active-state mask may explain nearly all benefit from preserving action labels.

Therefore the mandatory killer control is:

`SeparateHeads + DirectStateMask`.

It receives the same history, current regimen state, action labels, and deterministic state-valid mask as the structured probe.

## Current gate

`M0 — Event-Sourced Regimen-Edit Admission`.

Protocol:

[`model-reset-20260908-event-sourced-regimen-editing/m0-event-edit-admission-protocol.md`](model-reset-20260908-event-sourced-regimen-editing/m0-event-edit-admission-protocol.md).

M0 is one bounded investment gate, not publication evidence.

### PASS

`PASS_M0_EVENT_EDIT_STRUCTURE`.

Then route only this surviving family to `ccf-idea-optimizer`, followed by strict `ccf-idea-reviewer`. Idea 007 may be created only after that review admits a genuine method contribution.

### FAIL

`FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`.

Then return to `NO_HIGH_VALUE_DIRECTION_YET` without M0b or deeper-encoder rescue.

## Stable source links

- Rough et al. order-time medication prediction: https://doi.org/10.1002/cpt.1826
- MICRON: https://doi.org/10.24963/ijcai.2021/513
- ARMR: https://doi.org/10.24963/ijcai.2025/871
- HeteroMed: https://doi.org/10.1007/s13755-026-00430-5
- HypeMed: https://doi.org/10.1145/3803851
- KATMed: https://doi.org/10.1016/j.jbi.2026.104991
- NLA-MMR: https://doi.org/10.1145/3627673.3679529
- DMRNet: https://doi.org/10.1016/j.neunet.2026.109168
- MIMIC-IV data paper: https://doi.org/10.1038/s41597-022-01899-x
