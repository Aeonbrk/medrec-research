# MICA cross-dataset mechanism replication (Stage -1F)

This directory contains the matched Train/Dev screen for the frozen MICA
mechanism on the canonical MIMIC-III surface and the frozen Stage -1E
MIMIC-IV visit-level adapter.  It is additive to the historical MICA
prototype and does not read the MIMIC-IV Test targets.

## Frozen question

Within each dataset, does medication-specific clinical evidence selection
(`DrugQuery`) improve the matched medication-independent `SharedPool` control?
The primary signed delta is:

```text
Delta_query = Jaccard(DrugQuery) - Jaccard(SharedPool)
```

The two arms use the same MICA dimensions, BCE plus normalized DDI loss,
seed `20260914`, AdamW learning rate `1e-4`, weight decay `1e-4`, batch size
16, sigmoid threshold `0.35`, and strict highest-complete-Dev-Jaccard
checkpoint selection (earliest exact tie).  MIMIC-III runs for 60 complete
epochs.  MIMIC-IV is deliberately capped at exactly `39,360` optimizer
updates, with a full Dev evaluation every `3,280` updates; this is not an
automatic continuation rule.

The MIMIC-IV runner uses only the private Train/Dev JSONL materialized by
Stage -1E.  It indexes those files without copying them into Git, verifies
strict prefix history and target-only labels while parsing, and supports the
dataset-native 173-medication vocabulary through the optional medication
dimension in the historical MICA module.  The existing default of 131
medications is unchanged for all historical MICA runs.

## Budget interpretation

The budget-inconclusive condition is predeclared: if the selected MIMIC-IV
checkpoint is the terminal evaluation and terminal Dev Jaccard exceeds the
immediately preceding full evaluation by more than `0.002`, the final verdict
is `MIMIC_IV_TRAINING_BUDGET_INCONCLUSIVE`.  No extension is launched from
that result.

Otherwise, both dataset deltas above `+0.004` yield
`MICA_MECHANISM_REPLICATED_BOTH_DATASETS`; a MIMIC-IV delta at or below zero
yields `MICA_MECHANISM_NOT_REPLICATED_MIMIC_IV`; all other valid positive but
non-meaningful outcomes yield `WEAK_CROSS_DATASET_REPLICATION`.  These are
Train/Dev routing labels, not paper or held-out claims.

## Remote execution contract

Use a clean checkout at the exact `--source-revision` on the approved 319
execution plane.  Keep all checkpoints, logits, JSONL indexes, patient
membership, targets, and logs outside Git.  The four authorized lanes are:

```text
GPU 0  MIMIC-III SharedPool
GPU 1  MIMIC-III DrugQuery
GPU 2  MIMIC-IV SharedPool
GPU 3  MIMIC-IV DrugQuery
```

Prepare the private MIMIC-IV JSONL indexes once, run each lane with its
explicit `CUDA_VISIBLE_DEVICES`, and then summarize only aggregate
`results.json` files.  Do not run a model on Test, add a seed, tune a
threshold, or start Stage 0/RSM from this directory.

## Diagnostics

`diagnose_replication.py` is a no-training Train/Dev diagnostic.  It reports
target-set cardinality, per-visit normalization coverage where raw provenance
is available, and the observed-set-size/coverage correlation.  A missing
MIMIC-III raw provenance artifact is reported as unavailable rather than
treated as 100% coverage.

