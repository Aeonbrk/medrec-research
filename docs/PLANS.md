# Plans

## Accepted: Controlled GAMENet Reproduction Launch

- **Status**: accepted on `2026-07-13`; execution begins with one GAMENet MIMIC-III v1.4 Reproduction Mode lane only.
- **Plan**: `docs/plans/2026-07-13-003-chore-controlled-gamenet-reproduction-launch-plan.md`.
- **Scope**: runtime-only smoke followed by one source-native seed `1203` attempt; MIMIC-IV, Comparison Mode, test-set selection, cross-seed stability claims, and registry readiness advancement are excluded.
- **Hard stops**: source and MIT license, data inputs, upstream split and evaluation semantics, patient-level non-overlap, isolated environment lock, target-free adapter contract, available GPU, disk capacity, and restricted-artifact handling all must pass.
- **Evidence boundary**: successful smoke is a runtime check only and creates no readiness evidence. The source-native run produces restricted diagnostics plus a public-safe Reproduction Characterization or Failure Record, never a Comparison Qualification.
- **Current outcome**: faithful Reproduction Mode remains blocked because the fixed GAMENet source does not attribute the recorded API-matched `dnc` candidate. The source-native `1203` characterization contract selects the source-reported `best_epoch` checkpoint without reading `data_test`, but remote connectivity failed before environment verification and no GPU work began. It cannot establish stability or advance readiness. See `research/failures/gamenet-reproduction-2026-07-13.md`.

## 已完成：基于第一性原理的科研实践参考资料

- **状态**：于 `2026-07-13` 完成；仅新增公开来源的中文研究方法资料，不改变运行时、基线、档案或研究协议。
- **计划**：`docs/plans/2026-07-13-002-docs-first-principles-research-practice-plan.md`。
- **目标**：将用户提供的三篇 Notion 页面、公开子页面和附件，以及直接引用的研究方法资源，整理为选题、解题、实验诊断、实验记录、阅读、讨论、写作、报告和 rebuttal 的可执行参考。
- **来源边界**：三篇种子页面、公开子页面和附件、固定提交 `6fdbcdfe24167feb7164d5625a477c75bd118040` 的 `pengsida/learning_research`，以及其中直接引用的实质性研究方法资源；不对所有嵌套链接做无限递归抓取。
- **保留边界**：只保留原创综合、来源 URL 和访问状态；不镜像原文、PDF、图片、附件、下载文件、浏览器轨迹或临时解析结果。受阻和已漂移链接已在来源台账中标注，未从中推断内容。
- **验证**：正文来源编号与台账逐项对应；新增资料不包含私有数据、原始附件或运行痕迹；Markdown lint 和差异空白检查通过后交付。

## Completed: Expand the New-Search Research Memory Ledger

- **Status**: completed on `2026-07-13`; documentation-only migration with no runtime, baseline, or archive mutation.
- **Plan**: `docs/plans/2026-07-13-001-docs-new-search-research-memory-ledger-plan.md`.
- **Goal**: expand the curated record of the pinned `New-Search` archive into
  a lifecycle-aware ledger of canonical ideas, experiments, claims, literature,
  reusable lessons, and historical route boundaries.
- **Source boundary**: committed archive content at
  `9971464253c556345262b22ed6d44b2cc14c9da8` only; user-owned archive worktree
  changes remain excluded.
- **Safety boundary**: no archive mirroring, private data, raw result tables,
  traces, model artifacts, or server-specific operational details enter Git.
- **Evidence**: all 6 ideas, 11 experiments, 12 claims, and 21 paper cards
  reconcile to the pinned source; every cited Markdown record resolves; 212
  tests, Ruff, formatting, Markdown lint, and a diff-scoped review pass.

## Accepted: Benchmark Authority Contract Hardening

