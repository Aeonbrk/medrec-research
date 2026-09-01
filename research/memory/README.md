<!-- markdownlint-disable MD013 -->

# Cross-Idea Research Memory

This directory stores curated, cross-idea reusable knowledge, negative lessons, and canonical memory carried from the `New-Search` archive (`commit 9971464`).

## Boundaries & Admission Policy

This directory is **not** a dumping ground for dead markdown files or idea-local scratchpads. Knowledge belongs here only if it satisfies one rule:

> **It has decoupled from its original idea and changes the design, controls, or evaluation of future research questions.**

- **Idea-specific findings** (e.g. why an ablation within a specific method scored lower) remain inside `research/ideas/<idea>/`.
- **Baseline reproduction quirks** (e.g. Table 2 metric variances) belong in `research/baselines/`.
- **Cross-idea principles** (e.g. "always test a strong global scalar control before claiming a context-conditioned selector") belong here.

## Navigation

- **[`reusable-lessons.md`](reusable-lessons.md)**: Authoritative cross-route methodological guardrails (e.g., leveling hard filters across baselines, separating diagnostic metrics from solvers, distinguishing percentage points from relative gains).
- **`failures/`**: Decisive negative cases whose failure mechanisms provide permanent methodological lessons:
  - [`crc-ps-r006--conformal-risk-certificate-exhaustion.md`](failures/crc-ps-r006--conformal-risk-certificate-exhaustion.md): Statistical certificate exhaustion on finite grids.
  - [`eg-ter-repair--hard-safety-filter-baseline-trap.md`](failures/eg-ter-repair--hard-safety-filter-baseline-trap.md): The "Hard-Safety Baseline Trap" (why unlevelled baselines overstate policy value).
  - [`egsf-selector--global-scalar-reranking-dominance.md`](failures/egsf-selector--global-scalar-reranking-dominance.md): Apparent selector gains absorbed by global scalar reranking under strict count matching.
- **[`accumulated-experience.md`](accumulated-experience.md)**: Lifecycle-aware ledger for every historical idea, experiment, and claim node from the archive.
- **[`literature-memory.md`](literature-memory.md)**: Canonical inventory of 21 paper cards and their archived prior-art threat boundaries.
- **[`archive-evidence-index.md`](archive-evidence-index.md)**: File-to-file provenance map back to the read-only `New-Search` commit.
