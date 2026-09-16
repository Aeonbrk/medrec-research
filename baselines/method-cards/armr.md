# ARMR method card

`METHOD_ID`: `armr`

`DISPLAY_NAME`: ARMR (adaptively responsive medication recommendation)

`SCIENTIFIC_ROLE`: external longitudinal baseline; development-only until a
current paper-profile run passes the fidelity and evaluator checks.

## SOURCE

- Paper: [ARMR: Adaptively Responsive Network for Medication Recommendation](https://www.ijcai.org/proceedings/2025/871), IJCAI 2025.
- Official implementation: [seucoin/armr2](https://github.com/seucoin/armr2).
- Pinned source revision: `c0de843d43a1f2867d45ede836b918abd11a0fda`.
- The source checkout is kept immutable for each run; no Stage -1G runner is
  reused.

## SCIENTIFIC_CORE

ARMR combines diagnosis, procedure, and medication-history representations over
the recent visits with a piecewise temporal sequence module for farther history.
It learns medication representations from Train-only EHR co-occurrence and DDI
graphs, then combines patient and medication representations for one logit per
medication. The pinned `MyNet.forward` explicitly zeroes the procedure tensor;
that released behavior is preserved and recorded rather than silently repaired.

- Objective: `BCEWithLogitsLoss`.
- Optimizer: source Adam (`lr=2e-4`, betas `(0.9, 0.999)`, `eps=1e-5`,
  `weight_decay=1e-6`).
- Source training defaults: MIMIC-III 56 epochs, batch size 32, recent-visit
  length 3; source validation uses threshold `0.30` and best PRAUC with
  PRAUC-decline early stopping.
- Decoder: independent sigmoid medication scores; no DDI post-filter or
  target-cardinality input.
- Required learned context: a Train-only medication co-occurrence graph and
  the frozen aligned DDI matrix.

## BENCHMARK_PROFILE

- Benchmark: MIMIC-III canonical-131 paper development profile
  [`research/benchmarks/mimiciii-medrec/profile.json`](../../research/benchmarks/mimiciii-medrec/profile.json).
- Input budget: current diagnosis/procedure sets plus strictly previous visits'
  diagnosis, procedure, and medication sets; current medications are masked.
- Output: one finite score for every canonical medication coordinate.
- Evidence role: `DEVELOPMENT`; no MIMIC-IV Test access or Test evaluation.

## ADAPTATION

- Mechanical: load the frozen canonical snapshot, apply the declared patient
  split, construct Train-only EHR co-occurrence, and feed the source model's
  expected near-to-far sequence tensors.
- Benchmark-specific: evaluate the complete Dev surface after each checkpoint
  and select checkpoint plus global operating point jointly by patient-macro
  Jaccard under the frozen paper profile. The source threshold and source
  validation metrics remain reference diagnostics.
- Scientific changes: `NONE` to the model, loss, graphs, history semantics, or
  procedure-channel behavior. Any such change is a named variant.

## SOURCE_SANITY

- The pinned source imports `einops`; the locked MoleRec environment does not
  provide it. A separate remote Python 3.8 environment with Torch 2.4.1+cu121
  and `einops` 0.8.1 passed static compilation and a CUDA forward smoke.
- Formal execution uses `/root/anaconda3/envs/xytf/armr_irsa_py38` with explicit
  environment hash `6af6bd1e97fc0ea5991e09bcf2f99e18326fa1d88871e53cc6496230310f3921`.
- The bundled source data are identical to the audited ARMR vocabulary/DDI
  assets, but their source split and evaluator are not the paper-profile
  contract. Source-native smoke values are non-evidence.
- Admission checks require finite logits, non-collapsed predictions,
  non-pathological medication cardinality, correct graph/input use, and a
  complete terminal artifact before any ranking use.
- Verdict: `FIDELITY_UNRESOLVED` until a current-profile run and independent
  audit pass.

## VALIDATION_AND_DECODING

- Maximum source-informed budget: 56 Train epochs, with source early stopping
  preserved unless the frozen run record declares otherwise.
- Evaluate every observed checkpoint on all Dev patients.
- Legal operating points: the frozen profile's `0.05` through `0.95` grid;
  native source default `0.30` is retained as a reference.
- Selection metric: Dev patient-macro Jaccard. Report F1, PRAUC/AP, DDI,
  predicted/target medication counts, and the source-native diagnostics
  separately.

## STATUS

`DEVELOPMENT_ONLY`

## LIMITATIONS

- The released source uses a different data split and visit-macro-style
  evaluation than the current paper profile.
- The source's procedure-channel zeroing is surprising but is part of the
  pinned implementation; no stronger procedure-enabled variant is called
  ARMR.
- The alternate environment differs from the historical lock; its complete
  identity and run-specific hashes must be recorded before formal execution.
