"""Architecture portfolio for bounded medication-recommendation mechanism screens.

Four matched pairs probe orthogonal bottlenecks between EHR evidence and a
candidate medication decision:

- temporal_shared vs temporal_med: medication identity after vs before temporal compression.
- resolution_visit vs resolution_code: candidate read after visit pooling vs at code resolution.
- depth_state vs depth_reread: state-only refinement vs repeated evidence access.
- prediction_aggregate vs prediction_local: pooled context prediction vs direct local evidence potentials.

The model is target-free at inference. Current-visit medications never enter inputs.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import torch
from torch import nn

MEDICATIONS = 131
DIM = 128
HEADS = 4
FF_DIM = 256
CLINICAL_LAYERS = 2
CHUNK = 16
DDI_WEIGHT = 0.05

VARIANTS = (
    "temporal_shared",
    "temporal_med",
    "resolution_visit",
    "resolution_code",
    "depth_state",
    "depth_reread",
    "prediction_aggregate",
    "prediction_local",
)

PAIR_MAP = {
    "temporal": ("temporal_shared", "temporal_med"),
    "resolution": ("resolution_visit", "resolution_code"),
    "depth": ("depth_state", "depth_reread"),
    "prediction": ("prediction_aggregate", "prediction_local"),
}


def configure_numeric_policy() -> Dict[str, Any]:
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


def _dedup(values: Sequence[int]) -> List[int]:
    return sorted(set(int(value) for value in values))


def pack_rows(
    rows: Sequence[Mapping[str, Any]], diagnosis_count: int, procedure_count: int
) -> Dict[str, torch.Tensor]:
    """Pack strictly previous D/P/M visits plus current D/P into visit/code tensors.

    Every real visit receives a learned contextual anchor token. Padded visits also
    receive that anchor so within-visit self-attention never sees an all-masked row;
    `visit_mask` excludes padded visits from all downstream reads.
    """
    if not rows:
        raise ValueError("cannot pack an empty batch")
    med_offset = diagnosis_count + procedure_count
    special_id = med_offset + MEDICATIONS

    encoded_rows: List[List[List[Tuple[int, int, int]]]] = []
    current_indices: List[int] = []
    persistence_rows: List[List[List[float]]] = []
    max_visits = 1
    max_tokens = 1

    for row in rows:
        history = list(row["history"])
        visits: List[List[Tuple[int, int, int]]] = []
        total_visits = len(history) + 1
        for history_index, visit in enumerate(history):
            lag = len(history) - history_index
            tokens: List[Tuple[int, int, int]] = [(special_id, 0, lag)]
            tokens.extend((code, 1, lag) for code in _dedup(visit[0]))
            tokens.extend(
                (diagnosis_count + code, 2, lag) for code in _dedup(visit[1])
            )
            tokens.extend((med_offset + code, 3, lag) for code in _dedup(visit[2]))
            visits.append(tokens)
            max_tokens = max(max_tokens, len(tokens))

        current: List[Tuple[int, int, int]] = [(special_id, 0, 0)]
        current.extend((code, 1, 0) for code in _dedup(row["diagnoses"]))
        current.extend(
            (diagnosis_count + code, 2, 0) for code in _dedup(row["procedures"])
        )
        visits.append(current)
        max_tokens = max(max_tokens, len(current))
        max_visits = max(max_visits, total_visits)
        current_indices.append(len(history))
        encoded_rows.append(visits)

        med_sets = [set(_dedup(visit[2])) for visit in history]
        per_med: List[List[float]] = []
        h = len(med_sets)
        for med in range(MEDICATIONS):
            if h == 0:
                per_med.append([0.0, 0.0, 0.0])
                continue
            hits = [index for index, meds in enumerate(med_sets) if med in meds]
            last = 1.0 if med in med_sets[-1] else 0.0
            freq = float(len(hits)) / float(h)
            if hits:
                visits_since = h - 1 - hits[-1]
                recency = 1.0 / float(1 + visits_since)
            else:
                recency = 0.0
            per_med.append([last, freq, recency])
        persistence_rows.append(per_med)

    batch = len(rows)
    codes = torch.full((batch, max_visits, max_tokens), special_id, dtype=torch.long)
    types = torch.zeros((batch, max_visits, max_tokens), dtype=torch.long)
    lags = torch.zeros((batch, max_visits, max_tokens), dtype=torch.float32)
    token_mask = torch.zeros((batch, max_visits, max_tokens), dtype=torch.bool)
    visit_mask = torch.zeros((batch, max_visits), dtype=torch.bool)

    # Padded visits keep exactly one valid special token for numerically stable MHA.
    token_mask[:, :, 0] = True
    for row_index, visits in enumerate(encoded_rows):
        for visit_index, tokens in enumerate(visits):
            visit_mask[row_index, visit_index] = True
            for token_index, (code, kind, lag) in enumerate(tokens):
                codes[row_index, visit_index, token_index] = int(code)
                types[row_index, visit_index, token_index] = int(kind)
                lags[row_index, visit_index, token_index] = float(lag)
                token_mask[row_index, visit_index, token_index] = True

    return {
        "codes": codes,
        "types": types,
        "lags": lags,
        "token_mask": token_mask,
        "visit_mask": visit_mask,
        "current_index": torch.tensor(current_indices, dtype=torch.long),
        "persistence": torch.tensor(persistence_rows, dtype=torch.float32),
    }


class ClinicalBlock(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(DIM, eps=1e-5)
        self.attention = nn.MultiheadAttention(DIM, HEADS, dropout=0.0, batch_first=True)
        self.norm2 = nn.LayerNorm(DIM, eps=1e-5)
        self.ff = nn.Sequential(nn.Linear(DIM, FF_DIM), nn.GELU(), nn.Linear(FF_DIM, DIM))

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        normalized = self.norm1(x)
        attended = self.attention(
            normalized, normalized, normalized, key_padding_mask=~mask, need_weights=False
        )[0]
        x = x + attended
        return x + self.ff(self.norm2(x))


class CrossHop(nn.Module):
    """One medication-state update from an evidence memory."""

    def __init__(self) -> None:
        super().__init__()
        self.state_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.mem_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.query = nn.Linear(DIM, DIM, bias=False)
        self.key = nn.Linear(DIM, DIM, bias=False)
        self.value = nn.Linear(DIM, DIM, bias=False)
        self.ff = nn.Sequential(nn.Linear(DIM, FF_DIM), nn.GELU(), nn.Linear(FF_DIM, DIM))
        self.out_norm = nn.LayerNorm(DIM, eps=1e-5)

    def forward(
        self, state: torch.Tensor, memory: torch.Tensor, memory_mask: torch.Tensor
    ) -> torch.Tensor:
        # state: [B,M,D], memory: [B,N,D], mask: [B,N]
        normalized_state = self.state_norm(state)
        normalized_memory = self.mem_norm(memory)
        keys = self.key(normalized_memory)
        values = self.value(normalized_memory)
        chunks: List[torch.Tensor] = []
        for start in range(0, state.shape[1], CHUNK):
            q = self.query(normalized_state[:, start : start + CHUNK])
            scores = torch.einsum("bmd,bnd->bmn", q, keys) / math.sqrt(DIM)
            scores = scores.masked_fill(~memory_mask[:, None, :], float("-inf"))
            weights = torch.softmax(scores, dim=-1)
            chunks.append(torch.einsum("bmn,bnd->bmd", weights, values))
        context = torch.cat(chunks, dim=1)
        return self.out_norm(state + self.ff(context))


class PortfolioModel(nn.Module):
    def __init__(self, diagnosis_count: int, procedure_count: int, variant: str) -> None:
        super().__init__()
        if variant not in VARIANTS:
            raise ValueError("unknown portfolio variant: " + str(variant))
        self.variant = variant
        self.med_offset = diagnosis_count + procedure_count
        self.total_codes = self.med_offset + MEDICATIONS + 1
        self.special_id = self.total_codes - 1

        self.codes = nn.Embedding(self.total_codes, DIM)
        self.types = nn.Embedding(4, DIM)
        self.token_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.input_dropout = nn.Dropout(0.1)
        self.blocks = nn.ModuleList([ClinicalBlock() for _ in range(CLINICAL_LAYERS)])
        self.final_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.drug_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.read_norm = nn.LayerNorm(DIM, eps=1e-5)
        self.read_query = nn.Linear(DIM, DIM, bias=False)
        self.read_key = nn.Linear(DIM, DIM, bias=False)
        self.read_value = nn.Linear(DIM, DIM, bias=False)
        self.visit_query = nn.Parameter(torch.empty(DIM))

        self.temporal_cell = nn.GRUCell(DIM, DIM)
        self.persistence_proj = nn.Sequential(nn.Linear(3, DIM), nn.GELU())
        self.pair_head = nn.Sequential(
            nn.Linear(4 * DIM, DIM), nn.GELU(), nn.Dropout(0.1), nn.Linear(DIM, 1)
        )
        self.single_head = nn.Sequential(
            nn.Linear(3 * DIM, DIM), nn.GELU(), nn.Dropout(0.1), nn.Linear(DIM, 1)
        )

        self.hops = nn.ModuleList([CrossHop(), CrossHop()])

        self.local_q = nn.Linear(DIM, DIM, bias=False)
        self.local_k = nn.Linear(DIM, DIM, bias=False)
        self.local_hidden = nn.Sequential(nn.Linear(DIM, DIM), nn.GELU())
        self.local_out = nn.Linear(DIM, 1)
        self.local_bias = nn.Sequential(nn.Linear(2 * DIM, DIM), nn.GELU(), nn.Linear(DIM, 1))

        self.drug_bias = nn.Parameter(torch.zeros(MEDICATIONS))
        self.register_buffer(
            "lag_frequency", torch.exp(torch.arange(0, DIM, 2) * (-math.log(10000.0) / DIM))
        )
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            elif isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
        for block in self.blocks:
            nn.init.xavier_uniform_(block.attention.in_proj_weight)
            nn.init.zeros_(block.attention.in_proj_bias)
        nn.init.normal_(self.visit_query, mean=0.0, std=0.02)

    def initialize_prevalence(self, prevalence: torch.Tensor) -> None:
        with torch.no_grad():
            p = prevalence.clamp(1e-4, 1.0 - 1e-4)
            self.drug_bias.copy_(torch.log(p / (1.0 - p)))

    def _encode(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        lag_angle = batch["lags"].unsqueeze(-1) * self.lag_frequency
        positions = torch.stack((lag_angle.sin(), lag_angle.cos()), dim=-1).flatten(-2)
        x = self.token_norm(self.codes(batch["codes"]) + self.types(batch["types"])) + positions
        x = self.input_dropout(x)
        b, v, k, d = x.shape
        flat = x.reshape(b * v, k, d)
        mask = batch["token_mask"].reshape(b * v, k)
        for block in self.blocks:
            flat = block(flat, mask)
        flat = self.final_norm(flat)
        return flat.reshape(b, v, k, d)

    def _drugs(self) -> torch.Tensor:
        return self.drug_norm(self.codes.weight[self.med_offset : self.med_offset + MEDICATIONS])

    def _read_memory(
        self, memory: torch.Tensor, mask: torch.Tensor, drugs: torch.Tensor
    ) -> torch.Tensor:
        normalized = self.read_norm(memory)
        keys = self.read_key(normalized)
        values = self.read_value(normalized)
        outputs: List[torch.Tensor] = []
        for start in range(0, MEDICATIONS, CHUNK):
            selected = drugs[start : start + CHUNK]
            q = self.read_query(selected)
            scores = torch.einsum("md,bnd->bmn", q, keys) / math.sqrt(DIM)
            scores = scores.masked_fill(~mask[:, None, :], float("-inf"))
            weights = torch.softmax(scores, dim=-1)
            outputs.append(torch.einsum("bmn,bnd->bmd", weights, values))
        return torch.cat(outputs, dim=1)

    def _read_each_visit(
        self, encoded: torch.Tensor, batch: Mapping[str, torch.Tensor], drugs: torch.Tensor
    ) -> torch.Tensor:
        b, v, k, d = encoded.shape
        memory = encoded.reshape(b * v, k, d)
        mask = batch["token_mask"].reshape(b * v, k)
        contexts = self._read_memory(memory, mask, drugs)
        return contexts.reshape(b, v, MEDICATIONS, d).permute(0, 2, 1, 3).contiguous()

    def _shared_visit_pool(
        self, encoded: torch.Tensor, batch: Mapping[str, torch.Tensor]
    ) -> torch.Tensor:
        b, v, k, d = encoded.shape
        memory = self.read_norm(encoded.reshape(b * v, k, d))
        mask = batch["token_mask"].reshape(b * v, k)
        q = self.read_query(torch.nn.functional.normalize(self.visit_query, dim=0))
        scores = torch.einsum("d,bkd->bk", q, self.read_key(memory)) / math.sqrt(DIM)
        scores = scores.masked_fill(~mask, float("-inf"))
        weights = torch.softmax(scores, dim=-1)
        pooled = torch.einsum("bk,bkd->bd", weights, self.read_value(memory))
        return pooled.reshape(b, v, d)

    @staticmethod
    def _gather_current(contexts: torch.Tensor, current_index: torch.Tensor) -> torch.Tensor:
        b, m, _v, d = contexts.shape
        index = current_index[:, None, None, None].expand(b, m, 1, d)
        return contexts.gather(2, index).squeeze(2)

    def _history_shared(
        self, visits: torch.Tensor, batch: Mapping[str, torch.Tensor]
    ) -> torch.Tensor:
        b, v, _d = visits.shape
        h = torch.zeros(b, DIM, dtype=visits.dtype, device=visits.device)
        positions = torch.arange(v, device=visits.device)[None, :]
        hist_mask = batch["visit_mask"] & (positions < batch["current_index"][:, None])
        for step in range(v):
            new_h = self.temporal_cell(visits[:, step], h)
            h = torch.where(hist_mask[:, step, None], new_h, h)
        return h

    def _history_med(
        self, contexts: torch.Tensor, batch: Mapping[str, torch.Tensor]
    ) -> torch.Tensor:
        b, m, v, d = contexts.shape
        h = torch.zeros(b * m, d, dtype=contexts.dtype, device=contexts.device)
        positions = torch.arange(v, device=contexts.device)[None, :]
        hist_mask = batch["visit_mask"] & (positions < batch["current_index"][:, None])
        for step in range(v):
            x = contexts[:, :, step].reshape(b * m, d)
            new_h = self.temporal_cell(x, h)
            mask = hist_mask[:, step, None].expand(b, m).reshape(b * m, 1)
            h = torch.where(mask, new_h, h)
        return h.reshape(b, m, d)

    def _persistence(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        return self.persistence_proj(batch["persistence"])

    def _pair_score(
        self,
        primary: torch.Tensor,
        secondary: torch.Tensor,
        drugs: torch.Tensor,
        persistence: torch.Tensor,
    ) -> torch.Tensor:
        b = primary.shape[0]
        drug = drugs.unsqueeze(0).expand(b, -1, -1)
        features = torch.cat((primary, secondary, drug, persistence), dim=-1)
        return self.pair_head(features).squeeze(-1) + self.drug_bias

    def _single_score(
        self, context: torch.Tensor, drugs: torch.Tensor, persistence: torch.Tensor
    ) -> torch.Tensor:
        b = context.shape[0]
        drug = drugs.unsqueeze(0).expand(b, -1, -1)
        features = torch.cat((context, drug, persistence), dim=-1)
        return self.single_head(features).squeeze(-1) + self.drug_bias

    def _flat_evidence(
        self, encoded: torch.Tensor, batch: Mapping[str, torch.Tensor]
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        b, v, k, d = encoded.shape
        mask = batch["token_mask"] & batch["visit_mask"][:, :, None]
        return encoded.reshape(b, v * k, d), mask.reshape(b, v * k)

    def _forward_temporal(
        self, encoded: torch.Tensor, batch: Mapping[str, torch.Tensor], drugs: torch.Tensor
    ) -> torch.Tensor:
        each_visit = self._read_each_visit(encoded, batch, drugs)
        current = self._gather_current(each_visit, batch["current_index"])
        persistence = self._persistence(batch)
        if self.variant == "temporal_med":
            history = self._history_med(each_visit, batch)
        else:
            visits = self._shared_visit_pool(encoded, batch)
            shared = self._history_shared(visits, batch)
            history = shared[:, None, :].expand(-1, MEDICATIONS, -1)
        return self._pair_score(current, history, drugs, persistence)

    def _forward_resolution(
        self, encoded: torch.Tensor, batch: Mapping[str, torch.Tensor], drugs: torch.Tensor
    ) -> torch.Tensor:
        persistence = self._persistence(batch)
        if self.variant == "resolution_code":
            memory, mask = self._flat_evidence(encoded, batch)
            context = self._read_memory(memory, mask, drugs)
        else:
            visits = self._shared_visit_pool(encoded, batch)
            context = self._read_memory(visits, batch["visit_mask"], drugs)
        return self._single_score(context, drugs, persistence)

    def _forward_depth(
        self, encoded: torch.Tensor, batch: Mapping[str, torch.Tensor], drugs: torch.Tensor
    ) -> torch.Tensor:
        memory, mask = self._flat_evidence(encoded, batch)
        first = self._read_memory(memory, mask, drugs)
        state = torch.nn.functional.layer_norm(drugs[None] + first, (DIM,))
        if self.variant == "depth_reread":
            for hop in self.hops:
                state = hop(state, memory, mask)
        else:
            frozen_memory = first
            one_mask = torch.ones(first.shape[0], 1, dtype=torch.bool, device=first.device)
            b, m, d = state.shape
            state_flat = state.reshape(b * m, 1, d)
            mem_flat = frozen_memory.reshape(b * m, 1, d)
            for hop in self.hops:
                state_flat = hop(
                    state_flat.reshape(b * m, 1, d),
                    mem_flat,
                    one_mask.repeat_interleave(m, 0),
                )
            state = state_flat.reshape(b, m, d)
        return self._single_score(state, drugs, self._persistence(batch))

    def _forward_direct(
        self, encoded: torch.Tensor, batch: Mapping[str, torch.Tensor], drugs: torch.Tensor
    ) -> torch.Tensor:
        memory, mask = self._flat_evidence(encoded, batch)
        persistence = self._persistence(batch)
        normalized = self.read_norm(memory)
        keys = self.local_k(normalized)
        bias_features = torch.cat(
            (drugs[None].expand(memory.shape[0], -1, -1), persistence), dim=-1
        )
        base = self.local_bias(bias_features).squeeze(-1) + self.drug_bias
        outputs: List[torch.Tensor] = []
        valid_count = mask.sum(dim=-1).clamp_min(1).to(memory.dtype)
        for start in range(0, MEDICATIONS, CHUNK):
            selected = drugs[start : start + CHUNK]
            q = self.local_q(selected)
            interaction = q[None, :, None, :] * keys[:, None, :, :]
            hidden = self.local_hidden(interaction)
            if self.variant == "prediction_local":
                local = self.local_out(hidden).squeeze(-1)
                local = local.masked_fill(~mask[:, None, :], float("-inf"))
                score = torch.logsumexp(local, dim=-1) - valid_count.log()[:, None]
            else:
                weights = mask[:, None, :, None].to(hidden.dtype)
                pooled = (hidden * weights).sum(dim=2) / valid_count[:, None, None]
                score = self.local_out(pooled).squeeze(-1)
            outputs.append(score)
        return torch.cat(outputs, dim=1) + base

    def forward(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        encoded = self._encode(batch)
        drugs = self._drugs()
        if self.variant.startswith("temporal_"):
            return self._forward_temporal(encoded, batch, drugs)
        if self.variant.startswith("resolution_"):
            return self._forward_resolution(encoded, batch, drugs)
        if self.variant.startswith("depth_"):
            return self._forward_depth(encoded, batch, drugs)
        return self._forward_direct(encoded, batch, drugs)


def objective(
    logits: torch.Tensor, targets: torch.Tensor, ddi: torch.Tensor
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    bce = nn.functional.binary_cross_entropy_with_logits(logits, targets)
    probabilities = logits.sigmoid()
    ddi_loss = (
        torch.einsum(
            "bi,ij,bj->b", probabilities, torch.triu(ddi, diagonal=1), probabilities
        ).mean()
        / MEDICATIONS
    )
    return bce + DDI_WEIGHT * ddi_loss, bce, ddi_loss


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())
