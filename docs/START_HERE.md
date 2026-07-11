# Start here

Use this page to find the source of truth for the question in front of you.

## Understand the project

- [`../CONTEXT.md`](../CONTEXT.md) defines domain terms, research modes, records, and readiness states.
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) maps modules, ownership, dependency direction, and trust boundaries.
- [`specs/UNIFIED_RESEARCH_PROTOCOL.md`](specs/UNIFIED_RESEARCH_PROTOCOL.md) defines first-party comparison semantics.

## Work on the repository

- [`PLANS.md`](PLANS.md) lists accepted multi-step work and its current outcome.
- [`plans/`](plans/) contains implementation-ready plans and their decision history.
- [`playbooks/index.md`](playbooks/index.md) routes operational work to the relevant playbook.

## Inspect research state

- [`../baselines/registry.toml`](../baselines/registry.toml) is the baseline identity and readiness registry.
- [`../research/README.md`](../research/README.md) explains curated Research Memory and Failure Records.
- [`../README.md`](../README.md) gives runnable local commands and the current public-safe status.

Real data, model training, GPU work, and baseline Conda environments run only on `319-wild` after the remote preflight passes. Local runs are limited to core tests, synthetic fixtures, protocol checks, status publication, and the loopback harness.
