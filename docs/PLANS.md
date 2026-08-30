# Plans

## Blocked: Five-Model Baseline Readiness

- **Plan**: `docs/plans/2026-08-29-1541-feat-five-model-baseline-readiness-plan.md`.
- **Phase A state**: attempt `formal-20260828-a09fcab-u8-b` is `formal_incomplete`. The exact schedule was reaccepted at clean harness revision `c4fc4d8408ce3119a02813525e17435a9ba102ec`, validation-only SafeDrug selection chose `molerec-safedrug-lr-5e-4`, and the five-entry serial queue was published before testing.
- **Terminal event**: RETAIN, the first and only claimed test, finalized as `failed` / `test_failed` before upstream ten-round evaluation because the recovered-test invocation used the recovery directory basename instead of the original training-run basename. The failed evidence was preserved; no later lane was claimed and no test metric was inferred.
- **Axes**: `execution_integrity = failed`, `paper_point_fidelity = not_evaluated`, `directional_relationships = not_evaluated`, and `artifact_completeness = failed`. No final audit packet exists because the five-pair barrier correctly rejected admission.
- **Phase B state**: not started. The five baselines remain `registered`, with no current-scope Comparison Qualification. The first shared blocker is the missing legal Phase A five-pair audit required before Comparison execution.
- **Suite conclusions**: `engineering_ready = false`, `reproduction_complete = false`, and `research_baseline_ready = false`.
- **Reports**: `research/baseline-preflight/molerec-five-model-reproduction-report.md` and `research/baseline-preflight/five-model-baseline-readiness-report.md`.
- **Authorized continuation**: on `2026-08-30`, the user authorized one additive continuation identity that reuses the seven immutable training/recovery pairs without retraining. It must create new submission IDs and independent test roots, preserve the failed queue, and wait for a clean committed harness plus an idle reserved GPU 7 before launch.

## Completed: MoleRec Finalization Recovery and Conformance

- **Status**: U1–U5 recovery and the later continuation-admission conformance are complete for formal attempt `formal-20260828-a09fcab-u8-b`: all seven source lanes retain one validated immutable recovery sibling. No lane was terminated, duplicated, retrained, or tested during recovery.
- **Plan amendment**: `docs/plans/2026-08-28-1718-fix-molerec-finalization-recovery-plan.md` permits immutable same-attempt finalization from preserved histories and checkpoints. It does not permit retraining, test-based selection, Baseline Core changes, or source-artifact overwrite.
- **Local conformance**: validation-only SafeDrug selection, declaration-owned probes, additive frozen-schedule continuation admission, recovered-test invocation, exact five-entry queue admission, failed-entry terminalization, and the five-pair audit barrier are synthetic-tested. These checks are not scientific evidence.
- **Remote boundary**: The original source artifacts and seven recovery siblings remain immutable. The accepted schedule was additively rebound to clean revision `c4fc4d8408ce3119a02813525e17435a9ba102ec`; the source schedule was not overwritten. The first formal RETAIN test then failed as recorded above, closing the current attempt without a five-model result.

## Blocked: MoleRec Table 1 Five-Model Full Reproduction

- **Status**: The recovery slice for `formal-20260828-a09fcab-u8-b` is complete, but the five-model reproduction is `formal_incomplete`. One finalized failed RETAIN test pair exists; four canonical tests and the final audit do not.
- **Plan**: `docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md` is authoritative for this work.
- **Scientific scope**: RETAIN, LEAP, GAMENet, SafeDrug, and MoleRec use the frozen SafeDrug archived revision `8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, MoleRec revision `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, and preprocessing revision `c7218d0976e5ee5588aeaf5bdbc86b338126bba5`. Five scientific models map to seven 50-epoch training lanes because SafeDrug has three disclosed learning-rate candidates (`1e-5`, `1e-4`, `5e-4`) and validation-only selection.
- **Current contract**: all seven lanes use `medrec-molerec-table1` (Python 3.8.16, PyTorch 1.9.0+cu111, PyG 2.0.3) and the additive `snapshots/molerec-table1-c721-www23` declaration. The executable dataset contract is 6,350 patients, 15,032 visits, 131 medications, 448 DDI pairs, and 491 molecular substructures; 14,995 remains paper-reported metadata only.
- **Evidence boundary**: attempt `formal-20260826-025500` remains immutable historical SafeDrug-family evidence and is not successor evidence. The seven recovered artifacts are training evidence only. The failed RETAIN pair contains no test metrics; neither training artifacts nor logs may substitute for the four absent pairs.
- **Next gate**: the current queue cannot be continued or audited. The authorized additive continuation must preserve it, reuse the existing training/recovery evidence without mutation, and create a new five-entry controller state with distinct test submissions and test roots.

