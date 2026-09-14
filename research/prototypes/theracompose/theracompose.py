"""TheraCompose: a bounded latent-intent medication-set prototype.

The module is intentionally self-contained and throwaway.  It answers one
question: does representing a visit with several soft therapeutic intents make
medication ranking and structured set inference better than one patient vector
with independent medication logits?
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

CANDIDATE_COUNT = 131
INTENT_SLOTS = 4
DEFAULT_CODE_HASH_WIDTH = 128
DEFAULT_HISTORY_LENGTH = 4
DEFAULT_SLOT_ITERATIONS = 2
DEFAULT_SEARCH_ITERATIONS = 3
DEFAULT_SEARCH_CANDIDATE_POOL = 8
ENERGY_COMPATIBILITY_WEIGHT = 0.25
ENERGY_DDI_WEIGHT = 0.50
ENERGY_COVERAGE_WEIGHT = 0.25
ENERGY_CARDINALITY_WEIGHT = 0.10
HARD_NEGATIVE_TYPES = (
    "high_score_swap",
    "ddi_inducing_swap",
    "intent_coverage_deletion",
    "redundant_addition",
)

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
        raise RuntimeError("NumPy is required for TheraCompose experiment execution")
    return np


def _require_torch() -> Any:
    if torch is None:
        raise RuntimeError("PyTorch is required for TheraCompose experiment execution")
    return torch


def _hash_bucket(namespace: str, code: int, width: int) -> int:
    digest = hashlib.blake2b(f"{namespace}:{int(code)}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % width


def event_feature_dimension(code_hash_width: int = DEFAULT_CODE_HASH_WIDTH) -> int:
    if code_hash_width <= 0:
        raise ValueError("code hash width must be positive")
    return 2 * code_hash_width + CANDIDATE_COUNT + 2


def encode_visit_event(
    diagnoses: Iterable[int],
    procedures: Iterable[int],
    medications: Iterable[int],
    *,
    code_hash_width: int = DEFAULT_CODE_HASH_WIDTH,
    is_current: bool = False,
    history_depth: float = 0.0,
) -> tuple[float, ...]:
    """Encode one event without exposing the current visit's target labels."""

    vector = [0.0] * event_feature_dimension(code_hash_width)
    for code in set(int(value) for value in diagnoses):
        vector[_hash_bucket("d", code, code_hash_width)] += 1.0
    procedure_offset = code_hash_width
    for code in set(int(value) for value in procedures):
        vector[procedure_offset + _hash_bucket("p", code, code_hash_width)] += 1.0
    medication_offset = 2 * code_hash_width
    for medication in set(int(value) for value in medications):
        if 0 <= medication < CANDIDATE_COUNT:
            vector[medication_offset + medication] = 1.0
    # A signed event marker keeps padded rows distinguishable from real history
    # rows while still making the current event explicit to the encoder.
    vector[-2] = 1.0 if is_current else -1.0
    vector[-1] = float(max(0.0, min(1.0, history_depth)))
    return tuple(vector)


def build_patient_event_sequences(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_indices: Iterable[int],
    *,
    code_hash_width: int = DEFAULT_CODE_HASH_WIDTH,
    history_length: int = DEFAULT_HISTORY_LENGTH,
) -> Any:
    """Build left-padded historical-event sequences in record order.

    A target visit contributes current diagnoses/procedures only.  Its
    medication features come from prior visits, while each padded history event
    contains the medications that were available before the target.
    """

    numpy = _require_numpy()
    if history_length <= 0:
        raise ValueError("history length must be positive")
    dimension = event_feature_dimension(code_hash_width)
    sequences: list[list[list[float]]] = []
    for patient_index in patient_indices:
        patient = records[int(patient_index)]
        history_events: list[tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]] = []
        history_medications: set[int] = set()
        for admission in patient:
            diagnoses = tuple(sorted(int(value) for value in admission[0]))
            procedures = tuple(sorted(int(value) for value in admission[1]))
            current = [[0.0] * dimension for _ in range(history_length + 1)]
            prior_events = history_events[-history_length:]
            first = history_length - len(prior_events)
            for offset, (old_diagnoses, old_procedures, old_medications) in enumerate(
                prior_events, start=first
            ):
                current[offset] = list(
                    encode_visit_event(
                        old_diagnoses,
                        old_procedures,
                        old_medications,
                        code_hash_width=code_hash_width,
                        is_current=False,
                        history_depth=0.0,
                    )
                )
            current[-1] = list(
                encode_visit_event(
                    diagnoses,
                    procedures,
                    history_medications,
                    code_hash_width=code_hash_width,
                    is_current=True,
                    history_depth=len(history_events) / float(history_length),
                )
            )
            sequences.append(current)
            medications = tuple(sorted(int(value) for value in admission[2]))
            history_events.append((diagnoses, procedures, medications))
            history_medications.update(medications)
    return numpy.asarray(sequences, dtype=numpy.float32)


