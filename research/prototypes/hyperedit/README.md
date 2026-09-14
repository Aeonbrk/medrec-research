# HyperEdit-MR

HyperEdit-MR is a fast method prototype, not Idea 009. It tests whether a
retrieval-conditioned, patient-specific medication graph plus a list-wise
prescription editor can move the medication set beyond the frozen MoleRec
surface.

## v0 contract

- Frozen MoleRec logits and per-medication embeddings are the backbone signal.
- Retrieval uses diagnosis/procedure bags and Train visits only. Every query
  excludes all visits from the same patient, which is stricter than excluding
  only future visits.
- The candidate graph has 131 medication nodes. Node features are the frozen
  score, retrieval support, historical-medication indicator, baseline-set
  indicator, frozen MoleRec embedding, and its patient-context projection.
- Edge features are the DDI matrix, weighted retrieval co-support, and the
  existing EHR co-prescription matrix.
- The interaction encoder has two scalar-attention message-passing layers with
  hidden width 96.
- The editor starts from the MoleRec set and predicts bounded canonical
  `REMOVE`, `ADD`, `STOP` actions. v0 trains with teacher-forced edit targets
  (remove false positives, add false negatives, stop), final set BCE, and a
  differentiable DDI penalty. It does not use RL/GRPO.

The primary screen is one seed and one configuration on existing Train/Dev
resources. It reports Jaccard, F1, PRAUC, DDI, mean medication count, set-change
fraction, and mean symmetric difference versus MoleRec. No held-out project
test resource, bootstrap, confidence interval, or formal audit is used.

## Remote run

Run from this directory in the verified `medrec-molerec-table1` environment:

```bash
conda run --no-capture-output -n medrec-molerec-table1 \
  python run_hyperedit.py \
  --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
  --output /root/zhb/medrec-data/prototypes/hyperedit/screen.json
```

The runner writes only aggregate screen output to the requested output path;
raw records, predictions, and model weights remain outside the repository.

## Screen result

The one-seed screen on the existing Train/Dev resources used 10,489 Train
visits and 2,130 Gate01-Dev visits. It produced a weak effect and the bounded
prototype was stopped: HyperEdit-MR changed 99.95% of Dev sets, with mean
symmetric difference 7.24 versus MoleRec, but the Jaccard loss was larger than
the allowed safety trade-off.

| Surface | Jaccard | F1 | PRAUC | DDI | Mean medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen MoleRec | 0.5292 | 0.6835 | 0.7736 | 0.0722 | 21.5451 |
| Retrieval-only fusion | 0.5308 | 0.6850 | 0.7764 | 0.0720 | 20.8502 |
| HyperEdit-MR | 0.4975 | 0.6545 | 0.7842 | 0.0647 | 14.3085 |

Recommendation: `STOP_HYPEREDIT`.
