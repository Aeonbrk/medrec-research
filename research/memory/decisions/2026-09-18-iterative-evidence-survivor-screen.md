# Iterative evidence survivor screen verdict — 2026-09-18

Date: 2026-09-18
Status: **DECISION ENFORCED: RETURN_TO_ARCHITECTURE_SEARCH_DEPTH_NOT_STABLE**

## Evidence

A bounded, eight-lane 60-epoch survivor-discrimination screen was executed on `mimic-iii-canonical-131-paper-dev-v1` at immutable source revision `82fb054abefe3a4b6560c9a3a2fd8640a32bc944` on the 319 Execution Plane from a clean detached worktree (`/root/zhb/medrec-research-iterative-survivor`).

The screen tested two frozen scientific questions following the evidence-access architecture portfolio:

1. **Q1 (Final-Architecture Resolution Attribution)**: Does code-level evidence resolution remain causally important inside the final multi-hop re-reading computation graph (`reread_code` vs `reread_visit`, canonical seed)?
2. **Q2 (Depth Stability Across Prospective Seeds)**: Is the iterative re-reading gain (`depth_reread` vs `depth_state`) stable across a 4-condition frozen seed set (`canonical` [inherited from prior portfolio `result.json`] + 3 prospective deterministic offsets `stability_1`, `stability_2`, `stability_3`)?

All eight variants ran concurrently across physical GPUs 0–7 and completed all 60 epochs without early stopping or modification. Every lane instantiated exactly 1,295,367 trainable parameters and passed strict matched initialization checks. Preflight confirmed zero state/output numerical divergence (`state_max_abs_diff = 0.0`, `output_max_abs_diff = 0.0`) between `reread_code` and the prior canonical `depth_reread` implementation. Test remained strictly sealed (`test_loaded = false`).

### Question 1: Final-Architecture Resolution Attribution

| Variant | Role | Selected Ckpt / OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI Rate | Avg Med Count |
| :--- | :--- | :---: | ---: | ---: | ---: | ---: | ---: |
| `resolution_visit_canonical` | Control (`reread_visit`) | Ep 8 / 0.35 | 0.536608 | 0.689280 | 0.785254 | 0.074260 | 19.8410 |
| `resolution_code_canonical` | Candidate (`reread_code`) | Ep 4 / 0.35 | 0.551259 | 0.702581 | 0.796649 | 0.071966 | 20.7648 |
| **Delta ($\Delta$)** | **Gain** | — | **+0.014651** | **+0.013301** | **+0.011395** | **-0.002295** | **+0.9238** |

Resolution Attribution Verdict: **`CODE_RESOLUTION_CARRIES_FINAL_ARCHITECTURE`**

- $\Delta \text{Jaccard} = +0.014651 > +0.004000$;
- Supporting guardrails all pass: $\Delta \text{F1} = +0.013301 \ge -0.002$, $\Delta \text{PR-AUC} = +0.011395 \ge -0.002$, $\Delta \text{DDI} = -0.002295 \le +0.002000$.

### Question 2: Four-Condition Depth Stability

| Condition | Source | Control Ckpt / OP (Jaccard) | Candidate Ckpt / OP (Jaccard) | $\Delta$ Jaccard | $\Delta$ F1 | $\Delta$ PR-AUC | $\Delta$ DDI Rate | $\Delta$ Avg Meds |
| :--- | :--- | :---: | :---: | ---: | ---: | ---: | ---: | ---: |
| `canonical` | Prior Portfolio (`result.json`) | Ep 5 / 0.35 (0.547115) | Ep 4 / 0.35 (0.551259) | **+0.004144** | +0.003790 | +0.005406 | -0.000731 | +0.3433 |
| `stability_1` | Survivor Screen (`results.json`) | Ep 4 / 0.35 (0.551534) | Ep 5 / 0.35 (0.550884) | **-0.000650** | -0.000863 | +0.003052 | +0.004964 | +0.1703 |
| `stability_2` | Survivor Screen (`results.json`) | Ep 6 / 0.35 (0.547138) | Ep 6 / 0.35 (0.548502) | **+0.001365** | +0.000824 | +0.002637 | +0.002049 | +1.1524 |
| `stability_3` | Survivor Screen (`results.json`) | Ep 5 / 0.40 (0.546843) | Ep 5 / 0.35 (0.549875) | **+0.003033** | +0.002590 | +0.003085 | +0.002240 | +1.1305 |
| **Mean** | **4 Conditions** | — | — | **+0.001973** | **+0.001585** | **+0.003545** | **+0.002130** | **+0.6991** |

