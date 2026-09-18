
"""Candidate-conditioned relational evidence model for the bounded mechanism screen."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Mapping, Tuple

import torch
from torch import nn

HERE = Path(__file__).resolve().parent
PORTFOLIO_DIR = HERE.parents[0] / "evidence-access-portfolio"
if str(PORTFOLIO_DIR) not in sys.path:
    sys.path.insert(0, str(PORTFOLIO_DIR))

from portfolio_model import (  # noqa: E402
    CHUNK,
    DIM,
    MEDICATIONS,
    PortfolioModel,
    configure_numeric_policy,
    objective,
    pack_rows,
    parameter_count,
)

RELATION_DIM = 64
RELATIONAL_VARIANTS = ("unary_code", "relational_code")


class RelationalEvidenceModel(PortfolioModel):
    """Fine-code medication-specific reads with additive or multiplicative relation slots."""

    def __init__(self, diagnosis_count: int, procedure_count: int, variant: str) -> None:
        if variant not in RELATIONAL_VARIANTS:
            raise ValueError("unknown relational evidence variant: " + str(variant))
        super().__init__(diagnosis_count, procedure_count, "resolution_code")
        self.variant = variant

        self.rel_d = nn.Linear(DIM, RELATION_DIM, bias=False)
        self.rel_p = nn.Linear(DIM, RELATION_DIM, bias=False)
        self.rel_h = nn.Linear(DIM, RELATION_DIM, bias=False)
        self.rel_d_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)
        self.rel_p_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)
        self.rel_h_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)

        feature_dim = 5 * DIM + 3 * RELATION_DIM
        self.relational_head = nn.Sequential(
            nn.Linear(feature_dim, DIM),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(DIM, 1),
        )
        self._reset_relational_parameters()

    def _reset_relational_parameters(self) -> None:
        for module in (
            self.rel_d,
            self.rel_p,
            self.rel_h,
            self.relational_head[0],
            self.relational_head[3],
        ):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)

    def _safe_read(
        self,
        memory: torch.Tensor,
        mask: torch.Tensor,
        drugs: torch.Tensor,
    ) -> torch.Tensor:
        """Medication-specific normalized read that returns zero for an empty field."""
        normalized = self.read_norm(memory)
        keys = self.read_key(normalized)
        values = self.read_value(normalized)
        outputs = []
        float_mask = mask[:, None, :].to(memory.dtype)
        for start in range(0, MEDICATIONS, CHUNK):
            selected = drugs[start : start + CHUNK]
            query = self.read_query(selected)
            scores = torch.einsum("md,bnd->bmn", query, keys) / math.sqrt(DIM)
            scores = scores.masked_fill(~mask[:, None, :], -1e9)
            weights = torch.softmax(scores, dim=-1) * float_mask
            weights = weights / weights.sum(dim=-1, keepdim=True).clamp_min(1e-12)
            outputs.append(torch.einsum("bmn,bnd->bmd", weights, values))
        return torch.cat(outputs, dim=1)

    def _field_reads(
        self,
        encoded: torch.Tensor,
        batch: Mapping[str, torch.Tensor],
        drugs: torch.Tensor,
    ) -> Tuple[
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
    ]:
        b, v, k, d = encoded.shape
        memory = encoded.reshape(b, v * k, d)
        token_types = batch["types"].reshape(b, v * k)
        base_mask = (
            batch["token_mask"] & batch["visit_mask"][:, :, None]
        ).reshape(b, v * k)

        diagnosis_mask = base_mask & (token_types == 1)
        procedure_mask = base_mask & (token_types == 2)
        history_med_mask = base_mask & (token_types == 3)

        diagnosis = self._safe_read(memory, diagnosis_mask, drugs)
        procedure = self._safe_read(memory, procedure_mask, drugs)
        history_med = self._safe_read(memory, history_med_mask, drugs)

        return (
            diagnosis,
            procedure,
            history_med,
            diagnosis_mask.any(dim=-1),
            procedure_mask.any(dim=-1),
            history_med_mask.any(dim=-1),
        )

    def _relation_slots(
        self,
        diagnosis: torch.Tensor,
        procedure: torch.Tensor,
        history_med: torch.Tensor,
        diagnosis_present: torch.Tensor,
        procedure_present: torch.Tensor,
        history_med_present: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        d = self.rel_d_norm(self.rel_d(diagnosis))
        p = self.rel_p_norm(self.rel_p(procedure))
        h = self.rel_h_norm(self.rel_h(history_med))

        dp_mask = (diagnosis_present & procedure_present)[:, None, None].to(d.dtype)
        dh_mask = (diagnosis_present & history_med_present)[:, None, None].to(d.dtype)
        ph_mask = (procedure_present & history_med_present)[:, None, None].to(d.dtype)

        if self.variant == "relational_code":
            dp = (d * p) * dp_mask
            dh = (d * h) * dh_mask
            ph = (p * h) * ph_mask
        else:
            scale = 1.0 / math.sqrt(2.0)
            dp = ((d + p) * scale) * dp_mask
            dh = ((d + h) * scale) * dh_mask
            ph = ((p + h) * scale) * ph_mask
        return dp, dh, ph

    def forward(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        encoded = self._encode(batch)
        drugs = self._drugs()
        (
            diagnosis,
            procedure,
            history_med,
            diagnosis_present,
            procedure_present,
            history_med_present,
        ) = self._field_reads(encoded, batch, drugs)

        dp, dh, ph = self._relation_slots(
            diagnosis,
            procedure,
            history_med,
            diagnosis_present,
            procedure_present,
            history_med_present,
        )

        batch_size = encoded.shape[0]
        drug = drugs[None].expand(batch_size, -1, -1)
        persistence = self._persistence(batch)
        features = torch.cat(
            (
                diagnosis,
                procedure,
                history_med,
                dp,
                dh,
                ph,
                drug,
                persistence,
            ),
            dim=-1,
        )
        return self.relational_head(features).squeeze(-1) + self.drug_bias


__all__ = [
    "DIM",
    "MEDICATIONS",
    "RELATION_DIM",
    "RELATIONAL_VARIANTS",
    "RelationalEvidenceModel",
    "configure_numeric_policy",
    "objective",
    "pack_rows",
    "parameter_count",
]
