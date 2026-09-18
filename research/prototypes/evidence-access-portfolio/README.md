# Evidence-access architecture portfolio screen

Status: **PORTFOLIO EXECUTED / COMPLETED (2026-09-18)**

This directory defines one bounded eight-lane DEVELOPMENT screen on the canonical MIMIC-III 131-medication Train/Dev profile. It uses four matched candidate/control pairs to test four orthogonal bottlenecks between longitudinal EHR evidence and a candidate-medication decision.

It is not Idea 009, not a formal paper claim, not a hyperparameter sweep, and does not authorize Test access.

## Why this portfolio

The strongest repeated positive project evidence is medication-specific evidence access (`DrugQuery` over `SharedPool`). The current MICA implementation already isolates this reasonably well: both arms use the same clinical encoder, attention read/key/value maps, medication embeddings, conditioner and prediction head; `SharedPool` uses one medication-independent mean-medication query, while `DrugQuery` uses one query per medication. The positive direction also repeated under two matched MIMIC-III development seeds.

Therefore no GPU is allocated to re-test `SharedAttn` versus `DrugQuery`.

The portfolio instead asks where a still-unresolved bottleneck remains:

```text
temporal placement     medication identity before vs after temporal compression
resolution             medication read after visit pooling vs at code resolution
interaction depth      refine state only vs use the refined state to re-read evidence
prediction granularity aggregate local interactions before prediction vs predict locally then aggregate
```

## Closest-work boundaries

Primitive novelty is not assumed.

- **MeSIN** (Knowledge-Based Systems 2021, DOI `10.1016/j.knosys.2021.107534`) already uses medication-relevance attention over medical codes inside admissions and an interactive LSTM, then fuses sequences to a final patient representation. Therefore code-level medication-aware selection and medication relevance before temporal modeling are occupied primitives. A temporal survivor would need the narrower model-level claim that candidate-specific longitudinal states remain separate through the final medication decision.
- **VITA** (AAAI 2024, DOI `10.1609/aaai.v38i8.28704`) explicitly performs relevant-past-visit selection and current-target-aware history attention. Current-state history filtering is therefore not included as a paper-identity lane.
- **HI-DR** (AAAI 2025, DOI `10.1609/aaai.v39i11.33301`) further occupies health-status-aware historical medication selection.
- **ARMR** (IJCAI 2025, DOI `10.24963/ijcai.2025/871`) uses recent/distant temporal modeling and adaptive treatment of new/existing drugs.
- **SubRec** (NeurIPS 2025) uses patient-drug interaction prototypes/codebooks, reducing the value of another latent multi-state/prototype lane.
- The project's own anonymous slots, multi-query, pairwise/set-context, semantic-route and cardinality screens provide additional negative evidence against latent intermediates and output-side correction families.

A positive first screen is mechanism evidence only. Any survivor requires a second primary-source closest-work audit before Paper Candidate Freeze.

## Shared substrate

All eight arms instantiate the exact same parameter set and use the exact same input packer.

Legal evidence for visit `t`:

```text
history visits j < t: diagnosis + procedure + medication codes
current visit t:       diagnosis + procedure codes only
current medications:   target only; never model input
```

Representation:

- hidden dimension 128;
- 4 attention heads;
- two shared within-visit Transformer-style clinical blocks;
- typed code embeddings;
- sinusoidal visit-lag encoding;
- one learned contextual anchor per real visit;
- one medication embedding table shared with historical medication codes;
- dropout 0.1;
- explicit medication-persistence features available identically to both arms of every pair:
  - medication in immediately previous visit;
  - fraction of historical visits containing the medication;
  - reciprocal visits-since-last-use.

The persistence features intentionally neutralize the simplest medication-copying explanation for the temporal pair.

All variants currently instantiate **865,543 trainable parameters**. Matched controls and candidates must start from tensor-identical initialization under the canonical RNG convention.

## Pair 1 — MedTemporal

### Scientific question

Should medication identity enter before longitudinal compression rather than only after it?

### `temporal_shared` control

```text
within each historical visit
  -> medication-independent learned attention pool
  -> one visit vector
visit vectors
  -> shared GRUCell over time
  -> one shared history state h

current D/P visit
  -> medication-specific read g_m

[g_m, h, drug_m, persistence_m]
  -> medication logit
```

### `temporal_med` candidate

```text
within each historical visit j
  -> static medication query q_m reads visit codes
  -> e_{m,j}

for every medication m:
e_{m,1}, ..., e_{m,t-1}
  -> same shared GRUCell weights
  -> h_m

current D/P visit
  -> same medication-specific read g_m

[g_m, h_m, drug_m, persistence_m]
  -> medication logit
```

Exact scientific difference: medication-specific evidence selection occurs **before** versus **after** temporal compression. No patient-conditioned query generator is used.

MeSIN prevents a broad novelty claim about medication-relevant pre-temporal attention. The narrower survivor claim would concern preserving candidate-specific longitudinal states to the output rather than fusing them back into one patient representation.

