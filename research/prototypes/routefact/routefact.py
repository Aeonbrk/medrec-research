"""Route-factored medication recommendation matched mechanism model."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, Tuple, Union

import torch
from torch import nn

MICA_DIR = Path(__file__).resolve().parents[1] / "mica"
if str(MICA_DIR) not in sys.path:
    sys.path.insert(0, str(MICA_DIR))
from mica import CHUNK, DIM, MICA  # noqa: E402

MEDICATIONS = 131
ROUTE_AUX_WEIGHT = 0.10
DDI_WEIGHT = 0.05


class RouteFactModel(MICA):
    """DrugQuery substrate with a shared medication-route prediction surface.

    Variants have identical parameters and route supervision.

    ``route_aux`` predicts medication presence with the ordinary direct MICA
    head while route logits are auxiliary.

    ``route_fact`` predicts medication presence only through the route logits,
    using a fixed noisy-OR over Train-supported routes for each medication.
    The direct head remains instantiated (for exact parameter matching) but is
    intentionally outside the RouteFact medication decision path.
    """

    ROUTE_VARIANTS = ("route_aux", "route_fact")

    def __init__(
        self,
        diagnosis_count: int,
        procedure_count: int,
        route_count: int,
        variant: str,
        medication_count: int = MEDICATIONS,
    ) -> None:
        if variant not in self.ROUTE_VARIANTS:
            raise ValueError("variant must be route_aux or route_fact")
        if route_count <= 0:
            raise ValueError("route_count must be positive")
        super().__init__(
            diagnosis_count,
            procedure_count,
            variant="drug_query",
            medication_count=medication_count,
        )
        self.route_variant = variant
        self.route_count = int(route_count)
        self.route_projection = nn.Sequential(
            nn.Linear(3 * DIM, DIM),
            nn.GELU(),
            nn.Dropout(0.1),
        )
        self.route_embedding = nn.Parameter(torch.empty(self.route_count, DIM))
        self.route_bias = nn.Parameter(torch.zeros(self.medication_count, self.route_count))
        nn.init.xavier_uniform_(self.route_projection[0].weight)
        nn.init.zeros_(self.route_projection[0].bias)
        nn.init.normal_(self.route_embedding, mean=0.0, std=0.02)

    def initialize_route_prevalence(
        self,
        route_prevalence: torch.Tensor,
        medication_prevalence: torch.Tensor,
        allowed_route_mask: torch.Tensor,
    ) -> None:
        """Initialize route biases so noisy-OR matches medication prevalence.

        Relative route frequencies come from Train route labels. A single
        medication-specific scale is solved by bisection, avoiding the severe
        positive-bias that zero route logits would induce under noisy-OR.
        """
        if route_prevalence.shape != (self.medication_count, self.route_count):
            raise ValueError("route_prevalence shape mismatch")
        if medication_prevalence.shape != (self.medication_count,):
            raise ValueError("medication_prevalence shape mismatch")
        allowed = allowed_route_mask.to(dtype=torch.bool, device=route_prevalence.device)
        with torch.no_grad():
            bias = torch.full_like(route_prevalence, -20.0)
            for med in range(self.medication_count):
                indices = torch.nonzero(allowed[med], as_tuple=False).flatten()
                if indices.numel() == 0:
                    raise ValueError("medication has no allowed route")
                raw = route_prevalence[med, indices].clamp_min(0.0)
                if float(raw.sum().item()) <= 0.0:
                    weights = torch.full_like(raw, 1.0 / float(indices.numel()))
                else:
                    weights = raw / raw.sum()
                target = float(medication_prevalence[med].clamp(1e-4, 1.0 - 1e-4).item())
                upper = min(0.95 / max(float(weights.max().item()), 1e-8), 100.0)
                low = 0.0
                high = upper
                for _ in range(60):
                    mid = 0.5 * (low + high)
                    q = (weights * mid).clamp(1e-6, 0.95)
                    p = 1.0 - float(torch.prod(1.0 - q).item())
                    if p < target:
                        low = mid
                    else:
                        high = mid
                q = (weights * (0.5 * (low + high))).clamp(1e-6, 0.95)
                bias[med, indices] = torch.log(q / (1.0 - q))
            self.route_bias.copy_(bias.to(self.route_bias.device))

    def _drugquery_features(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        x = self.encode_tokens(batch)
        mask = batch["mask"]
        drugs = self.drug_norm(self.codes.weight[self.med_offset :])
        assembled = self.assemble(x, mask)
        contexts = []
        for start in range(0, self.medication_count, CHUNK):
            selected = drugs[start : start + CHUNK]
            expanded = assembled[:, None].expand(-1, selected.shape[0], -1, -1)
            pooled = self.read(expanded, selected, mask)
            contexts.append(self.condition_context(pooled, selected))
        context = torch.cat(contexts, dim=1)
        broadcast_drugs = drugs.unsqueeze(0).expand(context.shape[0], -1, -1)
        return torch.cat((context, broadcast_drugs, context * broadcast_drugs), dim=-1)

    @staticmethod
    def aggregate_routes(
        route_logits: torch.Tensor, allowed_route_mask: torch.Tensor
    ) -> torch.Tensor:
        """Convert route logits to medication logits with a stable noisy-OR.

        ``allowed_route_mask`` is [M,R], frozen from Train only. Every medication
        must retain at least one allowed route. The target builder enables the
        UNSPECIFIED coordinate only where Train data require it.
        """
        if route_logits.ndim != 3:
            raise ValueError("route_logits must be [B,M,R]")
        if allowed_route_mask.shape != route_logits.shape[1:]:
            raise ValueError("allowed_route_mask must match [M,R]")
        allowed = allowed_route_mask.to(dtype=torch.bool, device=route_logits.device)
        if not bool(allowed.any(dim=1).all().item()):
            raise ValueError("every medication must have at least one allowed route")
        log_p0_terms = torch.nn.functional.logsigmoid(-route_logits)
        log_p0 = (log_p0_terms * allowed.unsqueeze(0)).sum(dim=-1)
        log_p0 = torch.clamp(log_p0, max=-1e-7)
        log_p1 = torch.log(-torch.expm1(log_p0))
        return log_p1 - log_p0

    def forward(
        self,
        batch: Dict[str, torch.Tensor],
        allowed_route_mask: torch.Tensor,
        return_all: bool = False,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
        features = self._drugquery_features(batch)
        direct_logits = self.head(features).squeeze(-1) + self.drug_bias
        route_hidden = self.route_projection(features)
        route_logits = (
            torch.einsum("bmd,rd->bmr", route_hidden, self.route_embedding) / math.sqrt(DIM)
            + self.route_bias.unsqueeze(0)
        )
        if self.route_variant == "route_aux":
            medication_logits = direct_logits
        else:
            medication_logits = self.aggregate_routes(route_logits, allowed_route_mask)
        if return_all:
            return medication_logits, route_logits, direct_logits
        return medication_logits


def masked_route_bce(
    route_logits: torch.Tensor,
    route_targets: torch.Tensor,
    route_supervision_mask: torch.Tensor,
    allowed_route_mask: torch.Tensor,
) -> torch.Tensor:
    """BCE over legal medication-route coordinates with per-pair observability."""
    if route_logits.shape != route_targets.shape:
        raise ValueError("route logits and targets must have identical shape")
    if route_supervision_mask.shape != route_logits.shape[:2]:
        raise ValueError("route supervision mask must be [B,M]")
    if allowed_route_mask.shape != route_logits.shape[1:]:
        raise ValueError("allowed route mask must be [M,R]")
    mask = (
        route_supervision_mask.to(dtype=torch.bool, device=route_logits.device).unsqueeze(-1)
        & allowed_route_mask.to(dtype=torch.bool, device=route_logits.device).unsqueeze(0)
    )
    if not bool(mask.any().item()):
        raise ValueError("route supervision mask is empty")
    losses = torch.nn.functional.binary_cross_entropy_with_logits(
        route_logits, route_targets, reduction="none"
    )
    return losses.masked_select(mask).mean()


def objective(
    medication_logits: torch.Tensor,
    medication_targets: torch.Tensor,
    route_logits: torch.Tensor,
    route_targets: torch.Tensor,
    route_supervision_mask: torch.Tensor,
    allowed_route_mask: torch.Tensor,
    ddi: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    med_bce = torch.nn.functional.binary_cross_entropy_with_logits(
        medication_logits, medication_targets
    )
    route_bce = masked_route_bce(
        route_logits, route_targets, route_supervision_mask, allowed_route_mask
    )
    probabilities = medication_logits.sigmoid()
    ddi_loss = (
        torch.einsum(
            "bi,ij,bj->b", probabilities, torch.triu(ddi, diagonal=1), probabilities
        ).mean()
        / medication_logits.shape[-1]
    )
    total = med_bce + ROUTE_AUX_WEIGHT * route_bce + DDI_WEIGHT * ddi_loss
    return total, med_bce, route_bce, ddi_loss
