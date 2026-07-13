# MoleRec And RETAIN Source Audit

**Scope:** public, read-only source preflight performed on 2026-07-13. This
record covers the official MoleRec repository, the canonical RETAIN author
repository, and the fixed GAMENet medication-combination RETAIN implementation
already named by the Baseline Audit. It contains no restricted data, run logs,
weights, predictions, or environment secrets.

## Decision

- **MoleRec:** source and MIT license pass. Its fixed repository contains a
  Linux Conda environment and a complete source-level training path, but it is
  not ready to execute until a source-faithful data, split, seed, and checkpoint
  manifest is accepted. The repository supports only its native fixed seeds,
  not an externally chosen seed set; its maintainer also says PyG prevents
  deterministic reproduction.
- **RETAIN:** keep `registered` and do not create an environment or queue a
  run. The canonical author source is a Python 2/Theano sequence-classification
  implementation, including a MIMIC mortality example. It is not a medication-
  combination implementation. The PyTorch `Retain` under GAMENet is a distinct
  comparison implementation with no author-proven equivalence, no complete
  environment lock, no checkpoint-selection rule, and inherited GAMENet data
  provenance and `dnc` import gates.

No candidate advances to `smoke_ready`, `comparison_ready`, or a result lane
from this audit.

## Fixed Sources

