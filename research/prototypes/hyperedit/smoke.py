#!/usr/bin/env python3
"""Small-batch forward/backward smoke for HyperEdit-MR's PyTorch path."""

from __future__ import annotations

import numpy as np
import torch
from hyperedit import CANDIDATE_COUNT, HyperEditMR, hyperedit_loss


def main() -> None:
    torch.manual_seed(17)
    rng = np.random.default_rng(17)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    batch_size = 2
    node_features = 132
    model = HyperEditMR(node_features=node_features, hidden_dim=96, max_steps=4).to(device)
    nodes = torch.from_numpy(
        rng.normal(size=(batch_size, CANDIDATE_COUNT, node_features)).astype(np.float32)
    ).to(device)
    initial = torch.from_numpy(
        rng.integers(0, 2, size=(batch_size, CANDIDATE_COUNT)).astype(np.float32)
    ).to(device)
    actions = torch.full((batch_size, 4), 2 * CANDIDATE_COUNT, dtype=torch.long, device=device)
    actions[:, 0] = CANDIDATE_COUNT
    targets = torch.from_numpy(
        rng.integers(0, 2, size=(batch_size, CANDIDATE_COUNT)).astype(np.float32)
    ).to(device)
    ddi = torch.zeros((CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=torch.float32, device=device)
    ddi[0, 1] = ddi[1, 0] = 1.0
    co_support = torch.from_numpy(
        rng.random((batch_size, CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=np.float32)
    ).to(device)
    ehr = torch.zeros_like(ddi)
    action_logits, set_logits = model.forward_sequence(
        nodes, initial, ddi, co_support, ehr, teacher_actions=actions
    )
    loss, detail = hyperedit_loss(action_logits, actions, set_logits, targets, ddi)
    loss.backward()
    if not torch.isfinite(loss) or any(
        not torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
        if parameter.grad is not None
    ):
        raise RuntimeError("HyperEdit-MR smoke produced a non-finite loss or gradient")
    print({"device": str(device), "loss": float(loss.detach().cpu()), "detail": detail})


if __name__ == "__main__":
    main()
