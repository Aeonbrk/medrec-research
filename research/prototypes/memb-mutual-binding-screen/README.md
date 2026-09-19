# Medication–Evidence Mutual Binding (MEMB) Family Screen

Status: **COMPLETE / FALSIFIED (KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY)**

This is a bounded architecture-family screen after `KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS`. It is not an MSED rescue, not a modality-normalization rescue, not iterative rereading, and not output-side medication-set repair.

## Scientific question

The stable project evidence now says:

- medication identity should bind to clinical evidence before visit/patient compression (`DrugQuery`, stable FineCode);
- fine-code medication–evidence interaction is highly valuable (`resolution_code`);
- direct local medication–token potentials are highly predictive (`prediction_local`) but incur a DDI-rate cost;
- richer within-medication evidence distributions, modality-specific normalization budgets, dense cross-code relations, dynamic queries, recurrent rereading, and output-side set correction have not produced a stable paper-level mechanism.

The remaining untested axis is **cross-medication specificity at the evidence-binding stage**.

Current FineCode attention asks independently for each medication:

```text
Which evidence tokens support medication m?
```

MEMB additionally asks:

```text
Is token i unusually supportive of medication m relative to the other candidate medications?
```

The screen tests whether generic evidence that is simultaneously compatible with many medications should be down-weighted before medication-level prediction.

## Computation graph

Let `S[m,i]` be the exact existing FineCode medication–evidence affinity. Define the medication-commonness of evidence token `i`:

```text
c_i = logsumexp_n S[n,i] - log(M)
```

where `M=131` medications. `c_i` is zero-centered so that uniformly matched evidence is not shifted merely because the label vocabulary is large.

### Existing FineCode foundation

```text
a_mi = softmax_i(S[m,i])
context_m = sum_i a_mi v_i
```

### Scale-1 specificity

```text
a_mi = softmax_i(S[m,i] - c_i)
```

This is the cleanest test of medication-relative evidence specificity: same score matrix and same scale, with only the cross-medication commonness penalty added.

### Mutual binding

The product of the two directional soft matches,

```text
p(i | m) * M * p(m | i)
```

after renormalization over evidence, is equivalent to:

```text
a_mi = softmax_i(2*S[m,i] - c_i)
```

This is called `mutual_code`.

### Mandatory sharpening control

Multiplying the two directional terms algebraically doubles `S`. Therefore the correct control is not only the original foundation but:

```text
scale2_code = softmax_i(2*S[m,i])
```

The decisive scale-2 contrast is:

```text
mutual_code - scale2_code
```

so MEMB receives credit only for `-c_i`, not for sharper attention.

## PredictionLocal formulation

The exact historical local support potential is `r[m,i]`. PredictionLocal uses:

```text
LME_m = logmeanexp_i r[m,i]
```

The screen evaluates the same commonness idea without changing the local interaction network:

```text
specificity_local = logmeanexp_i(r[m,i]   - c_i)
scale2_local      = logmeanexp_i(2*r[m,i])
mutual_local      = logmeanexp_i(2*r[m,i] - c_i)
```

where for the local path:

```text
c_i = logsumexp_n r[n,i] - log(M)
```

All existing medication bias, persistence features, encoder parameters, and the BCE + normalized DDI objective remain unchanged.

## Parameter and information budget

Every one of the eight lanes instantiates the exact historical `PortfolioModel` parameter graph. MEMB adds **zero learnable parameters**.

The lanes share:

- the same legal FineCode evidence;
- the same code/type/lag encoder;
- the same medication embeddings;
- the same Q/K/V or local interaction projections;
- the same medication prediction heads;
- the same persistence features;
- the same loss, optimizer, RNG, Dev selection, and training horizon.

No current-medication target enters the model input.

## Eight GPU lanes

| GPU | Lane | Matched role | Params | Epochs | Selected Ep | Op Point | Dev Jaccard | Dev F1 | Dev PRAUC | Dev DDI | Avg Med |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | `mutual_code` | scale-2 mutual FineCode candidate | 1,295,367 | 30 | 7 | 0.35 | 0.542110 | 0.694402 | 0.785345 | 0.076355 | 21.17 |
| 1 | `scale2_code` | scale-2 sharpening control for GPU 0 | 1,295,367 | 30 | 5 | 0.30 | 0.540015 | 0.693071 | 0.785565 | 0.071793 | 21.47 |
| 2 | `specificity_code` | scale-1 commonness candidate | 1,295,367 | 30 | 5 | 0.30 | 0.547125 | 0.698713 | 0.793489 | 0.071194 | 21.26 |
| 3 | `foundation_code_anchor` | exact scale-1 control + historical anchor | 1,295,367 | 30 | 5 | 0.30 | 0.546626 | 0.698386 | 0.792678 | 0.071069 | 21.43 |
| 4 | `mutual_local` | scale-2 mutual PredictionLocal candidate | 1,295,367 | 30 | 5 | 0.35 | 0.547092 | 0.698671 | 0.794902 | 0.067738 | 20.92 |
| 5 | `scale2_local` | scale-2 sharpening control for GPU 4 | 1,295,367 | 30 | 5 | 0.35 | 0.548099 | 0.699482 | 0.795203 | 0.068090 | 21.20 |
| 6 | `specificity_local` | scale-1 local-commonness candidate | 1,295,367 | 30 | 5 | 0.30 | 0.548141 | 0.699645 | 0.795108 | 0.070112 | 21.37 |
| 7 | `prediction_local_anchor` | exact scale-1 control + historical anchor | 1,295,367 | 30 | 3 | 0.35 | 0.548911 | 0.700462 | 0.794832 | 0.075148 | 19.96 |

