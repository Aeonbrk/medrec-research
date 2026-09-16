# Stage -1G protocol — Competitive substrate calibration

## 1. Scientific question

Stage -1F answered whether medication-specific evidence selection replicates across MIMIC-III and MIMIC-IV. Stage -1G asks whether the resulting MICA-Core surface is competitive enough against strong faithful external methods to justify using it as the substrate for the next model-level hypothesis.

This stage is calibration, not final paper confirmation. It remains Train/Dev, one seed, no Test, no Idea 009, no Gate, and no RSM implementation.

## 2. Experimental standard

The comparison standard is semantic fairness, not a shared optimizer.

Every compared method must share:

- the frozen patient split and role semantics;
- the same current-visit target definition;
- the same prediction-time information budget;
- the same ATC4 target semantics for the dataset;
- the same core evaluator for common metrics;
- Dev-only model selection/tuning;
- no Test access.

Every external baseline keeps its own scientific core, loss, architecture, optimizer family, thresholding/checkpoint logic, and documented training recipe unless the upstream method leaves a choice unspecified. Mechanical adaptation may translate dataset files, identifiers, tensor shapes, or target-free payloads; it must not improve or weaken the model logic.

This follows the experimental logic used in MoleRec (WWW 2023), which compares many model families under one task while using original/default or validation-tuned baseline settings rather than forcing one optimizer recipe. MoleRec also reports accuracy, DDI safety, medication count, bootstrap variability, and ablations. Stage -1G adopts that evidence shape but modernizes it with dual-dataset calibration and patient-clustered paired diagnostics.

Primary sources:

- MoleRec, WWW 2023: https://doi.org/10.1145/3543507.3583872
- ARMR, IJCAI 2025: https://doi.org/10.24963/ijcai.2025/871
- SSPNet, IJCAI 2025: https://doi.org/10.24963/ijcai.2025/1052
- HypeMed, ACM TOIS 2026: https://doi.org/10.1145/3803851

## 3. Frozen MICA references

Do not rerun MICA merely to fill GPUs. Use the frozen Stage -1F rows unless `G0_EQUIVALENCE` finds a real implementation drift that invalidates the generalized path.

Reference rows:

| Dataset | Arm | Jaccard | F1 | PRAUC | DDI | NLL |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| MIMIC-III | SharedPool | 0.531796 | 0.685760 | 0.785189 | 0.076841 | 0.206553 |
| MIMIC-III | DrugQuery | 0.539316 | 0.692880 | 0.788679 | 0.078599 | 0.204234 |
| MIMIC-IV | SharedPool | 0.552883 | 0.698327 | 0.789836 | 0.063074 | 0.115632 |
| MIMIC-IV | DrugQuery | 0.559369 | 0.703702 | 0.796329 | 0.061812 | 0.112925 |

The MICA working recipe remains useful for matched MICA-family screens, not as a universal baseline recipe.

## 4. G0 — exact-equivalence audit

Before external training, resolve the remaining fixed-131/generalized-MICA concern.

Locate the source-bound revision used by the Stage -1C fixed-131 `1e-4` Core and the generalized implementation used by Stage -1F from run-local provenance. Do not guess revisions from handoff text.

On the 131-medication path, under the same seed and deterministic settings, compare:

- parameter names and shapes;
- initialized tensor values after deterministic state mapping;
- forward logits on the same target-free synthetic or Train-derived input batch;
- objective components using deterministic synthetic labels if needed for loss comparison.

Expected numerical tolerance for equivalent float32 paths:

- state tensors: exact where initialization order is identical; otherwise explain any deterministic remapping;
- logits: maximum absolute difference `<= 1e-6`;
- scalar objective components: absolute difference `<= 1e-7` where the same operations are used.

If a scientific computation differs, stop with:

`STOP_MICA_GENERALIZATION_EQUIVALENCE_FAILURE`

Do not hide the difference behind training stochasticity. A purely mechanical difference with proven identical computation may be fixed, followed by one scoped regression check.

## 5. G1 — external baseline qualification

Qualification precedes training. Search primary papers and official repositories at execution time and pin exact source revisions.

### 5.1 Preferred paired baseline families

