# MIMIC-III canonical-131 paper development profile

This directory freezes the smallest MIMIC-III task and evaluator contract
needed by new Train/Dev runs. It does not authorize Test access or create a
paper candidate. Historical MICA runs remain separate because they used a
fixed threshold and visit-macro selection rather than this profile.

## Frozen benchmark identity

- surface: `MIMIC-III canonical-131`;
- source snapshot: `molerec-table1-c721-www23`;
- snapshot assets: the pinned `records_final.pkl`, `voc_final.pkl`, and
  `ddi_A_final.pkl` recorded in [`profile.json`](profile.json);
- medication axis: the ordered 131-entry MoleRec/SafeDrug ATC4 identity set;
- patient split: the first `floor(2N/3)` snapshot patients are Train, and the
  remaining patients selected by the frozen SHA-256 rule are Dev;
- Train/Dev counts: 4,233/1,004 patients and 10,489/2,130 visits;
- all observed Train/Dev targets are non-empty. If a future materialization
  contains an empty mapped target, it is excluded from recommendation
  examples but remains in chronology and history.

The model sees current diagnosis and procedure sets plus strictly earlier
diagnosis, procedure, and medication history. It never sees the current
target medication set, a future visit, or a target-derived statistic at
prediction time. The first visit is eligible when its mapped target is
non-empty.

## Frozen evaluator and selection

The primary endpoint is patient-macro Jaccard. A patient mean is computed
over that patient's eligible visits, then patient means are averaged equally.
Patient-macro F1, PRAUC/AP, and predicted medication count use the same
aggregation. Visit-macro values are supplementary. PRAUC/AP is average
precision over all 131 coordinates using one finite sigmoid score per
medication; ties use vocabulary order and an empty target has AP `0.0`.

DDI is the pooled ratio of interacting unordered predicted pairs. Self-pairs
are omitted, duplicate pairs are counted once, and a zero denominator is
reported as DDI `0.0` with pair count `0`. OOV targets are profile errors after
the frozen mapping; zero-support coordinates remain in the output space and
in AP.

Every validation checkpoint is evaluated at every threshold in
`selection.operating_points`. The selected checkpoint and threshold jointly
maximize Dev patient-macro Jaccard. Ties use the threshold closest to the
native default, then the declared threshold order, then the earlier
checkpoint. The maximum budget, validation schedule, threshold list, and
tie-break are fixed before repeated runs.

The profile declares MICA stability seeds `20260917` and `20260918`. A pair
uses the same seed in SharedPool and DrugQuery. These seeds are new
development evidence; the historical single-seed result is not silently
relabelled.

MIMIC-IV Test remains sealed. This profile contains no Test membership,
targets, predictions, or metrics.
