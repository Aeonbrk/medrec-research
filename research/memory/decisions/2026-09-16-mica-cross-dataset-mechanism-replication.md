# MICA medication-specific evidence selection replicates across MIMIC-III and MIMIC-IV

## Context / Trigger

Stage -1F tested the same scientific question on two frozen Train/Dev surfaces: whether medication-specific clinical evidence selection (`DrugQuery`) improves over a matched shared clinical pool (`SharedPool`). Both arms used the same source revision and matched training recipe within each dataset. MIMIC-IV used an optimizer-update budget appropriate to its much larger training set rather than mechanically copying 60 epochs.

Decisive evidence:

- `research/prototypes/mica-cross-dataset-replication/result.json`
- `research/prototypes/mica-cross-dataset-replication/diagnostics.json`
- `research/prototypes/mica-cross-dataset-replication/README.md`
- `research/benchmarks/mimiciv-medrec/`

## Decision / Belief Update

Observed result: `DrugQuery - SharedPool` improved Dev Jaccard by `+0.007520` on MIMIC-III and `+0.006486` on MIMIC-IV. F1, PRAUC, and NLL also moved in the favorable direction on both datasets. The frozen Stage -1F verdict is `MICA_MECHANISM_REPLICATED_BOTH_DATASETS`.

Interpretation: medication-specific evidence selection is now a reusable mechanism with cross-dataset Train/Dev support. The evidence is stronger than the earlier single-dataset attribution, but it is still single-seed development evidence rather than held-out paper confirmation.

Routing guidance: preserve MICA-Core/DrugQuery as a validated substrate or building block. It is not mandatory as the backbone of every future model.

## Rejected Alternatives / Interpretations

- Do not interpret the result as a stable safety improvement. MIMIC-IV DDI improved while MIMIC-III DDI worsened slightly.
- Do not interpret it as a held-out generalization claim; Test remains untouched.
- Do not revive patient-conditioned dynamic-query variants. Their matched Stage -1 screen showed no material contribution.
- Do not claim that medication-specific attention itself is novel; novelty requires the complete future mechanism and primary-source comparison.
- Do not require equal epoch counts across MIMIC-III and MIMIC-IV; the datasets differ by orders of magnitude in training examples, so matched scientific arms use dataset-appropriate frozen budgets.

## Consequences / Invariants

- Future MICA-derived architecture screens should use DrugQuery as the validated proposal/evidence reader when that role is scientifically appropriate.
- A new method must still introduce a material new prediction process, representation, information flow, decoder, or supervision mechanism; adding a small head to MICA-Core is not enough.
- Test, G3/G4, R0 Holdout, and other quarantined surfaces remain unavailable for exploratory architecture selection.
- The current leading bounded architecture candidate is direct partial regimen assignment (RSM), but no Stage 0 experiment, formal Idea, or Gate is created by this note.