| Candidate | Exact source examined | Commit-history finding | License |
| --- | --- | --- | --- |
| MoleRec | [official repository at `dd5afaf`](https://github.com/yangnianzu0515/MoleRec/tree/dd5afaf0a503fd3de3229f86ec7f26b345d10e3a) | This was the repository tip on 2026-07-13. The only code/environment commit is the [initial commit](https://github.com/yangnianzu0515/MoleRec/commit/d330fedf498f7cf5228be5ebe91bc60a59f9f99b); later commits add license or README metadata. | [MIT](https://github.com/yangnianzu0515/MoleRec/blob/dd5afaf0a503fd3de3229f86ec7f26b345d10e3a/LICENSE) |
| RETAIN canonical | [author repository at `9fd39c4`](https://github.com/mp2893/retain/tree/9fd39c46e44b3fdae3a667a47fbdd5ffbd87bff5) | This was the repository tip on 2026-07-13. Its final code change before the pinned merge was [a dropout correction](https://github.com/mp2893/retain/commit/eae6d0356c7ef54d9a8e8e54cb7b8298962329ad). | [BSD 3-Clause](https://github.com/mp2893/retain/blob/9fd39c46e44b3fdae3a667a47fbdd5ffbd87bff5/LICENSE) |
| RETAIN medication comparison | [GAMENet at `da695b4`](https://github.com/sjy1203/GAMENet/tree/da695b4fc9390882f3a681c82115e81291ae6380) | The three-commit GAMENet history does not add a RETAIN-specific environment, seed interface, or selection policy. | [MIT](https://github.com/sjy1203/GAMENet/blob/da695b4fc9390882f3a681c82115e81291ae6380/LICENSE) applies to this comparison code, not to an equivalence claim with the RETAIN author implementation. |

## MoleRec

### Reproduction Evidence

The [README](https://github.com/yangnianzu0515/MoleRec/blob/dd5afaf0a503fd3de3229f86ec7f26b345d10e3a/README.md)
calls this the official implementation and specifies MIMIC-III. It requires
`PRESCRIPTIONS.csv`, `DIAGNOSES_ICD.csv`, and `PROCEDURES_ICD.csv`, then invokes
`data/processing.py`. It explicitly inherits SafeDrug processing at
[`c7218d0`](https://github.com/ycq091044/SafeDrug/tree/c7218d0976e5ee5588aeaf5bdbc86b338126bba5).

The [environment file](https://github.com/yangnianzu0515/MoleRec/blob/dd5afaf0a503fd3de3229f86ec7f26b345d10e3a/MoleRec.yml)
is an explicit Linux Conda specification: Python 3.8.16, PyTorch 1.9.0,
CUDA toolkit 10.2.89, PyG 2.0.3 with its matching PyTorch extensions, and RDKit
2022.09.1. This is enough to build a candidate server-only environment after
normal remote preflight. It is not a cross-platform lock and must not be
silently revised to newer CUDA, PyTorch, PyG, or RDKit versions.

The [training entry point](https://github.com/yangnianzu0515/MoleRec/blob/dd5afaf0a503fd3de3229f86ec7f26b345d10e3a/src/main.py)
has train and `--Test` modes. It fixes `torch.manual_seed(1203)` and
`numpy.random.seed(2048)` before argument parsing; it exposes no seed argument,
does not seed Python `random`, and does not set deterministic CUDA behavior.
Therefore an attempt can be characterized only as this source-native seed pair,
not as a multi-seed stability result. In [Issue 5](https://github.com/yangnianzu0515/MoleRec/issues/5#issuecomment-2314810135),
the repository owner states that PyG itself prevents guaranteed reproducibility
even after fixing a random seed. This is an execution disclosure and a bar
against treating repeated runs as deterministically interchangeable.

### Data And Split Gate

The fixed [processor](https://github.com/yangnianzu0515/MoleRec/blob/dd5afaf0a503fd3de3229f86ec7f26b345d10e3a/data/processing.py)
maps medication codes to ATC-4, keeps the 300 most frequent medications and
2,000 most frequent diagnoses, combines admissions with all three modalities,
and constructs patient sequences. The initial multiple-admission filter is
applied before later medication mapping and modality intersections. The runner
must retain the fixed processor behavior and record public-safe input/output
manifests; it must not add a post-processing single-visit filter.

This is not merely theoretical. In [Issue 3](https://github.com/yangnianzu0515/MoleRec/issues/3#issuecomment-1873860665),
the maintainer says the observed final one-visit records could not be resolved
without the original data, and in the follow-up says the choice to filter them
is up to the user. That is insufficient authority to invent a new reproduction
variant. A source-faithful MoleRec lane must preserve the pinned code's output,
then disclose the final patient/visit eligibility check in restricted evidence.

`main.py` divides the ordered patient-record list into the first two thirds for
training, the first half of the remaining third as `data_test`, and the final
half as `data_eval`. The [training code](https://github.com/yangnianzu0515/MoleRec/blob/dd5afaf0a503fd3de3229f86ec7f26b345d10e3a/src/training.py)
validates every epoch on `data_eval`; `--Test` evaluates the manually supplied
checkpoint on `data_test`. The required preflight must verify patient-level
disjointness before this ordered split and bind the exact generated vocabulary
and record ordering to the restricted manifest.

### Checkpoint And Reporting Gate

Every epoch is saved. Training tracks strict Jaccard improvements on
`data_eval` only after epoch 0 and appends the running best epoch to `best.txt`,
but it neither restores that checkpoint nor supplies it automatically to
`--Test`. A wrapper may select only the final `best.txt` entry and its uniquely
matching `Epoch_*_TARGET_*_JA_*_DDI_*.model`; missing, malformed, or ambiguous
artifacts must fail. It may not select by `data_test`, metric rounding, or a
manual scan of checkpoints.

The test routine performs ten seeded bootstrap samples (seed 0, 80 percent
sample size, replacement) from `data_test`. Preserve that source behavior for
Reproduction Characterization and report it separately from a one-pass shared
protocol metric.

### MoleRec Stop Conditions

- Environment solve/import/GPU smoke differs from the pinned `MoleRec.yml`.
- Required MIMIC-III inputs or the fixed SafeDrug lineage inputs are absent.
- Patient-level split disjointness, generated vocabulary, or generated record
  ordering cannot be evidenced on the restricted side.
- A caller requests seeds other than the source-native pair, deterministic
  equivalence, filtering after processing, or a test-selected checkpoint.

## RETAIN

### Canonical Source Is Not This Benchmark Task

The [author README](https://github.com/mp2893/retain/blob/9fd39c46e44b3fdae3a667a47fbdd5ffbd87bff5/README.md)
explicitly says that this repository implements sequence classification, while
the paper's per-timestep formulation is a more general form that the repository
does not provide. Its MIMIC example consumes `ADMISSIONS.csv`,
`DIAGNOSES_ICD.csv`, and `PATIENTS.csv`, builds longitudinal diagnosis records,
and predicts mortality. The [processor](https://github.com/mp2893/retain/blob/9fd39c46e44b3fdae3a667a47fbdd5ffbd87bff5/process_mimic.py)
contains no prescriptions, procedures, multi-label medication targets, or DDI
inputs.

The canonical environment statement is only Python 2.7, Theano 0.8, and CUDA
for GPU use. There is no requirements file, Conda file, exact CUDA version, or
package lock. The model initializes parameters with unseeded NumPy randomness
and shuffles batches using unseeded Python `random`; only Theano dropout uses
`RandomStreams(1234)`. It cannot support a declared reproducibility seed policy
without changing the core or finding immutable upstream evidence.

The code has a source-native checkpoint rule: it saves a model on strict
validation-AUC improvement. However, it also calculates and logs test AUC on
each such improvement. This is upstream behavior for characterization, not an
untouched-test comparison protocol. With `--simple_load`, it makes a seeded
NumPy 70/10/20 random split; otherwise it requires caller-provided train,
validation, and test files. Neither path makes it a medication-combination
candidate.

The [Issue 4 maintainer reply](https://github.com/mp2893/retain/issues/4#issuecomment-326890558)
confirms that historical documentation used obsolete dropout flag names. Use
the pinned source's `--keep_prob_context` and `--keep_prob_emb` spelling, but
do not treat this correction as missing environment or task evidence.

### GAMENet RETAIN Is A Separate Blocked Candidate

GAMENet's [README](https://github.com/sjy1203/GAMENet/blob/da695b4fc9390882f3a681c82115e81291ae6380/README.md)
lists RETAIN under model-comparison code and describes medication-combination
prediction. Its [PyTorch `Retain`](https://github.com/sjy1203/GAMENet/blob/da695b4fc9390882f3a681c82115e81291ae6380/code/models.py)
outputs a medication vocabulary, unlike the author repository's scalar
classification setup. No official RETAIN source or maintainer issue found in
this audit establishes that this PyTorch code is a faithful implementation of
the canonical RETAIN source for this task.

Its [training script](https://github.com/sjy1203/GAMENet/blob/da695b4fc9390882f3a681c82115e81291ae6380/code/baseline/train_Retain.py)
is not a command-line runner. It hardcodes CUDA device 0, 40 epochs, learning
rate 0.0002, a 0.3 medication threshold, and only `torch.manual_seed(1203)`.
It saves every epoch after evaluation on `data_eval`, writes history, and leaves
test mode and checkpoint name as manual source edits. It has no automatic
best-checkpoint rule. The shared [models module](https://github.com/sjy1203/GAMENet/blob/da695b4fc9390882f3a681c82115e81291ae6380/code/models.py)
imports `dnc` at module import time, so this RETAIN path inherits the unresolved
GAMENet `dnc` provenance/environment gate even though `Retain` itself does not
instantiate a DNC.

It also inherits GAMENet's preprocessing discrepancy. In
[GAMENet Issue 7](https://github.com/sjy1203/GAMENet/issues/7#issuecomment-562848153),
the owner states that repository training data do not match the paper's data and
directs users to regenerate it with `EDA.ipynb`; the difference concerns whether
medications beyond the first 24 hours were collected. Do not use bundled data,
choose a first-24-hour setting, or mix regenerated and bundled artifacts without
an immutable upstream instruction and a restricted manifest.

### RETAIN Stop Conditions

- Do not create a RETAIN medication-combination environment from the canonical
  author repository; it is the wrong task.
- Do not run GAMENet's `Retain` until an authoritative lineage decision accepts
  that implementation as the candidate, resolves its `dnc` import, fixes the
  exact preprocessing branch, and specifies a validation-only checkpoint rule.
- Do not convert the author source's Python 2/Theano program to a modern stack,
  add medication outputs, add seeds, or substitute GAMENet code while calling
  the result canonical RETAIN reproduction.

## Required Reopen Evidence

MoleRec can reopen only with a pinned environment lock derived from
`MoleRec.yml`, a source-faithful restricted data manifest, patient-disjoint
ordered split proof, and a wrapper contract that derives selection from the
final `best.txt` entry without reading `data_test` during training.

RETAIN medication-combination can reopen only with immutable, authoritative
evidence linking a fixed implementation to the desired task, a complete
environment specification, a preprocessing decision consistent with the source
and paper, a seed policy executable without core changes, and a validation-only
checkpoint-selection contract.
