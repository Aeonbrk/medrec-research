"""Survivor-discrimination models for fine-grained iterative evidence reading."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Mapping

import torch

PORTFOLIO_DIR = Path(__file__).resolve().parents[1] / "evidence-access-portfolio"
if str(PORTFOLIO_DIR) not in sys.path:
    sys.path.insert(0, str(PORTFOLIO_DIR))

from portfolio_model import (  # noqa: E402
    DIM,
    MEDICATIONS,
    PortfolioModel,
    configure_numeric_policy,
    objective,
    pack_rows,
    parameter_count,
)

SURVIVOR_VARIANTS = ("reread_visit", "reread_code", "depth_state", "depth_reread")


class SurvivorModel(PortfolioModel):
    """Exact portfolio substrate plus a final-architecture resolution control."""

    def __init__(self, diagnosis_count: int, procedure_count: int, variant: str) -> None:
        if variant not in SURVIVOR_VARIANTS:
            raise ValueError("unknown survivor variant: " + str(variant))
        super().__init__(diagnosis_count, procedure_count, "depth_reread")
        self.variant = variant

    def _reread_from_memory(
        self,
        memory: torch.Tensor,
        mask: torch.Tensor,
        batch: Mapping[str, torch.Tensor],
        drugs: torch.Tensor,
    ) -> torch.Tensor:
        first = self._read_memory(memory, mask, drugs)
        state = torch.nn.functional.layer_norm(drugs[None] + first, (DIM,))
        for hop in self.hops:
            state = hop(state, memory, mask)
        return self._single_score(state, drugs, self._persistence(batch))

    def forward(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        encoded = self._encode(batch)
        drugs = self._drugs()
        if self.variant in {"depth_state", "depth_reread"}:
            return self._forward_depth(encoded, batch, drugs)
        if self.variant == "reread_code":
            memory, mask = self._flat_evidence(encoded, batch)
            return self._reread_from_memory(memory, mask, batch, drugs)
        visits = self._shared_visit_pool(encoded, batch)
        return self._reread_from_memory(visits, batch["visit_mask"], batch, drugs)


__all__ = [
    "DIM",
    "MEDICATIONS",
    "SURVIVOR_VARIANTS",
    "SurvivorModel",
    "configure_numeric_policy",
    "objective",
    "pack_rows",
    "parameter_count",
]
