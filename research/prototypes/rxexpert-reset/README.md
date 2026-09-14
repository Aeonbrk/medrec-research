# Rx-Expert coarse-grained architecture-family screen

This is a bounded architecture-family triangulation screen, not Idea 009 and
not a new model.  It runs the official coarse-grained Rx-Expert implementation
from `jhxu003/Rx-Expert` at revision
`0750f92cfbf51988d78693ef7797a82ead0ea585` against the canonical medication
recommendation Train/Gate01-Dev split.

The executable model is loaded from an external checkout rather than
reimplemented in this repository.  The loader makes only the two mechanical
syntax repairs required by the published source (`class Rx-Expert` and its
matching `super(...)` call); this source is otherwise executed unchanged.
The official coarse path therefore retains:

- separate diagnosis/procedure pathways;
- two four-GRU expert banks with the upstream learned Top-2 router and
  auxiliary routing loss;
- four-layer GIN global-molecule and BRICS-substructure encoders;
- two-head SetTransformer/SAB substructure encoding;
- fixed `smiles_rep.pkl` drug-caption features and the `1024 -> 64`
  projection;
- DDI-substructure masking, Cross Fusion Module, patient-conditioned
  substructure weighting, history attention, recommendation head, and the
  upstream DDI penalty.

The adaptation changes only the data root, the patient-disjoint Train and
Gate01-Dev partition, target-free history construction, explicit medication
index alignment, canonical evaluation, and one bounded execution optimization:
the patient-independent GIN branches are evaluated once per 256-visit
gradient-accumulation batch rather than once per single-visit update.  This
keeps the official modules, dropout, loss, and 50-epoch budget but is reported
as `RXEXPERT_MINOR_EXECUTION_PATCHES_ONLY`, not byte-for-byte upstream
optimizer scheduling.  It uses the official defaults:
dimension 64, dropout 0.7, Adam at `5e-4`, no weight decay, 50 epochs,
threshold 0.5, DDI coefficient `0.0005`, and the upstream
`0.95 BCE + 0.05 multilabel-margin + MoE auxiliary + DDI` loss.  The primary
seed is `20260914`.

## Source and feature gate

`SOURCE_REVIEW.md` records the primary paper and official-code inspection.
Before training, the runner checks the exact source revision, compares the
canonical and official 131-code medication vocabularies by code, remaps every
official drug row explicitly, verifies the remapped DDI matrix byte values,
loads the official `idx2SMILES.pkl`, `substructure_smiles.pkl`,
`smiles_rep.pkl`, and `ddi_mask_H.pkl`, and asserts finite CUDA forward and
backward values.  `smiles_rep.pkl` is the official fixed
description-derived `[131, 1024]` representation; it is not regenerated,
zero-filled, or replaced with random vectors.

Every target visit is passed with its current medication tuple masked.  The
mechanical history assertion requires that medication history equals prior
visits only.  No Audit/test resource is opened, and no Gate01-Dev label is used
to construct routing, fit features, set thresholds, or select a checkpoint.

## Remote execution

Run in the verified `medrec-molerec-table1` environment on one admitted free
RTX 3090.  The source checkout and all real-data artifacts remain outside Git:

```bash
conda run --no-capture-output -n medrec-molerec-table1 \
  python run_rxexpert.py \
  --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
  --official-source-root /root/zhb/medrec-data/external/rx-expert-source-20260914/src/coarse-grained \
  --device 1 \
  --output /root/zhb/medrec-data/prototypes/rxexpert-reset/rxexpert-screen.json
```

The output contains aggregate metrics, learning-curve checkpoints at epochs
10/20/30/40/50, router utilization/entropy and effective-dead-expert fraction,
the explicit feature mapping audit, and the fidelity/performance verdicts.
`RxExpert-MoleRecK` keeps the Rx-Expert ranking and uses the frozen MoleRec
cardinality for a single count-isolation diagnostic.  `RxExpert-NoMoE` is
created only after faithful execution and the Stage-B health criterion pass;
it retains the upstream four GRUs and parameter scale while bypassing only the
patient-conditioned router.

