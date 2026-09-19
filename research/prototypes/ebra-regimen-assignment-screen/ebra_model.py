"""Matched FineCode proposal and medication-or-NULL assignment models."""

from __future__ import annotations

import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import torch
from torch import nn

try:
    from scipy.optimize import linear_sum_assignment as _scipy_linear_sum_assignment
except ModuleNotFoundError:  # pragma: no cover - exercised only on minimal harnesses
    _scipy_linear_sum_assignment = None

PORTFOLIO_DIR = Path(__file__).resolve().parents[1] / "evidence-access-portfolio"
if str(PORTFOLIO_DIR) not in sys.path:
    sys.path.insert(0, str(PORTFOLIO_DIR))

from portfolio_model import (  # noqa: E402
    DIM,
    MEDICATIONS,
    PortfolioModel,
    configure_numeric_policy,
    pack_rows,
    parameter_count,
)

SLOTS = MEDICATIONS


def _linear_sum_assignment(cost: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Solve a finite rectangular assignment, using SciPy when available.

    The 319 environment provides SciPy. The small fallback keeps the harness
    preflight importable without adding a dependency to the reusable package.
    """

    values = np.asarray(cost, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] > values.shape[1]:
        raise ValueError("assignment cost must be a rectangular matrix with rows <= columns")
    if not np.isfinite(values).all():
        raise ValueError("assignment cost must be finite")
    if _scipy_linear_sum_assignment is not None:
        return _scipy_linear_sum_assignment(values)

    rows, columns = values.shape
    u = np.zeros(rows + 1, dtype=np.float64)
    v = np.zeros(columns + 1, dtype=np.float64)
    matching = np.zeros(columns + 1, dtype=np.int64)
    way = np.zeros(columns + 1, dtype=np.int64)
    for row in range(1, rows + 1):
        matching[0] = row
        column_zero = 0
        minimum = np.full(columns + 1, np.inf, dtype=np.float64)
        used = np.zeros(columns + 1, dtype=bool)
        while True:
            used[column_zero] = True
            row_zero = int(matching[column_zero])
            delta = np.inf
            column_one = 0
            for column in range(1, columns + 1):
                if used[column]:
                    continue
                reduced = values[row_zero - 1, column - 1] - u[row_zero] - v[column]
                if reduced < minimum[column]:
                    minimum[column] = reduced
                    way[column] = column_zero
                if minimum[column] < delta:
                    delta = minimum[column]
                    column_one = column
            for column in range(columns + 1):
                if used[column]:
                    u[int(matching[column])] += delta
                    v[column] -= delta
                else:
                    minimum[column] -= delta
            column_zero = column_one
            if matching[column_zero] == 0:
                break
        while True:
            column_one = int(way[column_zero])
            matching[column_zero] = matching[column_one]
            column_zero = column_one
            if column_zero == 0:
                break

    assigned_columns = np.zeros(rows, dtype=np.int64)
    for column in range(1, columns + 1):
        if matching[column] != 0:
            assigned_columns[int(matching[column]) - 1] = column - 1
    return np.arange(rows, dtype=np.int64), assigned_columns


class EBRAModel(PortfolioModel):
    """Portfolio FineCode resolution followed by one shared EBRA decision block."""

    def __init__(self, diagnosis_count: int, procedure_count: int) -> None:
        super().__init__(diagnosis_count, procedure_count, "resolution_code")
        self.proposal_head = nn.Sequential(nn.Linear(3 * DIM, DIM), nn.GELU())
        self.proposal_norm = nn.LayerNorm(DIM, eps=1e-5)

        self.decision_queries = nn.Parameter(torch.empty(SLOTS, DIM))
        self.decision_norm1 = nn.LayerNorm(DIM, eps=1e-5)
        self.decision_self = nn.MultiheadAttention(DIM, 4, dropout=0.0, batch_first=True)
        self.decision_norm2 = nn.LayerNorm(DIM, eps=1e-5)
        self.decision_cross = nn.MultiheadAttention(DIM, 4, dropout=0.0, batch_first=True)
        self.decision_norm3 = nn.LayerNorm(DIM, eps=1e-5)
        self.decision_ff = nn.Sequential(
            nn.Linear(DIM, 2 * DIM), nn.GELU(), nn.Linear(2 * DIM, DIM)
        )

        self.slot_projection = nn.Linear(DIM, DIM, bias=False)
        self.medication_projection = nn.Linear(DIM, DIM, bias=False)
        self.medication_bias = nn.Parameter(torch.zeros(MEDICATIONS))
        self.null_projection = nn.Linear(DIM, 1, bias=False)
        self.null_bias = nn.Parameter(torch.zeros(()))
        self.reset_parameters()
        for attention in (self.decision_self, self.decision_cross):
            nn.init.xavier_uniform_(attention.in_proj_weight)
            nn.init.zeros_(attention.in_proj_bias)
        nn.init.normal_(self.decision_queries, mean=0.0, std=0.02)

    def initialize_prevalence(self, prevalence: torch.Tensor) -> None:
        super().initialize_prevalence(prevalence)
        with torch.no_grad():
            p = prevalence.clamp(1e-4, 1.0 - 1e-4)
            self.medication_bias.copy_(torch.log(p / (1.0 - p)))

    def proposal_bank(self, batch: Mapping[str, torch.Tensor]) -> torch.Tensor:
        """Build the shared medication-specific FineCode proposal bank."""

        encoded = self._encode(batch)
        memory, memory_mask = self._flat_evidence(encoded, batch)
        drugs = self._drugs()
        fine_context = self._read_memory(memory, memory_mask, drugs)
        persistence = self._persistence(batch)
        drug_batch = drugs.unsqueeze(0).expand(fine_context.shape[0], -1, -1)
        features = torch.cat((fine_context, drug_batch, persistence), dim=-1)
        return self.proposal_norm(self.proposal_head(features))

    def decision_scores(self, proposals: torch.Tensor) -> Mapping[str, torch.Tensor]:
        batch_size = proposals.shape[0]
        queries = self.decision_queries.unsqueeze(0).expand(batch_size, -1, -1)
        normalized = self.decision_norm1(queries)
        queries = (
            queries + self.decision_self(normalized, normalized, normalized, need_weights=False)[0]
        )
        normalized = self.decision_norm2(queries)
        queries = (
            queries + self.decision_cross(normalized, proposals, proposals, need_weights=False)[0]
        )
        queries = queries + self.decision_ff(self.decision_norm3(queries))

        slots = self.slot_projection(queries)
        medications = self.medication_projection(proposals)
        medication_logits = torch.einsum("bkd,bmd->bkm", slots, medications)
        medication_logits = medication_logits / math.sqrt(DIM) + self.medication_bias
        null_logits = self.null_projection(queries).squeeze(-1) + self.null_bias
        return {
            "medication_logits": medication_logits,
            "null_logits": null_logits,
            "proposals": proposals,
            "slots": queries,
        }

    def forward(self, batch: Mapping[str, torch.Tensor]) -> Mapping[str, torch.Tensor]:
        return self.decision_scores(self.proposal_bank(batch))


def categorical_logits(outputs: Mapping[str, torch.Tensor]) -> torch.Tensor:
    return torch.cat((outputs["medication_logits"], outputs["null_logits"].unsqueeze(-1)), dim=-1)


def fixed_multilabel_loss(
    outputs: Mapping[str, torch.Tensor], targets: torch.Tensor
) -> torch.Tensor:
    logits = outputs["medication_logits"]
    null_logits = outputs["null_logits"]
    diagonal = logits[
        :,
        torch.arange(MEDICATIONS, device=logits.device),
        torch.arange(MEDICATIONS, device=logits.device),
    ]
    return nn.functional.binary_cross_entropy_with_logits(diagonal - null_logits, targets)


def _canonical_targets(
    target: Sequence[int], medication_count: int = MEDICATIONS
) -> tuple[int, ...]:
    values = tuple(sorted({int(value) for value in target}))
    if any(value < 0 or value >= medication_count for value in values):
        raise ValueError("target medication ID is outside the declared vocabulary")
    return values


def matching_labels(
    log_probabilities: torch.Tensor, targets: Sequence[Sequence[int]]
) -> torch.Tensor:
    """Return the minimum-cost medication/NULL assignment labels."""

    if log_probabilities.ndim != 3 or log_probabilities.shape[1:] != (SLOTS, MEDICATIONS + 1):
        raise ValueError("log_probabilities must have shape [batch, slots, medications + NULL]")
    if len(targets) != log_probabilities.shape[0]:
        raise ValueError("target batch does not match log probabilities")
    labels = torch.full(
        (log_probabilities.shape[0], SLOTS),
        MEDICATIONS,
        dtype=torch.long,
        device=log_probabilities.device,
    )
    detached = log_probabilities.detach().cpu().numpy()
    for batch_index, target in enumerate(targets):
        canonical = _canonical_targets(target)
        if len(canonical) > SLOTS:
            raise ValueError("target cardinality exceeds slot capacity")
        columns = list(canonical) + [MEDICATIONS] * (SLOTS - len(canonical))
        cost = -detached[batch_index][:, columns]
        rows, assigned = _linear_sum_assignment(cost)
        for row, column in zip(rows.tolist(), assigned.tolist()):  # noqa: B905
            labels[batch_index, row] = int(columns[column])
    return labels


def assignment_loss(
    outputs: Mapping[str, torch.Tensor], targets: Sequence[Sequence[int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute the balanced matched-real plus matched-NULL objective."""

    log_probabilities = nn.functional.log_softmax(categorical_logits(outputs), dim=-1)
    labels = matching_labels(log_probabilities, targets)
    losses = []
    for batch_index in range(labels.shape[0]):
        real = labels[batch_index] != MEDICATIONS
        null = ~real
        terms = []
        if real.any():
            terms.append(-log_probabilities[batch_index, real, labels[batch_index, real]].mean())
        if null.any():
            terms.append(-log_probabilities[batch_index, null, MEDICATIONS].mean())
        losses.append(torch.stack(terms).sum())
    return torch.stack(losses).mean(), labels


def assignment_decode(
    medication_logits: np.ndarray, null_logits: np.ndarray
) -> tuple[tuple[int, ...], np.ndarray]:
    """Decode one-to-one medication assignments and continuous PRAUC scores."""

    medication = np.asarray(medication_logits, dtype=np.float64)
    null = np.asarray(null_logits, dtype=np.float64)
    if medication.shape != (SLOTS, MEDICATIONS) or null.shape != (SLOTS,):
        raise ValueError("assignment logits have an unexpected shape")
    logits = np.concatenate((medication, null[:, None]), axis=1)
    shifted = logits - logits.max(axis=1, keepdims=True)
    log_probabilities = shifted - np.log(np.exp(shifted).sum(axis=1, keepdims=True))
    cost = np.concatenate(
        (
            -log_probabilities[:, :MEDICATIONS],
            -np.repeat(log_probabilities[:, MEDICATIONS:], SLOTS, axis=1),
        ),
        axis=1,
    )
    rows, columns = _linear_sum_assignment(cost)
    selected = [
        int(column)
        for row, column in zip(rows.tolist(), columns.tolist())  # noqa: B905
        if column < MEDICATIONS
    ]
    if len(selected) != len(set(selected)):
        raise RuntimeError("assignment decoder emitted duplicate medications")
    scores = log_probabilities[:, :MEDICATIONS].max(axis=0)
    return tuple(sorted(selected)), scores


__all__ = (
    "MEDICATIONS",
    "SLOTS",
    "EBRAModel",
    "assignment_decode",
    "assignment_loss",
    "categorical_logits",
    "configure_numeric_policy",
    "fixed_multilabel_loss",
    "matching_labels",
    "pack_rows",
    "parameter_count",
)
