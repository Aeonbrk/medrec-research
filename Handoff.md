# Handoff: Idea 008 Gate 01 Implementation / Mechanical Preflight Authorized

## Current state

- **Current Stage**: `IDEA_008_GATE_01_IMPLEMENTATION_MECHANICAL_PREFLIGHT_AUTHORIZED`
- **Active Idea**: `008-budgetset-residual-budget-marginal-ddi-set-refinement`
- **Gate 01 protocol**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-protocol.md`
- **Protocol revision**: `v1.2`
- **Protocol state**: `DESIGNED_NOT_EXECUTED / DESIGN_INTEGRITY_PASS`
- **Implementation authorization**: `research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-implementation-authorization.md`
- **Implementation**: `AUTHORIZED_NOT_STARTED`
- **Mechanical preflight**: `AUTHORIZED_NOT_RUN`
- **Formal recommendation-model training**: `NOT_AUTHORIZED`
- **Formal Gate execution**: `NOT_AUTHORIZED`
- **Gate01-Audit**: `UNOPENED`
- **Quarantine**: intact; G3/G4, R0 Holdout, and historical project test remain outside this phase
- **Implementation owner**: local coding agent
- **Next owner after successful preflight**: independent implementation/protocol verifier, then `ccf-pipeline-orchestrator`

## Routing decision

Protocol v1.2 has already passed independent design-integrity re-audit. The pipeline therefore advances only to bounded implementation and mechanical preflight. The design and integrity review are not reopened.

The local coding agent is authorized to implement the minimum Idea-local code needed to realize protocol v1.2 and to run mechanical tests that establish deterministic implementation faithfulness. It is not authorized to train BudgetSet or Independent, select real-run checkpoints or hyperparameters, open Gate01-Audit, produce scientific Gate evidence, or issue a PASS/KILL Gate verdict.

The exact implementation and access boundary is frozen in:

`research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate-01-implementation-authorization.md`

## Frozen implementation boundary

The implementation must preserve the protocol's admitted scientific identity, including:

```text
q0
-> c0, rho0
-> z1, q1
-> c1, rho1
-> z2
-> exact TopK(K_x)
```

with the explicit `+s_i` residual anchor and recomputation after the first update. BudgetSet and Independent must receive `s_i(x)` and `e_i(x)` from the same pinned frozen MoleRec forward, where `e_i(x)` is `molecule_embeddings[i]` immediately before `score_extractor`.

A narrow frozen-backbone integration check may use the existing Comparison-qualified `molerec-embedding` checkpoint on canonical Comparison Train only, strictly to establish shared-forward provenance, `eval()` / no-gradient behavior, and 131-candidate tensor alignment. It may not generate scientific utility/DDI evidence.

## Mechanical preflight result semantics

Successful implementation faithfulness may be recorded only as:

```text
MECHANICAL_PREFLIGHT_PASS
```

A frozen-contract mismatch yields:

```text
STOP_IMPLEMENTATION_MISMATCH
```

Neither state is a scientific Gate result.

## Routing

```text
Idea 008: ADMITTED
Gate 01 protocol v1.2: DESIGN_INTEGRITY_PASS / DESIGNED_NOT_EXECUTED
Stage: IDEA_008_GATE_01_IMPLEMENTATION_MECHANICAL_PREFLIGHT_AUTHORIZED
Implementation: AUTHORIZED_NOT_STARTED
Mechanical preflight: AUTHORIZED_NOT_RUN
Formal training: NOT_AUTHORIZED
Formal Gate execution: NOT_AUTHORIZED
Gate01-Audit: UNOPENED
Quarantine: intact
Current implementation owner: local coding agent
After successful preflight: independent implementation/protocol verification
Then: ccf-pipeline-orchestrator
```