## Pair 2 — MedResolution

### Scientific question

Does medication-specific selection need code-level evidence, or is visit-level compression sufficient?

### `resolution_visit` control

```text
fine code tokens
  -> medication-independent within-visit attention pool
  -> visit vectors
  -> medication-specific read across visits
  -> medication logit
```

### `resolution_code` candidate

```text
same fine code tokens
  -> no visit pooling
  -> medication-specific read directly over all legal code tokens
  -> medication logit
```

The information budget is identical; the control's visit vectors are computed only from the exact code tokens available to the candidate.

This is primarily a mechanism screen, not a novelty claim. MeSIN and other fine-grained EHR models already occupy code-level attention as a primitive.

## Pair 3 — MedDepth

### Scientific question

After one medication-specific read, is there value in using the updated medication state to ask follow-up questions of the clinical evidence?

Both arms first perform the same medication-specific read and form the same first-hop medication state.

### `depth_state` control

Two additional CrossHop modules update each medication state using only its own frozen first-hop context as a one-token memory.

### `depth_reread` candidate

The exact same two CrossHop modules use the updated medication state to re-attend the complete clinical evidence memory at every hop.

Exact scientific difference: **same-depth state transformation** versus **iterative evidence re-access**. This is not a mere depth comparison.

## Pair 4 — MedPrediction

### Scientific question

Is forcing all medication-token interactions through an aggregated patient context itself a remaining bottleneck?

Both arms compute identical medication-token interaction hidden states:

```text
h_{m,i} = GELU(W(q_m elementwise-multiplied-by k_i))
```

### `prediction_aggregate` control

```text
{h_{m,i}}
  -> masked mean hidden aggregation
  -> shared scalar output map
  -> medication logit
```

### `prediction_local` candidate

```text
h_{m,i}
  -> shared scalar local potential for every token
  -> masked log-mean-exp over token potentials
  -> medication logit
```

The local interaction modules and scalar output map are shared. The difference is whether evidence is aggregated **before** or **after** local medication-specific prediction.

This pair tests prediction granularity; a survivor still needs a dedicated closest-work audit against label-wise/local-interaction prediction methods.

## Frozen DEVELOPMENT protocol

```text
profile:  mimic-iii-canonical-131-paper-dev-v1
Train:    4,233 patients / 10,489 visits
Dev:      1,004 patients / 2,130 visits
Test:     SEALED

epochs:   60 complete epochs
batch:    16 visits
optimizer: AdamW
lr:       1e-4
weight decay: 1e-4
clip:     5.0
loss:     BCE + 0.05 * normalized DDI penalty

selection:
complete Dev after every epoch
thresholds 0.05 ... 0.95
joint checkpoint / threshold selection by patient-macro Jaccard
native threshold tie-break = 0.35
```

Canonical project-owned DEVELOPMENT RNG:

```python
torch.manual_seed(1203)
torch.cuda.manual_seed_all(1203)
np.random.seed(2048)
random.seed(1203)
```

One initial convention only. No additional seeds until a mechanism survives.

## Decision rule

For each candidate minus its own matched control:

```text
Delta J <= +0.002
  -> KILL_NO_MATERIAL_SIGNAL

+0.002 < Delta J <= +0.004
  -> WEAK_STOP

Delta J > +0.004
  and Delta F1 >= -0.002
  and Delta PRAUC >= -0.002
  and Delta DDI <= +0.002
  -> MECHANISM_SIGNAL

Delta J > +0.004 but guardrail failure
  -> SIGNAL_WITH_SUPPORTING_METRIC_COST
```

No automatic combination follows. If multiple mechanisms survive, arbitrate them scientifically before any A+B model.

## Decision-relevant preflight only

`preflight_portfolio.py` checks:

- exact profile / snapshot / target-array hashes;
- clean immutable source revision;
- current target medication exclusion from model payload;
- finite CUDA forward/backward for all eight variants on a high-load real Train batch;
- exact parameter-count matching within each pair;
- exact tensor-identical initial state within each pair;
- each pair is behaviorally active on history-bearing examples;
- `temporal_shared` and `temporal_med` are numerically equivalent when no history exists.

Do not add broad smoke/regression infrastructure before the screen.

## GPU assignment

```text
GPU 0  temporal_shared
GPU 1  temporal_med
GPU 2  resolution_visit
GPU 3  resolution_code
GPU 4  depth_state
GPU 5  depth_reread
GPU 6  prediction_aggregate
GPU 7  prediction_local
```

All eight jobs must use one clean immutable revision.

## Execution

Run the preflight once, then use `launch_8gpu.sh`. Private checkpoints, logits and logs stay outside Git. After all eight jobs finish, use `summarize_portfolio.py` to produce the aggregate matched comparison.

No Test access, no HPO, no additional seed, no early scientific redesign, and no automatic compound model are authorized by this screen.

