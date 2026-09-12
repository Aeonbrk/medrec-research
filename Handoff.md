# Handoff: Idea 008 Gate 01 Design Integrity Failed

## Current state

- **Current Stage**: `IDEA_008_GATE_01_DESIGN_INTEGRITY_FAIL_PENDING_PROTOCOL_CORRECTION`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 owner completed**: `ccf-experiment-designer / design`
- **Gate 01 design verdict**: `DESIGN_INTEGRITY_FAIL`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Integrity audit**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-audit.md`
- **Implementation**: `NOT_STARTED`
- **Formal recommendation-model training**: `NOT_AUTHORIZED`
- **Experiment execution**: `NOT_AUTHORIZED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside the Gate
- **Next owner**: `ccf-experiment-designer / design`
- **Next task**: bounded protocol correction for audit blockers B1--B7 only; do not train

## Frozen scientific question

> Under identical frozen recommendation scores, DDI information, candidate pool, requested DDI target, and exact per-patient medication cardinality, does residual-budget marginal-DDI joint set refinement provide incremental utility–DDI frontier value beyond cheap equal-information direct optimization and independent budget conditioning?

The admitted claim remains narrow:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The surviving scientific interaction remains:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

No empirical Gate result exists. Protocol v1.0 failed pre-execution integrity audit because execution-relevant semantics remain underdetermined or drifted from the admitted formulation.

## Required bounded correction

Only the following audit blockers may be corrected before re-audit:

1. restore the admitted explicit frozen-score residual anchor for both learned families;
2. freeze the exact MoleRec medication representation used as `e_i` and its extraction point;
3. freeze a mechanically reproducible Gate01-Dev / Gate01-Audit patient hash formula;
4. define Greedy+1Swap behavior for `K_x=0` and `K_x=1`;
5. freeze learned checkpoint-selection and patience semantics;
6. freeze target/composition aggregation, bootstrap frontier recomputation, and seed semantics;
7. freeze one primary terminal-verdict precedence order.

This is a protocol correction, not a method redesign. Do not add a backbone, solver family, loss, budget, seed, dataset, encoder, or rescue mechanism.

## Authorization boundary

Do not perform:

- model implementation for Gate execution;
- recommendation-model training or Gate execution;
- G3/G4, R0 Holdout, or historical project test access;
- subgroup mining or feature fishing;
- architecture expansion;
- extra solver families, losses, targets, or seeds;
- paper-level SOTA benchmarking.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.0: DESIGN_INTEGRITY_FAIL / NOT EXECUTED
Stage: IDEA_008_GATE_01_DESIGN_INTEGRITY_FAIL_PENDING_PROTOCOL_CORRECTION
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Quarantine: intact
Next owner: ccf-experiment-designer / design
Next task: bounded protocol correction for B1-B7 only
After correction: ccf-integrity-auditor re-audit
After a future integrity pass only: ccf-pipeline-orchestrator may decide execution authorization
```