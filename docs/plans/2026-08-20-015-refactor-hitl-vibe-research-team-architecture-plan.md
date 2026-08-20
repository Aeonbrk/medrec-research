---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
title: Refactor HITL Vibe-Research Architecture and Multi-Agent Team Composition
type: refactor
date: 2026-08-20
topic: hitl-vibe-research-team-architecture
---

# Refactor HITL Vibe-Research Architecture and Multi-Agent Team Composition

## Goal capsule

Deepen the HITL (Human-in-the-Loop) research subsystem across backend and frontend to realize a true human-driven, agentic **Vibe-Research Loop**. Decompose the 1,623-line monolithic `ResearchSession` into deep domain modules (`RemotePreflightProbe`, `ResearchContractStore`, `ExecutionOrchestrator`), evolve `LocalAIBridge` into a first-class `AgentTeamBridge` governed by `$team-composition-patterns` (Review, Debug, Feature, Fullstack, Research, Security, Migration teams), and modularize the frontend `pending-workbench.tsx` into high-locality panels with live multi-agent team observability.

## Hidden critical question

Can multi-agent team swarms execute parallel reviews, debugging hypotheses, and baseline adaptations while preserving fail-closed H1/H2 human gatekeeping, target-free evidence intake, and zero patient data leakage?

## Architectural invariants

- Mac remains Harness Terminal; 319 remains Execution Plane.
- Human researcher (H) retains exclusive, fail-closed authority over H1 (Contract Sign-off) and H2 (Decision on Decision Packet: `go`, `revise`, `kill`, `hold`).
- Agent teams generate structured, content-addressed proposals and diagnostic hypotheses; they never self-approve H1 or H2.
- Team sizing adheres strictly to heuristics (Simple: 1-2, Moderate: 2-3, Complex: 3-4, Very Complex: 4-5) to minimize coordination overhead.
- All public status, SSE streams, and UI panels handle only public-safe metadata, SHA-256 hashes, and target-free payloads.

## Work units

### U1. Domain Vocabulary & Architecture Glossary

Update `CONTEXT.md` and `ARCHITECTURE.md` with canonical definitions for `Agent Team Supervisor`, `Research Contract Store`, `Execution Orchestrator`, `Remote Preflight Probe`, `Decision Queue Panel`, and `Team Composition Console`.

### U2. Backend Deepening: `RemotePreflightProbe` & `ResearchContractStore`

- Extract remote preflight probing into a dedicated deep module `remote_preflight.py` with caching and alias resolution.
- Extract atomic H1/H2 storage, immutability checks, and lock management into `contract_store.py`.

### U3. Backend Deepening: `ExecutionOrchestrator`

- Extract execution queue dispatch, worker submission locking, manifest sealing, transport failure recovery, and evidence intake into `execution_orchestrator.py`.

### U4. Backend Deepening: `AgentTeamBridge` ($team-composition-patterns)

- Implement `agent_team_bridge.py` supporting:
  - 7 preset team compositions (Review, Debug, Feature, Fullstack, Research, Security, Migration).
  - Sizing heuristics and role validation (`team-lead`, `team-reviewer`, `team-debugger`, `team-implementer`, `general-purpose`).
  - Display mode configurations (`tmux`, `iterm2`, `in-process`).
  - Multi-hypothesis debugging for 319 failures and 3-reviewer adversarial H1 contract auditing.

### U5. Backend Refactor: Lean `ResearchSession` Facade

- Refactor `research_session.py` to be a cohesive, high-leverage facade over `RemotePreflightProbe`, `ResearchContractStore`, `ExecutionOrchestrator`, and `AgentTeamBridge`.
- Ensure all 321+ existing Python tests pass with zero regressions.

### U6. Frontend Deepening: Modularize Decision Workbench

- Decompose `web/src/components/pending-workbench.tsx` (956 lines) into:
  - `decision-queue-panel.tsx`: Queue state filtering, sorting, keyboard navigation, and row status badges.
  - `transport-recovery-card.tsx`: Dedicated transport failure resume/cancel controls and error diagnostics.
  - `team-composition-console.tsx`: Multi-agent team status, reviewer breakdown, hypothesis tree, and teammate logs.
  - `evidence-inspector-panel.tsx`: Public-safe aggregate table, metrics, and artifact checksums.
- Update `domain.ts` and `App.tsx` with team composition types.

### U7. Verification and Test Suite Expansion

- Add unit tests for `remote_preflight.py`, `contract_store.py`, `execution_orchestrator.py`, and `agent_team_bridge.py`.
- Run full Python test suite (`pytest`), Ruff linter/formatter.
- Run frontend typecheck (`tsc`), lint (`eslint`), format (`prettier`), and Vitest (`npm test`).
