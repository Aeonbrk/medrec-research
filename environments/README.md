# 319 environments

The core library does not install external baseline dependencies. Each baseline runs in a named Conda environment and communicates through the process adapter. The separate `medrec-core-evaluator` environment owns restricted Prediction Record validation and aggregate recomputation.

- `core-evaluator.yml`: Provisional 319 evaluator environment specification.
- `safedrug-archived.yml`: Historical recovery declaration for the prior SafeDrug archived four-model attempt. It is not the runtime for the current seven-lane attempt.
- `molerec-table1.yml`: Frozen compatibility environment declaration for all seven lanes of the MoleRec Table 1 five-model attempt.

The historical SafeDrug declaration and explicit Linux lock are retained for recovery and U10 ownership checks. They must not be used to admit a current formal lane.

The MoleRec Table 1 compatibility baseline environment specifies:

- Python 3.8.16
- PyTorch 1.9.0 with CUDA 11.1 (`torch==1.9.0+cu111`)
- PyTorch Geometric 2.0.3 with native extensions (`torch-scatter`, `torch-sparse`, `torch-cluster`, `torch-spline-conv`)
- NumPy 1.23.5
- pandas 1.5.3
- SciPy 1.10.0
- scikit-learn 1.2.0
- RDKit 2022.09.1
- dill 0.3.7
- dnc 1.1.0

Both `safedrug-archived` and `molerec` Reproduction Programs declare this compatibility environment for the current attempt. The Linux lock and environment identity remain provisional until U5 completes on 319; no formal lane is admissible before that proof.

> [!NOTE]
> **Hardware Compatibility Deviation**: Official MoleRec records CUDA 10.2, which predates NVIDIA Ampere (RTX 3090 / SM86) architecture support. `CUDA 11.1` (`torch==1.9.0+cu111`) is the minimal necessary deviation to support RTX 3090 hardware while preserving Python 3.8, PyTorch 1.9, and PyG 2.0.3 package versions.

## Package Resolution and Mirror Policy

- Conda and pip package resolution prioritizes China mirrors (e.g. TUNA, BFSU, Aliyun) via command-scoped or repository-scoped configuration.
- Exact version-specific wheels unavailable from mirrors (e.g., official PyTorch/PyG cu111 builds) fall back to official HTTPS authorities (`https://download.pytorch.org`, `https://data.pyg.org`).
- TLS verification remains strictly enabled (`ssl_verify: true`, no `--trusted-host`), and global machine/user package-manager configurations must never be modified.
