# Handoff: MICA Dynamic-Query Screen Complete — Family Killed

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
