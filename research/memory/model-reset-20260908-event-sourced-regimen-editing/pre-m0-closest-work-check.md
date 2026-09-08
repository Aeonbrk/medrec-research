<!-- markdownlint-disable MD013 -->

# Pre-M0 Closest-Work Check: Event-Sourced Regimen Editing

## Search date

2026-09-08.

## Purpose

This is a bounded collision check before local M0 execution. It is not a universal novelty proof and does not authorize Idea 007.

Question searched:

> Is there already a general medication-recommendation method whose central supervised decision is a strictly causal inpatient provider-order-time `(New / Change / D/C, medication)` mark over the current regimen state, with state-valid edit decoding?

## Closest retained work

### Rough et al. 2020 — order-time medication identity

Source: https://doi.org/10.1002/cpt.1826

Already covers:

- general inpatient medication-order prediction;
- prediction whenever a medication order is placed;
- a 10-minute multilabel horizon;
- use of only pre-order EHR information.

Does not appear to make explicit CPOE action type (`New / Change / D/C`) and state-valid regimen editing the supervised decision object.

### MICRON 2021 — visit-level medication change

Source: https://doi.org/10.24963/ijcai.2021/513

Already covers medication addition/removal prediction from changes between consecutive visits.

Therefore addition/removal or "change matters" is not a novelty claim.

The distinction retained for M0 is raw within-admission provider-order transaction marks and strictly causal event-sourced regimen state rather than visit-snapshot differencing.

### ARMR 2025 — new versus historical medication at visit level

Source: https://doi.org/10.24963/ijcai.2025/871

Already covers adaptive weighting between new medication needs and historical medication reuse.

Therefore new-versus-existing medication handling is not itself a novelty claim.

### HeteroMed 2026 — expansion/inheritance

Source: https://doi.org/10.1007/s13755-026-00430-5

Already covers visit-level collaborative drug expansion/inheritance and medication increases/decreases.

Therefore prescription expansion/inheritance is not a novelty claim.

### Generic continuous-time / marked-event modeling

Continuous-time decision models and marked temporal point-process methods already model irregular clinical/treatment event sequences. Recent general event-sequence work also provides strong MTPP and long-horizon baselines.

Examples:

- Continuous-Time Decision Transformer for Healthcare Applications: https://pmc.ncbi.nlm.nih.gov/articles/PMC10907982/
- HoTPP benchmark, Neurocomputing 2026: https://doi.org/10.1016/j.neucom.2026.132771

Therefore "use a marked temporal point process" or "model continuous time" cannot be the novelty claim of a future Idea.

## Additional narrow 2026 search

Queries combining medication recommendation/order prediction with:

- `transaction_type`;
- `New / Change / D/C`;
- discontinue/change medication actions;
- regimen editing;
- marked temporal point processes;

surfaced generic medication-recommendation models, generic clinical-action/point-process models, medication-discontinuation workflow studies, and Rough et al.'s order-time medication prediction. No retained close work was found that collapses the full M0 combination into the same general MedRec method problem.

This is a search-scoped negative finding only.

## Current collision verdict

`NO_CLOSE_COLLISION_FOUND_IN_BOUNDED_PRE_M0_SEARCH`

The narrow candidate delta remains:

> explicit raw provider-order action marks + strictly causal current regimen state + state-valid edit decoding + learned action-medication structure beyond an equal-entitlement direct mask control.

## Remaining novelty risk

Novelty confidence remains `MODERATE`, not high.

If M0 passes, a final strict closest-work review must search at least:

- medication-change recommendation;
- order-entry prediction;
- next clinical action prediction;
- medication discontinuation/change prediction;
- marked temporal point-process healthcare models;
- state-transition/set-edit recommendation;
- 2025--2026 MedRec papers and proceedings.

A future method must not claim novelty for visit-level changes, order-time prediction, continuous-time modeling, or MTPP usage separately.

## Routing implication

The current literature check is sufficient only to justify running the cheap M0 premise gate.

It is not sufficient to create Idea 007.
