#!/usr/bin/env python3
"""Minimal structural and CUDA preflight for the six MICA-v2 lanes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mica_v2 import (
    LOGIT_THRESHOLD,
    MEDICATIONS,
    VARIANTS,
    MICAv2,
    base_objective,
    coarse_pack_inputs,
    configure_numeric_policy,
    pack_dual_evidence,
    pack_fine_history,
    parameter_count,
    safe_rank_loss,
    safe_swap,
)

SEED = 20260914


def _state_equal(left: torch.nn.Module, right: torch.nn.Module) -> bool:
    left_state = left.state_dict()
    right_state = right.state_dict()
    return list(left_state) == list(right_state) and all(
        torch.equal(left_state[name], right_state[name]) for name in left_state
    )


def run(device_name: str = "cpu") -> dict[str, object]:
    numeric_policy = configure_numeric_policy()
    device = torch.device(device_name)
    rows = [
        {"diagnoses": [2, 1], "procedures": [1], "history": []},
        {
            "diagnoses": [0],
            "procedures": [0, 1],
            "history": [([1, 0], [0], [2, 1]), ([2], [1], [])],
        },
    ]
    coarse = {key: value.to(device) for key, value in coarse_pack_inputs(rows, 3, 2).items()}
    fine = {key: value.to(device) for key, value in pack_fine_history(rows, 3, 2).items()}
    dual_raw = pack_dual_evidence(rows, 3, 2)
    dual = {
        "current": {key: value.to(device) for key, value in dual_raw["current"].items()},
        "history": {key: value.to(device) for key, value in dual_raw["history"].items()},
        "history_present": dual_raw["history_present"].to(device),
    }
    if fine["mask"].shape[1] <= coarse["mask"].shape[1]:
        raise RuntimeError("FineHistory did not increase historical token granularity")
    if bool(dual["history_present"][0]) or not bool(dual["history_present"][1]):
        raise RuntimeError("DualEvidence history-present mask is not a strict-prefix signal")

    models: dict[str, MICAv2] = {}
    for variant in VARIANTS:
        torch.manual_seed(SEED)
        models[variant] = MICAv2(3, 2, variant).to(device)
    counts = {variant: parameter_count(model) for variant, model in models.items()}
    if counts["core"] != counts["fine_history"] or counts["core"] != counts["safe_rank"]:
        raise RuntimeError("Core, FineHistory, and SafeRank parameter counts differ")
    if counts["self_only"] != counts["set_context"]:
        raise RuntimeError("SelfOnly and SetContext parameter counts differ")
    if not _state_equal(models["core"], models["fine_history"]):
        raise RuntimeError("Core and FineHistory initial states differ")
    if not _state_equal(models["core"], models["safe_rank"]):
        raise RuntimeError("Core and SafeRank initial states differ")
    if not _state_equal(models["self_only"], models["set_context"]):
        raise RuntimeError("SelfOnly and SetContext initial states differ")

    # The tied dual path has one inherited clinical encoder, used twice; no
    # second encoder or medication target enters either stream.
    dual_model = models["dual_evidence"]
    if (
        len(dual_model.blocks) != 2
        or hasattr(dual_model, "current_encoder")
        or hasattr(dual_model, "history_encoder")
    ):
        raise RuntimeError("DualEvidence does not use one tied clinical encoder")

    for model in models.values():
        model.eval()
    with torch.no_grad():
        outputs = {
            "core": models["core"](coarse),
            "fine_history": models["fine_history"](fine),
            "dual_evidence": models["dual_evidence"](dual),
            "safe_rank": models["safe_rank"](coarse),
            "self_only": models["self_only"](coarse),
            "set_context": models["set_context"](coarse),
        }
    if any(not torch.isfinite(output).all() for output in outputs.values()):
        raise RuntimeError("target-free preflight logits are not finite")

    torch.manual_seed(SEED)
    logits_for_swap = torch.linspace(-2.0, 2.0, MEDICATIONS)
    ddi = torch.zeros((MEDICATIONS, MEDICATIONS), dtype=torch.float32)
    for left in range(0, MEDICATIONS - 1, 2):
        ddi[left, left + 1] = ddi[left + 1, left] = 1.0
    swap_a = safe_swap(logits_for_swap, ddi.tolist())
    swap_b = safe_swap(logits_for_swap, ddi.tolist())
    expected_k = int((logits_for_swap >= LOGIT_THRESHOLD).sum().item())
    if swap_a != swap_b or len(swap_a) != expected_k:
        raise RuntimeError("SafeSwap is not deterministic cardinality-preserving")

    # SelfOnly must have no cross-medication path, while SetContext should have
    # one under the same initialized block parameters.
    hidden = torch.randn((1, MEDICATIONS, 128), device=device)
    changed = hidden.clone()
    changed[:, 1] += 3.0
    with torch.no_grad():
        self_a = models["self_only"].medication_context(hidden, self_only=True)
        self_b = models["self_only"].medication_context(changed, self_only=True)
        set_a = models["set_context"].medication_context(hidden, self_only=False)
        set_b = models["set_context"].medication_context(changed, self_only=False)
    if not torch.allclose(self_a[:, 0], self_b[:, 0], atol=1e-6, rtol=1e-6):
        raise RuntimeError("SelfOnly has a cross-medication path")
    if torch.allclose(set_a[:, 0], set_b[:, 0], atol=1e-6, rtol=1e-6):
        raise RuntimeError("SetContext did not expose a cross-medication path")

    target = torch.zeros((2, MEDICATIONS), device=device)
    target[0, 0] = 1.0
    target[1, 1] = 1.0
    ddi_device = ddi.to(device)
    losses: dict[str, float] = {}
    for variant, model in models.items():
        model.train()
        model.zero_grad(set_to_none=True)
        batch = (
            dual if variant == "dual_evidence" else fine if variant == "fine_history" else coarse
        )
        logits = model(batch)
        base, _, _ = base_objective(logits, target, ddi_device)
        loss = base
        if variant == "safe_rank":
            loss = base + 0.1 * safe_rank_loss(logits, target, ddi.tolist())
        if not torch.isfinite(loss):
            raise RuntimeError(variant + " produced a non-finite loss")
        loss.backward()
        if not all(
            parameter.grad is not None and torch.isfinite(parameter.grad).all()
            for parameter in model.parameters()
        ):
            raise RuntimeError(variant + " produced a non-finite gradient")
        losses[variant] = float(loss.item())

    return {
        "status": "PASS",
        "device": str(device),
        "parameter_count": counts,
        "losses": losses,
        "target_free_interface": True,
        "fine_history_no_truncation": True,
        "dual_tied_encoder": True,
        "safe_swap_deterministic_cardinality_preserving": True,
        "self_only_no_cross_path": True,
        "set_context_cross_path": True,
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
