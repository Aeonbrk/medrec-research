<!-- markdownlint-disable MD013 -->

# MIMIC-IV medication-recommendation benchmark readiness

## Stage boundary

`STAGE -1D — MICA CORE CONSOLIDATION + TRAINING DIAGNOSIS + MIMIC-IV READINESS`

This is a protocol-freezing and resource-readiness record. It is **PRE-IDEA**,
**PRE-GATE**, **NO PAPER CLAIM**, **NO HOLDOUT TEST**, and **NO NEW METHOD
FAMILY**. No MICA-IV model was trained in this stage.

The target is a dataset-native MIMIC-IV implementation of the existing MICA
task: current-visit diagnosis/procedure evidence and strictly earlier visit
history predict the current medication set. The existing MIMIC-IV order-time /
exposure resources are useful mechanical evidence, but they are not silently
relabelled as this visit-level benchmark.

## Decision

`MIMIC_IV_PROTOCOL_READY_FOR_IMPLEMENTATION`

Readiness means that the source tables, chronology, identity linkage, and an
auditable medication-normalization path are available, and that the task
boundary can be frozen without looking at a target or future event. It does not
mean that an implementation, training run, cross-dataset comparison, or
held-out evaluation has been completed.

## Resource inventory

| Requirement | Status | Evidence and boundary |
| --- | --- | --- |
| Admissions / visits | AVAILABLE | MIMIC-IV v3.1 `hosp/admissions` supplies `subject_id`, `hadm_id`, and admission chronology. |
| Diagnoses | AVAILABLE | `hosp/diagnoses_icd` is linkable by `hadm_id`; ICD-9 and ICD-10 version tokens must remain distinct. |
| Procedures | AVAILABLE | `hosp/procedures_icd` is linkable by `hadm_id`; version tokens remain distinct. |
| Prescription medication orders | AVAILABLE | `hosp/prescriptions` supplies medication order rows, NDC/formulary identifiers, and course times. |
| Patient identity / chronology | AVAILABLE | `subject_id` groups patients and `hadm_id` orders visits; deterministic admission-time ordering is possible. |
| Drug normalization | REUSABLE | Existing 319-side rebuild has a deterministic NDC → RxNorm → ATC path plus formulary fallback. Exact mapping file/version and coverage must be frozen in the implementation manifest. |
| ATC representation | REUSABLE | ATC4 is the current MICA-compatible representation. Vocabulary is dataset-native; equal vocabulary size across MIMIC-III and MIMIC-IV is not required. |
| DDI mapping | REUSABLE | The frozen SafeDrug/MoleRec DDI asset can be projected onto the normalized MIMIC-IV vocabulary. Projection coverage and unmapped pairs must be reported before training. |
| Patient-level split | REUSABLE | Patient grouping and deterministic split machinery exist. The protocol below uses a 2/3–1/6–1/6 role split to match the current MIMIC-III benchmark semantics; the existing 80/10/10 candidate is not yet frozen. |
| Visit-level target boundary | NEEDS_IMPLEMENTATION | A repository-owned adapter must materialize current-visit D/P, strict prior history, and current medication targets from MIMIC-IV. Existing order-time/exposure artifacts are not this adapter. |
| Credentialed raw-data execution | AVAILABLE | Raw MIMIC-IV v3.1 is available on the approved 319 execution plane; it is not copied into Git or the local Mac harness. |
| Held-out test access in this stage | MISSING | The untouched test partition is deliberately not read or evaluated in Stage -1. |
| MICA-IV training result | MISSING | Training is explicitly not run in this stage. |

## Why the protocol is feasible

The 319-side MIMIC-IV 3.1 rebuild already demonstrates the required mechanical
surface: linked admissions, diagnosis/procedure tables, prescription rows,
patient chronology, an ATC4-compatible medication axis, and a DDI matrix. Its
candidate artifact contains 77,615 patients and 209,358 visits after its own
filtering, with 131 normalized medication concepts. Those counts are resource
evidence only; they do not freeze the MICA-IV cohort or assert that MIMIC-IV
must have 131 medications.

The earlier resource reset independently verified the raw v3.1 hospital tables
and a combined NDC/formulary normalization path (reported coverage 81.92% for
eligible orders and 81.89% for eligible eMAR rows). That record concerns a
strict pre-order exposure task, so it is reused here only as availability and
mapping evidence; its order-time target, exposure state, and quarantine split
are not imported into the MICA benchmark ([resource-reset decision](../../memory/resource-reset-20260905-exposure-localized-safety/r0-decision.md)).

The current MIMIC-III MICA contract is therefore implementable on MIMIC-IV
without importing future information: for visit `t`, use `D_t`, `P_t`, and
`(D_j, P_j, M_j)` only for `j < t`, and use `M_t` only as the loss/evaluation
target. The implementation must publish mapping coverage and row counts before
any model run.

## Non-claims and next implementation seam

This record does not claim that the two datasets have identical coding,
practice patterns, patient counts, medication vocabularies, or DDI support. It
also does not claim clinical appropriateness or safety from prescription
co-membership. The next and only authorized action is to implement and freeze
the protocol in [`protocol-draft.md`](protocol-draft.md), then run mechanical
data-contract checks before considering any MICA-IV Train/Dev execution.

The source-level comparison of recent dual-dataset papers is in
[`source-comparison.md`](source-comparison.md); machine-readable status is in
[`readiness.json`](readiness.json).
