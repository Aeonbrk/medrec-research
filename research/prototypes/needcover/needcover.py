"""NeedCover: regimen-conditioned residual clinical-need reasoning.

This module is a throwaway pre-Idea prototype.  It deliberately keeps the
research contribution narrow: explicit current diagnosis problem nodes send a
first message to medication states, one relation-aware medication interaction
layer produces a provisional regimen, and the resulting problem coverage is
used only to reweight a second problem-to-medication message.

The implementation does not import HypeMed, does not use current-visit
medications as features, and keeps the 131-candidate vocabulary fixed.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

CANDIDATE_COUNT = 131
DEFAULT_DIAGNOSIS_HASH_WIDTH = 2048
DEFAULT_PROCEDURE_HASH_WIDTH = 512
DEFAULT_HISTORY_LENGTH = 4
DEFAULT_HIDDEN_DIM = 96
DEFAULT_THRESHOLD = 0.0
DEFAULT_PROVISIONAL_WEIGHT = 0.3

VARIANTS = ("problem_drug", "static_two_pass", "needcover")

try:  # pragma: no cover - exercised in the remote MoleRec environment.
    import numpy as np
except ImportError:  # pragma: no cover - the Mac harness need not install NumPy.
    np = None  # type: ignore[assignment]

try:  # pragma: no cover - exercised in the remote MoleRec environment.
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - the Mac harness need not install PyTorch.
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    F = None  # type: ignore[assignment]


def _require_numpy() -> Any:
    if np is None:
        raise RuntimeError("NumPy is required for NeedCover experiment execution")
    return np


def _require_torch() -> Any:
    if torch is None:
        raise RuntimeError("PyTorch is required for NeedCover experiment execution")
    return torch


def _hash_bucket(namespace: str, code: int, width: int) -> int:
    digest = hashlib.blake2b(f"{namespace}:{int(code)}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % width


def history_feature_dimension(
    diagnosis_hash_width: int = DEFAULT_DIAGNOSIS_HASH_WIDTH,
    procedure_hash_width: int = DEFAULT_PROCEDURE_HASH_WIDTH,
) -> int:
    """Return the fixed history-event feature width."""

    if diagnosis_hash_width <= 0 or procedure_hash_width <= 0:
        raise ValueError("history hash widths must be positive")
    return diagnosis_hash_width + procedure_hash_width + CANDIDATE_COUNT + 1


@dataclass(frozen=True)
class VisitExample:
    """Target-free current/history inputs plus a label retained for alignment."""

    patient_id: int
    visit_id: str
    diagnosis_codes: tuple[int, ...]
    procedure_codes: tuple[int, ...]
    history_events: tuple[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]], ...]
    target_medications: tuple[int, ...]


@dataclass(frozen=True)
class PackedVisits:
    """Padded arrays consumed by the PyTorch model."""

    diagnosis_codes: Any
    diagnosis_mask: Any
    procedure_codes: Any
    procedure_mask: Any
    history_features: Any
    history_mask: Any
    diagnosis_counts: Any


def build_visit_examples(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_indices: Iterable[int],
    *,
    history_length: int = DEFAULT_HISTORY_LENGTH,
) -> tuple[VisitExample, ...]:
    """Build visits in canonical record order without leaking current labels.

    ``target_medications`` is kept solely for a runner-side alignment check and
    is never included in the tensors returned by :func:`pack_visit_examples`.
    Medication history is updated only after the current row is materialized,
    so a visit cannot see its own prescription.
    """

    if history_length <= 0:
        raise ValueError("history length must be positive")
    examples: list[VisitExample] = []
    for patient_index in patient_indices:
        patient = records[int(patient_index)]
        prior_events: list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]] = []
        for visit_index, admission in enumerate(patient):
            diagnoses = tuple(sorted(int(code) for code in admission[0]))
            procedures = tuple(sorted(int(code) for code in admission[1]))
            medications = tuple(sorted(int(code) for code in admission[2]))
            examples.append(
                VisitExample(
                    patient_id=int(patient_index),
                    visit_id=f"{int(patient_index)}:{visit_index}",
                    diagnosis_codes=diagnoses,
                    procedure_codes=procedures,
                    history_events=tuple(prior_events[-history_length:]),
                    target_medications=medications,
                )
            )
            prior_events.append((diagnoses, procedures, medications))
    return tuple(examples)


def _encode_history_event(
    event: tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]],
    *,
    diagnosis_hash_width: int,
    procedure_hash_width: int,
    age: float,
) -> tuple[float, ...]:
    vector = [0.0] * history_feature_dimension(diagnosis_hash_width, procedure_hash_width)
    for code in set(event[0]):
        vector[_hash_bucket("history-diagnosis", code, diagnosis_hash_width)] += 1.0
    procedure_offset = diagnosis_hash_width
    for code in set(event[1]):
        vector[
            procedure_offset + _hash_bucket("history-procedure", code, procedure_hash_width)
        ] += 1.0
    medication_offset = diagnosis_hash_width + procedure_hash_width
    for medication in set(event[2]):
        if 0 <= medication < CANDIDATE_COUNT:
            vector[medication_offset + medication] = 1.0
    vector[-1] = float(max(0.0, min(1.0, age)))
    return tuple(vector)


def pack_visit_examples(
    examples: Sequence[VisitExample],
    *,
    max_diagnoses: int | None = None,
    max_procedures: int | None = None,
    diagnosis_hash_width: int = DEFAULT_DIAGNOSIS_HASH_WIDTH,
    procedure_hash_width: int = DEFAULT_PROCEDURE_HASH_WIDTH,
    history_length: int = DEFAULT_HISTORY_LENGTH,
) -> PackedVisits:
    """Pad variable-size diagnosis/procedure sets and encode prior events."""

    numpy = _require_numpy()
    if history_length <= 0:
        raise ValueError("history length must be positive")
    values = tuple(examples)
    if not values:
        raise ValueError("cannot pack an empty visit collection")
    inferred_diagnoses = max((len(item.diagnosis_codes) for item in values), default=1)
    inferred_procedures = max((len(item.procedure_codes) for item in values), default=1)
    max_diagnoses = max(1, inferred_diagnoses if max_diagnoses is None else int(max_diagnoses))
    max_procedures = max(1, inferred_procedures if max_procedures is None else int(max_procedures))
    if any(len(item.diagnosis_codes) > max_diagnoses for item in values):
        raise ValueError("max_diagnoses is smaller than an observed diagnosis set")
    if any(len(item.procedure_codes) > max_procedures for item in values):
        raise ValueError("max_procedures is smaller than an observed procedure set")

    diagnosis_codes = numpy.zeros((len(values), max_diagnoses), dtype=numpy.int64)
    diagnosis_mask = numpy.zeros((len(values), max_diagnoses), dtype=numpy.bool_)
    procedure_codes = numpy.zeros((len(values), max_procedures), dtype=numpy.int64)
    procedure_mask = numpy.zeros((len(values), max_procedures), dtype=numpy.bool_)
    history_features = numpy.zeros(
        (
            len(values),
            history_length,
            history_feature_dimension(diagnosis_hash_width, procedure_hash_width),
        ),
        dtype=numpy.float32,
    )
    history_mask = numpy.zeros((len(values), history_length), dtype=numpy.bool_)
    diagnosis_counts = numpy.zeros(len(values), dtype=numpy.int64)
    for row, example in enumerate(values):
        for index, code in enumerate(example.diagnosis_codes):
            diagnosis_codes[row, index] = _hash_bucket(
                "current-diagnosis", code, diagnosis_hash_width
            )
            diagnosis_mask[row, index] = True
        for index, code in enumerate(example.procedure_codes):
            procedure_codes[row, index] = _hash_bucket(
                "current-procedure", code, procedure_hash_width
            )
            procedure_mask[row, index] = True
        diagnosis_counts[row] = len(example.diagnosis_codes)
        first = history_length - len(example.history_events)
        for offset, event in enumerate(example.history_events, start=first):
            history_features[row, offset] = _encode_history_event(
                event,
                diagnosis_hash_width=diagnosis_hash_width,
                procedure_hash_width=procedure_hash_width,
                age=(offset + 1) / float(history_length),
            )
            history_mask[row, offset] = True
    return PackedVisits(
        diagnosis_codes=diagnosis_codes,
        diagnosis_mask=diagnosis_mask,
        procedure_codes=procedure_codes,
        procedure_mask=procedure_mask,
        history_features=history_features,
        history_mask=history_mask,
        diagnosis_counts=diagnosis_counts,
    )


def build_relation_features(ehr_adjacency: Any, ddi_adjacency: Any) -> tuple[Any, Any]:
    """Normalize Train-derived EHR/DDI matrices and return an edge mask."""

    numpy = _require_numpy()
    expected = (CANDIDATE_COUNT, CANDIDATE_COUNT)
    ehr = numpy.asarray(ehr_adjacency, dtype=numpy.float32)
    ddi = numpy.asarray(ddi_adjacency, dtype=numpy.float32)
    if ehr.shape != expected or ddi.shape != expected:
        raise ValueError("EHR and DDI adjacency matrices must both be 131 by 131")
    ehr = numpy.maximum(ehr, 0.0).copy()
    ddi = numpy.maximum(ddi, 0.0).copy()
    numpy.fill_diagonal(ehr, 0.0)
    numpy.fill_diagonal(ddi, 0.0)
    ehr_max = float(ehr.max())
    ddi_max = float(ddi.max())
    if ehr_max > 0.0:
        ehr /= ehr_max
    if ddi_max > 0.0:
        ddi /= ddi_max
    relation = numpy.stack((ehr, ddi), axis=-1).astype(numpy.float32)
    edge_mask = (ehr > 0.0) | (ddi > 0.0)
    numpy.fill_diagonal(edge_mask, True)
    return relation, edge_mask.astype(numpy.bool_)


def target_sets_from_matrix(target_matrix: Any) -> tuple[frozenset[int], ...]:
    """Convert a [visits, 131] target matrix to deterministic medication sets."""

    numpy = _require_numpy()
    values = numpy.asarray(target_matrix)
    if values.ndim != 2 or values.shape[1] != CANDIDATE_COUNT:
        raise ValueError("target matrix must have shape [visits, 131]")
    return tuple(frozenset(int(index) for index in numpy.flatnonzero(row > 0.5)) for row in values)


def threshold_sets(logits: Any, threshold: float = DEFAULT_THRESHOLD) -> tuple[frozenset[int], ...]:
    """Decode with the frozen non-oracle per-medication threshold."""

    numpy = _require_numpy()
    values = numpy.asarray(logits)
    if values.ndim != 2 or values.shape[1] != CANDIDATE_COUNT:
        raise ValueError("logits must have shape [visits, 131]")
    return tuple(
        frozenset(int(index) for index in numpy.flatnonzero(row >= float(threshold)))
        for row in values
    )


def metric_average_precision(target: Iterable[int], scores: Sequence[float]) -> float:
    """Compute one visit's average precision with deterministic ties."""

    target_set = {int(item) for item in target}
    if not target_set:
        return 0.0
    ranked = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    found = 0
    total = 0.0
    for rank, index in enumerate(ranked, start=1):
        if index in target_set:
            found += 1
            total += found / rank
    return total / len(target_set)


