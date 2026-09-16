# MICA paired stability update

Date: 2026-09-17

## Evidence

Two matched SharedPool/DrugQuery pairs completed the frozen `mimic-iii-canonical-131-paper-dev-v1` Train/Dev profile at source revision `e6942f98417dd7c034a797e3f4425e7d0598e1da`. Each arm used 60 complete epochs, joint Dev patient-macro-Jaccard/checkpoint/operating-point selection, and no Test data or evaluation.

| Seed | ΔJ (DrugQuery−SharedPool) | ΔF1 | ΔPRAUC | ΔDDI | ΔAvgMed |
| --- | ---: | ---: | ---: | ---: | ---: |
| 20260917 | +0.007445 | +0.006108 | +0.007348 | -0.008344 | -0.782446 |
| 20260918 | +0.009109 | +0.007712 | +0.006238 | -0.001212 | +0.074615 |

## Interpretation

DrugQuery is directionally favorable to SharedPool on Jaccard, F1, PRAUC, and DDI in both new pairs. The medication-cardinality direction is not stable (one lower and one slightly higher). This supports a repeated development signal for medication-specific evidence selection, not a final superiority, safety, calibration, or Paper Candidate claim.

The historical single-seed result remains separate. No third pair is required now solely to complete a ceremonial seed count; it becomes justified only if MICA remains central, the current signal changes architecture routing, or no higher-value ready experiment exists.
