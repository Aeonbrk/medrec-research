---
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
execution: code
title: Single-project HITL Research Control Console and Base UI Migration
type: feat
date: 2026-08-13
topic: hitl-control-console-base-ui
---

# Single-project HITL research control console and Base UI migration

## Goal capsule

Make the production Python harness the authoritative single-project decision console. A human researcher must be able to draft and challenge one structured research contract, create H1, inspect declared execution and exceptions, review public-safe evidence and a Decision Packet, create H2, and see the next eligible research step. The browser submits only bounded human input and one opaque Action Gate `request_id`.

## Hidden critical question

Can one Action Request be resolved server-side to exactly one registered execution declaration, then replayed through queue, bridge, monitor, evidence intake, evaluation, and H2 without allowing the browser or an automated repair to change scientific meaning?

The answer must be mechanically testable. UI completion without this binding is not completion.

## Current facts

- Python baseline: `274 passed`; Ruff check and format check pass on `2026-08-13`.
- Frontend baseline: TypeScript, ESLint, Vitest (`14` tests), production build, and asset drift pass.
- Production Web is React, Vite, Tailwind CSS v4, shadcn Nova, Tabler Icons, and Radix UI. It has `17` installed wrappers.
- H1 and H2 narrow write endpoints already bind server-loaded records. Action Requests are currently written as JSON files and never executed.
- No production execution declaration registry, durable state machine, bridge worker, monitor event stream, restricted evidence intake, or automatic Decision Packet assembly exists.
- Action Gate already owns a closed set of nine status actions. Runtime retry, resume, cancel, and exception handling must remain declaration-internal state transitions, not new Action Gate actions.
- ARIS checkout is clean on `main` at `e12e07c7b85ee1a4dc07e5463089aa16836af2bf`. Startup latest-candidate validation, atomic activation, fallback, and actual-revision recording are not implemented.
- GAMENet remains `registered`. License, environment lock, adapter smoke/readiness, remote source match, data root, acceptance authority, data/GPU/time/cost authorization, and source-native canary evidence are unresolved.

## Invariants

- Preserve Unified Research Protocol, Reproduction/Comparison separation, Baseline Core, Prediction Adapter, Action Gate, H1, and H2 authority semantics.
- H1 freezes problem, competing hypotheses, data, mode, evidence duties, acceptance, stopping rules, resources, and bounded repair budget.
- H2 is human-only and remains one of `go`, `revise`, `kill`, or `hold`.
- Browser input never contains shell, argv, host, port, working directory, Conda identity, source/data/output path, GPU assignment, credentials, source revision, contract digest, or packet digest.
- A registered declaration fixes action, revision, target, environment, resources, paths, command template, evidence schema, cancellation policy, and dependency graph.
- Only idempotent retry, checkpoint resume, endpoint repair, and bounded resource repair declared by H1 may proceed automatically. Scientific changes always return to the pending queue.
- Authority, privacy, license, data/evaluation integrity, and absolute resource failures trigger the declaration's fixed cancellation transition and evidence record.
- Failed or stuck dependencies block downstream work. Terminal status alone is insufficient.
- Production never falls back to fixtures, mocks, stale browser data, or inferred readiness.
- Local checks and synthetic/no-data rehearsals are control-plane evidence only.

## Work units

### U1. Audit and research contract

Record the problem brief, competing hypotheses, research contract, decision log, reviews, and Research Memory. Keep unresolved facts as blockers.

### U2. Registered execution control plane

Add public-safe execution declarations and queue records. Bind every allowed Action Request to one declaration by project, action, target, revision, contract, current H1, optional preceding H2, and authority digests. Current H1 plus Action Gate authority opens the registry-owned initial lane; only a current H2 `go` unlocks a subsequent declared claim or lane. Persist state atomically and idempotently. Project the normal lifecycle states `blocked`, `queued`, `submitting`, `running`, `monitoring`, `intake`, `review_pending`, `completed`, and `cancelled`. Project `failed` and `stuck` as abnormal terminal outcomes, never as dependency success.

The bridge may execute only a declaration-owned fixed command template. No browser field may influence argv or remote location. The local implementation must remain blocked until explicit remote authorization and all declaration gates exist.

### U3. Monitor, evidence intake, and Decision Packet assembly

Accept only schema-validated public-safe aggregate evidence bound to the declaration and remote attempt. Reject paths, identifiers, rows, predictions, weights, credentials, raw logs, and unknown fields. Recompute or validate core-owned aggregate conclusions, then assemble a current Decision Packet. Emit replayable SSE status with a persisted global monotonic event cursor and snapshot fallback.

