# MoleRec Table 1 Five-Model Reproduction Playbook

This playbook is the operator gate for the reproduction defined by `docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md`. It is not evidence of execution. As of 2026-08-29, the seven source lanes in attempt `formal-20260828-a09fcab-u8-b` have one validated immutable recovery sibling each. No test result or final five-model audit exists; stop before any new evidence-producing command until the final harness revision and frozen schedule are re-accepted.

## Scope and Invariants

1. **Reproduction Mode only**: Comparison Mode, Prediction Adapters, and comparison qualifications are out of scope.
2. **Frozen authorities**:
   - SafeDrug archived source: `8deee38cfdb2a38882377ff95cce5922d6d9e8d6` for SafeDrug, GAMENet, RETAIN, and LEAP behavior.
   - MoleRec source: `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` for MoleRec behavior and paired molecular assets.
   - Preprocessing source: `c7218d0976e5ee5588aeaf5bdbc86b338126bba5` for the common data lineage.
3. **Seven registry lanes**:
   - `molerec-retain`
   - `molerec-leap`
   - `molerec-gamenet`
   - `molerec-safedrug-lr-1e-5`
   - `molerec-safedrug-lr-1e-4`
   - `molerec-safedrug-lr-5e-4`
   - `molerec-embedding`

   The registry order is the logical order for a batch. Physical GPU/CPU placement is provisional until U7 profiling; GPU 7 is reserved for serial evaluation and permitted recovery.

4. **One compatibility environment**: all seven lanes use `medrec-molerec-table1`, declared as Python 3.8.16, PyTorch 1.9.0 with cu111, and PyG 2.0.3. The historical `medrec-safedrug-archived` declaration is recovery-only.
5. **One additive snapshot**: current lanes use `snapshots/molerec-table1-c721-www23`, containing exactly:

   - `records_final.pkl`
   - `voc_final.pkl`
   - `ddi_A_final.pkl`
   - `ehr_adj_final.pkl`
   - `ddi_mask_H.pkl`
   - `substructure_smiles.pkl`
   - `idx2SMILES.pkl`
   - byte-identical `idx2drug.pkl`

   Its executable counts are 6,350 patients, 15,032 visits, 131 medications, 448 DDI pairs, and 491 molecular substructures. The 14,995 visit value is paper-reported metadata only and must never replace the executable count.

6. **Validation-only SafeDrug selection**: all three SafeDrug training candidates must be terminal before selection. Rank by validation Jaccard descending, validation DDI ascending, learning rate ascending, and lane ID ascending. No test metric may enter `selection.json`; only the selected candidate may receive a test command.
7. **Four-axis verdict**: report execution integrity, paper point fidelity, directional relationships, and artifact completeness separately. `completed_match` requires all four axes; a complete scientific miss is `completed_mismatch`.

## Current Gate State

The following local contracts are implemented and synthetic-tested: registry lanes and program-declared probes, v2 status/result identity, atomic finalization, immutable source-aware recovery, validation-only SafeDrug selection, the eight-file snapshot builder, the four-axis audit, the frozen-schedule admission contract, the persisted GPU 7 queue, and bounded running-status heartbeats.

The following gates remain open and block a successor formal submission: a clean reviewed harness revision, re-acceptance of the measured schedule against that revision, and the normal preflight checks immediately before submission. The current attempt has seven recovered training results and remains test-free; its pending downstream gates are SafeDrug selection, five serial ten-round tests, and the final audit. The old `formal-20260826-025500` attempt remains immutable historical evidence and is not reusable successor evidence.

## Operator Sequence

### 1. Run local gates and inspect the freeze boundary

Run these checks on the Mac harness. They detect broken contracts, formatting regressions, and stale Markdown; failures must be fixed before a clean revision can be frozen.

```bash
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
rtk markdownlint '**/*.md' --ignore '.agents/**'
git status --short
```

Do not submit remotely while the worktree is dirty. Do not commit restricted data, patient-level predictions, checkpoints, weights, or private traces.

### 2. Verify remote identities before any data or GPU command

Use only the approved 319 alias and verify the following locations with read-only checks:

