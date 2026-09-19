# MHEF Normalization-Domain Screen Verdict — 2026-09-19

Date: 2026-09-19  
Status: **DECISION_RECORDED_HYPOTHESIS_FALSIFIED**  
Routing: `KILL_MHEF_NORMALIZATION_HYPOTHESIS`

## Context and Hypothesis

Following the falsification of dense combinatorial code pairs in the final relational architecture search, the project tested whether the bottleneck in the FineCode foundation was the zero-sum cross-modality attention budget:

> *Hypothesis:* Diagnosis ($D$), procedure ($P$), and historical medication ($H$) evidence should decouple from a shared softmax normalization budget into independent candidate-medication-specific budgets before medication-level prediction.

The model family was evaluated under the design recorded in `research/memory/decisions/2026-09-19-mhef-normalization-screen-design.md`.

## Execution Facts

- **Execution plane:** 319 Execution Plane (8 physical NVIDIA RTX 3090 GPUs, persistence mode active).
- **Frozen revision:** `4584f8a0d080f4300f9ba5778da08f7f82cdc805`.
- **Preflight:** Verified CUDA availability, zero data leakage, exact initialization and parameter match across all 8 variants (1,476,874 parameters each), and exact FineCode foundation global path equivalence (`shared_initialization_max_abs_diff = 0.0`, `global_context_max_abs_diff = 9.5367e-07` within float32 precision). Output: `PASS`.
- **Training protocol:** Full 30 epochs per lane without early stopping, evaluating on complete Dev set every epoch.
- **Horizon censoring check:** All 8 lanes selected their best Dev checkpoint at Epoch 5 (`safe_selected_epoch_max = 25 >= 5`). No horizon-censoring extension to 60 epochs was triggered.
- **Evaluation surface:** `mimic-iii-canonical-131-paper-dev-v1`. Test set remained completely sealed (`test_loaded = false`).

## Empirical Results

### Completed 30-Epoch Lanes

| Lane | GPU | Params | Epochs | Best Ep | Best OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI | Avg Med |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mhef_independent_add` | 0 | 1,476,874 | 30 | 5 | 0.30 | 0.549397 | 0.700657 | 0.794860 | 0.072165 | 21.58 |
| `coupled_budget_add` | 1 | 1,476,874 | 30 | 5 | 0.30 | 0.547986 | 0.699394 | 0.793084 | 0.071378 | 21.05 |
| `wide_global_add` | 2 | 1,476,874 | 30 | 5 | 0.30 | **0.549980** | 0.701313 | 0.794769 | 0.072489 | 21.59 |
| `mhef_independent_concat` | 3 | 1,476,874 | 30 | 5 | 0.30 | 0.545593 | 0.697693 | 0.794941 | 0.073200 | 21.67 |
| `coupled_budget_concat` | 4 | 1,476,874 | 30 | 5 | 0.35 | 0.545500 | 0.697330 | 0.793394 | 0.070904 | 20.25 |
| `private_only_add` | 5 | 1,476,874 | 30 | 5 | 0.30 | 0.547128 | 0.698678 | 0.792935 | 0.072477 | 21.32 |
| `hash_partition_a_add` | 6 | 1,476,874 | 30 | 5 | 0.35 | 0.544909 | 0.696626 | 0.793541 | 0.071163 | 20.33 |
| `hash_partition_b_add` | 7 | 1,476,874 | 30 | 5 | 0.35 | 0.544926 | 0.696638 | 0.793559 | 0.071163 | 20.33 |

### Matched Comparisons and Verdicts

| Comparison | Candidate | Control | Δ Jaccard | Δ F1 | Δ PR-AUC | Δ DDI | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `normalization_add` | `mhef_independent_add` | `coupled_budget_add` | +0.001410 | +0.001263 | +0.001776 | +0.000787 | `KILL_NO_MATERIAL_SIGNAL` |
| `capacity_wide_global` | `mhef_independent_add` | `wide_global_add` | -0.000583 | -0.000656 | +0.000091 | -0.000324 | `KILL_NO_MATERIAL_SIGNAL` |
| `normalization_concat` | `mhef_independent_concat` | `coupled_budget_concat` | +0.000093 | +0.000363 | +0.001547 | +0.002296 | `KILL_NO_MATERIAL_SIGNAL` |
| `global_complement` | `mhef_independent_add` | `private_only_add` | +0.002269 | +0.001979 | +0.001926 | -0.000312 | `WEAK_STOP` |
| `semantic_partition_a` | `mhef_independent_add` | `hash_partition_a_add` | +0.004488 | +0.004031 | +0.001320 | +0.001002 | `CLEAN_MECHANISM_SIGNAL` |
| `semantic_partition_b` | `mhef_independent_add` | `hash_partition_b_add` | +0.004471 | +0.004019 | +0.001302 | +0.001002 | `CLEAN_MECHANISM_SIGNAL` |

## Attribution and Causal Analysis

1. **Normalization decoupling is not materially beneficial:** The decisive causal test (`mhef_independent_add` vs `coupled_budget_add`) removes only the cross-modality zero-sum constraint while fixing token scores, key/value projections, parameter count, and final scoring head. The observed delta is only $+0.001410$ (+0.141 pp), which falls well short of the pre-registered $+0.0030$ threshold. Under the concat fusion head, the delta vanishes completely ($\Delta J = +0.000093$, +0.009 pp).
2. **Gain is entirely absorbed by wide global capacity:** The wide global control (`wide_global_add`), which feeds four identical global FineCode vectors into the four evidence slots of the prediction head, achieves $J = 0.549980$, exceeding `mhef_independent_add` ($J = 0.549397$) by $+0.000583$. This proves that the slight improvement over the base foundation ($J = 0.546626$) is a capacity/multi-head artifact of providing four slots to the scoring head, rather than any benefit from heterogeneous modality normalization.
3. **Partition controls isolate semantic damage, not normalization value:** While `mhef_independent_add` beats the two nonsemantic hash partitions ($0.5449$ vs $0.5494$, $\Delta \approx +0.0045$), this merely demonstrates that randomly permuting clinical code assignments degrades model performance. It does not rescue the primary normalization hypothesis against the coupled budget or wide global controls.
4. **Complete model does not surpass prior best:** The rank-1 candidate ($J = 0.549397$) remains slightly below the prior completed best architecture (`summary_add`, $J = 0.549611$, $\Delta J = -0.000214$).

## Decision and Routing

- **Verdict:** **`KILL_MHEF_NORMALIZATION_HYPOTHESIS`**.
- Multi-seed stability is **NOT** authorized.
- MIMIC-IV replication is **NOT** authorized.
- Test set access remains **SEALED**.
- No post-hoc HPO, threshold tuning, dynamic gating, or safety rerankers are permitted to rescue the killed mechanism.
- The project moves forward to evaluate the next orthogonal architectural hypothesis on top of the stable FineCode foundation.
