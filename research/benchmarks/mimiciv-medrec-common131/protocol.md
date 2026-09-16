# MIMIC-IV common-131 materialization protocol

## Scope

Materialize an additive MIMIC-IV common-131 surface for the Stage -1G primary
comparison. The native-173 benchmark remains immutable and is used only as a
secondary robustness surface.

## Frozen inputs

- native Stage -1E MIMIC-IV benchmark and manifest;
- the frozen patient split and Train/Dev/Test roles;
- diagnosis/procedure channels and visit chronology;
- canonical ordered vocabulary in `vocabulary.json`;
- canonical MoleRec/SafeDrug DDI and molecular assets;
- source revision `53765aa3c4ca5197bad38f768aea48c36ef48fa6`.

## Mapping

For every native medication token, retain it iff its normalized uppercase
four-character ATC token is in the canonical list. Apply the same projection to
the current target and strictly previous medication history. Do not infer a
mapping from model scores, Dev/Test frequencies, sorted native IDs, or a
top-131 frequency cutoff.

The canonical vocabulary is the established MoleRec/SafeDrug/Carmen ATC4
lineage. ARMR's official MIMIC-III and MIMIC-IV vocabularies are independent
identity checks: both contain the same 131-code set, although ARMR MIMIC-IV
uses a different insertion order. All consumers reindex to the frozen canonical
order.

## Empty projected targets

Keep the source row's chronology and history in the restricted audit, count the
row and affected patient, and exclude the row from recommendation examples.
This policy is frozen before training and is recorded in `manifest.json`.

## Required checks

The materializer and an independent validator must report passing results for
source identity, patient-split disjointness, chronology, strict history,
current-target exclusion, Train-only vocabulary fit, deterministic
normalization, DDI validity, and Train/Dev serialization reload. Test targets
must not be loaded.

## Asset alignment

Medication row order is canonical common-131 for the target vocabulary, DDI
matrix, MoleRec molecular projection, BRICS/SafeDrug masks, and evaluator.
MoleRec and SafeDrug may use different BRICS column orderings; their medication
rows must still align and their method-local mask hashes must be recorded.
The pinned MoleRec asset has one invalid `L01X` SMILES. The upstream
`buildPrjSmiles` behavior (drop that molecule from the row projection) is
preserved verbatim; no replacement or unsupported-medication imputation is
allowed.
