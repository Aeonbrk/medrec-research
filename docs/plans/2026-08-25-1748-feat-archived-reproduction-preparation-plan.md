---
title: Prepare the SafeDrug Archived Four-Model Reproduction
type: feat
date: 2026-08-25
status: accepted
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
origin: docs/plans/2026-08-23-archived-single-baseline-plan.md
deepened: 2026-08-25
---

# Prepare the SafeDrug Archived Four-Model Reproduction

## Goal Capsule

Make the archived SafeDrug four-model program ready for a later formal IJCAI 2021 Table 2 reproduction. The implementation and remote execution covered here end only after a modern 319 environment, a paper-matching archived dataset snapshot, and one non-evidence training epoch for each of GAMENet, SafeDrug, RETAIN, and LEAP have passed their gates.

Gemini is the intended executor. It must stop with a public-safe preparation packet in `runtime/reproduction-prep/<prep-id>/go-no-go.json` whose `aggregate_state` is `awaiting_human_go_no_go` and whose `formal_training_authorized` value is `false`. It must not launch a 50-epoch training job or an upstream ten-round test.

## Product Contract

All `A`, `R`, `AE`, `KTD`, and `U` identifiers are plan-local. The origin plan remains the scientific decision history through its named B0-B3 blocks; it is not the source of these identifiers and no implicit ID mapping exists.

### Actors

- **A1 — Research owner:** authorizes the scientific target, source authority, remote code replacement boundary, and later formal-training decision.
- **A2 — Execution agent:** implements the preparation path, performs the approved 319 operations, monitors every smoke lane, and leaves durable state for review.
- **A3 — Review agent:** inspects the local diff and public-safe preparation evidence after Gemini stops at the preparation boundary and before recommending a later go or no-go decision.
- **A4 — 319 host:** holds the authorized source data, isolated baseline environment, archived source checkout, generated dataset snapshot, and restricted runtime artifacts.

### Requirements