## Completed: Baseline Program Architecture

- **Status**: completed locally on `2026-08-23`; the repository now exposes one registry-driven SafeDrug archived Reproduction Program and no empty baseline directory skeleton.

- **Plan**: `docs/plans/2026-08-23-baseline-program-architecture-plan.md`.
- **Interface**: `medrec reproduce gamenet --gpu 0 --dry-run` plans one lane; `medrec reproduce all --gpus 0,1,2,3 --dry-run` plans four independent lanes.
- **Boundary**: dry-run is executable now. Real submission remains blocked until the 319 dataset and environment identity pass their declared gates; the clean exact harness revision binds the program.

## Completed: Active Tree Consolidation

- **Status**: completed on `2026-08-23`; the checked-out tree now retains only current protocol, archived-lineage identity, generic remote execution, and durable research evidence.
- **Plan**: `docs/plans/2026-08-23-active-tree-consolidation-plan.md`.
- **Scope**: removed SafeDrug-main runners and environments, MoleRec-only APIs, and retired HITL, Project Status, UI, review, and authority-control documentation. Git history remains the recovery layer.
- **Boundary**: historical SafeDrug-main run summaries and scientific failure records remain; no remote environment, data, checkpoint, or run artifact was deleted.

## Completed: SafeDrug Family Reproduction (SafeDrug, RETAIN, LEAP-SafeDrug) on 319

- **Status**: completed on `2026-08-23` as historical SafeDrug `main@88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a` Reproduction Mode evidence; concurrent 3-GPU execution completed for `safedrug` (GPU 2), `retain` (GPU 3), and `leap-safedrug` (GPU 4).
- **Historical implementation**: preserved in Git history. It repaired the shared `medrec-gamenet` environment on 319 (`971ad2bf...`), executed 50 training epochs, selected best checkpoints, ran 10 test rounds, and validated aggregate result artifacts for all three lanes.
- **Evidence**:
  - `safedrug`: Run `medrec-baseline-safedrug-20260822-132448-0bfb210f` (best epoch: 41), DDI $0.0589 \pm 0.0005$, Jaccard $0.5122 \pm 0.0031$, F1 $0.6687 \pm 0.0028$, PRAUC $0.7653 \pm 0.0027$, Avg Meds $20.5825 \pm 0.1611$.
  - `retain`: Run `medrec-baseline-retain-20260822-132548-abcbd1ce` (best epoch: 49), DDI $0.0851 \pm 0.0017$, Jaccard $0.4818 \pm 0.0025$, F1 $0.6425 \pm 0.0023$, PRAUC $0.7587 \pm 0.0019$, Avg Meds $19.6382 \pm 0.3093$.
  - `leap-safedrug`: Run `medrec-baseline-leap-safedrug-20260822-132647-545ede8a` (best epoch: 44), DDI $0.0705 \pm 0.0005$, Jaccard $0.4442 \pm 0.0030$, F1 $0.6068 \pm 0.0031$, PRAUC $0.6506 \pm 0.0035$, Avg Meds $18.9097 \pm 0.0782$.
- **Boundary**: these runs used 15,032 visits and a 112-medication vocabulary, not the paper's 14,995 visits and 131 medications. They remain truthful historical provenance but do not participate in future baseline selection, paper reproduction, or Comparison Mode.

## Blocked: Archived Four-Model Reproduction Preparation

