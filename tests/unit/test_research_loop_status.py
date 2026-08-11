from __future__ import annotations

from dataclasses import replace

import pytest

from medrec_research import (
    AttemptRecord,
    DecisionPacket,
    H1Approval,
    H2Action,
    H2Decision,
    LaneProgress,
    ProtocolValidationError,
    ResearchLoopStatus,
    SafeDrugBatchContract,
)
from medrec_research.reproduction_contract import REQUIRED_OUTCOMES


def _contract() -> SafeDrugBatchContract:
    from medrec_research import ModelAnnex

    intervals = {metric: [0.0, 1.0] for metric in REQUIRED_OUTCOMES}
    return SafeDrugBatchContract.create(
        model_annexes=tuple(
            ModelAnnex(model_id=model, metric_intervals=intervals)
            for model in ("leap", "retain", "gamenet", "safedrug")
        ),
        data_lineage={"manifest": "m" * 64},
        environment_identity={"image": "e" * 64},
        evaluation_semantics={"bootstrap_rounds": 10},
        resource_ceiling={"gpu_count": 1},
        repair_budget={"units": 0},
        stopping_rules={"max_attempts": 1},
        batch_id="status-fixture",
    )


def _packet(contract_sha256: str, lane_id: str = "gamenet") -> DecisionPacket:
    attempt = AttemptRecord(
        attempt_id=f"{lane_id}-attempt",
        lane_id=lane_id,
        contract_sha256=contract_sha256,
        outcomes={metric: 0.5 for metric in REQUIRED_OUTCOMES},
        uncertainty={metric: [0.4, 0.6] for metric in REQUIRED_OUTCOMES},
    )
    return DecisionPacket(
        packet_id=f"{lane_id}-packet",
        contract_sha256=contract_sha256,
        lane_id=lane_id,
        attempts=(attempt,),
        conclusion="accepted",
        validity="usable",
        outcomes={metric: 0.5 for metric in REQUIRED_OUTCOMES},
        uncertainty={metric: [0.4, 0.6] for metric in REQUIRED_OUTCOMES},
    )


def test_loop_projection_keeps_h1_and_lane_state_independent() -> None:
    contract = _contract()
    h1 = H1Approval.create(contract, owner="research-owner")
    packet = _packet(contract.contract_sha256)
    h2 = H2Decision.create(
        contract=contract,
        packet=packet,
        researcher="research-owner",
        action=H2Action.GO,
    )
    status = ResearchLoopStatus.create(
        contract=contract,
        h1=h1,
        packets=(packet,),
        h2_decisions={packet.lane_id: h2},
        model_ids={packet.lane_id: "gamenet"},
    )

    assert status.is_current
    assert status.h1_current
    assert status.h2_eligible_lane_ids == ("gamenet",)
    assert status.lanes[0].current
    assert status.lanes[0].packet_complete
    assert status.lanes[0].h2_action == "go"
    assert ResearchLoopStatus.from_json(status.to_json()) == status


def test_stale_h1_and_incomplete_packet_are_visible_and_not_authorized() -> None:
    contract = _contract()
    h1 = H1Approval.create(contract, owner="research-owner")
    changed = replace(contract, batch_id="changed", contract_sha256="")
    packet = _packet(changed.contract_sha256)
    status = ResearchLoopStatus.create(contract=changed, h1=h1, packets=(packet,))

    assert status.stale
    assert not status.h1_current
    assert "h1-stale-or-missing" in status.blockers
    assert not status.lanes[0].current
    assert not status.lanes[0].h2_go_eligible

    malformed = status.to_dict()
    malformed["status_sha256"] = "0" * 64
    with pytest.raises(ProtocolValidationError, match="status_sha256"):
        ResearchLoopStatus.from_dict(malformed)


def test_loop_marks_packets_from_a_different_contract_stale() -> None:
    contract = _contract()
    h1 = H1Approval.create(contract, owner="research-owner")
    other = replace(contract, batch_id="other", contract_sha256="")
    packet = _packet(other.contract_sha256)
    status = ResearchLoopStatus.create(contract=contract, h1=h1, packets=(packet,))

    assert status.stale
    assert status.lanes[0].current is False
    assert status.lanes[0].h2_action is None
    assert "contract-mismatch" in status.lanes[0].blockers
    assert "gamenet:contract-mismatch" in status.blockers


def test_lane_projection_rejects_local_evidence_paths() -> None:
    with pytest.raises(ProtocolValidationError, match="local path"):
        LaneProgress(
            lane_id="lane",
            model_id="gamenet",
            stage="safedrug",
            attempt_status="completed",
            packet_complete=True,
            conclusion="accepted",
            h2_action=None,
            h2_go_eligible=False,
            current=True,
            evidence_urls=("/private/trace.log",),
        )
