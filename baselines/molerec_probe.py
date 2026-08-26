#!/usr/bin/env python3
"""Environment probing and readiness verification for MoleRec reproduction."""

from __future__ import annotations

import importlib
import importlib.util
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .molerec_contract import (
        ARCHIVED_REVISION,
        REGISTRY_IMPORT_MODULES,
        profile_for,
        sha256,
        verify_upstream_source,
    )
    from .molerec_data import load_and_validate_canonical_inputs
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from molerec_contract import (
        ARCHIVED_REVISION,
        REGISTRY_IMPORT_MODULES,
        profile_for,
        sha256,
        verify_upstream_source,
    )
    from molerec_data import load_and_validate_canonical_inputs


def _package_version(module_name: str) -> str | None:
    try:
        mod = importlib.import_module(module_name)
        return str(getattr(mod, "__version__", "unknown"))
    except ImportError:
        return None


def _nvidia_driver_version() -> str | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return None


def check_imports() -> dict[str, str | None]:
    return {module: _package_version(module) for module in REGISTRY_IMPORT_MODULES}


def check_cuda_tensor() -> bool:
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        tensor = torch.tensor([1.0, 2.0, 3.0], device="cuda:0")
        return bool(tensor.sum().item() == 6.0)
    except Exception:
        return False


def check_rdkit() -> bool:
    try:
        from rdkit import Chem
        from rdkit.Chem import BRICS

        mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
        if mol is None:
            return False
        pieces = BRICS.BRICSDecompose(mol)
        return len(pieces) > 0
    except Exception:
        return False


def check_gensim() -> bool:
    try:
        import gensim
        from gensim.models import Word2Vec

        # Quick check that Word2Vec class is accessible
        return hasattr(gensim.models, "Word2Vec") or hasattr(Word2Vec, "load")
    except Exception:
        return False


def environment_summary() -> dict[str, Any]:
    env_file = Path(os.environ.get("CONDA_PREFIX", "")) / "conda-meta" / "pinned"
    conda_sha = sha256(env_file) if env_file.is_file() else "unpinned"
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "packages": check_imports(),
        "cuda_available": check_cuda_tensor(),
        "rdkit_working": check_rdkit(),
        "gensim_working": check_gensim(),
        "driver_version": _nvidia_driver_version(),
        "conda_explicit_sha256": conda_sha,
    }


def probe_environment_details() -> dict[str, Any]:
    return environment_summary()


def run_probe(
    *,
    baseline_id: str,
    upstream_root: Path,
    data_dir: Path | None = None,
    scope: str = "full",
) -> dict[str, Any]:
    profile = profile_for(baseline_id)
    env_info = environment_summary()

    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "molerec_probe",
        "baseline_id": profile.baseline_id,
        "source_revision": ARCHIVED_REVISION,
        "environment": env_info,
    }

    if scope == "environment":
        return report

    verify_upstream_source(upstream_root)

    if data_dir is not None and data_dir.is_dir():
        _, counts, _, _, _ = load_and_validate_canonical_inputs(data_dir)
        report["dataset_counts"] = counts
    else:
        report["dataset_counts"] = None

    return report
