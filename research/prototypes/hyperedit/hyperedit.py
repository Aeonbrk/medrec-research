"""HyperEdit-MR: a small retrieval-conditioned list-wise prescription editor.

The prototype deliberately keeps the public interface narrow: build a train-only
retrieval index, turn one visit into candidate-node features, train a bounded
ADD/REMOVE/STOP editor, and evaluate the resulting medication sets.  PyTorch is
optional at import time so the Mac harness can run the leakage and trajectory
tests without installing the remote MoleRec environment.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

CANDIDATE_COUNT = 131
DEFAULT_RETRIEVAL_WIDTH = 256
DEFAULT_TOP_K = 16
DEFAULT_MAX_STEPS = 32
DEFAULT_FUSION_ALPHA = 1.0

try:  # pragma: no cover - exercised in the remote MoleRec environment.
    import numpy as np
except ImportError:  # pragma: no cover - the Mac harness intentionally has no numpy.
    np = None  # type: ignore[assignment]

try:  # pragma: no cover - exercised in the remote MoleRec environment.
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - the Mac harness intentionally has no torch.
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    F = None  # type: ignore[assignment]


@dataclass(frozen=True)
class VisitContext:
    """A target visit with target-free retrieval features and optional labels."""

    patient_id: int | str
    visit_id: str
    diagnosis_codes: tuple[int, ...]
    procedure_codes: tuple[int, ...]
    historical_medications: tuple[int, ...]
    target_medications: tuple[int, ...] = ()

    def retrieval_tokens(self) -> tuple[str, ...]:
        """Return a typed bag-of-codes representation for visit retrieval."""

        tokens = [f"d:{code}" for code in self.diagnosis_codes]
        tokens.extend(f"p:{code}" for code in self.procedure_codes)
        return tuple(sorted(set(tokens)))


@dataclass(frozen=True)
class RetrievalFeatures:
    """Weighted support and co-support returned for a batch of visits."""

    support: Any
    co_support: Any
    neighbor_indices: tuple[tuple[int, ...], ...]
    similarities: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class RetrievalIndex:
    """Train-only visits, projections, and medication targets."""

    contexts: tuple[VisitContext, ...]
    projections: Any
    target_matrix: Any
    patient_ids: tuple[int | str, ...]


def build_visit_contexts(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_indices: Iterable[int],
) -> tuple[VisitContext, ...]:
    """Materialize visits in record order without exposing current medications."""

    contexts: list[VisitContext] = []
    for patient_index in patient_indices:
        patient = records[patient_index]
        diagnosis_history: set[int] = set()
        procedure_history: set[int] = set()
        medication_history: set[int] = set()
        for visit_index, admission in enumerate(patient):
            current_diagnoses = tuple(sorted(int(code) for code in admission[0]))
            current_procedures = tuple(sorted(int(code) for code in admission[1]))
            contexts.append(
                VisitContext(
                    patient_id=patient_index,
                    visit_id=f"{patient_index}:{visit_index}",
                    diagnosis_codes=tuple(sorted(diagnosis_history | set(current_diagnoses))),
                    procedure_codes=tuple(sorted(procedure_history | set(current_procedures))),
                    historical_medications=tuple(sorted(medication_history)),
                    target_medications=tuple(sorted(int(code) for code in admission[2])),
                )
            )
            diagnosis_history.update(current_diagnoses)
            procedure_history.update(current_procedures)
            medication_history.update(int(code) for code in admission[2])
    return tuple(contexts)


def _require_numpy() -> Any:
    if np is None:
        raise RuntimeError("NumPy is required for retrieval and experiment execution")
    return np


def _token_bucket(token: str, width: int) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % width


def visit_projections(
    contexts: Sequence[VisitContext],
    *,
    width: int = DEFAULT_RETRIEVAL_WIDTH,
) -> Any:
    """Create deterministic, normalized diagnosis/procedure visit vectors."""

    numpy = _require_numpy()
    if width <= 0:
        raise ValueError("retrieval projection width must be positive")
    result = numpy.zeros((len(contexts), width), dtype=numpy.float32)
    for row, context in enumerate(contexts):
        for token in context.retrieval_tokens():
            result[row, _token_bucket(token, width)] += 1.0
        norm = float(numpy.linalg.norm(result[row]))
        if norm:
            result[row] /= norm
    return result


def _target_matrix(contexts: Sequence[VisitContext]) -> Any:
    numpy = _require_numpy()
    result = numpy.zeros((len(contexts), CANDIDATE_COUNT), dtype=numpy.float32)
    for row, context in enumerate(contexts):
        for medication in context.target_medications:
            if medication < 0 or medication >= CANDIDATE_COUNT:
                raise ValueError("target medication index is outside the 131-candidate vocabulary")
            result[row, medication] = 1.0
    return result


def build_retrieval_index(
    train_contexts: Sequence[VisitContext],
    *,
    width: int = DEFAULT_RETRIEVAL_WIDTH,
) -> RetrievalIndex:
    """Build an index whose rows are exclusively Train visits."""

    contexts = tuple(train_contexts)
    return RetrievalIndex(
        contexts=contexts,
        projections=visit_projections(contexts, width=width),
        target_matrix=_target_matrix(contexts),
        patient_ids=tuple(context.patient_id for context in contexts),
    )


def select_neighbors(
    similarities: Sequence[float],
    candidate_patient_ids: Sequence[int | str],
    query_patient_id: int | str,
    *,
    top_k: int = DEFAULT_TOP_K,
) -> tuple[int, ...]:
    """Select deterministic neighbors while excluding the entire query patient.

    Excluding every visit from the query patient is stricter than merely
    excluding future visits and prevents a train label from being copied through
    the retrieval surface.  Ties use the original visit order.
    """

    if len(similarities) != len(candidate_patient_ids):
        raise ValueError("similarities and candidate patient ids must have equal length")
    if top_k <= 0:
        return ()
    candidates = [
        (float(similarities[index]), index)
        for index, patient_id in enumerate(candidate_patient_ids)
        if patient_id != query_patient_id and math.isfinite(float(similarities[index]))
    ]
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return tuple(index for _, index in candidates[:top_k])


def retrieve_features(
    queries: Sequence[VisitContext],
    index: RetrievalIndex,
    *,
    top_k: int = DEFAULT_TOP_K,
    query_projections: Any | None = None,
    batch_size: int = 256,
) -> RetrievalFeatures:
    """Retrieve weighted medication support and pair co-support from Train only."""

    numpy = _require_numpy()
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    query_contexts = tuple(queries)
    projections = (
        visit_projections(query_contexts, width=int(index.projections.shape[1]))
        if query_projections is None
        else numpy.asarray(query_projections, dtype=numpy.float32)
    )
    if projections.shape != (len(query_contexts), index.projections.shape[1]):
        raise ValueError("query projections do not match query count and retrieval width")
    support = numpy.zeros((len(query_contexts), CANDIDATE_COUNT), dtype=numpy.float32)
    co_support = numpy.zeros(
        (len(query_contexts), CANDIDATE_COUNT, CANDIDATE_COUNT), dtype=numpy.float32
    )
    neighbors: list[tuple[int, ...]] = []
    neighbor_scores: list[tuple[float, ...]] = []
    all_patient_ids = index.patient_ids
    for start in range(0, len(query_contexts), batch_size):
        stop = min(start + batch_size, len(query_contexts))
        similarity_block = projections[start:stop] @ index.projections.T
        for local, query in enumerate(query_contexts[start:stop]):
            similarities = similarity_block[local]
            selected = select_neighbors(
                similarities,
                all_patient_ids,
                query.patient_id,
                top_k=min(top_k, len(index.contexts)),
            )
            selected_scores = tuple(float(similarities[item]) for item in selected)
            neighbors.append(selected)
            neighbor_scores.append(selected_scores)
            if not selected:
                continue
            weights = numpy.maximum(numpy.asarray(selected_scores, dtype=numpy.float32), 0.0)
            weights += numpy.float32(1e-6)
            weights /= weights.sum()
            targets = index.target_matrix[list(selected)]
            support[start + local] = weights @ targets
            co_support[start + local] = numpy.einsum("k,ki,kj->ij", weights, targets, targets)
    return RetrievalFeatures(
        support=support,
        co_support=co_support,
        neighbor_indices=tuple(neighbors),
        similarities=tuple(neighbor_scores),
    )


def historical_support(contexts: Sequence[VisitContext]) -> Any:
    """Return per-medication historical support without reading current labels."""

    numpy = _require_numpy()
    result = numpy.zeros((len(contexts), CANDIDATE_COUNT), dtype=numpy.float32)
    for row, context in enumerate(contexts):
        for medication in context.historical_medications:
            if 0 <= medication < CANDIDATE_COUNT:
                result[row, medication] = 1.0
    return result


def backbone_sets(scores: Any) -> tuple[frozenset[int], ...]:
    """Materialize the frozen MoleRec set at the sigmoid half threshold."""

    numpy = _require_numpy()
    values = numpy.asarray(scores)
    if values.ndim != 2 or values.shape[1] != CANDIDATE_COUNT:
        raise ValueError("MoleRec scores must have shape [visits, 131]")
    return tuple(frozenset(int(index) for index in numpy.flatnonzero(row >= 0.0)) for row in values)


def retrieval_fusion_scores(
    scores: Any,
    support: Any,
    *,
    alpha: float = DEFAULT_FUSION_ALPHA,
) -> Any:
    """Fuse normalized retrieval support into frozen MoleRec logits."""

    numpy = _require_numpy()
    score_values = numpy.asarray(scores, dtype=numpy.float32)
    support_values = numpy.asarray(support, dtype=numpy.float32)
    if score_values.shape != support_values.shape or score_values.shape[1] != CANDIDATE_COUNT:
        raise ValueError(
            "backbone scores and retrieval support must have the same [visits, 131] shape"
        )
    if not math.isfinite(float(alpha)):
        raise ValueError("fusion alpha must be finite")
    return score_values + float(alpha) * (support_values - 0.5)


def edit_trajectory(
    initial_set: Iterable[int],
    target_set: Iterable[int],
    *,
    candidate_count: int = CANDIDATE_COUNT,
) -> tuple[int, ...]:
    """Return canonical REMOVE-then-ADD actions followed by STOP.

    Action ids are ``ADD(i) == i``, ``REMOVE(i) == candidate_count + i``, and
    ``STOP == 2 * candidate_count``.
    """

    initial = {int(item) for item in initial_set}
    target = {int(item) for item in target_set}
    if any(item < 0 or item >= candidate_count for item in initial | target):
        raise ValueError("edit set contains an out-of-range medication index")
    removals = sorted(initial - target)
    additions = sorted(target - initial)
    return (
        tuple(candidate_count + item for item in removals)
        + tuple(additions)
        + (2 * candidate_count,)
    )


def apply_edit_action(
    current_set: Iterable[int],
    action: int,
    *,
    candidate_count: int = CANDIDATE_COUNT,
) -> frozenset[int]:
    """Apply one valid editor action and reject invalid ADD/REMOVE transitions."""

    current = set(int(item) for item in current_set)
    stop = 2 * candidate_count
    if action == stop:
        return frozenset(current)
    if action < 0 or action >= stop:
        raise ValueError("unknown editor action")
    if action < candidate_count:
        if action in current:
            raise ValueError("cannot ADD a medication already in the set")
        current.add(action)
    else:
        medication = action - candidate_count
        if medication not in current:
            raise ValueError("cannot REMOVE a medication absent from the set")
        current.remove(medication)
    return frozenset(current)


def build_node_features(
    scores: Any,
    embeddings: Any,
    retrieval_support_values: Any,
    historical_support_values: Any,
) -> Any:
    """Assemble frozen node signals plus the baseline set indicator."""

    numpy = _require_numpy()
    score_values = numpy.asarray(scores, dtype=numpy.float32)
    embedding_values = numpy.asarray(embeddings, dtype=numpy.float32)
    retrieval_values = numpy.asarray(retrieval_support_values, dtype=numpy.float32)
    history_values = numpy.asarray(historical_support_values, dtype=numpy.float32)
    if score_values.ndim != 2 or score_values.shape[1] != CANDIDATE_COUNT:
        raise ValueError("scores must have shape [visits, 131]")
    if embedding_values.ndim != 3 or embedding_values.shape[:2] != score_values.shape:
        raise ValueError("embeddings must have shape [visits, 131, width]")
    for name, values in (("retrieval", retrieval_values), ("historical", history_values)):
        if values.shape != score_values.shape:
            raise ValueError(f"{name} support must have shape [visits, 131]")
    base = (score_values >= 0.0).astype(numpy.float32)
    context_projection = embedding_values.mean(axis=1, keepdims=True)
    context_projection = numpy.broadcast_to(context_projection, embedding_values.shape)
    scalar_features = numpy.stack(
        (numpy.clip(score_values, -12.0, 12.0) / 4.0, retrieval_values, history_values, base),
        axis=-1,
    )
    return numpy.concatenate(
        (scalar_features, embedding_values / 4.0, context_projection / 4.0), axis=-1
    )


def metric_average_precision(target: Iterable[int], scores: Sequence[float]) -> float:
    """Compute one visit's average precision with deterministic score ties."""

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


