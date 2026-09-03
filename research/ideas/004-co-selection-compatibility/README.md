<!-- markdownlint-disable MD013 -->

# Idea 004: Frequency-Corrected Co-Selection Compatibility

- **Idea ID**: `004-co-selection-compatibility`
- **Status**: `REJECTED / TERMINATED_AT_GATE_01`
- **Scientific stage**: Idea / hypothesis selection (terminated)
- **Target venue assumption**: generic CCF-A AI/ML/KDD-family target
- **Literature grounding**: `literature-search-20260903-co-selection-fp-routing/`
- **Strict idea review**: [`idea-review.md`](idea-review.md)
- **Gate 01 Protocol**: [`experiments/gate-01-co-selection-compatibility.md`](experiments/gate-01-co-selection-compatibility.md)
- **Design audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md) (`DESIGN_INTEGRITY_PASS`)
- **Gate 01 Summary**: [`experiments/gate-01-summary.json`](experiments/gate-01-summary.json)
- **Gate 01 Integrity Audit**: [`experiments/gate-01-integrity-audit.md`](experiments/gate-01-integrity-audit.md) (`INTEGRITY_PASS`)
- **Research Decision**: [`research-decision.md`](research-decision.md) (`STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY`)
- **Failure Record**: [`../../memory/failures/co-selection-compatibility-gate-01--no-incremental-co-selection-compatibility.md`](../../memory/failures/co-selection-compatibility-gate-01--no-incremental-co-selection-compatibility.md)
- **Next CCFA owner**: `ccf-pipeline-orchestrator` / exploratory direction scouting

## Problem statement

Ideas 001--003 closed three specific medication-level false-positive routing routes under frozen MoleRec: active-DDI-degree/Tension, preregistered five-bin score geometry, and within-prescription relative-confidence mid-rank. None established reproducible incremental routing information beyond its strongest frozen control.

The cumulative evidence does not show that static, relational, longitudinal, patient-conditioned, structural, or cross-model information is exhausted. Retrospective Oracle headroom remains substantial, but Oracle uses the target and therefore does not establish that a target-free observable mechanism exists.

## Residual question

$$
\boxed{\begin{aligned}
&\text{What target-free observable information, not already tested in Ideas 001--003,}\\
&\text{explains medication-level false-positive heterogeneity beyond the strongest simple control?}
\end{aligned}}
$$

## Falsifiable hypothesis

Let the frozen predicted prescription at visit $t$ be $\hat M_t$, with $n_t=|\hat M_t|$. Over eligible training visits $\mathcal T_{train}$ of size $V_{train}$, define

$$
C(m)=\sum_{v\in\mathcal T_{train}}\mathbf1[m\in M_v],
$$

and

$$
C(m,j)=\sum_{v\in\mathcal T_{train}}\mathbf1[m\in M_v\land j\in M_v].
$$

For $C(m,j)>0$, define empirical probabilities

$$
p_{train}(m)=\frac{C(m)}{V_{train}},\qquad
p_{train}(j)=\frac{C(j)}{V_{train}},\qquad
p_{train}(m,j)=\frac{C(m,j)}{V_{train}},
$$

and pairwise normalized pointwise mutual information

$$
\operatorname{NPMI}_{train}(m,j)=
\frac{\log\frac{p_{train}(m,j)}{p_{train}(m)p_{train}(j)}}{-\log p_{train}(m,j)}.
$$

Boundary values are fixed before outcome inspection:

$$
\operatorname{NPMI}_{train}(m,j)=
\begin{cases}
-1,&C(m,j)=0,\\
1,&C(m,j)=V_{train},\\
\frac{\log\frac{p_{train}(m,j)}{p_{train}(m)p_{train}(j)}}{-\log p_{train}(m,j)},&\text{otherwise.}
\end{cases}
$$

The candidate-level observable is

$$
A_t(m)=\frac{1}{n_t-1}\sum_{j\in\hat M_t\setminus\{m\}}\operatorname{NPMI}_{train}(m,j).
$$

The hypothesis is:

$$
\boxed{\text{Conditional on frozen medication confidence and trivial set/popularity controls, }A_t(m)\text{ provides reproducible incremental information about }Y^{PB}_{t,m}.}
$$

## Exact observable

`CoSelectionCompatibility` = $A_t(m)$, the mean train-only empirical NPMI between candidate $m$ and every other medication in the same frozen predicted prescription.

Higher values mean stronger historical co-selection association after marginal-frequency normalization. The Dev estimator may learn either coefficient sign; no outcome-direction claim is hard-coded.

## Why this information is new relative to prior controls

Ideas 001--003 tested DDI degree/Tension, score-only remapping, and same-visit relative score position. `CoSelectionCompatibility` instead observes medication identities plus train-only medication-medication co-selection relations.

Two candidates can have identical frozen score, predicted-set size, candidate prevalence, peer-set mean prevalence, and relative score position while receiving different $A_t(m)$ because their peer identities and pair relations differ.

This is materially new information relative to the tested selector controls. Co-prescription relations themselves are established prior art and are not claimed as novel.

## Mechanism

A frozen recommender can assign a medication high individual confidence while the medication remains statistically atypical relative to the other medications simultaneously predicted. Frequency correction asks whether pair association carries residual information after candidate confidence, set size, candidate prevalence, and peer-set popularity are controlled.

The mechanism is an error-routing hypothesis. Co-selection association is not interpreted as therapeutic synergy, clinical appropriateness, or causal compatibility.

## Closest prior work

