from __future__ import annotations

import importlib.util
import inspect
import sys
from dataclasses import replace
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[2]
    / "research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate01_mechanical_preflight.py"
)
SPEC = importlib.util.spec_from_file_location("idea008_gate01_mechanical_preflight", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _scores() -> list[float]:
    return [float(index) / 10.0 for index in range(MODULE.CANDIDATE_COUNT)]


def _embeddings() -> list[list[float]]:
    return [[float(index), 1.0, -1.0] for index in range(MODULE.CANDIDATE_COUNT)]


def _ddi() -> list[list[float]]:
    return [
        [1.0 if index != other else 0.0 for other in range(MODULE.CANDIDATE_COUNT)]
        for index in range(MODULE.CANDIDATE_COUNT)
    ]


def _validated_integration() -> dict[str, object]:
    return {
        "integration_status": "PASS",
        "validated_real": True,
        "source_revision": MODULE.UPSTREAM_MOLEREC_REVISION,
        "profile": MODULE.MOLEREC_PROFILE,
        "checkpoint_sha256": MODULE.MOLEREC_CHECKPOINT_SHA256,
        "dataset_id": MODULE.DATASET_ID,
        "partition": "canonical Comparison Train only",
        "model_eval": True,
        "no_gradient": True,
        "same_forward": True,
        "score_candidate_dimension": MODULE.CANDIDATE_COUNT,
        "embedding_candidate_dimension": MODULE.CANDIDATE_COUNT,
        "score_shape": [MODULE.CANDIDATE_COUNT],
        "embedding_shape": [MODULE.CANDIDATE_COUNT, 64],
        "embedding_rank": 2,
        "score_extractor_consistent": True,
    }


def test_explicit_residual_anchor_in_budgetset_and_independent() -> None:
    scores = _scores()
    embeddings = _embeddings()

    def zero(*_args: object) -> list[float]:
        return [0.0] * MODULE.CANDIDATE_COUNT

    zero_ddi = [[0.0] * MODULE.CANDIDATE_COUNT for _ in range(MODULE.CANDIDATE_COUNT)]
    trace = MODULE.budgetset_recurrence(scores, embeddings, 0.2, zero_ddi, 3, zero, zero)
    independent = MODULE.BudgetConditionedIndependentScorer(zero, zero)
    independent_scores = independent.score(scores, embeddings, 0.2, [0.0] * 131, [0.0] * 131)
    assert trace.z_final == pytest.approx(scores)
    assert independent_scores == pytest.approx(scores)


class _HookHandle:
    def __init__(self, callbacks: list[object], callback: object) -> None:
        self.callbacks = callbacks
        self.callback = callback

    def remove(self) -> None:
        self.callbacks.remove(self.callback)


class _FakeScoreExtractor:
    def __init__(self) -> None:
        self.pre_hooks: list[object] = []
        self.post_hooks: list[object] = []

    def register_forward_pre_hook(self, callback: object) -> _HookHandle:
        self.pre_hooks.append(callback)
        return _HookHandle(self.pre_hooks, callback)

    def register_forward_hook(self, callback: object) -> _HookHandle:
        self.post_hooks.append(callback)
        return _HookHandle(self.post_hooks, callback)

    def __call__(self, embeddings: list[list[float]]) -> list[float]:
        for callback in tuple(self.pre_hooks):
            callback(self, (embeddings,))
        scores = [row[0] for row in embeddings]
        for callback in tuple(self.post_hooks):
            callback(self, (embeddings,), scores)
        return scores


class _FakeMoleRec:
    def __init__(self) -> None:
        self.score_extractor = _FakeScoreExtractor()
        self.training = True
        self.forward_calls = 0

    def eval(self) -> _FakeMoleRec:
        self.training = False
        return self

    def __call__(self, *args: object, **kwargs: object) -> tuple[list[float], None]:
        del args, kwargs
        self.forward_calls += 1
        embeddings = [[float(index), 2.0] for index in range(MODULE.CANDIDATE_COUNT)]
        return self.score_extractor(embeddings), None


def test_frozen_forward_produces_s_and_e_from_one_eval_no_grad_forward() -> None:
    model = _FakeMoleRec()
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.extract_frozen_molerec_features(
            model,
            source_revision="wrong",
            profile=MODULE.MOLEREC_PROFILE,
            checkpoint_sha256=MODULE.MOLEREC_CHECKPOINT_SHA256,
            dataset_id=MODULE.DATASET_ID,
        )
    assert model.forward_calls == 0
    features = MODULE.extract_frozen_molerec_features(
        model,
        source_revision=MODULE.UPSTREAM_MOLEREC_REVISION,
        profile=MODULE.MOLEREC_PROFILE,
        checkpoint_sha256=MODULE.MOLEREC_CHECKPOINT_SHA256,
        dataset_id=MODULE.DATASET_ID,
        forward_kwargs={"x": 1},
    )
    assert model.forward_calls == 1
    assert features.same_forward is True
    assert features.eval_mode is True
    assert features.no_grad is True
    assert features.candidate_count == 131
    assert len(features.embeddings) == 131
    assert features.embedding_width == 2
    assert all(
        handle_count == 0
        for handle_count in (
            len(model.score_extractor.pre_hooks),
            len(model.score_extractor.post_hooks),
        )
    )
    summary = MODULE.frozen_molerec_integration_summary(features)
    assert summary["source_revision"] == MODULE.UPSTREAM_MOLEREC_REVISION
    assert summary["embedding_candidate_dimension"] == 131
    assert summary["integration_status"] == "UNVALIDATED"
    assert MODULE.validate_frozen_molerec_integration_result(summary) is False
    assert (
        MODULE.validate_frozen_molerec_integration_result(
            MODULE.frozen_molerec_integration_summary(features, validated_real=True)
        )
        is True
    )
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.frozen_molerec_integration_summary(replace(features, dataset_id="not-authorized"))


def test_budgetset_embedding_candidate_dimension_is_131() -> None:
    assert len(_embeddings()) == MODULE.CANDIDATE_COUNT
    assert (
        len(
            MODULE.FrozenMoleRecFeatures(
                _scores(),
                tuple(map(tuple, _embeddings())),
                MODULE.UPSTREAM_MOLEREC_REVISION,
                MODULE.MOLEREC_PROFILE,
                MODULE.MOLEREC_CHECKPOINT_SHA256,
                MODULE.DATASET_ID,
            ).embeddings
        )
        == 131
    )


def test_budgetset_t_two_recomputes_q_c_rho_after_first_update() -> None:
    scores = [0.0] * MODULE.CANDIDATE_COUNT
    embeddings = _embeddings()
    ddi = [[0.0] * MODULE.CANDIDATE_COUNT for _ in range(MODULE.CANDIDATE_COUNT)]
    ddi[0][1] = ddi[1][0] = 1.0

    def utility(*_args: object) -> list[float]:
        return [0.0] * 131

    seen_rho: list[float] = []

    def risk(_scores: object, _embeddings: object, rho: float) -> list[float]:
        seen_rho.append(rho)
        return [0.0] * 131

    trace = MODULE.budgetset_recurrence(scores, embeddings, 0.3, ddi, 2, utility, risk)
    assert MODULE.T == 2
    assert (
        len(trace.q_before_update)
        == len(trace.c_before_update)
        == len(trace.rho_before_update)
        == 2
    )
    assert trace.q_before_update[0] != trace.q_before_update[1]
    assert trace.c_before_update[0] == pytest.approx(
        MODULE.marginal_ddi(trace.q_before_update[0], ddi, 2)
    )
    assert trace.c_before_update[1] == pytest.approx(
        MODULE.marginal_ddi(trace.q_before_update[1], ddi, 2)
    )
    assert trace.rho_before_update == pytest.approx(seen_rho)
    assert trace.rho_before_update[0] != trace.rho_before_update[1]


def test_every_hard_output_path_has_exact_k() -> None:
    scores = _scores()
    embeddings = _embeddings()
    ddi = _ddi()
    vocabulary = tuple(f"M{index:03d}" for index in range(131))
    k_x = 4

    def zero(*_args: object) -> list[float]:
        return [0.0] * 131

    trace = MODULE.budgetset_recurrence(scores, embeddings, 0.2, ddi, k_x, zero, zero)
    independent = MODULE.BudgetConditionedIndependentScorer(zero, zero)
    outputs = [
        MODULE.exact_topk(trace.z_final, k_x, vocabulary),
        independent.hard_set(scores, embeddings, 0.2, [0.0] * 131, [0.0] * 131, k_x, vocabulary),
        MODULE.greedy_budget_aware_1swap(scores, ddi, 0.2, k_x, vocabulary),
        *MODULE.fixed_lambda_family(scores, ddi, k_x, vocabulary).values(),
    ]
    assert all(len(output) == k_x for output in outputs)


def test_protocol_paths_reject_incomplete_medication_pool() -> None:
    short_scores = _scores()[:-1]
    short_embeddings = _embeddings()[:-1]
    short_ddi = _ddi()[:-1]
    short_ddi = [row[:-1] for row in short_ddi]
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.BudgetConditionedIndependentScorer().score(
            short_scores, short_embeddings, 0.2, [0.0] * 130, [0.0] * 130
        )
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.exact_topk(short_scores, 2)
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.greedy_budget_aware_1swap(short_scores, short_ddi, 0.2, 2)
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.fixed_lambda_scores(short_scores, short_ddi, 2, 0.5)


def test_greedy_metric_ranking_places_selected_candidates_first() -> None:
    scores = [0.0] * MODULE.CANDIDATE_COUNT
    scores[1] = 2.0
    scores[2] = 1.0
    ranking = MODULE.greedy_ranking((2,), scores)
    assert ranking[0] == 2
    assert ranking[1] == 1


def test_k_zero_and_k_one_semantics_bypass_pair_greedy() -> None:
    scores = [0.0] * MODULE.CANDIDATE_COUNT
    vocabulary = tuple(reversed([f"M{index:03d}" for index in range(131)]))
    ddi = _ddi()
    assert MODULE.greedy_budget_aware_1swap(scores, ddi, 0.0, 0, vocabulary) == ()
    selected = MODULE.greedy_budget_aware_1swap(scores, ddi, 0.0, 1, vocabulary)
    assert selected == MODULE.exact_topk(scores, 1, vocabulary)
    assert MODULE.hard_ddi(selected, ddi) == 0.0
    assert MODULE.relaxed_ddi((0.5,) * 131, ddi, 1) == 0.0
    assert MODULE.marginal_ddi((0.5,) * 131, ddi, 1) == (0.0,) * 131


def test_frozen_base_cardinality_and_budget_calibration_are_fixed() -> None:
    probabilities = [0.5, 0.49] + [0.0] * 129
    assert MODULE.frozen_base_set(probabilities) == (0,)
    assert MODULE.frozen_base_cardinality(probabilities) == 1
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.frozen_base_set([0.5])
    assert MODULE.calibrate_budgets([0.1, 0.2]) == pytest.approx((0.15, 0.09, 0.12, 0.15))
    with pytest.raises(MODULE.ProtocolMismatch, match="STOP_NO_BASE_DDI_HEADROOM"):
        MODULE.calibrate_budgets([0.0, 0.0])


def test_independent_train_only_static_ddi_summaries() -> None:
    ddi = [[0.0, 1.0], [1.0, 0.0]]
    d_static, p_static = MODULE.static_ddi_summaries([{0, 1}, {0}], ddi)
    assert d_static == pytest.approx((1.0, 1.0))
    assert p_static == pytest.approx((0.5, 1.0))


def test_exact_v12_split_hash_fixtures() -> None:
    expected = {
        0: "Gate01-Dev",
        1: "Gate01-Dev",
        2: "Gate01-Audit",
        6: "Gate01-Audit",
        8: "Gate01-Audit",
    }
    assert {patient: MODULE.gate01_partition(patient) for patient in expected} == expected
    assert 0.0 <= MODULE.gate01_split_u(0) < 1.0


def test_greedy_plus_one_swap_is_deterministic_fixed_k() -> None:
    scores = [float(index % 7) for index in range(131)]
    ddi = _ddi()
    vocabulary = tuple(f"M{index:03d}" for index in range(131))
    first = MODULE.greedy_budget_aware_1swap(scores, ddi, 0.0, 5, vocabulary)
    second = MODULE.greedy_budget_aware_1swap(scores, ddi, 0.0, 5, vocabulary)
    assert first == second
    assert len(first) == 5


def test_independent_signature_excludes_current_set_feedback() -> None:
    parameters = tuple(
        inspect.signature(MODULE.BudgetConditionedIndependentScorer.score).parameters
    )
    assert parameters == ("self", "scores", "embeddings", "budget", "d_static", "p_static")
    assert MODULE.BudgetConditionedIndependentScorer.FORBIDDEN_INPUTS
    assert not MODULE.BudgetConditionedIndependentScorer.FORBIDDEN_INPUTS.intersection(parameters)


def test_ordinary_frontier_uses_max_utility_and_strict_positive_gap() -> None:
    budget = MODULE.OperatingPoint(risk=0.20, utility=0.60, order=0)
    controls = (
        MODULE.OperatingPoint(risk=0.19, utility=0.55, order=0),
        MODULE.OperatingPoint(risk=0.20, utility=0.50, order=1),
        MODULE.OperatingPoint(risk=0.30, utility=0.90, order=2),
    )
    comparison = MODULE.compare_seed_frontier(budget, controls)
    assert comparison.branch == "ordinary"
    assert comparison.selected_order == 0
    assert comparison.utility_gap == pytest.approx(0.05)
    assert comparison.favorable is True
    assert (
        MODULE.compare_seed_frontier(MODULE.OperatingPoint(0.2, 0.55, 0), controls).favorable
        is False
    )


def test_empty_frontier_is_total_and_uses_risk_utility_order_and_equality() -> None:
    budget = MODULE.OperatingPoint(risk=0.10, utility=0.50, order=0)
    controls = (
        MODULE.OperatingPoint(risk=0.20, utility=0.40, order=2),
        MODULE.OperatingPoint(risk=0.20, utility=0.50, order=1),
        MODULE.OperatingPoint(risk=0.25, utility=0.90, order=0),
    )
    first = MODULE.compare_seed_frontier(budget, controls)
    second = MODULE.compare_seed_frontier(budget, controls)
    assert first == second
    assert first.branch == "empty"
    assert first.selected_order == 1
    assert first.utility_gap == pytest.approx(0.0)
    assert first.favorable is True
    with pytest.raises(MODULE.InvalidGateImplementation):
        MODULE.compare_seed_frontier(budget, ())


def test_aggregate_frontier_applies_materiality_after_seed_endpoint_choice() -> None:
    budget = MODULE.OperatingPoint(0.20, 0.60, 0)
    controls = (MODULE.OperatingPoint(0.20, 0.59, 0),)
    assert (
        MODULE.compare_aggregate_frontier(budget, controls, bootstrap_lower_bound=0.0001).favorable
        is True
    )
    assert (
        MODULE.compare_aggregate_frontier(budget, controls, bootstrap_lower_bound=0.0).favorable
        is False
    )
    empty_controls = (MODULE.OperatingPoint(0.30, 0.60, 0),)
    assert (
        MODULE.compare_aggregate_frontier(
            budget, empty_controls, bootstrap_lower_bound=-0.004
        ).favorable
        is True
    )
    assert (
        MODULE.compare_aggregate_frontier(
            budget, empty_controls, bootstrap_lower_bound=-0.005
        ).favorable
        is False
    )


def test_independent_uses_matched_seed_only() -> None:
    budget = MODULE.OperatingPoint(0.10, 0.50, 0, seed=2002)
    independent = {
        2002: (MODULE.OperatingPoint(0.20, 0.40, 0, seed=2002),),
        2003: (MODULE.OperatingPoint(0.11, 0.99, 0, seed=2003),),
        2004: (MODULE.OperatingPoint(0.11, 0.99, 0, seed=2004),),
    }
    comparison = MODULE.matched_independent_frontier(2002, budget, independent)
    assert comparison.selected_order == 0
    assert comparison.favorable is True
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.matched_independent_frontier(
            2002,
            MODULE.OperatingPoint(0.10, 0.50, 0, seed=2003),
            independent,
        )
    unmatched = dict(independent)
    unmatched[2002] = (MODULE.OperatingPoint(0.20, 0.40, 0, seed=2003),)
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.matched_independent_frontier(2002, budget, unmatched)


def test_seed_robustness_requires_the_exact_matched_seed_set() -> None:
    comparisons = {
        seed: MODULE.FrontierComparison("ordinary", seed, 0.1, 0.0, seed != 2004)
        for seed in MODULE.LEARNED_SEEDS
    }
    assert MODULE.seed_robustness_satisfied(comparisons) is True
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.seed_robustness_satisfied({2002: comparisons[2002]})


def test_deterministic_controls_have_no_artificial_seeds() -> None:
    points = tuple(MODULE.OperatingPoint(0.1, 0.2, index) for index in range(3))
    assert all(point.seed is None for point in points)
    family = MODULE.fixed_lambda_family(_scores(), _ddi(), 2)
    assert tuple(family) == MODULE.FIXED_LAMBDAS
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.greedy_frontier(
            MODULE.OperatingPoint(0.1, 0.2, 0, seed=2002),
            (MODULE.OperatingPoint(0.1, 0.2, 0, seed=2002),),
        )


def test_composition_response_excludes_k_zero_by_default() -> None:
    assert MODULE.composition_change_rate([(), (1,)], [(), (2,)]) == pytest.approx(1.0)
    assert MODULE.composition_change_rate([(), ()], [(), ()]) == 0.0
    assert MODULE.composition_change_rate(
        [(), (1,)], [(), (2,)], k_x_values=[0, 1]
    ) == pytest.approx(1.0)


def test_patient_bootstrap_preserves_multiplicity_and_recomputes_frontier() -> None:
    rows = (
        {"patient": "p1", "visit": "a"},
        {"patient": "p1", "visit": "b"},
        {"patient": "p2", "visit": "c"},
    )
    sampled_lengths: list[int] = []
    frontier_calls: list[int] = []

    def recompute(sampled: list[dict[str, str]]) -> dict[str, int]:
        sampled_lengths.append(len(sampled))
        return {"rows": len(sampled)}

    def frontier(points: dict[str, int]) -> float:
        frontier_calls.append(points["rows"])
        return float(points["rows"])

    result = MODULE.patient_cluster_bootstrap(
        rows,
        patient_key=lambda row: row["patient"],
        recompute_operating_points=recompute,
        recompute_frontier_gap=frontier,
        replicates=4,
        seed=MODULE.BOOTSTRAP_SEED,
    )
    assert sampled_lengths == [3, 2, 4, 3]
    assert frontier_calls == sampled_lengths
    assert len(result.replicate_values) == 4


def test_checkpoint_and_configuration_keys_follow_frozen_lexicographic_order() -> None:
    assert MODULE.checkpoint_selection_key(2, 0.5, 0.2, 10) < MODULE.checkpoint_selection_key(
        1, 0.9, 0.0, 1
    )
    assert MODULE.checkpoint_selection_key(2, 0.5, 0.2, 10) < MODULE.checkpoint_selection_key(
        2, 0.4, 0.0, 1
    )
    assert MODULE.configuration_selection_key(
        2, 0.5, 0.2, 3e-4, 5
    ) < MODULE.configuration_selection_key(1, 0.9, 0.0, 1e-3, 10)
    selected = MODULE.select_checkpoint_with_patience(
        [
            {"epoch": 1, "n_compliant": 1, "u_primary": 0.1, "v_all": 0.2},
            {"epoch": 2, "n_compliant": 1, "u_primary": 0.1, "v_all": 0.3},
            {"epoch": 3, "n_compliant": 1, "u_primary": 0.1, "v_all": 0.4},
            {"epoch": 4, "n_compliant": 1, "u_primary": 0.1, "v_all": 0.5},
            {"epoch": 5, "n_compliant": 1, "u_primary": 0.1, "v_all": 0.6},
            {"epoch": 6, "n_compliant": 1, "u_primary": 0.1, "v_all": 0.7},
            {"epoch": 7, "n_compliant": 2, "u_primary": 0.0, "v_all": 0.0},
        ]
    )
    assert selected.best["epoch"] == 1
    assert selected.stop_epoch == 6


def test_terminal_precedence_is_frozen_top_to_bottom() -> None:
    conditions = {
        "PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES": True,
        "KILL_BUDGETSET": True,
        "KILL_TARGET_SEMANTICS": True,
        "STOP_NO_BASE_DDI_HEADROOM": True,
        "STOP_INVALID_GATE_IMPLEMENTATION": True,
    }
    assert MODULE.terminal_verdict(conditions) == "STOP_INVALID_GATE_IMPLEMENTATION"
    assert (
        MODULE.terminal_verdict({"KILL_BUDGETSET": True, "KILL_TARGET_SEMANTICS": True})
        == "KILL_TARGET_SEMANTICS"
    )
    assert MODULE.terminal_verdict({}) == "INCONCLUSIVE_STOP"
    assert (
        MODULE.terminal_verdict({"PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES": True})
        == "PASS_GATE_01_BUDGETSET_MECHANISM_SURVIVES"
    )


def test_public_record_distinguishes_mechanical_status_from_gate_status() -> None:
    synthetic_checks = {name: True for name in MODULE.SYNTHETIC_MECHANICAL_CHECKS}
    missing_integration = MODULE.build_mechanical_preflight_record(synthetic_checks)
    assert missing_integration["verdict"] == "MECHANICAL_PREFLIGHT_INCOMPLETE"
    assert missing_integration["checks"]["same_frozen_no_grad_forward"] is False
    record = MODULE.build_mechanical_preflight_record(
        synthetic_checks,
        integration=_validated_integration(),
    )
    assert record["verdict"] == "MECHANICAL_PREFLIGHT_PASS"
    assert record["formal_gate_execution"] == "NOT_RUN"
    assert record["gate01_audit"] == "UNOPENED"
    assert record["scientific_metrics_generated"] is False
    assert record["checks"]["same_frozen_no_grad_forward"] is True
    assert record["checks"]["embedding_candidate_dimension"] is True
    assert "patient_id" not in record["frozen_molerec_integration"]
    wrong_identity = _validated_integration()
    wrong_identity["source_revision"] = "wrong"
    assert (
        MODULE.build_mechanical_preflight_record(synthetic_checks, integration=wrong_identity)[
            "verdict"
        ]
        == "STOP_IMPLEMENTATION_MISMATCH"
    )
    malformed = _validated_integration()
    malformed["embedding_shape"] = [130, 64]
    assert (
        MODULE.build_mechanical_preflight_record(synthetic_checks, integration=malformed)["verdict"]
        == "STOP_IMPLEMENTATION_MISMATCH"
    )
    assert (
        MODULE.build_mechanical_preflight_record({"a": True})["verdict"]
        == "STOP_IMPLEMENTATION_MISMATCH"
    )
