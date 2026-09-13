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

- **Stage**: `IDEA_008_GATE_01_IMPLEMENTATION_INTEGRITY_PASS_PENDING_PIPELINE_ROUTING`.
- **Active Idea**: [`008-budgetset-residual-budget-marginal-ddi-set-refinement`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/README.md).
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`.
- **Gate 01 protocol v1.2**: `DESIGN_INTEGRITY_PASS`, `DESIGNED_NOT_EXECUTED`.
- **Gate 01 protocol**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md).
- **Implementation authorization**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-implementation-authorization.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-implementation-authorization.md).
- **Mechanical preflight**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-mechanical-preflight.json`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-mechanical-preflight.json), verdict `MECHANICAL_PREFLIGHT_PASS`.
- **Independent implementation verification**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-implementation-integrity-verification.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-implementation-integrity-verification.md), verdict `IMPLEMENTATION_INTEGRITY_PASS`.
- **Historical v1.0 audit**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-audit.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-audit.md), verdict `DESIGN_INTEGRITY_FAIL`.
- **Historical v1.1 re-audit**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-reaudit-v1.1.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-reaudit-v1.1.md), verdict `DESIGN_INTEGRITY_FAIL`.
- **v1.2 re-audit**: [`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-reaudit-v1.2.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-reaudit-v1.2.md), verdict `DESIGN_INTEGRITY_PASS`.
- **Implementation / mechanical preflight**: `COMPLETE / MECHANICAL_PREFLIGHT_PASS`.
- **Formal recommendation-model training**: `NOT_AUTHORIZED`.
- **Formal Gate execution**: `NOT_AUTHORIZED`.
- **Gate01-Audit**: unopened.
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside the Gate.
- **Next owner**: `ccf-pipeline-orchestrator`.

Idea 008 remains admitted for one bounded kill-first method cycle. No empirical Gate result exists. Protocol v1.2 passed independent design-integrity audit, and the authorized implementation/mechanical-preflight surface now also passes independent verification. This does not authorize model training, Gate01-Audit access, or formal Gate execution.

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

The v1.2 re-audit confirms B1–B7 PASS. The implementation verification confirms that the frozen recurrence, exact-cardinality semantics, control comparators, matched-seed logic, patient-cluster bootstrap semantics, and terminal precedence are mechanically represented, and that the pinned MoleRec `s_i/e_i(x)` integration is real-backbone validated on canonical Comparison Train only.

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
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / DESIGNED_NOT_EXECUTED
Stage: IDEA_008_GATE_01_IMPLEMENTATION_INTEGRITY_PASS_PENDING_PIPELINE_ROUTING
Implementation/mechanical preflight: COMPLETE / MECHANICAL_PREFLIGHT_PASS
Independent implementation verification: IMPLEMENTATION_INTEGRITY_PASS
Formal training: NOT_AUTHORIZED
Formal Gate execution: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Next owner: ccf-pipeline-orchestrator
Next task: decide formal Gate-execution authorization only; do not execute Gate 01 automatically
```
