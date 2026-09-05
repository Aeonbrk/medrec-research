<!-- markdownlint-disable MD013 -->

# Pre-Idea Premise Audit

## Status

The only authorized pre-Idea premise audit has been completed.

- **Gate**: `B0 — Cardinality Attribution`
- **Verdict**: `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`
- **Decision**: [`b0-decision.md`](b0-decision.md)
- **Aggregate summary**: [`b0-summary.json`](b0-summary.json)
- **Runner**: [`run_cardinality_attribution_gate.py`](run_cardinality_attribution_gate.py)
- **Integrity audit**: `PASS`
- **Test split**: untouched
- **Axis B**: terminated
- **Idea 006**: not created

No new premise audit is currently authorized. This directory is historical evidence for the completed bounded pre-Idea gate; it must not become a standing exploratory lane.

## B0 scientific question

Under frozen MoleRec validation predictions, does restoring the reference medication count with the **unchanged frozen score ranking** recover material target fidelity while materially increasing pair-normalized DDI rate?

For validation visit $t$ the diagnostic used:

$$
\hat M_t^{oc}
=\operatorname{TopK}_{m}(s_t(m), k_t),
\qquad
k_t=|M_t|.
$$

Because $k_t$ uses the target, `oracle-count` is diagnostic-only and non-deployable.

## Frozen protocol identity

B0 used the Unified Research Protocol lineage and frozen MoleRec identity already established by earlier Ideas. It did not retrain, fine-tune, alter thresholds, add a second backbone, or access the test split.

Required evidence consisted of:

- complete 131-medication frozen validation score vectors;
- original frozen predicted sets;
- validation target medication sets;
- the frozen Comparison-scope DDI relation asset;
- patient identifiers for clustered aggregation/bootstrap only.

## Metrics

For both original and oracle-count predictions B0 computed:

- medication count and count error;
- Jaccard;
- F1;
- precision;
- recall;
- pair-normalized DDI rate under repository evaluator semantics;
- absolute DDI-pair burden per visit.

Primary paired effects were:

$$
\Delta F1 = F1(\hat M_t^{oc},M_t)-F1(\hat M_t^{orig},M_t)
$$

and

$$
\Delta DDI = DDI(\hat M_t^{oc})-DDI(\hat M_t^{orig}).
$$

Absolute DDI-pair burden remained descriptive because it changes mechanically with set size; pair-normalized DDI rate was the primary safety-side attribution quantity.

## Statistical unit

B0 used patient-clustered paired bootstrap:

- 2,000 replicates;
- fixed seed `260905`;
- patient as the resampling unit;
- two-sided 95% percentile confidence intervals.

## Frozen pass rule

`PASS_B0_MATERIAL_COUNT_SAFETY_TRADEOFF` required all three conditions:

1. at least 20% of validation visits under-counted by the original prediction;
2. mean `delta F1 >= +0.010` and its 95% CI strictly above zero;
3. mean `delta DDI >= +0.005` and its 95% CI strictly above zero.

Any failure returned `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`.

## Result

B0 evaluated 1,220 eligible validation visits.

- Under-count prevalence: 33.77% — Condition 1 passed.
- Over-count prevalence: 58.44%; oracle-count reduced mean predicted count from 21.55 to 19.95.
- F1: 0.6881 -> 0.6981, `delta = +0.009977`, 95% CI `[+0.0067, +0.0134]` — Condition 2 failed the frozen point-estimate floor.
- Pair-normalized DDI rate: 0.044519 -> 0.044516, `delta = -0.000002`, 95% CI `[-0.0007, +0.0007]` — Condition 3 decisively failed.

The scientific result is therefore not a near-pass. The cardinality intervention did not expose the required normalized-DDI trade-off.

## Interpretation boundary

B0 establishes only that, under the frozen MoleRec validation setting, reference-cardinality restoration does not reveal a material count-mediated normalized-DDI/fidelity trade-off.

It does not establish clinical efficacy, clinical safety, or the impossibility of all undertreatment research.

The reusable failure record is:

[`../memory/failures/cardinality-attribution-b0--no-material-count-safety-tradeoff.md`](../memory/failures/cardinality-attribution-b0--no-material-count-safety-tradeoff.md)

## Closed execution boundary

Do not rescue B0 through:

- omission/count features;
- diagnosis maps;
- subgroup mining;
- alternative thresholds;
- a second backbone;
- GNN/LLM/RAG machinery;
- action-space remapping;
- a B1/B2 diagnostic derived from the same count-mediated premise.

The current project state and next workflow owner are defined in [`../../Handoff.md`](../../Handoff.md).
