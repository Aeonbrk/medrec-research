# MedRec Research Agent Instructions

## Research Guidelines

Must follow the `docs/guides/first-principles-research-practice-sources.md` to be an advanced researcher.

## Purpose

This repository is the active research home for general medication-recommendation computer science research. Keep reusable research capability independent of any single idea, route, or paper claim.

## Architecture invariants

- The Unified Research Protocol owns first-party comparison semantics.
- Reproduction Mode preserves recorded upstream behavior. Comparison Mode uses the shared protocol.
- A Baseline Core remains unchanged in Comparison Mode. Prediction Adapters may translate representations but must not change scientific behavior.
- Core development uses Python 3.11 and Homebrew `/opt/homebrew/bin/uv`. Each external baseline runs in an isolated Conda environment and process.
- Conda, pip, and uv package resolution prioritizes China mirrors through repository-scoped or command-scoped configuration; unavailable exact version-specific artifacts fall back to official HTTPS authorities (e.g., PyTorch, PyG) with TLS verification strictly enabled. Never disable TLS verification (`ssl_verify: false`, `--trusted-host`) or mutate machine/user-global package-manager configuration.
- The local MacBook Air is the harness terminal. Run only core tests, synthetic fixtures, protocol checks, submission, monitoring, and public-safe audits locally.
- Run real-data experiments, model training, GPU inference, and baseline Conda environments only on the `319-wild` server after the remote-execution preflight passes.
- Patient data, split membership, patient-level predictions, model weights, and private traces never enter Git.
- The Local Data Root lives outside every Git repository. Version only public-safe Dataset Manifests and synthetic fixtures.
- Git accepts only gate-approved research records. Drafts, Workflow Traces, and local logs stay under ignored runtime paths.
- `New-Search` is a read-only Research Archive. Cite its commit and path when migrated evidence depends on it.

## Sources of truth

- `CONTEXT.md`: canonical domain language.
- `ARCHITECTURE.md`: module and seam map.
- `docs/PLANS.md`: accepted multi-step work tracker.
- `docs/plans/`: implementation plans.
- `docs/specs/UNIFIED_RESEARCH_PROTOCOL.md`: comparison contract.
- `baselines/registry.toml`: baseline identity and readiness.
- `research/`: curated Research Memory and Failure Records.
- `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md`: Mac harness and 319 execution contract.
- `Handoff.md`: a note one coding agent (or session) leaves behind for the next one, like a shift-change note at a job.

## Work rules

- Prefer standard-library modules in the core package. Add dependencies only when they remove real complexity.
- Use `apply_patch` for manual file edits.
- Use `rg` for literal searches. Use CodeGraph or Semble before exploratory code search when available.
- Keep imported baseline source out of this repository unless its license, provenance, and need have been reviewed.
- Run lightweight Python commands through `rtk proxy /opt/homebrew/bin/uv run`. Run baseline commands through their declared Conda environment.
- Follow `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` before any real-data or GPU command. Do not treat a successful local synthetic run as experimental evidence.
- Record accepted multi-step work in `docs/PLANS.md` and keep the full plan under `docs/plans/`.

## Completion checks

```bash
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
markdownlint '**/*.md' --ignore '.agents/**'
```

=== SCOPE LIMITS (these bound what you PROPOSE, never what you look for) ===
Report anything that is actually wrong here — including a rare-looking case, if
this project actually produces it. Then keep the fix in scope:

1. This is not a security paper. Verification is welcome; over-defense is not.
   Unless this project states otherwise, assume a cooperating operator on their
   own machine; if it has a real adversary, it will say so and that scope wins.
2. Do not add hashes, checksums or fingerprints unless the hash replaces a
   materially more expensive operation AND its result changes what happens next.
3. No defensive scaffolding: no feature flags, migration frameworks, compat
   layers or wrappers for cases that do not occur here.
4. No corner-case obsession: exotic encodings, symlink races, RTL text and
   millisecond races are out of scope unless the case is reachable through this
   project's supported use — its documented inputs, its published interface, its
   real data. Reachable is enough; you do not need a reproduction. Constructible
   in principle is not enough.
5. Where judgement is needed, judge. Do not replace it with a scoring table, a
   checklist, or a re-verification loop over something already settled.
6. None of this overrides security, migration, verification or review that the
   user, this project's own conventions, or a higher-priority rule asked for.
   Those were requested; they are the work, not scope creep.
   Shapes already seen, for calibration. Examples, not a checklist — a real finding
   is not dismissed by resembling one:
   H hashing every row of two spreadsheets to answer what comparing cells answers
   H writing checksum files that nothing ever reads
   E hardening the accounts of an app that has no users and no deployment
   R auditing your own patch all night while the feature stays unwritten
   R a reviewer that returns a failing verdict on everything
   O guards whose justification is the previous guard, not the requirement
   And two that look like the above and are not. Report these:
   ✓ a digest that lets you skip re-reading a large file you already have
   ✓ a rare-looking input this project's own documentation example produces
   Before running any check, answer: what specific failure would this detect, and
   what would I do differently if it occurred? No answer means do not run it.
   Say plainly when something is correct. Do not manufacture findings.
