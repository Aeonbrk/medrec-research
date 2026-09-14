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

The terminal recommendation and aggregate numbers are appended below after
the one remote run.

### Result record

_Pending the single fixed Train/Gate01-Dev run._
