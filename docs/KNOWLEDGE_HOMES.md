# Knowledge homes

This repository separates current facts, engineering decisions, scientific evidence, scientific belief updates, and current-work handoff. They answer different questions and must not share one growing document.

| Question | Authoritative home | Update model |
| --- | --- | --- |
| How does the system work now? | `docs/`, `ARCHITECTURE.md`, `CONTEXT.md` | Update in place |
| Why was an engineering choice made? | `.agents/notes/` | Append-only decision notes |
| What did an experiment actually produce? | Owning `research/prototypes/`, `research/ideas/`, benchmark, audit, or run-local artifact | Immutable/source-bound evidence |
| What scientific belief changed because of evidence? | `research/memory/decisions/` | Append-only scientific decision notes |
| What does the project currently believe and prioritize? | `research/memory/current-research-state.md` | Short live synthesis |
| What should the next agent do now? | `Handoff.md` | Replace with the current handoff |
| What engineering work is active? | `docs/PLANS.md` and `docs/plans/` | Active tracker plus scoped plans |
| What is publication-facing claim support? | `papers/` | Survivor-only evidence package |

## Current facts

Evergreen documentation states the current contract, owner, interface, and operating procedure. It does not carry a chronological explanation of how the contract evolved. When a design changes, update the current-fact document and add a causal note if the decision is non-trivial.

## Engineering causality

`.agents/notes/` records durable engineering decisions: architecture boundaries, subsystem contracts, dependency choices, migrations, and meaningful trade-offs. Notes are append-only. Do not rewrite an old note because a later decision supersedes it; add a new note that explains the transition.

Engineering notes do not store scientific experiment conclusions. They may link to scientific evidence when that evidence caused an engineering decision.

## Scientific evidence and belief

Run-local evidence remains the authority for what happened. `research/memory/decisions/` records the project-level belief update caused by one or more runs, including rejected interpretations and consequences. `research/memory/current-research-state.md` then keeps only the live synthesis needed to route the next research step.

This separation prevents a routing recommendation from being mistaken for an experiment verdict and prevents historical negative results from becoming permanent method-family bans.

## Handoff

`Handoff.md` is intentionally disposable. Keep only the verified revision, stage, frozen current decisions, files to read, one active task, and stop conditions. Historical execution narratives belong in source-bound run records or `research/memory/archive/` if they still need preservation.

## Plans

`docs/PLANS.md` lists active multi-step engineering work only. Detailed implementation plans live in `docs/plans/`. Completed work should update the owning current docs; durable engineering rationale goes to `.agents/notes/`. Scientific experiment history does not belong in the plans ledger.

## No central note index

Do not maintain an `INDEX.md` for decision notes. Directory names and semantic filenames are the index. This avoids a merge-conflict hotspot when several agents add independent notes.

## Size discipline for a research repository

A blanket word-count limit is not appropriate here. Protocols, paper evidence, and source-bound scientific records can be long because their details are part of the evidence. The files that must stay small are live coordination surfaces: root/local `AGENTS.md`, `Handoff.md`, `docs/START_HERE.md`, `docs/PLANS.md`, and `research/memory/current-research-state.md`.

Use responsibility as the primary limit. If one live document starts answering both “what is true now?” and “why did we get here?”, archive the history and keep the live surface concise.
