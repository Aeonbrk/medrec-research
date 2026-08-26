# MoleRec Table 1 Five-Model Reproduction Playbook

This playbook defines the exact operator sequence and verification protocol for preparing and executing the MoleRec Table 1 five-model reproduction (`retain`, `leap`, `gamenet`, `safedrug`, `molerec`) across seven parallel GPU lanes on `319-wild`.

## Scope and Invariants

1. **Reproduction Mode Only**: Comparison Mode, Prediction Adapters, and comparison qualifications remain out of scope for this phase.
2. **Scientific Authority**:
   - MoleRec `0e46123049280d829910d6fc48bc953a99264c1b` is the primary scientific authority for MoleRec Table 1 code, data assets (`sub_structure.pkl`, `word2vec_300.model`), architecture, hyperparameters, and evaluation.
   - SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` is the scientific authority for archived SafeDrug/GAMENet/RETAIN/LEAP code and candidate learning rates.
3. **Seven Parallel Execution Lanes**:
   - `molerec-retain` (GPU 0): RETAIN baseline (LR 5e-4)
   - `molerec-leap` (GPU 1): LEAP baseline (LR 5e-4)
   - `molerec-gamenet` (GPU 2): GAMENet baseline (LR 1e-4)
   - `molerec-safedrug-lr-1e-5` (GPU 3): SafeDrug candidate learning rate 1e-5
   - `molerec-safedrug-lr-1e-4` (GPU 4): SafeDrug candidate learning rate 1e-4
   - `molerec-safedrug-lr-5e-4` (GPU 5): SafeDrug candidate learning rate 5e-4 (default)
   - `molerec-embedding` (GPU 6): MoleRec Table 1 (LR 5e-4)
4. **Validation-Only SafeDrug Selection**: SafeDrug model selection among candidate learning rates (`1e-5`, `1e-4`, `5e-4`) evaluates only validation loss / Jaccard across the training logs, selecting the single best model before evaluating on the test set.
5. **Hardware Compatibility & Environment Isolation**:
   - `medrec-safedrug-archived`: Python 3.11, PyTorch 2.2.2 with CUDA 12.1.
   - `molerec`: Python 3.8.16, PyTorch 1.9.0 with CUDA 11.1 (RTX 3090 Ampere SM86 support) and PyG 2.0.3.
6. **Non-Global Mirror-First Resolution**: Package managers prioritize China mirrors (TUNA, BFSU, Aliyun) via command-scoped configuration. TLS verification remains strictly enabled (`ssl_verify: true`). Global configs (`~/.condarc`, `~/.pip/pip.conf`) must never be modified.
7. **Multi-Axis Verdict**: Outcome is evaluated as `completed_match` (all 25 intervals and 4 directional relationships satisfied) or `completed_mismatch` (completed execution with interval/relationship discrepancies).

## Operator Sequence

### Step 1: Local Verification and Revision Pinning

Run local test suite and quality gates on the Mac harness:

```bash
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
markdownlint '**/*.md' --ignore '.agents/**'
```

Commit changes to establish an immutable local Git revision `HEAD`.

### Step 2: Converge Remote Code Checkouts on 319-wild

1. Verify SSH connectivity and target directories on `319-wild`:
   - Remote harness root: `/root/zhb/medrec-research`
   - Upstream SafeDrug root: `/root/zhb/SafeDrug` (`archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`)
   - Upstream MoleRec root: `/root/zhb/MoleRec` (`0e46123049280d829910d6fc48bc953a99264c1b`)
   - External data root: `/root/zhb/medrec-data`

2. Sync remote harness checkout to exact local `HEAD` with clean worktree.

### Step 3: Build and Prove Environments

1. Build `medrec-safedrug-archived` Conda environment from `environments/safedrug-archived.yml`.
2. Build `molerec` Conda environment from `environments/molerec-table1.yml`.
3. Run data-independent environment probes:

```bash
CUDA_VISIBLE_DEVICES=0 python baselines/safedrug_archived.py gamenet \
  --upstream-root /root/zhb/SafeDrug \
  --mode probe --probe-scope environment

CUDA_VISIBLE_DEVICES=0 python baselines/molerec.py molerec \
  --upstream-root /root/zhb/MoleRec \
  --mode probe --probe-scope environment
```

### Step 4: Staged Dataset Validation

Verify dataset files in `/root/zhb/medrec-data/snapshots/safedrug-archived-ijcai21`:

- `records_final.pkl` (6,350 patients, 15,032 executable visits)
- `voc_final.pkl` (1,958 diag, 1,430 pro, 131 med)
- `ddi_A_final.pkl` (131x131, 448 pairs)
- `ddi_mask_H.pkl` (131x491 substructure mask)
- `ehr_adj_final.pkl` (131x131 medication co-occurrence)
- `sub_structure.pkl`
- `word2vec_300.model`
- `sub_structure_mask.pkl`

### Step 5: Concurrent Seven-Lane Execution

1. Verify 7 idle GPUs (0 through 6) on `319-wild` via `nvidia-smi`.
1. Submit all seven reproduction lanes:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec-research reproduce all --gpus 0,1,2,3,4,5,6
```

1. Monitor tmux sessions:
   - `medrec-baseline-molerec-retain-*`
   - `medrec-baseline-molerec-leap-*`
   - `medrec-baseline-molerec-gamenet-*`
   - `medrec-baseline-molerec-safedrug-lr-1e-5-*`
   - `medrec-baseline-molerec-safedrug-lr-1e-4-*`
   - `medrec-baseline-molerec-safedrug-lr-5e-4-*`
   - `medrec-baseline-molerec-embedding-*`

### Step 6: SafeDrug Candidate Learning Rate Selection

Compare validation logs of GPUs 3, 4, 5:

- Identify candidate with lowest validation loss and highest validation Jaccard.
- Select winning SafeDrug model checkpoint for Table 1 evaluation.

### Step 7: Table 1 Audit and Packet Emission

Run deterministic audit against Table 1 reference targets:

```bash

rtk proxy /opt/homebrew/bin/uv run medrec-research audit-molerec-table1 \
  --ledger runtime/reproduction/molerec-table1-ledger.json \
  --retain-result runs/molerec-retain/result.json \
  --leap-result runs/molerec-leap/result.json \
  --gamenet-result runs/molerec-gamenet/result.json \
  --safedrug-result runs/molerec-safedrug-selected/result.json \
  --molerec-result runs/molerec-embedding/result.json \
  --output runtime/reproduction/molerec-table1-audit-packet.json
```

Verify emitted public-safe audit packet.
