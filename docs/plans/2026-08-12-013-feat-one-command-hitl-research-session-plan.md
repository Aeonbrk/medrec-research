# One-command HITL Research Session

## Status

Completed locally on 2026-08-12. This plan replaces the manual collection of status, research-loop, authority-bundle, port, and browser-launch arguments with one repository-root command:

```bash
./start-research
```

## Product contract

The command starts a real project session, not a synthetic demonstration. It discovers the repository and installed ARIS checkout, performs a read-only 319 preflight, publishes public-safe current projections under the ignored `runtime/hitl/` directory, starts the packaged production Web console on literal loopback, and opens it in the default browser. The existing versioned `research/` directory prevents a same-name root executable on Unix, so the unambiguous root entrypoint is `start-research`.

The human researcher remains the only scientific authority:

- H1 explicitly freezes one complete, current reproduction contract before work is eligible to start.
- H2 explicitly records `go`, `revise`, `kill`, or `hold` for one current Decision Packet.
- `go` remains invalid unless the packet is current, complete, usable, and accepted.
- H1/H2 never become Action Gate credentials and never execute a remote command by themselves.

Mechanical discovery and projection are automatic. Scientific approval, restricted-data authority, license resolution, source synchronization, environment creation, resource allocation, job submission, and destructive remote operations are not inferred from starting the console.

## Scope change

The earlier React console plan deliberately preserved a read-only browser and prohibited new write endpoints. The current product request explicitly asks for an operational Human-in-the-loop system. This plan therefore permits two narrow loopback-only writes: creation of an H1 record from the current contract and creation of an H2 record from a current packet. The existing `/api/action-requests` schema and Action Gate semantics remain unchanged.

No endpoint accepts shell text, argv, hostnames, filesystem paths, source revisions, contract digests, or packet digests supplied by the browser. The server resolves all protected identities from its current ignored runtime state.

## Runtime layout

`runtime/hitl/` is the ignored, local session system of record:

```text
runtime/hitl/
├── authority-bundle.json       # optional external Action Gate authority
├── contract.json               # current production reproduction contract
├── h1.json                     # human H1 record
├── packets/                    # current Decision Packets by lane
├── h2/                         # human H2 records by lane
├── project-status.json         # generated public-safe project projection
├── research-loop.json          # generated HITL projection
├── remote-preflight.json       # generated read-only 319 observation
└── action-requests/            # allowed requests, queued but not executed
```

The launcher never copies files from `fixtures/` into this directory and never falls back to fixture state. Missing files produce named blockers.

## Remote preflight

Every launch tries `319-lab` first and `319-lab-via-server` second. The fixed read-only probe verifies the expected remote account, checkout existence and cleanliness, remote revision, whether `MEDREC_DATA_ROOT` is configured and exists, Conda availability, GPU capacity, and disk headroom. It records booleans, counts, revisions, and reason codes only; it does not record addresses, credentials, data paths, environment variables, patient data, process command lines, or raw remote logs.

The coordinator fails closed when any required observation is missing. In particular, it must not pull or reset the remote checkout, create a data root, create or modify a Conda environment, kill a process, reserve a GPU, or submit a job.

## Session state and actions

The generated Project Status uses repository-owned program, audits, registry, ARIS manifest, local source identity, and the remote preflight as authorities. Runtime blockers are additive to existing source/license/readiness blockers.

The generated Research Loop Status is always structurally available, including before H1. This lets the console explain `contract-missing`, `h1-stale-or-missing`, packet gaps, and remote blockers instead of replacing them with an opaque unavailable panel.

Allowed Action Requests may be atomically queued in `runtime/hitl/action-requests/`. Queueing is not execution. A future fixed-command remote submitter must independently require a current H1/H2, a usable packet, an allowed Action Gate decision, matching immutable local and remote revisions, a configured data root, a verified declared environment, and fresh capacity.

## Acceptance examples

- From any working directory, running the repository-root `./start-research` requires no JSON path arguments, prints the selected loopback URL, and opens the packaged production console.
- With no production contract, the console identifies `contract-missing`; it does not show synthetic lanes and cannot create H1.
- If the primary SSH profile fails and the fallback authenticates as the expected account, the preflight succeeds through the fallback without exposing connection details in the browser.
- A missing data root, dirty or mismatched checkout, undeclared/unverified environment, insufficient capacity, or unresolved license appears as a blocker and prevents executable authority.
- H1 creation binds the server-loaded current contract. A changed contract makes the old H1 stale.
- H2 creation binds the server-loaded packet. `go` against an ineligible or stale packet is rejected by the existing constructor.
- Stopping the launcher stops the loopback server; it does not alter remote state.

## Verification

- Unit-test preflight parsing, primary-to-fallback selection, public-safe serialization, runtime projection, and H1/H2 stale/current behavior with injected command results.
- Integration-test the one-command CLI, loopback origin/Host protections, narrow POST schemas, atomic records, missing-authority behavior, and queued-versus-executed separation.
- Run the complete Python, Ruff, frontend type/lint/test/build, build-drift, production browser, wheel, Markdown, and agent-document gates.

## Current real blockers

The 2026-08-12 read-only observation reached 319 through the fallback profile, found an existing clean checkout and available GPU capacity, but found a source revision different from the local accepted revision and no configured `MEDREC_DATA_ROOT`. Baseline environment identity/readiness, SafeDrug license disposition, and source-backed acceptance intervals are not yet verified. The launcher must report these facts; implementation of the launcher does not resolve them.
