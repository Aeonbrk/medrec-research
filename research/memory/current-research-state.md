# Current research state — 2026-09-16

This file is the live scientific synthesis and routing authority. It does not replace run-local evidence.

## Current phase

```text
Active formal Idea: none
Ideas 001–008: terminated
Idea 009: absent
Active formal Gate: none
Current phase: post-Stage -1F scientific review
Paper claim: none
Held-out evaluation: untouched for current architecture search
```

The Stage -1 substrate work is complete enough for scientific review. No Stage 0 experiment is authorized by the knowledge-governance migration.

## Validated substrate

### Medication-specific evidence selection

Stage -1F replicated the MICA `DrugQuery` mechanism against matched `SharedPool` controls on both frozen Train/Dev surfaces:

| Dataset | SharedPool J | DrugQuery J | ΔJ | ΔF1 | ΔPRAUC | ΔNLL | ΔDDI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MIMIC-III | 0.531796 | 0.539316 | +0.007520 | +0.007120 | +0.003489 | -0.002319 | +0.001758 |
| MIMIC-IV | 0.552883 | 0.559369 | +0.006486 | +0.005375 | +0.006493 | -0.002707 | -0.001262 |

Observed verdict: `MICA_MECHANISM_REPLICATED_BOTH_DATASETS`.

Interpretation: medication-specific clinical evidence selection is a reusable cross-dataset Train/Dev mechanism. It is not a stable safety claim and not held-out paper evidence.

Evidence:

- `research/prototypes/mica-cross-dataset-replication/result.json`
- `research/prototypes/mica-cross-dataset-replication/diagnostics.json`
- `research/memory/decisions/2026-09-16-mica-cross-dataset-mechanism-replication.md`

### Training dynamics

Stage -1A diagnosed the MIMIC-III MICA family as `OVERFIT_DOMINANT`: Train BCE continued to fall while Dev NLL rose and Dev Jaccard/PRAUC declined. This is shared family/training behavior rather than a DrugQuery-specific failure.

Stage -1B selected AdamW constant `1e-4` as the working recipe for subsequent matched screens. It reduces, but does not remove, late overfitting. Validation checkpoint selection remains necessary.

### MIMIC-IV benchmark

The visit-level MIMIC-IV v3.1 Train/Dev benchmark is frozen and passed source, split, chronology, strict-history, target-leakage, Train-only vocabulary, normalization, DDI, and serialization checks.

Task semantics:

```text
current diagnoses + current procedures
+ strictly previous visit D/P/M history
→ current medication set
```

MIMIC-IV uses dataset-native vocabularies with ATC4 medication targets. Test membership remains sealed; Test medication targets were not loaded for Stage -1E/-1F.

## Current architecture evidence

Preserve as positive evidence:

- MICA DrugQuery over SharedPool on MIMIC-III and MIMIC-IV.
- GraphRefine-SameK as a weak but real patient-conditioned ranking reference, not a current paper direction.

Do not rescue unchanged:

- patient-conditioned dynamic-query family;
- FineHistory refinement after weak-only signal;
- DualEvidence;
- SetContext medication self-attention;
- MICA Early/Late FiLM as the source of the gain;
- post-hoc safety heads that require large accuracy loss;
- strong-unary pairwise residual correction;
- NeedCover, MedState, RxDiffSet-v0, TheraCompose-v0, FutureGraphKD-v0, RxUnitSet target semantics.

These are formulation-local negative results, not universal bans on their primitives.

## Current comparison anchors

MIMIC-III canonical/reference surfaces retained in project memory:

| Surface | Jaccard | PRAUC | DDI | Role |
| --- | ---: | ---: | ---: | --- |
| MoleRec | 0.529174 | 0.773576 | 0.072223 | strong simple canonical anchor |
| GraphRefine-SameK | 0.533650 | 0.784240 | 0.073328 | executed admissible reference |
| HypeMed-LeakageSafe | 0.512112 | 0.753822 | 0.059404 | faithful recent reference |
| Rx-Expert coarse | 0.510522 | 0.757858 | 0.077303 | faithful architecture-family reference |

Literature scores are not automatically comparable when information budget, split, vocabulary, or evaluation differs.

## Current candidate

The leading bounded architecture candidate from scientific review is direct partial regimen assignment (RSM): medication-specific evidence proposals feed anonymous regimen slots that predict medication-or-NULL assignments instead of only independent medication membership probabilities.

This candidate has not been implemented, trained, admitted as Idea 009, or opened as a formal Gate. Before execution, its exact matched controls and attribution must remain able to separate representation capacity, structured supervision, and assignment decoding.

## Evaluation boundaries

- Current exploratory evidence is Train/Dev and single-seed unless a run explicitly states otherwise.
- G3/G4, R0 Holdout, historical Test, and MIMIC-IV Test remain unavailable for exploratory architecture selection.
- DDI is interpreted within a dataset's measurement surface; cross-dataset absolute DDI values are not treated as directly equivalent safety measurements.
- Lower DDI caused by fewer medications is not sufficient evidence of safer treatment.

## Next scientific action

After the knowledge-organization migration receives adversarial engineering review, return to scientific review of the bounded RSM contract. Do not launch a new model, seed, Gate, Idea, or held-out evaluation merely because this file names the candidate.
