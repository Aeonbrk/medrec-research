# Plans

## Completed: Architecture Surface Hardening and Boundary Consolidation

- **Plan**: `docs/plans/2026-09-01-refactor-architecture-surface-hardening-plan.md`.
- **Status**: Completed; units U0 through U5 implemented and verified across all 323 tests.
- **Architectural Deliverables**:
  - Narrowed concrete Reproduction Programs (`baselines/safedrug_archived.py`, `baselines/molerec.py`) public interface to strictly `__all__ = ("execute", "probe")`, with `main()` acting as a thin CLI transport adapter delegating to `probe`/`execute`.
  - Moved all 13 reproduction CLI commands, argument parsers, resource validators, and git revision inspectors out of root `src/medrec_research/cli.py` into `src/medrec_research/reproduction/cli_commands.py`. Root `cli.py` is a pure composition root delegating via `register_reproduction_commands`.
  - Completely deleted dead Process Adapter Schema v1 and unused `PredictionAdapter` protocol, establishing `ProcessPredictionAdapter.predict_comparison(...)` (schema v2) as the single Comparison Mode process seam.
  - Rewrote process adapter tests and CLI integration tests without architectural drift or compatibility wrappers.
- **Verification**: Local verification passed: 323 pytest tests passing, ruff lint and format check clean, Python 3.8 AST syntax check clean across all baseline files.

## Completed: Reproduction Architecture Refactoring

- **Plan**: `docs/plans/2026-08-31-1849-refactor-reproduction-architecture-plan.md`.
- **Status**: Completed; units U1 through U7 implemented and verified across all 318 tests.
- **Architectural Deliverables**:
  - `RemoteExecutor` is attempt-agnostic and manages only generic 319 command execution, environment activation, preflight, SSH, and synchronization.
  - Attempt-level scheduling, continuation validation, and Table 1 policy are isolated in `src/medrec_research/reproduction/molerec_table1_attempt.py`.
  - `attempt_declaration.json` is the authoritative contract for evaluation queues with backward-compatible fallback for legacy queues.
  - Shared reproduction execution (`reproduction_runner.py`, `reproduction_artifacts.py`) is reduced to mechanical primitives without model-specific branches or hardcoded lane tables.
  - SafeDrug archived and MoleRec Reproduction Programs are deepened as self-contained programs (`safedrug_archived.py`, `molerec.py`) with programmatic `probe` and `execute` APIs, internal collaborator modules, and no legacy contract/runner split.
  - Python 3.8 syntax compatibility verified across baseline execution files using AST parsing; this architecture refactor did not require scientific runtime execution.
- **Verification**: Local verification passed: 318 pytest tests passing, ruff lint and format check clean, markdownlint clean, Python 3.8 AST syntax check clean on all baseline execution files.

## Completed: Five-Model Baseline Readiness

- **Plan**: `docs/plans/2026-08-29-1541-feat-five-model-baseline-readiness-plan.md`.
- **Phase A state**: attempt `formal-20260828-a09fcab-u8-b` completed through continuation `continuation-20260830-pathfix-1`. All five frozen upstream ten-round tests finalized legally; no training lane, recovery ID, checkpoint, threshold, or test selection changed.
- **Axes**: `execution_integrity = passed`, `paper_point_fidelity = failed` (16/25), `directional_relationships = failed` (3/4), and `artifact_completeness = passed`. The terminal verdict is `completed_mismatch`.
- **Phase B state**: RETAIN, LEAP, GAMENet, selected SafeDrug, and MoleRec each passed all seven qualification gates under one Unified Research Protocol v1.1 Comparison Scope at harness revision `9fa239269f5a9ac0c394263ebe0ba3c02fbdafc5`.
- **Shared scope**: Dataset Manifest `82d4efc2…`, 1,058 patient-disjoint test patients, 1,206 eligible visits, 131 medications, feature identity `9e403591…`, DDI asset `dcb20789…`, and equal Adaptation Budget `180fd7e4…`.
- **Suite conclusions**: `engineering_ready = true`, `reproduction_complete = true`, and `research_baseline_ready = true`.
- **Execution note**: the user explicitly authorized SafeDrug and MoleRec Phase B qualification on shared GPU 0 after 0% utilization and sufficient free memory were verified; the resident external process was not stopped. The exclusivity exception is public and did not change scientific behavior or qualification semantics.
- **Reports**: `research/baseline-preflight/molerec-five-model-reproduction-report.md` and `research/baseline-preflight/five-model-baseline-readiness-report.md`.
- **Qualification artifact**: `research/baseline-preflight/five-model-comparison-qualification.json`.

