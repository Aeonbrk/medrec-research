---
title: Expand the New-Search Research Memory Ledger
date: 2026-07-13
execution: knowledge-work
---

# Expand the New-Search Research Memory Ledger

## Goal

Make the Active Research Home carry a complete, curated account of the pinned
`New-Search` scientific record without turning Research Memory into an archive
mirror or promoting a failed route.

## Source Boundary

- Source archive: locally maintained New-Search Research Archive (path intentionally omitted).
- Source commit: `9971464253c556345262b22ed6d44b2cc14c9da8`.
- Read Git objects at that commit only; do not use or modify the archive
  worktree.

## Changes

- Add a lifecycle-aware ledger for every canonical idea, experiment, and claim.
- Add a compact literature-memory inventory for every canonical paper record.
- Expand research navigation, the archive evidence index, and reusable lessons.
- Preserve existing Failure Records as detailed route-boundary documents.

## Boundaries

- Exclude raw or processed data, patient-level outputs, result tables, model
  artifacts, workflow traces, timestamped log duplicates, and server-specific
  operational details.
- Retain only decision-bearing aggregate metrics, each with archive provenance.
- Label preliminary passes superseded by stronger evidence; do not portray them
  as surviving method success.
- Do not modify `New-Search`.

## Verification

- Reconcile canonical counts and every cited archive path against the pinned
  source commit.
- Check lifecycle labels against source records and review the content for
  privacy and route-promotion violations.
- Run the repository Markdown, Python test, Ruff, and formatting gates.
