# SafeDrug Archived Four-Model Reproduction Preparation Playbook

This playbook defines the exact operator sequence and verification protocol for preparing the SafeDrug archived four-model reproduction (`gamenet`, `safedrug`, `retain`, `leap-safedrug`) on `319-wild`.

## Scope and Invariants

1. **Reproduction Mode Only**: Comparison Mode, Prediction Adapters, and comparison qualifications remain out of scope for this phase.
2. **Scientific Authority**: SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` is the sole scientific authority for code, cohort, vocabularies, loss weights, learning rates, checkpoint selection rules, and test evaluation. Upstream `master`/`main` is an engineering reference only.
3. **Allowed Transformations**: Only two audited, run-scoped source adaptations are permitted in the Reproduction Program:
   - Training mode default `--Test` inversion (formal and smoke).
   - Smoke mode 50-to-1 epoch limitation (`EPOCH = 50` -> `EPOCH = 1`, leaving `Leap.py`'s `fine_tune()` `EPOCH = 100` untouched).
4. **Code Replacement Boundary**: The local repository is the code authority. The remote harness checkout (`/root/zhb/medrec-research`) and upstream SafeDrug checkout (`/root/zhb/SafeDrug`) may be converged or replaced to match clean local/pinned revisions. External data, historical runs, checkpoints, weights, and Conda environments outside those two checkouts must never be overwritten or deleted.
5. **Non-Evidence Smoke**: Four one-epoch smokes verify end-to-end integration (forward, backward, optimizer step, checkpoint emission). Smoke runs must not execute test branches, must not generate `test.log` or `result.json`, and must never be treated as scientific evidence.
6. **Hard Preparation Stop**: Execution terminates at `aggregate_state=awaiting_human_go_no_go` with `formal_training_authorized: false` in `runtime/reproduction-prep/<prep-id>/go-no-go.json`. Formal 50-epoch training and ten-round testing are strictly prohibited without human authorization.
7. **Historical Execution Record**: Attempt `formal-20260826-025500` completed full 50-epoch training and 10-round evaluation for all four models, achieving 12/20 point intervals and 3/3 directional relationships (terminal verdict `completed_mismatch`). In comparative reporting, metric differences are percentage-point changes (+1.312 points for Jaccard, +1.328 points for F1), not relative percentages. This historical attempt remains immutable and is succeeded by the MoleRec five-model reproduction plan.

## Operator Sequence

### Step 1: Local Verification and Revision Pinning

Run local test suite and quality gates:

```bash
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
markdownlint '**/*.md' --ignore '.agents/**'
```

Commit changes to establish an immutable local Git revision `HEAD`.

### Step 2: Converge Remote Code Checkouts

1. Verify SSH connectivity and target paths on 319:
   - Remote harness root: `/root/zhb/medrec-research`
   - Upstream SafeDrug root: `/root/zhb/SafeDrug`
   - External data root: `/root/zhb/medrec-data`

2. Sync remote harness checkout to the exact local revision `HEAD` and ensure a clean working tree.

3. Ensure `/root/zhb/SafeDrug` is clean and checked out at `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`.

### Step 3: Build and Prove Candidate Modern Environment

1. Create candidate Conda environment `medrec-safedrug-archived` on 319 from `environments/safedrug-archived.yml`:

   ```bash
   conda env create --file environments/safedrug-archived.yml
   ```

2. Run data-independent environment probe:

   ```bash
   CUDA_VISIBLE_DEVICES=0 python baselines/safedrug_archived.py gamenet \
     --upstream-root /root/zhb/SafeDrug \
     --mode probe --probe-scope environment
   ```

   Verify module imports, CUDA tensor execution on 1 visible RTX 3090, RDKit BRICS decomposition, and DNC forward pass.

### Step 4: Regenerate Staged Dataset and Validate B0 Counts

1. Run archived preprocessing into a staging directory: `/root/zhb/medrec-data/snapshots/staging-safedrug-archived-ijcai21`.

2. Verify all six canonical inputs exist as regular files:
   - `records_final.pkl`
   - `voc_final.pkl`
   - `ddi_A_final.pkl`
   - `ddi_mask_H.pkl`
   - `ehr_adj_final.pkl`
   - `idx2drug.pkl`

3. Verify the exact B0 paper aggregate counts:
   - Patients: `6,350`
   - Visits: `14,995`
   - Medications: `131`
   - DDI pairs: `448`
   - Molecular substructures: `491`

### Step 5: Freeze Environment Lock and Publish Integrated Pair

1. Export explicit Linux Conda lock on 319:

   ```bash
   conda list --explicit -n medrec-safedrug-archived > environments/safedrug-archived-linux-64.lock
   ```

2. Land the lock file in local Git, commit, and recreate the environment on 319 from the lock:

   ```bash
   conda create --name medrec-safedrug-archived --file environments/safedrug-archived-linux-64.lock --force
   ```

3. Run the complete program probe against staging:

   ```bash
   CUDA_VISIBLE_DEVICES=0 python baselines/safedrug_archived.py gamenet \
     --upstream-root /root/zhb/SafeDrug \
     --dataset-root /root/zhb/medrec-data/snapshots/staging-safedrug-archived-ijcai21 \
     --mode probe --probe-scope full
   ```

4. Compute SHA-256 of `conda list --explicit`, update `environment_sha256` in `baselines/registry.toml`, commit locally, and resync.

5. Atomically rename staging directory to final target:
   `/root/zhb/medrec-data/snapshots/safedrug-archived-ijcai21`.

### Step 6: Execute Four Independent One-Epoch Smokes

1. Identify four idle GPUs (e.g. `0,1,2,3`) via `nvidia-smi`.

2. Submit four independent smoke lanes:

   ```bash
   rtk proxy /opt/homebrew/bin/uv run medrec-research reproduce-smoke all --gpus 0,1,2,3
   ```

3. Monitor each `medrec-smoke-` tmux session and terminal artifacts until completion.

4. Verify each lane's terminal artifacts:
   - `status.json`: `state: "completed"`, `stage: "terminal"`, `failure_code: null`
   - `smoke.json`: `non_evidence: true`, `epochs_requested: 1`, `epochs_observed: 1`, `best_epoch: 0`, valid epoch-0 checkpoint
   - Confirm absence of `test.log` and `result.json`.

### Step 7: Assemble Review Packet and Terminate

Write public-safe `runtime/reproduction-prep/<prep-id>/go-no-go.json` containing:

- `aggregate_state`: `awaiting_human_go_no_go` (or `partial_smoke_failure`)
- `formal_training_authorized`: `false`
- All four lane statuses, GPU indices, session IDs, and registry-relative terminal artifact identifiers.
- Stop and hand over to human review.
