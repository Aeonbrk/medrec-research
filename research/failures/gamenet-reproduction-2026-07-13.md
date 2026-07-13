<!-- markdownlint-disable MD013 -->

# Failure Record: GAMENet controlled reproduction

Source boundary: GAMENet commit `da695b4fc9390882f3a681c82115e81291ae6380` and the public-safe audit in `baselines/audits/gamenet.toml`. Restricted source checkout, data copy, checksum manifest, and diagnostics remain outside Git.

## Decision

The planned MIMIC-III v1.4 GAMENet Reproduction Mode lane is blocked before Conda environment creation, adapter implementation, GPU smoke, and seed execution. GAMENet remains `registered`.

## What was verified

The fixed source commit checked out cleanly and contains an MIT license. Its README describes the expected preprocessed records, vocabulary, EHR adjacency, DDI adjacency, and medication-code mapping inputs. The restricted source copy passed a checksum comparison against its read-only source.

`code/train_GAMENet.py` splits the patient sequence by order: the first two thirds train, half of the remainder test, and the final portion evaluates each epoch. It thresholds medication probabilities at `0.5`. The script writes every epoch checkpoint and a final model, but its evaluation mode requires an explicit `--resume_path`.

## Why execution stopped

The pinned source imports `DNC` in `code/models.py`, but it contains no requirements file, environment declaration, setup metadata, or documented `dnc` version. Pinning a package by guess would change the recorded upstream behavior without evidence.

The training script sets both Torch and NumPy seeds to `1203` at module import. It exposes no seed argument. Running the pre-registered full seeds `7`, `19`, and `31` would require changing the Baseline Core, so it is not faithful Reproduction Mode.

The source evaluates every epoch on its final data partition, records `best_epoch`, and saves all epoch checkpoints. It does not save or select that tracked best epoch automatically. The README evaluation command accepts a manually supplied checkpoint path. No fixed-source evidence states how that path was chosen for the reported result, so choosing one now would invent a selection rule.

## Non-revival boundary

Do not infer a `dnc` version from its import name, patch GAMENet to accept new seeds, choose a checkpoint from test results, or replace unavailable inputs with MIMIC-IV, RxNorm, or another representation. Those actions create a different method or experiment and cannot support this reproduction record.

## Reopening condition

Reopen only with immutable upstream or contemporaneous environment evidence that identifies the `dnc` implementation and version, a source-compatible way to execute the pre-registered seed policy without changing GAMENet, and a documented checkpoint-selection rule independent of the held-out test partition. A reopened plan must preserve the fixed source identity and repeat the restricted preflight.
