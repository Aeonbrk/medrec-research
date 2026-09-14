#!/usr/bin/env python3
"""Small CUDA/CPU finite forward-backward smoke for the HypeInteract modules."""

from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hypeinteract import (
    CANDIDATE_COUNT,
    HypeMedScorer,
    HypergraphEncoder,
    PatientConditionedInteraction,
    build_domain_hypergraph,
)


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    records = (
        (((0, 1), (0,), (0, 1)), ((1,), (1,), (1,))),
        (((2,), (2,), (2, 3)),),
    )
    domain = build_domain_hypergraph(records, (0, 1), domain="diag", num_nodes=4)
    encoder = HypergraphEncoder(4, domain.incidence.shape[1], dim=8, heads=2).to(device)
    nodes, _ = encoder(domain.incidence.to(device))
    scorer = HypeMedScorer(torch.randn(CANDIDATE_COUNT, 8), dim=8).to(device)
    context = torch.randn(3, 8, device=device)
    history = torch.randn(3, 8, device=device)
    similar = torch.randn(3, 8, device=device)
    score = scorer(context, history, similar)
    interaction = PatientConditionedInteraction(
        torch.randn(CANDIDATE_COUNT, 8), dim=8, hidden_dim=12
    ).to(device)
    relation = torch.eye(CANDIDATE_COUNT, device=device)
    output = interaction(context, score.detach(), torch.zeros_like(score), relation, relation)
    loss = nodes.pow(2).mean() + output.pow(2).mean()
    loss.backward()
    if not all(
        torch.isfinite(parameter).all()
        for parameter in list(encoder.parameters())
        + list(scorer.parameters())
        + list(interaction.parameters())
    ):
        raise RuntimeError("non-finite gradient smoke output")
    print("hypeinteract CUDA/CPU smoke: PASS", device)


if __name__ == "__main__":
    main()
