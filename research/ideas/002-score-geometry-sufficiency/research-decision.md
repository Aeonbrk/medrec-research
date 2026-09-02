<!-- markdownlint-disable MD013 -->

# Research Decision — Idea 002: Score-Geometry Sufficiency

- **Idea**: `research/ideas/002-score-geometry-sufficiency/`
- **Gate**: `Gate 01 — Score-Geometry Sufficiency`
- **Formal Run ID**: `gate-01-score-geometry-sufficiency-20260902-174013`
- **Harness Revision**: `28fc24c64998c81563446f3f8e5bc10340e2b17b`
- **Decision Date**: 2026-09-02
- **Integrity Audit**: `INTEGRITY_PASS` (`research/ideas/002-score-geometry-sufficiency/experiments/gate-01-integrity-audit.md`)
- **Public Summary**: `research/ideas/002-score-geometry-sufficiency/experiments/gate-01-summary.json` (SHA256: `ee2ef10ffb9bd9b4e52135f6062e2e4375c6dabc7c53799f436117a39b476a58`)

---

## 1. Formal Scientific Verdict

```text
Formal Verdict: STOP_NO_INCREMENTAL_SCORE_GEOMETRY
Dev Diagnostic: STOP_DEV_ORDER_EQUIVALENT
Scientific Status: HYPOTHESIS_FALSIFIED
Stage Transition: TERMINATE_IDEA_002
```

---

## 2. Core Question & Hypotheses

- **Preregistered Research Question**: Does a preregistered low-complexity non-monotone mapping of the frozen MoleRec medication score contain reproducible false-positive ranking structure that raw `ScoreOnly` fails to exploit?
- **Hypothesis 1 (Score-Geometry Sufficiency)**: Falsified. The empirical false-positive rate across quintile score bins is strictly monotonically non-increasing with model score ($0.5811 \to 0.4629 \to 0.3172 \to 0.1799 \to 0.0539$). When combined with deterministic ascending-score tie-breaking, the induced candidate ordering on both Dev and Audit is 100% order-equivalent to monotonic `ScoreOnly`.
- **Incremental Value**: Zero. $Gap_{Geometry - Score} = 0.000000$ (95% CI: $[0.000000, 0.000000]$) across all evaluation budgets ($10\%, 20\%, 30\%$). Low-complexity score geometry captures $0.0\%$ of the residual headroom.

---

## 3. Authoritative Experimental Evidence

### Cohort & Split Invariants

- **Universe**: Full validation cohort of 1,059 patients (`range(1059)`), partitioned via standard library `random.Random(2002)` into 529 Dev patients and 530 Audit patients.
- **Candidate Corpus**: Upstream audited corpus `gate-02-confidence-sufficiency-20260902-155433` (`gate-02-candidates.jsonl`, SHA256: `50b8f7587f44ec81dd5ec0ec188d953cf9edfbb332279ce3fb759ae33ed2e736`).
- **Counts**: Dev partition contains 7,422 candidates across 436 eligible patients; Audit partition contains 8,127 candidates across 422 eligible patients ($7,422 + 8,127 = 15,549$). Zero patient overlap.
- **Support**: Audit contains 419 beneficial patients ($Y^{PB}=1$) and 421 non-beneficial patients ($Y^{PB}=0$), both $\ge 50$. Support is sufficient.

### Dev Quintile Score Map ($g(s)$)

Nearest-rank cutpoints fit strictly on the 7,422 Dev candidates:

- $c_{0.2} = 0.758362$
- $c_{0.4} = 0.890841$
- $c_{0.6} = 0.949205$
- $c_{0.8} = 0.979460$

| Bin | Score Interval | Dev Count | Empirical PB Rate ($\hat p_j$) | Priority Rank |
| :---: | :--- | :---: | :---: | :---: |
| B1 | $s \le 0.758362$ | 1,485 | 0.581145 (863 / 1485) | 1 |
| B2 | $0.758362 < s \le 0.890841$ | 1,484 | 0.462938 (687 / 1484) | 2 |
| B3 | $0.890841 < s \le 0.949205$ | 1,485 | 0.317172 (471 / 1485) | 3 |
| B4 | $0.949205 < s \le 0.979460$ | 1,484 | 0.179919 (267 / 1484) | 4 |
| B5 | $s > 0.979460$ | 1,484 | 0.053908 (80 / 1484) | 5 |

Because $\hat p_1 > \hat p_2 > \hat p_3 > \hat p_4 > \hat p_5$, `ScoreGeometry` prioritizes bins in exact ascending score order ($B_1 \to B_2 \to B_3 \to B_4 \to B_5$). Within bins, tie-breaking sorts $s$ ascending. Consequently, `ScoreGeometry` ordering is identical to `ScoreOnly` on both Dev and Audit.

