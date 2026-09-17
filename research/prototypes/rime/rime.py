"""Regimen-conditional marginal-energy model for medication sets.

The clinical encoder is a 64-dimensional, target-free DrugQuery path.  The
full model and the count-only control share every parameter.  They differ only
in how the medication-specific set features are reduced before the global
utility head is evaluated.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

import torch
from torch import nn

MEDICATIONS = 131
DIM = 64
SET_HIDDEN = 128
HEADS = 4
FF_DIM = 128
CLINICAL_LAYERS = 2
CHUNK = 16
FLIP_CAP = 2 * MEDICATIONS


def configure_numeric_policy() -> dict[str, object]:
    """Freeze the float32 CUDA policy used by both matched arms."""

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
    """Pack current D/P and strictly earlier D/P/M tuples.

    The representation follows the frozen MICA token contract.  Every row has
    an explicit null token and every preceding visit contributes one mean bag
    for each of diagnosis, procedure, and medication codes.
    """

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


class RIMEModel(nn.Module):
    """RIME full arm or the parameter-matched count-only control."""

    VARIANTS = ("composition", "count_only")

    def __init__(
        self,
        diagnosis_count: int,
        procedure_count: int,
        variant: str = "composition",
        medication_count: int = MEDICATIONS,
    ) -> None:
        super().__init__()
        if variant not in self.VARIANTS:
            raise ValueError("variant must be composition or count_only")
        if medication_count <= 0:
            raise ValueError("medication_count must be positive")
        self.variant = variant
        self.medication_count = int(medication_count)
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
        self.blocks = nn.ModuleList([ClinicalBlock() for _ in range(CLINICAL_LAYERS)])
        self.final_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.read_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.query = nn.Linear(DIM, DIM, bias=False)
        self.key = nn.Linear(DIM, DIM, bias=False)
        self.value = nn.Linear(DIM, DIM, bias=False)

        # p_x is the masked mean of the target-free assembled clinical tokens.
        self.z_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.wd = nn.Linear(DIM, DIM, bias=False)
        self.we = nn.Linear(DIM, DIM, bias=False)
        self.wp = nn.Linear(DIM, DIM, bias=False)
        self.local = nn.Linear(DIM, 1)
        self.phi = nn.Sequential(
            nn.Linear(DIM, SET_HIDDEN),
            nn.GELU(),
            nn.Linear(SET_HIDDEN, DIM),
        )
        self.rho = nn.Sequential(
            nn.Linear(2 * DIM, SET_HIDDEN),
            nn.GELU(),
            nn.Linear(SET_HIDDEN, 1),
        )
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

    def read(self, views: torch.Tensor, drugs: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Medication-specific attention pooling over ``[B,M,K,D]`` views."""

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
            contexts.append(self.read(expanded, selected, mask))
        return torch.cat(contexts, dim=1)

    def encode(self, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        """Return target-free unary and set-feature representations."""

        encoded = self.encode_tokens(batch)
        assembled = self.assemble(encoded, batch["mask"])
        mask = batch["mask"].to(assembled.dtype).unsqueeze(-1)
        p_x = (assembled * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        drugs = self.drug_norm(self.codes.weight[self.med_offset :])
        e_m = self.medication_representations(assembled, batch["mask"], drugs)
        z = self.z_norm(self.wd(drugs).unsqueeze(0) + self.we(e_m) + self.wp(p_x).unsqueeze(1))
        return {
            "p_x": p_x,
            "d_m": drugs,
            "e_m": e_m,
            "z_m": z,
            "a_m": self.local(z).squeeze(-1),
            "phi_m": self.phi(z),
        }

    def forward(self, batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        return self.encode(batch)

    def _base_terms(
        self, encoded: dict[str, torch.Tensor], context: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return local sum, set feature, and global utility for each context."""

        a_m = encoded["a_m"]
        phi_m = encoded["phi_m"]
        p_x = encoded["p_x"]
        if context.dtype != torch.bool:
            context = context.bool()
        local_sum = (a_m * context.to(a_m.dtype)).sum(dim=1)
        if self.variant == "composition":
            r = torch.einsum("bm,bmd->bd", context.to(phi_m.dtype), phi_m)
        else:
            count = context.to(phi_m.dtype).sum(dim=1, keepdim=True)
            r = count * phi_m.mean(dim=1)
        global_utility = self.rho(torch.cat((p_x, r), dim=-1)).squeeze(-1)
        return local_sum, r, global_utility

    def utility(self, encoded: dict[str, torch.Tensor], context: torch.Tensor) -> torch.Tensor:
        """Evaluate ``U(x,S)`` for one or more medication sets."""

        local_sum, _r, global_utility = self._base_terms(encoded, context)
        return local_sum + global_utility

    def marginal_logits(
        self, encoded: dict[str, torch.Tensor], context: torch.Tensor
    ) -> torch.Tensor:
        """Return ``U((C minus m) union {m}) - U(C minus m)`` for every m."""

        context = context.bool()
        batch, meds = context.shape
        phi_m = encoded["phi_m"]
        a_m = encoded["a_m"]
        p_x = encoded["p_x"]
        if self.variant == "composition":
            additions = phi_m
        else:
            additions = phi_m.mean(dim=1, keepdim=True).expand_as(phi_m)
        without = context[:, None, :].expand(-1, meds, -1).clone()
        indices = torch.arange(meds, device=context.device)
        without[:, indices, indices] = False
        if self.variant == "composition":
            base_r = torch.einsum("bmk,bkd->bmd", without.to(phi_m.dtype), phi_m)
        else:
            counts = without.to(phi_m.dtype).sum(dim=-1, keepdim=True)
            base_r = counts * phi_m.mean(dim=1, keepdim=True)
        base_p = p_x[:, None, :].expand(-1, meds, -1)
        base_global = self.rho(
            torch.cat((base_p, base_r), dim=-1).reshape(batch * meds, -1)
        ).reshape(batch, meds)
        candidate_r = base_r + additions
        candidate_global = self.rho(
            torch.cat((base_p, candidate_r), dim=-1).reshape(batch * meds, -1)
        ).reshape(batch, meds)
        return a_m + candidate_global - base_global

    def flip_gains(
        self, encoded: dict[str, torch.Tensor], context: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return add and remove gains for each row and medication."""

        context = context.bool()
        _local_sum, r, base_global = self._base_terms(encoded, context)
        phi_m = encoded["phi_m"]
        a_m = encoded["a_m"]
        p_x = encoded["p_x"]
        if self.variant == "composition":
            additions = phi_m
        else:
            additions = phi_m.mean(dim=1, keepdim=True).expand_as(phi_m)
        add_r = r[:, None, :] + additions
        remove_r = r[:, None, :] - additions
        batch, meds, _ = add_r.shape
        candidate_p = p_x[:, None, :].expand(-1, meds, -1)
        add_global = self.rho(
            torch.cat((candidate_p, add_r), dim=-1).reshape(batch * meds, -1)
        ).reshape(batch, meds)
        remove_global = self.rho(
            torch.cat((candidate_p, remove_r), dim=-1).reshape(batch * meds, -1)
        ).reshape(batch, meds)
        add = a_m + add_global - base_global[:, None]
        remove = -(a_m + base_global[:, None] - remove_global)
        neg_inf = torch.full_like(add, float("-inf"))
        add = torch.where(context, neg_inf, add)
        remove = torch.where(context, remove, neg_inf)
        return add, remove


def sample_contexts(
    targets: torch.Tensor, rng: random.Random, medication_count: int = MEDICATIONS
) -> tuple[torch.Tensor, torch.Tensor]:
    """Sample ``C_pos`` and ``C_err`` exactly as declared by RIME."""

    if targets.ndim != 2 or targets.shape[1] != medication_count:
        raise ValueError("targets must have shape [batch, medication_count]")
    device = targets.device
    positive = torch.zeros_like(targets, dtype=torch.bool)
    erroneous = torch.zeros_like(targets, dtype=torch.bool)
    for row_index in range(targets.shape[0]):
        values = torch.nonzero(targets[row_index] > 0.5, as_tuple=False).flatten().tolist()
        negatives = [index for index in range(medication_count) if index not in values]
        if not negatives:
            raise ValueError("target set leaves no negative medication for C_err")
        k = rng.randint(0, len(values))
        chosen = rng.sample(values, k)
        positive[row_index, chosen] = True
        erroneous[row_index, chosen] = True
        erroneous[row_index, rng.choice(negatives)] = True
    return positive.to(device), erroneous.to(device)


def context_loss(
    model: RIMEModel,
    encoded: dict[str, torch.Tensor],
    targets: torch.Tensor,
    rng: random.Random,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Compute the equal-weight positive/error-context BCE objective."""

    positive, erroneous = sample_contexts(targets, rng, model.medication_count)
    positive_logits = model.marginal_logits(encoded, positive)
    erroneous_logits = model.marginal_logits(encoded, erroneous)
    positive_loss = nn.functional.binary_cross_entropy_with_logits(positive_logits, targets)
    erroneous_loss = nn.functional.binary_cross_entropy_with_logits(erroneous_logits, targets)
    return 0.5 * (positive_loss + erroneous_loss), positive_loss, erroneous_loss


def greedy_decode(
    model: RIMEModel,
    encoded: dict[str, torch.Tensor],
    *,
    flip_cap: int = FLIP_CAP,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Run deterministic positive-gain single-flip inference.

    Returns the final set mask, add count, remove count, and cap-hit flag for
    each row.  Ties use the first medication coordinate, which is canonical
    vocabulary order. Model utilities remain float32.
    """

    batch = encoded["p_x"].shape[0]
    device = encoded["p_x"].device
    selected = torch.zeros((batch, model.medication_count), dtype=torch.bool, device=device)
    adds = torch.zeros(batch, dtype=torch.long, device=device)
    removes = torch.zeros(batch, dtype=torch.long, device=device)
    active = torch.ones(batch, dtype=torch.bool, device=device)
    cap_hits = torch.zeros(batch, dtype=torch.bool, device=device)
    for step in range(flip_cap):
        if not bool(active.any()):
            break
        add, remove = model.flip_gains(encoded, selected)
        gains = torch.where(selected, remove, add)
        gains = gains.masked_fill(~active[:, None], float("-inf"))
        max_gain, medication = gains.max(dim=1)
        moving = active & (max_gain > 0.0)
        if not bool(moving.any()):
            active = moving
            break
        rows = torch.nonzero(moving, as_tuple=False).flatten()
        chosen = medication[moving]
        was_selected = selected[rows, chosen]
        selected[rows, chosen] = ~was_selected
        adds[moving] += (~was_selected).to(adds.dtype)
        removes[moving] += was_selected.to(removes.dtype)
        active = moving
        if step == flip_cap - 1:
            cap_hits = active.clone()
    return selected, adds, removes, cap_hits


def scores_for_set(
    model: RIMEModel, encoded: dict[str, torch.Tensor], selected: torch.Tensor
) -> torch.Tensor:
    """Compute ``score_m = U(S minus m plus m) - U(S minus m)``."""

    selected = selected.bool()
    _local_sum, set_r, _set_global = model._base_terms(encoded, selected)
    phi_m = encoded["phi_m"]
    if model.variant == "composition":
        additions = phi_m
    else:
        additions = phi_m.mean(dim=1, keepdim=True).expand_as(phi_m)
    base_r = set_r[:, None, :] - selected.to(phi_m.dtype)[:, :, None] * additions
    candidate_r = base_r + additions
    batch, medication_count, _ = candidate_r.shape
    candidate_p = encoded["p_x"][:, None, :].expand(-1, medication_count, -1)
    base_global = model.rho(
        torch.cat((candidate_p, base_r), dim=-1).reshape(batch * medication_count, -1)
    ).reshape(batch, medication_count)
    candidate_global = model.rho(
        torch.cat((candidate_p, candidate_r), dim=-1).reshape(batch * medication_count, -1)
    ).reshape(batch, medication_count)
    return encoded["a_m"] + candidate_global - base_global


__all__ = (
    "CHUNK",
    "CLINICAL_LAYERS",
    "DIM",
    "FF_DIM",
    "FLIP_CAP",
    "HEADS",
    "MEDICATIONS",
    "SET_HIDDEN",
    "RIMEModel",
    "configure_numeric_policy",
    "context_loss",
    "greedy_decode",
    "pack_inputs",
    "sample_contexts",
    "scores_for_set",
)
