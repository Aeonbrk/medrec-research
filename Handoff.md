# Handoff: STAGE -1 — MICA Core consolidation + MIMIC-IV readiness

Updated: 2026-09-16.

## Current authoritative state

```text
Stage: STAGE -1 — MICA CORE CONSOLIDATION + TRAINING DIAGNOSIS + MIMIC-IV READINESS
Status: PRE-IDEA / PRE-GATE / NO PAPER CLAIM / NO HOLDOUT TEST / NO NEW METHOD FAMILY
AUTHORITATIVE_START_REVISION: de07bc22b8f05272b62417b769307dfb22754435
FINAL_REVISION: final Stage -1E materialization commit (see final report)
Active formal Idea: none
Idea 009: not created
Active formal Gate: none
```

Stage -1E is complete for its bounded scope. No Test target partition was
opened, no model or new seed was run, no new method family was added, and no
paper or novelty claim follows.

## Stage -1A — training diagnosis

[`research/diagnostics/mica-training-dynamics/diagnosis.json`](research/diagnostics/mica-training-dynamics/diagnosis.json)
classifies the available progress as `OVERFIT_DOMINANT`. Fifteen complete
MICA/MICA-v2/Dynamic Query arms were available: twelve peak at epoch 3 and
three at epoch 4. With 10,489 Train visits and batch 16, this is about 1,968
and 2,624 optimizer updates. Train total/BCE objectives continue to fall (DDI
loss is retained in the curve file) while Dev NLL rises and Dev Jaccard/PRAUC
fall. SafePTO had no epoch-level progress and was not classified. The common
recipe/encoder dynamics are the supported explanation; the prior DrugQuery
architecture verdict is unchanged.

## Stage -1B — training recipe

The three complete recipe arms are recorded in
[`recipe-result.json`](research/prototypes/mica-core-consolidation/recipe-result.json).
Constant AdamW `1e-4` (`t1_lower_constant`) was selected for Stage -1C: its
peak Jaccard is `0.542280` versus anchor `0.542244`, peak PRAUC remains within
the `0.002` floor, and all late Jaccard/PRAUC/NLL drift measures are lower than
the anchor. Cosine decay was not selected because its NLL drift was larger.

## Stage -1C — intrinsic Core controls

All four controls completed 60 epochs with the selected recipe and are
summarized in
[`consolidation-result.json`](research/prototypes/mica-core-consolidation/consolidation-result.json).
The predeclared decision is `KEEP_EXISTING_MICA_CORE`: OneClinicalBlock misses
the PRAUC floor and has worse late J/PRAUC degradation; NoPostReadConditioner
is slightly worse on late PRAUC drop despite fewer parameters; SimplifiedHead
misses both peak floors. No intrinsic simplification is promoted.

## Stage -1D/-1E — MIMIC-IV readiness and materialization

The frozen protocol is a dataset-native visit-level task:
`(current diagnoses, current procedures, strictly previous visit
diagnosis/procedure/medication history) -> current medication set`. It uses
patient-level `2/3, 1/6, 1/6` roles, target-only current medications,
versioned deterministic NDC/formulary → RxNorm → ATC4 normalization, fixed
MICA metrics/threshold/checkpoint semantics, and pre-training leakage/split/
DDI checks. Stage -1E materialized this contract on 319 with adapter revision
`e87411be3df305f55a4a68d10a9db3eb505e1232`.
The public manifest digest is
`110090bb79411ecf9f8057e75e16a1f6cb0c0e4b4e159bc29d4434018628da23`.

The public-safe manifest freezes 149,001 Train patients / 364,492 visits /
308,824 examples and 37,076 Dev patients / 90,033 visits / 76,529 examples.
Train normalization coverage is `0.785936`, Dev coverage `0.785400`, Dev
medication-target OOV is `0.0`, and the 131-concept / 448-pair SafeDrug/MoleRec
DDI authority represents 129 of 131 source concepts, retains 90 of 91
DDI-supported concepts, and projects 443 of 448 pairs on the 173-concept Train
vocabulary. All required mechanical checks pass. Test membership is sealed by
count/digest only; no Test medication target was loaded or evaluated.

The terminal status is `MIMIC_IV_BENCHMARK_FROZEN_READY_FOR_TRAINDEV`; see the
[`public-safe benchmark record`](research/benchmarks/mimiciv-medrec/README.md).

## One next action

Review the prepared MIMIC-IV Train/Dev SharedPool versus MICA-Core/DrugQuery
screen contract. Do not run it automatically or enter Stage 0.

---