def evaluate_surface(
    targets: Sequence[Iterable[int]],
    predictions: Sequence[Iterable[int]],
    scores: Any,
    ddi: Any,
) -> dict[str, float]:
    """Return visit-macro metrics required by the NeedCover screen."""

    numpy = _require_numpy()
    score_values = numpy.asarray(scores, dtype=numpy.float32)
    ddi_values = numpy.asarray(ddi)
    if len(targets) != len(predictions) or score_values.shape != (len(targets), CANDIDATE_COUNT):
        raise ValueError("targets, predictions, and scores are not visit-aligned")
    if ddi_values.shape != (CANDIDATE_COUNT, CANDIDATE_COUNT):
        raise ValueError("DDI matrix must be 131 by 131")
    jaccard = precision = recall = f1 = prauc = 0.0
    ddi_count = pair_count = 0
    medication_counts: list[int] = []
    for target_raw, prediction_raw, score_row in zip(targets, predictions, score_values):  # noqa: B905
        target = {int(item) for item in target_raw}
        prediction = {int(item) for item in prediction_raw}
        intersection = len(target & prediction)
        union = len(target | prediction)
        visit_precision = (
            1.0
            if not prediction and not target
            else intersection / len(prediction)
            if prediction
            else 0.0
        )
        visit_recall = (
            1.0 if not prediction and not target else intersection / len(target) if target else 0.0
        )
        visit_f1 = (
            0.0
            if visit_precision + visit_recall == 0.0
            else 2.0 * visit_precision * visit_recall / (visit_precision + visit_recall)
        )
        jaccard += 1.0 if not union else intersection / union
        precision += visit_precision
        recall += visit_recall
        f1 += visit_f1
        prauc += metric_average_precision(target, score_row)
        medication_counts.append(len(prediction))
        ordered = sorted(prediction)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                pair_count += 1
                ddi_count += int(bool(ddi_values[left, right]))
    count = len(targets)
    if count <= 0:
        raise ValueError("cannot evaluate an empty visit collection")
    return {
        "jaccard": jaccard / count,
        "f1": f1 / count,
        "prauc": prauc / count,
        "precision": precision / count,
        "recall": recall / count,
        "ddi_rate": 0.0 if pair_count == 0 else ddi_count / pair_count,
        "mean_medication_count": float(sum(medication_counts) / count),
        "std_medication_count": float(numpy.asarray(medication_counts, dtype=numpy.float32).std()),
        "visit_count": float(count),
    }