## Terminal portfolio results (2026-09-18)

Executed on the 319 Execution Plane across 8 physical RTX 3090 GPUs (0–7) in parallel from clean detached worktree revision `aec07f311c5fc2f137d07bb172b67e12a89eeee3` (starting authoritative revision `ecf32d7737f855e3ac713c5e3b694a8b3d845f49`, preflight bug fixed in `aec07f311c5fc2f137d07bb172b67e12a89eeee3`). All 8 variants instantiate exactly 1,295,367 trainable parameters and completed all 60 epochs under canonical RNG (`torch=1203`, `cuda=1203`, `random=1203`, `numpy=2048`). Test strictly sealed (`test_loaded = false`).

### Matched-pair results

| Pair | Control (Selected Ckpt / OP) | Candidate (Selected Ckpt / OP) | Control J | Candidate J | ΔJ | ΔF1 | ΔPRAUC | ΔDDI | ΔAvgMed | Verdict |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **Temporal** | `temporal_shared` (Ep 3 / 0.30) | `temporal_med` (Ep 3 / 0.30) | 0.544485 | 0.544932 | +0.000447 | +0.000415 | -0.000049 | +0.000292 | -0.0053 | **`KILL_NO_MATERIAL_SIGNAL`** |
| **Resolution** | `resolution_visit` (Ep 7 / 0.35) | `resolution_code` (Ep 5 / 0.30) | 0.535091 | 0.546626 | **+0.011536** | +0.010238 | +0.007785 | -0.005589 | +0.4715 | **`MECHANISM_SIGNAL`** |
| **Depth** | `depth_state` (Ep 5 / 0.35) | `depth_reread` (Ep 4 / 0.35) | 0.547115 | 0.551259 | **+0.004144** | +0.003790 | +0.005406 | -0.000731 | +0.3433 | **`MECHANISM_SIGNAL`** |
| **Prediction** | `prediction_aggregate` (Ep 5 / 0.35) | `prediction_local` (Ep 3 / 0.35) | 0.535935 | 0.548911 | **+0.012976** | +0.011286 | +0.009895 | +0.003843 | -0.3692 | **`SIGNAL_WITH_SUPPORTING_METRIC_COST`** |

### Absolute candidate performance

| Candidate | Dev Jaccard | Dev F1 | Dev PR-AUC | Dev DDI Rate | Avg Med Count |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `temporal_med` | 0.544932 | 0.697154 | 0.788846 | 0.078785 | 20.8596 |
| `resolution_code` | 0.546626 | 0.698386 | 0.792678 | 0.071069 | 21.4289 |
| `depth_reread` | 0.551259 | 0.702581 | 0.796649 | 0.071966 | 20.7648 |
| `prediction_local` | 0.548911 | 0.700462 | 0.794832 | 0.075148 | 19.9647 |

### Scientific takeaways

1. **Temporal placement falsified**: Feeding candidate medication identity into history before longitudinal compression (`temporal_med`) yielded only $\Delta J = +0.000447$ over shared history (`temporal_shared`). When explicit medication persistence features (previous-visit presence, frequency, recency) are provided, pre-temporal medication tracking does not add value.
2. **Code resolution validated**: Direct medication-specific attention over fine clinical code tokens (`resolution_code`) beats within-visit pooling (`resolution_visit`) by $\Delta J = +0.011536$, with favorable guardrails across all dimensions ($\Delta \text{F1} = +0.0102$, $\Delta \text{PR-AUC} = +0.0078$, $\Delta \text{DDI} = -0.0056$).
3. **Iterative evidence re-access validated**: Using updated medication states to re-attend clinical evidence memory (`depth_reread`) beats state-only refinement (`depth_state`) at identical parameter count and depth by $\Delta J = +0.004144$ ($\Delta \text{F1} = +0.0038$, $\Delta \text{PR-AUC} = +0.0054$, $\Delta \text{DDI} = -0.0007$). The candidate achieves the highest absolute Jaccard in the portfolio ($0.551259$).
4. **Prediction granularity trade-off**: Local token-interaction potentials (`prediction_local`) achieve strong Jaccard gain ($\Delta J = +0.012976$) over aggregate hidden state pooling, but incur a DDI penalty ($\Delta \text{DDI} = +0.003843 > +0.0020$). Classified as `SIGNAL_WITH_SUPPORTING_METRIC_COST`.

### Portfolio routing

```text
MULTIPLE_SURVIVORS_ARBITRATE_BEFORE_ANY_COMBINATION
```

Survivors: `resolution` (`resolution_code`), `depth` (`depth_reread`).
Per the frozen contract, no automatic A+B combination is authorized. The surviving mechanisms must be arbitrated scientifically before any compound architecture is trained.

Artifact: `research/prototypes/evidence-access-portfolio/result.json`.
Decision record: `research/memory/decisions/2026-09-18-evidence-access-portfolio-screen.md`.
