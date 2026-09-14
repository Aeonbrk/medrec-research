"""Idea 008 Gate 01 v1.2 execution runner.

This module owns the learned BudgetSet and Independent shells and the small
training orchestration needed by a later, explicitly authorized Gate run. It
does not discover data, open Gate01-Audit, or start training when imported. The
protocol's deterministic and evaluation semantics remain owned by
``gate01_mechanical_preflight`` and are re-exported here for the execution
caller.

PyTorch is intentionally optional in the Mac harness environment. The
``medrec-molerec-table1`` Conda environment used by the later 319 run supplies
it; importing this module locally still permits protocol and selection tests.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import inspect
import json
import math
import random
import sys
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence as SequenceABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Mapping, Sequence  # noqa: UP035


def _load_mechanical_preflight() -> Any:
    """Load the sibling Idea-local module in script and test import modes."""

    module_path = Path(__file__).with_name("gate01_mechanical_preflight.py").resolve()
    for name in ("idea008_gate01_mechanical_preflight", "gate01_mechanical_preflight"):
        module = sys.modules.get(name)
        module_file = getattr(module, "__file__", None) if module is not None else None
        if module is not None and module_file is not None:
            try:
                same_path = Path(module_file).resolve() == module_path
            except OSError:
                same_path = False
        else:
            same_path = False
        if same_path:
            return module

    spec = importlib.util.spec_from_file_location(
        "idea008_gate01_mechanical_preflight", module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load mechanical preflight from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_PREFLIGHT = _load_mechanical_preflight()

# The preflight module is the single owner of these protocol semantics. Keep
# aliases here so an execution caller cannot accidentally implement a second
# tie-breaker, split, frontier, or terminal-decision variant.
ProtocolMismatch = _PREFLIGHT.ProtocolMismatch
InvalidGateImplementation = _PREFLIGHT.InvalidGateImplementation
FrozenMoleRecFeatures = _PREFLIGHT.FrozenMoleRecFeatures
OperatingPoint = _PREFLIGHT.OperatingPoint
FrontierComparison = _PREFLIGHT.FrontierComparison
CheckpointSelection = _PREFLIGHT.CheckpointSelection
BootstrapResult = _PREFLIGHT.BootstrapResult

extract_frozen_molerec_features = _PREFLIGHT.extract_frozen_molerec_features
extract_molerec_features = _PREFLIGHT.extract_molerec_features
validate_frozen_molerec_identity = _PREFLIGHT.validate_frozen_molerec_identity
frozen_molerec_integration_summary = _PREFLIGHT.frozen_molerec_integration_summary
validate_frozen_molerec_integration_result = _PREFLIGHT.validate_frozen_molerec_integration_result
gate01_split_u = _PREFLIGHT.gate01_split_u
gate01_partition = _PREFLIGHT.gate01_partition
classify_gate01 = _PREFLIGHT.classify_gate01
exact_topk = _PREFLIGHT.exact_topk
deterministic_ranking = _PREFLIGHT.deterministic_ranking
greedy_ranking = _PREFLIGHT.greedy_ranking
frozen_base_set = _PREFLIGHT.frozen_base_set
frozen_base_cardinality = _PREFLIGHT.frozen_base_cardinality
budgetset_recurrence = _PREFLIGHT.budgetset_recurrence
budgetset_hard_set = _PREFLIGHT.budgetset_hard_set
BudgetConditionedIndependentScorer = _PREFLIGHT.BudgetConditionedIndependentScorer
calibrate_budgets = _PREFLIGHT.calibrate_budgets
sigmoid = _PREFLIGHT.sigmoid
hard_ddi = _PREFLIGHT.hard_ddi
relaxed_ddi = _PREFLIGHT.relaxed_ddi
marginal_ddi = _PREFLIGHT.marginal_ddi
static_ddi_summaries = _PREFLIGHT.static_ddi_summaries
greedy_budget_aware_1swap = _PREFLIGHT.greedy_budget_aware_1swap
fixed_lambda_scores = _PREFLIGHT.fixed_lambda_scores
fixed_lambda_family = _PREFLIGHT.fixed_lambda_family
select_fixed_lambda = _PREFLIGHT.select_fixed_lambda
visit_level_metrics = _PREFLIGHT.visit_level_metrics
aggregate_visit_metrics = _PREFLIGHT.aggregate_visit_metrics
aggregate_seed_metrics = _PREFLIGHT.aggregate_seed_metrics
target_compliant = _PREFLIGHT.target_compliant
composition_change_rate = _PREFLIGHT.composition_change_rate
compare_seed_frontier = _PREFLIGHT.compare_seed_frontier
compare_aggregate_frontier = _PREFLIGHT.compare_aggregate_frontier
matched_independent_frontier = _PREFLIGHT.matched_independent_frontier
seed_robustness_satisfied = _PREFLIGHT.seed_robustness_satisfied
greedy_frontier = _PREFLIGHT.greedy_frontier
checkpoint_selection_key = _PREFLIGHT.checkpoint_selection_key
configuration_selection_key = _PREFLIGHT.configuration_selection_key
select_checkpoint_with_patience = _PREFLIGHT.select_checkpoint_with_patience
patient_cluster_bootstrap = _PREFLIGHT.patient_cluster_bootstrap
terminal_verdict = _PREFLIGHT.terminal_verdict

PROTOCOL_VERSION = _PREFLIGHT.PROTOCOL_VERSION
SPLIT_NAMESPACE = _PREFLIGHT.SPLIT_NAMESPACE
UPSTREAM_MOLEREC_REVISION = _PREFLIGHT.UPSTREAM_MOLEREC_REVISION
MOLEREC_PROFILE = _PREFLIGHT.MOLEREC_PROFILE
MOLEREC_CHECKPOINT_SHA256 = _PREFLIGHT.MOLEREC_CHECKPOINT_SHA256
DATASET_ID = _PREFLIGHT.DATASET_ID
CANDIDATE_COUNT = _PREFLIGHT.CANDIDATE_COUNT
T = _PREFLIGHT.T
LEARNED_SEEDS = _PREFLIGHT.LEARNED_SEEDS
FIXED_LAMBDAS = _PREFLIGHT.FIXED_LAMBDAS
DELTA_U = _PREFLIGHT.DELTA_U
DELTA_R = _PREFLIGHT.DELTA_R
BOOTSTRAP_REPLICATES = _PREFLIGHT.BOOTSTRAP_REPLICATES
BOOTSTRAP_SEED = _PREFLIGHT.BOOTSTRAP_SEED
MAX_EPOCHS = _PREFLIGHT.MAX_EPOCHS
PATIENCE = _PREFLIGHT.CHECKPOINT_PATIENCE

# Frozen by protocol v1.2. These are constants rather than a caller-facing
# search space; CONFIGURATION_GRID below is exactly the four admitted pairs.
WEIGHT_DECAY = 1e-4
LEARNING_RATES = (3e-4, 1e-3)
ETAS = (5.0, 10.0)
GAMMA = 1e-3
BUDGET_FRACTIONS = (0.60, 0.80, 1.00)

# Existing baseline conventions. The private checkpoint path is supplied by
# the controller on 319; only its already-qualified identity is recorded here.
MOLEREC_CONDA_ENVIRONMENT = "medrec-molerec-table1"
MOLEREC_UPSTREAM_ROOT = "/root/zhb/MoleRec"
MOLEREC_DATASET_SUBDIRECTORY = "snapshots/molerec-table1-c721-www23"


def extract_gate01_molerec_features(
    model: Any,
    *,
    substruct_data: Any,
    mol_data: Any,
    patient_data: Any,
    ddi_mask_H: Any,
    tensor_ddi_adj: Any,
    average_projection: Any,
) -> FrozenMoleRecFeatures:
    """Extract one Gate 01 feature record through the pinned MoleRec contract.

    MoleRec's pinned ``forward`` takes six positional-or-keyword parameters,
    but the formal execution path supplies every one by keyword.  Keeping this
    assembly in the Idea-local runner prevents an external controller from
    accidentally binding ``patient_data`` to ``substruct_data``.
    """

    return extract_frozen_molerec_features(
        model,
        source_revision=UPSTREAM_MOLEREC_REVISION,
        profile=MOLEREC_PROFILE,
        checkpoint_sha256=MOLEREC_CHECKPOINT_SHA256,
        dataset_id=DATASET_ID,
        forward_args=(),
        forward_kwargs={
            "substruct_data": substruct_data,
            "mol_data": mol_data,
            "patient_data": patient_data,
            "ddi_mask_H": ddi_mask_H,
            "tensor_ddi_adj": tensor_ddi_adj,
            "average_projection": average_projection,
        },
    )


def frozen_base_from_logits(
    logits: Sequence[float], vocabulary: Sequence[str] | None = None
) -> tuple[int, ...]:
    """Materialize Frozen Base directly from frozen MoleRec logits."""

    if len(logits) != CANDIDATE_COUNT:
        raise ProtocolMismatch("Frozen Base logits must cover all 131 candidates")
    probabilities = tuple(sigmoid(float(value)) for value in logits)
    return frozen_base_set(probabilities, vocabulary)


def frozen_k_from_logits(logits: Sequence[float]) -> int:
    """Return the protocol ``K_x`` count using sigmoid(logit) >= 0.5."""

    return len(frozen_base_from_logits(logits))


compute_k_x = frozen_k_from_logits

try:  # pragma: no cover - exercised in the 319 Conda environment.
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - the Mac harness has no torch package.
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    F = None  # type: ignore[assignment]


FamilyName = Literal["BudgetSet", "Independent"]


def _require_torch() -> Any:
    if torch is None:
        raise RuntimeError(
            "PyTorch is required for Idea 008 model execution; use the "
            f"{MOLEREC_CONDA_ENVIRONMENT!r} execution environment"
        )
    return torch


@dataclass(frozen=True)
class MLPArchitecture:
    """The non-negotiable architecture of either learned head."""

    input_features: int
    hidden_features: tuple[int, int] = (64, 32)
    output_features: int = 1
    activation: str = "GELU"
    dropout: float = 0.0


if nn is not None:

    class MLPHead(nn.Module):
        """A two-hidden-layer GELU MLP with no dropout."""

        def __init__(self, input_features: int) -> None:
            super().__init__()
            if input_features <= 0:
                raise ValueError("MLP input width must be positive")
            self.architecture = MLPArchitecture(input_features=input_features)
            self.layers = nn.Sequential(
                nn.Linear(input_features, 64),
                nn.GELU(),
                nn.Linear(64, 32),
                nn.GELU(),
                nn.Linear(32, 1),
            )

        def forward(self, values: Any) -> Any:
            return self.layers(values)

else:

    class MLPHead:  # type: ignore[no-redef]
        """Import-safe placeholder when the execution environment lacks torch."""

        def __init__(self, input_features: int) -> None:
            del input_features
            _require_torch()


@dataclass(frozen=True)
class BudgetSetTrace:
    """Relaxed states immediately before each of the two frozen updates."""

    z_final: Any
    q_before_update: tuple[Any, ...]
    c_before_update: tuple[Any, ...]
    rho_before_update: tuple[Any, ...]


def _as_float_tensor(value: Any, *, device: Any = None) -> Any:
    torch_module = _require_torch()
    if isinstance(value, torch_module.Tensor):
        if device is None:
            return value.to(dtype=torch_module.float32)
        return value.to(device=device, dtype=torch_module.float32)
    return torch_module.as_tensor(value, dtype=torch_module.float32, device=device)


def _prepare_scores_embeddings(scores: Any, embeddings: Any) -> tuple[Any, Any, bool]:
    _require_torch()
    # MoleRec is frozen; learned-family backpropagation must stop at both
    # representations even if a caller accidentally passes grad-carrying tensors.
    score_tensor = _as_float_tensor(scores).detach()
    embedding_tensor = _as_float_tensor(embeddings, device=score_tensor.device).detach()
    squeezed = score_tensor.ndim == 1
    if squeezed:
        score_tensor = score_tensor.unsqueeze(0)
    if embedding_tensor.ndim == 2:
        embedding_tensor = embedding_tensor.unsqueeze(0)
    if score_tensor.ndim != 2 or embedding_tensor.ndim != 3:
        raise ValueError("scores must be [batch, 131] and embeddings [batch, 131, width]")
    if score_tensor.shape[1] != CANDIDATE_COUNT:
        raise ProtocolMismatch("Idea 008 requires exactly 131 frozen candidate scores")
    if embedding_tensor.shape[:2] != score_tensor.shape:
        raise ProtocolMismatch("frozen scores and embeddings are not candidate-aligned")
    if embedding_tensor.shape[2] <= 0:
        raise ValueError("embedding width must be positive")
    return score_tensor, embedding_tensor, squeezed


def _prepare_ddi(ddi: Any, *, device: Any) -> Any:
    matrix = _as_float_tensor(ddi, device=device).detach()
    if matrix.ndim != 2 or tuple(matrix.shape) != (CANDIDATE_COUNT, CANDIDATE_COUNT):
        raise ProtocolMismatch("Gate 01 DDI matrix must be 131 by 131")
    return matrix


def _prepare_batch_scalar(value: Any, batch_size: int, *, device: Any, name: str) -> Any:
    _require_torch()
    tensor = _as_float_tensor(value, device=device).detach()
    if tensor.ndim == 0:
        tensor = tensor.expand(batch_size)
    elif tensor.ndim != 1 or tensor.shape[0] != batch_size:
        raise ValueError(f"{name} must be a scalar or one value per batch item")
    return tensor


def _prepare_k(k_x: Any, batch_size: int, *, device: Any) -> Any:
    torch_module = _require_torch()
    if isinstance(k_x, bool):
        raise ValueError("K_x must be an integer cardinality")
    tensor = torch_module.as_tensor(k_x, dtype=torch_module.long, device=device)
    if tensor.ndim == 0:
        tensor = tensor.expand(batch_size)
    elif tensor.ndim != 1 or tensor.shape[0] != batch_size:
        raise ValueError("K_x must be a scalar or one value per batch item")
    if bool(torch_module.any(tensor < 0).item()) or bool(
        torch_module.any(tensor > CANDIDATE_COUNT).item()
    ):
        raise ValueError("K_x must lie in [0, 131]")
    return tensor


def execution_device_for_model(model: Any, requested_device: Any = None) -> Any:
    """Resolve the one device owned by a learned runner invocation.

    A requested device is authoritative.  When it is omitted, the device of
    the model's first parameter is used, which keeps a caller-created model and
    its execution inputs on one device without introducing another wrapper.
    """

    torch_module = _require_torch()
    if requested_device is not None:
        return torch_module.device(requested_device)
    try:
        return next(model.parameters()).device
    except StopIteration as error:  # pragma: no cover - all frozen models have parameters.
        raise ValueError(
            "learned model has no parameters from which to resolve a device"
        ) from error


def prepare_learned_execution_inputs(
    batch: Mapping[str, Any],
    *,
    device: Any,
    ddi: Any,
    budget: Any = None,
    static_d: Any = None,
    static_p: Any = None,
    independent: bool = False,
) -> dict[str, Any]:
    """Materialize every learned-execution input on one runner-owned device.

    The frozen MoleRec score and embedding tensors are detached here, before a
    learned forward pass can build a graph.  The same placement path handles
    CPU lists, CPU tensors, CUDA tensors, DDI, targets, budgets, ``K_x``, and
    the Independent static summaries.
    """

    torch_module = _require_torch()
    target_device = torch_module.device(device)
    if "scores" not in batch or "embeddings" not in batch or "targets" not in batch:
        raise ValueError("learned execution batches require scores, embeddings, and targets")
    score_tensor, embedding_tensor, _ = _prepare_scores_embeddings(
        _as_float_tensor(batch["scores"], device=target_device).detach(),
        _as_float_tensor(batch["embeddings"], device=target_device).detach(),
    )
    batch_size = score_tensor.shape[0]
    targets_tensor = _as_float_tensor(batch["targets"], device=target_device).detach()
    if targets_tensor.ndim == 1:
        targets_tensor = targets_tensor.unsqueeze(0)
    if tuple(targets_tensor.shape) != tuple(score_tensor.shape):
        raise ValueError("targets must align with the [batch, 131] frozen scores")
    if budget is None:
        if "budget" not in batch:
            raise ValueError("learned execution requires a budget tensor")
        budget = batch["budget"]
    budget_tensor = _prepare_batch_scalar(budget, batch_size, device=target_device, name="budget")
    if "k_x" not in batch:
        raise ValueError("learned execution batches require K_x")
    k_tensor = _prepare_k(batch["k_x"], batch_size, device=target_device)
    ddi_tensor = _prepare_ddi(ddi, device=target_device)
    prepared: dict[str, Any] = {
        "scores": score_tensor,
        "embeddings": embedding_tensor,
        "targets": targets_tensor,
        "budget": budget_tensor,
        "ddi": ddi_tensor,
        "k_x": k_tensor,
    }
    if independent:
        d_values = batch.get("d_static", static_d)
        p_values = batch.get("p_static", static_p)
        if d_values is None or p_values is None:
            raise ValueError("Independent training requires frozen d_static and p_static")
        for name, value in (("d_static", d_values), ("p_static", p_values)):
            tensor = _as_float_tensor(value, device=target_device).detach()
            if tensor.ndim == 1:
                tensor = tensor.unsqueeze(0).expand(batch_size, -1)
            if tuple(tensor.shape) != tuple(score_tensor.shape):
                raise ValueError(f"Independent {name} must align with the [batch, 131] scores")
            prepared[name] = tensor
    return prepared


def relaxed_ddi_tensor(q: Any, ddi: Any, k_x: Any) -> Any:
    """Torch equivalent of the preflight relaxed DDI function, including K<2."""

    torch_module = _require_torch()
    q_tensor = _as_float_tensor(q)
    squeezed = q_tensor.ndim == 1
    if squeezed:
        q_tensor = q_tensor.unsqueeze(0)
    if q_tensor.ndim != 2 or q_tensor.shape[1] != CANDIDATE_COUNT:
        raise ProtocolMismatch("relaxed DDI requires a 131-candidate probability vector")
    matrix = _prepare_ddi(ddi, device=q_tensor.device)
    cardinalities = _prepare_k(k_x, q_tensor.shape[0], device=q_tensor.device)
    # The protocol sums each unordered pair once and excludes diagonal terms.
    pair_matrix = torch_module.triu(matrix, diagonal=1)
    pair_sum = torch_module.einsum("bi,ij,bj->b", q_tensor, pair_matrix, q_tensor)
    denominator = (cardinalities * (cardinalities - 1) / 2).to(q_tensor.dtype).clamp_min(1.0)
    risk = pair_sum / denominator
    risk = torch_module.where(cardinalities >= 2, risk, torch_module.zeros_like(risk))
    return risk[0] if squeezed else risk


def marginal_ddi_tensor(q: Any, ddi: Any, k_x: Any) -> Any:
    """Torch equivalent of ``c_i(q)`` with the frozen low-cardinality branch."""

    torch_module = _require_torch()
    q_tensor = _as_float_tensor(q)
    squeezed = q_tensor.ndim == 1
    if squeezed:
        q_tensor = q_tensor.unsqueeze(0)
    if q_tensor.ndim != 2 or q_tensor.shape[1] != CANDIDATE_COUNT:
        raise ProtocolMismatch("marginal DDI requires a 131-candidate probability vector")
    matrix = _prepare_ddi(ddi, device=q_tensor.device)
    cardinalities = _prepare_k(k_x, q_tensor.shape[0], device=q_tensor.device)
    denominator = (cardinalities - 1).clamp_min(1).to(q_tensor.dtype).unsqueeze(1)
    pair_matrix = matrix - torch_module.diag(torch_module.diagonal(matrix))
    marginal = torch_module.matmul(q_tensor, pair_matrix.transpose(0, 1)) / denominator
    valid = (cardinalities >= 2).unsqueeze(1)
    marginal = torch_module.where(valid, marginal, torch_module.zeros_like(marginal))
    return marginal[0] if squeezed else marginal


if nn is not None:

    class BudgetSet(nn.Module):
        """BudgetSet's exact two-step residual-budget set refiner."""

        def __init__(self, embedding_dim: int) -> None:
            super().__init__()
            if not isinstance(embedding_dim, int) or embedding_dim <= 0:
                raise ValueError("embedding_dim must be a positive integer")
            self.embedding_dim = embedding_dim
            self.candidate_count = CANDIDATE_COUNT
            self.utility_head = MLPHead(1 + embedding_dim)
            self.risk_price_head = MLPHead(2 + embedding_dim)

        def _run(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            ddi: Any,
            k_x: Any,
        ) -> tuple[Any, BudgetSetTrace]:
            torch_module = _require_torch()
            score_tensor, embedding_tensor, squeezed = _prepare_scores_embeddings(
                scores, embeddings
            )
            if embedding_tensor.shape[2] != self.embedding_dim:
                raise ValueError("embedding width does not match the BudgetSet heads")
            batch_size = score_tensor.shape[0]
            budget_tensor = _prepare_batch_scalar(
                budget, batch_size, device=score_tensor.device, name="budget"
            )
            cardinalities = _prepare_k(k_x, batch_size, device=score_tensor.device)
            matrix = _prepare_ddi(ddi, device=score_tensor.device)
            candidate_features = torch_module.cat(
                [score_tensor.unsqueeze(-1), embedding_tensor], dim=-1
            )
            z = score_tensor
            q = torch_module.sigmoid(z)
            q_trace: list[Any] = []
            c_trace: list[Any] = []
            rho_trace: list[Any] = []
            for _ in range(T):
                c = marginal_ddi_tensor(q, matrix, cardinalities)
                relaxed_risk = relaxed_ddi_tensor(q, matrix, cardinalities)
                rho = budget_tensor - relaxed_risk
                utility = self.utility_head(candidate_features).squeeze(-1)
                rho_feature = rho.view(batch_size, 1, 1).expand(-1, CANDIDATE_COUNT, -1)
                price_input = torch_module.cat([candidate_features, rho_feature], dim=-1)
                price = self.risk_price_head(price_input).squeeze(-1)
                q_trace.append(q)
                c_trace.append(c)
                rho_trace.append(rho)
                # The frozen score is deliberately present as the residual anchor.
                z = score_tensor + utility - torch_module.nn.functional.softplus(price) * c
                q = torch_module.sigmoid(z)
            if squeezed:
                z_out = z[0]
                trace = BudgetSetTrace(
                    z_final=z_out,
                    q_before_update=tuple(item[0] for item in q_trace),
                    c_before_update=tuple(item[0] for item in c_trace),
                    rho_before_update=tuple(item[0] for item in rho_trace),
                )
            else:
                z_out = z
                trace = BudgetSetTrace(
                    z_final=z,
                    q_before_update=tuple(q_trace),
                    c_before_update=tuple(c_trace),
                    rho_before_update=tuple(rho_trace),
                )
            return z_out, trace

        def forward(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            ddi: Any,
            k_x: Any,
            *,
            return_trace: bool = False,
        ) -> Any:
            z, trace = self._run(scores, embeddings, budget, ddi, k_x)
            return (z, trace) if return_trace else z

        def forward_with_trace(
            self, scores: Any, embeddings: Any, budget: Any, ddi: Any, k_x: Any
        ) -> tuple[Any, BudgetSetTrace]:
            return self._run(scores, embeddings, budget, ddi, k_x)

        def hard_set(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            ddi: Any,
            k_x: int,
            vocabulary: Sequence[str] | None = None,
        ) -> tuple[int, ...]:
            torch_module = _require_torch()
            if isinstance(k_x, bool) or not isinstance(k_x, int):
                raise ValueError("hard_set requires one integer K_x")
            with torch_module.no_grad():
                logits = self(scores, embeddings, budget, ddi, k_x)
            return exact_topk(logits.detach().cpu().tolist(), k_x, vocabulary)

