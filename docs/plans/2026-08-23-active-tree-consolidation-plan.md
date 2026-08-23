---
title: Active Tree Consolidation
type: refactor
date: 2026-08-23
status: completed
execution: local
---

# Active Tree Consolidation

## Goal

Keep the checked-out tree focused on the current research system: SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6`, the Unified Research Protocol, public-safe comparison records, and the 319 execution boundary. Git history remains the recovery layer for retired implementations. Current documentation keeps only the provenance needed to interpret accepted or failed research evidence.

## Decisions

- Delete code, scripts, tests, environment declarations, plans, playbooks, and UI assets that have no current consumer or describe a removed control plane.
- Do not create an in-repository archive. Moving retired files would preserve their maintenance and navigation cost.
- Preserve research evidence, failure constraints, literature provenance, active specifications, applicable ADRs, and the three historical SafeDrug-main run summaries.
- Keep the generic 319 remote execution seam, but remove built-in launchers until an archived runner and verified environment exist.
- Do not invent the archived runner during cleanup. It must follow the accepted data-count and training-mode gates in the archived baseline plan.

## Work

### U1. Remove retired baseline execution

- Delete the SafeDrug-main runners, parser, setup helper, and environment probe.
- Delete unverified `gamenet` and `safedrug` Conda declarations.
- Make remote launchers explicit constructor input instead of module-global historical declarations.
- Keep current registry entries blocked until archived adapter and environment identities are verified.

### U2. Remove retired baseline APIs

- Delete the MoleRec artifact-bundle module and its tests.
- Remove MoleRec-only constants, protocol exceptions, exports, and examples.
- Keep the general structural-decoder protocol capability because LEAP and GAMENet still need it.

### U3. Remove retired workflow surfaces

- Delete plans, architecture notes, playbooks, wireframes, review notes, and assets whose implementations were already removed.
- Remove their vocabulary and navigation entries from current context and plan tracking.
- Retain only concise historical outcomes that explain still-relevant evidence.

### U4. Align current documentation

- Describe `baselines/` as identity metadata until the archived adapter is implemented.
- Describe `environments/` as the core evaluator bootstrap only until an archived lock exists.
- Remove commands and remediation guidance for deleted launchers and environments.
- Record this consolidation in `docs/PLANS.md`.

## Verification

- Repository searches find no active references to deleted files, MoleRec, final-five, HITL, Project Status Harness, or SafeDrug-main launch commands except explicit historical provenance.
- `medrec baseline list` still reports the reference and four archived model lanes.
- Archived `medrec run --dry-run` fails because no launcher is declared, not because a stale main launcher mismatches the registry.
- Pytest, Ruff, Markdownlint, shell syntax checks for remaining scripts, and whitespace checks pass.

## Definition of done

- The active tree has one current research authority and no executable fallback to SafeDrug main.
- Every remaining top-level directory has a current purpose described by `ARCHITECTURE.md` or `docs/START_HERE.md`.
- Historical evidence remains interpretable without retaining historical implementation surfaces.

## Superseded execution state

At completion, archived `medrec run --dry-run` intentionally failed because no archived launcher existed. The later SafeDrug Archived Baseline Program work replaced that temporary state with the registry-driven `medrec reproduce` interface. This plan remains the record of the cleanup decision, not current execution guidance.
