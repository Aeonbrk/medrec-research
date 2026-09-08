<!-- markdownlint-disable MD013 -->

# Pre-Idea Constraint — Privileged Response Specificity Requires Matched Subtraction

## Status

`REUSABLE_PRE_IDEA_CONSTRAINT / SATISFIED_FOR_IDEA_007_ADMISSION / NOT_AN_EMPIRICAL_FAILURE`

Source admission review:

`research/memory/model-reset-20260908-privileged-physiological-response/idea-review.md`

Current reviewer verdict:

`ACCEPT_TO_CREATE_IDEA_007`

This record does not terminate the privileged physiological response family. It preserves the mechanism-identification rule that was required before the family could become an Idea. The bounded R1--R3 optimizer revision now satisfies this admission condition prospectively; whether the mechanism survives remains a future Gate-01 empirical question.

## Constraint

A future-only clinical signal can be a legal predictive training target while still failing to support the scientific mechanism attributed to it.

For privileged physiological response supervision, recommendation gains are not evidence of medication-specific response learning unless the design separates at least four alternative explanations:

1. generic future-state supervision;
2. focal medication identity or static medication prototypes;
3. monitoring availability/frequency and missingness policy;
4. sample-selection or positive-event reweighting caused by response supervision existing only on linked administered events.

The durable rule is:

> **Privileged future information is method evidence only when the claimed semantics survive matched controls that remove the semantic component while preserving future access, support, capacity, optimization entitlement, and deployment inputs as closely as possible.**

## Admission conditions now frozen

The current packet freezes:

- a medication-ablated future / generic future-state control with matched future window, support, student, and comparable capacity/optimization entitlement;
- a monitoring-mask-only control and explicit physiological-value versus response-availability separation;
- positive-only administered-event response semantics and identical support/sample entitlement across privileged variants;
- a strictly pre-order student feature and normalization contract;
- response-shuffle and static-prototype controls for individualized pairing and static medication identity explanations.

This is sufficient for Idea creation because it converts the prior blocker into a prospective kill-first test rather than assuming the mechanism.

## Future kill boundary

If a later Gate finds that generic future, medication-ablated future, response shuffle, monitoring mask, static prototypes, or richer pre-order physiology explains the gain, terminate the response-specific mechanism rather than scale architecture.

Deployment leakage or unmatched support/reweighting invalidates the Gate.

Do not rescue those outcomes with a larger teacher, another backbone, a different response window, extra modalities, subgroup mining, or repeated response-definition search under the same Idea.

## Claim boundary

Observed post-administration physiology remains observational and confounded. It may support a predictive response-associated representation under the historical care policy, but it does not identify:

- treatment effect;
- causal response;
- drug efficacy;
- therapeutic benefit;
- counterfactual outcome;
- clinically optimal medication;
- individualized causal benefit.

## Routing

Next owner:

`ccf-pipeline-orchestrator`.

Authorized next workflow:

```text
ccf-pipeline-orchestrator
-> create/admit Idea 007
-> ccf-experiment-designer
-> Gate 01 design-integrity audit
-> push
-> stop before training
```

This constraint record does not itself authorize local response-coverage inspection, Gate execution, or training.
