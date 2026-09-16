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

The target-free CUDA/data preflight for all four controls passed on the exact
source revision; its public-safe summary is [`preflight-result.json`](preflight-result.json).

## Stage -1C result

The four complete 60-epoch controls used the selected `t1_lower_constant`
recipe on source revision `5864011a864851c7eba1ed2a0742221c9e7dcf5f`. The
public-safe aggregate is [`consolidation-result.json`](consolidation-result.json).

| Control | Params | Best epoch | Jaccard | F1 | PRAUC | DDI | NLL | Epoch-60 J | Epoch-60 PRAUC | Epoch-60 NLL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 848900 | 5 | 0.542280 | 0.695095 | 0.790848 | 0.076524 | 0.204557 | 0.474699 | 0.715865 | 0.513763 |
| OneClinicalBlock | 716420 | 5 | 0.541037 | 0.693987 | 0.788838 | 0.076553 | 0.204490 | 0.466714 | 0.708844 | 0.503723 |
| NoPostReadConditioner | 815876 | 5 | 0.541534 | 0.694440 | 0.790505 | 0.076623 | 0.204606 | 0.474836 | 0.714880 | 0.501174 |
| SimplifiedHead | 799876 | 5 | 0.536593 | 0.690080 | 0.786329 | 0.076371 | 0.205739 | 0.467744 | 0.709090 | 0.423841 |

The predeclared rule therefore gives `KEEP_EXISTING_MICA_CORE`. Both
OneClinicalBlock and NoPostReadConditioner reduce parameters, but
OneClinicalBlock misses the PRAUC floor and has worse late Jaccard/PRAUC
degradation. NoPostReadConditioner stays within the peak Jaccard/PRAUC floors
and has lower Jaccard drop and NLL drift, but its PRAUC drop is slightly worse
than Core (`0.075625` versus `0.074983`), so it is not a stable replacement.
SimplifiedHead fails both peak accuracy floors. No simplification had a
meaningful Jaccard gain (`>0.004`).

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