Summary Statistics:

- Positive Jaccard conditions: 3 / 4 (failed 4/4 requirement; `stability_1` is $-0.000650$);
- Material Jaccard conditions ($> +0.002$): 2 / 4 (failed $\ge 3/4$ requirement; only `canonical` at $+0.004144$ and `stability_3` at $+0.003033$ exceed $+0.0020$);
- Mean $\Delta$ Jaccard: $+0.001973$ (failed $> +0.0040$ requirement);
- Median $\Delta$ Jaccard: $+0.002199$;
- Std $\Delta$ Jaccard: $0.002089$;
- Min $\Delta$ Jaccard: $-0.000650$;
- Max $\Delta$ Jaccard: $+0.004144$;
- Mean guardrails pass: `False` (mean $\Delta \text{DDI} = +0.002130$, violating the $\le +0.002000$ guardrail threshold).

Depth Stability Verdict: **`UNSTABLE_DEPTH_REREAD`**

## Scientific Interpretation and Takeaways

1. **Code-level evidence resolution remains decisively supported**: Inside the final multi-hop re-reading computation graph, providing unpooled fine code tokens directly to medication queries delivers a massive $+0.014651$ Jaccard improvement (+1.47%) over within-visit pooling, with clean supporting gains ($\Delta \text{F1} = +0.0133$, $\Delta \text{PRAUC} = +0.0114$) and lower DDI rate ($-0.0023$). Code-level memory resolution is a genuine, structural causal factor.
2. **Iterative re-reading depth is not robust across random seeds**: While the canonical seed showed a $+0.004144$ Jaccard gain, prospective seeds failed the strict stability criteria:
   - In `stability_1` (seeds 1204 / 2049), `depth_state` actually outperformed `depth_reread` (0.551534 vs 0.550884, $\Delta J = -0.000650$) and `depth_reread` suffered higher DDI ($\Delta \text{DDI} = +0.004964$).
   - In `stability_2` (seeds 1205 / 2050), the gain was subthreshold ($\Delta J = +0.001365 < +0.002000$).
   - In `stability_3` (seeds 1206 / 2051), a modest gain was recovered ($\Delta J = +0.003033$), but the mean gain across all 4 conditions was only $+0.001973$, below the $+0.0040$ requirement, with mean $\Delta \text{DDI} = +0.002130$ exceeding safety guardrails.
3. **Implication for Paper Candidate status**: The iterative re-reading mechanism (`depth_reread`) cannot be claimed as a stable, robust architectural contribution on its own without cherry-picking seeds. Because scientific claims must hold up across initialization and data ordering, `depth_reread` fails promotion.

## Enforced Decision and Routing

- **Exact Routing String**: `RETURN_TO_ARCHITECTURE_SEARCH_DEPTH_NOT_STABLE`.
- **Policy Enforcement**:
  - `depth_reread` is NOT promoted to Paper Candidate review.
  - No automatic Test set evaluation is authorized (`test_loaded = false` preserved).
  - No post-hoc tuning, cherry-picked seed selection, learning rate sweeps, or loss function redesign is permitted to rescue depth re-reading.
  - The project returns to architecture search. Future candidate architectures may retain code-level resolution (which is decisively validated), but must search for a more robust inductive bias than simple unconstrained recurrent re-reading.

Artifact: `research/prototypes/iterative-evidence-survivor/result.json`.
