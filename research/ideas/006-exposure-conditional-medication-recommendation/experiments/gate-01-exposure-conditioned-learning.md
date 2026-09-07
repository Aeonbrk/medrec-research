<!-- markdownlint-disable MD013 -->

# Gate 01 — Exposure-Conditioned Learning vs Direct Exposure Controls

## 0. Protocol identity

- **Idea**: `006-exposure-conditional-medication-recommendation`
- **Owner**: `ccf-experiment-designer`
- **Mode**: raw protocol / hypothesis selection
- **Status**: `FROZEN / AUTHORIZED / NOT_EXECUTED`
- **R0 prerequisite**: `PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE`
- **R0 execution commit**: `ea134b7e75583186242bc72bc71eb2975b812edc`
- **Primary data**: raw MIMIC-IV 3.1 under the R0 normalization/linkage contract
- **Medication vocabulary**: frozen 131 ATC-L4 concepts from R0
- **DDI asset**: frozen SafeDrug/MoleRec asset, SHA256 `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7`
- **Existing project test split**: forbidden
- **R0 Holdout**: forbidden
- **R0 Dev**: authorized only for one frozen Gate-01 evaluation after all training/tuning decisions are complete

Gate 01 is the only authorized method experiment. It is not publication claim-support evidence and it does not authorize a paper directory, Holdout evaluation, multi-backbone expansion, or model rescue.

## 1. Claim under test

The central method claim is:

> Under a leakage-safe provider-order-time medication recommendation task, end-to-end DDI learning conditioned on the strictly pre-order execution-confirmed active regimen creates a material active-exposure safety/fidelity advantage that cannot be reproduced by direct use of the identical active-exposure DDI signal at inference time.

The strongest null is not prediction-only training. It is:

> Once the active-regimen DDI signal is known, a deterministic exposure-aware reranker or constraint is sufficient; end-to-end exposure-conditioned learning adds no scientific value.

Gate 01 is designed to prefer this null unless the learned method produces a reproducible incremental advantage.

## 2. Evidence map

| Claim component | Required evidence | Gate-01 decision role |
| --- | --- | --- |
| Exposure-localized DDI learning changes the intended safety quantity | `ExposureConditional` vs `Base` on primary risk at fixed $K=5$ | Required |
| Gain is not ordinary set-level DDI regularization | `ExposureConditional` vs `StaticLoss` | Required |
| Learned value is not absorbed by the available rule | `ExposureConditional` vs `DirectExposureRerank` with identical $A_t$ and DDI matrix | **Primary killer comparison** |
| Gain is not an artifact of variable medication count | all primary methods emit exactly $K=5$ recommendations | Required |
| A trivial hard safety rule is not already superior | `ExposureHardConstraint` | Required dominance check |
| Result is not patient-resampling noise | patient-clustered paired bootstrap | Required |

## 3. Patient partitions

R0 already created patient-disjoint Discovery/Dev/Holdout partitions from `subject_id` with salt `exposure-reset-20260905`.

Gate 01 must preserve those exact assignments.

### 3.1 Inner split inside R0 Discovery

Before constructing any model-dependent statistic, repartition **R0 Discovery patients only** with a second deterministic subject-only hash:

```text
u = int(SHA256(f"{subject_id}|idea006-gate01-inner-20260907").hexdigest()[:8], 16) / 0xffffffff
InnerTrain: 0.00 <= u < 0.85
InnerTune:  0.85 <= u <= 1.00
```

- `InnerTrain`: model fitting only.
- `InnerTune`: checkpoint selection, safety-budget construction, and the frozen hyperparameter grids below.
- `R0 Dev`: one final frozen Gate-01 evaluation only.
- `R0 Holdout`: no event, feature, target, risk, or performance aggregate may be inspected.
- existing project test split: remains completely untouched.

R0 Discovery was used for resource/premise admission; therefore InnerTune is not final confirmatory evidence. R0 Dev was unused by R0 and is the clean outer partition for this hypothesis-selection gate.

## 4. Decision-event construction

### 4.1 Eligible medication orders

Use provider medication orders in MIMIC-IV `poe` linked deterministically to the R0-selected 131-concept medication identity.

Positive target transactions are medication-order transactions with `transaction_type` in:

```text
New
Change
```

`D/C` transactions are state transitions only and are never positive medication targets.

If the local version exposes additional transaction labels, report their counts publicly at aggregate level but do not add them to the positive target set after inspecting performance.

### 4.2 Non-overlapping 10-minute order bursts

Within each hospitalization and patient partition:

