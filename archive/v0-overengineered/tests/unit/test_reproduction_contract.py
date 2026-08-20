from __future__ import annotations

from dataclasses import replace

import pytest

from medrec_research import (
    AttemptRecord,
    AttemptStatus,
    AttemptValidity,
    DecisionPacket,
    EvidenceConclusion,
    H1Approval,
    H2Action,
    H2Decision,
    ModelAnnex,
    MoleRecStageContract,
    ProtocolValidationError,
    SafeDrugBatchContract,
    Stage,
)
from medrec_research.reproduction_contract import (
    MOLEREC_REVISION,
    REQUIRED_OUTCOMES,
    SAFE_DRUG_MAIN_REVISION,
)


def _intervals() -> dict[str, list[float]]:
    return {metric: [0.0, 1.0] for metric in REQUIRED_OUTCOMES}


def _contract() -> SafeDrugBatchContract:
    annexes = tuple(
        ModelAnnex(model_id=model_id, metric_intervals=_intervals())
        for model_id in ("leap", "retain", "gamenet", "safedrug")
    )
    return SafeDrugBatchContract.create(
        model_annexes=annexes,
        data_lineage={"manifest": "m" * 64, "split": "patient-disjoint"},
        environment_identity={"python": "3.11", "image": "e" * 64},
        evaluation_semantics={
            "bootstrap_rounds": 10,
            "sample_fraction": 0.8,
            "with_replacement": True,
        },
        resource_ceiling={"gpu_count": 1, "cpu_hours": 8},
        repair_budget={"units": 2},
        stopping_rules={"max_attempts": 2},
        batch_id="safedrug-four-models",
    )


def _attempt(
    contract_sha256: str,
    *,
    lane_id: str = "gamenet",
    outcomes: object | None = None,
    uncertainty: object | None = None,
    **kwargs: object,
) -> AttemptRecord:
    return AttemptRecord(
        attempt_id=f"{lane_id}-attempt-1",
        lane_id=lane_id,
        contract_sha256=contract_sha256,
        outcomes=({metric: 0.5 for metric in REQUIRED_OUTCOMES} if outcomes is None else outcomes),
        uncertainty=(
            {metric: [0.4, 0.6] for metric in REQUIRED_OUTCOMES}
            if uncertainty is None
            else uncertainty
        ),
        **kwargs,
    )


def _packet(
    contract_sha256: str,
    *,
    conclusion: EvidenceConclusion = EvidenceConclusion.ACCEPTED,
    validity: AttemptValidity = AttemptValidity.USABLE,
    attempt: AttemptRecord | None = None,
    lane_id: str = "gamenet",
    stage: Stage | None = None,
    outcomes: object | None = None,
    uncertainty: object | None = None,
) -> DecisionPacket:
    return DecisionPacket(
        packet_id=f"{lane_id}-packet",
        contract_sha256=contract_sha256,
        lane_id=lane_id,
        attempts=(attempt or _attempt(contract_sha256, lane_id=lane_id),),
        conclusion=conclusion,
        validity=validity,
        outcomes=({metric: 0.5 for metric in REQUIRED_OUTCOMES} if outcomes is None else outcomes),
        uncertainty=(
            {metric: [0.4, 0.6] for metric in REQUIRED_OUTCOMES}
            if uncertainty is None
            else uncertainty
        ),
        stage=stage,
    )


def test_batch_h1_round_trip_and_presentation_metadata_does_not_stale() -> None:
    contract = _contract()
    approval = H1Approval.create(contract, owner="research-owner")

    assert SafeDrugBatchContract.from_json(contract.to_json()) == contract
    assert H1Approval.from_json(approval.to_json()) == approval
    assert approval.is_current(contract)

    presentation_edit = replace(contract, display_name="A clearer label", notes="Updated note")
    assert presentation_edit.contract_sha256 == contract.contract_sha256
    assert approval.is_current(presentation_edit)

    scientific_edit = replace(contract, batch_id="different-batch", contract_sha256="")
    assert scientific_edit.contract_sha256 != contract.contract_sha256
    assert not approval.is_current(scientific_edit)


def test_batch_rejects_missing_model_or_acceptance_interval() -> None:
    with pytest.raises(ProtocolValidationError, match="exactly four"):
        SafeDrugBatchContract.create(model_annexes=())

    with pytest.raises(ProtocolValidationError, match="missing required metric"):
        ModelAnnex(model_id="gamenet", metric_intervals={"jaccard": [0.0, 1.0]})


def test_decision_packets_are_independent_and_h2_go_is_fail_closed() -> None:
    contract = _contract()
    accepted = _packet(contract.contract_sha256)
    rejected = _packet(
        contract.contract_sha256,
        conclusion=EvidenceConclusion.REJECTED,
        lane_id="retain",
    )
    invalid_attempt = _attempt(
        contract.contract_sha256,
        lane_id="safedrug",
        status=AttemptStatus.INVALID,
    )
    invalid = _packet(
        contract.contract_sha256,
        conclusion=EvidenceConclusion.INCONCLUSIVE,
        validity=AttemptValidity.INVALID,
        attempt=invalid_attempt,
        lane_id="safedrug",
    )

    assert accepted.go_eligible
    assert not rejected.go_eligible
    assert not invalid.go_eligible
    assert H2Decision.create(
        contract=contract, packet=accepted, researcher="research-owner", action=H2Action.GO
    ).allows_execution
    for packet in (rejected, invalid):
        with pytest.raises(ProtocolValidationError, match="go"):
            H2Decision.create(
                contract=contract,
                packet=packet,
                researcher="research-owner",
                action=H2Action.GO,
            )
        assert (
            H2Decision.create(
                contract=contract,
                packet=packet,
                researcher="research-owner",
                action=H2Action.REVISE,
            ).action
            is H2Action.REVISE
        )


