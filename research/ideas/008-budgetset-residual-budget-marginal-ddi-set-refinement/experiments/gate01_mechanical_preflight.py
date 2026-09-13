"""Idea 008 Gate 01 v1.2 implementation and mechanical preflight.

This module is intentionally Idea-local.  It contains the frozen pure
functions and small data objects needed to make the protocol executable, but
does not train either learned family or read Gate01-Audit data.  The public
record helpers expose only protocol identity, shapes, booleans, and aggregate
mechanical status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import tempfile
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

PROTOCOL_VERSION = "v1.2"
SPLIT_NAMESPACE = "idea008-gate01-v1"
UPSTREAM_MOLEREC_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"
MOLEREC_PROFILE = "molerec-embedding"
MOLEREC_CHECKPOINT_SHA256 = "5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca"
DATASET_ID = "molerec-table1-comparison-v1-1"
CANDIDATE_COUNT = 131
T = 2
LEARNED_SEEDS = (2002, 2003, 2004)
FIXED_LAMBDAS = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)
DELTA_U = 0.005
DELTA_R = 0.005
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 80081
CHECKPOINT_PATIENCE = 5
MAX_EPOCHS = 30

TERMINAL_PRECEDENCE = (
    "STOP_INVALID_GATE_IMPLEMENTATION",
    "STOP_NO_BASE_DDI_HEADROOM",
    "KILL_TARGET_SEMANTICS",
    "KILL_BUDGET_RESPONSE",
    "KILL_COMPOSITION_RESPONSE",
    "KILL_BUDGETSET",
    "KILL_JOINT_SET_INTERACTION",
    "KILL_SEED_FRAGILITY",
    "INCONCLUSIVE_STOP",
    "PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES",
)
REQUIRED_MECHANICAL_CHECKS = frozenset(
    {
        "explicit_residual_anchor",
        "same_frozen_no_grad_forward",
        "embedding_candidate_dimension",
        "t_two_recomputes_state",
        "exact_k_hard_outputs",
        "low_cardinality_semantics",
        "exact_v12_split_hash",
        "deterministic_greedy_1swap",
        "independent_no_current_set_feedback",
        "ordinary_frontier",
        "empty_frontier",
        "matched_independent_seeds",
        "deterministic_controls_no_seeds",
        "patient_bootstrap_recomputes_frontier",
        "terminal_precedence",
    }
)
REAL_MOLEREC_INTEGRATION_CHECKS = frozenset(
    {
        "same_frozen_no_grad_forward",
        "embedding_candidate_dimension",
    }
)
SYNTHETIC_MECHANICAL_CHECKS = REQUIRED_MECHANICAL_CHECKS - REAL_MOLEREC_INTEGRATION_CHECKS
INTEGRATION_PUBLIC_FIELDS = (
    "integration_status",
    "validated_real",
    "source_revision",
    "profile",
    "checkpoint_sha256",
    "dataset_id",
    "partition",
    "model_eval",
    "no_gradient",
    "same_forward",
    "score_candidate_dimension",
    "embedding_candidate_dimension",
    "score_shape",
    "embedding_shape",
    "embedding_rank",
    "score_extractor_consistent",
)


class ProtocolMismatch(RuntimeError):
    """Raised when a frozen v1.2 implementation contract is violated."""


class InvalidGateImplementation(ProtocolMismatch):
    """Raised when a required comparison family cannot produce a control point."""


def _python_value(value: Any) -> Any:
    """Detach a tensor-like value without importing a training dependency."""

    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "tolist"):
        value = value.tolist()
    return value


def _strip_singleton_batches(value: Any) -> Any:
    """Normalize the one-example tensor shapes emitted by MoleRec."""

    value = _python_value(value)
    while (
        isinstance(value, (list, tuple))
        and len(value) == 1
        and value
        and isinstance(value[0], (list, tuple))
    ):
        value = value[0]
    return value


def _score_vector(value: Any) -> tuple[float, ...]:
    """Convert ``[1, 131]`` or ``[131, 1]`` score output to one vector."""

    value = _strip_singleton_batches(value)
    if not isinstance(value, (list, tuple)):
        raise ProtocolMismatch("MoleRec score output is not a sequence")
    if value and isinstance(value[0], (list, tuple)):
        if all(isinstance(row, (list, tuple)) and len(row) == 1 for row in value):
            value = [row[0] for row in value]
        else:
            raise ProtocolMismatch("MoleRec score output has an unsupported rank")
    result = tuple(float(item) for item in value)
    if len(result) != CANDIDATE_COUNT:
        raise ProtocolMismatch(f"MoleRec score candidate dimension is {len(result)}, not 131")
    return result


def _embedding_rows(value: Any) -> tuple[tuple[float, ...], ...]:
    """Convert MoleRec's pre-score-extractor tensor to 131 candidate rows."""

    value = _strip_singleton_batches(value)
    if not isinstance(value, (list, tuple)) or not value:
        raise ProtocolMismatch("MoleRec molecule_embeddings is not a non-empty matrix")
    if not all(isinstance(row, (list, tuple)) for row in value):
        raise ProtocolMismatch("MoleRec molecule_embeddings has unsupported rank")
    rows = tuple(tuple(float(item) for item in row) for row in value)
    if len(rows) != CANDIDATE_COUNT:
        raise ProtocolMismatch(
            f"MoleRec molecule_embeddings candidate dimension is {len(rows)}, not 131"
        )
    width = len(rows[0])
    if width == 0 or any(len(row) != width for row in rows):
        raise ProtocolMismatch("MoleRec molecule_embeddings rows are not rectangular")
    return rows


@dataclass(frozen=True)
class FrozenMoleRecFeatures:
    """Public-safe representation of one frozen MoleRec forward."""

    scores: tuple[float, ...]
    embeddings: tuple[tuple[float, ...], ...]
    source_revision: str
    profile: str
    checkpoint_sha256: str
    dataset_id: str
    same_forward: bool = True
    eval_mode: bool = True
    no_grad: bool = True

    @property
    def candidate_count(self) -> int:
        return len(self.scores)

    @property
    def embedding_width(self) -> int:
        return len(self.embeddings[0]) if self.embeddings else 0


def _torch_no_grad() -> Any:
    try:
        import torch
    except ImportError:
        return nullcontext()
    return torch.no_grad()


