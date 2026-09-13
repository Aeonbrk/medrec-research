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

- **Stage**: `IDEA_008_GATE_01_RUNNER_INTEGRITY_FAIL_PENDING_BOUNDED_CORRECTION`.
- **Active Idea**: [`008-budgetset-residual-budget-marginal-ddi-set-refinement`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/README.md).
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`.
- **Gate 01 protocol v1.2**: `DESIGN_INTEGRITY_PASS`, `DESIGNED_NOT_EXECUTED`.
- **Mechanical preflight**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-mechanical-preflight.json`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-mechanical-preflight.json), verdict `MECHANICAL_PREFLIGHT_PASS`.
- **Independent implementation verification**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-implementation-integrity-verification.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-implementation-integrity-verification.md), verdict `IMPLEMENTATION_INTEGRITY_PASS`.
- **Formal execution authorization**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-execution-authorization.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-execution-authorization.md), verdict `FORMAL_GATE_01_EXECUTION_AUTHORIZED`.
- **Runner integrity verification**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-runner-integrity-verification.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-runner-integrity-verification.md), verdict `RUNNER_INTEGRITY_FAIL`.
- **Execution-specific learned runner**: `IMPLEMENTED / BOUNDED_CORRECTION_REQUIRED`.
- **Formal recommendation-model training**: `NOT_AUTHORIZED`.
- **Gate01-Audit**: unopened.
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside the Gate.
- **Next owner**: local coding agent.

Idea 008 remains admitted for one bounded kill-first method cycle. No scientific Gate result exists. Protocol v1.2, design integrity, the mechanical-preflight surface, and the formal execution authorization remain valid. The runner-integrity failure is implementation-local and does not reopen the scientific design.

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

The current correction is limited to two runner responsibilities: device-consistent learned execution and runner-owned closure of the exact four-configuration/three-seed Dev-selection procedure. No protocol, architecture, objective, seed, budget, control, metric, or data-boundary change is authorized.

Recommendation-model training remains withheld until the corrected runner passes independent integrity verification. Gate01-Audit remains unopened until all Train/Dev selection is frozen, after which it may be used only for terminal evaluation under protocol v1.2.

## Historical closed state

Ideas 001--007 remain terminated. Idea 007 remains `TERMINATED_AT_GATE_01_P1`. The strict drug-changing Pair/Context route remains `ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE`. Idea 008 reopens neither route.

`memory/research-space-reorientation.md` is a historical pre-Idea-008 reorientation record and must not override the current state in this file, `Handoff.md`, or the active Idea record.

## Quarantine

Do not inspect or use:

- MIMIC-IV G3/G4 future reserve;
- R0 Holdout;
- historical project test split.

Gate01-Audit remains unopened at the current stage.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / DESIGNED_NOT_EXECUTED
Mechanical preflight: MECHANICAL_PREFLIGHT_PASS
Implementation integrity: IMPLEMENTATION_INTEGRITY_PASS
Formal Gate execution phase: AUTHORIZED
Runner integrity: RUNNER_INTEGRITY_FAIL
Formal training: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Stage: IDEA_008_GATE_01_RUNNER_INTEGRITY_FAIL_PENDING_BOUNDED_CORRECTION
Next owner: local coding agent
```
