<!-- markdownlint-disable MD013 -->

# Failure Memory — Exposure-Conditioned Learning Gate 01: Direct-Control Sufficiency

## Failure class

`NEW_STATE_SEMANTICS_WITHOUT_INCREMENTAL_LEARNED_VALUE`

## Source

- Idea: `006-exposure-conditional-medication-recommendation`
- Gate: Gate 01 — Exposure-Conditioned Learning vs Direct Exposure Controls
- Gate verdict: `STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`
- Execution commit: `3e51887a570bf8c4ef9503f7ffb852881c931130`
- Integrity audit: `INTEGRITY_AUDIT_PASS`

## Reusable lesson

A new decision-state or risk-state semantic can be empirically real and still fail to justify an end-to-end learned method.

In Idea 006, R0 independently established that hospitalization-level DDI pair co-membership and execution-confirmed current exposure are materially different. The learned `ExposureConditional` objective also reached a risk level that the conventional `StaticLoss` grid could not reach.

However, once the exact same active-regimen state and DDI matrix were given to a direct inference-time reranker, the learned method did not provide incremental medication-order fidelity at the frozen Gate operating point.

The project-level constraint is:

> **Novel information/state semantics must survive direct-use controls before they can support a learned-method claim.**

This extends the earlier EG-TER rule-entitlement lesson from hard feasibility rules to dynamic operational state signals.

## Decisive numbers

R0 Dev, `K=5` primary universe:

- Base: Recall@5 `0.510442`, IncrementalExposureDDI@5 `0.098269`.
- DirectExposureRerank: Recall@5 `0.509797`, risk `0.087302`.
- ExposureConditional: Recall@5 `0.505470`, risk `0.074756`.

EC vs direct reranker:

- risk delta: `-0.012546`, 95% CI `[-0.012891, -0.012204]`;
- Recall@5 delta: approximately `-0.004327`, 95% CI `[-0.005315, -0.003362]`.

The preregistered method-admission condition required `+0.005` Recall@5 over the direct reranker at near-equal-or-better risk, with CI lower bound above zero. The observed fidelity effect was significantly negative.

## What remains reusable

The following are still valid reusable assets/evidence:

- the R0 order/eMAR linkage and 131-concept normalization pipeline;
- the leakage-safe provider-order-time task construction;
- the causal pre-order active-regimen construction;
- the project-local finding that `21.0521%` of the frozen eMAR-observed visit-union DDI episodes were static-only;
- fixed-cardinality exposure-localized DDI metrics;
- equal-entitlement direct-control methodology.

These may be reused for a genuinely different research question. They do not authorize a safety-loss rescue.

## Closed resurrection patterns

Do not respond to this failure by:

- making the exposure DDI loss nonlinear or deeper;
- replacing the risk term with a GNN/attention/Transformer over the same active state and DDI matrix;
- learning a personalized scalar risk tolerance without a new identifiable target;
- broadening hyperparameter grids after the result;
- adding dose/route/labs merely to recover Gate-01 performance;
- using a second backbone to search for a favorable exception;
- withholding the active-exposure signal from direct controls.

All of these preserve the same scientific premise while weakening the falsification value of Gate 01.

## Reopen condition

A related safety route is eligible for reconsideration only if it changes at least one scientific primitive that matters to the claim, such as:

- a different independently grounded safety target rather than the same pairwise DDI surrogate;
- a different action/decision problem where direct inference-time rule use is not sufficient by construction;
- new outcome evidence that identifies patient-specific risk beyond the frozen DDI relation;
- a method question not reducible to applying the same known risk signal directly.

`CLOSED` does not mean every use of administration timing or active medications is prohibited.
