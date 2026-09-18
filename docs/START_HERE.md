# Start here

Use this page to find the source of truth for the question in front of you.

## Project semantics

- [`../CONTEXT.md`](../CONTEXT.md): canonical domain language.
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md): current module, ownership, dependency, and execution map.
- [`KNOWLEDGE_HOMES.md`](KNOWLEDGE_HOMES.md): where current facts, engineering decisions, scientific evidence, scientific belief updates, plans, and handoff state belong.
- [`../AGENTS.md`](../AGENTS.md): repository-wide invariants and routing to subtree rules.

## Current paper experiment contract

Read these together:

- [`specs/PAPER_EXPERIMENT_CONTRACT.md`](specs/PAPER_EXPERIMENT_CONTRACT.md): v1.0 base paper-facing experiment governance, evidence roles, baseline adaptation, Dev selection, seeds, Test use, statistics, and research lifecycle.
- [`specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`](specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md): current additive amendment covering asymmetric development effort, anti-underoptimization baseline fairness, benchmark-role defaults, harmonized-131 lineage audit, and control/ablation optimization.
- [`specs/PAPER_EXPERIMENT_CONTRACT_V1_2.md`](specs/PAPER_EXPERIMENT_CONTRACT_V1_2.md): current additive seed-policy amendment covering the MoleRec-derived canonical seed convention for project-owned initial development screens, survivor multi-seed boundaries, and source-native seed policy for external baselines.
- [`specs/PAPER_EVALUATOR_SPEC.md`](specs/PAPER_EVALUATOR_SPEC.md): current core metric and aggregation semantics.
- [`guides/PAPER_METHOD_CARD_TEMPLATE.md`](guides/PAPER_METHOD_CARD_TEMPLATE.md): concise per-method identity/adaptation/selection record.

The historical [`specs/UNIFIED_RESEARCH_PROTOCOL.md`](specs/UNIFIED_RESEARCH_PROTOCOL.md) and [`specs/UNIFIED_RESEARCH_PROTOCOL_V1_1.md`](specs/UNIFIED_RESEARCH_PROTOCOL_V1_1.md) remain provenance for earlier Reproduction/Comparison work. They do not govern new paper-facing experiments.

## Scientific state

- [`../research/memory/current-research-state.md`](../research/memory/current-research-state.md): live scientific synthesis and next-phase boundary.
- [`../research/README.md`](../research/README.md): research directory roles.
- [`../research/memory/README.md`](../research/memory/README.md): evidence precedence and research-memory boundaries.
- [`../papers/README.md`](../papers/README.md): publication-facing survivor boundary.
- [`../Handoff.md`](../Handoff.md): short current task handoff.

## Baselines

- [`../baselines/registry.toml`](../baselines/registry.toml): historical integration identities, pinned source/environment records, and earlier qualification provenance. Its Reproduction/Comparison fields are not the active paper experiment abstraction.
- [`../baselines/AGENTS.md`](../baselines/AGENTS.md): current baseline-subtree operating rules.

## Work on the repository

- [`PLANS.md`](PLANS.md): active multi-step engineering work only.
- [`plans/`](plans/): scoped implementation plans.
- [`playbooks/index.md`](playbooks/index.md): operating procedures, including remote 319 execution.
- [`.agents/notes/`](../.agents/notes/): append-only engineering decision history. There is intentionally no central notes index.
- [`../research/memory/decisions/`](../research/memory/decisions/): append-only scientific belief updates.

## Execution boundary

Real EHR processing, model training, GPU inference, and baseline Conda environments run on the 319 Execution Plane after the remote preflight. The local MacBook Air is the Harness Terminal for core tests, synthetic checks, submission, monitoring, and public-safe intake.
