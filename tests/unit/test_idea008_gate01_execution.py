from __future__ import annotations

import importlib.util
import inspect
import json
import random
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "../research/ideas/008-budgetset-residual-budget-marginal-ddi-set-refinement/experiments/gate01_execution.py"
).resolve()
SPEC = importlib.util.spec_from_file_location("idea008_gate01_execution", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _torch() -> object:
    return pytest.importorskip("torch")


def _scores() -> list[float]:
    return [float(index) / 10.0 for index in range(MODULE.CANDIDATE_COUNT)]


def _embeddings(width: int = 3) -> list[list[float]]:
    return [[float(index + column) for column in range(width)] for index in range(131)]


def _zero_ddi() -> list[list[float]]:
    return [[0.0] * MODULE.CANDIDATE_COUNT for _ in range(MODULE.CANDIDATE_COUNT)]


def _one_edge_ddi() -> list[list[float]]:
    ddi = _zero_ddi()
    ddi[0][1] = ddi[1][0] = 1.0
    return ddi


def _budget_targets() -> tuple[float, float, float]:
    return (0.60, 0.80, 1.00)


def _dev_budget_metrics(
    *,
    jaccards: tuple[float, float, float] = (0.5, 0.5, 0.5),
    violations: tuple[float, float, float] = (0.0, 0.0, 0.0),
    hard_ddi_values: tuple[float, float, float] | None = None,
) -> tuple[dict[str, float], ...]:
    hard = hard_ddi_values or _budget_targets()
    return tuple(
        {
            "jaccard": float(jaccards[index]),
            "positive_violation": float(violations[index]),
            "hard_ddi": float(hard[index]),
        }
        for index in range(3)
    )


def _seed_result(
    configuration: object,
    seed: int,
    budget_metrics: tuple[dict[str, float], ...],
    *,
    family: str = "BudgetSet",
) -> object:
    return MODULE.SeedTrainingResult(
        family=family,
        seed=seed,
        configuration=configuration,
        model=object(),
        best_epoch=1,
        stop_epoch=1,
        best_evaluation={"budget_metrics": budget_metrics, "audit_u_primary": -100.0},
        evaluations=(),
    )


def test_frozen_architecture_grid_and_execution_identity() -> None:
    assert MODULE.LEARNING_RATES == (3e-4, 1e-3)
    assert MODULE.ETAS == (5.0, 10.0)
    assert MODULE.LEARNED_SEEDS == (2002, 2003, 2004)
    assert MODULE.GAMMA == 1e-3
    assert MODULE.WEIGHT_DECAY == 1e-4
    assert MODULE.MAX_EPOCHS == 30
    assert MODULE.PATIENCE == 5
    assert len(MODULE.CONFIGURATION_GRID) == 4
    assert MODULE.frozen_molerec_execution_spec() == {
        "environment": "medrec-molerec-table1",
        "upstream_root": "/root/zhb/MoleRec",
        "upstream_revision": MODULE.UPSTREAM_MOLEREC_REVISION,
        "profile": "molerec-embedding",
        "dataset_subdirectory": "snapshots/molerec-table1-c721-www23",
        "dataset_id": MODULE.DATASET_ID,
        "checkpoint_sha256": MODULE.MOLEREC_CHECKPOINT_SHA256,
    }


def test_k_x_is_count_of_sigmoid_frozen_logits_at_half() -> None:
    logits = [0.0] * MODULE.CANDIDATE_COUNT
    logits[0] = 1.0
    logits[1] = -1.0
    assert MODULE.frozen_k_from_logits(logits) == 130
    assert MODULE.compute_k_x(logits) == MODULE.frozen_k_from_logits(logits)
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.frozen_k_from_logits(logits[:-1])


def test_mlp_architecture_spec_has_exact_width_activation_and_no_dropout() -> None:
    assert MODULE.MLPArchitecture(4) == MODULE.MLPArchitecture(
        input_features=4,
        hidden_features=(64, 32),
        output_features=1,
        activation="GELU",
        dropout=0.0,
    )


def test_budgetset_heads_have_exact_mlp_structure() -> None:
    torch = _torch()
    model = MODULE.BudgetSet(embedding_dim=3)
    for head, input_width in (
        (model.utility_head, 4),
        (model.risk_price_head, 5),
    ):
        layers = tuple(head.layers)
        assert [type(layer) for layer in layers] == [
            torch.nn.Linear,
            torch.nn.GELU,
            torch.nn.Linear,
            torch.nn.GELU,
            torch.nn.Linear,
        ]
        assert [(layer.in_features, layer.out_features) for layer in layers[::2]] == [
            (input_width, 64),
            (64, 32),
            (32, 1),
        ]
        assert not any(isinstance(layer, torch.nn.Dropout) for layer in layers)


def test_independent_heads_have_exact_mlp_structure_and_no_feedback_parameters() -> None:
    torch = _torch()
    model = MODULE.IndependentScorer(embedding_dim=3)
    assert tuple(inspect.signature(model.forward).parameters) == (
        "scores",
        "embeddings",
        "budget",
        "d_static",
        "p_static",
    )
    assert not MODULE.IndependentScorer.FORBIDDEN_INPUTS.intersection(
        inspect.signature(model.forward).parameters
    )
    for head, input_width in (
        (model.utility_head, 4),
        (model.risk_price_head, 7),
    ):
        layers = tuple(head.layers)
        assert [type(layer) for layer in layers] == [
            torch.nn.Linear,
            torch.nn.GELU,
            torch.nn.Linear,
            torch.nn.GELU,
            torch.nn.Linear,
        ]
        assert [(layer.in_features, layer.out_features) for layer in layers[::2]] == [
            (input_width, 64),
            (64, 32),
            (32, 1),
        ]
        assert not any(isinstance(layer, torch.nn.Dropout) for layer in layers)


def test_budgetset_explicit_residual_anchor_and_exact_two_state_recomputations() -> None:
    torch = _torch()
    model = MODULE.BudgetSet(embedding_dim=3)
    scores = torch.zeros(MODULE.CANDIDATE_COUNT)
    embeddings = torch.tensor(_embeddings(), dtype=torch.float32)
    zero_ddi = torch.tensor(_zero_ddi(), dtype=torch.float32)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    anchored = model(scores, embeddings, 0.2, zero_ddi, 3)
    assert torch.allclose(anchored, scores)

    ddi = torch.tensor(_one_edge_ddi(), dtype=torch.float32)
    traced, trace = model.forward_with_trace(scores, embeddings, 0.2, ddi, 3)
    assert traced.shape == scores.shape
    assert (
        len(trace.q_before_update)
        == len(trace.c_before_update)
        == len(trace.rho_before_update)
        == 2
    )
    assert not torch.equal(trace.q_before_update[0], trace.q_before_update[1])
    assert torch.allclose(
        trace.c_before_update[1], MODULE.marginal_ddi_tensor(trace.q_before_update[1], ddi, 3)
    )
    assert not torch.equal(trace.rho_before_update[0], trace.rho_before_update[1])


def test_independent_has_no_current_set_feedback_and_keeps_anchor() -> None:
    torch = _torch()
    model = MODULE.IndependentScorer(embedding_dim=3)
    scores = torch.tensor(_scores(), dtype=torch.float32)
    embeddings = torch.tensor(_embeddings(), dtype=torch.float32)
    zeros = torch.zeros(MODULE.CANDIDATE_COUNT)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    output = model(scores, embeddings, 0.2, zeros, zeros)
    assert torch.allclose(output, scores)


def test_frozen_molerec_inputs_are_detached_from_learned_backpropagation() -> None:
    torch = _torch()
    model = MODULE.BudgetSet(embedding_dim=3)
    scores = torch.zeros(MODULE.CANDIDATE_COUNT, requires_grad=True)
    embeddings = torch.zeros((MODULE.CANDIDATE_COUNT, 3), requires_grad=True)
    ddi = torch.tensor(_zero_ddi(), dtype=torch.float32)
    model(scores, embeddings, 0.2, ddi, 3).sum().backward()
    assert scores.grad is None
    assert embeddings.grad is None


def test_objective_contains_exact_bce_hinge_and_cardinality_terms() -> None:
    torch = _torch()
    logits = torch.zeros((2, MODULE.CANDIDATE_COUNT), dtype=torch.float32)
    targets = torch.zeros_like(logits)
    ddi = torch.tensor(_one_edge_ddi(), dtype=torch.float32)
    budgets = torch.tensor([0.0, 0.2], dtype=torch.float32)
    k_x = torch.tensor([2, 1], dtype=torch.long)
    terms = MODULE.compute_objective_terms(logits, targets, ddi, budgets, k_x, eta=5.0)
    probabilities = torch.sigmoid(logits)
    expected_risk = MODULE.relaxed_ddi_tensor(probabilities, ddi, k_x)
    expected_bce = torch.nn.functional.binary_cross_entropy_with_logits(
        logits, targets, reduction="mean"
    )
    expected_hinge = torch.relu(expected_risk - budgets).mean()
    expected_cardinality = (probabilities.sum(dim=-1) - k_x.float()).square().mean()
    expected = expected_bce + 5.0 * expected_hinge + MODULE.GAMMA * expected_cardinality
    assert torch.allclose(terms.total, expected)
    assert torch.allclose(terms.bce, expected_bce)
    assert torch.allclose(terms.budget_penalty, expected_hinge)
    assert torch.allclose(terms.cardinality_penalty, expected_cardinality)
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.compute_objective(logits, targets, ddi, budgets, k_x, eta=5.0, gamma=0.01)


def test_differentiable_ddi_excludes_diagonal_and_preserves_ordered_marginals() -> None:
    torch = _torch()
    ddi = torch.zeros((MODULE.CANDIDATE_COUNT, MODULE.CANDIDATE_COUNT))
    ddi[0, 0] = 99.0
    ddi[1, 1] = 88.0
    ddi[0, 1] = 0.25
    ddi[1, 0] = 0.75
    q = torch.ones(MODULE.CANDIDATE_COUNT)
    assert torch.allclose(MODULE.relaxed_ddi_tensor(q, ddi, 2), torch.tensor(0.25))
    marginal = MODULE.marginal_ddi_tensor(q, ddi, 2)
    assert torch.allclose(marginal[0], torch.tensor(0.25))
    assert torch.allclose(marginal[1], torch.tensor(0.75))


def test_optimizer_and_frozen_seed_budget_grid() -> None:
    torch = _torch()
    configuration = MODULE.TrainingConfiguration(3e-4, 5.0)
    model = MODULE.BudgetSet(embedding_dim=3)
    optimizer = MODULE.make_adamw(model, configuration)
    assert type(optimizer) is torch.optim.AdamW
    assert optimizer.defaults["lr"] == 3e-4
    assert optimizer.defaults["weight_decay"] == 1e-4
    sampled = MODULE.sample_training_budgets(
        0.60,
        0.80,
        1.00,
        200,
        rng=random.Random(80081),
    )
    assert set(sampled) <= {0.60, 0.80, 1.00}
    assert set(sampled) == {0.60, 0.80, 1.00}
    with pytest.raises(ValueError):
        MODULE.TrainingConfiguration(2e-3, 5.0)
    with pytest.raises(ValueError):
        MODULE.validate_training_seed(2005)


def test_checkpoint_patience_and_configuration_selection_are_dev_only() -> None:
    evaluations = [
        {"epoch": 1, "n_compliant": 1, "u_primary": 0.2, "v_all": 0.1},
        {"epoch": 2, "n_compliant": 1, "u_primary": 0.2, "v_all": 0.2},
        {"epoch": 3, "n_compliant": 1, "u_primary": 0.2, "v_all": 0.3},
        {"epoch": 4, "n_compliant": 1, "u_primary": 0.2, "v_all": 0.4},
        {"epoch": 5, "n_compliant": 1, "u_primary": 0.2, "v_all": 0.5},
        {"epoch": 6, "n_compliant": 1, "u_primary": 0.2, "v_all": 0.6},
        {"epoch": 7, "n_compliant": 2, "u_primary": 0.0, "v_all": 0.0},
    ]
    selected = MODULE.select_checkpoint_with_patience(evaluations)
    assert selected.best["epoch"] == 1
    assert selected.stop_epoch == 6

    budgets = _budget_targets()
    config_results = []
    for index, configuration in enumerate(MODULE.CONFIGURATION_GRID):
        if index == 1:
            metrics = _dev_budget_metrics(jaccards=(0.9, 0.9, 0.9))
        elif index == 0:
            metrics = _dev_budget_metrics(hard_ddi_values=(0.6, 0.81, 1.01))
        else:
            metrics = _dev_budget_metrics(jaccards=(0.8, 0.8, 0.8))
        config_results.append(
            MODULE.ConfigurationDevResult(
                configuration=configuration,
                seed_results=tuple(
                    _seed_result(configuration, seed, metrics) for seed in MODULE.LEARNED_SEEDS
                ),
                budget_targets=budgets,
            )
        )
    chosen_result = MODULE.select_configuration_result(config_results)
    assert chosen_result.configuration.eta == 10.0
    assert chosen_result.configuration.learning_rate == 3e-4
    assert chosen_result.n_compliant_config == 3
    assert chosen_result.u_primary_config == 0.9
    assert chosen_result.v_all_config == 0.0
    assert MODULE.select_configuration(config_results) == chosen_result.configuration
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.select_configuration(config_results[:-1])
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.select_configuration(
            {
                configuration: {
                    "n_compliant_config": 2,
                    "u_primary_config": 0.9,
                    "v_all_config": 0.2,
                }
                for configuration in MODULE.CONFIGURATION_GRID
            }
        )
    assert "audit" not in inspect.signature(MODULE.select_configuration).parameters

    seen: list[int] = []

    def audit(model: object, seed: int) -> dict[str, object]:
        del model
        seen.append(seed)
        return {"seed": seed, "audit_only": True}

    assert [row["seed"] for row in MODULE.evaluate_selected_audit(chosen_result, audit)] == list(
        MODULE.LEARNED_SEEDS
    )
    assert seen == list(MODULE.LEARNED_SEEDS)


def test_configuration_records_reject_missing_and_duplicate_seed_checkpoints() -> None:
    configuration = MODULE.CONFIGURATION_GRID[0]
    metrics = _dev_budget_metrics()
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.ConfigurationDevResult(
            configuration=configuration,
            seed_results=tuple(_seed_result(configuration, seed, metrics) for seed in (2002, 2003)),
            budget_targets=_budget_targets(),
        )
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.ConfigurationDevResult(
            configuration=configuration,
            seed_results=tuple(
                _seed_result(configuration, seed, metrics) for seed in (2002, 2002, 2004)
            ),
            budget_targets=_budget_targets(),
        )


def test_device_placement_supports_cpu_lists_and_detaches_frozen_features() -> None:
    torch = _torch()
    model = MODULE.BudgetSet(embedding_dim=3)
    scores = torch.tensor(_scores(), dtype=torch.float32, requires_grad=True)
    embeddings = torch.tensor(_embeddings(), dtype=torch.float32, requires_grad=True)
    prepared = MODULE.prepare_learned_execution_inputs(
        {
            "scores": scores.tolist(),
            "embeddings": embeddings.tolist(),
            "targets": [0.0] * MODULE.CANDIDATE_COUNT,
            "k_x": 3,
        },
        device=MODULE.execution_device_for_model(model, "cpu"),
        ddi=_zero_ddi(),
        budget=0.2,
    )
    assert all(value.device.type == "cpu" for value in prepared.values())
    assert not prepared["scores"].requires_grad
    assert not prepared["embeddings"].requires_grad
    assert MODULE.execution_device_for_model(model).type == "cpu"
    logits = model(
        prepared["scores"],
        prepared["embeddings"],
        prepared["budget"],
        prepared["ddi"],
        prepared["k_x"],
    )
    MODULE.compute_objective(
        logits,
        prepared["targets"],
        prepared["ddi"],
        prepared["budget"],
        prepared["k_x"],
        eta=5.0,
    ).backward()
    detached = MODULE.prepare_learned_execution_inputs(
        {
            "scores": scores,
            "embeddings": embeddings,
            "targets": [0.0] * MODULE.CANDIDATE_COUNT,
            "k_x": 3,
        },
        device="cpu",
        ddi=_zero_ddi(),
        budget=0.2,
    )
    detached_logits = model(
        detached["scores"],
        detached["embeddings"],
        detached["budget"],
        detached["ddi"],
        detached["k_x"],
    )
    MODULE.compute_objective(
        detached_logits,
        detached["targets"],
        detached["ddi"],
        detached["budget"],
        detached["k_x"],
        eta=5.0,
    ).backward()
    assert scores.grad is None
    assert embeddings.grad is None


def test_independent_device_placement_moves_static_inputs_without_feedback() -> None:
    torch = _torch()
    model = MODULE.IndependentScorer(embedding_dim=3)
    prepared = MODULE.prepare_learned_execution_inputs(
        {
            "scores": _scores(),
            "embeddings": _embeddings(),
            "targets": [0.0] * MODULE.CANDIDATE_COUNT,
            "k_x": 1,
        },
        device="cpu",
        ddi=_zero_ddi(),
        budget=0.2,
        static_d=[0.0] * MODULE.CANDIDATE_COUNT,
        static_p=[0.0] * MODULE.CANDIDATE_COUNT,
        independent=True,
    )
    assert prepared["d_static"].device == torch.device("cpu")
    assert prepared["p_static"].device == torch.device("cpu")
    assert not prepared["d_static"].requires_grad
    assert not prepared["p_static"].requires_grad
    logits = model(
        prepared["scores"],
        prepared["embeddings"],
        prepared["budget"],
        prepared["d_static"],
        prepared["p_static"],
    )
    assert logits.shape == (1, MODULE.CANDIDATE_COUNT)


def test_cuda_device_path_runs_one_synthetic_forward_backward_step() -> None:
    torch = _torch()
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    model = MODULE.BudgetSet(embedding_dim=3).to("cuda")
    prepared = MODULE.prepare_learned_execution_inputs(
        {
            "scores": _scores(),
            "embeddings": _embeddings(),
            "targets": [0.0] * MODULE.CANDIDATE_COUNT,
            "k_x": 3,
        },
        device=MODULE.execution_device_for_model(model),
        ddi=_zero_ddi(),
        budget=0.2,
    )
    assert all(value.device.type == "cuda" for value in prepared.values())
    optimizer = MODULE.make_adamw(model, MODULE.TrainingConfiguration(3e-4, 5.0))
    optimizer.zero_grad(set_to_none=True)
    logits = model(
        prepared["scores"],
        prepared["embeddings"],
        prepared["budget"],
        prepared["ddi"],
        prepared["k_x"],
    )
    loss = MODULE.compute_objective(
        logits,
        prepared["targets"],
        prepared["ddi"],
        prepared["budget"],
        prepared["k_x"],
        eta=5.0,
    )
    loss.backward()
    optimizer.step()
    assert all(parameter.device.type == "cuda" for parameter in model.parameters())


def test_learned_family_orchestration_runs_exact_grid_and_derives_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object, int]] = []
    budgets = _budget_targets()

    def fake_train(family: str, configuration: object, seed: int, **kwargs: object) -> object:
        del kwargs
        calls.append((family, configuration, seed))
        if configuration == MODULE.CONFIGURATION_GRID[1]:
            metrics = _dev_budget_metrics(jaccards=(0.9, 0.9, 0.9))
        else:
            metrics = _dev_budget_metrics(hard_ddi_values=(0.7, 0.9, 1.1))
        return _seed_result(configuration, seed, metrics, family=family)

    monkeypatch.setattr(MODULE, "train_seed_configuration", fake_train)
    selection = MODULE.train_learned_family(
        "BudgetSet",
        embedding_dim=3,
        ddi=_zero_ddi(),
        budget_targets=budgets,
        train_batches=(),
        dev_evaluator=lambda model: {"budget_metrics": _dev_budget_metrics()},
    )
    assert len(calls) == 4 * 3
    assert {(configuration, seed) for _, configuration, seed in calls} == {
        (configuration, seed)
        for configuration in MODULE.CONFIGURATION_GRID
        for seed in MODULE.LEARNED_SEEDS
    }
    assert len(selection.configuration_results) == 4
    assert all(
        tuple(result.seed for result in record.seed_results) == MODULE.LEARNED_SEEDS
        for record in selection.configuration_results
    )
    assert selection.selected_configuration == MODULE.CONFIGURATION_GRID[1]
    assert selection.selected_result.n_compliant_config == 3
    assert selection.selected_result.u_primary_config == 0.9
    assert len(selection.retained_checkpoints) == 3
    assert tuple(result.seed for result in selection.retained_checkpoints) == MODULE.LEARNED_SEEDS
    assert len(selection.runs) == 12


