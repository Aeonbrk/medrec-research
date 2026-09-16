# Start here

Use this page to find the source of truth for the question in front of you.

## Project semantics

- [`../CONTEXT.md`](../CONTEXT.md): canonical domain language.
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md): current module, ownership, dependency, and execution map.
- [`KNOWLEDGE_HOMES.md`](KNOWLEDGE_HOMES.md): where current facts, engineering decisions, scientific evidence, scientific belief updates, plans, and handoff state belong.
- [`../AGENTS.md`](../AGENTS.md): repository-wide invariants and routing to subtree rules.

## Scientific state

- [`../research/memory/current-research-state.md`](../research/memory/current-research-state.md): live scientific synthesis and next-phase boundary.
- [`../research/README.md`](../research/README.md): research directory roles.
- [`../research/memory/README.md`](../research/memory/README.md): evidence precedence and research-memory boundaries.
- [`../papers/README.md`](../papers/README.md): publication-facing survivor boundary.
- [`../Handoff.md`](../Handoff.md): short current task handoff.

## Protocols and baselines

- [`specs/UNIFIED_RESEARCH_PROTOCOL.md`](specs/UNIFIED_RESEARCH_PROTOCOL.md): Comparison Mode base contract.
- [`specs/UNIFIED_RESEARCH_PROTOCOL_V1_1.md`](specs/UNIFIED_RESEARCH_PROTOCOL_V1_1.md): current additive amendment; read it with the base contract.
- [`../baselines/registry.toml`](../baselines/registry.toml): baseline identity, Reproduction Programs, and readiness.

## Work on the repository

- [`PLANS.md`](PLANS.md): active multi-step engineering work only.
- [`plans/`](plans/): scoped implementation plans.
- [`playbooks/index.md`](playbooks/index.md): operating procedures, including remote 319 execution.
- [`.agents/notes/`](../.agents/notes/): append-only engineering decision history. There is intentionally no central notes index.
- [`../research/memory/decisions/`](../research/memory/decisions/): append-only scientific belief updates.

## Execution boundary

Real EHR processing, model training, GPU inference, and baseline Conda environments run on the 319 Execution Plane after the remote preflight. The local MacBook Air is the Harness Terminal for core tests, synthetic checks, submission, monitoring, and public-safe intake.
