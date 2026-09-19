# MEMB Mutual-Binding Family Screen Design — 2026-09-19

Date: 2026-09-19  
Status: **DESIGN_FROZEN_IMPLEMENTED_PENDING_319_EXECUTION**

## Belief update after MSED

MSED falsified the hypothesis that the *shape* of each medication's local FineCode support distribution carries material predictive information beyond strong point summaries. Combined with prior MHEF and relational failures, the accumulated evidence argues against spending another screen on richer within-medication pooling, modality normalization, or pairwise evidence relations.

The strongest unresolved clue remains `prediction_local`: direct medication–token support potentials produced `+0.012976` Jaccard over its matched aggregate control, but with `+0.003843` DDI-rate cost. FineCode medication-specific evidence access itself is stable across prospective conditions.

This motivates one orthogonal question: the current model lets every medication independently consume the same evidence. Generic tokens may therefore support many medications simultaneously. The project has not yet tested whether **medication-relative evidence specificity before evidence aggregation** is useful.

## Hypothesis

For raw medication–evidence affinity `S[m,i]`, evidence token `i` should contribute more to medication `m` when its affinity to `m` is high *relative to its affinities to the other candidate medications*.

Define:

```text
c_i = logsumexp_n S[n,i] - log(M)
```

and compare the exact same parameter graph under:

```text
foundation:       softmax_i(S[m,i])
specificity:      softmax_i(S[m,i] - c_i)
scale2 control:   softmax_i(2*S[m,i])
mutual binding:   softmax_i(2*S[m,i] - c_i)
```

The scale-2 comparison isolates the commonness term from the algebraic sharpening produced by a dual-direction soft match. The scale-1 comparison tests the same commonness term without sharpening.

The same two contrasts are tested on the historical PredictionLocal potentials using normalized log-sum-exp aggregation.

## Frozen 8-lane screen

```text
GPU0  mutual_code
GPU1  scale2_code
GPU2  specificity_code
GPU3  foundation_code_anchor
GPU4  mutual_local
GPU5  scale2_local
GPU6  specificity_local
GPU7  prediction_local_anchor
```

Pre-registered commonness comparisons:

```text
P1 specificity_code  - foundation_code_anchor
P2 mutual_code       - scale2_code
P3 specificity_local - prediction_local_anchor
P4 mutual_local      - scale2_local
```

Every lane has the exact historical PortfolioModel parameter graph. MEMB adds zero parameters.

## Decision boundary

Per comparison:

```text
Delta J <= +0.002                          -> KILL_NO_MATERIAL_SIGNAL
+0.002 < Delta J <= +0.004                -> WEAK_STOP
Delta J > +0.004 with F1/PRAUC/DDI guards -> CLEAN_MECHANISM_SIGNAL
Delta J > +0.004 with guard failure       -> SIGNAL_WITH_SUPPORTING_METRIC_COST
```

Family promotion requires cross-scale support or an explicitly recorded scale-sensitive review; it cannot select a favorable scale post hoc. For accuracy-led promotion, the best surviving candidate must also exceed the strong `wide_global_add` Dev Jaccard reference (`0.549980`). A local mechanism may trigger a separate bounded accuracy–safety Pareto review if it reduces DDI by at least `0.010` with Jaccard/F1/PRAUC losses each no worse than `0.005`.

No stability, MIMIC-IV, or Test execution is automatically authorized.

## Claim boundary

Competitive attention, dual-softmax matching, label-specific representations, token/region-to-label optimal transport, and fine-grained medication mapping are known primitives. This screen is a mechanism test, not a novelty claim.

If the mechanism survives strongly, the next architecture must be materially larger than an axis-flipped softmax: a coherent medication-semantic evidence-to-regimen assignment model with its own closest-work audit and matched architecture controls.

If the mechanism fails across both scales/paths, terminate the medication-evidence competition family in this formulation. Do not rescue it with temperature/exponent sweeps, Sinkhorn iterations, OT marginal tuning, sparse activations, or DDI rerankers.