def evaluate_sets(
    targets: Sequence[Iterable[int]],
    predictions: Sequence[Iterable[int]],
    scores: Any,
    ddi: Any,
) -> dict[str, float]:
    """Return the requested visit-macro metrics for one prediction surface."""

    numpy = _require_numpy()
    score_values = numpy.asarray(scores)
    if len(targets) != len(predictions) or score_values.shape != (len(targets), CANDIDATE_COUNT):
        raise ValueError("targets, predictions, and scores are not visit-aligned")
    ddi_values = numpy.asarray(ddi)
    if ddi_values.shape != (CANDIDATE_COUNT, CANDIDATE_COUNT):
        raise ValueError("DDI matrix must be 131 by 131")
    jaccard = 0.0
    f1 = 0.0
    prauc = 0.0
    count = 0
    ddi_count = 0
    pair_count = 0
    for target_raw, prediction_raw, score_row in zip(targets, predictions, score_values):  # noqa: B905
        target = {int(item) for item in target_raw}
        prediction = {int(item) for item in prediction_raw}
        intersection = len(target & prediction)
        union = len(target | prediction)
        jaccard += 1.0 if not union else intersection / union
        precision = (
            1.0
            if not prediction and not target
            else intersection / len(prediction)
            if prediction
            else 0.0
        )
        recall = (
            1.0 if not prediction and not target else intersection / len(target) if target else 0.0
        )
        f1 += 0.0 if precision + recall == 0.0 else 2 * precision * recall / (precision + recall)
        prauc += metric_average_precision(target, score_row)
        ordered = sorted(prediction)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                pair_count += 1
                ddi_count += int(bool(ddi_values[left, right]))
        count += 1
    if not count:
        raise ValueError("cannot evaluate an empty visit collection")
    return {
        "jaccard": jaccard / count,
        "f1": f1 / count,
        "prauc": prauc / count,
        "ddi": 0.0 if not pair_count else ddi_count / pair_count,
        "mean_medication_count": sum(len(set(item)) for item in predictions) / count,
    }


