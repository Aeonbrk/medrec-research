<!-- markdownlint-disable MD013 -->

# Strict Pre-Idea Review — Exposure-Conditional Medication Recommendation

## Verdict

`ACCEPT_TO_DEVELOP / RESOURCE_ADMISSION_REQUIRED`

**Do not create Idea 006 yet.**

Weighted score: **4.04 / 5.00**.

Current conference readiness: **medium-low** because the required raw MIMIC-IV execution resource has not been admitted.

Development potential: **high** if R0 confirms linkability, vocabulary support, and a material static-versus-executed DDI mismatch.

Target assumption: generic CCF-A AI/data-mining method venue family; the final paper must be method-dominant rather than benchmark-only.

## Search basis

Current public search covered:

- order-time inpatient medication prediction;
- safe MedRec with static DDI regularization, contraindication rules, medication-history dynamics, and finer medication granularity;
- MIMIC-IV prescription/order versus eMAR administration semantics;
- time-dependent and contextualized DDI clinical decision support;
- recent temporal-leakage criticism in medication recommendation.

No searched recent MedRec work was found with actual-administration / executed-active exposure as the central DDI conditioning state for order-time recommendation. This is provisional closest-work confidence, not a claim of exhaustive novelty.

## Normalized idea

Problem: visit-level medication sets make static DDI co-membership stand in for current interaction applicability.

Insight: medication safety at order time is a state-transition problem; a known DDI pair is relevant only relative to the medications currently active/executed, not medications that appear elsewhere in the hospitalization.

Method family: order-time predictor plus exposure-conditional DDI regularization using only pre-order executed-active medication state.

Primary claim: improved medication-order fidelity at matched **exposure-localized DDI surrogate**, compared with both static-DDI learning and direct use of the same dynamic risk signal.

Scope boundary: no ADE, optimal-treatment, or clinical-safety claim from binary DDI/eMAR alone.

## Closest prior art

| Prior | Overlap | Remaining delta | Risk |
| --- | --- | --- | --- |
| Rough et al. 2020 inpatient medication-order prediction | Same order-time prediction paradigm and pre-order-only EHR | Adds dynamic safety semantics; order-time task itself is not claimed novel | High if framing drifts to task novelty |
| SafeDrug / current static-DDI MedRec family | Differentiable DDI pressure | DDI pressure becomes state-conditional on executed-active regimen rather than predicted visit-set pair union | High |
| KATMed 2026 | Differentiable clinical constraints | Condition is active medication exposure, not drug-disease contraindication | Medium-high |
| HeteroMed 2026 | Dynamic medication change plus expected DDI regularizer | DDI applicability itself becomes time-local/execution-conditioned | Medium |
| SafeRx-Agent / GRAIN 2026 | Safety granularity and verification | Proposed delta is temporal applicability, not finer code/ingredient granularity | Medium |
| Contextualized DDI CDS literature | Uses active/concomitant exposure, timing, stopped drugs, labs, workflow context | Proposed contribution learns medication recommendation under that state rather than only firing/suppressing alerts | High; direct-rule baseline mandatory |

## Expert panel

### Field expert

Best argument: the route attacks a real semantic mismatch between visit-set MedRec and order-time medication safety. Clinical CDS literature independently shows that pairwise DDI alerts can be inapplicable when administrations are separated or one drug has stopped.

Rejection-grade concern: if the cohort-level mismatch is small, the paper becomes an elaborate task rebuild with no material scientific consequence.

Repair condition: R0 must demonstrate substantial visit-union DDI mass that does not correspond to execution-confirmed concurrent active medication periods.

### Method expert

Best argument: the method changes the optimization state rather than adding another encoder. The new state has a direct causal role in which negative safety gradients are applied.

Rejection-grade concern: `BCE + dynamic DDI penalty` can look like a trivial substitution of one risk matrix for another.

Repair condition: end-to-end exposure-conditioned learning must beat a post-hoc exposure-risk reranker and hard filter at matched exposure-DDI operating points; otherwise the learned method has no value beyond direct rule application.

### Experiment expert

Best argument: both task target and safety surrogate are mechanically testable without pretending eMAR is clinical ground truth.

