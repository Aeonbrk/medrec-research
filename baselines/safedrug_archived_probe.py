#!/usr/bin/env python3
"""Environment and program probing for archived SafeDrug."""

from __future__ import annotations

import hashlib
import importlib
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Support both relative import and path-based import
if __package__:
    from .safedrug_archived_contract import (
        ARCHIVED_REVISION,
        REGISTRY_IMPORT_MODULES,
        REPORTED_PAPER_METADATA,
        ReproductionError,
        profile_for,
        verify_upstream_source,
    )
    from .safedrug_archived_data import load_and_validate_canonical_inputs
else:
    _pkg_dir = str(Path(__file__).parent)
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)
    from safedrug_archived_contract import (
        ARCHIVED_REVISION,
        REGISTRY_IMPORT_MODULES,
        REPORTED_PAPER_METADATA,
        ReproductionError,
        profile_for,
        verify_upstream_source,
    )
    from safedrug_archived_data import load_and_validate_canonical_inputs


def environment_summary() -> dict[str, str]:
    conda_exe = shutil.which("conda")
    if not conda_exe:
        for candidate in (
            Path(sys.prefix).parent.parent / "bin" / "conda",
            Path(sys.prefix).parent / "bin" / "conda",
            Path.home() / "anaconda3" / "bin" / "conda",
            Path.home() / "miniconda3" / "bin" / "conda",
            Path("/root/anaconda3/bin/conda"),
            Path("/root/miniconda3/bin/conda"),
        ):
            if candidate.is_file():
                conda_exe = str(candidate)
                break
    if not conda_exe:
        conda_exe = "conda"

    try:
        explicit = subprocess.run(
            [conda_exe, "list", "--explicit", "-p", sys.prefix],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReproductionError("unable to record active Conda environment") from error
    return {
        "conda_explicit_sha256": hashlib.sha256(explicit).hexdigest(),
        "python": sys.version.split()[0],
    }


def _nvidia_driver_version() -> str:
    proc_path = Path("/proc/driver/nvidia/version")
    if proc_path.is_file():
        try:
            content = proc_path.read_text(encoding="utf-8")
            match = re.search(r"NVRM version:\s*([^\s]+)", content)
            if match:
                return match.group(1)
        except OSError:
            pass
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip().splitlines()[0]
    except OSError:
        pass
    return "unknown"


def _package_version(module_name: str) -> str:
    try:
        mod = importlib.import_module(module_name)
        ver = getattr(mod, "__version__", None)
        if ver is not None:
            return str(ver)
    except Exception:
        pass
    try:
        metadata_mod = importlib.import_module("importlib.metadata")
        return metadata_mod.version(module_name)
    except Exception:
        pass
    return "unknown"


def probe_environment_details() -> dict[str, Any]:
    summary = environment_summary()
    torch_mod = sys.modules.get("torch") or importlib.import_module("torch")

    torch_cuda = getattr(getattr(torch_mod, "version", None), "cuda", None) or "unknown"
    cuda_count = torch_mod.cuda.device_count() if torch_mod.cuda.is_available() else 0
    gpu_name = torch_mod.cuda.get_device_name(0) if cuda_count > 0 else "unknown"
    if cuda_count > 0:
        cap = torch_mod.cuda.get_device_capability(0)
        gpu_cap = f"{cap[0]}.{cap[1]}"
    else:
        gpu_cap = "unknown"

    return {
        "conda_explicit_sha256": summary["conda_explicit_sha256"],
        "python": summary["python"],
        "pytorch": getattr(torch_mod, "__version__", "unknown"),
        "torch_cuda": str(torch_cuda),
        "nvidia_driver": _nvidia_driver_version(),
        "numpy": _package_version("numpy"),
        "pandas": _package_version("pandas"),
        "scipy": _package_version("scipy"),
        "scikit_learn": _package_version("sklearn"),
        "rdkit": _package_version("rdkit"),
        "dill": _package_version("dill"),
        "dnc": _package_version("dnc"),
        "cuda_visible_device_count": cuda_count,
        "gpu_name": gpu_name,
        "gpu_capability": gpu_cap,
    }


def check_cuda_tensor() -> str:
    try:
        torch_mod = sys.modules.get("torch") or importlib.import_module("torch")
        if not torch_mod.cuda.is_available():
            raise ReproductionError("CUDA is not available")
        if torch_mod.cuda.device_count() != 1:
            raise ReproductionError(
                f"expected exactly 1 visible CUDA device, observed {torch_mod.cuda.device_count()}"
            )
        tensor_sum = (torch_mod.ones(1, device="cuda") + 1.0).sum().item()
        if tensor_sum != 2.0:
            raise ReproductionError(
                f"CUDA tensor calculation error: expected 2.0, observed {tensor_sum}"
            )
        return "passed"
    except Exception as error:
        raise ReproductionError(f"CUDA tensor check failed: {error}") from error


def check_rdkit_brics() -> str:
    try:
        chem_mod = importlib.import_module("rdkit.Chem")
        brics_mod = importlib.import_module("rdkit.Chem.BRICS")
        mol = chem_mod.MolFromSmiles("CC(=O)OC1=CC=CC=C1C(=O)O")
        if mol is None:
            raise ReproductionError("RDKit failed to parse test SMILES")
        frags = list(brics_mod.BRICSDecompose(mol))
        if not frags:
            raise ReproductionError("RDKit BRICSDecompose returned empty fragments")
        return "passed"
    except Exception as error:
        raise ReproductionError(f"RDKit BRICS check failed: {error}") from error


def check_dnc_forward() -> str:
    try:
        dnc_mod = importlib.import_module("dnc")
        dnc_cls = dnc_mod.DNC
        torch_mod = sys.modules.get("torch") or importlib.import_module("torch")
        use_cuda = torch_mod.cuda.is_available()
        gpu_id = 0 if use_cuda else -1
        rnn = dnc_cls(
            input_size=10,
            hidden_size=20,
            rnn_type="lstm",
            num_layers=1,
            num_hidden_layers=1,
            nr_cells=5,
            cell_size=10,
            read_heads=2,
            batch_first=True,
            gpu_id=gpu_id,
        )
        x = torch_mod.randn(1, 4, 10)
        if use_cuda:
            x = x.cuda()
        out, _ = rnn(x)
        if out is None or out.shape[0] != 1:
            raise ReproductionError("dnc forward produced invalid output shape")
        return "passed"
    except Exception as error:
        raise ReproductionError(f"dnc forward check failed: {error}") from error


def check_imports(upstream_root: Path) -> dict[str, str]:
    src_dir = str(upstream_root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    results = {}
    for module_name in REGISTRY_IMPORT_MODULES:
        try:
            importlib.import_module(module_name)
            results[module_name] = "passed"
        except Exception as error:
            raise ReproductionError(f"failed to import '{module_name}': {error}") from error
    return results


def run_probe(
    *,
    baseline_id: str,
    upstream_root: Path,
    data_dir: Path | None,
    scope: str,
    dispatch_module: Any = None,
) -> dict[str, Any]:
    if scope not in ("environment", "full"):
        raise ReproductionError(f"unknown probe scope '{scope}'")

    mod = (
        dispatch_module
        or sys.modules.get("safedrug_archived_program")
        or sys.modules.get("baselines.safedrug_archived")
        or sys.modules.get("safedrug_archived")
        or sys.modules[__name__]
    )

    get_profile = getattr(mod, "profile_for", profile_for)
    get_profile(baseline_id)

    verify_src = getattr(mod, "verify_upstream_source", verify_upstream_source)
    verify_src(upstream_root)

    chk_imports = getattr(mod, "check_imports", check_imports)
    import_checks = chk_imports(upstream_root)

    chk_cuda = getattr(mod, "check_cuda_tensor", check_cuda_tensor)
    cuda_status = chk_cuda()

    chk_rdkit = getattr(mod, "check_rdkit_brics", check_rdkit_brics)
    rdkit_status = chk_rdkit()

    chk_dnc = getattr(mod, "check_dnc_forward", check_dnc_forward)
    dnc_status = chk_dnc()

    probe_env = getattr(mod, "probe_environment_details", probe_environment_details)
    env_details = probe_env()

    if env_details["cuda_visible_device_count"] != 1:
        raise ReproductionError("probe requires exactly 1 visible CUDA device")

    inputs_result: dict[str, str] | None = None
    dataset_counts: dict[str, int] | None = None
    bridge_checks: dict[str, str] | None = None
    statistics_evidence: dict[str, Any] | None = None
    metadata_disclosure: dict[str, int] | None = None

    if scope == "full":
        if data_dir is None:
            raise ReproductionError("full probe scope requires --dataset-root")
        load_inputs = getattr(
            mod, "load_and_validate_canonical_inputs", load_and_validate_canonical_inputs
        )
        (
            inputs_result,
            dataset_counts,
            bridge_checks,
            statistics_evidence,
            metadata_disclosure,
        ) = load_inputs(data_dir)

    return {
        "schema_version": 1,
        "kind": "safedrug_archived_probe",
        "scope": scope,
        "baseline_id": baseline_id,
        "source_revision": ARCHIVED_REVISION,
        "environment": env_details,
        "checks": {
            "imports": import_checks,
            "cuda_tensor": cuda_status,
            "rdkit_brics": rdkit_status,
            "dnc_forward": dnc_status,
        },
        "inputs": inputs_result,
        "dataset_counts": dataset_counts,
        "bridge_checks": bridge_checks,
        "statistics": statistics_evidence,
        "metadata": metadata_disclosure or REPORTED_PAPER_METADATA,
    }
