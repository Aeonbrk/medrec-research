# MSED Evidence-Distribution Screen Design — 2026-09-19

Date: 2026-09-19  
Status: **DESIGN_FROZEN_IMPLEMENTED_PENDING_319_EXECUTION**

## Belief update

The MHEF screen falsified the hypothesis that decoupling diagnosis/procedure/history softmax normalization budgets is the missing architecture mechanism. `wide_global_add` absorbed the MHEF gain, so modality-specific normalization is not promoted.

A separate previously quarantined result is now reinterpreted as a high-value structural clue rather than a candidate architecture: `prediction_local` improved Dev Jaccard by `+0.012976` over its matched aggregate control, with large F1/PRAUC gains but a `+0.003843` DDI-rate cost. Inspection of the exact code shows that this pair isolates approximately:

```text
mean of medication-token support potentials
versus
normalized log-sum-exp of the same support potentials
```

The average medication count decreased in `prediction_local`, so its DDI cost is an identity-selection shift rather than simple over-prescription.

## Rank-1 hypothesis

For candidate medication `m`, the longitudinal FineCode evidence produces scalar medication-specific support potentials `r_mi`. The predictive object should be the empirical support distribution

```text
P_m = (1/N) sum_i delta(r_mi)
```

rather than a single point summary.

The Rank-1 MSED architecture preserves the stable global FineCode read and encodes `P_m` with a bounded characteristic spectrum. The decisive control receives the same raw local scores, the same `logmeanexp` statistic, the same spectrum dimensionality, the same decoder, and the same parameter budget, but applies the spectrum to the scalar LME rather than to the full support distribution.

Therefore the primary comparison isolates distribution-shape information beyond the known LME signal.

## Frozen screen

Eight lanes:

```text
GPU0  msed_ecf_global
GPU1  point_lme_global
GPU2  point_mean_global
GPU3  point_max_global
GPU4  msed_ecf_only
GPU5  point_lme_only
GPU6  prediction_local_anchor
GPU7  foundation_code_anchor
```

Primary falsification:

```text
msed_ecf_global - point_lme_global
```

Decision boundary:

```text
Delta J <= +0.002                          -> KILL
+0.002 < Delta J <= +0.004                -> WEAK / STOP
Delta J > +0.004 with F1/PRAUC/DDI guards -> CLEAN_MECHANISM_SIGNAL
Delta J > +0.004 with guard failure       -> STOP; NO SAFETY RESCUE
```

Additional requirements before stability review:

- `msed_ecf_only - point_lme_only > +0.002 J` with guardrails;
- complete candidate exceeds `wide_global_add` (`J=0.549980`);
- both historical anchors reproduce exactly;
- no unresolved v1.3 horizon censoring.

No multi-seed stability, MIMIC-IV, or Test is automatically authorized.

## Research-family constraints

Do not rescue a negative MSED result by sweeping kernel bandwidths/frequencies, LSE temperatures, top-k values, head widths, hidden sizes, query adapters, DDI weights, thresholds, or rerankers. A negative matched result terminates the distribution-shape formulation in this form and triggers another architecture-family reset.

Distribution pooling, kernel mean embeddings, MIL/MIML, and characteristic features are reusable primitives, not novelty claims. Whole-computation-graph novelty remains unverified until empirical survival.
