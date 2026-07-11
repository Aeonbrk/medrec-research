from __future__ import annotations

import pytest

from medrec_research import PredictionRecord, ProtocolValidationError


def test_prediction_record_round_trip_uses_canonical_targets() -> None:
    record = PredictionRecord(
        patient_id="synthetic-patient",
        visit_id="visit-1",
        split="test",
        target_medications=("RX_B", "RX_A"),
        predicted_medications=("RX_A", "RX_C"),
    )

    assert record.target_medications == ("RX_A", "RX_B")
    assert PredictionRecord.from_json(record.to_json()) == record


def test_prediction_record_rejects_duplicate_medication_codes() -> None:
    with pytest.raises(ProtocolValidationError, match=r"predicted_medications.*unique"):
        PredictionRecord(
            patient_id="synthetic-patient",
            visit_id="visit-1",
            split="test",
            target_medications=("RX_A",),
            predicted_medications=("RX_A", "RX_A"),
        )


def test_prediction_record_rejects_control_characters_in_medication_codes() -> None:
    with pytest.raises(ProtocolValidationError, match="control characters"):
        PredictionRecord(
            patient_id="synthetic-patient",
            visit_id="visit-1",
            split="test",
            target_medications=("RX_A\nRX_B",),
            predicted_medications=(),
        )


def test_prediction_record_rejects_surrounding_identifier_whitespace() -> None:
    with pytest.raises(ProtocolValidationError, match="surrounding whitespace"):
        PredictionRecord(
            patient_id=" synthetic-patient",
            visit_id="visit-1",
            split="test",
            target_medications=("RX_A",),
            predicted_medications=("RX_A",),
        )


def test_prediction_record_rejects_partial_payload() -> None:
    with pytest.raises(ProtocolValidationError, match="target_medications"):
        PredictionRecord.from_dict(
            {
                "schema_version": 1,
                "patient_id": "synthetic-patient",
                "visit_id": "visit-1",
                "split": "test",
                "predicted_medications": ["RX_A"],
            }
        )


def test_score_factory_breaks_ties_by_medication_code() -> None:
    record = PredictionRecord.from_scores(
        patient_id="synthetic-patient",
        visit_id="visit-1",
        split="test",
        target_medications=("RX_A",),
        medication_scores={"RX_B": 0.8, "RX_C": 0.2, "RX_A": 0.8},
        max_medications=2,
    )

    assert record.predicted_medications == ("RX_A", "RX_B")
    assert tuple(score.medication_code for score in record.scores) == ("RX_A", "RX_B")