def extract_frozen_molerec_features(
    model: Any,
    *,
    source_revision: str,
    profile: str,
    checkpoint_sha256: str,
    dataset_id: str,
    forward_args: Sequence[Any] = (),
    forward_kwargs: Mapping[str, Any] | None = None,
) -> FrozenMoleRecFeatures:
    """Extract ``s`` and pre-``score_extractor`` ``e`` from one frozen forward.

    The pre-hook is attached to the pinned model's ``score_extractor``.  Thus
    the captured tensor is the exact ``molecule_embeddings`` consumed by that
    module, rather than a global molecular or checkpoint tensor.
    """

    validate_frozen_molerec_identity(
        source_revision=source_revision,
        profile=profile,
        checkpoint_sha256=checkpoint_sha256,
        dataset_id=dataset_id,
    )
    score_extractor = getattr(model, "score_extractor", None)
    register_pre = getattr(score_extractor, "register_forward_pre_hook", None)
    register_post = getattr(score_extractor, "register_forward_hook", None)
    if not callable(register_pre) or not callable(register_post):
        raise ProtocolMismatch("MoleRec score_extractor does not expose forward hooks")

    captured: dict[str, Any] = {}

    def pre_hook(_module: Any, inputs: tuple[Any, ...]) -> None:
        if not inputs:
            raise ProtocolMismatch("score_extractor received no molecule_embeddings")
        captured["embeddings"] = inputs[0]

    def post_hook(_module: Any, _inputs: tuple[Any, ...], output: Any) -> None:
        captured["score_extractor_output"] = output

    model.eval()
    pre_handle = register_pre(pre_hook)
    post_handle = register_post(post_hook)
    no_grad_active = True
    try:
        with _torch_no_grad():
            try:
                import torch
            except ImportError:
                torch = None
            if torch is not None:
                no_grad_active = not bool(torch.is_grad_enabled())
            output = model(*tuple(forward_args), **dict(forward_kwargs or {}))
            if torch is not None:
                no_grad_active = no_grad_active and not bool(torch.is_grad_enabled())
    finally:
        pre_handle.remove()
        post_handle.remove()

    if "embeddings" not in captured or "score_extractor_output" not in captured:
        raise ProtocolMismatch("MoleRec forward did not execute score_extractor")
    model_output = output[0] if isinstance(output, (tuple, list)) else output
    scores = _score_vector(model_output)
    extractor_scores = _score_vector(captured["score_extractor_output"])
    if len(scores) != len(extractor_scores) or any(
        not math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-7)
        for a, b in ((scores[index], extractor_scores[index]) for index in range(len(scores)))
    ):
        raise ProtocolMismatch("MoleRec returned scores inconsistent with score_extractor")

    embeddings = _embedding_rows(captured["embeddings"])
    requires_grad = bool(getattr(captured["embeddings"], "requires_grad", False))
    output_requires_grad = bool(getattr(model_output, "requires_grad", False))
    if not no_grad_active or requires_grad or output_requires_grad:
        raise ProtocolMismatch("MoleRec frozen forward produced a gradient-bearing tensor")
    if bool(getattr(model, "training", False)):
        raise ProtocolMismatch("MoleRec model is not in eval mode")
    return FrozenMoleRecFeatures(
        scores=scores,
        embeddings=embeddings,
        source_revision=source_revision,
        profile=profile,
        checkpoint_sha256=checkpoint_sha256,
        dataset_id=dataset_id,
        no_grad=no_grad_active,
    )


# Short alias used by callers that already name the model backbone explicitly.
extract_molerec_features = extract_frozen_molerec_features


def validate_frozen_molerec_identity(
    *,
    source_revision: str,
    profile: str,
    checkpoint_sha256: str,
    dataset_id: str,
) -> None:
    """Reject integration inputs that are not the already-qualified frozen identity."""

    expected = {
        "source_revision": UPSTREAM_MOLEREC_REVISION,
        "profile": MOLEREC_PROFILE,
        "checkpoint_sha256": MOLEREC_CHECKPOINT_SHA256,
        "dataset_id": DATASET_ID,
    }
    observed = {
        "source_revision": source_revision,
        "profile": profile,
        "checkpoint_sha256": checkpoint_sha256,
        "dataset_id": dataset_id,
    }
    if observed != expected:
        raise ProtocolMismatch("frozen MoleRec integration identity mismatch")


def gate01_split_u(patient_id: int) -> float:
    """Return the exact v1.2 patient-only split hash value."""

    if isinstance(patient_id, bool) or not isinstance(patient_id, int) or patient_id < 0:
        raise ValueError("patient_id must be a non-negative zero-based integer")
    patient_key = str(patient_id)
    message = f"{SPLIT_NAMESPACE}:{patient_key}".encode()
    value = int.from_bytes(hashlib.sha256(message).digest()[:8], "big", signed=False)
    return value / float(2**64)


def gate01_partition(patient_id: int) -> str:
    """Assign one patient to the deterministic Dev/Audit half split."""

    return "Gate01-Dev" if gate01_split_u(patient_id) < 0.5 else "Gate01-Audit"


classify_gate01 = gate01_partition


def _canonical_positions(vocabulary: Sequence[str] | None, size: int) -> dict[int, int]:
    if vocabulary is None:
        return {index: index for index in range(size)}
    if len(vocabulary) != size:
        raise ValueError("canonical medication vocabulary length does not match candidate count")
    if len(set(vocabulary)) != size:
        raise ValueError("canonical medication vocabulary contains duplicate codes")
    return {
        index: rank
        for rank, index in enumerate(sorted(range(size), key=lambda i: str(vocabulary[i])))
    }


def _require_protocol_candidate_pool(size: int) -> None:
    """Require the complete pinned medication vocabulary for protocol paths."""

    if size != CANDIDATE_COUNT:
        raise ProtocolMismatch(
            f"Idea 008 Gate 01 requires exactly {CANDIDATE_COUNT} medication candidates"
        )


def _ordered_indices(
    indices: Iterable[int], vocabulary: Sequence[str] | None, size: int
) -> tuple[int, ...]:
    positions = _canonical_positions(vocabulary, size)
    return tuple(sorted(indices, key=lambda index: positions[index]))


def exact_topk(
    scores: Sequence[float], k_x: int, vocabulary: Sequence[str] | None = None
) -> tuple[int, ...]:
    """Return exactly ``k_x`` indices with canonical ascending-code ties."""

    _require_protocol_candidate_pool(len(scores))
    if not 0 <= k_x <= len(scores):
        raise ValueError("K_x must lie in [0, candidate_count]")
    positions = _canonical_positions(vocabulary, len(scores))
    ranked = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), positions[i]))
    return tuple(ranked[:k_x])


def deterministic_ranking(
    scores: Sequence[float], vocabulary: Sequence[str] | None = None
) -> tuple[int, ...]:
    """Rank all candidates by frozen score and canonical medication order."""

    positions = _canonical_positions(vocabulary, len(scores))
    return tuple(sorted(range(len(scores)), key=lambda i: (-float(scores[i]), positions[i])))