- **Status**: Codex review blocked the `2026-08-25` preparation at B0. The frozen snapshot contains 6,350 patients, 15,032 visits, and 131 medications, but the accepted SafeDrug/MoleRec paper-lineage contract requires exactly 14,995 visits. No upstream evidence supports the preparation packet's claim that the 37-visit difference is a paper typo.
- **Plan**: `docs/plans/2026-08-25-1748-feat-archived-reproduction-preparation-plan.md`.
- **Artifacts**: `runtime/reproduction-prep/prep-20260825-202045/state.json`, `runtime/reproduction-prep/prep-20260825-202045/go-no-go.json`.
- **Scope**: the modern environment, Linux lock, probe path, and four one-epoch smoke mechanics were exercised, but every smoke consumed the rejected 15,032-visit snapshot and is non-authorizing. The artifacts remain only as preparation diagnostics.
- **Execution boundary**: current state is `blocked_data` with `formal_training_authorized: false`. Regenerate a 14,995-visit, 6,350-patient, 131-medication snapshot and rerun all four smokes before any 50-epoch job or upstream ten-round test.
- **Authority**: SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` owns model behavior. The SafeDrug and MoleRec paper statistics plus MoleRec's declared SafeDrug-after-`c7218d0976e5ee5588aeaf5bdbc86b338126bba5` preprocessing lineage own the 14,995-visit B0 boundary. Data, runs, checkpoints, and weights remain untouched.

## Terminated: SafeDrug Archived Four-Model Full Reproduction

- **Status**: terminated on `2026-08-25` at the B0 Data Gate during attempt `formal-20260825-231500`.
- **Plan**: `docs/plans/2026-08-25-2140-feat-four-model-full-reproduction-plan.md`.
- **Failure Record**: `research/failures/safedrug-reproduction-b0-failure-2026-08-25.md`.
- **Outcome**:
  - Remote environment preflight, 319 Input Contract validation, and `stage-safedrug-c721` execution completed cleanly.
  - Preprocessing script execution from upstream `c7218d0` generated 6,350 patients, 131 medications, 448 DDI pairs, and 491 substructures, but 15,032 visits (expected: 14,995 visits, difference: +37 visits).
  - All 6 semantic bridge checks passed (bijections, structure, SMILES map, symmetry, zero diagonal, DDI mask).
  - Under the fail-closed protocol, snapshot `snapshots/safedrug-paper-c721-ijcai21` was **not published**, the staging candidate was rejected, no formal/smoke lanes were admitted, and no retry or parameter tuning was conducted.
- **State**: `runtime/reproduction-formal/formal-20260825-231500/state.json` is marked `terminated_b0_failure`.

## Completed: SafeDrug Archived Four-Model Full Reproduction (Attempt formal-20260826-025500)

- **Status**: completed on `2026-08-26`; executed full end-to-end Reproduction Mode for GAMENet, SafeDrug, RETAIN, and LEAP on 319 under attempt `formal-20260826-025500`.
- **Plan**: `docs/plans/2026-08-25-2140-feat-four-model-full-reproduction-plan.md`.
- **Audit Artifact**: `research/baseline-preflight/safedrug-table2-audit-packet.json`.
- **Detailed Report**: `research/baseline-preflight/safedrug-four-model-reproduction-report.md`.
- **Summary**:
  - Validated 15,032 executable visits with 14,995 paper metadata disclosure (R17) and verified all R18 Table 1 average statistics (157,970 diag, 57,778 pro, 171,900 med) and 6 semantic bridge checks.
  - Published verified snapshot `snapshots/safedrug-paper-c721-ijcai21`.
  - Executed 4 1-epoch fresh smokes (all passed).
  - Executed 4 50-epoch formal lanes with 10-round upstream testing (GAMENet: GPU 0, SafeDrug: GPU 1, RETAIN: GPU 2, LEAP: GPU 3).
  - Validated all 3/3 core publication scientific claims/relationships (SafeDrug Jaccard > GAMENet Jaccard, SafeDrug F1 > GAMENet F1, SafeDrug DDI < LEAP DDI).
  - Generated deterministic Table 2 audit packet (`completed_mismatch`, 12/20 point intervals within $2\sigma$, 3/3 relationships passed).

## Accepted: SafeDrug Archived Single-Baseline Program

- **Status**: in progress since `2026-08-23`; SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` is the only active SafeDrug-family model source and the common baseline for future innovation. The shared four-model Reproduction Program, registry-driven dry-run, local synthetic contract tests, and 319 environment gate are implemented; the paper-lineage data gate remains blocked.
- **Plan**: `docs/plans/2026-08-23-archived-single-baseline-plan.md`.
- **Scope**: reuse the existing `gamenet`, `safedrug`, `retain`, and `leap-safedrug` IDs under one archived lineage; regenerate paper-matching preprocessing, add only the mechanical training-mode adaptation required by the archived entrypoints, run four independent GPU lanes, and compare aggregate results with SafeDrug Table 2.
- **Execution boundary**: no archived run is launchable until the exact paper aggregate counts pass, the training-mode adaptation is audited, and the archived environment succeeds. SafeDrug `main` receives no new registry identity or future run lane.
- **Follow-on**: the decision history in this plan remains authoritative; the implementation-ready full execution is owned by `docs/plans/2026-08-25-2140-feat-four-model-full-reproduction-plan.md`.
