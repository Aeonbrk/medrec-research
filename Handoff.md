# Handoff: MoleRec five-model reproduction

## Next-session focus

Resume from the frozen-schedule admission gate for attempt `formal-20260828-a09fcab-u8-b`. The recovery and local conformance slice is complete, but the scientific reproduction is not. Do not restart training, rerun recovery, or infer test results from training artifacts.

## Current state

- Local conformance is committed as `7997af12dc77baf5cb6b1bc78ef72e6974d7f317` on `feat/archived-reproduction-preparation`.
- All seven training lanes completed 50 epochs and retain native histories and checkpoints: RETAIN, LEAP, GAMENet, MoleRec Embedding, and three SafeDrug learning-rate candidates. Their original status pairs are `training_failed` because finalization could not parse unlabeled validation metrics after training; this was not an early-stop failure.
- Immutable recovery siblings were created from those preserved artifacts without retraining. Their source/recovery evidence pairs were reopened and validated. Do not allocate or reuse another recovery ID.
- U6–U10 are implemented and locally synthetic-tested. That is protocol/conformance evidence, not scientific evidence.
- No successor test result, test metrics, five-model result, or final audit exists. Non-selected SafeDrug candidates remain `not_tested_by_design`.
- The attempt-owned schedule is frozen and reserves GPU 7, but it is bound to an earlier harness revision rather than the current clean revision. Formal testing is not yet admissible.
- Local verification is green: 293 tests passed; Ruff check and format checks passed; Markdown lint passed.
- Preserve the pre-existing `AGENTS.md` work-in-progress. This file is user-owned handoff context and is intentionally not part of the conformance commit.

## Safe continuation

1. Read the authoritative plan and both execution contracts listed below.
2. Run the remote preflight on the designated 319 server, then inspect the attempt-owned status and ledger without mutating source artifacts.
3. Re-accept the frozen schedule against the clean conformance revision. Require the exact GPU/CPU mapping, GPU 7 reservation, and no duplicate, overlapping, omitted, or altered allocation.
4. Only if schedule admission succeeds, submit exactly five serial tests: RETAIN, LEAP, GAMENet, the selected SafeDrug lane, and MoleRec.
5. Validate terminal evidence and run the final audit only after those tests complete. Keep training evidence, test evidence, and local synthetic evidence separate.

## Authoritative references

- `docs/PLANS.md` — accepted-work status and next gates.
- `docs/plans/2026-08-28-1718-fix-molerec-finalization-recovery-plan.md` — recovery and conformance contract.
- `docs/plans/2026-08-26-1709-feat-molerec-five-model-reproduction-plan.md` — scientific reproduction contract.
- `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` — remote preflight and execution boundary.
- `docs/playbooks/MOLEREC_TABLE1_EXECUTION_PLAYBOOK.md` — MoleRec Table 1 execution procedure.

## Suggested skills

- `compound-engineering:ce-work` — continue from the accepted plan and schedule blocker.
- `monitor-experiment` — inspect remote status and ledgers before any submission.
- `experiment-audit` — validate terminal evidence after admissible tests exist.
- `analyze-results` — analyze scientific outputs only after the final audit passes.
