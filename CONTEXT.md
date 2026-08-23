# Medication Recommendation Research

This context covers reusable computational research for medication recommendation, independent of any single research route or hypothesis.

## Language

**MedRec Research Library**:
The idea-agnostic body of reusable medication-recommendation research capability.
_Avoid_: Baseline collection, route code

**Harness Terminal**:
The local MacBook Air that runs protocol checks, synthetic validation, remote submission, monitoring, and public-safe evidence intake without running real-data experiments.
_Avoid_: Local experiment machine, training laptop

**319 Execution Plane**:
The remote compute system that runs real EHR processing, training, GPU inference, and isolated Baseline Environments while retaining restricted artifacts.
_Avoid_: Harness, local backend

**Unified Research Protocol**:
The shared scientific contract under which first-party medication-recommendation methods and baselines become comparable. It fixes what evidence means without replacing upstream reproduction semantics.
_Avoid_: Our narrative, common benchmark

**Comparison Mode**:
The use of a baseline under the Unified Research Protocol to support claims of relative performance.
_Avoid_: Fair mode, canonical run

**Reproduction Mode**:
The use of a baseline under its recorded upstream scientific semantics to verify historical reproducibility, not cross-method superiority.
_Avoid_: Legacy mode, comparison run

**Baseline Core**:
The scientific mechanism of an imported baseline. It remains unchanged in Comparison Mode unless the modified method is reported as a separate baseline.
_Avoid_: Baseline implementation, editable baseline

**Prediction Adapter**:
The translation between an unchanged Baseline Core and the Unified Research Protocol. It changes representation, not scientific behavior.
_Avoid_: Baseline patch, compatibility code

**Adapter Prediction Payload**:
The target-free wire result emitted by a Baseline Environment. The core Prediction Adapter validates it and joins it with core-owned split and target data to create a Prediction Record.
_Avoid_: Prediction Record, model labels

**Adaptation Budget**:
The predeclared and equal allowance for tuning and mechanical integration granted to every compared method.
_Avoid_: Tuning freedom, fair tuning

**Comparison Scope**:
The immutable Unified Research Protocol version, Dataset Manifest identity, and Adaptation Budget identity that delimit one set of comparable qualification and Run Record evidence.
_Avoid_: Scope digest, comparison context, loose protocol fields

**Active Research Home**:
The sole authoritative location for future research work and newly produced evidence.
_Avoid_: Working folder, current checkout

**Research Archive**:
A read-only historical source that preserves provenance, failed routes, and prior evidence without accepting new research work.
_Avoid_: Backup, deprecated repository

**Research Memory**:
The curated current scientific state, reusable lessons, failed-route constraints, and evidence references carried by the Active Research Home.
_Avoid_: Log collection, artifact dump

**Failure Record**:
A durable account of a falsified or demoted research route and the evidence that prevents its unsupported revival.
_Avoid_: Negative result file, abandoned idea

**Baseline Registry**:
The authoritative catalog of supported baselines, their upstream identity, scientific modes, and comparison readiness.
_Avoid_: Baseline folder list, model zoo

**Pinned Baseline Source**:
An external baseline source fixed to an immutable revision from which a Baseline Core can be reproduced.
_Avoid_: Latest upstream, copied checkout

**Local Data Root**:
The repository-independent local home for restricted EHR inputs, derived datasets, and private experiment outputs.
_Avoid_: Repository data folder, archived dataset

**Dataset Manifest**:
A public-safe identity record built while membership is available on 319. It records provenance, split aggregates, eligible-visit membership digests, snapshot integrity, and medication-vocabulary integrity without patient-level content. Restricted manifests use a private HMAC key for membership digests.
_Avoid_: Dataset README, data path

**Protocol Vertical Slice**:
The smallest end-to-end research path that proves the Unified Research Protocol, evaluation, and provenance work together.
_Avoid_: Scaffold, demo pipeline

**Protocol Check Record**:
A content-addressed result from the public synthetic harness. It proves software and protocol wiring only and cannot support a research claim, Reproduction Mode result, or Comparison Mode result.
_Avoid_: Run Record, experiment result

**Comparable Baseline**:
A registered baseline whose source identity, Prediction Adapter, scientific modes, and protocol verification are sufficient for Comparison Mode.
_Avoid_: Available baseline, copied model

**Run Record**:
An immutable public-safe account accepted under Comparison Mode. It binds the authoritative baseline definition, adapter and environment revisions, Dataset Manifest, eligible test visits, Adaptation Budget, configuration, aggregate outcome, and artifact checksums.
_Avoid_: Run log, result folder

**Readiness Evidence**:
A content-addressed artifact tied to one named readiness gate. A readiness enum without the full required evidence set has no authority.
_Avoid_: Status note, successful import

**Comparison Qualification**:
The content-addressed evidence that one smoke-ready baseline passed Comparison Mode gates for one exact protocol version, Dataset Manifest, and Adaptation Budget. Qualification in one scope does not transfer to another cohort or budget.
_Avoid_: Global comparable flag, baseline quality score

**Workflow Trace**:
Local operational detail produced while performing research work. It is diagnostic context, not accepted scientific evidence.
_Avoid_: Research record, provenance

**Baseline Environment**:
An isolated Conda environment that makes one Pinned Baseline Source runnable without constraining the core research environment.
_Avoid_: Shared environment, project environment

**Core Evaluator Environment**:
The separate Python 3.11 Conda environment on 319 that validates restricted Prediction Records, recomputes aggregate metrics, and emits candidate Run Records. It does not contain Baseline Core dependencies.
_Avoid_: Baseline Environment, Mac core environment

**Prediction Record**:
The protocol-defined medication prediction and evaluation evidence emitted by a method without exposing its internal representation.
_Avoid_: Model output, result row

**Remote Preflight**:
The read-only revision, environment, data, GPU, and disk checks performed immediately before a declared 319 submission.
_Avoid_: Readiness evidence, successful training, remote cleanup
