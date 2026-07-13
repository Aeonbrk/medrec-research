# Medication Recommendation Research

This context covers reusable computational research for medication recommendation, independent of any single research route or hypothesis.

## Language

**MedRec Research Library**:
The idea-agnostic body of reusable medication-recommendation research capability. It remains usable without ARIS.
_Avoid_: Baseline collection, route code

**ARIS Control Plane**:
The research-workflow authority that carries work through discovery, protocol, execution, audit, and claim formation while recording provenance. It orchestrates the MedRec Research Library but is not part of its runtime.
_Avoid_: ARIS runtime, ARIS library

**Harness Terminal**:
The local MacBook Air that runs ARIS, protocol checks, synthetic validation, remote submission, monitoring, and public-safe evidence intake without running real-data experiments.
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

**Live Benchmark Authority**:
The current correlated Baseline Program, Baseline Audit, Audit Review, Selection Result, Baseline Registry, and Comparison Scope records from which a Project Status Snapshot can be derived. It owns no scientific fact beyond those source records.
_Avoid_: Status input bundle, mutable status state, controller state

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
The smallest end-to-end research path that proves the Unified Research Protocol, evaluation, provenance, and ARIS orchestration work together.
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
Local operational detail produced while ARIS performs research work. It is diagnostic context, not accepted scientific evidence.
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

**Baseline Audit**:
针对一个候选的公开安全来源、许可证与四层 lineage 记录。`pass` 声明只有在匹配的 Audit Review 接受后才能通过选择硬门。
_Avoid_: README 摘要, 可运行证明

**Selection Result**:
固定 V1 scorecard 对完整六候选审计、审核和 diagnostics 的内容寻址投影。优先顺序不能绕过来源或许可证硬门。
_Avoid_: 运行队列, 实验结论

**Selection Acceptance**:
The content-addressed steward decision that authorizes one candidate from a current Selection Result to enter Reproduction Characterization. It binds the Selection Result, candidate, reviewer, and issue time without changing selection authority or expiring independently; Live Benchmark Authority drift makes it unusable.
_Avoid_: Selection Result, launch request, approval note

**Reproduction Characterization**:
The content-addressed account of repeat Reproduction Mode attempts and predeclared stability evidence for one accepted candidate. It determines a three-state stability result without becoming Comparison Mode evidence.
_Avoid_: Benchmark result, Run Record, comparison qualification

**Reproduction Stability Policy**:
The versioned Reproduction Mode rule that declares required attempt identities, expected output IDs, and criteria for stable, failed, or unresolved Reproduction Characterization.
_Avoid_: Variance rule, benchmark policy, training criterion

**Project Status Snapshot**:
从 program、audit、registry、Comparison Scope、selection 和 qualification 派生的短时公开安全视图。它不拥有科学事实，authority 漂移或过期时必须 fail closed。
_Avoid_: 数据库, readiness 权威

**Action Context**:
The public-safe current action binding derived from a Project Status Snapshot and an explicitly injected Authority Bundle. It identifies one allowable action and remote target or declares that no action is usable; callers submit only an opaque `request_id`.
_Avoid_: Action Intent, ambient authorization, launch context

**Authority Bundle**:
调用方显式注入的当前 authority digest、Action Authorization 和 Remote Preflight 集合。动作门不会从环境或远端隐式发现 authority。
_Avoid_: 环境变量权限, ambient credentials

**Action Request**:
通过共享动作门后生成的内容寻址请求记录。它描述被允许请求什么，不执行命令、SSH、环境创建或远端作业。
_Avoid_: Job, launch result

**Project Status Harness**:
只绑定 `127.0.0.1` 的本地 Web 投影，读取 Project Status Snapshot 并调用共享动作门。它没有数据库、科学写接口或执行面。
_Avoid_: 319 controller, experiment dashboard
