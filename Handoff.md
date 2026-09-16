# Handoff

Updated: 2026-09-16.

## Current state

```text
Knowledge migration reviewed revision: 3c420eb0d810c10f629f575495a767aef5698436
Migration review verdict: PASS
Scientific phase: pre-Stage 0 bounded candidate review
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
Held-out/Test use: not authorized
```

Stage -1F is complete. Medication-specific evidence selection (`DrugQuery`) replicated against matched `SharedPool` controls on both frozen Train/Dev surfaces:

- MIMIC-III: `ΔJ = +0.007520`
- MIMIC-IV: `ΔJ = +0.006486`

The frozen run verdict remains `MICA_MECHANISM_REPLICATED_BOTH_DATASETS`. Full evidence is in `research/prototypes/mica-cross-dataset-replication/`.

The knowledge-home migration passed independent adversarial review with no blocker, major, or minor findings. The review confirmed byte-preserved history, scientific-state preservation, reference integrity, subtree rule precedence, and no material over-migration. The accepted engineering record is `.agents/notes/migrations/2026-09-16-knowledge-home-review-pass.md`.

## Current scientific candidate

Direct Partial Regimen Assignment / RSM remains the leading bounded architecture candidate. It is not implemented, trained, admitted as Idea 009, or opened as a Gate.

Before any RSM training, resolve the remaining cheap implementation-equivalence concern from Stage -1F: the generalized variable-medication MICA path produced a lower MIMIC-III DrugQuery peak than the prior fixed-131 implementation under nominally matched settings. This requires a no-training exact-equivalence check, not another optimization sweep.

## One next action

Run a bounded, target-free, no-training exact-equivalence audit between the prior fixed-131 MICA implementation and the generalized MICA implementation on the 131-medication path. Compare parameter names/shapes, initialized tensors under the same seed, forward logits, and objective values on the same synthetic or target-free batch.

If equivalent, return the result for final RSM experiment-contract review. Do not launch RSM automatically.

Do not read Test, create Idea 009, open a Gate, add seeds, tune hyperparameters, or alter frozen experiment evidence during this check.
