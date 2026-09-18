# CCTM trajectory supportability audit falsification — 2026-09-18

Date: 2026-09-18
Status: **DECISION ENFORCED: KILL_CCTM_SUPPORTABILITY**

## Evidence

A bounded, Train-only supportability audit evaluated Clinical Concept Trajectory Memory (CCTM) data density on `mimic-iii-canonical-131-paper-dev-v1` at source revision `fbdcdafdf93aa4d14fa0cea2d19039ff7b02c488` against canonical snapshot `molerec-table1-c721-www23` on the 319 Execution Plane.

The audit analyzed all 4,233 frozen Train patients (10,489 visits, 6,256 history-bearing prediction events, zero Dev/Test access). For each prediction visit $t \ge 1$, prior visits $0 \dots t-1$ were grouped by patient-specific typed concept identity (`("diag", id)`, `("proc", id)`, `("med", id)`). A recurrent trajectory was defined as occurrence in $\ge 2$ distinct prior visits.

### Primary Support Metrics

| Metric | Definition | Observed Value | Threshold | Result |
| :--- | :--- | ---: | ---: | :--- |
| **A. All-history recurrent occurrence coverage** | Recurrent D/P/M tokens / all history tokens | 0.476337 (228,786 / 480,303) | $\ge 0.30$ | **PASS** |
| **B. Non-med recurrent occurrence coverage** | Recurrent D/P tokens / all non-med history tokens | 0.373536 (87,273 / 233,640) | $\ge 0.20$ | **PASS** |
| **C. Event-level recurrent non-med support** | Fraction of history events with $\ge 3$ recurrent D/P | 0.365249 (2,285 / 6,256) | $\ge 0.50$ | **FAIL** |
| **D. Event-level recurrent all-concept support** | Fraction of history events with $\ge 5$ recurrent D/P/M | 0.405850 (2,539 / 6,256) | $\ge 0.50$ | **FAIL** |

### Supporting Diagnostics

- **Population sparsity**: Over 59% of history-bearing prediction events contain zero recurrent trajectories of any type (`events_ge1_recurrent_all_fraction = 0.407449`).
- **Trajectory count quantiles**:
  - Recurrent D/P/M trajectories per event: p25 = 0.0, p50 = 0.0, p75 = 20.0, p90 = 38.0, max = 130.0.
  - Recurrent non-med (D/P) trajectories per event: p25 = 0.0, p50 = 0.0, p75 = 6.0, p90 = 16.0, max = 75.0.
  - Across the Train population, the median prediction event with prior history has **zero** recurrent concept trajectories.
- **Current visit overlap with prior history**:
  - Current diagnosis seen in prior history: 38.43%
  - Current procedure seen in prior history: 27.51%
  - Current non-med combined: 35.56%
- **Per-modality recurrence**:
  - Diagnosis: 40.16% recurrent occurrence coverage (18.49% recurrent unique concept fraction, median recurrent trajectory length 2.0)
  - Procedure: 28.11% recurrent occurrence coverage (12.51% recurrent unique concept fraction, median recurrent trajectory length 2.0)
  - Medication: 57.37% recurrent occurrence coverage (29.62% recurrent unique concept fraction, median recurrent trajectory length 2.0)

## Interpretation and Decision

1. **Falsification of the concept-trajectory density premise**: The scientific premise of CCTM was that patient-specific concept trajectories constitute a dense, pervasive patient-history substrate that could explain longitudinal clinical state better than flat cross-visit representations. While aggregated token counts show high recurrence among a small subset of heavily readmitted patients, event-level coverage fails the practical viability floors: only 36.5% of history-bearing visits have $\ge 3$ recurrent non-med trajectories (threshold 50%), and 59.3% of history-bearing visits have no recurrent trajectory at all.
2. **Structural consequence**: For the vast majority of prediction events, an addressable concept-trajectory memory would be empty or degenerate, forcing the model to rely entirely on standard cross-sectional reads. Spending a multi-GPU Train/Dev architecture search on a representation that does not exist for the majority of the population is unjustified.
3. **No post-hoc rescue authorized**: Per the frozen protocol, a failed supportability audit immediately terminates the premise. No ontology merging, CCS code collapsing, ICD hierarchy truncation, external knowledge injection, or medication-only trajectory variants are authorized.
4. **Verdict**: `KILL_CCTM_SUPPORTABILITY`. The CCTM route is permanently closed before model implementation.

Artifact: `research/diagnostics/cctm-trajectory-support/result.json`.