def topk_set(logits: Sequence[float], cardinality: int) -> frozenset[int]:
    """Return a deterministic Top-K medication set."""

    values = tuple(float(value) for value in logits)
    if len(values) != CANDIDATE_COUNT:
        raise ValueError("medication logits must have the 131-candidate shape")
    if cardinality < 0 or cardinality > CANDIDATE_COUNT:
        raise ValueError("cardinality is outside the 131-candidate vocabulary")
    ranked = sorted(range(CANDIDATE_COUNT), key=lambda index: (-values[index], index))
    return frozenset(ranked[:cardinality])


def aggregate_slot_utilities(
    slot_scores: Sequence[Sequence[float]],
    activity: Sequence[float],
) -> tuple[float, ...]:
    """Smoothly aggregate intent-specific medication utilities.

    The operation is permutation invariant over the four slots, which is the
    useful latent-slot contract tested on the local harness.
    """

    if len(slot_scores) != INTENT_SLOTS or len(activity) != INTENT_SLOTS:
        raise ValueError("TheraCompose v0 requires exactly four intent slots")
    if not slot_scores:
        return ()
    medication_count = len(slot_scores[0])
    if any(len(row) != medication_count for row in slot_scores):
        raise ValueError("slot score rows must have equal length")
    result = []
    for medication in range(medication_count):
        values = [
            float(slot_scores[slot][medication]) + math.log(max(float(activity[slot]), 1e-4))
            for slot in range(INTENT_SLOTS)
        ]
        maximum = max(values)
        result.append(maximum + math.log(sum(math.exp(value - maximum) for value in values)))
    return tuple(result)


def target_sets_from_matrix(target_matrix: Any) -> tuple[frozenset[int], ...]:
    numpy = _require_numpy()
    values = numpy.asarray(target_matrix)
    if values.ndim != 2 or values.shape[1] != CANDIDATE_COUNT:
        raise ValueError("target matrix must have shape [visits, 131]")
    return tuple(frozenset(int(index) for index in numpy.flatnonzero(row > 0.5)) for row in values)


def _ordered_by_score(indices: Iterable[int], scores: Sequence[float]) -> list[int]:
    return sorted(
        (int(index) for index in indices), key=lambda index: (-float(scores[index]), index)
    )


def construct_hard_negative_sets(
    target_sets: Sequence[Iterable[int]],
    base_scores: Sequence[Sequence[float]],
    ddi: Sequence[Sequence[float]],
) -> tuple[tuple[frozenset[int], ...], ...]:
    """Construct four deterministic hard-negative prescriptions per visit."""

    if len(target_sets) != len(base_scores):
        raise ValueError("target sets and score rows must be aligned")
    if len(ddi) != CANDIDATE_COUNT or any(len(row) != CANDIDATE_COUNT for row in ddi):
        raise ValueError("DDI matrix must be 131 by 131")
    all_medications = set(range(CANDIDATE_COUNT))
    rows: list[tuple[frozenset[int], ...]] = []
    for target_raw, score_row in zip(target_sets, base_scores):  # noqa: B905
        if len(score_row) != CANDIDATE_COUNT:
            raise ValueError("score rows must contain 131 medications")
        target = {int(value) for value in target_raw}
        if any(value < 0 or value >= CANDIDATE_COUNT for value in target):
            raise ValueError("target set contains an out-of-range medication")
        non_target = all_medications - target

        high_score_swap = set(target)
        if target and non_target:
            remove = min(target, key=lambda index: (float(score_row[index]), index))
            add = _ordered_by_score(non_target, score_row)[0]
            high_score_swap.remove(remove)
            high_score_swap.add(add)

        ddi_swap = set(target)
        if target and non_target:
            add = max(
                non_target,
                key=lambda index: (
                    sum(float(ddi[index][other]) for other in target),
                    float(score_row[index]),
                    -index,
                ),
            )
            remove = min(
                target,
                key=lambda index: (
                    sum(float(ddi[index][other]) for other in target if other != index),
                    float(score_row[index]),
                    index,
                ),
            )
            ddi_swap.remove(remove)
            ddi_swap.add(add)

        deletion = set(target)
        if deletion:
            deletion.remove(min(deletion, key=lambda index: (float(score_row[index]), index)))

        addition = set(target)
        if non_target:
            addition.add(_ordered_by_score(non_target, score_row)[0])

        rows.append(
            (
                frozenset(high_score_swap),
                frozenset(ddi_swap),
                frozenset(deletion),
                frozenset(addition),
            )
        )
    return tuple(rows)


