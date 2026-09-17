from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[2] / "research" / "prototypes" / "rime"
sys.path.insert(0, str(ROOT))

from rime import MEDICATIONS, RIMEModel, pack_inputs, sample_contexts, scores_for_set  # noqa: E402


def _encoded(variant: str):
    torch.manual_seed(7)
    model = RIMEModel(5, 4, variant, medication_count=MEDICATIONS).eval()
    rows = [{"diagnoses": [1], "procedures": [0], "history": []}]
    batch = pack_inputs(rows, 5, 4)
    return model, model(batch)


def test_context_sampler_adds_one_negative() -> None:
    targets = torch.zeros((2, MEDICATIONS))
    targets[0, [1, 3]] = 1
    targets[1, [2]] = 1
    positive, erroneous = sample_contexts(targets, random.Random(11))
    assert torch.all(~positive | targets.bool())
    assert torch.all(erroneous >= positive)
    assert torch.equal(erroneous.sum(1), positive.sum(1) + 1)


@pytest.mark.parametrize("variant", ["composition", "count_only"])
def test_score_identity(variant: str) -> None:
    model, encoded = _encoded(variant)
    selected = torch.zeros((1, MEDICATIONS), dtype=torch.bool)
    selected[0, [1, 3]] = True
    scores = scores_for_set(model, encoded, selected)
    for medication in range(MEDICATIONS):
        context = selected.clone()
        context[0, medication] = False
        expected = model.marginal_logits(encoded, context)[0, medication]
        assert torch.allclose(scores[0, medication], expected, atol=1e-5, rtol=1e-5)


def test_count_only_is_composition_invariant() -> None:
    model, encoded = _encoded("count_only")
    left = torch.zeros((1, MEDICATIONS), dtype=torch.bool)
    right = torch.zeros((1, MEDICATIONS), dtype=torch.bool)
    left[0, [1, 3, 5]] = True
    right[0, [2, 4, 6]] = True
    left_score = model.marginal_logits(encoded, left)[0, 20]
    right_score = model.marginal_logits(encoded, right)[0, 20]
    assert torch.allclose(left_score, right_score, atol=1e-6, rtol=1e-6)
