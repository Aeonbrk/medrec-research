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
    torch.manual_seed(20260914)
    early = MICA(3, 2, "early").to(device)
    torch.manual_seed(20260914)
    late = MICA(3, 2, "late").to(device)
    early_state = early.state_dict()
    late_state = late.state_dict()
    if (
        list(early_state) != list(late_state)
        or any(not torch.equal(early_state[name], late_state[name]) for name in early_state)
        or sum(p.numel() for p in early.parameters()) != sum(p.numel() for p in late.parameters())
    ):
        raise RuntimeError("early/late parameter names or counts differ")
    # The zero conditioner is part of the model initialization contract.
    early.eval()
    late.eval()
    with torch.no_grad():
        e0 = early(packed)
        l0 = late(packed)
        e_perm = early(packed_permuted)
    if not torch.allclose(e0, l0, atol=1e-5, rtol=1e-5):
        raise RuntimeError("early and late zero-conditioner logits differ")
    if not torch.allclose(e0, e_perm, atol=1e-5, rtol=1e-5):
        raise RuntimeError("canonicalized current-code permutation changed logits")
    gradients = {}
    target = torch.zeros((2, 131), device=device)
    target[0, 0] = 1.0
    ddi = torch.zeros((131, 131), device=device)
    ddi[0, 1] = ddi[1, 0] = 1.0
    for name, model in (("early", early), ("late", late)):
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
        "parameter_count": sum(p.numel() for p in early.parameters()),
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