def greedy_ranking(
    selected: Iterable[int],
    scores: Sequence[float],
    vocabulary: Sequence[str] | None = None,
) -> tuple[int, ...]:
    """Section 10.1 ranking: selected first, then frozen-score order."""

    selected_set = set(selected)
    positions = _canonical_positions(vocabulary, len(scores))
    return tuple(
        sorted(
            range(len(scores)),
            key=lambda index: (
                0 if index in selected_set else 1,
                -float(scores[index]),
                positions[index],
            ),
        )
    )


def frozen_base_set(
    probabilities: Sequence[float], vocabulary: Sequence[str] | None = None
) -> tuple[int, ...]:
    """Materialize the Frozen Base set from the fixed ``0.5`` threshold."""

    _require_protocol_candidate_pool(len(probabilities))
    selected = [
        index for index, probability in enumerate(probabilities) if float(probability) >= 0.5
    ]
    return _ordered_indices(selected, vocabulary, len(probabilities))


def frozen_base_cardinality(probabilities: Sequence[float]) -> int:
    return len(frozen_base_set(probabilities))


def calibrate_budgets(base_ddi_rates: Iterable[float]) -> tuple[float, float, float, float]:
    """Return ``r_train, b_L, b_M, b_H`` without clipping or extra targets."""

    rates = tuple(float(rate) for rate in base_ddi_rates)
    if not rates:
        raise ValueError("Gate01-Train base DDI rates are empty")
    r_train = sum(rates) / len(rates)
    if r_train == 0.0:
        raise ProtocolMismatch("STOP_NO_BASE_DDI_HEADROOM")
    return r_train, 0.60 * r_train, 0.80 * r_train, 1.00 * r_train


def sigmoid(value: float) -> float:
    if value >= 0:
        exponent = math.exp(-value)
        return 1.0 / (1.0 + exponent)
    exponent = math.exp(value)
    return exponent / (1.0 + exponent)


def softplus(value: float) -> float:
    return max(value, 0.0) + math.log1p(math.exp(-abs(value)))


def hard_ddi(
    selected: Iterable[int], ddi: Sequence[Sequence[float]], k_x: int | None = None
) -> float:
    selected = tuple(selected)
    cardinality = len(selected) if k_x is None else int(k_x)
    if cardinality < 2:
        return 0.0
    pair_sum = sum(
        float(ddi[i][j]) for offset, i in enumerate(selected) for j in selected[offset + 1 :]
    )
    return pair_sum / math.comb(cardinality, 2)


def relaxed_ddi(q: Sequence[float], ddi: Sequence[Sequence[float]], k_x: int) -> float:
    if k_x < 2:
        return 0.0
    pair_sum = sum(
        float(ddi[i][j]) * float(q[i]) * float(q[j])
        for i in range(len(q))
        for j in range(i + 1, len(q))
    )
    return pair_sum / math.comb(k_x, 2)


def marginal_ddi(q: Sequence[float], ddi: Sequence[Sequence[float]], k_x: int) -> tuple[float, ...]:
    if k_x < 2:
        return tuple(0.0 for _ in q)
    denominator = k_x - 1
    return tuple(
        sum(float(ddi[i][j]) * float(q[j]) for j in range(len(q)) if j != i) / denominator
        for i in range(len(q))
    )


def _vector_from_head(value: Any, size: int) -> tuple[float, ...]:
    value = _python_value(value)
    if isinstance(value, (list, tuple)):
        if len(value) == size:
            return tuple(float(item) for item in value)
        if len(value) == 1 and not isinstance(value[0], (list, tuple)):
            return tuple(float(value[0]) for _ in range(size))
    if isinstance(value, (int, float)):
        return tuple(float(value) for _ in range(size))
    raise ProtocolMismatch("candidate head did not return one value per medication")


def _call_head(head: Callable[..., Any] | None, size: int, *args: Any) -> tuple[float, ...]:
    if head is None:
        return tuple(0.0 for _ in range(size))
    return _vector_from_head(head(*args), size)


@dataclass(frozen=True)
class BudgetSetTrace:
    z_final: tuple[float, ...]
    q_before_update: tuple[tuple[float, ...], ...]
    c_before_update: tuple[tuple[float, ...], ...]
    rho_before_update: tuple[float, ...]


def budgetset_recurrence(
    scores: Sequence[float],
    embeddings: Sequence[Sequence[float]],
    budget: float,
    ddi: Sequence[Sequence[float]],
    k_x: int,
    utility_head: Callable[..., Any] | None,
    risk_price_head: Callable[..., Any] | None,
) -> BudgetSetTrace:
    """Run exactly ``q0 -> c0,rho0 -> z1,q1 -> c1,rho1 -> z2``."""

    if len(scores) != CANDIDATE_COUNT or len(embeddings) != CANDIDATE_COUNT:
        raise ProtocolMismatch("BudgetSet requires the complete 131-medication candidate pool")
    z = tuple(float(value) for value in scores)
    q = tuple(sigmoid(value) for value in z)
    q_trace: list[tuple[float, ...]] = []
    c_trace: list[tuple[float, ...]] = []
    rho_trace: list[float] = []
    for _ in range(T):
        c = marginal_ddi(q, ddi, k_x)
        rho = float(budget) - relaxed_ddi(q, ddi, k_x)
        utility = _call_head(utility_head, len(scores), tuple(scores), embeddings)
        prices = _call_head(risk_price_head, len(scores), tuple(scores), embeddings, rho)
        q_trace.append(q)
        c_trace.append(c)
        rho_trace.append(rho)
        z = tuple(
            float(scores[i]) + utility[i] - softplus(prices[i]) * c[i] for i in range(len(scores))
        )
        q = tuple(sigmoid(value) for value in z)
    return BudgetSetTrace(
        z_final=z,
        q_before_update=tuple(q_trace),
        c_before_update=tuple(c_trace),
        rho_before_update=tuple(rho_trace),
    )


def budgetset_hard_set(
    scores: Sequence[float],
    embeddings: Sequence[Sequence[float]],
    budget: float,
    ddi: Sequence[Sequence[float]],
    k_x: int,
    utility_head: Callable[..., Any] | None,
    risk_price_head: Callable[..., Any] | None,
    vocabulary: Sequence[str] | None = None,
) -> tuple[int, ...]:
    trace = budgetset_recurrence(
        scores, embeddings, budget, ddi, k_x, utility_head, risk_price_head
    )
    return exact_topk(trace.z_final, k_x, vocabulary)


