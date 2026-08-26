<!-- markdownlint-disable MD013 -->

# SafeDrug IJCAI 2021 Four-Model Full Reproduction Report

- **Attempt ID**: `formal-20260826-025500`
- **Execution Date**: 2026-08-26
- **Server**: `319-lab-via-server` (8× NVIDIA GeForce RTX 3090, 24 GB VRAM each)
- **Conda Environment**: `medrec-safedrug-archived` (Python 3.11.15, PyTorch 2.2.2+cu121, CUDA 12.1)
- **Environment SHA-256**: `c17ebfc53484b74497e2d6d8058271de8d7503a2fdb19eb756ddff17ba9715b9`
- **Harness Revision**: `dc4781edc3ffa707042817cee7c29eed1aeb7a3c`
- **Archived Model Revision**: `ycq091044/SafeDrug@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`
- **Preprocessing Source Revision**: `ycq091044/SafeDrug@c7218d0976e5ee5588aeaf5bdbc86b338126bba5`
- **Additive Snapshot**: `snapshots/safedrug-paper-c721-ijcai21`

---

## 1. Executive Summary

We executed the complete end-to-end Reproduction Mode pipeline for all four models evaluated in the IJCAI 2021 SafeDrug paper: **GAMENet**, **SafeDrug**, **RETAIN**, and **LEAP**.

Every step of the pipeline was executed under strict fail-closed reproduction invariants:

1. **Pre-flight & Environment**: Passed all module imports (`torch`, `dnc`, `rdkit`, `pandas`, `dill`, `sklearn`, `models`, `util`), CUDA tensor allocations, RDKit BRICS substructure decompositions, and DNC forward passes on 319.
2. **Dataset Regeneration & Bridge Validation**: Executed `c7218d0` preprocessing against official MIMIC-III v1.4, producing exactly 6,350 patients and 15,032 executable visits (with metadata disclosure of 14,995 paper-reported visits, $\Delta = 37$). Verified all 6 semantic bridge invariants and verified that Table 1 average counts match down to the hundredth decimal place (157,970 diagnoses / 10.51 avg, 57,778 procedures / 3.84 avg, 171,900 medications / 11.44 avg).
3. **Fresh Smoke Lanes**: Executed 1-epoch fresh smoke runs on GPUs 0, 1, 2, and 3 for all 4 models; all 4 models completed with zero exceptions.
4. **Formal 50-Epoch Lanes & 10-Round Evaluation**: Completed full 50-epoch training and 10-round upstream testing on dedicated GPUs (GAMENet: GPU 0, SafeDrug: GPU 1, RETAIN: GPU 2, LEAP: GPU 3).
5. **Deterministic Table 2 Audit**: Executed `audit-safedrug-table2` on the 4 result artifacts and runtime state ledger.

---

## 2. Table 2 Reproduction Comparison

