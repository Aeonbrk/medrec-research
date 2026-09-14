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

## Cardinality-controlled graph diagnostic

The prior checkpoint was not persisted, so the exact v0 configuration was
retrained once with seed `20260914`; retrieval, graph layers, losses, and all
optimizer settings were unchanged. The diagnostic used 10,489 Train visits and
2,130 Gate01-Dev visits only. `GraphRefine-SameK` ranks the existing graph
`set_head` logits at each frozen MoleRec cardinality; it does not call the
sequential editor or use ground-truth cardinality.

| Surface | Jaccard | F1 | PRAUC | DDI | Mean medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen MoleRec | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 |
| HyperEdit-MR sequential | 0.497527 | 0.654454 | 0.784240 | 0.064668 | 14.3085 |
| GraphRefine-SameK | 0.533650 | 0.687394 | 0.784240 | 0.073328 | 21.5451 |

GraphRefine-SameK preserved the MoleRec cardinality exactly (`YES`), changed
32.02% of Dev sets, and had mean symmetric difference `0.8197`. The optional
retrieval-pregraph SameK surface scored `0.529825 / 0.684076 / 0.776350 /
0.072906` (Jaccard / F1 / PRAUC / DDI), changed 13.19% of sets, and had mean
symmetric difference `0.2761`.

The graph-refined ranking surface therefore shows a moderate accuracy/ranking
movement (Jaccard `+0.004476`, F1 `+0.003914`, PRAUC `+0.010664`) at fixed
cardinality, while DDI changes slightly upward (`+0.001105`). The sequential
editor remains rejected; the representation signal survives for a redesigned
cardinality-aware score refinement and explicit set decoder.

Diagnostic decision: `SURVIVE_GRAPH_REFINEMENT`.
