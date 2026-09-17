# RIME: regimen-conditional marginal energy

RIME is a bounded development screen. It asks whether the identity of a
currently proposed medication set changes the marginal utility of another
medication after patient evidence and set size are held fixed. It is not a
formal Idea, a Test run, or a paper-candidate claim.

## Frozen comparison

The screen has one seed, `20260920`, on the Train/Dev-only
`mimic-iii-canonical-131-paper-dev-v1` profile. Both arms use 60 complete
epochs, batch size 16, AdamW at `3e-4`, weight decay `1e-4`, gradient clipping at
5, float32 with TF32 disabled, and dropout `0.1`. The two arms use identical
initialization, visit permutations, context samples, and checkpoints.

The shared clinical path is a 64-dimensional DrugQuery encoder. `p_x` is the
masked mean of the final target-free clinical tokens. For each medication,
`d_m` is its learned medication embedding, `e_m` is its DrugQuery attention
read, and

```text
z_m = LN(Wd d_m + We e_m + Wp p_x)
a_m = Linear(z_m)
phi_m = Linear(64,128) -> GELU -> Linear(128,64)
U(x,S) = sum(a_m for m in S) + rho(concat(p_x, r(S)))
```

The composition arm uses `r(S) = sum(phi_m for m in S)`. The count-only arm
uses `r(S) = |S| * mean(phi_m over all 131 medications)`. The control has the
same parameters and legal inputs, so it retains patient-specific nonlinear
count utility but cannot distinguish equal-cardinality compositions.

For every target set `Y`, training samples a uniform `k` from `0..|Y|`, a
uniform `k`-subset `C_pos` of `Y`, one uniform negative medication `n` from
`M\\Y`, and `C_err = C_pos union {n}`. It trains the mean of the two full
131-coordinate BCE losses over marginal logits
`U(C union {m}) - U(C)`. No DDI, auxiliary, margin, cardinality, or assignment
loss is used.

Inference starts at the empty set and repeatedly applies the positive-gain
single medication flip with the lowest canonical medication index as the tie
break. It stops at a non-positive maximum gain or after `2 * 131` flips. The
PRAUC/AP score for medication `m` is the raw marginal utility after removing
`m` from the final set. There is no threshold or beta operating point. Dev
selection therefore compares the native decoder at each complete checkpoint
using the repository's patient-macro-Jaccard joint checkpoint procedure.

The run records Jaccard, F1, PRAUC/AP, pooled-pair DDI, AvgMed, count MAE/bias,
adds, removes, total flips, cap hits, and same-cardinality composition
sensitivity. The latter replaces the lowest selected medication with the
lowest unselected medication and compares candidates absent from both contexts.
The count-only control should be zero up to numerical tolerance; a positive
full-arm value is the direct mechanism diagnostic.

## Preflight and remote execution

Run the targeted preflight in the declared `medrec-molerec-table1` environment
before either 60-epoch arm:

```bash
python research/prototypes/rime/preflight_rime.py --device cuda \
  --output /root/zhb/medrec-data/prototypes/rime/preflight.json
```

Then launch the two arms independently from a clean checkout, with outputs
outside all repositories:

```bash
CUDA_VISIBLE_DEVICES=0 python research/prototypes/rime/run_rime.py \
  --variant composition --snapshot-root "$SNAPSHOT_ROOT" \
  --train-dev-root "$TRAIN_DEV_ROOT" --source-revision "$RUN_REVISION" \
  --output-dir "$RIME_OUTPUT/composition"

CUDA_VISIBLE_DEVICES=1 python research/prototypes/rime/run_rime.py \
  --variant count_only --snapshot-root "$SNAPSHOT_ROOT" \
  --train-dev-root "$TRAIN_DEV_ROOT" --source-revision "$RUN_REVISION" \
  --output-dir "$RIME_OUTPUT/count_only"
```

After both terminal results pass their independent audits, make the primary
comparison without reading patient-level artifacts:

```bash
python research/prototypes/rime/summarize_rime.py \
  --composition "$RIME_OUTPUT/composition/results.json" \
  --count-only "$RIME_OUTPUT/count_only/results.json" \
  --output "$RIME_OUTPUT/rime-comparison.json"
```

The local checkout does not contain restricted EHR data and must not run this
training. Keep checkpoints, aligned predictions, targets, and raw logs on the
319 Execution Plane. Only aggregate `results.json` files may return to the
Harness Terminal.

## Decision rule

Compare the selected Dev rows as `composition - count_only`. The aggregate
comparator treats F1 or PRAUC below the control by more than `0.002` as an
inconsistent support metric. RIME survives only with `Delta J >= about +0.004`
and both supporting metrics within that bound, or with a clear
accuracy-DDI/cardinality Pareto improvement. A delta near `+0.008` to `+0.010`
is a strong signal. A smaller delta without a material safety Pareto advantage
kills this formulation.

If conditional-context performance and composition sensitivity are positive but
greedy inference shows a specific off-manifold error-propagation failure, one
rerun may replace or add random contexts with one-step model-generated
contexts. This is the only bounded redesign. Do not add GNNs, DDI loss,
cardinality tuning, assignment solvers, beam search, or multiple corruption
rates.
