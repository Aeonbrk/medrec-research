<!-- markdownlint-disable MD013 -->

# Failure Record: SafeDrug Four-Model Reproduction B0 Data Gate Termination

- **Attempt ID**: `formal-20260825-231500`
- **Status**: Historical (Terminal attempt; succeeded by `formal-20260826-025500`)
- **Date**: 2026-08-25
- **Harness Revision**: `caec25e7f41166998b4ed0d7ad201b8355f77eea`
- **Archived Model Revision**: `8deee38cfdb2a38882377ff95cce5922d6d9e8d6`
- **Preprocessing Source Revision**: `c7218d0976e5ee5588aeaf5bdbc86b338126bba5`
- **Environment SHA-256**: `c17ebfc53484b74497e2d6d8058271de8d7503a2fdb19eb756ddff17ba9715b9`

---

## Decision

The four-model full reproduction attempt (`formal-20260825-231500`) is **terminated** at Unit 3 (Dataset Regeneration) under the fail-closed protocol.

- Target snapshot `snapshots/safedrug-paper-c721-ijcai21` was **not published**.
- Staging candidate `.safedrug-paper-c721-ijcai21.formal-20260825-231500.staging` was **rejected**.
- Formal training lanes and smoke lanes were not admitted.
- Baseline registry statuses remain at `registered`.

---

## What Was Verified

1. **Remote Preflight & Environment Identity**:
   - 319-lab-via-server host preflight passed (`root`, 8× RTX 3090 GPUs idle, >2.5 TiB free disk).
   - Conda environment `medrec-safedrug-archived` explicitly verified (`sha256 = c17ebfc53484b74497e2d6d8058271de8d7503a2fdb19eb756ddff17ba9715b9`).
   - Remote environment probe passed all import checks (`torch`, `dnc`, `rdkit`, `pandas`, `dill`, `sklearn`, `models`, `util`), CUDA tensor allocation, RDKit BRICS decomposition, and DNC forward pass.

2. **319 Input Contract & Lineage**:
   - `PRESCRIPTIONS.csv.gz`: 4,156,450 data rows, exact columns verified.
   - `DIAGNOSES_ICD.csv.gz`: 651,047 data rows, exact columns verified.
   - `PROCEDURES_ICD.csv.gz`: 240,095 data rows, exact columns verified.
   - `drug-DDI.csv`: 4,649,441 data rows, exact columns verified.
   - Preprocessing checkout `/root/zhb/SafeDrug-c7218d0` clean at `c7218d0976e5ee5588aeaf5bdbc86b338126bba5`.
   - Archived model checkout `/root/zhb/SafeDrug` clean at `8deee38cfdb2a38882377ff95cce5922d6d9e8d6`.

3. **Preprocessing Script Execution & Semantic Bridge Checks**:
   - Executed `data/processing.py` from `c7218d0` with exact 4-path substitution.
   - Generated the 4 primary outputs (`records_final.pkl`, `voc_final.pkl`, `ddi_A_final.pkl`, `ehr_adj_final.pkl`).
   - Confirmed exact ordered bijection between generated `med_voc.idx2word` and pinned `c7218d0` `med_voc.idx2word`.
   - Verified 6 semantic bridge checks:
     - Vocabulary bijections: `passed`
     - Records 3-modality structure: `passed`
     - SMILES molecule mapping contract: `passed`
     - DDI adjacency matrix symmetry & zero-diagonal: `passed`
     - EHR adjacency matrix symmetry & zero-diagonal: `passed`
     - DDI mask matrix `[131, 491]` binary contract: `passed`

---

## The B0 Gate Discrepancy

When evaluated against the IJCAI 2021 Table 1 Paper Baseline (`B0`), the regenerated dataset yielded:

| Metric / Dimension | Expected (IJCAI 2021 Table 1) | Observed (Regenerated `c7218d0`) | Status |
| :--- | :--- | :--- | :--- |
| **Patients** | 6,350 | 6,350 | **MATCH** |
| **Visits** | 14,995 | 15,032 | **MISMATCH (+37 visits)** |
| **Medications** | 131 | 131 | **MATCH** |
| **DDI Pairs** | 448 | 448 | **MATCH** |
| **Molecular Substructures** | 491 | 491 | **MATCH** |

The observation of **15,032 visits** instead of **14,995 visits** is a property of running the upstream authors' exact published preprocessing code (`c7218d0:data/processing.py`) against official MIMIC-III 1.4.

---

## Non-Revival Boundary

Under the Unified Research Protocol and the fail-closed reproduction policy:

- We do **not** retroactively filter visits, manipulate date thresholds, or trim admissions to force 14,995 visits.
- We do **not** train or claim reproduction on a dataset that drifts from the published paper counts.
- This failure is permanently recorded as an upstream data-pipeline characteristic.
