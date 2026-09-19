# Handoff

Updated: 2026-09-20.

```text
Current phase: MEMB_SCREEN_COMPLETED_FALSIFIED_ARCHITECTURE_SEARCH_RESET
Working branch: prototype/memb-mutual-binding-screen
Active formal Idea: none
Active formal Gate: none
Evidence role: DEVELOPMENT
Test access: not authorized
GPU capacity: 8 × RTX 3090 24GB
Terminal routing: KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY
```

## Authoritative starting point

The Medication–Evidence Mutual Binding (MEMB) architecture screen has completed on the 319 Execution Plane at frozen revision:

```text
f1f74e5eb143f49a2bac73d81a13c42f33f4a4a2
```

Read first:

- `AGENTS.md`
- `research/AGENTS.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_1.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_2.md`
- `docs/specs/PAPER_EXPERIMENT_CONTRACT_V1_3.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-19-memb-mutual-binding-screen-verdict.md`
- `research/prototypes/memb-mutual-binding-screen/README.md`
- `research/prototypes/memb-mutual-binding-screen/closest-work-audit.md`
- `research/prototypes/memb-mutual-binding-screen/result.json`

## Screen outcome summary

All eight physical RTX 3090 GPU lanes completed all 30 planned epochs without early stopping under canonical RNG (`torch/cuda/python=1203`, `numpy=2048`). All lanes selected best Dev checkpoints between Epochs 3 and 7 (`safe_selected_epoch_max = 25 >= 7`), with zero horizon censoring.

### Completed 30-epoch lanes

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

### Pre-registered commonness comparisons

- **Code commonness scale 1 (`specificity_code - foundation_code_anchor`)**: $\Delta J = +0.000499$ (+0.050 pp), $\Delta F1 = +0.000327$, $\Delta \text{PR-AUC} = +0.000811$, $\Delta \text{DDI} = +0.000126$. Fails $+0.0020$ threshold (`KILL_NO_MATERIAL_SIGNAL`).
- **Code commonness scale 2 (`mutual_code - scale2_code`)**: $\Delta J = +0.002095$, $\Delta F1 = +0.001332$, $\Delta \text{PR-AUC} = -0.000220$, $\Delta \text{DDI} = +0.004562$ (`WEAK_STOP` / guardrail failure). Artifact of partial recovery from severe sharpening damage (`scale2_code` lost $-0.006611$ vs base); both scale-2 lanes underperform `foundation_code_anchor` ($0.546626$).
- **Local commonness scale 1 (`specificity_local - prediction_local_anchor`)**: $\Delta J = -0.000770$, $\Delta F1 = -0.000817$, $\Delta \text{PR-AUC} = +0.000276$, $\Delta \text{DDI} = -0.005036$ (`KILL_NO_MATERIAL_SIGNAL`). DDI reduction falls short of the pre-registered Pareto gate ($\Delta \text{DDI} \le -0.010$).
- **Local commonness scale 2 (`mutual_local - scale2_local`)**: $\Delta J = -0.001007$, $\Delta F1 = -0.000811$, $\Delta \text{PR-AUC} = -0.000301$, $\Delta \text{DDI} = -0.000351$ (`KILL_NO_MATERIAL_SIGNAL`).
- **Anchor integrity**: Both historical anchors reproduce with exactly 0.0 absolute difference across all five metrics.

### Terminal routing

`KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY`.

Per the research contract, no hyperparameter sweeps, score exponents, temperatures, top-k competition, Sinkhorn iterations, OT marginals, sparse activations, or rerankers are permitted to rescue the killed mechanism. Multi-seed stability and MIMIC-IV replication are **NOT** authorized. Test set remains **SEALED**.

## Next agent guidance

1. The cross-medication commonness / mutual-binding hypothesis is definitively falsified. Do not iterate on MEMB variants.
2. The stable FineCode foundation and the `summary_add` / `wide_global_add` baseline clues remain the highest-performing validated references.
3. Reset the architecture search and formulate the next candidate mechanism around an orthogonal hypothesis.
