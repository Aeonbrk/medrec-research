<!-- markdownlint-disable MD013 -->

# Early-Stage Research Ideas

This directory is the fundamental organizational unit for exploratory, early-stage medication recommendation research.

## Purpose

Each idea folder represents a single, focused scientific line of inquiry before it graduates to a paper project or is terminated. Ideas are managed to minimize the marginal cost of proposing and testing hypotheses.

## Invariants for Each Idea

Every idea folder (e.g. `001-tension-guided-verification/`) must be able to clearly answer:

1. **Core Hypothesis**: What specific causal mechanism or behavior is being proposed?
2. **Key Uncertainty**: What is the most likely reason this hypothesis could be false or trivial?
3. **Next Minimal Experiment**: What is the cheapest, most decisive test that could falsify or confirm the hypothesis?
4. **Existing Evidence**: What empirical observations or diagnostics currently support or constrain this idea?
5. **Current Verdict**: What is the current scientific status (`active`, `revised`, `killed`, `graduated`)?

## Lifecycle & Code Promotion

- **Idea-Stage Code**: Prototype scripts, data probes, and temporary diagnostic logic stay inside the idea's directory or local scratch space. They must **not** be placed in `src/medrec_research/` prematurely.
- **Promotion to Core**: Only when a capability survives falsification and is reused across multiple experiments or ideas is it promoted to `src/medrec_research/` (`idea-local prototype → reusable research capability → src/`).
- **Failures**: Idea-specific failures remain in the idea's local experimental history. Only generalizable negative patterns (e.g. baseline traps, pseudo-gains from scalar reranking) are distilled into `research/memory/`.
- **Graduation**: When an idea survives all minimal falsification gates and has sufficient multi-backbone evidence, it graduates to a dedicated paper project in `papers/<paper-name>/`.

## Active Ideas Index

| ID | Title | Status | Core Uncertainty | Next Minimal Experiment |
| :--- | :--- | :--- | :--- | :--- |
| [`001-tension-guided-verification`](001-tension-guided-verification/README.md) | Tension-Guided Verification | **Active** | Can decision tension outperform simple predictive uncertainty or global scalar reranking under strict count matching? | S-1 timestamp semantics audit & S0 transition decomposition |