The retained closest-work set includes HI-DR (AAAI 2025; DOI `10.1609/aaai.v39i11.33301`), DMRNet (Neural Networks 2026; DOI `10.1016/j.neunet.2026.109168`), MSAM (arXiv `2601.19259`), GenRxR (RecSys 2026; DOI `10.1145/3773078.3831753`), GRAIN (arXiv `2608.00098`), and CRHP (IEEE JBHI; DOI `10.1109/JBHI.2025.3582393`). These works make generic “use medication relations/co-prescription” claims non-novel.

## Novelty delta

Within the completed search scope, no retained work directly tests the following decision problem:

```text
frozen medication score
+ predicted-set size
+ candidate prevalence
+ peer-set popularity
+ predeclared score interactions
vs.
those same controls + one train-only frequency-corrected co-selection statistic
```

with medication-level false-positive routing as the decision unit, a fresh patient-disjoint validation Dev/Audit split, and held-out incremental review yield as the central claim.

This is search-scoped wording, not universal novelty proof. NPMI itself is not novel.

## Strongest simple control

Gate 01 freezes the following control variables:

- frozen MoleRec medication confidence;
- frozen predicted prescription size;
- train-only candidate-medication prevalence;
- mean train-only prevalence of the other medications in the frozen predicted prescription;
- score-by-size, score-by-candidate-prevalence, and score-by-peer-prevalence interactions.

The augmented selector adds exactly one scientific feature: `CoSelectionCompatibility`.

No GNN, hypergraph encoder, Transformer, Mamba, LLM verifier, learned relation encoder, or new backbone is justified.

## Candidate universe

$$
\mathcal Q_t=\{m\in\hat M_t:d_t(m)>0\}.
$$

## Revision operator

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\}.
$$

Within $\mathcal Q_t$, singleton deletion removes at least one active DDI edge. The retrospective Gate outcome remains

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
- train-only pairwise co-selection counts and frozen empirical NPMI relations;
- DDI graph only to reproduce the already frozen candidate universe $\mathcal Q_t$.

Forbidden selector inputs:

- current target-prescription membership;
- current outcome labels;
- future visits or future prescriptions;
- validation-derived co-selection statistics;
- Audit labels for fitting, feature selection, coefficient selection, cutpoints, or formula selection;
- any test data, test targets, test predictions, or test-derived statistics;
- Idea 001 Tension features, Idea 002 score bins, or Idea 003 relative-rank cosmetic variants as rescue features.

## Prediction-time availability

Yes. The current predicted set and scores are frozen model outputs. Medication prevalence and pairwise co-selection relations are computed once from training prescriptions and frozen before validation evaluation.

## Leakage boundary

Training target prescriptions may define aggregate train-only prevalence and pair statistics. They may not be joined to validation targets. Dev labels may fit the preregistered low-capacity selectors. Audit labels may only evaluate already frozen selectors. Test remains unindexed, unpredicted, and untouched.

## Cheapest decisive experiment

One validation-only Gate 01:

1. identity-verify or regenerate frozen validation prediction payloads without accessing test;
2. compute train-only prevalence and empirical NPMI once;
3. create the preregistered patient-disjoint Idea-004 Dev/Audit split;
4. fit the frozen strongest simple control on Dev;
5. fit the identical estimator with exactly one additional $A_t(m)$ feature on Dev;
6. freeze both selectors;
7. compare Audit Pareto-beneficial yield at preregistered budgets with patient-clustered bootstrap uncertainty.

## PASS semantics

PASS means only:

> Under the frozen MoleRec validation setting and preregistered controls, mean train-only frequency-corrected co-selection compatibility contains reproducible incremental medication-level false-positive routing information beyond frozen score and trivial set/popularity explanations.

## FAIL semantics

FAIL means only:

> The preregistered one-scalar train-only co-selection-compatibility route did not establish incremental medication-level false-positive routing information beyond the frozen strongest simple control.

FAIL terminates this representation. It does not authorize replacing NPMI with embeddings, frequent-pattern mining, a hypergraph, attention, or a learned relation model on the same information after outcome inspection.

## What PASS would not prove

PASS would not prove clinical safety, patient benefit, therapeutic compatibility, causality, prescribing correctness, prospective utility, untouched final generalization, cross-backbone portability, or that co-selection relations are novel in MedRec. It would not prove NPMI is the optimal relation statistic.

## What FAIL would not prove

FAIL would not prove that all medication relations are useless, all static observables are exhausted, longitudinal history is useless, DDI topology is useless, patient-conditioned evidence is useless, or no target-free explanation of residual heterogeneity exists.

## Portability

The statistic is backbone-agnostic for multi-label recommenders whose medication vocabulary aligns to a train-only prescription corpus and whose current predicted set is exposed. Cross-backbone empirical portability is outside Gate 01.

## Known limitations

- The Gate is retrospective and validation-only.
- Co-prescription association can encode historical prescribing practice or bias.
- MoleRec already learns from EHR-derived information; a PASS would establish residual information in an explicit statistic after the frozen score, not a previously unavailable raw data source.
- The closest-work neighborhood is dense; novelty depends on the conditional medication-level error-routing formulation.

## Historical validation adaptivity

Ideas 001--003 already used validation data for route selection. A fresh Idea-004 patient-disjoint Dev/Audit partition is held-out route-selection evidence only, not untouched final-generalization evidence. Test remains reserved for a later explicitly authorized stage.

## Stop boundary

Gate 01 is the only authorized next scientific experiment after protocol freeze. No architecture expansion, test evaluation, multi-backbone benchmark, Gate 02, or Idea 005 is implied.

## Next CCFA owner

Execution complete. Next CCFA owner: `ccf-pipeline-orchestrator` / exploratory research direction scouting.