### Audit Policy Performance ($N=8,127$ candidates, 422 patients)

| Policy / Metric | Budget 10% ($k=812$) | Budget 20% ($k=1625$) | Budget 30% ($k=2438$) |
| :--- | :---: | :---: | :---: |
| **Random** (base rate) | 0.314630 | 0.314630 | 0.314630 |
| **ScoreOnly** | 0.612069 [0.577102, 0.656406] | 0.593231 [0.559443, 0.623548] | 0.563167 [0.536761, 0.588607] |
| **ScoreGeometry** | 0.612069 [0.577102, 0.656406] | 0.593231 [0.559443, 0.623548] | 0.563167 [0.536761, 0.588607] |
| **Oracle** | 1.000000 [1.000000, 1.000000] | 1.000000 [1.000000, 1.000000] | 1.000000 [1.000000, 1.000000] |
| **Score - Random** | +0.297439 [0.265999, 0.337452] | +0.278601 [0.252789, 0.301563] | +0.248536 [0.230716, 0.265182] |
| **Geometry - Score** | **0.000000 [0.000000, 0.000000]** | **0.000000 [0.000000, 0.000000]** | **0.000000 [0.000000, 0.000000]** |
| **Oracle - Score** | +0.387931 [0.343594, 0.422898] | +0.406769 [0.376452, 0.440557] | +0.436833 [0.411393, 0.462322] |
| **Residual Capture** | **0.000000 [0.000000, 0.000000]** | **0.000000 [0.000000, 0.000000]** | **0.000000 [0.000000, 0.000000]** |

*Note: Brackets report 95% bootstrap confidence intervals across 1,000 patient-clustered replicates (seed 1203).*

---

## 4. Preregistered Decision Tree Audit

```text
Gate 01-A (Audit Support Check):
  - Audit beneficial patients: 419 >= 50 -> PASS
  - Audit non-beneficial patients: 421 >= 50 -> PASS

Gate 01-B (Residual Headroom Check):
  - LowerCI_95%[Oracle - Score (10%)] = 0.343594 > 0 -> PASS
  - LowerCI_95%[Oracle - Score (20%)] = 0.376452 > 0 -> PASS

Gate 01-C (Score-Geometry Incremental Value Check):
  - LowerCI_95%[Geometry - Score (10%)] = 0.000000 <= 0 -> FAIL
  - LowerCI_95%[Geometry - Score (20%)] = 0.000000 <= 0 -> FAIL

Dev-Only Diagnostic:
  - Dev candidate order equivalence: TRUE
  - Diagnostic: STOP_DEV_ORDER_EQUIVALENT

Terminal Decision: STOP_NO_INCREMENTAL_SCORE_GEOMETRY
```

---

## 5. Scientific Findings & Scope Boundaries

### What Has Been Established

1. **Raw Model Score is an Excellent Monotonic Selector**: Lower score corresponds strongly to higher empirical false-positive risk. At a 10% budget, raw score achieves a 61.21% Pareto-beneficial yield, nearly doubling the base prevalence of 31.46% ($+29.74\%$).
2. **Substantial Uncaptured Headroom Survives**: The Oracle policy achieves 100.0% yield, leaving a massive $+38.79\%$ to $+40.68\%$ residual gap beyond raw score. The model's score alone does not saturate the routing opportunity.
3. **Score Geometry Fails to Exploit This Headroom**: Low-complexity non-monotone partitioning of the 1D score space discovers no inversion or non-monotonic false-positive pocket. The empirical risk is strictly monotonic in score. Thus, binning adds exactly 0.0% improvement over sorting by raw score directly.

### Scope and Boundary Limits

- **No Universal Falsification of Multidimensional Representations**: This falsification strictly bounds 1D score transformations on the frozen MoleRec baseline. It does not speak to multi-feature representations (e.g. representations incorporating graph topology, patient history, or multi-task embeddings).
- **No Evaluation on Test Split**: In strict compliance with the Unified Research Protocol, all evaluations occurred on the validation cohort. The test split remains pristine.
- **No Retraining**: MoleRec was not retrained.

---

## 6. Authoritative Next Steps

1. **Gate 02 of Idea 002 is NOT AUTHORIZED**: Do not proceed to Gate 02.
2. **Candidate 2 is NOT AUTHORIZED**: Do not explore ad-hoc feature additions under Idea 002 without a formal, reviewed idea proposal.
3. **Idea 002 is TERMINATED**: Conclude Idea 002 as cleanly falsified at Gate 01 (`FALSIFIED_AT_GATE_01`).
4. **Research Memory Updated**: Persist this negative finding in research memory so future directions do not attempt simple 1D score-space partitioning.
