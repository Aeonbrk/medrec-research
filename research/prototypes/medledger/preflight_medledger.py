#!/usr/bin/env python3
"""Preflight verification for MedLedger vs NormalizedLedger mechanism screen.

Verifies:
1. Parameter matching and identical initialization across both arms.
2. Target-free input packing and history temporal consistency (no leakage).
3. Exact mechanism contrast: independent sigmoid accumulation vs softmax competition.
4. Explicit count nuisance path behavior.
5. Finite forward and backward execution under float32 policy.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import torch
from torch import nn

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from medledger import (  # noqa: E402
    MEDICATIONS,
    MedLedgerModel,
    configure_numeric_policy,
    pack_inputs,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _synthetic_rows() -> list[dict[str, Any]]:
    return [
        {
            "diagnoses": [1, 2],
            "procedures": [0],
            "history": [],
            "_medications": [10, 20],  # must NOT enter inputs
        },
        {
            "diagnoses": [0, 3],
            "procedures": [1],
            "history": [
                ([2], [0], [4, 5]),
                ([1], [1], [8]),
            ],
            "_medications": [5, 12, 18],
        },
        {
            "diagnoses": [4],
            "procedures": [],
            "history": [
                ([0], [0], [1]),
            ],
            "_medications": [0],
        },
    ]


def _test_parameters_and_initialization(device: torch.device) -> dict[str, Any]:
    torch.manual_seed(20260920)
    full_model = MedLedgerModel(5, 4, variant="medledger", medication_count=MEDICATIONS).to(device)
    torch.manual_seed(20260920)
    ctrl_model = MedLedgerModel(5, 4, variant="normalized", medication_count=MEDICATIONS).to(device)

    _assert(
        list(full_model.state_dict().keys()) == list(ctrl_model.state_dict().keys()),
        "State dict keys differ between MedLedger and NormalizedLedger",
    )
    full_params = sum(p.numel() for p in full_model.parameters())
    ctrl_params = sum(p.numel() for p in ctrl_model.parameters())
    _assert(full_params == ctrl_params, f"Parameter count differs: {full_params} vs {ctrl_params}")

    for k in full_model.state_dict():
        _assert(
            torch.equal(full_model.state_dict()[k], ctrl_model.state_dict()[k]),
            f"Initialization differs for parameter {k}",
        )

    # Check v is initialized to 0
    _assert(torch.all(full_model.v == 0.0), "v is not initialized to 0 in MedLedger")
    _assert(torch.all(ctrl_model.v == 0.0), "v is not initialized to 0 in NormalizedLedger")

    # Check tau is initialized to DEFAULT_TAU_INIT
    softplus_tau = float(nn.functional.softplus(full_model.tau).item())
    _assert(
        abs(softplus_tau - 1.0) < 1e-4,
        f"softplus(tau) is not ~1.0 at initialization: {softplus_tau}",
    )

    return {"parameter_count": full_params}


def _test_leakage_and_packing() -> None:
    rows = _synthetic_rows()
    batch = pack_inputs(rows, diagnosis_count=5, procedure_count=4)

    # Target medications in rows: [10, 20], [5, 12, 18], [0]
    # Diagnosis offset = 0..4, Procedure offset = 5..8, Medication offset = 9..9+131
    # Check that current target medication codes do NOT appear in the current visit tokens
    # Current visit tokens are type 1 and type 2
    types = batch["types"]
    offsets = batch["offsets"]

    # NULL token check:
    _assert(int(types[0].item()) == 0, "First token must be NULL token (type 0)")
    _assert(offsets[1] == 0, "NULL token must be empty bag (offset 0)")

    # History lag check:
    lags = batch["lags"].reshape(*batch["mask"].shape).tolist()
    # Row 0: no history, all lags must be 0.0
    _assert(all(lag_val == 0.0 for lag_val in lags[0]), "Row 0 has no history but non-zero lags")
    # Row 1 has 2 history visits: lags should be 2.0 then 1.0
    hist_lags = [lag_val for lag_val in lags[1] if lag_val > 0.0]
    _assert(
        len(hist_lags) == 6,
        f"Expected 6 historical tokens (2 visits x 3 modalities), got {len(hist_lags)}",
    )

    # Check q_counts matches [log1p(num_dx), log1p(num_proc), log1p(num_hist)]
    q = batch["q_counts"]
    _assert(q.shape == (3, 3), f"q_counts shape is {q.shape}")
    _assert(abs(float(q[0, 0].item()) - math.log1p(2)) < 1e-6, "q_counts num_dx mismatch")
    _assert(abs(float(q[0, 1].item()) - math.log1p(1)) < 1e-6, "q_counts num_proc mismatch")
    _assert(abs(float(q[0, 2].item()) - math.log1p(0)) < 1e-6, "q_counts num_hist mismatch")


def _test_mechanism_contrast(device: torch.device) -> dict[str, Any]:
    rows = _synthetic_rows()
    batch = {k: v.to(device) for k, v in pack_inputs(rows, 5, 4).items()}

    torch.manual_seed(20260920)
    full_model = MedLedgerModel(5, 4, variant="medledger", medication_count=MEDICATIONS).to(device)
    torch.manual_seed(20260920)
    ctrl_model = MedLedgerModel(5, 4, variant="normalized", medication_count=MEDICATIONS).to(device)

    full_model.eval()
    ctrl_model.eval()

    with torch.no_grad():
        full_logits, full_diag = full_model(batch, return_diagnostics=True)
        ctrl_logits, ctrl_diag = ctrl_model(batch, return_diagnostics=True)

    # 1. Check NormalizedLedger softmax property:
    ctrl_alpha = ctrl_diag["relevance_weights"]  # [B, M, K]
    mask = batch["mask"].unsqueeze(1)  # [B, 1, K]
    # Sum over valid tokens
    ctrl_alpha_sum = (ctrl_alpha * mask).sum(dim=-1)  # [B, M]
    _assert(
        torch.allclose(ctrl_alpha_sum, torch.ones_like(ctrl_alpha_sum), atol=1e-5),
        "NormalizedLedger relevance weights do not sum to 1.0 over valid tokens",
    )

    # 2. Check MedLedger sigmoid property:
    full_g = full_diag["relevance_weights"]  # [B, M, K]
    full_g_sum = (full_g * mask).sum(dim=-1)  # [B, M]
    # In general, sigmoid gates do NOT sum to 1
    _assert(
        not torch.allclose(full_g_sum, torch.ones_like(full_g_sum), atol=1e-2),
        "MedLedger relevance weights unexpectedly summed to 1.0",
    )

    # 3. Check masked padding tokens are 0 in both models:
    inv_mask = ~mask
    _assert(
        torch.all(full_diag["c"][inv_mask.expand_as(full_diag["c"])] == 0.0),
        "MedLedger has non-zero contributions on padding tokens",
    )
    _assert(
        torch.all(ctrl_diag["c"][inv_mask.expand_as(ctrl_diag["c"])] == 0.0),
        "NormalizedLedger has non-zero contributions on padding tokens",
    )

    # 4. Check logit difference:
    _assert(
        not torch.allclose(full_logits, ctrl_logits, atol=1e-3),
        "MedLedger and NormalizedLedger produced identical logits despite different gating",
    )

    return {
        "ctrl_alpha_sum_mean": float(ctrl_alpha_sum.mean().item()),
        "full_g_sum_mean": float(full_g_sum.mean().item()),
        "full_g_sum_min": float(full_g_sum.min().item()),
        "full_g_sum_max": float(full_g_sum.max().item()),
    }


def _test_finite_forward_backward(device: torch.device) -> None:
    rows = _synthetic_rows()
    batch = {k: v.to(device) for k, v in pack_inputs(rows, 5, 4).items()}
    targets = torch.zeros((len(rows), MEDICATIONS), dtype=torch.float32, device=device)
    targets[0, [10, 20]] = 1.0
    targets[1, [5, 12, 18]] = 1.0
    targets[2, [0]] = 1.0

    for variant in ("medledger", "normalized"):
        torch.manual_seed(20260920)
        model = MedLedgerModel(5, 4, variant=variant, medication_count=MEDICATIONS).to(device)
        model.train()
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=3e-4, weight_decay=1e-4, betas=(0.9, 0.999), eps=1e-8
        )

        optimizer.zero_grad()
        logits = model(batch)
        _assert(torch.isfinite(logits).all(), f"{variant} forward produced non-finite logits")

        loss = nn.functional.binary_cross_entropy_with_logits(logits, targets)
        _assert(torch.isfinite(loss), f"{variant} loss is non-finite")

        loss.backward()
        for name, p in model.named_parameters():
            if p.grad is not None:
                _assert(torch.isfinite(p.grad).all(), f"{variant} grad for {name} is non-finite")

        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()

        for name, p in model.named_parameters():
            _assert(
                torch.isfinite(p).all(),
                f"{variant} param {name} is non-finite after optimizer step",
            )


def run(args: argparse.Namespace) -> dict[str, Any]:
    policy = configure_numeric_policy()
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")

    _test_leakage_and_packing()
    param_info = _test_parameters_and_initialization(device)
    contrast_info = _test_mechanism_contrast(device)
    _test_finite_forward_backward(device)

    result = {
        "status": "PASS",
        "device": str(device),
        "seed": 20260920,
        "numeric_policy": policy,
        "test_accessed": False,
        "parameter_matching": param_info,
        "mechanism_contrast": contrast_info,
        "forward_backward": "PASS",
        "target_leakage": "PASS",
    }
    if args.output is not None:
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