def coverage_residual_diagnostics(
    coverage: Any,
    residual: Any,
    problem_mask: Any,
) -> dict[str, float]:
    """Summarize the mechanism state over explicit, non-padding problems."""

    numpy = _require_numpy()
    c = numpy.asarray(coverage, dtype=numpy.float32)
    r = numpy.asarray(residual, dtype=numpy.float32)
    mask = numpy.asarray(problem_mask, dtype=numpy.bool_)
    if c.shape != r.shape or c.shape != mask.shape or c.ndim != 2:
        raise ValueError("coverage, residual, and problem mask must share [visits, problems]")
    valid_c = c[mask]
    valid_r = r[mask]
    if valid_c.size == 0:
        raise ValueError("coverage diagnostics require at least one problem state")
    near_zero_c = valid_c <= 0.05
    near_one_c = valid_c >= 0.95
    near_zero_r = valid_r <= 0.05
    near_one_r = valid_r >= 0.95
    return {
        "problem_state_count": float(valid_c.size),
        "coverage_mean": float(valid_c.mean()),
        "coverage_std": float(valid_c.std()),
        "residual_mean": float(valid_r.mean()),
        "residual_std": float(valid_r.std()),
        "coverage_near_zero_fraction": float(near_zero_c.mean()),
        "coverage_near_one_fraction": float(near_one_c.mean()),
        "coverage_near_boundary_fraction": float((near_zero_c | near_one_c).mean()),
        "residual_near_zero_fraction": float(near_zero_r.mean()),
        "residual_near_one_fraction": float(near_one_r.mean()),
        "residual_near_boundary_fraction": float((near_zero_r | near_one_r).mean()),
    }


