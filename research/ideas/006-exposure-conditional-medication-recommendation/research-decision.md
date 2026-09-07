<!-- markdownlint-disable MD013 -->

# Research Decision — Idea 006: Exposure-Conditional Medication Recommendation

## Verdict

`STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`

- **Idea**: `006-exposure-conditional-medication-recommendation`
- **Gate**: Gate 01 — Exposure-Conditioned Learning vs Direct Exposure Controls
- **Execution commit**: `3e51887a570bf8c4ef9503f7ffb852881c931130`
- **Integrity audit**: `INTEGRITY_AUDIT_PASS`
- **Lifecycle transition**: `ACTIVE -> TERMINATED_AT_GATE_01`
- **R0 Holdout**: quarantined / uninspected
- **Historical project test split**: untouched / uninspected

## Decision question

Gate 01 asked whether end-to-end exposure-conditioned DDI learning creates incremental safety/fidelity value beyond a direct exposure-aware reranker when both receive the same strictly pre-order active-regimen state and the same frozen DDI matrix.

The preregistered strongest null was:

> The active-exposure signal may be useful, but learning is unnecessary; direct inference-time use of the same signal is sufficient.

The null was not rejected.

## Decisive evidence

On the frozen R0 Dev primary universe at `K=5`:

| Method | Recall@5 | IncrementalExposureDDI@5 |
| --- | ---: | ---: |
| Base | 0.510442 | 0.098269 |
| StaticLoss | 0.508464 | 0.097290 |
| DirectExposureRerank | 0.509797 | 0.087302 |
| ExposureHardConstraint | 0.309724 | 0.000000 |
| ExposureConditional | 0.505470 | 0.074756 |

`ExposureConditional` materially reduced the frozen exposure-localized DDI surrogate relative to Base:

- risk delta: `-0.023513`;
- 95% patient-clustered bootstrap CI: `[-0.023961, -0.023062]`;
- Recall@5 delta versus Base: approximately `-0.004972`, within the preregistered fidelity-loss allowance.

However, the primary method-admission condition compared the learned method with `DirectExposureRerank` under equal DDI/active-state entitlement. It failed:

- risk delta, EC minus reranker: `-0.012546`;
- Recall@5 delta, EC minus reranker: approximately `-0.004327`;
- Recall delta 95% CI: `[-0.005315, -0.003362]`.

The protocol required at least `+0.005` Recall@5 over the reranker with the confidence-interval lower bound above zero. The observed effect had the opposite sign.

Condition 4 therefore failed while Conditions 1, 2, 3, and 5 passed.

## What was learned

### 1. R0 resource/semantic evidence remains valid

R0 independently established that hospitalization-level DDI pair co-membership materially overstates execution-confirmed temporal overlap under the frozen operational definition (`static_only_fraction = 21.0521%`). Gate 01 does not invalidate that result.

### 2. Exposure-conditioned training is not equivalent to the tested static DDI loss

All four `StaticLoss` configurations missed the common InnerTune risk budget. `ExposureConditional` reached it at `lambda=2.0` and `lambda=8.0`. The active-exposure term therefore changes the tested optimization behavior relative to conventional new-set DDI regularization.

This is mechanism evidence about the surrogate objective, not evidence that the learned method is scientifically superior.

### 3. New information-state semantics do not automatically imply learned method value

The exposure signal is operationally meaningful and useful for controlling the surrogate, but a direct inference-time control with identical information retained better medication-order fidelity at the frozen Gate-01 comparison.

The project must therefore distinguish:

`new state / new metric semantics`

from

`incremental learned method contribution`.

### 4. The hard-rule extreme is also insufficient

`ExposureHardConstraint` reached zero measured incremental-exposure DDI at the cost of a large Recall@5 collapse (`0.309724`). The result does not support replacing the learned route with an unconditional hard filter.

## Exact closure boundary

Idea 006 is terminated under the following frozen premise:

- provider-order-time medication recommendation;
- strictly pre-order execution-confirmed active regimen;
- 131 ATC-L4 action space;
- frozen SafeDrug/MoleRec DDI matrix;
- common causal order-time backbone;
- fixed-`K` evaluation;
- exposure-conditioned differentiable DDI objective;
- equal-entitlement direct reranking and hard-constraint controls;
- frozen Gate-01 tuning/evaluation protocol.

Do not revive this route by adding:

- a GNN/Transformer risk encoder;
- personalized risk tolerance;
- an LLM agent;
- a larger lambda/gamma grid;
- another DDI database;
- dose/route features;
- labs/vitals;
- subgroup mining;
- a second backbone solely to rescue the same premise.

A future route may reuse the leakage-safe order-time data resource or R0 exposure-state instrumentation only for a materially different scientific question.

## Non-claims

This decision does not establish that:

- exposure-localized DDI semantics are clinically useless;
- direct reranking dominates every possible safety/fidelity frontier;
- static-only DDI pairs are clinically safe;
- DDI overlap is an ADE label;
- all end-to-end safety objectives are inferior to post-hoc controls.

It establishes only that the preregistered Idea-006 end-to-end exposure-conditioned route failed to show the required incremental learned value over its strongest equal-entitlement direct control.

## Next state

Return to `ccf-pipeline-orchestrator` for cross-idea consolidation and a bounded research-space reset outside the Idea-006 safety premise.

No additional Idea-006 experiment is authorized.
