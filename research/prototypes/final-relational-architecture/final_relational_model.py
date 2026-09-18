"""Paper-intended relational architecture search on the stable FineCode substrate."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, Mapping, Tuple

import torch
from torch import nn

HERE = Path(__file__).resolve().parent
PORTFOLIO_DIR = HERE.parents[0] / "evidence-access-portfolio"
if str(PORTFOLIO_DIR) not in sys.path:
    sys.path.insert(0, str(PORTFOLIO_DIR))

from portfolio_model import (  # noqa: E402
    DIM,
    MEDICATIONS,
    PortfolioModel,
    configure_numeric_policy,
    objective,
    pack_rows,
    parameter_count,
)

RELATION_DIM = 64
RELATION_CHUNK = 8

ARCH_VARIANTS = (
    "summary_add",
    "summary_mul",
    "factorized_pair",
    "nonseparable_pair",
    "joint_competition_pair",
    "untyped_edge_pair",
    "temporal_edge_pair",
)


def _masked_softmax(
    scores: torch.Tensor,
    mask: torch.Tensor,
    dim: int = -1,
) -> torch.Tensor:
    masked = scores.masked_fill(~mask, -1e9)
    weights = torch.softmax(masked, dim=dim) * mask.to(scores.dtype)
    return weights / weights.sum(dim=dim, keepdim=True).clamp_min(1e-12)


class FinalRelationalModel(PortfolioModel):
    """FineCode foundation plus progressively stronger cross-type relation evidence."""

    def __init__(self, diagnosis_count: int, procedure_count: int, variant: str) -> None:
        if variant not in ARCH_VARIANTS:
            raise ValueError("unknown final relational variant: " + str(variant))
        super().__init__(diagnosis_count, procedure_count, "resolution_code")
        self.variant = variant

        self.rel_d_key = nn.Linear(DIM, RELATION_DIM, bias=False)
        self.rel_p_key = nn.Linear(DIM, RELATION_DIM, bias=False)
        self.rel_h_key = nn.Linear(DIM, RELATION_DIM, bias=False)
        self.rel_d_value = nn.Linear(DIM, RELATION_DIM, bias=False)
        self.rel_p_value = nn.Linear(DIM, RELATION_DIM, bias=False)
        self.rel_h_value = nn.Linear(DIM, RELATION_DIM, bias=False)

        self.rel_d_key_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)
        self.rel_p_key_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)
        self.rel_h_key_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)
        self.rel_d_value_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)
        self.rel_p_value_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)
        self.rel_h_value_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)

        self.rel_query = nn.Linear(DIM, RELATION_DIM, bias=False)
        self.rel_query_norm = nn.LayerNorm(RELATION_DIM, eps=1e-5)

        # [DP, DH, PH, same-visit, current-history, both-historical, log1p(lag gap)]
        self.edge_query = nn.Linear(DIM, 7, bias=False)

        feature_dim = 3 * DIM + 3 * RELATION_DIM
        self.final_relational_head = nn.Sequential(
            nn.Linear(feature_dim, DIM),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(DIM, 1),
        )
        self._reset_relation_parameters()

    def _reset_relation_parameters(self) -> None:
        modules = (
            self.rel_d_key,
            self.rel_p_key,
            self.rel_h_key,
            self.rel_d_value,
            self.rel_p_value,
            self.rel_h_value,
            self.rel_query,
            self.edge_query,
            self.final_relational_head[0],
            self.final_relational_head[3],
        )
        for module in modules:
            nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)

    def _field_memories(
        self,
        encoded: torch.Tensor,
        batch: Mapping[str, torch.Tensor],
    ) -> Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
        b, v, k, d = encoded.shape
        memory = encoded.reshape(b, v * k, d)
        types = batch["types"].reshape(b, v * k)
        lags = batch["lags"].reshape(b, v * k)
        valid = (
            batch["token_mask"] & batch["visit_mask"][:, :, None]
        ).reshape(b, v * k)

        return {
            "d": (memory, valid & (types == 1), lags),
            "p": (memory, valid & (types == 2), lags),
            "h": (memory, valid & (types == 3), lags),
        }

    def _safe_read(
        self,
        memory: torch.Tensor,
        mask: torch.Tensor,
        drugs: torch.Tensor,
    ) -> torch.Tensor:
        normalized = self.read_norm(memory)
        keys = self.read_key(normalized)
        values = self.read_value(normalized)
        float_mask = mask[:, None, :].to(memory.dtype)
        outputs = []
        for start in range(0, MEDICATIONS, RELATION_CHUNK):
            selected = drugs[start : start + RELATION_CHUNK]
            q = self.read_query(selected)
            scores = torch.einsum("md,bnd->bmn", q, keys) / math.sqrt(DIM)
            weights = _masked_softmax(scores, mask[:, None, :], dim=-1)
            outputs.append(torch.einsum("bmn,bnd->bmd", weights, values))
        return torch.cat(outputs, dim=1)

    def _project_field(
        self,
        name: str,
        memory: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        key_layer = getattr(self, "rel_" + name + "_key")
        value_layer = getattr(self, "rel_" + name + "_value")
        key_norm = getattr(self, "rel_" + name + "_key_norm")
        value_norm = getattr(self, "rel_" + name + "_value_norm")
        return (
            key_norm(key_layer(memory)),
            value_norm(value_layer(memory)),
        )

    def _relation_query(self, drugs: torch.Tensor) -> torch.Tensor:
        return self.rel_query_norm(self.rel_query(drugs))

    def _summary_relations(
        self,
        fields: Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
        drugs: torch.Tensor,
        multiplicative: bool,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        summaries = {}
        present = {}
        for name in ("d", "p", "h"):
            memory, mask, _lags = fields[name]
            summaries[name] = self._safe_read(memory, mask, drugs)
            present[name] = mask.any(dim=-1)

        d = self.rel_d_value_norm(self.rel_d_value(summaries["d"]))
        p = self.rel_p_value_norm(self.rel_p_value(summaries["p"]))
        h = self.rel_h_value_norm(self.rel_h_value(summaries["h"]))
        gate = 1.0 + torch.tanh(self._relation_query(drugs))[None]

        def combine(
            left: torch.Tensor,
            right: torch.Tensor,
            left_present: torch.Tensor,
            right_present: torch.Tensor,
        ) -> torch.Tensor:
            mask = (left_present & right_present)[:, None, None].to(left.dtype)
            if multiplicative:
                value = left * right
            else:
                value = (left + right) / math.sqrt(2.0)
            return value * gate * mask

        return (
            combine(d, p, present["d"], present["p"]),
            combine(d, h, present["d"], present["h"]),
            combine(p, h, present["p"], present["h"]),
        )

    def _factorized_relation(
        self,
        left_name: str,
        right_name: str,
        fields: Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
        drugs: torch.Tensor,
    ) -> torch.Tensor:
        left_memory, left_mask, _ = fields[left_name]
        right_memory, right_mask, _ = fields[right_name]
        left_key, left_value = self._project_field(left_name, left_memory)
        right_key, right_value = self._project_field(right_name, right_memory)
        q_all = self._relation_query(drugs)

        outputs = []
        scale = math.sqrt(RELATION_DIM)
        for start in range(0, MEDICATIONS, RELATION_CHUNK):
            q = q_all[start : start + RELATION_CHUNK]
            left_scores = torch.einsum("mr,bir->bmi", q, left_key) / scale
            right_scores = torch.einsum("mr,bjr->bmj", q, right_key) / scale
            left_weights = _masked_softmax(
                left_scores, left_mask[:, None, :], dim=-1
            )
            right_weights = _masked_softmax(
                right_scores, right_mask[:, None, :], dim=-1
            )
            left_summary = torch.einsum("bmi,bir->bmr", left_weights, left_value)
            right_summary = torch.einsum("bmj,bjr->bmr", right_weights, right_value)
            outputs.append(left_summary * right_summary)
        return torch.cat(outputs, dim=1)

    @staticmethod
    def _edge_features(
        left_lag: torch.Tensor,
        right_lag: torch.Tensor,
        relation_type_index: int,
        temporal: bool,
    ) -> torch.Tensor:
        b, left_n = left_lag.shape
        right_n = right_lag.shape[1]
        zeros = torch.zeros(
            b, left_n, right_n, dtype=left_lag.dtype, device=left_lag.device
        )
        type_features = [zeros.clone(), zeros.clone(), zeros.clone()]
        type_features[relation_type_index] = torch.ones_like(zeros)

        if not temporal:
            return torch.stack(
                (
                    type_features[0],
                    type_features[1],
                    type_features[2],
                    zeros,
                    zeros,
                    zeros,
                    zeros,
                ),
                dim=-1,
            )

        left = left_lag[:, :, None]
        right = right_lag[:, None, :]
        same_visit = (left == right).to(left_lag.dtype)
        left_current = left == 0
        right_current = right == 0
        current_history = torch.logical_xor(left_current, right_current).to(
            left_lag.dtype
        )
        both_historical = ((left > 0) & (right > 0)).to(left_lag.dtype)
        lag_gap = torch.log1p((left - right).abs())
        return torch.stack(
            (
                type_features[0],
                type_features[1],
                type_features[2],
                same_visit,
                current_history,
                both_historical,
                lag_gap,
            ),
            dim=-1,
        )

    def _pair_components(
        self,
        left_name: str,
        right_name: str,
        fields: Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
        drugs: torch.Tensor,
        edge_mode: str,
        relation_type_index: int,
    ) -> Tuple[
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor | None,
    ]:
        left_memory, left_mask, left_lag = fields[left_name]
        right_memory, right_mask, right_lag = fields[right_name]
        left_key, left_value = self._project_field(left_name, left_memory)
        right_key, right_value = self._project_field(right_name, right_memory)
        pair_mask = left_mask[:, :, None] & right_mask[:, None, :]

        edge = None
        if edge_mode in {"type_only", "temporal"}:
            edge = self._edge_features(
                left_lag,
                right_lag,
                relation_type_index=relation_type_index,
                temporal=edge_mode == "temporal",
            )

        return left_key, right_key, left_value, right_value, pair_mask, edge

    def _pair_relation_separate(
        self,
        left_name: str,
        right_name: str,
        fields: Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
        drugs: torch.Tensor,
    ) -> torch.Tensor:
        (
            left_key,
            right_key,
            left_value,
            right_value,
            pair_mask,
            _edge,
        ) = self._pair_components(
            left_name,
            right_name,
            fields,
            drugs,
            edge_mode="none",
            relation_type_index=0,
        )
        q_all = self._relation_query(drugs)
        outputs = []
        scale = math.sqrt(RELATION_DIM)

        for start in range(0, MEDICATIONS, RELATION_CHUNK):
            q = q_all[start : start + RELATION_CHUNK]
            scores = torch.einsum(
                "mr,bir,bjr->bmij", q, left_key, right_key
            ) / scale
            b, m, i, j = scores.shape
            flat_scores = scores.reshape(b, m, i * j)
            flat_mask = pair_mask.reshape(b, 1, i * j).expand(-1, m, -1)
            weights = _masked_softmax(flat_scores, flat_mask, dim=-1).reshape(
                b, m, i, j
            )
            outputs.append(
                torch.einsum(
                    "bmij,bir,bjr->bmr", weights, left_value, right_value
                )
            )
        return torch.cat(outputs, dim=1)

    def _joint_pair_relations(
        self,
        fields: Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
        drugs: torch.Tensor,
        edge_mode: str,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        relation_types = (("d", "p"), ("d", "h"), ("p", "h"))
        components = [
            self._pair_components(
                left,
                right,
                fields,
                drugs,
                edge_mode=edge_mode,
                relation_type_index=type_index,
            )
            for type_index, (left, right) in enumerate(relation_types)
        ]
        q_all = self._relation_query(drugs)
        edge_q_all = self.edge_query(drugs)
        outputs_by_type = [[], [], []]
        scale = math.sqrt(RELATION_DIM)

        for start in range(0, MEDICATIONS, RELATION_CHUNK):
            q = q_all[start : start + RELATION_CHUNK]
            edge_q = edge_q_all[start : start + RELATION_CHUNK]
            flat_scores = []
            flat_masks = []
            shapes = []

            for (
                left_key,
                right_key,
                _left_value,
                _right_value,
                pair_mask,
                edge,
            ) in components:
                scores = torch.einsum(
                    "mr,bir,bjr->bmij", q, left_key, right_key
                ) / scale
                pair_count = pair_mask.sum(dim=(1, 2)).clamp_min(1).to(scores.dtype)
                scores = scores - pair_count.log()[:, None, None, None]
                if edge is not None:
                    scores = scores + (
                        torch.einsum("me,bije->bmij", edge_q, edge)
                        / math.sqrt(7.0)
                    )
                b, m, i, j = scores.shape
                shapes.append((i, j))
                flat_scores.append(scores.reshape(b, m, i * j))
                flat_masks.append(
                    pair_mask.reshape(b, 1, i * j).expand(-1, m, -1)
                )

            all_scores = torch.cat(flat_scores, dim=-1)
            all_mask = torch.cat(flat_masks, dim=-1)
            all_weights = _masked_softmax(all_scores, all_mask, dim=-1)

            offset = 0
            for type_index, (
                _left_key,
                _right_key,
                left_value,
                right_value,
                _pair_mask,
                _edge,
            ) in enumerate(components):
                i, j = shapes[type_index]
                length = i * j
                weights = all_weights[:, :, offset : offset + length].reshape(
                    all_weights.shape[0], q.shape[0], i, j
                )
                outputs_by_type[type_index].append(
                    torch.einsum(
                        "bmij,bir,bjr->bmr", weights, left_value, right_value
                    )
                )
                offset += length

        return tuple(
            torch.cat(type_outputs, dim=1) for type_outputs in outputs_by_type
        )

    def _relations(
        self,
        fields: Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
        drugs: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if self.variant == "summary_add":
            return self._summary_relations(fields, drugs, multiplicative=False)
        if self.variant == "summary_mul":
            return self._summary_relations(fields, drugs, multiplicative=True)
        if self.variant == "factorized_pair":
            return (
                self._factorized_relation("d", "p", fields, drugs),
                self._factorized_relation("d", "h", fields, drugs),
                self._factorized_relation("p", "h", fields, drugs),
            )
        if self.variant == "nonseparable_pair":
            return (
                self._pair_relation_separate("d", "p", fields, drugs),
                self._pair_relation_separate("d", "h", fields, drugs),
                self._pair_relation_separate("p", "h", fields, drugs),
            )
        if self.variant == "joint_competition_pair":
            return self._joint_pair_relations(fields, drugs, edge_mode="none")
        if self.variant == "untyped_edge_pair":
            return self._joint_pair_relations(fields, drugs, edge_mode="type_only")
        return self._joint_pair_relations(fields, drugs, edge_mode="temporal")

    def forward(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        encoded = self._encode(batch)
        drugs = self._drugs()
        memory, memory_mask = self._flat_evidence(encoded, batch)
        foundation = self._read_memory(memory, memory_mask, drugs)
        fields = self._field_memories(encoded, batch)
        relation_dp, relation_dh, relation_ph = self._relations(fields, drugs)

        batch_size = encoded.shape[0]
        drug = drugs[None].expand(batch_size, -1, -1)
        persistence = self._persistence(batch)
        features = torch.cat(
            (
                foundation,
                relation_dp,
                relation_dh,
                relation_ph,
                drug,
                persistence,
            ),
            dim=-1,
        )
        return self.final_relational_head(features).squeeze(-1) + self.drug_bias


__all__ = [
    "ARCH_VARIANTS",
    "DIM",
    "MEDICATIONS",
    "RELATION_DIM",
    "FinalRelationalModel",
    "configure_numeric_policy",
    "objective",
    "pack_rows",
    "parameter_count",
]
