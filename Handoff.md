# Handoff

Updated: 2026-09-18.

```text
Current phase: ARCHITECTURE SEARCH — POST-ROUTEFACT FAMILY RESET
Paper Experiment Contract: v1.0 + v1.1 amendment CURRENT
Active formal Idea: none
Idea 009: absent
Active formal Gate: none
New Test access: not authorized
Available concurrent GPU capacity: 8 × RTX 3090-class
```

Read first:

- `AGENTS.md`
- `research/AGENTS.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-18-dcpm-mechanism-screen-falsification.md`
- `research/memory/decisions/2026-09-18-routefact-bounded-screen-authorization.md`
- `research/memory/decisions/2026-09-18-routefact-mechanism-screen-falsification.md`
- `research/prototypes/routefact/README.md`

## Current evidence

Medication-specific local evidence selection (DrugQuery) remains the strongest surviving positive mechanism.

Two bounded mechanism screens have been executed and falsified under the frozen Train/Dev protocol:

1. **DCPM (Drug-Conditioned Precedent Memory)**: Seed `20260921`, 60 complete epochs. Tested candidate-specific query attention over cross-patient Train precedents. Dev Jaccard `0.542203` vs `0.543606` for SharedPrecedent (`Delta J = -0.001403`, `Delta DDI = +0.002181`). Falsified and terminated (`KILL_DCPM_MECHANISM`).
2. **RouteFact (Route-Factored Medication Recommendation)**: Seed `20260922`, 60 complete epochs, source revision `8eee27ad88b63990cc8f1c5355b4a47bd84c7923`. Tested noisy-OR route factorization over Train-supported multi-hot administration routes. Dev Jaccard `0.534931` vs `0.543183` for RouteAux (`Delta J = -0.008252`, `Delta F1 = -0.006919`, `Delta PRAUC = -0.005145`, `Delta DDI = -0.001539`, `Delta AvgMed = +0.115149`). Falsified and terminated (`KILL_ROUTEFACT_MECHANISM`).

Both arms in RouteFact strictly followed the Train-only route contract: Dev raw route labels were not read (`no dev_route_targets.npy`), parameter counts exactly matched (914,497 parameters), and Test remained completely sealed. No route taxonomy merge, route-loss sweep, dose extension, second seed, or RouteFact-v2 is authorized.

## Next action

1. RouteFact is closed. The intermediate noisy-OR route factorization hypothesis is falsified.
2. The next research step requires an architecture-family reset outside candidate-conditioned precedent retrieval (DCPM) and route-level factorization (RouteFact).
3. Detached baseline recovery can continue independently, but must not delay architecture decisions. Test remains sealed.
