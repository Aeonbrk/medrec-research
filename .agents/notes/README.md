# Engineering decision notes

This directory stores durable engineering causality for future maintainers and agents. It is not current documentation and it is not scientific evidence.

## When to write a note

Write a note for a non-trivial engineering decision such as:

- a new architecture or subsystem boundary;
- a stable interface or state-machine change;
- a dependency choice with meaningful trade-offs;
- a performance/complexity compromise;
- a migration or breaking protocol change.

Do not write a note for formatting, routine bug fixes, one-file cleanup, ordinary experiment outcomes, or temporary debugging history.

## Note structure

New notes use four sections:

```text
Context / Trigger
Decision
Rejected Alternatives
Consequences / Invariants
```

State unknown history as unknown. Do not invent rejected alternatives to make an old decision look more deliberate than the evidence supports.

## Immutability

Notes are append-only historical records. When a decision changes, add a new note describing the transition; do not rewrite the old note to match the new state.

Legacy `docs/adr/` records were moved into `architecture/` during the 2026-09-16 knowledge-home migration without changing their historical meaning. New notes should use dated semantic filenames where practical.

## Boundaries

- Current system facts: `docs/`, `ARCHITECTURE.md`, `CONTEXT.md`.
- Scientific run evidence: owning `research/` artifact.
- Scientific belief updates: `research/memory/decisions/`.
- Current work: `Handoff.md`.

Do not maintain a central note index. The directory structure and filenames are the navigation surface.
