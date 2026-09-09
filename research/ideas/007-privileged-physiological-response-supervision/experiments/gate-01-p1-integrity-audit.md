# Gate 01 P1 Mechanical-Preflight Integrity Audit — Idea 007

## Audit status

- **Auditor**: `ccf-integrity-auditor`
- **Audit mode**: `claim-audit / numeric-audit`
- **Protocol audited**: `gate-01-protocol.md` revision `v1.2`
- **Physiology source spec**: `idea007-gate01-physiology-mimiciv-v1`
- **Execution source revision**: `2c7fb811a268275c4de2a637c89bc578db3f8992`
- **Runner**: `gate01_mechanical_preflight.py`
- **Evidence**: `gate-01-mechanical-preflight.json`
- **Recommendation outcomes accessed**: `NO`
- **Training / model metrics accessed**: `NO`
- **G3/G4, R0 Holdout, historical project test accessed**: `NO`
- **Quarantine**: `INTACT`
- **Verdict**: `INTEGRITY_AUDIT_PASS`

This audit covers only the public-safe P1 support record and the arithmetic that
decides the frozen support gate. It does not review the Idea, reopen the protocol,
inspect a patient row, or evaluate a model.

## Claim-evidence matrix

| Claim | Evidence | Verdict |
| --- | --- | --- |
| The runner used the frozen protocol and source specification. | The report records protocol `v1.2`, source spec `idea007-gate01-physiology-mimiciv-v1`, salt `idea007-gate01-v1`, the six canonical channels, the `(a(e), a(e)+24h]` window, 24 right-closed bins, median aggregation, and no filling/interpolation. | **PASS** |
| Patient assignment preceded response-linked aggregation. | The report access order lists partition assignment before E_rec construction, administration anchors, tensorization, and aggregate support. | **PASS** |
| Global and partition counts are arithmetically consistent. | `E_rec`: `3,907,607 + 826,301 + 819,547 = 5,553,455`; `N_A`: `114,350 + 25,091 + 24,169 = 163,610`. | **PASS** |
| Coverage ratios are computed from the reported counts. | Global `163,610 / 5,553,455 = 0.0294609392`; Train `0.0292634341`; Dev `0.0303654479`; Audit `0.0294906820`. | **PASS** |
| Concentration booleans follow the frozen thresholds. | Medication shares pass all scopes. Patient maximum/top-20 shares fail in Dev and Audit and pass in Train exactly as reported against `0.01` / `0.10`. | **PASS** |
| The STOP verdict follows the frozen decision rule. | Global and every partition fail the coverage floor; every scope also fails the minimum supported-events-per-counted-medication floor. Dev and Audit additionally fail patient concentration. | **PASS** |
| No private material entered the committed report. | JSON validation and a forbidden-field scan found no patient/admission/event identifiers, raw times, trajectories, predictions, checkpoints, or weights. | **PASS** |
| No downstream scientific execution occurred. | Report flags `training: NOT_RUN`, `recommendation_outcomes_accessed: false`, quarantines intact, and the remote run exited immediately after writing aggregate evidence. | **PASS** |

## Public-safe numeric record

| Scope | `E_rec` | `N_A` | Coverage | Supported patients | Supported meds | Min events/med | Concentration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Global | 5,553,455 | 163,610 | 0.029461 | 12,372 | 116 | 1 | medication pass; patient pass |
| Gate01-Train | 3,907,607 | 114,350 | 0.029263 | 8,686 | 114 | 1 | pass |
| Gate01-Dev | 826,301 | 25,091 | 0.030365 | 1,796 | 103 | 1 | patient max/top-20 fail |
| Gate01-Audit | 819,547 | 24,169 | 0.029491 | 1,890 | 103 | 1 | patient max/top-20 fail |

Global medication concentration was maximum share `0.132211` and top-five share
`0.410825`; global patient concentration was maximum share `0.002060` and top-20
share `0.027614`. These are descriptive aggregates only.

## Integrity conclusion

`STOP_INSUFFICIENT_OR_MATERIALLY_CONCENTRATED_RESPONSE_SUPPORT` is mechanically
supported. The response-specific mechanism terminates at Gate 01 P1. No rescue
window, item-ID change, medication deletion, subgroup mining, response-definition
change, or threshold adjustment is authorized. Full V1–V8 implementation,
training, Dev/Audit model evaluation, G3/G4, R0 Holdout, and historical-test access
remain unperformed or quarantined.

## Audit output contract

- **Mode**: `claim-audit / numeric-audit`
- **Artifacts checked**: P0 freeze record, P1 aggregate report, runner revision, and this audit
- **Numeric consistency findings**: all checks passed
- **Citation metadata/context findings**: not applicable; no citation audit requested
- **Severity**: blocking P1 support failure, not an implementation or arithmetic-integrity failure
- **Safe edit suggestions**: none; follow the frozen no-rescue boundary
- **Next CCFA owner**: `ccf-pipeline-orchestrator`
- **No-invention status**: `PASS`; no unsupported claim or result was added