- **R1:** Work in Reproduction Mode only. Comparison Mode, Prediction Adapters, and Unified Research Protocol comparison records are outside this phase.
- **R2:** Treat SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` as scientific authority for all four models. SafeDrug master/main is an engineering reference only.
- **R3:** Preserve the archived branch's recorded learning rates, ordered split, thresholds, losses, model behavior, validation-Jaccard checkpoint rule, and eventual ten test bootstraps even where paper prose differs.
- **R4:** Permit only two audited, run-scoped source transformations: the existing exact reversible `--Test` default change for training, and, in smoke mode only, an exact reversible 50-to-1 epoch change. Any other archived-source compatibility edit is a blocker.
- **R5:** Regenerate a new external archived dataset snapshot from the authorized 319 inputs and require exactly 6,350 patients, 14,995 visits, 131 medications, 448 DDI pairs, and 491 molecular substructures before smoke execution.
- **R6:** Use a modern isolated Linux environment, beginning with Python 3.11, PyTorch 2.2.2 with CUDA 12.1, NumPy 1.26.4, pandas 2.0.3, SciPy 1.11.4, scikit-learn 1.3.2, RDKit 2023.09.6, dill 0.3.7, and dnc 1.1.0. The frozen environment must be proved on the RTX 3090 host, not accepted merely because dependency resolution succeeds.
- **R7:** Give each of `gamenet`, `safedrug`, `retain`, and `leap-safedrug` one independent one-epoch smoke that reaches forward pass, backward pass, optimizer step, validation/checkpoint emission, and a terminal smoke record.
- **R8:** Smoke artifacts are non-evidence. They may contain diagnostic training/validation logs and a smoke-only checkpoint under their restricted run roots, but they must not run the test branch, publish `result.json`, enter Table 2 comparison, or become checkpoint-selection candidates for a formal run.
- **R9:** Local Git state is the code authority. The executor may replace the remote harness checkout and SafeDrug checkout to make them exact, but must not overwrite or delete remote data, runs, checkpoints, or weights.
- **R10:** All four lanes remain independent. A blocked or failed lane does not cancel the other lanes, and the final packet preserves each lane's terminal state.
- **R11:** Do not add multi-seed training. In the later formal phase, one archived training run per model and ten upstream test bootstraps are required; the bootstrap spread is not training-seed variance.
- **R12:** The later Table 2 numeric gate is all 20 reproduced means within the paper mean plus or minus two reported standard deviations, with SafeDrug-over-GAMENet Jaccard/F1 and SafeDrug-under-LEAP DDI checked separately. No post-test retuning, seed changes, or checkpoint cherry-picking are allowed.
- **R13:** The current execution ends before formal training and exposes an explicit human go/no-go boundary.

### Key Decisions

1. **Archived is the sole scientific source.** (session-settled: user-directed — chosen over SafeDrug master as scientific authority: upstream identifies archived as the paper-reproduction branch, while master changes cohort, medication vocabulary, preprocessing, and model behavior.) Governs R2-R4.
2. **Recorded archived code semantics win over conflicting paper prose.** (session-settled: user-approved — chosen over normalizing implementation details to prose: Reproduction Mode preserves the authoritative upstream execution behavior.) Governs R3-R4.
3. **Preparation stops before the first formal job.** (session-settled: user-directed — chosen over starting complete training immediately: the owner wants all prerequisites and four short smokes reviewed first.) Governs R7-R8 and R13.
4. **Local code may overwrite the two remote code checkouts.** (session-settled: user-directed — chosen over preserving the remote checkouts: local progress is authoritative and restricted data and run artifacts are explicitly outside the replacement boundary.) Governs R9.
5. **The eventual study uses one training run per model.** (session-settled: user-directed — chosen over multi-seed training: the reproduction target is archived source behavior and its ten test bootstraps, with their uncertainty interpreted correctly.) Governs R11-R12.

### Acceptance Examples

- **AE1 — Ready:** all local gates pass; the remote harness and upstream source match their intended revisions; the recreated environment matches its explicit lock; B0 counts match; four smoke records report one observed epoch and a checkpoint; no smoke run contains `result.json`; the final state is `awaiting_human_go_no_go` with formal training disabled.
- **AE2 — Environment blocker:** Conda resolves the candidate environment, but dnc cannot construct and execute a minimal forward pass under PyTorch 2.2.2. Preparation stops at `blocked_environment`; package pins may be revised, but archived model source is not patched.
- **AE3 — Data blocker:** archived preprocessing completes but produces 15,032 visits or 112 medications. All smoke submission is blocked; the mismatch is investigated in preprocessing and mapping lineage rather than compensated in model code.
- **AE4 — Partial smoke failure:** SafeDrug smoke fails while the other three complete. The surviving lanes remain completed, SafeDrug is recorded as failed with its public-safe reason, and the aggregate state is not advanced to `awaiting_human_go_no_go`.
- **AE5 — Boundary violation prevention:** an executor attempts to invoke the formal `reproduce` command during this plan. The attempt is rejected by the plan's stop condition; only `reproduce-smoke` is authorized.

## Planning Contract

### Scope Boundaries

#### In Scope

- Extend the existing archived Reproduction Program with environment/data probe and non-evidence smoke behavior.
- Add a distinct local smoke-submission interface that reuses remote preflight and preserves four-lane independence.
- Declare, prove, explicitly lock, and register the modern 319 baseline environment.
- Update the baseline and 319 playbooks with the preparation state contract and operator sequence.
- Converge the two approved remote code checkouts to local/pinned authority without changing restricted data or prior run artifacts.
- Regenerate the archived external snapshot, pass B0, run and monitor four one-epoch smokes, and assemble the review packet.

#### Out of Scope

- Any formal 50-epoch training, ten-round test execution, Table 2 result analysis, or paper claim conclusion.
- Multi-seed training, hyperparameter search, post-test tuning, or checkpoint selection across runs.
- Comparison Mode qualification, a Prediction Adapter, core metric recomputation, or baseline readiness promotion.
- Treating SafeDrug master/main runs as paper-reproduction evidence.
- Copying source data, patient membership, predictions, checkpoints, weights, pickle files, or raw logs into Git.
- Backup frameworks, migration layers, feature flags, compatibility wrappers, checksums without a behavioral use, or generalized remote-state machinery.

#### Deferred to Follow-Up Work

- A separately authorized formal four-lane reproduction run.
- Ten-round bootstrap validation, Table 2 comparison, headline relationship checks, integrity audit, and result-to-claim work.
- Comparison Mode integration and qualification after Reproduction Mode is complete.

### Assumptions

- All relevant 319 data is authorized. The executor must not ask for authorization again.
- The remote observations collected during planning are stale by definition; the executor reruns the normal read-only preflight before changing code or submitting smoke lanes.
- The candidate package set in R6 is a starting declaration, not a claimed verified lock. Package pins may change when an observed compatibility failure requires it; scientific source behavior may not.
- GPU indices are selected from the idle physical devices observed immediately before submission.
- A clean immutable local harness revision can be produced through the repository's normal workflow before a real remote launch.
- If the authorized raw inputs needed by archived preprocessing cannot be located on 319, that is a genuine blocker rather than a reason to synthesize or substitute data.

### Key Technical Decisions

1. **KTD1 — Keep one Reproduction Program with three parser-enforced behaviors.** The program accepts `--mode probe|smoke|formal`, with `formal` as the compatibility-preserving default. Probe creates no run root and performs no training; its `--probe-scope environment|full` selector separates data-independent candidate checks from the full six-input/B0 gate. Smoke runs exactly one epoch and has no testing tail; only formal may select the full-run checkpoint, invoke upstream testing, or publish `result.json`. The program defines one canonical six-file input manifest, a four-file B0 subset, and each profile's model-specific subset instead of treating the current four-file `GATE_INPUTS` as the complete contract.
2. **KTD2 — Expose smoke as a separate top-level submission command and make the program probe a protocol.** `medrec reproduce-smoke` reuses lane mapping and remote resource gates but emits smoke sessions prefixed `medrec-smoke-` and program commands containing `--mode smoke`. After source/data/environment identity and GPU-idle checks, `RemoteExecutor` invokes `--mode probe --probe-scope full`, parses one versioned public-safe JSON object, and rejects any nonzero exit, extra output, missing field, failed check, or identity mismatch before tmux launch. The JSON names its scope, baseline/source, B0 counts when full, environment versions/identity, visible GPU identity, and pass/fail results for imports, CUDA tensor execution, RDKit BRICS, dnc forward, and, when full, six pickle loads; executor code must consume this program-owned result rather than duplicate the checks.
3. **KTD3 — Make both source transformations exact, ordered, mode-limited, and jointly reversible.** (session-settled: user-approved — chosen over general source patching: the owner accepted the existing training-mode adaptation and a smoke-only 50-to-1 epoch adaptation, but no compatibility edits to archived scientific source.) Smoke transforms original archived bytes through exactly one training-default substitution and then exactly one epoch substitution; reversing them in the opposite order must reproduce the original bytes. Formal applies only the training-default substitution and can never receive the epoch substitution.
4. **KTD4 — Freeze the modern environment only after it proves the integrated data path.** (session-settled: user-approved — chosen over recreating the paper's PyTorch 1.4 stack: PyTorch 1.4 CUDA builds do not support the RTX 3090's compute capability, while a modern environment is acceptable when the deviation is declared.) First use a named candidate environment for dependency/runtime probes and archived preprocessing into staging. After all six staged inputs load and B0 passes, export the Linux explicit lock, land those exact lock bytes in the local source of truth, recreate the declared environment from that lock, repeat the complete program probe, and only then register the hash of the recreated environment's exact `conda list --explicit` bytes.
5. **KTD5 — Regenerate data additively and publish once.** Preprocessing writes to a staging directory under the same external snapshot parent as the final registry target. After the frozen environment loads all six files and B0 passes, one same-filesystem atomic directory rename publishes the target; file-by-file copying, target merging, and target overwrite are forbidden. An unexpected existing target is a blocker, not permission to delete it.
6. **KTD6 — Make the execution agent the narrow preparation-state owner.** Gemini writes `runtime/reproduction-prep/<prep-id>/state.json` after each material gate from structured program/RemoteExecutor facts and emits `go-no-go.json` only after validating all four remote terminal records. The CLI remains argument parsing, lane orchestration, and public-safe presentation; `RemoteExecutor` owns remote facts; the baseline program owns probe/smoke records. This avoids inventing a generic job database while leaving agent-legible state outside shell history.

#### Exact Smoke Source Contract

The epoch transformation matches the complete line token below once in the selected entrypoint after the training-default transformation. The source must contain exactly one original token and no smoke token before adaptation. The adapted source must contain exactly one smoke token and no original token at that location. Replacing the smoke token with the original token, then reversing the training-default transformation, must reproduce the original entrypoint bytes.

| Baseline | Archived entrypoint | Exact original token | Exact smoke token | Required original occurrences |
| --- | --- | --- | --- | --- |
| `gamenet` | `src/GAMENet.py` | `'    EPOCH = 50\n'` | `'    EPOCH = 1\n'` | 1 |
| `safedrug` | `src/SafeDrug.py` | `'    EPOCH = 50\n'` | `'    EPOCH = 1\n'` | 1 |
| `retain` | `src/Retain.py` | `'    EPOCH = 50\n'` | `'    EPOCH = 1\n'` | 1 |
| `leap-safedrug` | `src/Leap.py` | `'    EPOCH = 50\n'` | `'    EPOCH = 1\n'` | 1 |

The unrelated `'    EPOCH = 100\n'` inside `Leap.py`'s dormant `fine_tune()` function is not part of `main()` and must remain unchanged. The audit source for all five declarations is archived revision `8deee38cfdb2a38882377ff95cce5922d6d9e8d6`.

### High-Level Technical Design

These sketches constrain responsibilities and state transitions, not exact implementation syntax.

#### Component Relationships

```text
local CLI
  -> RemoteExecutor
      -> 319 identity/resource gates
      -> versioned program probe JSON
      -> tmux smoke submission
          -> archived Reproduction Program
              -> pinned SafeDrug source
              -> isolated Conda environment
              -> external dataset snapshot
              -> restricted smoke run root

