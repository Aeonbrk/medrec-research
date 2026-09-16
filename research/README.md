# Research organization

`research/` owns scientific exploration, evidence, formal Ideas, benchmarks, diagnostics, and cross-project research memory. Read `AGENTS.md` in this directory before changing scientific artifacts.

## Directory roles

- `prototypes/`: bounded pre-Idea architecture, mechanism, supportability, and calibration screens.
- `ideas/`: formal Ideas with frozen scientific contracts and their terminal evidence.
- `benchmarks/`: dataset/task contracts and public-safe benchmark records.
- `diagnostics/`: bounded diagnostics that can change a concrete scientific or training decision.
- `baselines/`: research-side baseline evidence/infrastructure that is distinct from the root executable baseline programs.
- `memory/`: live synthesis, scientific decisions, failure memory, literature/search provenance, and archived syntheses.
- `premise-audit/`: bounded premise checks retained for provenance; not a standing exploratory lane.

## Current state

Do not duplicate the live stage here. Read [`memory/current-research-state.md`](memory/current-research-state.md).

Run-local evidence remains authoritative for what an experiment actually did. The live synthesis reconciles that evidence for current routing. Historical packets do not override later evidence.

## Research progression

```text
search / premise
→ bounded prototype
→ decisive matched evidence
→ survive / redesign once / kill
→ formal Idea only when a frozen contract is worth the cost
→ paper package only after the mechanism earns claim-support rigor
```

Historical failures constrain equivalent formulations but do not ban whole method families by name. A strong positive component is a reusable building block, not automatically the mandatory backbone of the next model.

See [`../docs/KNOWLEDGE_HOMES.md`](../docs/KNOWLEDGE_HOMES.md) for the separation between scientific evidence, scientific belief updates, engineering decisions, and current documentation.
