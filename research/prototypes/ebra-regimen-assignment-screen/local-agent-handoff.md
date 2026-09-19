# Local Agent Handoff — EBRA Matched Screen

You are taking over implementation and execution of the frozen **Evidence-Bound Regimen Assignment (EBRA)** screen.

Repository:

~~~text
https://github.com/Aeonbrk/medrec-research
~~~

Working branch:

~~~text
prototype/ebra-regimen-assignment-screen
~~~

Authoritative scientific base for this branch:

~~~text
83f422bd968bbcbf503179ec0a420c5a4029123d
~~~

Important repository state note: GitHub default main is currently older than the MEMB/v1.4 line. Do not rebase this work onto default main or overwrite the newer research state without first reconciling that divergence.

## Read first

~~~text
AGENTS.md
research/AGENTS.md
Handoff.md
research/memory/current-research-state.md

research/memory/decisions/2026-09-20-ebra-regimen-assignment-screen-design.md
research/prototypes/ebra-regimen-assignment-screen/README.md
research/prototypes/ebra-regimen-assignment-screen/closest-work-audit.md

docs/specs/PAPER_EXPERIMENT_CONTRACT.md
docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_4.md
~~~

For inherited evidence, especially read the MEMB/MSED/MHEF verdicts and the evidence-access portfolio result. Do not redesign those killed families.

## Your task

Execute this sequence:

~~~text
fetch exact branch
-> inspect the existing FineCode / PortfolioModel implementation
-> implement only the frozen two-arm EBRA comparison
-> run scoped preflight checks
-> execute the full 15-epoch Train/Dev matched pair on 319
-> apply horizon-censoring rule exactly
-> summarize result
-> update research state and routing
-> commit and push
~~~

Do not brainstorm a replacement architecture before this experiment runs.

## Frozen main pair

Control:

~~~text
fixed_multilabel
~~~

Candidate:

~~~text
ebra_assignment
~~~

Both arms must share:

- identical FineCode evidence-bound medication proposal bank;
- K=M=131 learned decision queries;
- one self-attention layer;
- one cross-attention layer over the medication proposal bank;
- one FFN block;
- identical full score matrix L[k,m];
- identical NULL scorer;
- same legal information and initialization convention.

The control fixes slot k to medication k and trains:

~~~text
b_m = L[m,m] - L[m,NULL]
BCE(target_m, b_m)
~~~

with the standard paper-contract Dev threshold selection.

The candidate uses the full medication-or-NULL categorical score matrix, permutation-invariant bipartite supervision, and native one-to-one assignment decoding. No threshold and no cardinality head.

Read the design note rather than reconstructing details from this handoff.

## Implementation constraints

Use the existing repository model/data/evaluator infrastructure wherever possible.

Do not add:

- a new evidence family;
- DDI-specific loss or reranking;
- retrieval;
- MoE;
- dynamic medication queries;
- extra rereading;
- code-pair modeling;
- cardinality prediction;
- extra decoder layers;
- assignment-temperature or slot-count tuning;
- post-hoc output repair.

Use a standard exact linear-sum assignment implementation already available in the environment if possible. Add a dependency only if the repository/environment genuinely lacks a reliable solver and the dependency is materially simpler than implementing one.

The candidate and control should be parameter-matched within 1%. If not, widen the control rather than weakening it.

## Preflight

Only check failures that can invalidate the experiment:

1. correct canonical MIMIC-III Train/Dev surface;
2. zero Test loading;
3. no current-target/future leakage;
4. exact shared proposal-bank path;
5. shared query/decision/scoring initialization;
6. parameter match;
7. finite forward/backward for both arms;
8. candidate loss invariant to target-set ordering;
9. assignment decoding never duplicates a medication;
10. one full repository-native evaluation pass works for both arms.

Do not build broad test infrastructure.

## Execution

Use canonical DEVELOPMENT RNG:

~~~text
torch=1203
cuda=1203
python random=1203
numpy=2048
~~~

Run both complete arms for 15 epochs without early stopping. Parallelize the two arms on separate RTX 3090 GPUs.

Do not create six additional EBRA variants just because eight GPUs exist.

Interpretation:

~~~text
both selected epochs <= 10
=> evaluate frozen decision rule

either selected epoch 11-15
=> HORIZON_CENSORED_15_TO_30
=> extend exact pair unchanged to total 30

30-epoch selected epoch 26-30
=> HORIZON_CENSORED_30_TO_60
=> extend exact pair unchanged to total 60
~~~

Do not inspect partial metrics to change architecture, loss, slot count, NULL bias, or horizon.

## Required output

Report:

~~~text
candidate/control parameter counts
completed epochs
selected epochs
control selected threshold
candidate native-decode status
patient-macro Jaccard
patient-macro F1
patient-macro PRAUC
pooled-pair DDI
average medication count
Delta candidate-control for all metrics
horizon status
terminal routing
test_loaded
~~~

For EBRA PRAUC use the frozen continuous score:

~~~text
score_m = max_k log p_k(m)
~~~

Discrete EBRA predictions must come only from assignment decoding.

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

Delta J > +0.004 with a supporting-metric guard failure
=> SIGNAL_REVIEW_BEFORE_STABILITY

Delta DDI <= -0.010
and Delta J >= -0.005
and Delta F1 >= -0.005
and Delta PRAUC >= -0.005
=> SURVIVE_TO_PARETO_REVIEW
~~~

Always report medication count. If a strong apparent gain is dominated by cardinality shift, record that explicitly and stop for one bounded count-equalization diagnostic before any stability promotion.

## Result integration

If execution is valid, update:

~~~text
research/prototypes/ebra-regimen-assignment-screen/README.md
research/prototypes/ebra-regimen-assignment-screen/result.json
research/memory/decisions/<date>-ebra-regimen-assignment-screen-verdict.md
research/memory/current-research-state.md
Handoff.md
~~~

Commit public-safe aggregate evidence only. Do not commit patient-level predictions, data, split membership, model weights, private paths, or raw traces.

If the mechanism is negative, terminate it without rescue sweeps. If it survives, do not touch Test; route next to DEVELOPMENT stability plus a deeper closest-work audit.