else:

    class BudgetSet:  # type: ignore[no-redef]
        """Import-safe placeholder when the execution environment lacks torch."""

        def __init__(self, embedding_dim: int) -> None:
            del embedding_dim
            _require_torch()

        def forward(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            ddi: Any,
            k_x: Any,
            *,
            return_trace: bool = False,
        ) -> Any:
            del scores, embeddings, budget, ddi, k_x, return_trace
            _require_torch()

        def hard_set(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            ddi: Any,
            k_x: int,
            vocabulary: Sequence[str] | None = None,
        ) -> tuple[int, ...]:
            del scores, embeddings, budget, ddi, k_x, vocabulary
            _require_torch()


if nn is not None:

    class IndependentScorer(nn.Module):
        """Budget-conditioned scorer with no provisional-set information."""

        FORBIDDEN_INPUTS = frozenset(
            {
                "q",
                "q_t",
                "c",
                "rho",
                "provisional_set",
                "current_set",
                "pair_features",
                "feedback",
            }
        )

        def __init__(self, embedding_dim: int) -> None:
            super().__init__()
            if not isinstance(embedding_dim, int) or embedding_dim <= 0:
                raise ValueError("embedding_dim must be a positive integer")
            self.embedding_dim = embedding_dim
            self.candidate_count = CANDIDATE_COUNT
            self.utility_head = MLPHead(1 + embedding_dim)
            self.risk_price_head = MLPHead(4 + embedding_dim)

        def _run(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            d_static: Any,
            p_static: Any,
        ) -> Any:
            torch_module = _require_torch()
            score_tensor, embedding_tensor, squeezed = _prepare_scores_embeddings(
                scores, embeddings
            )
            if embedding_tensor.shape[2] != self.embedding_dim:
                raise ValueError("embedding width does not match the Independent heads")
            batch_size = score_tensor.shape[0]
            budget_tensor = _prepare_batch_scalar(
                budget, batch_size, device=score_tensor.device, name="budget"
            )
            d_tensor = _as_float_tensor(d_static, device=score_tensor.device).detach()
            p_tensor = _as_float_tensor(p_static, device=score_tensor.device).detach()
            if d_tensor.ndim == 1:
                d_tensor = d_tensor.unsqueeze(0).expand(batch_size, -1)
            if p_tensor.ndim == 1:
                p_tensor = p_tensor.unsqueeze(0).expand(batch_size, -1)
            if d_tensor.shape != score_tensor.shape or p_tensor.shape != score_tensor.shape:
                raise ValueError("Independent static summaries must align with scores")
            candidate_features = torch_module.cat(
                [score_tensor.unsqueeze(-1), embedding_tensor], dim=-1
            )
            budget_feature = budget_tensor.view(batch_size, 1, 1).expand(-1, CANDIDATE_COUNT, -1)
            risk_features = torch_module.cat(
                [
                    candidate_features,
                    budget_feature,
                    d_tensor.unsqueeze(-1),
                    p_tensor.unsqueeze(-1),
                ],
                dim=-1,
            )
            utility = self.utility_head(candidate_features).squeeze(-1)
            price = self.risk_price_head(risk_features).squeeze(-1)
            # Independent has the same residual anchor but only static inputs.
            logits = score_tensor + utility - torch_module.nn.functional.softplus(price) * d_tensor
            return logits[0] if squeezed else logits

        def forward(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            d_static: Any,
            p_static: Any,
        ) -> Any:
            return self._run(scores, embeddings, budget, d_static, p_static)

        def hard_set(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            d_static: Any,
            p_static: Any,
            k_x: int,
            vocabulary: Sequence[str] | None = None,
        ) -> tuple[int, ...]:
            torch_module = _require_torch()
            if isinstance(k_x, bool) or not isinstance(k_x, int):
                raise ValueError("hard_set requires one integer K_x")
            with torch_module.no_grad():
                logits = self(scores, embeddings, budget, d_static, p_static)
            return exact_topk(logits.detach().cpu().tolist(), k_x, vocabulary)

