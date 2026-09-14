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

The aggregate result is recorded in [`result.json`](result.json) from one
authorized Train/Gate01-Dev run. The run-code revision was
`8ad4c599bb464c539e6641d75c776cdb79efce7f`; the repository state before this
prototype was `a85c12a4171d1536d0339001dbe13990f94ceb78`, and
`origin/main` remained `530f4d22111f385c8f735454cde36155363d7292`.

### Alignment

| Measure | All selected admissions | Train | Gate01-Dev |
| --- | ---: | ---: | ---: |
| Raw prescription rows | 1,238,801 | 1,016,153 | 222,648 |
| Rows with valid NDC | 1,068,492 | 880,681 | 187,811 |
| Rows mapped to any ATC4 | 811,208 | 663,035 | 148,173 |
| Canonical 131-vocabulary rows | 786,818 | 643,033 | 143,785 |
| Rows outside canonical vocabulary | 24,390 | 20,002 | 4,388 |
| Unmapped rows | 427,593 | 353,118 | 74,475 |
| Normalized route classes | 66 | 62 | 51 |
| Route observed | 99.999873% | 100% | 99.999305% |
| Numeric dose plus unit | 93.516417% | 93.576379% | 93.248253% |

NDC alignment follows the existing SafeDrug c721 NDC → RxNorm → ATC4 lineage
with no ambiguous mapping keys. Routes are only trimmed, uppercased, and
whitespace-normalized; clinically distinct values are retained. `PROD_STRENGTH`
is present on all canonical rows but is not used to infer doses. Dose kinds in
the selected rows are 735,804 single-numeric, 41,234 numeric-range, 9,775
otherwise-unparsable, and 5 textual values.

### Admission and episode semantics

| Diagnostic | Train | Gate01-Dev |
| --- | ---: | ---: |
| Canonical admission-medication pairs | 198,844 | 41,946 |
| One unique dose-route pair | 55.9207% | 54.4843% |
| Multiple doses, same route | 18.9923% | 17.5344% |
| Same dose, multiple routes | 3.3524% | 3.1421% |
| Multiple doses and routes | 21.7346% | 24.8391% |
| Pairs with temporally supported config change | 69,716 (79.5400% of multi-config) | 15,463 (80.9920% of multi-config) |
| Route-temporally-distinct fraction of multi-route pairs | 73.4524% | 75.0596% |
| Duplicate order-row fraction | 6.2536% | 6.5083% |
| Episode ordering ambiguity rate | 54.3878% | 55.4995% |

Stable complete admission units number 103,848 in Train and 21,615 in
Gate01-Dev (10,480 and 2,129 supported cases; mean sizes 9.91 and 10.15).
They represent 130 and 123 of the 131 medications. Complete temporal episodes
would yield 565,311 and 125,551 units (10,485 and 2,129 cases; mean sizes
53.92 and 58.97), representing 130 and 124 medications, respectively, but the
canonical diagnosis and procedure inputs are admission-level and have no event
timestamps. All 4,231 Train and 1,004 Gate01-Dev patients with at least two
prescription decision points therefore have zero episodes with proven strictly
preceding clinical context under the causal contract.

Admission-unit concentration is top-10/top-25/bottom-half share
31.9765%/61.3859%/6.2197% in Train and 32.7504%/63.1506%/6.5279% in
Gate01-Dev. Episode-unit concentration is
56.6851%/78.5672%/2.6209% and 56.5420%/79.9675%/2.5464%, respectively.
Conditioned route-row concentration is
56.2358%/80.0702%/2.4342% (Train) and 56.6767%/81.1168%/2.3090%
(Gate01-Dev), with 109/87 medications having at least 50 rows and 97/77 at
least 100. Conditioned numeric-dose-row concentration is
57.5558%/79.2177%/2.5367% and 57.1552%/80.5940%/2.4344%, with 109/86
medications having at least 50 rows and 96/77 at least 100.

### Decision

The predeclared floors require causal episode context, or otherwise at least
90% stable complete admission pairs, 90% observed routes, and 80% numeric
dose-plus-unit rows. Observed values are episode context `0`, stable admission
pair fraction `0.521047`, route fraction `0.999999`, and dose fraction
`0.935164`. No model was trained, no target collapse or rescue was attempted,
and no Idea 009, formal Gate, heldout/Audit/G3/G4/historical-test resource, or
push was used.

### Terminal decision

`KILL_RXUNIT_UNSUPPORTABLE_TARGET`
