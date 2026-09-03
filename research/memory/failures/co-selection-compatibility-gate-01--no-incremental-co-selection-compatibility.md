<!-- markdownlint-disable MD013 -->

# Failure Record: Co-Selection Compatibility (Gate 01 no incremental co-selection compatibility)

Source boundary: `medrec-research` Idea `004-co-selection-compatibility`, Gate 01 formal run `gate-01-co-selection-compatibility-20260903-154343` on `319-lab` at frozen harness commit `8640ce521a942bd34daa2a5547c2e2db1febca6a`. The independent integrity audit concluded `INTEGRITY_PASS`; the authoritative research decision is `STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY` / `TERMINATE_IDEA_004`.

- **Status**: Historical Memory (this train-only co-selection compatibility route is terminated under the recorded setting; revisit only when materially different observable information, problem formalization, causal/mechanistic claim, baseline, representation, or evidence source changes the hypothesis)

## Failed hypothesis

Among DDI-active medications predicted by frozen MoleRec, train-only frequency-corrected pairwise co-selection compatibility (empirical NPMI) averaged over peer predicted medications contains reproducible incremental false-positive routing information beyond a strong simple control built from absolute medication score $s_t(m)$, predicted prescription size $n_t$, candidate train prevalence $p_{train}(m)$, peer prevalence mean $q_t(m)$, and their score interactions.

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

For each candidate, the mean co-selection compatibility $A_t(m)$ was computed over peer predicted medications:

$$
A_t(m) = \frac{1}{|\hat M_t \setminus \{m\}|} \sum_{j \in \hat M_t \setminus \{m\}} \text{NPMI}_{train}(m, j),
$$

where empirical Normalized Pointwise Mutual Information (NPMI) was computed on the 6,256 train visits with exact boundary values $-1$ for $C(m, j)=0$ and $+1$ for $C(m, j)=V_{train}$.

The full 1,059-patient validation cohort was partitioned into a deterministic patient-disjoint Dev set (529 patients, 7,762 candidates) and Audit set (530 patients, 7,787 candidates) with seed `2004`.

Dev-only ridge linear probability models ($\lambda = 10^{-6}$, unpenalized intercept) were fit for:

- `StrongControl`: $[u, c, f, g, u \cdot c, u \cdot f, u \cdot g]$ where $u = 1 - s$, $c = \log(1 + n_t)$, $f = \text{logit}(p_{train})$, $g = \text{logit}(q_t)$.
- `CoSelectionAugmented`: $[u, c, f, g, u \cdot c, u \cdot f, u \cdot g, A_t(m)]$.

Audit candidates were evaluated at 10% ($k=778$), 20% ($k=1,557$), and 30% ($k=2,336$) review budgets, with patient-clustered bootstrap uncertainty (1,000 replicates, seed `1204`).

## What was observed

1. **Preregistered split and Dev-only fitting held strictly**: 7,762 Dev candidates from 432 eligible patients, 7,787 Audit candidates from 426 eligible patients; zero patient overlap between partitions; test split untouched.
2. **`StrongControl` versus `ScoreOnly`**:
   - 10% budget: 61.57% vs 61.57% (0.00%, 95% CI: [-1.80%, +1.66%])
   - 20% budget: 59.54% vs 58.38% (+1.16%, 95% CI: [+0.14%, +2.07%])
   The control improvement is statistically supported at the 20% primary budget, replicating the finding from Idea 003 that prevalence and size signals refine scores at broader review depths.
3. **`CoSelectionAugmented` failed to provide incremental signal over `StrongControl`**:
   - 10% budget: 62.34% vs 61.57% (+0.77%, 95% CI: [-1.16%, +2.50%])
   - 20% budget: 59.60% vs 59.54% (+0.06%, 95% CI: [-0.68%, +0.78%])
   - 30% budget: 55.99% vs 56.81% (-0.81%, 95% CI: [-1.18%, -0.04%])
4. **Gate C failed at both primary budgets**: the lower 95% confidence bounds for `CoSelectionAugmented - StrongControl` were $-1.16\%$ and $-0.68\%$, so the preregistered PASS condition was not met. Both intervals cross zero.
5. **Residual retrospective outcome heterogeneity remained large**: `Oracle - StrongControl` was $+38.43\%$ (10% budget, 95% CI: $[+33.87\%, +42.93\%]$) and $+40.46\%$ (20% budget, 95% CI: $[+37.18\%, +43.61\%]$).
6. **Independent integrity audit passed**: `ccf-integrity-auditor` confirmed all numbers, split counts, regression coefficients, and bootstrap intervals with exact precision (`INTEGRITY_PASS`).

## Why this route failed

The preregistered `CoSelectionAugmented` construction did not generalize incrementally beyond the frozen `StrongControl` on held-out Audit patients. The experiment does not identify a unique causal explanation for that failure. Pair co-selection sparsity in the training set, linear probability formulation of set compatibility, representation limits of scalar NPMI averaging, or genuine absence of incremental relational signal relative to strong control remain potential factors; none is established as the sole scientific mechanism.

The durable finding is therefore limited to the tested representation and estimator:

> The preregistered train-only co-selection compatibility observable did not establish reproducible incremental false-positive routing information beyond the frozen strong control.

## What did not fail

- **The strong-control requirement remains valid**: Future candidate selectors must face frozen recommender confidence, prescription size, candidate prevalence, and peer prevalence. Strong control again showed positive incremental headroom over score alone at 20% budget.
- **Residual false-positive heterogeneity remains unresolved**:

$$
\boxed{\text{Residual false-positive heterogeneity remains unresolved.}}
$$

- **Oracle headroom is opportunity, not mechanism evidence**: Retrospective Oracle headroom demonstrates outcome heterogeneity not explained by the frozen control. Because Oracle uses the target, it does not prove that this heterogeneity is target-free observable, concentrated in a particular feature space, or learnable by a deployable selector.
- **Other information sources remain untested by this Gate**: The failure is localized to the preregistered one-scalar train-only empirical NPMI co-selection compatibility observable. It does not adjudicate multi-visit longitudinal patient history, structural graph information, patient-conditioned clinical covariates, or cross-model consensus.

## Reusable residue

- The frozen `StrongControl` ($u, c, f, g, u \cdot c, u \cdot f, u \cdot g$) remains the mandatory benchmark for successor candidate selectors unless a later preregistration provides a stronger candidate-specific simple control.
- Train-only empirical NPMI averaging should not be revived by cosmetic reparameterization (e.g. PMI thresholds, smoothing variations) under the same information source.
- A feature's failure conditional on a strong control terminates the tested feature/representation, not the entire information family from which it was drawn.

## Route boundary

This train-only co-selection compatibility route is terminated.

The result must not be generalized into claims that all static observables, multi-visit temporal history, longitudinal patient recurrence, structural graph embeddings, DDI-derived representations, or cross-model evidence are useless or exhausted.

## Non-revival condition

Changing the co-selection calculation (for example positive PMI, raw co-occurrence, lift, Jaccard, or embedding cosine similarity) without materially changing the observable information and scientific mechanism does not constitute a new hypothesis.

A future route is scientifically distinct only when it introduces materially different observable evidence, problem formalization, mechanism, baseline, representation, or evidence source and receives its own literature grounding, strongest-simple-control design, and preregistration.
