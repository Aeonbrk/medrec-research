---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
title: Refactor HITL Research Control Console into Task-Oriented Research Cockpit
type: refactor
date: 2026-08-20
topic: hitl-cockpit-ux-and-observability
---

# Refactor HITL Research Control Console into Task-Oriented Research Cockpit

## Goal capsule

Transform the HITL (Human-in-the-Loop) Control Console from a fragmented, confusing state-machine debugger into a polished, human-friendly **Task-Oriented Research Cockpit**. 
Key improvements:
1. **Research Lifecycle Stepper**: Guided flow (`[1. 前置准备] -> [2. 契约拟定与AI评审] -> [3. 人工签核冻结] -> [4. 319算力调度监控] -> [5. 证据评估与决策]`).
2. **1-Click AI Contract Generation**: Replace raw error callouts and manual forms with a smart contract generation card, preset baseline selectors, and interactive questionnaire preview.
3. **Top Environment & Preflight Health Bar**: Unify Git dirty status, 319 connection reachability, and Harness SSE status into a non-blocking top bar with clear human explanations and 1-click diagnostics.
4. **Humanized Terminology & Clean UX**: Replace internal jargon (`H1`/`H2`, raw SHA-256 digests, `Fail-Closed`, `local-worktree-dirty`) with accessible domain concepts (`实验契约签核`, `研究结论决策`, `Git 工作区未提交`), removing false-alarm red blocks.
5. **Real-time 319 Cluster Monitoring & Multi-Agent Swarm Cards**: Visual GPU/VRAM utilization, live training epoch streams, 3-reviewer AI comments, and multi-hypothesis debugger trees.
6. **Baseline Comparison Matrix & Leaderboard**: Side-by-side metric comparison (SafeDrug, GAMENet, RETAIN, MoleRec, LEAP) for PRAUC, F1, DDI Rate, and Reproducibility Status.

## Hidden critical question

Can we completely modernize the interaction model, visual hierarchy, and actionable workflow while strictly preserving the underlying scientific invariants (Action Gate, fail-closed H1/H2 human approval boundaries, target-free evidence intake, and zero patient data leakage)?

## Architectural invariants

- Mac remains Harness Terminal; 319 remains Execution Plane.
- Human researcher (H) retains exclusive, fail-closed authority over H1 (Contract Sign-off) and H2 (Decision on Decision Packet).
- AI agent teams generate structured proposals, draft contracts, and review critiques; they never self-approve.
- All public status, SSE streams, and UI components handle only public-safe metadata, SHA-256 hashes, and target-free payloads.
- All existing backend routes (`/api/harness-state`, `/api/hitl-control`, `/api/contract`, `/api/contract-ai`, `/api/h1`, `/api/h2`, `/api/executions`, `/api/execution-control`, `/api/execution-events`) remain backwards compatible.

## Work units

### U1. Backend Contract Path & Auto-Drafting Support
- Update `research_session.py` to target `research-contract.json` (with fallback to default reproduction template when first drafting).
- Ensure `/api/contract-ai` with operation `"draft"` can generate a valid initial `SafeDrugBatchContract` when no contract exists.
- Verify contract persistence and immutability validation.

### U2. Frontend Environment & Preflight Health Bar (`environment-health-bar.tsx`)
- Create top status bar summarizing:
  - Git Working Tree (Clean vs Dirty with friendly tooltip: "存在未提交改动，保证可复现性建议提交/暂存")
  - 319 Compute Cluster (Reachable / GPU ready / Latency)
  - Harness Control Plane (Live SSE stream, Valid Until)
  - Action Gate (Authorized / Pending)
- Replace full-page red blockers with actionable status chips.

### U3. Research Lifecycle Stepper & Task Cockpit (`research-task-cockpit.tsx`)
- Implement 5-stage visual progress stepper:
  1. **环境与准备 (Setup & Preflight)**
  2. **契约拟定与评审 (Drafting & Review)**
  3. **契约签核冻结 (H1 Sign-off)**
  4. **319 算力调度与监控 (Execution & 319 Monitor)**
  5. **结论决策与沉淀 (H2 Decision & Insights)**
- Dynamic primary action card (CTA) tailored to the active stage.

### U4. Intelligent Contract Drafting & Sign-off Card (`contract-cockpit-card.tsx`)
- **Empty State**: Clean, elegant card: "准备启动基线复现实验", baseline selection pills (SafeDrug, GAMENet, RETAIN, MoleRec, LEAP), and button `✨ 由 AI Team 智能起草实验契约`.
- **Draft State**: Rich visual preview of hypothesis, datasets, model annexes, resource ceiling, stopping rules, plus `TeamCompositionConsole` (3 Reviewers' comments & challenge points).
- **Sign-off Action**: 1-click `✍️ 审核通过并签核冻结`, auto-populating researcher ID and providing quick presets for decision reasons.

### U5. Live 319 Cluster Monitoring & Log Streamer (`cluster-monitor-panel.tsx`)
- Real-time visual progress bars for each model lane (`gamenet`, `retain`, `safedrug`, `leap`).
- GPU/VRAM mock/live gauge indicators, epoch progress, ETA, and transport recovery controls (Resume / Cancel).
- Streaming log console tab with terminal aesthetic.

### U6. Baseline Comparison Matrix & Leaderboard (`baseline-matrix-table.tsx`)
- Side-by-side comparison table for the 5 baselines:
  - Model Name & Paper Source
  - Reproduction Mode & Target
  - Key Metrics (PRAUC, F1, DDI Rate, Avg Meds, Jaccard)
  - Verification & Evidence Status (Pass / In Progress / Blocked)

### U7. Refactor Pending Workbench & Navigation Layout
- Reassemble `pending-workbench.tsx` using the new modular components:
  - `EnvironmentHealthBar` at top
  - `ResearchLifecycleStepper`
  - Active Task Cockpit (Drafting -> Sign-off -> 319 Monitoring -> H2 Decision)
  - Collapsible Secondary Tabs (Decision Queue, Baseline Matrix, Agent Swarm Console, Raw Audit Trace)
- Humanize all text labels and badges across the UI.

### U8. Verification and Test Suite Expansion
- Update and add unit/integration tests in Vitest for new components.
- Run Python pytest suite (`pytest`), Ruff check and format.
- Run frontend typecheck (`tsc`), lint (`eslint`), and test (`npm test`).
