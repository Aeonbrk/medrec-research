# 319 environments

The core library does not install external baseline dependencies. Each baseline runs in a named Conda environment and communicates through the process adapter. The separate `medrec-core-evaluator` environment owns restricted Prediction Record validation and aggregate recomputation.

- `core-evaluator.yml`: Provisional 319 evaluator environment specification.
- `safedrug-archived.yml`: Candidate 319 baseline environment specification for the SafeDrug archived four-model reproduction (`gamenet`, `safedrug`, `retain`, `leap-safedrug`).

The candidate baseline environment specifies:

- Python 3.11
- PyTorch 2.2.2 with CUDA 12.1
- NumPy 1.26.4
- pandas 2.0.3
- SciPy 1.11.4
- scikit-learn 1.3.2
- RDKit 2023.09.6
- dill 0.3.7
- dnc 1.1.0

The explicit Linux lock (`environments/safedrug-archived-linux-64.lock`) is exported from the candidate environment only after dependency/runtime checks and staged-data validation succeed on 319. The declared baseline environment is then recreated from that lock, validated against the complete versioned program probe, and its explicit lock hash is recorded in `baselines/registry.toml`.
