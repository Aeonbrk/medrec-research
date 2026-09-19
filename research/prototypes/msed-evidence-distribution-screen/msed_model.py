"""Medication-Specific Evidence Distribution modeling over longitudinal FineCode evidence."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import List, Mapping, Tuple

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

SPECTRUM_FREQUENCIES = 8
MSED_VARIANTS = (
    "msed_ecf_global",
    "point_lme_global",
    "point_mean_global",
    "point_max_global",
    "msed_ecf_only",
    "point_lme_only",
)
ANCHOR_VARIANTS = ("prediction_local_anchor", "foundation_code_anchor")
ALL_VARIANTS = MSED_VARIANTS + ANCHOR_VARIANTS


class MSEDModel(PortfolioModel):
    """Represent each medication's local FineCode support as an empirical distribution.

    All MSED variants share one parameter graph. The scientific difference is the
    statistic supplied to the fixed-size local distribution feature:

    - msed_ecf_*: [LME(r), E_i phi(r_i)]
    - point_lme_*: [LME(r), phi(LME(r))]
    - point_mean_global: [mean(r), phi(mean(r))]
    - point_max_global: [max(r), phi(max(r))]

    where phi is a fixed-frequency sine/cosine characteristic feature map with one
    shared learnable score scale. The stable global FineCode context is preserved in
    *_global variants and zeroed (without deleting parameters) in *_only variants.
    """

    def __init__(self, diagnosis_count: int, procedure_count: int, variant: str) -> None:
        if variant not in MSED_VARIANTS:
            raise ValueError("unknown MSED variant: " + str(variant))
        super().__init__(diagnosis_count, procedure_count, "resolution_code")
        self.msed_variant = variant

        # Fixed positive frequencies. They are not a hyperparameter sweep; scale is
        # adapted by one shared scalar so matched variants retain identical capacity.
        frequencies = torch.exp(
            torch.linspace(math.log(0.25), math.log(4.0), SPECTRUM_FREQUENCIES)
        )
        self.register_buffer("distribution_frequencies", frequencies)
        self.log_score_scale = nn.Parameter(torch.zeros(()))
        spectrum_dim = 2 * SPECTRUM_FREQUENCIES
        self.distribution_proj = nn.Sequential(
            nn.Linear(1 + spectrum_dim, DIM),
            nn.GELU(),
            nn.Dropout(0.1),
        )
        self.msed_head = nn.Sequential(
            nn.Linear(4 * DIM, DIM),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(DIM, 1),
        )
        self._reset_msed_parameters()

    def _reset_msed_parameters(self) -> None:
        for module in (self.distribution_proj[0], self.msed_head[0], self.msed_head[3]):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        with torch.no_grad():
            self.log_score_scale.zero_()

    def _local_score_chunks(
        self,
        memory: torch.Tensor,
        mask: torch.Tensor,
        drugs: torch.Tensor,
    ) -> List[torch.Tensor]:
        """Exact medication-token scalar potentials used by PredictionLocal."""
        normalized = self.read_norm(memory)
        keys = self.local_k(normalized)
        chunks: List[torch.Tensor] = []
        for start in range(0, MEDICATIONS, CHUNK):
            selected = drugs[start : start + CHUNK]
            q = self.local_q(selected)
            interaction = q[None, :, None, :] * keys[:, None, :, :]
            hidden = self.local_hidden(interaction)
            local = self.local_out(hidden).squeeze(-1)
            chunks.append(local)
        return chunks

    @staticmethod
    def _masked_lme(scores: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        masked = scores.masked_fill(~mask[:, None, :], float("-inf"))
        valid_count = mask.sum(dim=-1).clamp_min(1).to(scores.dtype)
        return torch.logsumexp(masked, dim=-1) - valid_count.log()[:, None]

    @staticmethod
    def _masked_mean(scores: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        weights = mask[:, None, :].to(scores.dtype)
        count = mask.sum(dim=-1).clamp_min(1).to(scores.dtype)
        return (scores * weights).sum(dim=-1) / count[:, None]

    @staticmethod
    def _masked_max(scores: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        return scores.masked_fill(~mask[:, None, :], float("-inf")).max(dim=-1).values

    def _point_spectrum(self, point: torch.Tensor) -> torch.Tensor:
        scale = self.log_score_scale.clamp(-3.0, 3.0).exp()
        angles = point[..., None] / scale * self.distribution_frequencies
        return torch.cat((angles.cos(), angles.sin()), dim=-1)

    def _distribution_spectrum(
        self,
        scores: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        scale = self.log_score_scale.clamp(-3.0, 3.0).exp()
        angles = scores[..., None] / scale * self.distribution_frequencies
        features = torch.cat((angles.cos(), angles.sin()), dim=-1)
        weights = mask[:, None, :, None].to(features.dtype)
        count = mask.sum(dim=-1).clamp_min(1).to(features.dtype)
        return (features * weights).sum(dim=2) / count[:, None, None]

    def _local_distribution_features(
        self,
        memory: torch.Tensor,
        mask: torch.Tensor,
        drugs: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return [B,M,D] local vector, raw LME, and raw local-score tensor.

        Raw scores are concatenated only for preflight/debug attribution. Training
        computation still uses medication chunks internally.
        """
        vectors: List[torch.Tensor] = []
        lmes: List[torch.Tensor] = []
        raw_chunks = self._local_score_chunks(memory, mask, drugs)

        for scores in raw_chunks:
            lme = self._masked_lme(scores, mask)
            if self.msed_variant.startswith("msed_ecf_"):
                statistic = lme
                spectrum = self._distribution_spectrum(scores, mask)
            elif self.msed_variant.startswith("point_lme_"):
                statistic = lme
                spectrum = self._point_spectrum(lme)
            elif self.msed_variant == "point_mean_global":
                statistic = self._masked_mean(scores, mask)
                spectrum = self._point_spectrum(statistic)
            elif self.msed_variant == "point_max_global":
                statistic = self._masked_max(scores, mask)
                spectrum = self._point_spectrum(statistic)
            else:  # pragma: no cover - constructor guards this
                raise RuntimeError("unsupported MSED variant")

            local_feature = torch.cat((statistic[..., None], spectrum), dim=-1)
            vectors.append(self.distribution_proj(local_feature))
            lmes.append(lme)

        return (
            torch.cat(vectors, dim=1),
            torch.cat(lmes, dim=1),
            torch.cat(raw_chunks, dim=1),
        )

    def debug_local_objects(
        self,
        batch: Mapping[str, torch.Tensor],
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Expose global context, raw local scores, raw LME, and local vector for preflight."""
        encoded = self._encode(batch)
        memory, mask = self._flat_evidence(encoded, batch)
        drugs = self._drugs()
        global_context = self._read_memory(memory, mask, drugs)
        local_vector, lme, raw = self._local_distribution_features(memory, mask, drugs)
        return global_context, raw, lme, local_vector

    def forward(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        encoded = self._encode(batch)
        memory, mask = self._flat_evidence(encoded, batch)
        drugs = self._drugs()
        global_context = self._read_memory(memory, mask, drugs)
        local_vector, _lme, _raw = self._local_distribution_features(memory, mask, drugs)
        persistence = self._persistence(batch)

        if self.msed_variant.endswith("_only"):
            global_context = torch.zeros_like(global_context)

        b = global_context.shape[0]
        drug = drugs[None].expand(b, -1, -1)
        features = torch.cat((global_context, local_vector, drug, persistence), dim=-1)
        return self.msed_head(features).squeeze(-1) + self.drug_bias


__all__ = [
    "ALL_VARIANTS",
    "ANCHOR_VARIANTS",
    "MSED_VARIANTS",
    "MSEDModel",
    "configure_numeric_policy",
    "objective",
    "pack_rows",
    "parameter_count",
]
