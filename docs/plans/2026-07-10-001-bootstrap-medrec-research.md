---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
title: Bootstrap the MedRec Research Library
date: 2026-07-10
---

# Bootstrap the MedRec Research Library

## Goal Capsule

Create `/Users/oian/Codes/master/medrec-research` as the independent Active Research Home for general medication-recommendation research. The core Python package must run without ARIS, external baselines must cross an isolated process seam, and the repository must contain a curated account of prior progress and failed routes without copying private data or noisy workflow logs.

## Scope Boundaries

- Do not copy raw or processed EHR data, split membership, patient-level predictions, weights, checkpoints, restricted outputs, `.aris` traces, or timestamped workflow logs.
- Do not copy all imported baseline source trees.
- Do not claim GAMENet or SafeDrug Comparison Mode readiness until their real adapters, environments, checkpoints, and protocol verification pass.
- Do not revive EGSF, EG-TER repair, or CRC-PS action-family routes as active architecture.
- Do not move, delete, chmod, or rewrite the `New-Search` archive.
- Do not make ARIS a runtime dependency of the core package.

## Verification Contract

- `uv run pytest` passes unit and integration tests.
- `uv run ruff check .` passes.
- `uv run ruff format --check .` passes.
- `markdownlint '**/*.md' --ignore '.agents/**'` passes.
- The reference Protocol Vertical Slice writes a public-safe Run Record from synthetic fixtures.
- Baseline registry parsing rejects missing source identity and invalid readiness transitions.
- The process adapter rejects malformed or partial Prediction Records.
- No tracked file matches restricted data or model artifact patterns.
- `New-Search` retains its original directory and Git history.

## Implementation Units

### U1. Repository control plane and docs

**Goal**: establish project instructions, domain language, architecture, protocol, ADRs, playbooks, and a concise README.

**Files**: `AGENTS.md`, `CONTEXT.md`, `README.md`, `ARCHITECTURE.md`, `docs/**`.

**Approach**: keep top-level docs short and route details into specifications and playbooks. Record the archive, ARIS, protocol, and Conda adapter decisions as ADRs.

**Verification**: markdownlint passes and every top-level documentation link resolves.

### U2. Core protocol modules

**Goal**: implement deep in-process modules for Dataset Manifests, Prediction Records, evaluation, baseline registry, process adapters, and Run Records.

**Files**: `src/medrec_research/**`, `tests/unit/**`.

**Approach**: use Python 3.11 standard library dataclasses, `tomllib`, JSON, hashing, and subprocess. Keep public interfaces explicit through package `__all__` declarations.

**Execution note**: create failing tests for schema rejection, metric edge cases, registry validation, and process failures before implementation.

**Verification**: focused unit tests pass through public interfaces.

### U3. Protocol Vertical Slice

**Goal**: run a deterministic reference baseline against synthetic medication visits and emit aggregate evaluation plus a public-safe Run Record.

**Files**: `src/medrec_research/cli.py`, `src/medrec_research/reference.py`, `tests/integration/**`, `fixtures/synthetic/**`.

**Approach**: exercise the same Prediction Record and evaluation seam that external adapters will use. Keep synthetic fixtures small and inspectable.

**Execution note**: prove the end-to-end test fails before the CLI and reference implementation exist.

**Verification**: the CLI smoke command succeeds and integration tests validate deterministic output.

### U4. Baseline registry and isolated environments

**Goal**: register all archived baseline roots, establish the reference/GAMENet/SafeDrug phase-one set, and define Conda environment seams without claiming unverified model readiness.

**Files**: `baselines/**`, `environments/**`, `tests/unit/test_registry.py`, `tests/unit/test_process_adapter.py`.

**Approach**: pin known upstream identity, mark genuine unknowns as `needs_pin`, and distinguish `registered`, `smoke_ready`, and `comparison_ready` states.

**Verification**: registry validation passes; reference is smoke-ready; GAMENet and SafeDrug remain explicitly non-comparable until real scientific checks pass.

### U5. Curated Research Memory

**Goal**: migrate current scientific posture, reusable lessons, Failure Records, and evidence references from the archive.

**Files**: `research/**`.

**Approach**: synthesize current state and failure mechanisms. Point every quantitative statement to an archive path and commit. Preserve uncertainty and avoid route promotion.

**Verification**: all archive references exist; no copied private or patient-level content appears.

### U6. ARIS installation and archive handoff

**Goal**: install project-local ARIS Codex skills, document the gated workflow, and mark `New-Search` as the non-destructive Research Archive.

**Files**: `.aris/**`, `.agents/skills/**`, `AGENTS.md`, `README.md`, `ARCHIVED.md` in the archive.

**Approach**: use the ARIS installer, keep runtime files ignored, and add a clear archive pointer without changing historical research content.

**Verification**: ARIS manifest resolves to the upstream skill repository; archive path and Git history remain intact; agent-document completion gates pass.

## Definition of Done

- The new repository is initialized on `main` without an automatic commit.
- Core package setup uses Python 3.11 and `uv`; external baselines use isolated Conda process adapters.
- The synthetic vertical slice, tests, lint, format, and Markdown checks pass.
- README quick start runs from a clean core environment.
- Research Memory states what failed, why it failed, what remains reusable, and what is not yet an active route.
- `New-Search` is visibly archived but unchanged apart from archive metadata, the new domain glossary, and the user-owned pre-existing worktree changes.
