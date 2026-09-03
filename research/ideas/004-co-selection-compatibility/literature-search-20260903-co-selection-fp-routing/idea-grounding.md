<!-- markdownlint-disable MD013 -->

# Idea Grounding — Frequency-Corrected Co-Selection Compatibility

## Source-supported observations

1. Medication co-prescription relations are already established modeling objects. HI-DR explicitly strengthens an EHR medication graph by representing how strongly one medication is co-prescribed with another. DMRNet mines frequent medication combinations; MSAM learns collective medication effects; GenRxR models co-recommended medication relationships; GRAIN includes an EHR-derived co-prescription graph.
2. Longitudinal medication reuse is also established. COGNet uses copy-or-predict, KERL models reusable historical drugs, HeteroMed uses expansion/inheritance, and DMRNet performs temporal drug recalibration.
3. Medication confidence is already an explicit MedRec research object, including calibration/quantification work. In this repository, Ideas 001--003 independently establish frozen recommender confidence as a mandatory successor control.
4. The reviewed relation/history papers optimize medication recommendation quality or safety. In the completed search, they do not directly answer the repository's narrower conditional medication-level false-positive routing question after the frozen control stack.

## Project-supported observations

1. Ideas 001--003 are closed negative routes with independent integrity passes.
2. The tested active-DDI-degree/Tension route, five-bin score-geometry route, and within-prescription mid-rank route did not provide reproducible incremental routing information beyond their respective frozen controls.
3. Idea 003's `StrongControl - ScoreOnly` interval is strictly positive at the 20% primary budget but crosses zero at 10%; the control must not be described as universally dominating ScoreOnly.
4. Substantial retrospective `Oracle - StrongControl` headroom remains. Because Oracle uses the current target, this establishes unresolved outcome heterogeneity, not target-free observability.
5. Historical validation has already been used adaptively for route selection. A new Idea-004 Dev/Audit partition remains route-selection evidence, not untouched final generalization evidence.

## Inferred gap

The literature and repository jointly leave one narrow unresolved question:

> Does an explicit target-free medication-set relation statistic retain candidate-level false-positive information that is not already summarized by the frozen medication score and trivial marginal set/popularity quantities?

This is an inference from the completed search and project evidence. It is not a claim made by the cited papers.

## Mechanism primitive

The selected primitive is a single train-only frequency-corrected medication-pair compatibility relation.

For each validation candidate, average the frozen pair relation over the other medications in the same frozen predicted set. This yields one scalar `CoSelectionCompatibility`.

The mechanistic expectation is not that historical co-prescription equals therapeutic compatibility. It is only that an atypical candidate-to-peer relation may expose a brittle simultaneous prediction after marginal popularity is controlled.

## Control primitive

A valid Gate must remove the strongest trivial explanation first:

- low frozen score;
- larger/smaller predicted prescription;
- candidate medication popularity;
- peer-set popularity composition.

The proposed scientific feature is allowed to enter only after these quantities are in the primary control.

## Protocol anchors

- candidate universe remains $\mathcal Q_t=\{m\in\hat M_t:d_t(m)>0\}$;
- revision remains singleton deletion $R_0$;
- outcome remains $Y^{PB}_{t,m}=\mathbf1[m\notin M_t]$ under the frozen retrospective benchmark semantics;
- co-selection and prevalence quantities are training-only;
- Dev may fit the preregistered low-capacity selector;
- Audit may evaluate only frozen selectors;
- test remains untouched;
- PASS requires positive held-out incremental evidence at both primary review budgets;
- FAIL terminates the one-scalar relation representation and does not authorize a graph/attention rescue.

## What the literature does not support

The search does not support claims that:

- co-prescription relations are novel;
- longitudinal history must be the missing information;
- Oracle headroom proves observability;
- false positives are known to concentrate in low-compatibility regions;
- a relational neural architecture is justified before the scalar Gate;
- improved retrospective routing would establish clinical safety or patient benefit.
