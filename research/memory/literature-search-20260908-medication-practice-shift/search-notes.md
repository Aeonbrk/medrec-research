<!-- markdownlint-disable MD013 -->

# Search Notes — Medication-Transition Practice Shift

## Workflow context

This search is the single bounded post-Idea-006 research-space reset authorized by `ccf-pipeline-orchestrator` after:

`STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`.

It is deliberately outside the Idea-006 safety premise. No exposure-DDI loss, risk-network, direct-reranker rescue, dose/route extension, or DDI-source substitution is in scope.

Search mode: `ccf-literature-searcher / exploratory`.

Date: 2026-09-08.

## Search questions

1. Is temporal or institutional degradation of medication recommendation already established?
2. Do current general MedRec methods explicitly solve source-to-future-period or source-to-new-institution adaptation, rather than train/evaluate independently on several datasets?
3. What simple confounds could make an apparent temporal shift scientifically trivial?
4. Does MIMIC-IV expose a defensible low-cost temporal environment variable without reconstructing a new external benchmark?

## Query families

Representative query families included:

- `medication recommendation temporal validation MIMIC-IV MIMIC-III`
- `medication recommendation temporal drift`
- `medication recommendation practice shift`
- `medication recommendation domain adaptation EHR`
- `medication recommendation domain generalization MIMIC eICU`
- `medication recommendation continual learning`
- `cross-institutional medication recommendation eICU`
- current named methods + `eICU`, `external validation`, `generalization`
- `MIMIC-IV anchor_year_group medical practice over time`

Closest-work searches focused on HypeMed, KATMed, Rx-Expert, NLA-MMR, DMRNet, and narrow temporal/external medication recommender validation.

## Source policy

Preferred:

- ACM / DOI publisher pages;
- Elsevier / PubMed;
- official MIMIC-IV / PhysioNet documentation;
- full-text peer-reviewed articles when available.

Excluded from decision-bearing evidence:

- MDPI per CCFA source policy;
- generic recommender-system domain adaptation papers that do not operate on medication recommendation;
- search snippets that did not expose enough experimental semantics to determine the training/evaluation relation.

Generic domain-adaptation literature will become a baseline/search requirement only if the local premise passes and an Idea enters optimization.

## What the search supports

### Supported

- Current medication-recommendation papers increasingly report MIMIC-III, MIMIC-IV, and/or eICU together.
- HypeMed explicitly describes eICU as a cross-institutional generalization dataset, but the accessible experimental setup reports a separate eICU task with different medication coding and missing procedure/DDI resources.
- KATMed reports partial eICU external validation and explicitly acknowledges practice-pattern/case-mix/coding differences.
- A 2025 schizophrenia-spectrum medication recommender reports both geographic external and temporal validation with material performance degradation.
- DMRNet establishes medication-frequency imbalance as an active MedRec problem, making marginal label-prior drift a mandatory simple explanation.
- MIMIC-IV's `anchor_year_group` was intentionally introduced to support analysis of changes in medical practice over time.
- Recent MedRec validity work explicitly warns that temporal leakage can inflate reported performance.

### Not established by this search

The search did **not** establish that no general medication-recommendation domain-adaptation method exists anywhere. The defensible statement is narrower:

> Within the retained current search, no close general MedRec work was found whose central method question is adapting a source-trained medication recommender to a later prescribing-practice environment while explicitly separating marginal medication-prior drift from residual conditional shift.

This is a search-scoped opportunity, not a novelty proof.

## Important negative result

The reset must not use the following as novelty:

- multi-dataset evaluation;
- eICU evaluation;
- external validation;
- temporal validation;
- causal/order-time masking;
- medication-frequency debiasing by itself;
- generic continual/domain adaptation transplanted unchanged into MedRec.

## Research-space conclusion

The only route retained from this reset is:

`MEDICATION_TRANSITION_PRACTICE_SHIFT`

Its pre-method premise is:

> A source-trained causal medication-order model suffers a material forward-period fidelity drop, and a strong medication-level recent-prior/logit-bias adjustment cannot explain or recover most of that degradation.

If the residual vanishes under the simple prior control, there is no method-paper premise and the route terminates.

If the residual survives, the project may call `ccf-idea-optimizer` to determine whether a MedRec-specific adaptation mechanism exists beyond generic fine-tuning/domain adaptation.
