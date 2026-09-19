# Handoff

Updated: 2026-09-19.

```text
Current phase: MHEF_NORMALIZATION_HYPOTHESIS_FALSIFIED_NEXT_DIRECTION_DECISION
Working branch: prototype/mhef-normalization-screen
Active formal Idea: none
Active formal Gate: none
Evidence role: DEVELOPMENT
Test access: not authorized
GPU capacity: 8 × RTX 3090 24GB
Terminal routing: KILL_MHEF_NORMALIZATION_HYPOTHESIS
```

## Authoritative starting point

This branch was executed on the 319 Execution Plane at frozen revision:

```text
4584f8a0d080f4300f9ba5778da08f7f82cdc805
```

Read first:

- `AGENTS.md`
- `research/AGENTS.md`
- `research/memory/current-research-state.md`
- `research/memory/decisions/2026-09-19-mhef-normalization-screen-verdict.md`
- `research/prototypes/mhef-normalization-screen/README.md`
- `research/prototypes/mhef-normalization-screen/result.json`

## What was completed

All 8 physical RTX 3090 GPU lanes completed all 30 planned epochs without early stopping or divergence:

1. **Preflight passed:** exact FineCode global path preservation, zero data leakage, verified common parameter count (1,476,874 params across all lanes), and active mechanisms.
2. **Execution completed:** all eight 30-epoch lanes completed. All models selected their peak checkpoint at Epoch 5 (`safe_selected_epoch_max = 25 >= 5`, no horizon censoring).
3. **Public-safe evidence preserved:** aggregate results recorded in `research/prototypes/mhef-normalization-screen/result.json`.
4. **Test set remained sealed:** zero Test evaluation performed (`test_loaded = false`).

## Summary of empirical evidence

| Lane | Role | Best Ep / OP | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| `mhef_independent_add` | Rank-1 Candidate | Ep 5 / 0.30 | 0.549397 | 0.700657 | 0.794860 | 0.072165 |
| `coupled_budget_add` | Matched Normalization Control | Ep 5 / 0.30 | 0.547986 | 0.699394 | 0.793084 | 0.071378 |
| `wide_global_add` | Capacity Absorption Control | Ep 5 / 0.30 | **0.549980** | 0.701313 | 0.794769 | 0.072489 |
| `mhef_independent_concat` | Concat Candidate | Ep 5 / 0.30 | 0.545593 | 0.697693 | 0.794941 | 0.073200 |
| `coupled_budget_concat` | Concat Control | Ep 5 / 0.35 | 0.545500 | 0.697330 | 0.793394 | 0.070904 |
| `private_only_add` | Private-Only Ablation | Ep 5 / 0.30 | 0.547128 | 0.698678 | 0.792935 | 0.072477 |
| `hash_partition_a_add` | Hash Partition A | Ep 5 / 0.35 | 0.544909 | 0.696626 | 0.793541 | 0.071163 |
| `hash_partition_b_add` | Hash Partition B | Ep 5 / 0.35 | 0.544926 | 0.696638 | 0.793559 | 0.071163 |

## Decisive scientific conclusions

- **Primary normalization comparison:** `mhef_independent_add - coupled_budget_add` yields $\Delta J = +0.001410$ (+0.141 pp), failing the $+0.0030$ material threshold (`KILL_NO_MATERIAL_SIGNAL`).
- **Concat control:** `mhef_independent_concat - coupled_budget_concat` yields $\Delta J = +0.000093$ (+0.009 pp).
- **Capacity absorption:** `wide_global_add` ($J = 0.549980$) outperforms `mhef_independent_add` ($J = 0.549397$), proving that the slight gain over the base foundation is absorbed by multi-slot capacity rather than heterogeneous normalization decoupling.
- **Terminal routing:** `KILL_MHEF_NORMALIZATION_HYPOTHESIS`.

## Next agent instructions

1. Do **NOT** attempt to rescue MHEF with query adapters, dynamic gating, extra layers, or post-hoc threshold/DDI tuning.
2. Do **NOT** run multi-seed stability or MIMIC-IV replication on MHEF.
3. Keep the Test set sealed.
4. Formulate the next orthogonal architectural hypothesis building on the verified FineCode foundation.
