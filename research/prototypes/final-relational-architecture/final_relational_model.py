"""Paper-intended relational architecture search on the stable FineCode substrate."""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

import torch
from torch import nn
from torch.utils.checkpoint import checkpoint

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

RELATION_DIM = DIM
RELATION_CHUNK = 1

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


class EdgeScoreFunction(torch.autograd.Function):
    @staticmethod
    def forward(
        ctx,
        eq: torch.Tensor,
        left_lag: torch.Tensor,
        right_lag: torch.Tensor,
        type_idx: int,
        temporal: bool,
    ) -> torch.Tensor:
        ctx.save_for_backward(eq, left_lag, right_lag)
        ctx.type_idx = type_idx
        ctx.temporal = temporal

        sqrt_7 = math.sqrt(7.0)
        c_type = eq[:, type_idx : type_idx + 1] / sqrt_7
        b, i = left_lag.shape
        j = right_lag.shape[1]

        score = c_type.unsqueeze(-1).expand(b, eq.shape[0], i, j).clone()
        if temporal:
            c3 = eq[:, 3 : 4].unsqueeze(-1) / sqrt_7
            c4 = eq[:, 4 : 5].unsqueeze(-1) / sqrt_7
            c5 = eq[:, 5 : 6].unsqueeze(-1) / sqrt_7
            c6 = eq[:, 6 : 7].unsqueeze(-1) / sqrt_7

            left = left_lag[:, :, None]
            right = right_lag[:, None, :]

            diff = left - right
            same_visit = (diff == 0).to(left_lag.dtype).unsqueeze(1)
            score = score + c3 * same_visit
            del same_visit

            cur_hist = torch.logical_xor(left == 0, right == 0).to(left_lag.dtype).unsqueeze(1)
            score = score + c4 * cur_hist
            del cur_hist

            both_hist = ((left > 0) & (right > 0)).to(left_lag.dtype).unsqueeze(1)
            score = score + c5 * both_hist
            del both_hist

            lag_gap = torch.log1p(diff.abs()).unsqueeze(1)
            score = score + c6 * lag_gap
            del lag_gap

        return score

    @staticmethod
    def backward(
        ctx, grad_output: torch.Tensor
    ) -> Tuple[
        torch.Tensor,
        Optional[torch.Tensor],
        Optional[torch.Tensor],
        Optional[torch.Tensor],
        Optional[torch.Tensor],
    ]:
        eq, left_lag, right_lag = ctx.saved_tensors
        sqrt_7 = math.sqrt(7.0)
        grad_eq = torch.zeros_like(eq)

        grad_eq[:, ctx.type_idx] = grad_output.sum(dim=(0, 2, 3)) / sqrt_7

        if ctx.temporal:
            left = left_lag[:, :, None]
            right = right_lag[:, None, :]
            diff = left - right

            same_visit = (diff == 0).to(grad_output.dtype).unsqueeze(1)
            grad_eq[:, 3] = (grad_output * same_visit).sum(dim=(0, 2, 3)) / sqrt_7
            del same_visit

            cur_hist = torch.logical_xor(left == 0, right == 0).to(grad_output.dtype).unsqueeze(1)
            grad_eq[:, 4] = (grad_output * cur_hist).sum(dim=(0, 2, 3)) / sqrt_7
            del cur_hist

            both_hist = ((left > 0) & (right > 0)).to(grad_output.dtype).unsqueeze(1)
            grad_eq[:, 5] = (grad_output * both_hist).sum(dim=(0, 2, 3)) / sqrt_7
            del both_hist

            lag_gap = torch.log1p(diff.abs()).unsqueeze(1)
            grad_eq[:, 6] = (grad_output * lag_gap).sum(dim=(0, 2, 3)) / sqrt_7
            del lag_gap

        return grad_eq, None, None, None, None


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
        Optional[torch.Tensor],
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

        def _chunk_fn(q, lk, rk, lv, rv, pm):
            s = torch.einsum("mr,bir,bjr->bmij", q, lk, rk) / scale
            b, m, i, j = s.shape
            fs = s.reshape(b, m, i * j)
            fm = pm.reshape(b, 1, i * j).expand(-1, m, -1)
            w = _masked_softmax(fs, fm, dim=-1).reshape(b, m, i, j)
            temp = torch.matmul(w, rv.unsqueeze(1))
            return torch.sum(lv.unsqueeze(1) * temp, dim=2)

        for start in range(0, MEDICATIONS, RELATION_CHUNK):
            q = q_all[start : start + RELATION_CHUNK]
            if self.training:
                chunk_out = checkpoint(
                    _chunk_fn,
                    q,
                    left_key,
                    right_key,
                    left_value,
                    right_value,
                    pair_mask,
                )
            else:
                chunk_out = _chunk_fn(
                    q, left_key, right_key, left_value, right_value, pair_mask
                )
            outputs.append(chunk_out)
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
                edge_mode="none",
                relation_type_index=type_index,
            )
            for type_index, (left, right) in enumerate(relation_types)
        ]
        q_all = self._relation_query(drugs)
        edge_q_all = self.edge_query(drugs)
        scale = math.sqrt(RELATION_DIM)

        left_keys = [c[0] for c in components]
        right_keys = [c[1] for c in components]
        left_values = [c[2] for c in components]
        right_values = [c[3] for c in components]
        pair_masks = [c[4] for c in components]

        lags = [
            (fields[left][2], fields[right][2])
            for left, right in relation_types
        ]

        def _chunk_joint_fn(
            q,
            eq,
            lk0,
            lk1,
            lk2,
            rk0,
            rk1,
            rk2,
            lv0,
            lv1,
            lv2,
            rv0,
            rv1,
            rv2,
            pm0,
            pm1,
            pm2,
            l_lag0,
            r_lag0,
            l_lag1,
            r_lag1,
            l_lag2,
            r_lag2,
        ):
            lks = [lk0, lk1, lk2]
            rks = [rk0, rk1, rk2]
            lvs = [lv0, lv1, lv2]
            rvs = [rv0, rv1, rv2]
            pms = [pm0, pm1, pm2]
            l_lags = [l_lag0, l_lag1, l_lag2]
            r_lags = [r_lag0, r_lag1, r_lag2]

            flat_scores = []
            shapes = []
            for t in range(3):
                s = torch.einsum("mr,bir,bjr->bmij", q, lks[t], rks[t]) / scale
                pc = pms[t].sum(dim=(1, 2)).clamp_min(1).to(s.dtype)
                s = s - pc.log()[:, None, None, None]
                if edge_mode in {"type_only", "temporal"}:
                    edge_score = EdgeScoreFunction.apply(
                        eq, l_lags[t], r_lags[t], t, edge_mode == "temporal"
                    )
                    s = s + edge_score
                b, m, i, j = s.shape
                shapes.append((i, j))
                flat_scores.append(s.reshape(b, m, i * j))

            all_scores = torch.cat(flat_scores, dim=-1)
            flat_masks = [
                pms[t].reshape(b, 1, shapes[t][0] * shapes[t][1]).expand(-1, m, -1)
                for t in range(3)
            ]
            all_mask = torch.cat(flat_masks, dim=-1)
            all_weights = _masked_softmax(all_scores, all_mask, dim=-1)

            out_types = []
            offset = 0
            for t in range(3):
                i, j = shapes[t]
                length = i * j
                w = all_weights[:, :, offset : offset + length].reshape(
                    all_weights.shape[0], q.shape[0], i, j
                )
                temp = torch.matmul(w, rvs[t].unsqueeze(1))
                out_types.append(torch.sum(lvs[t].unsqueeze(1) * temp, dim=2))
                offset += length
            return torch.stack(out_types, dim=0)

        outputs_by_type = [[], [], []]
        for start in range(0, MEDICATIONS, RELATION_CHUNK):
            q = q_all[start : start + RELATION_CHUNK]
            eq = edge_q_all[start : start + RELATION_CHUNK]
            args = (
                q,
                eq,
                left_keys[0],
                left_keys[1],
                left_keys[2],
                right_keys[0],
                right_keys[1],
                right_keys[2],
                left_values[0],
                left_values[1],
                left_values[2],
                right_values[0],
                right_values[1],
                right_values[2],
                pair_masks[0],
                pair_masks[1],
                pair_masks[2],
                lags[0][0],
                lags[0][1],
                lags[1][0],
                lags[1][1],
                lags[2][0],
                lags[2][1],
            )
            if self.training:
                stacked = checkpoint(_chunk_joint_fn, *args)
            else:
                stacked = _chunk_joint_fn(*args)
            for t in range(3):
                outputs_by_type[t].append(stacked[t])

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