class BudgetConditionedIndependentScorer:
    """Independent control with only frozen per-candidate inputs and ``+s``."""

    FORBIDDEN_INPUTS = frozenset(
        {"q", "q_t", "c", "rho", "provisional_set", "current_set", "pair_features", "feedback"}
    )

    def __init__(
        self,
        utility_head: Callable[..., Any] | None = None,
        risk_price_head: Callable[..., Any] | None = None,
    ) -> None:
        self.utility_head = utility_head
        self.risk_price_head = risk_price_head

    def score(
        self,
        scores: Sequence[float],
        embeddings: Sequence[Sequence[float]],
        budget: float,
        d_static: Sequence[float],
        p_static: Sequence[float],
    ) -> tuple[float, ...]:
        _require_protocol_candidate_pool(len(scores))
        if len(embeddings) != CANDIDATE_COUNT:
            raise ProtocolMismatch("Independent embeddings must cover the complete candidate pool")
        if len(scores) != len(d_static) or len(scores) != len(p_static):
            raise ValueError("Independent static summaries must align with scores")
        utility = _call_head(self.utility_head, len(scores), tuple(scores), embeddings)
        prices = _call_head(
            self.risk_price_head,
            len(scores),
            tuple(scores),
            embeddings,
            float(budget),
            tuple(float(value) for value in d_static),
            tuple(float(value) for value in p_static),
        )
        return tuple(
            float(scores[i]) + utility[i] - softplus(prices[i]) * float(d_static[i])
            for i in range(len(scores))
        )

    def hard_set(
        self,
        scores: Sequence[float],
        embeddings: Sequence[Sequence[float]],
        budget: float,
        d_static: Sequence[float],
        p_static: Sequence[float],
        k_x: int,
        vocabulary: Sequence[str] | None = None,
    ) -> tuple[int, ...]:
        return exact_topk(
            self.score(scores, embeddings, budget, d_static, p_static), k_x, vocabulary
        )


