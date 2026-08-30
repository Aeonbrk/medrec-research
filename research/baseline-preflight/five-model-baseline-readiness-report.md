# Five-Model Baseline Readiness Report

## Overall conclusion

- `engineering_ready = true`
- `reproduction_complete = true`
- `research_baseline_ready = true`

All five unchanged Baseline Cores have a legal terminal Reproduction Mode result and an accepted Unified Research Protocol v1.1 Comparison Qualification under one shared scope. Reproduction remains `completed_mismatch`; Comparison qualification does not relabel that result.

## Per-model readiness

| Model | Pinned source / scientific identity | Reproduction Mode | Comparison Mode | Mechanism experiments | Sole current blocking gate |
| --- | --- | --- | --- | --- | --- |
| RETAIN | SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, profile `retain` | `completed_mismatch`; legal ten-round result | `comparison_ready`; qualification `b14f12ae…` | Yes | None |
| LEAP | SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, structural profile `leap-safedrug` | `completed_mismatch`; legal ten-round result | `comparison_ready`; qualification `c2d258d2…` | Yes | None |
| GAMENet | SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, profile `gamenet` | `completed_mismatch`; legal ten-round result | `comparison_ready`; qualification `79891870…` | Yes | None |
| SafeDrug | SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, validation-selected `5e-4` lane | `completed_mismatch`; legal ten-round result; other LR candidates not tested | `comparison_ready`; qualification `5280019b…` | Yes | None |
| MoleRec | MoleRec `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, profile `molerec-embedding` | `completed_mismatch`; legal ten-round result | `comparison_ready`; qualification `f3a00ae8…` | Yes | None |

## Shared Comparison Scope

- Protocol: Unified Research Protocol v1.1, amendment `c5b8ac4a…`.
- Dataset Manifest: `82d4efc2…`; 1,058 patient-disjoint test patients and 1,206 eligible test visits.
- Vocabulary: 131 medications.
- Feature availability: `9e403591…`.
- DDI evaluation asset: `dcb20789…`.
- Equal Adaptation Budget: `180fd7e4…`; no Comparison search or test-driven model selection was used.
- Execution path: `Baseline Core -> target-free predictions -> core-owned target join -> core evaluator`.
- All five qualification attempts passed `environment_lock`, `adapter_smoke`, `cohort_identity`, `adaptation_budget`, `core_integrity`, `deterministic_adapter`, and `independent_evaluation`.

## Core-recomputed Comparison outcomes

| Model | DDI | Jaccard | F1 | PRAUC | Avg medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| RETAIN | 0.0891 | 0.4872 | 0.6477 | 0.7578 | 19.1111 |
| LEAP | 0.0723 | 0.4565 | 0.6186 | 0.6573 | 18.7662 |
| GAMENet | 0.0857 | 0.5034 | 0.6608 | 0.7690 | 28.0697 |
| SafeDrug | 0.0601 | 0.5142 | 0.6716 | 0.7650 | 19.9959 |
| MoleRec | 0.0737 | 0.5269 | 0.6822 | 0.7731 | 21.6617 |

These values are descriptive Comparison evidence, not clinical claims and not a new leaderboard. The five models are mechanism carriers from two pinned source lineages, not five independent research lineages.

## Execution note

The first three qualifications ran under the original remote execution admission. For SafeDrug and MoleRec, all server GPUs had resident external processes. The user explicitly authorized Phase B to share GPU 0 after it showed 0% utilization and 22,359 MiB free; the external process was not stopped. The GPU exclusivity check was therefore recorded as an operator-authorized Phase B exception rather than falsely reported as passed. Source, environment, checkpoint, features, decoder, threshold, prediction set, target ownership, and evaluation semantics were unchanged, and both formal qualifications completed without OOM or retry.

The complete public-safe scope, gate, attempt, qualification, evaluation, outcome, and uncertainty identities are recorded in `five-model-comparison-qualification.json`. Restricted predictions, memberships, checkpoints, weights, private paths, and raw traces remain outside Git.
