#!/usr/bin/env python3
"""Small deterministic contract preflight for the MICA runner/model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mica import MICA, configure_numeric_policy, objective, pack_inputs


def run(device_name: str = "cpu") -> dict:
    numeric_policy = configure_numeric_policy()
    device = torch.device(device_name)
    rows = [
        {"diagnoses": [2, 1], "procedures": [1], "history": []},
        {"diagnoses": [0], "procedures": [0, 1], "history": [([1], [0], [2])]},
    ]
    permuted = [dict(rows[0], diagnoses=[1, 2]), dict(rows[1], procedures=[1, 0])]
    packed = {k: v.to(device) for k, v in pack_inputs(rows, 3, 2).items()}
    packed_permuted = {k: v.to(device) for k, v in pack_inputs(permuted, 3, 2).items()}
    variants = ("shared_pool", "drug_query", "late")
    models = []
    for variant in variants:
        torch.manual_seed(20260914)
        models.append(MICA(3, 2, variant).to(device))
    reference_state = models[0].state_dict()
    parameter_count = sum(p.numel() for p in models[0].parameters())
    if any(
        list(reference_state) != list(model.state_dict())
        or any(
            not torch.equal(reference_state[name], model.state_dict()[name])
            for name in reference_state
        )
        or sum(p.numel() for p in model.parameters()) != parameter_count
        for model in models[1:]
    ):
        raise RuntimeError("variant parameter names, initial state, or counts differ")
    # The zero conditioner is part of the model initialization contract. The
    # two query-pooling arms must therefore start identically; SharedPool has a
    # deliberately different, shared query and is not expected to match them.
    for model in models:
        model.eval()
    with torch.no_grad():
        outputs = [model(packed) for model in models]
        permuted_outputs = [model(packed_permuted) for model in models]
    if not torch.allclose(outputs[1], outputs[2], atol=1e-5, rtol=1e-5):
        raise RuntimeError("drug-query and late zero-conditioner logits differ")
    if any(
        not torch.allclose(outputs[index], permuted_outputs[index], atol=1e-5, rtol=1e-5)
        for index in range(len(outputs))
    ):
        raise RuntimeError("canonicalized current-code permutation changed logits")
    if any(not torch.isfinite(output).all() for output in outputs):
        raise RuntimeError("target-free variant logits are not finite")
    gradients = {}
    target = torch.zeros((2, 131), device=device)
    target[0, 0] = 1.0
    ddi = torch.zeros((131, 131), device=device)
    ddi[0, 1] = ddi[1, 0] = 1.0
    for index, name in enumerate(variants):
        model = models[index]
        model.train()
        model.zero_grad(set_to_none=True)
        loss, _, _ = objective(model(packed), target, ddi)
        loss.backward()
        gradients_ok = all(
            p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()
        )
        norm = float(model.conditioner.weight.grad.abs().sum().item())
        if not gradients_ok or norm <= 0.0:
            raise RuntimeError(name + " gradients are not finite or conditioner gradient is zero")
        gradients[name] = norm
    return {
        "status": "PASS",
        "device": str(device),
        "parameter_count": parameter_count,
        "conditioner_gradient_l1": gradients,
        "target_free_interface": True,
        "numeric_policy": numeric_policy,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    print(json.dumps(run(args.device), sort_keys=True))


if __name__ == "__main__":
    main()
