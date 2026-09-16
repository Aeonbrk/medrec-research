# MIMIC-IV common-131 benchmark variant

This is an additive Stage -1G benchmark variant. It does not replace
[`../mimiciv-medrec`](../mimiciv-medrec), whose native-173 surface remains the
secondary robustness benchmark.

The 131 medication axis is the canonical ATC4 code set reconstructed from the
pinned MoleRec/SafeDrug/Carmen preprocessing lineage and verified against the
official ARMR MIMIC-III and MIMIC-IV vocabularies. The frozen hash of the
sorted code set is
`6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08`.

`semantic-audit.json` records the source and identity audit. `vocabulary.json`
is the public ordered medication list. `materialize_common131.py` is the
restricted-plane materializer; it reads the frozen native MIMIC-IV JSONL and
writes private projected rows, offsets, and an aggregate manifest outside Git.

Projection is exact uppercase ATC4 identity. Native-only codes are dropped
from target and history; the two canonical codes without native support remain
explicit zero-support output columns. Projected-empty targets are excluded
from recommendation examples but retained in the chronology audit and counted
in the manifest. No target-frequency or model-performance statistic selects
the vocabulary.

The pinned MoleRec asset set contains one source-native invalid `L01X` SMILES;
the official `buildPrjSmiles` path drops that molecule from its projection while
retaining the medication row. No replacement structure or unknown-medication
mapping is introduced.

The variant is Train/Dev-only for Stage -1G. It reuses the native patient split,
visit chronology, current-target exclusion, and strict previous-visit history
contract. It must never be populated with Test rows or targets.
