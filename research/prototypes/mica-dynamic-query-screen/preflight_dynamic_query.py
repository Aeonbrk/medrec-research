#!/usr/bin/env python3
"""Minimal synthetic checks for the bounded MICA dynamic-query screen."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mica_dynamic_query import (
    ADAPTER_VARIANTS,
    MULTIQUERY_VARIANTS,
    VARIANTS,
    MICADynamicQuery,
    parameter_count,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mica"))
from mica import MICA as BaseMICA
from mica import objective, pack_inputs

SEED = 20260914
DX = 32
PROC = 16


def _seed() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)


def _batch(device: torch.device) -> dict[str, torch.Tensor]:
    rows: list[dict[str, Any]] = [
        {
            "diagnoses": [1, 3, 7],
            "procedures": [2, 4],
            "history": [([2, 5], [1], [3, 9]), ([1], [3, 5], [2, 4, 8])],
        },
        {
            "diagnoses": [0, 9, 11, 17],
            "procedures": [0, 7],
            "history": [([6], [2, 9], [1, 10])],
        },
    ]
    return {key: value.to(device) for key, value in pack_inputs(rows, DX, PROC).items()}


def _same_state(left: torch.nn.Module, right: torch.nn.Module) -> bool:
    left_state = left.state_dict()
    right_state = right.state_dict()
    if tuple(left_state) != tuple(right_state):
        return False
    return all(torch.equal(left_state[key], right_state[key]) for key in left_state)


def run(device_name: str) -> dict[str, Any]:
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    device = torch.device(device_name)
    batch = _batch(device)

    _seed()
    base = BaseMICA(DX, PROC, "drug_query").to(device).eval()
    _seed()
    core = MICADynamicQuery(DX, PROC, "core").to(device).eval()
    if parameter_count(base) != parameter_count(core) or not _same_state(base, core):
        raise RuntimeError("Core is not the exact inherited MICA DrugQuery parameterization")
    with torch.no_grad():
        if not torch.allclose(base(batch), core(batch), atol=1e-7, rtol=1e-6):
            raise RuntimeError("Core logits differ from exact MICA DrugQuery")

    multi_models = []
    for variant in sorted(MULTIQUERY_VARIANTS):
        _seed()
        multi_models.append(MICADynamicQuery(DX, PROC, variant).to(device))
    if len({parameter_count(model) for model in multi_models}) != 1:
        raise RuntimeError("multi-query variants are not parameter matched")
    if not all(_same_state(multi_models[0], model) for model in multi_models[1:]):
        raise RuntimeError("multi-query variants do not start from identical parameters")

    adapter_models = []
    for variant in sorted(ADAPTER_VARIANTS):
        _seed()
        adapter_models.append(MICADynamicQuery(DX, PROC, variant).to(device))
    if len({parameter_count(model) for model in adapter_models}) != 1:
        raise RuntimeError("adapter variants are not parameter matched")
    if not _same_state(adapter_models[0], adapter_models[1]):
        raise RuntimeError("adapter variants do not start from identical parameters")
    for model in adapter_models:
        model.eval()
    with torch.no_grad():
        static_logits = adapter_models[0](batch)
        dynamic_logits = adapter_models[1](batch)
        core_logits = core(batch)
        if not torch.allclose(static_logits, core_logits, atol=1e-7, rtol=1e-6):
            raise RuntimeError("zero-initialized static adapter does not start at Core")
        if not torch.allclose(dynamic_logits, core_logits, atol=1e-7, rtol=1e-6):
            raise RuntimeError("zero-initialized dynamic adapter does not start at Core")

    ddi = torch.zeros(131, 131, device=device)
    targets = torch.zeros(2, 131, device=device)
    targets[0, [1, 3, 5]] = 1.0
    targets[1, [0, 4, 9]] = 1.0
    gradient_checks = {}
    for variant in VARIANTS:
        _seed()
        model = MICADynamicQuery(DX, PROC, variant).to(device).train()
        logits = model(batch)
        if not torch.isfinite(logits).all():
            raise RuntimeError("non-finite logits for " + variant)
        loss = objective(logits, targets, ddi)[0]
        loss.backward()
        gradients = [parameter.grad for parameter in model.parameters() if parameter.requires_grad]
        if any(gradient is not None and not torch.isfinite(gradient).all() for gradient in gradients):
            raise RuntimeError("non-finite gradient for " + variant)
        total = float(
            sum(
                gradient.detach().abs().sum().item()
                for gradient in gradients
                if gradient is not None
            )
        )
        if total <= 0.0:
            raise RuntimeError("zero total gradient for " + variant)
        if variant in MULTIQUERY_VARIANTS:
            route_grad = model.route_delta.grad
            prior_grad = model.route_prior.grad
            if route_grad is None or float(route_grad.abs().sum().item()) <= 0.0:
                raise RuntimeError("route_delta receives no gradient for " + variant)
            if prior_grad is None or float(prior_grad.abs().sum().item()) <= 0.0:
                raise RuntimeError("route_prior receives no gradient for " + variant)
        if variant in ADAPTER_VARIANTS:
            adapter_grad = model.query_adapter[2].weight.grad
            if adapter_grad is None or float(adapter_grad.abs().sum().item()) <= 0.0:
                raise RuntimeError("query adapter receives no gradient for " + variant)
        gradient_checks[variant] = total

    return {
        "status": "PASS",
        "device": str(device),
        "core_parameter_count": parameter_count(core),
        "multiquery_parameter_count": parameter_count(multi_models[0]),
        "adapter_parameter_count": parameter_count(adapter_models[0]),
        "core_exact_match": True,
        "multiquery_parameter_and_initialization_match": True,
        "adapter_parameter_and_initialization_match": True,
        "adapter_zero_init_matches_core": True,
        "finite_forward_backward": True,
        "gradient_l1": gradient_checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    print(json.dumps(run(args.device), sort_keys=True))


if __name__ == "__main__":
    main()