else:

    class IndependentScorer:  # type: ignore[no-redef]
        """Import-safe placeholder when the execution environment lacks torch."""

        FORBIDDEN_INPUTS = frozenset(
            {
                "q",
                "q_t",
                "c",
                "rho",
                "provisional_set",
                "current_set",
                "pair_features",
                "feedback",
            }
        )

        def __init__(self, embedding_dim: int) -> None:
            del embedding_dim
            _require_torch()

        def forward(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            d_static: Any,
            p_static: Any,
        ) -> Any:
            del scores, embeddings, budget, d_static, p_static
            _require_torch()

        def hard_set(
            self,
            scores: Any,
            embeddings: Any,
            budget: Any,
            d_static: Any,
            p_static: Any,
            k_x: int,
            vocabulary: Sequence[str] | None = None,
        ) -> tuple[int, ...]:
            del scores, embeddings, budget, d_static, p_static, k_x, vocabulary
            _require_torch()


# Descriptive aliases for callers that use the protocol's family names.
BudgetSetModel = BudgetSet
IndependentModel = IndependentScorer
BudgetConditionedIndependentModel = IndependentScorer


@dataclass(frozen=True)
class ObjectiveTerms:
    """The exact objective components, retained for transparent tests/logging."""

    total: Any
    bce: Any
    budget_penalty: Any
    cardinality_penalty: Any
    relaxed_risk: Any
    probabilities: Any


