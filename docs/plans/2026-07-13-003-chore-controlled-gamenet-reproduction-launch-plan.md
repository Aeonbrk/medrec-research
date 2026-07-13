---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
title: Controlled GAMENet Reproduction Launch
type: chore
date: 2026-07-13
topic: gamenet-reproduction-launch
---

# Controlled GAMENet Reproduction Launch

## Goal Capsule

| Item | Decision |
| --- | --- |
| First lane | GAMENet only, fixed upstream commit `da695b4fc9390882f3a681c82115e81291ae6380`. |
| Scientific scope | MIMIC-III v1.4, Reproduction Mode only. MIMIC-IV and Comparison Mode are out of scope. |
| Seed policy | Runtime-only smoke without source training, then one source-native run at fixed seed `1203`. |
| Checkpoint policy | Select the unique source-saved checkpoint for the source-reported `best_epoch`, which tracks strict Jaccard improvements on `data_eval`; evaluate it only on `data_test`. |
| Execution plane | The Mac is the public-safe harness terminal. Restricted data, source checkout, Conda environment, logs, predictions, models, and run diagnostics remain on 319. |
| Readiness boundary | This source-native single-run lane stays `registered`; neither smoke nor the completed run creates readiness evidence. It never calls `accept-comparison` or claims `comparison_ready`. |

## Scope Boundaries

- Do not rebuild the local repository or overwrite existing user work. Freeze the current reviewed public-safe worktree in one immutable commit before remote deployment.
- Preserve the local `codex/medrec-benchmark-harness` branch. Publish the exact frozen SHA as private remote `main`.
- Do not copy external source, restricted data, patient identifiers, split membership, predictions, weights, logs, keys, private paths, or runtime traces into this repository.
- Do not replace unavailable GAMENet inputs with MIMIC-IV, RxNorm, or another representation. Do not invent a compatible split when upstream semantics cannot be reconstructed.
- Treat the single source-native attempt as Reproduction Characterization only. It cannot establish cross-seed stability, enter the V3 stability policy, advance readiness, or support Comparison Mode.
- SafeDrug, MICRON, and LEAP-SafeDrug do not enter this GAMENet lane. Their fixed-source, dependency, training, checkpoint, and input evidence is evaluated separately; a license-policy exception does not resolve those technical conditions. MoleRec and RETAIN receive read-only evidence work only.

## Preconditions And Stops

Stop the lane and retain only a public-safe Failure Record when any condition below fails:

- frozen local SHA, private remote, dedicated clean 319 checkout, and exact SHA verification;
- restricted data root outside Git, read-only source preservation, copied-data checksum manifest, and required GAMENet ICD, prescription, procedure, and DDI inputs;
- pinned source and MIT license confirmation, reconstructed upstream preprocessing, split, selection, and evaluation semantics, and patient-level non-overlap;
- Python 3.8, PyTorch 1.8, CUDA import, GPU tensor smoke, exported explicit Linux environment lock, and adapter protocol checks;
- one explicitly selected GPU with less than 500 MiB memory in use and zero utilization immediately before launch, enough disk capacity, and a named `tmux` session writing only under the restricted data root.

No run may preempt, terminate, attach to, or otherwise disrupt another user's GPU process. A failed condition is not retried as a success and cannot advance readiness.

## Execution Units

### U1. Record And Freeze Public-Safe State

**Goal:** Record this decision artifact, inspect all current changes, and create one reviewed immutable public-safe commit.

**Files:** `docs/PLANS.md`, this plan, existing modified public-safe files.

**Approach:** Run the full local suite, Ruff, format check, Markdown lint, privacy scan, and `git diff --check`; review the diff before staging intended public-safe files. Commit only after every gate passes. Create a private GitHub repository, set `origin`, and push this exact SHA as `main` without renaming the local branch.

**Verification:** The commit exists locally and remotely; its working tree is clean and its SHA matches the remote `main` tip.

### U2. Establish Restricted Remote Inputs And Upstream Evidence

**Goal:** Prepare a dedicated 319 checkout, repository-external restricted data root, and auditable GAMENet source checkout without importing any restricted artifact into Git.

**Files:** Restricted remote storage only; public-safe Failure Record only on failure.

**Approach:** Clone remote `main` into a non-archive location, verify the SHA and clean tree, create a permission-`0700` data root, copy MIMIC-III v1.4 from its read-only source, and retain a restricted checksum manifest. Clone the fixed GAMENet source under restricted storage and verify commit and MIT license. Recover upstream preprocessing, split, selection, and evaluation behavior before implementation.

**Verification:** Remote preflight reports no source drift; required input categories exist; no patient-level artifact is present in Git or command output.

### U3. Build Isolated Environment And Prediction Adapter

**Goal:** Create a pinned GAMENet Conda environment and a project-owned target-free process adapter while preserving the GAMENet Baseline Core.

**Files:** `environments/gamenet.yml`, `baselines/adapters/gamenet/`, adapter tests, and a public-safe remote-run declaration.

**Approach:** Establish the upstream-supported `dnc` version before creating the environment. Export a restricted explicit Linux lock after Python, PyTorch, CUDA, and GPU tensor checks. The adapter receives no targets, labels, or split membership and emits schema-v1 visit predictions without target or split fields. The project core continues to own targets, vocabulary validation, exact cohort validation, and scoring.

**Verification:** Contract tests cover valid output, target-bearing input or output, incomplete or duplicate visits, unknown medication codes, nonzero exits, timeouts, and private stderr suppression. A remote GPU smoke succeeds only after all environment and adapter gates pass.

### U4. Execute And Characterize Reproduction

**Goal:** Run a runtime-only smoke, then one fixed source-native seed `1203` attempt without test-set selection or undocumented reruns.

**Files:** Restricted remote run roots and logs; public-safe Reproduction Characterization or Failure Record.

**Approach:** Check selected GPU state immediately before each launch, bind one available device, and use a named restricted `tmux` session. The smoke does not invoke source training. For the source-native run, retain the source's fixed `1203` seed, parse its restricted `best_epoch` output, require exactly one `Epoch_{best_epoch}_JA_*.model` checkpoint, then pass that path to the source `--eval` command. The wrapper must fail closed if parsing or checkpoint resolution fails and must not read `data_test` metrics before choosing the path. Preserve all raw outputs remotely. Audit restricted outputs before publishing only aggregate, public-safe characterization observations.

**Verification:** Report the one source-native attempt, including any failure. A successful smoke is a runtime check only and cannot create readiness evidence. The completed attempt remains Reproduction Characterization, cannot establish cross-seed stability, and does not create a Comparison Qualification.

## Verification Contract

| Gate | Pass signal |
| --- | --- |
| Local contract | `pytest`, Ruff lint, Ruff format, Markdown lint, privacy scan, and `git diff --check` pass. |
| Git identity | Local commit, private `main`, and 319 checkout resolve to one SHA with clean trees. |
| Restricted preflight | Data, source, environment, GPU, disk, and adapter checks all satisfy the recorded stop conditions. |
| Scientific boundary | Upstream split and evaluation semantics are reconstructed; patient-level overlap is absent; no semantic substitution occurs. |
| Evidence boundary | Public records contain no restricted artifacts and do not state Comparison Mode acceptance or `comparison_ready`. |
