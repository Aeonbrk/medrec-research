# Handoff

Updated: 2026-09-16.

## Current state

```text
Expected main before this migration: de2b3246947426d7d832c8f30a4a21b261071590
Scientific phase: post-Stage -1F review
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
Held-out/Test use: not authorized
```

Stage -1F is complete. Medication-specific evidence selection (`DrugQuery`) replicated against `SharedPool` on both frozen Train/Dev surfaces:

- MIMIC-III: `ΔJ = +0.007520`
- MIMIC-IV: `ΔJ = +0.006486`

The frozen run verdict is `MICA_MECHANISM_REPLICATED_BOTH_DATASETS`. Full evidence is in `research/prototypes/mica-cross-dataset-replication/`.

## Knowledge organization

This migration separates repository knowledge by responsibility:

- current facts: `docs/`, `ARCHITECTURE.md`, `CONTEXT.md`;
- engineering causality: `.agents/notes/`;
- scientific run evidence: owning `research/` artifact;
- scientific belief updates: `research/memory/decisions/`;
- live scientific synthesis: `research/memory/current-research-state.md`;
- this file: current handoff only.

Read `docs/KNOWLEDGE_HOMES.md` and the nearest subtree `AGENTS.md` before evaluating the migration.

## Current scientific candidate

Direct Partial Regimen Assignment / RSM remains the leading bounded architecture candidate after Stage -1F review. It is not implemented, trained, admitted as Idea 009, or opened as a Gate.

## One next action

Perform an adversarial review of the knowledge-organization migration only. Check for broken references, duplicated/conflicting authority, lost historical evidence, incorrect subtree rule precedence, and any migration choice that does not fit a scientific research repository.

Do not launch training, implement RSM, read Test, create Idea 009, open a Gate, or alter frozen experiment evidence during that review.
