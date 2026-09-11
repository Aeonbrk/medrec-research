# Pair/Context Incremental Value Decision

## Scientific question

Does strict drug-changing order-revision supervision contain context-dependent, cross-patient predictive value beyond ordinary flattened final-prescription supervision and trivial source/destination frequency structure?

## Semantic-object integrity

`PASS_SEMANTIC_ADMISSION` strict identity was re-materialized: 1040 events observed (expected 1040), with 0 frozen semantic violations.

## Aggregate partition counts

| Partition | Strict events | Unique patients |
| --- | ---: | ---: |
| Discovery | 855 | 835 |
| Dev | 185 | 176 |

## Variant metrics

### `DestinationMarginal`

| Seed | Dev NLL | MRR | Hit@5 |
| ---: | ---: | ---: | ---: |
| 260911 | 3.8409421039 | 0.195975842748 | 0.302702702703 |
| 260912 | 3.8409421039 | 0.195975842748 | 0.302702702703 |
| 260913 | 3.8409421039 | 0.195975842748 | 0.302702702703 |
| mean | 3.8409421039 | 0.195975842748 | 0.302702702703 |

### `SourceTransitionPrior`

| Seed | Dev NLL | MRR | Hit@5 |
| ---: | ---: | ---: | ---: |
| 260911 | 4.52416922182 | 0.275651004847 | 0.389189189189 |
| 260912 | 4.52416922182 | 0.275651004847 | 0.389189189189 |
| 260913 | 4.52416922182 | 0.275651004847 | 0.389189189189 |
| mean | 4.52416922182 | 0.275651004847 | 0.389189189189 |

### `FlatFinalBase`

| Seed | Dev NLL | MRR | Hit@5 |
| ---: | ---: | ---: | ---: |
| 260911 | 4.12712049484 | 0.166427101804 | 0.243243243243 |
| 260912 | 4.01619291306 | 0.165526966254 | 0.221621621622 |
| 260913 | 4.16385650635 | 0.166979215245 | 0.232432432432 |
| mean | 4.10238997142 | 0.166311094435 | 0.232432432432 |

### `FlatFinalPlusSourcePrior`

| Seed | Dev NLL | MRR | Hit@5 |
| ---: | ---: | ---: | ---: |
| 260911 | 5.30760930919 | 0.229595551548 | 0.383783783784 |
| 260912 | 5.14500251396 | 0.232162957799 | 0.372972972973 |
| 260913 | 5.34969594477 | 0.236652634554 | 0.367567567568 |
| mean | 5.26743592264 | 0.232803714634 | 0.374774774775 |

### `TraceContextOnly`

| Seed | Dev NLL | MRR | Hit@5 |
| ---: | ---: | ---: | ---: |
| 260911 | 4.04598474503 | 0.255058782119 | 0.4 |
| 260912 | 4.04598474503 | 0.255058782119 | 0.4 |
| 260913 | 4.04598474503 | 0.255058782119 | 0.4 |
| mean | 4.04598474503 | 0.255058782119 | 0.4 |

### `PermutedPairContext`

| Seed | Dev NLL | MRR | Hit@5 |
| ---: | ---: | ---: | ---: |
| 260911 | 5.38530254364 | 0.181187485204 | 0.27027027027 |
| 260912 | 5.61731958389 | 0.185206168738 | 0.297297297297 |
| 260913 | 5.57842302322 | 0.197065847588 | 0.291891891892 |
| mean | 5.52701505025 | 0.187819833843 | 0.286486486486 |

### `PairContext`

| Seed | Dev NLL | MRR | Hit@5 |
| ---: | ---: | ---: | ---: |
| 260911 | 5.61303329468 | 0.242230463658 | 0.313513513514 |
| 260912 | 5.30500078201 | 0.24170849312 | 0.313513513514 |
| 260913 | 5.28878688812 | 0.238415606035 | 0.362162162162 |
| mean | 5.40227365494 | 0.240784854271 | 0.32972972973 |

## Frozen gate comparisons

| Control | Relative NLL gain | Bootstrap 95% CI | Pair lower each seed | Status |
| --- | ---: | --- | :---: | :---: |
| `DestinationMarginal` | -0.406497028282 | [-0.534555278856, -0.290190244981] | FAIL | FAIL |
| `SourceTransitionPrior` | -0.194091863073 | [-0.293378693149, -0.102950670792] | FAIL | FAIL |
| `FlatFinalPlusSourcePrior` | -0.0255983621403 | [-0.110141712987, 0.0502783737719] | FAIL | FAIL |
| `TraceContextOnly` | -0.335218493243 | [-0.440288918977, -0.237130181762] | FAIL | FAIL |
| `PermutedPairContext` | 0.0225693404964 | [-0.0481722803414, 0.0905026894091] | FAIL | FAIL |

## Verdict

`ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE`

No clinical correctness, treatment effect, validated RAR, therapeutic substitution, or superiority is inferred.

## Quarantine

G3/G4, R0 Holdout, and the historical project test split were not accessed or loaded.

## Next-stage boundary

The candidate is terminated under the frozen definition; no rescue is authorized.
