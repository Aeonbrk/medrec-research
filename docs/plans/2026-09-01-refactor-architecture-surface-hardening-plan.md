---
title: "refactor: Harden MedRec architecture surfaces"
type: refactor
status: completed
date: 2026-09-01
artifact_readiness: implementation-ready
execution: code
origin: "full-repository architecture audit; all three candidates accepted"
target_branch: main
baseline_revision: 87e4a393dfc955d26b1a048c9320980bec6e5146
---

# refactor: Harden MedRec Architecture Surfaces

## Goal Capsule

完成现有架构重构的最后一层“surface hardening”，使代码的**真实依赖面**与已经确定的架构意图一致，而不重新设计科学执行架构。

最终状态必须满足：

1. `baselines/safedrug_archived.py` 与 `baselines/molerec.py` 是真正的 deep Reproduction Programs，对外只暴露 Program-level behavior。
2. `src/medrec_research/cli.py` 是 composition root，而不是 reproduction scientific/workflow knowledge owner。
3. `ProcessPredictionAdapter` 只保留当前实际使用的 target-free Comparison process seam，不继续维护无人使用的 schema-v1 process interface。
4. 现有 Registry、RemoteExecutor、attempt policy、evaluation queue、evidence、snapshot、selection、audit、comparison protocol 等已经合理的知识边界不被重新拆解。
5. 所有公共 CLI、科学语义、artifact schema、historical evidence 和五模型 Comparison 行为保持不变。

这不是一次“大重构”。这是一次**边界闭合与删除型重构**。

---

# 1. Settled Decisions

以下决策已经确定，实施过程中不得重新打开，除非出现能够证明其错误的新代码证据。

## A1. 三个候选全部实施

实施顺序固定为：

`Candidate 1 (Program façade) → Candidate 2 (CLI ownership) → Candidate 3 (dead adapter deletion)`

原因是后一步依赖前一步已经稳定的 seam。

## A2. 不按文件大小拆 Program

以下大文件保持 deep module：

- `baselines/safedrug_archived.py`
- `baselines/molerec.py`
- `src/medrec_research/remote_executor.py`
- `src/medrec_research/reproduction/molerec_table1_attempt.py`
- `src/medrec_research/reproduction/molerec_evaluation.py`
- `src/medrec_research/reproduction/evaluation_queue.py`
- `src/medrec_research/reproduction/reproduction_evidence.py`
- `src/medrec_research/comparison_protocol.py`
- `src/medrec_research/registry.py`

只在发现新的独立 knowledge domain 时拆分，禁止按 train/test/recovery、LOC、函数数量机械拆分。

## A3. 两个 Reproduction Program 平行但不抽象成共同基类

SafeDrug 与 MoleRec 可以拥有相同的高层行为形状：

- `probe(request)`
- `execute(request)`

但不创建：

- `BaseProgram`
- lifecycle framework
- callback bag
- generic state machine
- hook registry
- plugin architecture

相似不等于共享知识。

## A4. Python runtime boundary 是设计边界

继续保持：

- baseline execution closure 与其声明运行时兼容；
- MoleRec Python 3.8 compatibility；
- core Python 3.11 runtime；
- baseline runtime 不逆向 import core runtime；
- baseline/core 两侧相似 evidence helper 不因 DRY 被强行合并。

## A5. CLI 保留一个用户入口

继续保留：

- `medrec`
- `medrec-research`
- `python -m medrec_research`

不新增 reproduction executable。

## A6. Candidate 3 是 deletion refactor，不是 Comparison redesign

删除的是：

- `PredictionAdapter` schema-v1 process abstraction；
- `ProcessPredictionAdapter.predict(...)` schema-v1 path；
- 对应无生产调用的测试与 export。

明确保留：

- `PredictionRecord`
- `evaluate_predictions`
- `RunRecord`
- `accept-comparison`
- file-based Comparison workflow
- `ProcessPredictionAdapter.predict_comparison(...)`
- `ComparisonPredictionBatch`
- target-free Comparison protocol