def compute_objective_terms(
    logits: Any,
    targets: Any,
    ddi: Any,
    budget: Any,
    k_x: Any,
    eta: float,
    *,
    gamma: float = GAMMA,
) -> ObjectiveTerms:
    """Compute BCE-with-logits + budget hinge + fixed-cardinality penalty."""

    torch_module = _require_torch()
    if float(eta) not in ETAS:
        raise ProtocolMismatch("Gate 01 eta is one of 5 or 10")
    if not math.isclose(float(gamma), GAMMA, rel_tol=0.0, abs_tol=0.0):
        raise ProtocolMismatch(f"Gate 01 fixes gamma at {GAMMA}")
    logits_tensor = _as_float_tensor(logits)
    targets_tensor = _as_float_tensor(targets, device=logits_tensor.device).detach()
    squeezed = logits_tensor.ndim == 1
    if squeezed:
        logits_tensor = logits_tensor.unsqueeze(0)
        targets_tensor = targets_tensor.unsqueeze(0)
    if logits_tensor.ndim != 2 or tuple(logits_tensor.shape) != tuple(targets_tensor.shape):
        raise ValueError("logits and targets must have matching [batch, 131] shapes")
    if logits_tensor.shape[1] != CANDIDATE_COUNT:
        raise ProtocolMismatch("the objective requires all 131 candidate medications")
    batch_size = logits_tensor.shape[0]
    budget_tensor = _prepare_batch_scalar(
        budget, batch_size, device=logits_tensor.device, name="budget"
    )
    cardinalities = _prepare_k(k_x, batch_size, device=logits_tensor.device)
    probabilities = torch_module.sigmoid(logits_tensor)
    relaxed_risk = relaxed_ddi_tensor(probabilities, ddi, cardinalities)
    positive_violation = torch_module.relu(relaxed_risk - budget_tensor)
    cardinality_error = (probabilities.sum(dim=-1) - cardinalities.to(probabilities.dtype)).square()
    bce = F.binary_cross_entropy_with_logits(logits_tensor, targets_tensor, reduction="mean")
    budget_penalty = positive_violation.mean()
    cardinality_penalty = cardinality_error.mean()
    total = bce + float(eta) * budget_penalty + GAMMA * cardinality_penalty
    if squeezed:
        probabilities = probabilities[0]
    return ObjectiveTerms(
        total=total,
        bce=bce,
        budget_penalty=budget_penalty,
        cardinality_penalty=cardinality_penalty,
        relaxed_risk=relaxed_risk,
        probabilities=probabilities,
    )


def compute_objective(
    logits: Any,
    targets: Any,
    ddi: Any,
    budget: Any,
    k_x: Any,
    eta: float,
    *,
    gamma: float = GAMMA,
) -> Any:
    """Return only the frozen scalar objective used by both learned families."""

    return compute_objective_terms(logits, targets, ddi, budget, k_x, eta, gamma=gamma).total


gate01_objective = compute_objective
exact_objective = compute_objective


