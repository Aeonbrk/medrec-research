#!/usr/bin/env python3
"""Small CUDA forward/backward smoke for RxDiffSet-v0."""

from __future__ import annotations

import numpy as np
import torch
from rxdiffset import (
    CANDIDATE_COUNT,
    RxDiffSetModel,
    build_relation_features,
    rx_diffset_loss,
)


def main() -> None:
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for the RxDiffSet smoke")
    torch.manual_seed(20260914)
    device = torch.device("cuda")
    relation = build_relation_features(
        np.zeros((CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=np.float32),
        np.zeros((CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=np.float32),
    )
    model = RxDiffSetModel(
        embedding_dim=64,
        relation_features=relation,
        max_cardinality=12,
        hidden_dim=112,
        attention_heads=4,
        blocks=2,
        noise_levels=8,
    ).to(device)
    embeddings = torch.randn(2, CANDIDATE_COUNT, 64, device=device)
    scores = torch.randn(2, CANDIDATE_COUNT, device=device)
    noisy = torch.randint(0, 2, (2, CANDIDATE_COUNT), device=device).float()
    levels = torch.tensor([7, 4], device=device)
    targets = torch.randint(0, 2, (2, CANDIDATE_COUNT), device=device).float()
    counts = targets.sum(dim=1).long().clamp(max=12)
    output = model(embeddings, scores, noisy, levels)
    loss, detail = rx_diffset_loss(output, targets, counts)
    loss.backward()
    if not torch.isfinite(loss) or not all(
        parameter.grad is None or torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    ):
        raise RuntimeError("RxDiffSet CUDA smoke produced a non-finite loss or gradient")
    print({"device": str(device), "loss": float(loss.detach().cpu()), "detail": detail})


if __name__ == "__main__":
    main()