Every lane has the exact historical PortfolioModel parameter graph (1,295,367 parameters). Both historical anchors reproduce with exactly 0.0 absolute difference across all five metrics.

## Frozen decision rules and falsification boundaries

For each commonness comparison:

```text
Delta J <= +0.002
=> KILL_NO_MATERIAL_SIGNAL

+0.002 < Delta J <= +0.004
=> WEAK_STOP

Delta J > +0.004
and Delta F1 >= -0.002
and Delta PRAUC >= -0.002
and Delta DDI <= +0.002
=> CLEAN_MECHANISM_SIGNAL

Delta J > +0.004 with guard failure
=> SIGNAL_WITH_SUPPORTING_METRIC_COST
```

## Screen outcome and analysis

### Pre-registered commonness comparisons

| Comparison | Candidate | Control | Δ Jaccard | Δ F1 | Δ PR-AUC | Δ DDI | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `code_commonness_scale1` | `specificity_code` | `foundation_code_anchor` | +0.000499 | +0.000327 | +0.000811 | +0.000126 | `KILL_NO_MATERIAL_SIGNAL` |
| `code_commonness_scale2` | `mutual_code` | `scale2_code` | +0.002095 | +0.001332 | -0.000220 | +0.004562 | `WEAK_STOP` |
| `local_commonness_scale1` | `specificity_local` | `prediction_local_anchor` | -0.000770 | -0.000817 | +0.000276 | -0.005036 | `KILL_NO_MATERIAL_SIGNAL` |
| `local_commonness_scale2` | `mutual_local` | `scale2_local` | -0.001007 | -0.000811 | -0.000301 | -0.000351 | `KILL_NO_MATERIAL_SIGNAL` |

### Sharpening diagnostics

| Comparison | Candidate | Control | Δ Jaccard | Δ F1 | Δ PR-AUC | Δ DDI |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| `code_sharpening` | `scale2_code` | `foundation_code_anchor` | -0.006611 | -0.005315 | -0.007113 | +0.000724 |
| `local_sharpening` | `scale2_local` | `prediction_local_anchor` | -0.000811 | -0.000980 | +0.000371 | -0.007058 |

### Scientific attribution

1. **Commonness penalty yields no material gain at scale 1:** In both the global FineCode read (`specificity_code`, $\Delta J = +0.000499$) and the local prediction read (`specificity_local`, $\Delta J = -0.000770$), subtracting evidence commonness $c_i$ without score sharpening produces no material signal and fails the $+0.0020$ threshold.
2. **Mutual matching gain at scale 2 is an artifact of recovering from severe sharpening damage:** While `mutual_code` beats `scale2_code` by $\Delta J = +0.002095$ (with a large $+0.004562$ DDI safety penalty), both lanes are severely degraded by the $2 \times$ score scale: `scale2_code` loses $-0.006611$ Jaccard relative to `foundation_code_anchor` ($0.540015$ vs $0.546626$). `mutual_code` ($0.542110$) merely partially mitigates this destruction, remaining $-0.004516$ below the original base model.
3. **Local mutual matching provides no benefit:** In the local path, `mutual_local` underperforms `scale2_local` by $\Delta J = -0.001007$, and both trail the historical anchor `prediction_local_anchor` ($0.548911$).
4. **Pareto safety threshold not met:** While `specificity_local` drops DDI by $-0.005036$ (from $0.0751$ to $0.0701$), it does not meet the pre-registered Pareto gate of $\Delta \text{DDI} \le -0.010$.
5. **No horizon censoring:** All lanes selected best Dev checkpoints between Epochs 3 and 7 (`safe_selected_epoch_max = 25 >= 7`).

### Terminal scientific routing

`KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY`.

No multi-seed stability, MIMIC-IV replication, or Test set evaluation is authorized. Per the protocol, no temperature tuning, Sinkhorn iterations, OT marginals, or rerankers will be evaluated to rescue this mechanism.

## Training protocol

```text
profile: mimic-iii-canonical-131-paper-dev-v1
training: 30 complete epochs, no early stopping
Dev: complete Dev every epoch
canonical RNG: torch/cuda/python=1203, numpy=2048
Test: SEALED
```

Under contract v1.3, if a relevant comparison selects epoch 26–30, only that exact comparison may be extended unchanged to 60 epochs. No architecture or optimization change is permitted during the extension.

## Explicit non-rescue rule

A negative result is not followed by temperature tuning, exponent tuning, top-k medication competition, Sinkhorn iterations, OT marginals, sparsemax/entmax, DDI reranking, query adapters, extra attention rounds, or output-set repair. Those would constitute new hypotheses, not repairs of this screen.

## Claim boundary

The matching primitives are not new. Competitive slots, dual-softmax matching, label-specific representations, token/region-to-label optimal transport, and fine-grained drug–disease correspondence all have prior work. This screen therefore does **not** establish a paper contribution by itself.

If the family survives strongly, the next scientific object is not “dual softmax for MedRec.” It would be a larger medication-semantic evidence-assignment architecture in which longitudinal FineCode evidence is allocated among clinically meaningful medication decisions. A post-survival primary-source novelty audit is mandatory before any novelty claim.
