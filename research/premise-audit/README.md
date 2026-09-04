<!-- markdownlint-disable MD013 -->

# Pre-Idea Premise Audit

## Scope

This directory contains bounded empirical premise tests that occur **before** an Idea is created. It exists only when the next research decision depends on project-local evidence that literature search cannot answer.

It must not become a standing exploratory lane. Every audit must have one frozen decision question, one minimal execution, an explicit pass/fail rule, and a named downstream owner.

Current authorized audit: **B0 — Cardinality Attribution**.

No Idea 006 exists. No method implementation is authorized.

## B0 — Cardinality Attribution

### Scientific decision question

Under the frozen MoleRec validation predictions, is there a material count-mediated safety/fidelity trade-off?

More precisely, when the prediction set is expanded or contracted to the reference medication count using the **unchanged frozen score ranking**, does restoring count recover target-medication fidelity while materially increasing the pair-normalized DDI rate?

The gate tests a premise for a possible future treatment-preserving safety method. It does not test such a method.

### Frozen evidence setting

Use the existing Unified Research Protocol lineage and frozen MoleRec identity already used by Ideas 001--005.

Required input per validation visit $t$:

- frozen current-visit MoleRec score $s_t(m)$ over the complete 131-medication vocabulary;
- frozen original predicted set $\hat M_t$ under the repository's existing decision rule;
- validation target medication set $M_t$;
- frozen DDI relation asset used by the current Comparison scope;
- patient identifier sufficient only for patient-clustered aggregation/bootstrap.

Prefer the existing restricted validation prediction payload. If it does not contain complete vocabulary scores, regenerate **validation-only target-free inference** under the exact frozen MoleRec checkpoint/configuration already authorized by the earlier gates. Do not retrain MoleRec and do not change its threshold or configuration.

The test split must not be indexed, staged, predicted, evaluated, or inspected.

### Diagnostic construction

For every validation visit define the original prediction:

$$
\hat M_t^{orig}=\hat M_t.
$$

Define the oracle-count diagnostic set:

$$
\hat M_t^{oc}
=\operatorname{TopK}_{m}(s_t(m), k_t),
\qquad
k_t=|M_t|.
$$

Ties are resolved deterministically by medication code ascending.

`oracle-count` is a diagnostic intervention because $k_t$ uses the target. It is not deployable and must never be reported later as a fair production baseline.

### Required metrics

Compute visit-level and patient-aggregated values for both `orig` and `oracle-count`:

- medication count;
- count error $|\hat M_t|-|M_t|$;
- Jaccard;
- F1;
- precision;
- recall;
- pair-normalized DDI rate using the repository's current evaluator semantics;
- absolute number of DDI pairs per visit.

Also report the prevalence of visits with:

$$
|\hat M_t|<|M_t|,
\quad
|\hat M_t|=|M_t|,
\quad
|\hat M_t|>|M_t|.
$$

The primary mechanism analysis is the paired difference:

$$
\Delta F1 = F1(\hat M_t^{oc},M_t)-F1(\hat M_t^{orig},M_t),
$$

and

$$
\Delta DDI = DDI(\hat M_t^{oc})-DDI(\hat M_t^{orig}).
$$

Report Jaccard and recall analogues as secondary corroboration. DDI-pair burden is descriptive because it is mechanically affected by set size; the pair-normalized DDI rate is the primary safety-side attribution quantity.

### Statistical unit

Use patient-clustered paired bootstrap with 2,000 replicates and a fixed public seed `260905`.

Bootstrap patients, retaining all of a sampled patient's validation visits together. Report the mean paired difference and two-sided 95% percentile confidence interval.

Do not run repeated alternative seeds or multiple bootstrap schemes after seeing the result.

### Frozen pass rule

Return `PASS_B0_MATERIAL_COUNT_SAFETY_TRADEOFF` only if **all** conditions hold:

1. At least 20% of validation visits are under-counted by the original prediction: $|\hat M_t|<|M_t|$.
2. Oracle-count improves mean F1 by at least `+0.010` absolute, and the 95% patient-clustered bootstrap CI for $\Delta F1$ is strictly above zero.
3. Oracle-count increases the pair-normalized DDI rate by at least `+0.005` absolute, and the 95% patient-clustered bootstrap CI for $\Delta DDI$ is strictly above zero.

Otherwise return `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`.

These floors are hypothesis-selection thresholds, not clinical safety thresholds. They require a trade-off large enough to justify investing in a method paper rather than continuing diagnostics around a negligible effect.

### Interpretation

A pass establishes only this narrow premise:

> Restoring reference cardinality using the unchanged score ranking recovers a material amount of target fidelity but exposes a material increase in normalized DDI rate.

It does **not** establish:

- that the reference count is deployable;
- that every omitted target medication is clinically required;
- that lower DDI rate is clinically safer;
- that a learned allocation mechanism can solve the trade-off;
- that action-space semantics are adequate.

A pass hands the route to `ccf-idea-optimizer`. The optimizer must propose a deployable mechanism that does not use oracle count and whose learned contribution can beat simple deployable cardinality and DDI-aware allocation controls.

A failure terminates Axis B. Do not add features, subgroup searches, diagnosis maps, GNNs, LLMs, or alternative thresholds to rescue B0.

### Explicit exclusions

B0 must not:

- train or fine-tune any recommender;
- access the test split;
- add a second backbone;
- search hyperparameters;
- introduce clinical indication/substitution mappings;
- perform action-space remapping;
- become a benchmark or paper contribution;
- create Idea 006.

### Public artifacts after execution

Commit only public-safe artifacts:

- `run_cardinality_attribution_gate.py` — idea-local-style standalone runner for this bounded audit;
- `b0-summary.json` — aggregate counts, metrics, paired effects, confidence intervals, frozen identities, and verdict;
- `b0-decision.md` — concise evidence-bound research decision.

Restricted prediction payloads, private dataset paths, raw patient-level rows, and environment-specific execution traces remain off Git.

## Next owner

- B0 pass -> `ccf-idea-optimizer`, then `ccf-idea-reviewer`.
- B0 fail -> `ccf-pipeline-orchestrator` records `NO_HIGH_VALUE_DIRECTION_YET`, then one bounded `ccf-literature-searcher / exploratory` reset outside the closed research-space map.
