# Initial audit review

## Security

The current browser boundary is narrow and same-origin protected. Action Requests bind server-side to content-addressed declarations and durable records without exposing command or path identifiers. The local AI bridge is fixed, read-only, opt-in, and advisory. The ARIS transport is also fixed and server-only: schema-v2 manifests carry identities and digests, while the package registry owns SSH, commands, Conda, GPU, and paths. It is implemented and tested locally but remains unauthorized on 319. Adding generic browser command fields would be a critical regression.

## Research integrity

Mode separation is explicit and must remain so. H selected SafeDrug-main `88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a` for GAMENet source-native Reproduction Mode. Immutable `src/GAMENet.py` bytes (SHA-256 `906a37fb1f05e77c68a437d5b681ddd957c652b60a145b073c24cace581c8aa3`) confirm seed `1203`, split, evaluation-Jaccard selection, and checkpoint naming. SafeDrug-main warns that main differs from paper results and supplies no attributable root license file, so original-paper fidelity, license, environment, adapter, and readiness remain blocked.

## Product and UI

The production console is pending-decision-first. Desktop uses queue, detail, and bounded-action columns; mobile preserves the same review and H2 path in one column. All registered shadcn wrappers use Base UI. Production axe found three concrete regressions during the migration: toggle transition sampling, destructive badge contrast inside an active queue item, and an unfocusable scrollable detail region. Stable theme sampling, semantic selected-state colors, and a focusable detail surface now pass.

The current API projects Decision Packet completion, eligibility, blockers, aggregate outcomes, uncertainty, and public evidence URLs. A valid restricted aggregate receipt now enables an explicitly labelled raw data table; absent, malformed, or conflicting receipts keep the packet not-go-eligible. Curves remain unavailable unless supplied as public-safe evidence, so the UI never infers them from summary metrics. The structured contract questionnaire and fixed local AI draft/challenge route are present; the bridge remains unavailable unless explicitly configured.

An independent code review found that H2 was previously written to `<lane_id>.json`, so a later action could overwrite the same packet's prior human decision. H2 is now stored by `packet_sha256`; identical retries return the original record, changed retries return conflict, and ambiguous historical records produce an `h2-conflict` blocker. Production coverage exercises `hold`, `revise`, `kill`, and `go` on four separate synthetic packets rather than rewriting one scientific record.

## Operations

`./start-research` performs fail-closed read-only preflight, validates the ARIS `main` candidate, atomically records candidate/active/last-known-good revision state, creates the production handler, health-checks `/api/harness-state`, and opens the pending root only after the checks pass. A failed candidate is recorded and falls back to the last-known-good revision without starting. The real start command was not executed because it probes 319 and this work has no explicit 319 authorization. The declaration worker now seals a fixed manifest and can invoke the server-only submit/monitor/cancel/resume wrapper; no live invocation occurred.

## Verification update

- Python: `321 passed`; Ruff check and format check pass.
- Frontend: typecheck, lint, format, `24` unit tests, production build, `10` production browser scenarios passed with `10` mobile/desktop skips, axe, and asset drift pass. The retry, fixed takeover, and persistent-SSE regressions are covered against the packaged production bundle, not only Vite source.
- Package/security: wheel verified with `9` web resources; npm audit reports `0` vulnerabilities.
- Lighthouse: performance `99`, accessibility `100`, best practices `100`.
- Screenshots: `docs/assets/research-console/after-desktop.png` and `after-mobile.png` show the default pending workbench without overlap or horizontal overflow.
- ARIS: clean `main` checkout at `e12e07c7b85ee1a4dc07e5463089aa16836af2bf`.
- ARIS revision: candidate validation, atomic runtime activation, fallback recording, and `/api/aris-revision` projection are covered by unit tests; the current candidate is valid.

The production browser harness uses one temporary `ResearchSession` for contract, H1, Decision Packet, H2, declarations, queue, and SSE. It never calls remote preflight. The only execution blocker is the explicit synthetic `remote-execution-not-authorized`, so no local test can be mistaken for 319 readiness or scientific evidence.

## U4 and authority-integrity update

The production harness now exposes `/api/contract` as a read-only, schema-validated questionnaire projection over the current pinned contract and `/api/contract-ai` for bounded local assistance. Each field carries `protected` or `derived` provenance; the bridge accepts only `draft|challenge`, uses a fixed command, returns bounded text, and marks `h1_written: false`. The default AI status is `unavailable / local-ai-bridge-not-configured`; no browser payload can change the contract. The production browser test exercises the H1 detail, AI request boundary, and axe on these fields.

H1 is immutable per contract digest with exact replay idempotency. Queue parsing no longer drops malformed records, so corruption returns an unavailable control surface instead of authorizing a fresh initial lane.

The Decision Packet detail now reads `/api/decision-packets` and displays aggregate outcomes and uncertainty before the raw-artifact section. When the evaluator receipt contains public-safe aggregate rows, the UI renders those rows as a table; otherwise it shows an explicit unavailable blocker. No curve or table is synthesized from summary metrics.

The local production-domain rehearsal now covers H1, declaration-bound queueing, immutable submission envelopes, monitor transitions, restricted evidence intake, evaluator packet assembly, receipt corruption fail-closed behavior, H2 GO, and next-lane binding. It does not submit to ARIS or 319 and cannot establish readiness or scientific evidence.

## Control-plane correction

