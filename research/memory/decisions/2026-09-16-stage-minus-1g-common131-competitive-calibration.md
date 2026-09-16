# Stage -1G common-131 protocol correction and competitive calibration

## Trigger

Stage -1G began with MIMIC-IV's dataset-native 173-medication surface. During
the primary-source audit, the official ARMR MIMIC-III/MIMIC-IV vocabularies and
the MoleRec/SafeDrug/Carmen lineage were found to share a 131-code ATC4
identity, while the project-native MIMIC-IV surface is an independent 173-code
vocabulary. This exposed a comparability problem before external results could
be interpreted as a substrate verdict.

## Semantic decision

Admit an additive MIMIC-IV common-131 benchmark reconstructed by exact
uppercase ATC4 identity projection from the frozen native benchmark. Keep the
native-173 benchmark immutable as secondary robustness evidence. The semantic
verdict is `COMMON_131_RECONSTRUCTABLE_WITH_DOCUMENTED_MAPPING`: the published
lineage is reproducible at the identity/mapping level, but the pinned ARMR
commit does not expose one uniquely attributable hidden Carmen threshold.

The common-131 variant retains the frozen split, chronology, strict history,
current-target exclusion, and Train/Dev roles. Native-only medication codes
are dropped from target/history; two canonical codes without native support
remain explicit zero-support columns. Projected-empty target rows are retained
for chronology accounting and excluded from recommendation examples. All
required mechanical checks passed, and DDI/molecular medication rows are
aligned to the canonical order. No Test target or model-performance statistic
was used to define the vocabulary.

## Execution record

The correction is comparability-driven, not performance-driven. Results that
existed before the freeze, including the MIMIC-IV native-173 MICA pair and
native-173 external processes, are preserved and remain secondary/diagnostic.
The primary common-131 matrix uses ARMR, MoleRec, and GAMENet with their
method-appropriate source recipes. A no-training fixed-131/generalized-MICA
equivalence audit passed. During execution, one MoleRec lane lacking
`model.eval()` and pre-fix external evaluator threshold handling were detected;
those attempts remain labeled invalid and were not promoted. Corrected lanes
were launched in separate output directories.

The pinned ARMR `MyNet.forward` source was also audited: it explicitly replaces
the supplied procedure tensor with zeros before encoding. The corrected ARMR
lane preserves that official behavior; it is recorded as a source-faithful
limitation and is not silently repaired or threshold-tuned.

## Decision and consequences

The final Train/Dev competitiveness verdict and paired patient-cluster
bootstrap diagnostics will be appended after all valid common-131 lanes
finish. This stage remains one-seed calibration only: no Test, RSM, Idea 009,
formal Gate, broad sweep, or SOTA claim is authorized.

## Rejected interpretations

- Native-173 is not deleted or silently substituted; it answers a separate
  robustness question.
- Common-131 is not a top-frequency, sorted-ID, or MICA-performance-selected
  vocabulary.
- Literature numbers are not direct comparison rows without matched data and
  information-budget provenance.
- A lower DDI value caused by predicting fewer medications is not by itself a
  safety improvement.
