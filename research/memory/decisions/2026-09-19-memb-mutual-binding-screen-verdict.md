# MEMB Mutual-Binding Family Screen Verdict — 2026-09-19

Date: 2026-09-19  
Status: **DECISION_RECORDED_HYPOTHESIS_FALSIFIED**  
Routing: `KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY`

## Context and Hypothesis

Following the falsification of support-distribution shape in MSED, the project evaluated an orthogonal architectural question: whether evidence should be weighted by its specificity to one candidate medication relative to competing medication identities before evidence aggregation. In the standard FineCode formulation, each medication independently queries clinical evidence, potentially allowing generic, non-discriminative tokens to support many medications simultaneously.

> *Hypothesis:* For raw medication–evidence affinity $S[m,i]$ (or local support potential $r[m,i]$), penalizing evidence commonness $c_i = \text{logsumexp}_n S[n,i] - \log(M)$ before aggregation improves medication recommendation quality.

The screen evaluated this hypothesis at two score scales across both the global FineCode read and the PredictionLocal read, using the exact historical PortfolioModel parameter graph (zero added parameters) under the frozen design recorded in `research/memory/decisions/2026-09-19-memb-mutual-binding-screen-design.md`.

## Execution Facts

- **Execution plane:** 319 Execution Plane (8 physical NVIDIA RTX 3090 GPUs, persistence mode active).
- **Frozen revision:** `f1f74e5eb143f49a2bac73d81a13c42f33f4a4a2`.
- **Preflight:** Verified CUDA availability, zero target leakage, exact parameter count match across all eight lanes (1,295,367 parameters each), exact raw code affinity preservation (`0.0` max abs diff), exact raw local potential preservation (`0.0` max abs diff), exact historical anchor reproduction (`0.0` error), finite forward/backward/no-history execution, and zero Test access (`test_loaded = false`). Output: `PASS`.
- **Training protocol:** Full 30 epochs per lane without early stopping, evaluating on the complete Dev set every epoch under canonical RNG (`torch/cuda/python=1203`, `numpy=2048`).
- **Horizon censoring check:** All eight lanes selected their best Dev checkpoint between Epochs 3 and 7 (`safe_selected_epoch_max = 25 >= 7`). Zero horizon censoring occurred; no 60-epoch extension was indicated.
- **Evaluation surface:** `mimic-iii-canonical-131-paper-dev-v1`. Test set remained completely sealed (`test_loaded = false`).

## Empirical Results

### Completed 30-Epoch Lanes

