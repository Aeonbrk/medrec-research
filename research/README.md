<!-- markdownlint-disable MD013 -->

# Research Organization

This directory manages the scientific lifecycle:

`bounded pre-Idea admission when necessary -> idea optimization/review -> Idea -> Minimal Experiment -> Evidence -> Decision -> Paper`.

## Core policy

The project targets its first formal **method paper** at at least a CCF-A Data/Mining/AI venue family.

Allowed:

- genuinely new models/architectures;
- new supervision, representation, decision, state-transition, or information-flow mechanisms;
- bounded pre-Idea checks when a method premise cannot be established from literature alone.

Not acceptable as terminal outcomes:

- pure benchmark/measurement/survey work;
- indefinite diagnostic chains;
- months of feature fishing;
- swapping backbones over a failed scientific premise.

The strongest simple/equal-entitlement control precedes method storytelling.

## Directory structure

- `ideas/`: admitted method hypotheses and their bounded hypothesis-selection experiments.
- `memory/`: cross-Idea failure constraints, literature maps, and pre-Idea resets.
- `premise-audit/`: historical bounded premise tests; not a standing exploratory lane.
- `baselines/`: reproduction/comparison infrastructure, separate from scientific Idea failures.

## Current scientific state

- **Stage**: `IDEA_008_ADMITTED_PENDING_GATE_01_DESIGN`.
- **Active Idea**: [`008-budgetset-residual-budget-marginal-ddi-set-refinement`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/README.md).
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008` (medium-high reviewer confidence).
- **Admission owner**: `ccf-pipeline-orchestrator`.
- **Admission source revision**: `0be7c5c30762b232cd47a0c2ccf9b08aee1b23b5`.
- **Ideas 001--007**: terminated.
- **Idea 007**: `TERMINATED_AT_GATE_01_P1`.
- **Pair/Context execution**: `ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE`.
- **Gate 01 protocol for Idea 008**: not yet designed/frozen.
- **Formal recommendation-model training**: `NOT_AUTHORIZED`.
- **Quarantine**: intact; G3/G4, R0 Holdout, and the historical project test split remain uninspected.
- **Next routing**: `ccf-experiment-designer / design`.

Idea 008 is admitted for one bounded kill-first method cycle. Admission is a workflow decision, not publication evidence.

## Active Idea 008 boundary

Working name:

**BudgetSet: Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement**.

The admitted scientific claim is:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The surviving interaction is specifically:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

Generic joint set prediction, Pareto MedRec, DDI-aware loss, DDI targets, one-model/many-objectives, list-wise refinement, training-time safety coefficients, and generic preference conditioning are not novelty claims.

The residual `rho = b - R_DDI(q)` is a surrogate slack on the relaxed set representation. It is not a clinical safety guarantee. The achieved DDI of the final hard set is the operating-point quantity. The `K_x < 2` pair-risk domain must be frozen by the future Gate 01 protocol before execution.

Canonical Idea record:

[`ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/README.md`](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/README.md).

## Frozen Idea 008 killer controls

The next Gate 01 design must preserve two primary killers:

1. **Fixed-K Budget-Aware Greedy + 1-Swap** under identical frozen recommendation scores, DDI information, candidate pool, requested target, and exact cardinality. If it is comparable to BudgetSet, terminate with `KILL_BUDGETSET`.
2. **Budget-Conditioned Independent Scorer** with equal information entitlement. If it is comparable to BudgetSet, terminate the joint-set interaction claim.

Exact MILP/MIQP is not a replacement for the first killer at Gate 01. It can be considered later only if the Idea survives and a paper-level efficiency/optimality comparison becomes necessary.

The next owner must freeze the cheapest falsifiable protocol before any training or experiment execution.

## Historical closed state

Idea 007 remains closed after its frozen Gate 01 P1 supportability failure. The strict drug-changing Pair/Context route also remains closed after all five frozen incremental-value comparisons failed. Their evidence and reusable constraints remain under `memory/` and the Idea-007 directory; Idea 008 does not reopen either route.

Key historical records:

- [`ideas/007-privileged-physiological-response-supervision/`](ideas/007-privileged-physiological-response-supervision/)
- [`memory/failures/privileged-physiological-response-gate-01-p1--insufficient-support.md`](memory/failures/privileged-physiological-response-gate-01-p1--insufficient-support.md)
- [`memory/failures/strict-drug-changing-pair-context--no-incremental-value.md`](memory/failures/strict-drug-changing-pair-context--no-incremental-value.md)

## Routing

```text
Idea 008: ADMITTED
Active Idea: 008-budgetset-residual-budget-marginal-ddi-set-refinement
Stage: IDEA_008_ADMITTED_PENDING_GATE_01_DESIGN
Gate 01: NOT YET DESIGNED / NOT FROZEN
Training: NOT_AUTHORIZED
Quarantine: intact
Next owner: ccf-experiment-designer / design
Next task: freeze cheapest falsifiable Gate 01
```

## Quarantine

Until explicitly authorized by a later frozen claim-support protocol, do not inspect:

- MIMIC-IV G3/G4 future reserve;
- R0 Holdout;
- historical project test split.

## Navigation

- [Active Idea 008](ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/README.md)
- [Research-Space Reorientation](memory/research-space-reorientation.md)
- [Literature Opportunity Map](memory/literature-opportunity-map.md)
- [Cross-Idea Memory](memory/README.md)
- [Reusable Lessons](memory/reusable-lessons.md)
- [Ideas Index](ideas/README.md)
