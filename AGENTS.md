# MedRec research agent instructions

This repository is the Active Research Home for medication-recommendation method research. Optimize for:

```text
scientific value × iteration speed × trustworthy evidence
```

The practical publication floor is CCF-B; research quality remains CCF-A-oriented.

## Start here

Before changing anything:

1. Verify the authoritative `origin/main` revision.
2. Read `CONTEXT.md`, `Handoff.md`, and the nearest directory-level `AGENTS.md`.
3. Use `docs/START_HERE.md` to find the current source of truth.
4. For research work, read `research/memory/current-research-state.md` before acting on historical notes.

Rules inherit downward. A nearer `AGENTS.md` may add or narrow rules for its subtree but must not weaken repository-wide safety, privacy, provenance, or evidence boundaries.

## Global invariants

- Run-local result files, audits, and source-bound experiment records are authoritative for what a run actually did.
- `research/memory/current-research-state.md` owns current cross-project scientific synthesis and routing.
- `docs/` describes current system facts and operating contracts. Do not put historical decision narratives there.
- `.agents/notes/` stores append-only engineering causality: why an architecture, dependency, or subsystem decision was made.
- `research/memory/decisions/` stores append-only scientific belief updates caused by evidence. It does not replace run-local evidence.
- `Handoff.md` is a short current-work pointer, not a historical archive.
- Historical evidence is never rewritten merely to match the latest interpretation. Archive or supersede it explicitly.
- No global notes index is maintained; use directory structure and semantic filenames.
- Always follow `unslop` to reduce AI slop.

## Research boundaries

- Default early screen: one seed, one main configuration, Train/Dev only, full intended training budget, and a strong matched control.
- Prefer architecture-level changes in representation, information flow, prediction granularity, decoder/inference, or supervision over repeated small correction heads.
- Two bounded weak prototypes in one family normally trigger a family reset. Do not rescue weak mechanisms with broad hyperparameter sweeps.
- Historical failures constrain the tested formulation; they are not universal bans on primitives such as GNNs, retrieval, MoE, structured prediction, or attention.
- Novelty, closest-work, SOTA, and benchmark-comparability claims that matter to a survivor or paper must be verified from primary sources.
- Held-out Test, G3/G4, R0 Holdout, or any quarantined evaluation surface is not used for exploratory architecture selection.

Detailed research execution rules live in `research/AGENTS.md`.

## Execution and privacy

- The local MacBook Air is the Harness Terminal. Use it for core tests, synthetic fixtures, protocol checks, submission, monitoring, and public-safe intake.
- Real EHR processing, model training, GPU inference, and baseline Conda environments run only on the 319 Execution Plane after the remote preflight.
- Patient data, split membership, patient-level predictions, model weights, private traces, and restricted paths never enter Git.
- The Local Data Root stays outside the repository. Git stores only public-safe manifests, aggregate evidence, synthetic fixtures, code, and compact research records.
- `New-Search` is a read-only Research Archive. Cite its revision and path when migrated evidence depends on it.

## Directory routing

| Work                                                | Read first                      |
| --------------------------------------------------- | ------------------------------- |
| Current docs, specs, playbooks, plans               | `docs/AGENTS.md`                |
| Scientific prototypes, ideas, memory, benchmarks    | `research/AGENTS.md`            |
| External baselines and reproduction/comparison code | `baselines/AGENTS.md`           |
| Reusable core library                               | `src/medrec_research/AGENTS.md` |
| Publication-facing survivor packages                | `papers/AGENTS.md`              |

Canonical sources:

- `CONTEXT.md`: domain language.
- `ARCHITECTURE.md`: current module, ownership, and dependency map.
- `docs/KNOWLEDGE_HOMES.md`: where current facts, decisions, evidence, and handoff state belong.
- `docs/specs/UNIFIED_RESEARCH_PROTOCOL.md`: comparison contract.
- `baselines/registry.toml`: baseline identity and readiness.
- `research/memory/current-research-state.md`: current scientific state.
- `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md`: remote execution contract.
- `Handoff.md`: concise next-agent handoff.

## Engineering rules

- Prefer standard-library modules in the reusable core. Add dependencies only when they remove real complexity.
- Keep external baseline dependencies isolated from the core package.
- Do not refactor adjacent code during a scoped bug fix unless the bug proves the shared abstraction is wrong.
- Run a check only when it can detect a concrete failure that would change trust or action.
- Do not add migration frameworks, compatibility layers, feature flags, hashes, or defensive scaffolding without a concrete project need.
- Use available GPUs for distinct hypotheses, matched controls, or survivor seeds, not parameter fishing.

## Completion checks

For code or contract changes, run the applicable repository checks:

```bash
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
markdownlint '**/*.md' --ignore '.agents/**'
```

Documentation-only changes may use the relevant Markdown/reference checks rather than unrelated GPU or real-data work.
