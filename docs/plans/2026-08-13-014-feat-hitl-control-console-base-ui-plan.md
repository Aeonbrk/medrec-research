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

- Python verification: `321 passed`; Ruff check and format check pass on `2026-08-18`.
- Frontend verification: TypeScript, ESLint, Prettier, Vitest (`24` tests), production build, package drift, production Playwright (`10 passed`, `10 skipped`), axe, wheel resources, npm audit (`0 vulnerabilities`), and production-asset drift pass after the fixed transport-control and persistent-SSE work.
- Production Web is React, Vite, Tailwind CSS v4, shadcn Base Nova, Tabler Icons, and Base UI. All `17` installed wrappers are migrated; no Radix runtime or dependency remains.
- H1 and H2 narrow write endpoints already bind server-loaded records. Action Requests are currently written as JSON files and never executed.
- A production execution declaration registry, durable state machine, and fixed server-only ARIS transport exist for the control-plane slice. Local monitor observations, restricted aggregate intake, receipt validation, and core-owned Decision Packet assembly are implemented. The wrapper translates a sealed manifest into the pinned ARIS `experiment-queue` scheduler without exposing its free-form manifest to the browser. It is implemented and tested locally only; authorized 319 installation and live receipts remain open.
- Action Gate already owns a closed set of nine status actions. Runtime retry, resume, cancel, and exception handling must remain declaration-internal state transitions, not new Action Gate actions.
- ARIS checkout is clean on `main` at `e12e07c7b85ee1a4dc07e5463089aa16836af2bf`. The local revision bridge validates the candidate, records atomic active/last-known-good state, and blocks startup on invalid candidates. Fixed submission is locally implemented but has not been invoked remotely.
- GAMENet remains `registered`. H selected SafeDrug-main `88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a`; immutable source bytes confirm seed and checkpoint semantics. License, environment lock, adapter smoke/readiness, remote source/package match, data root, acceptance authority, data/GPU/time/cost authorization, and source-native canary evidence remain unresolved.
- The default pending workbench now composes existing production endpoints into a desktop three-column and mobile single-column decision surface. Its tested synthetic path is Action Gate to durable blocked queue to replayable SSE to H2; it is control-plane evidence only. `/api/contract` exposes a read-only, provenance-labelled questionnaire projection, and `/api/contract-ai` exposes a fixed, opt-in local Codex bridge that remains unavailable by default.

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

The bridge may execute only a declaration-owned fixed command template. No browser field may influence argv or remote location. Schema-v2 manifests bind the transport registry, wrapper modules, queue-manager artifact, source, ARIS, contract, H1, preflight, declaration, and submission by digest. Per-request OS locks serialize submission; monitor, cancellation, and explicit recovery remain durable and fail closed. Live use stays blocked until explicit remote authorization and all declaration gates exist.

### U3. Monitor, evidence intake, and Decision Packet assembly

Accept only schema-validated public-safe aggregate evidence bound to the declaration and remote attempt. Reject paths, identifiers, rows, predictions, weights, credentials, raw logs, and unknown fields. Recompute or validate core-owned aggregate conclusions, then assemble a current Decision Packet. Emit replayable SSE status with a persisted global monotonic event cursor and snapshot fallback.

Status: the server-side synthetic production-domain chain now binds monitor observations, restricted aggregate evidence, receipt digests, and evaluator-owned Decision Packet assembly. `/api/decision-packets` returns a raw aggregate table only when a valid receipt exists; missing, malformed, or conflicting receipts fail closed. Curves remain unavailable unless a public-safe table is supplied. `monitor-apply` and `evidence-intake` provide bounded local JSON ingress without calling remote preflight or exposing paths to the browser. The fixed ARIS worker is locally implemented; authorized 319 execution and canary evidence remain open.

### U4. Contract questionnaire and local AI bridge

Expose structured contract fields and bounded human inputs. AI drafting and challenge use only the local Codex/ARIS bridge. Browser holds no model key and cannot select arbitrary commands or remote targets. Draft output never becomes H1 without explicit human acceptance.

Status: the production harness exposes `/api/contract` and `/api/contract-ai`. The bridge accepts only `draft|challenge` plus an opaque request ID, uses a fixed read-only local Codex command, bounds output, and never writes H1. It is disabled unless `MEDREC_LOCAL_AI_BRIDGE=1` is explicitly configured; the default production projection remains visibly unavailable rather than using a fallback.

