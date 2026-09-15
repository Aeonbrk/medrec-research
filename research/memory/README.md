<!-- markdownlint-disable MD013 -->

# Cross-Project Research Memory

This directory stores the current research-state synthesis, reusable lessons, failure records, and historical search/literature snapshots.

## Authority and precedence

Use the following order when documents disagree:

1. **Run-local evidence**: aggregate result JSON, audit records, formal Idea artifacts, and source-bound experiment README files describe what actually happened in that run.
2. **Current synthesis**: [`current-research-state.md`](current-research-state.md) is the authoritative current scientific-state and routing summary.
3. **Indexes / handoff**: `research/README.md`, `research/ideas/README.md`, `research/prototypes/README.md`, and `Handoff.md` summarize the current synthesis.
4. **Historical memory**: older literature maps, reset packets, review notes, failure records, and reorientation documents preserve what was believed or decided at their recorded time. Old `CLOSED`, `CROWDED`, `PRIOR ART`, `NOT AUTHORIZED`, or routing labels do not override later evidence.

Do not edit historical result records merely to make their old state labels look current. Resolve contradictions by fixing the current synthesis and clearly marking historical snapshots.

Within current synthesis, distinguish:

- **observed result** — directly produced by a run or audit;
- **interpretation** — scientific reading of the evidence;
- **routing guidance** — current prioritization for future work.

Do not present routing guidance as if it were a runner-produced terminal verdict.

## Current state

See [`current-research-state.md`](current-research-state.md).

As of 2026-09-15:

```text
Active formal Idea: none
Ideas 001--008: terminated
Idea 009: absent
Active formal Gate: none
Modern backbone calibration: MODERN_BACKBONE_CALIBRATION_COMPLETE
Strong-unary pairwise residual-correction route: deprioritized
Current phase: architecture-first open search
```

The frozen-unary residual run itself returned `DEPENDENCE_NOT_ALIGNED_WITH_SET_ACCURACY`; the project-level decision to deprioritize repeated strong-unary pairwise residual correction is a routing interpretation, not a replacement of that run-local verdict.

The project is deliberately **not** precommitted to a named architecture. New models, representations, prediction granularities, training paradigms, decoders, and coherent combinations are open for search.

## Durable evidence bundles

- [`modern-backbone-calibration.md`](modern-backbone-calibration.md): faithful recent-baseline calibration and information-budget lessons.
- [`../prototypes/README.md`](../prototypes/README.md): current inventory of pre-Idea prototypes, mechanism screens, and observed terminal decisions.
- [`../ideas/README.md`](../ideas/README.md): formal Ideas 001--008 and their terminal scope.
- [`failures/`](failures/): failure records. These are formulation-local evidence, not universal architectural prohibitions.
- [`reusable-lessons.md`](reusable-lessons.md): methodological lessons from multiple routes.
- [`accumulated-experience.md`](accumulated-experience.md): historical archive synthesis; not live routing authority.

## Historical discovery material

- [`literature-opportunity-map.md`](literature-opportunity-map.md): historical literature/opportunity snapshot. Use it for discovery and prior search provenance, not as a current novelty gate.
- [`research-space-reorientation.md`](research-space-reorientation.md): current directional synthesis, with historical boundaries explicitly scoped.
- `model-reset-*`, `literature-search-*`, and `resource-reset-*` directories: dated search/reset packets. Their authorization language belongs to those packets only.

## How to use failure memory

Failure memory should answer:

```text
What exact formulation was tested?
What strong control absorbed it?
What information budget and target semantics were used?
What should we avoid repeating unchanged?
What components remain reusable in a materially different mechanism?
```

Do not generalize `a tested formulation failed` into `the entire method family is impossible`. Conversely, do not rename an equivalent failed formulation and rerun it without a new scientific reason.

## Research posture

- Search broadly, execute narrowly, kill weak directions quickly.
- Prefer architecture-level hypotheses over small residual corrections when the evidence supports a reset.
- Use strong simple baselines and equal-information controls.
- Treat novelty as a survivor/paper requirement, not a barrier to cheap discovery.
- Preserve raw negative evidence, but keep the search space open to genuinely different capabilities, objects, inductive biases, and information flows.
- Stop diagnostic chains once they answer the scoped scientific question.
- Treat prototype-first execution as the default, not an absolute rule; formalize earlier when the scientific contract itself requires it.
