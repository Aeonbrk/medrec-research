# Knowledge-home migration adversarial review passed

## Context / Trigger

Commit `3c420eb0d810c10f629f575495a767aef5698436` reorganized repository knowledge by separating current engineering facts, engineering decision causality, scientific run evidence, scientific belief updates, live scientific synthesis, and current-work handoff.

An independent local-agent review compared it with parent `de2b3246947426d7d832c8f30a4a21b261071590`. The review returned `PASS` with no blocker, major, or minor findings. It checked history preservation, Stage -1F scientific-state preservation, relative references, subtree rule precedence, and over-migration risk.

## Decision

Accept the knowledge-home migration as the current repository organization. No corrective restructuring is required.

The migration review closes the engineering-review action recorded in `Handoff.md`. Scientific work can return to the bounded post-Stage -1F candidate path without reopening the documentation migration unless a concrete defect appears.

## Rejected Alternatives

- **Add fixes despite a clean review.** Rejected because the review identified no failure mode. Manufacturing changes would add churn without improving correctness.
- **Add more governance layers or a central note index.** Rejected because the reviewed structure already provides clear authority and routing.
- **Re-run scientific experiments as migration verification.** Rejected because the migration changed knowledge organization only; the review verified that frozen scientific evidence and verdicts were preserved.

## Consequences / Invariants

- `docs/`, `.agents/notes/`, run-local research artifacts, `research/memory/decisions/`, `research/memory/current-research-state.md`, and `Handoff.md` keep their reviewed responsibilities.
- The five migrated architecture notes remain historical records; later decisions are added rather than rewriting them.
- The Stage -1F verdict remains `MICA_MECHANISM_REPLICATED_BOTH_DATASETS` and remains single-seed Train/Dev evidence.
- Held-out/Test, G3/G4, and R0 Holdout remain unavailable for exploratory architecture selection.
- Future documentation changes should be driven by an observed ownership or routing problem, not by further imitation of an external project layout.