- Harness: `/root/zhb/medrec-research`
- SafeDrug checkout: `/root/zhb/SafeDrug` at `8deee38cfdb2a38882377ff95cce5922d6d9e8d6`
- MoleRec checkout: `/root/zhb/MoleRec` at `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`
- External data root: `/root/zhb/medrec-data`

The harness checkout must match the clean local revision. The external data root must resolve outside the harness checkout. The model checkouts must be clean at their declared revisions. The primary `319-lab` alias must be tried first; use `319-lab-via-server` only after that preflight fails. If any identity differs, stop; do not substitute a nearby checkout or snapshot.

### 3. Build and prove `medrec-molerec-table1`

Build on 319 from `environments/molerec-table1.yml` using repository- or command-scoped China mirrors with TLS verification enabled. Use official PyTorch/PyG HTTPS endpoints only for exact missing binary artifacts, and record every fallback. Do not modify global Conda, pip, or uv configuration.

After the build succeeds, freeze the explicit Linux declaration and its identity:

```bash
conda env create -f environments/molerec-table1.yml
conda list --explicit -n medrec-molerec-table1 > environments/molerec-table1-linux-64.lock
sha256sum environments/molerec-table1-linux-64.lock
```

Record the actual 64-character hash in the registry only after the declaration, lock, and runtime output agree. Until then, the registry is intentionally not 319-verified.

Run environment-only probes for both explicit programs:

```bash
conda run -n medrec-molerec-table1 python baselines/safedrug_archived.py safedrug \
  --upstream-root /root/zhb/SafeDrug \
  --mode probe --probe-scope environment

conda run -n medrec-molerec-table1 python baselines/molerec.py molerec-embedding \
  --upstream-root /root/zhb/MoleRec \
  --mode probe --probe-scope environment
```

The full probe must additionally prove the new snapshot, imports, CUDA allocation, RDKit BRICS, PyG extensions, and every declared architecture/profile before U6 admission.

### 4. Build and publish the additive eight-file snapshot

First verify the accepted c721 common snapshot and resolve the MoleRec directory containing the three canonical molecular files. Do not infer that directory from a filename; record the read-only resolution in the ignored attempt trace.

Run the staging command only after both source directories pass the input checks:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec stage-molerec-snapshot \
  --common-snapshot /root/zhb/medrec-data/snapshots/safedrug-paper-c721-ijcai21 \
  --molerec-data-directory <directory-containing-molerec-assets> \
  --staging-directory /root/zhb/medrec-data/.staging/molerec-table1-<attempt-id> \
  --snapshot-directory /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --proof /root/zhb/medrec-data/.staging/molerec-table1-<attempt-id>/staging-proof.json
```

The builder must prove ordered vocabulary equality, mask and substructure-column alignment, matrix invariants, common counts, both consumer contracts, and byte equality of `idx2SMILES.pkl` and `idx2drug.pkl`. Any failed bridge rejects the candidate; do not patch the source or trim visits.

### 5. Run seven fresh non-evidence smokes

For a new successor attempt, run the seven registry lanes once with a shared new attempt ID and the provisional mapping chosen for the smoke gate:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec reproduce-smoke all \
  --gpus 0,1,2,3,4,5,6 \
  --attempt-id <attempt-id>
```

Each result/status pair must be v2, identity-consistent, `non_evidence: true`, and free of test artifacts. A smoke is not formal evidence and cannot authorize a different snapshot, source, environment, seed, or parameter.

### 6. Profile the server and freeze the schedule

Run P1 isolated one-epoch architecture profiles and P2 seven-lane concurrency profiles while GPU 7 remains idle. Capture wall time, peak memory, utilization, temperature/throttle state, CPU pressure, I/O wait, NUMA placement, and interference notes. Freeze the lower measured makespan mapping only if it passes all isolation and resource gates; otherwise use the safe measured alternative. Persist the selected mapping and its tie resolution in the ignored attempt ledger.

### 7. Train seven lanes once

