<!-- markdownlint-disable MD013 -->

# Decision Record: MoleRec Table 1 Five-Model Full Reproduction Authority and Architecture

- **Date**: 2026-08-26
- **Status**: Accepted
- **Plan**: `docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md`
- **Authors**: Gemini (Implementation), Codex (Review)

---

## 1. Context and Problem Statement

The previous pilot reproduction (`formal-20260826-025500`) confirmed the execution pipeline for four SafeDrug-family models but revealed that:

1. `baselines/safedrug_archived.py` conflated scientific contracts, data validation, log parsing, and process execution in a single 1,300-line module.
2. The control plane hardcoded 4 scientific models to 4 execution lanes, precluding hyperparameter candidates (such as SafeDrug's 3 learning-rate candidates).
3. The existing modern environment (Python 3.11 / PyTorch 2.2) differs from official MoleRec's recorded Python 3.8 / PyTorch 1.9 / PyG 2.0.3 stack.
4. Adding MoleRec requires paired molecular assets (`ddi_mask_H.pkl`, `substructure_smiles.pkl`) that must align with the common `c7218d0` medication vocabulary.

---

## 2. Settled Decisions

### D1: Two-Source Model Authority

- **SafeDrug Family** (RETAIN, LEAP, GAMENet, SafeDrug): Frozen at `ycq091044/SafeDrug@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`.
- **MoleRec**: Frozen at `yangnianzu0515/MoleRec@dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, using the embedding-table variant (`--embedding`).

### D2: Common Data Authority and Executable Counts

- Common EHR and DDI data processed under `ycq091044/SafeDrug@c7218d0976e5ee5588aeaf5bdbc86b338126bba5`.
- Exact executable visit count is **15,032**; 14,995 is retained as paper-reported metadata. No post hoc visit trimming is permitted.

### D3: Five Scientific Models, Seven Execution Lanes

- Five scientific models map to seven formal 50-epoch training lanes:
  - `molerec-retain` (RETAIN)
  - `molerec-leap` (LEAP)
  - `molerec-gamenet` (GAMENet)
  - `molerec-safedrug-lr-1e-5` (SafeDrug, LR $1\times 10^{-5}$)
  - `molerec-safedrug-lr-1e-4` (SafeDrug, LR $1\times 10^{-4}$)
  - `molerec-safedrug-lr-5e-4` (SafeDrug, LR $5\times 10^{-4}$)
  - `molerec-embedding` (MoleRec `--embedding`)
- SafeDrug model selection is strictly **validation-only**: max validation Jaccard, min validation DDI, smaller LR tie-break. `selection.json` is generated before SafeDrug test evaluation. Non-selected candidates remain `not_tested_by_design`.

### D4: Unified Compatibility Environment with Documented CUDA Deviation

- Environment `medrec-molerec-table1` declares:
  - Python 3.8.16
  - PyTorch 1.9.0 with CUDA 11.1 (`torch==1.9.0+cu111`)
  - PyTorch Geometric 2.0.3 with native extensions (`torch-scatter`, `torch-sparse`, `torch-cluster`, `torch-spline-conv`)
  - NumPy 1.23.5, pandas 1.5.3, SciPy 1.10.0, scikit-learn 1.2.0, RDKit 2022.09.1, dill 0.3.7, dnc 1.1.0
- **Hardware Deviation**: CUDA 11.1 is the minimal necessary deviation from recorded CUDA 10.2 to support NVIDIA Ampere RTX 3090 (SM86) hardware.

### D5: Additive Eight-File Snapshot

- Snapshot `snapshots/molerec-table1-c721-www23` exposes exactly 8 consumer files:
  - `records_final.pkl`, `voc_final.pkl`, `ddi_A_final.pkl`, `ehr_adj_final.pkl` (from accepted c721 dataset)
  - `ddi_mask_H.pkl`, `substructure_smiles.pkl`, `idx2SMILES.pkl` (paired from MoleRec revision `dd5afaf`)
  - `idx2drug.pkl` (byte-identical alias to `idx2SMILES.pkl`)
- Proves ordered medication vocabulary equality and 491-column substructure alignment.

### D6: GPU and NUMA Topology-Aware Scheduling

- P1 isolated profiling (5 architectures) and P2 concurrent profiling (7 lanes across GPUs 0–6).
- Two NUMA nodes balanced; GPU 7 reserved for serial 10-round test evaluations and recorded recovery.

### D7: Multi-Axis Verdicts

- Audit separately reports:
  1. `execution_integrity`
  2. `paper_point_fidelity` (25 Table 1 point estimates against reported mean $\pm 2\sigma$)
  3. `directional_relationships` (4 checks: MoleRec > SafeDrug on Jaccard/F1/PRAUC, MoleRec < SafeDrug on DDI)
  4. `artifact_completeness`
- Overall verdict is `completed_match` if all pass; `completed_mismatch` if execution is complete but any point/direction check fails; or specific incomplete/blocked states.

### D8: Narrow Reversible Terminal Cleanup

- Superseded environment `medrec-safedrug-archived` may be removed only after successor environment and full reproduction attempt are terminal. Lock `environments/safedrug-archived-linux-64.lock` remains versioned for recovery.

### D9: Package Resolution and Security Policy

- China mirrors prioritized via command/repo-scoped config.
- Official HTTPS fallbacks with TLS verification strictly enforced. No global config mutation.
