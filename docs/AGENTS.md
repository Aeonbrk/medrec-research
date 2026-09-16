# Documentation subtree instructions

`docs/` describes how the repository works now. Keep current facts separate from historical causality.

## What belongs here

- `START_HERE.md`: navigation to authoritative current sources.
- `specs/`: current scientific/software contracts and additive protocol amendments.
- `playbooks/`: current operating procedures.
- `guides/`: durable methodological or usage guidance.
- `plans/`: implementation-ready plans for substantial engineering work.
- `PLANS.md`: short list of active multi-step engineering work only.
- `KNOWLEDGE_HOMES.md`: repository knowledge-ownership rules.

## What does not belong here

- Engineering decision history or rejected alternatives: use `.agents/notes/`.
- Scientific belief changes caused by experiment evidence: use `research/memory/decisions/`.
- Raw experiment evidence: keep it with the owning prototype/Idea/run.
- Historical handoff narratives: archive under `research/memory/archive/` when they still matter.

Evergreen docs should say what the current contract is, who owns it, and how to use it. Avoid maintaining history paragraphs such as “previously”, “we used to”, or “this replaced” unless the history is required to operate the current interface.

Do not hand-copy API inventories that can be read from code. Link to the owning module or spec instead.

## Plans

Use `docs/plans/` for substantial implementation plans. After completion, update current facts in the owning docs and record any durable engineering decision in `.agents/notes/`. Do not keep completed scientific experiment history in `docs/PLANS.md`.

## Size discipline

Do not impose one global word limit on all documentation: scientific protocols, evidence records, and specifications can legitimately be long. Keep live navigation and coordination documents small by giving each one a single responsibility. If a current-fact document turns into a historical narrative, split or archive the history rather than expanding the live file indefinitely.
