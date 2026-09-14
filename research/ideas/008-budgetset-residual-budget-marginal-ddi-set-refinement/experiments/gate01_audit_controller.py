"""Idea 008 Gate 01 Audit controller plumbing.

The formal controller keeps visit-level predictions and their aggregate metrics
in :class:`Bundle` objects.  This module owns the small, data-agnostic bridge
from those bundles to the existing v1.2 aggregation, frontier, bootstrap, and
terminal-decision helpers.  It does not load data, train models, or select
scientific configurations.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _load_preflight() -> Any:
    """Load the sibling preflight module in script and test import modes."""

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


_PREFLIGHT = _load_preflight()

ProtocolMismatch = _PREFLIGHT.ProtocolMismatch
BootstrapResult = _PREFLIGHT.BootstrapResult
compare_aggregate_frontier = _PREFLIGHT.compare_aggregate_frontier
compare_seed_frontier = _PREFLIGHT.compare_seed_frontier
greedy_frontier = _PREFLIGHT.greedy_frontier
matched_independent_frontier = _PREFLIGHT.matched_independent_frontier
patient_cluster_bootstrap = _PREFLIGHT.patient_cluster_bootstrap
seed_robustness_satisfied = _PREFLIGHT.seed_robustness_satisfied
terminal_verdict = _PREFLIGHT.terminal_verdict

BUDGET_LABELS = ("b_L", "b_M", "b_H")
LEARNED_SEEDS = (2002, 2003, 2004)
BOOTSTRAP_REPLICATES = _PREFLIGHT.BOOTSTRAP_REPLICATES
BOOTSTRAP_SEED = _PREFLIGHT.BOOTSTRAP_SEED
METRIC_NAMES = (
    "jaccard",
    "f1",
    "prauc",
    "hard_ddi",
    "positive_violation",
    "absolute_deviation",
    "mean_medications",
    "exact_k",
)


@dataclass(frozen=True)
class AuditRow:
    """One synthetic- or real-data visit reference used by controller plumbing."""

    index: int
    patient_id: Hashable
    target: frozenset[int]
    k_x: int


@dataclass(frozen=True)
class Bundle:
    """Predictions, per-visit metrics, and one aggregate operating point."""

    predictions: tuple[tuple[int, ...], ...]
    rankings: tuple[tuple[int, ...], ...]
    per_visit: Mapping[str, Sequence[float]]
    aggregate: Mapping[str, float]
    budget: float
    seed: int | None


def aggregate_seed_bundles(bundles: Mapping[int, Bundle]) -> dict[str, float]:
    """Aggregate exactly three Bundle objects without losing their ownership.

    The conversion from ``Bundle`` to its aggregate metric mapping happens only
    at this boundary, immediately before the verified preflight reducer.  A
    plain aggregate mapping is rejected so a caller cannot accidentally feed a
    sampled/partial mapping back into a Bundle-level orchestration function.
    """

    if set(bundles) != set(LEARNED_SEEDS):
        raise ProtocolMismatch(
            "learned-family aggregation requires exactly seeds 2002, 2003, and 2004"
        )
    if any(not isinstance(bundle, Bundle) for bundle in bundles.values()):
        raise TypeError("seed aggregation requires Bundle objects")
    return {
        str(name): float(value)
        for name, value in _PREFLIGHT.aggregate_seed_metrics(
            {seed: bundle.aggregate for seed, bundle in bundles.items()}
        ).items()
    }


def point_from_aggregate(
    aggregate: Mapping[str, float],
    order: int,
    budget: float,
    seed: int | None = None,
) -> Any:
    """Build a protocol operating point from one already-derived aggregate."""

    return _PREFLIGHT.OperatingPoint(
        risk=float(aggregate["hard_ddi"]),
        utility=float(aggregate["jaccard"]),
        order=int(order),
        seed=seed,
        budget=float(budget),
    )


def _aggregate_from_bundle(bundle: Bundle, sampled_rows: Sequence[AuditRow]) -> dict[str, float]:
    if not sampled_rows:
        raise ValueError("cannot aggregate an empty sampled visit collection")
    indices = tuple(int(row.index) for row in sampled_rows)
    return {
        name: sum(float(bundle.per_visit[name][index]) for index in indices) / len(indices)
        for name in METRIC_NAMES
    }


def make_bundle_from_sample(bundle: Bundle, sampled_rows: Sequence[AuditRow]) -> Bundle:
    """Return a sampled Bundle, preserving the Bundle contract for reducers."""

    if not isinstance(bundle, Bundle):
        raise TypeError("sampled controller inputs require a Bundle object")
    indices = tuple(int(row.index) for row in sampled_rows)
    if not indices:
        raise ValueError("cannot sample an empty Bundle")
    aggregate = _aggregate_from_bundle(bundle, sampled_rows)
    return Bundle(
        predictions=tuple(bundle.predictions[index] for index in indices),
        rankings=tuple(bundle.rankings[index] for index in indices),
        per_visit={
            name: tuple(values[index] for index in indices)
            for name, values in bundle.per_visit.items()
        },
        aggregate=aggregate,
        budget=bundle.budget,
        seed=bundle.seed,
    )


def bootstrap_comparison(
    rows: Sequence[AuditRow],
    budgetset_bundles: Mapping[int, Mapping[int, Bundle]],
    independent_bundles: Mapping[int, Mapping[int, Bundle]],
    deterministic_bundles: Mapping[int, Bundle],
    control: str,
    region_index: int,
    budgets: Sequence[float],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> BootstrapResult[float]:
    """Recompute a frontier gap from sampled Bundles under the frozen bootstrap."""

    def family_point(family: str, budget_index: int, sampled: Sequence[AuditRow]) -> Any:
        family_bundles = budgetset_bundles if family == "BudgetSet" else independent_bundles
        sampled_bundles = {
            seed_value: make_bundle_from_sample(family_bundles[budget_index][seed_value], sampled)
            for seed_value in LEARNED_SEEDS
        }
        aggregate = aggregate_seed_bundles(sampled_bundles)
        return point_from_aggregate(aggregate, budget_index, budgets[budget_index])

    def deterministic_point(budget_index: int, sampled: Sequence[AuditRow]) -> Any:
        return point_from_aggregate(
            make_bundle_from_sample(deterministic_bundles[budget_index], sampled).aggregate,
            budget_index,
            budgets[budget_index],
        )

    def recompute(sampled: Sequence[AuditRow]) -> dict[str, Any]:
        budget_point = family_point("BudgetSet", region_index, sampled)
        if control == "Greedy+1Swap":
            control_points = tuple(deterministic_point(index, sampled) for index in range(3))
        elif control == "Independent":
            control_points = tuple(
                family_point("Independent", index, sampled) for index in range(3)
            )
        else:
            raise ValueError(f"unknown controller comparison family {control!r}")
        return {"budget": budget_point, "control": control_points}

    def gap(points: Mapping[str, Any]) -> float:
        return float(compare_seed_frontier(points["budget"], points["control"]).utility_gap)

    return patient_cluster_bootstrap(
        rows,
        patient_key=lambda row: row.patient_id,
        recompute_operating_points=recompute,
        recompute_frontier_gap=gap,
        replicates=replicates,
        seed=seed,
    )


def seed_robustness(
    budgetset_bundles: Mapping[int, Mapping[int, Bundle]],
    independent_bundles: Mapping[int, Mapping[int, Bundle]],
    greedy_bundles: Mapping[int, Bundle],
    budgets: Sequence[float],
    control: str,
    region_index: int,
) -> dict[str, Any]:
    """Run the protocol matched-seed robustness comparator for one region."""

    greedy_points = tuple(
        point_from_aggregate(greedy_bundles[index].aggregate, index, budgets[index])
        for index in range(3)
    )
    independent_points = {
        seed: tuple(
            point_from_aggregate(
                independent_bundles[index][seed].aggregate,
                index,
                budgets[index],
                seed=seed,
            )
            for index in range(3)
        )
        for seed in LEARNED_SEEDS
    }
    comparisons: dict[int, Any] = {}
    for seed in LEARNED_SEEDS:
        budget_point = point_from_aggregate(
            budgetset_bundles[region_index][seed].aggregate,
            region_index,
            budgets[region_index],
            seed=seed,
        )
        if control == "Greedy+1Swap":
            comparison = greedy_frontier(budget_point, greedy_points)
        elif control == "Independent":
            comparison = matched_independent_frontier(seed, budget_point, independent_points)
        else:
            raise ValueError(f"unknown controller comparison family {control!r}")
        comparisons[seed] = comparison
    satisfied = seed_robustness_satisfied(comparisons)
    return {
        "favorable_count": int(sum(item.favorable for item in comparisons.values())),
        "required_count": 2,
        "satisfied": bool(satisfied),
        "seeds": {
            str(seed): {
                "branch": comparisons[seed].branch,
                "selected_order": int(comparisons[seed].selected_order),
                "utility_gap": float(comparisons[seed].utility_gap),
                "risk_gap": float(comparisons[seed].risk_gap),
                "favorable": bool(comparisons[seed].favorable),
            }
            for seed in LEARNED_SEEDS
        },
    }


def frontier_record(
    budgetset_bundles: Mapping[int, Mapping[int, Bundle]],
    independent_bundles: Mapping[int, Mapping[int, Bundle]],
    deterministic_bundles: Mapping[int, Bundle],
    rows: Sequence[AuditRow],
    budgets: Sequence[float],
    control: str,
    *,
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Build both primary-region frontier records from Bundle inputs."""

    if control not in {"Greedy+1Swap", "Independent"}:
        raise ValueError(f"unknown controller comparison family {control!r}")
    result: dict[str, Any] = {}
    for region_index in (0, 1):
        # Keep Bundle objects intact until this reducer boundary.  Passing
        # ``bundle.aggregate`` values here was the confirmed runtime defect.
        budget_aggregate = aggregate_seed_bundles(budgetset_bundles[region_index])
        budget_point = point_from_aggregate(budget_aggregate, region_index, budgets[region_index])
        if control == "Greedy+1Swap":
            control_points = tuple(
                point_from_aggregate(
                    deterministic_bundles[index].aggregate,
                    index,
                    budgets[index],
                )
                for index in range(3)
            )
        else:
            control_points = tuple(
                point_from_aggregate(
                    aggregate_seed_bundles(independent_bundles[index]),
                    index,
                    budgets[index],
                )
                for index in range(3)
            )
        bootstrap = bootstrap_comparison(
            rows,
            budgetset_bundles,
            independent_bundles,
            deterministic_bundles,
            control,
            region_index,
            budgets,
            replicates=bootstrap_replicates,
            seed=bootstrap_seed,
        )
        aggregate_comparison = compare_aggregate_frontier(
            budget_point,
            control_points,
            bootstrap_lower_bound=float(bootstrap.lower),
        )
        robustness = seed_robustness(
            budgetset_bundles,
            independent_bundles,
            deterministic_bundles,
            budgets,
            control,
            region_index,
        )
        result[BUDGET_LABELS[region_index]] = {
            "aggregate": {
                "branch": aggregate_comparison.branch,
                "selected_order": int(aggregate_comparison.selected_order),
                "utility_gap": float(aggregate_comparison.utility_gap),
                "risk_gap": float(aggregate_comparison.risk_gap),
                "material_outside": bool(aggregate_comparison.favorable),
            },
            "bootstrap": {
                "replicates": int(bootstrap_replicates),
                "seed": int(bootstrap_seed),
                "ci_lower": float(bootstrap.lower),
                "ci_upper": float(bootstrap.upper),
            },
            "matched_seed_robustness": robustness,
        }
    return result


# Names mirror the one-shot controller's existing private calls while keeping
# the implementation repository-owned and directly testable.
_aggregate_seed_bundles = aggregate_seed_bundles
_make_bundle_from_sample = make_bundle_from_sample
_bootstrap_comparison = bootstrap_comparison
_seed_robustness = seed_robustness
_frontier_record = frontier_record


__all__ = (
    "BOOTSTRAP_REPLICATES",
    "BOOTSTRAP_SEED",
    "BUDGET_LABELS",
    "LEARNED_SEEDS",
    "METRIC_NAMES",
    "AuditRow",
    "Bundle",
    "_aggregate_seed_bundles",
    "_bootstrap_comparison",
    "_frontier_record",
    "_make_bundle_from_sample",
    "_seed_robustness",
    "aggregate_seed_bundles",
    "bootstrap_comparison",
    "frontier_record",
    "make_bundle_from_sample",
    "point_from_aggregate",
    "seed_robustness",
    "terminal_verdict",
)
