"""Medication-Evidence Mutual Binding (MEMB) family screen.

The screen preserves the stable FineCode / PredictionLocal parameter graph and
changes only how medication-evidence affinities are normalized before aggregation.

For affinity S[m,i], foundation FineCode uses softmax_i(S). MEMB forms a
bidirectional soft matching score proportional to

    softmax_i(S[m,i]) * M * softmax_m(S[m,i])

which, after renormalization over evidence i, is equivalent to

    softmax_i(2*S[m,i] - logsumexp_n S[n,i]).

The scale2 controls use softmax_i(2*S) (or LME(2*r) for PredictionLocal), so
MEMB is credited only for medication-relative specificity beyond the sharpening
that arises algebraically from multiplying the two directional probabilities.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import List, Mapping, Tuple

import torch

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

MEMB_VARIANTS = (
    "mutual_code",
    "scale2_code",
    "specificity_code",
    "mutual_local",
    "scale2_local",
    "specificity_local",
)
ANCHOR_VARIANTS = ("foundation_code_anchor", "prediction_local_anchor")
ALL_VARIANTS = MEMB_VARIANTS + ANCHOR_VARIANTS


class MEMBModel(PortfolioModel):
    """Parameter-identical FineCode/PredictionLocal model with cross-medication binding."""

    def __init__(self, diagnosis_count: int, procedure_count: int, variant: str) -> None:
        if variant not in MEMB_VARIANTS:
            raise ValueError("unknown MEMB variant: " + str(variant))
        base = "prediction_local" if variant.endswith("_local") else "resolution_code"
        super().__init__(diagnosis_count, procedure_count, base)
        self.memb_variant = variant

    def _code_objects(
        self,
        memory: torch.Tensor,
        mask: torch.Tensor,
        drugs: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return raw affinity, transformed affinity, and value vectors."""
        normalized = self.read_norm(memory)
        keys = self.read_key(normalized)
        values = self.read_value(normalized)
        q = self.read_query(drugs)
        raw = torch.einsum("md,bnd->bmn", q, keys) / math.sqrt(DIM)

        if self.memb_variant == "scale2_code":
            transformed = 2.0 * raw
        elif self.memb_variant == "specificity_code":
            commonness = torch.logsumexp(raw, dim=1, keepdim=True)
            transformed = raw - commonness
        elif self.memb_variant == "mutual_code":
            commonness = torch.logsumexp(raw, dim=1, keepdim=True)
            transformed = 2.0 * raw - commonness + math.log(float(MEDICATIONS))
        else:  # pragma: no cover - constructor/forward guard this
            raise RuntimeError("code objects requested for a local MEMB variant")

        transformed = transformed.masked_fill(~mask[:, None, :], float("-inf"))
        return raw, transformed, values

    def _read_competitive_code(
        self,
        memory: torch.Tensor,
        mask: torch.Tensor,
        drugs: torch.Tensor,
    ) -> torch.Tensor:
        _raw, transformed, values = self._code_objects(memory, mask, drugs)
        weights = torch.softmax(transformed, dim=-1)
        return torch.einsum("bmn,bnd->bmd", weights, values)

    def _local_raw(
        self,
        memory: torch.Tensor,
        drugs: torch.Tensor,
    ) -> torch.Tensor:
        normalized = self.read_norm(memory)
        keys = self.local_k(normalized)
        chunks: List[torch.Tensor] = []
        for start in range(0, MEDICATIONS, CHUNK):
            selected = drugs[start : start + CHUNK]
            q = self.local_q(selected)
            interaction = q[None, :, None, :] * keys[:, None, :, :]
            hidden = self.local_hidden(interaction)
            chunks.append(self.local_out(hidden).squeeze(-1))
        return torch.cat(chunks, dim=1)

    def _forward_competitive_local(
        self,
        encoded: torch.Tensor,
        batch: Mapping[str, torch.Tensor],
        drugs: torch.Tensor,
    ) -> torch.Tensor:
        memory, mask = self._flat_evidence(encoded, batch)
        persistence = self._persistence(batch)
        raw = self._local_raw(memory, drugs)
        if self.memb_variant == "scale2_local":
            transformed = 2.0 * raw
        elif self.memb_variant == "specificity_local":
            commonness = torch.logsumexp(raw, dim=1, keepdim=True)
            transformed = raw - commonness + math.log(float(MEDICATIONS))
        elif self.memb_variant == "mutual_local":
            commonness = torch.logsumexp(raw, dim=1, keepdim=True)
            transformed = 2.0 * raw - commonness + math.log(float(MEDICATIONS))
        else:  # pragma: no cover
            raise RuntimeError("local forward requested for a code MEMB variant")

        transformed = transformed.masked_fill(~mask[:, None, :], float("-inf"))
        valid_count = mask.sum(dim=-1).clamp_min(1).to(raw.dtype)
        local_score = torch.logsumexp(transformed, dim=-1) - valid_count.log()[:, None]

        bias_features = torch.cat(
            (drugs[None].expand(memory.shape[0], -1, -1), persistence), dim=-1
        )
        base = self.local_bias(bias_features).squeeze(-1) + self.drug_bias
        return local_score + base

    def debug_code_objects(
        self, batch: Mapping[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        encoded = self._encode(batch)
        memory, mask = self._flat_evidence(encoded, batch)
        raw, transformed, _values = self._code_objects(memory, mask, self._drugs())
        return raw, transformed, mask

    def debug_local_objects(
        self, batch: Mapping[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        encoded = self._encode(batch)
        memory, mask = self._flat_evidence(encoded, batch)
        raw = self._local_raw(memory, self._drugs())
        if self.memb_variant == "scale2_local":
            transformed = 2.0 * raw
        elif self.memb_variant == "specificity_local":
            transformed = (
                raw
                - torch.logsumexp(raw, dim=1, keepdim=True)
                + math.log(float(MEDICATIONS))
            )
        elif self.memb_variant == "mutual_local":
            transformed = (
                2.0 * raw
                - torch.logsumexp(raw, dim=1, keepdim=True)
                + math.log(float(MEDICATIONS))
            )
        else:  # pragma: no cover
            raise RuntimeError("local debug requested for a code MEMB variant")
        return raw, transformed, mask

    def forward(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        encoded = self._encode(batch)
        drugs = self._drugs()
        if self.memb_variant.endswith("_local"):
            return self._forward_competitive_local(encoded, batch, drugs)

        memory, mask = self._flat_evidence(encoded, batch)
        context = self._read_competitive_code(memory, mask, drugs)
        return self._single_score(context, drugs, self._persistence(batch))


__all__ = [
    "ALL_VARIANTS",
    "ANCHOR_VARIANTS",
    "MEMB_VARIANTS",
    "MEMBModel",
    "configure_numeric_policy",
    "objective",
    "pack_rows",
    "parameter_count",
]
