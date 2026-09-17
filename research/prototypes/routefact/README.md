# RouteFact bounded mechanism screen

## Scientific question

This prototype tests one architecture-level hypothesis on the frozen
`mimic-iii-canonical-131-paper-dev-v1` development surface:

> Does preserving the observed administration-route distinction as a
> medication-level intermediate decision object improve recorded medication-set
> prediction beyond using exactly the same route labels only as auxiliary
> supervision?

The screen is not a revival of RxUnitSet. RxUnitSet required a single stable
`(drug,dose,route)` admission unit or causally aligned prescription episode and
was correctly terminated. Its own supportability evidence nevertheless showed
that route itself is almost fully observed and genuinely non-degenerate: route
coverage was ~100%, 62 Train route classes were observed, median per-medication
route entropy was 1.0573 bits, and many admission-medication pairs contained
multiple routes. RouteFact therefore models a **multi-hot route set conditional
on medication**, not one unique route, dose, or temporal episode.

## Frozen two-arm comparison

Both arms use the same target-free MICA DrugQuery clinical path, the same
medication embeddings, the same medication-route head, the same Train-only
route vocabulary/support mask, the same route labels, the same loss weights,
and exactly the same parameter count.

- `route_aux` (matched control): DrugQuery produces the medication score through
  the ordinary direct medication head. Medication-route logits receive the
  same auxiliary route supervision but do not determine medication presence.
- `route_fact` (candidate): DrugQuery produces medication-route logits and the
  medication probability is **forced through** a fixed noisy-OR across the
  Train-supported routes for that medication. The direct medication head stays
  instantiated only to preserve exact parameter matching and is outside the
  medication decision path.

For medication `m` and its Train-supported route coordinates `R_m`:

```text
p_imr = sigmoid(a_imr)
P(y_im = 1 | X_i) = 1 - product_{r in R_m} (1 - p_imr)
```

`<UNSPECIFIED_ROUTE>` is a frozen fallback coordinate, but it is **not**
allowed for every medication. It is enabled only for medications whose Train
positive pairs genuinely require a fallback (or have no real Train route
coordinate at all). This prevents the factorized arm from learning a generic
"unspecified route = medication present" shortcut. Dev never expands the
Train-frozen support mask.

The route vocabulary, per-medication support mask, and route supervision are
derived from **Train only**. Dev raw prescription-route labels are not read.
Dev contributes only the frozen canonical medication targets used by the common
paper evaluator. Test is never loaded.

## Training contract

- dataset: `mimic-iii-canonical-131-paper-dev-v1`
- seed: `20260922`
- 60 complete epochs
- batch size: 16 visits
- AdamW, learning rate `1e-4`, weight decay `1e-4`
- gradient clipping: 5
- float32, TF32 disabled, deterministic cuDNN policy
- loss: medication BCE + `0.10 * route BCE + 0.05 * normalized DDI`
- joint Dev checkpoint / global medication threshold selection over
  `0.05, 0.10, ..., 0.95`
- primary metric: Dev patient-macro Jaccard
- no route threshold is tuned; route predictions are an intermediate training
  object, not a second Dev selection surface

The route BCE is evaluated only on Train-supported medication-route
coordinates. Negative medications contribute all-zero route labels; positive
medications have one or more observed routes or the explicit unspecified
fallback.

## Decision rule

```text
Delta J = J(RouteFact) - J(RouteAux)

Delta J <= +0.002
    KILL_ROUTEFACT_MECHANISM

+0.002 < Delta J <= +0.004
    WEAK_ROUTEFACT_SIGNAL_STOP_NO_RESCUE

Delta J > +0.004 and F1/PRAUC are not worse by > 0.002
    advance as a meaningful mechanism signal

Delta J >= +0.008
    strong signal
```

DDI and medication cardinality are reported jointly. This is not a safety
mechanism screen, so there is no predeclared DDI-only rescue. A negative result
receives no route taxonomy merge, route-loss sweep, dose extension, second
seed, or RouteFact-v2.

## Private route-target materialization on 319

Run from the **final clean RouteFact implementation revision**. Outputs remain
outside Git.

```bash
conda run --no-capture-output -n medrec-molerec-table1 \
  python research/prototypes/routefact/build_route_targets.py \
  --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
  --canonical-data /root/zhb/SafeDrug-c7218d0/data/data_final.pkl \
  --mimic-root /root/zhb/Search/dataset/mimic-iii-1.4 \
  --mapping-dir /root/zhb/SafeDrug-c7218d0/data \
  --source-revision <ROUTEFACT_REVISION> \
  --output-dir /root/zhb/medrec-data/prototypes/routefact/route-targets
```

The builder verifies canonical visit/target alignment, reuses the SafeDrug c721
NDC -> RxNorm -> ATC4 lineage, freezes route vocabulary/support from Train
only, and writes dense uint8 Train route targets plus hashes and aggregate
metadata. No patient/admission identifiers are written; Dev raw route labels
are not read.

## Preflight

`run_routefact_trainonly.py` is the execution entrypoint. It is a thin
mechanical wrapper around the frozen training runner that enforces the intended
Train-only route-asset contract and rejects any `dev_route_targets.npy`.
Use the same route-target directory for both arms:

```bash
for VARIANT in route_aux route_fact; do
  CUDA_VISIBLE_DEVICES=0 \
  conda run --no-capture-output -n medrec-molerec-table1 \
    python research/prototypes/routefact/run_routefact_trainonly.py \
    --variant ${VARIANT} --seed 20260922 \
    --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
    --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
    --route-target-root /root/zhb/medrec-data/prototypes/routefact/route-targets \
    --source-revision <ROUTEFACT_REVISION> \
    --output-dir /tmp/routefact-preflight-${VARIANT} \
    --preflight-only
done
```

Require both preflights to report the same `parameter_count`, the same
route-target metadata hash, finite forward/backward, exact frozen split counts,
and `test_loaded=false`.

## Full Train/Dev screen

After preflight, launch both arms concurrently on separate 3090s:

```bash
CUDA_VISIBLE_DEVICES=0 \
conda run --no-capture-output -n medrec-molerec-table1 \
  python research/prototypes/routefact/run_routefact_trainonly.py \
  --variant route_aux --seed 20260922 \
  --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
  --route-target-root /root/zhb/medrec-data/prototypes/routefact/route-targets \
  --source-revision <ROUTEFACT_REVISION> \
  --output-dir /root/zhb/medrec-data/prototypes/routefact/20260922/route_aux &

CUDA_VISIBLE_DEVICES=1 \
conda run --no-capture-output -n medrec-molerec-table1 \
  python research/prototypes/routefact/run_routefact_trainonly.py \
  --variant route_fact --seed 20260922 \
  --snapshot-root /root/zhb/medrec-data/snapshots/molerec-table1-c721-www23 \
  --train-dev-root /root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a \
  --route-target-root /root/zhb/medrec-data/prototypes/routefact/route-targets \
  --source-revision <ROUTEFACT_REVISION> \
  --output-dir /root/zhb/medrec-data/prototypes/routefact/20260922/route_fact &
wait
```

Then summarize:

```bash
python research/prototypes/routefact/summarize_routefact.py \
  --route-aux /root/zhb/medrec-data/prototypes/routefact/20260922/route_aux/results.json \
  --route-fact /root/zhb/medrec-data/prototypes/routefact/20260922/route_fact/results.json \
  --output /root/zhb/medrec-data/prototypes/routefact/20260922/comparison.json
```

Only the public-safe aggregate comparison and decision record should later be
committed. Checkpoints, logits, dense route targets, raw prescription rows, and
patient/admission-level material remain outside Git.
