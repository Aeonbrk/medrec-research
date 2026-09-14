from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "../research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate01_audit_controller.py"
).resolve()
SPEC = importlib.util.spec_from_file_location("idea008_gate01_audit_controller", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _rows() -> tuple[object, ...]:
    return tuple(
        MODULE.AuditRow(
            index=index,
            patient_id="p1" if index < 2 else "p2",
            target=frozenset({index}),
            k_x=1,
        )
        for index in range(3)
    )


def _bundle(*, seed: int | None, budget: float, jaccard: float) -> object:
    predictions = ((0,), (1,), (2,))
    rankings = ((0, 1, 2), (1, 0, 2), (2, 0, 1))
    per_visit = {
        name: (float(jaccard), float(jaccard), float(jaccard)) for name in MODULE.METRIC_NAMES
    }
    aggregate = {name: float(values[0]) for name, values in per_visit.items()}
    return MODULE.Bundle(
        predictions=predictions,
        rankings=rankings,
        per_visit=per_visit,
        aggregate=aggregate,
        budget=budget,
        seed=seed,
    )


def _bundle_grid() -> tuple[
    dict[int, dict[int, object]], dict[int, dict[int, object]], dict[int, object]
]:
    budgets = (0.10, 0.20, 0.30)
    budgetset = {
        index: {
            seed: _bundle(seed=seed, budget=budgets[index], jaccard=0.8)
            for seed in MODULE.LEARNED_SEEDS
        }
        for index in range(3)
    }
    independent = {
        index: {
            seed: _bundle(seed=seed, budget=budgets[index], jaccard=0.5)
            for seed in MODULE.LEARNED_SEEDS
        }
        for index in range(3)
    }
    deterministic = {
        index: _bundle(seed=None, budget=budgets[index], jaccard=0.4) for index in range(3)
    }
    return budgetset, independent, deterministic


def test_controller_closure_preserves_bundles_through_both_frontiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budgets = (0.10, 0.20, 0.30)
    rows = _rows()
    budgetset, independent, deterministic = _bundle_grid()
    aggregate_inputs: list[dict[int, object]] = []
    bootstrap_calls: list[tuple[int, int]] = []
    greedy_calls: list[int] = []
    matched_calls: list[int] = []

    original_aggregate = MODULE.aggregate_seed_bundles

    def aggregate_spy(bundles: dict[int, object]) -> dict[str, float]:
        assert set(bundles) == set(MODULE.LEARNED_SEEDS)
        assert all(isinstance(bundle, MODULE.Bundle) for bundle in bundles.values())
        aggregate_inputs.append(bundles)
        return original_aggregate(bundles)  # type: ignore[arg-type]

    def fake_bootstrap(
        sampled_rows: tuple[object, ...],
        *,
        patient_key: object,
        recompute_operating_points: object,
        recompute_frontier_gap: object,
        replicates: int,
        seed: int,
    ) -> object:
        del patient_key
        bootstrap_calls.append((replicates, seed))
        points = recompute_operating_points(sampled_rows)
        gap = recompute_frontier_gap(points)
        return MODULE.BootstrapResult((float(gap),), float(gap), float(gap))

    original_greedy = MODULE.greedy_frontier
    original_matched = MODULE.matched_independent_frontier

    def greedy_spy(*args: object, **kwargs: object) -> object:
        del kwargs
        greedy_calls.append(1)
        return original_greedy(*args)

    def matched_spy(*args: object, **kwargs: object) -> object:
        del kwargs
        matched_calls.append(int(args[0]))
        return original_matched(*args)

    monkeypatch.setattr(MODULE, "aggregate_seed_bundles", aggregate_spy)
    monkeypatch.setattr(MODULE, "patient_cluster_bootstrap", fake_bootstrap)
    monkeypatch.setattr(MODULE, "greedy_frontier", greedy_spy)
    monkeypatch.setattr(MODULE, "matched_independent_frontier", matched_spy)

    greedy_result = MODULE.frontier_record(
        budgetset,
        independent,
        deterministic,
        rows,
        budgets,
        "Greedy+1Swap",
        bootstrap_replicates=2,
        bootstrap_seed=MODULE.BOOTSTRAP_SEED,
    )
    independent_result = MODULE.frontier_record(
        budgetset,
        independent,
        deterministic,
        rows,
        budgets,
        "Independent",
        bootstrap_replicates=2,
        bootstrap_seed=MODULE.BOOTSTRAP_SEED,
    )

    assert set(greedy_result) == set(MODULE.BUDGET_LABELS[:2])
    assert set(independent_result) == set(MODULE.BUDGET_LABELS[:2])
    assert bootstrap_calls == [(2, MODULE.BOOTSTRAP_SEED)] * 4
    assert len(aggregate_inputs) >= 12
    assert len(greedy_calls) == 6
    assert matched_calls == list(MODULE.LEARNED_SEEDS) * 2
    assert (
        MODULE.terminal_verdict({"PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES": True})
        == "PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES"
    )


def test_sampled_controller_bundle_rejects_aggregate_mapping() -> None:
    bundle = _bundle(seed=2002, budget=0.1, jaccard=0.5)
    with pytest.raises(TypeError, match="Bundle object"):
        MODULE.make_bundle_from_sample(  # type: ignore[arg-type]
            bundle.aggregate,
            _rows(),
        )
