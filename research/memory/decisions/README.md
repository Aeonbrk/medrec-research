# Scientific decision notes

This directory stores append-only project-level scientific belief updates caused by evidence. It sits between run-local evidence and the short live synthesis in `../current-research-state.md`.

Write a decision note when one or more experiments materially change project interpretation or routing.

## Structure

```text
Context / Trigger
Decision / Belief Update
Rejected Alternatives / Interpretations
Consequences / Invariants
```

Link to decisive run-local evidence instead of copying full logs or tables. Distinguish observed evidence, interpretation, and routing guidance.

Decision notes do not replace result JSON, audits, formal Idea records, or benchmark manifests. If later evidence changes the conclusion, add a new note rather than rewriting the old one.

Engineering architecture and dependency decisions belong in `.agents/notes/`, not here.
