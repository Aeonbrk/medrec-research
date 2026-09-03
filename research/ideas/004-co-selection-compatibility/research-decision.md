<!-- markdownlint-disable MD013 -->

# Research Decision: Idea 004 (Co-Selection Compatibility)

- **Idea**: `004-co-selection-compatibility`
- **Gate**: `gate-01-co-selection-compatibility`
- **Formal Run ID**: `gate-01-co-selection-compatibility-20260903-154343`
- **Harness Revision**: `8640ce521a942bd34daa2a5547c2e2db1febca6a`
- **Execution Host**: `319-lab`
- **Decision Date**: 2026-09-03
- **Authoritative Verdict**: `STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY`
- **Action**: `TERMINATE_IDEA_004`

---

## 1. Executive Summary

Idea 004 hypothesized that train-only frequency-corrected pairwise co-selection compatibility (empirical Normalized Pointwise Mutual Information, NPMI) averaged over peer predicted medications, $A_t(m) = \frac{1}{|\hat M_t|-1} \sum_{j \in \hat M_t \setminus \{m\}} \text{NPMI}_{train}(m, j)$, contains reproducible incremental false-positive routing signal for DDI-active medications beyond a strong simple control model incorporating absolute score $s_t(m)$, predicted prescription size $n_t$, candidate train prevalence $p_{train}(m)$, peer prevalence mean $q_t(m)$, and their predeclared score interactions.

Gate 01 evaluated this hypothesis on the full frozen MoleRec validation cohort under a deterministic, patient-disjoint Dev (529 patients) / Audit (530 patients) split (seed `2004`), reserving the test split completely untouched. Dev-fitted ridge linear probability models were evaluated on 7,787 held-out Audit candidate revisions across 426 eligible patients.

The preregistered mechanical decision tree yielded:

1. **Gate A (Audit Support)**: **PASS** ($N_{PB=1}=417 \ge 50$, $N_{PB=0}=426 \ge 50$, $k(10\%)=778 > 0$, $k(20\%)=1557 > 0$).
2. **Gate B (Oracle Headroom over Strong Control)**: **PASS** (Oracle achieves 100.0% yield; `Oracle - StrongControl` is $+38.43\%$ at 10% budget with 95% CI $[+33.87\%, +42.93\%]$; $+40.46\%$ at 20% budget with 95% CI $[+37.18\%, +43.61\%]$; both lower bounds $> 0$).
3. **Gate C (CoSelectionAugmented Incremental Yield over Strong Control)**: **FAIL** (`CoSelectionAugmented - StrongControl` is $+0.77\%$ at 10% budget with 95% CI $[-1.16\%, +2.50\%]$; $+0.06\%$ at 20% budget with 95% CI $[-0.68\%, +0.78\%]$; both lower bounds $\le 0$, crossing zero).

Because Gate C failed at both preregistered primary budgets, the mandatory verdict is:
`STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY`
The research decision is to terminate Idea 004 at Gate 01.

---

## 2. Quantitative Evidence Summary

All figures independently verified by `ccf-integrity-auditor` (`INTEGRITY_PASS`) from restricted candidate records on 319:

### Policy Yields on Audit Cohort ($N_{Audit} = 7,787$)

| Policy / Selector | 10% Budget ($k=778$) | 20% Budget ($k=1,557$) | 30% Budget ($k=2,336$) |
| :--- | :---: | :---: | :---: |
| `Random` Base Yield | 31.64% | 31.64% | 31.64% |
| `ScoreOnly` | 61.57% | 58.38% | 56.25% |
| `StrongControl` ($u, c, f, g, u \cdot c, u \cdot f, u \cdot g$) | 61.57% | 59.54% | 56.81% |
| `CoSelectionAugmented` ($x_{ctrl}, A_t(m)$) | 62.34% | 59.60% | 55.99% |
| Retrospective `Oracle` | 100.0% | 100.0% | 100.0% |

### Paired Differences and Patient-Clustered Bootstrap 95% CIs (1,000 replicates)

| Comparison | 10% Budget Point Est | 10% Budget 95% CI | 20% Budget Point Est | 20% Budget 95% CI |
| :--- | :---: | :---: | :---: | :---: |
| `StrongControl - ScoreOnly` | 0.00% | [-1.80%, +1.66%] | +1.16% | [+0.14%, +2.07%] |
| `Oracle - StrongControl` (Gate B) | +38.43% | [+33.87%, +42.93%] | +40.46% | [+37.18%, +43.61%] |
| `CoSelectionAugmented - StrongControl` (Gate C) | +0.77% | [-1.16%, +2.50%] | +0.06% | [-0.68%, +0.78%] |

---

## 3. Failure Diagnosis

1. **The preregistered co-selection compatibility observable did not generalize incrementally**: Although co-selection compatibility $A_t(m)$ entered the Dev linear probability model with negative coefficient ($\beta_A = -0.9439$), its addition produced statistically indistinguishable point differences ($+0.77\%$ at 10%, $+0.06\%$ at 20%) with bootstrap 95% confidence intervals crossing zero.
2. **The Gate does not identify a single universal explanation for that failure**: The evidence supports the narrower conclusion that the frozen `CoSelectionAugmented` construction did not improve routing beyond the frozen `StrongControl`. It does not establish that the control absorbs all relational information, nor does it distinguish definitively between co-selection sparsity, linear representation limits, or absence of incremental signal.
3. **Residual retrospective outcome heterogeneity remains unexplained**: `Oracle - StrongControl` exceeds $+38.4\%$ at 10% and $+40.4\%$ at 20%. Because Oracle uses the target, this establishes substantial retrospective outcome heterogeneity not explained by the frozen control; it does not establish that the heterogeneity is target-free observable.

---

## 4. Closure & Scope Boundaries

- Idea 004 is formally **CLOSED** at Gate 01.
- No Gate 02 will be designed or executed for Idea 004.
- The test split remains 100% untouched and unindexed.
- The failed hypothesis is the preregistered one-scalar train-only empirical NPMI co-selection compatibility observable under the frozen MoleRec setting and strong control.
- This result does not establish that other single-visit, patient-conditioned, longitudinal, structural, or cross-model observables are useless.

---

## 5. Post-Idea-004 Research Selection

Synthesizing the scoped findings across Ideas 001, 002, 003, and 004:

- **Idea 001**: The preregistered active-DDI-degree scalar and Tension interaction did not establish incremental routing information beyond frozen recommender confidence.
- **Idea 002**: The preregistered five-bin Dev-fitted score map induced the same candidate ordering as `ScoreOnly` and produced zero incremental routing yield.
- **Idea 003**: The preregistered within-prescription mid-rank feature did not establish incremental routing information beyond absolute score, prescription size, train-only prevalence, and their frozen interactions.
- **Idea 004**: The preregistered train-only co-selection compatibility feature did not establish incremental routing information beyond absolute score, prescription size, candidate prevalence, peer prevalence, and their interactions.
- **Residual question**: Substantial retrospective Oracle headroom remains beyond the frozen controls; its target-free observable explanation is unresolved.

No Idea 005 is selected by this decision. Any candidate successor must undergo current literature grounding, novelty audit, and explicit idea scoring before any Idea 005 directory or Gate is created.

The next CCFA sequence is:

```text
ccf-pipeline-orchestrator
-> ccf-literature-monitor / ccf-literature-searcher
-> ccf-idea-optimizer (exploratory)
-> ccf-idea-reviewer (standard, explicit ranking)
-> ccf-idea-optimizer (standard, winner only)
-> ccf-experiment-designer
```
