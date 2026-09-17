"""Minimal slot-based medication-set model and exact decoders.

The clinical path follows the frozen MICA DrugQuery path.  The two experiment
arms use this same module and differ only in their objective and decoder.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np
import torch
from scipy.optimize import linear_sum_assignment
from torch import nn

MEDICATIONS = 131
DIM = 128
HEADS = 4
FF_DIM = 256
CLINICAL_LAYERS = 2
SLOTS = 131
CHUNK = 16
UNAVAILABLE_WEIGHT = -1.0e12


def configure_numeric_policy() -> dict[str, object]:
    """Freeze the float32 CUDA policy shared by both arms."""

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
    """Pack target-free current D/P and strictly earlier D/P/M tuples."""

    packed: list[list[tuple[list[int], int, int]]] = []
    med_offset = diagnosis_count + procedure_count
    for row in rows:
        tokens: list[tuple[list[int], int, int]] = [([], 0, 0)]
        tokens.extend(([int(code)], 1, 0) for code in sorted(set(row["diagnoses"])))
        tokens.extend(
            ([diagnosis_count + int(code)], 2, 0) for code in sorted(set(row["procedures"]))
        )
        history = row["history"]
        for index, visit in enumerate(history):
            lag = len(history) - index
            tokens.append((sorted(set(map(int, visit[0]))), 3, lag))
            tokens.append(([diagnosis_count + int(code) for code in sorted(set(visit[1]))], 4, lag))
            tokens.append(([med_offset + int(code) for code in sorted(set(visit[2]))], 5, lag))
        packed.append(tokens)
    width = max(map(len, packed))
    ids: list[int] = []
    offsets = [0]
    types: list[int] = []
    lags: list[float] = []
    masks: list[list[bool]] = []
    for tokens in packed:
        mask: list[bool] = []
        for index in range(width):
            codes, kind, lag = tokens[index] if index < len(tokens) else ([], 0, 0)
            ids.extend(codes)
            offsets.append(len(ids))
            types.append(kind)
            lags.append(float(lag))
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
                normalized,
                normalized,
                normalized,
                key_padding_mask=~mask,
                need_weights=False,
            )[0]
        )
        return x + self.ff(self.norm2(x))


class StructuredSetModel(nn.Module):
    """MICA DrugQuery evidence path followed by anonymous set slots."""

    def __init__(
        self,
        diagnosis_count: int,
        procedure_count: int,
        medication_count: int = MEDICATIONS,
        slot_count: int = SLOTS,
    ) -> None:
        super().__init__()
        if medication_count <= 0 or slot_count <= 0:
            raise ValueError("medication_count and slot_count must be positive")
        self.medication_count = int(medication_count)
        self.slot_count = int(slot_count)
        self.med_offset = int(diagnosis_count + procedure_count)
        self.codes = nn.EmbeddingBag(
            self.med_offset + self.medication_count,
            DIM,
            mode="mean",
            include_last_offset=True,
        )
        self.types = nn.Embedding(6, DIM)
        self.token_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.input_dropout = nn.Dropout(0.1)
        self.drug_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.conditioner = nn.Linear(DIM, 2 * DIM)
        self.blocks = nn.ModuleList([ClinicalBlock() for _ in range(CLINICAL_LAYERS)])
        self.final_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.read_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.query = nn.Linear(DIM, DIM, bias=False)
        self.key = nn.Linear(DIM, DIM, bias=False)
        self.value = nn.Linear(DIM, DIM, bias=False)

        self.representation = nn.Sequential(nn.Linear(3 * DIM, DIM), nn.GELU(), nn.Dropout(0.1))

        self.slot_tokens = nn.Parameter(torch.empty(self.slot_count, DIM))
        self.slot_norm1 = nn.LayerNorm(DIM, eps=1e-5)
        self.slot_self = nn.MultiheadAttention(DIM, HEADS, dropout=0.0, batch_first=True)
        self.slot_norm2 = nn.LayerNorm(DIM, eps=1e-5)
        self.slot_cross = nn.MultiheadAttention(DIM, HEADS, dropout=0.0, batch_first=True)
        self.slot_norm3 = nn.LayerNorm(DIM, eps=1e-5)
        self.slot_ff = nn.Sequential(nn.Linear(DIM, FF_DIM), nn.GELU(), nn.Linear(FF_DIM, DIM))

        self.slot_projection = nn.Linear(DIM, DIM, bias=False)
        self.medication_projection = nn.Linear(DIM, DIM, bias=False)
        self.medication_bias = nn.Parameter(torch.zeros(self.medication_count))
        self.null_projection = nn.Linear(DIM, 1, bias=False)
        self.null_bias = nn.Parameter(torch.zeros(()))
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
        for attention in (self.slot_self, self.slot_cross):
            nn.init.xavier_uniform_(attention.in_proj_weight)
            nn.init.zeros_(attention.in_proj_bias)
        nn.init.zeros_(self.conditioner.weight)
        nn.init.zeros_(self.conditioner.bias)
        nn.init.normal_(self.slot_tokens, mean=0.0, std=0.02)

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
        normalized = self.read_norm(views)
        scores = torch.einsum("md,bmkd->bmk", self.query(drugs), self.key(normalized)) / math.sqrt(
            DIM
        )
        weights = scores.masked_fill(~mask[:, None], float("-inf")).softmax(dim=-1)
        return torch.einsum("bmk,bmkd->bmd", weights, self.value(normalized))

    def medication_representations(
        self, assembled: torch.Tensor, mask: torch.Tensor, drugs: torch.Tensor
    ) -> torch.Tensor:
        contexts: list[torch.Tensor] = []
        for start in range(0, self.medication_count, CHUNK):
            selected = drugs[start : start + CHUNK]
            expanded = assembled[:, None].expand(-1, selected.shape[0], -1, -1)
            pooled = self.read(expanded, selected, mask)
            contexts.append(self.condition_context(pooled, selected))
        context = torch.cat(contexts, dim=1)
        broadcast_drugs = drugs.unsqueeze(0).expand(context.shape[0], -1, -1)
        features = torch.cat((context, broadcast_drugs, context * broadcast_drugs), dim=-1)
        return self.representation(features)

    def condition_context(self, context: torch.Tensor, drugs: torch.Tensor) -> torch.Tensor:
        scale, shift = (0.5 * self.conditioner(drugs).tanh()).chunk(2, dim=-1)
        return context * (1.0 + scale[None]) + shift[None]

    def slot_representations(self, medication_representations: torch.Tensor) -> torch.Tensor:
        batch_size = medication_representations.shape[0]
        slots = self.slot_tokens.unsqueeze(0).expand(batch_size, -1, -1)
        normalized = self.slot_norm1(slots)
        slots = slots + self.slot_self(normalized, normalized, normalized, need_weights=False)[0]
        normalized = self.slot_norm2(slots)
        slots = (
            slots
            + self.slot_cross(
                normalized,
                medication_representations,
                medication_representations,
                need_weights=False,
            )[0]
        )
        return slots + self.slot_ff(self.slot_norm3(slots))

    def forward(self, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        x = self.encode_tokens(batch)
        assembled = self.assemble(x, batch["mask"])
        drugs = self.drug_norm(self.codes.weight[self.med_offset :])
        representations = self.medication_representations(assembled, batch["mask"], drugs)
        slots = self.slot_representations(representations)
        slot_scores = self.slot_projection(slots)
        medication_scores = self.medication_projection(drugs)
        medication_logits = torch.einsum("bkd,md->bkm", slot_scores, medication_scores)
        medication_logits = medication_logits / math.sqrt(DIM) + self.medication_bias
        null_logits = self.null_projection(slots).squeeze(-1) + self.null_bias
        utility = medication_logits - null_logits.unsqueeze(-1)
        return {
            "utility": utility,
            "medication_logits": medication_logits,
            "null_logits": null_logits,
            "slots": slots,
            "representations": representations,
        }


def target_indices(target: Sequence[int] | np.ndarray, medication_count: int) -> tuple[int, ...]:
    """Return canonical sorted target IDs and reject malformed cardinality."""

    values = tuple(sorted({int(value) for value in target}))
    if any(value < 0 or value >= medication_count for value in values):
        raise ValueError("target medication ID is outside the declared vocabulary")
    return values


def matching_labels(
    utility: torch.Tensor,
    targets: Sequence[Sequence[int]],
    medication_count: int,
    slot_count: int,
) -> torch.Tensor:
    """Match each target to a slot with cost ``-u`` and fill others with NULL."""

    if utility.ndim != 3 or utility.shape[1:] != (slot_count, medication_count):
        raise ValueError("utility must have shape [batch, slots, medications]")
    if len(targets) != utility.shape[0]:
        raise ValueError("target batch does not match utility batch")
    labels = torch.full(
        (utility.shape[0], slot_count), medication_count, dtype=torch.long, device=utility.device
    )
    detached = utility.detach().cpu().numpy()
    for batch_index, values in enumerate(targets):
        canonical = target_indices(values, medication_count)
        if len(canonical) > slot_count:
            raise ValueError("target cardinality exceeds slot capacity")
        if not canonical:
            continue
        cost = -detached[batch_index][:, canonical]
        rows, columns = linear_sum_assignment(cost)
        if len(rows) != len(canonical):
            raise RuntimeError("matching solver did not assign every target")
        if len(rows) != len(columns):
            raise RuntimeError("matching solver returned unequal row and column counts")
        for row, column in zip(rows.tolist(), columns.tolist()):  # noqa: B905 - equal solver outputs; Python 3.8
            labels[batch_index, row] = canonical[column]
    return labels


def matching_cross_entropy(
    outputs: dict[str, torch.Tensor],
    targets: Sequence[Sequence[int]],
    medication_count: int,
    slot_count: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute categorical CE after Hungarian matching on ``-u``."""

    labels = matching_labels(outputs["utility"], targets, medication_count, slot_count)
    logits = torch.cat((outputs["medication_logits"], outputs["null_logits"].unsqueeze(-1)), dim=-1)
    loss = nn.functional.cross_entropy(logits.reshape(-1, medication_count + 1), labels.reshape(-1))
    return loss, labels


