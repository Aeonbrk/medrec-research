"""Medication-indexed clinical assembly attribution variants."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import torch
from torch import nn

MEDICATIONS = 131
DIM = 128
HEADS = 4
FF_DIM = 256
LAYERS = 2
CHUNK = 16
THRESHOLD = 0.35


def configure_numeric_policy() -> dict[str, object]:
    """Freeze the float32 CUDA policy shared by both MICA variants."""

    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    return {
        "dtype": "float32",
        "cuda_matmul_allow_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
        "cudnn_allow_tf32": bool(torch.backends.cudnn.allow_tf32),
        "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
        "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
    }


def pack_inputs(
    rows: Sequence[dict[str, Any]], diagnosis_count: int, procedure_count: int
) -> dict[str, torch.Tensor]:
    """Pack target-free current D/P and strictly earlier D/P/M visit tuples.

    Each current code is a singleton bag; each earlier modality is one mean
    bag. Empty historical bags remain explicit. No clinical-code positions or
    patient identifier is encoded, and no input is truncated or hashed.
    """
    packed: list[list[tuple[list[int], int, int]]] = []
    med_offset = diagnosis_count + procedure_count
    for row in rows:
        tokens: list[tuple[list[int], int, int]] = [([], 0, 0)]
        tokens.extend(([int(c)], 1, 0) for c in sorted(set(row["diagnoses"])))
        tokens.extend(([diagnosis_count + int(c)], 2, 0) for c in sorted(set(row["procedures"])))
        history = row["history"]
        for index, visit in enumerate(history):
            lag = len(history) - index
            tokens.append((sorted(set(map(int, visit[0]))), 3, lag))
            tokens.append(([diagnosis_count + int(c) for c in sorted(set(visit[1]))], 4, lag))
            tokens.append(([med_offset + int(c) for c in sorted(set(visit[2]))], 5, lag))
        packed.append(tokens)
    width = max(map(len, packed))
    ids: list[int] = []
    offsets = [0]
    types, lags, masks = [], [], []
    for tokens in packed:
        mask = []
        for index in range(width):
            codes, kind, lag = tokens[index] if index < len(tokens) else ([], 0, 0)
            ids.extend(codes)
            offsets.append(len(ids))
            types.append(kind)
            lags.append(lag)
            mask.append(index < len(tokens))
        masks.append(mask)
    return {
        "codes": torch.tensor(ids, dtype=torch.long),
        "offsets": torch.tensor(offsets, dtype=torch.long),
        "types": torch.tensor(types, dtype=torch.long),
        "lags": torch.tensor(lags, dtype=torch.float32),
        "mask": torch.tensor(masks, dtype=torch.bool),
    }


class ClinicalBlock(nn.Module):
    """One shared-parameter clinical-token interaction block."""

    def __init__(self) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(DIM, eps=1e-5)
        self.attention = nn.MultiheadAttention(DIM, HEADS, dropout=0.0, batch_first=True)
        self.norm2 = nn.LayerNorm(DIM, eps=1e-5)
        self.ff = nn.Sequential(nn.Linear(DIM, FF_DIM), nn.GELU(), nn.Linear(FF_DIM, DIM))

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        normalized = self.norm1(x)
        x = (
            x
            + self.attention(
                normalized, normalized, normalized, key_padding_mask=~mask, need_weights=False
            )[0]
        )
        return x + self.ff(self.norm2(x))


class MICA(nn.Module):
    """Parameter-matched attribution variants for the MICA clinical path.

    ``shared_pool`` evaluates ``T(X) -> shared_pool -> F_m(c)``;
    ``drug_query`` evaluates ``T(X) -> medication_pool(c_m) -> F_m(c_m)``;
    ``late`` evaluates ``T(X) -> F_m(T(X)) -> medication_pool(c_m)``.
    All variants retain the same medication embeddings, readout Q/K/V maps,
    prediction head, and target-free forward interface.
    """

    VARIANTS = ("shared_pool", "drug_query", "late")

    def __init__(
        self, diagnosis_count: int, procedure_count: int, variant: str = "shared_pool"
    ) -> None:
        super().__init__()
        if variant not in self.VARIANTS:
            raise ValueError("variant must be shared_pool, drug_query, or late")
        self.variant = variant
        self.med_offset = diagnosis_count + procedure_count
        self.codes = nn.EmbeddingBag(
            self.med_offset + MEDICATIONS, DIM, mode="mean", include_last_offset=True
        )
        self.types = nn.Embedding(6, DIM)
        self.token_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.input_dropout = nn.Dropout(0.1)
        self.drug_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.conditioner = nn.Linear(DIM, 2 * DIM)
        self.blocks = nn.ModuleList([ClinicalBlock() for _ in range(LAYERS)])
        self.final_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.read_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.query = nn.Linear(DIM, DIM, bias=False)
        self.key = nn.Linear(DIM, DIM, bias=False)
        self.value = nn.Linear(DIM, DIM, bias=False)
        self.head = nn.Sequential(
            nn.Linear(3 * DIM, DIM), nn.GELU(), nn.Dropout(0.1), nn.Linear(DIM, 1)
        )
        self.drug_bias = nn.Parameter(torch.zeros(MEDICATIONS))
        self.register_buffer(
            "lag_frequency", torch.exp(torch.arange(0, DIM, 2) * (-math.log(10000.0) / DIM))
        )
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for module in self.modules():
            if isinstance(module, (nn.Embedding, nn.EmbeddingBag)):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            elif isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
        for block in self.blocks:
            nn.init.xavier_uniform_(block.attention.in_proj_weight)
            nn.init.zeros_(block.attention.in_proj_bias)
        nn.init.zeros_(self.conditioner.weight)
        nn.init.zeros_(self.conditioner.bias)

    def initialize_prevalence(self, prevalence: torch.Tensor) -> None:
        with torch.no_grad():
            p = prevalence.clamp(1e-4, 1.0 - 1e-4)
            self.drug_bias.copy_(torch.log(p / (1.0 - p)))

    def encode_tokens(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        lag_angle = batch["lags"].unsqueeze(-1) * self.lag_frequency
        positions = torch.stack((lag_angle.sin(), lag_angle.cos()), dim=-1).flatten(-2)
        x = (
            self.token_norm(
                self.codes(batch["codes"], batch["offsets"]) + self.types(batch["types"])
            )
            + positions
        )
        return self.input_dropout(x.reshape(*batch["mask"].shape, DIM))

    def assemble(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        for block in self.blocks:
            x = block(x, mask)
        return self.final_norm(x)

    def condition(self, x: torch.Tensor, drugs: torch.Tensor) -> torch.Tensor:
        scale, shift = (0.5 * self.conditioner(drugs).tanh()).chunk(2, dim=-1)
        return x[:, None] * (1.0 + scale[None, :, None]) + shift[None, :, None]

    def read(self, views: torch.Tensor, drugs: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Medication-specific attention pooling over ``[B,M,K,D]`` views."""
        normalized = self.read_norm(views)
        scores = torch.einsum("md,bmkd->bmk", self.query(drugs), self.key(normalized)) / math.sqrt(
            DIM
        )
        weights = scores.masked_fill(~mask[:, None], float("-inf")).softmax(dim=-1)
        return torch.einsum("bmk,bmkd->bmd", weights, self.value(normalized))

    def read_shared(
        self, views: torch.Tensor, query_drug: torch.Tensor, mask: torch.Tensor
    ) -> torch.Tensor:
        """Attention-pool one shared clinical context with an existing readout.

        ``query_drug`` is a deterministic, normalized mean of the medication
        embeddings. The returned context is ``[B,D]`` and therefore gives every
        medication the same evidence weights.
        """
        normalized = self.read_norm(views)
        query = self.query(query_drug)
        scores = torch.einsum("d,bkd->bk", query, self.key(normalized)) / math.sqrt(DIM)
        weights = scores.masked_fill(~mask, float("-inf")).softmax(dim=-1)
        return torch.einsum("bk,bkd->bd", weights, self.value(normalized))

    def condition_context(self, context: torch.Tensor, drugs: torch.Tensor) -> torch.Tensor:
        """Apply the existing medication-specific conditioner to ``[B,M,D]``."""
        scale, shift = (0.5 * self.conditioner(drugs).tanh()).chunk(2, dim=-1)
        return context * (1.0 + scale[None]) + shift[None]

    def forward(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        x = self.encode_tokens(batch)
        mask = batch["mask"]
        drugs = self.drug_norm(self.codes.weight[self.med_offset :])
        assembled = self.assemble(x, mask)
        if self.variant == "shared_pool":
            # Normalize the mean after normalizing each medication embedding;
            # this creates one deterministic query without adding parameters.
            shared_query = torch.nn.functional.normalize(drugs.mean(dim=0), dim=-1)
            shared_context = self.read_shared(assembled, shared_query, mask)
            context = self.condition_context(
                shared_context[:, None, :].expand(-1, MEDICATIONS, -1), drugs
            )
        elif self.variant == "drug_query":
            contexts = []
            for start in range(0, MEDICATIONS, CHUNK):
                selected = drugs[start : start + CHUNK]
                expanded = assembled[:, None].expand(-1, selected.shape[0], -1, -1)
                pooled = self.read(expanded, selected, mask)
                contexts.append(self.condition_context(pooled, selected))
            context = torch.cat(contexts, dim=1)
        else:
            contexts = []
            for start in range(0, MEDICATIONS, CHUNK):
                selected = drugs[start : start + CHUNK]
                context = self.read(self.condition(assembled, selected), selected, mask)
                contexts.append(context)
            context = torch.cat(contexts, dim=1)
        broadcast_drugs = drugs.unsqueeze(0).expand(context.shape[0], -1, -1)
        features = torch.cat((context, broadcast_drugs, context * broadcast_drugs), dim=-1)
        return self.head(features).squeeze(-1) + self.drug_bias


def objective(
    logits: torch.Tensor, targets: torch.Tensor, ddi: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    bce = nn.functional.binary_cross_entropy_with_logits(logits, targets)
    probabilities = logits.sigmoid()
    ddi_loss = (
        torch.einsum(
            "bi,ij,bj->b", probabilities, torch.triu(ddi, diagonal=1), probabilities
        ).mean()
        / MEDICATIONS
    )
    return bce + 0.05 * ddi_loss, bce, ddi_loss