Rejection-grade concern: raw order/eMAR linkage, medication normalization, eMAR rollout coverage, and patient-level temporal splitting may dominate the project cost.

Repair condition: a single Discovery-only R0 must show adequate scale and mapping before any model work. Freeze a new Holdout before examining premise aggregates.

### AC / venue expert

Best argument: a clear assumption shift plus a simple architecture-agnostic method could be attractive to KDD/WWW/AAAI/IJCAI reviewers if it changes how safe MedRec is formulated and survives strong controls.

Rejection-grade concern: without strong method evidence it may be read as dataset engineering plus a standard regularizer.

Repair condition: final paper must show a nontrivial interaction between exposure semantics and learning across more than one predictor family, with the direct-rule control explicitly leveled.

### Skeptical prior-art expert

Best argument: current search finds the two ingredients in separate literatures—order-time medication prediction and contextual DDI CDS—but not their central combination in recent MedRec.

Rejection-grade concern: reviewers can still summarize it as "Rough 2020 + dynamic SafeDrug loss".

Repair condition: define the exact failure of static-DDI training, show it is material, and show direct dynamic reranking cannot reproduce the end-to-end result.

### Dataset / reproducibility expert

Best argument: MIMIC-IV explicitly separates medication requests from actual eMAR administrations and provides direct linkage fields.

Rejection-grade concern: eMAR deployment was phased in, medication identifiers are heterogeneous, and a cohort conditioned on eMAR availability can introduce a nontrivial setting shift.

Repair condition: R0 reports coverage/linkage/mapping distributions and freezes the population definition before model development.

## Rubric

| Dimension | Weight | Score | Confidence | Main deduction | Repair condition |
| --- | ---: | ---: | ---: | --- | --- |
| Problem importance | 12 | 5 | 4 | None material at idea stage | Show cohort-level mismatch |
| Novelty against likely prior work | 14 | 4 | 3 | Intersection novelty; ingredients individually established | Final closest-work search after R0 |
| Conceptual innovation | 12 | 4 | 4 | Strong assumption shift, but method may remain simple | Show learning-specific effect beyond direct rule |
| Method soundness | 14 | 4 | 3 | Executed-active state is operational, not physiological exposure | Keep surrogate claim narrow; robust state definition |
| Elegance and simplicity | 8 | 4 | 4 | Risk of adding unnecessary patient-state machinery | Keep central method objective-level |
| Feasibility under resources | 8 | 3 | 4 | New raw MIMIC-IV pipeline and normalization required | R0 resource admission |
| Experimental convincibility | 10 | 4 | 3 | New task needs strong controls and holdout discipline | Freeze split and direct-rule controls |
| Venue and audience fit | 8 | 4 | 3 | Could be seen as clinical application/data work | Multi-backbone method evidence |
| Timeliness and topic heat | 6 | 4 | 4 | Safe MedRec is crowded | Lead with semantic mismatch, not safety buzzwords |
| Risk-adjusted acceptance potential | 8 | 4 | 3 | Data cost and trivial-loss objection remain | R0 pass plus learned-vs-direct gap |

Weighted score:

$$
\frac{404}{100}=4.04/5.
$$

The score is a development decision aid, not an acceptance probability.

## Fatal gate before Idea creation

Run exactly one `R0 — Exposure Resource & Premise Admission`.

R0 failure terminates this route without method implementation.

R0 pass authorizes Idea 006 creation and handoff to `ccf-experiment-designer` for one minimal learned-vs-direct-control Gate 01.

## What would lower the score materially

- fewer than a practically useful number of linked medication-order / execution events after deterministic normalization;
- no material difference between visit-union DDI occurrences and executed-active DDI occurrences;
- a medication vocabulary too small or skewed to support a general medication-recommendation claim;
- a newly found recent paper with the same order-time executed-exposure safety objective.

## What would raise the score

- R0 demonstrates a large, distributed semantic mismatch with stable medication mapping;
- the method remains simple and architecture-agnostic;
- direct exposure-aware reranking/filtering is strong but leaves measurable headroom for end-to-end exposure-conditioned learning;
- the effect reproduces across two substantially different prediction backbones without relaxing the safety surrogate.
