from __future__ import annotations

import json
from pathlib import Path

import pytest

from medrec_research.errors import ProtocolValidationError
from medrec_research.safedrug_selection import (
    SAFE_DRUG_LANE_IDS,
    require_selected_safedrug_lane,
    select_safedrug_candidate,
    write_selection,
)


def _candidate(
    lane_id: str,
    *,
    learning_rate: float,
    jaccard: float,
    ddi_rate: float,
) -> dict[str, object]:
    return {
        "lane_id": lane_id,
        "learning_rate": learning_rate,
        "checkpoint_identity": f"{lane_id}-checkpoint",
        "validation_jaccard": jaccard,
        "validation_ddi_rate": ddi_rate,
    }


def _candidates() -> list[dict[str, object]]:
    return [
        _candidate(SAFE_DRUG_LANE_IDS[0], learning_rate=1e-5, jaccard=0.51, ddi_rate=0.07),
        _candidate(SAFE_DRUG_LANE_IDS[1], learning_rate=1e-4, jaccard=0.52, ddi_rate=0.08),
        _candidate(SAFE_DRUG_LANE_IDS[2], learning_rate=5e-4, jaccard=0.52, ddi_rate=0.06),
    ]


def test_selection_uses_validation_ties_and_is_order_independent() -> None:
    first = select_safedrug_candidate(_candidates())
    second = select_safedrug_candidate(list(reversed(_candidates())))

    assert first["state"] == "selection_ready"
    assert first["selected_lane_id"] == SAFE_DRUG_LANE_IDS[2]
    assert first["comparison_decisions"] == second["comparison_decisions"]
    assert first["test_metrics_available"] is False


def test_selection_marks_missing_candidate_incomplete() -> None:
    selection = select_safedrug_candidate(_candidates()[:-1])

    assert selection["state"] == "selection_incomplete"
    assert selection["selected_lane_id"] is None
    assert any(SAFE_DRUG_LANE_IDS[2] in error for error in selection["errors"])


def test_selection_rejects_test_fields_by_failing_closed() -> None:
    candidates = _candidates()
    candidates[0]["test_metrics"] = {"jaccard": 0.99}

    selection = select_safedrug_candidate(candidates)

    assert selection["state"] == "selection_incomplete"
    assert selection["selected_lane_id"] is None


def test_selected_lane_is_the_only_test_admission() -> None:
    selection = select_safedrug_candidate(_candidates())

    selected = require_selected_safedrug_lane(selection, SAFE_DRUG_LANE_IDS[2])
    assert selected["lane_id"] == SAFE_DRUG_LANE_IDS[2]
    with pytest.raises(ProtocolValidationError, match="was not selected"):
        require_selected_safedrug_lane(selection, SAFE_DRUG_LANE_IDS[0])


def test_test_fields_are_rejected_when_reopening_selection() -> None:
    selection = select_safedrug_candidate(_candidates())
    selection["candidates"][0]["test_metrics"] = {"jaccard": 0.99}

    with pytest.raises(ProtocolValidationError, match="unknown field"):
        require_selected_safedrug_lane(selection, SAFE_DRUG_LANE_IDS[2])


def test_selection_is_atomically_written_as_json(tmp_path: Path) -> None:
    selection = select_safedrug_candidate(_candidates())
    path = tmp_path / "selection.json"

    write_selection(path, selection)

    assert json.loads(path.read_text(encoding="utf-8")) == selection
