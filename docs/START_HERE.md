# Start here

Use this page to find the source of truth for the question in front of you.

## Understand the project

- [`../CONTEXT.md`](../CONTEXT.md) defines domain terms, research modes, records, and readiness states.
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) maps modules, ownership, dependency direction, and trust boundaries.
- [`specs/UNIFIED_RESEARCH_PROTOCOL.md`](specs/UNIFIED_RESEARCH_PROTOCOL.md) defines the Comparison Mode 1.0 base contract.
- [`specs/UNIFIED_RESEARCH_PROTOCOL_V1_1.md`](specs/UNIFIED_RESEARCH_PROTOCOL_V1_1.md) is the current additive Comparison Mode amendment. Read it with the 1.0 base contract; neither document silently replaces the other.

## Work on the repository

- [`PLANS.md`](PLANS.md) lists accepted multi-step work and its current outcome.
- [`plans/`](plans/) contains implementation-ready plans and their decision history.
- [`playbooks/index.md`](playbooks/index.md) routes operational work to the relevant playbook.

## Inspect research state

- [`../baselines/registry.toml`](../baselines/registry.toml) is the baseline identity, Reproduction Program, and readiness registry.
- [`../baselines/safedrug_archived.py`](../baselines/safedrug_archived.py) is the implemented four-lane archived Reproduction Program.
- [`../research/README.md`](../research/README.md) explains curated Research Memory and Failure Records.
- [`../README.md`](../README.md) gives runnable local commands and the current public-safe status.

## 科研方法参考

- [基于第一性原理的科研实践](guides/first-principles-research-practice.md) 将选题、解题、实验诊断、记录、阅读、讨论和写作组织为一条可检查的证据链。
- [来源台账](guides/first-principles-research-practice-sources.md) 记录该资料使用的公开来源、访问状态和未读取内容的限制。

Real data, model training, GPU work, and baseline Conda environments run only on `319-wild` after the remote preflight passes. Local runs are limited to core tests, synthetic fixtures, protocol checks, status publication, and the loopback harness.
