#!/usr/bin/env python3
"""Small-batch CUDA forward/backward smoke for TheraCompose v0."""

from __future__ import annotations

import numpy as np
import torch
from theracompose import (
    CANDIDATE_COUNT,
    TheraComposeModel,
    hard_negative_masks,
    theracompose_loss,
)


def main() -> None:
    torch.manual_seed(31)
    rng = np.random.default_rng(31)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    batch_size = 2
    event_features = 2 * 8 + CANDIDATE_COUNT + 2
    events = rng.normal(size=(batch_size, 5, event_features)).astype(np.float32)
    events[:, :-1, -2] = -1.0
    events[:, -1, -2] = 1.0
    sequence_mask = np.ones((batch_size, 5), dtype=np.bool_)
    base_scores = rng.normal(size=(batch_size, CANDIDATE_COUNT)).astype(np.float32)
    medication_embeddings = rng.normal(size=(CANDIDATE_COUNT, 12)).astype(np.float32)
    ehr = np.zeros((CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=np.float32)
    ehr[0, 2] = ehr[2, 0] = 1.0
    ddi = np.zeros_like(ehr)
    ddi[1, 3] = ddi[3, 1] = 1.0
    target_sets = (frozenset({0, 1, 4}), frozenset({2, 3}))
    targets = np.zeros((batch_size, CANDIDATE_COUNT), dtype=np.float32)
    for row, target in enumerate(target_sets):
        targets[row, list(target)] = 1.0
    negatives = hard_negative_masks(target_sets, base_scores, ddi)
    model = TheraComposeModel(
        event_features=event_features,
        medication_embeddings=medication_embeddings,
        ehr_adjacency=ehr,
        ddi_adjacency=ddi,
        hidden_dim=32,
        max_cardinality=8,
    ).to(device)
    output = model(
        torch.from_numpy(events).to(device=device),
        torch.from_numpy(sequence_mask).to(device=device),
        torch.from_numpy(base_scores).to(device=device),
    )
    loss, detail = theracompose_loss(
        model,
        output,
        torch.from_numpy(targets).to(device=device),
        torch.from_numpy(negatives).to(device=device),
    )
    loss.backward()
    if output.slots.shape[1] != 4:
        raise RuntimeError("TheraCompose smoke did not produce exactly four intent slots")
    if not torch.isfinite(loss) or any(
        not torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
        if parameter.grad is not None
    ):
        raise RuntimeError("TheraCompose smoke produced a non-finite loss or gradient")
    print({"device": str(device), "loss": float(loss.detach().cpu()), "detail": detail})


if __name__ == "__main__":
    main()