---

# 2. Repository Facts

## F1. Program implementation 已经足够 deep

SafeDrug/MoleRec 已经分别把内部知识分布到：

- `*_data.py`
- `*_logs.py`
- `*_probe.py`
- shared mechanical reproduction primitives

因此当前问题不是缺少拆分，而是 façade 仍然过宽。

## F2. 两个 Program 当前 `__all__` 仍暴露大量内部实现

包括但不限于：

- profile declarations
- adaptation helpers
- checkpoint helpers
- log parsers
- dataset helpers
- `run_formal_lane`
- `run_smoke_lane`
- `run_test_lane`
- recovery helpers
- probe internals

这与既定的 deep Program 设计不一致。

## F3. Root CLI 已拥有 reproduction-specific knowledge

`src/medrec_research/cli.py` 当前直接依赖：

- MoleRec attempt declaration/schedule
- continuation validation
- Table-1 evaluation lifecycle
- RemoteExecutor reproduction submission
- reproduction resource mapping
- recovery
- SafeDrug staging/audit
- attempt-specific handlers

测试还直接 import / monkeypatch root CLI 的私有 reproduction handlers。

因此 root CLI 已成为 knowledge owner，而非单纯 composition root。

## F4. Process adapter 存在两个协议世代

`ProcessPredictionAdapter` 当前同时实现：

- schema v1 `predict(...)`
- schema v2 `predict_comparison(...)`

生产代码使用的是 v2 Comparison seam。

v1 的 repo-internal调用只存在于 adapter 单元测试。

## F5. file-based Comparison v1 仍然活跃

`accept-comparison`、`PredictionRecord`、`evaluate_predictions`、`RunRecord` 有独立 integration/unit coverage。

它们不能因为 process adapter v1 删除而被误删。

---

# 3. Requirements

## Program façade

### R1

`baselines/safedrug_archived.py` 的正式 library façade 必须只表达 Program-level behavior。

### R2

`baselines/molerec.py` 的正式 library façade 必须只表达 Program-level behavior。

### R3

正式 Program API 与跨-runtime 执行边界明确定义为两层 seam：

1. `probe(request)` 与 `execute(request)` 是 concrete Reproduction Program 的正式 Python in-process behavior façade；
2. direct-script CLI `main()`（及其参数解析）是稳定的跨进程、跨 Conda/Python runtime transport boundary，被 Registry 与 RemoteExecutor 消费；
3. `main()` 保持 thin transport adapter 角色：解析现有 CLI 命令行参数后委托给 `probe(request)` 或 `execute(request)`，不得在 `main()` 中维护第二套独立的 scientific lifecycle orchestration；
4. direct-script CLI 参数、stdout/stderr 输出格式、Registry entrypoint 路径与 RemoteExecutor command 构造语义保持严格兼容。

### R4

不得因为收窄 façade 而移动或重写已经正确归属的 scientific lifecycle。

### R5

Program 内部 helper 可以继续存在；不要求为了“看起来 private”而机械批量改名。

Publicness 由：

- `__all__`
- docs
- caller usage
- tests

共同定义，而不是单纯由 Python 是否能够 explicit import 决定。

### R6

原有 direct script invocation 与 Registry entrypoint 路径完全保持。

---

## CLI ownership

### R7

`src/medrec_research/cli.py` 最终只拥有：

- top-level parser composition
- generic/core command wiring
- process exit/error boundary
- delegation to domain-owned command modules

### R8

所有 reproduction-specific CLI orchestration 转移到：

`src/medrec_research/reproduction/`

优先采用一个 cohesive reproduction CLI command module。

不要一开始拆成多个 parser/handler/helper 小文件。

### R9

Root CLI 不得直接 import：

- `src/medrec_research/reproduction/molerec_table1_attempt.py`
- `src/medrec_research/reproduction/molerec_evaluation.py`
- SafeDrug/MoleRec attempt-specific policy modules

