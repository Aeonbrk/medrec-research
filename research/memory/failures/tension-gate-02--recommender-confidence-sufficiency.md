<!-- markdownlint-disable MD013 -->

# Failure Record: Tension-guided verification (Gate 02 confidence sufficiency)

Source boundary: `medrec-research` Idea `001-tension-guided-verification`, Gate 02 formal run `gate-02-confidence-sufficiency-20260902-155433` on `319-wild` at harness commit `ef40f288fbf64f499d3f9967a7b2783ee3fe090b`. Public summary SHA256: `9f0e54ff484de7e935f62300e5a0016ed2042eb052ae8dcb86b2f7c3bd844e28`.

- **Status**: Historical Memory (Current route terminated under recorded setting; revisit only if a materially different assumption, evidence source, problem formulation, baseline, or mechanism changes the failure condition)

## Decision

The current Tension route under Idea 001 is terminated (`TERMINATE_CURRENT_TENSION_ROUTE`). The empirical evidence does not support the hypothesis that external constraint pressure (measured via active DDI degree or support-pressure interaction) provides incremental selective routing information over the base recommender's own confidence scores under fixed singleton deletion $R_0$.

## What was tested

Under the frozen MoleRec validation setting, review universe $\mathcal Q$ ($d_t(m) > 0$), and singleton deletion operator $R_0$, Gate 02 tested whether target-free observable constraint signals could identify false-positive medications beyond the base recommender's predicted probabilities ($s_t(m)$). Evaluated policies and diagnostics included:

1. **ScoreOnly**: Sorting candidates by ascending recommender confidence $s_t(m) \uparrow$ (strongest simple control).
2. **Scalar Control $R_\lambda$**: Global additive linear combination $r_{t,m}(\lambda) = s_t(m) - \lambda \cdot (d_t(m) / D_{\max})$, with $\lambda^*$ tuned on a patient-disjoint Dev split ($N=430$ patients).
3. **Tension Interaction Diagnostic $I_{\text{Tension}}$**: $2 \times 2$ difference-in-differences over high/low score ($s_t(m) \ge \tau_s$) and high/low DDI degree ($d_t(m) \ge \tau_d$).

## Why it failed

1. **Strongest simple control was highly predictive**: MoleRec confidence alone achieved **61.13%** Pareto-beneficial yield at 10% review budget and **58.52%** at 20% budget on the Audit partition ($N=428$ patients, 7,959 candidates), substantially beating Random (31.03%) and RiskOnly (36.48% at 10%, 35.76% at 20%).
2. **Dev scalar tuning selected zero constraint weight**: Grid search over 13 values on Dev selected $\lambda^* = 0.0$. Consequently, on Audit, the scalar policy collapsed identically to ScoreOnly:
   $$\text{Scalar} - \text{ScoreOnly} = 0.0\% \quad (95\%\ \text{CI: } [0.0\%, 0.0\%]) \quad \text{across all budgets}.$$
   Adding active DDI degree contributed zero incremental predictive signal.
3. **Interaction diagnostic rejected super-additive tension**:
   $$I_{\text{Tension}} = -0.005237 \quad (95\%\ \text{CI: } [-0.04575, +0.03645]),$$
   evaluated across four populated cells ($>400$ patients per cell). The interval is centered near zero and spans negative values, demonstrating no positive interaction between predictive support and constraint pressure.
4. **Independent reproduction**: The P5 integrity audit independently reproduced the `STOP_NO_INCREMENTAL_CONSTRAINT_SIGNAL` verdict with zero numeric discrepancy.

## What did not fail

- **Selective routing opportunity exists**: Gate 01 established that substantial retrospective revision headroom exists under $R_0$ (Oracle achieved 100.0% Pareto-beneficial yield, +68.33% over Random).
- **Usefulness of recommender confidence**: MoleRec's own confidence is a valid, strong simple signal for candidate revision triage.
- **Residual Oracle headroom survives**: Oracle outperforms ScoreOnly by **+38.87%** at 10% budget (95% CI: [35.43%, 42.61%]) and **+41.48%** at 20% budget (95% CI: [39.00%, 44.40%]). Model confidence does not exhaust routing headroom.
- **DDI information in other contexts**: This result does not prove all DDI-derived representations are useless or that DDI cannot assist other tasks; it falsifies the specific claim that active DDI degree provides incremental false-positive signal over confidence under $R_0$.

## Reusable residue

- A strict two-stage gate methodology: separating existence of routing headroom (Gate 01) from attribution to proposed mechanisms over strong simple controls (Gate 02).
- A rigorous Dev/Audit patient-disjoint partition protocol for tuning post-hoc selector parameters without test leakage.
- A fail-closed, patient-clustered bootstrap inference suite invariant to patient identifiers.
- Recommender output confidence established as an indispensable, mandatory baseline control for any future selective revision or routing policy.

## Non-revival boundary

Do not attempt to revive this route by post-hoc manipulation:

- Expanding or shifting the $\lambda$ grid.
- Modifying budget levels or score quantiles.
- Applying alternative nonlinear or logarithmic transforms to DDI degree.
- Adding complex neural selectors (MLPs, GNNs) on the same feature set.

A new route may only be considered if a genuinely different scientific foundation (problem formulation, external evidence source, causal hypothesis, or candidate/action semantics) changes the premise.

## Uncertainty

The failure is strictly scoped to the frozen MoleRec checkpoint, validation cohort, candidate review universe ($d_t(m) > 0$), and singleton deletion operator $R_0$. It does not establish that decision tension is universally nonexistent across all clinical AI domains, but it conclusively bounds this research route within the project scope.
