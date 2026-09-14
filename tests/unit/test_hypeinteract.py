from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1] / ".." / "research/prototypes/hypeinteract/hypeinteract.py"
).resolve()
SPEC = importlib.util.spec_from_file_location("hypeinteract_prototype", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _records() -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    return (
        (
            ((1, 2), (10,), (40,)),
            ((3,), (11,), (41,)),
            ((4,), (12,), (42,)),
        ),
        (((7,), (13,), (43,)),),
    )


def test_current_visit_target_is_not_in_historical_input() -> None:
    examples = MODULE.build_visit_examples(_records(), (0, 1))
    assert examples[0].historical_medications == ()
    assert examples[1].historical_medications == (40,)
    assert 41 not in examples[1].historical_medications
    assert examples[3].historical_medications == ()


def test_retrieval_excludes_query_patient_and_uses_train_rows_only() -> None:
    numpy = pytest.importorskip("numpy")
    train = MODULE.build_visit_examples(_records(), (0,))
    queries = MODULE.build_visit_examples(_records(), (1,))
    train_health = numpy.eye(len(train), dtype=numpy.float32)
    train_med = numpy.arange(len(train) * 4, dtype=numpy.float32).reshape(len(train), 4)
    query_health = numpy.ones((len(queries), len(train)), dtype=numpy.float32)
    retrieved, neighbors = MODULE._retrieval_channels(
        query_health,
        queries,
        train_health,
        train_med,
        train,
        top_k=2,
    )
    assert retrieved.shape == (len(queries), 4)
    assert all(index < len(train) for row in neighbors for index in row)
    assert all(
        train[index].patient_id != query.patient_id
        for query, row in zip(queries, neighbors)  # noqa: B905
        for index in row
    )


def test_hypergraph_edges_align_with_train_visits_and_samek_is_exact() -> None:
    torch = pytest.importorskip("torch")
    records = _records()
    examples = MODULE.build_visit_examples(records, (0, 1))
    domain = MODULE.build_domain_hypergraph(records, (0, 1), domain="diag", num_nodes=16)
    assert domain.incidence.shape[1] == len(examples)
    assert len(domain.visit_keys) == len(examples)
    scores = (
        torch.arange(MODULE.CANDIDATE_COUNT, dtype=torch.float32).repeat(len(examples), 1).numpy()
    )
    cardinalities = [0, 1, 7, 13]
    decoded = MODULE.topk_sets(scores, cardinalities)
    assert [len(item) for item in decoded] == cardinalities


def test_patient_conditioned_interaction_is_permutation_equivariant() -> None:
    torch = pytest.importorskip("torch")
    numpy = pytest.importorskip("numpy")
    torch.manual_seed(7)
    model = MODULE.PatientConditionedInteraction(
        torch.randn(MODULE.CANDIDATE_COUNT, 8), dim=8, hidden_dim=12
    )
    patient = torch.randn(2, 8)
    logits = torch.randn(2, MODULE.CANDIDATE_COUNT)
    history = torch.randint(0, 2, (2, MODULE.CANDIDATE_COUNT), dtype=torch.float32)
    relation = numpy.eye(MODULE.CANDIDATE_COUNT, dtype=numpy.float32)
    permutation = torch.randperm(MODULE.CANDIDATE_COUNT)
    with torch.no_grad():
        original = model(patient, logits, history, relation, relation)
        permuted = model(
            patient,
            logits[:, permutation],
            history[:, permutation],
            relation[permutation][:, permutation],
            relation[permutation][:, permutation],
        )
    assert original.shape == (2, MODULE.CANDIDATE_COUNT)
    assert torch.allclose(permuted, original[:, permutation], atol=1e-5, rtol=1e-5)