Select exactly three baseline families that can run faithfully on both frozen datasets. Priority order:

1. **ARMR** — recent IJCAI 2025 longitudinal/adaptive method with official code and MIMIC-III/MIMIC-IV evidence.
2. **HypeMed** — recent TOIS 2026 representation/retrieval method with official code and MIMIC-III/MIMIC-IV evidence.
3. **SSPNet** — IJCAI 2025 set-to-set method and the most structurally relevant external comparator for later RSM work, but execute only if a trustworthy source or sufficiently faithful implementation lineage can be established.
4. **GAMENet** — established longitudinal/graph control; existing project reproduction lineage is preferred fallback.
5. **RETAIN** — established longitudinal control fallback.
6. **SafeDrug** — safety/molecular control only if every required target medication has valid method-native assets or an official unknown-item policy.
7. **MoleRec** — molecular/substructure control only if every required target medication has valid method-native assets or an official unknown-item policy.

The preferred six-GPU matrix is therefore three paired families × two datasets. Do not fill a lane with a scientifically incompatible method merely to occupy a GPU.

### 5.2 Qualification requirements

A method is Stage -1G qualified only when all hold:

- primary paper and source identity are pinned;
- official source is used when available;
- the model can consume the frozen input information without current-target or future leakage;
- the output can represent the complete frozen Train medication vocabulary without silently dropping labels;
- any molecular, graph, knowledge, or retrieval assets are Train-safe and compatible with the output vocabulary;
- no Dev/Test target-derived global structure is required at prediction time;
- the method can use the frozen patient split without changing its scientific core;
- its training, checkpoint, and prediction semantics are documented enough to reproduce;
- comparison adaptation is mechanical rather than a new scientific method.

If a method requires future information, target-derived test structure, unsupported medication assets, or a major scientific rewrite, record a precise incompatibility and move to the next candidate. Do not create a weak inspired rewrite and call it the published baseline.

### 5.3 Coverage gate

Before `G2`, the selected set should contain:

- three paired baseline families runnable on both MIMIC-III and MIMIC-IV;
- at least two recent 2025–2026 methods when faithful compatible implementations are available;
- at least one established/classical lineage or otherwise structurally distinct comparator.

If this cannot be achieved without violating fidelity or information-budget rules, finish the qualification record and return:

`INSUFFICIENT_COMPETITIVE_CALIBRATION`

Do not lower the bar by relabeling literature-only scores as directly comparable.

## 6. G2 — six-GPU Train/Dev screen

Once three paired baseline families `B1/B2/B3` are frozen, use six GPUs in parallel:

```text
GPU0  B1 / MIMIC-III
GPU1  B1 / MIMIC-IV
GPU2  B2 / MIMIC-III
GPU3  B2 / MIMIC-IV
GPU4  B3 / MIMIC-III
GPU5  B3 / MIMIC-IV
```

Use one seed per arm for this calibration stage. Record the method-native seed if upstream code fixes one; otherwise use project seed `20260914`.

### 6.1 Training entitlement

Use the upstream/paper-recommended optimizer, loss, architecture settings, and training schedule when they remain valid under the frozen task. If the upstream repository contains dataset-specific MIMIC-III/MIMIC-IV configs, prefer them.

Do not force AdamW `1e-4` onto external baselines.

Do not perform broad hyperparameter sweeps. A single bounded adjustment is allowed only when a concrete source-backed reason shows that an upstream setting is invalid under the larger frozen cohort or different vocabulary. Examples include documented batch-size memory limits or a training horizon that ends while the Dev curve is still materially improving. Record the trigger and the one permitted adjustment before executing it.

A baseline must receive enough budget to make under-training implausible. If its terminal Dev surface is still the best and materially improving, mark the lane `BUDGET_INCONCLUSIVE` rather than calling the method weak. One bounded budget extension may be authorized when the source and curve support it; no rescue chain.

Multi-stage methods keep their documented pretraining/training stages. Pretraining may use Train data only.

### 6.2 Checkpoint and threshold semantics

Preserve the method's documented validation checkpoint and prediction rule when defined by the upstream method. If the method leaves a choice unspecified, freeze the missing choice before training and apply it consistently across both datasets.

