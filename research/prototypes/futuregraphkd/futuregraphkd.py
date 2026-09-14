"""FutureGraphKD-v0: privileged next-state teacher, deployable graph student.

The prototype keeps the interface deliberately narrow.  ``build_visit_features``
constructs current/history features plus a separate immediate-next
diagnosis/procedure tensor.  ``FutureGraphKDModel`` ignores that tensor for a
Student and consumes it through one small projection for a Teacher.  Both then
use the same two-layer patient-conditioned medication interaction core.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

CANDIDATE_COUNT = 131
DEFAULT_CODE_HASH_WIDTH = 64
DEFAULT_CONTEXT_PROJECTION = 32
DEFAULT_FUTURE_PROJECTION = 16
DEFAULT_HIDDEN_DIM = 96
DEFAULT_GRAPH_LAYERS = 2
DEFAULT_KD_WEIGHT = 0.5
DEFAULT_HIDDEN_WEIGHT = 0.05

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
        raise RuntimeError("NumPy is required for FutureGraphKD experiment execution")
    return np


def _hash_bucket(namespace: str, code: int, width: int) -> int:
    digest = hashlib.blake2b(f"{namespace}:{int(code)}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % width


def context_feature_dimension(code_hash_width: int = DEFAULT_CODE_HASH_WIDTH) -> int:
    if code_hash_width <= 0:
        raise ValueError("code hash width must be positive")
    return 4 * code_hash_width + CANDIDATE_COUNT + 1


def future_feature_dimension(code_hash_width: int = DEFAULT_CODE_HASH_WIDTH) -> int:
    if code_hash_width <= 0:
        raise ValueError("code hash width must be positive")
    return 2 * code_hash_width + 1


def _encode_current_context(
    current_diagnoses: Iterable[int],
    current_procedures: Iterable[int],
    historical_diagnoses: Iterable[int],
    historical_procedures: Iterable[int],
    historical_medications: Iterable[int],
    *,
    code_hash_width: int,
    history_depth: int,
) -> tuple[float, ...]:
    vector = [0.0] * context_feature_dimension(code_hash_width)
    for code in set(int(value) for value in current_diagnoses):
        vector[_hash_bucket("current-diagnosis", code, code_hash_width)] += 1.0
    for code in set(int(value) for value in current_procedures):
        vector[code_hash_width + _hash_bucket("current-procedure", code, code_hash_width)] += 1.0
    history_diagnosis_offset = 2 * code_hash_width
    history_procedure_offset = 3 * code_hash_width
    for code in set(int(value) for value in historical_diagnoses):
        vector[
            history_diagnosis_offset + _hash_bucket("history-diagnosis", code, code_hash_width)
        ] += 1.0
    for code in set(int(value) for value in historical_procedures):
        vector[
            history_procedure_offset + _hash_bucket("history-procedure", code, code_hash_width)
        ] += 1.0
    medication_offset = 4 * code_hash_width
    for medication in set(int(value) for value in historical_medications):
        if 0 <= medication < CANDIDATE_COUNT:
            vector[medication_offset + medication] = 1.0
    vector[-1] = min(float(history_depth) / 8.0, 1.0)
    return tuple(vector)


def _encode_future_state(
    diagnoses: Iterable[int],
    procedures: Iterable[int],
    *,
    code_hash_width: int,
) -> tuple[float, ...]:
    vector = [0.0] * future_feature_dimension(code_hash_width)
    for code in set(int(value) for value in diagnoses):
        vector[_hash_bucket("future-diagnosis", code, code_hash_width)] += 1.0
    for code in set(int(value) for value in procedures):
        vector[code_hash_width + _hash_bucket("future-procedure", code, code_hash_width)] += 1.0
    vector[-1] = 1.0
    return tuple(vector)


def build_visit_features(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_indices: Iterable[int],
    *,
    code_hash_width: int = DEFAULT_CODE_HASH_WIDTH,
) -> tuple[Any, Any, Any, tuple[tuple[int, int], ...]]:
    """Build aligned current/history and immediate-next-state features.

    The current feature row uses only codes and medications available before
    the decision.  The future row contains only the next visit's diagnoses and
    procedures; it is zero-filled, and marked unsupported, at a patient's last
    visit.  Current target medications and all future medications are excluded.
    """

    numpy = _require_numpy()
    if code_hash_width <= 0:
        raise ValueError("code hash width must be positive")
    current_rows: list[tuple[float, ...]] = []
    future_rows: list[tuple[float, ...]] = []
    supported: list[bool] = []
    visit_keys: list[tuple[int, int]] = []
    for patient_index in patient_indices:
        patient = records[int(patient_index)]
        historical_diagnoses: set[int] = set()
        historical_procedures: set[int] = set()
        historical_medications: set[int] = set()
        for visit_index, admission in enumerate(patient):
            diagnoses = tuple(sorted(int(value) for value in admission[0]))
            procedures = tuple(sorted(int(value) for value in admission[1]))
            current_rows.append(
                _encode_current_context(
                    diagnoses,
                    procedures,
                    historical_diagnoses,
                    historical_procedures,
                    historical_medications,
                    code_hash_width=code_hash_width,
                    history_depth=visit_index,
                )
            )
            if visit_index + 1 < len(patient):
                next_admission = patient[visit_index + 1]
                future_rows.append(
                    _encode_future_state(
                        next_admission[0],
                        next_admission[1],
                        code_hash_width=code_hash_width,
                    )
                )
                supported.append(True)
            else:
                future_rows.append(
                    tuple(0.0 for _ in range(future_feature_dimension(code_hash_width)))
                )
                supported.append(False)
            visit_keys.append((int(patient_index), visit_index))
            historical_diagnoses.update(diagnoses)
            historical_procedures.update(procedures)
            historical_medications.update(int(value) for value in admission[2])
    return (
        numpy.asarray(current_rows, dtype=numpy.float32),
        numpy.asarray(future_rows, dtype=numpy.float32),
        numpy.asarray(supported, dtype=numpy.bool_),
        tuple(visit_keys),
    )


def build_relation_features(ehr_adjacency: Any, ddi_adjacency: Any) -> Any:
    """Normalize the existing EHR and DDI matrices for graph message passing."""

    numpy = _require_numpy()
    expected = (CANDIDATE_COUNT, CANDIDATE_COUNT)
    ehr = numpy.asarray(ehr_adjacency, dtype=numpy.float32)
    ddi = numpy.asarray(ddi_adjacency, dtype=numpy.float32)
    if ehr.shape != expected or ddi.shape != expected:
        raise ValueError("EHR and DDI matrices must both be 131 by 131")
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
    return numpy.stack((ehr, ddi), axis=-1).astype(numpy.float32)


@dataclass(frozen=True)
class FutureGraphOutput:
    """Per-medication logits and final graph representations."""

    logits: Any
    hidden: Any


if nn is not None:

    class GraphInteractionCore(nn.Module):
        """The small two-layer patient-conditioned GraphRefine-style core."""

        def __init__(
            self,
            node_features: int,
            relation_features: Any,
            *,
            hidden_dim: int = DEFAULT_HIDDEN_DIM,
            layers: int = DEFAULT_GRAPH_LAYERS,
        ) -> None:
            super().__init__()
            if node_features <= 0 or hidden_dim <= 0 or layers != DEFAULT_GRAPH_LAYERS:
                raise ValueError("FutureGraphKD v0 fixes a positive two-layer graph core")
            relation_tensor = torch.as_tensor(relation_features, dtype=torch.float32)
            if tuple(relation_tensor.shape) != (CANDIDATE_COUNT, CANDIDATE_COUNT, 2):
                raise ValueError("relation features must have shape [131, 131, 2]")
            self.input_projection = nn.Linear(node_features, hidden_dim)
            self.self_layers = nn.ModuleList(
                nn.Linear(hidden_dim, hidden_dim) for _ in range(layers)
            )
            self.message_layers = nn.ModuleList(
                nn.Linear(hidden_dim, hidden_dim) for _ in range(layers)
            )
            self.edge_weights = nn.Parameter(torch.tensor([0.35, 0.75]))
            self.edge_bias = nn.Parameter(torch.tensor(0.1))
            self.register_buffer("relation_features", relation_tensor)

        def forward(self, node_features: Any) -> Any:
            hidden = F.gelu(self.input_projection(node_features))
            edge_score = self.edge_bias
            edge_score = edge_score + self.edge_weights[0] * self.relation_features[..., 0]
            edge_score = edge_score + self.edge_weights[1] * self.relation_features[..., 1]
            attention = F.softplus(edge_score).clamp_min(1e-4)
            attention = attention / attention.sum(dim=-1, keepdim=True).clamp_min(1e-6)
            for self_layer, message_layer in zip(  # noqa: B905
                self.self_layers, self.message_layers
            ):
                message = torch.matmul(attention.unsqueeze(0), hidden)
                hidden = F.gelu(self_layer(hidden) + message_layer(message))
            return hidden

    class FutureGraphKDModel(nn.Module):
        """Student/Teacher model; ``use_future`` is the only privilege switch."""

        def __init__(
            self,
            embedding_dim: int,
            context_dim: int,
            future_dim: int,
            relation_features: Any,
            *,
            hidden_dim: int = DEFAULT_HIDDEN_DIM,
            use_future: bool = False,
        ) -> None:
            super().__init__()
            if embedding_dim <= 0 or context_dim <= 0 or future_dim <= 0:
                raise ValueError("feature dimensions must be positive")
            self.use_future = bool(use_future)
            self.context_projection = nn.Sequential(
                nn.Linear(context_dim, DEFAULT_CONTEXT_PROJECTION * 2),
                nn.GELU(),
                nn.Linear(DEFAULT_CONTEXT_PROJECTION * 2, DEFAULT_CONTEXT_PROJECTION),
            )
            if self.use_future:
                self.future_projection: nn.Module | None = nn.Sequential(
                    nn.Linear(future_dim, DEFAULT_FUTURE_PROJECTION * 2),
                    nn.GELU(),
                    nn.Linear(DEFAULT_FUTURE_PROJECTION * 2, DEFAULT_FUTURE_PROJECTION),
                )
            else:
                self.future_projection = None
            node_features = embedding_dim + 1 + DEFAULT_CONTEXT_PROJECTION
            if self.use_future:
                node_features += DEFAULT_FUTURE_PROJECTION
            self.graph = GraphInteractionCore(
                node_features,
                relation_features,
                hidden_dim=hidden_dim,
            )
            self.logit_head = nn.Linear(hidden_dim, 1)

        def forward(
            self,
            medication_embeddings: Any,
            backbone_scores: Any,
            context_features: Any,
            future_features: Any | None = None,
        ) -> FutureGraphOutput:
            batch = medication_embeddings.shape[0]
            if medication_embeddings.ndim != 3 or medication_embeddings.shape[1] != CANDIDATE_COUNT:
                raise ValueError(
                    "medication embeddings must have shape [batch, 131, embedding_dim]"
                )
            if backbone_scores.shape != (batch, CANDIDATE_COUNT):
                raise ValueError("backbone scores must have shape [batch, 131]")
            if context_features.ndim != 2 or context_features.shape[0] != batch:
                raise ValueError("context features must have shape [batch, context_dim]")
            context = self.context_projection(context_features)
            context = context.unsqueeze(1).expand(-1, CANDIDATE_COUNT, -1)
            pieces = [medication_embeddings, backbone_scores.unsqueeze(-1), context]
            if self.use_future:
                if future_features is None:
                    raise ValueError("Teacher requires immediate-next diagnosis/procedure features")
                if future_features.ndim != 2 or future_features.shape[0] != batch:
                    raise ValueError("future features must have shape [batch, future_dim]")
                assert self.future_projection is not None
                future = self.future_projection(future_features)
                pieces.append(future.unsqueeze(1).expand(-1, CANDIDATE_COUNT, -1))
            # A Student intentionally never reads future_features, making its
            # output deployable and invariant to any privileged tensor.
            hidden = self.graph(torch.cat(pieces, dim=-1))
            return FutureGraphOutput(self.logit_head(hidden).squeeze(-1), hidden)

    def future_graph_kd_loss(
        student_output: FutureGraphOutput,
        teacher_output: FutureGraphOutput,
        targets: Any,
        supported_mask: Any,
        *,
        kd_weight: float = DEFAULT_KD_WEIGHT,
        hidden_weight: float = DEFAULT_HIDDEN_WEIGHT,
    ) -> tuple[Any, dict[str, float]]:
        """Student BCE + supported Teacher BCE + logit KD + hidden MSE."""

        if kd_weight < 0.0 or hidden_weight < 0.0:
            raise ValueError("distillation weights must be non-negative")
        student_bce = F.binary_cross_entropy_with_logits(student_output.logits, targets)
        support = supported_mask.to(dtype=torch.bool)
        if bool(support.any()):
            teacher_bce = F.binary_cross_entropy_with_logits(
                teacher_output.logits[support], targets[support]
            )
            teacher_probability = torch.sigmoid(teacher_output.logits[support]).detach()
            logit_kd = F.binary_cross_entropy_with_logits(
                student_output.logits[support], teacher_probability
            )
            hidden_mse = F.mse_loss(
                student_output.hidden[support], teacher_output.hidden[support].detach()
            )
        else:
            teacher_bce = student_bce.new_zeros(())
            logit_kd = student_bce.new_zeros(())
            hidden_mse = student_bce.new_zeros(())
        total = (
            student_bce
            + teacher_bce
            + float(kd_weight) * logit_kd
            + float(hidden_weight) * hidden_mse
        )
        return total, {
            "student_bce": float(student_bce.detach().cpu()),
            "teacher_bce": float(teacher_bce.detach().cpu()),
            "logit_kd": float(logit_kd.detach().cpu()),
            "hidden_mse": float(hidden_mse.detach().cpu()),
            "total": float(total.detach().cpu()),
        }

else:

    class GraphInteractionCore:  # type: ignore[no-redef]
        """Import-safe placeholder when PyTorch is unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for FutureGraphKD execution")

    class FutureGraphKDModel:  # type: ignore[no-redef]
        """Import-safe placeholder when PyTorch is unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for FutureGraphKD execution")

    def future_graph_kd_loss(*_args: Any, **_kwargs: Any) -> tuple[Any, dict[str, float]]:
        raise RuntimeError("PyTorch is required for FutureGraphKD execution")


__all__ = (
    "CANDIDATE_COUNT",
    "DEFAULT_CODE_HASH_WIDTH",
    "DEFAULT_GRAPH_LAYERS",
    "DEFAULT_HIDDEN_DIM",
    "DEFAULT_HIDDEN_WEIGHT",
    "DEFAULT_KD_WEIGHT",
    "FutureGraphKDModel",
    "FutureGraphOutput",
    "GraphInteractionCore",
    "build_relation_features",
    "build_visit_features",
    "context_feature_dimension",
    "future_feature_dimension",
    "future_graph_kd_loss",
)
