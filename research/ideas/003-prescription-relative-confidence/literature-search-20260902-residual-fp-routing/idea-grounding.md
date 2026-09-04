<!-- markdownlint-disable MD013 MD036 -->

# Idea Grounding — Residual False-Positive Routing Beyond Frozen Score

## Residual research question

$$
\boxed{\text{What target-free observable information, not reducible to }s_t(m),\text{ explains residual false-positive heterogeneity among DDI-active predicted medications?}}
$$

Candidate universe and action semantics remain intentionally narrow:

$$
\mathcal Q_t=\{m\in\hat M_t:d_t(m)>0\},
$$

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\},
$$

and therefore within this universe

$$
Y^{PB}_{t,m}=\mathbf1[m\notin M_t].
$$

## Evidence cards

### Confidence and boundary

**Source-supported observations**

- KDD 2025 explicitly studies medication-level confidence calibration and introduces a binning-based confidence method. Confidence itself is therefore not an untouched research object.
- GiantMed (KDD 2026) uses a deep model's absolute probability boundary to choose medications for local LLM refinement. “Boundary medications deserve verification” is already prior art.
- A 2026 antibiotic-optimization study explicitly reports Top1-Top2 probability margin as a relative-confidence measure, although in a single-choice treatment setting rather than multi-label medication-candidate routing.

**Optimizer inference**

The remaining narrow opening is not “confidence matters” or “relative confidence is new.” It is whether a medication's within-prescription relative position contains incremental error information after conditioning on the medication's own frozen confidence and trivial prescription-level confounds.

### Longitudinal medication actions

**Source-supported observations**

COGNet, KERL, HeteroMed, and DMRNet all make historical medications operational: copy/predict, continuation/inheritance, temporal recalibration, or separate historical-medication pathways.

**Optimizer inference**

A binary previous-prescription-membership signal remains cheap to test, but the scientific novelty of “continuation vs new” is weak. It can still be useful as a control or diagnostic; it is not the strongest new Idea by itself.

### Medication-set / co-selection relations

**Source-supported observations**

MSAM models collective medication effects; DMRNet mines frequent prescription patterns; GenRxR explicitly models co-recommended medications.

**Optimizer inference**

A train-only scalar compatibility statistic could still test whether set support explains false-positive routing conditional on confidence. The novelty would have to be the *confidence-conditional error-routing question*, not medication-combination modeling. This route is more prior-art exposed than prescription-relative confidence.

### Patient/history context

**Source-supported observations**

HypeMed, KERL, HeteroMed, DMRNet, and related 2026 work already exploit longitudinal or retrieved context for recommendation.

**Optimizer inference**

“Add patient history” is not a sufficiently sharp hypothesis. Any future history route should begin with one observable such as previous-prescription membership before an encoder is justified.

### Cross-model corroboration

**Source-supported observations**

Multi-LLM Collaboration for Medication Recommendation explores ensemble collaboration, stability, and calibration. General selective-prediction literature also treats ensembles/disagreement as uncertainty signals.

**Optimizer inference**

Frozen-backbone disagreement conditional on a primary model score remains distinguishable from LLM collaboration, but the central novelty risk is severe: a reviewer may interpret any gain as ordinary ensemble improvement rather than a new disagreement mechanism. It also costs more than a one-backbone observable.

## Cross-source opportunity map

| Candidate information | Why it may contain new information | Strongest prior-art pressure | Cheapest honest test |
| --- | --- | --- | --- |
| within-prescription relative confidence position | depends on other predicted medication scores in the same visit, not only $s_t(m)$ | KDD'25 calibration; GiantMed boundary; Top1-Top2 relative confidence in single-choice antibiotic optimization | add one rank-percentile scalar to a score + set-size + train-frequency control |
| train-only co-selection compatibility | depends on which medications are co-predicted and historical co-prescription structure | MSAM, DMRNet, GenRxR | one smoothed train-only compatibility scalar versus score + size + medication frequency |
| previous-prescription membership | distinguishes continuation from newly proposed medication | COGNet, KERL, HeteroMed, DMRNet | one binary bit versus score + train frequency |
| cross-backbone corroboration | uses independent model evidence unavailable to primary score | ensemble/selective prediction; Multi-LLM Collaboration | vote count or normalized-score dispersion versus best simple ensemble |

## Grounded selection implication

The minimum-information candidate is the best next falsification target because it adds exactly one observable derived from the frozen prediction set, needs no new model, can face an unusually strong simple control, and is cheap to kill before any architecture investment.

The key claim must remain narrow:

$$
\text{conditional on frozen }s_t(m),\text{ prescription size, and train-only medication prevalence, }r_t(m)\text{ carries reproducible incremental information about }Y^{PB}_{t,m}.
$$

where $r_t(m)$ is a within-prescription relative confidence statistic defined without target labels.

## Novelty uncertainty

Within the current search scope, no direct multi-label MedRec study was found that performs this conditional medication-level FP-routing test. This is not a proof of global novelty. The most important overlap challenge is whether the proposal will be read as a small variant of existing confidence calibration/boundary selection; the decisive differentiation is the conditional *within-prescription* observable and held-out incremental-information claim, not a new calibration formula.
