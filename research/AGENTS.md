# Research subtree instructions

This subtree owns scientific exploration, evidence, formal Ideas, benchmarks, and research memory.

## Scientific loop

Default exploratory loop:

```text
step back
→ search broadly
→ choose one mechanism-bearing hypothesis
→ smallest real Train/Dev prototype
→ decisive matched comparison
→ survive / redesign once / kill
```

Early screening normally uses one seed, one main configuration, full intended training budget, Train/Dev only, and the strongest practical equal-information control. Do not replace real experiments with repeated toy runs, partial training, or broad hyperparameter sweeps.

Architecture-first means the candidate changes at least one meaningful object, representation, information flow, prediction granularity, decoder/inference process, or supervision structure. Existing primitives are allowed when their composition creates a distinct capability.

## Evidence hierarchy

When records disagree:

1. Run-local aggregate result JSON, audit, source-bound README, and frozen protocol describe the run that actually happened.
2. `memory/current-research-state.md` owns current cross-project interpretation and routing.
3. `README.md`, prototype/idea indexes, and root `Handoff.md` summarize the current state.
4. Dated searches, reset packets, failure records, and archived syntheses preserve historical context only.

Never rewrite historical run evidence to make an old conclusion look current. Update the current synthesis or add a new scientific decision note instead.

## Knowledge homes

- `prototypes/`: bounded pre-Idea mechanism, architecture, supportability, and calibration screens.
- `ideas/`: formal Ideas with frozen scientific contracts and their terminal evidence.
- `benchmarks/`: dataset/task contracts and public-safe benchmark records.
- `diagnostics/`: bounded diagnostics whose result can change a concrete decision.
- `memory/current-research-state.md`: short live scientific synthesis.
- `memory/decisions/`: append-only scientific belief updates caused by evidence.
- `memory/failures/`: durable falsified-formulation records.
- `memory/archive/`: superseded live syntheses or mixed historical ledgers retained for provenance.
- `memory/literature-*`, `model-reset-*`, and other dated packets: discovery/provenance snapshots, not current routing authority.

A scientific decision note links to decisive evidence; it does not duplicate raw metrics, logs, or complete experiment narratives.

## Failure and novelty semantics

- A negative result kills the tested formulation, not every primitive used inside it.
- Two bounded weak prototypes in one family normally justify a reset. A third rescue needs a concrete new falsifiable mechanism, not a new name or parameter setting.
- A successful component is a building block, not automatically the mandatory backbone of the next model.
- Primary-source literature is required for novelty, closest-work, SOTA, and benchmark-comparability claims that matter to a survivor or paper.
- Internal X-ray summaries and literature memory are discovery aids only.

## Evaluation boundaries

- Do not use held-out Test, G3/G4, R0 Holdout, or historical test surfaces for exploratory model selection.
- Freeze information budget, target semantics, split roles, and checkpoint-selection rules before interpreting matched comparisons.
- Dataset-specific training budgets may differ when required by data scale; matched arms within a dataset must share the same budget and selection rule.
- Report accuracy and safety separately. A lower DDI rate caused by under-prescription is not automatically a safer recommender.

## Promotion

Prototype evidence earns more rigor only after it survives. Formal Idea/Gate machinery, multiple seeds, strong recent baselines, decisive ablations, statistical evidence, and untouched evaluation belong to survivors rather than weak early hypotheses.

A mature survivor moves to `papers/` only when a cohesive claim-support package is justified.
