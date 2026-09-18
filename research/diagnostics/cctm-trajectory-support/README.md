# CCTM trajectory-support audit

Status: **AUDIT EXECUTED / DECISION ENFORCED: KILL_CCTM_SUPPORTABILITY**

This diagnostic asks one structural question before any new architecture is built:

> Does the canonical MIMIC-III Train split contain enough repeated typed clinical concepts for patient-specific concept trajectories to be a common modeling object rather than a sparse special case?

It does not evaluate recommendation accuracy, inspect Dev/Test targets, train a model, or create Idea 009.

## Candidate architecture boundary

The candidate is **not** novel merely because it uses longitudinal trajectories.

Relevant occupied primitives include:

- TRANS (IJCAI 2024): patient-specific temporal heterogeneous graph with unique medical-code nodes, visit nodes, code-to-visit edges with temporal features, and visit-to-visit temporal edges.
- ARCI (CIKM 2024): medication-code temporal paths across consecutive visits, with intent-linked multi-head cross-visit attention.
- DCGM (Expert Systems with Applications 2026): dynamic clinical trajectory aggregation through retrieval of historically similar disease/medication visits.
- Med-BERT and general longitudinal EHR Transformers: code/visit contextualization in which same-code cross-visit attention can emerge.

Therefore the only viable model-level distinction is a complete information flow such as:

```text
historical typed occurrences
    -> identity-indexed patient-specific concept trajectories
    -> one trajectory state per recurrent (type, code)
current diagnosis/procedure evidence
    + trajectory states
    -> medication-specific late evidence read
    -> medication scores
```

The novelty object, if eventually supported, is the **trajectory-indexed evidence memory + medication-specific late binding computation graph**, not any individual GRU/attention/time-encoding primitive.

## Train-only definition

For a prediction event at visit `t`, history is visits `0..t-1`.

A typed concept identity is one of:

- `("diag", diagnosis_id)`
- `("proc", procedure_id)`
- `("med", medication_id)`

A **recurrent trajectory** exists when the same typed concept appears in at least two distinct historical visits.

Current-visit medications are never used in the audit for that event. Previous-visit medications are legal history.

## Primary support statistics

Across all Train prediction events with non-empty history, compute:

1. **All-history recurrent occurrence coverage**  
   fraction of historical D/P/M occurrence tokens belonging to concepts with history length >= 2.

2. **Non-medical recurrent occurrence coverage**  
   same quantity for diagnoses + procedures only. This prevents a positive audit from being explained only by historical-medication copying.

3. **Event-level recurrent non-medical coverage**  
   fraction of history-bearing prediction events that contain at least 3 recurrent diagnosis/procedure trajectories.

4. **Event-level recurrent all-concept coverage**  
   fraction of history-bearing prediction events that contain at least 5 recurrent D/P/M trajectories.

Supporting outputs include per-modality recurrent-concept fractions, trajectory-length distributions, recurrent trajectory counts per event, and current D/P overlap with earlier history.

## Frozen routing rule

Return `SUPPORT_CCTM_PREMISE` only if all conditions hold:

```text
all-history recurrent occurrence coverage        >= 0.30
non-med recurrent occurrence coverage            >= 0.20
events with >=3 recurrent non-med trajectories   >= 0.50
events with >=5 recurrent all trajectories       >= 0.50
```

These are practical density floors for deciding whether to spend a full Train/Dev architecture run. They are not claims about clinical prevalence or universal usefulness.

If any condition fails, return `KILL_CCTM_SUPPORTABILITY` and do not rescue the premise with ontology merging, CCS collapsing, larger temporal windows, external knowledge, or medication-only trajectories.

If the audit passes, it authorizes architecture design only. It does not establish predictive value or novelty.

## Execution

Run on the 319 Execution Plane against the canonical snapshot:

```bash
python research/diagnostics/cctm-trajectory-support/audit_cctm_support.py \
  --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --output /root/zhb/medrec-data/diagnostics/cctm-trajectory-support.json
```

Only the aggregate JSON should return to Git.

## Terminal Audit Results (2026-09-18)

Executed on the 319 Execution Plane against canonical snapshot `molerec-table1-c721-www23` at source revision `fbdcdafdf93aa4d14fa0cea2d19039ff7b02c488` (4,233 Train patients, 10,489 Train visits, 6,256 history-bearing prediction events, zero Dev/Test access).

### Primary Support Metrics

| Metric | Definition | Observed Value | Threshold | Result |
| :--- | :--- | ---: | ---: | :--- |
| **A. All-history recurrent occurrence coverage** | Recurrent D/P/M tokens / all history tokens | 0.476337 (228,786 / 480,303) | $\ge 0.30$ | **PASS** |
| **B. Non-med recurrent occurrence coverage** | Recurrent D/P tokens / all non-med history tokens | 0.373536 (87,273 / 233,640) | $\ge 0.20$ | **PASS** |
| **C. Event-level recurrent non-med support** | Fraction of history events with $\ge 3$ recurrent D/P | 0.365249 (2,285 / 6,256) | $\ge 0.50$ | **FAIL** |
| **D. Event-level recurrent all-concept support** | Fraction of history events with $\ge 5$ recurrent D/P/M | 0.405850 (2,539 / 6,256) | $\ge 0.50$ | **FAIL** |

### Supporting Diagnostics

- **Event-level recurrence presence**: Only 40.74% of history-bearing events contain even one recurrent trajectory of any type (`events_ge1_recurrent_all_fraction = 0.407449`).
- **Trajectory-count quantiles (recurrent D/P/M)**: p25 = 0.0, p50 = 0.0, p75 = 20.0, p90 = 38.0, max = 130.0. The median history-bearing event has zero recurrent trajectories.
- **Trajectory-count quantiles (recurrent non-med D/P)**: p25 = 0.0, p50 = 0.0, p75 = 6.0, p90 = 16.0, max = 75.0.
- **Current D/P prior-identity overlap**:
  - Diagnosis: 38.43%
  - Procedure: 27.51%
  - Non-med combined: 35.56%
- **Per-modality recurrence**:
  - Diagnosis: 40.16% recurrent occurrence coverage (18.49% recurrent unique concept fraction, median recurrent trajectory length 2.0)
  - Procedure: 28.11% recurrent occurrence coverage (12.51% recurrent unique concept fraction, median recurrent trajectory length 2.0)
  - Medication: 57.37% recurrent occurrence coverage (29.62% recurrent unique concept fraction, median recurrent trajectory length 2.0)

### Decision & Scientific Conclusion

- **Verdict**: `KILL_CCTM_SUPPORTABILITY`.
- **Reason**: The canonical Train data do not support sufficiently dense patient-specific concept trajectories under the frozen identity definition. While occurrence token counts show recurrence in heavy-utilizer visits, over 59% of prediction events with prior history have zero recurrent trajectories, and only 36.5% reach the $\ge 3$ non-med trajectory threshold (failing the 50% density floor). Concept trajectories are a sparse minority phenomenon in MIMIC-III rather than a pervasive modeling substrate.
- **Policy enforcement**: The CCTM route is terminated before model implementation. Per the frozen protocol, no ontology merging, CCS grouping, ICD hierarchy collapse, external knowledge, or threshold relaxation is permitted.
