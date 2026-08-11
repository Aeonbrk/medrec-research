# Unified Research Protocol v1.1 Amendment

Protocol v1.1 is an additive Comparison Mode amendment to
[Unified Research Protocol 1.0](UNIFIED_RESEARCH_PROTOCOL.md). Existing v1.0
records remain readable and keep their original scope semantics. A v1.1
qualification must carry both the amendment digest and the method-profile
digest; source-native reproduction evidence alone cannot satisfy either field.

## Lineage boundary

The Comparison Scope is built from the SafeDrug `main` processing lineage at
`88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a`. MoleRec's source-native
preprocessing lineage at `c7218d0976e5ee5588aeaf5bdbc86b338126bba5` remains
valid only for Reproduction Mode. It cannot be copied into a v1.1 comparison
qualification.

## Required outcomes and uncertainty

Every v1.1 method is evaluated independently for:

- `ddi_rate`
- `jaccard`
- `f1`
- `prauc`
- `average_medication_count`

The core evaluator owns target joins and recomputes these outcomes from
complete target-free predictions. Baseline-reported aggregates are descriptive
only. The declared uncertainty procedure is ten rounds sampling 80% of the
test set with replacement and an 80% percentile interval. This uncertainty is
not training-seed variance.

## Decoder classes

Each method declares one decoder class:

- `score_threshold`: a threshold may be selected only on validation data using
  the predeclared metric and bounded trial allowance. Test outcomes cannot
  select or revise the threshold.
- `structural_sequence`: the source-defined sequence decoder remains unchanged;
  no threshold selection is attached to this profile.

A Prediction Adapter may translate invocation, identifiers, storage, and output
representation. It may not modify the Baseline Core, feature information,
training objective, ranking, threshold, structural decoder, or prediction set.

## Adaptation Budget

The amendment binds one equal Adaptation Budget to every method. It fixes the
selection metric, maximum trials, compute allowance, stopping rule, seed policy,
and permitted mechanical integration work. Exhausting the budget is a result,
not permission to grant a method extra search.

## Qualification boundary

A method is comparison-qualified only when its current v1.1 profile, exact
Comparison Scope, complete target-free prediction coverage, core-owned target
join, and independent evaluation all agree. A source-native row, a checkpoint,
a matching paper number, or a baseline aggregate cannot create
`comparison_ready`.