@dataclass(frozen=True)
class TrainingConfiguration:
    """One of the four and only four learned-family configurations."""

    learning_rate: float
    eta: float
    weight_decay: float = WEIGHT_DECAY
    gamma: float = GAMMA
    max_epochs: int = MAX_EPOCHS
    patience: int = PATIENCE

    def __post_init__(self) -> None:
        if float(self.learning_rate) not in LEARNING_RATES:
            raise ValueError("learning rate is outside the frozen Gate 01 grid")
        if float(self.eta) not in ETAS:
            raise ValueError("eta is outside the frozen Gate 01 grid")
        if float(self.weight_decay) != WEIGHT_DECAY:
            raise ValueError("weight decay is fixed at 1e-4")
        if float(self.gamma) != GAMMA:
            raise ValueError("gamma is fixed at 1e-3")
        if (
            type(self.max_epochs) is not int
            or type(self.patience) is not int
            or self.max_epochs != MAX_EPOCHS
            or self.patience != PATIENCE
        ):
            raise ValueError("epoch ceiling and patience are frozen by protocol v1.2")


CONFIGURATION_GRID = tuple(
    TrainingConfiguration(learning_rate=learning_rate, eta=eta)
    for learning_rate in LEARNING_RATES
    for eta in ETAS
)
LEARNED_CONFIGURATION_GRID = CONFIGURATION_GRID
_FROZEN_CONFIGURATION_GRID = tuple(CONFIGURATION_GRID)


def validate_training_seed(seed: int) -> int:
    if isinstance(seed, bool) or int(seed) not in LEARNED_SEEDS:
        raise ValueError("Gate 01 learned seeds are exactly 2002, 2003, and 2004")
    return int(seed)


def set_frozen_seed(seed: int) -> None:
    """Set only an admitted learned seed; no hidden seed is introduced."""

    seed_value = validate_training_seed(seed)
    random.seed(seed_value)
    if torch is not None:  # pragma: no cover - exercised in the 319 environment.
        torch.manual_seed(seed_value)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed_value)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False


def sample_training_budgets(
    b_l: float,
    b_m: float,
    b_h: float,
    size: int,
    *,
    rng: random.Random | None = None,
) -> tuple[float, ...]:
    """Sample each recommendation example from exactly ``{b_L,b_M,b_H}``."""

    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("budget sample size must be a non-negative integer")
    choices = (float(b_l), float(b_m), float(b_h))
    chooser = rng if rng is not None else random
    return tuple(chooser.choice(choices) for _ in range(size))


def sample_training_budgets_tensor(
    targets: Sequence[float], size: int, *, rng: random.Random
) -> Any:
    """Torch batch form of the same three-point Uniform sampler."""

    torch_module = _require_torch()
    if len(targets) != 3:
        raise ValueError("budget targets must contain exactly b_L, b_M, and b_H")
    sampled = sample_training_budgets(*targets, size, rng=rng)
    return torch_module.as_tensor(sampled, dtype=torch_module.float32)


def gate01_budget_targets(base_ddi_rates: Iterable[float]) -> tuple[float, float, float, float]:
    """Calibrate ``r_train,b_L,b_M,b_H`` through the verified preflight helper."""

    return calibrate_budgets(base_ddi_rates)


def make_adamw(model: Any, configuration: TrainingConfiguration) -> Any:
    """Construct the one optimizer admitted by protocol v1.2."""

    torch_module = _require_torch()
    return torch_module.optim.AdamW(
        model.parameters(),
        lr=configuration.learning_rate,
        weight_decay=WEIGHT_DECAY,
    )


def _make_model(family: FamilyName, embedding_dim: int) -> Any:
    if family == "BudgetSet":
        return BudgetSet(embedding_dim)
    if family == "Independent":
        return IndependentScorer(embedding_dim)
    raise ValueError(f"unknown learned family {family!r}")


@dataclass(frozen=True)
class SeedTrainingResult:
    """One retained Dev-selected checkpoint and its immutable training trace."""

    family: FamilyName
    seed: int
    configuration: TrainingConfiguration
    model: Any
    best_epoch: int
    stop_epoch: int
    best_evaluation: Mapping[str, Any]
    evaluations: tuple[Mapping[str, Any], ...]


BatchFactory = Callable[[], Iterable[Mapping[str, Any]]]
DevEvaluator = Callable[[Any], Mapping[str, Any]]


def _batch_factory(batches: BatchFactory | Iterable[Mapping[str, Any]]) -> BatchFactory:
    if callable(batches):
        return batches
    materialized = tuple(batches)
    return lambda: iter(materialized)


_DEV_BUDGET_FIELDS = ("jaccard", "positive_violation", "hard_ddi")


def _normalize_budget_targets(budget_targets: Sequence[float]) -> tuple[float, float, float]:
    try:
        targets = tuple(float(value) for value in budget_targets)
    except (TypeError, ValueError) as error:
        raise ValueError("training budgets must be exactly b_L, b_M, and b_H") from error
    if len(targets) != 3 or not all(math.isfinite(value) for value in targets):
        raise ValueError("training budgets must be exactly b_L, b_M, and b_H")
    return targets  # type: ignore[return-value]


def _normalize_budget_metrics(
    budget_metrics: Any, budget_targets: Sequence[float]
) -> tuple[Mapping[str, float], ...]:
    """Normalize the three existing protocol operating points in budget order."""

    targets = _normalize_budget_targets(budget_targets)
    rows: list[Mapping[str, float] | None] = [None, None, None]
    if isinstance(budget_metrics, MappingABC):
        for raw_budget, raw_metrics in budget_metrics.items():
            try:
                budget = float(raw_budget)
            except (TypeError, ValueError) as error:
                raise ValueError("Dev budget metric keys must be numeric budgets") from error
            matches = [
                index
                for index, target in enumerate(targets)
                if math.isclose(budget, target, rel_tol=0.0, abs_tol=1e-12)
            ]
            if len(matches) != 1 or rows[matches[0]] is not None:
                raise ProtocolMismatch("Dev budget metrics must identify b_L, b_M, and b_H once")
            row_index = matches[0]
            row = raw_metrics
            if not isinstance(row, MappingABC):
                raise ValueError("each Dev budget metric must be a mapping")
            rows[row_index] = row
    elif isinstance(budget_metrics, SequenceABC) and not isinstance(
        budget_metrics, (str, bytes, bytearray)
    ):
        if len(budget_metrics) != 3:
            raise ValueError("Dev budget metrics must contain exactly b_L, b_M, and b_H")
        rows = list(budget_metrics)
    else:
        raise ValueError("Dev evaluator must provide budget_metrics for all three budgets")
    if any(row is None for row in rows):
        raise ProtocolMismatch("Dev budget metrics must contain b_L, b_M, and b_H exactly once")

    normalized: list[Mapping[str, float]] = []
    for row in rows:
        assert row is not None
        missing = [name for name in _DEV_BUDGET_FIELDS if name not in row]
        if missing:
            raise ValueError(f"Dev budget metric omitted fields: {missing}")
        copied = dict(row)
        for name in _DEV_BUDGET_FIELDS:
            try:
                value = float(copied[name])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Dev budget metric {name!r} must be numeric") from error
            if not math.isfinite(value):
                raise ValueError(f"Dev budget metric {name!r} must be finite")
            copied[name] = value
        normalized.append(copied)
    return tuple(normalized)


def _dev_quantities_from_budget_metrics(
    budget_metrics: Sequence[Mapping[str, float]], budget_targets: Sequence[float]
) -> dict[str, float | int]:
    targets = _normalize_budget_targets(budget_targets)
    rows = _normalize_budget_metrics(budget_metrics, targets)
    n_compliant = sum(target_compliant(rows[index], targets[index]) for index in range(3))
    u_primary = (float(rows[0]["jaccard"]) + float(rows[1]["jaccard"])) / 2.0
    v_all = sum(float(row["positive_violation"]) for row in rows) / 3.0
    return {
        "n_compliant": int(n_compliant),
        "u_primary": float(u_primary),
        "v_all": float(v_all),
    }


def derive_seed_dev_quantities(
    evaluation: Mapping[str, Any], budget_targets: Sequence[float]
) -> dict[str, float | int]:
    """Derive the frozen per-seed checkpoint quantities from its Dev points."""

    if "budget_metrics" not in evaluation:
        raise ValueError("Dev evaluator must provide budget_metrics for all three budgets")
    rows = _normalize_budget_metrics(evaluation["budget_metrics"], budget_targets)
    return _dev_quantities_from_budget_metrics(rows, budget_targets)