| Lane | GPU | Params | Epochs | Best Ep | Best OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI | Avg Med |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mutual_code` | 0 | 1,295,367 | 30 | 7 | 0.35 | 0.542110 | 0.694402 | 0.785345 | 0.076355 | 21.17 |
| `scale2_code` | 1 | 1,295,367 | 30 | 5 | 0.30 | 0.540015 | 0.693071 | 0.785565 | 0.071793 | 21.47 |
| `specificity_code` | 2 | 1,295,367 | 30 | 5 | 0.30 | 0.547125 | 0.698713 | 0.793489 | 0.071194 | 21.26 |
| `foundation_code_anchor` | 3 | 1,295,367 | 30 | 5 | 0.30 | 0.546626 | 0.698386 | 0.792678 | 0.071069 | 21.43 |
| `mutual_local` | 4 | 1,295,367 | 30 | 5 | 0.35 | 0.547092 | 0.698671 | 0.794902 | 0.067738 | 20.92 |
| `scale2_local` | 5 | 1,295,367 | 30 | 5 | 0.35 | 0.548099 | 0.699482 | 0.795203 | 0.068090 | 21.20 |
| `specificity_local` | 6 | 1,295,367 | 30 | 5 | 0.30 | 0.548141 | 0.699645 | 0.795108 | 0.070112 | 21.37 |
| `prediction_local_anchor` | 7 | 1,295,367 | 30 | 3 | 0.35 | 0.548911 | 0.700462 | 0.794832 | 0.075148 | 19.96 |

### Pre-Registered Commonness Comparisons

| Comparison | Candidate | Control | Δ Jaccard | Δ F1 | Δ PR-AUC | Δ DDI | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `code_commonness_scale1` | `specificity_code` | `foundation_code_anchor` | +0.000499 | +0.000327 | +0.000811 | +0.000126 | `KILL_NO_MATERIAL_SIGNAL` |
| `code_commonness_scale2` | `mutual_code` | `scale2_code` | +0.002095 | +0.001332 | -0.000220 | +0.004562 | `WEAK_STOP` |
| `local_commonness_scale1` | `specificity_local` | `prediction_local_anchor` | -0.000770 | -0.000817 | +0.000276 | -0.005036 | `KILL_NO_MATERIAL_SIGNAL` |
| `local_commonness_scale2` | `mutual_local` | `scale2_local` | -0.001007 | -0.000811 | -0.000301 | -0.000351 | `KILL_NO_MATERIAL_SIGNAL` |

### Sharpening Diagnostics

| Comparison | Candidate | Control | Δ Jaccard | Δ F1 | Δ PR-AUC | Δ DDI |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| `code_sharpening` | `scale2_code` | `foundation_code_anchor` | -0.006611 | -0.005315 | -0.007113 | +0.000724 |
| `local_sharpening` | `scale2_local` | `prediction_local_anchor` | -0.000811 | -0.000980 | +0.000371 | -0.007058 |

### Historical Anchor Reproductions

- `foundation_code_anchor`: Exactly 0.0 absolute difference across all five metrics.
- `prediction_local_anchor`: Exactly 0.0 absolute difference across all five metrics.

## Attribution and Causal Analysis

1. **Commonness penalty provides no material gain at scale 1:** Without score sharpening, subtracting the evidence commonness penalty $c_i$ yields $\Delta J = +0.000499$ (+0.050 pp) on the global FineCode read (`specificity_code`) and $\Delta J = -0.000770$ (-0.077 pp) on the local PredictionLocal read (`specificity_local`). Both fail the pre-registered $+0.0020$ material threshold.
2. **Mutual matching gain at scale 2 is an artifact of severe sharpening degradation:** While `mutual_code` shows a nominal gain of $+0.002095$ over `scale2_code`, this is entirely driven by the catastrophic $-0.006611$ collapse caused by scale-2 score sharpening (`scale2_code` Jaccard drops from $0.546626$ to $0.540015$). `mutual_code` ($0.542110$) only partially mitigates this destruction, remaining $-0.004516$ below the original base model `foundation_code_anchor`, while incurring an unacceptable DDI safety penalty of $+0.004562$.
3. **Local mutual matching is uniformly negative:** Under normalized log-sum-exp aggregation, mutual local competition (`mutual_local`) underperforms its matched scale-2 control (`scale2_local`) by $\Delta J = -0.001007$ and trails the historical anchor `prediction_local_anchor` by $-0.001819$.
4. **Pareto safety gate not reached:** While `specificity_local` lowers the DDI rate by $-0.005036$ (from $0.0751$ to $0.0701$), it falls short of the pre-registered Pareto gate of $\Delta \text{DDI} \le -0.010$.
5. **Candidate models trail reference baselines:** Every candidate lane falls below the strong reference control `wide_global_add` ($0.549980$) and prior best architecture `summary_add` ($0.549611$).

## Decision and Routing

- **Verdict:** **`KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY`**.
- Multi-seed stability is **NOT** authorized.
- MIMIC-IV replication is **NOT** authorized.
- Test set access remains **SEALED**.
- No post-hoc hyperparameter tuning (temperatures, score exponents, top-k competition, Sinkhorn iterations, OT marginals, sparse activations, or rerankers) is permitted.
- The project terminates the medication-evidence mutual competition family in this formulation and resets the architecture search around the next orthogonal mechanism.
