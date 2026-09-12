# Handoff: Idea 008 Gate 01 v1.1 Integrity Re-audit Failed

## Current state

- **Current Stage**: `IDEA_008_GATE_01_DESIGN_INTEGRITY_FAIL_PENDING_PROTOCOL_CORRECTION`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.1`
- **Historical v1.0 audit**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-audit.md`
- **v1.1 re-audit**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-reaudit-v1.1.md`
- **Integrity verdict**: `DESIGN_INTEGRITY_FAIL`
- **Implementation**: `NOT_STARTED`
- **Formal recommendation-model training**: `NOT_AUTHORIZED`
- **Experiment execution**: `NOT_AUTHORIZED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside the Gate
- **Gate01-Audit**: unopened
- **Next owner**: `ccf-experiment-designer / design`
- **Next task**: bounded B6 empty-frontier favorable-seed correction only; do not train

## Frozen scientific question

> Under identical frozen recommendation scores, DDI information, candidate pool, requested DDI target, and exact per-patient medication cardinality, does residual-budget marginal-DDI joint set refinement provide incremental utility–DDI frontier value beyond cheap equal-information direct optimization and independent budget conditioning?

The admitted claim remains:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The scientific interaction remains:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

## Re-audit result

Protocol v1.1 closes B1–B5 and B7. B6 still contains one execution-blocking ambiguity: Section 11 permits a safer-than-entire-control-frontier case when the eligible control set is empty, while Section 12.2 defines seed favorability only through `G_{r,C}=U_{B,r}-F_C(R_{B,r})`. In the empty-set case `F_C` is undefined, so the `>=2/3` favorable-seed rule can produce different `KILL_SEED_FRAGILITY` / PASS outcomes across otherwise compliant implementations.

The only authorized correction is to define one deterministic sign-only seed-level comparator for that empty-frontier case for deterministic controls and matched Independent seeds. Do not alter the aggregate material-frontier criterion or reopen B1–B5/B7.

## Authorization boundary

Do not perform:

- Gate implementation;
- recommendation-model training or Gate execution;
- Gate01-Audit access;
- G3/G4, R0 Holdout, or historical project test access;
- subgroup mining or feature fishing;
- architecture expansion;
- extra solver families, losses, targets, seeds, budgets, or tuning dimensions;
- paper-level SOTA benchmarking.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.1: DESIGN_INTEGRITY_FAIL / NOT EXECUTED
Stage: IDEA_008_GATE_01_DESIGN_INTEGRITY_FAIL_PENDING_PROTOCOL_CORRECTION
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Quarantine: intact
Gate01-Audit: UNOPENED
Next owner: ccf-experiment-designer / design
Next task: bounded B6 empty-frontier favorable-seed correction only
After correction: ccf-integrity-auditor re-audit
After a future integrity pass only: ccf-pipeline-orchestrator may decide execution authorization
```
