# Handoff: Idea 008 Gate 01 Execution Authorized Pending Runner Implementation

## Current state

- **Current Stage**: `IDEA_008_GATE_01_EXECUTION_AUTHORIZED_PENDING_RUNNER_IMPLEMENTATION`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.2`
- **Protocol state**: `DESIGNED_NOT_EXECUTED / DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: `COMPLETE / MECHANICAL_PREFLIGHT_PASS`
- **Implementation integrity**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Formal Gate 01 execution phase**: `AUTHORIZED`
- **Execution-specific training runner**: `REQUIRED / NOT_YET_IMPLEMENTED`
- **Runner implementation**: `AUTHORIZED`
- **Formal recommendation-model training**: `NOT_YET_AUTHORIZED`
- **Gate01-Audit**: `UNOPENED`
- **G3/G4**: `UNTOUCHED`
- **R0 Holdout**: `UNTOUCHED`
- **Historical project test**: `UNTOUCHED`
- **Quarantine**: intact
- **Next owner**: local coding agent

## Routing decision

Gate 01 v1.2 is scientifically execution-ready. No design-integrity or mechanical-preflight blocker remains.

The repository does not yet contain the execution-specific learned training runner required to realize the frozen BudgetSet and Independent MLPs, objective, optimizer, seed/hyperparameter sweep, Dev-only checkpoint/configuration selection, and Audit-only terminal evaluation. The existing `gate01_mechanical_preflight.py` intentionally provides protocol semantics and frozen MoleRec extraction but does not train either learned family.

Therefore the pipeline enters the formal Gate-execution phase, while actual recommendation-model training remains withheld until the new runner is implemented and checked against protocol v1.2. This is bounded downstream implementation, not a protocol redesign or a new experiment-design cycle.

The complete authorization boundary is frozen in:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-execution-authorization.md`

## Data boundary

Before runner integrity passes, no learned-family training is authorized and Gate01-Audit remains unopened.

After runner integrity passes, a separate routing step may activate:

- `Gate01-Train` for learned-family training and Train-only calibration;
- `Gate01-Dev` for epoch/checkpoint/configuration selection exactly as protocol v1.2 defines;
- `Gate01-Audit` only after all Train/Dev selections are frozen, and only for evaluation, bootstrap, frontier comparison, and terminal verdict generation.

Gate01-Audit must never influence epoch, seed, checkpoint, configuration, or hyperparameter selection. G3/G4, R0 Holdout, and historical project test remain outside Gate 01.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / DESIGNED_NOT_EXECUTED
Mechanical preflight: MECHANICAL_PREFLIGHT_PASS
Implementation integrity: IMPLEMENTATION_INTEGRITY_PASS
Formal Gate execution phase: AUTHORIZED
Runner implementation: AUTHORIZED / REQUIRED
Formal recommendation-model training: NOT_YET_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Stage: IDEA_008_GATE_01_EXECUTION_AUTHORIZED_PENDING_RUNNER_IMPLEMENTATION
Next owner: local coding agent
Next task: implement and mechanically verify the frozen execution runner only; do not train or open Gate01-Audit
```
