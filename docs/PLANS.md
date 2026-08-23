# Plans

## Completed: Architecture Friction-Point Refactor

- **Status**: implemented and review-hardened on `2026-08-22` after coherence, feasibility, product, security, scope, and adversarial review.
- **Plan**: `docs/plans/2026-08-22-001-refactor-architecture-friction-points-plan.md`.
- **Scope**: extract deterministic value-level CLI helpers and add a remote-only GAMENet Reproduction Mode path with fail-closed source, environment, input-data, GPU, disk, and launch gates.
- **Execution boundary**: local implementation, synthetic verification, and read-only 319 reconnaissance only. Its prior main-oriented registry declarations were removed when archived became the sole active lineage; this work did not perform a baseline run, remote mutation, environment change, or readiness transition.

## Completed: SafeDrug Family Reproduction (SafeDrug, RETAIN, LEAP-SafeDrug) on 319

- **Status**: completed on `2026-08-23` as historical SafeDrug `main@88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a` Reproduction Mode evidence; concurrent 3-GPU execution completed for `safedrug` (GPU 2), `retain` (GPU 3), and `leap-safedrug` (GPU 4).
- **Plan**: `docs/plans/2026-08-22-1756-feat-safedrug-family-reproduction-plan.md`.
- **Scope**: repaired shared Conda environment `medrec-gamenet` on 319 (`971ad2bf...`), deployed fail-closed runner `baselines/scripts/run_safedrug_family_319.sh` and strict parser `baselines/scripts/parse_safedrug_family_results.py`, executed 50 training epochs, selected best checkpoints, executed 10 test rounds, and validated atomic `result.json` Artifact Contracts for all 3 baselines.
- **Evidence**:
  - `safedrug`: Run `medrec-baseline-safedrug-20260822-132448-0bfb210f` (best epoch: 41), DDI $0.0589 \pm 0.0005$, Jaccard $0.5122 \pm 0.0031$, F1 $0.6687 \pm 0.0028$, PRAUC $0.7653 \pm 0.0027$, Avg Meds $20.5825 \pm 0.1611$.
  - `retain`: Run `medrec-baseline-retain-20260822-132548-abcbd1ce` (best epoch: 49), DDI $0.0851 \pm 0.0017$, Jaccard $0.4818 \pm 0.0025$, F1 $0.6425 \pm 0.0023$, PRAUC $0.7587 \pm 0.0019$, Avg Meds $19.6382 \pm 0.3093$.
  - `leap-safedrug`: Run `medrec-baseline-leap-safedrug-20260822-132647-545ede8a` (best epoch: 44), DDI $0.0705 \pm 0.0005$, Jaccard $0.4442 \pm 0.0030$, F1 $0.6068 \pm 0.0031$, PRAUC $0.6506 \pm 0.0035$, Avg Meds $18.9097 \pm 0.0782$.
- **Boundary**: these runs used 15,032 visits and a 112-medication vocabulary, not the paper's 14,995 visits and 131 medications. They remain truthful historical provenance but do not participate in future baseline selection, paper reproduction, or Comparison Mode.

## Accepted: SafeDrug Archived Single-Baseline Program

- **Status**: accepted on `2026-08-23`; SafeDrug `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` is the only active SafeDrug-family source and the common baseline for future innovation.
- **Plan**: `docs/plans/2026-08-23-archived-single-baseline-plan.md`.
- **Scope**: reuse the existing `gamenet`, `safedrug`, `retain`, and `leap-safedrug` IDs under one archived lineage; regenerate paper-matching preprocessing, add only the mechanical training-mode adaptation required by the archived entrypoints, run four independent GPU lanes, and compare aggregate results with SafeDrug Table 2.
- **Execution boundary**: no archived run is launchable until the exact paper aggregate counts pass, the training-mode adaptation is audited, and the archived environment succeeds. SafeDrug `main` receives no new registry identity or future run lane.

## Completed: Core Toolkit Simplification and ARIS Workflow Layer Strip

- **Status**: completed on `2026-08-21`; stripped complex multi-agent orchestration and UI mock layers in favor of the clean 4-command CLI (`reference`, `accept-comparison`, `evaluate`, `baseline list`), strict Comparison Protocol, and process-isolated 319 remote execution scripts.
- **Commit**: `ce2e71f`.
- **Scope**: streamlined `src/medrec_research` to pure protocol validation, run records, dataset manifests, and prediction evaluation; archived overengineered web artifacts to `archive/v0-overengineered/`; retained 76 core pytest unit and integration tests.
- **Execution boundary**: local repository simplification; zero regressions on core test suite, strict typechecks and clean linters.

## Archived: Refactor HITL Research Control Console into Task-Oriented Research Cockpit

- **Status**: archived on `2026-08-21` (superseded by Core Toolkit Simplification; web frontend archived to `archive/v0-overengineered/`).
- **Plan**: `docs/plans/2026-08-20-016-refactor-hitl-cockpit-ux-and-observability-plan.md`.
- **Scope**: overhaul frontend UX (`pending-workbench.tsx`, `environment-health-bar.tsx`, `research-task-cockpit.tsx`, `contract-cockpit-card.tsx`, `cluster-monitor-panel.tsx`, `baseline-matrix-table.tsx`).

## Completed: Refactor Frontend Sidebar and Aesthetic with shadcn sidebar-08 & b1GdfqsQE Preset