def static_ddi_summaries(
    train_targets: Iterable[Iterable[int]], ddi: Sequence[Sequence[float]]
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Compute Train-only ``d_i`` and ``p_i`` for the Independent control."""

    targets = [frozenset(target) for target in train_targets]
    candidate_count = len(ddi)
    denominator = max(1, candidate_count - 1)
    d_static = tuple(
        sum(float(ddi[i][j]) for j in range(candidate_count) if j != i) / denominator
        for i in range(candidate_count)
    )
    p_values: list[float] = []
    for i in range(candidate_count):
        containing = [target for target in targets if i in target]
        with_pair = sum(
            any(j != i and j in target and float(ddi[i][j]) != 0.0 for j in target)
            for target in containing
        )
        p_values.append(with_pair / max(1, len(containing)))
    return d_static, tuple(p_values)


def _pair_count(selected: Iterable[int], ddi: Sequence[Sequence[float]]) -> float:
    selected = tuple(selected)
    return sum(
        float(ddi[i][j]) for offset, i in enumerate(selected) for j in selected[offset + 1 :]
    )


def _set_sort_key(selected: Iterable[int], positions: Mapping[int, int]) -> tuple[int, ...]:
    return tuple(sorted(positions[index] for index in selected))


def greedy_budget_aware_1swap(
    scores: Sequence[float],
    ddi: Sequence[Sequence[float]],
    budget: float,
    k_x: int,
    vocabulary: Sequence[str] | None = None,
) -> tuple[int, ...]:
    """Deterministic Section 7 Greedy construction followed by 1-Swap."""

    n = len(scores)
    _require_protocol_candidate_pool(n)
    if not 0 <= k_x <= n:
        raise ValueError("K_x must lie in [0, candidate_count]")
    if k_x == 0:
        return ()
    if k_x == 1:
        return exact_topk(scores, 1, vocabulary)

    positions = _canonical_positions(vocabulary, n)
    total_budget = float(budget) * math.comb(k_x, 2)
    selected: set[int] = set()
    while len(selected) < k_x:
        remaining = [index for index in range(n) if index not in selected]
        feasible = [
            index for index in remaining if _pair_count((*selected, index), ddi) <= total_budget
        ]
        if feasible:
            candidate = min(feasible, key=lambda index: (-float(scores[index]), positions[index]))
        else:
            candidate = min(
                remaining,
                key=lambda index: (
                    _pair_count((*selected, index), ddi),
                    -float(scores[index]),
                    positions[index],
                ),
            )
        selected.add(candidate)

    def violation(indices: Iterable[int]) -> float:
        return max(0.0, _pair_count(indices, ddi) / math.comb(k_x, 2) - float(budget))

    while violation(selected) > 0:
        candidates: list[tuple[float, float, tuple[int, ...], int, int, set[int]]] = []
        current_violation = violation(selected)
        for outgoing in sorted(selected, key=lambda index: positions[index]):
            for incoming in range(n):
                if incoming in selected:
                    continue
                proposal = set(selected)
                proposal.remove(outgoing)
                proposal.add(incoming)
                reduced = current_violation - violation(proposal)
                if reduced > 0:
                    candidates.append(
                        (
                            -reduced,
                            -sum(float(scores[index]) for index in proposal),
                            _set_sort_key(proposal, positions),
                            outgoing,
                            incoming,
                            proposal,
                        )
                    )
        if not candidates:
            break
        selected = min(candidates)[-1]

    while True:
        feasible_swaps: list[tuple[float, float, tuple[int, ...], set[int]]] = []
        current_sum = sum(float(scores[index]) for index in selected)
        current_pair_budget = total_budget
        for outgoing in sorted(selected, key=lambda index: positions[index]):
            for incoming in range(n):
                if incoming in selected:
                    continue
                proposal = set(selected)
                proposal.remove(outgoing)
                proposal.add(incoming)
                if _pair_count(proposal, ddi) <= current_pair_budget:
                    gain = sum(float(scores[index]) for index in proposal) - current_sum
                    if gain > 0:
                        feasible_swaps.append(
                            (
                                -gain,
                                _pair_count(proposal, ddi) / math.comb(k_x, 2),
                                _set_sort_key(proposal, positions),
                                proposal,
                            )
                        )
        if not feasible_swaps:
            break
        selected = min(feasible_swaps)[-1]
    result = _ordered_indices(selected, vocabulary, n)
    if len(result) != k_x:
        raise ProtocolMismatch("Greedy failed exact fixed-cardinality output")
    return result


def standardized_logits(scores: Sequence[float]) -> tuple[float, ...]:
    mean = sum(float(value) for value in scores) / len(scores)
    variance = sum((float(value) - mean) ** 2 for value in scores) / len(scores)
    std = math.sqrt(variance)
    scale = max(std, 1e-6)
    return tuple((float(value) - mean) / scale for value in scores)


def fixed_lambda_scores(
    scores: Sequence[float],
    ddi: Sequence[Sequence[float]],
    k_x: int,
    lam: float,
) -> tuple[float, ...]:
    _require_protocol_candidate_pool(len(scores))
    normalized = standardized_logits(scores)
    q = tuple(sigmoid(value) for value in normalized)
    z = normalized
    for _ in range(T):
        c = marginal_ddi(q, ddi, k_x)
        z = tuple(normalized[i] - float(lam) * c[i] for i in range(len(scores)))
        q = tuple(sigmoid(value) for value in z)
    return z


def fixed_lambda_family(
    scores: Sequence[float],
    ddi: Sequence[Sequence[float]],
    k_x: int,
    vocabulary: Sequence[str] | None = None,
    lambdas: Sequence[float] = FIXED_LAMBDAS,
) -> dict[float, tuple[int, ...]]:
    _require_protocol_candidate_pool(len(scores))
    return {
        float(lam): exact_topk(fixed_lambda_scores(scores, ddi, k_x, float(lam)), k_x, vocabulary)
        for lam in lambdas
    }


def select_fixed_lambda(
    mean_ddi_by_lambda: Mapping[float, float],
    target: float,
    mean_score_sum_by_lambda: Mapping[float, float],
) -> float:
    if not mean_ddi_by_lambda:
        raise ValueError("fixed-lambda family is empty")
    return min(
        mean_ddi_by_lambda,
        key=lambda lam: (
            abs(float(mean_ddi_by_lambda[lam]) - float(target)),
            -float(mean_score_sum_by_lambda[lam]),
            float(lam),
        ),
    )


@dataclass(frozen=True)
class VisitObservation:
    patient_id: Hashable
    target: frozenset[int]
    prediction: tuple[int, ...]
    ranking: tuple[int, ...]
    k_x: int


def _jaccard(prediction: set[int], target: set[int]) -> float:
    union = prediction | target
    return 1.0 if not union else len(prediction & target) / len(union)


def _f1(prediction: set[int], target: set[int]) -> float:
    if not prediction and not target:
        return 1.0
    denominator = len(prediction) + len(target)
    return 0.0 if denominator == 0 else 2.0 * len(prediction & target) / denominator


def _average_precision(ranking: Sequence[int], target: set[int]) -> float:
    if not target:
        return 0.0
    hits = 0
    total = 0.0
    for rank, candidate in enumerate(ranking, start=1):
        if candidate in target:
            hits += 1
            total += hits / rank
    return total / len(target)


def visit_level_metrics(
    observation: VisitObservation,
    ddi: Sequence[Sequence[float]],
    requested_budget: float,
) -> dict[str, float]:
    prediction = set(observation.prediction)
    target = set(observation.target)
    achieved = hard_ddi(prediction, ddi, observation.k_x)
    return {
        "jaccard": _jaccard(prediction, target),
        "f1": _f1(prediction, target),
        "prauc": _average_precision(observation.ranking, target),
        "hard_ddi": achieved,
        "positive_violation": max(0.0, achieved - requested_budget),
        "absolute_deviation": abs(achieved - requested_budget),
        "mean_medications": float(len(prediction)),
        "exact_k": float(len(prediction) == observation.k_x),
    }


def aggregate_visit_metrics(
    observations: Iterable[VisitObservation],
    ddi: Sequence[Sequence[float]],
    requested_budget: float,
) -> dict[str, float]:
    rows = [visit_level_metrics(row, ddi, requested_budget) for row in observations]
    if not rows:
        raise ValueError("cannot aggregate an empty visit collection")
    keys = rows[0].keys()
    return {key: sum(row[key] for row in rows) / len(rows) for key in keys}


def aggregate_seed_metrics(seed_metrics: Mapping[int, Mapping[str, float]]) -> dict[str, float]:
    """Arithmetic-mean learned-family aggregation without averaging predictions."""

    if not seed_metrics:
        raise ValueError("learned-family seed metrics are empty")
    if set(seed_metrics) != set(LEARNED_SEEDS):
        raise ValueError("learned-family aggregation requires exactly seeds 2002, 2003, and 2004")
    first = next(iter(seed_metrics.values()))
    keys = tuple(first)
    key_set = set(keys)
    if any(set(metrics) != key_set for metrics in seed_metrics.values()):
        raise ValueError("seed metric fields do not align")
    return {
        key: sum(float(metrics[key]) for metrics in seed_metrics.values()) / len(seed_metrics)
        for key in keys
    }


def target_compliant(aggregate: Mapping[str, float], requested_budget: float) -> bool:
    return (
        float(aggregate["positive_violation"]) <= DELTA_U
        and float(aggregate["hard_ddi"]) <= float(requested_budget) + DELTA_R
    )


def composition_change_rate(
    lower_sets: Iterable[Iterable[int]],
    higher_sets: Iterable[Iterable[int]],
    *,
    eligible: Iterable[bool] | None = None,
    k_x_values: Iterable[int] | None = None,
) -> float:
    left = list(lower_sets)
    right = list(higher_sets)
    if len(left) != len(right):
        raise ValueError("composition comparison collections must align")
    if eligible is not None and k_x_values is not None:
        raise ValueError("provide either eligible or k_x_values, not both")
    if k_x_values is not None:
        mask = [int(k_x) >= 1 for k_x in k_x_values]
    elif eligible is not None:
        mask = list(eligible)
    else:
        # Exact-K outputs make an empty hard set the K_x=0 branch.
        mask = [bool(left[index]) or bool(right[index]) for index in range(len(left))]
    if len(mask) != len(left):
        raise ValueError("composition eligibility mask must align")
    compared = [index for index, include in enumerate(mask) if include]
    if not compared:
        return 0.0
    return sum(set(left[index]) != set(right[index]) for index in compared) / len(compared)


@dataclass(frozen=True)
class OperatingPoint:
    risk: float
    utility: float
    order: int
    seed: int | None = None
    budget: float | None = None


@dataclass(frozen=True)
class FrontierComparison:
    branch: str
    selected_order: int
    utility_gap: float
    risk_gap: float
    favorable: bool


def compare_seed_frontier(
    budget_point: OperatingPoint,
    control_points: Sequence[OperatingPoint],
    *,
    delta_r: float = DELTA_R,
) -> FrontierComparison:
    """Apply the v1.2 total seed-level frontier comparator."""

    if not control_points:
        raise InvalidGateImplementation("required killer control family has zero sampled points")
    eligible = [point for point in control_points if point.risk <= budget_point.risk + delta_r]
    if eligible:
        selected = min(eligible, key=lambda point: (-point.utility, point.order))
        gap = budget_point.utility - selected.utility
        return FrontierComparison(
            branch="ordinary",
            selected_order=selected.order,
            utility_gap=gap,
            risk_gap=selected.risk - budget_point.risk,
            favorable=gap > 0.0,
        )
    selected = min(control_points, key=lambda point: (point.risk, -point.utility, point.order))
    utility_gap = budget_point.utility - selected.utility
    return FrontierComparison(
        branch="empty",
        selected_order=selected.order,
        utility_gap=utility_gap,
        risk_gap=selected.risk - budget_point.risk,
        favorable=utility_gap >= 0.0,
    )


def compare_aggregate_frontier(
    budget_point: OperatingPoint,
    control_points: Sequence[OperatingPoint],
    *,
    delta_u: float = DELTA_U,
    delta_r: float = DELTA_R,
    bootstrap_lower_bound: float | None,
) -> FrontierComparison:
    """Apply Section 11 materiality, retaining the same total endpoint choice."""

    comparison = compare_seed_frontier(budget_point, control_points, delta_r=delta_r)
    if bootstrap_lower_bound is None:
        material = False
    elif comparison.branch == "ordinary":
        material = comparison.utility_gap >= delta_u and bootstrap_lower_bound > 0.0
    else:
        material = (
            comparison.risk_gap >= delta_r
            and comparison.utility_gap >= -delta_u
            and bootstrap_lower_bound > -delta_u
        )
    return FrontierComparison(
        branch=comparison.branch,
        selected_order=comparison.selected_order,
        utility_gap=comparison.utility_gap,
        risk_gap=comparison.risk_gap,
        favorable=material,
    )


def matched_independent_frontier(
    budget_seed: int,
    budget_point: OperatingPoint,
    independent_points_by_seed: Mapping[int, Sequence[OperatingPoint]],
) -> FrontierComparison:
    if budget_seed not in LEARNED_SEEDS:
        raise ValueError("unknown learned seed")
    if budget_point.seed != budget_seed:
        raise ProtocolMismatch("BudgetSet point is not labeled with its matched seed")
    try:
        points = independent_points_by_seed[budget_seed]
    except KeyError as error:
        raise InvalidGateImplementation(
            f"missing matched Independent seed {budget_seed}"
        ) from error
    if any(point.seed != budget_seed for point in points):
        raise ProtocolMismatch("Independent seed comparator received an unmatched seed")
    return compare_seed_frontier(budget_point, points)


def seed_robustness_satisfied(comparisons: Mapping[int, FrontierComparison]) -> bool:
    """Return the frozen ``>=2/3`` favorable-seed result."""

    if set(comparisons) != set(LEARNED_SEEDS):
        raise ProtocolMismatch("seed robustness requires exactly seeds 2002, 2003, and 2004")
    return sum(item.favorable for item in comparisons.values()) >= 2


def greedy_frontier(
    budget_point: OperatingPoint, deterministic_points: Sequence[OperatingPoint]
) -> FrontierComparison:
    """Compare every BudgetSet seed against one deterministic Greedy family."""

    if any(point.seed is not None for point in deterministic_points):
        raise ProtocolMismatch("deterministic Greedy points must not carry seed labels")
    return compare_seed_frontier(budget_point, deterministic_points)


def checkpoint_selection_key(
    n_compliant: int, u_primary: float, v_all: float, epoch: int
) -> tuple[int, float, float, int]:
    return (-int(n_compliant), -float(u_primary), float(v_all), int(epoch))


def configuration_selection_key(
    n_compliant_config: int,
    u_primary_config: float,
    v_all_config: float,
    learning_rate: float,
    eta: float,
) -> tuple[int, float, float, float, float]:
    return (
        -int(n_compliant_config),
        -float(u_primary_config),
        float(v_all_config),
        float(learning_rate),
        float(eta),
    )


def _metric_mapping(item: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if isinstance(item, Mapping):
        return item
    return vars(item)


@dataclass(frozen=True)
class CheckpointSelection:
    best: Mapping[str, Any]
    stop_epoch: int


def select_checkpoint_with_patience(
    evaluations: Iterable[Mapping[str, Any]],
    *,
    patience: int = CHECKPOINT_PATIENCE,
    max_epochs: int = MAX_EPOCHS,
) -> CheckpointSelection:
    """Select one per-seed checkpoint with local strict-improvement patience."""

    best: Mapping[str, Any] | None = None
    best_key: tuple[int, float, float, int] | None = None
    non_improvements = 0
    stop_epoch = 0
    for evaluation in evaluations:
        values = _metric_mapping(evaluation)
        epoch = int(values["epoch"])
        if epoch > max_epochs:
            break
        key = checkpoint_selection_key(
            values["n_compliant"], values["u_primary"], values["v_all"], epoch
        )
        if best_key is None or key < best_key:
            best = evaluation
            best_key = key
            non_improvements = 0
        else:
            non_improvements += 1
        stop_epoch = epoch
        if non_improvements >= patience or epoch >= max_epochs:
            break
    if best is None:
        raise ValueError("checkpoint evaluations are empty")
    return CheckpointSelection(best=best, stop_epoch=stop_epoch)


RowT = TypeVar("RowT")


@dataclass(frozen=True)
class BootstrapResult(Generic[RowT]):
    replicate_values: tuple[RowT, ...]
    lower: float
    upper: float


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot calculate a percentile of an empty collection")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def patient_cluster_bootstrap(
    rows: Sequence[RowT],
    *,
    patient_key: Callable[[RowT], Hashable],
    recompute_operating_points: Callable[[Sequence[RowT]], Any],
    recompute_frontier_gap: Callable[[Any], float],
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> BootstrapResult[float]:
    """Resample patient clusters with replacement and recompute frontier per draw.

    The two callbacks are deliberately separate: the first must rebuild all
    sampled operating points from fixed predictions, and the second must build
    the control frontier from those points before returning the gap.  No model
    fitting occurs in this utility.
    """

    if not rows or replicates <= 0:
        raise ValueError("bootstrap requires rows and a positive replicate count")
    groups: dict[Hashable, list[T]] = defaultdict(list)
    patient_order: list[Hashable] = []
    for row in rows:
        patient = patient_key(row)
        if patient not in groups:
            patient_order.append(patient)
        groups[patient].append(row)
    try:
        patient_order = sorted(patient_order, key=lambda patient: str(patient))
    except TypeError as error:
        raise ValueError("patient keys must have a deterministic ordering") from error
    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(replicates):
        sampled_patients = [rng.choice(patient_order) for _ in patient_order]
        sampled_rows = [row for patient in sampled_patients for row in groups[patient]]
        operating_points = recompute_operating_points(sampled_rows)
        values.append(float(recompute_frontier_gap(operating_points)))
    return BootstrapResult(
        replicate_values=tuple(values),
        lower=_percentile(values, 0.025),
        upper=_percentile(values, 0.975),
    )


def terminal_verdict(conditions: Mapping[str, bool]) -> str:
    """Return the first triggered v1.2 terminal condition."""

    for condition in TERMINAL_PRECEDENCE[:-2]:
        if bool(conditions.get(condition, False)):
            return condition
    if bool(conditions.get("INCONCLUSIVE_STOP", False)):
        return "INCONCLUSIVE_STOP"
    if bool(conditions.get("PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES", False)):
        return "PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES"
    return "INCONCLUSIVE_STOP"


def build_mechanical_preflight_record(
    checks: Mapping[str, bool], *, integration: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Build a public-safe record with a mandatory real-backbone gate."""

    check_values = {str(name): value is True for name, value in checks.items()}
    synthetic_passed = SYNTHETIC_MECHANICAL_CHECKS.issubset(check_values) and all(
        check_values[name] for name in SYNTHETIC_MECHANICAL_CHECKS
    )
    integration_mapping = integration if isinstance(integration, Mapping) else None
    if integration is None:
        integration_status = "MISSING"
    elif integration_mapping is None:
        integration_status = "MALFORMED"
    else:
        integration_status = str(integration_mapping.get("integration_status", "MALFORMED"))
    integration_passed = validate_frozen_molerec_integration_result(integration_mapping)
    if not synthetic_passed:
        verdict = "STOP_IMPLEMENTATION_MISMATCH"
    elif integration_passed:
        verdict = "MECHANICAL_PREFLIGHT_PASS"
    elif integration_status in {"MISSING", "BLOCKED", "INCOMPLETE", "UNVALIDATED"}:
        verdict = "MECHANICAL_PREFLIGHT_INCOMPLETE"
    else:
        verdict = "STOP_IMPLEMENTATION_MISMATCH"
    final_checks = {
        name: bool(check_values.get(name, False)) for name in REQUIRED_MECHANICAL_CHECKS
    }
    final_checks["same_frozen_no_grad_forward"] = (
        bool(integration_passed and integration_mapping.get("same_forward", False))
        if integration_mapping is not None
        else False
    )
    final_checks["embedding_candidate_dimension"] = (
        bool(
            integration_passed
            and integration_mapping.get("embedding_candidate_dimension") == CANDIDATE_COUNT
        )
        if integration_mapping is not None
        else False
    )
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "IDEA_008_GATE_01_MECHANICAL_PREFLIGHT",
        "protocol_revision": PROTOCOL_VERSION,
        "checks": final_checks,
        "verdict": verdict,
        "training": "NOT_RUN",
        "formal_gate_execution": "NOT_RUN",
        "gate01_audit": "UNOPENED",
        "quarantine": "INTACT",
        "scientific_metrics_generated": False,
    }
    if integration_mapping is not None:
        record["frozen_molerec_integration"] = {
            field: integration_mapping[field]
            for field in INTEGRATION_PUBLIC_FIELDS
            if field in integration_mapping
        }
    return record


