#!/usr/bin/env python3
"""Compare the fixed-131 and generalized MICA implementations without training."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import torch


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load MICA module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _state_summary(left: dict[str, torch.Tensor], right: dict[str, torch.Tensor]) -> dict[str, Any]:
    left_names = list(left)
    right_names = list(right)
    if left_names != right_names:
        raise RuntimeError("parameter names differ")
    shape_mismatches = [
        name for name in left_names if tuple(left[name].shape) != tuple(right[name].shape)
    ]
    if shape_mismatches:
        raise RuntimeError(f"parameter shapes differ: {shape_mismatches}")
    diffs = {
        name: float((left[name].detach().cpu() - right[name].detach().cpu()).abs().max().item())
        for name in left_names
    }
    return {
        "parameter_names_identical": True,
        "parameter_shapes_identical": True,
        "parameter_count": int(sum(value.numel() for value in left.values())),
        "initialized_tensor_max_abs_diff": max(diffs.values(), default=0.0),
        "initialized_tensor_exact": all(value == 0.0 for value in diffs.values()),
    }


def run(old_path: Path, new_path: Path, device_name: str) -> dict[str, Any]:
    old = _load_module(old_path, "mica_fixed_131")
    new = _load_module(new_path, "mica_generalized")
    device = torch.device(device_name)
    old.configure_numeric_policy()
    new.configure_numeric_policy()
    torch.manual_seed(20260914)
    fixed = old.MICA(7, 5, "drug_query").to(device).eval()
    torch.manual_seed(20260914)
    generalized = new.MICA(7, 5, "drug_query", medication_count=131).to(device).eval()
    state = _state_summary(fixed.state_dict(), generalized.state_dict())

    rows = [
        {"diagnoses": [1, 3, 3], "procedures": [0, 2], "history": []},
        {
            "diagnoses": [2],
            "procedures": [1, 4],
            "history": [([0, 5], [2], [3, 8]), ([6], [0, 3], [1, 7, 10])],
        },
        {
            "diagnoses": [],
            "procedures": [2],
            "history": [([], [], [])],
        },
    ]
    old_batch = {key: value.to(device) for key, value in old.pack_inputs(rows, 7, 5).items()}
    new_batch = {key: value.to(device) for key, value in new.pack_inputs(rows, 7, 5).items()}
    if old_batch.keys() != new_batch.keys() or any(
        not torch.equal(old_batch[key], new_batch[key]) for key in old_batch
    ):
        raise RuntimeError("target-free packed inputs differ")
    with torch.no_grad():
        old_logits = fixed(old_batch)
        new_logits = generalized(new_batch)
    logits_diff = float((old_logits - new_logits).abs().max().item())

    target = torch.zeros((len(rows), 131), device=device, dtype=torch.float32)
    target[0, 0] = 1.0
    target[1, 5] = 1.0
    ddi = torch.zeros((131, 131), device=device, dtype=torch.float32)
    ddi[0, 1] = ddi[1, 0] = 1.0
    ddi[5, 10] = ddi[10, 5] = 1.0
    old_objective = old.objective(old_logits, target, ddi)
    new_objective = new.objective(new_logits, target, ddi, medication_count=131)
    objective_diffs = [
        float((left - right).abs().item())
        for left, right in zip(old_objective, new_objective, strict=False)
    ]
    result = {
        "status": "PASS"
        if logits_diff <= 1e-6
        and max(objective_diffs, default=0.0) <= 1e-7
        and state["initialized_tensor_exact"]
        else "FAIL",
        "old_source_revision": "5864011a864851c7eba1ed2a0742221c9e7dcf5f",
        "new_source_revision": "ffdaec8a6c0cdc20d071ad00eca8bb025f336ef0",
        "variant": "drug_query",
        "medication_count": 131,
        "device": str(device),
        "numeric_policy": new.configure_numeric_policy(),
        "state": state,
        "forward_logits_max_abs_diff": logits_diff,
        "objective_component_abs_diffs": objective_diffs,
        "objective_component_max_abs_diff": max(objective_diffs, default=0.0),
        "target_free_input": True,
        "target_source": "deterministic synthetic labels for objective only",
    }
    if result["status"] != "PASS":
        raise RuntimeError(json.dumps(result, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    print(json.dumps(run(args.old, args.new, args.device), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
