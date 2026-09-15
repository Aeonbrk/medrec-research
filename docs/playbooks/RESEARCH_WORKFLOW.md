# Research Workflow

This workflow separates **fast scientific search** from **formal claim support**. The default objective is to test important hypotheses quickly without lowering the evidence standard for methods that survive.

## Directory philosophy

- `research/prototypes/`: bounded pre-Idea architecture, mechanism, target-supportability, and baseline-calibration screens. A prototype may fail, succeed, or only answer a diagnostic question. It does not need an Idea number or formal Gate.
- `research/ideas/<idea-name>/`: formally admitted survivors whose scientific object and decisive experiment are mature enough to justify a frozen protocol.
- `research/baselines/`: baseline reproduction/comparison infrastructure. Baseline execution failure is not automatically scientific-method failure.
- `research/memory/`: current cross-project synthesis plus reusable lessons and historical search records.
- `papers/<paper-name>/`: claim-support experiments and manuscript lifecycle after a method has earned promotion.

## Two-lane workflow

### Lane A — exploratory method search

Use this lane by default when no method has survived yet:

```text
step back
→ broad literature / adjacent-method search
→ formulate one mechanism-bearing candidate
→ implement the smallest decisive Train/Dev prototype
→ compare against a strong simple baseline and a mechanism control
→ continue / redesign once / kill
```

Typical early screen:

- one seed;
- one main configuration;
- Train/Dev only;
- no held-out test/Audit use;
- no broad hyperparameter sweep;
- one decisive matched ablation when the mechanism requires it.

A cheap diagnostic is allowed when the result could distinguish implementation/decoding failure from scientific failure. Repeated diagnostics that do not change the decision are not a research program.

Prototype code and aggregate public-safe results belong under `research/prototypes/`. Do not create Idea 009, a formal Gate, or a paper directory merely to test a new architecture.

### Lane B — survivor formalization and claim support

A prototype enters the formal lane only after it shows material signal or otherwise earns a paper-level investigation:

```text
surviving prototype
→ closest-work / novelty verification from primary sources
→ formal Idea or paper candidate
→ frozen experiment design
→ execute
→ verify integrity + decide
→ multi-seed / strong-baseline / decisive-ablation claim support
```

Formalization should add rigor, not ceremony. A coding bug normally means `fix → regression test → smoke test → rerun`, not a new authorization chain unless the scientific protocol changed.

## Scientific admission principles

Before implementing a candidate, state:

```text
What new object, interaction, information flow, prediction granularity,
training signal, or decision process is modeled?

Why can the strongest simple baseline not already express it?
```

This is a mechanism test, not a novelty-maximization test. Known primitives may be combined when their interaction creates a materially different capability.

Early literature search should identify obvious duplicates and strong controls. Do not reject a cheap architecture prototype merely because some component is prior art, the family is crowded, or a historical memory file used a `CLOSED` label for a narrower formulation. Rigorous novelty subtraction is required after empirical survival and before paper claims.

Negative evidence is local to the tested formulation and entitlement. Preserve it, use it to avoid repeating equivalent experiments, and reset a weak family after bounded failures. Do not transform a failed route into a universal ban on an architectural primitive.

## Baseline and information-budget rules

Public baseline adaptation is fidelity-first:

1. prefer official source at a pinned revision;
2. change data/split/evaluation plumbing through the thinnest practical wrapper;
3. document any semantic deviation;
4. never interpret a low score from a materially rewritten approximation as evidence that the published method is weak.

Reported literature metrics enter the canonical numerical frontier only when prediction-time information, target/vocabulary, split/evaluation semantics, and other material entitlements are comparable. Otherwise retain them as literature context.

A strong baseline is evidence, not a mandatory backbone. New models may be designed from scratch.

## Experiment execution

1. **Define the question.** Write the mechanism and the cheapest result that would change the decision.
2. **Fix the bounded screen.** Declare data entitlement, comparator, seed/configuration, metrics, and stopping interpretation. Formal Gate paperwork is unnecessary for a pre-Idea prototype.
3. **Execute on the proper plane.** Freeze a source revision, run real-data/GPU work on 319, and keep restricted artifacts outside Git.
4. **Check only decision-relevant integrity.** Leakage, target timing, index alignment, baseline fidelity, or source identity should be checked when they could invalidate the conclusion.
5. **Decide.** Continue, redesign once, or kill. Do not rescue weak effects with unbounded tuning.
6. **Record compact evidence.** Preserve aggregate metrics, scope, provenance, and the scientific interpretation. Promote genuinely cross-project lessons to `research/memory/`.

## Formal Idea / paper experiments

For a survivor, freeze the comparison contract before claim-support evaluation. Strong baselines, equal-information controls, multiple seeds where appropriate, decisive ablations, untouched evaluation data, and statistical evidence belong here.

Changes to cohort, split, target, material feature entitlement, or selection rule invalidate downstream claim-support evidence and require a revised frozen protocol. This rule applies to formal evidence; it should not be used to prevent exploratory Train/Dev architecture search.

## Test and reserve data

Held-out resources are evaluation-only. Do not use them to choose architecture, threshold, seed, prompt, checkpoint, loss weight, or post-processing. If historical test evidence has already influenced a route, use a genuinely untouched confirmatory resource before making a new paper claim.

## Git acceptance

Git may contain public-safe:

- prototype contracts and aggregate Train/Dev results;
- Dataset Manifests and synthetic fixtures;
- baseline provenance/fidelity audits;
- formal protocols and aggregate Run Records;
- Failure Records and cross-project research syntheses.

Git may not contain EHR rows, split membership, patient-level outputs, checkpoints, credentials, private host details, or raw workflow traces.

## Execution model

Use the MacBook Air as the harness terminal and `319-wild` as the execution plane. Follow `REMOTE_319_EXECUTION_PLAYBOOK.md`; local synthetic execution proves harness behavior only.
