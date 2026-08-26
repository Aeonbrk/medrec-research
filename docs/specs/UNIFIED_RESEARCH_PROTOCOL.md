# Unified Research Protocol

Protocol version: `1.0`

## Purpose

The Unified Research Protocol defines when medication-recommendation methods are scientifically comparable. It does not impose one model architecture and does not replace faithful upstream reproduction.

## Modes

Reproduction Mode preserves the pinned upstream source, data preparation, split, feature access, training, prediction, and evaluation semantics. Its records must name those semantics and may not be presented as Comparison Mode evidence.

Reproduction execution is organized around two decoupled concepts:

- **Reproduction Program**: Declares the upstream codebase revision, isolated Conda execution environment, dataset snapshot subdirectory, run root, required input assets, and audited entrypoints.
- **Reproduction Lane**: Binds a specific scientific baseline to a reproduction program, profile ID, and candidate hyperparameter configuration (e.g., candidate learning rates for model selection). Lanes allow parallel execution across isolated GPU workers while maintaining strict provenance.

Comparison Mode fixes the dataset snapshot, eligible cohort, patient-disjoint split, medication vocabulary, feature availability, prediction task, evaluation functions, adaptation budget, and provenance requirements before test evaluation. All compared methods cross the Prediction Record seam.

## Comparison contract

### Dataset identity

Each run references a public-safe Dataset Manifest built while split membership remains available on 319. The builder rejects patient overlap, duplicate eligible visits, and visits assigned outside their patient's split. The manifest records split aggregates, eligible-visit membership digests, medication-vocabulary identity, and protocol-relevant preparation without patient identifiers, rows, membership lists, or local paths. Restricted manifests derive membership digests with a private HMAC key that never leaves the Local Data Root.

The split unit is the patient. A patient may occur in exactly one of train, validation, or test. Split generation and all exclusions must be fixed before model selection. A Dataset Manifest identity change creates a different comparison cohort.

Medication-vocabulary identity uses SHA-256 over UTF-8 medication codes sorted lexicographically, with one code and one trailing newline per entry. Adapters validate every predicted code against the corresponding declared vocabulary before evaluation.

### Prediction task

The unit of prediction is one eligible visit. The target is a set of medication codes from the declared vocabulary. A method may use only features declared available at prediction time. Evaluation targets remain core-owned and are not sent to the prediction subprocess. The subprocess emits one target-free Adapter Prediction Payload per eligible visit. The core joins each payload to its split and target, then creates the Prediction Record used for evaluation. An abstention is an empty recommendation, not a missing payload.

Predicted medication codes must be unique. If scores are emitted, each predicted code has one finite score. Ordering must be deterministic; ties use medication-code order. The adapter rejects missing, duplicate, unknown, malformed, or extra visit payloads. It also rejects split, target, label, or ground-truth fields in subprocess output and rejects target-bearing request fields before launch.

### Baseline integrity

The Baseline Core remains unchanged in Comparison Mode. A Prediction Adapter may translate storage formats, identifiers, invocation details, and output representation. It may not alter model logic, training objectives, input information, decision thresholds, ranking rules, or post-hoc selection unless the same operation is a declared protocol operation applied to every method.

Any scientific modification creates a separate method identity. The Run Record must point to both the Pinned Baseline Source and the adapter revision.

### Adaptation budget

Before experiments begin, the experiment plan declares one Adaptation Budget for every compared method. It fixes the allowed hyperparameter search space, selection metric, number of trials or equivalent compute allowance, stopping rule, seed policy, and permitted mechanical integration work.

The test split cannot select thresholds, hyperparameters, checkpoints, seeds, prompts, post-processing, or routes. Exhausting the budget without a valid run is a result, not permission to grant one method more search.

## Evaluation

Primary set metrics are visit-macro Jaccard, precision, recall, and F1. Each visit contributes once. For a visit with target set `T` and prediction set `P`:

- Jaccard is `|P intersect T| / |P union T|`.
- Precision is `|P intersect T| / |P|`.
- Recall is `|P intersect T| / |T|`.
- F1 is the harmonic mean of precision and recall.

When both sets are empty, all four metrics equal `1.0`. When exactly one set is empty, all four metrics equal `0.0`. The aggregate is the arithmetic mean over eligible visits. Reports must also include eligible visit count and mean predicted medication count so abstention and set-size changes remain visible.

DDI rate, unsafe-visit rate, calibration, omission, continuation, and addition measurements may be registered secondary metrics when their inputs and aggregation are fixed in advance. They are retrospective computational measurements. None independently establishes clinical safety, treatment benefit, or causal validity.

## Selection and reporting

Validation data owns all model and route selection. The test split is evaluated only after configuration lock. Repeated test peeking invalidates Comparison Mode until an untouched test set or a prospectively defined correction is available.

Every mechanism claim must face the strongest predeclared simple control that could explain the same result. A method layered on an existing predictor must include the unchanged predictor. A route that changes risk trade-offs, medication count, or abstention must add the relevant fixed-penalty, count-matched, or abstention controls. These controls are conditional on the claimed mechanism, not a permanent architecture inherited from prior ideas. A safety filter applied to all methods is part of the protocol, not method innovation.

Results must report all predeclared seeds and failures. Selective seed removal, silent reruns, and choosing a favorable aggregation after evaluation are protocol violations.

## Public-safe records

Each accepted Comparison Mode execution emits an immutable Run Record containing protocol version, source identity, the authoritative baseline-definition digest, adapter revision, environment digest, Dataset Manifest digest, eligible test-visit digest, Adaptation Budget digest, configuration identity, seed, readiness state, aggregate metrics, and artifact checksums. Parsing an accepted record requires the authoritative Baseline Registry entry and Dataset Manifest; self-declared readiness is insufficient. A Run Record must not contain rows, patient or visit identifiers, local paths, hostnames, credentials, environment variables, or restricted artifact locations.

The repository does not yet accept Reproduction Mode Run Records. No real baseline has completed upstream-semantics characterization, and a generic Comparison Mode-shaped record would misstate reproduction evidence. The first completed reproduction must define its upstream split, selection, evaluation, and artifact semantics before this schema is added.

A Protocol Check Record comes from public synthetic fixtures. It verifies software wiring only and cannot support a method, reproduction, comparison, safety, or clinical claim.

Raw Prediction Records are restricted when they derive from real EHR data. Only synthetic Prediction Records may be committed.

## Comparison readiness

A baseline may advance from `registered` to `smoke_ready` after its pinned source and environment execute through the process seam. Structured Readiness Evidence must bind both the environment lock and adapter smoke to artifact checksums. `comparison_ready` means that at least one Comparison Qualification exists. Each qualification binds the protocol version, Dataset Manifest digest, Adaptation Budget digest, cohort identity, unchanged Baseline Core behavior, deterministic adapter translation, and independent aggregate evaluation. Qualification in one scope does not transfer to another dataset or budget. A readiness string and free-form note do not satisfy these gates.

GAMENet and SafeDrug are not `comparison_ready` in the initial repository. Registration or a successful import does not make them comparable.

## Research gates

A research question progresses through protocol definition, experiment planning, execution, integrity audit, result-to-claim review, and writing. A stage may consume only gate-approved artifacts from the prior stage. Local logs help diagnose operation but are not evidence. Failed routes become Failure Records so later work inherits their constraints without inheriting their code structure.
