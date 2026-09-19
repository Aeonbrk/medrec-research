# MSED Evidence-Distribution Screen Verdict — 2026-09-19

Date: 2026-09-19  
Status: **DECISION_RECORDED_HYPOTHESIS_FALSIFIED**  
Routing: `KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS`

## Context and Hypothesis

Following the falsification of modality-specific normalization decoupling in the MHEF screen, the project investigated the unresolved structural clue from `PredictionLocal` (`+0.012976` Jaccard over its matched aggregate control). Exact code inspection established that the key difference between `PredictionAggregate` and `PredictionLocal` was the aggregation of medication-token local support potentials: arithmetic mean versus normalized log-sum-exp (`logmeanexp`).

> *Hypothesis:* For each candidate medication, the complete empirical distribution of longitudinal FineCode support potentials carries decision information beyond a single point statistic (`logmeanexp`).

The Medication-Specific Evidence Distribution (MSED) screen evaluated this hypothesis with a bounded characteristic spectrum representation of the empirical support distribution under the pre-registered protocol in `research/memory/decisions/2026-09-19-msed-evidence-distribution-screen-design.md` and `research/prototypes/msed-evidence-distribution-screen/README.md`.

## Execution Facts

- **Execution plane:** 319 Execution Plane (8 physical NVIDIA RTX 3090 GPUs, persistence mode active).
- **Frozen revision:** `e54d3d5a2a5145d14beadb109d574ad82efdae9e`.
- **Preflight:** Verified CUDA availability, zero target leakage, exact parameter count match across all six MSED variants (1,363,465 parameters each), exact FineCode global context preservation (`global_context_max_abs_diff = 0.0`), exact PredictionLocal raw local score preservation (`raw_local_scores_max_abs_diff = 0.0`), exact PredictionLocal LME preservation (`raw_lme_max_abs_diff = 0.0`), finite forward/backward/no-history execution, and zero Test access (`test_loaded = false`). Output: `PASS`.
- **Training protocol:** Full 30 epochs per lane without early stopping, evaluating on the complete Dev set every epoch under canonical RNG (torch/cuda/python=1203, numpy=2048).
- **Horizon censoring check:** All eight lanes selected their best Dev checkpoint between Epoch 3 and 8 (`safe_selected_epoch_max = 25 >= 8`). Zero horizon censoring occurred; no 60-epoch extension was triggered.
- **Evaluation surface:** `mimic-iii-canonical-131-paper-dev-v1`. Test set remained completely sealed (`test_loaded = false`).

## Empirical Results

### Completed 30-Epoch Lanes

| Lane | GPU | Params | Epochs | Best Ep | Best OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI | Avg Med |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `msed_ecf_global` | 0 | 1,363,465 | 30 | 8 | 0.35 | 0.546806 | 0.698507 | 0.793325 | 0.076335 | 20.11 |
| `point_lme_global` | 1 | 1,363,465 | 30 | 8 | 0.35 | 0.546180 | 0.698087 | 0.792862 | 0.076761 | 20.36 |
| `point_mean_global` | 2 | 1,363,465 | 30 | 7 | 0.35 | 0.546378 | 0.698442 | 0.791671 | 0.077119 | 21.14 |
| `point_max_global` | 3 | 1,363,465 | 30 | 8 | 0.35 | 0.546652 | 0.698253 | 0.793283 | 0.074867 | 20.15 |
| `msed_ecf_only` | 4 | 1,363,465 | 30 | 8 | 0.35 | 0.530734 | 0.684700 | 0.777805 | 0.071420 | 21.17 |
| `point_lme_only` | 5 | 1,363,465 | 30 | 5 | 0.30 | 0.534433 | 0.687944 | 0.780670 | 0.076338 | 21.85 |
| `prediction_local_anchor` | 6 | 1,295,367 | 30 | 3 | 0.35 | 0.548911 | 0.700462 | 0.794832 | 0.075148 | 19.96 |
| `foundation_code_anchor` | 7 | 1,295,367 | 30 | 5 | 0.30 | 0.546626 | 0.698386 | 0.792678 | 0.071069 | 21.43 |

