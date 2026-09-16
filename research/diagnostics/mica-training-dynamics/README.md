# MICA training-dynamics diagnosis

## Stage boundary

`STAGE -1A — MICA CORE CONSOLIDATION + TRAINING DIAGNOSIS + MIMIC-IV READINESS`

This is a pre-idea, pre-gate, Train/Dev-only diagnostic. It is not a paper
claim, a holdout evaluation, or permission to reopen the Dynamic Query,
FineHistory, DualEvidence, SetContext, Late FiLM, or other closed families.

The source progress files were read on the execution plane and reduced to
aggregate epoch rows before intake. The repository contains no patient IDs,
targets, logits, checkpoints, or raw logs. [`diagnosis.json`](diagnosis.json)
and [`learning_curves.csv`](learning_curves.csv) are therefore evidence for
training dynamics only, not a replacement for the original prototype result
artifacts.

## Update accounting

The canonical MICA run has 10,489 Train visits and batch size 16, hence
`ceil(10,489 / 16) = 656` optimizer updates per epoch:

| Point | Updates |
| --- | ---: |
| Epoch 3 | 1,968 |
| Epoch 4 | 2,624 |
| Epoch 60 | 39,360 |

The optimizer-update view does not change the conclusion: the Dev surface
peaks after roughly two thousand updates, while the training objective keeps
improving for the remaining 36,000-plus updates.

## Diagnosis

`OVERFIT_DOMINANT`

All 15 arms for which complete epoch-level progress was available show the
same shape. Train BCE decreases on 58–59 of 59 transitions; the largest total
loss increase is below the material-drift threshold used by the diagnostic.
Dev Jaccard and PRAUC fall materially by epoch 60, while Dev NLL drifts up.
Twelve arms select epoch 3 and three select epoch 4. The common timing across
MICA SharedPool/DrugQuery/Late, MICA-v2 controls, and all six Dynamic Query
arms points to the shared optimizer/encoder recipe and rapid memorization of
the small Train surface. It does not identify DrugQuery as the cause, and it
does not alter the existing DrugQuery attribution verdict.

Representative MICA rows:

| Arm | Best J epoch | Best J | Best PRAUC | Best NLL epoch | Best NLL | Epoch-60 J | Epoch-60 PRAUC | Epoch-60 NLL | Epoch-60 train BCE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SharedPool | 3 | 0.532430 | 0.787419 | 3 | 0.205589 | 0.458946 | 0.702440 | 0.618642 | 0.057145 |
| DrugQuery / Core | 3 | 0.542244 | 0.792730 | 3 | 0.202483 | 0.474090 | 0.714524 | 0.540265 | 0.062049 |
| MICA-Late | 3 | 0.541656 | 0.792254 | 3 | 0.202460 | 0.475597 | 0.717962 | 0.526675 | 0.061618 |

The complete curve file includes Train total loss, BCE, DDI loss and Dev
Jaccard, F1, PRAUC, and NLL for every included arm. It also records the source
revision and optimizer-update count on every row.

## Family coverage

| Family | Included complete progress | Peak epochs |
| --- | --- | --- |
| MICA | SharedPool, DrugQuery/Core, MICA-Late | 3, 3, 3 |
| MICA-v2 | Core, FineHistory, DualEvidence, SelfOnly, SetContext, SafeRank | 3, 3, 3, 4, 4, 3 |
| Dynamic Query | Core, StaticMultiQuery, GlobalDynamicMultiQuery, EvidenceDynamicMultiQuery, StaticQueryAdapter, DynamicQueryAdapter | 3, 3, 3, 4, 3, 3 |

The public v2 aggregate contains a SafePTO row, but no corresponding
epoch-level progress artifact was available. It is explicitly marked as
`MISSING_EPOCH_PROGRESS` in the JSON; no SafePTO curve or classification is
invented.

## Historical baseline context

The archived MoleRec/SafeDrug/GAMENet/RETAIN logs are not semantically
identical to MICA's row-level progress (their native evaluators and split
roles differ), so they are not pooled into the classifier. Their available
training records still show why “best epoch” must be reported with the native
selection rule. The per-epoch validation rows extracted from those logs are in
[`baseline_learning_curves.csv`](baseline_learning_curves.csv); they contain
only aggregate metrics, not patient-level data.

| Baseline | Complete epochs | Logged best epoch | Optimizer / LR evidence | Scheduler evidence | Checkpoint rule |
| --- | ---: | ---: | --- | --- | --- |
| MoleRec embedding | 50 | source index 44 (human epoch 45) | Adam, `5e-4` | none observed | native validation Jaccard, checkpoint per epoch |
| GAMENet | 50 | source index 48 (human epoch 49) | Adam, run `5e-4` | none in source | strict best validation Jaccard on `data_eval` |
| RETAIN | 50 | source index 49 (human epoch 50) | Adam, run `5e-4` | none in source | strict best validation Jaccard on `data_eval` |
| SafeDrug | 50 | source index 29 (human epoch 30) | Adam, selected run `5e-4` | none in source | strict best validation Jaccard on `data_eval` |

The baseline source loops over 4,233 Train patients, one optimizer update per
patient, so the rough update count is 4,233 per epoch (for example, MoleRec's
human epoch 45 is about 190,485 updates). This is not directly comparable to
MICA's 656 visit-batches per epoch: the baseline records are retained as
historical context and their evaluation surface is not merged with the MICA
classifier.

These rows are historical context only. They do not justify changing MICA's
recipe or architecture, and no test-side result was read for this diagnostic.

## Consequence for Stage -1B

The next bounded question is exactly the frozen recipe test: whether constant
`3e-4` causes late drift relative to constant `1e-4` or a 60-epoch cosine
decay to `3e-6`. Only MICA-Core, seed `20260914`, the existing Train/Dev
surface, and the three declared arms are authorized.
