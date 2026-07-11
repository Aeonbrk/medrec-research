# Plans

## Completed: bootstrap the MedRec Research Library

- **Status**: accepted and completed on `2026-07-10`; awaiting the user's first commit and remote decision.
- **Plan**: `docs/plans/2026-07-10-001-bootstrap-medrec-research.md`.
- **Goal**: create the independent active research home, prove one protocol vertical slice, preserve curated scientific memory, and leave `New-Search` as a non-destructive Research Archive.
- **Source archive**: `/Users/oian/Codes/master/New-Search` at commit `9971464253c556345262b22ed6d44b2cc14c9da8` plus documented uncommitted archive metadata.
- **Execution model**: the MacBook Air is the ARIS harness terminal; real EHR and GPU experiments run only on `319-wild` under isolated Conda environments.
- **Scientific correction**: final review rejected the plan's claim that the synthetic reference was `smoke_ready` Reproduction Mode evidence. ADR-0006 replaces that output with a non-evidentiary Protocol Check Record; no baseline is currently above `registered`.
- **Evidence**: 61 tests pass; Ruff check and format pass; `uv lock --check`, package build, Markdown lint, ARIS reconcile dry run, CodeGraph sync, registry parse, YAML parse, synthetic CLI smoke, and public-record privacy scan pass.
- **Residual unknowns**: upstream pins and licenses for unresolved baselines, real baseline adapters, verified 319 environment locks, the first upstream-specific Reproduction Mode record, the Git remote, and the 319 checkout.
- **Superseded next step**: this plan originally named the first immutable commit as the immediate next step. The accepted six-candidate benchmark program now requires a public source, license, and lineage audit first; the initial commit, remote, and 319 checkout remain separately authorized gates.

## Implemented: MedRec Baseline Benchmark Harness

- **Status**: local public-safe implementation completed on `2026-07-11`; baseline execution, 319 deployment, real data, environment creation, and experiments remain unauthorized.
- **Plan**: `docs/plans/2026-07-10-002-feat-medrec-benchmark-harness-plan.md`.
- **Goal**: establish a six-candidate portfolio for RETAIN, GAMENet, SafeDrug, MICRON, MoleRec, and the separately named `LEAP-SafeDrug` derivative before new-method discovery.
- **Scientific gates**: every candidate needs source, license, and four-layer lineage audit; shared lineage remains visible and does not create independent replication evidence.
- **Sequencing**: audit all candidates, select one first reproduction lane with a predeclared scorecard, stabilize it, then operate at most two isolated lanes in parallel. At four `comparison_ready` candidates, pause for human review; new-method discovery stays closed until all six are ready.
- **Harness boundary**: the loopback Web harness reads a project-owned public-safe status contract and emits gated action requests only. It cannot own scientific state, a database, restricted artifacts, or an execution surface.
- **Authorization boundary**: do not modify baseline sources or registry state, create a commit or remote, deploy to 319, access real data, create environments, or run experiments without a separate user instruction.
- **Current evidence**: all six audits validate; fixed-order selection proposes GAMENet; every registry entry remains `registered`; CLI/action/harness focused tests and Ruff pass.
