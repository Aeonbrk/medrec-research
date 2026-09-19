# EBRA regimen-assignment screen verdict — 2026-09-20

Date: 2026-09-20
Status: **TERMINATED: KILL_SET_ASSIGNMENT_HYPOTHESIS**
Evidence role: `DEVELOPMENT`

## Frozen comparison

The EBRA matched pair ran on the canonical MIMIC-III Train/Dev profile
`mimic-iii-canonical-131-paper-dev-v1` at source revision
`5e01a15c7bd9587bc0e41cd5b016c2bded8df069`. Both arms used the same
FineCode proposal bank, 131 learned decision queries, one self-attention layer,
one cross-attention layer, one FFN, full medication score matrix, NULL scorer,
legal information budget, initialization convention, and 1,593,483 trainable
parameters.

The control was `fixed_multilabel`. It used fixed slot-to-medication
responsibility, BCE on `L[m,m] - L[m,NULL]`, and the paper-contract global Dev
threshold. The candidate was `ebra_assignment`. It used balanced
permutation-invariant medication/NULL matching and one-to-one native assignment
decoding. No Test data were loaded.

The scoped preflight passed. It checked the canonical split, target-free model
inputs, shared initialization, parameter equality, finite forward/backward,
target-order invariance of the candidate loss, duplicate-free decoding, and one
repository-native evaluator pass. The public-safe evidence is in
`research/prototypes/ebra-regimen-assignment-screen/preflight.json`.

## Complete 15-epoch result

Both arms completed all 15 epochs. The control selected epoch 5 at threshold
`0.35`. EBRA selected epoch 4 with native assignment decoding.

| Arm | Jaccard | F1 | PRAUC | DDI | AvgMed |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fixed_multilabel` | 0.549849 | 0.701033 | 0.797330 | 0.075543 | 20.321054 |
| `ebra_assignment` | 0.497956 | 0.655389 | 0.770241 | 0.084804 | 29.111485 |

Candidate minus control is:

~~~text
Delta J       = -0.051893
Delta F1      = -0.045644
Delta PRAUC   = -0.027090
Delta DDI     = +0.009260
Delta AvgMed  = +8.790431
~~~

Both selected epochs are at most 10. The v1.4 horizon status is therefore
`INTERPRETABLE`; no 15-to-30 or 30-to-60 extension is required.

## Routing

The primary rule is decisive because ΔJ is below `+0.002`:

~~~text
KILL_SET_ASSIGNMENT_HYPOTHESIS
~~~

The candidate also loses F1 and PRAUC, increases DDI, and predicts 8.79 more
medications on average. The negative result closes this tested
FineCode-proposal-to-medication-or-NULL assignment formulation. It does not
claim that every structured-set method must fail.

No count-equalization diagnostic is authorized because the candidate has no
accuracy gain to explain. Do not run slot-count, NULL-bias, assignment-
temperature, decoder-depth, DDI-reranking, cardinality-head, retrieval, MoE,
iterative-rereading, or post-hoc-repair rescues. Test remains sealed, and no
stability, MIMIC-IV, or Test execution follows this screen.

## Evidence artifacts

- `research/prototypes/ebra-regimen-assignment-screen/result.json`
- `research/prototypes/ebra-regimen-assignment-screen/preflight.json`
- `research/prototypes/ebra-regimen-assignment-screen/fixed_multilabel.results.json`
- `research/prototypes/ebra-regimen-assignment-screen/ebra_assignment.results.json`
