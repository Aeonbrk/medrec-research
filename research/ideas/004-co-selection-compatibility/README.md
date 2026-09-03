<!-- markdownlint-disable MD013 -->

# Idea 004: Frequency-Corrected Co-Selection Compatibility

- **Idea ID**: `004-co-selection-compatibility`
- **Status**: `SELECTED / GATE_01_NOT_YET_DESIGNED`
- **Scientific stage**: Post-negative-result hypothesis selection
- **Target venue assumption**: generic CCF-A AI/ML/KDD-family target
- **Literature grounding**: `literature-search-20260903-co-selection-fp-routing/`
- **Strict idea review**: [`idea-review.md`](idea-review.md)
- **Next CCFA owner**: `ccf-experiment-designer / design`

## Problem statement

Ideas 001--003 closed three specific medication-level false-positive routing routes under frozen MoleRec: active-DDI-degree/Tension, a preregistered five-bin score-only geometry map, and within-prescription relative confidence mid-rank. None established reproducible incremental routing information beyond its strongest frozen control.

The cumulative evidence does not show that static, relational, longitudinal, or patient-conditioned information is exhausted. Substantial retrospective `Oracle - StrongControl` headroom remains, but Oracle uses the current target and therefore does not establish that a target-free explanation exists.

## Residual question

$$
\boxed{\begin{aligned}
&\text{What target-free observable information, not already tested in Ideas 001--003,}\\
&\text{explains medication-level false-positive heterogeneity beyond the strongest simple control?}
\end{aligned}}
$$

## Falsifiable hypothesis

Let the frozen predicted prescription at visit $t$ be $\hat M_t$, with $n_t=|\hat M_t|$. For each medication pair $(m,j)$, compute a frequency-corrected co-selection relation using **training prescriptions only**.

For the eligible training-visit universe $\mathcal T_{train}$ of size $V_{train}$, define counts

$$
C(m)=\sum_{v\in\mathcal T_{train}}\mathbf1[m\in M_v],
$$

and

$$
C(m,j)=\sum_{v\in\mathcal T_{train}}\mathbf1[m\in M_v\land j\in M_v].
$$

Use Laplace-smoothed Bernoulli probabilities

$$
p_{train}(m)=\frac{C(m)+1}{V_{train}+2},
$$

$$
p_{train}(m,j)=\frac{C(m,j)+1}{V_{train}+2}.
$$

Define pairwise normalized pointwise mutual information

$$
\operatorname{NPMI}_{train}(m,j)=
\frac{
\log\frac{p_{train}(m,j)}{p_{train}(m)p_{train}(j)}
}{
-\log p_{train}(m,j)
}.
$$

For candidate $m\in\hat M_t$, define the exact proposed observable

$$
A_t(m)=\frac{1}{n_t-1}\sum_{j\in\hat M_t\setminus\{m\}}
\operatorname{NPMI}_{train}(m,j).
$$

The frozen candidate universe guarantees $n_t\ge2$.

The hypothesis is:

$$
\boxed{\text{Conditional on frozen medication confidence and trivial set/popularity controls, }A_t(m)\text{ provides reproducible incremental information about }Y^{PB}_{t,m}.}
$$

## Exact observable

`CoSelectionCompatibility` = $A_t(m)$, the mean train-only pairwise NPMI between candidate $m$ and every other medication in the same frozen predicted prescription.

Higher values mean that the candidate is, on average, more compatible with its co-predicted medications under frequency-corrected historical co-selection structure. The Gate may learn either coefficient sign on Dev; no outcome-direction claim is hard-coded.

## Why this information is new relative to prior controls

Ideas 001--003 tested DDI degree/Tension, score-only remapping, and same-visit relative score position. `CoSelectionCompatibility` instead observes **medication identities plus train-only medication-medication co-selection relations**.

Two candidates can have the same frozen score, prescription size, medication prevalence, and relative score position while receiving different $A_t(m)$ because their co-predicted medication identities differ and the train-only pair relations differ.