def hard_negative_masks(
    target_sets: Sequence[Iterable[int]],
    base_scores: Sequence[Sequence[float]],
    ddi: Sequence[Sequence[float]],
) -> Any:
    numpy = _require_numpy()
    negatives = construct_hard_negative_sets(target_sets, base_scores, ddi)
    masks = numpy.zeros(
        (len(negatives), len(HARD_NEGATIVE_TYPES), CANDIDATE_COUNT), dtype=numpy.float32
    )
    for row, candidates in enumerate(negatives):
        for negative_index, candidate in enumerate(candidates):
            masks[row, negative_index, list(candidate)] = 1.0
    return masks


def _set_energy_python(
    selected: Iterable[int],
    unary: Sequence[float],
    compatibility: Sequence[Sequence[float]],
    risk: Sequence[Sequence[float]],
    intent_support: Sequence[Sequence[float]],
    activity: Sequence[float],
    expected_cardinality: float,
) -> float:
    chosen = tuple(sorted(set(int(value) for value in selected)))
    pair_normalizer = float(max(len(chosen) ** 2, 1))
    unary_term = -sum(float(unary[index]) for index in chosen)
    compatibility_term = sum(
        float(compatibility[left][right])
        for left_index, left in enumerate(chosen)
        for right in chosen[left_index + 1 :]
    )
    risk_term = sum(
        float(risk[left][right])
        for left_index, left in enumerate(chosen)
        for right in chosen[left_index + 1 :]
    )
    activity_total = max(sum(float(value) for value in activity), 1e-6)
    uncovered = 0.0
    for slot, slot_activity in enumerate(activity):
        probability_not_covered = 1.0
        for medication in chosen:
            probability_not_covered *= 1.0 - float(intent_support[slot][medication])
        uncovered += float(slot_activity) * probability_not_covered
    uncovered /= activity_total
    cardinality_term = ((len(chosen) - float(expected_cardinality)) / float(CANDIDATE_COUNT)) ** 2
    return (
        unary_term
        - ENERGY_COMPATIBILITY_WEIGHT * compatibility_term / pair_normalizer
        + ENERGY_DDI_WEIGHT * risk_term / pair_normalizer
        + ENERGY_COVERAGE_WEIGHT * uncovered
        + ENERGY_CARDINALITY_WEIGHT * cardinality_term
    )


def set_energy(
    selected: Iterable[int],
    unary: Sequence[float],
    compatibility: Sequence[Sequence[float]],
    risk: Sequence[Sequence[float]],
    intent_support: Sequence[Sequence[float]],
    activity: Sequence[float],
    expected_cardinality: float,
) -> float:
    """Evaluate one prescription energy using the explicit v0 terms."""

    return _set_energy_python(
        selected,
        unary,
        compatibility,
        risk,
        intent_support,
        activity,
        expected_cardinality,
    )