def frozen_molerec_integration_summary(
    features: FrozenMoleRecFeatures,
    *,
    validated_real: bool = False,
) -> dict[str, Any]:
    """Return an identity/shape/boolean-only integration summary.

    ``validated_real`` is deliberately explicit.  Synthetic hook fixtures may
    exercise this extraction utility, but they cannot authorize the final
    mechanical preflight verdict.
    """

    validate_frozen_molerec_identity(
        source_revision=features.source_revision,
        profile=features.profile,
        checkpoint_sha256=features.checkpoint_sha256,
        dataset_id=features.dataset_id,
    )
    return {
        "integration_status": "PASS" if validated_real else "UNVALIDATED",
        "validated_real": bool(validated_real),
        "source_revision": features.source_revision,
        "profile": features.profile,
        "checkpoint_sha256": features.checkpoint_sha256,
        "dataset_id": features.dataset_id,
        "partition": "canonical Comparison Train only",
        "model_eval": features.eval_mode,
        "no_gradient": features.no_grad,
        "same_forward": features.same_forward,
        "score_candidate_dimension": features.candidate_count,
        "embedding_candidate_dimension": len(features.embeddings),
        "score_shape": [features.candidate_count],
        "embedding_shape": [features.candidate_count, features.embedding_width],
        "embedding_rank": 2,
        "score_extractor_consistent": True,
    }


