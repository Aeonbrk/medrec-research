# Handoff

Updated: 2026-09-20.

~~~text
Current phase: EBRA_REGIMEN_ASSIGNMENT_SCREEN_COMPLETE_KILLED
Working branch: prototype/ebra-regimen-assignment-screen
Scientific base: 5e01a15c7bd9587bc0e41cd5b016c2bded8df069
Active formal Idea: none
Active formal Gate: none
Evidence role: DEVELOPMENT
Test access: not authorized
GPU capacity: 8 × RTX 3090 24GB
Previous terminal routing: KILL_SET_ASSIGNMENT_HYPOTHESIS
~~~

## Repository-state warning

GitHub default main is currently older than the MEMB/v1.4 research line. The EBRA branch was created directly from verified scientific commit 83f422bd968bbcbf503179ec0a420c5a4029123d.

Do not rebase onto default main or overwrite this research state until that branch divergence is explicitly reconciled.

## Completed screen

Evidence-Bound Regimen Assignment (EBRA) tested a decision-factorization
hypothesis rather than another evidence-side refinement:

~~~text
fine legal EHR evidence
-> medication-specific FineCode proposal bank
-> common decision block
-> fixed binary medication responsibility (control)
   versus
   free medication-or-NULL partial assignment (candidate)
-> final medication set
~~~

The candidate and control shared the same proposal bank, K=M=131 learned
queries, self-attention, cross-attention, FFN, full score matrix, NULL scorer,
information budget, and initialization convention.

Only the supervision and decoding responsibility differed. The complete 15-
epoch Train/Dev pair selected epoch 5 for `fixed_multilabel` at threshold 0.35
and epoch 4 for `ebra_assignment` with native assignment decoding. Both arms
had 1,593,483 parameters.

Dev metrics were:

~~~text
fixed_multilabel: J=0.549849 F1=0.701033 PRAUC=0.797330 DDI=0.075543 AvgMed=20.321054
ebra_assignment:  J=0.497956 F1=0.655389 PRAUC=0.770241 DDI=0.084804 AvgMed=29.111485
delta:            J=-0.051893 F1=-0.045644 PRAUC=-0.027090 DDI=+0.009260 AvgMed=+8.790431
~~~

Both selected epochs were at most 10. v1.4 therefore marked the comparison
`INTERPRETABLE`, with no 30- or 60-epoch extension. The frozen route is
`KILL_SET_ASSIGNMENT_HYPOTHESIS`. No rescue sweep, count-equalization
diagnostic, stability run, MIMIC-IV run, or Test run is authorized.

Aggregate evidence is in
`research/prototypes/ebra-regimen-assignment-screen/result.json`,
`preflight.json`, `fixed_multilabel.results.json`, and
`ebra_assignment.results.json`. The decision note is
`research/memory/decisions/2026-09-20-ebra-regimen-assignment-screen-verdict.md`.

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

## Completed local agent task

The agent implemented and executed only the frozen two-arm comparison:

~~~text
fixed_multilabel
vs
ebra_assignment
~~~

Completed actions:

1. ran the scoped preflight in the local-agent handoff;
2. executed both arms for 15 complete epochs, with no early stopping, on MIMIC-III canonical Train/Dev;
3. used canonical RNG torch/cuda/python=1203, numpy=2048;
4. applied v1.4 horizon-censoring exactly;
5. kept the architecture unchanged while the pair ran;
6. summarized Jaccard/F1/PRAUC/DDI/AvgMed and selected epochs;
7. routed using the frozen thresholds;
8. updated README, result.json, verdict note, current-research-state, and this Handoff;
9. committed and pushed aggregate public-safe evidence only.

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
