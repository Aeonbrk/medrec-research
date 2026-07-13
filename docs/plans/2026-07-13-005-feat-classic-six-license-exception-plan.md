---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
title: Classic-six License Exception And Source Reconstruction
type: feat
date: 2026-07-13
topic: classic-six-license-exception
---

# Classic-six License Exception And Source Reconstruction

## Goal Capsule

Apply the research owner's current classic-six decision: unresolved public-source licenses remain visible in audit records but no longer block reproduction-lane selection. Preserve V1 selection records, allow a user-approved GAMENet `dnc` compatibility reconstruction, and record CS598 as independent MICRON environment evidence without replacing the official MICRON Baseline Core.

## Scope Boundaries

- V1 selection remains `source + license` and must keep parsing unchanged.
- V2 selection uses `source` as its only audit hard gate. It does not state that an unlicensed repository is licensed or authorize external-source distribution in Git.
- SafeDrug, MICRON, and LEAP-SafeDrug keep their fixed official source identity. Their unresolved training, checkpoint, input, split, and dependency evidence remains blocking where applicable.
- `yuheng222/CS598-DL4H-MICRON@201df22cd61902c337f3ba91f705246645b67936` is an independent course reproduction and environment reference, not the official MICRON Baseline Core.
- GAMENet uses the approved API-compatible `ixaxaar/pytorch-dnc@bbf48e61e8d3c7dd551aa0e271fbb9ba3fbc6380` only as a compatibility reconstruction. It cannot establish the authors' historical environment.

## Implementation Units

### U1. Version Selection Policy

Add V2 selection semantics while retaining V1 parsing and the V1 source/license hard gates. Make V2 the default for new current selection publication. License dispositions remain part of Baseline Audits, but V2 does not emit license blockers.

### U2. Prove License Is Informational In V2

Add a focused selection test that removes GAMENet's license review and still selects GAMENet under V2. Preserve the V1 fixture test by creating V1 explicitly.

### U3. Record Execution Evidence

Update the classic-six preflight and integration playbook with the V1/V2 distinction, the GAMENet dependency reconstruction, and the CS598 provenance boundary. Do not alter registry readiness or baseline source code.

## Verification Contract

- The focused V2 test fails before the implementation and passes afterward.
- Existing V1 selection and status fixtures remain parseable.
- Full pytest, Ruff check, Ruff format check, Markdown lint, audit validation, lock check, public-safe scan, and `git diff --check` pass.
