# Strict Drug-Changing Supportability Decision

## Scientific question

Under the already frozen strict drug-changing order-revision semantics, is the admitted supervision sufficiently large, patient-distributed, recurrent on the source side, medication-diverse, and non-concentrated to justify one subsequent bounded test of incremental learning value?

## Semantic-object integrity

`PASS_SEMANTIC_ADMISSION` was re-materialized at the frozen revision: 1040 strict events observed (expected 1,040), with zero frozen-invariant violations. Candidate New sets were complete before identity-difference filtering; no nearest/first matching or tie-breaking was used.

## Frozen criteria

| Criterion | Value | Status |
| --- | ---: | :---: |
| `C1_total_support` | `1040` | PASS |
| `C2_patient_breadth` | `1011` | PASS |
| `C3_patient_concentration` | `981.4882032667877` | PASS |
| `C4_admission_contexts` | `1031` | PASS |
| `C5_source_breadth` | `72` | PASS |
| `C6_source_recurrence` | `28` | PASS |
| `C7_source_concentration` | `22.441696406340775` | PASS |
| `C8_destination_breadth` | `74` | PASS |
| `C9_destination_concentration` | `27.5960606215237` | PASS |
| `C10_temporal_event_width` | `0.2692307692307692` | PASS |
| `C11_temporal_patient_width` | `0.27101879327398615` | PASS |

## Verdict

`PASS_STRICT_DRUG_CHANGING_SUPPORTABILITY`

No predictive value, treatment effect, replacement/correction meaning, clinical correctness, or causal superiority is inferred.

## Quarantine

G3/G4, R0 Holdout, and the historical project test were not accessed; no model, prediction, outcome, or pair-specific statistic was computed.

## Next-stage boundary

If this pass stands, the only authorized next scientific stage is `Pair/Context Incremental Value`; it requires a fresh frozen design and is not executed in this round.
