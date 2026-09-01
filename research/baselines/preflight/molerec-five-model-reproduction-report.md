# MoleRec Five-Model Reproduction Report

## Verdict

Attempt `formal-20260828-a09fcab-u8-b`, completed through continuation `continuation-20260830-pathfix-1`, is `completed_mismatch`.

The execution is legal and complete. The mismatch means that some paper point intervals and one directional relationship were not reproduced; it is not permission to retrain, tune, select a different checkpoint, change a threshold, or replay a test.

| Axis | Result | Evidence |
| --- | --- | --- |
| `execution_integrity` | passed | All five continuation test pairs reopen with the frozen source, environment, checkpoint, schedule, and ten-round semantics. |
| `paper_point_fidelity` | failed | 16 of 25 paper point checks passed. |
| `directional_relationships` | failed | 3 of 4 declared directional checks passed. |
| `artifact_completeness` | passed | Five finalized test pairs and the terminal audit packet exist. |

## Frozen scientific identity

- RETAIN, LEAP, GAMENet, and SafeDrug use SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`.
- MoleRec uses `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`.
- The shared preprocessing revision is `c7218d0976e5ee5588aeaf5bdbc86b338126bba5`.
- All seven 50-epoch training lanes reuse their validated immutable recovery siblings. No lane was retrained and no recovery identity changed.
- Validation-only selection chose `molerec-safedrug-lr-5e-4`; the `1e-5` and `1e-4` lanes remain `not_tested_by_design`.

## Upstream ten-round results

| Model | DDI | Jaccard | F1 | PRAUC | Avg medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| RETAIN | 0.0885 ± 0.0014 | 0.4872 ± 0.0026 | 0.6475 ± 0.0025 | 0.7598 ± 0.0045 | 19.1019 ± 0.2296 |
| LEAP | 0.0720 ± 0.0005 | 0.4581 ± 0.0024 | 0.6191 ± 0.0023 | 0.6541 ± 0.0039 | 18.6645 ± 0.0893 |
| GAMENet | 0.0856 ± 0.0004 | 0.4985 ± 0.0020 | 0.6553 ± 0.0020 | 0.7655 ± 0.0022 | 27.8810 ± 0.1553 |
| SafeDrug | 0.0601 ± 0.0005 | 0.5149 ± 0.0025 | 0.6715 ± 0.0022 | 0.7659 ± 0.0023 | 19.9595 ± 0.1518 |
| MoleRec | 0.0724 ± 0.0008 | 0.5292 ± 0.0031 | 0.6834 ± 0.0028 | 0.7728 ± 0.0024 | 21.5314 ± 0.1653 |

These are Reproduction Mode aggregates only. They do not create Comparison Mode readiness and were not used to choose the later Comparison configuration.

## Evidence boundary

The original failed RETAIN queue and evidence remain immutable. The authorized continuation used new test submission identities and independent test roots while reusing only the admitted seven training/recovery pairs. No historical four-model test metric, training artifact, log inference, seed sweep, test-driven selection, or mismatch-driven retry entered the audit.
