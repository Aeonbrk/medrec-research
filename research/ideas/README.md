<!-- markdownlint-disable MD013 -->

# Early-Stage Research Ideas

Each Idea is one admitted, focused scientific line before it graduates to a paper project or is terminated. The project optimizes expected scientific value per unit research time.

A genuinely new model/architecture is allowed when it instantiates an admitted scientific mechanism. A new backbone over a failed premise is not a new Idea.

## Invariants

Every active Idea must state:

1. core hypothesis;
2. strongest simple alternative;
3. next minimal falsification experiment;
4. existing literature/project evidence;
5. current verdict.

Idea-stage prototypes stay inside the Idea until stable reusable infrastructure is justified. Untouched holdout/test data remain inaccessible until a later frozen claim-support protocol authorizes them.

## Ideas index

| ID | Title | Status | Terminal reason |
| :--- | :--- | :--- | :--- |
| [`001-tension-guided-verification`](001-tension-guided-verification/README.md) | Tension-Guided Verification | **Terminated** | no incremental constraint signal beyond recommender confidence / strong scalar control |
| [`002-score-geometry-sufficiency`](002-score-geometry-sufficiency/README.md) | Score-Geometry Sufficiency | **Terminated** | score geometry was ordering-equivalent and supplied no new routing information |
| [`003-prescription-relative-confidence`](003-prescription-relative-confidence/README.md) | Prescription-Relative Confidence Residual | **Terminated** | relative/rank features failed after expanded strong control |
| [`004-co-selection-compatibility`](004-co-selection-compatibility/README.md) | Frequency-Corrected Co-Selection Compatibility | **Terminated** | NPMI co-selection scalar added no reliable incremental value |
| [`005-safety-substitution-structure`](005-safety-substitution-structure/README.md) | Safety-Preserving Substitution Structure | **Terminated** | ATC structure failed therapeutic semantic admission |
| [`006-exposure-conditional-medication-recommendation`](006-exposure-conditional-medication-recommendation/README.md) | Exposure-Conditional Medication Recommendation | **Terminated** | learned exposure-conditioned method failed equal-entitlement direct-reranker challenge |
| [`007-privileged-physiological-response-supervision`](007-privileged-physiological-response-supervision/README.md) | Privileged Physiological Response Supervision | **Terminated at Gate 01 P1** | insufficient / materially concentrated response support under frozen floors; no rescue |
| [`008-budgetset-residual-budget-marginal-ddi-set-refinement`](008-budgetset-residual-budget-marginal-ddi-set-refinement/README.md) | BudgetSet: Residual-Budget Marginal-DDI Fixed-Cardinality Set Refinement | **Admitted / Gate 01 design pending** | — |

## Current project state

Idea 008 is the active admitted Idea.

- **Stage**: `IDEA_008_ADMITTED_PENDING_GATE_01_DESIGN`.
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`.
- **Formal admission**: `ACCEPT_TO_CREATE_IDEA_008`.
- **Reviewer confidence**: medium-high.
- **Admission owner**: `ccf-pipeline-orchestrator`.
- **Admission source revision**: `0be7c5c30762b232cd47a0c2ccf9b08aee1b23b5`.
- **Ideas 001--007**: terminated.
- **Pair/Context**: `ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE`.
- **Gate 01 design**: not yet frozen.
- **Formal training**: `NOT_AUTHORIZED`.
- **Quarantine**: intact.
- **Next owner**: `ccf-experiment-designer / design`.

The admitted claim is narrow:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

The scientific interaction under test is:

```text
requested residual constraint slack
× composition-dependent marginal DDI cost
× iterative fixed-K set refinement
```

The next Gate 01 must challenge this interaction before any architecture expansion or training story.

## Frozen Idea 008 killers

1. **Fixed-K Budget-Aware Greedy + 1-Swap** receives identical frozen recommendation scores, DDI information, candidate pool, requested DDI target, and exact per-patient cardinality. `Greedy+1Swap ≈ BudgetSet` terminates the method with `KILL_BUDGETSET`.
2. **Budget-Conditioned Independent Scorer** receives the same information entitlement. A comparable result terminates the joint-set interaction claim.

Exact MILP/MIQP is not a replacement for the first Gate-01 killer. It may be considered later only if the method survives and a paper-level efficiency/optimality comparison becomes necessary.

The residual budget signal on relaxed `q` is a surrogate constraint slack, not a clinical safety guarantee. Final hard-set achieved DDI is the operating-point quantity. The `K_x < 2` pair-risk domain remains for the Gate 01 protocol to define before execution.

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
