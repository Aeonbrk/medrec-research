<!-- markdownlint-disable MD013 -->

# Research Organization

This directory manages the scientific lifecycle:

`bounded pre-Idea admission when necessary -> idea optimization/review -> Idea -> Minimal Experiment -> Evidence -> Decision -> Paper`.

## Core policy

The project targets its first formal method paper at at least a CCF-A Data/Mining/AI venue family. Genuine new models and mechanisms are allowed; pure benchmark/measurement/survey work, indefinite diagnostics, and feature fishing are not acceptable terminal outcomes. The strongest simple or equal-entitlement control precedes method storytelling.

## Directory structure

- `ideas/`: admitted method hypotheses and bounded hypothesis-selection experiments.
- `memory/`: cross-Idea reusable lessons and historical research-space records.
- `premise-audit/`: bounded premise tests; not a standing exploratory lane.
- `baselines/`: reproduction/comparison infrastructure, separate from scientific Idea failures.

## Current scientific state

- **Stage**: `IDEA_008_GATE_01_DESIGN_INTEGRITY_FAIL_PENDING_PROTOCOL_CORRECTION`.
- **Active Idea**: [`008-budgetset-residual-budget-marginal-ddi-set-refinement`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/README.md).
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`.
- **Gate 01 protocol v1.1**: `DESIGN_INTEGRITY_FAIL`, not executed.
- **Gate 01 protocol**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md).
- **Historical v1.0 audit**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-audit.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-audit.md).
- **v1.1 re-audit**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-reaudit-v1.1.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-reaudit-v1.1.md).
- **Implementation**: `NOT_STARTED`.
- **Formal recommendation-model training**: `NOT_AUTHORIZED`.
- **Experiment execution**: `NOT_AUTHORIZED`.
- **Gate01-Audit**: unopened.
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside the Gate.
- **Next routing**: `ccf-experiment-designer / design` for one bounded B6 empty-frontier favorable-seed correction, followed by `ccf-integrity-auditor` re-audit.

Idea 008 remains admitted for one bounded kill-first method cycle. No empirical Gate result exists. Protocol v1.1 must not be implemented, trained, or executed until the remaining B6 blocker is corrected, independently re-audited, and execution is explicitly authorized.

## Active Idea 008 boundary

Working name: **BudgetSet: Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement**.

The admitted claim is:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The scientific interaction under test remains:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

The v1.1 re-audit passes the residual anchor, exact MoleRec representation, deterministic patient split, low-cardinality execution, learned checkpoint/configuration selection, and terminal precedence. The sole remaining blocker is within seed-robustness semantics when a seed-specific eligible control frontier is empty; `F_C(R_{B,r})` is then undefined while favorable seed is still defined through `G_{r,C}=U_{B,r}-F_C(R_{B,r})`.

Primary killers remain:

1. **Fixed-K Budget-Aware Greedy + 1-Swap** under identical frozen scores, DDI information, candidate pool, target, and exact cardinality.
2. **Budget-Conditioned Independent Scorer** with comparable learned capacity and the same frozen residual score anchor, but no current-set marginal interaction or iterative feedback.

`rho` is relaxed surrogate slack, not a clinical guarantee. Final hard-set achieved DDI is the operating-point quantity.

## Historical closed state

Ideas 001--007 remain terminated. Idea 007 remains `TERMINATED_AT_GATE_01_P1`. The strict drug-changing Pair/Context route remains `ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE`. Idea 008 reopens neither route.

`memory/research-space-reorientation.md` is a historical pre-Idea-008 reorientation record and must not override the current state in this file, `Handoff.md`, or the active Idea record.

## Quarantine

Until a later explicit authorization, do not inspect or use:

- MIMIC-IV G3/G4 future reserve;
- R0 Holdout;
- historical project test split.

Gate01-Audit remains unopened.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.1: DESIGN_INTEGRITY_FAIL / NOT EXECUTED
Stage: IDEA_008_GATE_01_DESIGN_INTEGRITY_FAIL_PENDING_PROTOCOL_CORRECTION
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Next owner: ccf-experiment-designer / design
Next task: bounded B6 empty-frontier favorable-seed correction only
After correction: ccf-integrity-auditor re-audit
After a future integrity pass only: ccf-pipeline-orchestrator may decide execution authorization
```
