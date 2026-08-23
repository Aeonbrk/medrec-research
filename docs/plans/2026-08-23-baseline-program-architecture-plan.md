---
title: Baseline Program Architecture
type: refactor
date: 2026-08-23
status: completed
execution: local
---

# Baseline Program Architecture

## Goal

Make the checked-in SafeDrug archived reproduction understandable and executable through one interface, including by smaller coding models, without weakening scientific gates or inventing empty module seams.

## Decisions

- Delete empty `baselines/` subdirectories and every other untracked empty repository skeleton. A directory exists only after a real tracked module needs it.
- Name the source-native executable module a Reproduction Program, not a Prediction Adapter. Reproduction Mode and Comparison Mode remain distinct scientific interfaces.
- Keep one SafeDrug archived program with four internal profiles because GAMENet, SafeDrug, RETAIN, and LEAP share source, dataset, environment, and upstream evaluation lineage.
- Make the Baseline Registry the only authority for program entrypoint, external 319 roots, required inputs, import probe, and verified identities. Delete the duplicate production `BaselineLauncher` declaration.
- Expose `medrec reproduce <baseline>` and `medrec reproduce all`. Dry-run generates complete commands without SSH; real submission remains blocked until the environment identity is verified on 319. The clean exact harness revision already binds the program.
- Keep the Unified Research Protocol 1.0 base contract and v1.1 amendment as separate scientific documents, but make their authority relationship explicit in repository navigation.

## Verification responsibility

Synthetic tests prove registry parsing, complete launch construction, four-GPU mapping, independent lane failure, archived data-count gates, training-mode adaptation, checkpoint selection, and result finalization. They do not prove real dataset availability, archived dependency compatibility, GPU execution, or paper reproduction.

## Follow-on gate

On 319, prepare the exact archived dataset, verify the shared Conda environment and import probe, record the observed environment identity, then invoke the same interface without `--dry-run`. Do not raise readiness or claim reproduction before those gates pass.
