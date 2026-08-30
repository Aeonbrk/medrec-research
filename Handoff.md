# Handoff: five-model baseline readiness

## Next-session focus

Do not resume test claims for attempt `formal-20260828-a09fcab-u8-b`. Its first formal RETAIN test has a finalized `failed` / `test_failed` evidence pair, so the attempt is `formal_incomplete`. The queue and ledger intentionally preserve that failure, and the remaining four test entries have not been claimed.

On 2026-08-30, the user authorized one additive continuation identity that reuses the seven immutable training/recovery pairs without retraining. The old failed queue and submission remain closed. The authorized continuation must use new test submission IDs and independent test roots; it still may not allocate a recovery ID or enter Comparison Mode before a legal five-pair audit exists.

## Current state

- All seven 50-epoch training lanes and their validated immutable recovery siblings remain the only accepted training evidence. No lane was retrained and no recovery ID was changed.
- Continuation admission reopened all seven evidence pairs and rebound the exact frozen schedule to clean harness revision `c4fc4d8408ce3119a02813525e17435a9ba102ec`. Schedule B, lane isolation, and the GPU 7 reservation were preserved.
- Validation-only SafeDrug selection chose `molerec-safedrug-lr-5e-4`. The `1e-5` and `1e-4` candidates remain `not_tested_by_design`.
- The frozen serial queue was RETAIN, LEAP, GAMENet, selected SafeDrug, MoleRec. RETAIN was the only claimed test.
- RETAIN finalized as `failed` / `test_failed` before upstream ten-round evaluation. The controller supplied the recovery directory basename as the upstream model name, while the checkpoint namespace was created from the original training-run basename.
- LEAP, GAMENet, selected SafeDrug, and MoleRec remain unclaimed. No test aggregate was inferred from training artifacts or logs, and the five-pair audit barrier was not bypassed.
- The local runner now derives the recovered test model name from the original training source root and exposes the validated source checkpoint through the basename-only upstream namespace. The queue refuses every later claim after a failed or blocked entry, and future finalization writes the ledger before the idempotent queue transition so an interrupted queue write can be reconciled without replaying a test. These are future-path engineering fixes, not evidence for the failed attempt.
- Phase B did not start. All five registry entries remain `registered`; no current-scope Comparison Qualification exists.

## Terminal conclusions

- `execution_integrity`: failed
- `paper_point_fidelity`: not evaluated
- `directional_relationships`: not evaluated
- `artifact_completeness`: failed
- Reproduction Mode: `formal_incomplete`
- `engineering_ready`: false
- `reproduction_complete`: false
- `research_baseline_ready`: false

## Authoritative records

- `docs/PLANS.md` — accepted-work state and blocked gates.
- `docs/plans/2026-08-29-1541-feat-five-model-baseline-readiness-plan.md` — combined continuation/readiness plan and execution outcome.
- `research/baseline-preflight/molerec-five-model-reproduction-report.md` — public-safe Phase A report.
- `research/baseline-preflight/five-model-baseline-readiness-report.md` — per-model two-axis readiness report.
- `docs/playbooks/MOLEREC_TABLE1_EXECUTION_PLAYBOOK.md` — current stop boundary and future operator procedure.

## Non-negotiable continuation boundary

1. Preserve the failed RETAIN pair, queue, ledger, selection, preregistration, source schedule, continuation schedule, and seven recovery siblings.
2. Do not claim another test or run the final audit for the current attempt.
3. Do not start U4–U7 Comparison qualification work until Phase A has the legal five-pair audit required by the Unified Research Protocol plan.
4. Freeze the authorized continuation identity against a new clean harness revision, wait for GPU 7 to become idle, and write every new test pair under its independent continuation root.
