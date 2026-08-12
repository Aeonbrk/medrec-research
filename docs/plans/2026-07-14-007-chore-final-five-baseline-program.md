---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
title: Final Five Baseline Program
type: chore
date: 2026-07-14
topic: final-five-baselines
---

# Final five baseline program

## Goal capsule

The active program contains GAMENet, SafeDrug, RETAIN, and LEAP from `ycq091044/SafeDrug@88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a`, plus MoleRec from `yangnianzu0515/MoleRec@dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`.

## Boundaries

- The four SafeDrug-main entries share the repository's processing, split, and reporting semantics.
- MoleRec remains an independent pinned source.
- `reference` remains only a synthetic Protocol Check control and is not an active candidate.
- Real-data execution remains blocked until the 319 preflight succeeds.

## Implementation units

### U1. Replace the active program

Set the fixed candidate order to GAMENet, SafeDrug, MoleRec, RETAIN, and LEAP-SafeDrug. Regenerate all authority-bound public fixtures and preserve the existing audit, selection, status, and action contracts.

### U2. Pin final-five source identities

Point the four SafeDrug-main baselines at the selected immutable revision. Keep their derivative identities explicit. Retain MoleRec's official source identity. Delete every removed candidate from the registry and audit set.

### U3. Remove superseded records

Delete superseded plans, audits, and preflight records. Replace the active preflight index with final-five source and execution constraints.

## Verification contract

- `audit-validate` accepts `baselines/programs/final-five.toml`.
- Selection, status, and action fixtures parse with exactly five candidates.
- No active registry, program, audit, fixture, test, or documentation reference remains for removed candidates or superseded programs.
- Full local quality gates pass before remote execution resumes.
