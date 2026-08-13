# Research Memory: HITL control console

## Current state

The project has strong immutable scientific records, Action Gate, H1/H2 types, a read-only/small-write production harness, and deterministic scheduling contracts. The missing capability is not another scientific schema. It is a production control-plane binding from current authority to one declared, durable, observable execution.

## Reusable lessons

- A terminal state is not a dependency success signal. Downstream work requires an explicit successful outcome and current bindings.
- Browser opacity is necessary but insufficient. The server must also resolve the opaque identifier against a closed declaration registry.
- Queue durability without scientific identity binding can resume the wrong experiment.
- H2 is not an initial execution credential. H1 freezes the work; H2 decides what follows evidence from that work.
- A compound cursor ordered by content digest is not a global event order. Reconnect requires a separate monotonic journal identity.
- Scientific exception handling and operational recovery are different. Only predeclared operational recovery can be automated.
- UI migration is valid only if behavior, focus, state semantics, and production evidence survive. Dependency replacement alone proves little.
- Source-native reproduction fixes source behavior, including inconvenient seed and checkpoint rules. Compatibility work cannot silently turn into method modification.

## Open blockers

- Real 319/data/GPU/time/cost/license/environment authorization.
- GAMENet SafeDrug-main fixed launch and verified 319 environment lock.
- GAMENet adapter smoke and readiness evidence.
- Remote/local accepted revision and data-root readiness.
- ARIS latest-candidate validation and atomic last-known-good activation.
- Independent production security, UI, research, and code reviews after implementation.

## Current execution semantics

- Normal lifecycle projection has nine states: `blocked`, `queued`, `submitting`, `running`, `monitoring`, `intake`, `review_pending`, `completed`, and `cancelled`.
- `failed` and `stuck` are explicit abnormal terminal projections with matching outcomes. They are not extra normal lifecycle phases, and neither counts as dependency success.
- The execution registry declares the initial lane and the stable final-five lane order. Browser input never selects or overrides either.
