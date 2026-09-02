<!-- markdownlint-disable MD013 -->

# Failure Record: Prescription-relative confidence (Gate 01 no incremental relative confidence)

Source boundary: `medrec-research` Idea `003-prescription-relative-confidence`, Gate 01 formal run `gate-01-prescription-relative-confidence-20260902-233128` on `319-lab` at frozen harness commit `ac9dfe860bbce7a9a9620cf21836931136582055`. The independent integrity audit concluded `INTEGRITY_PASS`; the authoritative research decision is `STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE` / `TERMINATE_IDEA_003`.

- **Status**: Historical Memory (this within-prescription relative confidence route is terminated under the recorded setting; revisit only when materially different observable information, problem formalization, causal/mechanistic claim, baseline, representation, or evidence source changes the hypothesis)

## Failed hypothesis

Among DDI-active medications predicted by frozen MoleRec, within-prescription relative confidence mid-rank position $r_t(m)$ contains reproducible incremental false-positive routing information beyond a strong simple control built from absolute medication score $s_t(m)$, predicted prescription size $n_t$, and train-only medication prevalence $p_{train}(m)$.

## What was tested

Under the frozen MoleRec validation setting, candidate universe:

$$
\mathcal Q_t = \{m \in \hat M_t : d_t(m) > 0\},
$$

and singleton deletion revision operator:

$$
R_0(\hat M_t, m) = \hat M_t \setminus \{m\},
$$

the candidate outcome is false-positive status:

$$
Y^{PB}_{t,m} = \mathbf 1[m \notin M_t].
$$

For each candidate, the exact mid-rank position $r_t(m)$ was computed over the complete predicted prescription $\hat M_t$:

$$
r_t(m) = \frac{|\{j \in \hat M_t : s_t(j) > s_t(m)\}| + 0.5 \cdot |\{j \in \hat M_t \setminus \{m\} : s_t(j) == s_t(m)\}|}{n_t - 1}.
$$

The full 1,059-patient validation cohort was partitioned into a deterministic patient-disjoint Dev set (529 patients, 7,809 candidates) and Audit set (530 patients, 7,740 candidates) with seed `2003`.

Dev-only ridge linear probability models ($\lambda = 10^{-6}$, unpenalized intercept) were fit for:

- `StrongControl`: $[u, c, f, u \cdot c, u \cdot f]$ where $u = 1 - s$, $c = \log(1 + n_t)$, $f = \text{logit}(p_{train})$.
- `RankAugmented`: $[u, c, f, u \cdot c, u \cdot f, r_t(m)]$.

Audit candidates were evaluated at 10% ($k=774$), 20% ($k=1,548$), and 30% ($k=2,322$) review budgets, with patient-clustered bootstrap uncertainty (1,000 replicates, seed `1203`).

## What was observed

1. **Preregistered split and Dev-only fitting held strictly**: 7,809 Dev candidates from 435 eligible patients, 7,740 Audit candidates from 423 eligible patients; zero patient overlap between partitions; test split untouched.
2. **`StrongControl` modestly improved over `ScoreOnly` on Audit**:
   - 10% budget: 57.49% vs 56.85% (+0.65%, 95% CI: [-0.70%, +1.44%])
   - 20% budget: 57.17% vs 55.88% (+1.29%, 95% CI: [+0.34%, +1.73%])
3. **`RankAugmented` failed to provide incremental signal over `StrongControl`**:
   - 10% budget: 57.24% vs 57.49% ($-0.26\%$, 95% CI: $[-1.37\%, +1.19\%]$)
   - 20% budget: 56.91% vs 57.17% ($-0.26\%$, 95% CI: $[-0.65\%, +0.80\%]$)
   - 30% budget: 55.00% vs 55.30% ($-0.30\%$, 95% CI: $[-0.94\%, +0.34\%]$)
4. **Gate C failed at both primary budgets**: Lower bounds of the 95% bootstrap confidence intervals for `RankAugmented - StrongControl` were strictly negative ($-1.37\%$ and $-0.65\%$). Point estimates showed slight negative transfer ($-0.26\%$).
5. **Residual retrospective outcome heterogeneity remained large**: `Oracle - StrongControl` was $+42.51\%$ (10% budget, 95% CI: $[+39.04\%, +46.15\%]$) and $+42.83\%$ (20% budget, 95% CI: $[+40.34\%, +45.78\%]$).
6. **Independent integrity audit passed**: `ccf-integrity-auditor` confirmed all numbers, split counts, regression coefficients, and bootstrap intervals with exact precision (`INTEGRITY_PASS`).

## Why this route failed

Within-prescription relative rank $r_t(m)$ is largely redundant with the combination of absolute score $s_t(m)$ and predicted prescription size $n_t$. In a multi-label sigmoid scoring architecture, absolute scores already encode confidence calibrated across the vocabulary. While rank varies within each visit, conditioning on absolute score, prescription size, and marginal baseline prevalence absorbs the available single-visit predictive variance. Adding $r_t(m)$ introduces noise and slight over-fitting on Dev, resulting in zero (and slightly negative) incremental yield on held-out Audit patients.

## What did not fail

- **`StrongControl` is an effective baseline**: Combining absolute score with prescription size and train prevalence provides a modest, reproducible improvement over raw `ScoreOnly` (+1.29% at 20% budget).
- **Residual false-positive heterogeneity remains unresolved**:

$$
\boxed{\text{Residual false-positive heterogeneity remains unresolved.}}
$$

- **Oracle headroom is not mechanism evidence**: Retrospective Oracle yield of 100.0% (+42.5% over control) demonstrates that false positives are highly non-random, but single-visit score observables cannot separate them.
- **Longitudinal and relational mechanisms remain untested**: The failure is strictly localized to static within-prescription confidence ranking.

## Reusable residue

- `StrongControl` ($u, c, f, u \cdot c, u \cdot f$) should be retained as the required benchmark control for any future candidate selector.
- Within-prescription relative rank should not be pursued further as an independent routing feature under static single-visit representations.
- The 1,059-patient validation cohort, train-only prevalence extraction, and patient-cluster bootstrap framework provide a rigorous standard for rapid falsification of candidate signals.

## Route boundary

This within-prescription relative confidence route is terminated.

The result must not be generalized into claims that multi-visit temporal history, longitudinal patient recurrence, or structural graph embeddings are useless.

## Non-revival condition

Changing the rank calculation (e.g. dense rank, fractional percentile, or non-linear rank transformation) without altering the information source does not constitute a new hypothesis. A future route is scientifically distinct only if it incorporates materially different observable evidence (e.g. longitudinal prescription transitions, multi-visit patient history, or clinical ontology structure).

## Evidence boundary

Scoped to the frozen MoleRec checkpoint, validation-only candidate corpus, DDI-active review universe, singleton deletion operator, train-only Laplace prevalence, and frozen budgets. The test split remains untouched.