# Historical handoff: MICA Dynamic-Query Screen Complete — Family Killed

The remainder of this file is retained as historical execution context. Its
older routing text is superseded by the current Stage -1 handoff above.

Updated: 2026-09-16.

The verified starting `origin/main` for this preparation was
`abe01977e1d8838d0291ad195e5027883c0e86a1`. The execution starting
`origin/main` was `cf6e17b7325b43a197babcd8d0fbdb0aa19d1623`; a scoped
execution fix was committed and pushed as
`5083cdba2e02067f949e8a6fe0c4dcf2f323748b`, which is the run revision. Public
evidence was recorded in a later documentation commit on `origin/main`.

The previous six-lane MICA-v2 screen is complete and remains frozen. Its conclusion is `KEEP_MICA_CORE_AND_RETURN_TO_MATERIAL_ARCHITECTURE_SEARCH`.

A new additive bounded prototype was executed at:

`research/prototypes/mica-dynamic-query-screen/`

Scientific question:

> Should the medication query itself change with the current patient's clinical evidence, beyond MICA-Core's already patient-dependent keys/values?

This preparation deliberately avoids strong latent-route semantics and does not use counterfactual route teachers, route competition, NULL routes, safety decoders, or hyperparameter sweeps.

Six authorized Train/Dev lanes are:

```text
core
static_multiquery
global_dynamic_multiquery
evidence_dynamic_multiquery
static_query_adapter
dynamic_query_adapter
```

The primary matched mechanism deltas are:

```text
GlobalDynamicMultiQuery - StaticMultiQuery
EvidenceDynamicMultiQuery - StaticMultiQuery
DynamicQueryAdapter - StaticQueryAdapter
```

The two static controls separate dynamic conditioning from extra capacity. The adapter pair additionally tests patient-conditioned query generation without any latent-route assumption.

Frozen common configuration remains the successful MICA configuration: seed `20260914`, hidden dim `128`, two clinical blocks, four heads, FFN `256`, batch `16`, full `60` epochs, AdamW `3e-4`, weight decay `1e-4`, BCE + `0.05` normalized DDI penalty, fixed sigmoid threshold `0.35`, highest complete-Dev Jaccard with strict improvement and earliest exact tie, float32 with TF32 disabled and deterministic cuDNN.

All six lanes used the one clean immutable run revision. The data-contract and
synthetic CUDA preflights passed after the scoped fix. The remote route was
`319-lab-via-server`, with Python `3.8.16`, PyTorch `1.9.0+cu111`, NumPy
`1.23.5`; actual GPU mapping was Core→0, StaticMultiQuery→1,
GlobalDynamicMultiQuery→2, EvidenceDynamicMultiQuery→3,
StaticQueryAdapter→4, and DynamicQueryAdapter→6. GPU 5 was occupied by an
unrelated process and was not touched. Every lane completed all 60 epochs.

Frozen mechanism interpretation:

```text
matched Delta J <= 0.002       -> no material dynamic contribution
0.002 < Delta J <= 0.004       -> weak; not a survivor
Delta J > 0.004                -> meaningful mechanism signal
Delta J >= 0.008               -> strong signal
```

A dynamic arm survives only if it also reaches at least the same-revision Core Jaccard, loses no more than `0.002` F1/PRAUC, and worsens DDI by no more than `0.002`.

Do not create Idea 009, open a formal Gate, use Audit/G3/G4/R0 Holdout or historical test, add seeds, tune K/adapter width/loss/LR/DDI weight/threshold, or start a rescue cycle from this handoff.

The six results were summarized with `summarize_dynamic_query.py` and the
public-safe aggregate is recorded in
`research/prototypes/mica-dynamic-query-screen/result.json`. Stop here for
scientific review; do not start a follow-up experiment automatically.

Frozen result:

```text
GlobalDynamicMultiQuery - StaticMultiQuery ΔJ = -0.000678623
EvidenceDynamicMultiQuery - StaticMultiQuery ΔJ = -0.000560345
DynamicQueryAdapter - StaticQueryAdapter ΔJ = -0.000729051
decision = KILL_PATIENT_CONDITIONED_QUERY_FAMILY
next route = KEEP_MICA_CORE_AND_RETURN_TO_MATERIAL_ARCHITECTURE_SEARCH
```

Current routing:

```text
Active formal Idea: none
Formal Gate: none
Held-out architecture selection: forbidden
MICA-Core DrugQuery: preserved strong substrate
MICA-v2 extensions: closed
MICA dynamic-query screen: complete; patient-conditioned query family killed
Next owner: material architecture search after scientific review
```
