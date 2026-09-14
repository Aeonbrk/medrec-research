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
the patient-independent GIN branches are evaluated once per 32-visit
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
  --official-source-root /root/zhb/medrec-data/external/rx-expert-source-0750f92cfbf51988d78693ef7797a82ead0ea585/src/coarse-grained \
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
| Static GIN execution schedule | One training-mode graph result replayed per 32-visit accumulation batch | Minor execution patch | Makes the official 50-epoch screen tractable; all graph parameters remain trainable |
| Dataset/split/evaluation | Canonical snapshot and Train/Gate01-Dev | Changed | Required comparison protocol adaptation |
| Python identifier spelling | `Rx-Expert` mechanically renamed to `RxExpert` | Minor execution patch | Published source is syntactically invalid otherwise |

The final run record must report independent fidelity and performance verdicts:
`RXEXPERT_FAITHFUL` versus `RXEXPERT_ADAPTATION_FIDELITY_UNRESOLVED`, and only
after fidelity passes, `RXEXPERT_BACKBONE_HEALTHY` versus
`STOP_RXEXPERT_BACKBONE_RESET`.
