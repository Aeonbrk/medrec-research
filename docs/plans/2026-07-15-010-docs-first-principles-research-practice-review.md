---
title: First-principles research practice guide review
date: 2026-07-15
execution: knowledge-work
---

# First-principles research practice guide review

## Goal

Review the current worktree version of `docs/guides/first-principles-research-practice.md` for coherence, feasibility, product assumptions, scope, security, and adversarial weaknesses.

## Scope

- Apply the `compound-engineering:ce-doc-review` workflow in interactive mode.
- Check consistency with `docs/guides/first-principles-research-practice-sources.md` and the repository's research boundaries.
- Use only role-specific review findings and an independent cross-model review when an eligible peer is available.
- Apply only `safe_auto` documentation fixes before requesting a decision on all remaining findings.

## Non-goals

- Do not alter research code, baselines, private data boundaries, remote infrastructure, or experiment state.
- Do not treat the guide as evidence for a medical-recommendation result.
- Do not change user-authored worktree edits except for an accepted or `safe_auto` review fix.

## Completion evidence

- Every required review lens returns or is recorded as unavailable.
- Findings are deduplicated, anchored to the guide, and classified by action tier.
- `markdownlint` and `git diff --check` run after any Markdown mutation.
