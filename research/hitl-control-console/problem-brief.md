# Problem brief: single-project HITL research control console

## Long-term goal

Reduce the uncertainty and operational risk between a human research decision and its auditable evidence. One researcher should be able to control one current medication-recommendation project without reconstructing state from terminals, chats, files, and remote logs.

## Current problem

The production console can display project state and create H1/H2 records, but it stops at an Action Request JSON file. There is no registered execution declaration, durable worker state, fixed ARIS bridge, monitor stream, restricted public-safe evidence intake, or automatic Decision Packet assembly. The current UI is Radix-based and organizes information around sections rather than the researcher's pending decisions.

## Evaluation setting

- Local evidence: unit/integration tests, production Python harness, synthetic/no-data rehearsal, package resources, security checks, Playwright, axe, and screenshots.
- Remote evidence: only read-only preflight is currently authorized.
- Scientific mode: GAMENet source-native canary is Reproduction Mode only.
- Current resources: local Mac control plane. No data, GPU, 319 write, duration, cost, license, credential, or formal experiment authority has been granted.

## Known failures

- Allowed Action Requests are queued as isolated files and never advance.
- Dependencies cannot distinguish successful terminal state from failed or stuck terminal state.
- Browser has no replayable status stream or reconnect cursor.
- Decision evidence is not assembled from conclusion to grounds to raw public-safe artifacts.
- GAMENet has unresolved license, environment-lock, adapter-smoke, readiness, remote-revision, and data-root gates.
- ARIS startup does not validate and atomically activate a latest candidate with last-known-good fallback.

## Current unknowns

- Whether one declaration schema can cover all final-five lanes without weakening per-lane scientific identity.
- Whether ARIS exposes a stable non-interactive bridge surface suitable for fixed declaration-owned commands.
- Which exact SafeDrug-main launch command and environment lock will be accepted after authorized 319 inspection.
- Whether the user will authorize real data, GPU, 319 writes, cost, license work, and canary duration.

## Exit conditions

- Continue: local control chain, Base UI migration, production browser evidence, and no-data rehearsal pass.
- Revise: a state transition, declaration binding, UI primitive, or evidence schema fails twice; return to original logs and contract.
- Stop: any change would broaden browser authority, change scientific semantics, exceed declared resources, weaken privacy/integrity, or require ungranted remote authority.
