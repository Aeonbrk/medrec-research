<!-- markdownlint-disable MD013 -->

# Gate 01 Physiology Source Specification

This Idea-007-local, public-safe declaration is the single source of truth for
the six physiology channels used by Gate 01. It identifies source metadata only;
it contains no patient rows, split membership, outcomes, or trajectories.

- **Spec id**: `idea007-gate01-physiology-mimiciv-v1`
- **Source dataset**: MIMIC-IV, the already declared Gate-01 dataset snapshot
- **Source table**: `icu.chartevents` joined to `icu.d_items` for item metadata
- **Allowed source rows**: only the item IDs listed below; no substitute item,
  inferred channel, or seventh channel is admitted.

## Canonical channels and source identifiers

| Canonical channel | Admitted `itemid` values (precedence order) | Canonical unit | Deterministic conversion |
| --- | --- | --- | --- |
| `heart_rate` | `220045` (Heart Rate) | `bpm` | none |
| `systolic_blood_pressure` | `220050` (Arterial BP systolic), `220179` (NBP systolic) | `mmHg` | none |
| `diastolic_blood_pressure` | `220051` (Arterial BP diastolic), `220180` (NBP diastolic) | `mmHg` | none |
| `respiratory_rate` | `220210` (Respiratory Rate) | `breaths/min` | none |
| `oxygen_saturation` | `220277` (O2 saturation by pulse oximetry) | `%` | none |
| `temperature` | `223762` (Temperature Celsius), `223761` (Temperature Fahrenheit) | `degC` | Fahrenheit: `(x - 32) * 5 / 9`; Celsius: unchanged |

The item descriptions above are metadata labels from `icu.d_items`; the item ID
is the identity key. A row is valid only when its numeric value is finite and its
unit is the declared canonical unit (case/whitespace-normalized) or the source
item's declared temperature unit (`degF`/`F` for `223761`, `degC`/`C` for
`223762`). Unit-incompatible, missing, non-numeric, non-finite, and otherwise
unparseable rows are discarded. Values are never clipped, imputed, or
physiologically winsorized.

When two admitted source IDs for one channel produce the same patient, admission,
and chart-time key, the earlier ID in the precedence list wins. Remaining valid
rows are retained for the fixed-grid median; source ID is never used as a feature.
This precedence rule is the only duplicate-source rule.

## Public-safe identity and ordering

The general repository `DatasetManifest` remains the authority for dataset
snapshot and split identity. This file is the Idea-007-local extension for source
schema and must be recorded beside the Gate-01 protocol. Canonical channel order
is exactly:

```text
heart_rate,
systolic_blood_pressure,
diastolic_blood_pressure,
respiratory_rate,
oxygen_saturation,
temperature
```