### U4. Contract questionnaire and local AI bridge

Expose structured contract fields and bounded human inputs. AI drafting and challenge use only the local Codex/ARIS bridge. Browser holds no model key and cannot select arbitrary commands or remote targets. Draft output never becomes H1 without explicit human acceptance.

### U5. Base UI whole-project migration

Run shadcn project preflight, establish a `radix-nova`/`base-nova` golden pair, install `@base-ui/react` beside Radix, migrate wrappers bottom-up, migrate consumers, and write one `.migration/<component>.md` report per component plus `.migration/project.md`. Remove Radix only after the final wrapper and consumer are clean. Use official Base UI wrappers, semantic tokens, Tabler icons, Tailwind v4, both themes, and WCAG 2.2 AA behavior.

### U6. Decision workbench

Make the pending queue the default page. Desktop uses a dense three-column workbench: queue, selected decision context, and evidence/action inspector. Mobile preserves the complete review and decision flow. Evidence discloses conclusion, grounds, then raw public-safe artifact. Curves include a raw data table.

Cover loading, empty, error, stale, blocked, disabled, malformed, and transport-failure states; URL query persistence; SSE reconnect; keyboard/focus/overlay/table/Sheet behavior; and light/dark themes.

### U7. GAMENet readiness repair

Reconcile the selected SafeDrug-main launch entry, source revision, fixed source-native seed `1203`, source-owned checkpoint selection, license disposition, 319 environment lock, Prediction Adapter boundary, and readiness evidence. Never patch seed behavior or use test metrics for checkpoint selection. Keep the lane blocked until every required artifact exists.

### U8. Verification, reviews, and PR

Run Python, frontend, production browser, axe, package/wheel, drift, security, and Markdown gates. Perform up to three evidence-driven UI/control-plane iterations. Record independent security, UI, research, and code reviews. Push a Draft PR only after local gates and screenshots pass. It remains Draft until an explicitly authorized GAMENet source-native Reproduction Mode canary and H2 evidence complete.

## Acceptance contract

- `./start-research` checks ARIS candidate/latest state, verifies a candidate before activation, falls back to last-known-good, records the actual revision, starts the production harness, passes health checks, and opens the pending queue.
- Browser production tests use only the Python harness and submit only opaque Action Gate request IDs plus bounded H1/H2/contract-review fields.
- The nine existing Action Gate actions remain unchanged and have an explicit final-five lane/action matrix.
- Queue records survive restart, duplicate requests are idempotent, cancellation is recorded, and downstream dependencies fail closed on failed/stuck inputs.
- Initial execution requires current H1 but no prior H2. Subsequent claims require the preceding current H2 `go`; `revise`, `kill`, and `hold` leave execution blocked.
- SSE reconnect after events on multiple requests replays every event newer than the supplied global cursor exactly once in journal order.
- No Radix runtime import or dependency remains. Every migrated wrapper has a conforming `.migration` report.
- Contract questionnaire, H1, run states, exceptions, Decision Packet, H2, query state, SSE recovery, all UI failure states, keyboard, and both themes pass production Playwright and axe.
- All final-five lanes appear. Non-ready lanes show exact blockers.
- A no-data rehearsal demonstrates H1 through H2 without creating research evidence.
- The GAMENet canary is attempted only after explicit authorization for 319 write access, data, GPU, duration, cost, license, and environment work. Its evidence remains Reproduction Mode evidence.

## Pause conditions

Pause before any real 319 write, data access, GPU use, environment creation, source synchronization, cost-bearing work, license determination, credential use, or formal experiment. Also pause if implementation would change Action Gate, H1/H2 authority, the Unified Research Protocol, privacy boundaries, browser execution permissions, Baseline Core behavior, Prediction Adapter scientific semantics, or API compatibility.

## Verification commands

```bash
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
markdownlint '**/*.md' --ignore '.agents/**'
cd web && rtk proxy npm run typecheck
cd web && rtk proxy npm run lint
cd web && rtk proxy npm run test
cd web && rtk proxy npm run build
cd web && rtk proxy npm run test:e2e
cd web && rtk proxy npm run package:verify
cd web && rtk proxy npm run build:check
```

Additional repository security, wheel/package-resource, ARIS revision, and startup health gates will be named in package scripts or documented with exact commands before completion.