This is materially new information relative to the tested selector controls. It is not claimed to be a new information source for medication recommendation generally: co-prescription relations are established prior art.

## Mechanism

A frozen recommender can assign a medication high individual confidence while the medication remains weakly coherent with the rest of the simultaneously predicted regimen under empirical training-prescription relations. Frequency correction separates pair association from the simpler explanation that common medications co-occur often because they are common.

The narrow mechanism is therefore:

> residual medication-level false positives may be enriched among candidates whose predicted-set membership is relationally atypical after accounting for candidate confidence, prescription size, candidate prevalence, and peer-set popularity.

This is an error-routing hypothesis, not a claim that co-selection represents therapeutic synergy or clinical appropriateness.

## Closest prior work

The closest-work search identifies substantial relation-modeling prior art:

- HI-DR, AAAI 2025, DOI `10.1609/aaai.v39i11.33301`: uses a weighted EHR Graph+ to represent how strongly medications are co-prescribed and combines it with health-status-aware evidence.
- DMRNet, Neural Networks 2026, DOI `10.1016/j.neunet.2026.109168`: mines frequent medication patterns and uses temporal prescription recalibration.
- MSAM, arXiv `2601.19259`: models collective medication effects and medication-set abstractions.
- GenRxR, RecSys 2026, DOI `10.1145/3773078.3831753`, arXiv `2607.24829`: explicitly models co-recommended medication relations for rare-med recommendation.
- GRAIN, arXiv `2608.00098`: includes an EHR-derived co-prescription graph alongside drug- and ingredient-level DDI knowledge.
- CRHP, IEEE JBHI, DOI `10.1109/JBHI.2025.3582393`: uses covariance knowledge graphs and hierarchical prescription inference.

These works make generic claims such as “medication relations improve recommendation” non-novel for this project.

## Novelty delta

Within the completed search scope, no retained work directly tests the following decision problem:

```text
frozen medication score
+ prescription-size / medication-popularity / peer-popularity controls
vs.
those same controls + one frequency-corrected train-only co-selection statistic
```

with medication-level false-positive routing as the decision unit, a patient-disjoint Dev/Audit validation split, and held-out incremental review yield as the central claim.

This is search-scoped wording, not a universal novelty claim. The proposed NPMI statistic itself is not novel.

## Strongest simple control

Gate 01 must begin with the strongest simple explanation of the proposed relation statistic. The primary control must include:

- frozen MoleRec medication confidence;
- frozen predicted prescription size;
- train-only candidate-medication prevalence;
- mean train-only prevalence of the other medications in the frozen predicted prescription;
- only the minimal score interactions needed to prevent the relation feature from standing in for those quantities.

The augmented selector may add exactly one scientific feature: `CoSelectionCompatibility`.

No GNN, Transformer, Mamba, LLM verifier, learned relation encoder, or new backbone is justified by Idea selection.

## Candidate universe

The scientific formalization remains unchanged:

$$
\mathcal Q_t=\{m\in\hat M_t:d_t(m)>0\}.
$$

## Revision operator

Singleton deletion remains fixed:

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\}.
$$

Within $\mathcal Q_t$, deletion removes at least one active DDI edge. The retrospective Gate outcome therefore remains

$$
Y^{PB}_{t,m}=\mathbf1[m\notin M_t].
$$

This is a benchmark false-positive label under the frozen operator, not a clinical-safety or treatment-benefit label.

## Target-free contract

Allowed at prediction/revision time:

- frozen MoleRec score for the current candidate;
- frozen MoleRec predicted medication set for the current visit;
- predicted medication count;
- train-only medication prevalence;
- train-only pairwise co-selection counts/probabilities and the frozen NPMI relation derived from them;
- DDI graph only to reproduce the already frozen candidate universe $\mathcal Q_t$.

Forbidden selector inputs:

- membership in the current target prescription;
- current-visit outcome labels;
- future visits or future prescriptions;
- Dev/Audit target-derived pair statistics;
- Audit labels for fitting, cutpoints, feature selection, or coefficient selection;
- any test data, test targets, test predictions, or test-derived statistics;
- Idea 001 Tension features, Idea 002 score bins, or Idea 003 relative-rank cosmetic variants as rescue features.

## Prediction-time availability

Yes. The current predicted set and scores are frozen model outputs. The co-selection matrix and medication prevalences are computed once from the training split and frozen before validation evaluation.

## Leakage boundary

Training target prescriptions may define aggregate train-only prevalence and pair statistics. They may not be joined to validation target prescriptions.

Dev labels may fit the preregistered low-capacity control and augmented selector. Audit labels may only evaluate already frozen selectors. The test split remains unindexed, unpredicted, and untouched.

## Cheapest decisive experiment

One validation-only Gate 01:

1. reproduce or identity-verify the frozen validation prediction payload without accessing test;
2. compute train-only prevalence and pairwise NPMI once;
3. create a fresh deterministic patient-disjoint Idea-004 Dev/Audit split chosen before outcome inspection;
4. fit the low-capacity strongest simple control on Dev;
5. fit the identical model with exactly one additional $A_t(m)$ feature on Dev;
6. freeze both selectors;
7. compare Audit Pareto-beneficial yield at preregistered review budgets using patient-clustered bootstrap uncertainty.

## PASS semantics

PASS means only:

> Under the frozen MoleRec validation setting and preregistered controls, mean train-only frequency-corrected co-selection compatibility contains reproducible incremental medication-level false-positive routing information beyond frozen score and trivial set/popularity explanations.

## FAIL semantics

FAIL means:

> The preregistered one-scalar train-only co-selection-compatibility route did not establish incremental medication-level false-positive routing information beyond the frozen strongest simple control.

FAIL terminates this representation. It does not authorize replacing NPMI with embeddings, frequent-pattern mining, a hypergraph, attention, or a learned relation model on the same information after inspecting the outcome.

## What PASS would not prove

PASS would not prove clinical safety, patient benefit, therapeutic compatibility, causal mechanism, prescribing correctness, prospective utility, untouched final generalization, or that co-selection relations are novel in MedRec. It would not prove that NPMI is the optimal relation statistic.

## What FAIL would not prove

FAIL would not prove that all medication relations are useless, that all static observables are exhausted, that longitudinal history is useless, that DDI topology is useless, that patient-conditioned evidence is useless, or that no target-free explanation of residual heterogeneity exists.

## Portability

The statistic is backbone-agnostic for multi-label recommenders whose medication vocabulary can be aligned to a train-only prescription corpus and whose current predicted set is exposed. Cross-backbone empirical portability is a later question and is not part of Gate 01.

## Known limitations

- The Gate remains retrospective and validation-only.
- Co-prescription association is observational and can encode historical prescribing practice or bias; it must not be interpreted as therapeutic synergy.
- MoleRec already learns from EHR-derived information, so a PASS would show that an explicit relation statistic retains residual predictive information after the frozen score, not that the raw data source was absent from the backbone.
- The closest-work neighborhood is dense. The novelty claim depends on the conditional medication-level error-routing formulation, not on co-prescription modeling itself.

## Historical validation adaptivity

Validation data has already been used for route selection in Ideas 001--003. A fresh Idea-004 patient-disjoint Dev/Audit partition can provide held-out **route-selection evidence** only. It must not be described as untouched final-generalization evidence.

The test split remains reserved for a later, explicitly authorized stage.

## Stop boundary

Gate 01 is the only authorized next scientific experiment after protocol freeze. No architecture expansion, test evaluation, multi-backbone benchmark, Gate 02, or Idea 005 is implied by Idea selection.

## Next CCFA owner

`ccf-experiment-designer / design` for the validation-only Gate 01 preregistration, followed by a design-level `ccf-integrity-auditor` review before any implementation or formal 319 execution.
