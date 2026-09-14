# FutureGraphKD-v0

FutureGraphKD-v0 is a bounded Train/Dev representation-transfer prototype, not
Idea 009 and not a causal or treatment-effect model. It tests whether the
patient's immediate next recorded diagnoses/procedures provide observational
privileged information that can transfer to a deployable current-visit
medication recommender. The future state is not a medication-response,
efficacy, benefit, or counterfactual representation.

## Architecture

- The Student and Teacher use the same compact two-layer, hidden-96
  patient-conditioned medication message-passing core over the 131 candidates,
  with the canonical EHR co-prescription and DDI relations.
- Each visit uses the frozen MoleRec score and the frozen patient-specific
  per-visit medication embedding directly (no cross-visit averaging).
- Student features contain current and historical diagnosis/procedure codes,
  historical medications, and the frozen MoleRec signals. The Teacher adds
  only the immediate next visit's diagnoses/procedures; it never receives
  future medications or the current target vector.
- Student training uses BCE on every Train visit. On visits with an immediate
  next visit, the Teacher has its BCE objective and the Student receives
  `0.5` soft-logit distillation plus `0.05` final-hidden-state MSE. There is no
  cardinality model: `Student-SameK` is a ranking diagnostic decoded at the
  frozen MoleRec per-visit cardinality.

## Protocol

One seed (`20260914`), one configuration, six epochs, batch size 64, learning
rate `1e-3`, weight decay `1e-4`, hidden width `96`, two graph layers, code-hash
width `64`, KD weight `0.5`, and hidden-alignment weight `0.05`. The run used
10,489 Train visits and 2,130 Gate01-Dev visits (4,233 and 1,004 patients,
respectively) from the existing MoleRec-compatible artifact. No held-out
Audit/test resource, bootstrap, confidence interval, sweep, or additional
seed was used. The implementation run was bound to
`a83c9329e0b752a2d7725c2852ac1457a01a5509`.

Train privileged support was 6,256/10,489 visits (59.6434%) across 3,707
patients. Gate01-Dev support was 1,126/2,130 visits (52.8638%) across 831
patients.

## Full Gate01-Dev screen

All rows use the frozen MoleRec cardinality for the two SameK surfaces.

| Surface | Jaccard | F1 | PRAUC | DDI | Mean medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| MoleRec | 0.529174 | 0.683480 | 0.773576 | 0.072223 | 21.5451 |
| GraphRefine-SameK | 0.533650 | 0.687394 | 0.784240 | 0.073328 | 21.5451 |
| FutureGraphKD Student-SameK | 0.528843 | 0.683264 | 0.774511 | 0.074672 | 21.5451 |

Student-SameK preserved the MoleRec cardinality exactly for every visit. It
changed 16.2911% of Dev sets versus MoleRec, with mean symmetric difference
`0.328638`.

## Privileged supported-subset diagnostic

The following rows use exactly the 1,126 Gate01-Dev visits with an immediate
next visit (831 patients). GraphRefine-SameK is the matched aggregate from one
unchanged HyperEdit diagnostic run; it is included only to contextualize the
privileged comparison.

| Surface | Jaccard | F1 | PRAUC | DDI | Mean medications |
| --- | ---: | ---: | ---: | ---: | ---: |
| GraphRefine-SameK | 0.528967 | 0.683363 | 0.776601 | 0.071296 | 21.7593 |
| FutureGraphKD Student-SameK | 0.526075 | 0.680852 | 0.770654 | 0.073393 | 21.7593 |
| FutureGraphKD Teacher-SameK | 0.526587 | 0.681328 | 0.770649 | 0.072723 | 21.7593 |

Teacher minus matched Student was only `+0.000513` Jaccard and `-0.000005`
PRAUC, far below the approximately `+0.005` privileged-signal threshold.

## Focused validation and decision

The visit-order/next-visit alignment and privilege-boundary assertions passed.
The CUDA forward/backward smoke passed with finite loss/gradients and verified
that Student outputs are invariant to privileged future tensors while Teacher
outputs consume them. The observed effect was weak: the supported-subset
Teacher did not materially outperform the matched Student, and the full-Dev
Student did not improve on MoleRec or GraphRefine-SameK.

Decision: `STOP_NO_FUTURE_STATE_SIGNAL`.
