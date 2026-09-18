#!/usr/bin/env python3
"""Decision-relevant synthetic preflight for the ECRC screen."""

from __future__ import annotations

import itertools
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import torch

try:
    from ecrc import (
        ECRC,
        MEDICATIONS,
        VARIANTS,
        configure_numeric_policy,
        fixed_cardinality_log_normalizer,
        joint_objective,
        pack_inputs,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ecrc import (
        ECRC,
        MEDICATIONS,
        VARIANTS,
        configure_numeric_policy,
        fixed_cardinality_log_normalizer,
        joint_objective,
        pack_inputs,
    )


SEED = 20260923


def _seed() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
    configure_numeric_policy()


def _synthetic_rows() -> list[dict[str, object]]:
    return [
        {
            "diagnoses": [0, 2],
            "procedures": [0],
            "history": [([1], [1], [0, 3]), ([0, 4], [], [2])],
        },
        {
            "diagnoses": [1],
            "procedures": [1, 2],
            "history": [],
        },
    ]


def _targets(device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    target = torch.zeros((2, MEDICATIONS), dtype=torch.float32, device=device)
    target[0, [0, 3, 7]] = 1.0
    target[1, [2, 5]] = 1.0
    return target, target.sum(dim=-1).to(torch.long)


def _state_equal(left: ECRC, right: ECRC) -> bool:
    if left.state_dict().keys() != right.state_dict().keys():
        return False
    return all(
        torch.equal(left.state_dict()[key], right.state_dict()[key]) for key in left.state_dict()
    )


def _dp_fixture() -> float:
    logits = torch.tensor(
        [
            [0.4, -0.2, 0.7, 0.1] + [-30.0] * (MEDICATIONS - 4),
            [-0.1, 0.5, 0.2, -0.3] + [-30.0] * (MEDICATIONS - 4),
        ],
        dtype=torch.float64,
    )
    k = torch.tensor([2, 3], dtype=torch.long)
    observed = fixed_cardinality_log_normalizer(logits, k)
    expected = []
    for row, count in zip(logits.tolist(), k.tolist(), strict=True):
        terms = []
        for combo in itertools.combinations(range(MEDICATIONS), int(count)):
            terms.append(sum(row[index] for index in combo))
        peak = max(terms)
        expected.append(peak + math.log(sum(math.exp(value - peak) for value in terms)))
    expected_tensor = torch.tensor(expected, dtype=torch.float64)
    return float(torch.max(torch.abs(observed - expected_tensor)).item())


def run(device: torch.device) -> dict[str, object]:
    _seed()
    rows = _synthetic_rows()
    batch = {key: value.to(device) for key, value in pack_inputs(rows, 8, 4).items()}
    target, target_k = _targets(device)

    models: dict[str, ECRC] = {}
    for variant in VARIANTS:
        _seed()
        models[variant] = ECRC(8, 4, k_max=6, variant=variant).to(device)

    if not _state_equal(models["kind_bce"], models["kcond_bce"]):
        raise RuntimeError("BCE pair does not start from identical tensors")
    if not _state_equal(models["kind_exact"], models["kcond_exact"]):
        raise RuntimeError("Exact pair does not start from identical tensors")

    parameter_counts = {
        variant: sum(parameter.numel() for parameter in model.parameters())
        for variant, model in models.items()
    }
    if len(set(parameter_counts.values())) != 1:
        raise RuntimeError("ECRC variants are not parameter matched")

    # With zero cardinality embeddings, paired medication utilities must match exactly.
    models["kind_bce"].eval()
    models["kcond_bce"].eval()
    with torch.no_grad():
        bce_ind = models["kind_bce"](batch, k=target_k)["medication_logits"]
        bce_cond = models["kcond_bce"](batch, k=target_k)["medication_logits"]
    if not torch.equal(bce_ind, bce_cond):
        raise RuntimeError("paired zero-initialized medication logits are not identical")
    models["kind_bce"].train()
    models["kcond_bce"].train()

    # Force opposite K rows while preserving zero mean. KInd must remain K-invariant;
    # KCond must respond to cardinality identity.
    for name in ("kind_bce", "kcond_bce"):
        model = models[name]
        with torch.no_grad():
            model.k_embedding.weight.zero_()
            model.k_embedding.weight[2].fill_(0.25)
            model.k_embedding.weight[3].fill_(-0.25)
        features, base_logits, _ = model._features(batch)
        k2 = torch.tensor([2, 2], device=device)
        k3 = torch.tensor([3, 3], device=device)
        out2 = model.logits_for_k(features, base_logits, k2)
        out3 = model.logits_for_k(features, base_logits, k3)
        changed = float(torch.max(torch.abs(out2 - out3)).item())
        if name.startswith("kind_") and changed != 0.0:
            raise RuntimeError("KInd medication ranking depends on K")
        if name.startswith("kcond_") and changed <= 1e-7:
            raise RuntimeError("KCond medication path is insensitive to K")
        with torch.no_grad():
            model.k_embedding.weight.zero_()

    losses: dict[str, float] = {}
    for variant, model in models.items():
        model.zero_grad(set_to_none=True)
        output = model(batch, k=target_k)
        loss, _ = joint_objective(output, target, target_k, exact=model.exact)
        if not torch.isfinite(loss):
            raise RuntimeError("non-finite synthetic loss")
        loss.backward()
        if not all(
            parameter.grad is not None and torch.isfinite(parameter.grad).all()
            for parameter in model.parameters()
        ):
            raise RuntimeError("non-finite ECRC gradient")
        losses[variant] = float(loss.item())

    dp_error = _dp_fixture()
    if dp_error > 1e-9:
        raise RuntimeError("fixed-cardinality dynamic program disagrees with brute force")

    # Inference does not accept a target tensor. Predicted K comes only from size logits.
    with torch.no_grad():
        models["kcond_exact"].eval()
        primary = models["kcond_exact"](batch)
        if not torch.equal(primary["selected_k"], primary["predicted_k"]):
            raise RuntimeError("native inference is not using predicted cardinality")

    return {
        "status": "PASS",
        "device": str(device),
        "seed": SEED,
        "parameter_counts": parameter_counts,
        "synthetic_losses": losses,
        "fixed_cardinality_dp_max_abs_error": dp_error,
        "checks": [
            "paired initialization equality",
            "exact parameter-count matching",
            "KInd cardinality invariance",
            "KCond cardinality sensitivity",
            "finite BCE and exact forward/backward",
            "fixed-cardinality DP brute-force equivalence",
            "native inference uses predicted K only",
        ],
    }


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the frozen preflight")
    print(json.dumps(run(torch.device("cuda")), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
