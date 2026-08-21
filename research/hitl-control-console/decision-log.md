# Decision log

## D1: Preserve the existing nine Action Gate actions

The repository already defines a closed nine-action status set. Retry, resume, monitor, intake, cancel, and review are execution-state transitions inside a registered declaration, not new browser or Action Gate actions.

## D2: Build one complete GAMENet vertical slice before generalizing

The first implementation binds the GAMENet source-native lane end to end. Final-five support is then a registry projection over the same declaration and state contracts, with honest blockers for non-ready lanes.

## D3: Treat local synthetic/no-data work as control-plane evidence only

No local fixture, mock, or synthetic run can create Reproduction or Comparison evidence. Production must show missing authority as a blocker rather than substitute data.

## D4: Use official Base UI golden pairs

The migration skill reference files are installed at the skill root rather than under a `references/` directory. The migration will use those mappings together with official shadcn `radix-nova`/`base-nova` registry files and installed `@base-ui/react` type definitions. No prop mapping will be guessed.

## D5: Keep Draft PR status until real canary and H2 evidence

Local completion can justify a Draft PR. It cannot justify Ready status because the requested GAMENet canary requires separate human authorization and unresolved scientific gates.

## D6: H1 opens the initial declared lane; H2 governs subsequent claims

The first Action Request binds the registry-owned `gamenet` initial lane after current H1 and Action Gate authority. It does not require prior H2. A current H2 `go` may unlock the next registry-owned claim or lane; `revise`, `kill`, and `hold` never authorize another execution. The browser still submits only the opaque Action Gate `request_id`.

## D7: SSE uses one global durable event order

Per-request event sequence remains useful for record integrity, but it is not a reconnect cursor. Every persisted event also receives a globally monotonic journal sequence. SSE replay filters and orders only by that journal sequence, so a later event for a request with a lexically smaller digest cannot be skipped.

## D8: Production browser evidence uses one synthetic session

The browser harness may seed public-safe synthetic contract, H1, and packet records in a temporary directory, but every production endpoint must read that same `ResearchSession`. It does not call remote preflight or create a fixture fallback in production. Execution remains blocked by `remote-execution-not-authorized`, and the run is control-plane evidence only.

## D9: Canonical lane IDs come from the execution registry

The final-five execution lanes are `gamenet`, `safedrug`, `molerec`, `retain`, and `leap-safedrug`. UI labels may show model names, but tests, queue bindings, dependencies, and declarations use the canonical lane IDs from the package registry.

## D10: H2 is immutable per Decision Packet

An H2 record is stored by `packet_sha256`, not by lane. An exact browser replay returns the existing record; changing researcher, action, or rationale for the same packet is rejected. A new H2 requires a new current packet identity. Conflicting historical H2 records remove that packet's decision from the current projection and add an `h2-conflict` blocker.

## D11: Contract questionnaire is a read-only projection

The Web questionnaire is derived from the current pinned `SafeDrugBatchContract`. Protected fields are labelled as such; the problem and competing-lane summary are explicitly labelled derived. The browser cannot write a contract or alter the H1 digest. AI drafting/challenge is opt-in through the fixed local bridge and remains visibly unavailable when that bridge is not configured.

## D12: H1 and queue records fail closed

An exact H1 replay for the same contract, owner, and rationale returns the original approval. A changed replay is rejected; a changed contract starts a new H1 authority. Any malformed durable execution JSON now makes queue reads fail closed instead of silently resetting the current lane.

## D13: Decision Packet evidence is projected without synthesizing artifacts

`/api/decision-packets` exposes current aggregate outcomes, uncertainty, attempt state, and content digests. Curves and raw aggregate tables remain `null` with `raw-aggregate-table-unavailable` until a restricted intake supplies them; the UI must not derive a curve from summary metrics.

## D14: AI assistance is opt-in and advisory only

`/api/contract-ai` accepts only the fixed `draft` and `challenge` operations plus an opaque request ID. The server resolves the current contract, invokes the fixed read-only local Codex command only when `MEDREC_LOCAL_AI_BRIDGE=1` is explicitly configured, bounds and validates plain-text output, and returns `h1_written: false`. Unavailable, timeout, command, and transport states stay visible; AI output never becomes H1 automatically.

## D15: Stop before unauthorized remote publication or experiment

All local and production-browser control-plane gates pass on `codex/hitl-base-ui-control-console`, but no remote push, Draft PR publication, 319 access, data/GPU use, or canary was performed. Those actions remain paused until H explicitly authorizes the corresponding remote write and experiment scope.

## D16: Receipt integrity gates H2 GO

Restricted evidence intake rebinds model, source revision, acceptance intervals, outcomes, validity, and hard gates to the current contract before creating a packet. The evaluator writes a public-safe aggregate table receipt with a content digest. If the receipt is missing, malformed, or conflicting while the evidence directory is active, packet projection removes GO eligibility and H2 rejects the decision.

## D17: Synthetic chain is not experiment evidence

The local production-domain rehearsal may exercise H1, declaration-bound queueing, monitor transitions, restricted aggregate intake, evaluator assembly, receipt replay, H2, and next-lane binding. It must not be labelled Reproduction or Comparison evidence, and it does not authorize remote submission, 319 access, GPU use, or a GAMENet canary.

