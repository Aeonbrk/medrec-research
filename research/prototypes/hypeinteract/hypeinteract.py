"""Bounded HypeMed adaptation and patient-conditioned interaction screen.

This module keeps the scientific seams of the official HypeMed implementation
visible while avoiding optional ``torch_geometric``/FAISS dependencies.  The
adaptation has three pieces: separate visit hypergraphs with KHGE-style local
and global updates, contrastive node/visit/membership pretraining, and a
SimMR-style history/similar-visit medication scorer.  A small relation-aware
interaction model is provided for the conditional Stage-B screen.

The code is intentionally a prototype: all data loading and experiment policy
live in ``run_hypeinteract.py`` and no patient-level outputs are persisted in
the repository.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - exercised in the remote experiment environment.
    import numpy as np
except ImportError:  # pragma: no cover - the Mac harness need not install NumPy.
    np = None  # type: ignore[assignment]

try:  # pragma: no cover - exercised in the remote experiment environment.
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - the Mac harness need not install PyTorch.
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    F = None  # type: ignore[assignment]


CANDIDATE_COUNT = 131
DOMAIN_NAMES = ("diag", "proc", "med")
DEFAULT_DIM = 64
DEFAULT_HEADS = 4
DEFAULT_LAYERS = 2
DEFAULT_DROPOUT = 0.30
DEFAULT_RETRIEVAL_K = 10
DEFAULT_HISTORY_WINDOW = 3


def _require_numpy() -> Any:
    if np is None:
        raise RuntimeError("NumPy is required for HypeInteract experiment execution")
    return np


def _require_torch() -> Any:
    if torch is None:
        raise RuntimeError("PyTorch is required for HypeInteract experiment execution")
    return torch


@dataclass(frozen=True)
class VisitExample:
    """One current visit with only target-free current/history inputs."""

    patient_id: int
    visit_index: int
    diagnoses: tuple[int, ...]
    procedures: tuple[int, ...]
    historical_medications: tuple[int, ...]
    target_medications: tuple[int, ...]
    prior_visit_indices: tuple[int, ...]


@dataclass(frozen=True)
class HypergraphDomain:
    """Incidence structure for one entity domain.

    ``incidence`` has shape ``[num_nodes, num_train_visits]`` and each column
    is the visit-as-hyperedge representation used by HypeMed.
    """

    name: str
    num_nodes: int
    incidence: Any
    visit_keys: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class HypeMedRepresentations:
    """Frozen representation surfaces consumed by the recommendation scorer."""

    node_embeddings: dict[str, Any]
    edge_embeddings: dict[str, Any]
    current_diag_proc: Any
    historical_med: Any
    retrieval_med: Any
    patient_context: Any
    train_health: Any
    train_med_visit: Any
    retrieval_neighbors: tuple[tuple[int, ...], ...]


def build_visit_examples(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_indices: Iterable[int],
) -> tuple[VisitExample, ...]:
    """Flatten patients in record order without leaking the current target.

    Diagnosis/procedure tuples are current-event codes.  Historical medication
    support is materialized before the current admission is appended, so a
    caller can safely use these examples as model inputs.
    """

    examples: list[VisitExample] = []
    flat_index = 0
    for patient_id in patient_indices:
        patient = records[int(patient_id)]
        seen_meds: set = set()
        prior: list[int] = []
        for visit_index, admission in enumerate(patient):
            diagnoses = tuple(sorted(int(value) for value in admission[0]))
            procedures = tuple(sorted(int(value) for value in admission[1]))
            targets = tuple(sorted(int(value) for value in admission[2]))
            examples.append(
                VisitExample(
                    patient_id=int(patient_id),
                    visit_index=int(visit_index),
                    diagnoses=diagnoses,
                    procedures=procedures,
                    historical_medications=tuple(sorted(seen_meds)),
                    target_medications=targets,
                    prior_visit_indices=tuple(prior[-DEFAULT_HISTORY_WINDOW:]),
                )
            )
            prior.append(flat_index)
            flat_index += 1
            seen_meds.update(targets)
    return tuple(examples)


def build_domain_hypergraph(
    records: Sequence[Sequence[Sequence[Sequence[int]]]],
    patient_indices: Iterable[int],
    *,
    domain: str,
    num_nodes: int,
) -> HypergraphDomain:
    """Build a separate sparse visit hypergraph for diagnoses/procedures/meds."""

    if domain not in DOMAIN_NAMES:
        raise ValueError("domain must be one of diag, proc, med")
    rows: list[int] = []
    cols: list[int] = []
    visit_keys: list[tuple[int, int]] = []
    edge_index = 0
    for patient_id in patient_indices:
        for visit_index, admission in enumerate(records[int(patient_id)]):
            values = admission[DOMAIN_NAMES.index(domain)]
            unique_values = sorted(set(int(value) for value in values))
            if not unique_values:
                # Canonical MIMIC-III visits are non-empty in all three domains,
                # but retaining a self-contained edge makes the adapter robust.
                unique_values = [0]
            for value in unique_values:
                if value < 0 or value >= num_nodes:
                    raise ValueError("hypergraph code index is outside the vocabulary")
                rows.append(value)
                cols.append(edge_index)
            visit_keys.append((int(patient_id), int(visit_index)))
            edge_index += 1
    if torch is None:
        raise RuntimeError("PyTorch is required to build hypergraph incidence")
    indices = torch.tensor([rows, cols], dtype=torch.long)
    values = torch.ones(len(rows), dtype=torch.float32)
    incidence = torch.sparse_coo_tensor(
        indices, values, size=(int(num_nodes), int(edge_index))
    ).coalesce()
    return HypergraphDomain(
        name=domain,
        num_nodes=int(num_nodes),
        incidence=incidence,
        visit_keys=tuple(visit_keys),
    )


def build_knowledge_bias(labels: Sequence[Any] | None, *, same_prefix_bias: float = 0.05) -> Any:
    """Create a small code-prefix knowledge bias for global attention.

    HypeMed's official feature encoder derives knowledge encodings from code
    hierarchy metadata.  The canonical vocabulary supplies code strings but no
    extra ontology is needed for this screen, so shared three-character code
    prefixes provide a deterministic, inspectable approximation.
    """

    if torch is None:
        raise RuntimeError("PyTorch is required to build knowledge bias")
    size = len(labels) if labels is not None else 0
    bias = torch.zeros((size, size), dtype=torch.float32)
    if not labels:
        return bias
    prefixes = []
    for value in labels:
        text = str(value).replace(".", "").upper()
        prefixes.append(text[:3])
    for left in range(size):
        if not prefixes[left]:
            continue
        for right in range(size):
            if left != right and prefixes[left] == prefixes[right]:
                bias[left, right] = float(same_prefix_bias)
    return bias


if nn is not None:

    class KHGEBlock(nn.Module):
        """One HypeMed KHGE block: local hypergraph + global attention + FFN."""

        def __init__(self, dim: int, heads: int, dropout: float) -> None:
            super().__init__()
            self.node_self = nn.Linear(dim, dim)
            self.node_message = nn.Linear(dim, dim)
            self.edge_update = nn.Linear(dim, dim)
            self.global_attention = nn.MultiheadAttention(
                embed_dim=dim,
                num_heads=heads,
                dropout=dropout,
                batch_first=True,
            )
            self.local_norm = nn.LayerNorm(dim)
            self.global_norm = nn.LayerNorm(dim)
            self.output_norm = nn.LayerNorm(dim)
            self.dropout = nn.Dropout(dropout)
            self.ffn = nn.Sequential(
                nn.Linear(dim, dim * 2),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(dim * 2, dim),
            )

        @staticmethod
        def _edge_mean(nodes: Any, incidence: Any) -> Any:
            degree = torch.sparse.sum(incidence, dim=0).to_dense().clamp_min(1.0)
            return torch.sparse.mm(incidence.transpose(0, 1), nodes) / degree.unsqueeze(-1)

        @staticmethod
        def _node_mean(edges: Any, incidence: Any) -> Any:
            degree = torch.sparse.sum(incidence, dim=1).to_dense().clamp_min(1.0)
            return torch.sparse.mm(incidence, edges) / degree.unsqueeze(-1)

        def forward(
            self, nodes: Any, edges: Any, incidence: Any, knowledge_bias: Any
        ) -> tuple[Any, Any]:
            edge_mean = self._edge_mean(nodes, incidence)
            updated_edges = self.edge_update(edge_mean) + edges
            local_message = self._node_mean(updated_edges, incidence)
            local = self.local_norm(
                nodes + self.dropout(self.node_self(nodes) + self.node_message(local_message))
            )

            # MultiheadAttention accepts an additive [nodes, nodes] mask on the
            # torch 1.9 runtime used by the existing MoleRec environment.
            global_out, _ = self.global_attention(
                nodes.unsqueeze(0),
                nodes.unsqueeze(0),
                nodes.unsqueeze(0),
                attn_mask=knowledge_bias,
                need_weights=False,
            )
            global_state = self.global_norm(nodes + self.dropout(global_out.squeeze(0)))
            mixed = local + global_state
            output = self.output_norm(mixed + self.dropout(self.ffn(mixed)))
            return output, updated_edges

    class HypergraphEncoder(nn.Module):
        """Compact two-layer KHGE-style encoder for one entity domain."""

        def __init__(
            self,
            num_nodes: int,
            num_edges: int,
            *,
            dim: int = DEFAULT_DIM,
            heads: int = DEFAULT_HEADS,
            layers: int = DEFAULT_LAYERS,
            dropout: float = DEFAULT_DROPOUT,
            knowledge_bias: Any | None = None,
        ) -> None:
            super().__init__()
            if layers != DEFAULT_LAYERS:
                raise ValueError("the bounded HypeMed adapter fixes KHGE depth at two layers")
            self.num_nodes = int(num_nodes)
            self.num_edges = int(num_edges)
            self.dim = int(dim)
            self.node_table = nn.Parameter(torch.randn(num_nodes, dim) * 0.02)
            self.edge_table = nn.Parameter(torch.randn(num_edges, dim) * 0.02)
            self.layers = nn.ModuleList(
                KHGEBlock(dim=dim, heads=heads, dropout=dropout) for _ in range(layers)
            )
            self.node_norm = nn.LayerNorm(dim)
            self.edge_norm = nn.LayerNorm(dim)
            if knowledge_bias is None:
                knowledge_bias = torch.zeros((num_nodes, num_nodes), dtype=torch.float32)
            self.register_buffer("knowledge_bias", knowledge_bias.float(), persistent=False)

        def forward(self, incidence: Any, *, node_features: Any | None = None) -> tuple[Any, Any]:
            nodes = self.node_table if node_features is None else node_features
            edges = self.edge_table
            states = [nodes]
            edge_states = [edges]
            for layer in self.layers:
                nodes, edges = layer(nodes, edges, incidence, self.knowledge_bias)
                states.append(nodes)
                edge_states.append(edges)
            return self.node_norm(torch.stack(states).mean(dim=0)), self.edge_norm(
                torch.stack(edge_states).mean(dim=0)
            )

        def event_representation(self, node_embeddings: Any, codes: Sequence[int]) -> Any:
            """Encode a visit hyperedge from its current-event nodes."""

            if not codes:
                return node_embeddings.new_zeros((node_embeddings.shape[-1],))
            indices = torch.as_tensor(
                sorted(set(int(value) for value in codes)),
                dtype=torch.long,
                device=node_embeddings.device,
            )
            indices = indices.clamp(0, node_embeddings.shape[0] - 1)
            return node_embeddings.index_select(0, indices).mean(dim=0)

    class HypeMedScorer(nn.Module):
        """SimMR-style longitudinal/similar-visit channel fusion and scorer."""

        def __init__(
            self,
            medication_embeddings: Any,
            dim: int = DEFAULT_DIM,
            dropout: float = DEFAULT_DROPOUT,
        ) -> None:
            super().__init__()
            self.medication_embeddings = nn.Parameter(medication_embeddings.detach().clone())
            self.context_projection = nn.Linear(dim, dim)
            self.history_projection = nn.Linear(dim, dim)
            self.similar_projection = nn.Linear(dim, dim)
            self.channel_gate = nn.Sequential(
                nn.LayerNorm(dim * 3),
                nn.Linear(dim * 3, 3),
                nn.Dropout(dropout),
            )
            self.output_norm = nn.LayerNorm(dim)
            self.prediction_bias = nn.Parameter(torch.zeros(CANDIDATE_COUNT))

        def fuse_channels(self, context: Any, history: Any, similar: Any) -> Any:
            context_state = self.context_projection(context)
            history_state = self.history_projection(history)
            similar_state = self.similar_projection(similar)
            stacked = torch.cat((context_state, history_state, similar_state), dim=-1)
            gates = torch.softmax(self.channel_gate(stacked), dim=-1)
            fused = (
                gates[:, 0:1] * context_state
                + gates[:, 1:2] * history_state
                + gates[:, 2:3] * similar_state
            )
            fused = self.output_norm(fused)
            return fused

        def forward(self, context: Any, history: Any, similar: Any) -> Any:
            fused = self.fuse_channels(context, history, similar)
            return fused @ self.medication_embeddings.transpose(0, 1) + self.prediction_bias

    class PatientConditionedInteraction(nn.Module):
        """Two-layer patient-conditioned relation-aware medication interaction."""

        def __init__(
            self, medication_embeddings: Any, dim: int = DEFAULT_DIM, hidden_dim: int = 96
        ) -> None:
            super().__init__()
            self.medication_embeddings = nn.Parameter(medication_embeddings.detach().clone())
            self.input_projection = nn.Linear(dim + 2, hidden_dim)
            self.patient_projection = nn.Linear(dim, hidden_dim)
            self.self_layers = nn.ModuleList(nn.Linear(hidden_dim, hidden_dim) for _ in range(2))
            self.message_layers = nn.ModuleList(nn.Linear(hidden_dim, hidden_dim) for _ in range(2))
            self.relation_weights = nn.Parameter(torch.tensor([0.45, 0.25]))
            self.norms = nn.ModuleList(nn.LayerNorm(hidden_dim) for _ in range(2))
            self.output = nn.Linear(hidden_dim, 1)

        def forward(
            self,
            patient_context: Any,
            original_logits: Any,
            historical_indicator: Any,
            ehr_relation: Any,
            ddi_relation: Any,
        ) -> Any:
            batch_size = patient_context.shape[0]
            med = self.medication_embeddings.unsqueeze(0).expand(batch_size, -1, -1)
            scalar = torch.stack((original_logits, historical_indicator), dim=-1)
            hidden = F.gelu(self.input_projection(torch.cat((med, scalar), dim=-1)))
            patient = torch.tanh(self.patient_projection(patient_context)).unsqueeze(1)
            hidden = hidden + patient
            relations = []
            for relation in (ehr_relation, ddi_relation):
                value = (
                    relation if isinstance(relation, torch.Tensor) else torch.as_tensor(relation)
                )
                value = value.to(device=hidden.device, dtype=hidden.dtype)
                if value.ndim == 2:
                    value = value.unsqueeze(0).expand(batch_size, -1, -1)
                relations.append(value)
            relation_mix = (
                self.relation_weights[0] * relations[0] + self.relation_weights[1] * relations[1]
            )
            relation_mix = relation_mix / relation_mix.sum(dim=-1, keepdim=True).clamp_min(1.0)
            for self_layer, message_layer, norm in zip(  # noqa: B905
                self.self_layers, self.message_layers, self.norms
            ):
                message = torch.bmm(relation_mix, hidden)
                hidden = norm(hidden + F.gelu(self_layer(hidden) + message_layer(message)))
            return self.output(hidden).squeeze(-1)


def _drop_incidence(incidence: Any, rate: float, generator: Any | None = None) -> Any:
    """Drop incidence entries while retaining at least one entry per edge."""

    if rate < 0.0 or rate >= 1.0:
        raise ValueError("incidence drop rate must be in [0, 1)")
    indices = incidence.coalesce().indices()
    values = incidence.coalesce().values()
    keep = torch.rand(values.shape, device=values.device, generator=generator) >= rate
    if not bool(keep.any()):
        keep[0] = True
    dropped = torch.sparse_coo_tensor(
        indices[:, keep], values[keep], size=incidence.shape, device=incidence.device
    )
    return dropped.coalesce()


def _drop_features(features: Any, rate: float, generator: Any | None = None) -> Any:
    if rate < 0.0 or rate >= 1.0:
        raise ValueError("feature drop rate must be in [0, 1)")
    mask = torch.rand(features.shape, device=features.device, generator=generator) >= rate
    return features * mask.to(dtype=features.dtype)


def _infonce(first: Any, second: Any, temperature: float, max_items: int = 1024) -> Any:
    if first.shape[0] == 0:
        return first.sum() * 0.0
    if first.shape[0] > max_items:
        # Deterministic truncation is sufficient for a bounded screen and keeps
        # the contrastive matrix well within GPU memory.
        first = first[:max_items]
        second = second[:max_items]
    first = F.normalize(first, dim=-1)
    second = F.normalize(second, dim=-1)
    logits = first @ second.transpose(0, 1) / float(temperature)
    labels = torch.arange(logits.shape[0], device=logits.device)
    return 0.5 * (F.cross_entropy(logits, labels) + F.cross_entropy(logits.transpose(0, 1), labels))


def membership_contrastive_loss(
    node_first: Any,
    edge_first: Any,
    node_second: Any,
    edge_second: Any,
    incidence: Any,
    *,
    temperature: float = 1.0,
    max_items: int = 1024,
) -> Any:
    """Contrast node/edge embeddings for sampled positive memberships."""

    indices = incidence.coalesce().indices()
    if indices.shape[1] == 0:
        return node_first.sum() * 0.0
    selected = indices[:, : min(indices.shape[1], max_items)]
    node_ids = selected[0]
    edge_ids = selected[1]
    left_nodes = node_first.index_select(0, node_ids)
    right_edges = edge_second.index_select(0, edge_ids)
    left_edges = edge_first.index_select(0, edge_ids)
    right_nodes = node_second.index_select(0, node_ids)
    return 0.5 * (
        _infonce(left_nodes, right_edges, temperature, max_items)
        + _infonce(left_edges, right_nodes, temperature, max_items)
    )


def contrastive_pretrain_step(
    model: Any,
    incidence: Any,
    *,
    generator: Any | None = None,
    drop_incidence_rate: float = 0.20,
    drop_feature_rate: float = 0.20,
    tau_node: float = 0.5,
    tau_edge: float = 0.5,
    tau_membership: float = 1.0,
) -> Any:
    """One TriCL-style node/edge/membership contrastive update."""

    model.train()
    nodes = model.node_table
    incidence_first = _drop_incidence(incidence, drop_incidence_rate, generator)
    incidence_second = _drop_incidence(incidence, drop_incidence_rate, generator)
    nodes_first = _drop_features(nodes, drop_feature_rate, generator)
    nodes_second = _drop_features(nodes, drop_feature_rate, generator)
    first_nodes, first_edges = model(incidence_first, node_features=nodes_first)
    second_nodes, second_edges = model(incidence_second, node_features=nodes_second)
    common_nodes = min(first_nodes.shape[0], second_nodes.shape[0])
    common_edges = min(first_edges.shape[0], second_edges.shape[0])
    node_loss = _infonce(first_nodes[:common_nodes], second_nodes[:common_nodes], tau_node)
    edge_loss = _infonce(first_edges[:common_edges], second_edges[:common_edges], tau_edge)
    membership_loss = membership_contrastive_loss(
        first_nodes,
        first_edges,
        second_nodes,
        second_edges,
        incidence,
        temperature=tau_membership,
    )
    return node_loss + edge_loss + membership_loss, {
        "node": float(node_loss.detach().cpu()),
        "edge": float(edge_loss.detach().cpu()),
        "membership": float(membership_loss.detach().cpu()),
    }


def _target_sets(targets: Any) -> tuple[frozenset, ...]:
    numpy = _require_numpy()
    return tuple(frozenset(int(index) for index in numpy.flatnonzero(row > 0.5)) for row in targets)


def metric_average_precision(target: Iterable[int], scores: Sequence[float]) -> float:
    target_set = set(int(value) for value in target)
    if not target_set:
        return 0.0
    ranked = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    found = 0
    total = 0.0
    for rank, index in enumerate(ranked, start=1):
        if index in target_set:
            found += 1
            total += found / float(rank)
    return total / float(len(target_set))


def evaluate_sets(
    targets: Any, predictions: Sequence[Iterable[int]], scores: Any, ddi: Any
) -> dict[str, float]:
    """Visit-macro Jaccard/F1/PRAUC/DDI and medication count."""

    numpy = _require_numpy()
    target_values = numpy.asarray(targets)
    score_values = numpy.asarray(scores)
    ddi_values = numpy.asarray(ddi)
    if target_values.shape != score_values.shape or score_values.shape[1] != CANDIDATE_COUNT:
        raise ValueError("targets and scores must have aligned [visits, 131] shapes")
    if len(predictions) != target_values.shape[0] or ddi_values.shape != (
        CANDIDATE_COUNT,
        CANDIDATE_COUNT,
    ):
        raise ValueError("predictions or DDI matrix are not aligned")
    jaccard = 0.0
    f1 = 0.0
    prauc = 0.0
    ddi_pairs = 0
    ddi_hits = 0
    for target_row, prediction_raw, score_row in zip(target_values, predictions, score_values):  # noqa: B905
        target = set(int(index) for index in numpy.flatnonzero(target_row > 0.5))
        prediction = set(int(index) for index in prediction_raw)
        intersection = len(target & prediction)
        union = len(target | prediction)
        jaccard += 1.0 if union == 0 else intersection / float(union)
        precision = intersection / float(len(prediction)) if prediction else 0.0
        recall = intersection / float(len(target)) if target else 0.0
        f1 += 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)
        prauc += metric_average_precision(target, score_row)
        ordered = sorted(prediction)
        for left, first in enumerate(ordered):
            for second in ordered[left + 1 :]:
                ddi_pairs += 1
                ddi_hits += int(bool(ddi_values[first, second]))
    count = float(target_values.shape[0])
    return {
        "jaccard": jaccard / count,
        "f1": f1 / count,
        "prauc": prauc / count,
        "ddi": 0.0 if ddi_pairs == 0 else ddi_hits / float(ddi_pairs),
        "mean_medication_count": sum(len(set(item)) for item in predictions) / count,
    }


def topk_sets(scores: Any, cardinalities: Sequence[int]) -> tuple[frozenset, ...]:
    numpy = _require_numpy()
    values = numpy.asarray(scores)
    if (
        values.ndim != 2
        or values.shape[1] != CANDIDATE_COUNT
        or len(cardinalities) != values.shape[0]
    ):
        raise ValueError("scores and cardinalities are not aligned")
    result = []
    for row, cardinality in zip(values, cardinalities):  # noqa: B905
        k = max(0, min(CANDIDATE_COUNT, int(cardinality)))
        ranked = sorted(range(CANDIDATE_COUNT), key=lambda index: (-float(row[index]), index))
        result.append(frozenset(ranked[:k]))
    return tuple(result)


def threshold_sets(logits: Any) -> tuple[frozenset, ...]:
    numpy = _require_numpy()
    values = numpy.asarray(logits)
    return tuple(frozenset(int(index) for index in numpy.flatnonzero(row >= 0.0)) for row in values)


def set_change_summary(
    baseline: Sequence[Iterable[int]], edited: Sequence[Iterable[int]]
) -> dict[str, float]:
    if len(baseline) != len(edited) or not baseline:
        raise ValueError("baseline and edited sets must be non-empty and aligned")
    differences = [len(set(left) ^ set(right)) for left, right in zip(baseline, edited)]  # noqa: B905
    return {
        "changed_fraction": sum(value > 0 for value in differences) / float(len(differences)),
        "mean_symmetric_difference": sum(differences) / float(len(differences)),
    }


def ddi_penalty(logits: Any, ddi_relation: Any) -> Any:
    """Differentiable expected DDI pair penalty for recommendation training."""

    probabilities = torch.sigmoid(logits)
    relation = (
        ddi_relation if isinstance(ddi_relation, torch.Tensor) else torch.as_tensor(ddi_relation)
    )
    relation = relation.to(device=logits.device, dtype=logits.dtype)
    if relation.ndim == 2:
        relation = relation.unsqueeze(0).expand(logits.shape[0], -1, -1)
    pair_prob = probabilities.unsqueeze(2) * probabilities.unsqueeze(1)
    denominator = pair_prob.sum(dim=(1, 2)).clamp_min(1.0)
    return (pair_prob * relation).sum(dim=(1, 2)).div(denominator).mean()
