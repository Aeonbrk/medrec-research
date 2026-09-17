# RouteFact bounded screen authorization — 2026-09-18

## Decision

`AUTHORIZE_ROUTEFACT_TRAIN_DEV_SCREEN`

DCPM is terminated. The next bounded architecture hypothesis changes prediction granularity rather than extending candidate-conditioned retrieval/routing.

RouteFact tests whether administration route should be a supervised intermediate decision object between DrugQuery evidence and the recorded medication label. The target is **multi-hot route set conditional on medication**, not a unique `(drug,dose,route)` unit and not a prescription episode. Therefore the earlier `KILL_RXUNIT_UNSUPPORTABLE_TARGET` decision does not apply: that decision required a stable unique dose-route unit or causally aligned episode context.

Existing RxUnit supportability evidence is sufficient to skip another route-discovery diagnostic: route was observed on ~100% of canonical rows; Train contained 62 normalized route classes; median per-medication route entropy was 1.0573 bits; multi-route admission-medication pairs were non-trivial. No new Dev/Test supportability scan is authorized.

## Frozen matched comparison

- dataset: `mimic-iii-canonical-131-paper-dev-v1`
- seed: `20260922`
- 60 complete epochs
- Test access: forbidden
- candidate: `route_fact`
- matched control: `route_aux`
- same DrugQuery substrate, medication-route head, Train-only route labels, loss weights, optimizer, and parameter count
- `route_aux`: direct medication head determines medication presence; route logits are auxiliary only
- `route_fact`: medication probability is forced through noisy-OR over Train-supported route logits
- route vocabulary/support/supervision: Train raw prescription rows only; Dev raw route labels are not read
- Dev selection: joint checkpoint/global medication threshold by patient-macro Jaccard under the paper contract

Decision boundary:

```text
Delta J <= +0.002                         -> KILL_ROUTEFACT_MECHANISM
+0.002 < Delta J <= +0.004               -> WEAK_ROUTEFACT_SIGNAL_STOP_NO_RESCUE
Delta J > +0.004 with F1/PRAUC >= -0.002 -> advance
Delta J >= +0.008                         -> strong signal
```

No route taxonomy merge, route-loss sweep, dose extension, second seed, or RouteFact-v2 is authorized after a negative screen.

## Implementation

Canonical implementation revision: `063b9646e55c8cb61639e35e934479f405ab2070`.

Execution instructions are in `research/prototypes/routefact/README.md`. Use `run_routefact_trainonly.py` as the runner; it enforces the strict Train-only route asset contract and rejects Dev route-target assets.
