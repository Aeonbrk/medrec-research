<!-- markdownlint-disable MD013 -->

# Baseline Research Infrastructure

This directory manages the external baseline models, reproduction audits, readiness preflights, and candidate pools.

## Purpose & Scope

Baseline reproduction and qualification belong to **research infrastructure**, not scientific idea exploration. Mismatches in published point estimates, environment setup interruptions, or upstream codebase quirks are operational/reproduction issues and are strictly decoupled from scientific idea failures.

## Directory Structure

- **`preflight/`**: Public-safe readiness reports, qualification records, and reference point targets:
  - [`five-model-baseline-readiness-report.md`](preflight/five-model-baseline-readiness-report.md): Two-axis readiness assessment for all 5 classical baselines.
  - [`five-model-comparison-qualification.json`](preflight/five-model-comparison-qualification.json): Public-safe Phase B qualification records under URP v1.1.
  - [`molerec-five-model-reproduction-report.md`](preflight/molerec-five-model-reproduction-report.md): Formal reproduction attempt audit report.
  - Reference targets: [`molerec-table1-reference.json`](preflight/molerec-table1-reference.json), [`safedrug-table2-reference.json`](preflight/safedrug-table2-reference.json).
- **`decisions/`**: Formal baseline authority and execution decisions:
  - [`molerec-five-model-reproduction-authority-2026-08-26.md`](decisions/molerec-five-model-reproduction-authority-2026-08-26.md): Settled decisions D1–D9 for the five-model suite.
- **`failures/`**: Operational and reproduction mismatch records:
  - [`gamenet-reproduction-2026-07-13.md`](failures/gamenet-reproduction-2026-07-13.md): Remote environment setup interruption and reconstruction boundaries.
  - [`safedrug-four-model-table2-mismatch-2026-08-26.md`](failures/safedrug-four-model-table2-mismatch-2026-08-26.md): Table 2 pilot reproduction mismatch (`completed_mismatch`).
  - [`safedrug-reproduction-b0-failure-2026-08-25.md`](failures/safedrug-reproduction-b0-failure-2026-08-25.md): Pilot execution failure history.
- **[`candidate-expansion-pool.md`](candidate-expansion-pool.md)**: Roadmap of candidate baselines for future Comparison Mode qualification (e.g. VITA, ARMR, FLAME, KEHGCN, HypeMed).

## Authoritative Baseline Identity

The single authoritative source of truth for baseline definitions, code entrypoints, Conda environments, and readiness states is [`../../baselines/registry.toml`](../../baselines/registry.toml).
