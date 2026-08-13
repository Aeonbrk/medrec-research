# Initial audit review

## Security

The current browser boundary is narrow and same-origin protected. Action Requests now bind server-side to content-addressed declarations and durable records without exposing command or path identifiers. Bridge execution remains absent and blocked; adding generic command fields would be a critical regression.

## Research integrity

Mode separation is explicit and must remain so. GAMENet registry and audit correctly stay `registered` with unresolved license. The old failure record concerns the original GAMENet repository, while the active program selects the SafeDrug-main derivative; launch, revision, seed, environment, and readiness evidence must be reconciled before any canary.

## Product and UI

The current console is production-built and accessible at baseline, but it is section-first rather than pending-decision-first. H1/H2 forms use raw labels and native selects instead of the shadcn field and Base UI selection patterns. Backend SSE now has a durable global cursor; frontend reconnect and complete state rendering remain absent.

## Operations

`./start-research` already performs fail-closed read-only preflight and opens the production harness. It does not validate a latest ARIS candidate, atomically activate it, fall back to last-known-good, or record activation history. Remote submission remains intentionally absent.

## Baseline verification

- Python: `274 passed`; Ruff check and format check pass.
- Frontend: typecheck, lint, `14` unit tests, build, and asset drift pass.
- Worktree: clean before implementation; branch `codex/hitl-base-ui-control-console` created from `af3975f`.
- ARIS: clean `main` checkout at `e12e07c7b85ee1a4dc07e5463089aa16836af2bf`.

## Control-plane correction

The first implementation incorrectly required a current H2 `go` before the first Action Request and used `request_sha256:sequence` as an SSE cursor. Both conflicted with the research contract. Initial execution now requires current H1 plus Action Gate authority and binds the registry-owned GAMENet lane. H2 governs subsequent execution, and SSE uses a global durable journal sequence.