- **Status**: local public-safe implementation completed on `2026-07-12`. No baseline execution, 319 deployment, environment creation, real-data access, or experiment work is authorized.
- **Plan**: `docs/plans/2026-07-12-001-fix-authority-contract-hardening-plan.md`.
- **Goal**: make Project Status, Reproduction Characterization, and action requests fail closed when their correlated public-safe authority records drift.
- **Authority model**: Comparison Scope owns identity matching only; Baseline Registry retains readiness and evidence authority; Live Benchmark Authority validates Program, Audit Review, Registry, Scope, and published Selection Result before status projection.
- **Evidence model**: Selection Acceptance is durable steward provenance. Policy V2 owns complete expected metric identities but cannot open a new lane; the controlled GAMENet V3 policy additionally fixes source, MIMIC-III v1.4, and full seeds `7`, `19`, and `31`. V1 records remain parseable but cannot affect current status.
- **Action model**: CLI and Harness derive one Action Context from an explicitly injected current Authority Bundle; browser input is opaque `request_id` only and every Harness GET/POST reloads the configured bundle.
- **Deferred seam**: Comparison Mode acceptance extraction remains deferred until a second concrete core adapter needs its lifecycle.
- **Evidence**: 212 tests pass; Ruff check and format check, Markdown lint, diff check, fixture parsing, public-safe validation, and a full diff-scoped review pass.

## Completed: bootstrap the MedRec Research Library

- **Status**: accepted and completed on `2026-07-10`; awaiting the user's first commit and remote decision.
- **Plan**: `docs/plans/2026-07-10-001-bootstrap-medrec-research.md`.
- **Goal**: create the independent active research home, prove one protocol vertical slice, preserve curated scientific memory, and leave `New-Search` as a non-destructive Research Archive.
- **Source archive**: New-Search Research Archive at commit `9971464253c556345262b22ed6d44b2cc14c9da8` plus documented uncommitted archive metadata; local path intentionally omitted.
- **Execution model**: the MacBook Air is the ARIS harness terminal; real EHR and GPU experiments run only on `319-wild` under isolated Conda environments.
- **Scientific correction**: final review rejected the plan's claim that the synthetic reference was `smoke_ready` Reproduction Mode evidence. ADR-0006 replaces that output with a non-evidentiary Protocol Check Record; no baseline is currently above `registered`.
- **Evidence**: 61 tests pass; Ruff check and format pass; `uv lock --check`, package build, Markdown lint, ARIS reconcile dry run, CodeGraph sync, registry parse, YAML parse, synthetic CLI smoke, and public-record privacy scan pass.
- **Residual unknowns**: upstream pins and licenses for unresolved baselines, real baseline adapters, verified 319 environment locks, the first upstream-specific Reproduction Mode record, the Git remote, and the 319 checkout.
- **Superseded next step**: this plan originally named the first immutable commit as the immediate next step. The accepted six-candidate benchmark program now requires a public source, license, and lineage audit first; the initial commit, remote, and 319 checkout remain separately authorized gates.

## Implemented: MedRec Baseline Benchmark Harness

- **Status**: local public-safe implementation completed on `2026-07-11`; baseline execution, 319 deployment, real data, environment creation, and experiments remain unauthorized.
- **Plan**: `docs/plans/2026-07-10-002-feat-medrec-benchmark-harness-plan.md`.
- **Goal**: establish a six-candidate portfolio for RETAIN, GAMENet, SafeDrug, MICRON, MoleRec, and the separately named `LEAP-SafeDrug` derivative before new-method discovery.
- **Scientific gates**: every candidate needs source, license, and four-layer lineage audit; shared lineage remains visible and does not create independent replication evidence.
- **Sequencing**: audit all candidates, select one first reproduction lane with a predeclared scorecard, stabilize it, then operate at most two isolated lanes in parallel. At four `comparison_ready` candidates, pause for human review; new-method discovery stays closed until all six are ready.
- **Harness boundary**: the loopback Web harness reads a project-owned public-safe status contract and emits gated action requests only. It cannot own scientific state, a database, restricted artifacts, or an execution surface.
- **Authorization boundary**: do not modify baseline sources or registry state, create a commit or remote, deploy to 319, access real data, create environments, or run experiments without a separate user instruction.
- **Current evidence**: all six audits validate; fixed-order selection proposes GAMENet; every registry entry remains `registered`; CLI/action/harness focused tests and Ruff pass.
