# Paper subtree instructions

`papers/` is for mature, publication-facing survivor packages. Do not move speculative or weak early ideas here.

Paper-stage work is governed by:

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EVALUATOR_SPEC.md`

## Entry boundary

A paper package is justified only after the scientific mechanism survives bounded Train/Dev falsification, credible references exist, closest-work boundaries are understood, and a cohesive candidate claim is worth formal confirmation.

Early prototypes and architecture search remain under `research/`.

## Evidence discipline

A paper result must distinguish two properties:

- **final-table eligible**: frozen method/benchmark/evaluator/selection policy, declared final seeds, complete traceability, no unresolved correctness issue;
- **independent confirmation**: additionally evaluated on a population that did not feed back into model/protocol/analysis choices.

A historically exposed standard benchmark may still be reported, but not described as untouched confirmation. The primary confirmatory conclusion for a new method should have at least one non-feedback evaluation population when the project can support one honestly.

Paper-stage work may include:

- strong recent and closest baselines under explicit Method Cards;
- decisive matched ablations and mechanism attribution;
- multiple frozen training seeds;
- accuracy/DDI/cardinality analysis;
- predeclared patient-cluster uncertainty for central comparisons;
- robustness/subgroup analyses that were fixed before Test;
- final efficiency measurement;
- manuscript, figures, tables, reviews, and submission artifacts.

The protocol can be frozen while scientific claims still narrow in response to results. Do not preserve a storyline when final evidence weakens it.

## Final confirmation

`Test once` means one frozen confirmatory analysis phase, not one function call. Before the phase starts, freeze methods, configs, seed sets, checkpoint/operating-point selection, evaluator, nominated comparisons, and planned Test analyses.

Do not select a `strongest comparator` after seeing Test if the paper will make a formal paired claim against it. Nominate that comparison from Dev/scientific role first, or account for additional multiplicity.

Failures are evidence: do not silently drop divergent/OOM/no-checkpoint final seeds or replace them with new seed IDs.

## Provenance

Publication-facing claims must link back to authoritative run records or source-bound aggregate evidence. Do not copy exploratory numbers into the manuscript without preserving dataset profile, evaluation feedback status, information budget, seed set, checkpoint/operating-point rule, source revision, and evaluator identity.

Novelty, closest-work, SOTA, and benchmark-comparability claims require primary-source verification.
