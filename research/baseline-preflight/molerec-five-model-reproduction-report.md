# MoleRec Five-Model Reproduction Report

## Verdict

Attempt `formal-20260828-a09fcab-u8-b` is `formal_incomplete`.

This is an execution failure, not a paper mismatch. No five-model aggregate, paper-point comparison, or directional relationship can be inferred from the available evidence.

| Axis | Result | Evidence boundary |
| --- | --- | --- |
| `execution_integrity` | failed | The first formal RETAIN test finalized `failed` / `test_failed` before upstream ten-round evaluation. |
| `paper_point_fidelity` | not evaluated | No valid RETAIN test metrics and no five-model test set exist. |
| `directional_relationships` | not evaluated | The required five current-attempt test pairs do not exist. |
| `artifact_completeness` | failed | One failed test pair exists; four canonical test pairs and the final audit packet are absent. |

## Frozen scientific identity

- RETAIN, LEAP, GAMENet, and SafeDrug use SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`.
- MoleRec uses `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`.
- The shared preprocessing revision is `c7218d0976e5ee5588aeaf5bdbc86b338126bba5`.
- All seven 50-epoch training lanes reuse their validated immutable recovery siblings. No lane was retrained and no recovery identity changed.

## Admitted continuation

The attempt-owned frozen schedule was additively rebound to clean harness revision `c4fc4d8408ce3119a02813525e17435a9ba102ec`. The seven-lane order, measured GPU and CPU allocation, lane isolation, and GPU 7 reservation were unchanged.

Validation-only SafeDrug selection consumed the three recovered candidates and selected `molerec-safedrug-lr-5e-4`. The `1e-5` and `1e-4` candidates remain `not_tested_by_design`. The frozen serial test order was RETAIN, LEAP, GAMENet, selected SafeDrug, and MoleRec.

## Terminal event

RETAIN was the only claimed formal test. Its status/result pair finalized as `failed` / `test_failed`, with artifact type `test` and no test metrics. The recovered-test controller formed the upstream model name from the recovery directory basename, while the source checkpoint namespace had been formed from the original training-run basename. Upstream therefore could not resolve the checkpoint name before evaluation began.

The failed pair was retained. The controller did not claim LEAP, GAMENet, selected SafeDrug, or MoleRec. It did not retry RETAIN, read a training artifact as a test result, use historical four-model metrics, or bypass the five-pair audit barrier.

## Engineering correction and evidence boundary

The local runner now derives the recovered test model name from the original training source root and exposes the validated source checkpoint through the basename-only upstream namespace. The queue also refuses later claims after any failed or blocked entry, while finalization leaves a queue-write interruption safely retryable without replaying the test. Focused tests cover these behaviors and reject a mismatched test identity.

These changes are prospective engineering corrections only. They do not repair, relabel, or authorize a replay of this attempt. A future execution requires an explicit new attempt or continuation contract.
