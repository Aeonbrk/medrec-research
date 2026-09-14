# RxUnitSet — Structured Prescription-Unit Supportability

This is a bounded pre-Idea supportability check for the proposed unordered
`(drug, dose, route)` prescription-unit target. It is not Idea 009, not a
formal CCFA Gate, and makes no novelty or paper-readiness claim. No model is
trained.

## Boundary

- The only raw clinical source is the authorized MIMIC-III 1.4
  `PRESCRIPTIONS.csv(.gz)` table.
- Canonical admission identities come from the existing SafeDrug c721 data
  product. The established first-two-thirds Train split and
  `idea008-gate01-v1` Gate01-Dev hash half are reused; no second split is
  introduced.
- Medication alignment reuses the c721 NDC → RxNorm → ATC4 mapping and the
  ordered 131-medication vocabulary. The vocabulary is not broadened.
- Route normalization is limited to trim, uppercase, and whitespace
  canonicalization. Clinically distinct abbreviations and routes are not
  merged.
- A numeric dose is retained as its value plus the observed unit. Ranges,
  textual values, missing units, and other unparsable values are not converted
  using clinical assumptions. `PROD_STRENGTH` is inspected but is not used as
  an unsafe dose conversion.
- Admission-level diagnoses and procedures have no event timestamps. They can
  identify an admission, but they cannot provide a proven strictly preceding
  context for a within-admission prescription episode.
- Heldout, Audit, G3, G4, historical-test, future-visit, and model-training
  resources are not used.

## Analysis

Run on 319 after the remote preflight, from a clean commit of this prototype:

```bash
python research/prototypes/rxunit-support/analyze_rxunit_support.py \
  --mimic-root /root/zhb/Search/dataset/mimic-iii-1.4 \
  --canonical-data /root/zhb/SafeDrug-c7218d0/data/data_final.pkl \
  --vocabulary /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23/voc_final.pkl \
  --mapping-dir /root/zhb/SafeDrug-c7218d0/data \
  --source-revision <clean-commit> \
  --output /root/zhb/medrec-data/prototypes/rxunit-support/result.json
```

The output is aggregate-only. It reports NDC/ATC alignment, route and dose
coverage, per-medication entropy/concentration, admission-medication
ambiguity, duplicate versus temporally separated records, episode counts,
Train/Dev target support, and the predeclared decision rule. Patient,
admission, and row identifiers are retained only in process memory.

## Decision contract

The preferred target is the prescription episode, but it is supportable only
when distinct episodes can be causally aligned to preceding clinical evidence.
The admission target is supportable only when at least 90% of canonical
admission-medication pairs are one stable complete dose-route unit, at least
90% of mapped canonical rows have an observed route, and at least 80% have a
single numeric dose with a unit. Otherwise the direction is terminated. There
is no rescue, target collapse, model training, or hyperparameter search.

## Result

The aggregate result is recorded in `result.json` after the one authorized
Train/Gate01-Dev run. This surface does not create Idea 009 or a formal Gate.
