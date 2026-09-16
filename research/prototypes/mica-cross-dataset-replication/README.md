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

## Stage -1F execution result

The four authorized arms completed at source revision
`ffdaec8a6c0cdc20d071ad00eca8bb025f336ef0`.  MIMIC-III completed 60 epochs
(656 updates per epoch); MIMIC-IV completed exactly 39,360 updates (19,302
updates per full pass) with 12 full Dev evaluations.  No Test
targets were loaded.  Selected checkpoints and terminal Dev surfaces are:

The canonical MIMIC-III snapshot supplies 1,958 diagnosis, 1,430 procedure,
and 131 medication IDs.  The frozen MIMIC-IV adapter fits 26,070 diagnosis,
13,118 procedure, and 173 medication IDs on Train only; its Dev input uses
explicit unknown tokens and does not extend those axes.

| dataset / arm | parameters | selected update (epoch-equivalent) | selected J | selected F1 | selected PRAUC | selected DDI | selected NLL | terminal J | terminal PRAUC | terminal NLL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MIMIC-III SharedPool | 848900 | 2624 (4.000) | 0.531796 | 0.685760 | 0.785189 | 0.076841 | 0.206553 | 0.437912 | 0.672784 | 1.266637 |
| MIMIC-III DrugQuery | 848900 | 1968 (3.000) | 0.539316 | 0.692880 | 0.788679 | 0.078599 | 0.204234 | 0.445612 | 0.675816 | 1.324851 |
| MIMIC-IV SharedPool | 5436718 | 36080 (1.869) | 0.552883 | 0.698327 | 0.789836 | 0.063074 | 0.115632 | 0.551189 | 0.789019 | 0.116182 |
| MIMIC-IV DrugQuery | 5436718 | 36080 (1.869) | 0.559369 | 0.703702 | 0.796329 | 0.061812 | 0.112925 | 0.557984 | 0.795794 | 0.113301 |

The primary deltas (DrugQuery minus its matched SharedPool) are:

| dataset | ΔJaccard | ΔF1 | ΔPRAUC | ΔNLL | ΔDDI | interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| MIMIC-III | +0.007520 | +0.007120 | +0.003489 | -0.002319 | +0.001758 | meaningful; below the ~+0.008 strong range |
| MIMIC-IV | +0.006486 | +0.005375 | +0.006493 | -0.002707 | -0.001262 | meaningful; below the ~+0.008 strong range |

Both MIMIC-IV arms selected update 36,080 rather than the terminal update;
their terminal Jaccard changes were -0.001385 (DrugQuery) and -0.001694
(SharedPool).  The predeclared terminal-improvement rule therefore does not
make the MIMIC-IV budget inconclusive.  The aggregate verdict is
`MICA_MECHANISM_REPLICATED_BOTH_DATASETS`: medication-specific evidence
selection clears the +0.004 meaningful threshold on both datasets.  This is
single-seed Train/Dev evidence only, not a held-out or paper claim.

The no-training diagnostics are in [`diagnostics.json`](diagnostics.json).
Target cardinality means (median; range) are MIMIC-III Train 18.959 (19; 1–53),
Dev 19.695 (19; 1–51), and MIMIC-IV Train 14.596 (13; 1–67), Dev 14.604 (13;
1–63).  Mean per-visit normalization coverage is 0.762594/0.801292 for
MIMIC-III Train/Dev (the Dev estimate covers 2,129 of 2,130 target visits with
an eligible row) and 0.799133/0.798783 for MIMIC-IV Train/Dev.  Pearson
correlations between target cardinality and coverage are 0.126171/0.012016
and 0.007457/0.002894, respectively.  Full histograms, row denominators, and
the fixed lineage are retained in the public-safe diagnostic JSON.

The complete public-safe aggregate, including all evaluation points, is
[`result.json`](result.json).  Private checkpoints, logits, patient
membership, targets, raw rows, and logs remain on 319.  The only next action
authorized by this screen is scientific review of this frozen Train/Dev
result; do not run another seed, open Test, implement RSM, or enter Stage 0
automatically.
