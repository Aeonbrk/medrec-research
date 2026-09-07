<!-- markdownlint-disable MD013 -->

# Literature Opportunity Map

## Current status

Refresh date: 2026-09-08.

Current project stage:

`PRE_IDEA_PRACTICE_SHIFT_S0`

There is no active Idea. Idea 006 terminated at Gate 01 with:

`STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`.

Current bounded reset packet:

[`literature-search-20260908-medication-practice-shift/`](literature-search-20260908-medication-practice-shift/).

## Closed or compressed spaces

| Space | Current judgment | Main reason |
| --- | --- | --- |
| Frozen-output feature/routing variants | `CLOSED` | Ideas 001--004 + EGSF; strong-control absorption |
| ATC sibling therapeutic substitution | `CLOSED` | Idea 005 semantic admission failure |
| Count-mediated safety/coverage | `CLOSED` | B0 normalized-DDI result |
| Selective prescription supervision | `NOT ADMITTED` | latent acceptable-treatment target not identifiable |
| Exposure-conditioned DDI learning | `CLOSED under Idea 006` | learned method failed equal-entitlement direct-reranker challenge |
| Generic longitudinal modeling | `CROWDED` | MR-DTR, DrugDoctor, HeteroMed, ChainCare, DMRNet and related work |
| Generic KG/RAG/agent safety | `CROWDED` | KATMed, RES-MR, SafeRx-Agent, ATLAS and related work |
| Generic finer action granularity | `CROWDED / HIGH COST` | FineMed, GRAIN, SafeRx-Agent, RxEval |
| Multi-dataset MIMIC/eICU results | `PRIOR ART` | HypeMed, KATMed, Rx-Expert, NLA-MMR |
| Temporal/external validation itself | `PRIOR ART` | narrow clinical recommender studies already report it |

## Idea 006 update

R0's resource result remains useful: actual order/eMAR timing demonstrates that static hospitalization DDI co-membership and execution-confirmed overlap differ materially.

But Gate 01 showed that changing this safety-state semantic did not produce the required incremental learned value. The equal-entitlement direct exposure reranker retained higher medication-order fidelity than the learned ExposureConditional model at the frozen comparison.

Therefore the project must not treat a valid measurement/premise as a method contribution.

## Current selected opportunity: medication-transition practice shift

### Source-supported background

Current MedRec papers increasingly report multiple datasets:

- HypeMed: MIMIC-III, MIMIC-IV, eICU; describes eICU as cross-institutional generalization.
- KATMed: MIMIC-III/MIMIC-IV plus partial external eICU validation and acknowledges practice-pattern/case-mix/coding differences.
- Rx-Expert: MIMIC-III/MIMIC-IV/eICU.
- NLA-MMR: three public datasets.

This means "we also test on eICU" is not a publishable novelty delta.

A 2025 schizophrenia-spectrum medication recommender additionally reports true temporal/geographic validation degradation, so temporal degradation itself is also not novel.

MIMIC-IV, however, provides `anchor_year_group` specifically to enable analyses of changes in medical practice over time. This supplies a low-cost chronological environment for a premise test.

### Search-scoped gap

Within the retained search, no close **general** medication-recommendation method was found whose central problem is:

> source-era medication recommendation -> future prescribing environment -> distinguish marginal medication-prior shift from residual conditional medication-transition shift -> adapt the model only if that residual is real.

This is not a universal novelty claim.

### Strongest trivial explanation

DMRNet and broader medication-frequency evidence make one control mandatory:

> changed medication marginals alone may explain the apparent temporal degradation.

Therefore a per-medication target-prior/logit-bias adjustment must be tried before any adaptation method is admitted.

## Current gate

`S0 — Medication Practice-Shift Admission`

Protocol:

[`literature-search-20260908-medication-practice-shift/s0-practice-shift-admission-protocol.md`](literature-search-20260908-medication-practice-shift/s0-practice-shift-admission-protocol.md).

S0 is not publication evidence. It is a single investment gate.

### PASS

`PASS_S0_RESIDUAL_MEDICATION_PRACTICE_SHIFT`

Then route the single surviving family to `ccf-idea-optimizer`, followed by strict idea review. Generic fine-tuning, generic domain adaptation, and generic continual learning are mandatory collision/baseline families.

### FAIL

`FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`

Then return to `NO_HIGH_VALUE_DIRECTION_YET` without temporal-split rescue or Idea 007.

## Stable source links

- HypeMed: https://doi.org/10.1145/3803851
- KATMed: https://doi.org/10.1016/j.jbi.2026.104991
- NLA-MMR: https://doi.org/10.1145/3627673.3679529
- DMRNet: https://doi.org/10.1016/j.neunet.2026.109168
- Rough et al. order-time prediction: https://doi.org/10.1002/cpt.1826
- MIMIC-IV data paper: https://doi.org/10.1038/s41597-022-01899-x
- Temporal-leakage appraisal: https://doi.org/10.1016/j.jbi.2026.105016
- Schizophrenia recommender temporal/external validation: https://doi.org/10.1186/s12888-025-07657-8