After the final clean harness revision, environment identity, snapshot proof, smoke gate, and schedule are frozen, submit the seven lanes in registry order with the selected mapping. The current read-only schedule artifact is `/root/zhb/medrec-data/runtime/reproduction-prep/u7-schedule.json`; it is bound to the old harness revision and cannot authorize this code revision until re-accepted. The accepted mapping recorded there is schedule B: GPU order `3,4,5,6,1,2,0`, with GPU 7 reserved and CPU sets `12-15,44-47`, `16-19,48-51`, `20-23,52-55`, `24-27,56-59`, `4-7,36-39`, `8-11,40-43`, and `0-3,32-35` in registry order.

```bash
rtk proxy /opt/homebrew/bin/uv run medrec reproduce all \
  --gpus 3,4,5,6,1,2,0 \
  --schedule /path/to/reaccepted-u7-schedule.json \
  --attempt-id <attempt-id>
```

The controller-issued identity must bind attempt, lane, scientific baseline, program, profile, harness revision, model revision, preprocessing revision, snapshot, environment hash, mode, and submission ID. Each lane receives one training submission and a unique run directory. Do not tune, retry, substitute a checkpoint, or reuse the historical attempt.

### 8. Admit the GPU 7 evaluation queue

Create the persisted queue with GPU 7 reserved. Admit non-SafeDrug tests only after their finalized training pair is identity-valid. Admit a SafeDrug test only after all three SafeDrug training candidates are terminal and a valid `selection.json` selects that lane. The production admission command resolves the attempt-owned training artifact and reopens normal or recovered evidence before appending one queue entry:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec admit-evaluation \
  --queue runtime/reproduction/<attempt-id>/evaluation-queue.json \
  --attempt-root runtime/reproduction/<attempt-id> \
  --lane-id <lane-id> \
  --scientific-baseline-id <scientific-baseline-id> \
  --training-artifact-id <attempt-relative-result.json> \
  --test-submission-id <test-submission-id> \
  [--selection runtime/reproduction/<attempt-id>/selection.json]
```

The queue must reject duplicate lanes/submissions, preserve FIFO order, serialize GPU 7, and leave terminal entries untouched across restart or recovery.

Mark the two non-selected SafeDrug candidates `not_tested_by_design`. A running queue entry may be requeued only after the operator proves its process is dead; never replay a completed, failed, or blocked entry.

### 9. Run five serial tests and audit

Run the exact upstream ten-round test procedure serially on GPU 7 for RETAIN, LEAP, GAMENet, the selected SafeDrug lane, and MoleRec. Recompute each summary from ten raw aggregate rounds using population standard deviation. Then run the additive Table 1 audit:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec audit-molerec-table1 \
  --ledger runtime/reproduction/<attempt-id>/molerec-table1-ledger.json \
  --retain-result runtime/reproduction/<attempt-id>/molerec-retain/test/result.json \
  --leap-result runtime/reproduction/<attempt-id>/molerec-leap/test/result.json \
  --gamenet-result runtime/reproduction/<attempt-id>/molerec-gamenet/test/result.json \
  --safedrug-result runtime/reproduction/<attempt-id>/molerec-safedrug-selected/test/result.json \
  --molerec-result runtime/reproduction/<attempt-id>/molerec-embedding/test/result.json \
  --selection runtime/reproduction/<attempt-id>/selection.json \
  --output runtime/reproduction/<attempt-id>/molerec-table1-audit-packet.json
```

The audit reopens finalized sibling artifacts, checks all 25 inclusive mean ± 2 standard-deviation intervals, checks the four MoleRec/SafeDrug directions, and reports all four axes. Do not promote the packet to Git until Codex reviews its public-safe contents.

## Stop Conditions

Stop before formal training or testing when any of these occurs: source/environment/snapshot identity mismatch, dirty or changed code after freeze, failed program probe, missing or mismatched input, failed bridge check, incomplete smoke pair, missing SafeDrug candidate, invalid selection, queue collision, invalid recovery premise, or any attempt to use the old attempt's checkpoints/logs/metrics.

Do not treat local synthetic checks or recovered training artifacts as a completed five-model reproduction. U10 progress is limited to the bounded running-status heartbeat and truthful documentation. Removing the historical `medrec-safedrug-archived` environment requires the separate terminal authorization and exact-prefix checks in the plan.