def _masked_mean(values: Any, mask: Any, dim: int) -> Any:
    weights = mask.to(dtype=values.dtype).unsqueeze(-1)
    return (values * weights).sum(dim=dim) / weights.sum(dim=dim).clamp_min(1.0)


if nn is not None:

    @dataclass(frozen=True)
    class NeedCoverOutput:
        """Intermediate and final states exposed for mechanism diagnostics."""

        final_logits: Any
        provisional_logits: Any
        coverage: Any
        residual: Any
        problem_mask: Any

    class HistoryEncoder(nn.Module):
        """Small shared longitudinal encoder; temporal modeling is not the claim."""

        def __init__(self, input_dim: int, hidden_dim: int) -> None:
            super().__init__()
            self.input_projection = nn.Linear(input_dim, hidden_dim)
            self.gru = nn.GRU(hidden_dim, hidden_dim, batch_first=True)
            self.norm = nn.LayerNorm(hidden_dim)

        def forward(self, history_features: Any, history_mask: Any) -> Any:
            projected = F.gelu(self.input_projection(history_features))
            projected = projected * history_mask.unsqueeze(-1).to(projected.dtype)
            _, hidden = self.gru(projected)
            return self.norm(hidden[-1])

    class ProblemEncoder(nn.Module):
        """Explicit diagnosis nodes with diagnosis-query procedure attention."""

        def __init__(
            self,
            diagnosis_hash_width: int,
            procedure_hash_width: int,
            hidden_dim: int,
        ) -> None:
            super().__init__()
            self.hidden_dim = hidden_dim
            self.diagnosis_embedding = nn.Embedding(diagnosis_hash_width, hidden_dim)
            self.procedure_embedding = nn.Embedding(procedure_hash_width, hidden_dim)
            self.query_projection = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.key_projection = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.value_projection = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.history_projection = nn.Linear(hidden_dim, hidden_dim)
            self.current_projection = nn.Sequential(
                nn.Linear(hidden_dim * 2, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, hidden_dim)
            )
            self.norm = nn.LayerNorm(hidden_dim)

        def forward(
            self,
            diagnosis_codes: Any,
            diagnosis_mask: Any,
            procedure_codes: Any,
            procedure_mask: Any,
            h_hist: Any,
        ) -> tuple[Any, Any]:
            diagnosis = self.diagnosis_embedding(diagnosis_codes)
            procedures = self.procedure_embedding(procedure_codes)
            query = self.query_projection(diagnosis)
            key = self.key_projection(procedures)
            value = self.value_projection(procedures)
            attention_logits = torch.matmul(query, key.transpose(1, 2)) / math.sqrt(
                float(self.hidden_dim)
            )
            attention_logits = attention_logits.masked_fill(
                ~procedure_mask.unsqueeze(1).to(dtype=torch.bool), -1e4
            )
            attention = torch.softmax(attention_logits, dim=-1)
            procedure_context = torch.matmul(attention, value)
            procedure_context = procedure_context * procedure_mask.any(dim=1).unsqueeze(
                -1
            ).unsqueeze(-1)
            history_context = self.history_projection(h_hist).unsqueeze(1)
            nodes = self.norm(diagnosis + procedure_context + history_context)
            diagnosis_pool = _masked_mean(diagnosis, diagnosis_mask, dim=1)
            procedure_pool = _masked_mean(procedures, procedure_mask, dim=1)
            h_current = self.current_projection(torch.cat((diagnosis_pool, procedure_pool), dim=-1))
            return nodes, h_current

    class RelationInteractionLayer(nn.Module):
        """Exactly one patient-conditioned relation-aware medication layer."""

        def __init__(self, relation_features: Any, edge_mask: Any, hidden_dim: int) -> None:
            super().__init__()
            relation_tensor = torch.as_tensor(relation_features, dtype=torch.float32)
            mask_tensor = torch.as_tensor(edge_mask, dtype=torch.bool)
            expected = (CANDIDATE_COUNT, CANDIDATE_COUNT)
            if (
                tuple(relation_tensor.shape) != (*expected, 2)
                or tuple(mask_tensor.shape) != expected
            ):
                raise ValueError("relation features must have shape [131, 131, 2]")
            self.query_projection = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.key_projection = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.value_projection = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.context_query = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.context_key = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.output_projection = nn.Linear(hidden_dim, hidden_dim)
            self.relation_weights = nn.Parameter(torch.tensor([0.35, 0.75], dtype=torch.float32))
            self.norm = nn.LayerNorm(hidden_dim)
            self.register_buffer("relation_features", relation_tensor)
            self.register_buffer("edge_mask", mask_tensor)

        def forward(self, medication_state: Any, h_patient: Any) -> Any:
            query = self.query_projection(medication_state) + self.context_query(
                h_patient
            ).unsqueeze(1)
            key = self.key_projection(medication_state) + self.context_key(h_patient).unsqueeze(1)
            value = self.value_projection(medication_state)
            scores = torch.matmul(query, key.transpose(1, 2)) / math.sqrt(float(query.shape[-1]))
            relation_bias = torch.einsum("ijr,r->ij", self.relation_features, self.relation_weights)
            scores = scores + relation_bias.unsqueeze(0)
            scores = scores.masked_fill(~self.edge_mask.unsqueeze(0), -1e4)
            attention = torch.softmax(scores, dim=-1)
            message = torch.matmul(attention, value)
            return self.norm(medication_state + self.output_projection(message))

    class NeedCoverModel(nn.Module):
        """ProblemDrug, StaticTwoPass, and NeedCover under one shared interface."""

        def __init__(
            self,
            *,
            diagnosis_hash_width: int,
            procedure_hash_width: int,
            history_feature_dim: int,
            hidden_dim: int,
            relation_features: Any,
            edge_mask: Any,
            variant: str,
        ) -> None:
            super().__init__()
            if variant not in VARIANTS:
                raise ValueError(f"unknown NeedCover variant: {variant}")
            if hidden_dim <= 0:
                raise ValueError("hidden dimension must be positive")
            self.variant = variant
            self.hidden_dim = hidden_dim
            self.history_encoder = HistoryEncoder(history_feature_dim, hidden_dim)
            self.problem_encoder = ProblemEncoder(
                diagnosis_hash_width, procedure_hash_width, hidden_dim
            )
            self.medication_embeddings = nn.Parameter(
                torch.randn(CANDIDATE_COUNT, hidden_dim) * 0.02
            )
            self.affinity = nn.Sequential(
                nn.Linear(hidden_dim * 3, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, 1)
            )
            self.state_ffn = nn.Sequential(
                nn.Linear(hidden_dim * 4, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, hidden_dim)
            )
            self.patient_norm = nn.LayerNorm(hidden_dim)
            if variant == "problem_drug":
                self.interaction = None
            else:
                self.interaction = RelationInteractionLayer(
                    relation_features, edge_mask, hidden_dim
                )
            self.provisional_head = nn.Linear(hidden_dim, 1, bias=False)
            if variant == "problem_drug":
                self.second_ffn = None
                self.final_head = None
            else:
                self.second_ffn = nn.Sequential(
                    nn.Linear(hidden_dim * 2, hidden_dim),
                    nn.GELU(),
                    nn.Linear(hidden_dim, hidden_dim),
                )
                self.final_head = nn.Linear(hidden_dim, 1, bias=False)

        def _problem_message(self, alpha: Any, nodes: Any, weights: Any | None = None) -> Any:
            effective = alpha if weights is None else alpha * weights.unsqueeze(-1)
            message = torch.einsum("bkm,bkh->bmh", effective, nodes)
            denominator = effective.sum(dim=1).unsqueeze(-1).clamp_min(1e-6)
            return message / denominator

        def forward(
            self,
            diagnosis_codes: Any,
            diagnosis_mask: Any,
            procedure_codes: Any,
            procedure_mask: Any,
            history_features: Any,
            history_mask: Any,
        ) -> NeedCoverOutput:
            h_hist = self.history_encoder(history_features, history_mask)
            nodes, h_current = self.problem_encoder(
                diagnosis_codes, diagnosis_mask, procedure_codes, procedure_mask, h_hist
            )
            medication = self.medication_embeddings.unsqueeze(0).expand(nodes.shape[0], -1, -1)
            affinity_input = torch.cat(
                (
                    nodes.unsqueeze(2).expand(-1, -1, CANDIDATE_COUNT, -1),
                    medication.unsqueeze(1).expand(-1, nodes.shape[1], -1, -1),
                    nodes.unsqueeze(2).expand(-1, -1, CANDIDATE_COUNT, -1)
                    * medication.unsqueeze(1).expand(-1, nodes.shape[1], -1, -1),
                ),
                dim=-1,
            )
            affinity_logits = self.affinity(affinity_input).squeeze(-1)
            affinity_logits = affinity_logits.masked_fill(
                ~diagnosis_mask.unsqueeze(-1).to(dtype=torch.bool), -1e4
            )
            alpha = torch.softmax(affinity_logits, dim=-1)
            alpha = alpha * diagnosis_mask.unsqueeze(-1).to(alpha.dtype)
            m0 = self._problem_message(alpha, nodes)
            h_hist_expanded = h_hist.unsqueeze(1).expand(-1, CANDIDATE_COUNT, -1)
            h_current_expanded = h_current.unsqueeze(1).expand(-1, CANDIDATE_COUNT, -1)
            state_input = torch.cat((medication, m0, h_hist_expanded, h_current_expanded), dim=-1)
            z0 = self.state_ffn(state_input)
            h_patient = self.patient_norm(h_hist + h_current)
            z_tilde = z0 if self.interaction is None else self.interaction(z0, h_patient)
            provisional_logits = self.provisional_head(z_tilde).squeeze(-1)
            provisional_probability = torch.sigmoid(provisional_logits)
            coverage = torch.einsum("bkm,bm->bk", alpha, provisional_probability)
            coverage = coverage * diagnosis_mask.to(dtype=coverage.dtype)
            residual = (1.0 - coverage) * diagnosis_mask.to(dtype=coverage.dtype)
            if self.variant == "problem_drug":
                final_logits = provisional_logits
            else:
                weights = None if self.variant == "static_two_pass" else residual
                m1 = self._problem_message(alpha, nodes, weights=weights)
                second_input = torch.cat((z_tilde, m1), dim=-1)
                z1 = self.second_ffn(second_input)
                final_logits = self.final_head(z1).squeeze(-1)
            return NeedCoverOutput(
                final_logits=final_logits,
                provisional_logits=provisional_logits,
                coverage=coverage,
                residual=residual,
                problem_mask=diagnosis_mask,
            )

    def needcover_loss(
        output: NeedCoverOutput,
        targets: Any,
        *,
        provisional_weight: float = DEFAULT_PROVISIONAL_WEIGHT,
    ) -> tuple[Any, dict[str, float]]:
        """Use one BCE objective plus the identical auxiliary term for all variants."""

        final_loss = F.binary_cross_entropy_with_logits(output.final_logits, targets)
        provisional_loss = F.binary_cross_entropy_with_logits(output.provisional_logits, targets)
        total = final_loss + float(provisional_weight) * provisional_loss
        return total, {
            "final_bce": float(final_loss.detach().cpu()),
            "provisional_bce": float(provisional_loss.detach().cpu()),
            "total": float(total.detach().cpu()),
        }

