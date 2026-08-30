# MoleRec Table 1 Five-Model Reproduction Playbook

This playbook is the operator gate for the reproduction defined by `docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md`. It is not evidence of execution. As of 2026-08-29, attempt `formal-20260828-a09fcab-u8-b` is `formal_incomplete`: its seven source lanes retain one validated immutable recovery sibling each, but its first formal RETAIN test finalized `failed` / `test_failed`. Do not claim another test, retry RETAIN, or run the final audit for this attempt.

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

The clean continuation gate passed at revision `c4fc4d8408ce3119a02813525e17435a9ba102ec`. Validation-only SafeDrug selection chose `molerec-safedrug-lr-5e-4`, the exact five-entry queue was published, and RETAIN was the only claimed test. That test failed before ten-round evaluation because the recovered invocation used the recovery directory basename rather than the original training-run basename.

The failed pair, queue, ledger, selection, preregistration, schedules, and seven recovered training results are immutable evidence. The current attempt is closed to further claims. The local invocation correction binds the original training-run model name and exposes its validated checkpoint through the basename-only upstream namespace; it is for a separately authorized future attempt and does not authorize replay or relabel this one. The old `formal-20260826-025500` attempt remains immutable historical evidence and is not reusable successor evidence.

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

Do not run this section for attempt `formal-20260828-a09fcab-u8-b`; its seven training lanes and recovery siblings are already frozen. The exact schedule B allocation was additively reaccepted without training. The following command is retained only for a separately authorized fresh attempt after all preceding gates pass.

```bash
rtk proxy /opt/homebrew/bin/uv run medrec reproduce all \
  --gpus 3,4,5,6,1,2,0 \
  --schedule /path/to/reaccepted-u7-schedule.json \
  --attempt-id <attempt-id>
```

The controller-issued identity must bind attempt, lane, scientific baseline, program, profile, harness revision, model revision, preprocessing revision, snapshot, environment hash, mode, and submission ID. Each lane receives one training submission and a unique run directory. Do not tune, retry, substitute a checkpoint, or reuse the historical attempt.

### 8. Admit the GPU 7 evaluation queue

For a separately authorized attempt, first use `admit-reproduction-continuation` to reopen all seven immutable training pairs and publish an additive schedule. Then use `prepare-molerec-table1-evaluation` to perform validation-only SafeDrug selection, publish the prospective Comparison preregistration, mark both non-selected candidates `not_tested_by_design`, and create the exact five-entry queue. Both commands require all seven `--training-artifact LANE_ID=RELATIVE_RESULT_JSON` arguments.

```bash
rtk proxy /opt/homebrew/bin/uv run medrec admit-reproduction-continuation \
  --source-schedule <frozen-schedule.json> \
  --source-schedule-id <immutable-source-schedule-id> \
  --attempt-root runtime/reproduction/<attempt-id> \
  --attempt-id <attempt-id> \
  --training-artifact <lane-id>=<attempt-relative-result.json> \
  --output <continuation-schedule.json> \
  --dry-run

rtk proxy /opt/homebrew/bin/uv run medrec prepare-molerec-table1-evaluation \
  --schedule <continuation-schedule.json> \
  --attempt-root runtime/reproduction/<attempt-id> \
  --attempt-id <attempt-id> \
  --training-artifact <lane-id>=<attempt-relative-result.json> \
  --state-root runtime/reproduction/<attempt-id>/evaluation-state
```

The continuation dry-run detects schedule, attempt, or evidence drift; if it fails, publish nothing and do not construct a test. Repeat both `--training-artifact` options exactly seven times in registry order. Run the continuation command without `--dry-run` only after reviewing the summary.

Claim exactly one queue entry, execute only the returned frozen command, and finalize its pair before another claim:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec claim-molerec-table1-evaluation \
  --state-root runtime/reproduction/<attempt-id>/evaluation-state \
  --attempt-root runtime/reproduction/<attempt-id>

rtk proxy /opt/homebrew/bin/uv run medrec finalize-molerec-table1-evaluation \
  --state-root runtime/reproduction/<attempt-id>/evaluation-state \
  --attempt-root runtime/reproduction/<attempt-id>
```

The queue rejects duplicate lanes/submissions, preserves FIFO order, serializes GPU 7, and leaves terminal entries untouched. A failed or blocked entry closes the attempt to every later claim.

Mark the two non-selected SafeDrug candidates `not_tested_by_design`. A running queue entry may be requeued only after the operator proves its process is dead; never replay a completed, failed, or blocked entry.

### 9. Run five serial tests and audit

Run the exact upstream ten-round test procedure serially on GPU 7 for RETAIN, LEAP, GAMENet, the selected SafeDrug lane, and MoleRec. Recompute each summary from ten raw aggregate rounds using population standard deviation. Only after all five finalized pairs validate may the prepared-state audit run:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec audit-prepared-molerec-table1 \
  --state-root runtime/reproduction/<attempt-id>/evaluation-state \
  --attempt-root runtime/reproduction/<attempt-id> \
  --output runtime/reproduction/<attempt-id>/molerec-table1-audit-packet.json
```

The audit reopens finalized sibling artifacts, checks all 25 inclusive mean ± 2 standard-deviation intervals, checks the four MoleRec/SafeDrug directions, and reports all four axes. It must reject the current attempt because its RETAIN entry failed and four pairs are absent. Do not promote any packet to Git until Codex reviews its public-safe contents.

## Stop Conditions

Stop before formal training or testing when any of these occurs: source/environment/snapshot identity mismatch, dirty or changed code after freeze, failed program probe, missing or mismatched input, failed bridge check, incomplete smoke pair, missing SafeDrug candidate, invalid selection, queue collision, invalid recovery premise, or any attempt to use the old attempt's checkpoints/logs/metrics.

Do not treat local synthetic checks or recovered training artifacts as a completed five-model reproduction. U10 progress is limited to the bounded running-status heartbeat and truthful documentation. Removing the historical `medrec-safedrug-archived` environment requires the separate terminal authorization and exact-prefix checks in the plan.
