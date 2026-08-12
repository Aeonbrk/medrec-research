# MedRec Research

MedRec Research is the active repository for general computer-science research on medication recommendation. It provides shared cohort, prediction, evaluation, provenance, and baseline-comparison semantics without binding the library to one research idea.

## Current status

The repository has one runnable synthetic Protocol Vertical Slice and a public-safe final-five benchmark control surface. GAMENet, SafeDrug, MoleRec, RETAIN, and `LEAP-SafeDrug` are registered, but zero candidates are `smoke_ready` or `comparison_ready`. Audit and status output therefore describe blocked research work, not completed reproductions or experimental evidence.

Prior work remains in the read-only Research Archive at `/Users/oian/Codes/master/New-Search`. Curated findings and failed-route constraints live under [`research/`](research/); new research work belongs here.

## Start here

- [`docs/START_HERE.md`](docs/START_HERE.md) is the repository navigation map.
- [`CONTEXT.md`](CONTEXT.md) defines the project language.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) maps modules and seams.
- [`docs/specs/UNIFIED_RESEARCH_PROTOCOL.md`](docs/specs/UNIFIED_RESEARCH_PROTOCOL.md) defines Comparison Mode.
- [`docs/playbooks/index.md`](docs/playbooks/index.md) indexes operational playbooks.
- [`baselines/registry.toml`](baselines/registry.toml) records baseline identity and readiness.
- [`docs/PLANS.md`](docs/PLANS.md) tracks accepted multi-step work.

## Core environment

Use Python 3.11 and the Homebrew `uv` executable. Do not rely on whichever `uv` appears first on `PATH`.

```bash
rtk proxy /opt/homebrew/bin/uv sync
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
```

Run the local synthetic harness:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec-research reference \
  --manifest fixtures/synthetic/manifest.json \
  --visits fixtures/synthetic/visits.json \
  --output /tmp/medrec-reference-run.json \
  --top-k 2 \
  --seed 7
```

This emits a public-safe Protocol Check Record. It exercises dataset, prediction, evaluation, and provenance modules but is neither Reproduction Mode evidence nor Comparison Mode evidence.

## 本地基线控制面

先验证五个审计，再按固定顺序发布选择结果。硬门优先于顺序；当前顺序是 GAMENet、SafeDrug、MoleRec、RETAIN、`LEAP-SafeDrug`。

```bash
rtk proxy /opt/homebrew/bin/uv run medrec-research audit-validate \
  --program baselines/programs/final-five.toml \
  --audit-dir baselines/audits

rtk proxy /opt/homebrew/bin/uv run medrec-research selection-publish \
  --program baselines/programs/final-five.toml \
  --audit-dir baselines/audits \
  --registry baselines/registry.toml \
  --reviews fixtures/benchmark/audit-reviews.json \
  --scope /tmp/medrec-comparison-scope.json \
  --diagnostics fixtures/benchmark/selection-diagnostics.json \
  --output /tmp/medrec-selection.json
```

`status-publish` 需要显式 Comparison Scope JSON、当前 Audit Review Set 和已发布 Selection Result。Live Benchmark Authority 会重新校验 program、audit、review、registry、scope 与 selection；任一 digest 漂移都会拒绝发布，不会重新选择候选。可选的 V2 Reproduction Characterization 只有在提供匹配的 Selection Acceptance 时才影响状态；V1 记录仅供历史解析，不能推进当前状态。相同时钟输入会产生相同字节；生产 CLI 使用当前 UTC 时间。

```bash
rtk proxy /opt/homebrew/bin/uv run medrec-research status-publish \
  --program baselines/programs/final-five.toml \
  --audit-dir baselines/audits \
  --registry baselines/registry.toml \
  --reviews fixtures/benchmark/audit-reviews.json \
  --selection /tmp/medrec-selection.json \
  --scope /tmp/medrec-comparison-scope.json \
  --output /tmp/medrec-status.json

rtk proxy /opt/homebrew/bin/uv run medrec-research harness \
  --status /tmp/medrec-status.json \
  --port 0
```

Harness 只绑定 `127.0.0.1`。不传 Authority Bundle 时只读；传入后，每次 Action Context GET 和 Action Request POST 都重新解析该 Bundle。浏览器只提交不透明 `request_id`；CLI 调用方先用 `action-context` 取得相同的公共 context。服务器从当前 Status 与显式 Bundle 推导完整绑定并生成允许或 blocked 的 Action Decision/Action Request。它不运行 shell、SSH、Conda 或 319 作业。操作与恢复步骤见 status harness playbook。

External baselines do not run in this environment. Each baseline uses its declared Conda environment and communicates with the core through a separate process.

On 319, `environments/core-evaluator.yml` isolates the core evaluator from every Baseline Environment. The evaluator reads restricted Prediction Records in place, recomputes aggregate metrics, and emits a candidate Comparison Mode Run Record:

```bash
conda run -n medrec-core-evaluator medrec-research accept-comparison \
  --manifest "$MEDREC_RUN_ROOT/manifest.json" \
  --registry baselines/registry.toml \
  --baseline-id "$BASELINE_ID" \
  --predictions "$MEDREC_RUN_ROOT/predictions.json" \
  --medication-vocabulary "$MEDREC_RUN_ROOT/medications.txt" \
  --membership-hmac-key "$MEDREC_DATA_ROOT/keys/membership-hmac.key" \
  --run-config "$MEDREC_RUN_ROOT/run-config.json" \
  --adaptation-budget "$MEDREC_RUN_ROOT/adaptation-budget.json" \
  --output "$MEDREC_RUN_ROOT/run-record.json"
```

This command still rejects every current registry entry because none is `comparison_ready`.

## ARIS control plane

Project-local ARIS Codex skills are installed as ignored symlinks and recorded in an ignored local manifest. Install or reconcile them from the upstream ARIS repository:

```bash
rtk bash /Users/oian/Codes/master/Auto-claude-code-research-in-sleep/tools/install_aris_codex.sh \
  /Users/oian/Codes/master/medrec-research \
  --quiet
```

ARIS runtime traces stay local. Gate-approved protocols, aggregate Run Records, audits, claims, and Failure Records are the durable research state.

## Execution model

The MacBook Air is the harness terminal. It runs ARIS, protocol validation, synthetic fixtures, source submission, monitoring, aggregate-result intake, and public-safe audits. Real EHR experiments, training, GPU inference, and external baseline environments run only on `319-wild`.

The 319 checkout does not exist yet. Do not launch a real experiment until the intended source revision is available on 319, the remote checkout is verified, and the remote preflight in the playbook passes.

## Data safety

Set `MEDREC_DATA_ROOT` on 319 to a repository-independent directory before working with EHR data. Do not copy restricted EHR state to the Mac harness. Never place raw or processed EHR data, patient split membership, patient-level predictions, model weights, private traces, or restricted outputs in this repository.

## Scientific interpretation

Reproduction Mode preserves a baseline's recorded upstream semantics. Comparison Mode uses the Unified Research Protocol and an unchanged Baseline Core. A Prediction Adapter may translate representation, but it may not change the method. Lower retrospective DDI metrics, calibration, or label agreement do not establish clinical safety.