### U5. Base UI whole-project migration

Run shadcn project preflight, establish a `radix-nova`/`base-nova` golden pair, install `@base-ui/react` beside Radix, migrate wrappers bottom-up, migrate consumers, and write one `.migration/<component>.md` report per component plus `.migration/project.md`. Remove Radix only after the final wrapper and consumer are clean. Use official Base UI wrappers, semantic tokens, Tabler icons, Tailwind v4, both themes, and WCAG 2.2 AA behavior.

Status: complete. Production axe found and fixed pressed-toggle contrast, selected blocked-badge contrast, and keyboard access to the scrollable detail region.

### U6. Decision workbench

Make the pending queue the default page. Desktop uses a dense three-column workbench: queue, selected decision context, and evidence/action inspector. Mobile preserves the complete review and decision flow. Evidence discloses conclusion, grounds, then raw public-safe artifact. Curves include a raw data table.

Cover loading, empty, error, stale, blocked, disabled, malformed, and transport-failure states; URL query persistence; SSE reconnect; keyboard/focus/overlay/table/Sheet behavior; and light/dark themes.

Status: local production slice complete. The browser submits opaque request IDs, the Python handler resolves fixed declarations, and `DeclarationBoundWorker` persists declaration-derived submission envelopes without shell text or paths. Service-side dispatch seals and submits only fixed manifests; browser GETs are projection-only. A transport failure exposes only fixed `resume` and `cancel` controls, whose POST body contains request ID, closed operation, kind, and schema version; the server resolves all transport authority and preserves idempotent recovery. SSE now remains connected, emits heartbeats, replays the global journal from `Last-Event-ID`, and delivers new events without reconnect churn. URL selection replays after reload, and mobile H2 covers `hold`, `revise`, `kill`, and `go` on independent packet identities. H1/H2 records are immutable per bound identity: exact retries are idempotent, changed retries are rejected, conflicting historical records fail closed, and malformed queue records are not silently dropped. The structured contract questionnaire, explicit local AI draft/challenge action, monitor state path, restricted intake, receipt gate, and raw aggregate table disclosure are present. The ARIS revision bridge validates a clean `main` candidate, atomically records active/last-known-good state, and refuses startup on candidate failure. Remote authorization, live ARIS/319 receipts, and the canary remain open.

### U7. GAMENet readiness repair

Reconcile the selected SafeDrug-main launch entry, source revision, fixed source-native seed `1203`, source-owned checkpoint selection, license disposition, 319 environment lock, Prediction Adapter boundary, and readiness evidence. Never patch seed behavior or use test metrics for checkpoint selection. Keep the lane blocked until every required artifact exists.

Status: H selected SafeDrug-main `88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a`. Its immutable `src/GAMENet.py` bytes (SHA-256 `906a37fb1f05e77c68a437d5b681ddd957c652b60a145b073c24cace581c8aa3`) own seed `1203`, the two-thirds split, evaluation-Jaccard checkpoint selection, strict improvement, and checkpoint names. The launch and declaration now use this revision. SafeDrug-main warns that main differs from paper results and supplies no attributable root license; the environment remains provisional and adapter smoke/readiness evidence is absent.

### U8. Verification, reviews, and PR

Run Python, frontend, production browser, axe, package/wheel, drift, security, and Markdown gates. Perform up to three evidence-driven UI/control-plane iterations. Record independent security, UI, research, and code reviews. Push a Draft PR only after local gates and screenshots pass. It remains Draft until an explicitly authorized GAMENet source-native Reproduction Mode canary and H2 evidence complete.

Status: local gates and screenshots pass on `codex/hitl-base-ui-control-console`: `321` Python tests, Ruff, frontend typecheck/lint/format, `24` unit tests, production build, `10` applicable Playwright/axe scenarios, wheel/package resources, asset drift, and npm audit. No remote push or Draft PR was created because H authorized local implementation and tests only.

## Acceptance contract

- `./start-research` checks ARIS candidate/latest state, verifies a candidate before activation, falls back to last-known-good without startup when validation fails, records the actual revision, starts the production harness, passes health checks, and opens the pending queue.
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
