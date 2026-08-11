from __future__ import annotations

import pytest

from medrec_research import (
    DecisionPacket,
    H2Action,
    H2Decision,
    MoleRecArtifactBundle,
    MoleRecStageContract,
    ProtocolValidationError,
    Stage,
)
from medrec_research.reproduction_contract import REQUIRED_OUTCOMES


def _bundle() -> MoleRecArtifactBundle:
    return MoleRecArtifactBundle.create(
        variant="molerec-default",
        checkpoint_sha256="a" * 64,
        vocabulary_sha256="b" * 64,
        preprocessing_sha256="c" * 64,
        ddi_sha256="d" * 64,
        brics_sha256="e" * 64,
    )


def _packet(contract_sha256: str, stage: Stage) -> DecisionPacket:
    from medrec_research import AttemptRecord

    attempt = AttemptRecord(
        attempt_id=f"{stage.value}-attempt",
        lane_id=f"{stage.value}-lane",
        contract_sha256=contract_sha256,
        outcomes={metric: 0.5 for metric in REQUIRED_OUTCOMES},
        uncertainty={metric: [0.4, 0.6] for metric in REQUIRED_OUTCOMES},
    )
    return DecisionPacket(
        packet_id=f"{stage.value}-packet",
        contract_sha256=contract_sha256,
        lane_id=f"{stage.value}-lane",
        attempts=(attempt,),
        conclusion="accepted",
        validity="usable",
        outcomes={metric: 0.5 for metric in REQUIRED_OUTCOMES},
        uncertainty={metric: [0.4, 0.6] for metric in REQUIRED_OUTCOMES},
        stage=stage,
    )


def test_molerec_bundle_round_trip_and_exact_digest() -> None:
    bundle = _bundle()
    assert MoleRecArtifactBundle.from_json(bundle.to_json()) == bundle
    assert bundle.is_current()
    assert bundle.vocabulary_sha256 == "b" * 64
    assert bundle.preprocessing_sha256 == "c" * 64

    with pytest.raises(ProtocolValidationError, match="artifact identity"):
        MoleRecArtifactBundle(
            variant=bundle.variant,
            checkpoint_sha256="f" * 64,
            vocabulary_order_sha256=bundle.vocabulary_order_sha256,
            preprocessing_artifact_sha256=bundle.preprocessing_artifact_sha256,
            ddi_artifact_sha256=bundle.ddi_artifact_sha256,
            brics_artifact_sha256=bundle.brics_artifact_sha256,
            bundle_sha256=bundle.bundle_sha256,
        )


def test_checkpoint_replay_binds_bundle_and_training_requires_equivalence() -> None:
    bundle = _bundle()
    replay = MoleRecStageContract.create(
        stage=Stage.CHECKPOINT_REPLAY,
        variant=bundle.variant,
        artifact_bundle_sha256=bundle.bundle_sha256,
        artifact_bundle=bundle,
    )
    assert MoleRecStageContract.from_json(replay.to_json()) == replay
    replay_packet = _packet(replay.contract_sha256, Stage.CHECKPOINT_REPLAY)
    replay_h2 = H2Decision.create(
        contract=replay,
        packet=replay_packet,
        researcher="research-owner",
        action=H2Action.GO,
        contract_family="molerec-reproduction",
        source_revision=replay.source_revision,
        research_target=replay.research_target,
    )
    training = MoleRecStageContract.create(
        stage=Stage.TRAINING_REPRODUCTION,
        variant=bundle.variant,
        artifact_bundle_sha256=bundle.bundle_sha256,
        artifact_bundle=bundle,
        parent_h2=replay_h2,
        parent_packet=replay_packet,
    )
    assert training.bundle_equivalence_sha256 == bundle.bundle_sha256

    with pytest.raises(ProtocolValidationError, match="bundle digest"):
        MoleRecStageContract.create(
            stage=Stage.CHECKPOINT_REPLAY,
            variant=bundle.variant,
            artifact_bundle_sha256="f" * 64,
            artifact_bundle=bundle,
        )


def test_comparison_stage_requires_a_new_scope_and_protocol_identity() -> None:
    bundle = _bundle()
    replay = MoleRecStageContract.create(
        stage=Stage.CHECKPOINT_REPLAY,
        variant=bundle.variant,
        artifact_bundle_sha256=bundle.bundle_sha256,
        artifact_bundle=bundle,
    )
    replay_packet = _packet(replay.contract_sha256, Stage.CHECKPOINT_REPLAY)
    replay_h2 = H2Decision.create(
        contract=replay,
        packet=replay_packet,
        researcher="research-owner",
        action=H2Action.GO,
        contract_family="molerec-reproduction",
        source_revision=replay.source_revision,
        research_target=replay.research_target,
    )
    training = MoleRecStageContract.create(
        stage=Stage.TRAINING_REPRODUCTION,
        variant=bundle.variant,
        artifact_bundle_sha256=bundle.bundle_sha256,
        artifact_bundle=bundle,
        parent_h2=replay_h2,
        parent_packet=replay_packet,
    )
    training_packet = _packet(training.contract_sha256, Stage.TRAINING_REPRODUCTION)
    training_h2 = H2Decision.create(
        contract=training,
        packet=training_packet,
        researcher="research-owner",
        action=H2Action.GO,
        contract_family="molerec-reproduction",
        source_revision=training.source_revision,
        research_target=training.research_target,
    )
    comparison = MoleRecStageContract.create(
        stage=Stage.COMPARISON_QUALIFICATION,
        variant=bundle.variant,
        artifact_bundle_sha256=bundle.bundle_sha256,
        artifact_bundle=bundle,
        parent_h2=training_h2,
        parent_packet=training_packet,
        comparison_scope_sha256="1" * 64,
        comparison_protocol_sha256="2" * 64,
    )
    assert comparison.comparison_protocol_sha256 == "2" * 64

    with pytest.raises(ProtocolValidationError, match="scope and protocol"):
        MoleRecStageContract.create(
            stage=Stage.COMPARISON_QUALIFICATION,
            variant=bundle.variant,
            artifact_bundle_sha256=bundle.bundle_sha256,
            artifact_bundle=bundle,
            parent_h2=training_h2,
            parent_packet=training_packet,
        )
