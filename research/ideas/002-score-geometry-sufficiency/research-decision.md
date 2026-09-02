<!-- markdownlint-disable MD013 -->

# Research Decision — Idea 002: Score-Geometry Sufficiency

- **Idea**: `research/ideas/002-score-geometry-sufficiency/`
- **Gate**: `Gate 01 — Score-Geometry Sufficiency`
- **Formal Run ID**: `gate-01-score-geometry-sufficiency-20260902-174013`
- **Harness Revision**: `28fc24c64998c81563446f3f8e5bc10340e2b17b`
- **Decision Date**: 2026-09-02
- **Integrity Audit**: `INTEGRITY_PASS`
- **Formal Verdict**: `STOP_NO_INCREMENTAL_SCORE_GEOMETRY`
- **Stage Transition**: `TERMINATE_IDEA_002`

## Decision

The preregistered hypothesis is falsified under the frozen Gate 01 setting. The five-bin Dev-fitted score map did not produce a candidate ordering different from raw `ScoreOnly`, and therefore supplied no incremental routing value on Audit.

Gate 02 is not authorized. The exploratory Candidate 2 recorded before execution is not authorized as an automatic continuation.

## Authoritative evidence

The full validation cohort contained `1,059` patients. The frozen patient-level split with seed `2002` produced `529` Dev and `530` Audit patients. Eligible candidate counts were `7,422` on Dev and `8,127` on Audit with zero patient overlap.

The Dev empirical PB risks were strictly monotonic across the five frozen score bins:

| Bin | Empirical PB risk |
| --- | ---: |
| B1 | 0.581145 |
| B2 | 0.462938 |
| B3 | 0.317172 |
| B4 | 0.179919 |
| B5 | 0.053908 |

Because the bin priority followed this same ordering and the frozen within-bin tie-break was ascending score, `ScoreGeometry` and `ScoreOnly` induced identical rankings.

| Metric | 10% | 20% | 30% |
| --- | ---: | ---: | ---: |
| ScoreOnly PBYield | 0.612069 | 0.593231 | 0.563167 |
| Geometry - Score | 0.000000 | 0.000000 | 0.000000 |
| 95% CI, Geometry - Score | [0, 0] | [0, 0] | [0, 0] |
| Oracle - Score | +0.387931 | +0.406769 | +0.436833 |

The uncertainty calculation used 1,000 patient-clustered bootstrap replicates with seed `1203`. Independent `ccf-integrity-auditor` recomputation reported zero numeric discrepancy, no Dev/Audit leakage, and no test access.

## Scientific interpretation

Supported:

> The preregistered five-bin low-complexity score-only mapping did not provide reproducible ranking information beyond raw ScoreOnly.

Also supported:

> Significant Oracle–ScoreOnly headroom shows retrospective false-positive heterogeneity not explained by the frozen scalar confidence.

Not established:

- that one-dimensional score space has no other non-monotone structure;
- that all confidence-derived functions are universally useless;
- that a target-free residual signal is necessarily observable, learnable, or deployable;
- that relational, temporal, structural, patient-conditioned, cross-model, or other DDI-derived information is useless;
- clinical safety, patient benefit, prescribing validity, or causal mechanism.

## Route boundary

This particular score-geometry route is terminated. Changing only the function class on the same scientific premise — for example, five bins to ten bins, a spline, or an MLP — is not an authorized rescue. A future hypothesis must materially change the observable information, problem formalization, mechanistic claim, baseline, representation, or evidence source and must be preregistered before outcome inspection.

Historical validation evidence from Ideas 001 and 002 has already informed route selection. Future validation-only Audit evidence may continue to support research-route selection, but it is not untouched final generalization evidence. The test split remains untouched.

## Next owner

`ccf-pipeline-orchestrator` for post-negative-result ideation coordination, followed by literature grounding and a new `ccf-idea-optimizer` cycle. No next Idea is implied by this decision.
