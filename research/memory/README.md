# Research memory

This directory carries cross-project scientific context without replacing source-bound experiment evidence.

## Authority

When records disagree:

1. Run-local result JSON, audits, source-bound experiment README files, formal Idea artifacts, and frozen benchmark records describe what actually happened.
2. [`current-research-state.md`](current-research-state.md) is the live scientific synthesis and routing authority.
3. [`decisions/`](decisions/) contains append-only scientific belief updates that explain why project interpretation changed.
4. Root/research indexes and `Handoff.md` are navigation and handoff surfaces.
5. Failure records, dated literature/search packets, reset packets, and [`archive/`](archive/) are historical context.

Do not edit historical evidence to make an old state label look current. Update the live synthesis or add a new decision note.

## Directory roles

- `current-research-state.md`: concise current synthesis only.
- `decisions/`: append-only scientific belief updates linked to decisive evidence.
- `failures/`: durable records of falsified or demoted formulations.
- `archive/`: superseded live syntheses and mixed ledgers preserved for provenance.
- `reusable-lessons.md`: lessons supported across multiple routes.
- `accumulated-experience.md`: historical synthesis, not live routing authority.
- `literature-memory.md`, `literature-opportunity-map.md`, dated `literature-search-*` packets: discovery and prior-search provenance.
- `model-reset-*`, `resource-reset-*`, and other dated packets: scoped historical search/reset material.

## Epistemic labels

Current synthesis and scientific decision notes distinguish:

- **Observed result**: produced directly by a run, audit, or source review.
- **Interpretation**: scientific reading of one or more observed results.
- **Routing guidance**: what the project should prioritize next.

A routing recommendation is not a runner-produced verdict.

## Failure memory

A failure record should make it possible to answer:

```text
What exact formulation was tested?
What matched control absorbed or beat it?
What information budget and target semantics applied?
What should not be repeated unchanged?
What primitives remain reusable in a materially different mechanism?
```

Negative evidence is formulation-local unless a broader claim is directly tested.

Engineering architecture/dependency decisions are not stored here; they belong in `.agents/notes/`.
