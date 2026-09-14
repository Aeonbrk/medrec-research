from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1] / ".." / "research/prototypes/futuregraphkd/futuregraphkd.py"
).resolve()
SPEC = importlib.util.spec_from_file_location("futuregraphkd_prototype", MODULE_PATH)
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


def test_next_visit_alignment_and_privilege_boundary() -> None:
    pytest.importorskip("numpy")
    current, future, supported, keys = MODULE.build_visit_features(
        _records(), (0, 1), code_hash_width=8
    )
    assert current.shape == (4, MODULE.context_feature_dimension(8))
    assert future.shape == (4, MODULE.future_feature_dimension(8))
    assert supported.tolist() == [True, True, False, False]
    assert keys == ((0, 0), (0, 1), (0, 2), (1, 0))

    diagnosis_bucket = MODULE._hash_bucket("future-diagnosis", 3, 8)
    procedure_bucket = 8 + MODULE._hash_bucket("future-procedure", 11, 8)
    assert future[0, diagnosis_bucket] == 1.0
    assert future[0, procedure_bucket] == 1.0
    assert future[0].sum() == 3.0  # two next-state codes plus the support marker
    assert future[0, -1] == 1.0
    assert future[2].sum() == 0.0
    assert future[3].sum() == 0.0

    historical_medication_offset = 4 * 8
    assert current[0, historical_medication_offset + 40] == 0.0
    assert current[1, historical_medication_offset + 40] == 1.0
    assert current[1, historical_medication_offset + 41] == 0.0


def test_student_future_invariance_contract_when_torch_is_available() -> None:
    torch = pytest.importorskip("torch")
    numpy = pytest.importorskip("numpy")
    relation = MODULE.build_relation_features(
        numpy.zeros((MODULE.CANDIDATE_COUNT, MODULE.CANDIDATE_COUNT), dtype=numpy.float32),
        numpy.zeros((MODULE.CANDIDATE_COUNT, MODULE.CANDIDATE_COUNT), dtype=numpy.float32),
    )
    student = MODULE.FutureGraphKDModel(
        embedding_dim=4,
        context_dim=MODULE.context_feature_dimension(8),
        future_dim=MODULE.future_feature_dimension(8),
        relation_features=relation,
        hidden_dim=8,
        use_future=False,
    )
    embeddings = torch.randn(2, MODULE.CANDIDATE_COUNT, 4)
    scores = torch.randn(2, MODULE.CANDIDATE_COUNT)
    context = torch.randn(2, MODULE.context_feature_dimension(8))
    future_a = torch.randn(2, MODULE.future_feature_dimension(8))
    future_b = torch.randn(2, MODULE.future_feature_dimension(8))
    with torch.no_grad():
        output_a = student(embeddings, scores, context, future_a)
        output_b = student(embeddings, scores, context, future_b)
    assert torch.allclose(output_a.logits, output_b.logits)