def _required_dev_values(
    evaluation: Mapping[str, Any], epoch: int, budget_targets: Sequence[float]
) -> dict[str, Any]:
    if not isinstance(evaluation, MappingABC):
        raise ValueError("Dev evaluator must return a mapping")
    if "budget_metrics" not in evaluation:
        missing = [name for name in ("n_compliant", "u_primary", "v_all") if name not in evaluation]
        if missing:
            raise ValueError(f"Dev evaluator omitted checkpoint fields: {missing}")
        result = dict(evaluation)
        result["epoch"] = int(epoch)
        return result
    quantities = derive_seed_dev_quantities(evaluation, budget_targets)
    result = dict(evaluation)
    for name, expected in quantities.items():
        if name in result:
            try:
                supplied = float(result[name])
            except (TypeError, ValueError) as error:
                raise ProtocolMismatch(f"Dev checkpoint field {name!r} must be numeric") from error
            if not math.isclose(supplied, float(expected), rel_tol=0.0, abs_tol=1e-12):
                raise ProtocolMismatch(
                    f"Dev checkpoint field {name!r} disagrees with its budget metrics"
                )
        result[name] = expected
    result["budget_metrics"] = _normalize_budget_metrics(
        evaluation["budget_metrics"], budget_targets
    )
    result["epoch"] = int(epoch)
    return result


def train_seed_configuration(
    family: FamilyName,
    configuration: TrainingConfiguration,
    seed: int,
    *,
    embedding_dim: int,
    ddi: Any,
    budget_targets: Sequence[float],
    train_batches: BatchFactory | Iterable[Mapping[str, Any]],
    dev_evaluator: DevEvaluator,
    static_d: Any = None,
    static_p: Any = None,
    device: Any = None,
) -> SeedTrainingResult:
    """Train one admitted seed/configuration and select its Dev checkpoint.

    ``dev_evaluator`` is deliberately a single Dev-only callback. Audit is
    evaluated later from the returned checkpoint and is not an input to this
    function or to any selection key.
    """

    torch_module = _require_torch()
    validate_training_seed(seed)
    normalized_budget_targets = _normalize_budget_targets(budget_targets)
    if float(configuration.eta) not in ETAS:
        raise ProtocolMismatch("training configuration eta is outside the frozen grid")
    set_frozen_seed(seed)
    model = _make_model(family, embedding_dim)
    if device is not None:
        model = model.to(device)
    execution_device = execution_device_for_model(model, device)
    execution_ddi = _prepare_ddi(ddi, device=execution_device)
    optimizer = make_adamw(model, configuration)
    batch_source = _batch_factory(train_batches)
    budget_rng = random.Random(seed)
    evaluations: list[Mapping[str, Any]] = []
    best_state: Mapping[str, Any] | None = None
    best_key: tuple[int, float, float, int] | None = None
    best_evaluation: Mapping[str, Any] | None = None
    non_improvements = 0
    stop_epoch = 0

    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        for batch in batch_source():
            optimizer.zero_grad(set_to_none=True)
            scores = batch["scores"]
            scores_tensor = _as_float_tensor(scores, device=execution_device).detach()
            batch_size = scores_tensor.shape[0] if scores_tensor.ndim > 1 else 1
            budgets = sample_training_budgets_tensor(
                normalized_budget_targets, batch_size, rng=budget_rng
            ).to(execution_device)
            prepared = prepare_learned_execution_inputs(
                batch,
                device=execution_device,
                ddi=execution_ddi,
                budget=budgets,
                static_d=static_d,
                static_p=static_p,
                independent=family == "Independent",
            )
            if family == "BudgetSet":
                logits = model(
                    prepared["scores"],
                    prepared["embeddings"],
                    prepared["budget"],
                    prepared["ddi"],
                    prepared["k_x"],
                )
            else:
                logits = model(
                    prepared["scores"],
                    prepared["embeddings"],
                    prepared["budget"],
                    prepared["d_static"],
                    prepared["p_static"],
                )
            loss = compute_objective(
                logits,
                prepared["targets"],
                prepared["ddi"],
                prepared["budget"],
                prepared["k_x"],
                configuration.eta,
            )
            loss.backward()
            optimizer.step()

        model.eval()
        with torch_module.no_grad():
            evaluation = _required_dev_values(
                dev_evaluator(model), epoch, normalized_budget_targets
            )
        evaluations.append(evaluation)
        key = checkpoint_selection_key(
            evaluation["n_compliant"], evaluation["u_primary"], evaluation["v_all"], epoch
        )
        if best_key is None or key < best_key:
            best_key = key
            best_state = copy.deepcopy(model.state_dict())
            best_evaluation = evaluation
            non_improvements = 0
        else:
            non_improvements += 1
        stop_epoch = epoch
        if non_improvements >= PATIENCE:
            break

    if best_state is None or best_evaluation is None:
        raise ValueError("training produced no Dev checkpoint")
    selected = select_checkpoint_with_patience(
        evaluations, patience=PATIENCE, max_epochs=MAX_EPOCHS
    )
    if int(selected.best["epoch"]) != int(best_evaluation["epoch"]):
        raise ProtocolMismatch("training loop and frozen checkpoint selector disagree")
    model.load_state_dict(best_state)
    model.eval()
    return SeedTrainingResult(
        family=family,
        seed=int(seed),
        configuration=configuration,
        model=model,
        best_epoch=int(best_evaluation["epoch"]),
        stop_epoch=stop_epoch,
        best_evaluation=dict(best_evaluation),
        evaluations=tuple(dict(item) for item in evaluations),
    )


def _canonical_seed_results(
    seed_results: Sequence[SeedTrainingResult],
    configuration: TrainingConfiguration | None = None,
) -> tuple[SeedTrainingResult, ...]:
    if len(seed_results) != len(LEARNED_SEEDS):
        raise ProtocolMismatch(
            "each configuration requires exactly the three learned seed checkpoints"
        )
    expected_configuration = configuration or seed_results[0].configuration
    by_seed: dict[int, SeedTrainingResult] = {}
    for result in seed_results:
        if not isinstance(result, SeedTrainingResult):
            raise TypeError("configuration selection requires SeedTrainingResult checkpoints")
        if result.configuration != expected_configuration:
            raise ProtocolMismatch("seed checkpoint configuration does not match its record")
        validate_training_seed(result.seed)
        if result.seed in by_seed:
            raise ProtocolMismatch("configuration selection received a duplicate learned seed")
        by_seed[result.seed] = result
    if set(by_seed) != set(LEARNED_SEEDS):
        raise ProtocolMismatch("configuration selection requires seeds 2002, 2003, and 2004")
    families = {result.family for result in by_seed.values()}
    if len(families) != 1:
        raise ProtocolMismatch("configuration selection cannot mix learned families")
    return tuple(by_seed[seed] for seed in LEARNED_SEEDS)


def _derive_configuration_dev_data(
    seed_results: Sequence[SeedTrainingResult], budget_targets: Sequence[float]
) -> tuple[tuple[SeedTrainingResult, ...], tuple[Mapping[str, float], ...], dict[str, float | int]]:
    targets = _normalize_budget_targets(budget_targets)
    if not seed_results:
        raise ValueError("configuration Dev results are empty")
    ordered = _canonical_seed_results(seed_results)
    rows_by_seed = {
        result.seed: _normalize_budget_metrics(
            result.best_evaluation.get("budget_metrics"), targets
        )
        for result in ordered
    }
    aggregate_rows = tuple(
        aggregate_seed_metrics({seed: rows_by_seed[seed][budget_index] for seed in LEARNED_SEEDS})
        for budget_index in range(3)
    )
    n_compliant = sum(target_compliant(aggregate_rows[index], targets[index]) for index in range(3))
    quantities: dict[str, float | int] = {
        "n_compliant_config": int(n_compliant),
        "u_primary_config": float(
            (aggregate_rows[0]["jaccard"] + aggregate_rows[1]["jaccard"]) / 2.0
        ),
        "v_all_config": float(sum(row["positive_violation"] for row in aggregate_rows) / 3.0),
    }
    return ordered, aggregate_rows, quantities


