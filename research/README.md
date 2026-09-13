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

- **Stage**: `IDEA_008_GATE_01_AUDIT_AUTHORIZED_PENDING_EXECUTION`.
- **Active Idea**: [`008-budgetset-residual-budget-marginal-ddi-set-refinement`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/README.md).
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`.
- **Gate 01 protocol v1.2**: `DESIGN_INTEGRITY_PASS`; Train/Dev complete, Audit authorized but not executed.
- **Mechanical preflight**: `MECHANICAL_PREFLIGHT_PASS`.
- **Independent implementation verification**: `IMPLEMENTATION_INTEGRITY_PASS`.
- **Runner integrity re-verification**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-runner-integrity-reverification.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-runner-integrity-reverification.md), verdict `RUNNER_INTEGRITY_PASS`.
- **Gate01-Train + Gate01-Dev**: `COMPLETE`.
- **Gate01-Audit authorization**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-audit-authorization.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-audit-authorization.md), state `AUTHORIZED_NOT_RUN`.
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside the Gate.
- **Next owner**: local execution agent.

Idea 008 remains admitted for one bounded kill-first method cycle. All Train-only and Dev selections are frozen. The only active scientific execution is the one-shot Gate01-Audit terminal evaluation under protocol v1.2; no new training or tuning is authorized.

## Active Idea 008 boundary

Working name: **BudgetSet: Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement**.

The admitted claim is:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate's composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The scientific interaction under test remains:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

Primary killers remain:

1. **Fixed-K Budget-Aware Greedy + 1-Swap** under identical frozen scores, DDI information, candidate pool, target, and exact cardinality.
2. **Budget-Conditioned Independent Scorer** with comparable learned capacity and the same frozen residual score anchor, but no current-set marginal interaction or iterative feedback.

`rho` is relaxed surrogate slack, not a clinical guarantee. Final hard-set achieved DDI is the operating-point quantity.

## Execution routing

Train/Dev is complete. Audit is authorized only for terminal evaluation with the frozen budgets, controls, fixed-lambda choices, learned configurations, and retained checkpoints. Audit cannot change any selection made on Train/Dev.

After Audit execution and protocol classification, stop and route the resulting public-safe record to `ccf-integrity-auditor` before any research decision or paper work.

## Historical closed state

Ideas 001--007 remain terminated. Idea 007 remains `TERMINATED_AT_GATE_01_P1`. The strict drug-changing Pair/Context route remains `ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE`. Idea 008 reopens neither route.

`memory/research-space-reorientation.md` is a historical pre-Idea-008 reorientation record and must not override the current state in this file, `Handoff.md`, or the active Idea record.

## Quarantine

Do not inspect or use:

- MIMIC-IV G3/G4 future reserve;
- R0 Holdout;
- historical project test split.

Gate01-Audit is the only newly authorized evaluation partition.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / TRAIN_DEV_COMPLETE / AUDIT_AUTHORIZED_NOT_RUN
Mechanical preflight: MECHANICAL_PREFLIGHT_PASS
Implementation integrity: IMPLEMENTATION_INTEGRITY_PASS
Runner integrity: RUNNER_INTEGRITY_PASS
Gate01-Train + Gate01-Dev: COMPLETE
Gate01-Audit: AUTHORIZED_NOT_RUN
Quarantine: intact
Stage: IDEA_008_GATE_01_AUDIT_AUTHORIZED_PENDING_EXECUTION
Next owner: local execution agent
```
