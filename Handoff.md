# Handoff: Idea 008 Gate 01 Protocol Corrected, Pending Integrity Re-audit

## Current state

- **Current Stage**: `IDEA_008_GATE_01_PROTOCOL_CORRECTED_PENDING_INTEGRITY_REAUDIT`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.1`
- **Protocol state**: `DESIGNED_NOT_EXECUTED / PENDING_INTEGRITY_REAUDIT`
- **Historical integrity audit**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-design-integrity-audit.md`
- **Implementation**: `NOT_STARTED`
- **Formal recommendation-model training**: `NOT_AUTHORIZED`
- **Experiment execution**: `NOT_AUTHORIZED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside the Gate
- **Gate01-Audit**: unopened
- **Next owner**: `ccf-integrity-auditor`
- **Next task**: independent pre-execution integrity re-audit of corrected protocol v1.1

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

## Corrected protocol boundary

Protocol v1.1 contains only the bounded pre-execution corrections authorized after the prior integrity audit:

1. explicit frozen-score residual anchor restored for BudgetSet and Independent;
2. `e_i(x)` frozen to the pinned MoleRec `molecule_embeddings[i]` immediately before `score_extractor`, from the same no-grad forward as `s_i`;
3. Idea-local Dev/Audit patient split frozen to one SHA-256 membership formula using namespace `idea008-gate01-v1`;
4. deterministic Greedy branches frozen for `K_x=0` and `K_x=1`;
5. per-seed checkpoint, patience, and configuration-selection nesting frozen;
6. visit observation, patient-cluster bootstrap, learned-seed aggregation, composition response, frontier recomputation, and favorable-seed semantics frozen;
7. one top-to-bottom primary terminal-verdict precedence frozen.

No backbone, architecture, solver, loss, budget, seed, dataset, tuning dimension, or scientific claim has been added.

## Authorization boundary

Do not perform:

- Gate implementation;
- recommendation-model training or Gate execution;
- Gate01-Audit access before re-audit authorization;
- G3/G4, R0 Holdout, or historical project test access;
- subgroup mining or feature fishing;
- architecture expansion;
- extra solver families, losses, targets, seeds, or tuning dimensions;
- paper-level SOTA benchmarking.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.1: CORRECTED / DESIGNED_NOT_EXECUTED
Integrity state: PENDING_REAUDIT
Stage: IDEA_008_GATE_01_PROTOCOL_CORRECTED_PENDING_INTEGRITY_REAUDIT
Implementation: NOT_STARTED
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Quarantine: intact
Gate01-Audit: UNOPENED
Next owner: ccf-integrity-auditor
Next task: independent re-audit of protocol v1.1
After a future integrity pass only: ccf-pipeline-orchestrator may decide execution authorization
```