它最多依赖一个 reproduction-owned command registration/dispatch seam。

### R10

现有 CLI command names、arguments、defaults、stdout/stderr semantics、exit codes、dry-run behavior 必须保持。

### R11

`recover-reproduction` 必须继续保持 mechanical recovery command，不重新获得 scientific execution hooks。

### R12

测试不得继续把 root `cli.py` 的 reproduction private handlers 当作测试 API。

需要直接测试 domain handler 时，从 reproduction-owned command module 测试。

用户可观察行为继续通过 CLI integration tests 验证。

---

## Adapter deletion

### R13

删除 `PredictionAdapter` Protocol，除非实施时发现 repo 内新的真实 production caller。

### R14

删除 `ProcessPredictionAdapter.predict(...)` schema-v1 process path。

### R15

`ProcessPredictionAdapter.predict_comparison(...)` 的 schema-v2 behavior、validation、privacy boundary、error semantics 保持不变。

### R16

从 `src/medrec_research/__init__.py` 删除废弃 process-v1 public export。

### R17

不得修改 file-based Comparison v1 protocol，仅因为它与 process schema-v1 都使用“v1”编号。

两者不是同一个 seam。

---

## Architecture preservation

### R18

以下模块除必要 import/doc/test 调整外不做结构重构：

- `src/medrec_research/registry.py`
- `src/medrec_research/remote_executor.py`
- `src/medrec_research/reproduction/evaluation_queue.py`
- `src/medrec_research/reproduction/molerec_table1_attempt.py`
- `src/medrec_research/reproduction/molerec_evaluation.py`
- `src/medrec_research/reproduction/reproduction_evidence.py`
- `src/medrec_research/reproduction/safedrug_selection.py`
- `src/medrec_research/reproduction/safedrug_c721.py`
- `src/medrec_research/reproduction/reproduction_audit.py`
- `src/medrec_research/reproduction/molerec_reproduction_audit.py`
- `src/medrec_research/reproduction/molerec_snapshot.py`
- `src/medrec_research/comparison_protocol.py`
- `src/medrec_research/comparison_scope.py`
- `src/medrec_research/prediction.py`
- `src/medrec_research/evaluation.py`
- `src/medrec_research/run_record.py`

### R19

不得新建 compatibility shim、deprecated alias 或“双接口过渡层”。

这是内部研究代码的 architecture closure，不保留新的技术债。

### R20

不得运行真实 319 scientific workload、重新训练、测试集 evaluation 或产生新的研究 evidence。

---

# 4. Acceptance Evidence

## AE1 — Program façade

两个 Program 的正式 in-process export surface 只包含：

```text
probe
execute
```

Direct-script CLI `main()` 作为跨进程/跨 runtime transport entrypoint 保持完全兼容，并在内部直接委托给 `probe`/`execute`。

## AE2 — Program behavior

以下行为保持：

- probe
- smoke
- formal training
- formal test
- recovery
- SafeDrug selection admission
- MoleRec native history/checkpoint semantics

## AE3 — Program tests

不存在测试把：

```text
run_formal_lane
run_smoke_lane
run_test_lane
recover_formal_lane
parse_* 
check_*
```

视为 Program public contract。

Scientific helper 的 focused tests 仍可以直接测试真正 owning module。

## AE4 — Root CLI

`src/medrec_research/cli.py` 不包含 MoleRec Table-1 scientific attempt/evaluation implementation knowledge。

## AE5 — CLI compatibility

所有现有 public command integration tests保持相同行为。

## AE6 — Root CLI test locality

`tests/integration/test_run_cli.py` 不再依赖 root CLI reproduction private handlers。

## AE7 — Adapter surface

以下符号不存在：

```text
PredictionAdapter
ProcessPredictionAdapter.predict
```

以下符号继续存在：

```text
ProcessPredictionAdapter.predict_comparison
```

## AE8 — Comparison preservation

`accept-comparison` integration test保持通过。

