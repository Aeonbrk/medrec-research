#!/usr/bin/env python3
"""Environment probing and readiness verification for MoleRec reproduction."""

from __future__ import annotations

import hashlib
import importlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .molerec_data import (
        REPORTED_PAPER_METADATA,
        ReproductionError,
        load_and_validate_canonical_inputs,
    )
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from molerec_data import (
        REPORTED_PAPER_METADATA,
        ReproductionError,
        load_and_validate_canonical_inputs,
    )

ARCHIVED_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"
REGISTRY_IMPORT_MODULES = (
    "torch",
    "torch_geometric",
    "ogb",
    "rdkit",
    "pandas",
    "dill",
    "sklearn",
)
PYG_EXTENSION_MODULES = (
    "torch_scatter",
    "torch_sparse",
    "torch_cluster",
    "torch_spline_conv",
)


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


def _conda_explicit_sha256() -> str:
    conda = os.environ.get("CONDA_EXE") or shutil.which("conda")
    if not conda:
        return "unpinned"
    try:
        completed = subprocess.run(
            [conda, "list", "--explicit", "-p", sys.prefix],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unpinned"
    return hashlib.sha256(completed.stdout).hexdigest()


def check_cuda_tensor() -> bool:
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        tensor = torch.tensor([1.0, 2.0, 3.0], device="cuda:0")
        return bool(tensor.sum().item() == 6.0)
    except Exception:
        return False


def _cuda_device_details() -> dict[str, Any]:
    try:
        import torch

        if not torch.cuda.is_available():
            return {
                "cuda_visible_device_count": 0,
                "gpu_name": "unknown",
                "gpu_capability": "unknown",
            }
        device_count = int(torch.cuda.device_count())
        if device_count == 0:
            return {
                "cuda_visible_device_count": 0,
                "gpu_name": "unknown",
                "gpu_capability": "unknown",
            }
        capability = torch.cuda.get_device_capability(0)
        return {
            "cuda_visible_device_count": device_count,
            "gpu_name": torch.cuda.get_device_name(0),
            "gpu_capability": f"{capability[0]}.{capability[1]}",
        }
    except Exception:
        return {
            "cuda_visible_device_count": 0,
            "gpu_name": "unknown",
            "gpu_capability": "unknown",
        }


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


def check_pyg_extensions() -> bool:
    try:
        importlib.import_module("torch_geometric")
        for module_name in PYG_EXTENSION_MODULES:
            importlib.import_module(module_name)
        return True
    except Exception:
        return False


def environment_summary() -> dict[str, Any]:
    cuda_details = _cuda_device_details()
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "packages": check_imports(),
        "cuda_available": check_cuda_tensor(),
        **cuda_details,
        "rdkit_working": check_rdkit(),
        "pyg_extensions_working": check_pyg_extensions(),
        "driver_version": _nvidia_driver_version(),
        "conda_explicit_sha256": _conda_explicit_sha256(),
    }


def probe_environment_details() -> dict[str, Any]:
    return environment_summary()


def run_probe(
    *,
    baseline_id: str,
    upstream_root: Path,
    data_dir: Path | None = None,
    scope: str = "full",
    dispatch_module: Any = None,
) -> dict[str, Any]:
    mod = dispatch_module or sys.modules.get("baselines.molerec") or sys.modules.get("molerec")
    get_profile = getattr(mod, "profile_for", None)
    profile = get_profile(baseline_id) if get_profile is not None else None
    required_inputs = (
        profile.required_inputs
        if profile is not None
        else (
            "records_final.pkl",
            "voc_final.pkl",
            "ddi_A_final.pkl",
            "ehr_adj_final.pkl",
            "ddi_mask_H.pkl",
            "substructure_smiles.pkl",
            "idx2SMILES.pkl",
            "idx2drug.pkl",
        )
    )

    verify_src = getattr(mod, "verify_upstream_source", None)
    if verify_src is not None:
        verify_src(upstream_root)
    else:
        source_dir = upstream_root / "src"
        if not source_dir.is_dir():
            raise ReproductionError(f"archived upstream missing src directory: {source_dir}")

    env_info = environment_summary()
    package_versions = env_info["packages"]
    import_checks = {
        module: "passed" if package_versions.get(module) is not None else "failed"
        for module in REGISTRY_IMPORT_MODULES
    }
    checks = {
        "imports": import_checks,
        "cuda_tensor": "passed" if env_info["cuda_available"] else "failed",
        "rdkit_brics": "passed" if env_info["rdkit_working"] else "failed",
        "pyg_extensions": ("passed" if env_info["pyg_extensions_working"] else "failed"),
    }
    if any(status != "passed" for status in import_checks.values()) or any(
        checks[name] != "passed" for name in ("cuda_tensor", "rdkit_brics", "pyg_extensions")
    ):
        raise ReproductionError("MoleRec environment probe failed runtime checks")

    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "molerec_probe",
        "scope": scope,
        "baseline_id": baseline_id,
        "source_revision": ARCHIVED_REVISION,
        "environment": env_info,
        "checks": checks,
    }

    if scope == "environment":
        report["inputs"] = None
        report["dataset_counts"] = None
        return report

    if data_dir is None or not data_dir.is_dir():
        raise ReproductionError("full probe scope requires --dataset-root")
    _, counts, _, _, _ = load_and_validate_canonical_inputs(data_dir)
    report["inputs"] = {name: "passed" for name in required_inputs}
    report["dataset_counts"] = counts
    report["metadata"] = REPORTED_PAPER_METADATA

    return report
