# Handoff: Idea 008 Gate 01 v1.2 Corrected, Pending Integrity Re-audit

## Current state

- **Current Stage**: `IDEA_008_GATE_01_PROTOCOL_CORRECTED_PENDING_INTEGRITY_REAUDIT`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.2`
- **Protocol state**: `DESIGNED_NOT_EXECUTED / PENDING_INTEGRITY_REAUDIT`
- **Historical v1.0 audit**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-audit.md`
- **Historical v1.1 re-audit**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-reaudit-v1.1.md`
- **Implementation**: `NOT_STARTED`
- **Formal recommendation-model training**: `NOT_AUTHORIZED`
- **Experiment execution**: `NOT_AUTHORIZED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside the Gate
- **Gate01-Audit**: unopened
- **Next owner**: `ccf-integrity-auditor`
- **Next task**: independent pre-execution integrity re-audit of corrected protocol v1.2

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

## Bounded B6 correction

Protocol v1.2 changes only the seed-robustness comparator for the case where a BudgetSet seed has no eligible sampled control point under the frozen risk tolerance.

For each BudgetSet seed, primary region, and killer control, define the seed-specific eligible control set under the existing `delta_R` rule. When that set is non-empty, the existing favorable rule is unchanged: compare against the maximum-utility eligible control point and require positive utility gap.

When the eligible set is empty, select exactly one control reference endpoint by lexicographically minimizing hard-set DDI, then maximizing Jaccard, then using the existing deterministic control-point order (`b_L`, `b_M`, `b_H`). The seed is favorable iff its Jaccard is at least that endpoint's Jaccard; equality is favorable because the empty-frontier branch already guarantees a strict lower-risk direction.

This is a zero-margin direction-only seed-robustness rule. It does not alter Section 11's aggregate material-frontier criterion, the safer-than-entire-frontier aggregate branch, bootstrap semantics, the `>=2/3` robustness requirement, or any B1–B5/B7 definition. Greedy remains deterministic; Independent remains matched seed-by-seed. A required killer control with zero sampled operating points is an invalid Gate implementation under the existing `STOP_INVALID_GATE_IMPLEMENTATION` verdict.

## Authorization boundary

Do not perform:

- Gate implementation;
- recommendation-model training or Gate execution;
- Gate01-Audit access before re-audit authorization;
- G3/G4, R0 Holdout, or historical project test access;
- subgroup mining or feature fishing;
- architecture expansion;
- extra solver families, losses, targets, seeds, budgets, or tuning dimensions;
- paper-level SOTA benchmarking.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: CORRECTED / DESIGNED_NOT_EXECUTED
Integrity state: PENDING_REAUDIT
Stage: IDEA_008_GATE_01_PROTOCOL_CORRECTED_PENDING_INTEGRITY_REAUDIT
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Quarantine: intact
Gate01-Audit: UNOPENED
Next owner: ccf-integrity-auditor
Next task: independent re-audit of protocol v1.2
After a future integrity pass only: ccf-pipeline-orchestrator may decide execution authorization
```
