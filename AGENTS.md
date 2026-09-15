# MedRec Research Agent Instructions

## Research objective

This repository is the active research home for medication-recommendation method research. Optimize for:

```text
scientific value × iteration speed × trustworthy evidence
```

The immediate goal is a credible first method paper. CCF-B-level publishability is a practical floor; CCF-A is a stretch target. New architectures, new representations, new prediction granularities, new decoders/inference procedures, new supervision paradigms, and coherent combinations of known primitives are all allowed.

Use `docs/guides/first-principles-research-practice-sources.md` as methodological background, but do not turn any checklist, novelty heuristic, prior failure, or workflow artifact into a substitute for scientific judgment.

## Research execution principles

Default exploratory workflow:

```text
step back
→ broad literature / method search
→ choose one mechanism-bearing candidate
→ fast Train/Dev prototype
→ decisive comparison / ablation
→ continue / redesign once / kill
```

Early prototypes normally use one seed, one main configuration, Train/Dev only, and a strong baseline. Formal claim-support rigor is paid after a method earns it.

Architecture-first means changing what is modeled when the evidence calls for it. Prioritize candidates that introduce a materially different object, interaction, information flow, prediction granularity, decision process, decoder, or supervision structure. Before implementation, answer:

```text
What new object, interaction, information flow, or decision process is modeled?
Why can a strong simple baseline not already express it?
```

If the current backbone did not exist, periodically ask how the task would be formulated from scratch.

Search beyond Medication Recommendation when useful: structured prediction, set/list generation, optimization, energy models, graph learning, mixture-of-experts, retrieval/ranking, counterfactual learning, reinforcement learning, multimodal learning, and adjacent recommendation research. Do not force fashionable methods into the problem.

Historical failures are evidence about the tested formulation, information budget, controls, and data. They are not universal bans on words such as GNN, hypergraph, retrieval, MoE, interaction, or structured prediction. A primitive from a failed route may be reused inside a materially different mechanism. Two bounded weak prototypes in the same family should normally trigger a family reset rather than repeated rescue.

Novelty is important for a paper, but it is not the admission gate for a cheap prototype. Early literature search should prevent obvious duplication and expose strong controls. Rigorous closest-work and novelty verification from primary sources is required for survivors before formal paper claims. A coherent A+B+C mechanism can be publishable even when its individual components are known.

Do not spend repeated cycles tuning thresholds, hidden sizes, loss weights, retrieval K, layer counts, or small heads to rescue a weak mechanism. One cheap diagnostic is acceptable when it can distinguish implementation/decoding failure from scientific failure.

Useful screening magnitudes include roughly Jaccard `+0.010`, or DDI `-0.010` with Jaccard loss no worse than about `0.005`, or a clear accuracy–safety Pareto improvement. These are heuristics, not laws.

## Evidence and provenance

- `research/memory/current-research-state.md` is the current scientific-state synthesis and routing authority.
- Raw experiment result files, audit records, and idea-local artifacts remain the evidence authority for the runs they describe.
- Historical memory documents are discovery aids and provenance records. Their old `CLOSED`, `CROWDED`, `PRIOR ART`, authorization, or routing labels apply to the recorded scope and date; they do not override the current-state synthesis.
- Novelty, closest-work, SOTA, and benchmark-comparability claims must be verified from primary sources when they matter to a survivor decision or paper claim.
- Public baseline adaptation is fidelity-first: prefer official source plus a thin data/evaluation wrapper. A semantically inspired rewrite cannot be used to reject a published method.
- Reported literature performance is not automatically a comparable frontier. Information budget, prediction-time semantics, split, vocabulary, and evaluation must match.

Run a check only when it can detect a concrete failure that would change trust or action. Do not manufacture review findings or add verification ceremony without a decision consequence.

## Architecture invariants

- The Unified Research Protocol owns first-party comparison semantics.
- Reproduction Mode preserves recorded upstream behavior. Comparison Mode uses the shared protocol.
- A Baseline Core remains unchanged in Comparison Mode. Prediction Adapters may translate representations but must not change scientific behavior.
- Core development uses Python 3.11 and Homebrew `/opt/homebrew/bin/uv`. Each external baseline runs in an isolated Conda environment and process.
- Conda, pip, and uv package resolution prioritizes repository/command-scoped China mirrors; unavailable exact artifacts fall back to official HTTPS authorities with TLS verification enabled. Never disable TLS verification or mutate machine/user-global package-manager configuration.
- The local MacBook Air is the harness terminal. Run only core tests, synthetic fixtures, protocol checks, submission, monitoring, and public-safe audits locally.
- Run real-data experiments, model training, GPU inference, and baseline Conda environments only on `319-wild` after the remote-execution preflight passes.
- Patient data, split membership, patient-level predictions, model weights, and private traces never enter Git.
- The Local Data Root lives outside every Git repository. Version only public-safe Dataset Manifests, aggregate evidence, and synthetic fixtures.
- Git may contain compact public-safe prototype contracts, aggregate results, failure records, audits, and current-state syntheses. A formal Gate is not required merely to record an exploratory Train/Dev prototype.
- `New-Search` is a read-only Research Archive. Cite its commit and path when migrated evidence depends on it.

## Sources of truth

- `CONTEXT.md`: canonical domain language.
- `ARCHITECTURE.md`: module and seam map.
- `docs/PLANS.md`: accepted multi-step work tracker.
- `docs/plans/`: implementation plans.
- `docs/specs/UNIFIED_RESEARCH_PROTOCOL.md`: comparison contract.
- `baselines/registry.toml`: baseline identity and readiness.
- `research/memory/current-research-state.md`: current scientific state and next-phase boundary.
- `research/prototypes/README.md`: exploratory prototype inventory.
- `research/ideas/README.md`: formal Idea inventory.
- `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md`: Mac harness and 319 execution contract.
- `Handoff.md`: concise current handoff for the next agent/session.

## Work rules

- Prefer standard-library modules in the core package. Add dependencies only when they remove real complexity.
- Use `apply_patch` for manual file edits.
- Use `rg` for literal searches. Use CodeGraph or Semble before exploratory code search when available.
- Keep imported baseline source out of this repository unless its license, provenance, and need have been reviewed.
- Run lightweight Python commands through `rtk proxy /opt/homebrew/bin/uv run`. Run baseline commands through their declared Conda environment.
- Follow `docs/playbooks/REMOTE_319_EXECUTION_PLAYBOOK.md` before real-data or GPU commands. A local synthetic run proves harness behavior only.
- Use available GPUs to parallelize distinct hypotheses, strong controls, or survivor seeds rather than broad hyperparameter sweeps.
- Record substantial engineering work in `docs/PLANS.md` when useful; do not require a planning artifact for a tiny bounded scientific probe.

## Completion checks

```bash
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
markdownlint '**/*.md' --ignore '.agents/**'
```

## Scope limits

These bound what you propose, never what you look for.

1. This is not a security paper. Verification is welcome; over-defense is not. Unless the project states otherwise, assume a cooperating operator on their own machine.
2. Do not add hashes, checksums, fingerprints, feature flags, migration frameworks, compatibility layers, or wrappers unless they solve a concrete observed need and change execution or trust.
3. Do not optimize for exotic corner cases that are not reachable through supported inputs, published interfaces, or real project data.
4. Where judgment is needed, judge. Do not replace it with scoring tables, authorization churn, or repeated re-review of settled evidence.
5. Before running any check, answer: what specific failure would this detect, and what would change if it occurred? If there is no answer, do not run the check.
6. Say plainly when something is correct. Do not manufacture findings.
