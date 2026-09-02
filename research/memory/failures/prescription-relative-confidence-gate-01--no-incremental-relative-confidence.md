<!-- markdownlint-disable MD013 -->

# Failure Record: Prescription-relative confidence (Gate 01 no incremental relative confidence)

Source boundary: `medrec-research` Idea `003-prescription-relative-confidence`, Gate 01 formal run `gate-01-prescription-relative-confidence-20260902-233128` on `319-lab-via-server` at frozen harness commit `ac9dfe860bbce7a9a9620cf21836931136582055`. The independent integrity audit concluded `INTEGRITY_PASS`; the authoritative research decision is `STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE` / `TERMINATE_IDEA_003`.

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
2. **`StrongControl` versus `ScoreOnly`**:
   - 10% budget: 57.49% vs 56.85% (+0.65%, 95% CI: [-0.70%, +1.44%])
   - 20% budget: 57.17% vs 55.88% (+1.29%, 95% CI: [+0.34%, +1.73%])
   The control improvement is statistically supported at the 20% primary budget but not at 10%.
3. **`RankAugmented` failed to provide incremental signal over `StrongControl`**:
   - 10% budget: 57.24% vs 57.49% ($-0.26\%$, 95% CI: $[-1.37\%, +1.19\%]$)
   - 20% budget: 56.91% vs 57.17% ($-0.26\%$, 95% CI: $[-0.65\%, +0.80\%]$)
   - 30% budget: 55.00% vs 55.30% ($-0.30\%$, 95% CI: $[-0.94\%, +0.34\%]$)
4. **Gate C failed at both primary budgets**: the lower 95% confidence bounds for `RankAugmented - StrongControl` were $-1.37\%$ and $-0.65\%$, so the preregistered PASS condition was not met. Point estimates were slightly negative at both primary budgets.
5. **Residual retrospective outcome heterogeneity remained large**: `Oracle - StrongControl` was $+42.51\%$ (10% budget, 95% CI: $[+39.04\%, +46.15\%]$) and $+42.83\%$ (20% budget, 95% CI: $[+40.34\%, +45.78\%]$).
6. **Independent integrity audit passed**: `ccf-integrity-auditor` confirmed all numbers, split counts, regression coefficients, and bootstrap intervals with exact precision (`INTEGRITY_PASS`).

## Why this route failed

The preregistered `RankAugmented` construction did not generalize incrementally beyond the frozen `StrongControl` on held-out Audit patients. The experiment does not identify a unique causal explanation for that failure. Redundancy with the control, weak or absent rank signal, estimator mismatch, and Dev-specific instability remain possible interpretations; none is established as the scientific finding.

The durable finding is therefore limited to the tested representation and estimator:

> The preregistered within-prescription mid-rank feature did not establish reproducible incremental false-positive routing information beyond the frozen strong control.

## What did not fail

- **The strong-control requirement remains valid**: Future candidate selectors must face frozen recommender confidence and candidate-specific trivial confounds. Idea 003 additionally shows a positive `StrongControl - ScoreOnly` interval at the 20% primary budget, while the 10% interval crosses zero.
- **Residual false-positive heterogeneity remains unresolved**:

$$
\boxed{\text{Residual false-positive heterogeneity remains unresolved.}}
$$

- **Oracle headroom is opportunity, not mechanism evidence**: Retrospective Oracle headroom demonstrates outcome heterogeneity not explained by the frozen control. Because Oracle uses the target, it does not prove that this heterogeneity is target-free observable, concentrated in a particular feature space, or learnable by a deployable selector.
- **Other information sources remain untested by this Gate**: The failure is localized to the preregistered within-prescription mid-rank observable. It does not adjudicate other single-visit relational statistics, longitudinal patient history, structural graph information, patient-conditioned evidence, or cross-model evidence.

## Reusable residue

- The frozen `StrongControl` remains the mandatory benchmark for successor candidate selectors unless a later preregistration provides a stronger candidate-specific simple control.
- Within-prescription mid-rank should not be revived by cosmetic rank reparameterization under the same information source.
- A feature's failure conditional on a strong control terminates the tested feature/representation, not the entire information family from which it was drawn.
- The 1,059-patient validation cohort, train-only prevalence extraction, and patient-cluster bootstrap framework remain useful protocol machinery for rapid falsification, subject to the accumulated validation-adaptivity boundary.

## Route boundary

This within-prescription relative confidence route is terminated.

The result must not be generalized into claims that all static observables, medication-set relations, multi-visit temporal history, longitudinal patient recurrence, structural graph embeddings, DDI-derived representations, or cross-model evidence are useless or exhausted.

## Non-revival condition

Changing the rank calculation (for example dense rank, fractional percentile, rank binning, or a nonlinear transform of the same rank) without materially changing the observable information and scientific mechanism does not constitute a new hypothesis.

A future route is scientifically distinct only when it introduces materially different observable evidence, problem formalization, mechanism, baseline, representation, or evidence source and receives its own literature grounding, strongest-simple-control design, and preregistration.

## Evidence boundary

Scoped to the frozen MoleRec checkpoint, validation-only candidate corpus, DDI-active review universe, singleton deletion operator, train-only Laplace prevalence, preregistered low-capacity selector, and frozen budgets. The test split remains untouched. Historical validation has already been used for route selection across Ideas 001--003; future validation-only Audit evidence remains route-selection evidence rather than untouched final generalization evidence.