1. sort eligible positive medication-order events by `ordertime`, then deterministic `poe_id` order;
2. the first unassigned eligible positive order defines decision time $t$;
3. the target burst contains all eligible positive medication concepts whose provider order times lie in the half-open interval $[t,t+10\text{ min})$;
4. deduplicate repeated medication concepts within the burst;
5. mark all target events in that interval as assigned;
6. the next unassigned positive order starts the next burst.

The model is evaluated as if immediately before $t$. The 10-minute horizon follows the established inpatient order-prediction formulation and is frozen before Gate-01 execution.

### 4.3 Feature-time boundary

Every model input for a burst at $t$ must satisfy timestamp `< t`.

Events exactly at $t$ belong to the target/action stream and are not visible as input.

Forbidden current-burst inputs include:

- the target medication identity;
- target-burst transaction labels;
- eMAR administrations at or after $t$;
- future D/C events;
- final current-order status used retrospectively;
- current-hospitalization discharge-coded diagnoses/procedures;
- any future event or target-derived statistic.

## 5. Causal active-regimen construction

Let $A_t$ be the pre-order execution-confirmed active medication set.

### 5.1 Order-level state

For each linked provider medication order $o$ created before $t$:

1. map $o$ to one frozen ATC-L4 medication concept;
2. require at least one linked administration with `emar.charttime < t` using exact `poe_id` when available, otherwise exact `pharmacy_id` linkage;
3. track D/C transactions causally: a `poe` event with `transaction_type = D/C`, timestamp `< t`, and `discontinue_of_poe_id = o.poe_id` deactivates that order from its D/C event time onward;
4. if the same medication has multiple prior orders, the medication remains in $A_t$ when at least one execution-confirmed order is still not causally discontinued.

### 5.2 Forbidden retrospective state fields

Do not use:

- `discontinued_by_poe_id` as a backward-looking future pointer;
- final `order_status` to infer historical activity;
- prescription `stoptime` unless a future separately frozen protocol establishes that the stop was already known at $t$;
- post-$t$ administration evidence.

$A_t$ is an operational execution-confirmed active-order state. It is not a PK concentration estimate and must not be described as one.

## 6. Primary evaluation universe

All eligible bursts are retained for secondary prediction reporting.

The **primary Gate-01 universe** is target-free and defined before seeing the burst target:

$$
\mathcal Q=\left\{t:\ |A_t|>0\ \land\ \exists m\in V,\exists a\in A_t:D_{ma}=1\right\}.
$$

This restriction asks whether the method helps only when an exposure-conditioned DDI opportunity actually exists. It does not use the true next medication.

A burst may enter $\mathcal Q$ even when the eventual target contains no interacting medication.

## 7. Common backbone

Gate 01 deliberately uses one small, non-novel causal backbone. Architecture search is prohibited.

### 7.1 Inputs

For every burst at $t$:

- the last **64** normalized medication-order transactions strictly before $t$ within the current hospitalization;
- for each historical transaction: medication concept and transaction type (`New`, `Change`, `D/C` after resolving the referenced medication concept);
- log-scaled elapsed time since the previous historical transaction;
- the 131-dimensional binary active-regimen indicator for $A_t$;
- `log1p(hours since admission)`.

No labs, vitals, notes, current-visit discharge diagnosis/procedure codes, molecular representations, knowledge graphs, or LLM features are allowed in Gate 01.

### 7.2 Architecture

Freeze:

- medication embedding: 64;
- transaction-type embedding: 8;
- elapsed-time projection: 8;
- one-layer GRU: hidden size 128;
- concatenate final GRU state + 131-dim active-regimen indicator + scalar log-hours-since-admission;
- MLP: `260 -> 128 -> 131` with ReLU and dropout `0.10` after the hidden layer;
- output: 131 logits.

If there is no prior transaction, use the learned zero-history state and the active-regimen/time inputs.

All learned variants use exactly this architecture and exactly these inputs. `ExposureConditional` must not receive a richer representation than `Base` or `StaticLoss`.

### 7.3 Prediction loss and optimization

Target $y_t\in\{0,1\}^{131}$ is the deduplicated 10-minute positive order-burst vector.

Use full-vocabulary unweighted binary cross-entropy:

$$
L_{pred}(t)=\frac{1}{|V|}\sum_{m\in V}\operatorname{BCEWithLogits}(z_t(m),y_t(m)).
$$

Freeze training:

- optimizer: AdamW;
- learning rate: `1e-3`;
- weight decay: `1e-5`;
- batch size: `2048` bursts, or the largest deterministic power-of-two batch not exceeding 2048 if memory prevents 2048; the actual batch is frozen for all learned variants before the first complete training run;
- maximum epochs: `5`;
- early stopping patience: `1` completed epoch;
- checkpoint selection within each configuration: lowest InnerTune `L_pred`;
- training seed: `260907`;
- deterministic tie handling where supported by the runtime.

No architecture, optimizer, learning-rate, sequence-length, or seed search is authorized.

## 8. DDI terms

Let $p_t(m)=\sigma(z_t(m))$ and $D$ be the frozen binary DDI matrix.

### 8.1 Conventional new-set term

$$
L_{new}(t)
=
\frac{2}{|V|(|V|-1)}
\sum_{i<j}p_t(i)p_t(j)D_{ij}.
$$

### 8.2 Exposure-conditioned active-regimen term

For $|A_t|>0$:

$$
L_{active}(t)
=
\frac{1}{|V||A_t|}
\sum_{m\in V}\sum_{a\in A_t}p_t(m)D_{ma}.
$$

For $|A_t|=0$, set $L_{active}(t)=0$.

### 8.3 Candidate objective

$$
L_{EC}(t)=L_{pred}(t)+\lambda\left[L_{new}(t)+L_{active}(t)\right].
$$

The static-loss control uses:

$$
L_{Static}(t)=L_{pred}(t)+\lambda L_{new}(t).
$$

## 9. Frozen method/control matrix

### 9.1 `GlobalFrequency@5` — sanity only

Rank medications by InnerTrain target-burst frequency. No patient-specific input. This is reported only to verify task non-triviality and cannot determine Gate PASS.

### 9.2 `Base`

Common backbone trained with $L_{pred}$ only.

### 9.3 `StaticLoss`

Same backbone, inputs, initialization policy, optimizer, and training contract as `Base`, trained with $L_{Static}$.

Frozen InnerTune grid:

```text
lambda_static ∈ {0.1, 0.5, 2.0, 8.0}
```

### 9.4 `DirectExposureRerank` — primary killer control

Use frozen `Base` logits. No retraining.

Starting from an empty selected set $S$, greedily choose one medication at a time until $K$ medications are selected.

For candidate $m\notin S$ define:

$$
r_t(m\mid S)
=
\frac{\sum_{a\in A_t}D_{ma}+\sum_{s\in S}D_{ms}}
{\max(1,|A_t|+|S|)}.
$$

Choose:

$$
\arg\max_{m\notin S}\left[z_t(m)-\gamma r_t(m\mid S)\right].
$$

Frozen InnerTune grid:

```text
gamma ∈ {0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0}
```

This control receives the identical $A_t$ and $D$ available to the learned method.

### 9.5 `ExposureHardConstraint`

Use frozen `Base` logits and the identical $A_t,D$.

At each greedy step:

1. among remaining candidates with zero incremental DDI edges to both $A_t$ and the already selected set $S$, select the highest Base logit;
2. if no zero-increment candidate remains, select the candidate with minimum $r_t(m\mid S)$, tie-breaking by higher Base logit, then ascending medication code;
3. continue until exactly $K$ medications are selected.

There is no tuned parameter.

### 9.6 `ExposureConditional` — candidate method

Same backbone and inputs as `Base`, trained with $L_{EC}$.

Frozen InnerTune grid:

```text
lambda_EC ∈ {0.1, 0.5, 2.0, 8.0}
```

No other learned risk model, contextual DDI network, personalization module, or architecture variant is allowed.

## 10. Fixed-cardinality evaluation

Primary evaluation uses exactly:

```text
K = 5
```

for every method and every eligible burst.

Secondary reporting uses `K=10` with the already frozen configuration selected at `K=5`. K=10 must not trigger retuning.

Ties in logits/scores are resolved by ascending medication concept code.

No method may alter output count to obtain a safety gain.

## 11. Primary fidelity metrics

On $\mathcal Q$, primary fidelity is mean burst-level `Recall@5`:

$$
Recall@5(t)=\frac{|Top5_t\cap Y_t|}{|Y_t|}.
$$

All eligible target bursts have at least one positive medication.

Secondary fidelity metrics:

- `NDCG@5`;
- `Hit@5`;
- `MRR` of the first true target medication;
- micro-PRAUC from the pre-selection 131 probabilities for learned models (`Base`, `StaticLoss`, `ExposureConditional`) only;
- Recall/NDCG at K=10.

Gate decisions use only `Recall@5` among fidelity metrics.

## 12. Primary safety metrics

For a fixed selected set $S_t$ of size $K$:

### 12.1 Active-regimen DDI

$$
ActiveDDI@K(t)
=
\frac{\sum_{m\in S_t}\sum_{a\in A_t}D_{ma}}
{K|A_t|}.
$$

Defined on $\mathcal Q$, where $|A_t|>0$.

### 12.2 New-set DDI

$$
NewDDI@K(t)
=
\frac{\sum_{i<j,\ i,j\in S_t}D_{ij}}
{\binom{K}{2}}.
$$

### 12.3 Incremental exposure DDI — primary safety metric

$$
IncrementalExposureDDI@K(t)
=
\frac{
\sum_{m\in S_t}\sum_{a\in A_t}D_{ma}
+
\sum_{i<j,\ i,j\in S_t}D_{ij}
}
{K|A_t|+\binom{K}{2}}.
$$

Primary safety metric:

```text
IncrementalExposureDDI@5
```

`ActiveDDI@5` is the mechanism-specific secondary safety metric; `NewDDI@5` checks whether a method merely shifts risk between active-regimen and newly recommended pairs.

These are DDI exposure surrogates, not ADE, clinical-harm, or pharmacokinetic outcomes.

## 13. InnerTune selection contract

### 13.1 Safety budget

After training `Base`, compute its mean `IncrementalExposureDDI@5` on InnerTune $\mathcal Q$ exactly once:

$$
R_{Base}^{Tune}.
$$

Freeze the common target budget:

$$
B=0.90\,R_{Base}^{Tune}.
$$

No later method may redefine $B$.

### 13.2 Learned configuration selection

For `StaticLoss` and `ExposureConditional` separately:

1. train all four frozen lambda configurations on InnerTrain;
2. within each lambda, select the checkpoint with minimum InnerTune $L_{pred}$;
3. compute InnerTune `Recall@5` and primary risk on $\mathcal Q$;
4. among configurations with risk $\le B$, choose highest `Recall@5`;
5. tie-break by lower primary risk, then smaller lambda;
6. if no configuration reaches $B$, select the configuration with lowest primary risk, tie-break by higher Recall@5, and mark `TUNE_BUDGET_MISS`.

### 13.3 Direct reranker selection

For all seven frozen gamma settings:

1. apply the setting to the same frozen Base logits on InnerTune;
2. among settings with risk $\le B$, choose highest `Recall@5`;
3. tie-break by lower risk, then smaller gamma;
4. if none reaches $B$, select the lowest-risk setting, tie-break by higher Recall@5, and mark `TUNE_BUDGET_MISS`.

`ExposureHardConstraint` has no tuning.

### 13.4 Freeze before Dev

After this selection:

- selected checkpoints;
- selected lambdas;
- selected gamma;
- common $B$;
- all metric code;
- all task construction;

are immutable before any R0 Dev clinical/event/target/performance aggregate is computed.

## 14. Dev evaluation and uncertainty

Run each frozen method once on R0 Dev.

No Dev-derived hyperparameter, checkpoint, threshold, K, risk budget, or subgroup selection is permitted.

### 14.1 Bootstrap

Use paired patient-clustered bootstrap:

- resampling unit: `subject_id`;
- all bursts of a patient stay together;
- replicates: `2000`;
- seed: `260907`;
- confidence interval: two-sided 95% percentile interval.

For pairwise deltas, resample the same patient multiplicities for both methods.

Metric aggregation within a bootstrap replicate remains event/burst weighted after patient resampling.

## 15. Frozen Gate-01 PASS rule

Return:

`PASS_GATE01_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`

only if **all** conditions below hold on frozen R0 Dev $\mathcal Q$.

### Condition 1 — method reaches the preregistered Tune risk budget

The selected `ExposureConditional` configuration must not carry `TUNE_BUDGET_MISS`.

### Condition 2 — material and reproducible safety improvement over Base

At full precision:

$$
R_{EC}^{Dev}\le0.90\,R_{Base}^{Dev},
$$

where $R$ is mean `IncrementalExposureDDI@5`.

Additionally, for

$$
\Delta R_{EC-Base}=R_{EC}^{Dev}-R_{Base}^{Dev},
$$

the 95% patient-clustered bootstrap CI upper bound must be strictly below zero.

### Condition 3 — bounded fidelity cost versus Base

At full precision:

$$
Recall@5_{EC}^{Dev}-Recall@5_{Base}^{Dev}\ge-0.010.
$$

### Condition 4 — learned value beyond the direct exposure-aware killer control

Let `DirectExposureRerank` be the single InnerTune-selected gamma setting.

