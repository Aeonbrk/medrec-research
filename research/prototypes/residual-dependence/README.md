# Residual-Dependence Headroom Probe

This is one bounded, throwaway pre-Idea diagnostic. It asks whether the true
medication vector contains visit-specific conditional dependence after the
full frozen 131-dimensional MoleRec score vector is known. It is not Idea 009,
a formal CCFA Gate, or a candidate recommendation model.

## Boundary

- Read only the canonical `train_scores.npy`, `train_targets.npy`,
  `dev_scores.npy`, and `dev_targets.npy` surfaces: 10,489 Train visits and
  2,130 Gate01-Dev visits.
- Prevalence is computed from Train targets only. No raw EHR, DDI/EHR graph,
  MoleRec retraining, heldout/Audit/G3/G4/historical-test resource, future
  visit, SameK, cardinality oracle, or Dev threshold tuning is permitted.
- `ScoreOnly` fits `u=A*s+b` with BCE. The conditional diagnostic fits the
  same score calibrator plus a symmetric zero-diagonal `W` using Train
  pseudo-likelihood/BCE with the other Train labels.
- `OracleCoLabel` uses true Dev `y_-i` and is privileged, non-deployable
  evidence only. `ShuffledCoLabel` uses the same fitted parameters with one
  seeded cyclic derangement of Dev rows. `MeanField` uses exactly five frozen
  damped updates and no Dev labels.
- All metrics are visit-macro. Logit surfaces decode at zero (`sigmoid=0.5`);
  NLL is Bernoulli BCE. DDI rate is intentionally not computed because this
  probe is forbidden from reading the DDI graph.

## Fixed execution

The single configuration is AdamW, 80 epochs, batch size 512, learning rate
`5e-3`, weight decay `1e-4`, seed `20260914`, and no sweep. The implementation
is `probe_residual_dependence.py`. Run it in the existing
`medrec-molerec-table1` environment on 319 after the normal remote preflight:

```bash
CUDA_VISIBLE_DEVICES=1 \
  python research/prototypes/residual-dependence/probe_residual_dependence.py \
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
  --source-revision <clean-commit> \
  --output /root/zhb/medrec-data/prototypes/residual-dependence/result.json
```

Only the aggregate result JSON may be copied back to the Mac harness. It must
contain the five required surfaces, the four requested Jaccard/NLL/PRAUC
deltas, mean prescription counts, the derangement record, and the explicit
current-target leakage check.

## Decision semantics

The interpretation is made once from the full pattern, not tuned to Dev:

- little Oracle-over-ScoreOnly or Oracle-over-Shuffled separation closes the
  interaction-first family;
- clear Oracle separation with no roughly `+0.004` deployable MeanField gain
  records an inference gap;
- clear Oracle separation plus a non-pathological MeanField gain of roughly
  `+0.004` is real interaction headroom;
- a roughly `+0.008` ScoreOnly-over-MoleRec gain with little interaction signal
  identifies the decision surface as the bottleneck.

The terminal recommendation and aggregate numbers below come from the one
remote run. `OracleCoLabel` rows are diagnostic upper-bound evidence only and
must not be presented as candidate performance.

### Result record

- Run-code revision: `31fb90a0a006775427cfdb76a5575d488658e2af`
- Starting local and origin/main: `3fa399c6238a1a30e1ec10066bdeb0ac697b76bd`
- Result-recording commit: `ba4c377c27b8d4b498e388d44b2e6f5d218d8159`;
  final verified origin/main remains `3fa399c6238a1a30e1ec10066bdeb0ac697b76bd`.
  No push was performed. The remote run used a bundle checkout at the run-code
  revision.
- Device: CUDA (GPU 1), seed `20260914`; Train-only prevalence was used for
  centering.

| Surface | BCE / NLL | PRAUC | Jaccard | F1 | Precision | Recall | Mean count | Count std | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| MoleRec | 0.246618 | 0.773576 | 0.529174 | 0.683480 | 0.661221 | 0.736513 | 21.545071 | 5.762196 | deployable frozen comparator |
| ScoreOnly | 0.223217 | 0.762376 | 0.498969 | 0.655857 | 0.740243 | 0.613936 | 16.266197 | 6.053830 | deployable |
| ShuffledCoLabel | 0.255080 | 0.739166 | 0.468939 | 0.629616 | 0.709492 | 0.601317 | 16.426291 | 5.153008 | privileged diagnostic; non-deployable |
| OracleCoLabel | 0.216182 | 0.763757 | 0.515021 | 0.669693 | 0.735967 | 0.623099 | 16.719719 | 6.432374 | privileged oracle; non-deployable |
| MeanField | 0.227172 | 0.764049 | 0.501691 | 0.658982 | 0.741872 | 0.616222 | 16.111736 | 5.354187 | deployable diagnostic |

The four required deltas (Oracle and Shuffled remain privileged diagnostics)
are:

| Comparison | Jaccard delta | NLL delta | PRAUC delta |
| --- | ---: | ---: | ---: |
| OracleCoLabel − ScoreOnly | +0.016051 | −0.007035 | +0.001380 |
| OracleCoLabel − ShuffledCoLabel | +0.046081 | −0.038898 | +0.024590 |
| MeanField − ScoreOnly | +0.002721 | +0.003955 | +0.001673 |
| ScoreOnly − MoleRec | −0.030204 | −0.023401 | −0.011200 |

The conditional fit has a finite symmetric `W` (Frobenius norm `97.859123`,
maximum absolute entry `3.317461`, symmetry residual `0`, diagonal residual
`0`). The seeded Dev derangement is a cyclic shift of `1382` rows and was
verified to have no fixed points. The current-target leakage check perturbed
each context coordinate on eight Dev rows: maximum change to that medication's
own logit was `0.0` (tolerance `1e-6`). The five mean-field updates used no
true Dev labels and reduced mean count by `0.154461` versus ScoreOnly, so the
small operational gain is not count inflation.

The Oracle gains over both ScoreOnly and its row-shuffled control establish
residual conditional dependence in this frozen-score setting, but the fixed
five-step deployable MeanField gain is only `+0.002721` Jaccard (with worse NLL
than ScoreOnly). Under the pre-registered interpretation this is an inference
gap, not evidence for a new recommendation architecture.

Terminal recommendation: `RESIDUAL_DEPENDENCE_EXISTS_INFERENCE_GAP`

## Frozen-unary identification follow-up

The prior implementation was inspected before this follow-up. `ScoreOnly` and
the pairwise Oracle/MeanField model did **not** share `A,b`: each learned its
own `A,b`, initialized as identity/zero, and the pairwise model optimized them
jointly with `W`. Its neutral context therefore did not reproduce raw MoleRec,
so a W-only fit with the unary term frozen to `s` was required.

This follow-up uses the same Train/Gate01-Dev arrays, seed, optimizer budget,
and zero-logit decoder. Only `W` is learned; no score calibration, graph,
embedding, patient input, or MoleRec retraining is present. `FrozenOracle` and
`FrozenShuffled` remain privileged, non-deployable diagnostics.

### Result record

- Run-code revision: `b841b1f4583746f92c8ad9ea97012f34c6538f88`
- Starting local HEAD: `77e99a49d8da04335bfbcffe8d8a2fbaf4d7c7f5`
- Starting and final verified origin/main: `3fa399c6238a1a30e1ec10066bdeb0ac697b76bd`
- Result was run on CUDA GPU 1 with seed `20260914`; no push was performed.

| Surface | NLL | PRAUC | Jaccard | F1 | Precision | Recall | Mean count | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| MoleRec | 0.246618 | 0.773576 | 0.529174 | 0.683480 | 0.661221 | 0.736513 | 21.545071 | deployable frozen comparator |
| FrozenNeutral | 0.246618 | 0.773576 | 0.529174 | 0.683480 | 0.661221 | 0.736513 | 21.545071 | deployable; identical to MoleRec |
| FrozenShuffled | 0.264541 | 0.747369 | 0.518786 | 0.674247 | 0.655150 | 0.725246 | 21.492489 | privileged diagnostic; non-deployable |
| FrozenOracle | 0.236136 | 0.762602 | 0.529430 | 0.683539 | 0.671101 | 0.718177 | 20.815023 | privileged oracle; non-deployable |
| FrozenMeanField | 0.248891 | 0.767215 | 0.525737 | 0.680518 | 0.661540 | 0.730321 | 21.416901 | deployable diagnostic |

Primary deltas:

| Comparison | Jaccard delta | NLL delta | PRAUC delta | Mean-count delta |
| --- | ---: | ---: | ---: | ---: |
| FrozenOracle − MoleRec | +0.000257 | −0.010482 | −0.010974 | −0.730047 |
| FrozenOracle − FrozenShuffled | +0.010644 | −0.028405 | +0.015233 | −0.677465 |
| FrozenMeanField − MoleRec | −0.003437 | +0.002273 | −0.006360 | −0.128170 |

The neutral-equivalence assertion passed exactly (`max_abs = 0.0`, tolerance
`1e-7`). `W` was symmetric with zero diagonal (Frobenius norm `74.674240`,
maximum absolute entry `4.283398`). The Dev derangement was a fixed-point-free
cyclic shift of `1382` rows. The current-target leakage check passed with
maximum own-logit change `0.0`; the finite CUDA forward/backward smoke passed.

FrozenOracle is only `+0.000257` Jaccard over the original MoleRec surface,
below the `+0.004` set-accuracy headroom threshold. It does improve NLL by
`0.010482`, but PRAUC decreases by `0.010974`, and FrozenMeanField is below
MoleRec on Jaccard, NLL, and PRAUC. The one-shot positive/negative context
decomposition was correctly skipped because Oracle headroom was below `+0.008`.

Terminal recommendation: `DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY`
