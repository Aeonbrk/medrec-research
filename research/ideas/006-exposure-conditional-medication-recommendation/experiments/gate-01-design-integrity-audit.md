<!-- markdownlint-disable MD013 -->

# Gate 01 Design Integrity Audit — Idea 006

## Audit status

- **Audit owner**: `ccf-integrity-auditor`
- **Audit mode**: pre-execution claim/evidence/design consistency
- **Protocol**: [`gate-01-exposure-conditioned-learning.md`](gate-01-exposure-conditioned-learning.md)
- **Idea**: [`../README.md`](../README.md)
- **R0 evidence**: `PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE`
- **Verdict**: `DESIGN_INTEGRITY_PASS`

No Gate-01 result exists at audit time. This audit checks whether the frozen design can answer the stated Idea-006 question without structural leakage, control asymmetry, cardinality confounding, or post-result adaptivity.

## Claim-evidence matrix

| Intended claim / decision | Required evidence in protocol | Audit status |
| --- | --- | --- |
| Exposure-conditioned learning changes the intended safety surrogate | `ExposureConditional` vs `Base` at fixed K on `IncrementalExposureDDI@5` | `SUPPORTED_BY_DESIGN` |
| Effect is not ordinary static set-level DDI regularization | same backbone `ExposureConditional` vs `StaticLoss` | `SUPPORTED_BY_DESIGN` |
| Learned value exceeds direct rule use | `ExposureConditional` vs InnerTune-selected `DirectExposureRerank` with identical active-state/DDI entitlement | `SUPPORTED_BY_DESIGN / PRIMARY KILLER` |
| Hard constraint is not already sufficient | deterministic `ExposureHardConstraint` with same Base logits, active state, and DDI matrix | `SUPPORTED_BY_DESIGN` |
| Safety result is not caused by shrinking the recommendation set | every primary method emits exactly `K=5` | `SUPPORTED_BY_DESIGN` |
| Final gate is not tuned on outer evaluation | all checkpoints/hyperparameters/budget frozen on InnerTune before R0 Dev access | `SUPPORTED_BY_DESIGN` |
| Uncertainty respects repeated bursts within a patient | paired patient-clustered bootstrap | `SUPPORTED_BY_DESIGN` |

## 1. Temporal leakage audit

### Target boundary

`PASS`.

The decision time is the first unassigned positive medication-order event in each non-overlapping 10-minute burst. The target consists of positive medication-order concepts in `[t, t+10 min)`, while all model inputs must be strictly `< t`.

Events at exactly `t` are therefore correctly treated as action/target events, not features.

### Active-state boundary

`PASS`.

The online state requires:

- provider order before `t`;
- linked eMAR administration before `t`;
- no pre-`t` D/C transaction for that order.

The protocol explicitly forbids:

- future administrations;
- `discontinued_by_poe_id` as a future pointer;
- final order status for historical reconstruction;
- current-visit discharge-coded diagnosis/procedure information;
- post-`t` D/C events.

D/C transactions use `discontinue_of_poe_id` only when the D/C event itself occurred before `t`, which is causal at the decision point.

## 2. Partition and adaptivity audit

`PASS`.

- R0 Discovery is repartitioned by a second subject-only deterministic hash into InnerTrain and InnerTune.
- R0 Dev was unused by R0 and is reserved for one frozen Gate-01 outer evaluation.
- R0 Holdout remains uninspected.
- the historical project test split remains untouched.

The protocol prohibits Dev-derived checkpoint, lambda, gamma, K, risk-budget, metric, subgroup, or task-construction decisions.

This is a strong hypothesis-selection hierarchy and materially cleaner than the repeatedly adaptive historical validation route.

## 3. Equal-entitlement audit

`PASS`.

The central EG-TER failure lesson is respected.

`ExposureConditional`, `DirectExposureRerank`, and `ExposureHardConstraint` receive the same:

- active regimen `A_t`;
- frozen DDI matrix `D`;
- 131-medication action universe.

The learned method receives no clinical rule, DDI relation, or active-state variable that the direct controls are denied.

The Base/Static/ExposureConditional learned variants also share the exact backbone and non-DDI inputs, so architecture capacity cannot explain a Gate-01 method gain.

## 4. Cardinality-confounding audit

`PASS`.

B0 showed that medication cardinality must not be conflated with normalized DDI propensity.

Gate 01 fixes primary output size to exactly `K=5` for every method. `K=10` is secondary and cannot trigger retuning.

The primary safety metric is pair-opportunity normalized rather than absolute DDI-pair count:

`IncrementalExposureDDI@5`.

Therefore a method cannot pass by simply recommending fewer medications.

## 5. Primary-universe audit

`PASS`.

The primary DDI-opportunity universe is defined from `A_t`, `V`, and `D` only:

$$
|A_t|>0\ \land\ \exists m\in V, a\in A_t:D_{ma}=1.
$$

It does not depend on the true target burst or any model prediction. This prevents target-conditioned or Base-conditioned opportunity selection.

All eligible bursts are still retained for secondary prediction reporting.

## 6. Method-control alignment audit

`PASS`.

The protocol tests the exact strongest scientific objection:

> The active-exposure DDI signal may be useful, but learning may be unnecessary.

The direct reranker uses frozen Base logits and greedily penalizes incremental DDI risk against both the active regimen and already selected recommendations. It receives a wider seven-value Tune grid than the four-value learned lambda grids, so the method is not advantaged by a weaker parameter search.

The hard constraint provides a second deterministic direct-use baseline.

The conventional `StaticLoss` control tests whether any benefit comes from ordinary predicted-set DDI regularization rather than exposure-conditioned applicability.

## 7. Selection-budget audit

`PASS`.

The common Tune safety budget is constructed exactly once from Base:

$$
B=0.90R_{Base}^{Tune}.
$$

All risk-aware methods are selected against that same budget. The budget is not redefined per method and cannot be changed after Dev is inspected.

If the candidate method cannot reach the budget on InnerTune, Condition 1 fails automatically.

## 8. PASS-rule audit

`PASS`.

The all-conditions rule prevents a method from advancing on a single favorable axis.

A PASS requires simultaneously:

1. Tune-budget feasibility;
2. at least 10% Dev primary-risk reduction versus Base plus a strictly negative bootstrap interval for the risk delta;
3. at most 0.010 absolute Recall@5 loss versus Base;
4. at least +0.005 Recall@5 over the direct reranker at near-equal-or-better risk, with bootstrap CI lower bound above zero;
5. no point-estimate weak dominance by StaticLoss or the hard constraint.

Condition 4 is appropriately the primary method-admission condition.

## 9. Statistical-evidence audit

`PASS_WITH_SCOPE_BOUNDARY`.

The paired patient-clustered bootstrap correctly handles within-patient dependence across repeated order bursts for route-selection uncertainty.

However, Gate 01 freezes **one training seed** (`260907`). The bootstrap therefore quantifies patient/sample uncertainty, not training stochasticity.

This is acceptable because Gate 01 is a bounded hypothesis-selection gate, not final publication claim support.

Mandatory downstream boundary if Gate 01 passes:

- do not present Gate 01 as multi-seed final evidence;
- later claim-support design must include training-seed robustness and at least one materially different causal predictor family before consuming quarantined final evidence.

## 10. Clinical-claim audit

`PASS`.

The protocol consistently treats:

- eMAR as administration/execution evidence, not treatment appropriateness;
- DDI overlap as an operational exposure surrogate, not an ADE;
- `IncrementalExposureDDI` as a safety surrogate, not patient harm;
- observed order bursts as prescribing-fidelity targets, not optimal therapy.

The design therefore does not repeat Idea 005's semantic overreach.

## 11. Architecture/search-scope audit

`PASS`.

The one-layer GRU is intentionally non-novel and frozen. Gate 01 prohibits architecture search, extra clinical modalities, alternative DDI databases, and rescue modules.

The common learned backbone dimensions are internally consistent:

- GRU final state: 128;
- active-regimen vector: 131;
- log-hours-since-admission: 1;
- concatenated MLP input: 260.

The batch-size fallback is operational only; the actual batch must be frozen for all learned variants before the first full training run.

## Non-blocking limitations

These do not invalidate Gate 01 but constrain interpretation:

1. The online active state is an operational active-order/execution state rather than a pharmacokinetic concentration estimate.
2. `Change` orders may include treatment modifications whose medication concept was already active; this is part of the frozen observed-order prediction task and applies equally to all methods.
3. One training seed is insufficient for final paper evidence.
4. A Gate-01 PASS establishes one-backbone mechanism evidence only; it does not establish broad generalization.

## Verdict

`DESIGN_INTEGRITY_PASS`

The protocol is sufficiently strict to answer the Idea-006 admission question without an obvious control, leakage, cardinality, or adaptivity loophole.

No protocol expansion is recommended before execution.

## Next CCFA owner

Local repository Agent executes Gate 01 exactly as frozen, then runs `ccf-integrity-auditor` on the resulting public-safe summary/decision artifacts.