### Matched Comparisons and Verdicts

| Comparison | Candidate | Control | Δ Jaccard | Δ F1 | Δ PR-AUC | Δ DDI | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `distribution_beyond_lme_global` | `msed_ecf_global` | `point_lme_global` | +0.000626 | +0.000421 | +0.000463 | -0.000427 | `KILL_NO_MATERIAL_SIGNAL` |
| `distribution_beyond_lme_only` | `msed_ecf_only` | `point_lme_only` | -0.003699 | -0.003243 | -0.002865 | -0.004918 | `KILL_NO_MATERIAL_SIGNAL` |
| `distribution_vs_mean_global` | `msed_ecf_global` | `point_mean_global` | +0.000428 | +0.000065 | +0.001654 | -0.000784 | `KILL_NO_MATERIAL_SIGNAL` |
| `distribution_vs_max_global` | `msed_ecf_global` | `point_max_global` | +0.000154 | +0.000254 | +0.000042 | +0.001468 | `KILL_NO_MATERIAL_SIGNAL` |
| `global_complement` | `msed_ecf_global` | `msed_ecf_only` | +0.016072 | +0.013807 | +0.015520 | +0.004915 | `SIGNAL_WITH_SUPPORTING_METRIC_COST` |

### Historical Anchor Reproductions

- `prediction_local_anchor`: Reproduced historical evaluation with exactly 0.0 absolute difference across all five metrics (Jaccard, F1, PR-AUC, DDI rate, Average Medication Count).
- `foundation_code_anchor`: Reproduced historical evaluation with exactly 0.0 absolute difference across all five metrics.

## Attribution and Causal Analysis

1. **Distribution shape yields no material signal beyond scalar LME:** The primary decisive comparison (`msed_ecf_global` vs `point_lme_global`) isolates the difference between the empirical characteristic spectrum $E_i[\phi(r_{mi})]$ and the point spectrum $\phi(\text{LME}_m)$ on top of identical global context and scalar LME features. The observed lift is $\Delta J = +0.000626$ (+0.063 pp), which falls well below the pre-registered material signal threshold of $+0.0020$.
2. **Distribution representation degrades performance in isolation:** In the absence of the global FineCode context (`msed_ecf_only` vs `point_lme_only`), encoding the distribution via characteristic spectrum yields $\Delta J = -0.003699$ (-0.370 pp), showing that the distribution spectrum actually loses decision value compared to the scalar LME point summary.
3. **No advantage over simple mean or max point controls:** The full candidate `msed_ecf_global` shows virtually identical performance to simple mean point control (`point_mean_global`, $\Delta J = +0.000428$) and hard max point control (`point_max_global`, $\Delta J = +0.000154$).
4. **Candidate fails absolute benchmark gates:** `msed_ecf_global` achieves Dev Jaccard 0.546806, which is essentially identical to base `foundation_code` ($0.546626$, $\Delta J = +0.000179$), while falling substantially below `prediction_local_anchor` ($0.548911$, $\Delta J = -0.002105$), `summary_add` ($0.549611$, $\Delta J = -0.002805$), and `wide_global_add` ($0.549980$, $\Delta J = -0.003174$).
5. **No horizon censoring:** Best checkpoints were selected at Epochs 3 to 8, with flat or declining performance thereafter, firmly establishing that training horizon was sufficient.

## Decision and Routing

- **Verdict:** **`KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS`**.
- Multi-seed stability is **NOT** authorized.
- MIMIC-IV replication is **NOT** authorized.
- Test set access remains **SEALED**.
- No post-hoc hyperparameter tuning (frequency sweeps, kernel bandwidths, score scale adjustments, loss weight sweeps) is permitted.
- The project terminates the distribution-shape hypothesis and resets the architecture search around the next orthogonal mechanism.
