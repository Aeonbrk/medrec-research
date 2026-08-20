from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from medrec_research.hitl_decision import Decision, HITLDecisionGate


def test_decision_to_and_from_dict():
    now = datetime.now(UTC)
    decision = Decision(
        decision_id="20260820-001-baseline",
        timestamp=now,
        phase="baseline-established",
        context={"metric": "jaccard"},
        options=["Option A", "Option B"],
        chosen="Option A",
        notes="Testing notes",
    )
    d_dict = decision.to_dict()
    assert d_dict["decision_id"] == "20260820-001-baseline"

    restored = Decision.from_dict(d_dict)
    assert restored.decision_id == decision.decision_id
    assert restored.chosen == "Option A"
    assert restored.notes == "Testing notes"


def test_hitl_decision_gate_auto_choice(tmp_path: Path):
    gate = HITLDecisionGate(tmp_path, interactive=False)
    chosen = gate.wait_for_choice(
        phase="test-phase",
        prompt="Please select an option",
        options=["Choice 1", "Choice 2", "Choice 3"],
        context={"test": True},
        auto_choice="2",
    )
    assert chosen == "Choice 2"

    recorded = list(tmp_path.glob("*.json"))
    assert len(recorded) == 1
    content = json.loads(recorded[0].read_text(encoding="utf-8"))
    assert content["chosen"] == "Choice 2"
    assert content["phase"] == "test-phase"