def test_decision_packets_require_complete_evidence_and_bind_blockers() -> None:
    contract = _contract()
    with pytest.raises(ProtocolValidationError, match=r"packet\.outcomes"):
        _packet(contract.contract_sha256, outcomes={})
    with pytest.raises(ProtocolValidationError, match=r"packet\.uncertainty"):
        _packet(contract.contract_sha256, uncertainty={})

    incomplete_attempt = _attempt(contract.contract_sha256, outcomes={})
    packet = _packet(contract.contract_sha256, attempt=incomplete_attempt)
    assert not packet.go_eligible
    with pytest.raises(ProtocolValidationError, match="go"):
        H2Decision.create(
            contract=contract,
            packet=packet,
            researcher="research-owner",
            action=H2Action.GO,
        )

    accepted = _packet(contract.contract_sha256)
    h2 = H2Decision.create(
        contract=contract, packet=accepted, researcher="research-owner", action=H2Action.GO
    )
    blocked = replace(accepted, blockers=("manual-review",), packet_sha256="")
    assert blocked.packet_sha256 != accepted.packet_sha256
    assert not h2.is_current(contract=contract, packet=blocked)


def test_h2_rejects_contract_family_drift() -> None:
    contract = _contract()
    packet = _packet(contract.contract_sha256)
    with pytest.raises(ProtocolValidationError, match="metadata"):
        H2Decision.create(
            contract=contract,
            packet=packet,
            researcher="research-owner",
            action=H2Action.REVISE,
            contract_family="other-reproduction",
        )


def test_molerec_stages_require_the_previous_eligible_h2_go() -> None:
    replay = MoleRecStageContract.create(
        stage=Stage.CHECKPOINT_REPLAY,
        variant="molerec-default",
        artifact_bundle_sha256="b" * 64,
    )
    replay_packet = _packet(
        replay.contract_sha256,
        lane_id="molerec-replay",
        stage=Stage.CHECKPOINT_REPLAY,
    )
    replay_h2 = H2Decision.create(
        contract=replay,
        packet=replay_packet,
        researcher="research-owner",
        action=H2Action.GO,
        contract_family="molerec-reproduction",
        source_revision=MOLEREC_REVISION,
        research_target="molerec-source-native",
    )
    training = MoleRecStageContract.create(
        stage=Stage.TRAINING_REPRODUCTION,
        variant="molerec-default",
        artifact_bundle_sha256="c" * 64,
        bundle_equivalence_sha256="c" * 64,
        parent_h2=replay_h2,
        parent_packet=replay_packet,
    )

    assert training.parent_h2_sha256 == replay_h2.decision_sha256
    with pytest.raises(ProtocolValidationError, match="preceding"):
        MoleRecStageContract.create(
            stage=Stage.COMPARISON_QUALIFICATION,
            variant="molerec-default",
            artifact_bundle_sha256="d" * 64,
            parent_h2=replay_h2,
            parent_packet=replay_packet,
        )


def test_molerec_h2_rejects_safedrug_metadata() -> None:
    replay = MoleRecStageContract.create(
        stage=Stage.CHECKPOINT_REPLAY,
        variant="molerec-default",
        artifact_bundle_sha256="b" * 64,
    )
    packet = _packet(
        replay.contract_sha256,
        lane_id="molerec-replay",
        stage=Stage.CHECKPOINT_REPLAY,
    )
    with pytest.raises(ProtocolValidationError, match="metadata"):
        H2Decision.create(
            contract=replay,
            packet=packet,
            researcher="research-owner",
            action=H2Action.GO,
        )

    unstaged = _packet(replay.contract_sha256, lane_id="molerec-replay")
    with pytest.raises(ProtocolValidationError, match="staged"):
        H2Decision.create(
            contract=replay,
            packet=unstaged,
            researcher="research-owner",
            action=H2Action.REVISE,
            contract_family="molerec-reproduction",
            source_revision=MOLEREC_REVISION,
            research_target="molerec-source-native",
        )


def test_molerec_stage_requires_a_staged_parent_packet() -> None:
    replay = MoleRecStageContract.create(
        stage=Stage.CHECKPOINT_REPLAY,
        variant="molerec-default",
        artifact_bundle_sha256="b" * 64,
    )
    unstaged = _packet(replay.contract_sha256, lane_id="molerec-replay")
    parent_h2 = H2Decision(
        contract_sha256=replay.contract_sha256,
        packet_sha256=unstaged.packet_sha256,
        researcher="research-owner",
        action=H2Action.GO,
        contract_family="molerec-reproduction",
        source_revision=MOLEREC_REVISION,
        research_target="molerec-source-native",
    )
    with pytest.raises(ProtocolValidationError, match="preceding"):
        MoleRecStageContract.create(
            stage=Stage.TRAINING_REPRODUCTION,
            variant="molerec-default",
            artifact_bundle_sha256="c" * 64,
            bundle_equivalence_sha256="c" * 64,
            parent_h2=parent_h2,
            parent_packet=unstaged,
        )


def test_pinned_revisions_are_the_expected_sources() -> None:
    contract = _contract()
    assert contract.source_revision == SAFE_DRUG_MAIN_REVISION