def validate_frozen_molerec_integration_result(
    integration: Mapping[str, Any] | None,
) -> bool:
    """Return whether a public-safe result proves the real frozen integration."""

    if integration is None:
        return False
    if not isinstance(integration, Mapping):
        return False
    if integration.get("integration_status") != "PASS":
        return False
    if integration.get("validated_real") is not True:
        return False
    if {
        "source_revision": integration.get("source_revision"),
        "profile": integration.get("profile"),
        "checkpoint_sha256": integration.get("checkpoint_sha256"),
        "dataset_id": integration.get("dataset_id"),
    } != {
        "source_revision": UPSTREAM_MOLEREC_REVISION,
        "profile": MOLEREC_PROFILE,
        "checkpoint_sha256": MOLEREC_CHECKPOINT_SHA256,
        "dataset_id": DATASET_ID,
    }:
        return False
    if integration.get("partition") != "canonical Comparison Train only":
        return False
    if not all(
        integration.get(name) is True
        for name in ("model_eval", "no_gradient", "same_forward", "score_extractor_consistent")
    ):
        return False
    if integration.get("score_candidate_dimension") != CANDIDATE_COUNT:
        return False
    if integration.get("embedding_candidate_dimension") != CANDIDATE_COUNT:
        return False
    if integration.get("embedding_rank") != 2:
        return False
    try:
        score_shape = tuple(integration.get("score_shape", ()))
        embedding_shape = tuple(integration.get("embedding_shape", ()))
    except TypeError:
        return False
    if score_shape != (CANDIDATE_COUNT,):
        return False
    if len(embedding_shape) != 2 or embedding_shape[0] != CANDIDATE_COUNT:
        return False
    return type(embedding_shape[1]) is int and embedding_shape[1] > 0


