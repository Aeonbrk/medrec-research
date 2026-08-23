from __future__ import annotations

import pytest

from medrec_research import (
    AdaptationBudget,
    ComparisonProtocolV1_1,
    ComparisonScope,
    DecoderClass,
    DecoderProfile,
    IndependentEvaluationInput,
    ProtocolValidationError,
    ThresholdSelectionRule,
)
from medrec_research.comparison_protocol import SAFE_DRUG_ARCHIVED_REVISION


def _budget() -> AdaptationBudget:
    return AdaptationBudget(
        selection_metric="f1",
        max_trials=2,
        max_compute_units=8,
        stopping_rule="validation plateau",
        seed_policy="pinned-source-seed",
        trials_used=1,
        compute_units_used=4,
    )


def _score_profile() -> DecoderProfile:
    return DecoderProfile(
        method_id="retain",
        decoder_class=DecoderClass.SCORE_THRESHOLD,
        baseline_core_sha256="a" * 64,
        threshold_rule=ThresholdSelectionRule(
            selection_metric="f1",
            max_trials=2,
            trials_used=1,
        ),
    )


def _structural_profile() -> DecoderProfile:
    return DecoderProfile(
        method_id="gamenet",
        decoder_class=DecoderClass.STRUCTURAL_SEQUENCE,
        baseline_core_sha256="b" * 64,
        native_decoder="stop-token",
    )


def _protocol() -> ComparisonProtocolV1_1:
    return ComparisonProtocolV1_1(
        adaptation_budget=_budget(),
        decoder_profiles=(_score_profile(), _structural_profile()),
    )


def test_v1_1_protocol_and_profiles_round_trip() -> None:
    protocol = _protocol()
    restored = ComparisonProtocolV1_1.from_json(protocol.to_json())
    assert restored == protocol
    assert protocol.protocol_sha256 == restored.protocol_sha256
    assert protocol.profile_for("retain").decoder_class is DecoderClass.SCORE_THRESHOLD
    assert protocol.profile_for("gamenet").decoder_class is DecoderClass.STRUCTURAL_SEQUENCE

    scope = ComparisonScope(
        protocol_version="1.1",
        dataset_manifest_sha256="d" * 64,
        adaptation_budget_sha256=protocol.adaptation_budget.budget_sha256,
        protocol_amendment_sha256=protocol.protocol_sha256,
        method_profile_sha256=protocol.profile_for("retain").profile_sha256,
    )
    assert ComparisonScope.from_dict(scope.to_dict()) == scope
    assert scope.matches(
        protocol_version="1.1",
        dataset_manifest_sha256="d" * 64,
        adaptation_budget_sha256=protocol.adaptation_budget.budget_sha256,
        protocol_amendment_sha256=protocol.protocol_sha256,
        method_profile_sha256=protocol.profile_for("retain").profile_sha256,
    )
    assert not scope.matches(
        protocol_version="1.1",
        dataset_manifest_sha256="d" * 64,
        adaptation_budget_sha256=protocol.adaptation_budget.budget_sha256,
    )


def test_score_threshold_selection_is_validation_only_and_bounded() -> None:
    with pytest.raises(ProtocolValidationError, match="validation"):
        ThresholdSelectionRule(selection_split="test")
    with pytest.raises(ProtocolValidationError, match="validation"):
        ThresholdSelectionRule(test_peeking=True)
    with pytest.raises(ProtocolValidationError, match="exceeds"):
        ThresholdSelectionRule(max_trials=1, trials_used=2)
    with pytest.raises(ProtocolValidationError, match="exhausted"):
        AdaptationBudget(max_trials=1, max_compute_units=1, trials_used=2)


def test_structural_decoder_cannot_be_mutated_into_threshold_selection() -> None:
    with pytest.raises(ProtocolValidationError, match="must not select"):
        DecoderProfile(
            method_id="gamenet",
            decoder_class=DecoderClass.STRUCTURAL_SEQUENCE,
            baseline_core_sha256="c" * 64,
            native_decoder="stop-token",
            threshold_rule=ThresholdSelectionRule(),
        )


def test_decoder_profile_rejects_non_archived_lineage() -> None:
    with pytest.raises(ProtocolValidationError, match="archived comparison lineage"):
        DecoderProfile(
            method_id="gamenet",
            decoder_class=DecoderClass.STRUCTURAL_SEQUENCE,
            baseline_core_sha256="b" * 64,
            data_lineage_revision="c7218d0976e5ee5588aeaf5bdbc86b338126bba5",
            native_decoder="stop-token",
        )


def test_independent_evaluation_requires_complete_target_free_coverage() -> None:
    protocol = _protocol()
    profile = protocol.profile_for("retain")
    evidence = IndependentEvaluationInput(
        method_id="retain",
        expected_visit_digest="1" * 64,
        prediction_visit_digest="1" * 64,
        target_join_digest="2" * 64,
    )
    protocol.validate_evaluation(profile, evidence)
    assert evidence.is_independently_evaluable
    with pytest.raises(ProtocolValidationError, match="complete"):
        IndependentEvaluationInput(
            method_id="retain",
            expected_visit_digest="1" * 64,
            prediction_visit_digest="0" * 64,
            target_join_digest="2" * 64,
            complete=False,
        )


def test_comparison_protocol_uses_the_safe_drug_archived_lineage() -> None:
    assert _protocol().data_lineage_revision == SAFE_DRUG_ARCHIVED_REVISION
