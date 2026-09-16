<!-- markdownlint-disable MD013 -->

# MIMIC-IV visit-level medication-set protocol (draft to freeze)

This draft defines the MIMIC-IV surface that is intended to be semantically
aligned with the current MIMIC-III MICA task. It is a benchmark contract, not a
training result. No test partition is opened in Stage -1.

## 1. Prediction object and information entitlement

For patient `p` and an ordered hospital visit `t`, construct:

```text
(D_t, P_t, H_<t) -> M_t
H_<t = [(D_j, P_j, M_j) for strictly earlier visits j]
```

`D_t` is the current diagnosis set, `P_t` is the current procedure set, and
`M_t` is the current medication set. `M_t` is target-only: it must not be
present in the input, a vocabulary fit, a prevalence statistic, a DDI fit, or
any checkpoint decision. `H_<t` may contain medication sets from earlier
visits, but never current-visit medications or future visits.

This is an admission/visit-level recommendation task, not an order-time
recommendation task. Prescription start/stop status, eMAR administrations,
post-discharge fields, notes, labs, and future events are outside the MICA-IV
input contract unless a later protocol explicitly changes the task.

## 2. Cohort and visit construction

1. Start from MIMIC-IV v3.1 `hosp/admissions` and retain a deterministic
   `subject_id`/`hadm_id` visit key.
2. Join diagnoses and procedures by `hadm_id`. Keep ICD version in every code
   token (`ICD9:` versus `ICD10:`) so a numeric/code-string collision cannot
   occur. Deduplicate codes within a visit.
3. Join medication **prescription** rows by `hadm_id`; do not mix prescription
   orders with eMAR administrations for this benchmark.
4. Normalize each medication with one versioned deterministic map (the current
   candidate is NDC/formulary → RxNorm → ATC4). Deduplicate normalized drugs
   within a visit. Unmapped rows are excluded from `M_t`, counted, and reported
   by source and coverage; a visit with no mapped target medication is excluded
   from the recommendation rows rather than assigned an artificial empty target.
5. Sort each patient's visits by `admittime`, breaking exact ties by `hadm_id`.
   A visit contributes a row only after its current target set is materialized;
   history is the prefix of this sorted sequence. Retain first visits with an
   explicit empty history, matching the current MICA row construction; do not
   silently remove single-visit patients. The exact count after this rule is a
   pre-training artifact and must be published.
6. Do not use `prescriptions.starttime`, `stoptime`, order status, or any event
   after the visit to decide which current target drugs were prescribed. Those
   fields belong to a different order-time/exposure task.

The final implementation must report raw rows, mapped rows, unmapped rows,
visit counts, patient counts, and the fraction of visits removed by each rule.

## 3. Vocabulary and knowledge assets

- Fit diagnosis and procedure vocabularies on the Train patients only. Retain
  an explicit unknown token for Dev/Test codes; do not force MIMIC-III and
  MIMIC-IV code identities or vocabulary sizes to match.
- Fit the medication vocabulary from Train target sets after normalization.
  Dev/Test medications absent from Train are reported as out-of-vocabulary and
  are not silently remapped to a frequent drug.
- Keep the medication representation at ATC4 unless a future evidence record
  authorizes a different level. Record the mapping table version, hash, source,
  and per-stage coverage in a public-safe manifest.
- Project the frozen SafeDrug/MoleRec DDI matrix onto the dataset-native
  medication IDs using the same ATC4 identity. Report matrix shape,
  symmetry/zero-diagonal checks, represented concepts, and unmapped relations.
  Never interpret an unmapped pair as known non-interacting; if coverage is
  below the declared implementation floor, stop rather than publish a DDI
  comparison. DDI is a training/evaluation knowledge asset, not a clinical
  safety label.

## 4. Patient split and role semantics

Split by `subject_id` before fitting vocabularies, medication prevalence, DDI
projection, or any learned statistic. Use deterministic roles:

```text
Train = 2/3 of eligible patients
Dev   = 1/6
Test  = 1/6 (untouched in Stage -1)
```

The split seed and exact assignment algorithm must be written to the final
manifest. The existing 319 candidate used an 80/10/10 split with seed 42; that
mechanical artifact is reusable, but it is not the frozen MICA-IV role split
because the MICA-III comparison uses 2/3–1/6–1/6 roles. No patient IDs or split
membership are committed to Git.

## 5. Metrics and checkpoint philosophy

Use the MICA metric family and fixed decoder:

- Jaccard, example-averaged F1, PRAUC, DDI rate, and BCE/NLL;
- sigmoid threshold `0.35`, fixed before training and not tuned on Dev;
- strict best complete-Dev Jaccard checkpoint selection, earliest epoch on an
  exact tie;
- report the selected row and the final epoch row, including medication-count
  summaries where available.

The metric code must define empty-set behavior, average at the patient/visit
row level, and DDI pair counting in the same way as the current MICA runner.
Do not substitute literature thresholds, ranking losses, or test-derived
thresholds. A future cross-dataset comparison may use dataset-native D/P and
medication vocabularies while keeping this metric and checkpoint semantics.

## 6. Mechanical acceptance checks before any model run

The implementation is ready for a Train/Dev run only when all of the following
are recorded in a public-safe manifest:

1. source release and mapping versions are identified;
2. every retained row has one patient, one chronologically ordered visit, and
   finite binary target values;
3. no current target medication appears in the serialized input features;
4. every history visit is strictly earlier than its row's current visit;
5. patient split is disjoint and vocab/DDI fitting uses Train only;
6. normalization coverage and unknown/OOV counts are reported;
7. DDI matrix shape, symmetry, diagonal, and projection coverage pass;
8. Train/Dev row counts and target alignment are reproducible from the manifest.

Failure of any check means `STOP_MIMIC_IV_NOT_READY`; it is not repaired by
changing the target definition or opening the test partition.
