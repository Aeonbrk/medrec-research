<!-- markdownlint-disable MD013 -->

# Failure Record: SafeDrug Four-Model Reproduction Table 2 Mismatch

- **Attempt ID**: `formal-20260826-025500`
- **Date**: 2026-08-26
- **Harness Revision**: `dc4781edc3ffa707042817cee7c29eed1aeb7a3c`
- **Archived Model Revision**: `ycq091044/SafeDrug@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`
- **Preprocessing Source Revision**: `ycq091044/SafeDrug@c7218d0976e5ee5588aeaf5bdbc86b338126bba5`
- **Environment SHA-256**: `c17ebfc53484b74497e2d6d8058271de8d7503a2fdb19eb756ddff17ba9715b9`
- **Conda Environment**: `medrec-safedrug-archived` (Python 3.11.15, PyTorch 2.2.2+cu121)
- **Snapshot ID**: `snapshots/safedrug-paper-c721-ijcai21`

---

## 1. Terminal Outcome

The full four-model reproduction attempt `formal-20260826-025500` executed end-to-end (all 4 models completed 50 epochs of training on dedicated GPUs, followed by 10-round upstream test evaluation).

- **Execution Integrity**: `PASSED` (zero runtime crashes, valid checkpoints, full 10-round testing).
- **Directional Relationships**: `PASSED` (3 of 3 core directional relationships confirmed).
- **Point-Estimate Fidelity**: `FAILED` (12 of 20 metric point estimates within published $2\sigma$ statistical bounds; 8 misses).
- **Aggregate Verdict**: `completed_mismatch`.

Under the fail-closed reproduction protocol, validating directional relationships does **not** override point-estimate discrepancies. The attempt is permanently recorded as a completed mismatch rather than a full reproduction.

---

## 2. Table 2 Discrepancies Breakdown

| Model | Metric | Published Target | Published $2\sigma$ Interval | Observed Reproduction | Discrepancy | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GAMENet** | Avg Med | $27.2145 \pm 0.1141$ | $[26.9863, 27.4427]$ | $27.5790 \pm 0.1834$ | $+0.1363$ | **OUT** |
| **SafeDrug** | DDI Rate | $0.0589 \pm 0.0005$ | $[0.0579, 0.0599]$ | $0.0612 \pm 0.0006$ | $+0.0013$ | **OUT** |
| **SafeDrug** | Jaccard | $0.5213 \pm 0.0030$ | $[0.5153, 0.5273]$ | $0.5148 \pm 0.0022$ | $-0.0005$ | **OUT** |
| **RETAIN** | DDI Rate | $0.0835 \pm 0.0020$ | $[0.0795, 0.0875]$ | $0.0893 \pm 0.0007$ | $+0.0018$ | **OUT** |
| **RETAIN** | Avg Med | $20.4051 \pm 0.2832$ | $[19.8387, 20.9715]$ | $19.7880 \pm 0.1593$ | $-0.0507$ | **OUT** |
| **LEAP** | DDI Rate | $0.0731 \pm 0.0008$ | $[0.0715, 0.0747]$ | $0.0760 \pm 0.0008$ | $+0.0013$ | **OUT** |
| **LEAP** | Jaccard | $0.4521 \pm 0.0024$ | $[0.4473, 0.4569]$ | $0.4576 \pm 0.0025$ | $+0.0007$ | **OUT** |
| **LEAP** | Avg F1 | $0.6138 \pm 0.0026$ | $[0.6086, 0.6190]$ | $0.6193 \pm 0.0023$ | $+0.0003$ | **OUT** |

The remaining 12 cells passed within target intervals (GAMENet DDI, Jaccard, F1, PRAUC; SafeDrug F1, PRAUC, Avg Med; RETAIN Jaccard, F1, PRAUC; LEAP PRAUC, Avg Med).

---

## 3. Metric Reporting Correction: Percentage Points vs. Relative

In comparative summaries, changes in Jaccard and F1 are percentage-point shifts, not relative percentage changes:

- **Jaccard gain**: $\text{SafeDrug } (0.5148) - \text{GAMENet } (0.5017) = +0.01312$ ($+1.312$ percentage points), corresponding to a $+2.62\%$ relative increase.
- **Avg F1 gain**: $\text{SafeDrug } (0.6717) - \text{GAMENet } (0.6585) = +0.01328$ ($+1.328$ percentage points), corresponding to a $+2.02\%$ relative increase.
- **DDI reduction**: $\text{SafeDrug } (0.0612) \text{ vs. } \text{LEAP } (0.0760) = -0.0148$ ($-1.48$ percentage points), corresponding to a $-19.47\%$ relative reduction.

---

## 4. Non-Revival & Admissibility Boundaries

1. **Immutable Historical Pilot**: Attempt `formal-20260826-025500` is closed and immutable. No parameter tuning, seed sweeping, or checkpoint substitution is permitted.
2. **Inadmissibility as Successor Evidence**: The checkpoints, logs, and metrics from this pilot cannot serve as evidence for the five-model MoleRec Table 1 reproduction plan (`docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md`).
3. **Data Product Reuse**: The generated `c7218d0` data files may be reused for the successor additive snapshot `snapshots/molerec-table1-c721-www23` only after independent verification of ordered vocabulary equality and paired molecular asset alignment.
