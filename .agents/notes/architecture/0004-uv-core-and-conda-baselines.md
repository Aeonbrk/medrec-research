# Use Homebrew uv for the core and Conda for baselines

The Python 3.11 core uses the Homebrew `/opt/homebrew/bin/uv` on the Harness Terminal, while each external baseline runs in an isolated Conda environment and separate process on the 319 Execution Plane. A shared environment cannot honestly resolve the conflicting historical Python, PyTorch, CUDA, RDKit, and scientific-package constraints across baselines.
