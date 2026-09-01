<!-- markdownlint-disable MD013 -->

# Failure Record: EGSF selector

Source boundary: `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. Every archive path in this record refers to that revision.

## Decision

The EGSF context-conditioned selector route is failed historical memory. The archive does not support a method claim that patient or context buckets require different DDI trade-off parameters.

## What was tested

The route used a frozen trained backbone and a calibrated candidate frontier, then compared bucket/context and exact-count selectors with threshold/top-k, oracle-frontier, post-hoc, count-shrinkage, random-replacement, and global fixed-lambda controls. The decisive follow-up expanded the global control and tightened utility and medication-count gates. Archive evidence: `research-wiki/experiments/egsf_e3b_strong_followup.md`.

## Why it failed

The earlier positive result depended on an under-expanded fixed-lambda control. In the strong follow-up, the best eligible global control selected `lambda=30.0`; the bucket/context selector had LambdaGap `-0.00545` with bootstrap 95% CI `[-0.00588, -0.00499]`, and the exact-count selector had LambdaGap `-0.00454` with bootstrap 95% CI `[-0.00493, -0.00412]`. Archive evidence: `research-wiki/experiments/egsf_e3b_strong_followup.md` at commit `9971464253c556345262b22ed6d44b2cc14c9da8`.

The exact-count selector also lost, so medication-count shrinkage alone does not explain the failure. No predeclared subgroup supported the selector. The causal interpretation is that a strong global scalar DDI penalty explained the archived selector gain under the calibrated utility and count constraints. Archive evidence: `research-wiki/claims/egsf_not_fixed_lambda.md` and `refine-logs/E3B_STRONG_ANALYSIS.md`.

## Reusable residue

- A control stack that includes expanded global fixed-lambda search, calibrated utility, strict and exact count matching, subgroup LambdaGap, and bootstrap intervals.
- A negative case for testing whether a safety result survives simple scalar reranking.
- Candidate-frontier and aggregate evaluation machinery, provided it is treated as diagnostic infrastructure rather than method evidence.

## Non-revival boundary

Do not revive this route by adding another scalar DDI selector, a richer bucket encoder, an LLM agent, backbone retraining, or dataset transfer. A new selector route first has to beat the best tuned global scalar control under predeclared utility, count, and subgroup gates. Archive evidence: `idea-stage/EGSF_PIVOT_IDEA_DISCOVERY.md`.

## Uncertainty

The failure is scoped to the archived backbone, candidate construction, proxy-risk definition, and evaluation contract. It does not prove that every context-conditioned selector must fail. It does show that this route lacks evidence for its claimed mechanism and cannot be promoted from the archived results.
