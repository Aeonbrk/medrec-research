<!-- markdownlint-disable MD013 -->

# B0 Cardinality Attribution — No Material Count-Safety Trade-off

## Status

`TERMINATED / FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`

Source decision: [`research/premise-audit/b0-decision.md`](../../premise-audit/b0-decision.md)

Source summary: [`research/premise-audit/b0-summary.json`](../../premise-audit/b0-summary.json)

## Tested premise

The gate tested whether the apparent medication-recommendation safety/fidelity trade-off was materially mediated by prescription cardinality. Under the unchanged frozen MoleRec score ranking, the diagnostic replaced the original prediction set with oracle-count `TopK(score, |target medications|)` and asked whether restoring the reference count simultaneously recovered target fidelity and worsened pair-normalized DDI rate.

The oracle count used the validation target and was explicitly diagnostic-only and non-deployable.

## Decisive evidence

Validation-only evidence covered 1,220 eligible visits.

- Original predictions under-counted 412 visits (33.77%), meeting the preregistered prevalence condition.
- Original predictions over-counted 713 visits (58.44%); matching reference cardinality therefore reduced mean predicted medication count from 21.55 to 19.95.
- F1 increased from 0.6881 to 0.6981, with paired `delta F1 = +0.009977` and 95% patient-clustered bootstrap CI `[+0.0067, +0.0134]`. The point estimate missed the frozen `+0.010` materiality floor.
- Pair-normalized DDI rate was effectively invariant: 0.044519 versus 0.044516, with paired `delta DDI = -0.000002` and 95% CI `[-0.0007, +0.0007]`. This decisively failed the frozen `+0.005` safety-side attribution condition.
- Absolute DDI-pair burden fell because the diagnostic predicted fewer medications on average; this combinatorial count effect did not translate into a change in normalized DDI rate.

The integrity audit passed, and the test split remained untouched.

## Reusable scientific lesson

Within the frozen MoleRec validation setting, the fidelity/DDI behavior is **not materially explained by a simple 'fewer medications buys lower normalized DDI risk' mechanism**.

A change in prescription size can mechanically change the absolute number of interacting pairs without changing the pair-normalized DDI propensity. Therefore a future safety method cannot claim a treatment-preserving contribution merely by showing that a count intervention changes F1, recall, precision, or absolute DDI-pair burden.

The stronger control is:

> Separate cardinality effects from pair-normalized interaction propensity before attributing a safety/fidelity trade-off to undertreatment or prescription shrinkage.

## What is terminated

Do not revive the tested Axis B by adding:

- omission or count-routing features;
- diagnosis-frequency maps;
- alternative cardinality thresholds;
- subgroup searches;
- a different post-hoc ranker over the same frozen scores;
- GNN, LLM, RAG, or other architecture changes whose premise is still that medication-count restoration exposes a material normalized-DDI trade-off.

The failed representation is the frozen-score cardinality-attribution premise. This record does not prove that every clinically grounded undertreatment problem is absent from medication recommendation.

## Reopen condition

Reopen only if a materially different problem supplies an independently grounded treatment-coverage or acceptable-therapy target and does **not** depend on the disproven claim that reference-cardinality restoration itself reveals the safety mechanism.

Such a route must also satisfy the existing semantic-admission and rule-entitlement constraints before method design.
