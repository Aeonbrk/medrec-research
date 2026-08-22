# Plans

## Accepted: Architecture Friction-Point Refactor

- **Status**: implementation-ready on `2026-08-22` after mandatory coherence, feasibility, product, security, scope, and adversarial review.
- **Plan**: `docs/plans/2026-08-22-001-refactor-architecture-friction-points-plan.md`.
- **Scope**: extract deterministic value-level CLI helpers, make the GAMENet remote launcher explicit, and add a remote-only Reproduction Mode submission path with mandatory fail-closed 319 preflight.
- **Execution boundary**: local implementation and synthetic/mock verification only. The project registry still makes no readiness claims, so this work does not authorize or perform a real baseline run, remote mutation, environment change, or readiness transition.

## Active: 319-wild GAMENet Baseline Reproduction and Execution

- **Status**: active on `2026-08-21`; execution scripts and environment verification tools deployed in `baselines/scripts/`, full execution plan in `docs/playbooks/319-GAMENET-EXECUTION-PLAN.md`.
- **Plan**: `docs/playbooks/319-GAMENET-EXECUTION-PLAN.md`.
- **Scope**: configure Conda environment `medrec-gamenet`, resolve PyTorch MKL symbol conflict, run GAMENet on MIMIC-III on 319-wild, collect standardized metrics, and accept comparison Run Records.
- **Execution boundary**: execution on 319-wild GPU cluster; local MacBook terminal serves as harness terminal for verification and intake.

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

## Archived: Single-project HITL Research Control Console and Base UI Migration

- **Status**: archived on `2026-08-21` (superseded by Core Toolkit Simplification).
- **Plan**: `docs/plans/2026-08-13-014-feat-hitl-control-console-base-ui-plan.md`.
- **Scope**: turn production Python harness into single-project decision console; migrate Radix wrappers to Base UI.
- **Execution boundary**: H selected SafeDrug-main and authorized the fixed server-only wrapper for local implementation and tests. Real 319 writes, wrapper installation, data access, GPU work, environment creation, cost-bearing execution, GAMENet canary, commit, push, and PR publication remain blocked pending explicit human authorization and all scientific gates.
- **Evidence target**: durable idempotent queue, registered execution declarations, fixed bridge commands, replayable monitor state, opaque Web recovery/cancellation, schema-gated public-safe monitor/evidence ingress, fail-closed downstream dependencies, Base UI migration reports, production Playwright/axe evidence, package/drift/security gates, and honest final-five blocker projection.

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

## Accepted: Researcher HITL Reproduction Decision Loop

- **Status**: implementation-ready plan enriched on `2026-08-10`; local synthetic implementation may proceed, while real-data and 319 execution remain gated.
- **Plan**: `docs/plans/2026-07-16-011-feat-researcher-hitl-reproduction-loop-plan.md`.
- **Scope**: one researcher-controlled SafeDrug four-model Reproduction Mode batch at `88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a`, staged MoleRec replay and retraining at `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`, and separate five-model Comparison Qualification under a SafeDrug-main-derived protocol scope.
- **Success target**: one shared H1 freezes common batch authority, each model or MoleRec stage receives independent QA/QC, conclusion, Decision Packet, and H2, and only scope-qualified evidence may enter fair comparison.
- **Execution boundary**: requirements and audit only; no runtime, remote, real-data, training, registry, or baseline-source change has been authorized by this plan artifact.

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

## Accepted: Final Five Baseline Program

- **Status**: active on `2026-07-14`; GAMENet, SafeDrug, RETAIN, and LEAP-SafeDrug use `ycq091044/SafeDrug@88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a`; MoleRec uses `yangnianzu0515/MoleRec@dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`.
- **Plan**: `docs/plans/2026-07-14-007-chore-final-five-baseline-program.md`.
- **Execution boundary**: four SafeDrug-main entries share repository-native data, split, and evaluation semantics. MoleRec remains source-native. Every candidate is `registered` until 319 preflight and mode-specific evidence pass.
- **Current blocker**: the previous SSH and missing-checkout observation is superseded by the 2026-08-12 read-only preflight. The fallback route reaches a clean remote checkout, but source revision drift, a missing `MEDREC_DATA_ROOT`, unverified environment/readiness, and unresolved license/acceptance authority still block real execution.

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
