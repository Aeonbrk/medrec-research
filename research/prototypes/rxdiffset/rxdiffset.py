"""RxDiffSet-v0: patient-conditioned joint prescription denoising.

This deliberately throwaway module answers one narrow question: can a small
permutation-equivariant denoiser use the frozen, patient-specific MoleRec
medication embeddings to reconstruct a whole prescription set?  The module
owns the corruption process, relation-aware token model, cardinality head, and
deterministic inference helpers so the runner only has to bind the existing
Train/Dev artifacts.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

CANDIDATE_COUNT = 131
DEFAULT_NOISE_LEVELS = 8
DEFAULT_ALPHA_BARS = (1.0, 0.92, 0.80, 0.66, 0.50, 0.35, 0.20, 0.08)
DEFAULT_HIDDEN_DIM = 112
DEFAULT_ATTENTION_HEADS = 4
DEFAULT_BLOCKS = 2
DEFAULT_NOISE_EMBED_DIM = 16
DEFAULT_CARDINALITY_WEIGHT = 0.25

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
        raise RuntimeError("NumPy is required for RxDiffSet experiment execution")
    return np


def _require_torch() -> Any:
    if torch is None:
        raise RuntimeError("PyTorch is required for RxDiffSet experiment execution")
    return torch


def _adjacent_pairs(values: Sequence[Any]) -> Any:
    """Yield adjacent pairs on both the Python 3.8 baseline and core runtimes."""

    iterator = iter(values)
    try:
        previous = next(iterator)
    except StopIteration:
        return
    for current in iterator:
        yield previous, current
        previous = current


def validate_noise_schedule(alpha_bars: Sequence[float]) -> tuple[float, ...]:
    """Validate a monotone prevalence-preserving schedule once at the boundary."""

    values = tuple(float(value) for value in alpha_bars)
    if len(values) < 2:
        raise ValueError("RxDiffSet requires at least two noise levels")
    if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
        raise ValueError("noise schedule values must be finite probabilities")
    if values[0] != 1.0:
        raise ValueError("the first noise level must be clean (alpha_bar=1)")
    if any(left < right for left, right in _adjacent_pairs(values)):
        raise ValueError("alpha_bar must be non-increasing with noise level")
    return values


def topk_set(logits: Sequence[float], cardinality: int) -> frozenset[int]:
    """Decode deterministic Top-K membership without consulting target labels."""

    values = tuple(float(value) for value in logits)
    if len(values) != CANDIDATE_COUNT:
        raise ValueError("medication logits must have the 131-candidate shape")
    if cardinality < 0 or cardinality > CANDIDATE_COUNT:
        raise ValueError("cardinality is outside the 131-candidate vocabulary")
    ranked = sorted(range(CANDIDATE_COUNT), key=lambda index: (-values[index], index))
    return frozenset(ranked[:cardinality])


def corrupt_membership_with_uniforms(
    clean: Sequence[Sequence[float]],
    prevalence: Sequence[float],
    alpha_bar: float,
    preserve_uniforms: Sequence[Sequence[float]],
    replacement_uniforms: Sequence[Sequence[float]],
) -> tuple[tuple[float, ...], ...]:
    """Apply one corruption level from supplied uniforms.

    Keeping this small pure-Python form makes the target-free behavior easy to
    test on the Mac harness.  At ``alpha_bar=0`` the output is determined only
    by prevalence and replacement uniforms, never by the clean prescription.
    """

    if not 0.0 <= float(alpha_bar) <= 1.0:
        raise ValueError("alpha_bar must be a probability")
    medication_count = len(prevalence)
    if any(len(row) != medication_count for row in clean):
        raise ValueError("clean rows must match prevalence width")
    if any(len(row) != medication_count for row in preserve_uniforms):
        raise ValueError("preserve uniforms must match prevalence width")
    if any(len(row) != medication_count for row in replacement_uniforms):
        raise ValueError("replacement uniforms must match prevalence width")
    rows: list[tuple[float, ...]] = []
    for clean_row, preserve_row, replacement_row in zip(  # noqa: B905
        clean, preserve_uniforms, replacement_uniforms
    ):
        rows.append(
            tuple(
                float(clean_value)
                if float(preserve_value) < float(alpha_bar)
                else float(float(replacement_value) < float(prevalence[index]))
                for index, (clean_value, preserve_value, replacement_value) in enumerate(
                    zip(clean_row, preserve_row, replacement_row)  # noqa: B905
                )
            )
        )
    return tuple(rows)


def corrupt_memberships(
    clean: Any,
    prevalence: Any,
    alpha_bars: Sequence[float],
    levels: Any,
    rng: Any,
) -> Any:
    """Vectorized prevalence-preserving replacement corruption for a batch."""

    numpy = _require_numpy()
    schedule = validate_noise_schedule(alpha_bars)
    clean_values = numpy.asarray(clean, dtype=numpy.float32)
    prevalence_values = numpy.asarray(prevalence, dtype=numpy.float32)
    level_values = numpy.asarray(levels, dtype=numpy.int64).reshape(-1)
    if clean_values.ndim != 2 or clean_values.shape[1] != CANDIDATE_COUNT:
        raise ValueError("clean membership must have shape [batch, 131]")
    if prevalence_values.shape != (CANDIDATE_COUNT,):
        raise ValueError("prevalence must have shape [131]")
    if len(level_values) != clean_values.shape[0] or numpy.any(
        (level_values < 0) | (level_values >= len(schedule))
    ):
        raise ValueError("noise levels are not aligned with the clean batch")
    alpha = numpy.asarray(schedule, dtype=numpy.float32)[level_values, None]
    preserve = rng.random(clean_values.shape) < alpha
    replacement = rng.random(clean_values.shape) < prevalence_values[None, :]
    return numpy.where(preserve, clean_values, replacement).astype(numpy.float32)


def reverse_sample_state(
    clean_probability: Sequence[Sequence[float]],
    prevalence: Sequence[float],
    alpha_bar_previous: float,
    uniforms: Sequence[Sequence[float]],
) -> tuple[tuple[float, ...], ...]:
    """Sample one reverse state from a clean estimate and prevalence prior."""

    if not 0.0 <= float(alpha_bar_previous) <= 1.0:
        raise ValueError("alpha_bar_previous must be a probability")
    if any(len(row) != len(prevalence) for row in clean_probability):
        raise ValueError("clean probabilities must match prevalence width")
    if any(len(row) != len(prevalence) for row in uniforms):
        raise ValueError("reverse uniforms must match prevalence width")
    rows: list[tuple[float, ...]] = []
    for probability_row, uniform_row in zip(clean_probability, uniforms):  # noqa: B905
        rows.append(
            tuple(
                float(
                    float(uniform)
                    < float(alpha_bar_previous) * float(probability)
                    + (1.0 - float(alpha_bar_previous)) * float(prevalence[index])
                )
                for index, (probability, uniform) in enumerate(
                    zip(probability_row, uniform_row)  # noqa: B905
                )
            )
        )
    return tuple(rows)


def reverse_trace_from_probabilities(
    clean_probabilities: Sequence[Sequence[Sequence[float]]],
    prevalence: Sequence[float],
    alpha_bars: Sequence[float],
    *,
    seed: int,
) -> tuple[tuple[tuple[float, ...], ...], ...]:
    """Build a deterministic reverse trace for shape and seeding checks."""

    schedule = validate_noise_schedule(alpha_bars)
    if len(clean_probabilities) != len(schedule) - 1:
        raise ValueError("one clean-probability batch is required per reverse step")
    if not clean_probabilities:
        raise ValueError("reverse trace requires at least one step")
    rows = len(clean_probabilities[0])
    width = len(prevalence)
    if any(len(batch) != rows for batch in clean_probabilities):
        raise ValueError("reverse probability batches must have equal row counts")
    if any(any(len(row) != width for row in batch) for batch in clean_probabilities):
        raise ValueError("reverse probability batches must match prevalence width")
    generator = random.Random(int(seed))
    state = tuple(
        tuple(float(generator.random() < float(prevalence[index])) for index in range(width))
        for _ in range(rows)
    )
    trace = [state]
    for step, probabilities in enumerate(clean_probabilities):
        uniforms = tuple(tuple(generator.random() for _ in range(width)) for _ in range(rows))
        state = reverse_sample_state(
            probabilities,
            prevalence,
            schedule[-2 - step],
            uniforms,
        )
        trace.append(state)
    return tuple(trace)


def trace_change_summary(
    states: Sequence[Sequence[Sequence[float]]],
) -> dict[str, Any]:
    """Summarize reverse-process membership changes without target access."""

    if len(states) < 2:
        raise ValueError("a reverse trace requires an initial and final state")
    rows = len(states[0])
    if rows == 0 or any(len(state) != rows for state in states):
        raise ValueError("reverse states must have equal non-zero row counts")
    width = len(states[0][0])
    if width == 0 or any(any(len(row) != width for row in state) for state in states):
        raise ValueError("reverse states must have equal non-zero medication width")
    flips_per_step = []
    changed_any = [False] * rows
    for before, after in _adjacent_pairs(states):
        flips = [
            sum(float(left) != float(right) for left, right in zip(row_a, row_b))  # noqa: B905
            for row_a, row_b in zip(before, after)  # noqa: B905
        ]
        flips_per_step.append(sum(flips) / rows)
        changed_any = [old or value > 0 for old, value in zip(changed_any, flips)]  # noqa: B905
    initial = states[0]
    final = states[-1]
    changed_fraction = (
        sum(
            any(float(left) != float(right) for left, right in zip(row_a, row_b))  # noqa: B905
            for row_a, row_b in zip(initial, final)  # noqa: B905
        )
        / rows
    )
    return {
        "changed_fraction_initial_to_final": changed_fraction,
        "changed_any_fraction": sum(changed_any) / rows,
        "mean_membership_flips_per_reverse_step": sum(flips_per_step) / len(flips_per_step),
        "flips_per_reverse_step": tuple(flips_per_step),
    }


def build_relation_features(ehr_adjacency: Any, ddi_adjacency: Any) -> Any:
    """Normalize the existing EHR/DDI matrices into two relation channels."""

    numpy = _require_numpy()
    ehr = numpy.asarray(ehr_adjacency, dtype=numpy.float32)
    ddi = numpy.asarray(ddi_adjacency, dtype=numpy.float32)
    expected = (CANDIDATE_COUNT, CANDIDATE_COUNT)
    if ehr.shape != expected or ddi.shape != expected:
        raise ValueError("EHR and DDI matrices must both be 131 by 131")
    ehr = numpy.maximum(ehr, 0.0).copy()
    ddi = numpy.maximum(ddi, 0.0).copy()
    numpy.fill_diagonal(ehr, 0.0)
    numpy.fill_diagonal(ddi, 0.0)
    ehr_max = float(ehr.max())
    if ehr_max > 0.0:
        ehr /= ehr_max
    ddi_max = float(ddi.max())
    if ddi_max > 0.0:
        ddi /= ddi_max
    return numpy.stack((ehr, ddi), axis=-1).astype(numpy.float32)


@dataclass(frozen=True)
class DenoiseOutput:
    """Outputs needed by both reconstruction training and set decoding."""

    clean_logits: Any
    cardinality_logits: Any
    token_states: Any


if nn is not None:

    class RelationAttentionBlock(nn.Module):
        """A compact relation-biased self-attention block over medication tokens."""

        def __init__(self, hidden_dim: int, attention_heads: int) -> None:
            super().__init__()
            if hidden_dim <= 0 or attention_heads <= 0 or hidden_dim % attention_heads:
                raise ValueError("hidden dimension must be divisible by positive head count")
            self.hidden_dim = hidden_dim
            self.attention_heads = attention_heads
            self.head_dim = hidden_dim // attention_heads
            self.norm_attention = nn.LayerNorm(hidden_dim)
            self.query_key_value = nn.Linear(hidden_dim, hidden_dim * 3)
            self.output_projection = nn.Linear(hidden_dim, hidden_dim)
            self.relation_projection = nn.Linear(2, attention_heads, bias=False)
            self.norm_feed_forward = nn.LayerNorm(hidden_dim)
            self.feed_forward = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim * 2),
                nn.GELU(),
                nn.Linear(hidden_dim * 2, hidden_dim),
            )

        def forward(self, token_states: Any, relation_features: Any) -> Any:
            batch, medication_count, _ = token_states.shape
            normalized = self.norm_attention(token_states)
            qkv = self.query_key_value(normalized).reshape(
                batch, medication_count, 3, self.attention_heads, self.head_dim
            )
            query, key, value = qkv.permute(2, 0, 3, 1, 4)
            attention_logits = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(self.head_dim)
            relation_bias = self.relation_projection(relation_features).permute(2, 0, 1)
            attention_logits = attention_logits + relation_bias.unsqueeze(0)
            attention = torch.softmax(attention_logits, dim=-1)
            attended = (
                torch.matmul(attention, value)
                .transpose(1, 2)
                .reshape(batch, medication_count, self.hidden_dim)
            )
            token_states = token_states + self.output_projection(attended)
            token_states = token_states + self.feed_forward(self.norm_feed_forward(token_states))
            return token_states

    class RxDiffSetModel(nn.Module):
        """Relation-aware denoiser consuming patient-specific MoleRec tokens."""

        def __init__(
            self,
            embedding_dim: int,
            relation_features: Any,
            max_cardinality: int,
            *,
            hidden_dim: int = DEFAULT_HIDDEN_DIM,
            attention_heads: int = DEFAULT_ATTENTION_HEADS,
            blocks: int = DEFAULT_BLOCKS,
            noise_levels: int = DEFAULT_NOISE_LEVELS,
            noise_embedding_dim: int = DEFAULT_NOISE_EMBED_DIM,
        ) -> None:
            super().__init__()
            if embedding_dim <= 0 or max_cardinality < 1:
                raise ValueError("embedding dimension and max cardinality must be positive")
            if blocks <= 0 or noise_levels < 2 or noise_embedding_dim <= 0:
                raise ValueError("blocks, noise levels, and noise embedding must be positive")
            relation_tensor = torch.as_tensor(relation_features, dtype=torch.float32)
            if tuple(relation_tensor.shape) != (CANDIDATE_COUNT, CANDIDATE_COUNT, 2):
                raise ValueError("relation features must have shape [131, 131, 2]")
            self.noise_embedding = nn.Embedding(noise_levels, noise_embedding_dim)
            input_dim = embedding_dim + 2 + noise_embedding_dim
            self.input_projection = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.GELU(),
            )
            self.blocks = nn.ModuleList(
                RelationAttentionBlock(hidden_dim, attention_heads) for _ in range(blocks)
            )
            self.clean_head = nn.Sequential(nn.LayerNorm(hidden_dim), nn.Linear(hidden_dim, 1))
            self.cardinality_head = nn.Sequential(
                nn.LayerNorm(hidden_dim * 2),
                nn.Linear(hidden_dim * 2, max_cardinality + 1),
            )
            self.register_buffer("relation_features", relation_tensor)
            self.max_cardinality = int(max_cardinality)
            self.noise_levels = int(noise_levels)

        def forward(
            self,
            medication_embeddings: Any,
            backbone_scores: Any,
            noisy_membership: Any,
            noise_levels: Any,
        ) -> DenoiseOutput:
            if medication_embeddings.ndim != 3 or medication_embeddings.shape[1:] != (
                CANDIDATE_COUNT,
                medication_embeddings.shape[-1],
            ):
                raise ValueError(
                    "medication embeddings must have shape [batch, 131, embedding_dim]"
                )
            batch = medication_embeddings.shape[0]
            levels = noise_levels.reshape(-1).to(dtype=torch.long)
            if levels.numel() == 1:
                levels = levels.expand(batch)
            if (
                levels.shape[0] != batch
                or bool(torch.any(levels < 0))
                or bool(torch.any(levels >= self.noise_levels))
            ):
                raise ValueError("noise levels are not aligned with the medication batch")
            if backbone_scores.shape != (batch, CANDIDATE_COUNT):
                raise ValueError("backbone scores must have shape [batch, 131]")
            if noisy_membership.shape != (batch, CANDIDATE_COUNT):
                raise ValueError("noisy membership must have shape [batch, 131]")
            noise = self.noise_embedding(levels).unsqueeze(1).expand(-1, CANDIDATE_COUNT, -1)
            token_inputs = torch.cat(
                (
                    medication_embeddings,
                    backbone_scores.unsqueeze(-1),
                    noisy_membership.unsqueeze(-1),
                    noise,
                ),
                dim=-1,
            )
            token_states = self.input_projection(token_inputs)
            for block in self.blocks:
                token_states = block(token_states, self.relation_features)
            clean_logits = self.clean_head(token_states).squeeze(-1)
            pooled_mean = token_states.mean(dim=1)
            pooled_max = token_states.max(dim=1).values
            cardinality_logits = self.cardinality_head(torch.cat((pooled_mean, pooled_max), dim=-1))
            return DenoiseOutput(clean_logits, cardinality_logits, token_states)

    def rx_diffset_loss(
        output: DenoiseOutput,
        clean_membership: Any,
        target_cardinality: Any,
        *,
        cardinality_weight: float = DEFAULT_CARDINALITY_WEIGHT,
    ) -> tuple[Any, dict[str, float]]:
        """Reconstruction BCE plus the explicit Train-derived cardinality loss."""

        if cardinality_weight < 0.0 or not math.isfinite(float(cardinality_weight)):
            raise ValueError("cardinality weight must be a finite non-negative number")
        reconstruction = F.binary_cross_entropy_with_logits(output.clean_logits, clean_membership)
        counts = target_cardinality.to(dtype=torch.long).clamp(
            0, output.cardinality_logits.shape[1] - 1
        )
        cardinality = F.cross_entropy(output.cardinality_logits, counts)
        total = reconstruction + float(cardinality_weight) * cardinality
        return total, {
            "reconstruction_bce": float(reconstruction.detach().cpu()),
            "cardinality_ce": float(cardinality.detach().cpu()),
            "total": float(total.detach().cpu()),
        }

else:

    class RelationAttentionBlock:  # type: ignore[no-redef]
        """Import-safe placeholder when PyTorch is unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for RxDiffSet execution")

    class RxDiffSetModel:  # type: ignore[no-redef]
        """Import-safe placeholder when PyTorch is unavailable."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PyTorch is required for RxDiffSet execution")

    def rx_diffset_loss(*_args: Any, **_kwargs: Any) -> tuple[Any, dict[str, float]]:
        raise RuntimeError("PyTorch is required for RxDiffSet execution")


__all__ = (
    "CANDIDATE_COUNT",
    "DEFAULT_ALPHA_BARS",
    "DEFAULT_ATTENTION_HEADS",
    "DEFAULT_BLOCKS",
    "DEFAULT_CARDINALITY_WEIGHT",
    "DEFAULT_HIDDEN_DIM",
    "DEFAULT_NOISE_LEVELS",
    "DenoiseOutput",
    "RelationAttentionBlock",
    "RxDiffSetModel",
    "build_relation_features",
    "corrupt_membership_with_uniforms",
    "corrupt_memberships",
    "reverse_sample_state",
    "reverse_trace_from_probabilities",
    "rx_diffset_loss",
    "topk_set",
    "trace_change_summary",
    "validate_noise_schedule",
)
