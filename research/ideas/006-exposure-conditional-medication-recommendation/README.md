<!-- markdownlint-disable MD013 -->

# Idea 006: Exposure-Conditional Medication Recommendation

- **Idea ID**: `006-exposure-conditional-medication-recommendation`
- **Status**: `TERMINATED_AT_GATE_01`
- **Formal verdict**: `STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`
- **Scientific stage**: Idea / hypothesis selection — completed and falsified
- **Target venue assumption**: first formal method paper, CCF-A Data/Mining/AI venue family
- **R0 resource gate**: `PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE`
- **R0 execution commit**: `ea134b7e75583186242bc72bc71eb2975b812edc`
- **Gate 01 execution commit**: `3e51887a570bf8c4ef9503f7ffb852881c931130`
- **Final closest-work verdict**: `NOVELTY_DELTA_SURVIVES_FOR_IDEA_CREATION`
- **Strict idea review**: [`idea-review.md`](idea-review.md) (`ACCEPT_TO_DEVELOP / SELECT_FOR_GATE_01_ONLY`, `4.30/5`)
- **Gate 01 protocol**: [`experiments/gate-01-exposure-conditioned-learning.md`](experiments/gate-01-exposure-conditioned-learning.md)
- **Gate 01 design audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md) (`DESIGN_INTEGRITY_PASS`)
- **Gate 01 summary**: [`experiments/gate-01-summary.json`](experiments/gate-01-summary.json)
- **Gate 01 decision**: [`experiments/gate-01-decision.md`](experiments/gate-01-decision.md)
- **Gate 01 integrity audit**: [`experiments/gate-01-integrity-audit.md`](experiments/gate-01-integrity-audit.md) (`INTEGRITY_AUDIT_PASS`)
- **Formal research decision**: [`research-decision.md`](research-decision.md)
- **Cross-idea failure memory**: [`../../memory/failures/exposure-conditioned-learning-gate-01--direct-control-sufficiency.md`](../../memory/failures/exposure-conditioned-learning-gate-01--direct-control-sufficiency.md)
- **R0 Holdout**: quarantined and uninspected
- **Historical project test split**: untouched and uninspected

## Scientific question

At an inpatient provider medication-order decision point, can end-to-end DDI learning conditioned on a strictly pre-order, execution-confirmed active regimen create a reproducible safety/fidelity advantage beyond direct exposure-aware use of the same active-regimen DDI signal?

The strongest null was:

> The dynamic exposure signal is useful, but learning is unnecessary; a direct exposure-aware reranker receiving the same active state and DDI matrix is sufficient.

Gate 01 did not reject this null.

## Empirical premise that survived

R0 remains a valid project-local result.

On raw MIMIC-IV 3.1 Discovery:

- order normalization coverage exceeded 81%;
- administration normalization coverage exceeded 81%;
- the action vocabulary contained 131 ATC-L4 concepts, with 91 represented in the frozen DDI asset;
- 1,050,523 eMAR-observed visit-union DDI episodes were identified;
- 221,157 were `static-only` under the frozen retrospective operational definition;
- `static_only_fraction = 21.0521%`;
- 280 DDI relations independently exceeded the distributed-support floor;
- a strictly pre-order execution-confirmed active medication state was feasible.

Therefore hospitalization-level DDI pair co-membership is not equivalent to current execution-confirmed temporal exposure under the frozen resource definition.

This is a state-semantics result, not proof of clinical safety or method value.

## Gate 01 result

Primary Dev evaluation used fixed `K=5`, `Recall@5` as the primary fidelity metric, and `IncrementalExposureDDI@5` as the primary operational safety surrogate.

| Method | Recall@5 | IncrementalExposureDDI@5 |
| --- | ---: | ---: |
| Base | 0.510442 | 0.098269 |
| StaticLoss | 0.508464 | 0.097290 |
| DirectExposureRerank | 0.509797 | 0.087302 |
| ExposureHardConstraint | 0.309724 | 0.000000 |
| ExposureConditional | 0.505470 | 0.074756 |

`ExposureConditional` reduced the surrogate substantially versus Base:

- risk delta: `-0.023513`;
- 95% patient-clustered bootstrap CI: `[-0.023961, -0.023062]`;
- Recall@5 delta versus Base: approximately `-0.004972`.

However, the preregistered primary killer comparison failed.

EC versus DirectExposureRerank:

- risk delta: `-0.012546`;
- Recall@5 delta: approximately `-0.004327`;
- Recall delta 95% CI: `[-0.005315, -0.003362]`.

The protocol required at least `+0.005` Recall@5 over the direct reranker at near-equal-or-better risk, with CI lower bound above zero. The observed fidelity effect had the opposite sign.

Conditions 1, 2, 3, and 5 passed. Condition 4 failed. The all-conditions Gate therefore returned:

`STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`.

## Mechanistic interpretation

Two findings must be kept separate.

### Exposure semantics were nontrivial

The conventional `StaticLoss` grid failed to reach the common InnerTune safety budget, while `ExposureConditional` reached it. The active-exposure term therefore changed optimization behavior relative to the tested static new-set DDI regularizer.

### Learned method value was absent at the frozen Gate

The same exposure-risk information could be used directly at inference time while retaining higher medication-order fidelity at the selected operating point. The project therefore cannot promote the valid R0 semantic mismatch into a learned-method contribution.

This is the decisive scientific lesson of Idea 006.

## Exact closure boundary

The terminated route consists of:

- provider-order-time medication recommendation;
- strictly pre-order execution-confirmed active regimen;
- frozen 131 ATC-L4 action space;
- frozen SafeDrug/MoleRec binary DDI matrix;
- common causal order-time backbone;
- exposure-conditioned differentiable DDI loss;
- fixed-cardinality evaluation;
- equal-entitlement direct reranking/hard-constraint controls;
- the frozen Gate-01 selection and decision protocol.

Do not rescue this route by adding a deeper risk encoder, another backbone, wider parameter search, personalized DDI weighting, LLM verification, new DDI knowledge, dose/route, labs/vitals, or subgroup mining while retaining the same central premise.

## What remains reusable

The following may be reused by future, materially different Ideas:

- raw MIMIC-IV order/eMAR normalization and linkage;
- leakage-safe provider-order-time burst construction;
- causal pre-order active-regimen instrumentation;
- R0 exposure-state evidence;
- fixed-cardinality operational exposure-DDI metrics;
- equal-entitlement direct-control methodology.

Reusing infrastructure is allowed. Reusing the failed scientific claim is not.

## Non-claims

Idea 006 does not establish that:

- administration timing is clinically irrelevant;
- exposure-localized DDI semantics are useless;
- direct reranking dominates every possible frontier;
- static-only DDI pairs are safe;
- DDI overlap predicts ADEs;
- every end-to-end safety method is inferior to post-hoc control.

It establishes only that the preregistered Idea-006 learned route did not demonstrate the required incremental value beyond its strongest equal-entitlement direct control.

## Next research state

Idea 006 is closed.

Next owner: `ccf-pipeline-orchestrator` for cross-idea consolidation and a bounded research-space reset outside the current exposure-safety method family.

No Idea-006 Gate 02 or rescue experiment is authorized.