`PredictionRecord` / `RunRecord` / `evaluate_predictions` 测试保持通过。

## AE9 — Runtime preservation

MoleRec Program closure 继续通过 Python 3.8 syntax compatibility 检查。

SafeDrug Program 不引入逆向 core dependency。

## AE10 — No collateral architecture change

git diff 中不存在无关 Registry/evidence/attempt/queue/protocol redesign。

## AE11 — Repository quality

完整测试、lint、format 和 repository markdown/documentation gates 全绿。

---

# 5. Implementation Units

## U0. Characterize the three boundaries before editing

### Goal

把“不能改变的 observable contract”变成 implementation guardrail。

### Scope

Inspect and characterize only; do not create a generic compatibility layer.

### Required surfaces

Program:

- `tests/unit/test_safedrug_archived_program.py`
- `tests/unit/test_molerec_program.py`

CLI:

- `tests/integration/test_run_cli.py`
- `tests/integration/test_accept_comparison_cli.py`
- `tests/unit/test_reproduction_recovery_cli.py`

Adapter:

- `tests/unit/test_process_adapter.py`
- actual `predict_comparison` production callers

### Work

1. Enumerate currently tested public Program behavior.
2. Separate façade tests from internal scientific helper tests.
3. Record current public CLI subcommands and parser behavior.
4. Confirm repo-wide process-v1 adapter caller count.
5. If a new production caller contradicts F4, stop Candidate 3 and report the concrete caller rather than introducing compatibility code.

### Covers

R1–R20, AE1–AE11.

---

## U1. Close the Reproduction Program façades

### Goal

兑现既定 deep Program architecture，而不是再次重构 Program internals。

### Primary files

- `baselines/safedrug_archived.py`
- `baselines/molerec.py`
- `tests/unit/test_safedrug_archived_program.py`
- `tests/unit/test_molerec_program.py`
- `tests/unit/test_reproduction_artifacts.py`

Potential focused-test files only where ownership demands it:

- `*_data.py`
- `*_logs.py`
- `*_probe.py`

### Required outcome

1. Narrow both Program `__all__` to `probe` and `execute`.
2. Direct-script CLI `main()` 作为 thin transport adapter 委托给 `probe`/`execute`，保持原有 CLI 参数与 stdout/stderr 语义完全兼容。
3. Remove tests asserting implementation helpers are façade API。
4. 明确 SafeDrug selection admission 与 core selector 的跨-runtime 职责分离：
   - `tests/unit/test_reproduction_artifacts.py` 不再把 `safedrug_archived` 的 selection constants 或 `require_selected_safedrug_selection` 当作 façade API；
   - Program-side selection admission coverage 迁移到 `tests/unit/test_safedrug_archived_program.py`，通过 `execute(request)` 行为进行完整验证；
   - 测试构造 core-produced `selection.json` 时可使用 `medrec_research.reproduction.safedrug_selection`，但不得引入 baseline runtime → core runtime 逆向依赖；
   - 保留 Program-side admission 与 core selector 的跨-runtime 职责分离。
5. Keep Program-owned lifecycle implementation in place.
6. Keep internal data/log/probe modules as current knowledge owners.
7. Do not introduce Program base class or lifecycle abstraction.
8. Preserve direct-script CLI.
9. Preserve Python 3.8-compatible syntax for MoleRec closure.
10. Update architecture documentation language where it still suggests helper re-export is supported.

### Explicit non-work

Do not:

- split training/test/recovery modules;
- move adaptation merely to reduce Program LOC;
- merge SafeDrug/MoleRec helpers;
- modify artifact schemas;
- change selection authority.

### Verification gate U1

Run targeted:

```text
tests/unit/test_safedrug_archived_program.py
tests/unit/test_molerec_program.py
tests/unit/test_reproduction_runner.py
tests/unit/test_reproduction_artifacts.py
```

Plus Python 3.8 AST compatibility for MoleRec execution closure.

Do not start U2 until U1 passes.

---

