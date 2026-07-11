# 319 environments

The core library does not install external baseline dependencies. Each baseline runs in a named Conda environment and communicates through the process adapter. The separate `medrec-core-evaluator` environment owns restricted Prediction Record validation and aggregate recomputation.

`core-evaluator.yml`, `gamenet.yml`, and `safedrug.yml` are provisional Linux specifications for 319. None is a verified lock. The baseline files preserve dependency information available in the Research Archive; Python 3.8 is an integration choice compatible with the recorded package era, not a recovered upstream fact.

Known unresolved points block `smoke_ready` and `comparison_ready`:

- The archived GAMENet tree has no immutable upstream revision and documents only Python `>=3.5` and PyTorch `>=0.4`.
- GAMENet imports `dnc`, but the archived instructions do not pin its version.
- The archived SafeDrug instructions list reference package versions but do not pin Python or a source commit.
- CUDA, driver, and hardware compatibility still need verification on the execution host.
- The core evaluator needs an explicit 319 Linux lock and environment checksum before it can accept evidence.

Create these environments only on 319 after checking disk, GPU, driver, and existing Conda environments. Do not create them on the MacBook or solve them into the Homebrew `uv` core environment.

```bash
conda env create --file environments/core-evaluator.yml
conda env create --file environments/gamenet.yml
conda env create --file environments/safedrug.yml
```

After verification, export explicit locks for the target platform. Record each baseline lock checksum in the Baseline Registry and the core evaluator lock checksum in the experiment plan. Do not advance readiness merely because Conda resolves a file.