def set_energy_batch(
    masks: Any,
    unary: Any,
    compatibility: Any,
    risk: Any,
    intent_support: Any,
    activity: Any,
    expected_cardinality: float,
) -> Any:
    """Evaluate a batch of set energies for bounded local search."""

    numpy = _require_numpy()
    mask_values = numpy.asarray(masks, dtype=numpy.float32)
    if mask_values.ndim == 1:
        mask_values = mask_values[None, :]
    chosen_count = mask_values.sum(axis=1)
    pair_normalizer = numpy.maximum(chosen_count**2, 1.0)
    unary_values = numpy.asarray(unary, dtype=numpy.float32)
    compatibility_values = numpy.asarray(compatibility, dtype=numpy.float32)
    risk_values = numpy.asarray(risk, dtype=numpy.float32)
    support_values = numpy.asarray(intent_support, dtype=numpy.float32)
    activity_values = numpy.asarray(activity, dtype=numpy.float32)
    compatibility_term = 0.5 * numpy.einsum(
        "bi,ij,bj->b", mask_values, compatibility_values, mask_values
    )
    risk_term = 0.5 * numpy.einsum("bi,ij,bj->b", mask_values, risk_values, mask_values)
    activity_total = max(float(activity_values.sum()), 1e-6)
    covered = 1.0 - numpy.prod(1.0 - mask_values[:, None, :] * support_values[None, :, :], axis=-1)
    uncovered = (activity_values[None, :] * (1.0 - covered)).sum(axis=1) / activity_total
    cardinality_term = ((chosen_count - float(expected_cardinality)) / CANDIDATE_COUNT) ** 2
    return (
        -(mask_values * unary_values[None, :]).sum(axis=1)
        - ENERGY_COMPATIBILITY_WEIGHT * compatibility_term / pair_normalizer
        + ENERGY_DDI_WEIGHT * risk_term / pair_normalizer
        + ENERGY_COVERAGE_WEIGHT * uncovered
        + ENERGY_CARDINALITY_WEIGHT * cardinality_term
    )


def structured_set_search(
    unary: Any,
    compatibility: Any,
    risk: Any,
    intent_support: Any,
    activity: Any,
    expected_cardinality: Sequence[float],
    initial_sets: Sequence[Iterable[int]],
    *,
    max_iterations: int = DEFAULT_SEARCH_ITERATIONS,
    candidate_pool: int = DEFAULT_SEARCH_CANDIDATE_POOL,
) -> tuple[frozenset[int], ...]:
    """Run deterministic bounded same-K medication swaps under the learned energy."""

    numpy = _require_numpy()
    if max_iterations <= 0 or candidate_pool <= 0:
        raise ValueError("search bounds must be positive")
    unary_values = numpy.asarray(unary, dtype=numpy.float32)
    compatibility_values = numpy.asarray(compatibility, dtype=numpy.float32)
    risk_values = numpy.asarray(risk, dtype=numpy.float32)
    support_values = numpy.asarray(intent_support, dtype=numpy.float32)
    activity_values = numpy.asarray(activity, dtype=numpy.float32)
    expected_values = numpy.asarray(expected_cardinality, dtype=numpy.float32)
    predictions: list[frozenset[int]] = []
    for row, initial in enumerate(initial_sets):
        current = set(int(value) for value in initial)
        current_energy = float(
            set_energy_batch(
                numpy.asarray(
                    [[1.0 if index in current else 0.0 for index in range(CANDIDATE_COUNT)]],
                    dtype=numpy.float32,
                ),
                unary_values[row],
                compatibility_values[row],
                risk_values[row],
                support_values[row],
                activity_values[row],
                float(expected_values[row]),
            )[0]
        )
        for _ in range(max_iterations):
            available = sorted(
                (index for index in range(CANDIDATE_COUNT) if index not in current),
                key=lambda index: (-float(unary_values[row, index]), index),
            )[:candidate_pool]
            candidates: list[frozenset[int]] = []
            masks: list[list[float]] = []
            for remove in sorted(current):
                for add in available:
                    candidate = frozenset((current - {remove}) | {add})
                    candidates.append(candidate)
                    masks.append(
                        [1.0 if index in candidate else 0.0 for index in range(CANDIDATE_COUNT)]
                    )
            if not candidates:
                break
            energies = set_energy_batch(
                numpy.asarray(masks, dtype=numpy.float32),
                unary_values[row],
                compatibility_values[row],
                risk_values[row],
                support_values[row],
                activity_values[row],
                float(expected_values[row]),
            )
            best_index = min(
                range(len(candidates)),
                key=lambda index: (float(energies[index]), tuple(sorted(candidates[index]))),
            )
            best_energy = float(energies[best_index])
            if best_energy >= current_energy - 1e-7:
                break
            current = set(candidates[best_index])
            current_energy = best_energy
        predictions.append(frozenset(current))
    return tuple(predictions)