## U2. Move reproduction CLI knowledge under the reproduction namespace

### Goal

使 root `cli.py` 成为真正 composition root。

### Primary files

Modify:

- `src/medrec_research/cli.py`
- `tests/integration/test_run_cli.py`
- `tests/unit/test_reproduction_recovery_cli.py`

Add:

- one cohesive reproduction-owned CLI command module under
  `src/medrec_research/reproduction/`

Recommended initial shape:

```text
src/medrec_research/reproduction/cli_commands.py
```

Exact internal function decomposition由实现时基于代码局部性决定，但不要创建 framework。

### Ownership rule

Root CLI owns:

```text
top-level parser composition
generic command composition
generic error/exit boundary
```

Root CLI 与 reproduction command 之间的连接点明确为：

```text
register_reproduction_commands(subparsers: argparse._SubParsersAction) -> None
```

由 `src/medrec_research/reproduction/cli_commands.py` 导出，负责为所有 13 个 reproduction 子命令配置 argument parser 并绑定对应的 handler callable。

Reproduction CLI module (`src/medrec_research/reproduction/cli_commands.py`) owns:

```text
reproduce
reproduce-smoke
recover-reproduction (delegates to program.execute({'mode': 'recovery', ...}) and maps result['marker_path'] to stdout)
reproduction resource parsing
frozen schedule admission
continuation admission
MoleRec evaluation prepare/claim/finalize/audit command adapters
SafeDrug/MoleRec staging/audit command adapters
reproduction-specific git/source submission preparation (_local_source_revision 随 reproduction submission 移入此处；禁止新建 generic git utility/framework)
```

Domain modules themselves continue owning scientific semantics。

CLI command module只做 command adaptation/orchestration，不复制 scientific validation。

### Critical constraint

Do not move logic from:

- `src/medrec_research/reproduction/molerec_table1_attempt.py`
- `src/medrec_research/reproduction/molerec_evaluation.py`
- `src/medrec_research/reproduction/evaluation_queue.py`
- `src/medrec_research/reproduction/safedrug_selection.py`
- `src/medrec_research/reproduction/safedrug_c721.py`
- `src/medrec_research/reproduction/molerec_snapshot.py`
- `src/medrec_research/reproduction/reproduction_audit.py`
- `src/medrec_research/reproduction/molerec_reproduction_audit.py`
- `src/medrec_research/reproduction/reproduction_evidence.py`

into the new CLI module。

New CLI module calls those owners。

### Tests

1. Existing public subprocess CLI tests remain authoritative for user behavior.
2. Tests needing injection/mocking target `src/medrec_research/reproduction/cli_commands.py` directly.
3. Tests importing `_local_source_revision` or `_recover_reproduction` update import handles to `medrec_research.reproduction.cli_commands`.
4. Root CLI tests只验证 composition / routing，不再验证 attempt internals。
5. Preserve dirty-worktree privacy behavior。
6. Preserve batch-continuation-after-one-lane-blocked behavior。
7. Preserve seven-lane frozen schedule behavior。
8. Preserve continuation/evaluation IDs。

### Static acceptance

Root `src/medrec_research/cli.py` must have no direct import from any domain/policy/lifecycle module under `src/medrec_research/reproduction/` (including `molerec_table1_attempt.py`, `molerec_evaluation.py`, `evaluation_queue.py`, `safedrug_selection.py`, `safedrug_c721.py`, `molerec_snapshot.py`, `reproduction_audit.py`, `molerec_reproduction_audit.py`, `reproduction_evidence.py`), and no embedded Table-1 scientific lifecycle code. It accesses reproduction CLI orchestration strictly via `register_reproduction_commands`.

### Verification gate U2

Run:

```text
tests/integration/test_run_cli.py
tests/integration/test_accept_comparison_cli.py
tests/unit/test_reproduction_recovery_cli.py
tests/unit/test_remote_executor.py
tests/unit/test_molerec_table1_attempt.py
tests/unit/test_molerec_evaluation.py
tests/unit/test_evaluation_queue.py
```

