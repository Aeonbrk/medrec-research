# MICA stability under the paper development profile

This runner is a new Train/Dev development lane. It does not rewrite the
historical MICA screens under `research/prototypes/mica` or
`mica-cross-dataset-replication`, whose fixed-threshold, visit-macro results
remain separate evidence.

## Frozen question

With the same clinical evidence, does medication-specific query pooling
(`DrugQuery`) improve patient-macro Jaccard over the medication-independent
`SharedPool` control? Each declared seed runs both arms. The profile and
selection contract are [`../benchmarks/mimiciii-medrec/profile.json`](../../benchmarks/mimiciii-medrec/profile.json).

The runner uses the canonical 131-medication MIMIC-III snapshot, the existing
patient-disjoint Train/Dev split, 60 complete Train epochs, and a validation
evaluation after every epoch. It evaluates every frozen global threshold from
0.05 through 0.95 at every checkpoint, then selects checkpoint and threshold
together by Dev patient-macro Jaccard. The threshold tie-break is the profile's
native-default, declared-order, earlier-checkpoint rule.

The model receives current diagnosis/procedure sets and strictly earlier
diagnosis/procedure/medication history. Target arrays are used only for loss
and evaluation alignment. No Test rows or metrics are loaded.

## Remote command

Run only after the 319 preflight and from a clean checkout at the exact source
revision. Keep outputs outside every repository.

```bash
CUDA_VISIBLE_DEVICES=0 conda run --no-capture-output -n medrec-molerec-table1 \
  python research/prototypes/mica-stability/run_stability.py \
  --variant shared_pool --seed 20260917 \
  --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
  --source-revision <immutable-run-revision> \
  --output-dir /root/zhb/medrec-data/prototypes/mica-stability/20260917/shared_pool
```

Use the same seed and frozen source/configuration for the paired DrugQuery
job, then repeat the pair with seed `20260918`. GPU assignment is a scheduling
choice recorded in the private run identity; it does not change the scientific
comparison.

Each completed `results.json` records the source and asset identities,
selection candidates, selected checkpoint and threshold, patient/visit counts,
Jaccard, F1, PRAUC, DDI, precision, recall, predicted and target medication
counts, runtime, parameter count, and the epoch-60 Dev row. A partial or failed
run is not a completed result and must remain in its private output directory.