def matching_cost_from_probabilities(probabilities: np.ndarray, medication: int) -> np.ndarray:
    """Return the complete-CE assignment cost for one target medication."""

    values = np.asarray(probabilities, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] < 2:
        raise ValueError("probabilities must have shape [slots, medications + NULL]")
    if medication < 0 or medication >= values.shape[1] - 1:
        raise ValueError("target medication is outside the probability vocabulary")
    return -np.log(values[:, medication]) + np.log(values[:, -1])


def threshold_decode(utility: np.ndarray, beta: float) -> tuple[int, ...]:
    """Decode unique medication coordinates using strict ``v > beta``."""

    values = np.asarray(utility, dtype=np.float64)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("utility must be a finite [slots, medications] array")
    return tuple(int(index) for index in np.flatnonzero(values.max(axis=0) > beta))


def assignment_decode(utility: np.ndarray, beta: float) -> tuple[int, ...]:
    """Decode the exact positive-edge maximum-weight injective assignment."""

    return tuple(sorted(medication for _slot, medication in assignment_pairs(utility, beta)))


def assignment_pairs(utility: np.ndarray, beta: float) -> tuple[tuple[int, int], ...]:
    """Return canonical ``(slot, medication)`` pairs for exact decoding."""

    values = np.asarray(utility, dtype=np.float64)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("utility must be a finite [slots, medications] array")
    slot_count, medication_count = values.shape
    weights = np.full(
        (slot_count, medication_count + slot_count), UNAVAILABLE_WEIGHT, dtype=np.float64
    )
    positive = values - float(beta)
    weights[:, :medication_count] = np.where(positive > 0.0, positive, UNAVAILABLE_WEIGHT)
    weights[np.arange(slot_count), medication_count + np.arange(slot_count)] = 0.0
    rows, columns = linear_sum_assignment(-weights)
    selected = [
        (int(row), int(column))
        for row, column in zip(rows.tolist(), columns.tolist())  # noqa: B905 - equal solver outputs; Python 3.8
        if column < medication_count and weights[row, column] > 0.0
    ]
    medications = [medication for _slot, medication in selected]
    if len(medications) != len(set(medications)):
        raise RuntimeError("assignment decoder emitted duplicate medications")
    return tuple(sorted(selected, key=lambda pair: (pair[0], pair[1])))


def utilities_to_categorical_probabilities(
    medication_logits: np.ndarray, null_logits: np.ndarray
) -> np.ndarray:
    """Materialize categorical probabilities for deterministic matching fixtures."""

    logits = np.concatenate(
        (np.asarray(medication_logits), np.asarray(null_logits)[..., None]), axis=-1
    )
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=-1, keepdims=True)


__all__ = (
    "CLINICAL_LAYERS",
    "DIM",
    "FF_DIM",
    "HEADS",
    "MEDICATIONS",
    "SLOTS",
    "StructuredSetModel",
    "assignment_decode",
    "assignment_pairs",
    "configure_numeric_policy",
    "matching_cost_from_probabilities",
    "matching_cross_entropy",
    "matching_labels",
    "pack_inputs",
    "target_indices",
    "threshold_decode",
    "utilities_to_categorical_probabilities",
)