Do not start U3 until U2 passes。

---

## U3. Delete the obsolete process adapter v1 seam

### Goal

让 process adapter 只表达一个真实的 Comparison protocol。

### Primary files

- `src/medrec_research/adapters.py`
- `src/medrec_research/__init__.py`
- `tests/unit/test_process_adapter.py`

Potential callers:

- `baselines/five_model_comparison.py`

### Work

1. Repo-wide确认 `.predict(...)` 没有 production caller。
2. Delete `PredictionAdapter` Protocol。
3. Delete `ProcessPredictionAdapter.predict(...)`。
4. Delete schema-v1 process parsing/normalization code that becomes dead。
5. Remove unused imports such as `PredictionRecord` from adapter module if no longer needed。
6. Remove `PredictionAdapter` from root package exports。
7. Rewrite adapter tests around:
   - constructor validation;
   - launch/process/timeout errors;
   - target-free request enforcement (target field and split membership rejection);
   - unknown request fields rejection;
   - schema-v2 response;
   - method identity;
   - exact visit coverage;
   - vocabulary score order;
   - core-owned field rejection;
   - stderr privacy and error path masking.
8. Leave file-based Comparison untouched。

### Stop condition

If U0/U3 discovers a genuine supported external compatibility contract that requires `PredictionAdapter`, stop before deletion and report that exact compatibility boundary。

Do not silently add a deprecated shim。

### Verification gate U3

Run:

```text
tests/unit/test_process_adapter.py
tests/unit/test_prediction.py
tests/unit/test_evaluation.py
tests/unit/test_run_record.py
tests/unit/test_commands.py
tests/integration/test_accept_comparison_cli.py
tests/unit/test_comparison_adapters.py
tests/unit/test_comparison_protocol.py
```

---

## U4. Align architecture documentation with implemented surfaces

### Goal

确保未来维护者看到的 architecture 与真正代码 dependency graph 一致。

### Files

At minimum inspect/update where necessary:

- `ARCHITECTURE.md`
- `CONTEXT.md`
- `Handoff.md`
- `docs/START_HERE.md`
- current architecture plan completion notes

### Required documentation facts

Document explicitly:

1. Concrete Reproduction Programs are deep executable modules。
2. Official Program behavior surface is `probe` / `execute`。
3. `*_data.py`、`*_logs.py`、`*_probe.py` are internal knowledge modules。
4. Root CLI is composition only。
5. Reproduction commands live under reproduction namespace。
6. Process adapter supports only target-free Comparison schema。
7. File-based `accept-comparison` remains a separate supported workflow。
8. Python runtime boundary permits intentional implementation duplication where dependency inversion would otherwise be violated。

### Do not

Do not create a new ADR unless implementation reveals a genuinely new architectural decision。

This work primarily closes already accepted architecture。

---

## U5. Full verification, simplification, and architecture review

### Goal

证明本次变化是 architecture simplification，而不是 complexity displacement。

### Full behavior gates

Run:

```text
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Run repository-standard markdownlint/documentation check if documentation changed。

Run Python 3.8 AST compatibility check for MoleRec baseline execution files。

### Static architecture checks

Confirm：

```text
root cli → reproduction command seam
reproduction command seam → attempt/evaluation/remote owners
RemoteExecutor → no attempt-specific policy
Program → internal data/log/probe + mechanical primitives
external Program caller → probe/execute only
ProcessPredictionAdapter → predict_comparison only
```

### Deletion checks

Repo-wide search must find no active references to:

```text
PredictionAdapter
ProcessPredictionAdapter.predict(
Program façade run_formal_lane expectation
Program façade run_test_lane expectation
root CLI reproduction private handlers
```

Internal implementation functions may still legitimately have those names inside Program。

### Diff review

Reject the implementation if the final diff introduces:

- shared Program base class；
- lifecycle callback architecture；
- generic CLI plugin framework；
- new attempt policy in RemoteExecutor；
- duplicated lane authority；
- scientific logic in CLI；
- cross-runtime imports；
- unrelated refactors。

---

# 6. Expected Architecture After Completion

```text
                         ┌──────────────────────┐
                         │      Registry        │
                         │ scientific authority │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┴──────────────────┐
                 │                                     │
                 ▼                                     ▼
      ┌─────────────────────┐               ┌─────────────────────┐
      │ Reproduction Policy │               │ Comparison Protocol │
      │ attempt/evaluation  │               │ target-free eval    │
      └──────────┬──────────┘               └──────────┬──────────┘
                 │                                     │
                 ▼                                     ▼
      ┌─────────────────────┐               ┌─────────────────────┐
      │   RemoteExecutor    │               │ ProcessPrediction   │
      │ generic mechanics   │               │ Adapter             │
      └──────────┬──────────┘               │ predict_comparison  │
                 │ (subprocess CLI main)    └─────────────────────┘
                 ▼
      ┌─────────────────────┐
      │ Concrete Program    │
      │ probe / execute     │ ◄── transport main()
      ├─────────────────────┤
      │ data / logs / probe │
      │ source lifecycle    │
      │ recovery semantics  │
      └─────────────────────┘
```

CLI sits above these boundaries only as composition：

```text
medrec
  │
  ▼
root cli (src/medrec_research/cli.py)
  ├── core/comparison commands
  └── register_reproduction_commands(subparsers)
          │
          ▼
      reproduction cli commands (src/medrec_research/reproduction/cli_commands.py)
          ├── attempt policy & queue (evaluation_queue.py, molerec_table1_attempt.py)
          ├── evaluation (molerec_evaluation.py)
          ├── RemoteExecutor submission mechanics & git revision
          └── staging/audit owners (safedrug_c721.py, molerec_snapshot.py, reproduction_audit.py, molerec_reproduction_audit.py)
```

---

# 7. Non-Goals

明确不做：

- 不设计新研究模型。
- 不改变任何 baseline scientific semantics。
- 不重新复现模型。
- 不运行 319。
- 不重新计算研究指标。
- 不修改 Table-1/Table-2 reference values。
- 不统一两个 audit。
- 不统一两个 comparison adapter。
- 不抽象五模型 suite framework。
- 不拆 Registry。
- 不拆 RemoteExecutor。
- 不拆 evidence。
- 不拆 queue。
- 不迁移 historical artifact schema。
- 不做“顺便 cleanup”。
- 不以 LOC reduction 作为成功指标。

---

# 8. Risk Register

## Risk 1 — Public façade narrowing accidentally deletes testability

Mitigation：

Internal scientific helpers继续可被 owning-module focused tests验证。

收窄的是 supported façade，不是删除所有内部函数。

## Risk 2 — CLI move changes argparse behavior

Mitigation：

Characterization first；existing subprocess integration tests remain authoritative。

Parser composition必须复用原 argument declarations或保持严格等价。

## Risk 3 — CLI module重新成为新的 god module

Mitigation：

它只能拥有 command adaptation。

任何 scientific rule一旦需要被解释，应调用已有 owner，而不是复制。

只有当实施中发现两个真正独立 knowledge domains 时才允许再拆 CLI command module。

## Risk 4 — Candidate 3 accidentally destroys file-based Comparison

Mitigation：

把 process protocol 与 PredictionRecord file protocol视为两条不同边界。

`accept-comparison` 是独立 hard gate。

## Risk 5 — Python 3.8 regression

Mitigation：

U1 后立即做 AST compatibility，而不是拖到最终 gate。

## Risk 6 — Scope creep into recently stabilized reproduction architecture

Mitigation：

R18 为硬边界。

发现邻近代码“看起来也能优化”时默认不修改，除非它阻塞本计划 Acceptance Evidence。

## Risk 7 — Target-free Comparison wire format and privacy boundary regression

Mitigation & Acceptance Gate：

在 U3 中执行 1:1 安全验证测试迁移清单，将 `test_process_adapter.py` 中所有的负向防护测试（target field rejection、split membership rejection、unknown request fields rejection、core-owned output fields rejection、timeout 处理、stderr privacy 与 error masking）全部完整绑定在 `predict_comparison` 上，必须全绿方可通过 U3 gate。

## Risk 8 — Information leakage in reproduction CLI dirty-worktree and subprocess execution

Mitigation & Acceptance Gate：

保持 dirty-worktree error masking 与 stderr privacy 行为不变；将 `test_run_cli.py` 和 `test_reproduction_recovery_cli.py` 中的 privacy/error masking 测试作为 U2 的硬验收门禁。

---

# 9. Definition of Done

本计划只有在以下条件全部成立时才能标记 completed：

- 两个 Program 的 official in-process façade 只剩 `probe` / `execute`，direct-script `main()` 保持 thin transport adapter。
- `test_reproduction_artifacts.py` 不再耦合 Program 内部 selection helper，selection 职责分离保持。
- Program internals仍然 deep，不出现 lifecycle fragmentation。
- Root CLI 不再拥有 attempt-specific reproduction knowledge。
- Reproduction CLI orchestration归 reproduction namespace，`register_reproduction_commands` 是唯一 composition seam。
- 所有现有 CLI observable behavior保持。
- Root CLI tests不再耦合 reproduction private handlers。
- `PredictionAdapter` 删除。
- `ProcessPredictionAdapter.predict` 删除。
- `predict_comparison` 保持 target-free、严格、privacy-safe，1:1 安全负向测试全绿。
- `accept-comparison` file workflow保持。
- Registry / RemoteExecutor / queue / attempt / evidence authority不发生漂移，`evaluation_queue.py` 位于 `src/medrec_research/reproduction/`。
- MoleRec Python 3.8 compatibility保持。
- full pytest green。
- ruff check green。
- ruff format check green。
- docs lint green（若 docs 变化）。
- 静态搜索无废弃 surface residual。
- diff review 无 scope creep。
- 没有执行任何新的 scientific workload。

完成后，Software Design Philosophy 的 8 项 architecture diagnostic 应从当前 `5/8` 提升为目标 `8/8`：

1. module responsibility 可一句话描述；
2. interfaces 明显小于 implementations；
3. implementation change locality；
4. design comments；
5. strategic design；
6. deep modules；
7. newcomer 可从 module boundary 理解系统；
8. complexity 被主动删除而非重新包装。

---

# 10. Compound Engineering Execution Handoff

交给执行代理时使用：

```text
/goal Implement docs/plans/2026-09-01-refactor-architecture-surface-hardening-plan.md through its Definition of Done.

Treat Settled Decisions, Requirements, Architecture Preservation constraints, Acceptance Evidence, and Unit ordering as authoritative.

Execute U0 → U1 → U2 → U3 → U4 → U5 in order.

Do not redesign scientific architecture. Do not add compatibility shims, generic frameworks, Program base classes, callback lifecycle abstractions, or unrelated cleanup.

For each U-ID, inspect the current code before deciding the exact implementation HOW. Run that unit's targeted verification before proceeding.

After implementation:
1. simplify the diff without changing behavior;
2. perform architecture-focused code review;
3. fix eligible review findings;
4. run the full verification contract;
5. report residual findings rather than expanding scope.

No real-data, remote 319, retraining, or test-set scientific execution is permitted.
```

## Post-Review Compound Step

只有在本次实现产生新的、可复用且此前文档未表达的工程经验时，才进入 compound：

优先沉淀以下类型的 lesson：

- façade 应在移动 orchestration 之前先变窄；
- deep module 的目标是隐藏知识，不是降低 LOC；
- 跨 Python runtime 的重复可能是正确的信息隐藏；
- deletion test 可以区分真实 seam 与历史 compatibility debris。

若没有新的 lesson，不为了完成流程而制造文档。
