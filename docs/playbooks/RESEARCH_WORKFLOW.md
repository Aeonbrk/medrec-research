# Research workflow

This workflow separates **fast scientific search** from **formal claim support**. The default objective is to test important hypotheses quickly without lowering the evidence standard for methods that survive.

## Directory philosophy

- `research/prototypes/`: default lane for bounded pre-Idea architecture, mechanism, target-supportability, and baseline-calibration screens. A prototype may fail, succeed, or only answer a diagnostic question. It normally does not need an Idea number or formal Gate.
- `research/ideas/<idea-name>/`: formally admitted research lines whose scientific object and protocol are mature enough to justify a frozen contract. Formalization may occur before a prototype when target semantics, information entitlement, privileged supervision, or another scientific boundary must be fixed first.
- `research/baselines/`: baseline reproduction/comparison infrastructure. Baseline execution failure is not automatically scientific-method failure.
- `research/memory/`: current cross-project synthesis plus reusable lessons and historical search records.
- `papers/<paper-name>/`: claim-support experiments and manuscript lifecycle after a method has earned promotion.

## Two-lane workflow

### Lane A: exploratory method search

Use this lane by default when no method has survived yet:

```text
step back
→ broad literature / adjacent-method search
→ formulate one mechanism-bearing candidate
→ implement the smallest decisive Train/Dev prototype
→ compare against a strong simple baseline and a matched mechanism control
→ continue / redesign once / kill
```

Typical early screen:

- one seed;
- one main configuration;
- Train/Dev only;
- no held-out test/Audit use;
- no broad hyperparameter sweep;
- one decisive matched ablation or control when the mechanism requires it.

A cheap diagnostic is allowed when the result could distinguish implementation/decoding failure from scientific failure. Repeated diagnostics that do not change the decision are not a research program.

Prototype code and aggregate public-safe results belong under `research/prototypes/`. Do not create a formal Idea, Gate, or paper directory merely because a new architecture is being tested. Conversely, do not force a prototype-first sequence when the scientific contract itself must be frozen before modeling.

### Lane B: survivor formalization and claim support

A method typically enters the formal lane after it shows material signal or otherwise earns a paper-level investigation. It may enter earlier when formal target/information semantics are themselves necessary to make the experiment valid.

Typical progression:

```text
surviving or contract-sensitive candidate
→ closest-work / novelty verification from primary sources as appropriate
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
What capability, object, interaction, information flow, inductive bias,
prediction granularity, training signal, or decision process is changed?

What matched strong control can test whether that change, not merely
extra capacity or optimization budget, causes any gain?
```

This is a mechanism/attribution test, not a novelty-maximization test. A strong baseline may in principle be expressive enough to approximate the same mapping; a new method can still be scientifically valuable when its inductive bias, credit assignment, conditional computation, data efficiency, or inference process creates a reproducible capability. Known primitives may be combined when their interaction creates a materially different behavior.

Early literature search should identify obvious duplicates and strong controls. Do not reject a cheap architecture prototype merely because some component is prior art, the family is crowded, or a historical memory file used a `CLOSED` label for a narrower formulation. Rigorous novelty subtraction is required for survivors before paper claims.

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
2. **Fix the bounded screen.** Declare data entitlement, comparator, seed/configuration, metrics, and stopping interpretation. Formal Gate paperwork is normally unnecessary for a pre-Idea prototype.
3. **Execute on the proper plane.** Freeze a source revision, run real-data/GPU work on 319, and keep restricted artifacts outside Git.
4. **Check only decision-relevant integrity.** Leakage, target timing, index alignment, baseline fidelity, or source identity should be checked when they could invalidate the conclusion.
5. **Decide.** Continue, redesign once, or kill. Do not rescue weak effects with unbounded tuning.
6. **Record compact evidence.** Preserve aggregate metrics, scope, provenance, and the scientific interpretation. Distinguish observed run verdicts from later project-level routing decisions. Promote genuinely cross-project lessons to `research/memory/`.

## Formal idea / paper experiments

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
