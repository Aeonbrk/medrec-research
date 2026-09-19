"""Medication-conditioned heterogeneous evidence factorization on FineCode evidence."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import List, Mapping, Optional, Tuple

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

MHEF_VARIANTS = (
    "mhef_independent_add",
    "coupled_budget_add",
    "wide_global_add",
    "mhef_independent_concat",
    "coupled_budget_concat",
    "private_only_add",
    "hash_partition_a_add",
    "hash_partition_b_add",
)

_HASH_SALTS = {
    "hash_partition_a_add": 104729,
    "hash_partition_b_add": 130363,
}


def _masked_softmax(
    scores: torch.Tensor,
    mask: torch.Tensor,
    dim: int = -1,
) -> torch.Tensor:
    """Masked softmax that returns all zeros when a whole row is masked."""
    masked = scores.masked_fill(~mask, -1e9)
    weights = torch.softmax(masked, dim=dim) * mask.to(scores.dtype)
    return weights / weights.sum(dim=dim, keepdim=True).clamp_min(1e-12)


class MHEFModel(PortfolioModel):
    """FineCode with factorized heterogeneous evidence normalization.

    All variants share exactly one parameter graph. Scientific comparisons change
    only normalization/fusion/partition behavior in ``forward``.
    """

    def __init__(self, diagnosis_count: int, procedure_count: int, variant: str) -> None:
        if variant not in MHEF_VARIANTS:
            raise ValueError("unknown MHEF variant: " + str(variant))
        super().__init__(diagnosis_count, procedure_count, "resolution_code")
        self.variant = variant

        self.channel_embedding = nn.Embedding(4, DIM)
        self.evidence_head = nn.Sequential(
            nn.Linear(3 * DIM, DIM),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(DIM, 1),
        )
        self.persistence_head = nn.Sequential(
            nn.Linear(2 * DIM, DIM),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(DIM, 1),
        )
        self.concat_head = nn.Sequential(
            nn.Linear(6 * DIM, DIM),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(DIM, 1),
        )
        self._reset_mhef_parameters()

    def _reset_mhef_parameters(self) -> None:
        nn.init.normal_(self.channel_embedding.weight, mean=0.0, std=0.02)
        for module in (
            self.evidence_head[0],
            self.evidence_head[3],
            self.persistence_head[0],
            self.persistence_head[3],
            self.concat_head[0],
            self.concat_head[3],
        ):
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)

    @staticmethod
    def _flat_masks(
        batch: Mapping[str, torch.Tensor],
    ) -> Tuple[torch.Tensor, torch.Tensor, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
        b, v, k = batch["types"].shape
        valid = (
            batch["token_mask"] & batch["visit_mask"][:, :, None]
        ).reshape(b, v * k)
        types = batch["types"].reshape(b, v * k)
        fields = (
            valid & (types == 1),
            valid & (types == 2),
            valid & (types == 3),
        )
        return valid, types, fields

    @staticmethod
    def _hash_partition_masks(
        batch: Mapping[str, torch.Tensor],
        semantic_masks: Tuple[torch.Tensor, torch.Tensor, torch.Tensor],
        salt: int,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Reassign typed evidence while preserving per-example D/P/H bucket sizes."""
        b, v, k = batch["codes"].shape
        codes = batch["codes"].reshape(b, v * k)
        typed_union = semantic_masks[0] | semantic_masks[1] | semantic_masks[2]
        out = [torch.zeros_like(typed_union) for _ in range(3)]

        for row in range(b):
            positions = torch.nonzero(typed_union[row], as_tuple=False).flatten()
            if positions.numel() == 0:
                continue
            counts = [int(mask[row].sum().item()) for mask in semantic_masks]
            code_values = codes[row, positions].to(torch.int64)
            pos_values = positions.to(torch.int64)
            hash_values = (
                (code_values + 1) * 1103515245
                + (pos_values + 1) * 12345
                + int(salt)
            ) % 2147483647
            ordered = positions[torch.argsort(hash_values)]
            left = 0
            for field, count in enumerate(counts):
                right = left + count
                if count:
                    out[field][row, ordered[left:right]] = True
                left = right
        return out[0], out[1], out[2]

    def debug_view_masks(
        self,
        batch: Mapping[str, torch.Tensor],
        variant: Optional[str] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Expose the private partition only for decision-relevant preflight checks."""
        _, _, semantic = self._flat_masks(batch)
        chosen = self.variant if variant is None else variant
        if chosen in _HASH_SALTS:
            return self._hash_partition_masks(batch, semantic, _HASH_SALTS[chosen])
        return semantic

    def _contexts(
        self,
        encoded: torch.Tensor,
        batch: Mapping[str, torch.Tensor],
        drugs: torch.Tensor,
    ) -> Tuple[List[torch.Tensor], torch.Tensor]:
        b, v, k, d = encoded.shape
        memory = encoded.reshape(b, v * k, d)
        valid, _types, semantic_masks = self._flat_masks(batch)

        private_masks = semantic_masks
        if self.variant in _HASH_SALTS:
            private_masks = self._hash_partition_masks(
                batch,
                semantic_masks,
                _HASH_SALTS[self.variant],
            )

        normalized = self.read_norm(memory)
        keys = self.read_key(normalized)
        values = self.read_value(normalized)
        typed_union = semantic_masks[0] | semantic_masks[1] | semantic_masks[2]

        global_chunks: List[torch.Tensor] = []
        private_chunks: List[List[torch.Tensor]] = [[], [], []]

        for start in range(0, MEDICATIONS, CHUNK):
            selected = drugs[start : start + CHUNK]
            query = self.read_query(selected)
            scores = torch.einsum("md,bnd->bmn", query, keys) / math.sqrt(DIM)

            global_weights = _masked_softmax(scores, valid[:, None, :], dim=-1)
            global_chunks.append(torch.einsum("bmn,bnd->bmd", global_weights, values))

            if self.variant in {"coupled_budget_add", "coupled_budget_concat"}:
                coupled = _masked_softmax(scores, typed_union[:, None, :], dim=-1)
                for index, mask in enumerate(private_masks):
                    weights = coupled * mask[:, None, :].to(coupled.dtype)
                    private_chunks[index].append(
                        torch.einsum("bmn,bnd->bmd", weights, values)
                    )
            elif self.variant == "wide_global_add":
                # Filled after the exact global context is concatenated.
                continue
            else:
                for index, mask in enumerate(private_masks):
                    weights = _masked_softmax(scores, mask[:, None, :], dim=-1)
                    private_chunks[index].append(
                        torch.einsum("bmn,bnd->bmd", weights, values)
                    )

        global_context = torch.cat(global_chunks, dim=1)
        global_present = valid.any(dim=-1)

        if self.variant == "wide_global_add":
            private_contexts = [global_context, global_context, global_context]
            private_present = [global_present, global_present, global_present]
        else:
            private_contexts = [torch.cat(chunks, dim=1) for chunks in private_chunks]
            private_present = [mask.any(dim=-1) for mask in private_masks]

        if self.variant == "private_only_add":
            global_context = torch.zeros_like(global_context)
            global_present = torch.zeros_like(global_present)

        contexts = [global_context] + private_contexts
        present = torch.stack([global_present] + private_present, dim=1)
        return contexts, present

    def _additive_logits(
        self,
        contexts: List[torch.Tensor],
        present: torch.Tensor,
        drugs: torch.Tensor,
        persistence: torch.Tensor,
    ) -> torch.Tensor:
        b = contexts[0].shape[0]
        drug = drugs[None].expand(b, -1, -1)
        logits = torch.zeros(
            b,
            MEDICATIONS,
            dtype=contexts[0].dtype,
            device=contexts[0].device,
        )

        for channel, context in enumerate(contexts):
            channel_vector = self.channel_embedding.weight[channel][None, None, :].expand(
                b, MEDICATIONS, -1
            )
            features = torch.cat((context, drug, channel_vector), dim=-1)
            contribution = self.evidence_head(features).squeeze(-1)
            logits = logits + contribution * present[:, channel, None].to(contribution.dtype)

        persistence_features = torch.cat((persistence, drug), dim=-1)
        logits = logits + self.persistence_head(persistence_features).squeeze(-1)
        return logits + self.drug_bias

    def _concat_logits(
        self,
        contexts: List[torch.Tensor],
        drugs: torch.Tensor,
        persistence: torch.Tensor,
    ) -> torch.Tensor:
        b = contexts[0].shape[0]
        drug = drugs[None].expand(b, -1, -1)
        features = torch.cat((*contexts, drug, persistence), dim=-1)
        return self.concat_head(features).squeeze(-1) + self.drug_bias

    def forward(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        encoded = self._encode(batch)
        drugs = self._drugs()
        contexts, present = self._contexts(encoded, batch, drugs)
        persistence = self._persistence(batch)

        if self.variant in {"mhef_independent_concat", "coupled_budget_concat"}:
            return self._concat_logits(contexts, drugs, persistence)
        return self._additive_logits(contexts, present, drugs, persistence)


__all__ = [
    "DIM",
    "MEDICATIONS",
    "MHEF_VARIANTS",
    "MHEFModel",
    "configure_numeric_policy",
    "objective",
    "pack_rows",
    "parameter_count",
]
