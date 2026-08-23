# 319 environments

The core library does not install external baseline dependencies. Each baseline runs in a named Conda environment and communicates through the process adapter. The separate `medrec-core-evaluator` environment owns restricted Prediction Record validation and aggregate recomputation.

`core-evaluator.yml` is a provisional Linux specification for 319, not a verified lock. Baseline environment declarations are intentionally absent until the SafeDrug archived stack is resolved and verified on 319.

Known unresolved points block `smoke_ready` and `comparison_ready`:

- SafeDrug archived documents Python 3.7 and reference package versions, but the RTX 3090-compatible environment still requires verification.
- GAMENet imports `dnc`, but archived instructions do not pin its version.
- CUDA, driver, and hardware compatibility still need verification on the execution host.
- The core evaluator needs an explicit 319 Linux lock and environment checksum before it can accept evidence.

Create these environments only on 319 after checking disk, GPU, driver, and existing Conda environments. Do not create them on the MacBook or solve them into the Homebrew `uv` core environment.

```bash
conda env create --file environments/core-evaluator.yml
```

The Baseline Registry already declares one shared archived environment name. After verification, record its target-platform identity there; split into per-lane declarations only if observed dependency differences require it. Record the core evaluator identity in the experiment plan. Do not advance readiness merely because Conda resolves a file.
