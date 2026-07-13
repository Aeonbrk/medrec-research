# Classic-six baseline source preflight audit

## Goal

Audit every classic-six candidate against its official repository, immutable source revision, and maintainer Issue comments before any environment creation or real-data execution. Record environment, training, seed, split, checkpoint, and licensing evidence that would otherwise be discovered during a failed launch.

## Scope

- GAMENet, SafeDrug, MICRON, MoleRec, RETAIN, and LEAP-SafeDrug.
- Public, read-only GitHub source, repository metadata, commit history, and maintainer comments only.
- The source is identified by an immutable SHA. Issue comments explain intent but never replace a source revision, license, environment lock, or restricted-data manifest.

## Boundaries

- Do not clone external baseline source into this repository, create an environment, use restricted data, access 319, run training, or change a Baseline Core.
- Do not promote registry readiness. A source-compatible dependency, a bundled checkpoint, or a reproduced metric is not proof of faithful Reproduction Mode or Comparison Mode eligibility.
- Do not infer a missing dependency, CLI flag, seed, split, checkpoint rule, license, or task equivalence from a related baseline.

## Deliverables

- `research/baseline-preflight/` contains source audits and a six-candidate execution matrix.
- `docs/PLANS.md` indexes this audit.
- Existing Baseline Audit TOML records remain unchanged unless immutable evidence changes one of their explicit claims.

## Verification

- Inspect cited commits and maintainer comments through GitHub API.
- Run Markdown lint over new and modified Markdown, public-safe diff scan, and `git diff --check`.
- Run the repository audit validator and full local quality suite because the reports constrain future registry and execution decisions.