structured gate/submission facts
  -> Gemini-owned ignored preparation state
      -> Codex review packet
```

#### Preparation Protocol

```text
implement contracts
  -> pass local verification
  -> converge remote code
  -> prove candidate runtime
  -> regenerate staged data
  -> freeze environment and publish gated data
  -> submit four independent smokes
  -> monitor terminal records
  -> assemble go/no-go packet
  -> stop for human review
```

#### Preparation State Machine

```text
planned
  -> implementing
  -> local_verified
  -> remote_code_ready
  -> candidate_environment_ready
  -> data_staged
  -> environment_ready
  -> data_ready
  -> smoke_running
  -> awaiting_human_go_no_go

any active state -> blocked_<gate>
smoke_running    -> partial_smoke_failure
```

`awaiting_human_go_no_go` is terminal for this plan. There is no transition from it to formal training in this artifact.

#### Data Provenance Flow

```text
authorized 319 raw inputs
  -> pinned archived preprocessing
  -> staged canonical six-file manifest
      -> four-file B0 subset
      -> per-profile model-input subsets
  -> frozen-environment structural loads and B0 gate
  -> atomic external snapshot publication
  -> four read-only consumers during smoke

public-safe branch: B0 counts + revisions + environment identity + terminal states
restricted branch: rows + split membership + pickle values + logs + checkpoints
```

#### Program Mode Matrix

| Behavior | Program selector | Training-mode adaptation | Epoch adaptation | Training | Upstream test | Terminal artifact |
| --- | --- | --- | --- | --- | --- | --- |
| Environment probe | `--mode probe --probe-scope environment` | No | No | No | No | One versioned JSON object on stdout; no run or data root |
| Full probe | `--mode probe --probe-scope full` | No | No | No | No | One versioned JSON object including six-input/B0 results; no run root |
| Smoke | `--mode smoke` | Yes | Exact 50 to 1 | One epoch | No | `status.json` and `smoke.json` |
| Formal default | omitted or `--mode formal` | Yes | No | 50 epochs | Ten rounds | Existing `status.json` and `result.json` |

#### Public-Safe Protocol Shapes

The probe writes exactly one compact JSON object and one trailing newline to stdout on success. The top-level object has the following exact fields; unknown or missing fields are invalid.

| Probe field | Type and required value |
| --- | --- |
| `schema_version` | Integer `1` |
| `kind` | String `safedrug_archived_probe` |
| `scope` | String `environment` or `full`, equal to the requested scope |
| `baseline_id` | One of the four registry baseline IDs, equal to the request |
| `source_revision` | The exact archived revision from R2 |
| `environment` | Object with the exact keys `conda_explicit_sha256`, `python`, `pytorch`, `torch_cuda`, `nvidia_driver`, `numpy`, `pandas`, `scipy`, `scikit_learn`, `rdkit`, `dill`, `dnc`, `cuda_visible_device_count`, `gpu_name`, and `gpu_capability`; version and identity fields are non-empty strings, the hash is lowercase SHA-256 text, and the visible-device count is integer `1` |
| `checks` | Object with `imports`, `cuda_tensor`, `rdkit_brics`, and `dnc_forward`; the last three equal `passed`, while `imports` has exactly the registry-declared module names and every value equals `passed` |
| `inputs` | `null` for environment scope; for full scope, an object with exactly the six registry-declared filenames and every value equal to `passed` |
| `dataset_counts` | `null` for environment scope; for full scope, the exact five integer fields and values from R5 |

A probe failure exits nonzero and does not emit a success object; its diagnostic remains on stderr. `RemoteExecutor` accepts only exit zero, no stderr, exact schema/kind/scope/baseline/source equality, one visible GPU, all checks passed, the full six-input key set and B0 values for full scope, and an environment hash equal to the registry once that identity has been registered. The candidate environment probe records its hash but cannot use an absent registry hash as launch authority.

Smoke mode preserves the existing `status.json` filename but gives its smoke record a versioned shape. A terminal `status.json` has exact fields `schema_version`, `kind`, `state`, `stage`, `started_at`, `finished_at`, and `failure_code`: version is integer `1`, kind is `safedrug_archived_smoke_status`, state is `completed` or `failed`, stage is `terminal`, timestamps are UTC strings, and `failure_code` is `null` on completion or a public-safe lowercase `snake_case` code on failure. A completed lane also publishes `smoke.json` with these exact fields:

| Smoke field | Type and required value |
| --- | --- |
| `schema_version` | Integer `1` |
| `kind` | String `safedrug_archived_smoke` |
| `non_evidence` | Boolean `true` |
| `baseline_id` | The requested registry baseline ID |
| `source_revision` | The exact archived revision from R2 |
| `environment_sha256` | The registered recreated-environment identity |
| `dataset_counts` | The exact five integer fields and values from R5 |
| `epochs_requested`, `epochs_observed`, `best_epoch` | Integers `1`, `1`, and `0`, respectively |
| `adaptation` | Object with `training_default` and `epoch_limit`; each contains its exact original token, adapted token, integer occurrence count `1`, and `reverse_verification` equal to `byte-identical` |
| `checkpoint` | Object with integer `epoch` equal to `0`, a run-relative `artifact_id`, and positive integer `size_bytes`; no absolute path or hash |

Gemini owns two ignored aggregate artifacts with schema version `1`: mutable `state.json` has kind `safedrug_archived_preparation_state`, and the terminal handoff snapshot `go-no-go.json` has kind `safedrug_archived_go_no_go`. Both use the same exact remaining fields:

| Aggregate field | Type and required value |
| --- | --- |
| `prep_id` | Non-empty local preparation identifier |
| `aggregate_state` | One preparation-state value defined below |
| `formal_training_authorized` | Boolean `false`; no other value is valid in this plan |
| `next_permitted_action` | One of `implement`, `verify_local`, `converge_remote_code`, `build_candidate_environment`, `regenerate_data`, `freeze_environment`, `publish_data`, `submit_smokes`, `monitor_smokes`, `report_blocker`, or `request_codex_review` |
| `identities` | Object with `harness_revision`, fixed `upstream_revision`, `environment_sha256`, repo-relative `environment_lock`, and registry-relative `dataset_snapshot`; fields not yet proved are `null` |
| `dataset_counts` | `null` before B0 or the exact R5 count object after B0 |
| `dependency_pin_deviations` | Array of objects with `package`, `declared`, `observed`, and `reason`; empty when R6 pins stand |
| `lanes` | Object with exactly `gamenet`, `safedrug`, `retain`, and `leap-safedrug`; each value has `state`, `gpu_index`, `session_id`, `terminal_artifact_id`, and `failure_code` |
| `blocker` | `null` outside a blocked/partial state or an object with public-safe `gate`, `code`, and `summary` strings |
| `updated_at` | UTC timestamp string |

Each lane state is one of `pending`, `submitted`, `running`, `completed`, or `failed`. GPU, session, terminal-artifact, and failure fields are `null` until known; artifact identifiers are registry-relative and never absolute remote paths. Aggregate state is one of `planned`, `implementing`, `local_verified`, `blocked_remote_code`, `remote_code_ready`, `blocked_environment`, `candidate_environment_ready`, `data_staged`, `environment_ready`, `blocked_data`, `data_ready`, `smoke_running`, `partial_smoke_failure`, or `awaiting_human_go_no_go`. A blocked state permits only `report_blocker`; the last two states permit only `request_codex_review`. `go-no-go.json` is emitted only after all four lanes have terminal status, so its aggregate state is exactly `partial_smoke_failure` or `awaiting_human_go_no_go` and all lane fields are resolved. Both files are written atomically from allowlisted structured facts; neither contains a raw log excerpt or absolute remote path.

#### Gate Decisions

| Gate | Pass action | Failure action |
| --- | --- | --- |
| Local contract | Freeze an immutable harness revision | Fix local implementation; do not sync |
| Remote code identity | Continue to environment work | Replace only the approved code checkout, then recheck |
| Candidate runtime probe | Permit staged preprocessing | Adjust dependency pins or stop; do not patch archived source |
| Frozen environment plus data probe | Register recreated-environment identity and publish snapshot | Keep registry unverified and snapshot unpublished |
| B0 dataset counts | Enable smoke submission | Record mismatch and block all smokes |
| Per-lane smoke | Preserve terminal record and continue other lanes | Record lane failure; do not cancel surviving lanes |
| Four-lane aggregate | Emit ready review packet | Emit partial-smoke review packet without formal authorization |

### Research Grounding

- The repository already has one registry-driven program, exact training-mode adaptation, exact B0 count logic, formal checkpoint/test parsing, fail-closed remote preflight, and independent four-lane CLI mapping. The plan extends those seams instead of adding a second architecture.
- The current formal `run_lane` always expects 50 epochs, selects a checkpoint, and starts the upstream ten-round test. It cannot serve as the smoke entry without conflating evidence classes.
- The registry already supports `environment_sha256`, and the remote executor already compares it with the SHA-256 of `conda list --explicit`; no registry schema change is needed.
- The paper-reproduction dataset snapshot and declared Conda environment were absent during the planning preflight. The remote harness and upstream checkouts also did not match their intended clean revisions. These are observations to recheck, not assumptions to bypass.
- PyTorch 2.2.2 publishes a Python 3.11 Linux CUDA 12.1 wheel, and the observed 319 NVIDIA driver is new enough for CUDA 12.1. The unresolved load-bearing risk is the complete archived stack, especially dnc and archived preprocessing APIs, under this package combination.

## Implementation Units

### U1 — Add probe and non-evidence smoke behavior to the archived program

**Requirements:** R2-R8 and R13; Key Decisions 1-3; KTD1 and KTD3.

**Files:** `baselines/safedrug_archived.py`, `tests/unit/test_safedrug_archived_program.py`.

**Depends on:** None.

**Approach:** Preserve the current default formal behavior and dispatch the three parser-validated modes before entering any mode-specific tail. Define the canonical manifest as the registry's six inputs, preserve the current four B0 inputs for count calculation, and preserve each profile's required subset. Both probe scopes return the versioned KTD2 JSON after visible-CUDA tensor, RDKit BRICS, minimal dnc forward, imports, and environment identity checks; full scope additionally requires the dataset root, deserializes and validates the model-consumed structure of all six files, and calculates B0. Smoke must create one run-scoped entrypoint by applying the two KTD3 transformations, parse the log with `expected_epochs=1`, require `best_epoch: 0` and exactly one profile-matching epoch-0 checkpoint, then publish a non-evidence terminal record without entering the formal checkpoint/test/result tail.

**Test scenarios:**

- Happy path: environment scope succeeds without a dataset/run root; full scope requires a canonical six-file synthetic fixture and adds six-load/B0 results to the versioned probe JSON; the same archived-shaped source produces a smoke plan with one requested epoch.
- Profile coverage: all four profiles retain their archived entrypoints, learning rates, required inputs, model names, and checkpoint naming behavior.
- Error path: zero, duplicate, or already-modified epoch declarations fail before a subprocess starts; reversing the composed smoke transformations in reverse order reproduces the original archived bytes.
- Error path: a missing, unloadable, or structurally invalid `ehr_adj_final.pkl` or `idx2drug.pkl`, any other canonical input failure, B0 mismatch, failed CUDA operation, failed RDKit operation, or failed dnc forward produces a named probe failure.
- Integration path: a stubbed one-epoch log with `best_epoch: 0` and one epoch-0 checkpoint produces `status.json` plus `smoke.json`, reports `non_evidence: true`, `epochs_requested: 1`, `epochs_observed: 1`, and `best_epoch: 0`, and never creates `test.log` or `result.json`.
- Separation path: probe-scope arguments are rejected outside probe mode, full probe rejects a missing dataset root, both probes create no run root, smoke cannot call the formal tail, and formal cannot receive the epoch transformation.
- Formal regression: the unchanged default path still requires 50 training epochs, one selected checkpoint, ten test rounds, and the existing terminal result publication order.

**Verification outcome:** Local tests prove mode separation and source reversibility without importing the remote baseline stack; the formal behavior's existing tests remain green.

### U2 — Add an independent smoke-submission surface

**Requirements:** R1, R7-R10, and R13; Key Decision 3; KTD2 and KTD6.

**Files:** `src/medrec_research/cli.py`, `src/medrec_research/remote_executor.py`, `tests/unit/test_remote_executor.py`, `tests/integration/test_run_cli.py`.

**Depends on:** U1.

**Approach:** Add `medrec reproduce-smoke` with the same one-lane/all-lane GPU contract as `reproduce`. Reuse declaration validation and source/data/environment identity checks, then order dynamic checks as GPU identity/idle, disk capacity, and the program-level `--mode probe --probe-scope full` command. Parse its single versioned JSON object into structured preflight facts and compare its source, environment, GPU, environment scope, six-input, and B0 fields with the declared/observed values. Submit `--mode smoke` through a smoke-specific executor method and `medrec-smoke-<baseline>-...` session ID. Do not route smoke through `run_baseline`, and do not weaken the verified-environment requirement.

**Test scenarios:**

- Happy path: one-lane and four-lane dry runs produce complete commands containing `--mode smoke`, smoke-specific session IDs, and no implicit fall-through to the formal path.
- Mapping edge: `all` maps the four archived IDs to exactly four unique GPUs in the existing order.
- Error path: missing environment identity, source mismatch, busy GPU, insufficient disk, nonzero/invalid/identity-mismatched probe JSON, or incoherent GPU arguments prevent tmux launch; tests assert a distinct program-probe gate before `tmux-launch`.
- Independence path: one synthetic lane submission failure does not prevent attempts for the remaining three lanes, and the CLI exits nonzero with all four states represented.
- Integration path: real smoke submission reuses every existing remote preflight gate, creates smoke-specific session IDs, and launches the Reproduction Program's smoke behavior; the existing `reproduce` output and formal command remain unchanged.

**Verification outcome:** CLI and executor tests distinguish planned/submitted smoke work from formal reproduction and prove that no smoke request can silently become a formal request.

### U3 — Declare the candidate and frozen 319 environment contract

**Requirements:** R6 and R9; KTD4.

**Files:** `environments/safedrug-archived.yml`, `environments/safedrug-archived-linux-64.lock`, `environments/README.md`, `baselines/registry.toml`.

**Depends on:** U1.

**Approach:** Add the direct candidate package declaration from R6 with CUDA/PyTorch installation sources made explicit. Keep the explicit lock absent until the candidate has completed dependency/runtime checks and produced a six-file staged dataset that passes load/B0. U7 then exports and lands the lock, recreates `medrec-safedrug-archived` from those exact bytes, runs the complete program probe, hashes that recreated environment using the existing executor convention, and only then adds `environment_sha256`. Candidate or pre-recreation hashes are never registered. Keep all four models on one environment unless an observed, irreducible dependency conflict proves a split is necessary; such a split is outside this plan and must be surfaced.

**Test scenarios:**

- Happy path: the candidate resolves on 319, its dependency/runtime checks pass, and U7 later proves that the recreated explicit environment matches the only registered hash.
- Compatibility edge: archived pickles for all six inputs load without reserialization and with the expected structures under the recreated environment.
- Error path: dnc, RDKit, CUDA, archived imports, pickle loading, or environment-hash equality fails; readiness remains blocked and no archived source compatibility patch is introduced.
- Reproducibility path: recreating from the landed explicit lock yields the same package listing and repeats the full data-aware program probe on one visible RTX 3090.

**Verification outcome:** The registry identity refers to a host-proved explicit environment, not a provisional YAML solve.

### U4 — Document the bounded operator workflow and handoff state

**Requirements:** R1, R5, R8-R10, and R13; Key Decisions 3-4; KTD5-KTD6.

**Files:** `docs/playbooks/SAFEDRUG_ARCHIVED_PREPARATION_PLAYBOOK.md`, `docs/playbooks/index.md`, `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md`, `docs/playbooks/BASELINE_INTEGRATION_PLAYBOOK.md`, `docs/START_HERE.md`.

**Depends on:** U1-U3.

**Approach:** Add one focused preparation playbook, linked from the existing navigation. It must state the source authority, authorized-data assumption, exact remote code replacement boundary, candidate-data-lock-recreation sequence, atomic snapshot publication, the versioned program probe contract, probe/smoke/formal distinctions, and the hard stop before formal training. Formal reproduction procedures remain deferred. Define the Gemini-owned runtime-state schema and update points, including public-safe field allowlists, lane states, next permitted action, and resume from the last passed gate; make clear that CLI/program/executor produce facts but do not own the aggregate state. Update existing playbooks only where their current wording would conflict with this approved preparation path.

**Test expectation:** None — documentation-only unit. Verify links, command names, mode boundaries, and Markdown syntax.

**Verification outcome:** A fresh executor can start at `docs/START_HERE.md`, reach one canonical procedure, and identify the next permitted action from `runtime/reproduction-prep/<prep-id>/state.json` without reading shell history.

### U5 — Pass local gates and converge the approved remote code checkouts

**Requirements:** R2, R4, R9, and R13; Key Decisions 1 and 4.

**Files:** All files changed by U1-U4; runtime state at `runtime/reproduction-prep/<prep-id>/state.json`.

**Depends on:** U1-U4.

**Approach:** Run the targeted tests first, then the repository completion checks. Produce a clean immutable local harness revision through the normal repository workflow. Before any remote write, prove each approved target with its canonical path, Git top-level, current revision/status, and non-overlap with the resolved external data root; announce that uncommitted remote code will be discarded and Git/local history is the recovery source. Converge only the proved remote harness checkout and pinned SafeDrug checkout, without preserving either as an alternate authority and without touching data, run, checkpoint, weight, or environment roots. Record `remote_code_ready` only when the remote harness revision equals local and SafeDrug is clean at the archived revision.

**Test scenarios:**

- Happy path: both remote code checkouts become clean and exact while all external research artifact roots retain their pre-operation existence and paths.
- Stale-code path: the remote harness is dirty or at another revision; only that checkout is replaced, then the standard revision/cleanliness checks pass.
- Error path: a canonical target, Git top-level, or resolved data-root boundary is not exactly the approved one; stop before mutation and record `blocked_remote_code`.
- Partial-write path: a code-only replacement fails after mutation; recover only that checkout from the already recorded local/pinned revision and repeat identity checks, without touching external artifacts.
- Integration path: a smoke dry run generated from the clean local revision names the same remote harness revision and pinned upstream revision verified by preflight.

**Verification outcome:** Code identity is unambiguous and the preparation state contains only public-safe revisions and gate outcomes.

### U6 — Build and prove the candidate modern environment

**Requirements:** R2-R6 and R9; KTD3-KTD4.

**Files:** `environments/safedrug-archived.yml`, `environments/safedrug-archived-linux-64.lock`, `environments/README.md`, `baselines/registry.toml`, runtime state at `runtime/reproduction-prep/<prep-id>/state.json`.

**Depends on:** U5.

**Approach:** Create the candidate environment only on 319. Resolve observed dependency failures by changing environment pins within R6's scientific boundary. Run `--mode probe --probe-scope environment` to check all archived/module imports, Python/PyTorch/CUDA versions, one selected visible RTX 3090 tensor operation, RDKit BRICS, and minimal dnc forward without requiring a dataset. Record `candidate_environment_ready`, not `environment_ready`; do not export/register the final identity until U7 proves staged real-input loading and B0 under the candidate.

**Test scenarios:**

- Happy path: the candidate passes every data-independent runtime check and is permitted to run archived preprocessing into staging.
- Driver edge: CUDA reports exactly one selected visible RTX 3090 and executes a real tensor operation; a CPU-only or multi-visible-device probe fails.
- Dependency edge: an adjusted direct dependency pin fixes an observed API/binary issue while archived source bytes remain unchanged.
- Error path: import, CUDA, dnc, RDKit, or archived preprocessing startup fails; state remains `blocked_environment` and U7 does not start.

**Verification outcome:** The candidate's exact direct pins and observed Python/PyTorch/CUDA/driver/GPU identities are recorded for U7, but no candidate hash enters the registry.

### U7 — Regenerate data, freeze the environment, and publish the integrated pair

**Requirements:** R2-R5, R8-R10; Key Decisions 1-2 and 4; KTD5.

**Files:** `environments/safedrug-archived-linux-64.lock`, `baselines/registry.toml`, `baselines/safedrug_archived.py`, runtime state at `runtime/reproduction-prep/<prep-id>/state.json`; restricted generated files remain outside Git under the registry-declared data root.

**Depends on:** U6.

**Approach:** Use the pinned archived preprocessing under the candidate environment and write all canonical inputs into a new staging directory under the final snapshot's external parent. Deserialize and structurally validate every one of the six files, including `ehr_adj_final.pkl` and `idx2drug.pkl`, and calculate B0 from its four owning inputs. After candidate success, export the candidate's Linux explicit lock, land those exact bytes in a clean local harness revision, resync them, recreate the declared environment from the checked-in lock, and rerun the complete versioned program probe against staging. Compute the recreated environment hash, add only that hash to the registry, produce/resync the next clean harness revision, and require `RemoteExecutor.preflight` to observe the same value. Finally publish staging with one same-parent atomic directory rename after proving the target absent; do not copy files into the target, reuse master/main data, or reserialize inputs.

**Test scenarios:**

- Happy path: all six files are newly generated, load under both candidate and recreated locked environments, produce every exact R5 count, and are atomically published once the recreated environment identity is registered and observed.
- Lineage edge: a master/main-shaped 15,032-visit or 112-medication snapshot is rejected even if model imports succeed.
- Error path: missing raw input, preprocessing failure, missing/unloadable/structurally invalid `idx2drug.pkl` or any other output, shape mismatch, or count mismatch leaves staging unpublished and sets a specific `blocked_data` state.
- Environment-freeze path: a candidate hash is proposed for registration, the lock has not been landed/resynced, recreation differs, the complete staging probe fails, or post-registry preflight observes another hash; state remains `blocked_environment` and publication/smoke are forbidden.
- Existing-target path: an unexpected registry target already exists; stop and report it rather than deleting, merging, or silently reusing it.
- Publication path: the target is absent and staging shares its filesystem parent; one atomic rename makes the complete snapshot visible. A rename failure leaves no partial target, preserves staging for diagnosis, and blocks smoke.
- Integration path: after publication, the target directory identity is confirmed and each lane's standard preflight consumes a successful full-scope program probe before any smoke session is created.

**Verification outcome:** The state advances through `environment_ready` to `data_ready` only when the locked recreated environment, registered hash, final atomic snapshot, six-file structural loads, and public-safe B0 counts agree; every restricted value remains on 319 outside Git.

### U8 — Run four one-epoch smokes and assemble the Codex review packet

**Requirements:** R1, R7-R13; Key Decisions 3 and 5; KTD2-KTD3 and KTD6.

**Files:** Runtime state at `runtime/reproduction-prep/<prep-id>/state.json` and `runtime/reproduction-prep/<prep-id>/go-no-go.json`; restricted smoke roots remain outside Git.

**Depends on:** U7.

**Approach:** Select four idle GPUs and submit all four independent lanes through `medrec reproduce-smoke all`. Monitor each `medrec-smoke-` session and its terminal files until all lanes finish or fail; a submission return or vanished tmux session is not completion. For each lane validate `epochs_requested: 1`, `epochs_observed: 1`, `best_epoch: 0`, exactly one profile-matching epoch-0 checkpoint, non-evidence markers, absence of the test stage/`test.log`/`result.json`, and exact shared source/environment/data identities. Gemini writes aggregate state only after reading and validating the remote terminal records. After all four lanes are terminal, emit `go-no-go.json` with `awaiting_human_go_no_go` when all pass or `partial_smoke_failure` when any lane fails. Earlier environment/data blockers leave only `state.json`. Always set `formal_training_authorized` to `false` and stop.

**Test scenarios:**

- Happy path: four lanes each report one requested/observed epoch, `best_epoch: 0`, one epoch-0 checkpoint, terminal completion, and no formal result/test artifact; aggregate state becomes `awaiting_human_go_no_go`.
- Independence path: one lane fails during backward or checkpoint validation while the other three reach terminal completion; all four states are preserved and the aggregate state is `partial_smoke_failure`.
- Identity edge: a lane's source revision, environment hash, or B0 counts differ from the accepted shared values; that lane is rejected even if its process exits zero.
- Boundary path: any smoke root contains `test.log`, ten-round metrics, or `result.json`; the packet records a boundary violation and cannot become go/no-go ready.
- Monitoring path: tmux exits before a terminal status appears; the lane is failed rather than inferred successful from session disappearance.

**Verification outcome:** Codex receives the local diff plus one public-safe packet containing harness/upstream revisions, environment identity and deviations, B0 counts, all four lane IDs/GPU IDs/terminal states/registry-relative artifact identifiers, `formal_training_authorized: false`, and no absolute remote path or restricted content.

## System-Wide Impact

- **Reproduction Program:** gains probe and smoke behavior while its formal default and scientific profiles remain unchanged.
- **CLI:** gains one explicit top-level command; existing `reproduce` callers and JSON shape remain stable.
- **Remote execution:** reuses current host selection, source/environment/data/GPU/disk gates, tmux behavior, and lane independence. The new parsed program-probe gate replaces the shallow import-only assurance and returns structured facts without duplicating baseline checks in the executor.
- **Registry:** uses its existing environment identity field; no schema migration or readiness promotion occurs.
- **Environment:** adds one external-baseline declaration and one Linux lock without changing the Python 3.11 Homebrew `uv` core.
- **Data:** creates one external archived snapshot. Existing master/main datasets and historical runs remain untouched and excluded.
- **Runtime state:** Gemini owns a narrowly scoped ignored handoff directory assembled from program and executor facts. It does not become accepted research evidence, CLI-owned product state, or a generalized job database.
- **Documentation:** adds the canonical archived procedure and reconciles existing baseline/319 guidance with the approved code-overwrite boundary.
- **Failure propagation:** local failure blocks sync; environment failure blocks data/smoke; B0 failure blocks every smoke; lane smoke failure is isolated but blocks the aggregate go/no-go-ready state.

## Verification Contract

### Local Gates

Run targeted proof while implementing:

```bash
rtk proxy /opt/homebrew/bin/uv run pytest tests/unit/test_safedrug_archived_program.py tests/unit/test_remote_executor.py tests/integration/test_run_cli.py
```

Before the first real remote operation and again after registering the environment identity, run:

```bash
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
markdownlint '**/*.md' --ignore '.agents/**'
```

The specific failures detected are program-mode regression, formal/smoke command confusion, preflight bypass, registry parse/identity drift, Python quality failure, or broken documentation. Any failure is fixed before remote progression.

### Remote Preparation Gates

1. Before remote code mutation, both canonical targets are proved to be the approved Git roots and outside the external data root. After convergence, the harness checkout is clean at the exact local immutable revision and SafeDrug is clean at the archived revision.
2. The candidate environment passes data-independent runtime checks, then generates a staged canonical six-file dataset whose four B0 inputs produce exact counts.
3. The declared environment is recreated from the landed `environments/safedrug-archived-linux-64.lock`; the recreated environment's explicit-list hash is the only registered hash; post-resync preflight observes it; and the single-JSON program probe passes imports, all six structural pickle loads, CUDA, dnc, RDKit, GPU identity, and B0.
4. The final external snapshot appears through one same-parent atomic directory rename and contains the same already validated canonical six-file dataset.
5. Four `medrec-smoke-` sessions are monitored to terminal state; every lane reports one requested/observed epoch, `best_epoch: 0`, and one profile-matching epoch-0 checkpoint, and no lane reaches the test stage or publishes formal results.
6. The final local packet uses an allowlist of revisions, environment versions/hash, B0 counts, prep/lane/GPU IDs, terminal states, and registry-relative artifact identifiers. It contains no absolute remote/data/user path, raw row, patient/split identifier, pickle value, prediction, weight, checkpoint content/location, raw log, or credential.
7. No formal `medrec reproduce` submission occurs. This is a direct audit condition, not an inference from absent results.

### Review Handoff

Gemini returns:

- the clean local revision containing the implementation, environment lock, registry identity, and documentation;
- the path to `runtime/reproduction-prep/<prep-id>/go-no-go.json`, or to `state.json` if execution stopped before four terminal smoke outcomes;
- a concise list of any dependency-pin deviations from R6 and why each observed failure required it;
- the four lane IDs and registry-relative terminal artifact identifiers, never absolute remote smoke-root paths;
- confirmation that formal training was not launched.

Codex then reviews the diff, replays the local verification contract, checks the registered environment identity against the packet, inspects the B0 and four smoke terminal contracts, and reports go/no-go findings. Codex does not launch formal training without a new owner instruction.

## Risks and Dependencies

- **dnc compatibility is unresolved.** The mitigation is the explicit construct-and-forward probe plus four real smoke lanes. Environment pins may move; archived source may not.
- **Archived preprocessing may depend on removed library APIs.** Resolve this first through compatible package pins inside the modern environment. If source modification beyond R4 is required, stop and report the exact incompatibility.
- **Environment freezing requires staged local/remote revision convergence.** The lock exists only after candidate plus staged-data proof, and the registry hash exists only after lock recreation. Each landed artifact therefore requires a clean harness revision, resync, and exact-identity check before the next gate; candidate/pre-recreation hashes never become launch authority.
- **Remote state observed during planning may have changed.** The normal preflight decides execution-time truth; the plan does not encode yesterday's GPU choice or disk reading.
- **A 1-epoch smoke can pass while 50 epochs later fail.** This plan proves integration and one optimization/checkpoint cycle only. It makes no convergence or Table 2 claim.
- **Smoke logs contain diagnostic metrics.** Non-evidence classification, the absence of upstream testing/formal `result.json`, and isolation under smoke run roots prevent their accidental scientific use.

## Open Questions

### Resolved During Planning

- The reproduction target is IJCAI 2021 Table 2 in Reproduction Mode.
- Archived, not master/main, is scientific authority; master/main is engineering reference only.
- Archived code resolves paper/code conflicts.
- A modern environment is allowed and its deviations must be declared.
- No multi-seed training is planned.
- Four one-epoch smokes are required before formal training.
- Local code is authoritative over the two remote code checkouts.
- Server data authorization is settled and will not be re-asked.
- Formal training requires a later human go/no-go instruction.

### Deferred to Implementation

- The exact four GPU indices, chosen from the execution-time idle devices.
- Whether direct dependency pins in R6 need adjustment after observed dnc, RDKit, preprocessing, or pickle compatibility failures.
- The prep ID and smoke session IDs, generated at execution time and persisted in runtime state.

No product-level blocker remains. Any need for archived scientific-source modification beyond R4 is an execution blocker, not an implementation choice.

## Sources and References

### Repository Sources

- `docs/plans/2026-08-23-archived-single-baseline-plan.md` — accepted lineage, B0, adaptation, four-model, and paper-comparison decisions.
- `baselines/safedrug_archived.py` — current profiles, source adaptation, B0, formal runner, checkpoint/test parsing, and environment identity behavior.
- `baselines/registry.toml` — one shared program, pinned archived revision, six inputs, external roots, and four IDs.
- `src/medrec_research/remote_executor.py` — remote identity, environment, GPU, disk, and tmux gates.
- `src/medrec_research/cli.py` — current one/all lane mapping and formal submission surface.
- `tests/unit/test_safedrug_archived_program.py`, `tests/unit/test_remote_executor.py`, and `tests/integration/test_run_cli.py` — established contract-test seams.
- `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` and `docs/playbooks/BASELINE_INTEGRATION_PLAYBOOK.md` — remote and baseline operational policy.

### External Primary Sources

- PyTorch previous-version installation matrix: <https://pytorch.org/get-started/previous-versions/>
- NVIDIA CUDA minor-version compatibility: <https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html>
- Conda explicit environment export behavior: <https://docs.conda.io/projects/conda/en/latest/commands/list.html>

## Definition of Done

- U1-U4 are implemented with their test scenarios and documentation complete.
- The repository-wide local verification contract passes at the final immutable local revision.
- The remote harness and archived SafeDrug checkout are clean at their exact intended revisions.
- `environments/safedrug-archived-linux-64.lock` recreates the declared environment; the recreated environment passes the versioned full probe and is the only environment identity recorded in `baselines/registry.toml`.
- The new external archived snapshot is published atomically, contains the canonical six inputs, structurally loads under the frozen environment, and passes every exact B0 count.
- GAMENet, SafeDrug, RETAIN, and LEAP each complete exactly one non-evidence training epoch, report `best_epoch: 0`, and emit one valid epoch-0 smoke checkpoint plus terminal record.
- No smoke lane runs upstream testing or emits `result.json`; no formal 50-epoch job is launched.
- `runtime/reproduction-prep/<prep-id>/go-no-go.json` reaches `awaiting_human_go_no_go`, contains all required public-safe identities and lane outcomes, and sets `formal_training_authorized` to `false`.
- Gemini hands the final revision and packet path to Codex for review.
