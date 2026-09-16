# Baseline subtree instructions

This subtree owns external baseline source identity, isolated execution, adapters, and historical reproduction/comparison provenance.

New paper-facing experiments are governed by:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`
- `docs/guides/PAPER_METHOD_CARD_TEMPLATE.md`

Historical `Reproduction Mode` and `Comparison Mode` records remain valid evidence for what they actually executed. They are no longer the active scientific abstraction for new paper comparisons.

## Method identity first

For every paper-facing baseline:

- pin a primary-source paper and a trustworthy implementation revision;
- write one concise Method Card before expensive adaptation/training;
- preserve the scientific core: representation, information flow, objective/supervision, memory/update semantics, decoder/factorization, and required external assets;
- do not reject a method using a weak inspired rewrite;
- do not require byte-for-byte upstream execution when benchmark-specific Dev choices are legitimately allowed by the paper contract.

`baselines/registry.toml` remains authority for historical integration identities, environments, source pins, and completed earlier qualifications. Its mode/readiness fields do not automatically certify a future paper row.

## Adaptation boundary

Mechanical integration may translate file formats, identifiers, vocabulary order, storage, device placement, padding, and common evaluator payloads when the represented computation is preserved.

Benchmark-specific Train/Dev choices such as learning rate, bounded regularization, training horizon, checkpoint rule, early stopping, and global decoder operating point may be selected only through the frozen paper contract and Method Card.

A change to core objective, information availability, model logic, medication representation, memory semantics, prediction factorization, external knowledge, or optimization dynamics that materially changes training must be explicitly justified by equivalence evidence or named as a variant.

Batching is not automatically mechanical. If it changes optimizer update granularity or the effective objective, treat it as a scientific/training change until proven otherwise.

## Sanity before ranking

Reference numbers are sanity evidence only when dataset, split, input budget, eligibility, metric aggregation, and selection profile are sufficiently aligned. A large aligned discrepancy triggers investigation; do not tune toward a historical number as an admission target.

Source-native execution may be used as a sanity/reference profile. It is not a separate active scientific mode.

## Runtime boundaries

- External baselines run in their declared isolated Conda environment on the 319 Execution Plane.
- Core evaluation remains separate from baseline dependencies.
- Restricted data, patient-level predictions, model weights, and private runtime paths never enter Git.
- Target-bearing payloads remain core-owned unless the published method scientifically requires target information at training time; current/future target leakage at prediction time is never allowed.

## Changes

Keep baseline-specific fixes local. Promote a generic integration capability only after more than one real method needs it and its semantics are stable.

Historical mode documents and registry records are preserved for provenance; do not rewrite them to look like they were created under the current paper contract.
