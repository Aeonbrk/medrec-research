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
    rng = np.random.default_rng(20260914)
    ehr = rng.random((CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=np.float32)
    ddi = (rng.random((CANDIDATE_COUNT, CANDIDATE_COUNT)) > 0.98).astype(np.float32)
    relation = build_relation_features(
        ehr,
        ddi,
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
    permutation = torch.arange(CANDIDATE_COUNT - 1, -1, -1, device=device)
    permuted_model = RxDiffSetModel(
        embedding_dim=64,
        relation_features=relation[permutation.cpu().numpy()][:, permutation.cpu().numpy()],
        max_cardinality=12,
        hidden_dim=112,
        attention_heads=4,
        blocks=2,
        noise_levels=8,
    ).to(device)
    permuted_model.load_state_dict(model.state_dict())
    with torch.no_grad():
        permuted_model.relation_features.copy_(
            torch.as_tensor(
                relation[permutation.cpu().numpy()][:, permutation.cpu().numpy()],
                dtype=torch.float32,
                device=device,
            )
        )
    with torch.no_grad():
        permuted_output = permuted_model(
            embeddings[:, permutation], scores[:, permutation], noisy[:, permutation], levels
        )
    if not torch.allclose(
        permuted_output.clean_logits, output.clean_logits[:, permutation], atol=1e-2, rtol=1e-4
    ) or not torch.allclose(
        permuted_output.cardinality_logits, output.cardinality_logits, atol=1e-2, rtol=1e-4
    ):
        raise RuntimeError("RxDiffSet relation/token permutation equivariance check failed")
    print(
        {
            "device": str(device),
            "loss": float(loss.detach().cpu()),
            "detail": detail,
            "permutation_equivariant": True,
        }
    )


if __name__ == "__main__":
    main()
