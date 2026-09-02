<!-- markdownlint-disable MD013 -->

# Research Decision: Idea 003 (Prescription-Relative Confidence)

- **Idea**: `003-prescription-relative-confidence`
- **Gate**: `gate-01-prescription-relative-confidence`
- **Formal Run ID**: `gate-01-prescription-relative-confidence-20260902-233128`
- **Harness Revision**: `ac9dfe860bbce7a9a9620cf21836931136582055`
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

1. **Relative Rank Does Not Supply Incremental FP Routing Signal**:
   Although within-prescription relative rank $r_t(m)$ receives a positive coefficient on Dev ($\beta_r = +0.2223$), on the held-out Audit cohort its inclusion yields negative point gaps ($-0.26\%$ at 10% and 20%) and confidence intervals crossing zero.
2. **Absolute Score and Marginal Prevalence Absorb Observable Variance**:
   The simple control features (absolute score $u$, prescription size $c$, train prevalence $f$, and their pairwise interactions) capture all identifiable predictive signal available from single-visit confidence outputs. Once these controls are accounted for, within-prescription ordering provides zero incremental routing value.
3. **Large Residual Outcome Heterogeneity Remains Unexplained**:
   The retrospective Oracle headroom over `StrongControl` exceeds $+42.5\%$ across all review budgets. True false positives are highly concentrated, but intra-prescription score rank does not index them.

---

## 4. Closure & Scope Boundaries

- Idea 003 is formally **CLOSED** at Gate 01.
- No Gate 02 will be designed or executed for Idea 003.
- The test split remains 100% untouched and unindexed.
- This result does not imply that multi-agent, patient-conditioned, or longitudinal signals are useless; it establishes that within-prescription relative confidence ranking on frozen MoleRec predictions is insufficient for false-positive routing.

---

## 5. Next Idea Recommendation (Idea 004)

Synthesizing findings across Ideas 001, 002, and 003:

- **Idea 001**: Direct DDI degree / tension pressure interaction adds zero incremental signal over recommender score ($Scalar - Score = 0.0\%$).
- **Idea 002**: Non-monotone score geometry quintile mapping collapses identically to monotonic score sorting ($Geometry - Score = 0.0\%$).
- **Idea 003**: Within-prescription relative confidence ranking adds zero incremental signal beyond absolute score, prescription size, and train-only prevalence ($Rank - Control \le 0$).
- **Common Crux**: Single-visit prediction-time observables ($s, n_t, r_t, d_t$) and static marginal train prevalence ($p_{train}$) have been exhausted. Yet retrospective Oracle headroom ($>+42\%$) proves substantial outcome heterogeneity exists.

**Recommended Direction for Idea 004**:
**`004-longitudinal-prescription-novelty`** (or **`004-longitudinal-transition-verification`**):
Investigate whether **patient-specific longitudinal recurrence** (i.e. distinguishing repeat prescriptions previously administered to this specific patient vs novel drug initiations) provides reproducible incremental false-positive routing signal beyond the `StrongControl` benchmark. In clinical EHR prescribing, false-positive recommender errors disproportionately occur during acute medication continuation or novel initiations. Patient history is target-free, clinically grounded, and completely unexploited by static single-visit selectors.
