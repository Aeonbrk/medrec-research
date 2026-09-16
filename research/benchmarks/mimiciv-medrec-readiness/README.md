<!-- markdownlint-disable MD013 -->

# MIMIC-IV medication-recommendation benchmark readiness

## Stage boundary

`STAGE -1E — MIMIC-IV VISIT-LEVEL MEDREC BENCHMARK MATERIALIZATION`

This is a protocol-freezing and Train/Dev materialization record. It is **PRE-IDEA**,
**PRE-GATE**, **NO PAPER CLAIM**, **NO HOLDOUT TEST**, and **NO NEW METHOD
FAMILY**. No MICA-IV model was trained in this stage.

The target is a dataset-native MIMIC-IV implementation of the existing MICA
task: current-visit diagnosis/procedure evidence and strictly earlier visit
history predict the current medication set. The existing MIMIC-IV order-time /
exposure resources are useful mechanical evidence, but they are not silently
relabelled as this visit-level benchmark.

## Decision

`MIMIC_IV_BENCHMARK_FROZEN_READY_FOR_TRAINDEV`

The Stage -1E adapter materialized restricted Train/Dev examples on the
approved 319 execution plane and emitted only aggregate/public-safe metadata in
[`../mimiciv-medrec/`](../mimiciv-medrec/). The frozen identity is bound to
adapter revision `e87411be3df305f55a4a68d10a9db3eb505e1232` and manifest digest
`110090bb79411ecf9f8057e75e16a1f6cb0c0e4b4e159bc29d4434018628da23`.

This does not authorize MICA-IV training, threshold tuning, or Test access.

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
| Visit-level target boundary | AVAILABLE | The Stage -1E repository adapter materializes current D/P, strict prior history, and current prescription-derived medication targets. Existing order-time/exposure artifacts remain separate. |
| Credentialed raw-data execution | AVAILABLE | Raw MIMIC-IV v3.1 is available on the approved 319 execution plane; it is not copied into Git or the local Mac harness. |
| Held-out test access in this stage | MISSING | Test membership is sealed by count/digest only; no Test medication targets were loaded or evaluated in Stage -1E. |
| MICA-IV training result | MISSING | Training is explicitly not run in this stage. |

The checked execution-plane mapping inputs are the KGDNet
`ndc2rxnorm_mapping.txt`, `ndc2atc_level4.csv`, and `drug_codes_mapping.csv`
assets. The DDI authority is the frozen SafeDrug/MoleRec
`molerec-table1-c721-www23` snapshot. File hashes and precedence are frozen in
the Stage -1E manifest; coverage is reported rather than used to invent a new
threshold.

## Why the protocol is feasible

The Stage -1E materialization demonstrates the required mechanical surface on
the actual v3.1 files: 149,001 Train patients / 364,492 Train visits and
37,076 Dev patients / 90,033 Dev visits, with 308,824 / 76,529 recommendation
examples after excluding visits with no mapped target. The Train-only
medication vocabulary has 173 normalized concepts. These are frozen benchmark
aggregates, not a claim that MIMIC-III and MIMIC-IV have identical cohorts or
vocabularies.

The earlier resource reset independently verified the raw v3.1 hospital tables
and a combined NDC/formulary normalization path (reported coverage 81.92% for
eligible orders and 81.89% for eligible eMAR rows). That record concerns a
strict pre-order exposure task, so it is reused here only as availability and
mapping evidence; its order-time target, exposure state, and quarantine split
are not imported into the MICA benchmark ([resource-reset decision](../../memory/resource-reset-20260905-exposure-localized-safety/r0-decision.md)).

The current MIMIC-III MICA contract is therefore materialized on MIMIC-IV
without importing future information: for visit `t`, use `D_t`, `P_t`, and
`(D_j, P_j, M_j)` only for `j < t`, and use `M_t` only as the loss/evaluation
target. The adapter reports 0.785936 Train and 0.785400 Dev prescription-row
normalization coverage, 0.0 Dev target OOV, 0.984733 source-concept projection
coverage, 0.989011 DDI-supported-concept coverage (90 of 91), and 443 of 448
canonical pairs retained.

## Non-claims and next implementation seam

This record does not claim that the two datasets have identical coding,
practice patterns, patient counts, medication vocabularies, or DDI support. It
also does not claim clinical appropriateness or safety from prescription
co-membership. The adapter contract and mechanical checks are now frozen. The
next and only authorized action is a separate review of the Train/Dev screen
contract in [`../mimiciv-medrec/README.md`](../mimiciv-medrec/README.md); do not
start it automatically in Stage -1E.

The source-level comparison of recent dual-dataset papers is in
[`source-comparison.md`](source-comparison.md); machine-readable status is in
[`readiness.json`](readiness.json).