The first implementation incorrectly required a current H2 `go` before the first Action Request and used `request_sha256:sequence` as an SSE cursor. Both conflicted with the research contract. Initial execution now requires current H1 plus Action Gate authority and binds the registry-owned GAMENet lane. H2 governs subsequent execution, and SSE uses a global durable journal sequence.

## Independent review update

- Security review found the browser boundary, fixed AI argv, same-origin checks, Action Gate binding, H1/H2 immutability, and restricted intake fail-closed. One policy decision remains explicit: `protected` contract provenance currently means scientific immutability, while local Codex use is opt-in and expected to receive only public-safe contract text. It must not be treated as a confidentiality label without a separate redaction boundary.
- UI review confirmed Base UI usage, semantic tokens, Tabler icons, responsive queue/detail/action layout, keyboard recovery, progressive evidence disclosure, and axe coverage. The only observed regressions were the now-fixed transition-sampling, active blocked-badge contrast, and focusable-scroll-region issues.
- Research/code review found a GAMENet authority conflict: registry/audit evidence pointed at SafeDrug-main while the launch pointed at original GAMENet. H subsequently selected SafeDrug-main, and immutable source bytes now support its seed and checkpoint semantics. License, environment, adapter smoke, and readiness remain unresolved.
- A second control-plane review found execution retry could be detached by SSE refresh while a transport error was visible. The production bundle now holds failed execution refreshes for explicit retry and serializes full reload with SSE refresh. This is covered by the bounded-retry Playwright scenario.

## Remaining authority gates

No 319 access, real data, GPU, credentials, remote write, license acceptance, source synchronization, canary, Draft PR, or Ready transition occurred. Those are deliberate blockers, not missing UI states. The synthetic browser harness remains control-plane evidence only and ends at `remote-execution-not-authorized`.

## Remote bridge authority audit

The pinned ARIS checkout contains a generic `experiment-queue` scheduler, but not a versioned medrec/319 production submission API. Its manifest accepts free `cwd`, command, GPU, and expected-output values; SSH target and remote roots remain operator-supplied; monitoring is an SSH/`jq` recipe; cancellation has no external CLI; and result synchronization is explicitly unsupported. The scheduler state schema and atomic resume behavior are reusable implementation evidence, but the interactive skill is not a sufficient fixed transport contract.

The local fixed wrapper now supplies the missing immutable manifest, runtime root, submission identity, monitor/cancel/recovery surface, and public-safe receipt schema. GAMENet therefore no longer carries `aris-transport-contract-missing`. Live 319 installation and verification remain blocked, and the other four lanes retain the blocker because their launch templates are disabled.

The GAMENet audit also confirmed that evidence belongs to distinct source identities. H selected SafeDrug-main; its own source establishes seed `1203` and checkpoint selection for this source-native lane. The original repository's MIT-license observation is not transferable. SafeDrug-main license disposition, a content-addressed environment lock, and adapter-smoke evidence remain absent.

## Fixed transport implementation review

H selected SafeDrug-main and authorized a fixed server-only wrapper for local implementation and tests only. `baselines/adapters/gamenet/launch.toml` and the GAMENet execution declaration now bind SafeDrug-main. The existing human audit stayed unchanged because changing content without a new content-addressed review would invalidate its approval; new immutable-source evidence is recorded in this research memory instead.

The wrapper binds transport policy, wrapper package, queue-manager artifact, ARIS revision, SafeDrug revision, contract, H1, preflight, declaration, and submission digests. Local and remote per-request OS file locks close duplicate-scheduler races. Remote containment rejects escaped or symlinked mutable roots. Scheduler cancellation verifies PID start time, process group, and command digest before `killpg`. Explicit recovery reconciles existing queue state and preserves the scientific attempt when only an acknowledgement or control process was lost. Dispatch and monitor validation failures become durable `review_pending` records instead of silent retries.

Focused transport/HITL verification passes `18` tests, and focused ingress/evidence verification passes `6`. The full Python suite passes `321`; frontend typecheck, lint, format, `24` unit tests, production build, `10` applicable Playwright/axe scenarios, package drift, wheel resources, and npm audit remain green. Independent security findings about policy binding, duplicate submission, PID reuse, path containment, uncertain-completion reconciliation, detached recovery, browser control opacity, and SSE cursor replay are covered by regression tests. A 507 kB production chunk warning remains non-blocking.

The pending workbench now exposes declaration-internal `resume` and `cancel` only when the selected public execution state permits them. The browser POST contains only a closed operation and opaque request ID; the server resolves the durable record, transport receipt, manifest, preflight, and declaration. Exact recovery/cancellation replays are idempotent, and ordinary scientific review states expose no transport control.

`/api/execution-events` now keeps one HTTP/1.1 stream open, sends heartbeats, delivers journal additions on the same connection, and resumes after disconnect from `Last-Event-ID`. `monitor-apply` and `evidence-intake` make the already validated public-safe monitor/evidence paths locally callable without `ResearchSession.prepare()`, SSH, remote transport, or browser filesystem authority.

No 319 access, remote write, environment creation, data/GPU/cost use, canary, commit, push, Draft PR, or Ready transition occurred. The GAMENet lane remains honestly blocked by license, environment lock, adapter smoke, remote revision/package match, data root, and real authorization. The other four final-five lanes additionally retain `aris-transport-contract-missing` because their launch templates are disabled and unverified.
