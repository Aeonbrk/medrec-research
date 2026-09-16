<!-- markdownlint-disable MD013 -->

# Research organization

This directory contains the scientific evidence, exploratory prototypes, formal Ideas, and cross-project memory for `medrec-research`.

## Current state

The current scientific state is maintained in [`memory/current-research-state.md`](memory/current-research-state.md).

As of 2026-09-15:

- **Active formal Idea**: none.
- **Ideas 001--008**: terminated.
- **Idea 009**: not created.
- **Formal Gate**: none active.
- **Current phase**: architecture-first open search after modern-backbone calibration and interaction-first closure.
- **Modern-backbone calibration**: `MODERN_BACKBONE_CALIBRATION_COMPLETE`.
- **Residual interaction family**: closed as a primary research direction after frozen-unary isolation showed only `+0.000257` privileged Oracle Jaccard headroom over the original MoleRec unary surface.
- **Quarantined evaluation resources**: G3/G4, R0 Holdout, and historical project test remain untouched according to the current recorded evidence.

The next research step is not another backbone hunt, residual reranker, or diagnostic chain. It is broad architecture search followed by one small decisive Train/Dev prototype of the best mechanism-bearing candidate.

## Directory structure

- [`prototypes/`](prototypes/README.md): bounded pre-Idea architecture, mechanism, target-supportability, and baseline-calibration screens. A prototype does not require an Idea number or formal Gate.
- [`ideas/`](ideas/README.md): formal Ideas that survived far enough to justify a frozen scientific protocol. Ideas 001--008 are historical and terminated.
- [`memory/`](memory/README.md): current cross-project synthesis, reusable lessons, historical literature/search records, and failure memory.
- `premise-audit/`: bounded premise checks retained for provenance; not a standing exploratory lane.
- `baselines/`: reproduction/comparison infrastructure, separate from scientific Idea failures.

## Research policy

The project targets a real method paper. New architectures and models are explicitly welcome. Search broadly and test narrowly:

```text
step back
→ broad literature / adjacent-method search
→ choose one candidate with a real mechanism
→ one-seed Train/Dev prototype
→ decisive control / ablation
→ continue / redesign once / kill
```

Historical failures constrain equivalent formulations; they do not ban architectural primitives or adjacent families by name. A failed GNN does not ban GNNs, a failed interaction head does not ban every patient-conditioned interaction, and prior art on a component does not prevent a coherent new combination. Novelty and closest-work rigor become strict for survivors and paper claims, not as a barrier to cheap architecture discovery.

The strongest simple/equal-information control remains mandatory for interpretation. Public baseline adaptation must be faithful, and literature scores are comparable only when the information budget and evaluation semantics match.

See [`../docs/playbooks/RESEARCH_WORKFLOW.md`](../docs/playbooks/RESEARCH_WORKFLOW.md) for the prototype-first workflow and [`memory/current-research-state.md`](memory/current-research-state.md) for current routing.
