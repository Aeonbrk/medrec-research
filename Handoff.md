# Handoff: Idea 008 Gate 01 Runner Integrity Failed / Bounded Correction Required

## Current state

- **Current Stage**: `IDEA_008_GATE_01_RUNNER_INTEGRITY_FAIL_PENDING_BOUNDED_CORRECTION`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.2`
- **Protocol state**: `DESIGNED_NOT_EXECUTED / DESIGN_INTEGRITY_PASS`
- **Mechanical preflight**: `COMPLETE / MECHANICAL_PREFLIGHT_PASS`
- **Implementation integrity**: `IMPLEMENTATION_INTEGRITY_PASS`
- **Formal Gate 01 execution phase**: `AUTHORIZED`
- **Execution-specific runner**: `IMPLEMENTED / BOUNDED_CORRECTION_REQUIRED`
- **Runner integrity**: `RUNNER_INTEGRITY_FAIL`
- **Formal recommendation-model training**: `NOT_AUTHORIZED`
- **Gate01-Audit**: `UNOPENED`
- **G3/G4**: `UNTOUCHED`
- **R0 Holdout**: `UNTOUCHED`
- **Historical project test**: `UNTOUCHED`
- **Quarantine**: intact
- **Next owner**: local coding agent

## Integrity result

The runner preserves the frozen BudgetSet/Independent equations, MLP widths, GELU/no-dropout architecture, objective, AdamW shell, frozen grids, checkpoint key, patience rule, and Dev-before-Audit boundary. No scientific-design regression was found.

Two execution-integrity blockers remain:

1. `train_seed_configuration(..., device=...)` moves the model to the requested device but does not move ordinary CPU/list `scores`, `embeddings`, budgets, DDI inputs, and Independent static summaries to that device before model execution. The frozen MoleRec extraction surface materializes public Python/CPU values, so the normal CUDA execution path is not closed.
2. The runner trains one `family × configuration × seed` and exposes configuration selection, but it does not own the required `4 configurations × 3 seeds` Dev-selection closure. `n_compliant_config`, `u_primary_config`, and `v_all_config` are accepted from the caller rather than derived by the runner from the three retained seed checkpoints. Formal selection therefore still depends on unverified downstream orchestration.

The local handoff reported `29 passed, 9 skipped`; the skips were PyTorch-dependent. After correction, the full targeted runner tests must execute under `medrec-molerec-table1` on 319, including the device path, before runner integrity can pass.

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
Next task: fix only the two runner-integrity blockers and rerun targeted runner verification; do not train or open Gate01-Audit
```