def set_change_summary(
    baseline: Sequence[Iterable[int]],
    edited: Sequence[Iterable[int]],
) -> dict[str, float]:
    """Summarize how much the editor actually changed the prescription sets."""

    if len(baseline) != len(edited) or not baseline:
        raise ValueError("baseline and edited sets must be non-empty and aligned")
    differences = [len(set(left) ^ set(right)) for left, right in zip(baseline, edited)]  # noqa: B905
    return {
        "changed_fraction": sum(value > 0 for value in differences) / len(differences),
        "mean_symmetric_difference": sum(differences) / len(differences),
    }


if nn is not None:

    class GraphInteractionEncoder(nn.Module):
        """Two scalar-attention message-passing layers over the 131-node graph."""

        def __init__(self, node_features: int, hidden_dim: int = 96, layers: int = 2) -> None:
            super().__init__()
            if layers != 2:
                raise ValueError("HyperEdit-MR v0 fixes the graph depth at two layers")
            self.input_projection = nn.Linear(node_features, hidden_dim)
            self.self_layers = nn.ModuleList(
                nn.Linear(hidden_dim, hidden_dim) for _ in range(layers)
            )
            self.message_layers = nn.ModuleList(
                nn.Linear(hidden_dim, hidden_dim) for _ in range(layers)
            )
            self.edge_weights = nn.Parameter(torch.tensor([0.35, 0.75, 0.35]))
            self.edge_bias = nn.Parameter(torch.tensor(0.1))

        def forward(
            self,
            node_features: Any,
            ddi: Any,
            co_support: Any,
            ehr_co_prescription: Any,
        ) -> Any:
            hidden = F.gelu(self.input_projection(node_features))
            batch_size = hidden.shape[0]
            edge_values = []
            for value in (ddi, co_support, ehr_co_prescription):
                tensor = value if isinstance(value, torch.Tensor) else torch.as_tensor(value)
                tensor = tensor.to(device=hidden.device, dtype=hidden.dtype)
                if tensor.ndim == 2:
                    tensor = tensor.unsqueeze(0).expand(batch_size, -1, -1)
                edge_values.append(tensor)
            edge_score = self.edge_bias
            for edge_index in range(len(edge_values)):
                weight = self.edge_weights[edge_index]
                value = edge_values[edge_index]
                edge_score = edge_score + weight * value
            attention = F.softplus(edge_score).clamp_min(1e-4)
            attention = attention / attention.sum(dim=-1, keepdim=True).clamp_min(1e-6)
            for layer_index in range(len(self.self_layers)):
                self_layer = self.self_layers[layer_index]
                message_layer = self.message_layers[layer_index]
                message = torch.bmm(attention, hidden)
                hidden = F.gelu(self_layer(hidden) + message_layer(message))
            return hidden

    class HyperEditMR(nn.Module):
        """Graph encoder plus a bounded supervised ADD/REMOVE/STOP editor."""

        def __init__(
            self,
            node_features: int,
            *,
            hidden_dim: int = 96,
            max_steps: int = DEFAULT_MAX_STEPS,
        ) -> None:
            super().__init__()
            if max_steps <= 0:
                raise ValueError("max_steps must be positive")
            self.max_steps = max_steps
            self.encoder = GraphInteractionEncoder(node_features, hidden_dim=hidden_dim)
            self.set_head = nn.Linear(hidden_dim, 1)
            editor_input = hidden_dim + 2
            self.add_head = nn.Sequential(
                nn.Linear(editor_input, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, 1)
            )
            self.remove_head = nn.Sequential(
                nn.Linear(editor_input, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, 1)
            )
            self.stop_head = nn.Sequential(
                nn.Linear(hidden_dim + 1, hidden_dim // 2),
                nn.GELU(),
                nn.Linear(hidden_dim // 2, 1),
            )

        def encode(self, node_features: Any, ddi: Any, co_support: Any, ehr: Any) -> Any:
            return self.encoder(node_features, ddi, co_support, ehr)

        def _action_logits(self, hidden: Any, state: Any, set_logits: Any) -> Any:
            set_probability = torch.sigmoid(set_logits)
            repeated_state = state.unsqueeze(-1)
            repeated_probability = set_probability.unsqueeze(-1)
            editor_input = torch.cat((hidden, repeated_state, repeated_probability), dim=-1)
            add_logits = self.add_head(editor_input).squeeze(-1)
            remove_logits = self.remove_head(editor_input).squeeze(-1)
            summary = torch.cat(
                (hidden.mean(dim=1), state.mean(dim=1, keepdim=True)),
                dim=-1,
            )
            stop_logits = self.stop_head(summary)
            logits = torch.cat((add_logits, remove_logits, stop_logits), dim=-1)
            valid = torch.cat((1.0 - state, state, torch.ones_like(stop_logits)), dim=-1)
            return logits.masked_fill(valid <= 0.0, -1e4)

        def forward_sequence(
            self,
            node_features: Any,
            initial_set: Any,
            ddi: Any,
            co_support: Any,
            ehr: Any,
            *,
            teacher_actions: Any | None = None,
        ) -> tuple[Any, Any]:
            hidden = self.encode(node_features, ddi, co_support, ehr)
            set_logits = self.set_head(hidden).squeeze(-1)
            state = initial_set.to(device=hidden.device, dtype=hidden.dtype)
            sequence = []
            for step in range(self.max_steps):
                logits = self._action_logits(hidden, state, set_logits)
                sequence.append(logits)
                if teacher_actions is None:
                    action = logits.argmax(dim=-1)
                else:
                    action = teacher_actions[:, step].clamp_min(0)
                stop = 2 * CANDIDATE_COUNT
                adds = (action < CANDIDATE_COUNT).to(state.dtype)
                removes = ((action >= CANDIDATE_COUNT) & (action < stop)).to(state.dtype)
                medication = torch.where(action < CANDIDATE_COUNT, action, action - CANDIDATE_COUNT)
                one_hot = F.one_hot(medication.clamp(0, CANDIDATE_COUNT - 1), CANDIDATE_COUNT).to(
                    state.dtype
                )
                state = state * (1.0 - removes.unsqueeze(-1) * one_hot)
                state = state + (1.0 - state) * adds.unsqueeze(-1) * one_hot
            return torch.stack(sequence, dim=1), set_logits

        @torch.no_grad()
        def predict(
            self,
            node_features: Any,
            initial_set: Any,
            ddi: Any,
            co_support: Any,
            ehr: Any,
        ) -> tuple[tuple[frozenset[int], ...], Any, Any]:
            hidden = self.encode(node_features, ddi, co_support, ehr)
            set_logits = self.set_head(hidden).squeeze(-1)
            state = initial_set.to(device=hidden.device, dtype=hidden.dtype)
            desired = (set_logits >= 0.0).to(state.dtype)
            stopped = torch.zeros(state.shape[0], dtype=torch.bool, device=state.device)
            for _ in range(self.max_steps):
                logits = self._action_logits(hidden, state, set_logits)
                remaining = (desired != state).any(dim=1)
                toward = torch.cat(
                    (
                        (1.0 - state) * desired,
                        state * (1.0 - desired),
                        torch.ones_like(state[:, :1]),
                    ),
                    dim=-1,
                )
                force_edit = remaining & ~stopped
                logits = logits.masked_fill((toward <= 0.0) & force_edit.unsqueeze(-1), -1e4)
                logits[:, 2 * CANDIDATE_COUNT] = torch.where(
                    force_edit,
                    torch.full_like(logits[:, 2 * CANDIDATE_COUNT], -1e4),
                    logits[:, 2 * CANDIDATE_COUNT],
                )
                action = logits.argmax(dim=-1)
                action = torch.where(stopped, torch.full_like(action, 2 * CANDIDATE_COUNT), action)
                newly_stopped = action == 2 * CANDIDATE_COUNT
                stopped = stopped | newly_stopped
                adds = (action < CANDIDATE_COUNT).to(state.dtype)
                removes = ((action >= CANDIDATE_COUNT) & (action < 2 * CANDIDATE_COUNT)).to(
                    state.dtype
                )
                medication = torch.where(action < CANDIDATE_COUNT, action, action - CANDIDATE_COUNT)
                one_hot = F.one_hot(medication.clamp(0, CANDIDATE_COUNT - 1), CANDIDATE_COUNT).to(
                    state.dtype
                )
                state = state * (1.0 - removes.unsqueeze(-1) * one_hot)
                state = state + (1.0 - state) * adds.unsqueeze(-1) * one_hot
                if bool(stopped.all()):
                    break
            predictions = tuple(
                frozenset(
                    int(index)
                    for index in torch.nonzero(row > 0.5, as_tuple=False).flatten().tolist()
                )
                for row in state
            )
            return predictions, set_logits, state

    def hyperedit_loss(
        action_logits: Any,
        actions: Any,
        set_logits: Any,
        targets: Any,
        ddi: Any,
        *,
        lambda_set: float = 1.0,
        lambda_ddi: float = 0.05,
    ) -> tuple[Any, dict[str, float]]:
        """Combine action CE, final set BCE, and a differentiable DDI penalty."""

        action_loss = F.cross_entropy(
            action_logits.reshape(-1, action_logits.shape[-1]),
            actions.reshape(-1),
            ignore_index=-100,
        )
        set_loss = F.binary_cross_entropy_with_logits(set_logits, targets)
        probabilities = torch.sigmoid(set_logits)
        ddi_tensor = ddi if isinstance(ddi, torch.Tensor) else torch.as_tensor(ddi)
        ddi_tensor = ddi_tensor.to(device=probabilities.device, dtype=probabilities.dtype)
        pair_mass = probabilities.unsqueeze(1) * probabilities.unsqueeze(2) * ddi_tensor
        ddi_loss = pair_mass.sum() / max(1, probabilities.shape[0] * CANDIDATE_COUNT)
        total = action_loss + float(lambda_set) * set_loss + float(lambda_ddi) * ddi_loss
        return total, {
            "action_ce": float(action_loss.detach().cpu()),
            "set_bce": float(set_loss.detach().cpu()),
            "ddi_penalty": float(ddi_loss.detach().cpu()),
            "total": float(total.detach().cpu()),
        }

else:

    class GraphInteractionEncoder:  # type: ignore[no-redef]
        """Import-safe placeholder when PyTorch is unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for HyperEdit-MR execution")

    class HyperEditMR:  # type: ignore[no-redef]
        """Import-safe placeholder when PyTorch is unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for HyperEdit-MR execution")

    def hyperedit_loss(*_args: Any, **_kwargs: Any) -> tuple[Any, dict[str, float]]:
        raise RuntimeError("PyTorch is required for HyperEdit-MR execution")


__all__ = (
    "CANDIDATE_COUNT",
    "DEFAULT_MAX_STEPS",
    "DEFAULT_RETRIEVAL_WIDTH",
    "DEFAULT_TOP_K",
    "GraphInteractionEncoder",
    "HyperEditMR",
    "RetrievalFeatures",
    "RetrievalIndex",
    "VisitContext",
    "apply_edit_action",
    "backbone_sets",
    "build_node_features",
    "build_retrieval_index",
    "build_visit_contexts",
    "edit_trajectory",
    "evaluate_sets",
    "historical_support",
    "hyperedit_loss",
    "metric_average_precision",
    "retrieval_fusion_scores",
    "retrieve_features",
    "select_neighbors",
    "set_change_summary",
    "visit_projections",
)
