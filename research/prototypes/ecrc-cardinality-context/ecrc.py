"""Exact-cardinality regimen-choice mechanism screen.

The scientific difference is whether regimen cardinality changes named-medication
utilities.  Joint cardinality/set prediction and fixed-cardinality subset
likelihoods are treated as established primitives.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import torch
from torch import nn

MICA_DIR = Path(__file__).resolve().parents[1] / "mica"
if str(MICA_DIR) not in sys.path:
    sys.path.insert(0, str(MICA_DIR))

from mica import (  # noqa: E402
    CHUNK,
    DIM,
    MEDICATIONS,
    configure_numeric_policy,
    pack_inputs,
)
from mica import (  # noqa: E402
    MICA as BaseMICA,
)

RANK = 8
VARIANTS = ("kind_bce", "kcond_bce", "kind_exact", "kcond_exact")


class ECRC(nn.Module):
    """DrugQuery backbone with a parameter-matched cardinality context path."""

    def __init__(
        self,
        diagnosis_count: int,
        procedure_count: int,
        k_max: int,
        variant: str,
        rank: int = RANK,
    ) -> None:
        super().__init__()
        if variant not in VARIANTS:
            raise ValueError("unknown ECRC variant")
        if k_max < 1 or k_max > MEDICATIONS:
            raise ValueError("k_max must be in [1, MEDICATIONS]")
        if rank <= 0:
            raise ValueError("rank must be positive")
        self.variant = variant
        self.k_max = int(k_max)
        self.rank = int(rank)
        self.backbone = BaseMICA(
            diagnosis_count,
            procedure_count,
            variant="drug_query",
            medication_count=MEDICATIONS,
        )
        self.size_head = nn.Sequential(
            nn.LayerNorm(DIM, eps=1e-5),
            nn.Linear(DIM, DIM),
            nn.GELU(),
            nn.Linear(DIM, self.k_max + 1),
        )
        self.choice_projection = nn.Linear(3 * DIM, self.rank, bias=False)
        self.k_embedding = nn.Embedding(self.k_max + 1, self.rank)
        self.reset_ecrc_parameters()

    @property
    def conditioned(self) -> bool:
        return self.variant.startswith("kcond_")

    @property
    def exact(self) -> bool:
        return self.variant.endswith("_exact")

    def reset_ecrc_parameters(self) -> None:
        for module in self.size_head.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)
        nn.init.xavier_uniform_(self.choice_projection.weight)
        # Paired arms start from exact DrugQuery-equivalent medication utilities.
        nn.init.zeros_(self.k_embedding.weight)

    def initialize_prevalence(self, prevalence: torch.Tensor) -> None:
        self.backbone.initialize_prevalence(prevalence)

    def _features(
        self, batch: dict[str, torch.Tensor]
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Return medication features, base logits, and patient context."""

        model = self.backbone
        x = model.encode_tokens(batch)
        mask = batch["mask"]
        assembled = model.assemble(x, mask)
        drugs = model.drug_norm(model.codes.weight[model.med_offset :])

        contexts = []
        for start in range(0, model.medication_count, CHUNK):
            selected = drugs[start : start + CHUNK]
            expanded = assembled[:, None].expand(-1, selected.shape[0], -1, -1)
            pooled = model.read(expanded, selected, mask)
            contexts.append(model.condition_context(pooled, selected))
        context = torch.cat(contexts, dim=1)

        broadcast_drugs = drugs.unsqueeze(0).expand(context.shape[0], -1, -1)
        features = torch.cat((context, broadcast_drugs, context * broadcast_drugs), dim=-1)
        base_logits = model.head(features).squeeze(-1) + model.drug_bias

        weights = mask.to(assembled.dtype).unsqueeze(-1)
        patient_context = (assembled * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)
        return features, base_logits, patient_context

    def _cardinality_vector(self, k: torch.Tensor) -> torch.Tensor:
        if self.conditioned:
            return self.k_embedding(k)
        # Every row remains trainable because all rows contribute to the mean.
        return self.k_embedding.weight.mean(dim=0, keepdim=True).expand(k.shape[0], -1)

    def logits_for_k(
        self,
        features: torch.Tensor,
        base_logits: torch.Tensor,
        k: torch.Tensor,
    ) -> torch.Tensor:
        if k.ndim != 1 or k.shape[0] != features.shape[0]:
            raise ValueError("k must be a [batch] tensor")
        if torch.any(k < 0) or torch.any(k > self.k_max):
            raise ValueError("k is outside the trained cardinality range")
        basis = self.choice_projection(features)
        vector = self._cardinality_vector(k)
        delta = torch.einsum("bmr,br->bm", basis, vector) / math.sqrt(float(self.rank))
        return base_logits + delta

    def forward(
        self,
        batch: dict[str, torch.Tensor],
        k: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        features, base_logits, patient_context = self._features(batch)
        size_logits = self.size_head(patient_context)
        predicted_k = size_logits.argmax(dim=-1)
        selected_k = predicted_k if k is None else k
        medication_logits = self.logits_for_k(features, base_logits, selected_k)
        return {
            "medication_logits": medication_logits,
            "size_logits": size_logits,
            "predicted_k": predicted_k,
            "selected_k": selected_k,
            "features": features,
            "base_logits": base_logits,
        }


def fixed_cardinality_log_normalizer(logits: torch.Tensor, k: torch.Tensor) -> torch.Tensor:
    """Compute log sum exp over all subsets with exactly k selected labels."""

    if logits.ndim != 2 or logits.shape[1] != MEDICATIONS:
        raise ValueError("logits must have shape [batch, MEDICATIONS]")
    if k.ndim != 1 or k.shape[0] != logits.shape[0]:
        raise ValueError("k must have shape [batch]")
    if torch.any(k < 0) or torch.any(k > MEDICATIONS):
        raise ValueError("k is outside valid medication cardinality")
    max_k = int(k.max().item())
    dp = logits.new_zeros((logits.shape[0], 1))
    for index in range(MEDICATIONS):
        if max_k == 0:
            break
        col = logits[:, index : index + 1]
        if dp.shape[1] <= max_k:
            if dp.shape[1] == 1:
                dp = torch.cat([dp, dp + col], dim=1)
            else:
                mid = torch.logaddexp(dp[:, 1:], dp[:, :-1] + col)
                dp = torch.cat([dp[:, :1], mid, dp[:, -1:] + col], dim=1)
        else:
            mid = torch.logaddexp(dp[:, 1:], dp[:, :-1] + col)
            dp = torch.cat([dp[:, :1], mid], dim=1)
    return dp.gather(1, k[:, None]).squeeze(1)


def fixed_cardinality_nll(
    logits: torch.Tensor, targets: torch.Tensor, k: torch.Tensor
) -> torch.Tensor:
    if targets.shape != logits.shape:
        raise ValueError("targets must match medication logits")
    observed_k = targets.sum(dim=-1).to(torch.long)
    if not torch.equal(observed_k, k):
        raise ValueError("k must equal the target cardinality during training")
    log_z = fixed_cardinality_log_normalizer(logits, k)
    target_score = (logits * targets).sum(dim=-1)
    return (log_z - target_score).mean()


def joint_objective(
    output: dict[str, torch.Tensor],
    targets: torch.Tensor,
    target_k: torch.Tensor,
    exact: bool,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Joint cardinality + medication negative log-likelihood.

    Division by MEDICATIONS is a constant scaling of the joint NLL and keeps
    gradient magnitude close to historical MICA BCE training.
    """

    logits = output["medication_logits"]
    size_logits = output["size_logits"]
    if exact:
        medication_nll = fixed_cardinality_nll(logits, targets, target_k)
    else:
        medication_nll = (
            nn.functional.binary_cross_entropy_with_logits(logits, targets, reduction="none")
            .sum(dim=-1)
            .mean()
        )
    size_nll = nn.functional.cross_entropy(size_logits, target_k)
    loss = (medication_nll + size_nll) / float(MEDICATIONS)
    return loss, {
        "medication_nll": medication_nll.detach(),
        "size_nll": size_nll.detach(),
    }


def topk_indices(scores: torch.Tensor, k: torch.Tensor) -> list[list[int]]:
    """Exact per-row Top-K with canonical medication-index tie breaking."""

    if scores.ndim != 2 or scores.shape[1] != MEDICATIONS:
        raise ValueError("scores must have shape [batch, MEDICATIONS]")
    values = scores.detach().cpu().tolist()
    counts = k.detach().cpu().tolist()
    output: list[list[int]] = []
    for row, count in zip(values, counts):  # noqa: B905
        ordered = sorted(range(MEDICATIONS), key=lambda index: (-float(row[index]), index))
        output.append(ordered[: int(count)])
    return output


__all__ = (
    "DIM",
    "ECRC",
    "MEDICATIONS",
    "RANK",
    "VARIANTS",
    "configure_numeric_policy",
    "fixed_cardinality_log_normalizer",
    "fixed_cardinality_nll",
    "joint_objective",
    "pack_inputs",
    "topk_indices",
)
