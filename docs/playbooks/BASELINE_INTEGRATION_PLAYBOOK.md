# Baseline Integration Playbook

This playbook adds external medication-recommendation baselines without copying a model zoo into the Active Research Home.

## 1. Register identity

Add the baseline to `baselines/registry.toml`. Record its immutable upstream repository and revision when known, license status, supported scientific modes, environment declaration, adapter command, adapter revision, and readiness. Store historical archive pointers under `archive_evidence`, not `source.repository`. Use `needs_pin` and omit the repository when the archive is the only known source.

An archive path identifies historical evidence, not an upstream release. Do not invent a commit from the copied tree.

## 2. Audit source, license, and lineage

Complete public-safe source, license, and lineage review before selecting a reproduction lane. Source is always a hard gate; license status is always recorded. Shared preprocessing or evaluation lineage must remain visible and does not count as independent replication evidence.

The active Baseline Registry and explicit Comparison Scope own selection. Do not edit registry readiness to make a blocked candidate selectable.

## 3. Reproduce upstream behavior

When a pinned source needs harness-owned invocation, implement one Reproduction Program and declare it in the Baseline Registry. Put model profiles inside that module when they share source, data, environment, and evaluation lineage; do not create runner or script directories in advance. The program owns source-native preprocessing gates, mechanical invocation adaptation, training, checkpoint selection, upstream test aggregation, and terminal result publication.

Create the declared Conda environment and run the pinned source outside this repository. Record preprocessing, split, feature timing, checkpoint selection, thresholding, metric aggregation, random seeds, and working-directory assumptions. This characterizes Reproduction Mode only and cannot create a Comparison Mode Run Record. Preserve restricted outputs outside Git.

## 4. Implement the Prediction Adapter

The Baseline Environment emits target-free Adapter Prediction Payloads containing visit identity, predicted medications, and optional scores. It never emits split or target fields. The core Prediction Adapter joins those payloads to core-owned targets and creates Prediction Records. The baseline-side code may translate identifiers, storage formats, tensors, and output serialization. It may not modify the Baseline Core, add information, select a new threshold, or repair recommendations unless that operation is declared for every compared method.

The core process adapter keeps expected evaluation records outside the subprocess request. It rejects target-bearing requests before launch, nonzero exits, malformed JSON, schema violations, missing or extra visits, duplicate visits, unknown medication codes, and core-owned fields in output. Do not accept best-effort output or let baseline code define evaluation labels.

## 5. Spend the Adaptation Budget

Declare the same allowed tuning and integration allowance for all compared methods before validation runs. Record trial count, search space, selection metric, seeds, stopping rule, and compute allowance. Test data cannot be used.

## 6. Advance readiness

`registered` means identity metadata exists. `smoke_ready` requires a pinned source, immutable adapter revision, environment digest, and content-addressed environment-lock and adapter-smoke evidence. `comparison_ready` requires at least one Comparison Qualification with content-addressed cohort identity, Baseline Core integrity, deterministic translation, Adaptation Budget, and independent metric recomputation evidence. The qualification names one protocol version, Dataset Manifest, and Adaptation Budget; create another qualification when any of them changes. The registry rejects skipped transitions and incomplete evidence sets.

Registration, source checkout, import success, or a reproduced paper number is insufficient for `comparison_ready`.

## 6a. Framework implementation lanes

Any additional framework implementation is a distinct Baseline Core from an upstream paper repository. Give it a separate identity and fixed framework revision; do not relabel its result as a source-native reproduction. Freeze one shared task, patient-level partition, vocabulary rule, external DDI or molecular artifact revision, adaptation budget, monitor, checkpoint rule, threshold rule, and metrics for every framework candidate.

Before accepting a framework example, fit every input and output processor, code vocabulary, graph, and molecular artifact from the training partition only. Validation and test data must use frozen training transforms, with a pre-registered OOV or exclusion policy for every field. Some framework split objects retain a reference to the complete pre-split dataset; do not pass that reference to a constructor or training path unless a model-specific proof shows it cannot influence model state.

The subprocess request remains target-free even when a framework's training or evaluation helper normally consumes labels to calculate loss. Do not use that helper as a prediction adapter until a contract test proves its emitted prediction payload is target-free. The adapter must extract predictions only and fail closed on `loss`, `y_true`, labels, targets, split membership, or ground-truth fields in either request or response.

## 7. Preserve evidence

Commit only public-safe environment declarations, adapter code, protocol-verification tests, aggregate audits, and accepted Run Records. Keep source checkouts, datasets, weights, logs, real Prediction Records, and draft records in repository-independent local storage.
