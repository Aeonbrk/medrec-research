<!-- markdownlint-disable MD013 -->

# Frozen MIMIC-IV visit-level medication-recommendation benchmark

## Stage boundary

`STAGE -1E, MIMIC-IV VISIT-LEVEL MEDREC BENCHMARK MATERIALIZATION`

This directory records a public-safe Train/Dev materialization of MIMIC-IV
v3.1. It remains `PRE-IDEA`, `PRE-GATE`, `NO PAPER CLAIM`, `NO HOLDOUT TEST`,
and `NO NEW METHOD FAMILY`. No model was trained and no Test target was read
for statistics or evaluation.

## Frozen identity

- Benchmark: `mimiciv-visit-medrec-stage-minus-1e`
- Adapter source revision: `e87411be3df305f55a4a68d10a9db3eb505e1232`
- Public manifest digest: `110090bb79411ecf9f8057e75e16a1f6cb0c0e4b4e159bc29d4434018628da23`
- Source release: MIMIC-IV v3.1, hospital tables only
- Terminal verdict: `MIMIC_IV_BENCHMARK_FROZEN_READY_FOR_TRAINDEV`

The restricted 319 output contains the Train/Dev examples, Train-only
vocabularies, projected DDI matrix, mapping manifest, and split membership.
Only aggregate counts, hashes, coverage, and mechanical verdicts are checked
in here.

## Task contract

For patient `p` and chronologically ordered admission `t`:

```text
(D_t, P_t, [(D_j, P_j, M_j) for j < t]) -> M_t
```

`D_t` and `P_t` are the current diagnosis/procedure sets. `M_t` is target-only;
the input contains no current medication row, count, embedding, or DDI feature.
History is a strict prefix ordered by `admittime`, then deterministic `hadm_id`
tie-break. Visits without a mapped target remain in the prefix but do not
become recommendation examples.

Medication normalization is deterministic and versioned:

```text
NDC -> direct mapped ATC4 identity
    -> NDC -> RxNorm -> ATC4
    -> KGDNet NDC/RxNorm fallback
    -> Train-only formulary consensus fallback
```

The upstream mapping column is named `ATC4` and contains five-character
entries. The SafeDrug/MoleRec MICA vocabulary and DDI authority use the
four-character identity; the frozen adapter therefore applies the documented
`ATC4[:4]` projection. Unmapped rows are counted and excluded from the target;
no artificial medication `UNK` is added.

Diagnosis and procedure vocabularies are fitted on Train only and serialize
Dev/Test input codes outside those vocabularies as the explicit `<UNK>` token;
raw OOV counts remain reported in the manifest. Medication target vocabulary is
the Train-observed normalized identity set; Dev OOV targets are reported rather
than injected.

## Materialized aggregate

| role | patients | visits | recommendation examples | dx vocab | procedure vocab | medication vocab |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 149,001 | 364,492 | 308,824 | 26,070 | 13,118 | 173 |
| Dev | 37,076 | 90,033 | 76,529 | - | - | - |
| Test seal | 37,375 | membership only | not materialized | - | - | - |

Train normalization covers `10,602,979 / 13,490,898` eligible prescription
rows (`0.785936`); Dev covers `2,630,601 / 3,349,376` (`0.785400`). Dev target
medication OOV is `0 / 1,117,597` tokens. Diagnosis and procedure input OOV
rates are `0.001109` and `0.005854`, respectively.

The frozen SafeDrug/MoleRec matrix has 131 source concepts, 91 concepts with
DDI support, and 448 source pairs. Projection onto the 173-concept Train
medication vocabulary represents 129 source concepts (`0.984733`), retains 90
of the 91 DDI-supported concepts (`0.989011`), and retains 443 pairs. The
projected matrix is finite, binary, symmetric, and zero-diagonal. Coverage is
reported, not turned into a new arbitrary threshold or supplemented with
inferred pairs.

## Cross-dataset comparability

| contract field | MIMIC-III MICA | MIMIC-IV frozen adapter |
| --- | --- | --- |
| Task granularity | visit | visit |
| Current D/P input | yes | yes |
| Past D/P/M history | strict | strict |
| Current M in input | no | no |
| Medication level | ATC4 SafeDrug/MoleRec identity | ATC4 SafeDrug/MoleRec identity |
| Split | patient, 2/3–1/6–1/6 | patient, 2/3–1/6–1/6 |
| Train / Dev / Test role | Train / Dev / untouched Test | Train / Dev / sealed Test |
| DDI authority | SafeDrug/MoleRec canonical matrix | same authority, projected by identity |
| Decoder threshold | fixed 0.35 | fixed 0.35 |

This is the same task semantics, not the same vocabulary, cohort, or absolute
difficulty. The next authorized action is to review this frozen contract and,
only if accepted, run the separately specified MIMIC-IV Train/Dev SharedPool
versus MICA-Core screen. That screen is prepared but was not run in Stage -1E.

See [`protocol.json`](protocol.json), [`manifest.json`](manifest.json), and
[`mechanical-checks.json`](mechanical-checks.json) for the machine-readable
contract and public-safe evidence.
