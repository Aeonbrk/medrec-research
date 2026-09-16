# Paper-facing experiment governance replaces active mode semantics

## Context / Trigger

The repository previously used Reproduction Mode, Comparison Mode, Unified Research Protocol v1.0/v1.1, and opaque Stage/Gate names as active experiment-governance concepts. The competitive baseline fidelity review showed that those abstractions could obscure the more important distinction between preserving a published method's scientific identity and mechanically copying every upstream execution detail. Independent review also identified unresolved degrees of freedom around evaluation feedback history, joint checkpoint/threshold selection, seed handling, and final evidence qualification.

## Decision

New paper-facing experiments use one current `Paper Experiment Contract` plus one core evaluator specification and one concise per-method Method Card.

Historical Reproduction/Comparison records, baseline registry entries, Stage labels, Gate records, and earlier protocol documents remain valid provenance for what they actually executed. They do not automatically certify new paper rows and are not rewritten to look as though they were created under the new contract.

Human-facing research phases are now descriptive:

1. Credible Reference Setup
2. Architecture Hypothesis Testing
3. Paper Candidate Freeze
4. Final Confirmation

Final-table eligibility and independent confirmation are separate properties. A historically feedback-exposed benchmark may be reported transparently but cannot be relabeled as untouched confirmation by refreezing a later model.

## Rejected Alternatives

- Keep Reproduction Mode and Comparison Mode as two active scientific worlds: rejected because they encourage semantic exceptions and can hide whether a change is method-preserving or scientifically material.
- Require exact upstream execution for every paper baseline: rejected because benchmark-specific validation and bounded tuning can be legitimate without changing the scientific method.
- Allow unconstrained benchmark adaptation: rejected because optimization granularity, information flow, core objective, or decoder changes can materially change the method.
- Block all training until every benchmark/baseline audit finishes: rejected because unrelated audits should not become global research bureaucracy.

## Consequences / Invariants

- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md` is the active paper-facing governance source.
- `docs/specs/PAPER_EVALUATOR_SPEC.md` owns current metric/aggregation semantics.
- `docs/guides/PAPER_METHOD_CARD_TEMPLATE.md` defines the minimum current identity/adaptation record for a method about to enter paper-facing comparison.
- `docs/specs/UNIFIED_RESEARCH_PROTOCOL*.md` are historical and must not create new Comparison Mode qualifications.
- `baselines/registry.toml` keeps historical integration/readiness provenance; its mode/readiness fields do not automatically confer paper eligibility.
- Evaluation surfaces carry feedback-history status; final-table eligibility is not synonymous with independent confirmation.
- Checkpoint and operating-point selection are one frozen Dev procedure.
- Seed sets and failure handling are fixed before final training for each method.
- Experiment prerequisites are scoped to what can change that experiment's interpretation or execution.
