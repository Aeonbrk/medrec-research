# HypeMed fidelity semantic diff

Audit target: official HypeMed source revision
`33339ea973fd1d72908b3f6ae34b578d98fb4ba3`.  The previous adapter is the
implementation in `research/prototypes/hypeinteract/` at the base revision
`530f4d22111f385c8f735454cde36155363d7292`.  Source paths below refer to the
official checkout under `/tmp/hypemed-official.G0PHUs/HypeMed` and the adapter
path in this worktree.

| Official component | Previous adapter component | Equivalent? | Expected performance relevance |
| --- | --- | --- | --- |
| Separate diagnosis/procedure/medication incidence hypergraphs; one visit column per training visit (`graph_construction.py`) | Same three domains, with a fallback node for an empty edge | NO | Changes empty-visit semantics; otherwise preserves the visit-hyperedge idea. |
| PyG `HypergraphConv` attention with incidence and degree normalization | Sparse node-to-edge and edge-to-node mean aggregation | NO | Core local higher-order message passing is materially different. |
| KHGE local MPNN + global multi-head attention + residual/LN/FFN and layer averaging (`layers/hgt_encoder.py`) | Similar residual block with custom local means | NO | Global shape is similar, but local operator and state updates differ. |
| Structural encoding from node degree and incident-edge-size statistics (`layers/position_encoding.py`) | Omitted | NO | Missing structural signal. |
| Positional encoding from hypergraph Laplacian SVD with sign augmentation | Omitted | NO | Missing topology/position signal. |
| ICD/ATC hierarchy distance embeddings and attention bias | Three-character code-prefix equality bias | NO | Knowledge signal is only a rough deterministic proxy. |
| TriCL trainable node/edge tables, self-loop hyperedges, node/edge/membership InfoNCE | Direct encoder-output contrast; no self-loops or projection heads | NO | Pretraining representation and retrieval geometry differ. |
| Feature/node/incidence drops with valid node/edge membership masks | Feature/incidence drops only; no node dropout or valid masks | NO | Augmentation support and contrastive negatives differ. |
| `Node2EdgeAggregator`: mean query, entity MHA, residual/LN/FFN | Plain mean-pool event embeddings | NO | Visit representation loses within-visit attention. |
| Shifted dense medication-history visit embeddings | Prior-event medication mean | NO | Causality is preserved, but temporal capacity differs. |
| `HistoryAttention`: MHA + residual/LN/FFN with history mask | Mean history vector plus linear projection | NO | Longitudinal channel is substantially weaker. |
| FAISS GPU L2 top-`top_n` memory search, followed by MHA over retrieved health/medication values | NumPy cosine top-k, temperature weighted average | NO | Retrieval metric, weighting, and memory interaction differ. |
| Two-channel patient/history + EHR-memory softmax gate | Three-channel current/history/retrieval gate | NO | Channel semantics and capacity differ. |
| Dot-product scorer plus medication-vocabulary LayerNorm | Dot-product scorer without vocabulary LayerNorm | NO | Logit calibration differs. |
| Retrieval-alignment InfoNCE side loss | No retrieval InfoNCE | NO | No explicit representation-memory alignment. |
| Cosine orthogonality regularizer on fused channels | No orthogonality term | NO | Channel redundancy is unconstrained. |
| BCE + multilabel-margin + adaptive DDI + retrieval SSL/orthogonality (`HypeMed.py`) | BCE + mean DDI penalty | NO | Objective and safety/recall trade-off differ. |
| Adam recommendation optimizer + CosineAnnealingWarmRestarts (`T_0=25`, `T_mult=2`) | AdamW with no scheduler | NO | Optimization trajectory differs. |
| 1,500 pretraining epochs, 75 recommendation epochs, batch 16 | 3 pretraining epochs, 8 recommendation epochs, batch 128 | NO | The prior result is undertrained relative to official defaults. |
| Sigmoid threshold 0.5 | Logit threshold 0 (equivalent) | YES | Same decision threshold. |

Primary references: [official repository](https://github.com/xansar/HypeMed),
[paper](https://doi.org/10.1145/3803851), and the [full author manuscript](https://arxiv.org/html/2603.18459).

Conclusion: the previous `0.431689` result is not an exact HypeMed fidelity
result.  It is a simplified adapter result, so its prior terminal
interpretation is suspended pending the faithful-source runs below.