def derive_configuration_dev_quantities(
    seed_results: Sequence[SeedTrainingResult], budget_targets: Sequence[float]
) -> dict[str, float | int]:
    """Derive config-selection quantities from retained seed Dev checkpoints."""

    return _derive_configuration_dev_data(seed_results, budget_targets)[2]


@dataclass(frozen=True)
class ConfigurationDevResult:
    """Dev-only aggregate derived from exactly three retained seed checkpoints."""

    configuration: TrainingConfiguration
    seed_results: tuple[SeedTrainingResult, ...]
    budget_targets: tuple[float, float, float]
    n_compliant_config: int = field(init=False)
    u_primary_config: float = field(init=False)
    v_all_config: float = field(init=False)
    aggregate_budget_metrics: tuple[Mapping[str, float], ...] = field(init=False)

    def __post_init__(self) -> None:
        ordered, aggregate_rows, quantities = _derive_configuration_dev_data(
            self.seed_results, self.budget_targets
        )
        object.__setattr__(self, "seed_results", ordered)
        object.__setattr__(self, "budget_targets", _normalize_budget_targets(self.budget_targets))
        object.__setattr__(self, "aggregate_budget_metrics", aggregate_rows)
        object.__setattr__(self, "n_compliant_config", quantities["n_compliant_config"])
        object.__setattr__(self, "u_primary_config", quantities["u_primary_config"])
        object.__setattr__(self, "v_all_config", quantities["v_all_config"])


def _configuration_records(
    dev_results: Mapping[TrainingConfiguration, ConfigurationDevResult | Mapping[str, Any]]
    | Iterable[ConfigurationDevResult],
) -> tuple[ConfigurationDevResult, ...]:
    if isinstance(dev_results, MappingABC):
        records_list: list[ConfigurationDevResult] = []
        for configuration, values in dev_results.items():
            if isinstance(values, ConfigurationDevResult):
                records_list.append(values)
                continue
            if not isinstance(values, MappingABC):
                raise TypeError(
                    "configuration Dev records must be mappings or ConfigurationDevResult"
                )
            unsupported = set(values) - {"seed_results", "budget_targets"}
            if unsupported:
                raise ProtocolMismatch(
                    "configuration aggregate quantities must be derived from seed checkpoints"
                )
            if "seed_results" not in values or "budget_targets" not in values:
                raise ValueError(
                    "configuration Dev records require seed_results and budget_targets"
                )
            records_list.append(
                ConfigurationDevResult(
                    configuration=configuration,
                    seed_results=tuple(values["seed_results"]),
                    budget_targets=tuple(values["budget_targets"]),
                )
            )
        records = tuple(records_list)
    else:
        records = tuple(dev_results)
    if not records:
        raise ValueError("Dev configuration results are empty")
    allowed = set(_FROZEN_CONFIGURATION_GRID)
    if any(record.configuration not in allowed for record in records):
        raise ProtocolMismatch("configuration selection received a non-frozen hyperparameter")
    configurations = tuple(record.configuration for record in records)
    if len(records) != len(_FROZEN_CONFIGURATION_GRID) or set(configurations) != allowed:
        raise ProtocolMismatch(
            "configuration selection requires exactly the frozen four configurations"
        )
    families = {record.seed_results[0].family for record in records}
    if len(families) != 1:
        raise ProtocolMismatch("configuration selection cannot mix learned families")
    budget_sets = {record.budget_targets for record in records}
    if len(budget_sets) != 1:
        raise ProtocolMismatch("configuration selection requires one shared b_L, b_M, and b_H grid")
    return records


def select_configuration_result(
    dev_results: Mapping[TrainingConfiguration, ConfigurationDevResult | Mapping[str, Any]]
    | Iterable[ConfigurationDevResult],
) -> ConfigurationDevResult:
    """Select one configuration using Dev aggregate values only."""

    records = _configuration_records(dev_results)
    return min(
        records,
        key=lambda record: configuration_selection_key(
            record.n_compliant_config,
            record.u_primary_config,
            record.v_all_config,
            record.configuration.learning_rate,
            record.configuration.eta,
        ),
    )


def select_configuration(
    dev_results: Mapping[TrainingConfiguration, ConfigurationDevResult | Mapping[str, Any]]
    | Iterable[ConfigurationDevResult],
) -> TrainingConfiguration:
    """Return the Dev-selected configuration; Audit is intentionally absent."""

    return select_configuration_result(dev_results).configuration


@dataclass(frozen=True)
class LearnedFamilySelection:
    """Complete Dev selection result for one learned family."""

    family: FamilyName
    selected_configuration: TrainingConfiguration
    selected_result: ConfigurationDevResult
    configuration_results: tuple[ConfigurationDevResult, ...]
    runs: tuple[SeedTrainingResult, ...]
    retained_checkpoints: tuple[SeedTrainingResult, ...]

    @property
    def configuration(self) -> TrainingConfiguration:
        """Compatibility alias for callers that ask for the selected config."""

        return self.selected_configuration

    @property
    def checkpoints(self) -> tuple[SeedTrainingResult, ...]:
        """Exactly the three retained checkpoints of the selected config."""

        return self.retained_checkpoints


FamilyDevEvaluator = Callable[..., Mapping[str, Any]]


def _invoke_family_dev_evaluator(
    evaluator: FamilyDevEvaluator,
    model: Any,
    seed: int,
    configuration: TrainingConfiguration,
) -> Mapping[str, Any]:
    """Call a Dev evaluator with optional run context without an Audit channel."""

    try:
        signature = inspect.signature(evaluator)
    except (TypeError, ValueError):
        return evaluator(model)
    parameters = tuple(signature.parameters.values())
    positional = tuple(
        parameter
        for parameter in parameters
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    )
    if any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters):
        return evaluator(model, seed, configuration)
    if len(positional) >= 3:
        second_name = positional[1].name.lower()
        third_name = positional[2].name.lower()
        if "config" in second_name and "seed" in third_name:
            return evaluator(model, configuration, seed)
        return evaluator(model, seed, configuration)
    if len(positional) == 2:
        if "config" in positional[1].name.lower():
            return evaluator(model, configuration)
        return evaluator(model, seed)
    return evaluator(model)


