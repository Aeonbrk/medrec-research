<!-- markdownlint-disable MD013 -->

# Research Decision: Idea 003 (Prescription-Relative Confidence)

- **Idea**: `003-prescription-relative-confidence`
- **Gate**: `gate-01-prescription-relative-confidence`
- **Formal Run ID**: `gate-01-prescription-relative-confidence-20260902-233128`
- **Harness Revision**: `ac9dfe860bbce7a9a9620cf21836931136582055`
- **Execution Host**: `319-lab-via-server`
- **Decision Date**: 2026-09-02
- **Authoritative Verdict**: `STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE`
- **Action**: `TERMINATE_IDEA_003`

---

## 1. Executive Summary

Idea 003 hypothesized that within-prescription relative confidence rank $r_t(m)$ contains reproducible incremental false-positive routing signal for DDI-active medications beyond a strong simple control model built from absolute medication score $s_t(m)$, predicted prescription size $n_t$, and train-only medication prevalence $p_{train}(m)$.

Gate 01 evaluated this hypothesis on the full frozen MoleRec validation cohort under a deterministic, patient-disjoint Dev (529 patients) / Audit (530 patients) split (seed `2003`), reserving the test split completely untouched. Dev-fitted ridge linear probability models were evaluated on 7,740 held-out Audit candidate revisions across 423 eligible patients.

The preregistered mechanical decision tree yielded:

1. **Gate A (Audit Support)**: **PASS** ($N_{PB=1}=417 \ge 50$, $N_{PB=0}=423 \ge 50$, $k(10\%)=774 > 0$, $k(20\%)=1548 > 0$).
2. **Gate B (Oracle Headroom over Strong Control)**: **PASS** (Oracle achieves 100.0% yield; `Oracle - StrongControl` is $+42.51\%$ at 10% budget with 95% CI $[+39.04\%, +46.15\%]$; $+42.83\%$ at 20% budget with 95% CI $[+40.34\%, +45.78\%]$; both lower bounds $> 0$).
3. **Gate C (RankAugmented Incremental Yield over Strong Control)**: **FAIL** (`RankAugmented - StrongControl` is $-0.26\%$ at 10% budget with 95% CI $[-1.37\%, +1.19\%]$; $-0.26\%$ at 20% budget with 95% CI $[-0.65\%, +0.80\%]$; both lower bounds $\le 0$).

Because Gate C failed at both preregistered primary budgets, the mandatory verdict is:
`STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE`
The research decision is to terminate Idea 003 at Gate 01.

---

## 2. Quantitative Evidence Summary

All figures independently verified by `ccf-integrity-auditor` (`INTEGRITY_PASS`) from restricted candidate records on 319:

### Policy Yields on Audit Cohort ($N_{Audit} = 7,740$)

| Policy / Selector | 10% Budget ($k=774$) | 20% Budget ($k=1,548$) | 30% Budget ($k=2,322$) |
| :--- | :---: | :---: | :---: |
| `Random` Base Yield | 31.37% | 31.37% | 31.37% |
| `ScoreOnly` | 56.85% | 55.88% | 54.87% |
| `StrongControl` ($u, c, f, u \cdot c, u \cdot f$) | 57.49% | 57.17% | 55.30% |
| `RankAugmented` ($u, c, f, u \cdot c, u \cdot f, r$) | 57.24% | 56.91% | 55.00% |
| Retrospective `Oracle` | 100.0% | 100.0% | 100.0% |

### Paired Differences and Patient-Clustered Bootstrap 95% CIs (1,000 replicates)

| Comparison | 10% Budget Point Est | 10% Budget 95% CI | 20% Budget Point Est | 20% Budget 95% CI |
| :--- | :---: | :---: | :---: | :---: |
| `StrongControl - ScoreOnly` | +0.65% | [-0.70%, +1.44%] | +1.29% | [+0.34%, +1.73%] |
| `Oracle - StrongControl` (Gate B) | +42.51% | [+39.04%, +46.15%] | +42.83% | [+40.34%, +45.78%] |
| `RankAugmented - StrongControl` (Gate C) | -0.26% | [-1.37%, +1.19%] | -0.26% | [-0.65%, +0.80%] |

---

## 3. Failure Diagnosis

1. **The preregistered relative-rank feature did not generalize incrementally**: Although within-prescription relative rank $r_t(m)$ received a positive coefficient on Dev ($\beta_r = +0.2223$), its addition produced negative point gaps on held-out Audit ($-0.26\%$ at both primary budgets) with confidence intervals crossing zero.
2. **The Gate does not identify a universal explanation for that failure**: The evidence supports the narrower conclusion that the frozen `RankAugmented` construction did not improve routing beyond the frozen `StrongControl`. It does not establish that the control absorbs all possible single-visit predictive information, nor does it distinguish definitively among redundancy, estimator mismatch, weak signal, or absence of signal as causal explanations.
3. **Residual retrospective outcome heterogeneity remains unexplained**: `Oracle - StrongControl` exceeds $+42.5\%$ at both primary budgets. Because Oracle uses the target, this establishes substantial retrospective heterogeneity not explained by the frozen control; it does not establish that the heterogeneity is target-free observable, concentrated in any particular feature space, or attributable to a specific mechanism.

---

## 4. Closure & Scope Boundaries

- Idea 003 is formally **CLOSED** at Gate 01.
- No Gate 02 will be designed or executed for Idea 003.
- The test split remains 100% untouched and unindexed.
- The failed hypothesis is the preregistered one-scalar within-prescription mid-rank route under the frozen MoleRec setting and strong control.
- This result does not establish that other single-visit, medication-set relational, patient-conditioned, longitudinal, structural, DDI-derived, or cross-model observables are useless.

---

## 5. Post-Idea-003 Research Selection

Synthesizing the scoped findings across Ideas 001, 002, and 003:

- **Idea 001**: The preregistered active-DDI-degree scalar and Tension interaction did not establish incremental routing information beyond frozen recommender confidence under the recorded setting.
- **Idea 002**: The preregistered five-bin Dev-fitted score map induced the same candidate ordering as `ScoreOnly` and produced zero incremental routing yield.
- **Idea 003**: The preregistered within-prescription mid-rank feature did not establish incremental routing information beyond absolute score, prescription size, train-only prevalence, and their frozen interactions.
- **Residual question**: Substantial retrospective Oracle headroom remains beyond the frozen `StrongControl`; its target-free observable explanation is unresolved.

No Idea 004 is selected by this decision. In particular, longitudinal prescription recurrence or transition status is a candidate information source rather than an authorized successor. It must undergo current literature grounding and compete against materially different candidate hypotheses before any Idea 004 directory or Gate is created.

The next CCFA sequence is:

```text
ccf-pipeline-orchestrator
-> ccf-literature-monitor / ccf-literature-searcher
-> ccf-idea-optimizer (exploratory)
-> ccf-idea-reviewer (standard, explicit ranking)
-> ccf-idea-optimizer (standard, winner only)
-> ccf-experiment-designer
```
