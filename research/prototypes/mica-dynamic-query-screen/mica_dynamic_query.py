"""Bounded patient-conditioned medication-query screen built on MICA-Core."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import torch
from torch import nn

try:
    from mica import CHUNK, DIM, MEDICATIONS, MICA as BaseMICA
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mica"))
    from mica import CHUNK, DIM, MEDICATIONS, MICA as BaseMICA

ROUTES = 4
ADAPTER_DIM = 32
VARIANTS = (
    "core",
    "static_multiquery",
    "global_dynamic_multiquery",
    "evidence_dynamic_multiquery",
    "static_query_adapter",
    "dynamic_query_adapter",
)
MULTIQUERY_VARIANTS = {
    "static_multiquery",
    "global_dynamic_multiquery",
    "evidence_dynamic_multiquery",
}
ADAPTER_VARIANTS = {"static_query_adapter", "dynamic_query_adapter"}


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


class MICADynamicQuery(BaseMICA):
    """MICA-Core plus two matched families of patient-conditioned queries."""

    def __init__(self, diagnosis_count: int, procedure_count: int, variant: str = "core") -> None:
        if variant not in VARIANTS:
            raise ValueError("unknown dynamic-query variant: " + str(variant))
        super().__init__(diagnosis_count, procedure_count, "drug_query")
        self.variant = variant
        if variant in MULTIQUERY_VARIANTS:
            self.route_delta = nn.Parameter(torch.empty(MEDICATIONS, ROUTES, DIM))
            self.route_prior = nn.Parameter(torch.zeros(MEDICATIONS, ROUTES))
            nn.init.normal_(self.route_delta, mean=0.0, std=0.02)
        if variant in ADAPTER_VARIANTS:
            self.query_adapter = nn.Sequential(
                nn.Linear(DIM, ADAPTER_DIM, bias=False),
                nn.GELU(),
                nn.Linear(ADAPTER_DIM, DIM, bias=False),
            )
            nn.init.xavier_uniform_(self.query_adapter[0].weight)
            nn.init.zeros_(self.query_adapter[2].weight)

    def _base_drugs(self) -> torch.Tensor:
        return self.drug_norm(self.codes.weight[self.med_offset :])

    def _masked_summary(
        self, assembled: torch.Tensor, mask: torch.Tensor, projected: bool
    ) -> torch.Tensor:
        normalized = self.read_norm(assembled)
        values = self.key(normalized) if projected else normalized
        weights = mask.to(values.dtype).unsqueeze(-1)
        denominator = weights.sum(dim=1).clamp_min(1.0)
        return (values * weights).sum(dim=1) / denominator

    def _condition_route_contexts(
        self, contexts: torch.Tensor, drugs: torch.Tensor
    ) -> torch.Tensor:
        scale, shift = (0.5 * self.conditioner(drugs).tanh()).chunk(2, dim=-1)
        return contexts * (1.0 + scale[None, :, None, :]) + shift[None, :, None, :]

    def _route_queries(self) -> tuple[torch.Tensor, torch.Tensor]:
        raw_drugs = self.codes.weight[self.med_offset :]
        base_drugs = self.drug_norm(raw_drugs)
        route_queries = self.drug_norm(raw_drugs[:, None, :] + self.route_delta)
        return base_drugs, route_queries

    def _read_routes(
        self,
        assembled: torch.Tensor,
        mask: torch.Tensor,
        route_queries: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        normalized = self.read_norm(assembled)
        keys = self.key(normalized)
        values = self.value(normalized)
        contexts = []
        supports = []
        valid_count = mask.sum(dim=-1).clamp_min(1).to(assembled.dtype)
        for start in range(0, MEDICATIONS, CHUNK):
            selected = route_queries[start : start + CHUNK]
            queries = self.query(selected)
            scores = torch.einsum("ckd,btd->bckt", queries, keys) / math.sqrt(DIM)
            masked_scores = scores.masked_fill(~mask[:, None, None, :], float("-inf"))
            weights = masked_scores.softmax(dim=-1)
            contexts.append(torch.einsum("bckt,btd->bckd", weights, values))
            support = torch.logsumexp(masked_scores, dim=-1) - valid_count.log()[:, None, None]
            supports.append(support)
        return torch.cat(contexts, dim=1), torch.cat(supports, dim=1)

    def _multiquery_context(
        self,
        assembled: torch.Tensor,
        mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        drugs, route_queries = self._route_queries()
        route_contexts, evidence_support = self._read_routes(assembled, mask, route_queries)
        route_contexts = self._condition_route_contexts(route_contexts, drugs)
        route_logits = self.route_prior[None].expand(assembled.shape[0], -1, -1)
        if self.variant == "global_dynamic_multiquery":
            global_key = self._masked_summary(assembled, mask, projected=True)
            projected_routes = self.query(route_queries)
            route_logits = route_logits + torch.einsum(
                "mkd,bd->bmk", projected_routes, global_key
            ) / math.sqrt(DIM)
        elif self.variant == "evidence_dynamic_multiquery":
            route_logits = route_logits + evidence_support
        weights = route_logits.softmax(dim=-1)
        context = torch.einsum("bmk,bmkd->bmd", weights, route_contexts)
        return context, weights

    def _read_batch_queries(
        self,
        assembled: torch.Tensor,
        mask: torch.Tensor,
        queries: torch.Tensor,
    ) -> torch.Tensor:
        normalized = self.read_norm(assembled)
        keys = self.key(normalized)
        values = self.value(normalized)
        contexts = []
        for start in range(0, MEDICATIONS, CHUNK):
            selected = queries[:, start : start + CHUNK]
            scores = torch.einsum("bcd,btd->bct", self.query(selected), keys) / math.sqrt(DIM)
            weights = scores.masked_fill(~mask[:, None, :], float("-inf")).softmax(dim=-1)
            contexts.append(torch.einsum("bct,btd->bcd", weights, values))
        return torch.cat(contexts, dim=1)

    def _adapter_context(
        self,
        assembled: torch.Tensor,
        mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        drugs = self._base_drugs()
        batch_size = assembled.shape[0]
        if self.variant == "static_query_adapter":
            adapter_input = drugs[None].expand(batch_size, -1, -1)
        else:
            patient_summary = self._masked_summary(assembled, mask, projected=False)
            adapter_input = drugs[None] + patient_summary[:, None, :]
        delta = 0.5 * torch.tanh(self.query_adapter(adapter_input))
        queries = drugs[None] + delta
        context = self._read_batch_queries(assembled, mask, queries)
        context = self.condition_context(context, drugs)
        return context, delta

    def _predict(self, context: torch.Tensor, drugs: torch.Tensor) -> torch.Tensor:
        broadcast_drugs = drugs.unsqueeze(0).expand(context.shape[0], -1, -1)
        features = torch.cat((context, broadcast_drugs, context * broadcast_drugs), dim=-1)
        return self.head(features).squeeze(-1) + self.drug_bias

    def forward_with_diagnostics(
        self, batch: dict[str, Any]
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        if self.variant == "core":
            original = self.variant
            self.variant = "drug_query"
            try:
                logits = super().forward(batch)
            finally:
                self.variant = original
            return logits, {}
        assembled = self.assemble(self.encode_tokens(batch), batch["mask"])
        drugs = self._base_drugs()
        if self.variant in MULTIQUERY_VARIANTS:
            context, weights = self._multiquery_context(assembled, batch["mask"])
            return self._predict(context, drugs), {"route_weights": weights}
        context, delta = self._adapter_context(assembled, batch["mask"])
        return self._predict(context, drugs), {"query_delta": delta}

    def forward(self, batch: dict[str, Any]) -> torch.Tensor:
        return self.forward_with_diagnostics(batch)[0]