else:

    @dataclass(frozen=True)
    class NeedCoverOutput:  # type: ignore[no-redef]
        final_logits: Any = None
        provisional_logits: Any = None
        coverage: Any = None
        residual: Any = None
        problem_mask: Any = None

    class NeedCoverModel:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for NeedCover execution")

    def needcover_loss(*_args: Any, **_kwargs: Any) -> tuple[Any, dict[str, float]]:
        raise RuntimeError("PyTorch is required for NeedCover execution")


__all__ = (
    "CANDIDATE_COUNT",
    "DEFAULT_DIAGNOSIS_HASH_WIDTH",
    "DEFAULT_HIDDEN_DIM",
    "DEFAULT_HISTORY_LENGTH",
    "DEFAULT_PROCEDURE_HASH_WIDTH",
    "DEFAULT_PROVISIONAL_WEIGHT",
    "DEFAULT_THRESHOLD",
    "VARIANTS",
    "NeedCoverModel",
    "NeedCoverOutput",
    "PackedVisits",
    "VisitExample",
    "build_relation_features",
    "build_visit_examples",
    "coverage_residual_diagnostics",
    "evaluate_surface",
    "history_feature_dimension",
    "metric_average_precision",
    "needcover_loss",
    "pack_visit_examples",
    "target_sets_from_matrix",
    "threshold_sets",
)
