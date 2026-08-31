# Handoff: five-model baseline readiness

## Current state

The five-model baseline preparation is complete.

- All seven 50-epoch training lanes and their validated immutable recovery siblings remain the only accepted training evidence. No lane was retrained and no recovery ID was changed.
- Continuation `continuation-20260830-pathfix-1` completed the exact five serial upstream tests with new submission identities and independent test roots.
- Validation-only SafeDrug selection chose `molerec-safedrug-lr-5e-4`. The `1e-5` and `1e-4` candidates remain `not_tested_by_design`.
- The Phase A audit verdict is `completed_mismatch`: `execution_integrity` and `artifact_completeness` passed, `paper_point_fidelity` passed 16/25 checks, and `directional_relationships` passed 3/4 checks.
- Comparison revision `9fa239269f5a9ac0c394263ebe0ba3c02fbdafc5` produced five target-free Unified Research Protocol v1.1 qualifications under one shared scope.
- RETAIN, LEAP, GAMENet, SafeDrug, and MoleRec are all `comparison_ready` in `baselines/registry.toml`. The built-in reference remains `registered` and is not part of the five-model suite.
- SafeDrug and MoleRec Comparison qualifications used the user-authorized shared-GPU Phase B exception on GPU 0 at 0% prelaunch utilization and 22,359 MiB free. The resident external process was not stopped. No model behavior, selection rule, threshold, decoder, target ownership, or evaluator changed.
- Future remote GPU admission is utilization- and capacity-based: current utilization must be at most 10% and the run's free-memory threshold must pass. Existing external PIDs are ignored for admission and must not be stopped, preempted, or attached to.

## Terminal conclusions

- `execution_integrity`: passed
- `paper_point_fidelity`: failed, 16/25 checks passed
- `directional_relationships`: failed, 3/4 checks passed
- `artifact_completeness`: passed
- Reproduction Mode: `completed_mismatch`
- `engineering_ready`: true
- `reproduction_complete`: true
- `research_baseline_ready`: true

## Authoritative records

- `docs/PLANS.md` — completed-work state.
- `docs/plans/2026-08-29-1541-feat-five-model-baseline-readiness-plan.md` — accepted plan and terminal outcome.
- `research/baseline-preflight/molerec-five-model-reproduction-report.md` — public-safe Phase A report.
- `research/baseline-preflight/five-model-comparison-qualification.json` — public-safe Phase B scope, gate, qualification, and outcome identities.
- `research/baseline-preflight/five-model-baseline-readiness-report.md` — per-model two-axis readiness report.
- `baselines/registry.toml` — current Comparison readiness authority.

## Operational snapshot

- **Branch**: `main`
- **Suite health**: Local verification passed: 318 unit/integration tests passing; `ruff` lint and formatting clean; `markdownlint` clean; Python 3.8 syntax compatibility verified across baseline execution files via AST parsing.
- **Architecture**:
  - Unidirectional dependency: `Concrete Reproduction Program -> shared mechanical primitives`.
  - Callback cycle (`Program -> runner -> getattr/module hooks -> Program`) 100% eliminated.
  - Remote executor is attempt- and baseline-agnostic (`src/medrec_research/remote_executor.py`).
  - MoleRec Table 1 schedule, recovery, and continuation validation isolated in `src/medrec_research/reproduction/molerec_table1_attempt.py`.
  - Queue authority strictly bound to immutable `attempt_declaration.json` (`src/medrec_research/reproduction/evaluation_queue.py`); historical legacy queues supported for read-only audit.
  - Concrete Reproduction Programs (`baselines/safedrug_archived.py` and `baselines/molerec.py`) directly own execution and expose uniform `probe(request)` and `execute(request)` program boundaries.
  - Python 3.8 syntax compatibility verified across baseline execution files using AST parsing; this architecture refactor did not require scientific runtime execution.
  - Shared reproduction runner (`baselines/reproduction_runner.py`) reduced strictly to mechanical primitives (process execution, progress streaming, atomic writing, failure pair recording, layout validation).

## Next focus

The suite may now be used for downstream mechanism experiments that stay inside the recorded Comparison Scope. A new dataset, cohort, feature set, medication vocabulary, DDI asset, protocol version, Adaptation Budget, threshold, decoder, or model configuration creates a different scope and requires prospective qualification. Reproduction mismatches remain visible and must not be tuned away.
