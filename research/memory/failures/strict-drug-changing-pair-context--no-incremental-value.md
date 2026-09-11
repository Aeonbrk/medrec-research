<!-- markdownlint-disable MD013 -->

# Failure Memory — Strict Drug-Changing Pair/Context Incremental Value

## Failure class

`NO_INCREMENTAL_PAIR_CONTEXT_VALUE`

## Source

- Stage: `PRE_IDEA_PAIR_CONTEXT_INCREMENTAL_VALUE`
- Protocol: `research/memory/model-reset-20260910-strict-drug-changing-order-revision/pair-context-incremental-value-protocol.md`
- Execution revision: `4a71ab0f2c6cacafb58dbe8fe6ba2094f17de4f5`
- Semantic admission: `PASS_SEMANTIC_ADMISSION` (`1,040` strict events)
- Supportability: `PASS_STRICT_DRUG_CHANGING_SUPPORTABILITY`
- Verdict: `ABANDON_NO_INCREMENTAL_PAIR_CONTEXT_VALUE`

## Tested premise

The already admitted strict drug-changing order-revision trace might carry
context-dependent, cross-patient information about the downstream medication
beyond ordinary flattened final-prescription supervision and source/destination
frequency structure.

## Frozen test boundary

The run used the admitted directional trace
`x_pre -> m- -> DeltaI -> D/C(m-) -> m+`, the causal Idea-006 order-time context,
the frozen R0 Discovery/Dev subject partition, seven fixed variants, and the
predeclared patient-cluster bootstrap and gate rules. No pair filtering,
subgroup selection, semantic rescue, or threshold change was permitted.

## Result

The semantic identity re-materialized exactly: `1,040` strict events and zero
frozen invariant violations. Discovery contained `855` events from `835`
patients; Dev contained `185` events from `176` patients. The public-safe result
package is:

- `../model-reset-20260910-strict-drug-changing-order-revision/pair-context-incremental-value-summary.json`
- `../model-reset-20260910-strict-drug-changing-order-revision/pair-context-incremental-value-decision.md`

All five preregistered comparisons failed the required relative-gain, bootstrap
lower-bound, and per-seed lower-NLL conditions. PairContext mean Dev NLL was
`5.40227365494`; relative gains versus DestinationMarginal, SourceTransitionPrior,
FlatFinalPlusSourcePrior, TraceContextOnly, and PermutedPairContext were
`-0.406497028282`, `-0.194091863073`, `-0.0255983621403`,
`-0.335218493243`, and `0.0225693404964`, respectively.

## Scientific conclusion

> Under the frozen strict drug-changing trace and Pair/Context protocol, the
> observed supervision did not demonstrate context-dependent incremental value
> beyond the fixed controls. The candidate is terminated before any Idea or
> Gate-01 method claim.

This is a bounded failure of the tested incremental-value premise. It is not a
claim about clinical correctness, treatment effect, therapeutic substitution,
physiology, or the usefulness of every future workflow-revision object.

## Non-revival boundary

Do not rescue this candidate by changing strict-trace semantics, adding features
or tables, changing mappings, widening windows, filtering patients or
medications, mining pairs or subgroups, changing controls or thresholds, or
trying another architecture. A future route would require a materially
different falsifiable scientific object and a fresh design/review.

## Quarantine and routing

G3/G4, R0 Holdout, and the historical project test split remained quarantined.
No Idea 008 was created, no Gate 01 was entered, and no model work outside the
bounded frozen pre-Idea probes was authorized. Ownership returns to
`ccf-pipeline-orchestrator` for the next pre-Idea routing decision.
