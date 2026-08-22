# MedRec Research

MedRec Research is the active repository for general computer-science research on medication recommendation. It provides shared cohort, prediction, evaluation, provenance, and baseline-comparison semantics without binding the library to one research idea.

## Quick start

### Environment setup

Use Python 3.11 and the Homebrew `uv` executable:

```bash
rtk proxy /opt/homebrew/bin/uv sync
rtk proxy /opt/homebrew/bin/uv run pytest
rtk proxy /opt/homebrew/bin/uv run ruff check .
rtk proxy /opt/homebrew/bin/uv run ruff format --check .
```

### CLI commands

You can use `./start-research` or `medrec` / `medrec-research`:

1. **List baselines**:

   ```bash
   ./start-research baseline list
   ```

2. **Run synthetic reference slice**:

   ```bash
   ./start-research reference \
     --manifest fixtures/synthetic/manifest.json \
     --visits fixtures/synthetic/visits.json \
     --output /tmp/medrec-reference-run.json \
     --top-k 2 \
     --seed 0
   ```

3. **Evaluate predictions**:

   ```bash
   ./start-research evaluate \
     --predictions /path/to/predictions.json \
     --output /tmp/metrics.json
   ```

4. **Accept comparison run (Comparison Mode)**:

   ```bash
   ./start-research accept-comparison \
     --manifest fixtures/synthetic/manifest.json \
     --registry baselines/registry.toml \
     --baseline-id comparison-reference \
     --predictions /path/to/predictions.json \
     --medication-vocabulary /path/to/medications.txt \
     --run-config /path/to/run-config.json \
     --adaptation-budget /path/to/adaptation-budget.json \
     --output /path/to/run-record.json
   ```

5. **Plan a remote GAMENet reproduction run**:

   ```bash
   ./start-research run \
     --mode reproduction \
     --baseline-id gamenet \
     --gpu 0 \
     --min-free-gpu-mib 20000 \
     --min-free-disk-gib 100 \
     --dry-run
   ```

   Dry-run validates the local declaration and prints the explicit 319 command without opening SSH or running remote preflight. Removing `--dry-run` is allowed only for a clean immutable local revision after the registry entry reaches at least `smoke_ready`; the checked-in registry currently leaves every baseline at `registered`, so it authorizes no real submission.

## Key documents

- [`docs/START_HERE.md`](docs/START_HERE.md): Repository navigation map.
- [`CONTEXT.md`](CONTEXT.md): Canonical domain language and definitions.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): Architecture module and seam map.
- [`docs/specs/UNIFIED_RESEARCH_PROTOCOL.md`](docs/specs/UNIFIED_RESEARCH_PROTOCOL.md): Unified Research Protocol specification.
- [`baselines/registry.toml`](baselines/registry.toml): Baseline identity and readiness registry.
- [`docs/PLANS.md`](docs/PLANS.md): Multi-step work tracker.

## Execution model

- **Local MacBook Terminal**: Runs core tests, synthetic fixtures, protocol checks, and public-safe evidence intake.
- **319 Execution Plane**: Runs real EHR data processing, training, GPU inference, and isolated baseline Conda environments after the remote submission preflight passes.

## Data safety

Set `MEDREC_DATA_ROOT` on 319 to a repository-independent directory before working with EHR data. Do not copy restricted EHR state to the local harness. Never place raw or processed EHR data, patient split membership, patient-level predictions, model weights, private traces, or restricted outputs in this repository.

## Scientific interpretation

Reproduction Mode preserves a baseline's recorded upstream semantics. Comparison Mode uses the Unified Research Protocol and an unchanged Baseline Core. A Prediction Adapter may translate representation, but it may not change the method. Lower retrospective DDI metrics, calibration, or label agreement do not establish clinical safety.
