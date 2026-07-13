<!-- markdownlint-disable MD013 -->

# Failure Record: GAMENet controlled reproduction

Source boundary: GAMENet commit `da695b4fc9390882f3a681c82115e81291ae6380` and the public-safe audit in `baselines/audits/gamenet.toml`. Restricted source checkout, data copy, checksum manifest, and diagnostics remain outside Git.

## Decision

GAMENet remains `registered`. The research owner approved the API-compatible `dnc` reconstruction below for a source-native Reproduction Characterization after full remote preflight. This supports operational compatibility only; it cannot establish the authors' historical environment or advance readiness.

## Remote preflight interruption

The restricted source revision, source cleanliness, required preprocessed inputs, remote checkout revision, GPU availability, and disk capacity passed their public-safe preflight checks. The isolated environment creation command did not return a success signal before the existing SSH multiplexing connection failed. A direct BatchMode reconnection also timed out during the SSH banner exchange. The environment state is therefore unverified, and no GPU smoke, source training, evaluation, prediction export, or result intake began.

Do not reuse a potentially partial environment. After remote connectivity returns, re-run the entire restricted preflight, verify the exact remote checkout SHA and environment state, then create or replace the environment only under a new explicit preflight record.

## What was verified

The fixed source commit checked out cleanly and contains an MIT license. Its README describes the expected preprocessed records, vocabulary, EHR adjacency, DDI adjacency, and medication-code mapping inputs. The restricted source copy passed a checksum comparison against its read-only source.

`code/train_GAMENet.py` splits the patient sequence by order: the first two thirds train, half of the remainder test, and the final portion evaluates each epoch. It thresholds medication probabilities at `0.5`. The script writes every epoch checkpoint and a final model, but its evaluation mode requires an explicit `--resume_path`.

## Source-native seed and selection amendment

The source sets both Torch and NumPy seeds to `1203` at module import and exposes no seed argument. The source-native run therefore uses `1203`; the runtime-only smoke does not train GAMENet. One attempt cannot measure cross-seed stability, so it remains outside the V3 three-seed stability policy and cannot create readiness evidence.

The source initializes `best_epoch = 0` and `best_ja = 0`. After epoch zero, it updates both only when the Jaccard score on `data_eval` is strictly larger than the recorded score, then prints `best_epoch`. It saves one checkpoint per epoch. A restricted wrapper can therefore parse that source-owned value, require exactly one `Epoch_{best_epoch}_JA_*.model` file, and supply it to `--eval`; the evaluation branch uses `data_test`. This selection happens before the wrapper reads any `data_test` metric. Missing, malformed, or ambiguous source output is a failure, not a reason to choose a checkpoint manually.

## Dependency reconstruction update

The official GAMENet `master` history has three commits: initial source, `v1`, and the pinned README update. None adds a requirements file, environment declaration, package metadata, or a dependency reference for `dnc`. In [Issue #2](https://github.com/sjy1203/GAMENet/issues/2#issuecomment-481103960), the repository owner points a missing-`dnc.py` reporter to the official DMNC repository, but that repository's contemporaneous `dnc.py` is a TensorFlow implementation whose constructor is incompatible with the GAMENet call.

An API-matched, MIT-licensed PyTorch candidate is recoverable independently: [`ixaxaar/pytorch-dnc` commit `bbf48e61e8d3c7dd551aa0e271fbb9ba3fbc6380`](https://github.com/ixaxaar/pytorch-dnc/tree/bbf48e61e8d3c7dd551aa0e271fbb9ba3fbc6380), which predates GAMENet. Its package name is `dnc` and its declared version is `0.0.8`; its `DNC` constructor and `Memory.read` interface exactly match the GAMENet DMNC wrapper. The provisional environment now pins this source commit rather than resolving a floating PyPI package.

This is a source-compatible reconstruction candidate, not evidence that the GAMENet authors installed that exact commit. GAMENet itself neither links to this repository nor records a package version. The research owner approved it for compatibility reconstruction; it still cannot serve as environment-lock readiness evidence.

## Non-revival boundary

Do not treat the API-matched `dnc` candidate as author attribution, patch GAMENet to accept a seed argument, choose a checkpoint from `data_test` results, or replace unavailable inputs with MIMIC-IV, RxNorm, or another representation. Those actions create a different method or experiment and cannot support this reconstruction record.

## Reopening condition

Only immutable upstream or contemporaneous environment evidence attributing the `dnc` implementation and version can establish historical-environment fidelity. The source-native `1203` seed and source-owned checkpoint rule are fixed. Any compatibility characterization run must preserve the fixed source identity and repeat the restricted preflight.
