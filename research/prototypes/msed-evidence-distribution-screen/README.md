# Medication-Specific Evidence Distribution (MSED) Screen

Status: **DESIGN + IMPLEMENTATION READY / 319 EXECUTION PENDING**

This screen is a family reset after `KILL_MHEF_NORMALIZATION_HYPOTHESIS`. It does not rescue MHEF, relational pairs, dynamic queries, iterative rereading, or output-side set repair.

## Scientific question

The stable FineCode result establishes that medication identity should bind to clinical evidence before visit/patient compression. A second, previously under-interpreted result is `PredictionLocal`:

```text
prediction_aggregate: J 0.535935 / F1 0.689176 / PRAUC 0.784937 / DDI 0.071305
prediction_local:     J 0.548911 / F1 0.700462 / PRAUC 0.794832 / DDI 0.075148
Delta:                J +0.012976 / F1 +0.011286 / PRAUC +0.009895 / DDI +0.003843
```

The two models use the same medication-token interaction network. Because the final local output layer is linear, their essential difference is:

```text
PredictionAggregate = mean_i r_mi
PredictionLocal     = logmeanexp_i r_mi
```

where `r_mi` is the scalar support potential of fine-code token `i` for candidate medication `m`.

The new hypothesis is therefore not "another pooling layer":

> A candidate medication should be predicted from the shape of its longitudinal FineCode support distribution, not from a single point statistic of medication-specific local evidence responses.

For each medication `m`, MSED treats

```text
P_m = (1/N) sum_i delta(r_mi)
```

as the scientific object.

## Rank-1 architecture

`msed_ecf_global` preserves two already-supported primitives without alteration:

1. the stable global medication-specific FineCode read;
2. the exact PredictionLocal medication-token scalar support function `r_mi`.

It then represents the empirical support distribution with a bounded characteristic spectrum. For eight fixed positive frequencies `w_k` and one shared learnable positive score scale `tau`:

```text
phi(r) = [cos(w_k r / tau), sin(w_k r / tau)]_k
spectrum_m = mean_i phi(r_mi)
LME_m = logmeanexp_i r_mi
```

The local distribution vector is projected from:

```text
[LME_m, spectrum_m]
```

and the medication decision head receives:

```text
[global FineCode context, local distribution vector, medication embedding, persistence]
```

The existing loss remains unchanged:

```text
BCE + 0.05 * normalized DDI penalty
```

No DDI reranker, query adapter, extra rereading hop, relational branch, threshold tuning, or HPO is part of this screen.

## Decisive matched control

The primary comparison is:

```text
msed_ecf_global - point_lme_global
```

Both arms have exactly the same:

- raw EHR/FineCode evidence;
- medication embeddings;
- FineCode encoder;
- global medication-specific FineCode context;
- medication-token local support scores `r_mi`;
- raw `LME_m` statistic;
- characteristic-feature dimensionality;
- distribution projection;
- final decision head;
- parameter count and initialization;
- optimizer, loss, RNG, training horizon, and Dev selection.

Only one object differs:

```text
MSED candidate: E_i[phi(r_mi)]
Point control:  phi(LME_m)
```

Thus a gain isolates information in the **shape of the medication-specific support distribution beyond the already-known LME statistic**, rather than extra width or a larger decoder.

## Eight GPU lanes

| GPU | Lane | Role |
| ---: | --- | --- |
| 0 | `msed_ecf_global` | Rank-1 distribution candidate |
| 1 | `point_lme_global` | decisive point-LME matched control |
| 2 | `point_mean_global` | mean point-summary control |
| 3 | `point_max_global` | max point-sumary control |
| 4 | `msed_ecf_only` | distribution representation without global FineCode context |
| 5 | `point_lme_only` | exact matched control for GPU 4 |
| 6 | `prediction_local_anchor` | exact historical local-LME architecture anchor |
| 7 | `foundation_code_anchor` | exact stable FineCode architecture anchor |

The six MSED variants share one parameter graph. The two anchors intentionally retain their historical parameter counts; they are absolute integrity anchors, not matched-capacity controls.

## Frozen falsification

Primary comparison: `msed_ecf_global - point_lme_global`.

```text
Delta J <= +0.002
=> KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS

+0.002 < Delta J <= +0.004
=> WEAK / normally stop

Delta J > +0.004
and Delta F1 >= -0.002
and Delta PRAUC >= -0.002
and Delta DDI <= +0.002
=> CLEAN_MECHANISM_SIGNAL

Delta J > +0.004 with guardrail failure
=> stop; no safety rescue
```

Before multi-seed stability can even be reviewed, all of the following are additionally required:

1. `msed_ecf_only - point_lme_only > +0.002 J` with guardrails, so the effect is not merely a global-branch/head interaction;
2. the complete `msed_ecf_global` architecture must exceed the current strong matched-capacity control `wide_global_add` (Dev Jaccard `0.549980`);
3. historical `prediction_local` and `foundation_code` anchors must reproduce exactly under the canonical RNG;
4. no horizon censoring remains unresolved.

If `msed_ecf_global - msed_ecf_only <= +0.002 J` after the distribution mechanism otherwise survives, the global branch should be removed before any stability stage rather than preserved by inertia.

## Development protocol

```text
profile: mimic-iii-canonical-131-paper-dev-v1
training: 30 complete epochs, no early stopping
Dev: every epoch
canonical RNG: torch/cuda/python=1203, numpy=2048
Test: SEALED
```

Under contract v1.3, a selected epoch of 26--30 is `HORIZON_CENSORED`; only the exact affected comparison may be extended unchanged to 60 epochs. No architecture or optimization modification is allowed during that extension.

## Claim boundary

The primitives are not claimed as new. Set/MIL aggregation, attention MIL, distribution-based MIL pooling, kernel mean embeddings of instance-wise predictions, label-instance medication modeling, and diagnosis-level fine-grained medication recommendation all have prior work. The only plausible paper contribution, **if the mechanism survives**, is the complete label-conditioned longitudinal FineCode support-distribution computation graph and the evidence that distribution shape beyond a strong LME statistic materially improves medication decisions.

Closest-work details are recorded in `closest-work-audit.md`. Novelty remains unverified until after empirical survival and a dedicated primary-source audit.
