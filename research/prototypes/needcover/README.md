# NeedCover — Regimen-Conditioned Residual Clinical-Need Reasoning

NeedCover is a throwaway pre-Idea architecture screen. It is not Idea 009,
not a CCFA Gate, and not a formal research-state transition. The screen tests
one mechanism: a provisional medication regimen changes the residual clinical
need assigned to each explicit current diagnosis problem.

## Fixed screen contract

- One seed: `20260914`; one configuration; no sweep or rescue.
- Existing canonical MoleRec-compatible Train and Gate01-Dev arrays only.
- Current inputs are diagnosis and procedure code sets. History contains only
  prior diagnosis/procedure/medication events; current medications are labels.
- Candidate vocabulary is fixed at 131 medications.
- Relation priors are the existing Train-derived EHR co-prescription and DDI
  matrices. No diagnosis–medication prior is used.
- The frozen MoleRec threshold surface is `GlobalStrong`; it does not use
  ground-truth cardinality.
- Heldout, test, Audit, G3, and G4 resources are not read. HypeMed is not an
  input or required backbone.

## Architecture and controls

`ProblemDrug` builds explicit diagnosis problem nodes, problem–medication
affinities, and medication-specific patient states. It has no medication
interaction layer and no residual second pass.

`StaticTwoPass` uses the same front-end, one relation-aware medication layer,
and the same second-stage FFN as NeedCover, but its second message uses the
static problem weights `alpha_ki`.

`NeedCover` is identical to `StaticTwoPass` except that it computes

```text
c_k = sum_i alpha_ki * p_i^0
r_k = 1 - c_k
m_i^1 = sum_k r_k * alpha_ki * u_k / (sum_k r_k * alpha_ki + eps)
```

The model has exactly two reasoning stages, no latent intent slots, no
problem-activity gate, and no iterative refinement. All three learned surfaces
share dimensions, AdamW settings, epochs, batch size, BCE plus the same 0.3
provisional auxiliary term, seed, split, and frozen `logit >= 0` decoder.

## Remote execution

Run from this directory in the verified `medrec-molerec-table1` environment
after the 319 preflight:

```bash
conda run --no-capture-output -n medrec-molerec-table1 \
  python run_needcover.py \
  --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
  --output /root/zhb/medrec-data/prototypes/needcover/screen.json
```

The runner writes aggregate output only. Patient rows, checkpoints, and raw
logs remain outside the repository.

## Decision rule

The primary mechanism comparison is `NeedCover Jaccard - StaticTwoPass
Jaccard`. A delta at or below `0.002` is `KILL_NEEDCOVER_MECHANISM`. A delta in
`(+0.002, +0.004]` permits exactly one diagnosis-count/multimorbidity and
coverage-collapse diagnostic; it does not permit tuning. Survival additionally
requires an unambiguous accuracy/safety improvement over `GlobalStrong`, with
precision/F1/PRAUC guarding against prescription-size inflation.

## Screen result

Filled from the one remote Train/Gate01-Dev run:

| Surface | Jaccard | F1 | PRAUC | Precision | Recall | DDI rate | Mean medications |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GlobalStrong | 0.529174 | 0.683480 | 0.773576 | 0.661221 | 0.736513 | 0.072223 | 21.545070 |
| ProblemDrug | 0.466960 | 0.625717 | 0.755558 | 0.751977 | 0.565428 | 0.082206 | 14.993897 |
| StaticTwoPass | 0.481188 | 0.639966 | 0.761894 | 0.746491 | 0.587578 | 0.081395 | 15.541784 |
| NeedCover | 0.477415 | 0.636425 | 0.761072 | 0.745629 | 0.583867 | 0.081619 | 15.490610 |

NeedCover − StaticTwoPass Jaccard: `-0.00377264645`

The model-count standard deviations were `5.762196` (GlobalStrong),
`6.540338` (ProblemDrug), `6.091508` (StaticTwoPass), and `6.211919`
(NeedCover). The final NeedCover state therefore did not gain accuracy through
prescription-size inflation.

## Coverage and residual diagnostics

The 2,130 Dev visits contributed 33,456 explicit diagnosis problem states.

| Surface | Coverage mean ± std | Residual mean ± std | Coverage near-boundary | Residual near-boundary |
| --- | ---: | ---: | ---: | ---: |
| ProblemDrug | 0.259223 ± 0.212726 | 0.740777 ± 0.212726 | 0.058555 | 0.058555 |
| StaticTwoPass | 0.194231 ± 0.178338 | 0.805769 ± 0.178338 | 0.158268 | 0.158268 |
| NeedCover | 0.193676 ± 0.181950 | 0.806324 ± 0.181950 | 0.167892 | 0.167892 |

Near-boundary means `c_k <= 0.05` or `c_k >= 0.95` (and analogously for
`r_k`). NeedCover's residual signal was not a constant collapse, but it still
failed the decisive matched-depth comparison.

The run used code revision
`28eb0270cf18c48507abd3d0e7642cd702415de2`, CUDA, and the fixed configuration
above. The permitted small-delta diagnosis-count/multimorbidity diagnostic was
not run because the matched Jaccard delta was negative.

Terminal recommendation: `KILL_NEEDCOVER_MECHANISM`
