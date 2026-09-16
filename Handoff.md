# Handoff

Updated: 2026-09-16.

## Current state

```text
Expected origin/main before Stage -1G design: f94d0b8709be2dc6e2a7d150fc3d0406a2c2ace8
Scientific phase: STAGE -1G — COMPETITIVE SUBSTRATE CALIBRATION
Stage -1G status: DESIGNED_NOT_EXECUTED
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
Held-out/Test use: not authorized
```

Stage -1F remains frozen: medication-specific evidence selection (`DrugQuery`) replicated against `SharedPool` on both Train/Dev datasets.

- MIMIC-III: `ΔJ = +0.007520`
- MIMIC-IV: `ΔJ = +0.006486`
- verdict: `MICA_MECHANISM_REPLICATED_BOTH_DATASETS`

This establishes internal cross-dataset mechanism value, not external SOTA. The largest remaining experimental weakness is strong external coverage under the frozen MIMIC-IV task.

## Stage -1G

Read first:

- `research/AGENTS.md`
- `baselines/AGENTS.md`
- `research/memory/current-research-state.md`
- `research/prototypes/mica-competitive-substrate-calibration/protocol.md`
- `research/memory/decisions/2026-09-16-stage-minus-1g-competitive-substrate-calibration.md`

The experimental standard is semantic fairness rather than one forced optimizer. External baselines share the same task, information budget, split roles, target semantics, and evaluator, while retaining their documented scientific core and method-appropriate training recipe.

Stage -1G first resolves the fixed-131/generalized-MICA no-training equivalence concern. It then qualifies strong external methods from primary sources and official code. If qualification succeeds, select exactly three baseline families runnable faithfully on both MIMIC-III and MIMIC-IV and use six GPUs as three paired dataset lanes.

Preferred recent candidates are ARMR, HypeMed, and SSPNet. SSPNet is run only with trustworthy implementation provenance; otherwise use a faithful compatible fallback such as GAMENet. Do not create a low-fidelity rewrite merely to complete the matrix.

## One next action

Execute the frozen Stage -1G protocol through its terminal competitiveness verdict.

Do not read Test, implement RSM, add paper-level multi-seed confirmation, create Idea 009, open a Gate, or change frozen Stage -1F evidence.