Do not tune on Test. Do not choose a post-hoc threshold after seeing cross-method Dev rankings unless that threshold selection procedure was frozen as part of the method profile before the run.

## 7. Common evaluation

The core evaluator recomputes, where the method output supports them:

- Jaccard;
- F1;
- PRAUC;
- DDI rate;
- average medication count;
- NLL/calibration metric for probabilistic outputs.

Also record engineering cost:

- trainable parameter count;
- training wall time;
- peak GPU memory;
- inference latency on the same RTX 3090 class when a stable common measurement path exists.

Do not fabricate PRAUC or NLL for a method that does not expose the required scores. Mark unsupported metrics explicitly.

DDI is compared within each dataset only. Absolute MIMIC-III and MIMIC-IV DDI values are not treated as one shared safety scale.

## 8. Development-only uncertainty diagnostic

After all valid lanes finish, identify the strongest qualified external baseline on each dataset and compare it with frozen MICA DrugQuery using paired patient-cluster bootstrap on Dev predictions.

Use at least 2,000 patient-level resamples and report 95% percentile intervals for:

- `ΔJ`;
- `ΔF1`;
- `ΔDDI`.

This is a development diagnostic, not final statistical evidence, because model selection also used Dev. Do not attach confirmatory p-value language to it.

Patient-level predictions remain restricted; Git receives only aggregate intervals and counts.

## 9. Competitiveness decision

For each dataset, let `B*` be the strongest valid external baseline by Dev Jaccard and inspect the Jaccard–DDI Pareto surface.

A baseline materially dominates MICA on a dataset when all hold:

- `J_B - J_MICA > 0.004`;
- `F1_B - F1_MICA >= -0.002`;
- `PRAUC_B - PRAUC_MICA >= -0.002` when PRAUC is available;
- `DDI_B - DDI_MICA <= +0.002`.

A large accuracy deficit is independently concerning when:

- `J_B - J_MICA > 0.010`.

Terminal routing:

### `MICA_SUBSTRATE_COMPETITIVE_BOTH_DATASETS`

Use only when the coverage gate passed and neither dataset has material external dominance or a `>0.010` best-Jaccard deficit. This means MICA remains a credible substrate for one bounded Stage 0 architecture test; it is not a SOTA claim.

### `MICA_SUBSTRATE_BORDERLINE`

Use when the coverage gate passed, there is no clear material Pareto dominance, but the best-Jaccard deficit is `>0.005` and `<=0.010` on one dataset or another bounded ambiguity prevents a clean substrate decision.

### `MICA_SUBSTRATE_OUTCLASSED`

Use when a valid external baseline materially dominates MICA on either dataset or exceeds it by more than `0.010` Jaccard on either dataset. Step back from MICA-derived RSM rather than hoping a small downstream decoder recovers the gap.

### `INSUFFICIENT_COMPETITIVE_CALIBRATION`

Use when three faithful paired baseline families cannot be established or key lanes remain invalid/inconclusive.

### `STOP_MICA_GENERALIZATION_EQUIVALENCE_FAILURE`

Use when G0 exposes a real generalized-MICA computation drift that is not mechanically resolved.

## 10. Public-safe artifacts

Create:

```text
research/prototypes/mica-competitive-substrate-calibration/
  README.md
  protocol.md
  qualification.json
  result.json
  diagnostics.json
```

Only aggregate public-safe evidence enters Git. Keep patient IDs, predictions, weights, restricted dataset material, and private runtime paths on the 319 execution plane.

`qualification.json` should record source revision, primary-paper identity, compatibility decisions, and exact exclusion reason for every candidate considered.

`result.json` should bind run revision, dataset manifest, method profile, configuration, selected checkpoint, common metrics, and resource metrics.

## 11. Explicit non-goals

Stage -1G does not:

- read or evaluate Test;
- run multiple training seeds;
- claim SOTA;
- implement or train RSM;
- create Idea 009;
- open a formal Gate;
- broaden into a full 2023–2026 benchmark survey;
- force one optimizer across methods;
- rescue an incompatible external baseline by changing its scientific core.

If MICA passes Stage -1G, the next step is review of the already identified bounded Stage 0 RSM screen. If it fails, the next step is a model-level reset, not more MICA tuning.
