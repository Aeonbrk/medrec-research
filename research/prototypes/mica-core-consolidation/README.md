# MICA-Core consolidation (Stage -1B/-1C)

This directory is an additive execution harness for the frozen Stage -1
recipe test and the four intrinsic MICA-Core controls. It does not modify the
historical [`research/prototypes/mica`](../mica/) implementation or its result
artifact.

## Frozen scope

Stage -1B runs only MICA-Core (`DrugQuery`) with seed `20260914`, batch 16,
weight decay `1e-4`, current dropout/DDI loss/decoder, 60 complete epochs, and
the existing Train/Dev split and strict best-Dev-Jaccard checkpoint rule:

| Arm | Optimizer schedule |
| --- | --- |
| `t0_current_anchor` | AdamW, constant `3e-4` |
| `t1_lower_constant` | AdamW, constant `1e-4` |
| `t2_cosine_decay` | AdamW, initial `3e-4`, cosine to `3e-6`, no warmup |

Stage -1C reuses the recipe selected (or the current recipe with early
checkpointing if no new recipe passes) and runs exactly:

| Control | Change from Core |
| --- | --- |
| `core` | current MICA-Core |
| `one_clinical_block` | clinical blocks `2 → 1` |
| `no_post_read_conditioner` | retain DrugQuery; remove `condition_context` and its parameters |
| `simplified_head` | retain encoder + DrugQuery; `[c,e,c*e] → Linear(384,1)` plus existing medication bias |

No control adds a data source, history channel, graph, retrieval, router,
decoder, safety head, or auxiliary loss. The medication-specific DrugQuery
read remains unchanged in all four controls.

## Stage -1B result

The three complete 60-epoch aggregate results are in
[`recipe-result.json`](recipe-result.json). The lower constant arm is selected
as `ADOPT_STABLE_RECIPE_FOR_STAGE_MINUS_1C`: peak Jaccard is `0.542280`
(anchor `0.542244`), peak PRAUC is within `0.002` of the anchor (`0.790848`
versus `0.792730`), and its Jaccard/PRAUC drops and NLL drift are all lower
than the anchor (`0.067581/0.074983/0.309206` versus
`0.068154/0.078207/0.337782`). Cosine also lowers Jaccard/PRAUC drop but has
larger NLL drift (`0.430405`), so it is not selected. This is one seed of
Train/Dev evidence; it is not a sweep or a general optimizer claim.

The stabilized Stage -1C recipe is AdamW with constant learning rate `1e-4`,
seed `20260914`, batch 16, weight decay `1e-4`, the current DDI objective and
decoder, and 60 complete epochs.

## Execution and evidence boundary

`run_consolidation.py` requires an exact clean source revision, the canonical
MoleRec-compatible snapshot `molerec-table1-c721-www23`, and the canonical
Train/Dev root `gate01-train-dev-5752596a-20260913a`. `--preflight-only`
performs target-free CUDA forward/backward and data/shape checks without an
epoch. Full runs must execute on 319 in the declared `medrec-molerec-table1`
environment; use one detached process per authorized GPU. Output directories
must remain outside all Git checkouts. Keep checkpoints, predictions, IDs, and
logs on the private execution plane; only aggregate metrics may be copied into
the repository.

This remains exploratory Train/Dev evidence. It is not a formal Gate, an
Audit, a held-out Test, a multi-seed result, or a paper/novelty claim.