- **Status**: completed on `2026-08-20`; sidebar-08 inset architecture, Breadcrumb navigation, b1GdfqsQE translucent/subtle preset details, and full WCAG AA accessibility compliance are implemented and verified (now archived in `archive/v0-overengineered/`).
- **Plan**: `docs/plans/2026-08-20-016-refactor-frontend-shadcn-sidebar-preset-plan.md`.
- **Scope**: integrated shadcn `sidebar-08` inset layout, `NavMain`, `NavLanes`, `NavSecondary`, and `NavHarness` footer with `b1GdfqsQE` preset.

## Completed: Refactor HITL Vibe-Research Architecture and Multi-Agent Team Composition

- **Status**: completed on `2026-08-20`; deep backend subsystems and modular workbench components implemented; lessons absorbed into core toolkit in `ce2e71f`.
- **Plan**: `docs/plans/2026-08-20-015-refactor-hitl-vibe-research-team-architecture-plan.md`.
- **Scope**: decomposed monolithic `ResearchSession` into `RemotePreflightProbe`, `ResearchContractStore`, `ExecutionOrchestrator`, and `AgentTeamBridge`.

## Completed: One-command HITL Research Session

- **Status**: completed locally on `2026-08-12`; the one-command launcher is implemented and verified.
- **Plan**: `docs/plans/2026-08-12-013-feat-one-command-hitl-research-session-plan.md`.
- **Scope**: replace manual status and harness arguments with `./start-research`, a real-state coordinator that performs fail-closed 319 preflight, publishes ignored runtime projections, starts the production console, and exposes narrowly controlled H1/H2 decisions without bypassing the Action Gate.
- **Execution boundary**: startup and preflight are read-only on 319. The launcher never substitutes fixtures, mutates the remote checkout or environment, allocates resources, or executes an Action Request.
- **Current blockers**: remote/local source drift, missing remote `MEDREC_DATA_ROOT`, unverified declared environments and readiness, unresolved license evidence, and incomplete H1 acceptance authority.

## Completed: React Research Console Rebuild

- **Status**: completed locally on `2026-08-12` in the isolated `codex/shadcn-ui-rebuild` worktree; independent PR pending review.
- **Plan**: `docs/plans/2026-08-12-012-feat-react-research-console-plan.md`.
- **Scope**: replace the zero-build harness UI with a Chinese-first React, Vite, Tailwind CSS v4, and shadcn/ui console while preserving every API schema, research-state meaning, and action-gate behavior.
- **Execution boundary**: local public-safe UI, synthetic fixtures, packaging, and browser verification only; no real-data, training, GPU, remote execution, new endpoint, or scientific-authority change.
- **Evidence**: Python and frontend gates, production Playwright/axe, rebuild drift, clean-wheel/no-Node smoke, and desktop production Lighthouse `99/100/100` for Performance/Accessibility/Best Practices.

## Active: First-Principles Research Practice Guide Review

- **Status**: active on `2026-07-15`; reviewing the current worktree version of the research-practice guide through the `ce-doc-review` workflow.
- **Plan**: `docs/plans/2026-07-15-010-docs-first-principles-research-practice-review.md`.
- **Execution boundary**: documentation-only review of `docs/guides/first-principles-research-practice.md`; no research data, model, baseline, remote, or runtime changes.
- **Evidence target**: role-specific findings, an independent cross-model review where available, and Markdown validation after any accepted edits.

## Completed: Private Tailscale SSH Connectivity

- **Status**: completed on `2026-07-14`; configured and verified a private relay-to-target SSH path outside Git, without recording host identifiers, Tailnet node identities, keys, or credentials.
- **Plan**: `docs/plans/2026-07-14-008-chore-private-tailscale-ssh-connectivity.md`.
- **Execution boundary**: confirmed an SSH jump-host topology, then verified transport and SSH identity without accessing research data, source checkouts, GPU state, or workloads.
- **Evidence**: the relay accepted a dedicated client key, and the new local SSH alias reached the target identity through the relay.
- **Rollback**: remove the newly joined nodes from the Tailnet and restore the prior SSH host configuration; do not delete existing Tailnet nodes or keys.

## Completed: Knowledge Documentation Audit

- **Status**: completed on `2026-07-14`; reconciled final-five terminology, historical review provenance, and applicable agent-rule references without changing code, research data, remote state, or generated agent memory.
- **Plan**: `docs/plans/2026-07-14-009-chore-knowledge-documentation-audit.md`.
- **Evidence**: 218 tests, Ruff lint and format checks, Markdown lint, whitespace validation, and the global agent-document gate pass.

## Completed: Benchmark Authority Contract Hardening

- **Status**: local public-safe implementation completed on `2026-07-12`.
- **Plan**: `docs/plans/2026-07-12-001-fix-authority-contract-hardening-plan.md`.

## Completed: Bootstrap the MedRec Research Library

- **Status**: completed on `2026-07-10`; the repository has Git history and an `origin` remote, while the 319 checkout remains unverified.
- **Plan**: `docs/plans/2026-07-10-001-bootstrap-medrec-research.md`.

## 已完成：基于第一性原理的科研实践参考资料

- **状态**：于 `2026-07-13` 完成；仅新增公开来源的中文研究方法资料。
- **计划**：`docs/plans/2026-07-13-002-docs-first-principles-research-practice-plan.md`。

## Completed: Expand the New-Search Research Memory Ledger

- **Status**: completed on `2026-07-13`; documentation-only migration with no runtime or baseline mutation.
- **Plan**: `docs/plans/2026-07-13-001-docs-new-search-research-memory-ledger-plan.md`.