def intent_coverage_diagnostic(
    medication_sets: Sequence[Iterable[int]],
    intent_support: Any,
    activity: Any,
) -> float:
    numpy = _require_numpy()
    support_values = numpy.asarray(intent_support, dtype=numpy.float32)
    activity_values = numpy.asarray(activity, dtype=numpy.float32)
    if support_values.ndim != 3 or support_values.shape[1] != INTENT_SLOTS:
        raise ValueError("intent support must have shape [visits, 4, 131]")
    total = 0.0
    weight = 0.0
    for row, medication_set in enumerate(medication_sets):
        chosen = tuple(int(value) for value in medication_set)
        for slot in range(INTENT_SLOTS):
            covered = (
                0.0
                if not chosen
                else 1.0 - float(numpy.prod(1.0 - support_values[row, slot, list(chosen)]))
            )
            total += float(activity_values[row, slot]) * covered
            weight += float(activity_values[row, slot])
    return 0.0 if weight == 0.0 else total / weight


def set_change_summary(
    baseline: Sequence[Iterable[int]],
    edited: Sequence[Iterable[int]],
) -> dict[str, float]:
    if len(baseline) != len(edited) or not baseline:
        raise ValueError("baseline and edited sets must be non-empty and aligned")
    differences = [len(set(left) ^ set(right)) for left, right in zip(baseline, edited)]  # noqa: B905
    return {
        "changed_fraction": sum(value > 0 for value in differences) / len(differences),
        "mean_symmetric_difference": sum(differences) / len(differences),
    }


