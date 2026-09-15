# MICA Dynamic-Query Screen

Status: **prepared for one bounded six-GPU Train/Dev screen; not yet executed**.

Starting authoritative state for this preparation: `abe01977e1d8838d0291ad195e5027883c0e86a1`.

This prototype is additive. It does not modify the completed `mica/` attribution or `mica-v2-screen/` evidence.

## 1. Why this experiment exists

The clean MICA attribution established `SharedPool 0.532430`, `DrugQuery 0.542244`, and `MICA-Late 0.541656`, so medication-specific evidence selection is a material architecture signal (`DrugQuery - SharedPool = +0.009814`). The later six-lane MICA-v2 screen did not produce a survivor from finer history, current/history dual streams, safe decision learning, or medication self-attention.

The next narrow question is:

> Should the query used by the same medication itself change with the current patient's clinical evidence?

MICA-Core already has patient-dependent attention because patient keys/values vary. The new hypothesis is stronger: the **query representation itself** may need to be patient-conditioned.

This screen deliberately avoids claims about identifiable indications, therapeutic modes, or true latent clinical routes. It excludes counterfactual route teachers, route competition, NULL routes, extra safety mechanisms, and hyperparameter sweeps.

## 2. Six lanes

All lanes use the exact MICA coarse current/history tokens, shared two-block clinical encoder, medication vocabulary, prediction head, loss, optimizer, decoder, seed, Train/Dev split, and 60-epoch budget unless explicitly changed below.

### `core`

Exact inherited MICA-Core DrugQuery anchor.

### `static_multiquery`

Each medication has `K=4` learned residual queries `q_mk = LN(raw_drug_m + delta_mk)`. All four independently read the same assembled clinical evidence. A learned per-medication but patient-independent `route_prior[m,k]` mixes the four contexts. This is the direct capacity control for the multi-query family.

### `global_dynamic_multiquery`

Exactly the same parameters and four route queries as `static_multiquery`. The fixed route prior is augmented by a patient global clinical summary computed from the same assembled token keys:

```text
route_logit_mk(x)
  = route_prior_mk
  + <Q(q_mk), mean_masked K(U(x))> / sqrt(d)
```

### `evidence_dynamic_multiquery`

Exactly the same parameters and four route queries as `static_multiquery`. Each route first reads clinical evidence. Its dynamic routing signal is the mean-normalized log-sum-exp of its route-to-token affinities:

```text
support_mk(x)
  = logsumexp_i affinity(q_mk, u_i)
    - log(number of valid clinical tokens)

route_logit_mk(x)
  = route_prior_mk + support_mk(x)
```

### `static_query_adapter`

No multi-route assumption. A parameter-matched low-rank adapter (`128 -> 32 -> 128`) modifies the single medication query using medication identity only. Its final projection is zero-initialized, so it starts exactly at MICA-Core.

### `dynamic_query_adapter`

Same adapter parameters and initialization as `static_query_adapter`, but the adapter input also contains the current patient clinical summary. This tests patient-conditioned query generation without latent-route semantics.

## 3. Primary matched deltas

```text
Delta_global
= J(global_dynamic_multiquery) - J(static_multiquery)

Delta_evidence
= J(evidence_dynamic_multiquery) - J(static_multiquery)

Delta_adapter
= J(dynamic_query_adapter) - J(static_query_adapter)
```

Supporting capacity deltas are `StaticMultiQuery - Core` and `StaticAdapter - Core`.

Interpretation:

- multi-query capacity gain without a dynamic delta does not support patient-conditioned queries;
- dynamic multi-query gain alone supports route-mixture-specific conditioning;
- dynamic adapter gain alone supports continuous patient-conditioned query generation and argues against unnecessary latent-route semantics;
- gains in both families provide stronger evidence for patient-conditioned medication queries as a general mechanism.

## 4. Frozen common experiment

```text
snapshot = molerec-table1-c721-www23
Train = 4233 patients / 10489 visits
Dev = 1004 patients / 2130 visits
medications = 131
seed = 20260914
hidden dim = 128
clinical blocks = 2
heads = 4
FFN = 256
batch = 16 visits
epochs = 60 complete epochs
AdamW, lr = 3e-4, weight decay = 1e-4
betas = (0.9, 0.999), eps = 1e-8, clip = 5.0
loss = BCE + 0.05 * normalized DDI penalty
decoder = sigmoid probability >= 0.35
checkpoint = highest complete-Dev Jaccard, strict improvement, earliest exact tie
float32, TF32 off, deterministic cuDNN
```

No sweep of `K`, adapter width, loss, LR, DDI weight, threshold, temperature, dropout, or budget is authorized.

## 5. Minimum preflight

Verify only failures that would invalidate the comparison:

```text
exact clean source revision
canonical snapshot/split/vocabulary/target alignment
Core exact parameter/state/output match to inherited MICA DrugQuery
static/global/evidence multi-query exact parameter/init match
static/dynamic adapter exact parameter/init match
zero-initialized adapter variants start at Core function
finite CUDA forward/backward
route_delta and route_prior receive nonzero gradients
query adapter receives nonzero gradient
```

No broad new test suite and no shortened scientific run.

## 6. Frozen decisions

Use the new same-revision `core` lane for absolute comparisons.

```text
Delta <= 0.002            -> no material dynamic contribution
0.002 < Delta <= 0.004    -> weak; not a survivor
Delta > 0.004             -> meaningful mechanism signal
Delta >= 0.008            -> strong signal
```

A dynamic arm survives only if:

```text
matched Delta J > 0.004
J(dynamic) >= J(core)
F1(dynamic) >= F1(core) - 0.002
PRAUC(dynamic) >= PRAUC(core) - 0.002
DDI(dynamic) <= DDI(core) + 0.002
```

Overall routing:

```text
all three dynamic deltas <= 0.002
-> KILL_PATIENT_CONDITIONED_QUERY_FAMILY

only a dynamic multi-query arm survives
-> SURVIVE_DYNAMIC_MULTIQUERY

only dynamic adapter survives
-> SURVIVE_CONTINUOUS_DYNAMIC_QUERY

multi-query dynamic + adapter both survive
-> SURVIVE_GENERAL_PATIENT_CONDITIONED_QUERY

matched Delta > 0.004 but candidate remains below Core
-> MECHANISM_SIGNAL_NO_PROJECT_HEADROOM

only weak deltas
-> WEAK_DYNAMIC_QUERY_NO_SURVIVOR
```

No automatic rescue, seed, counterfactual teacher, route competition, or second-stage combination follows.

## 7. Execution boundary

This is exploratory single-seed Train/Dev work. Forbidden: Idea 009, formal Gate, Audit, G3/G4, R0 Holdout, historical project test, additional seeds, sweeps, threshold tuning, counterfactual route teacher, route competition, NULL route, or safety decoder changes.

Use six currently admissible RTX 3090 GPUs in parallel, one complete lane per GPU, after rechecking actual capacity immediately before launch.

Files:

- `mica_dynamic_query.py`
- `run_dynamic_query.py`
- `preflight_dynamic_query.py`
- `summarize_dynamic_query.py`

No experiment result exists until full remote execution completes.