## Completed: MoleRec Finalization Recovery and Conformance

- **Status**: U1–U5 recovery and the later continuation-admission conformance are complete for formal attempt `formal-20260828-a09fcab-u8-b`: all seven source lanes retain one validated immutable recovery sibling. No lane was terminated, duplicated, retrained, or tested during recovery.
- **Plan amendment**: `docs/plans/2026-08-28-1718-fix-molerec-finalization-recovery-plan.md` permits immutable same-attempt finalization from preserved histories and checkpoints. It does not permit retraining, test-based selection, Baseline Core changes, or source-artifact overwrite.
- **Local conformance**: validation-only SafeDrug selection, declaration-owned probes, additive frozen-schedule continuation admission, recovered-test invocation, exact five-entry queue admission, failed-entry terminalization, and the five-pair audit barrier are synthetic-tested. These checks are not scientific evidence.
- **Remote boundary**: The original source artifacts and seven recovery siblings remain immutable. The accepted schedule was additively rebound to clean revision `c4fc4d8408ce3119a02813525e17435a9ba102ec`; the source schedule was not overwritten. The first formal RETAIN test then failed as recorded above, closing the current attempt without a five-model result.

## Completed: MoleRec Table 1 Five-Model Full Reproduction

- **Status**: The original failed queue remains preserved, and the authorized continuation completed all five canonical test pairs plus the terminal audit without retraining.
- **Plan**: `docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md` is authoritative for this work.
- **Scientific scope**: RETAIN, LEAP, GAMENet, SafeDrug, and MoleRec use the frozen SafeDrug archived revision `8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, MoleRec revision `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, and preprocessing revision `c7218d0976e5ee5588aeaf5bdbc86b338126bba5`. Five scientific models map to seven 50-epoch training lanes because SafeDrug has three disclosed learning-rate candidates (`1e-5`, `1e-4`, `5e-4`) and validation-only selection.
- **Current contract**: all seven lanes use `medrec-molerec-table1` (Python 3.8.16, PyTorch 1.9.0+cu111, PyG 2.0.3) and the additive `snapshots/molerec-table1-c721-www23` declaration. The executable dataset contract is 6,350 patients, 15,032 visits, 131 medications, 448 DDI pairs, and 491 molecular substructures; 14,995 remains paper-reported metadata only.
- **Evidence boundary**: attempt `formal-20260826-025500` remains immutable historical SafeDrug-family evidence and is not successor evidence. The original failed RETAIN pair still contains no test metrics. Only the five finalized continuation test pairs feed the terminal audit.
- **Outcome**: `completed_mismatch`; execution integrity and artifact completeness passed, while paper point fidelity and one directional relationship missed.

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

## Completed (Superseded): SafeDrug Archived Single-Baseline Program

- **Status**: completed and superseded; SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` was consolidated under the four-model reproduction plan (`docs/plans/2026-08-25-2140-feat-four-model-full-reproduction-plan.md`) and five-model baseline readiness plan (`docs/plans/2026-08-29-1541-feat-five-model-baseline-readiness-plan.md`).
- **Plan**: `docs/plans/2026-08-23-archived-single-baseline-plan.md`.
- **Scope**: reuse the existing `gamenet`, `safedrug`, `retain`, and `leap-safedrug` IDs under one archived lineage; regenerate paper-matching preprocessing, add only the mechanical training-mode adaptation required by the archived entrypoints, run four independent GPU lanes, and compare aggregate results with SafeDrug Table 2.
- **Execution boundary**: superseded by the completed MoleRec Table 1 five-model reproduction and comparison qualification.
- **Follow-on**: the decision history in this plan remains authoritative; the full execution was completed in subsequent formal attempts.
