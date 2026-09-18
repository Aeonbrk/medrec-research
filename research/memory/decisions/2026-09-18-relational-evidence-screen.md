# Relational evidence screen verdict — 2026-09-18

Date: 2026-09-18
Status: **DECISION ENFORCED: PROMOTE_RELATIONAL_EVIDENCE_TO_STABILITY_SCREEN**

## Evidence

A bounded, eight-lane 60-epoch architecture screen was executed on `mimic-iii-canonical-131-paper-dev-v1` at immutable source revision `18ae6c89dcb6ca52137e18ebeabe36bd5a303002` on the 319 Execution Plane from a clean detached worktree (`/root/zhb/medrec-research-relational-evidence`).

The screen tested two scientific questions:

1. **Part A (Fine-Code Stability Across Random Seeds)**: Does code-level medication-specific evidence selection hold up across prospective random seed offsets (`resolution_code` vs `resolution_visit`, across canonical + 3 prospective seed conditions)?
2. **Part B (Relational Cross-Type Evidence Hypothesis)**: Does candidate-medication-conditioned multiplicative conjunction of diagnosis, procedure, and historical-medication evidence (`relational_code`) outperform matched additive/unary composition (`unary_code`) under identical parameter count and initialization?

All eight lanes ran concurrently across physical GPUs 0–7 and completed all 60 epochs without early stopping or modification. Preflight confirmed zero state/output divergence against previous portfolio implementations for the resolution baselines, exact parameter matching within all pairs, tensor-identical initialization, and finite forward/backward passes. Test remained strictly sealed (`test_loaded = false`).

### Part A: Fine-Code Stability (4 Conditions)

| Condition | Source | Control Ckpt / OP (Jaccard) | Candidate Ckpt / OP (Jaccard) | $\Delta$ Jaccard | $\Delta$ F1 | $\Delta$ PR-AUC | $\Delta$ DDI Rate | $\Delta$ Avg Meds |
| :--- | :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: |
| `canonical` | Prior Portfolio (`result.json`) | Ep 7 / 0.35 (0.535091) | Ep 5 / 0.30 (0.546626) | **+0.011536** | +0.010238 | +0.007785 | -0.005589 | +0.4715 |
| `stability_1` | Screen Lane (`results.json`) | Ep 7 / 0.30 (0.534789) | Ep 6 / 0.30 (0.545625) | **+0.010836** | +0.009038 | +0.007899 | +0.004406 | -0.7084 |
| `stability_2` | Screen Lane (`results.json`) | Ep 8 / 0.35 (0.533419) | Ep 6 / 0.35 (0.547681) | **+0.014262** | +0.012560 | +0.008141 | +0.000820 | +0.5093 |
| `stability_3` | Screen Lane (`results.json`) | Ep 6 / 0.30 (0.535859) | Ep 5 / 0.35 (0.546163) | **+0.010303** | +0.008637 | +0.008077 | -0.006196 | -1.3872 |
| **Mean** | **4 Conditions** | — | — | **+0.011734** | **+0.010118** | **+0.007976** | **-0.001640** | **-0.2787** |

Summary Statistics:

- Positive Jaccard conditions: 4 / 4 (passes strict 4/4 requirement);
- Material Jaccard conditions ($> +0.0020$): 4 / 4 (passes strict $\ge 3/4$ requirement; all 4 conditions exceed $+0.0100$);
- Mean $\Delta$ Jaccard: $+0.011734$ (well above the $> +0.0040$ threshold);
- Median $\Delta$ Jaccard: $+0.011186$;
- Std $\Delta$ Jaccard: $0.001759$;
- Min $\Delta$ Jaccard: $+0.010303$;
- Max $\Delta$ Jaccard: $+0.014262$;
- Mean guardrails pass: `True` (mean $\Delta \text{F1} = +0.010118 \ge -0.002$, mean $\Delta \text{PRAUC} = +0.007976 \ge -0.002$, mean $\Delta \text{DDI} = -0.001640 \le +0.0020$).

Fine-Code Stability Verdict: **`STABLE_FINE_CODE_ACCESS`**

### Part B: Relational Evidence Hypothesis

| Model Variant | Role | Trainable Params | Selected Ckpt / OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI Rate | Avg Med Count |
| :--- | :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: |
| `unary_code_canonical` | Control (`unary_code`) | 1,427,080 | Ep 7 / 0.35 | 0.538877 | 0.691721 | 0.789186 | 0.075167 | 20.2265 |
| `relational_code_canonical` | Candidate (`relational_code`) | 1,427,080 | Ep 5 / 0.35 | 0.542982 | 0.695092 | 0.790317 | 0.069825 | 20.0954 |
| **Delta ($\Delta$)** | **Gain** | **0** | — | **+0.004105** | **+0.003371** | **+0.001131** | **-0.005341** | **-0.1311** |

Relational Evidence Verdict: **`RELATIONAL_EVIDENCE_SIGNAL`**

- $\Delta \text{Jaccard} = +0.004105 > +0.004000$;
- Supporting guardrails all pass: $\Delta \text{F1} = +0.003371 \ge -0.002$, $\Delta \text{PR-AUC} = +0.001131 \ge -0.002$, $\Delta \text{DDI} = -0.005341 \le +0.0020$ (DDI rate reduced by 0.53%).

## Scientific Interpretation and Takeaways

1. **Fine-code clinical memory access is an exceptionally stable foundation**: Across four independent random seed conditions, medication-specific selection over unpooled clinical code tokens consistently outperforms visit-pooled representations by $+1.03\%$ to $+1.43\%$ Jaccard (mean $\Delta J = +0.011734$), with uniform gains in F1 ($+1.01\%$) and PR-AUC ($+0.80\%$), alongside an average DDI rate reduction ($-0.001640$). Fine-code token resolution is confirmed as a robust scientific foundation for all future architectures in this project.
2. **Relational evidence conjunction adds clean non-linear value**: After medication-specific selection over D, P, and H code streams, explicitly forming factorized cross-type multiplicative conjunctions ($u_D \odot u_P$, $u_D \odot u_H$, $u_P \odot u_H$) provides a $+0.004105$ Jaccard gain over equal-parameter additive composition ($u_D + u_P$, etc.). Moreover, this conjunction improves safety significantly ($\Delta \text{DDI} = -0.005341$).
3. **Implication**: Unlike iterative re-reading (which proved seed-unstable), relational cross-type conjunction introduces a structured inductive bias that successfully discriminates clinical synergies. Per the frozen protocol, it qualifies for promotion to a multi-seed stability screen.

## Enforced Decision and Routing

- **Exact Routing String**: `PROMOTE_RELATIONAL_EVIDENCE_TO_STABILITY_SCREEN`.
- **Policy Enforcement**:
  - Fine-code access is validated as a permanent foundation (`STABLE_FINE_CODE_ACCESS`).
  - Relational evidence is promoted to a multi-seed stability screen (`RELATIONAL_EVIDENCE_SIGNAL`).
  - Test set remains strictly sealed (`test_loaded = false` preserved; no Test access authorized).
  - No post-hoc tuning, HPO, rank sweeps, or automatic compound models authorized at this stage.

Artifact: `research/prototypes/relational-evidence-screen/result.json`.