def write_public_record(path: Path, record: Mapping[str, Any]) -> None:
    """Atomically write a public-safe JSON record under the canonical path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(record, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _self_check_record() -> dict[str, Any]:
    """Run public synthetic checks only; this is not Gate execution."""

    import inspect

    scores = [float(index) / 10.0 for index in range(CANDIDATE_COUNT)]
    embeddings = [[float(index), 1.0] for index in range(CANDIDATE_COUNT)]
    zero_ddi = [[0.0] * CANDIDATE_COUNT for _ in range(CANDIDATE_COUNT)]
    ddi = [[0.0] * CANDIDATE_COUNT for _ in range(CANDIDATE_COUNT)]
    ddi[0][1] = ddi[1][0] = 1.0

    def zero(*_args: Any) -> list[float]:
        return [0.0] * CANDIDATE_COUNT

    trace = budgetset_recurrence(scores, embeddings, 0.2, zero_ddi, 2, zero, zero)
    state_trace = budgetset_recurrence(scores, embeddings, 0.2, ddi, 2, zero, zero)
    independent = BudgetConditionedIndependentScorer(zero, zero)
    vocabulary = tuple(f"M{index:03d}" for index in range(CANDIDATE_COUNT))

    def close_sequence(left: Sequence[float], right: Sequence[float]) -> bool:
        return len(left) == len(right) and all(
            math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)
            for a, b in ((left[index], right[index]) for index in range(len(left)))
        )

    class _Hook:
        def __init__(self, callbacks: list[Any], callback: Any) -> None:
            self.callbacks = callbacks
            self.callback = callback

        def remove(self) -> None:
            self.callbacks.remove(self.callback)

    class _Extractor:
        def __init__(self) -> None:
            self.pre: list[Any] = []
            self.post: list[Any] = []

        def register_forward_pre_hook(self, callback: Any) -> _Hook:
            self.pre.append(callback)
            return _Hook(self.pre, callback)

        def register_forward_hook(self, callback: Any) -> _Hook:
            self.post.append(callback)
            return _Hook(self.post, callback)

        def __call__(self, rows: list[list[float]]) -> list[float]:
            for callback in tuple(self.pre):
                callback(self, (rows,))
            output = [row[0] for row in rows]
            for callback in tuple(self.post):
                callback(self, (rows,), output)
            return output

    class _Model:
        def __init__(self) -> None:
            self.score_extractor = _Extractor()
            self.training = True

        def eval(self) -> _Model:
            self.training = False
            return self

        def __call__(self) -> tuple[list[float], None]:
            rows = [[float(index), 1.0] for index in range(CANDIDATE_COUNT)]
            return self.score_extractor(rows), None

    _synthetic_features = extract_frozen_molerec_features(
        _Model(),
        source_revision=UPSTREAM_MOLEREC_REVISION,
        profile=MOLEREC_PROFILE,
        checkpoint_sha256=MOLEREC_CHECKPOINT_SHA256,
        dataset_id=DATASET_ID,
    )
    seed_points = {seed: (OperatingPoint(0.20, 0.40, 0, seed=seed),) for seed in LEARNED_SEEDS}
    matched = matched_independent_frontier(
        2002, OperatingPoint(0.10, 0.50, 0, seed=2002), seed_points
    )
    ordinary = compare_seed_frontier(
        OperatingPoint(0.10, 0.50, 0), (OperatingPoint(0.10, 0.40, 0),)
    )
    empty = compare_seed_frontier(OperatingPoint(0.10, 0.50, 0), (OperatingPoint(0.20, 0.50, 0),))
    sampled_lengths: list[int] = []
    frontier_calls: list[int] = []
    rows = (
        ("p1", "a"),
        ("p1", "b"),
        ("p2", "c"),
    )

    def recompute(sampled: Sequence[tuple[str, str]]) -> dict[str, int]:
        sampled_lengths.append(len(sampled))
        return {"rows": len(sampled)}

    def recompute_frontier(points: Mapping[str, int]) -> float:
        frontier_calls.append(points["rows"])
        return float(points["rows"])

    patient_cluster_bootstrap(
        rows,
        patient_key=lambda row: row[0],
        recompute_operating_points=recompute,
        recompute_frontier_gap=recompute_frontier,
        replicates=4,
        seed=BOOTSTRAP_SEED,
    )
    checks = {
        "explicit_residual_anchor": close_sequence(trace.z_final, scores)
        and close_sequence(
            independent.score(scores, embeddings, 0.2, [0.0] * 131, [0.0] * 131), scores
        ),
        "t_two_recomputes_state": state_trace.q_before_update[0] != state_trace.q_before_update[1]
        and state_trace.c_before_update[1]
        == tuple(marginal_ddi(state_trace.q_before_update[1], ddi, 2)),
        "exact_k_hard_outputs": all(
            len(output) == 3
            for output in (
                exact_topk(trace.z_final, 3, vocabulary),
                independent.hard_set(scores, embeddings, 0.2, [0.0] * 131, [0.0] * 131, 3),
                greedy_budget_aware_1swap(scores, ddi, 0.2, 3, vocabulary),
                *fixed_lambda_family(scores, ddi, 3, vocabulary).values(),
            )
        ),
        "low_cardinality_semantics": greedy_budget_aware_1swap(scores, ddi, 0.0, 0) == ()
        and len(greedy_budget_aware_1swap(scores, ddi, 0.0, 1)) == 1
        and relaxed_ddi((0.5,) * 131, ddi, 1) == 0.0
        and marginal_ddi((0.5,) * 131, ddi, 1) == (0.0,) * 131,
        "exact_v12_split_hash": all(
            gate01_partition(patient) == expected
            for patient, expected in {
                0: "Gate01-Dev",
                1: "Gate01-Dev",
                2: "Gate01-Audit",
                6: "Gate01-Audit",
                8: "Gate01-Audit",
            }.items()
        ),
        "deterministic_greedy_1swap": greedy_budget_aware_1swap(scores, ddi, 0.2, 3, vocabulary)
        == greedy_budget_aware_1swap(scores, ddi, 0.2, 3, vocabulary),
        "independent_no_current_set_feedback": not BudgetConditionedIndependentScorer.FORBIDDEN_INPUTS.intersection(
            inspect.signature(BudgetConditionedIndependentScorer.score).parameters
        ),
        "ordinary_frontier": ordinary.branch == "ordinary" and ordinary.favorable,
        "empty_frontier": empty.branch == "empty" and empty.favorable,
        "matched_independent_seeds": matched.favorable,
        "deterministic_controls_no_seeds": all(
            point.seed is None for point in (OperatingPoint(0.1, 0.2, 0),)
        )
        and tuple(fixed_lambda_family(scores, ddi, 3)) == FIXED_LAMBDAS,
        "patient_bootstrap_recomputes_frontier": sampled_lengths == frontier_calls
        and len(sampled_lengths) == 4
        and len(set(sampled_lengths)) > 1,
        "terminal_precedence": terminal_verdict(
            {"STOP_INVALID_GATE_IMPLEMENTATION": True, "KILL_BUDGETSET": True}
        )
        == "STOP_INVALID_GATE_IMPLEMENTATION",
    }
    return build_mechanical_preflight_record(checks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="canonical public-safe JSON output path")
    args = parser.parse_args()
    record = _self_check_record()
    if args.output is not None:
        write_public_record(args.output, record)
    print(json.dumps({"verdict": record["verdict"]}, sort_keys=True))
    return 0 if record["verdict"] == "MECHANICAL_PREFLIGHT_PASS" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