if nn is not None:

    @dataclass(frozen=True)
    class TheraComposeOutput:
        context: Any
        slots: Any
        activity: Any
        slot_scores: Any
        intent_support: Any
        unary_logits: Any
        cardinality_logits: Any
        expected_cardinality: Any
        medication_hidden: Any
        compatibility: Any
        risk: Any

    class PatientEncoder(nn.Module):
        """Small GRU history encoder followed by four permutation-symmetric slots."""

        def __init__(
            self,
            event_features: int,
            hidden_dim: int,
            *,
            slot_iterations: int = DEFAULT_SLOT_ITERATIONS,
        ) -> None:
            super().__init__()
            if slot_iterations <= 0:
                raise ValueError("slot iterations must be positive")
            self.slot_iterations = slot_iterations
            self.hidden_dim = hidden_dim
            self.event_projection = nn.Linear(event_features, hidden_dim)
            self.history_gru = nn.GRU(hidden_dim, hidden_dim, batch_first=True)
            self.slot_init = nn.Parameter(torch.randn(INTENT_SLOTS, hidden_dim) * 0.02)
            self.slot_query = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.token_key = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.token_value = nn.Linear(hidden_dim, hidden_dim, bias=False)
            self.slot_update = nn.GRUCell(hidden_dim, hidden_dim)
            self.slot_mlp = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, hidden_dim)
            )
            self.activity_head = nn.Linear(hidden_dim, 1)
            self.context_norm = nn.LayerNorm(hidden_dim)

        def forward(self, events: Any, sequence_mask: Any) -> tuple[Any, Any, Any, Any]:
            mask = sequence_mask.to(dtype=torch.bool)
            projected = F.gelu(self.event_projection(events))
            history_hidden, _ = self.history_gru(projected)
            history_hidden = history_hidden * mask.unsqueeze(-1).to(history_hidden.dtype)
            slots = self.slot_init.unsqueeze(0).expand(events.shape[0], -1, -1)
            for _ in range(self.slot_iterations):
                queries = self.slot_query(slots)
                keys = self.token_key(history_hidden)
                assignment_logits = torch.einsum("bth,bsh->bts", keys, queries)
                assignment_logits = assignment_logits / math.sqrt(float(self.hidden_dim))
                assignment_logits = assignment_logits.masked_fill(~mask.unsqueeze(-1), -1e4)
                assignment = torch.softmax(assignment_logits, dim=-1)
                assignment = assignment * mask.unsqueeze(-1).to(assignment.dtype)
                assignment = assignment / assignment.sum(dim=1, keepdim=True).clamp_min(1e-6)
                values = self.token_value(history_hidden)
                updates = torch.einsum("bts,bth->bsh", assignment, values)
                slots = self.slot_update(
                    updates.reshape(-1, self.hidden_dim), slots.reshape(-1, self.hidden_dim)
                ).reshape(events.shape[0], INTENT_SLOTS, self.hidden_dim)
                slots = slots + 0.1 * F.gelu(self.slot_mlp(slots))
            activity = torch.sigmoid(self.activity_head(slots).squeeze(-1))
            activity_weights = activity / activity.sum(dim=-1, keepdim=True).clamp_min(1e-6)
            context = history_hidden[:, -1] + (slots * activity_weights.unsqueeze(-1)).sum(dim=1)
            return self.context_norm(context), slots, activity, history_hidden

    class TheraComposeModel(nn.Module):
        """Latent-intent proposals plus patient-conditioned set energy."""

        def __init__(
            self,
            event_features: int,
            medication_embeddings: Any,
            ehr_adjacency: Any,
            ddi_adjacency: Any,
            *,
            hidden_dim: int = 96,
            max_cardinality: int = CANDIDATE_COUNT,
            slot_iterations: int = DEFAULT_SLOT_ITERATIONS,
        ) -> None:
            super().__init__()
            if hidden_dim <= 0:
                raise ValueError("hidden dimension must be positive")
            if max_cardinality <= 0 or max_cardinality > CANDIDATE_COUNT:
                raise ValueError("max cardinality must be between 1 and 131")
            medication_values = torch.as_tensor(medication_embeddings, dtype=torch.float32)
            if medication_values.ndim != 2 or medication_values.shape[0] != CANDIDATE_COUNT:
                raise ValueError("medication embeddings must have shape [131, width]")
            ehr_values = torch.as_tensor(ehr_adjacency, dtype=torch.float32)
            ddi_values = torch.as_tensor(ddi_adjacency, dtype=torch.float32)
            if ehr_values.shape != (CANDIDATE_COUNT, CANDIDATE_COUNT):
                raise ValueError("EHR adjacency must be 131 by 131")
            if ddi_values.shape != ehr_values.shape:
                raise ValueError("DDI adjacency must match EHR adjacency")
            edge = torch.clamp(ehr_values, min=0.0) + 0.5 * torch.clamp(ddi_values, min=0.0)
            edge = edge + torch.eye(CANDIDATE_COUNT, dtype=torch.float32)
            edge = edge / edge.sum(dim=-1, keepdim=True).clamp_min(1e-6)
            self.max_cardinality = max_cardinality
            self.hidden_dim = hidden_dim
            self.patient_encoder = PatientEncoder(
                event_features,
                hidden_dim,
                slot_iterations=slot_iterations,
            )
            self.medication_projection = nn.Linear(medication_values.shape[1], hidden_dim)
            self.context_projection = nn.Linear(hidden_dim, hidden_dim)
            self.intent_scorer = nn.Sequential(
                nn.Linear(hidden_dim * 2 + 1, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, 1),
            )
            self.support_projection = nn.Linear(1, hidden_dim)
            self.self_layers = nn.ModuleList(nn.Linear(hidden_dim, hidden_dim) for _ in range(2))
            self.message_layers = nn.ModuleList(nn.Linear(hidden_dim, hidden_dim) for _ in range(2))
            self.risk_head = nn.Linear(hidden_dim, 1)
            self.cardinality_head = nn.Linear(hidden_dim, max_cardinality + 1)
            self.base_score_scale = nn.Parameter(torch.tensor(0.25))
            self.register_buffer("medication_embeddings", medication_values)
            self.register_buffer("edge_adjacency", edge)
            self.register_buffer("ehr_adjacency", torch.clamp(ehr_values, min=0.0))
            self.register_buffer("ddi_adjacency", torch.clamp(ddi_values, min=0.0))
            self.register_buffer(
                "cardinality_values",
                torch.arange(max_cardinality + 1, dtype=torch.float32),
            )

        def forward(
            self,
            events: Any,
            sequence_mask: Any,
            base_scores: Any,
        ) -> TheraComposeOutput:
            context, slots, activity, _ = self.patient_encoder(events, sequence_mask)
            medication_base = F.gelu(self.medication_projection(self.medication_embeddings))
            medication_context = medication_base.unsqueeze(0) + self.context_projection(
                context
            ).unsqueeze(1)
            slot_context = slots.unsqueeze(2).expand(-1, -1, CANDIDATE_COUNT, -1)
            medication_context_expanded = medication_context.unsqueeze(1).expand(
                -1, INTENT_SLOTS, -1, -1
            )
            score_input = torch.cat(
                (
                    slot_context,
                    medication_context_expanded,
                    base_scores.unsqueeze(1).unsqueeze(-1).expand(-1, INTENT_SLOTS, -1, -1),
                ),
                dim=-1,
            )
            slot_scores = self.intent_scorer(score_input).squeeze(-1)
            intent_support = torch.sigmoid(slot_scores)
            weighted_scores = slot_scores + torch.log(activity.unsqueeze(-1).clamp_min(1e-4))
            unary_logits = torch.logsumexp(weighted_scores, dim=1)
            unary_logits = unary_logits + self.base_score_scale * base_scores
            support = (activity.unsqueeze(-1) * intent_support).sum(dim=1) / activity.sum(
                dim=-1, keepdim=True
            ).clamp_min(1e-6)
            medication_hidden = medication_context + self.support_projection(support.unsqueeze(-1))
            for self_layer, message_layer in zip(  # noqa: B905
                self.self_layers, self.message_layers
            ):
                message = torch.bmm(
                    self.edge_adjacency.unsqueeze(0).expand(events.shape[0], -1, -1),
                    medication_hidden,
                )
                medication_hidden = F.gelu(self_layer(medication_hidden) + message_layer(message))
            compatibility = torch.tanh(
                torch.bmm(medication_hidden, medication_hidden.transpose(1, 2))
                / math.sqrt(float(self.hidden_dim))
            ) * self.ehr_adjacency.unsqueeze(0)
            risk_strength = F.softplus(self.risk_head(medication_hidden).squeeze(-1))
            risk = (
                risk_strength.unsqueeze(2)
                * risk_strength.unsqueeze(1)
                * self.ddi_adjacency.unsqueeze(0)
            )
            cardinality_logits = self.cardinality_head(context)
            cardinality_probability = torch.softmax(cardinality_logits, dim=-1)
            expected_cardinality = cardinality_probability @ self.cardinality_values
            return TheraComposeOutput(
                context=context,
                slots=slots,
                activity=activity,
                slot_scores=slot_scores,
                intent_support=intent_support,
                unary_logits=unary_logits,
                cardinality_logits=cardinality_logits,
                expected_cardinality=expected_cardinality,
                medication_hidden=medication_hidden,
                compatibility=compatibility,
                risk=risk,
            )

        def energy(self, output: TheraComposeOutput, masks: Any) -> Any:
            mask = masks.to(dtype=output.unary_logits.dtype)
            pair_normalizer = mask.sum(dim=-1).square().clamp_min(1.0)
            compatibility_term = 0.5 * torch.einsum(
                "bi,bij,bj->b", mask, output.compatibility, mask
            )
            risk_term = 0.5 * torch.einsum("bi,bij,bj->b", mask, output.risk, mask)
            covered = 1.0 - torch.prod(1.0 - output.intent_support * mask.unsqueeze(1), dim=-1)
            activity_total = output.activity.sum(dim=-1).clamp_min(1e-6)
            uncovered = (output.activity * (1.0 - covered)).sum(dim=-1) / activity_total
            cardinality_term = (
                (mask.sum(dim=-1) - output.expected_cardinality) / CANDIDATE_COUNT
            ).square()
            return (
                -(mask * output.unary_logits).sum(dim=-1)
                - ENERGY_COMPATIBILITY_WEIGHT * compatibility_term / pair_normalizer
                + ENERGY_DDI_WEIGHT * risk_term / pair_normalizer
                + ENERGY_COVERAGE_WEIGHT * uncovered
                + ENERGY_CARDINALITY_WEIGHT * cardinality_term
            )

    def _repeat_output(output: TheraComposeOutput, repeats: int) -> TheraComposeOutput:
        if repeats <= 0:
            raise ValueError("repeat count must be positive")
        return TheraComposeOutput(
            context=output.context.repeat_interleave(repeats, dim=0),
            slots=output.slots.repeat_interleave(repeats, dim=0),
            activity=output.activity.repeat_interleave(repeats, dim=0),
            slot_scores=output.slot_scores.repeat_interleave(repeats, dim=0),
            intent_support=output.intent_support.repeat_interleave(repeats, dim=0),
            unary_logits=output.unary_logits.repeat_interleave(repeats, dim=0),
            cardinality_logits=output.cardinality_logits.repeat_interleave(repeats, dim=0),
            expected_cardinality=output.expected_cardinality.repeat_interleave(repeats, dim=0),
            medication_hidden=output.medication_hidden.repeat_interleave(repeats, dim=0),
            compatibility=output.compatibility.repeat_interleave(repeats, dim=0),
            risk=output.risk.repeat_interleave(repeats, dim=0),
        )

    def theracompose_loss(
        model: TheraComposeModel,
        output: TheraComposeOutput,
        targets: Any,
        negative_masks: Any,
        *,
        margin: float = 0.5,
        lambda_unary: float = 0.5,
        lambda_cardinality: float = 0.5,
    ) -> tuple[Any, dict[str, float]]:
        if negative_masks.ndim != 3:
            raise ValueError("negative masks must have shape [batch, negatives, 131]")
        positive_energy = model.energy(output, targets)
        negative_count = negative_masks.shape[1]
        repeated_output = _repeat_output(output, negative_count)
        negative_energy = model.energy(
            repeated_output,
            negative_masks.reshape(-1, CANDIDATE_COUNT),
        ).reshape(-1, negative_count)
        ranking_loss = F.relu(margin + positive_energy.unsqueeze(1) - negative_energy).mean()
        unary_loss = F.binary_cross_entropy_with_logits(output.unary_logits, targets)
        cardinality_targets = targets.sum(dim=-1).long().clamp(0, model.max_cardinality)
        cardinality_loss = F.cross_entropy(output.cardinality_logits, cardinality_targets)
        total = ranking_loss + lambda_unary * unary_loss + lambda_cardinality * cardinality_loss
        return total, {
            "energy_margin": float(ranking_loss.detach().cpu()),
            "unary_bce": float(unary_loss.detach().cpu()),
            "cardinality_ce": float(cardinality_loss.detach().cpu()),
            "total": float(total.detach().cpu()),
        }

