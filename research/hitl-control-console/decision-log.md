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