def train_learned_family(
    family: FamilyName,
    *,
    embedding_dim: int,
    ddi: Any,
    budget_targets: Sequence[float],
    train_batches: BatchFactory | Iterable[Mapping[str, Any]],
    dev_evaluator: FamilyDevEvaluator,
    static_d: Any = None,
    static_p: Any = None,
    device: Any = None,
) -> LearnedFamilySelection:
    """Train all frozen runs and own the complete Dev selection graph.

    Exactly four configurations and three learned seeds are executed.  The
    configuration quantities are computed only from the retained per-seed Dev
    checkpoints; no caller-supplied aggregate performance values are accepted.
    """

    if family not in ("BudgetSet", "Independent"):
        raise ValueError(f"unknown learned family {family!r}")
    if tuple(LEARNED_SEEDS) != (2002, 2003, 2004):
        raise ProtocolMismatch("learned-family orchestration requires seeds 2002, 2003, and 2004")
    if tuple(_FROZEN_CONFIGURATION_GRID) != tuple(CONFIGURATION_GRID):
        raise ProtocolMismatch("learned-family orchestration requires exactly four configurations")
    normalized_budget_targets = _normalize_budget_targets(budget_targets)
    batch_source = _batch_factory(train_batches)
    expected_keys = {
        (configuration, seed)
        for configuration in _FROZEN_CONFIGURATION_GRID
        for seed in LEARNED_SEEDS
    }
    runs_by_key: dict[tuple[TrainingConfiguration, int], SeedTrainingResult] = {}
    for configuration in _FROZEN_CONFIGURATION_GRID:
        for seed in LEARNED_SEEDS:
            expected_key = (configuration, seed)
            if expected_key in runs_by_key:
                raise ProtocolMismatch("duplicate learned seed/configuration run")

            def run_dev_evaluator(
                model: Any,
                *,
                _seed: int = seed,
                _configuration: TrainingConfiguration = configuration,
            ) -> Mapping[str, Any]:
                return _invoke_family_dev_evaluator(dev_evaluator, model, _seed, _configuration)

            result = train_seed_configuration(
                family,
                configuration,
                seed,
                embedding_dim=embedding_dim,
                ddi=ddi,
                budget_targets=normalized_budget_targets,
                train_batches=batch_source,
                dev_evaluator=run_dev_evaluator,
                static_d=static_d,
                static_p=static_p,
                device=device,
            )
            if not isinstance(result, SeedTrainingResult):
                raise TypeError("learned-family training must return SeedTrainingResult")
            actual_key = (result.configuration, result.seed)
            if (
                result.family != family
                or result.configuration != configuration
                or result.seed != seed
            ):
                raise ProtocolMismatch(
                    "learned run returned the wrong family, configuration, or seed"
                )
            if actual_key in runs_by_key:
                raise ProtocolMismatch("duplicate learned seed/configuration run")
            runs_by_key[actual_key] = result

    if set(runs_by_key) != expected_keys:
        raise ProtocolMismatch("learned-family orchestration has a missing seed/configuration run")

    configuration_results = tuple(
        ConfigurationDevResult(
            configuration=configuration,
            seed_results=tuple(runs_by_key[(configuration, seed)] for seed in LEARNED_SEEDS),
            budget_targets=normalized_budget_targets,
        )
        for configuration in _FROZEN_CONFIGURATION_GRID
    )
    selected_result = select_configuration_result(configuration_results)
    retained = retained_checkpoints_for_audit(selected_result)
    if tuple(result.seed for result in retained) != LEARNED_SEEDS:
        raise ProtocolMismatch("selected learned configuration did not retain all three seeds")
    return LearnedFamilySelection(
        family=family,
        selected_configuration=selected_result.configuration,
        selected_result=selected_result,
        configuration_results=configuration_results,
        runs=tuple(
            runs_by_key[(configuration, seed)]
            for configuration in _FROZEN_CONFIGURATION_GRID
            for seed in LEARNED_SEEDS
        ),
        retained_checkpoints=retained,
    )


def retained_checkpoints_for_audit(
    selected: ConfigurationDevResult,
) -> tuple[SeedTrainingResult, ...]:
    """Expose only the three retained checkpoints of the Dev-selected config."""

    if not selected.seed_results:
        raise ValueError("selected configuration has no retained seed checkpoints")
    seeds = tuple(result.seed for result in selected.seed_results)
    if seeds != LEARNED_SEEDS:
        raise ProtocolMismatch("Audit requires exactly the three retained learned seeds")
    if any(result.configuration != selected.configuration for result in selected.seed_results):
        raise ProtocolMismatch("Audit checkpoint set does not belong to the selected Dev config")
    return selected.seed_results


def evaluate_selected_audit(
    selected: ConfigurationDevResult,
    audit_evaluator: Callable[[Any, int], Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    """Evaluate only retained Dev-selected checkpoints; never select from Audit.

    The callback is deliberately invoked after ``select_configuration`` and
    receives no authority to mutate or replace the selected configuration.
    This is the later Gate path, not an instruction to open Audit now.
    """

    return tuple(
        dict(audit_evaluator(result.model, result.seed))
        for result in retained_checkpoints_for_audit(selected)
    )


def frozen_molerec_execution_spec() -> dict[str, str]:
    """Return existing registry/environment identity without a private path."""

    return {
        "environment": MOLEREC_CONDA_ENVIRONMENT,
        "upstream_root": MOLEREC_UPSTREAM_ROOT,
        "upstream_revision": UPSTREAM_MOLEREC_REVISION,
        "profile": MOLEREC_PROFILE,
        "dataset_subdirectory": MOLEREC_DATASET_SUBDIRECTORY,
        "dataset_id": DATASET_ID,
        "checkpoint_sha256": MOLEREC_CHECKPOINT_SHA256,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="print frozen identities/configuration without reading data or training",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Print the frozen execution plan only; model execution is import-driven."""

    args = build_parser().parse_args(argv)
    if not args.print_plan:
        raise SystemExit(
            "Idea 008 runner is implementation-only; later authorized execution must "
            "call its functions from the 319 runner"
        )
    payload = {
        "protocol_revision": PROTOCOL_VERSION,
        "molerec": frozen_molerec_execution_spec(),
        "seeds": LEARNED_SEEDS,
        "learning_rates": LEARNING_RATES,
        "etas": ETAS,
        "gamma": GAMMA,
        "weight_decay": WEIGHT_DECAY,
        "max_epochs": MAX_EPOCHS,
        "patience": PATIENCE,
        "fixed_lambdas": FIXED_LAMBDAS,
        "training": "NOT_RUN",
        "gate01_audit": "UNOPENED",
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - no scientific run is implicit.
    raise SystemExit(main())


__all__ = (
    "BUDGET_FRACTIONS",
    "CANDIDATE_COUNT",
    "CONFIGURATION_GRID",
    "DELTA_R",
    "DELTA_U",
    "ETAS",
    "FIXED_LAMBDAS",
    "GAMMA",
    "LEARNED_CONFIGURATION_GRID",
    "LEARNED_SEEDS",
    "LEARNING_RATES",
    "MAX_EPOCHS",
    "MOLEREC_CHECKPOINT_SHA256",
    "MOLEREC_CONDA_ENVIRONMENT",
    "MOLEREC_DATASET_SUBDIRECTORY",
    "MOLEREC_PROFILE",
    "MOLEREC_UPSTREAM_ROOT",
    "PATIENCE",
    "WEIGHT_DECAY",
    "BudgetConditionedIndependentModel",
    "BudgetConditionedIndependentScorer",
    "BudgetSet",
    "BudgetSetModel",
    "BudgetSetTrace",
    "ConfigurationDevResult",
    "IndependentModel",
    "IndependentScorer",
    "LearnedFamilySelection",
    "MLPArchitecture",
    "MLPHead",
    "ObjectiveTerms",
    "ProtocolMismatch",
    "SeedTrainingResult",
    "T",
    "TrainingConfiguration",
    "aggregate_seed_metrics",
    "aggregate_visit_metrics",
    "budgetset_hard_set",
    "budgetset_recurrence",
    "calibrate_budgets",
    "classify_gate01",
    "compare_aggregate_frontier",
    "compare_seed_frontier",
    "composition_change_rate",
    "compute_k_x",
    "compute_objective",
    "compute_objective_terms",
    "configuration_selection_key",
    "derive_configuration_dev_quantities",
    "derive_seed_dev_quantities",
    "deterministic_ranking",
    "evaluate_selected_audit",
    "exact_objective",
    "exact_topk",
    "execution_device_for_model",
    "extract_frozen_molerec_features",
    "extract_gate01_molerec_features",
    "extract_molerec_features",
    "fixed_lambda_family",
    "fixed_lambda_scores",
    "frozen_base_cardinality",
    "frozen_base_from_logits",
    "frozen_base_set",
    "frozen_k_from_logits",
    "frozen_molerec_execution_spec",
    "gate01_budget_targets",
    "gate01_objective",
    "gate01_partition",
    "gate01_split_u",
    "greedy_budget_aware_1swap",
    "greedy_frontier",
    "greedy_ranking",
    "hard_ddi",
    "make_adamw",
    "marginal_ddi",
    "marginal_ddi_tensor",
    "matched_independent_frontier",
    "patient_cluster_bootstrap",
    "prepare_learned_execution_inputs",
    "relaxed_ddi",
    "relaxed_ddi_tensor",
    "retained_checkpoints_for_audit",
    "sample_training_budgets",
    "sample_training_budgets_tensor",
    "seed_robustness_satisfied",
    "select_checkpoint_with_patience",
    "select_configuration",
    "select_configuration_result",
    "select_fixed_lambda",
    "set_frozen_seed",
    "sigmoid",
    "static_ddi_summaries",
    "target_compliant",
    "terminal_verdict",
    "train_learned_family",
    "train_seed_configuration",
    "validate_frozen_molerec_identity",
    "validate_training_seed",
    "visit_level_metrics",
)