def test_learned_family_orchestration_rejects_wrong_duplicate_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_train(family: str, configuration: object, seed: int, **kwargs: object) -> object:
        del kwargs
        returned_seed = 2002 if seed == 2003 else seed
        return _seed_result(configuration, returned_seed, _dev_budget_metrics(), family=family)

    monkeypatch.setattr(MODULE, "train_seed_configuration", fake_train)
    with pytest.raises(MODULE.ProtocolMismatch):
        MODULE.train_learned_family(
            "BudgetSet",
            embedding_dim=3,
            ddi=_zero_ddi(),
            budget_targets=_budget_targets(),
            train_batches=(),
            dev_evaluator=lambda model: {"budget_metrics": _dev_budget_metrics()},
        )


def test_exact_k_output_uses_preflight_topk_tie_breaking() -> None:
    torch = _torch()
    model = MODULE.BudgetSet(embedding_dim=3)
    scores = torch.zeros(MODULE.CANDIDATE_COUNT)
    embeddings = torch.tensor(_embeddings(), dtype=torch.float32)
    ddi = torch.tensor(_zero_ddi(), dtype=torch.float32)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    vocabulary = tuple(reversed(tuple(f"M{index:03d}" for index in range(131))))
    assert model.hard_set(scores, embeddings, 0.2, ddi, 0, vocabulary) == ()
    assert model.hard_set(scores, embeddings, 0.2, ddi, 1, vocabulary) == MODULE.exact_topk(
        [0.0] * 131, 1, vocabulary
    )
    assert len(model.hard_set(scores, embeddings, 0.2, ddi, 4, vocabulary)) == 4


def test_plan_cli_is_non_executing_and_reports_unopened_boundaries(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert MODULE.main(["--print-plan"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["training"] == "NOT_RUN"
    assert payload["gate01_audit"] == "UNOPENED"
