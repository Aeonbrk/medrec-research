# Research Memory: HITL control console

## Current state

The project now has immutable scientific records, Action Gate, H1/H2, a production decision workbench, declaration-bound durable execution, a fixed server-only remote transport, restricted evidence intake, and Decision Packet assembly. The transport is locally implemented and tested but has not been installed or exercised on 319. Remaining uncertainty is scientific and operational authority, not another browser execution API.

## Reusable lessons

- A terminal state is not a dependency success signal. Downstream work requires an explicit successful outcome and current bindings.
- Browser opacity is necessary but insufficient. The server must also resolve the opaque identifier against a closed declaration registry.
- Queue durability without scientific identity binding can resume the wrong experiment.
- H2 is not an initial execution credential. H1 freezes the work; H2 decides what follows evidence from that work.
- A compound cursor ordered by content digest is not a global event order. Reconnect requires a separate monotonic journal identity.
- Scientific exception handling and operational recovery are different. Only predeclared operational recovery can be automated.
- UI migration is valid only if behavior, focus, state semantics, and production evidence survive. Dependency replacement alone proves little.
- Accessibility scans must sample a stable theme state after CSS transitions. Scanning an interpolated color frame can report colors that are neither theme endpoint; stable sampling does not excuse an endpoint contrast failure.
- A production browser harness must source contract, H1, packet, H2, queue, and SSE from one session. Combining individually valid fixtures creates a scientifically incoherent console.
- Execution lane identity is canonical, not presentational. The fifth registry lane is `leap-safedrug`; `leap` is a baseline/model label and must not replace the declared lane ID.
- Source-native reproduction fixes source behavior, including inconvenient seed and checkpoint rules. Compatibility work cannot silently turn into method modification.
- Testing every H2 enum by overwriting one packet is not coverage; it demonstrates a research-integrity defect. Each packet has one immutable H2, exact retries are idempotent, and action-matrix tests need independent packet identities.
- Aggregate evidence must be revalidated against the frozen contract at intake. A Decision Packet can expose a raw table only through a digest-checked receipt; missing, malformed, or conflicting receipts must remove GO eligibility rather than leave a summary-only success path.
- A Git revision does not bind dirty runtime policy. Bind the canonical transport registry, fixed wrapper modules, and queue-manager artifact by digest, then require clean source checkouts remotely.
- PID liveness is not process identity. Cancellation needs start time, process group, and command identity and must fail closed when any binding changes.
- Transport acknowledgement recovery is not a scientific retry. Reconcile the remote durable state first and increment only when a declared workload attempt is actually created.
- A recovery button is safe only when the server re-resolves the opaque request against the durable receipt and fixed manifest. Showing a button based on a generic `review_pending` state would conflate operational loss with a scientific exception.
- Finite SSE replay is not a live stream. Closing a healthy connection makes the UI report a transport failure and creates needless reconnect traffic; durable replay and persistent delivery are separate requirements.
- Restricted intake needs an operational entry point even when the validator exists. A local CLI can preserve the browser filesystem boundary while making public-safe monitor and evidence records reachable by the control plane.

## Open blockers

- Real 319/data/GPU/time/cost/license/environment authorization.
- Authorized 319 installation of the fixed transport package plus matching transport-policy and queue-manager digests.
- GAMENet SafeDrug-main license disposition and verified 319 environment lock.
- GAMENet adapter smoke and readiness evidence.
- Remote/local accepted revision and data-root readiness.
- Independent production security, UI, research, and code reviews after the remaining implementation. The first code review found and drove the H2 immutability correction.
- Live 319 submission, monitor, recovery/cancellation receipts, and actual canary evidence. The fixed wrapper exists locally but is not authorized or verified remotely.
- Public-safe curves when an authorized evidence source supplies them; no curve may be inferred from aggregate summaries.

## Current execution semantics

- Normal lifecycle projection has nine states: `blocked`, `queued`, `submitting`, `running`, `monitoring`, `intake`, `review_pending`, `completed`, and `cancelled`.
- `failed` and `stuck` are explicit abnormal terminal projections with matching outcomes. They are not extra normal lifecycle phases, and neither counts as dependency success.
- The execution registry declares the initial lane and the stable final-five lane order. Browser input never selects or overrides either.
- The canonical registry lane order is `gamenet`, `safedrug`, `molerec`, `retain`, and `leap-safedrug`; the closed nine-action product is `45` declarations.
- The verified no-remote production path ends in `blocked` with `remote-execution-not-authorized`. This is expected control-plane behavior, not a failed or completed scientific run.
- H2 files are content-addressed by `packet_sha256`. An exact retry returns the original decision, a changed retry is rejected, and duplicate conflicting records fail closed as `h2-conflict`.
- Contract review is a read-only `/api/contract` projection. Protected and derived questionnaire fields are labelled separately; an unconfigured local AI bridge is a visible blocker.
- H1 replay is idempotent only for the same contract, owner, and rationale; changed authority is rejected. Malformed durable queue records fail closed.
- Decision Packet review uses a separate public-safe projection for aggregate outcomes and uncertainty. Missing curve/table artifacts stay `null` and blocked rather than being inferred from summary metrics.
- Restricted intake validates model/source/interval/conclusion bindings, stores only aggregate-safe receipt rows, and makes receipt integrity part of H2 GO eligibility.
- `monitor-apply` and `evidence-intake` are bounded local ingress commands over those validators. They never call remote preflight or let the browser name an input path.
- AI contract assistance is advisory: only fixed `draft`/`challenge` operations reach the local Codex bridge, the bridge is opt-in and read-only, output is bounded, and no AI response can write H1.
- Startup validates clean repository revision and includes its digest in project authorities.
- Declaration dispatch derives target, revision, environment, resource, launch, and evidence identities from the registered declaration. The sealed browser-safe manifest carries only identities and digests; the server-only transport registry owns SSH, command, path, Conda, and GPU values.
- GAMENet still remains blocked by license, environment, adapter, remote revision, and data readiness.

## Recent lessons

- Production browser verification must exercise the packaged asset consumed by the Python harness. Source-only Vite tests can pass while stale wheel assets still fail; rebuild before Playwright and run the drift check afterward.
- A durable queue's recovery control needs an explicit ownership boundary between SSE refresh and human retry. Once transport recovery is visible, background replay must not erase that state before H can act.
- Independent review cannot collapse GAMENet source identities. SafeDrug-main and original-GAMENet revisions are distinct authority domains; seed `1203` does not bridge them.
- `protected` is an integrity/provenance term in the current contract, not a confidentiality guarantee. Opt-in local AI must remain public-safe, and confidentiality would require a separate contract field and enforcement boundary.
- GAMENet evidence is source-specific. Original-source seed/checkpoint/license observations cannot be transferred to the SafeDrug derivative without attributable evidence and an explicit H source decision.
- H selected SafeDrug-main `88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a`; immutable source bytes confirm seed and checkpoint semantics, while the missing attributable license and the upstream main-versus-paper warning remain explicit blockers.
- Per-request OS locks are required on both Mac control state and remote runtime state. Atomic JSON replacement alone does not make a read-check-start sequence idempotent.
- The Web exception control carries only `{kind, operation, request_id, schema_version}`. The fixed transport operation is selected from `resume|cancel`; all remote execution values remain server-owned.
- SSE recovery uses the global journal sequence as `Last-Event-ID`, while a healthy connection remains open and receives later events without a reconnect.
