"""MedState: persistent patient-specific medication identity states.

This is a throwaway pre-Idea architecture screen.  The only intended new
object is a medication-identity-specific latent state that is carried from a
visit to the next.  The stateless and persistent surfaces share the same
clinical reader, explicit causal medication-history features, relation layer,
state-update depth, objective, and decoder.

The module is import-safe on the Mac harness (NumPy/PyTorch are optional) and
does not load any dataset itself.  Dataset I/O and the Train/Gate01-Dev split
live in ``run_medstate.py``.
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
DEFAULT_STATE_DIM = 64
DEFAULT_HISTORY_FEATURES = 3
DEFAULT_THRESHOLD = 0.0
DEFAULT_NEAR_ZERO_CHANGE = 1e-3

VARIANTS = (
    "stateless_relational",
    "persistent_independent",
    "persistent_relational",
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
        raise RuntimeError("NumPy is required for MedState experiment execution")
    return np


def _require_torch() -> Any:
    if torch is None:
        raise RuntimeError("PyTorch is required for MedState experiment execution")
    return torch


def _hash_bucket(namespace: str, code: int, width: int) -> int:
    digest = hashlib.blake2b(f"{namespace}:{int(code)}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % width


@dataclass(frozen=True)
class PatientSequence:
    """One patient's chronological, target-aligned sequence.

    ``history_features`` and ``prior_active`` are constructed before the
    current visit is appended to history.  ``target_medications`` is retained
    for alignment/evaluation and is never part of the current-visit input.
    """

    patient_id: int
    diagnosis_codes: tuple[tuple[int, ...], ...]
    procedure_codes: tuple[tuple[int, ...], ...]
    history_features: tuple[tuple[tuple[float, ...], ...], ...]
    prior_active: tuple[tuple[bool, ...], ...]
    target_medications: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class PackedSequences:
    """Padded arrays consumed by the sequence model."""

    diagnosis_codes: Any
    diagnosis_mask: Any
    procedure_codes: Any
    procedure_mask: Any
    history_features: Any
    prior_active: Any
    targets: Any
    visit_mask: Any
    history_lengths: Any
    patient_ids: tuple[int, ...]


def build_patient_sequences(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_indices: Iterable[int],
) -> tuple[PatientSequence, ...]:
    """Build chronological patient sequences under the causal history rule."""

    sequences: list[PatientSequence] = []
    for patient_index in patient_indices:
        patient = records[int(patient_index)]
        diagnoses_rows: list[tuple[int, ...]] = []
        procedure_rows: list[tuple[int, ...]] = []
        history_rows: list[tuple[tuple[float, ...], ...]] = []
        active_rows: list[tuple[bool, ...]] = []
        target_rows: list[tuple[int, ...]] = []
        previous_medications: set[int] = set()
        prescription_counts = [0] * CANDIDATE_COUNT
        last_prescribed = [-1] * CANDIDATE_COUNT

        for visit_index, admission in enumerate(patient):
            diagnoses = tuple(sorted(int(code) for code in admission[0]))
            procedures = tuple(sorted(int(code) for code in admission[1]))
            medications = tuple(sorted(int(code) for code in admission[2]))
            if any(medication < 0 or medication >= CANDIDATE_COUNT for medication in medications):
                raise ValueError("target medication index is outside the 131-candidate vocabulary")

            denominator = float(max(1, visit_index))
            feature_rows: list[tuple[float, ...]] = []
            active_values: list[bool] = []
            for medication in range(CANDIDATE_COUNT):
                is_previous = medication in previous_medications
                frequency = prescription_counts[medication] / denominator
                recency = (
                    0.0
                    if last_prescribed[medication] < 0
                    else 1.0 / (1.0 + visit_index - last_prescribed[medication])
                )
                feature_rows.append((float(is_previous), float(frequency), float(recency)))
                active_values.append(prescription_counts[medication] > 0)

            diagnoses_rows.append(diagnoses)
            procedure_rows.append(procedures)
            history_rows.append(tuple(feature_rows))
            active_rows.append(tuple(active_values))
            target_rows.append(medications)

            # This update happens after the current row has been materialized.
            previous_medications = set(medications)
            for medication in medications:
                prescription_counts[medication] += 1
                last_prescribed[medication] = visit_index

        sequences.append(
            PatientSequence(
                patient_id=int(patient_index),
                diagnosis_codes=tuple(diagnoses_rows),
                procedure_codes=tuple(procedure_rows),
                history_features=tuple(history_rows),
                prior_active=tuple(active_rows),
                target_medications=tuple(target_rows),
            )
        )
    if not sequences:
        raise ValueError("patient selection produced no sequences")
    return tuple(sequences)


def pack_patient_sequences(
    sequences: Sequence[PatientSequence],
    *,
    max_diagnoses: int | None = None,
    max_procedures: int | None = None,
    diagnosis_hash_width: int = DEFAULT_DIAGNOSIS_HASH_WIDTH,
    procedure_hash_width: int = DEFAULT_PROCEDURE_HASH_WIDTH,
) -> PackedSequences:
    """Pad sequences and hash code tokens without exposing current labels."""

    numpy = _require_numpy()
    values = tuple(sequences)
    if not values:
        raise ValueError("cannot pack an empty sequence collection")
    if diagnosis_hash_width <= 0 or procedure_hash_width <= 0:
        raise ValueError("code hash widths must be positive")
    inferred_diagnoses = max(
        (len(row) for sequence in values for row in sequence.diagnosis_codes),
        default=1,
    )
    inferred_procedures = max(
        (len(row) for sequence in values for row in sequence.procedure_codes),
        default=1,
    )
    max_visits = max(len(sequence.diagnosis_codes) for sequence in values)
    max_diagnoses = max(1, inferred_diagnoses if max_diagnoses is None else int(max_diagnoses))
    max_procedures = max(1, inferred_procedures if max_procedures is None else int(max_procedures))
    if any(len(row) > max_diagnoses for sequence in values for row in sequence.diagnosis_codes):
        raise ValueError("max_diagnoses is smaller than an observed diagnosis set")
    if any(len(row) > max_procedures for sequence in values for row in sequence.procedure_codes):
        raise ValueError("max_procedures is smaller than an observed procedure set")

    shape = (len(values), max_visits)
    diagnosis_codes = numpy.zeros((*shape, max_diagnoses), dtype=numpy.int64)
    diagnosis_mask = numpy.zeros((*shape, max_diagnoses), dtype=numpy.bool_)
    procedure_codes = numpy.zeros((*shape, max_procedures), dtype=numpy.int64)
    procedure_mask = numpy.zeros((*shape, max_procedures), dtype=numpy.bool_)
    history_features = numpy.zeros(
        (*shape, CANDIDATE_COUNT, DEFAULT_HISTORY_FEATURES), dtype=numpy.float32
    )
    prior_active = numpy.zeros((*shape, CANDIDATE_COUNT), dtype=numpy.bool_)
    targets = numpy.zeros((*shape, CANDIDATE_COUNT), dtype=numpy.float32)
    visit_mask = numpy.zeros(shape, dtype=numpy.bool_)
    history_lengths = numpy.zeros(shape, dtype=numpy.int64)

    for patient_row, sequence in enumerate(values):
        visit_count = len(sequence.diagnosis_codes)
        visit_mask[patient_row, :visit_count] = True
        history_lengths[patient_row, :visit_count] = numpy.arange(visit_count, dtype=numpy.int64)
        for visit_index in range(visit_count):
            for code_index, code in enumerate(sequence.diagnosis_codes[visit_index]):
                diagnosis_codes[patient_row, visit_index, code_index] = _hash_bucket(
                    "current-diagnosis", code, diagnosis_hash_width
                )
                diagnosis_mask[patient_row, visit_index, code_index] = True
            for code_index, code in enumerate(sequence.procedure_codes[visit_index]):
                procedure_codes[patient_row, visit_index, code_index] = _hash_bucket(
                    "current-procedure", code, procedure_hash_width
                )
                procedure_mask[patient_row, visit_index, code_index] = True
            history_features[patient_row, visit_index] = numpy.asarray(
                sequence.history_features[visit_index], dtype=numpy.float32
            )
            prior_active[patient_row, visit_index] = numpy.asarray(
                sequence.prior_active[visit_index], dtype=numpy.bool_
            )
            for medication in sequence.target_medications[visit_index]:
                targets[patient_row, visit_index, medication] = 1.0

    return PackedSequences(
        diagnosis_codes=diagnosis_codes,
        diagnosis_mask=diagnosis_mask,
        procedure_codes=procedure_codes,
        procedure_mask=procedure_mask,
        history_features=history_features,
        prior_active=prior_active,
        targets=targets,
        visit_mask=visit_mask,
        history_lengths=history_lengths,
        patient_ids=tuple(sequence.patient_id for sequence in values),
    )


def build_relation_features(ehr_adjacency: Any, ddi_adjacency: Any) -> tuple[Any, Any]:
    """Normalize Train-derived EHR/DDI matrices and return their union mask."""

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
    """Return the visit-macro metrics used by the single MedState screen."""

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


def _masked_mean(values: Any, mask: Any, dim: int) -> Any:
    weights = mask.to(dtype=values.dtype).unsqueeze(-1)
    return (values * weights).sum(dim=dim) / weights.sum(dim=dim).clamp_min(1.0)


if nn is not None:

    @dataclass(frozen=True)
    class MedStateOutput:
        """Sequence outputs and optional training loss."""

        logits: Any
        state_prev: Any | None
        state_pre: Any | None
        visit_mask: Any
        loss: Any | None

    class ClinicalEncoder(nn.Module):
        """Small current-visit diagnosis/procedure token encoder."""

        def __init__(
            self,
            diagnosis_hash_width: int,
            procedure_hash_width: int,
            state_dim: int,
        ) -> None:
            super().__init__()
            self.diagnosis_embedding = nn.Embedding(diagnosis_hash_width, state_dim)
            self.procedure_embedding = nn.Embedding(procedure_hash_width, state_dim)
            self.diagnosis_type = nn.Parameter(torch.zeros(state_dim))
            self.procedure_type = nn.Parameter(torch.zeros(state_dim))
            self.norm = nn.LayerNorm(state_dim)
            self.pool = nn.Sequential(
                nn.Linear(state_dim, state_dim), nn.GELU(), nn.Linear(state_dim, state_dim)
            )

        def forward(
            self,
            diagnosis_codes: Any,
            diagnosis_mask: Any,
            procedure_codes: Any,
            procedure_mask: Any,
        ) -> tuple[Any, Any, Any]:
            diagnosis = self.diagnosis_embedding(diagnosis_codes) + self.diagnosis_type
            procedures = self.procedure_embedding(procedure_codes) + self.procedure_type
            tokens = self.norm(torch.cat((diagnosis, procedures), dim=2))
            token_mask = torch.cat((diagnosis_mask, procedure_mask), dim=1).to(dtype=torch.bool)
            tokens = tokens * token_mask.unsqueeze(-1).to(dtype=tokens.dtype)
            pooled = self.pool(_masked_mean(tokens, token_mask, dim=1))
            return tokens, token_mask, pooled

    class RelationStateInteraction(nn.Module):
        """Exactly one patient-conditioned EHR/DDI state interaction layer."""

        RELATION_TYPES = 2

        def __init__(self, relation_features: Any, edge_mask: Any, state_dim: int) -> None:
            super().__init__()
            relation_tensor = torch.as_tensor(relation_features, dtype=torch.float32)
            mask_tensor = torch.as_tensor(edge_mask, dtype=torch.bool)
            expected = (CANDIDATE_COUNT, CANDIDATE_COUNT)
            if (
                tuple(relation_tensor.shape) != (*expected, self.RELATION_TYPES)
                or tuple(mask_tensor.shape) != expected
            ):
                raise ValueError("relation features must have shape [131, 131, 2]")
            self.query = nn.Linear(state_dim, state_dim, bias=False)
            self.key = nn.Linear(state_dim, state_dim, bias=False)
            self.evidence_query = nn.Linear(state_dim, state_dim, bias=False)
            self.evidence_key = nn.Linear(state_dim, state_dim, bias=False)
            self.context_query = nn.Linear(state_dim, state_dim, bias=False)
            self.context_key = nn.Linear(state_dim, state_dim, bias=False)
            self.relation_transforms = nn.Parameter(
                torch.randn(self.RELATION_TYPES, state_dim, state_dim) * (state_dim**-0.5)
            )
            self.relation_bias = nn.Parameter(torch.tensor([0.25, -0.25], dtype=torch.float32))
            self.output = nn.Linear(state_dim, state_dim)
            self.norm = nn.LayerNorm(state_dim)
            self.register_buffer("relation_features", relation_tensor)
            self.register_buffer("edge_mask", mask_tensor)

        def forward(self, state: Any, evidence: Any, h_current: Any) -> Any:
            query = (
                self.query(state)
                + self.evidence_query(evidence)
                + self.context_query(h_current).unsqueeze(1)
            )
            key = (
                self.key(state)
                + self.evidence_key(evidence)
                + self.context_key(h_current).unsqueeze(1)
            )
            scores = torch.matmul(query, key.transpose(1, 2)) / math.sqrt(float(query.shape[-1]))
            relation_bias = torch.einsum("ijr,r->ij", self.relation_features, self.relation_bias)
            scores = scores + relation_bias.unsqueeze(0)
            scores = scores.masked_fill(~self.edge_mask.unsqueeze(0), -1e4)
            attention = torch.softmax(scores, dim=-1)
            transformed = torch.einsum("bjd,rdh->bjrh", state, self.relation_transforms)
            pair_values = torch.einsum("ijr,bjrh->bijh", self.relation_features, transformed)
            message = torch.einsum("bij,bijh->bih", attention, pair_values)
            return self.norm(state + self.output(message))

    class MedStateModel(nn.Module):
        """Stateless/persistent medication-identity state surfaces."""

        def __init__(
            self,
            *,
            diagnosis_hash_width: int,
            procedure_hash_width: int,
            state_dim: int,
            relation_features: Any,
            edge_mask: Any,
            variant: str,
            history_feature_count: int = DEFAULT_HISTORY_FEATURES,
            detach_every_visit: bool = True,
        ) -> None:
            super().__init__()
            if variant not in VARIANTS:
                raise ValueError(f"unknown MedState variant: {variant}")
            if state_dim <= 0 or history_feature_count <= 0:
                raise ValueError("state dimension and history feature count must be positive")
            self.variant = variant
            self.state_dim = state_dim
            self.persistent = variant != "stateless_relational"
            self.relational = variant != "persistent_independent"
            self.detach_every_visit = bool(detach_every_visit)
            self.clinical_encoder = ClinicalEncoder(
                diagnosis_hash_width, procedure_hash_width, state_dim
            )
            self.medication_embeddings = nn.Parameter(
                torch.randn(CANDIDATE_COUNT, state_dim) * 0.02
            )
            self.state_init = nn.Sequential(
                nn.Linear(state_dim, state_dim), nn.Tanh(), nn.LayerNorm(state_dim)
            )
            self.current_query = nn.Linear(state_dim * 2, state_dim)
            self.current_key = nn.Linear(state_dim, state_dim, bias=False)
            self.current_value = nn.Linear(state_dim, state_dim, bias=False)
            self.pre_update = nn.GRUCell(state_dim * 2 + history_feature_count, state_dim)
            self.observed_embedding = nn.Linear(1, state_dim)
            self.observed_update = nn.GRUCell(state_dim, state_dim)
            self.score = nn.Sequential(
                nn.Linear(state_dim * 3, state_dim), nn.GELU(), nn.Linear(state_dim, 1)
            )
            self.interaction = (
                RelationStateInteraction(relation_features, edge_mask, state_dim)
                if self.relational
                else None
            )

        def initial_state(self) -> Any:
            """Return shared learned identity initialization ``s_0[i]``."""

            return self.state_init(self.medication_embeddings)

        def _read_current(
            self,
            tokens: Any,
            token_mask: Any,
            state_prev: Any,
        ) -> tuple[Any, Any]:
            batch_size = state_prev.shape[0]
            identity = self.medication_embeddings.unsqueeze(0).expand(batch_size, -1, -1)
            query = self.current_query(torch.cat((identity, state_prev), dim=-1))
            key = self.current_key(tokens)
            value = self.current_value(tokens)
            scores = torch.einsum("bmd,bld->bml", query, key) / math.sqrt(float(self.state_dim))
            scores = scores.masked_fill(~token_mask.unsqueeze(1), -1e4)
            attention = torch.softmax(scores, dim=-1)
            attention = attention * token_mask.unsqueeze(1).to(dtype=attention.dtype)
            attention = attention / attention.sum(dim=-1, keepdim=True).clamp_min(1e-6)
            evidence = torch.einsum("bml,bld->bmd", attention, value)
            return identity, evidence

        def forward(
            self,
            diagnosis_codes: Any,
            diagnosis_mask: Any,
            procedure_codes: Any,
            procedure_mask: Any,
            history_features: Any,
            visit_mask: Any,
            *,
            observed_targets: Any | None = None,
            collect_states: bool = False,
        ) -> MedStateOutput:
            """Predict visits, assimilating ``observed_targets`` only afterward.

            The order in each loop iteration is intentional: current evidence is
            read, ``s_pre`` and logits are produced, the per-visit BCE term is
            computed, and only then is ``observed_targets[:, t]`` passed to the
            post-prescription GRU for the next visit.
            """

            if diagnosis_codes.ndim != 3 or procedure_codes.ndim != 3:
                raise ValueError("current code tensors must have shape [patients, visits, tokens]")
            if history_features.ndim != 4 or history_features.shape[2] != CANDIDATE_COUNT:
                raise ValueError(
                    "history features must have shape [patients, visits, 131, features]"
                )
            if visit_mask.shape != diagnosis_codes.shape[:2]:
                raise ValueError("visit mask must align with patient and visit dimensions")
            if observed_targets is not None and observed_targets.shape != (
                diagnosis_codes.shape[0],
                diagnosis_codes.shape[1],
                CANDIDATE_COUNT,
            ):
                raise ValueError("observed targets must have shape [patients, visits, 131]")
            batch_size, time_steps = diagnosis_codes.shape[:2]
            if self.persistent and observed_targets is None and time_steps > 1:
                raise ValueError("persistent sequence prediction requires causal observed targets")

            base_state = self.initial_state().unsqueeze(0).expand(batch_size, -1, -1)
            state = base_state
            logits_rows: list[Any] = []
            prev_rows: list[Any] = []
            pre_rows: list[Any] = []
            loss_total: Any | None = None
            loss_count = 0.0
            for visit_index in range(time_steps):
                active = visit_mask[:, visit_index].to(dtype=torch.bool)
                state_prev = base_state if not self.persistent else state
                if self.persistent and self.detach_every_visit and visit_index > 0:
                    state_prev = state_prev.detach()
                tokens, token_mask, h_current = self.clinical_encoder(
                    diagnosis_codes[:, visit_index],
                    diagnosis_mask[:, visit_index],
                    procedure_codes[:, visit_index],
                    procedure_mask[:, visit_index],
                )
                identity, evidence = self._read_current(tokens, token_mask, state_prev)
                if self.interaction is None:
                    interaction_message = torch.zeros_like(state_prev)
                else:
                    interaction_state = self.interaction(state_prev, evidence, h_current)
                    interaction_message = interaction_state - state_prev
                update_input = torch.cat(
                    (evidence, interaction_message, history_features[:, visit_index]), dim=-1
                )
                state_pre = self.pre_update(
                    update_input.reshape(-1, update_input.shape[-1]),
                    state_prev.reshape(-1, state_prev.shape[-1]),
                ).reshape(batch_size, CANDIDATE_COUNT, self.state_dim)
                logits = self.score(torch.cat((state_pre, evidence, identity), dim=-1)).squeeze(-1)
                logits_rows.append(logits)
                if collect_states:
                    prev_rows.append(state_prev)
                    pre_rows.append(state_pre)

                # Compute this visit's loss before allowing y_t into state.
                if observed_targets is not None:
                    target = observed_targets[:, visit_index]
                    element_loss = F.binary_cross_entropy_with_logits(
                        logits, target, reduction="none"
                    )
                    active_loss = element_loss * active.unsqueeze(-1).to(element_loss.dtype)
                    loss_total = (
                        active_loss.sum() if loss_total is None else loss_total + active_loss.sum()
                    )
                    loss_count += float(active.sum().detach().cpu()) * CANDIDATE_COUNT

                if self.persistent and observed_targets is not None:
                    observed = self.observed_embedding(
                        observed_targets[:, visit_index].unsqueeze(-1)
                    )
                    next_state = self.observed_update(
                        observed.reshape(-1, self.state_dim),
                        state_pre.reshape(-1, self.state_dim),
                    ).reshape(batch_size, CANDIDATE_COUNT, self.state_dim)
                    if self.detach_every_visit:
                        next_state = next_state.detach()
                    state = torch.where(active[:, None, None], next_state, state)

            logits_tensor = torch.stack(logits_rows, dim=1)
            loss = None if loss_total is None else loss_total / max(1.0, loss_count)
            return MedStateOutput(
                logits=logits_tensor,
                state_prev=torch.stack(prev_rows, dim=1) if collect_states else None,
                state_pre=torch.stack(pre_rows, dim=1) if collect_states else None,
                visit_mask=visit_mask,
                loss=loss,
            )

else:

    @dataclass(frozen=True)
    class MedStateOutput:  # type: ignore[no-redef]
        logits: Any = None
        state_prev: Any | None = None
        state_pre: Any | None = None
        visit_mask: Any = None
        loss: Any | None = None

    class MedStateModel:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for MedState execution")


__all__ = (
    "CANDIDATE_COUNT",
    "DEFAULT_DIAGNOSIS_HASH_WIDTH",
    "DEFAULT_HISTORY_FEATURES",
    "DEFAULT_NEAR_ZERO_CHANGE",
    "DEFAULT_PROCEDURE_HASH_WIDTH",
    "DEFAULT_STATE_DIM",
    "DEFAULT_THRESHOLD",
    "VARIANTS",
    "MedStateModel",
    "MedStateOutput",
    "PackedSequences",
    "PatientSequence",
    "build_patient_sequences",
    "build_relation_features",
    "evaluate_surface",
    "metric_average_precision",
    "pack_patient_sequences",
    "target_sets_from_matrix",
    "threshold_sets",
)
