# MHEF normalization-domain screen design — 2026-09-19

Date: 2026-09-19  
Status: **DESIGN_FROZEN_IMPLEMENTED_PENDING_319_EXECUTION**

## Decision

After the final relational architecture search falsified dense non-separable fine-code pair modeling, the next architecture family is narrowed to **Medication-Conditioned Heterogeneous Evidence Factorization (MHEF)**.

This is not a continuation of relational pair modeling and not a generic `Multi-View + concat` implementation.

The scientific hypothesis is:

> The stable medication-specific FineCode reader is still constrained by one cross-modality softmax budget. Diagnosis, procedure, and strictly previous medication evidence may need independent candidate-medication-specific normalization budgets because clinically complementary evidence should not enter zero-sum competition before medication-level prediction.

## Why this is now the Rank-1 hypothesis

Positive project evidence repeatedly favors preserving decision-relevant granularity until medication identity has selected evidence:

- DrugQuery established medication-specific evidence selection;
- FineCode produced the strongest stable project-owned mechanism signal;
- PredictionLocal provided a strong but DDI-costly clue that later aggregation can also erase useful local evidence;
- `summary_add` became the best completed recent architecture and is linearly capable of preserving separate D/P/H summaries.

Negative evidence lowers prior on alternative explanations:

- patient-conditioned query generation failed;
- medication-conditioned temporal recurrence had negligible value;
- iterative rereading was unstable;
- multiplicative summary relations failed against additive composition;
- dense non-separable fine-code pair relations failed and were expensive;
- output-side set/cardinality/pairwise repair repeatedly failed to create meaningful identity-selection gains.

The remaining confound in `summary_add` is whether its gain comes from heterogeneous normalization or merely extra width/projections/head capacity. The new screen isolates that question directly.

## Decisive causal control

`mhef_independent_add` and `coupled_budget_add` share:

- raw evidence;
- medication embeddings and medication-query function;
- token keys and values;
- global FineCode path;
- D/P/H downstream slots;
- final evidence scorer;
- parameter count and initialization.

The scientific difference is only:

```text
IndependentBudget:
softmax separately inside D, P, H

CoupledBudget:
one softmax across D ∪ P ∪ H, then split the weighted sum by field
```

A positive result therefore attributes value to removal of cross-modality zero-sum normalization rather than to a larger network.

## Execution package

Implementation is frozen under:

`research/prototypes/mhef-normalization-screen/`

Eight lanes test:

1. main normalization mechanism;
2. matched wide-global capacity absorption;
3. normalization under an alternate concat fusion head;
4. complementarity of the stable global FineCode path;
5. two deterministic cardinality-matched nonsemantic partitions to test whether D/P/H semantics matter.

No HPO, dynamic query, relation rescue, extra hop, DDI reranker, or output correction is part of the screen.

## Decision rule

Primary comparison:

`mhef_independent_add - coupled_budget_add`

Use the frozen project mechanism thresholds. Multi-seed stability is not authorized automatically; aggregate results must first show a clean main mechanism, survive capacity/fusion/semantic-partition controls, and produce a complete architecture at least as strong as the prior completed best architecture.

Test remains sealed.
