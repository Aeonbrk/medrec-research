<!-- markdownlint-disable MD013 -->

# Cross-Idea Research Memory

This directory stores curated, cross-idea reusable knowledge, negative lessons, and research-space admission evidence. It is not a dumping ground for idea-local scratchpads.

## Boundaries & admission policy

Knowledge belongs here only if it has decoupled from one Idea and changes the design, controls, evaluation, or admission of future research.

- Idea-specific hypotheses/results stay in `research/ideas/<idea>/`.
- Baseline reproduction evidence stays in `research/baselines/`.
- Cross-idea constraints, decisive failures, and resource-reset evidence live here.

## Current state

Authoritative project stage:

`IDEA_006_GATE_01`

Active Idea:

[`../ideas/006-exposure-conditional-medication-recommendation/README.md`](../ideas/006-exposure-conditional-medication-recommendation/README.md).

R0 has passed; Idea 006 has been created and strictly admitted for **Gate 01 only**. R0 Holdout and the existing project test split remain untouched and unauthorized.

## Navigation

- **[`research-space-reorientation.md`](research-space-reorientation.md)**: current cross-idea SSOT, failure landscape, reusable constraints, R0 admission result, and active Idea-006 boundary.
- **[`literature-opportunity-map.md`](literature-opportunity-map.md)**: current literature-space judgment after R0 PASS and final closest-work subtraction.
- **[`resource-reset-20260905-exposure-localized-safety/`](resource-reset-20260905-exposure-localized-safety/)**: resource-reset packet containing search notes, paper ledger, pre-Idea review, frozen R0 protocol/results, and final closest-work check.
- **[`literature-search-20260905-prescription-supervision-reset/`](literature-search-20260905-prescription-supervision-reset/)**: rejected supervision-semantics reset; preserves the latent-target/PU identifiability boundary.
- **[`reusable-lessons.md`](reusable-lessons.md)**: authoritative methodological guardrails.
- **`failures/`**: decisive negative cases whose mechanisms constrain future work:
  - [`cardinality-attribution-b0--no-material-count-safety-tradeoff.md`](failures/cardinality-attribution-b0--no-material-count-safety-tradeoff.md): cardinality changed absolute DDI burden but not normalized DDI propensity.
  - [`safety-substitution-structure-semantic-admission--atc-structure-not-therapeutically-admissible.md`](failures/safety-substitution-structure-semantic-admission--atc-structure-not-therapeutically-admissible.md): predictive ATC structure failed therapeutic semantic admission.
  - [`co-selection-compatibility-gate-01--no-incremental-co-selection-compatibility.md`](failures/co-selection-compatibility-gate-01--no-incremental-co-selection-compatibility.md): static train-only co-selection compatibility added no robust routing signal.
  - [`prescription-relative-confidence-gate-01--no-incremental-relative-confidence.md`](failures/prescription-relative-confidence-gate-01--no-incremental-relative-confidence.md): relative-confidence/rank features failed after strong controls.
  - [`score-geometry-gate-01--no-incremental-score-geometry.md`](failures/score-geometry-gate-01--no-incremental-score-geometry.md): order-equivalent score geometry supplied no new routing information.
  - [`tension-gate-02--recommender-confidence-sufficiency.md`](failures/tension-gate-02--recommender-confidence-sufficiency.md): no incremental Tension signal beyond recommender confidence.
  - [`egsf-selector--global-scalar-reranking-dominance.md`](failures/egsf-selector--global-scalar-reranking-dominance.md): contextual selector gains were absorbed by a global scalar control.
  - [`eg-ter-repair--hard-safety-filter-baseline-trap.md`](failures/eg-ter-repair--hard-safety-filter-baseline-trap.md): unlevelled hard-safety rules overstated learned repair value.
  - [`crc-ps-r006--conformal-risk-certificate-exhaustion.md`](failures/crc-ps-r006--conformal-risk-certificate-exhaustion.md): empirical feasibility did not survive the finite-grid certificate.
- **[`accumulated-experience.md`](accumulated-experience.md)**: historical archive synthesis; not the live project-state registry.
- **[`literature-memory.md`](literature-memory.md)**: curated canonical literature cards.
- **[`archive-evidence-index.md`](archive-evidence-index.md)**: provenance map to the read-only `New-Search` archive.

## Active cross-idea constraint

R0 adds one admitted reusable constraint:

> hospitalization/visit-level DDI pair co-membership is not equivalent to execution-confirmed current exposure applicability.

On Discovery, 21.0521% of eMAR-observed visit-union DDI patient-hospitalization-pair episodes were static-only under the frozen R0 operational definition.

This constraint justifies testing a new method formulation; it does not establish that the learned formulation works. Idea 006 Gate 01 is the required learned-vs-direct-control test.
