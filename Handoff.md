# Handoff: Idea 008 Gate 01 Design Frozen

## Current state

- **Current Stage**: `IDEA_008_GATE_01_DESIGN_FROZEN_PENDING_INTEGRITY_AUDIT`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Admission revision**: `f9ae328f1d46bc7146454678bce34a9176213788`
- **Gate 01 owner completed**: `ccf-experiment-designer / design`
- **Gate 01 design verdict**: `DESIGN_READY`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Formal recommendation-model training**: `NOT_AUTHORIZED`
- **Experiment execution**: `NOT_AUTHORIZED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside the Gate
- **Next owner**: `ccf-integrity-auditor`
- **Next task**: independent design/integrity audit; do not train

## Frozen scientific question

> Under identical frozen recommendation scores, DDI information, candidate pool, requested DDI target, and exact per-patient medication cardinality, does residual-budget marginal-DDI joint set refinement provide incremental utility–DDI frontier value beyond cheap equal-information direct optimization and independent budget conditioning?

The admitted claim remains narrow:

> At fixed prescription cardinality, a medication-set refiner amortizes target-conditioned utility–DDI optimization by repeatedly pricing each candidate’s composition-dependent marginal DDI cost as a function of the current relaxed constraint slack.

`rho` is surrogate relaxed slack, not a hard DDI or clinical safety guarantee. Final hard-set achieved DDI is the operating-point quantity.

## Gate 01 frozen choices

```text
Backbone:
MoleRec / molerec-embedding, frozen

Candidate pool:
complete 131-medication vocabulary for every method

K_x:
frozen MoleRec threshold-0.5 output count; never ground-truth count

K_x < 2:
R_DDI = 0 and c_i = 0

Initialization:
z^(0) = s; q^(0) = sigmoid(s)

Refinement:
T = 2; no T sweep

Budget support:
b_L = 0.60 * r_train
b_M = 0.80 * r_train
b_H = 1.00 * r_train
P_B = Uniform{b_L, b_M, b_H}

Primary utility:
Jaccard

Supporting utility:
F1, PRAUC

Seeds:
2002, 2003, 2004

Practical margins:
0.005 Jaccard
0.005 hard-set DDI rate
```

`T=2` is frozen because `T=1` would never recompute marginal DDI and residual slack after a changed provisional composition and therefore would not test the admitted iterative interaction.

## Frozen killers

1. **Fixed-K Budget-Aware Greedy + 1-Swap** receives identical `s`, `D`, candidate pool, `b`, and `K_x`. If it is comparable to or better than BudgetSet at either required primary region, or BudgetSet wins only one isolated region: `KILL_BUDGETSET`.
2. **Budget-Conditioned Independent Scorer** receives the same frozen patient-conditioned score and medication embedding plus requested `b` and Train-only static DDI summaries, with comparable learned capacity but no provisional-set composition or iterative feedback. Comparable/better performance terminates the joint-set interaction claim.

The supporting Fixed-lambda family uses six fixed lambda values and Train-only target calibration; it does not expand into a solver family.

## Pass boundary

A Gate pass requires exact cardinality, target compliance, material budget responsiveness, actual hard-set substitutions, two separated frontier wins against both killers, and non-one-seed-only support. The exact decision rules are authoritative only in the Gate protocol.

No pass means clinical safety, CCF-A readiness, or paper completion.

## Routing

```text
Idea 008: ADMITTED / GATE_01_DESIGN_FROZEN
Stage: IDEA_008_GATE_01_DESIGN_FROZEN_PENDING_INTEGRITY_AUDIT
Training: NOT_AUTHORIZED
Execution: NOT_AUTHORIZED
Quarantine: intact
Next owner: ccf-integrity-auditor
After integrity pass: ccf-pipeline-orchestrator for explicit execution authorization
```