At full precision:

$$
R_{EC}^{Dev}\le R_{Rerank}^{Dev}+0.001,
$$

and

$$
Recall@5_{EC}^{Dev}-Recall@5_{Rerank}^{Dev}\ge+0.005.
$$

The 95% paired patient-bootstrap CI lower bound for

$$
Recall@5_{EC}^{Dev}-Recall@5_{Rerank}^{Dev}
$$

must be strictly above zero.

This is the primary scientific admission condition.

### Condition 5 — no required simple control weakly dominates the method

Neither `StaticLoss` nor `ExposureHardConstraint` may satisfy both:

$$
Recall@5_{control}^{Dev}\ge Recall@5_{EC}^{Dev}
$$

and

$$
R_{control}^{Dev}\le R_{EC}^{Dev},
$$

with at least one inequality strict at full precision.

If any one of Conditions 1–5 fails, return:

`STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`

No post-result threshold relaxation is allowed.

## 16. Interpretation boundaries

### PASS supports only

> In this frozen order-time MIMIC-IV task, end-to-end exposure-conditioned DDI learning creates a reproducible active-exposure safety/fidelity advantage that survives equal-entitlement direct exposure controls.

### PASS does not establish

- ADE reduction;
- prospective clinical safety;
- medication appropriateness;
- pharmacokinetic exposure;
- universal benefit across architectures/datasets;
- final paper acceptance or CCF-A readiness.

### FAIL means

The current simple learned mechanism did not establish scientific value beyond the strongest direct controls under the admitted exposure-localized safety semantics.

A FAIL terminates Idea 006's current method route. The R0 resource/premise result remains valid but cannot by itself serve as this project's target method paper.

## 17. No-rescue rule

After Gate-01 FAIL, do not rescue this route by adding:

- a GNN/Transformer/LLM risk encoder;
- personalized risk-tolerance modules;
- more DDI features or another DDI database;
- labs, vitals, dose, route, or notes;
- subcohort mining;
- variable output cardinality;
- alternative K, bootstrap, or risk budget;
- additional lambda/gamma grids;
- a hidden Gate 01b on the same mechanism.

Any scientifically different future route requires a new pipeline decision and a changed premise.

## 18. Result artifact contract

Gate execution must commit only public-safe aggregate artifacts under this Idea:

- `experiments/run_gate01_exposure_conditioned_learning.py` or a small idea-local module set if one file becomes unreasonably deep;
- `experiments/gate-01-summary.json`;
- `experiments/gate-01-decision.md`;
- `experiments/gate-01-integrity-audit.md`.

The summary must include:

- exact source revision and MIMIC-IV version;
- R0 mapping/DDI identities;
- patient/burst counts for InnerTrain, InnerTune, R0 Dev, and primary $\mathcal Q$;
- selected batch size;
- all frozen training hyperparameters;
- all four StaticLoss Tune rows;
- all four ExposureConditional Tune rows;
- all seven DirectExposureRerank Tune rows;
- selected configs and common Tune safety budget;
- Dev metrics for all required methods at K=5 and secondary K=10;
- paired bootstrap intervals for all gating deltas;
- exact Conditions 1–5 booleans;
- final verdict.

No raw patient rows, subject IDs, timestamps, local private paths, checkpoints, restricted event payloads, or Holdout/test artifacts may be committed.

## 19. Integrity audit

After execution, run `ccf-integrity-auditor` in at least:

- `claim-audit`;
- `numeric-audit`;
- leakage/quarantine audit appropriate to this Idea.

Audit must confirm:

- Base/Static/EC architecture and features are identical;
- direct controls receive the same $A_t,D$ entitlement;
- all primary outputs have fixed K=5;
- no Dev adaptation occurred;
- no Holdout/test access occurred;
- D/C state uses only pre-$t$ discontinuation transactions;
- target burst starts at $t$ while all features are `<t`;
- JSON/markdown values and decision booleans agree at full precision;
- safety surrogates are not described as ADE/clinical safety.

## 20. Routing

### If PASS

Next owner: `ccf-pipeline-orchestrator`.

The next scientific stage is broader claim-support design, not immediate Holdout/test evaluation. A later protocol should add at least one materially different causal predictor family and determine when the quarantined Holdout can be consumed.

### If FAIL

Record `STOP_NO_INCREMENTAL_EXPOSURE_CONDITIONED_LEARNING`, terminate Idea 006, preserve R0 as a resource/measurement lesson, and return to `ccf-pipeline-orchestrator`.

Do not create a rescue experiment in the same run.
