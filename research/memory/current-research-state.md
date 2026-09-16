# Current research state — 2026-09-16

This file is the live scientific synthesis and routing authority. It does not replace run-local evidence.

## Current phase

```text
Active formal Idea: none
Ideas 001–008: terminated
Idea 009: absent
Active formal Gate: none
Current phase: STAGE -1G — COMPETITIVE SUBSTRATE CALIBRATION
Stage -1G status: EXECUTION_PAUSED_AFTER_INVALIDATED_EXTERNAL_LANES
Paper claim: none
Held-out evaluation: untouched for current architecture search
Knowledge-home migration review: PASS
```

Stage -1F established a reusable cross-dataset MICA mechanism. Stage -1G
common-131 materialization and qualification evidence are preserved, but the
incomplete MIMIC-IV external lanes were stopped before terminal comparison.
There is no Stage -1G substrate verdict.

## Validated substrate

### Medication-specific evidence selection

Stage -1F replicated MICA `DrugQuery` against matched `SharedPool` controls on both frozen Train/Dev surfaces:

| Dataset | SharedPool J | DrugQuery J | ΔJ | ΔF1 | ΔPRAUC | ΔNLL | ΔDDI |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MIMIC-III | 0.531796 | 0.539316 | +0.007520 | +0.007120 | +0.003489 | -0.002319 | +0.001758 |
| MIMIC-IV | 0.552883 | 0.559369 | +0.006486 | +0.005375 | +0.006493 | -0.002707 | -0.001262 |

Observed verdict: `MICA_MECHANISM_REPLICATED_BOTH_DATASETS`.

Interpretation: medication-specific clinical evidence selection is a reusable cross-dataset Train/Dev mechanism. It is not a stable safety claim, SOTA claim, or held-out paper result.

Evidence:

- `research/prototypes/mica-cross-dataset-replication/result.json`
- `research/prototypes/mica-cross-dataset-replication/diagnostics.json`
- `research/memory/decisions/2026-09-16-mica-cross-dataset-mechanism-replication.md`

### Training dynamics

Stage -1A diagnosed the MIMIC-III MICA family as `OVERFIT_DOMINANT`: Train BCE continued to fall while Dev NLL rose and Dev Jaccard/PRAUC declined. Stage -1B selected AdamW constant `1e-4` as the working MICA-family recipe; it reduces but does not remove late overfitting.

This recipe is not a universal baseline recipe. External methods in Stage -1G retain method-appropriate training semantics.

### MIMIC-IV benchmark

The visit-level MIMIC-IV v3.1 Train/Dev benchmark is frozen and passed source, split, chronology, strict-history, current-target leakage, Train-only vocabulary, normalization, DDI, and serialization checks.

Task semantics:

```text
current diagnoses + current procedures
+ strictly previous visit D/P/M history
→ current medication set
```

MIMIC-IV uses dataset-native vocabularies with ATC4 medication targets. Test membership remains sealed; Test medication targets were not loaded for Stage -1E/-1F and remain unavailable in Stage -1G.

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
| MoleRec | 0.529174 | 0.773576 | 0.072223 | strong canonical anchor |
| GraphRefine-SameK | 0.533650 | 0.784240 | 0.073328 | executed admissible reference |
| HypeMed-LeakageSafe | 0.512112 | 0.753822 | 0.059404 | faithful recent reference |
| Rx-Expert coarse | 0.510522 | 0.757858 | 0.077303 | faithful architecture-family reference |

These surfaces do not establish a complete paper benchmark. MIMIC-IV currently lacks strong external methods under the frozen project protocol. Literature scores are not directly comparable when cohort, information budget, vocabulary, split, or evaluation differs.

## Stage -1G contract

Scientific question:

> Is MICA-Core competitive enough against strong faithful external methods on both frozen datasets to justify building the next architecture on top of it?

Frozen contract:

- `research/prototypes/mica-competitive-substrate-calibration/protocol.md`
- `research/memory/decisions/2026-09-16-stage-minus-1g-competitive-substrate-calibration.md`

Stage -1G phases:

1. no-training fixed-131/generalized-MICA equivalence audit;
2. primary-source and official-code baseline qualification;
3. exactly three qualified baseline families × MIMIC-III/MIMIC-IV using six GPUs;
4. common accuracy/safety/efficiency readout plus Dev-only paired patient-cluster bootstrap diagnostics;
5. substrate competitiveness decision.

External baselines share the frozen task, information budget, split roles, target semantics, and evaluator. They do not share one forced optimizer. The Baseline Core keeps its documented method-specific training and prediction behavior.

Preferred recent candidates are ARMR, HypeMed, and SSPNet. SSPNet is executable only with trustworthy implementation provenance; otherwise a faithful compatible fallback such as GAMENet is used. Molecular methods require valid method-native medication assets across the frozen output vocabulary.

Terminal Stage -1G verdicts:

- `MICA_SUBSTRATE_COMPETITIVE_BOTH_DATASETS`
- `MICA_SUBSTRATE_BORDERLINE`
- `MICA_SUBSTRATE_OUTCLASSED`
- `INSUFFICIENT_COMPETITIVE_CALIBRATION`
- `STOP_MICA_GENERALIZATION_EQUIVALENCE_FAILURE`

Only the first verdict permits returning to Stage 0 RSM contract review.

## Current candidate

Direct Partial Regimen Assignment / RSM remains the leading bounded architecture candidate, but it is deferred behind Stage -1G. It has not been implemented, trained, admitted as Idea 009, or opened as a formal Gate.

The candidate remains scientifically interesting because it changes the final decision from independent medication membership to direct medication-or-NULL partial set assignment over medication-specific evidence proposals. Its value should not be tested until the substrate is shown to be externally competitive.

## Stage -1G cleanup disposition

- `research/benchmarks/mimiciv-medrec-common131/` remains a preserved
  harmonized Train/Dev development surface; it is not an official universal
  MIMIC-IV benchmark.
- Valid Stage -1F MICA evidence, G0 equivalence evidence, common-131
  materialization, qualification, and completed MIMIC-III aggregates remain
  authoritative for what they actually record.
- Incomplete MIMIC-IV ARMR, MoleRec, GAMENet, and RETAIN lanes, plus prior
  native-173 diagnostic lanes, are recorded as invalidated diagnostics in
  `research/prototypes/mica-competitive-substrate-calibration/cleanup-invalidation.json`.
- No external baseline is admitted as a primary paper comparison row and no
  substrate verdict has been issued.

## Evaluation boundaries

- Stage -1G is Train/Dev and one seed per baseline arm unless a run explicitly states otherwise.
- G3/G4, R0 Holdout, historical Test, and MIMIC-IV Test remain unavailable for architecture or substrate selection.
- DDI is interpreted within a dataset's measurement surface; cross-dataset absolute DDI values are not one common safety scale.
- Lower DDI caused by under-prescription is not sufficient evidence of safer treatment.
- Published scores from differently processed MIMIC datasets remain literature context, not direct comparison rows.
- Final paper confirmation, if a model survives, requires broader baselines, multiple training seeds, untouched Test, decisive ablations, and final statistical evidence.

## Knowledge-organization status

The migration at `3c420eb0d810c10f629f575495a767aef5698436` passed independent adversarial review with no blocker, major, or minor findings. The accepted engineering record is `.agents/notes/migrations/2026-09-16-knowledge-home-review-pass.md`.

## Next scientific action

Independent cleanup/fidelity review is required before any new experiment.
Do not resume Stage -1G lanes, read Test, implement RSM, create Idea 009,
open a Gate, or broaden into a final-paper benchmark without that review.
