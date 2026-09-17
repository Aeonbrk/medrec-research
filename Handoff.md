# Handoff

Updated: 2026-09-18.

```text
Current phase: ARCHITECTURE SEARCH — ROUTEFACT BOUNDED SCREEN
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
- `research/prototypes/routefact/README.md`

## Current evidence

Medication-specific local evidence selection (DrugQuery) remains the strongest surviving positive mechanism. DCPM completed its frozen two-arm Train/Dev screen and was killed: Dev Jaccard `0.542203` vs `0.543606` for SharedPrecedent, `Delta J = -0.001403`, with no safety gain. Do not rescue DCPM or reinterpret it as a universal claim that medication-conditioned retrieval can never work.

The next family reset is **RouteFact**. It does not extend DrugQuery retrieval/routing. It changes the supervised intermediate prediction object from a flat medication label to a medication-conditioned **multi-hot administration-route set**, then tests whether medication presence should be forced through that route-level factorization.

This is not a revival of the terminated RxUnitSet target. RxUnitSet required a unique stable `(drug,dose,route)` unit or causally aligned prescription episode. RouteFact uses only route, permits multiple routes for one medication/admission, and reuses existing supportability evidence showing near-complete route observability and non-trivial per-medication route variation.

## Frozen screen

Two arms only, seed `20260922`, 60 complete epochs, `mimic-iii-canonical-131-paper-dev-v1`, Train/Dev only:

- `route_aux`: ordinary DrugQuery medication head is the decision path; the identical medication-route head receives auxiliary Train route supervision.
- `route_fact`: the same medication-route logits are the decision path; medication probability is noisy-OR over Train-supported route coordinates.

Both arms share the same DrugQuery substrate, route head, Train-only route vocabulary/support mask, route labels, loss weights, optimizer, and parameter count. Dev raw route labels are not read. Dev is used only for the frozen medication-set evaluator and checkpoint/threshold selection. Test remains sealed.

Decision rule:

```text
Delta J <= +0.002                         -> KILL_ROUTEFACT_MECHANISM
+0.002 < Delta J <= +0.004               -> WEAK_ROUTEFACT_SIGNAL_STOP_NO_RESCUE
Delta J > +0.004 with F1/PRAUC >= -0.002 -> advance
Delta J >= +0.008                         -> strong signal
```

No route taxonomy merge, route-loss sweep, dose extension, second seed, or RouteFact-v2 after a negative result.

## Next action on 319

1. Pull the final `origin/main` revision and require a clean checkout.
2. Materialize private Train-only route targets with `research/prototypes/routefact/build_route_targets.py` exactly as documented in the RouteFact README. Keep all dense targets outside Git.
3. Run both `route_aux` and `route_fact` preflights through `run_routefact_trainonly.py`. Require identical parameter counts and route-target hash, exact split counts, finite forward/backward, and `test_loaded=false`.
4. If preflight passes, launch both 60-epoch arms concurrently on two RTX 3090s. Do not stop based on partial Dev values unless there is a clear implementation fault.
5. Run `summarize_routefact.py` only after both arms complete. Apply its frozen decision directly.
6. Commit only public-safe aggregate comparison/decision evidence. Do not commit checkpoints, logits, dense route targets, raw prescription rows, patient IDs, or admission IDs.

Detached baseline recovery can continue independently, but it must not delay this matched mechanism screen and partial baseline values must not be promoted.