| Model | Metric | Target (IJCAI 2021 Table 2) | Target 2$\sigma$ Interval | Observed Reproduction (10 Rounds) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GAMENet** | **DDI Rate** | $0.0864 \pm 0.0006$ | $[0.0852, 0.0876]$ | $0.0867 \pm 0.0007$ | **PASS** |
| | **Jaccard** | $0.5067 \pm 0.0025$ | $[0.5017, 0.5117]$ | $0.5017 \pm 0.0037$ | **PASS** |
| | **Avg F1** | $0.6626 \pm 0.0025$ | $[0.6576, 0.6676]$ | $0.6585 \pm 0.0034$ | **PASS** |
| | **PRAUC** | $0.7631 \pm 0.0030$ | $[0.7571, 0.7691]$ | $0.7671 \pm 0.0036$ | **PASS** |
| | **Avg Med** | $27.2145 \pm 0.1141$ | $[26.9863, 27.4427]$ | $27.5790 \pm 0.1834$ | Out (+0.136) |
| **SafeDrug** | **DDI Rate** | $0.0589 \pm 0.0005$ | $[0.0579, 0.0599]$ | $0.0612 \pm 0.0006$ | Out (+0.0013) |
| | **Jaccard** | $0.5213 \pm 0.0030$ | $[0.5153, 0.5273]$ | $0.5148 \pm 0.0022$ | Out ($-0.0005$) |
| | **Avg F1** | $0.6768 \pm 0.0027$ | $[0.6714, 0.6822]$ | $0.6717 \pm 0.0020$ | **PASS** |
| | **PRAUC** | $0.7647 \pm 0.0025$ | $[0.7597, 0.7697]$ | $0.7645 \pm 0.0029$ | **PASS** |
| | **Avg Med** | $19.9178 \pm 0.1604$ | $[19.5970, 20.2386]$ | $19.6850 \pm 0.1464$ | **PASS** |
| **RETAIN** | **DDI Rate** | $0.0835 \pm 0.0020$ | $[0.0795, 0.0875]$ | $0.0893 \pm 0.0007$ | Out (+0.0018) |
| | **Jaccard** | $0.4887 \pm 0.0028$ | $[0.4831, 0.4943]$ | $0.4899 \pm 0.0032$ | **PASS** |
| | **Avg F1** | $0.6481 \pm 0.0027$ | $[0.6427, 0.6535]$ | $0.6499 \pm 0.0027$ | **PASS** |
| | **PRAUC** | $0.7556 \pm 0.0033$ | $[0.7490, 0.7622]$ | $0.7593 \pm 0.0038$ | **PASS** |
| | **Avg Med** | $20.4051 \pm 0.2832$ | $[19.8387, 20.9715]$ | $19.7880 \pm 0.1593$ | Out ($-0.051$) |
| **LEAP** | **DDI Rate** | $0.0731 \pm 0.0008$ | $[0.0715, 0.0747]$ | $0.0760 \pm 0.0008$ | Out (+0.0013) |
| | **Jaccard** | $0.4521 \pm 0.0024$ | $[0.4473, 0.4569]$ | $0.4576 \pm 0.0025$ | Out (+0.0007) |
| | **Avg F1** | $0.6138 \pm 0.0026$ | $[0.6086, 0.6190]$ | $0.6193 \pm 0.0023$ | Out (+0.0003) |
| | **PRAUC** | $0.6549 \pm 0.0033$ | $[0.6483, 0.6615]$ | $0.6581 \pm 0.0038$ | **PASS** |
| | **Avg Med** | $18.7138 \pm 0.0666$ | $[18.5806, 18.8470]$ | $18.7100 \pm 0.0624$ | **PASS** |

---

## 3. Core Scientific Claims and Relationship Checks

The core claims of the IJCAI 2021 SafeDrug paper were evaluated deterministically:

1. **Relationship 1 (Recommendation Quality - Jaccard)**:
   $$\text{SafeDrug } (0.5148) > \text{GAMENet } (0.5017) \implies \mathbf{PASSED}$$
   SafeDrug improves Jaccard similarity over GAMENet by **+1.31%**.

2. **Relationship 2 (Recommendation Quality - F1)**:
   $$\text{SafeDrug } (0.6717) > \text{GAMENet } (0.6585) \implies \mathbf{PASSED}$$
   SafeDrug improves Avg F1 score over GAMENet by **+1.33%**.

3. **Relationship 3 (Safety - DDI Rate)**:
   $$\text{SafeDrug } (0.0612) < \text{LEAP } (0.0760) \implies \mathbf{PASSED}$$
   SafeDrug reduces DDI rate relative to LEAP by **-19.5%** (and relative to GAMENet $0.0867$ by **-29.4%**).

**Result**: **3 out of 3 core scientific relationships (100%) are fully validated and confirmed**.

---

## 4. Fail-Closed Reproduction Protocol Verdict

- **Interval Checks**: **12 / 20** passed within strict $2\sigma$ statistical bounds.
- **Relationship Checks**: **3 / 3** passed.
- **Audit Verdict**: `completed_mismatch`
- **Rationale**: Under the repository’s fail-closed verification contract, any point metric deviation beyond the published $2\sigma$ interval results in a `completed_mismatch` audit verdict. No tuning, seed sweeping, or threshold manipulation is performed. All artifacts and exact traces are permanently preserved.
