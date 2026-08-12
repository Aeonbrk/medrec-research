# MedRec Research Agent Instructions

## Research Guidelines

Must follow the `docs/guides/first-principles-research-practice-sources.md` to be an advanced researcher.

## Purpose

This repository is the active research home for general medication-recommendation computer science research. Keep reusable research capability independent of any single idea, route, or paper claim.

## Architecture invariants

- ARIS is the control plane. The `medrec_research` Python package must remain usable without ARIS.
- The Unified Research Protocol owns first-party comparison semantics.
- Reproduction Mode preserves recorded upstream behavior. Comparison Mode uses the shared protocol.
- A Baseline Core remains unchanged in Comparison Mode. Prediction Adapters may translate representations but must not change scientific behavior.
- Core development uses Python 3.11 and Homebrew `/opt/homebrew/bin/uv`. Each external baseline runs in an isolated Conda environment and process.
- The local MacBook Air is the ARIS and harness terminal. Run only core tests, synthetic fixtures, protocol checks, submission, monitoring, and public-safe audits locally.
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
<!-- ARIS-CODEX:BEGIN -->

## ARIS Codex Skill Scope

ARIS Codex packages installed in this project: skills-codex
Managed entries: 83
Manifest: `.aris/installed-skills-codex.txt`
ARIS repo root: `/Users/oian/Codes/master/Auto-claude-code-research-in-sleep`
Project skill path: `.agents/skills/<skill-name>`
For ARIS Codex workflows, prefer the project-local skills under `.agents/skills/`.
When a skill needs ARIS helper scripts, resolve the repo root from the manifest or set it explicitly:
`ARIS_REPO=$(awk -F '\t' '$1=="repo_root"{print $2; exit}' "/Users/oian/Codes/master/medrec-research/.aris/installed-skills-codex.txt")`
Do not edit or delete symlinked skills in place; update upstream or rerun:
`bash /Users/oian/Codes/master/Auto-claude-code-research-in-sleep/tools/install_aris_codex.sh "/Users/oian/Codes/master/medrec-research" --reconcile`
For copied Codex installs, use:
`bash /Users/oian/Codes/master/Auto-claude-code-research-in-sleep/tools/smart_update_codex.sh --project "/Users/oian/Codes/master/medrec-research"`
<!-- ARIS-CODEX:END -->
