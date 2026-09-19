# Medication-Specific Evidence Distribution (MSED) Screen

Status: **COMPLETE / FALSIFIED (KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS)**

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

| GPU | Lane | Role | Selected Ep | Op Point | Dev Jaccard | Dev F1 | Dev PRAUC | Dev DDI | Avg Med |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | `msed_ecf_global` | Rank-1 distribution candidate | 8 | 0.35 | 0.546806 | 0.698507 | 0.793325 | 0.076335 | 20.11 |
| 1 | `point_lme_global` | decisive point-LME matched control | 8 | 0.35 | 0.546180 | 0.698087 | 0.792862 | 0.076761 | 20.36 |
| 2 | `point_mean_global` | mean point-summary control | 7 | 0.35 | 0.546378 | 0.698442 | 0.791671 | 0.077119 | 21.14 |
| 3 | `point_max_global` | max point-summary control | 8 | 0.35 | 0.546652 | 0.698253 | 0.793283 | 0.074867 | 20.15 |
| 4 | `msed_ecf_only` | distribution without global context | 8 | 0.35 | 0.530734 | 0.684700 | 0.777805 | 0.071420 | 21.17 |
| 5 | `point_lme_only` | exact matched control for GPU 4 | 5 | 0.30 | 0.534433 | 0.687944 | 0.780670 | 0.076338 | 21.85 |
| 6 | `prediction_local_anchor` | historical local-LME anchor | 3 | 0.35 | 0.548911 | 0.700462 | 0.794832 | 0.075148 | 19.96 |
| 7 | `foundation_code_anchor` | historical FineCode anchor | 5 | 0.30 | 0.546626 | 0.698386 | 0.792678 | 0.071069 | 21.43 |

The six MSED variants share one parameter graph (1,363,465 parameters each). The two anchors intentionally retain their historical parameter counts (1,295,367 parameters); both reproduce their historical evaluations with exactly 0.0 absolute difference across all five metrics.

## Frozen falsification boundary

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

## Screen outcome and analysis

### Primary falsification

`msed_ecf_global - point_lme_global`:

```text
Delta J:       +0.000626 (+0.063 pp)
Delta F1:      +0.000421
Delta PRAUC:   +0.000463
Delta DDI:     -0.000427
Delta AvgMed:  -0.243579
Verdict:       KILL_NO_MATERIAL_SIGNAL
```

The gain of $+0.000626$ Dev Jaccard fails the frozen $+0.0020$ threshold (`KILL_NO_MATERIAL_SIGNAL`). Representing the empirical support distribution via a bounded characteristic spectrum yields no material decision value beyond the scalar logmeanexp point statistic.

### Matched controls and ablations

1. **Without global context (`msed_ecf_only - point_lme_only`)**:
   $\Delta J = -0.003699$ (-0.370 pp). In isolation, encoding the distribution spectrum performs substantially worse than scalar LME.
2. **Mean and max point summaries**:
   - vs `point_mean_global`: $\Delta J = +0.000428$
   - vs `point_max_global`: $\Delta J = +0.000154$
   Distribution shape does not materially outperform simple linear mean or hard max pooling.
3. **Global complement (`msed_ecf_global - msed_ecf_only`)**:
   $\Delta J = +0.016072$, $\Delta F1 = +0.013807$, $\Delta PRAUC = +0.015520$, $\Delta DDI = +0.004915$. Global medication-specific FineCode context remains essential; distribution pooling cannot replace it.
4. **Absolute position**:
   `msed_ecf_global` (Dev Jaccard 0.546806) underperforms prior best control `wide_global_add` (0.549980, $\Delta J = -0.003174$), prior best architecture `summary_add` (0.549611, $\Delta J = -0.002805$), and `prediction_local_anchor` (0.548911, $\Delta J = -0.002105$).
5. **Anchor reproduction**:
   `prediction_local` and `foundation_code` historical checkpoints reproduce with exactly 0.0 absolute difference across all five metrics under the canonical RNG.
6. **Horizon censoring**:
   All lanes selected their best checkpoint between Epoch 3 and 8 (`safe_selected_epoch_max = 25 >= 8`). Zero horizon censoring.

### Terminal scientific routing

`KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS`.

No multi-seed stability, MIMIC-IV replication, or Test set evaluation is authorized. Per the research protocol, no hyperparameter sweeps, frequency adjustments, or architecture tweaks will be conducted to rescue this mechanism.

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