else:

    @dataclass(frozen=True)
    class TheraComposeOutput:  # type: ignore[no-redef]
        """Import-safe output placeholder when PyTorch is unavailable."""

        context: Any = None
        slots: Any = None
        activity: Any = None
        slot_scores: Any = None
        intent_support: Any = None
        unary_logits: Any = None
        cardinality_logits: Any = None
        expected_cardinality: Any = None
        medication_hidden: Any = None
        compatibility: Any = None
        risk: Any = None

    class PatientEncoder:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for TheraCompose execution")

    class TheraComposeModel:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for TheraCompose execution")

    def theracompose_loss(*_args: Any, **_kwargs: Any) -> tuple[Any, dict[str, float]]:
        raise RuntimeError("PyTorch is required for TheraCompose execution")


__all__ = (
    "CANDIDATE_COUNT",
    "DEFAULT_CODE_HASH_WIDTH",
    "DEFAULT_HISTORY_LENGTH",
    "DEFAULT_SEARCH_CANDIDATE_POOL",
    "DEFAULT_SEARCH_ITERATIONS",
    "DEFAULT_SLOT_ITERATIONS",
    "HARD_NEGATIVE_TYPES",
    "INTENT_SLOTS",
    "PatientEncoder",
    "TheraComposeModel",
    "TheraComposeOutput",
    "aggregate_slot_utilities",
    "build_patient_event_sequences",
    "construct_hard_negative_sets",
    "encode_visit_event",
    "event_feature_dimension",
    "hard_negative_masks",
    "intent_coverage_diagnostic",
    "set_change_summary",
    "set_energy",
    "set_energy_batch",
    "structured_set_search",
    "target_sets_from_matrix",
    "theracompose_loss",
    "topk_set",
)