## Required semantic diff

| Official component | Executed implementation | Status | Reason |
| --- | --- | --- | --- |
| Diagnosis/procedure embeddings and pathways | Upstream `RxExpert` source | Exact | Source loaded at the pinned revision |
| Two four-GRU expert banks | Upstream `GRUExperts` | Exact | No architecture rewrite |
| Patient-conditioned router | Upstream `MoE`/`Top2Gating` | Exact | Non-invasive probes observe indices/weights |
| MoE auxiliary loss | Upstream returned loss with coefficient `1e-2` | Exact | Included in official training expression |
| Global molecular GIN | Upstream `GNNGraph` | Exact | Official OGB/GIN graph construction |
| Substructure GIN + SAB | Upstream `GNNGraph` + `SAB` | Exact | Official BRICS list and graph batch |
| Drug caption representation | Official `smiles_rep.pkl`, explicitly remapped by code | Exact | Zero/random substitution is forbidden |
| DDI substructure mask | Official `ddi_mask_H.pkl`, explicitly remapped by code | Exact | Official mask has 492 substructures |
| Cross-feature fusion and history attention | Upstream `CFM` and `patient_data[:-1]` semantics | Exact | Current target is masked at adapter boundary |
| Recommendation head and DDI penalty | Upstream head and `0.0005` penalty | Exact | Official loss preserved |
| Static GIN execution schedule | One training-mode graph result replayed per 256-visit accumulation batch | Minor execution patch | Makes the official 50-epoch screen tractable; all graph parameters remain trainable |
| Dataset/split/evaluation | Canonical snapshot and Train/Gate01-Dev | Changed | Required comparison protocol adaptation |
| Python identifier spelling | `Rx-Expert` mechanically renamed to `RxExpert` | Minor execution patch | Published source is syntactically invalid otherwise |

The final run record must report independent fidelity and performance verdicts:
`RXEXPERT_FAITHFUL` versus `RXEXPERT_ADAPTATION_FIDELITY_UNRESOLVED`, and only
after fidelity passes, `RXEXPERT_BACKBONE_HEALTHY` versus
`STOP_RXEXPERT_BACKBONE_RESET`.

## Completed canonical Stage-B run

The one primary run completed on GPU 1 (`NVIDIA GeForce RTX 3090`) from the
remote checkout at `659f2994`; its aggregate record remains outside Git at
`/root/zhb/medrec-data/prototypes/rxexpert-reset/rxexpert-screen.json`.
The exact official source revision was
`0750f92cfbf51988d78693ef7797a82ead0ea585`.  The run used 50 epochs,
897,512 trainable parameters, 10,096.65 seconds of training, and a peak
reported allocation of 2,418,910,720 bytes.  The CUDA finite
forward/backward probe was finite.  The current branch contains a
post-run metadata-only correction that names the four supplied GRUs per path
as `gru_experts_per_path` and separately records the official 16-gate router;
the numeric run and model computation are unchanged.

Source sanity was limited to loading the pinned upstream modules and supplied
feature files, constructing the official graphs, and passing finite CPU/CUDA
forward/backward probes.  The upstream positional-split/test loop was not run:
it would access noncanonical/held-out resources and is not evidence for this
screen; the README checkpoint was not used as a tuning target.

| Method | Jaccard | F1 | PRAUC | DDI | AvgMed |
| --- | ---: | ---: | ---: | ---: | ---: |
| MoleRec | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 |
| RxExpert | 0.510522 | 0.666965 | 0.757858 | 0.077303 | 22.4268 |
| RxExpert-MoleRecK | 0.507881 | 0.664807 | 0.757858 | 0.076507 | 21.5451 |

The frozen-MoleRec-cardinality diagnostic changed the Rx-Expert set on
99.15% of Dev visits before selecting the same count, while the direct
threshold output differed on 99.81% of visits.  The learning curve was:

| Epoch | Train loss | Dev Jaccard | Dev F1 | Dev PRAUC | Dev DDI | Dev AvgMed |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 0.724855 | 0.457785 | 0.618976 | 0.717925 | 0.080329 | 21.1455 |
| 20 | 0.668535 | 0.486013 | 0.644911 | 0.737780 | 0.081737 | 21.8066 |
| 30 | 0.636356 | 0.492287 | 0.650542 | 0.745762 | 0.077699 | 22.3620 |
| 40 | 0.611871 | 0.501373 | 0.658863 | 0.751263 | 0.078081 | 22.6423 |
| 50 | 0.594075 | 0.510522 | 0.666965 | 0.757858 | 0.077303 | 22.4268 |

The router diagnostic used the official 16-gate Top-2 router over the two
four-GRU banks.  Before training, normalized routing entropy was `0.602820`
with an effective dead-expert fraction of `0.125`; after training it was
`0.947908` with dead-expert fraction `0.0625`.  Post-training routing entropy
was `2.628161` nats (`16` gates; maximum `ln(16)`), with combined Top-2
utilization:

```text
[0.020833, 0.020833, 0.125000, 0.062500, 0.062500, 0.104167,
 0.020833, 0.083333, 0.020833, 0.125000, 0.020833, 0.125000,
 0.062500, 0.020833, 0.000000, 0.125000]
```

Post-training mean routing weights were:

```text
[0.054752, 0.051145, 0.069341, 0.061392, 0.058788, 0.080485,
 0.055927, 0.071581, 0.061603, 0.071426, 0.058640, 0.055148,
 0.066556, 0.051598, 0.064666, 0.066950]
```

The feature gate passed: the canonical-to-official medication mapping was
identity with mapping checksum
`55362ad63c61cc4b91f7583d455ae5ab0dbac991b1a14a6cf835a8e46fb98d2b`;
`smiles_rep.pkl` was the official fixed drug-description tensor of shape
`[131, 1024]`, `torch.float32`; `idx2SMILES.pkl` covered 283 molecular SMILES;
the BRICS substructure list had 492 entries; `ddi_mask_H.pkl` was `[131, 492]`;
and the explicitly remapped official DDI adjacency equaled the canonical
matrix.  The relevant external-file SHA-256 values are:

```text
smiles_rep.pkl          784f790e25e83cd12b0d12acfca0d9061f8732ff306e75b1ee2ec91d38e66451
idx2SMILES.pkl          b1eaaba3a8bdcb2c7d51b7edaa53ed4357a76d5f8f4b9fa3bdcc4c4dc8a21ce6
substructure_smiles.pkl 5e24dea0d9733f100d57b6730403029023ed6a408d886243a77419644f2f674c
ddi_mask_H.pkl          5f2c43f8cacd3c36d1156545d15edfa8fc5f25492800f1a9824ffc25e293ee89
```

Protocol closeout: no held-out Audit/test resource was accessed; no Gate01-Dev
label entered routing construction, feature fitting, thresholds, loss
weighting, or model selection; no shared `main` checkout was overwritten; and
unrelated `.gitignore`, `slides/`, and other user files were left untouched.

The independent verdicts are:

- Fidelity: `RXEXPERT_MINOR_EXECUTION_PATCHES_ONLY`.  The only execution
  patch beyond the official modules is the documented static patient-
  independent GIN replay within each 256-visit accumulation batch, plus the
  mechanical Python identifier repair and canonical data/evaluation adapter.
- Performance: `STOP_RXEXPERT_BACKBONE_RESET`.  Final Jaccard (`0.510522`)
  was below `0.540`; PRAUC (`0.757858`) was below MoleRec by more than
  `0.001`; and DDI (`0.077303`) was not at least `0.010` below MoleRec.
  `RxExpert-NoMoE` was therefore not run, as required.