## D18: Session startup validation

Startup validates local repository state as a versioned authority. It accepts only a clean checkout, writes an atomic public-safe revision record, and includes that record in the project authorities.

## D19: Persist declaration envelopes before remote submission

The local worker resolves every queued request through the closed declaration registry and persists only declaration-derived identities. Remote envelopes remain held until a separately authorized fixed bridge submits them; no local synthetic fallback, arbitrary command, or inferred execution success is allowed.

## D20: Hold execution transport failures for explicit recovery

An SSE event must not silently replace an execution transport/malformed state while H is inspecting its recovery control. Failed execution refreshes therefore require an explicit bounded retry; a full reload serializes with the event stream and then performs one forced refresh. This preserves recoverability without adding an Action Gate action or changing scientific state.

## D21: Do not infer GAMENet source authority from a matching seed

The launch file, registry, audit, and playbook must agree on source revision and source-native seed semantics. The existing SafeDrug-main versus original-GAMENet mismatch is unresolved. No revision-only edit, readiness claim, or canary may proceed until H selects the authoritative reproduction source and accepts evidence for its seed/checkpoint rules.

## D22: Treat protected provenance as immutability unless confidentiality is separately specified

The current local AI bridge is opt-in and receives public-safe contract projections. `protected` fields prevent browser mutation and H1 drift; they do not promise secrecy from an explicitly enabled local bridge. A future confidentiality requirement needs a separate redaction policy, not a reinterpretation of this field.

## D23: GAMENet source selection precedes launch repair

SafeDrug-main and original GAMENet are distinct reproduction authorities. The SafeDrug registry identity cannot inherit original-GAMENet seed, checkpoint, DNC, or license evidence merely because the model name matches. H must select one source identity; only evidence attributable to that identity may determine launch semantics, license disposition, environment lock, adapter smoke, and readiness.

## D24: SafeDrug-main is the GAMENet reproduction authority

H selected SafeDrug-main revision `88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a`. Its immutable `src/GAMENet.py` bytes have SHA-256 `906a37fb1f05e77c68a437d5b681ddd957c652b60a145b073c24cace581c8aa3` and own seed `1203`, the two-thirds split, evaluation-Jaccard checkpoint selection, strict post-epoch-zero improvement, and `Epoch_{epoch}_JA_...` checkpoint names. SafeDrug-main also warns that main differs from paper results; this authority supports source-native Reproduction Mode only, not original-paper fidelity or Comparison evidence. No attributable root license file was found, so license remains blocked.

## D25: Remote execution uses a fixed server-only wrapper

The browser continues to submit only an opaque Action Gate request ID. The server seals declaration, contract, H1, preflight, source, transport-policy, wrapper-package, and queue-manager digests into a schema-v2 manifest. Only the package registry resolves SSH profile, remote module, runtime root, Conda environment, GPU profile, command, paths, and expected output. Reading `/api/execution-dispatch` is projection-only and cannot submit work.

## D27: Recovery reconciles transport state without inventing a scientific retry

Local and remote per-request file locks serialize submission. Remote resume first reconciles the durable receipt, queue state, and verified scheduler identity; a lost acknowledgement returns the existing attempt, while restarting a dead queue-manager control process preserves that attempt. Scientific failure is returned to the pending queue. Cancellation signals only the recorded process group when PID, process start time, process group, and command digest all match.

## D28: Fixed-wrapper authorization is local implementation and tests only

H authorized this implementation slice but did not authorize 319 access, remote writes, environment creation, data/GPU/cost use, source synchronization, canary execution, commit, push, or PR publication. The wrapper and synthetic H1-to-H2 chain are control-plane evidence only. License, environment lock, data layout, adapter smoke, readiness, remote package/revision match, and real canary evidence remain blockers.

## D29: Web exception takeover resolves opaque control server-side

Transport recovery and cancellation remain declaration-internal operations rather than new Action Gate actions. The pending workbench sends only an opaque Action Request ID and one closed `resume` or `cancel` operation. The server resolves the durable execution digest, receipt, manifest, preflight, declaration, fixed SSH profile, and wrapper operation. Active transport may be cancelled; only a recorded `remote-transport-*` failure may be resumed. Ordinary scientific review states expose neither operation.

## D30: Healthy SSE is persistent, not repeated finite replay

The execution event endpoint keeps one HTTP/1.1 stream open, sends a bounded heartbeat, and polls only the durable global journal. A reconnect supplies `Last-Event-ID` and receives only later journal events. Normal idle time must stay `live`; deliberate stream loss, malformed events, and unavailable queue state remain distinguishable failure conditions.

## D31: Restricted monitor and evidence ingress is local CLI authority

The browser cannot submit evidence, paths, or monitor observations. `monitor-apply` and `evidence-intake` read one bounded local JSON input, reuse the existing strict public-safe schemas and authority bindings, and atomically write the resulting public projection. These commands instantiate the current session records without calling `prepare()`, remote preflight, SSH, environment creation, or transport submission.
