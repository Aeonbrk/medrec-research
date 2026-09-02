<!-- markdownlint-disable MD013 -->

# Idea 003: Prescription-Relative Confidence Residual

- **Idea ID**: `003-prescription-relative-confidence`
- **Status**: `SELECTED`
- **Gate 01 Status**: `Gate 01 DESIGNED / FROZEN`
- **Execution Status**: `NOT EXECUTED`
- **Protocol**: [`experiments/gate-01-prescription-relative-confidence.md`](experiments/gate-01-prescription-relative-confidence.md)
- **Design Audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md) (`INTEGRITY_PASS`)
- **Scientific stage**: Gate 01 protocol preregistered and frozen; ready for P0 verification and P1 implementation
- **Target venue assumption**: generic CCF-A AI/ML/KDD-family target
- **Literature grounding**: `literature-search-20260902-residual-fp-routing/`
- **Strict idea review**: [`idea-review.md`](idea-review.md)

## Problem statement

Ideas 001 and 002 establish two facts under the frozen MoleRec validation setting: raw medication confidence is a strong selective-revision control, and substantial retrospective Oracle headroom remains after that control. Idea 002 also falsifies the preregistered five-bin score-only geometry route.

The unresolved question is therefore not whether confidence matters, and not whether another one-dimensional transform of confidence can be invented. It is whether a target-free observable that depends on *other simultaneously predicted medications* supplies reproducible incremental information about a candidate's false-positive status.

## Residual question

$$
\boxed{\text{Conditional on frozen }s_t(m),\text{ what minimal target-free output-set information explains residual false-positive heterogeneity?}}
$$

## Falsifiable hypothesis

Let $n_t=|\hat M_t|$. For every candidate $m$ in the DDI-active predicted-medication universe, define its within-prescription relative confidence position by mid-rank:

$$
r_t(m)=\frac{|\{j\in\hat M_t:s_t(j)>s_t(m)\}|+\tfrac12|\{j\in\hat M_t\setminus\{m\}:s_t(j)=s_t(m)\}|}{n_t-1}.
$$

The candidate universe guarantees $n_t\ge2$ because $d_t(m)>0$ requires at least one co-predicted medication.

The hypothesis is:

$$
\boxed{\text{Conditional on frozen }s_t(m),\ n_t,\ \text{and train-only medication prevalence, }r_t(m)\text{ provides reproducible incremental information about }Y^{PB}_{t,m}.}
$$

Higher $r_t(m)$ means that more medications in the same predicted prescription outrank $m$ by frozen confidence.

## Observable

`PrescriptionRelativeRank` = $r_t(m)$ as defined above.

It uses only the frozen model's predicted medication set and medication scores at the same visit. It does not use the current target prescription, future visits, DDI labels beyond the already frozen candidate-universe membership, or any Audit outcome.

## Why this information is new relative to ScoreOnly

`ScoreOnly` observes only $s_t(m)$. `PrescriptionRelativeRank` also observes the distribution of other predicted medication scores in the same visit.

Two candidates can have identical $s_t(m)$ yet different $r_t(m)$ because the rest of their predicted prescriptions differ. The observable is therefore not a scalar reparameterization of $s_t(m)$ and can induce a different cross-visit candidate ordering.

## Mechanism

Absolute confidence is globally comparable only to the extent that the backbone's output scale behaves consistently across visits. Multi-label prescriptions can differ in score compression, competition, and output-set composition. A medication that is moderately confident in a visit where nearly every selected medication scores higher may be a different error case from an equally scored medication that is among the visit's strongest model commitments.

This is a testable output-context mechanism, not a claim that relative rank is clinically meaningful by itself.

## Closest prior work

The main searched overlaps are:

- KDD 2025 medication-confidence calibration (`10.1145/3690624.3709232`): already studies individual-medication confidence and bin-based calibration.
- GiantMed, KDD 2026 (`10.1145/3770854.3780297`): already selects medications near an absolute decision boundary for refinement.
- A 2026 antibiotic-optimization study (`10.1186/s12911-026-03528-8`): uses Top1-Top2 probability margin as relative confidence in a single-choice setting.
- HeteroMed, KERL, DMRNet, MSAM, HypeMed, and GenRxR: establish that temporal/history and medication-set context are active MedRec research lines.

## Novelty delta

Within the current search scope, no direct work was found that tests a medication-level multi-label routing claim of this form:

```text
absolute frozen medication score
+ trivial prescription-size / medication-popularity controls
vs.
those controls + within-prescription relative confidence position
```

on a patient-disjoint held-out partition with false-positive routing as the decision unit.

This is search-scoped wording, not a universal novelty claim.

## Strongest simple control

The primary control must contain the explanations that can trivially make rank look useful:

```text
Frozen medication score
+ predicted medication count
+ train-only medication prevalence
+ frozen score × predicted-count interaction
```

The proposed selector may add exactly one scientific feature: `PrescriptionRelativeRank`.

No GNN, history encoder, LLM, new backbone, ensemble, or learned representation is justified at Gate 01.

## Candidate universe

The review universe is unchanged from the preceding routing work:

$$
\mathcal Q_t=\{m\in\hat M_t:d_t(m)>0\}.
$$

The revision operator is fixed singleton deletion:

$$
R_0(\hat M_t,m)=\hat M_t\setminus\{m\}.
$$

Within this universe, singleton deletion always reduces at least one active DDI edge, so the Pareto-beneficial outcome reduces to false-positive status:

$$
Y^{PB}_{t,m}=\mathbf1[m\notin M_t].
$$

## Target-free contract

Allowed at prediction/revision time:

- frozen MoleRec medication scores for the current visit;
- frozen MoleRec predicted medication set for the current visit;
- predicted medication count;
- train-only medication prevalence frozen before validation evaluation;
- DDI graph only to reproduce the already defined candidate universe $\mathcal Q_t$.

Forbidden selector inputs:

- membership in the current target prescription;
- current-visit outcome labels;
- future visits;
- Audit labels or Audit-derived cutpoints/coefficients;
- test data or test predictions;
- a new model trained to predict $Y^{PB}$ beyond the preregistered low-capacity Gate 01 selector.

## Leakage boundary

All train-only prevalence statistics are computed from the training split. Dev labels may fit the frozen low-capacity selectors. Audit labels may only evaluate the already frozen selectors. The test split remains unindexed and untouched.

Historical validation has already been used for research-route selection in Ideas 001 and 002. A fresh Idea-003 Dev/Audit partition is valid route-selection evidence but is not untouched final generalization evidence.

## Cheapest decisive experiment

One validation-only Gate 01:

1. regenerate or reuse identity-verified frozen MoleRec validation predictions without accessing test;
2. create a fresh patient-disjoint Idea-003 Dev/Audit partition chosen before outcome inspection;
3. fit the strongest low-capacity control on Dev;
4. fit the identical model with one additional $r_t(m)$ feature on Dev;
5. freeze both selectors;
6. compare Audit Pareto-beneficial yield at preregistered review budgets using patient-clustered bootstrap uncertainty.

## PASS semantics

PASS means only:

> Under the frozen MoleRec validation setting and preregistered controls, within-prescription relative confidence position contains reproducible incremental medication-level false-positive routing information beyond absolute score, prescription size, and train-only medication prevalence.

## FAIL semantics

FAIL means:

> The preregistered one-scalar prescription-relative-confidence route did not establish incremental routing information beyond the frozen strong control.

A FAIL terminates this route. It does not authorize adding rank bins, nonlinear selectors, attention, a GNN, an LLM, or a learned verifier on the same information.

## What PASS would not prove

A PASS would not establish clinical safety, patient benefit, causal mechanism, prospective prescribing validity, universal backbone portability, or untouched final generalization. It would not prove that relative rank is the best output-set observable.

## What FAIL would not prove

A FAIL would not establish that all output-set context is useless, that relational or temporal information is absent, that other target-free evidence cannot explain residual heterogeneity, or that Oracle headroom has disappeared.

## Portability

The observable is backbone-agnostic for multi-label recommenders that expose a predicted medication set and per-medication scores. Cross-backbone portability is a later question and is not part of Gate 01.

## Known limitations

- The Gate remains retrospective and validation-only.
- Validation has already participated in prior research-route selection.
- Relative position can be useful for statistical reasons without constituting a clinical decision rationale.
- Closest-work search found adjacent relative-confidence and boundary methods, so novelty depends on the conditional decision-unit formulation rather than the phrase “relative confidence.”

## Stop boundary

Gate 01 is the only authorized next experiment. No architecture expansion and no next Gate are implied by Idea selection.

## Next CCFA owner

P0 state / protocol verification, followed by P1 implementation of the frozen Gate 01 protocol (`stage_gate01_inputs.py` and `run_prescription_relative_confidence_gate.py`).
