# Evidence-Bound Regimen Assignment (EBRA) Screen

Status: **EXECUTED / KILLED (2026-09-20)**

EBRA is the next bounded architecture hypothesis after KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY.

Read together:

- research/memory/decisions/2026-09-20-ebra-regimen-assignment-screen-design.md
- research/prototypes/ebra-regimen-assignment-screen/closest-work-audit.md
- docs/specs/PAPER_EXPERIMENT_CONTRACT.md
- docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_4.md

## Scientific question

The project has repeatedly found that medication identity should retain direct access to fine-grained clinical evidence, while several attempts to enrich, normalize, reread, compete over, or repair that evidence have failed.

EBRA therefore changes the **decision process**, not the evidence family:

~~~text
fine legal EHR evidence
-> medication-specific FineCode proposal bank
-> shared decision slots
-> either fixed binary responsibility (control)
   or free medication-or-NULL partial assignment (EBRA)
-> medication set
~~~

## Main matched pair

### Control: fixed_multilabel

- same FineCode proposal bank;
- same K=131 learned decision queries;
- same self-attention, cross-attention, FFN, and score matrix;
- slot k is fixed to medication k;
- binary logit L[k,k] - L[k,NULL];
- BCE supervision;
- paper-contract Dev-selected global threshold.

### Candidate: ebra_assignment

- exact same proposal bank and decision block;
- every slot may choose any medication or NULL;
- categorical medication-or-NULL probabilities;
- bipartite matching to the unordered target set;
- unmatched slots supervised as NULL;
- one-to-one assignment decoding;
- no threshold and no cardinality head.

The full score matrix is computed in both arms. The causal difference is fixed named-label responsibility versus free set assignment.

## Minimum implementation

Implement only what is needed for the matched pair:

~~~text
common evidence encoder / FineCode proposal bank
common learned query bank
one self-attention layer
one cross-attention layer
one FFN
common score matrix L[K, M]
common NULL score
fixed_multilabel loss + threshold decode
ebra_assignment matching loss + assignment decode
paper-contract evaluator
~~~

Do not add DDI-specific loss, retrieval, MoE, cardinality prediction, iterative refinement, extra decoder depth, external knowledge, or post-processing to the first screen.

A standard exact linear-sum assignment implementation is acceptable. The assignment solver is part of the candidate's native training/decoding computation and must be included in latency accounting if the model survives.

## Required preflight

Before any full training, verify only failures that would invalidate the experiment:

1. correct MIMIC-III canonical Train/Dev split and zero Test loading;
2. exact legal information budget and no target/future leakage;
3. same proposal-bank implementation in both arms;
4. same initialization convention and decision-block parameters;
5. parameter counts matched within 1%;
6. full score matrix computed in both arms;
7. finite candidate/control forward and backward;
8. EBRA set loss unchanged by permutation of target-medication order;
9. assignment decoder never emits duplicate medications;
10. both arms can complete one repository-native evaluation pass.

Do not create a large smoke/audit framework.

## Frozen DEVELOPMENT screen

~~~text
profile: mimic-iii-canonical-131-paper-dev-v1
seed: torch/cuda/python=1203, numpy=2048
training: 15 complete epochs
early stopping: none
main comparison: ebra_assignment - fixed_multilabel
Test: SEALED
~~~

Use separate GPUs for the two full arms if available. The other six GPUs should remain available for independent ready work; do not invent EBRA hyperparameter lanes merely to fill them.

Contract v1.4 horizon rules apply exactly.

## Metrics

Report together:

- patient-macro Jaccard — primary;
- patient-macro F1;
- patient-macro PRAUC;
- pooled predicted-pair DDI rate;
- average predicted medication count;
- selected epoch and operating point / native decode status;
- parameter count.

For EBRA continuous medication scores used by PRAUC:

~~~text
score_m = max_k log p_k(m)
~~~

The discrete set must still come only from assignment decoding.

## Frozen routing

~~~text
Delta J <= +0.002
=> KILL_SET_ASSIGNMENT_HYPOTHESIS

+0.002 < Delta J <= +0.004
=> WEAK_STOP

Delta J > +0.004
with Delta F1 >= -0.002
and Delta PRAUC >= -0.002
and Delta DDI <= +0.002
=> SURVIVE_TO_STABILITY

Delta J > +0.004 with guard failure
=> SIGNAL_REVIEW_BEFORE_STABILITY

Delta DDI <= -0.010
with J/F1/PRAUC losses each <= 0.005
=> SURVIVE_TO_PARETO_REVIEW
~~~

No automatic stability, MIMIC-IV, or Test execution follows any single-seed result.

## Result artifacts expected from local execution

Keep the package compact:

- implementation code for the matched pair;
- one preflight script/output;
- per-arm aggregate run results;
- one result.json summarizing frozen comparison and horizon status;
- README updated with actual metrics and routing;
- one decision note;
- current-research-state and Handoff update.

Do not commit patient-level outputs, model weights, split membership, private paths, or raw EHR data.

## Executed result

The exact matched pair ran for 15 complete epochs on source revision
`5e01a15c7bd9587bc0e41cd5b016c2bded8df069` against
`mimic-iii-canonical-131-paper-dev-v1`. The canonical RNG was
`torch/cuda/python=1203` and `numpy=2048`. Test remained sealed.

The scoped preflight passed the split, leakage, shared initialization, parameter,
finite forward/backward, permutation-invariance, duplicate-free decoding, and
repository-evaluator checks. Both arms have 1,593,483 trainable parameters.

| Arm | Selected epoch | Operating point | Native decode | Jaccard | F1 | PRAUC | DDI | AvgMed |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `fixed_multilabel` | 5 | threshold 0.35 | no | 0.549849 | 0.701033 | 0.797330 | 0.075543 | 20.321054 |
| `ebra_assignment` | 4 | native assignment | yes | 0.497956 | 0.655389 | 0.770241 | 0.084804 | 29.111485 |

Candidate minus control was ΔJ `-0.051893`, ΔF1 `-0.045644`, ΔPRAUC
`-0.027090`, ΔDDI `+0.009260`, and ΔAvgMed `+8.790431`. Both selected epochs
are at most 10, so the v1.4 comparison is interpretable without a horizon
extension. The frozen route is `KILL_SET_ASSIGNMENT_HYPOTHESIS`.

The large medication-count increase did not produce a candidate gain, so no
count-equalization diagnostic is authorized. Do not add assignment, NULL-bias,
slot-count, decoder-depth, DDI, retrieval, MoE, or output-repair rescues.

Aggregate artifacts are `result.json`, `preflight.json`,
`fixed_multilabel.results.json`, and `ebra_assignment.results.json`. Restricted
checkpoints, logits, logs, and patient-level records remain on 319.
