# Handoff

Updated: 2026-09-20.

~~~text
Current phase: EBRA_REGIMEN_ASSIGNMENT_SCREEN_DESIGN_FROZEN_IMPLEMENTATION_PENDING
Working branch: prototype/ebra-regimen-assignment-screen
Scientific base: 83f422bd968bbcbf503179ec0a420c5a4029123d
Active formal Idea: none
Active formal Gate: none
Evidence role: DEVELOPMENT
Test access: not authorized
GPU capacity: 8 × RTX 3090 24GB
Previous terminal routing: KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY
~~~

## Repository-state warning

GitHub default main is currently older than the MEMB/v1.4 research line. The EBRA branch was created directly from verified scientific commit 83f422bd968bbcbf503179ec0a420c5a4029123d.

Do not rebase onto default main or overwrite this research state until that branch divergence is explicitly reconciled.

## Current hypothesis

Evidence-Bound Regimen Assignment (EBRA) tests a decision-factorization hypothesis rather than another evidence-side refinement:

~~~text
fine legal EHR evidence
-> medication-specific FineCode proposal bank
-> common decision block
-> fixed binary medication responsibility (control)
   versus
   free medication-or-NULL partial assignment (candidate)
-> final medication set
~~~

The candidate and control share the same proposal bank, K=M=131 learned queries, self-attention, cross-attention, FFN, full score matrix, NULL scorer, information budget, and initialization convention.

Only the supervision/decoding responsibility differs.

## Read first

~~~text
AGENTS.md
research/AGENTS.md
research/memory/current-research-state.md

research/memory/decisions/2026-09-20-ebra-regimen-assignment-screen-design.md
research/prototypes/ebra-regimen-assignment-screen/README.md
research/prototypes/ebra-regimen-assignment-screen/closest-work-audit.md
research/prototypes/ebra-regimen-assignment-screen/local-agent-handoff.md

docs/specs/PAPER_EXPERIMENT_CONTRACT.md
docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_4.md
~~~

Primary closest-work boundary already checked:

- SSPNet occupies set-to-set/permutation-consistent MedRec, but its published head is still sigmoid + threshold multi-label classification;
- DETR occupies learned direct-set queries, bipartite matching, unique predictions, and no-object/NULL;
- DSPN occupies generic permutation-respecting set prediction.

Do not make generic first-set / first-matching / first-structured-MedRec novelty claims.

## Local agent task

Implement only the frozen two-arm comparison:

~~~text
fixed_multilabel
vs
ebra_assignment
~~~

Then:

1. run the scoped preflight in the local-agent handoff;
2. execute both arms for 15 complete epochs, no early stopping, on MIMIC-III canonical Train/Dev;
3. use canonical RNG torch/cuda/python=1203, numpy=2048;
4. apply v1.4 horizon-censoring exactly;
5. do not inspect partial curves to change the architecture;
6. summarize Jaccard/F1/PRAUC/DDI/AvgMed and selected epochs;
7. route using the frozen thresholds;
8. update README, result.json, verdict note, current-research-state, and this Handoff;
9. commit and push aggregate public-safe evidence only.

Test remains SEALED.

## Frozen routing

~~~text
Delta J <= +0.002
=> KILL_SET_ASSIGNMENT_HYPOTHESIS

+0.002 < Delta J <= +0.004
=> WEAK_STOP

Delta J > +0.004
and Delta F1 >= -0.002
and Delta PRAUC >= -0.002
and Delta DDI <= +0.002
=> SURVIVE_TO_STABILITY

Delta J > +0.004 with guard failure
=> SIGNAL_REVIEW_BEFORE_STABILITY

Delta DDI <= -0.010
with J/F1/PRAUC losses each <= 0.005
=> SURVIVE_TO_PARETO_REVIEW
~~~

No automatic multi-seed, MIMIC-IV, or Test execution follows this single-seed screen.
