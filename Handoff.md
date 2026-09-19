# Handoff

Updated: 2026-09-19.

```text
Current phase: MSED_SCREEN_COMPLETED_FALSIFIED_ARCHITECTURE_SEARCH_RESET
Working branch: prototype/msed-evidence-distribution-screen
Active formal Idea: none
Active formal Gate: none
Evidence role: DEVELOPMENT
Test access: not authorized
GPU capacity: 8 × RTX 3090 24GB
Terminal routing: KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS
```

## Authoritative starting point

The Medication-Specific Evidence Distribution (MSED) architecture screen has completed on the 319 Execution Plane at frozen revision:

```text
e54d3d5a2a5145d14beadb109d574ad82efdae9e
```

Read first:

- `AGENTS.md`
- `research/AGENTS.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_2.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_3.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-19-msed-evidence-distribution-screen-verdict.md`
- `research/prototypes/msed-evidence-distribution-screen/README.md`
- `research/prototypes/msed-evidence-distribution-screen/closest-work-audit.md`
- `research/prototypes/msed-evidence-distribution-screen/result.json`

## Screen outcome summary

All eight physical RTX 3090 GPU lanes completed 30 epochs without early stopping under canonical RNG (`torch/cuda/python=1203`, `numpy=2048`). All lanes selected best Dev checkpoints between Epochs 3 and 8 (`safe_selected_epoch_max = 25 >= 8`), with zero horizon censoring.

### Completed 30-epoch lanes

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

### Matched comparisons

- **Primary distribution test (`msed_ecf_global - point_lme_global`)**: $\Delta J = +0.000626$ (+0.063 pp), $\Delta F1 = +0.000421$, $\Delta \text{PR-AUC} = +0.000463$, $\Delta \text{DDI} = -0.000427$. Fails the $+0.0020$ threshold (`KILL_NO_MATERIAL_SIGNAL`).
- **Distribution in isolation (`msed_ecf_only - point_lme_only`)**: $\Delta J = -0.003699$ (-0.370 pp). In isolation, empirical characteristic spectrum distribution encoding performs substantially worse than scalar LME.
- **Point controls**: `msed_ecf_global` does not materially outperform simple mean ($\Delta J = +0.000428$) or hard max ($\Delta J = +0.000154$).
- **Absolute benchmarks**: `msed_ecf_global` (0.546806) underperforms `prediction_local_anchor` (0.548911, $\Delta J = -0.002105$), `summary_add` (0.549611, $\Delta J = -0.002805$), and `wide_global_add` (0.549980, $\Delta J = -0.003174$).
- **Integrity anchors**: `prediction_local` and `foundation_code` historical checkpoints reproduce with exactly 0.0 absolute difference across all five metrics.

### Terminal routing

`KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS`.

Per the research contract, no hyperparameter sweeps, frequency bandwidth sweeps, temperature sweeps, or rerankers are permitted to rescue the killed mechanism. Multi-seed stability and MIMIC-IV replication are **NOT** authorized. Test set remains **SEALED**.

## Next agent guidance

1. The distribution-shape hypothesis is definitively falsified. Do not iterate on MSED variants.
2. The strong FineCode foundation and the `summary_add` / `wide_global_add` baseline clues remain the highest-performing validated references.
3. Reset the architecture search and formulate the next candidate mechanism around an orthogonal hypothesis.
