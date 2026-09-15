"""Bounded MICA-Core extension screen.

This module is intentionally additive.  The completed ``research/prototypes/mica``
experiment remains the source of the frozen Core implementation; this file only
adds the six explicitly requested screening lanes and the deterministic SafeSwap
decoder used by the safety lanes.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import torch
from torch import nn

try:
    from mica import (
        DIM,
        FF_DIM,
        HEADS,
        LAYERS,
        MEDICATIONS,
        THRESHOLD,
        configure_numeric_policy,
    )
    from mica import (
        MICA as BaseMICA,
    )
    from mica import (
        objective as base_objective,
    )
    from mica import (
        pack_inputs as coarse_pack_inputs,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mica"))
    from mica import (
        DIM,
        FF_DIM,
        HEADS,
        LAYERS,
        MEDICATIONS,
        THRESHOLD,
        configure_numeric_policy,
    )
    from mica import (
        MICA as BaseMICA,
    )
    from mica import (
        objective as base_objective,
    )
    from mica import (
        pack_inputs as coarse_pack_inputs,
    )


VARIANTS = (
    "core",
    "fine_history",
    "dual_evidence",
    "safe_rank",
    "self_only",
    "set_context",
)
LOGIT_THRESHOLD = math.log(THRESHOLD / (1.0 - THRESHOLD))
SAFE_RATE = 0.065
RANK_WEIGHT = 0.1


def _pack_token_lists(
    token_rows: Sequence[Sequence[tuple[list[int], int, int]]],
) -> dict[str, torch.Tensor]:
    """Pack variable-width token bags without truncating any row."""

    if not token_rows:
        raise ValueError("cannot pack an empty row collection")
    width = max(len(tokens) for tokens in token_rows)
    ids: list[int] = []
    offsets = [0]
    types: list[int] = []
    lags: list[float] = []
    masks: list[list[bool]] = []
    for tokens in token_rows:
        row_mask: list[bool] = []
        for index in range(width):
            codes, kind, lag = tokens[index] if index < len(tokens) else ([], 0, 0)
            ids.extend(codes)
            offsets.append(len(ids))
            types.append(kind)
            lags.append(float(lag))
            row_mask.append(index < len(tokens))
        masks.append(row_mask)
    return {
        "codes": torch.tensor(ids, dtype=torch.long),
        "offsets": torch.tensor(offsets, dtype=torch.long),
        "types": torch.tensor(types, dtype=torch.long),
        "lags": torch.tensor(lags, dtype=torch.float32),
        "mask": torch.tensor(masks, dtype=torch.bool),
    }


def pack_fine_history(
    rows: Sequence[dict[str, Any]], diagnosis_count: int, procedure_count: int
) -> dict[str, torch.Tensor]:
    """Pack Core current tokens and per-code tokens for every preceding visit."""

    token_rows: list[list[tuple[list[int], int, int]]] = []
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
            diagnoses = sorted(set(map(int, visit[0])))
            procedures = sorted(set(map(int, visit[1])))
            medications = sorted(set(map(int, visit[2])))
            if diagnoses:
                tokens.extend(([code], 3, lag) for code in diagnoses)
            else:
                tokens.append(([], 3, lag))
            if procedures:
                tokens.extend(([diagnosis_count + code], 4, lag) for code in procedures)
            else:
                tokens.append(([], 4, lag))
            if medications:
                tokens.extend(([med_offset + code], 5, lag) for code in medications)
            else:
                tokens.append(([], 5, lag))
        token_rows.append(tokens)
    return _pack_token_lists(token_rows)


def pack_dual_evidence(
    rows: Sequence[dict[str, Any]], diagnosis_count: int, procedure_count: int
) -> dict[str, Any]:
    """Pack separate current and coarse strictly-preceding history streams."""

    current_rows: list[list[tuple[list[int], int, int]]] = []
    history_rows: list[list[tuple[list[int], int, int]]] = []
    history_present: list[bool] = []
    med_offset = diagnosis_count + procedure_count
    for row in rows:
        current: list[tuple[list[int], int, int]] = [([], 0, 0)]
        current.extend(([int(code)], 1, 0) for code in sorted(set(row["diagnoses"])))
        current.extend(
            ([diagnosis_count + int(code)], 2, 0) for code in sorted(set(row["procedures"]))
        )
        history: list[tuple[list[int], int, int]] = [([], 0, 0)]
        visits = row["history"]
        for index, visit in enumerate(visits):
            lag = len(visits) - index
            history.append((sorted(set(map(int, visit[0]))), 3, lag))
            history.append(
                ([diagnosis_count + int(code) for code in sorted(set(visit[1]))], 4, lag)
            )
            history.append(([med_offset + int(code) for code in sorted(set(visit[2]))], 5, lag))
        current_rows.append(current)
        history_rows.append(history)
        history_present.append(bool(visits))
    return {
        "current": _pack_token_lists(current_rows),
        "history": _pack_token_lists(history_rows),
        "history_present": torch.tensor(history_present, dtype=torch.bool),
    }


class MedicationContextBlock(nn.Module):
    """One parameter-matched medication-state self-attention block."""

    def __init__(self) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(DIM, eps=1e-5)
        self.attention = nn.MultiheadAttention(DIM, HEADS, dropout=0.0, batch_first=True)
        self.norm2 = nn.LayerNorm(DIM, eps=1e-5)
        self.ff = nn.Sequential(nn.Linear(DIM, FF_DIM), nn.GELU(), nn.Linear(FF_DIM, DIM))
        mask = torch.full((MEDICATIONS, MEDICATIONS), float("-inf"))
        mask.fill_diagonal_(0.0)
        self.register_buffer("self_only_mask", mask)
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.xavier_uniform_(self.attention.in_proj_weight)
        nn.init.zeros_(self.attention.in_proj_bias)
        nn.init.xavier_uniform_(self.attention.out_proj.weight)
        nn.init.zeros_(self.attention.out_proj.bias)
        for module in self.ff:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(self, hidden: torch.Tensor, self_only: bool) -> torch.Tensor:
        normalized = self.norm1(hidden)
        attended = self.attention(
            normalized,
            normalized,
            normalized,
            attn_mask=self.self_only_mask if self_only else None,
            need_weights=False,
        )[0]
        hidden = hidden + attended
        return hidden + self.ff(self.norm2(hidden))


class MICAv2(BaseMICA):
    """MICA-Core plus the five explicitly bounded extension lanes."""

    VARIANTS = VARIANTS

    def __init__(self, diagnosis_count: int, procedure_count: int, variant: str = "core") -> None:
        if variant not in self.VARIANTS:
            raise ValueError("unknown MICA-v2 variant: " + str(variant))
        # BaseMICA's drug-query modules are the exact Core modules.  The
        # variant field is changed only after construction, so Core/FineHistory/
        # SafeRank share the original parameter names and shapes.
        super().__init__(diagnosis_count, procedure_count, "drug_query")
        self.variant = variant
        if variant == "dual_evidence":
            self.dual_gate = nn.Linear(3 * DIM, 1)
            nn.init.xavier_uniform_(self.dual_gate.weight)
            nn.init.zeros_(self.dual_gate.bias)
        if variant in {"self_only", "set_context"}:
            self.medication_context = MedicationContextBlock()

    def _drug_query_context(
        self, assembled: torch.Tensor, mask: torch.Tensor, drugs: torch.Tensor
    ) -> torch.Tensor:
        contexts: list[torch.Tensor] = []
        for start in range(0, MEDICATIONS, 16):
            selected = drugs[start : start + 16]
            expanded = assembled[:, None].expand(-1, selected.shape[0], -1, -1)
            pooled = self.read(expanded, selected, mask)
            contexts.append(self.condition_context(pooled, selected))
        return torch.cat(contexts, dim=1)

    def _predict_from_context(
        self, context: torch.Tensor, drugs: torch.Tensor, *, context_mode: str | None = None
    ) -> torch.Tensor:
        broadcast_drugs = drugs.unsqueeze(0).expand(context.shape[0], -1, -1)
        features = torch.cat((context, broadcast_drugs, context * broadcast_drugs), dim=-1)
        if context_mode is None:
            return self.head(features).squeeze(-1) + self.drug_bias
        hidden = self.head[0](features)
        hidden = self.head[1](hidden)
        hidden = self.head[2](hidden)
        hidden = self.medication_context(hidden, self_only=context_mode == "self_only")
        return self.head[3](hidden).squeeze(-1) + self.drug_bias

    def _forward_dual(self, batch: dict[str, Any]) -> torch.Tensor:
        current_batch = batch["current"]
        history_batch = batch["history"]
        current = self.assemble(self.encode_tokens(current_batch), current_batch["mask"])
        history = self.assemble(self.encode_tokens(history_batch), history_batch["mask"])
        drugs = self.drug_norm(self.codes.weight[self.med_offset :])
        current_context = self._drug_query_context(current, current_batch["mask"], drugs)
        history_context = self._drug_query_context(history, history_batch["mask"], drugs)
        present = batch["history_present"].to(dtype=torch.bool)
        history_context = history_context * present[:, None, None].to(history_context.dtype)
        broadcast_drugs = drugs.unsqueeze(0).expand(current_context.shape[0], -1, -1)
        gate_input = torch.cat((current_context, history_context, broadcast_drugs), dim=-1)
        gate = self.dual_gate(gate_input).sigmoid()
        gate = torch.where(present[:, None, None], gate, torch.ones_like(gate))
        context = gate * current_context + (1.0 - gate) * history_context
        return self._predict_from_context(context, drugs)

    def forward(self, batch: dict[str, Any]) -> torch.Tensor:
        if self.variant == "core":
            # Keep the anchor byte-for-byte on the original MICA computation
            # path rather than reproducing it in a second implementation.
            self.variant = "drug_query"
            try:
                return super().forward(batch)
            finally:
                self.variant = "core"
        if self.variant == "dual_evidence":
            return self._forward_dual(batch)
        x = self.encode_tokens(batch)
        assembled = self.assemble(x, batch["mask"])
        drugs = self.drug_norm(self.codes.weight[self.med_offset :])
        context = self._drug_query_context(assembled, batch["mask"], drugs)
        if self.variant in {"self_only", "set_context"}:
            return self._predict_from_context(context, drugs, context_mode=self.variant)
        return self._predict_from_context(context, drugs)


def _ddi_pair_count(selected: Iterable[int], ddi: Sequence[Sequence[float]]) -> int:
    ordered = sorted(int(index) for index in selected)
    return sum(
        int(bool(ddi[left][right]))
        for offset, left in enumerate(ordered)
        for right in ordered[offset + 1 :]
    )


def _logit_values(logits: Sequence[float] | torch.Tensor) -> list[float]:
    if isinstance(logits, torch.Tensor):
        return [float(value) for value in logits.detach().cpu().flatten().tolist()]
    return [float(value) for value in logits]


def safe_swap(
    logits: Sequence[float] | torch.Tensor,
    ddi: Sequence[Sequence[float]],
    safety_rate: float = SAFE_RATE,
) -> tuple[int, ...]:
    """Deterministic cardinality-preserving safe-set decoder."""

    values = _logit_values(logits)
    n = len(values)
    if n != MEDICATIONS:
        raise ValueError("SafeSwap requires exactly 131 logits")
    k = sum(value >= LOGIT_THRESHOLD for value in values)
    if k == 0:
        return ()
    selected = set(sorted(range(n), key=lambda index: (-values[index], index))[:k])
    budget = math.floor(float(safety_rate) * k * (k - 1) / 2.0)

    while _ddi_pair_count(selected, ddi) > budget:
        current_count = _ddi_pair_count(selected, ddi)
        candidates: list[tuple[float, tuple[int, ...], int, int, set[int]]] = []
        for outgoing in sorted(selected):
            for incoming in range(n):
                if incoming in selected:
                    continue
                proposal = set(selected)
                proposal.remove(outgoing)
                proposal.add(incoming)
                new_count = _ddi_pair_count(proposal, ddi)
                if new_count < current_count:
                    new_sum = sum(values[index] for index in proposal)
                    candidates.append(
                        (-new_sum, tuple(sorted(proposal)), outgoing, incoming, proposal)
                    )
        if not candidates:
            break
        selected = min(candidates)[-1]

    while True:
        current_count = _ddi_pair_count(selected, ddi)
        if current_count > budget:
            break
        current_sum = sum(values[index] for index in selected)
        candidates = []
        for outgoing in sorted(selected):
            for incoming in range(n):
                if incoming in selected:
                    continue
                proposal = set(selected)
                proposal.remove(outgoing)
                proposal.add(incoming)
                if _ddi_pair_count(proposal, ddi) <= budget:
                    gain = sum(values[index] for index in proposal) - current_sum
                    if gain > 0.0:
                        candidates.append(
                            (-gain, tuple(sorted(proposal)), outgoing, incoming, proposal)
                        )
        if not candidates:
            break
        selected = min(candidates)[-1]
    return tuple(sorted(selected))


def _set_quality(
    selected: Iterable[int], target: Iterable[int], ddi: Sequence[Sequence[float]]
) -> float:
    selected_set = frozenset(int(index) for index in selected)
    target_set = frozenset(int(index) for index in target)
    union = selected_set | target_set
    jaccard = 1.0 if not union else len(selected_set & target_set) / len(union)
    k = len(selected_set)
    pair_total = k * (k - 1) / 2
    ddi_rate = 0.0 if pair_total == 0 else _ddi_pair_count(selected_set, ddi) / pair_total
    return jaccard - max(0.0, ddi_rate - SAFE_RATE)


def _set_score(logit_row: torch.Tensor, selected: Iterable[int]) -> torch.Tensor:
    mask = torch.zeros_like(logit_row, dtype=torch.bool)
    selected_list = list(selected)
    if selected_list:
        mask[selected_list] = True
    return torch.where(
        mask, nn.functional.logsigmoid(logit_row), nn.functional.logsigmoid(-logit_row)
    ).mean()


def safe_rank_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    ddi: Sequence[Sequence[float]],
) -> torch.Tensor:
    """Construct detached candidate sets and rank them with current logits."""

    losses: list[torch.Tensor] = []
    detached = logits.detach().cpu()
    for row_index in range(logits.shape[0]):
        detached_row = detached[row_index]
        target_set = frozenset(
            int(index)
            for index, value in enumerate(targets[row_index].detach().cpu())
            if float(value) > 0.5
        )
        base_set = frozenset(
            int(index)
            for index, value in enumerate(detached_row.tolist())
            if float(value) >= LOGIT_THRESHOLD
        )
        safe_set = frozenset(safe_swap(detached_row.tolist(), ddi))
        candidates: list[frozenset[int]] = []
        for candidate in (target_set, base_set, safe_set):
            if candidate not in candidates:
                candidates.append(candidate)
        qualities = [_set_quality(candidate, target_set, ddi) for candidate in candidates]
        for left, left_quality in enumerate(qualities):
            for right, right_quality in enumerate(qualities):
                if left_quality > right_quality:
                    difference = _set_score(logits[row_index], candidates[left]) - _set_score(
                        logits[row_index], candidates[right]
                    )
                    losses.append(nn.functional.softplus(-difference))
    if not losses:
        return logits.sum() * 0.0
    return torch.stack(losses).mean()


def safe_rank_objective(
    logits: torch.Tensor,
    targets: torch.Tensor,
    ddi: torch.Tensor,
    ddi_rows: Sequence[Sequence[float]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    base, bce, ddi_loss = base_objective(logits, targets, ddi)
    rank = safe_rank_loss(logits, targets, ddi_rows)
    return base + RANK_WEIGHT * rank, bce, ddi_loss, rank


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


__all__ = [
    "DIM",
    "FF_DIM",
    "HEADS",
    "LAYERS",
    "MEDICATIONS",
    "RANK_WEIGHT",
    "SAFE_RATE",
    "THRESHOLD",
    "VARIANTS",
    "MICAv2",
    "base_objective",
    "coarse_pack_inputs",
    "configure_numeric_policy",
    "pack_dual_evidence",
    "pack_fine_history",
    "parameter_count",
    "safe_rank_loss",
    "safe_rank_objective",
    "safe_swap",
]
