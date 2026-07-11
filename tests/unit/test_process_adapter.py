from __future__ import annotations

import sys

import pytest

from medrec_research import (
    AdapterProcessError,
    AdapterProtocolError,
    AdapterTimeoutError,
    PredictionAdapter,
    PredictionRecord,
    ProcessPredictionAdapter,
    ProtocolValidationError,
)


def _command(source: str) -> tuple[str, ...]:
    return (sys.executable, "-c", source)


def _wire_prediction_payload() -> dict[str, object]:
    return {
        "patient_id": "synthetic-patient",
        "visit_id": "visit-1",
        "predicted_medications": ["RX_A"],
    }


def _expected_record() -> PredictionRecord:
    return PredictionRecord(
        patient_id="synthetic-patient",
        visit_id="visit-1",
        split="test",
        target_medications=("RX_A",),
        predicted_medications=(),
    )


def test_process_adapter_implements_protocol_and_parses_complete_records() -> None:
    response = {
        "schema_version": 1,
        "predictions": [_wire_prediction_payload()],
    }
    source = f"import json, sys; json.load(sys.stdin); json.dump({response!r}, sys.stdout)"
    adapter = ProcessPredictionAdapter(_command(source))

    records = adapter.predict(
        {"dataset_id": "synthetic-medrec", "split": "test"},
        expected_records=(_expected_record(),),
        medication_vocabulary=("RX_A", "RX_B"),
    )

    assert isinstance(adapter, PredictionAdapter)
    assert records[0].predicted_medications == ("RX_A",)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("print('not-json')", "valid JSON"),
        (
            "import json; json.dump({'schema_version': 1, 'predictions': [{}]}, "
            "__import__('sys').stdout)",
            "complete prediction payload",
        ),
    ],
)
def test_process_adapter_rejects_malformed_or_partial_output(source: str, message: str) -> None:
    with pytest.raises(AdapterProtocolError, match=message):
        ProcessPredictionAdapter(_command(source)).predict(
            {},
            expected_records=(_expected_record(),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


@pytest.mark.parametrize("case", ["missing", "extra"])
def test_process_adapter_rejects_incomplete_or_changed_evaluation_cohort(case: str) -> None:
    expected = _wire_prediction_payload()
    if case == "missing":
        predictions: list[dict[str, object]] = []
    else:
        extra = {**expected, "visit_id": "visit-2"}
        predictions = [expected, extra]
    response = {"schema_version": 1, "predictions": predictions}
    source = f"import json, sys; json.load(sys.stdin); json.dump({response!r}, sys.stdout)"

    with pytest.raises(AdapterProtocolError, match="expected evaluation records"):
        ProcessPredictionAdapter(_command(source)).predict(
            {},
            expected_records=(_expected_record(),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


def test_process_adapter_rejects_medications_outside_declared_vocabulary() -> None:
    changed = {**_wire_prediction_payload(), "predicted_medications": ["RX_Z"]}
    response = {"schema_version": 1, "predictions": [changed]}
    source = f"import json, sys; json.load(sys.stdin); json.dump({response!r}, sys.stdout)"

    with pytest.raises(AdapterProtocolError, match="declared medication vocabulary"):
        ProcessPredictionAdapter(_command(source)).predict(
            {},
            expected_records=(_expected_record(),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


@pytest.mark.parametrize("field", ["split", "target_medications", "labels", "y_true"])
def test_process_adapter_rejects_core_owned_output_fields(field: str) -> None:
    changed = {**_wire_prediction_payload(), field: ["RX_A"]}
    response = {"schema_version": 1, "predictions": [changed]}
    source = f"import json, sys; json.load(sys.stdin); json.dump({response!r}, sys.stdout)"

    with pytest.raises(AdapterProtocolError, match="core-owned fields"):
        ProcessPredictionAdapter(_command(source)).predict(
            {},
            expected_records=(_expected_record(),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


def test_process_adapter_rejects_target_bearing_request() -> None:
    with pytest.raises(ProtocolValidationError, match="core-owned target data"):
        ProcessPredictionAdapter(_command("raise SystemExit(99)")).predict(
            {"nested": {"target_medications": ["RX_A"]}},
            expected_records=(_expected_record(),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


def test_process_adapter_keeps_expected_targets_out_of_subprocess_input() -> None:
    response = {"schema_version": 1, "predictions": [_wire_prediction_payload()]}
    source = (
        "import json, sys; request = json.load(sys.stdin); "
        "assert 'RX_A' not in json.dumps(request); "
        f"json.dump({response!r}, sys.stdout)"
    )

    records = ProcessPredictionAdapter(_command(source)).predict(
        {"dataset_id": "synthetic-medrec", "split": "test"},
        expected_records=(_expected_record(),),
        medication_vocabulary=("RX_A", "RX_B"),
    )

    assert records[0].target_medications == ("RX_A",)


def test_process_adapter_reports_nonzero_exit_without_echoing_private_stderr() -> None:
    adapter = ProcessPredictionAdapter(
        _command("import sys; print('/private/patient/path', file=sys.stderr); raise SystemExit(7)")
    )

    with pytest.raises(AdapterProcessError, match="status 7") as caught:
        adapter.predict(
            {},
            expected_records=(_expected_record(),),
            medication_vocabulary=("RX_A", "RX_B"),
        )

    assert caught.value.returncode == 7
    assert "/private/patient/path" not in str(caught.value)


def test_process_adapter_times_out() -> None:
    adapter = ProcessPredictionAdapter(
        _command("import time; time.sleep(1)"),
        timeout_seconds=0.01,
    )

    with pytest.raises(AdapterTimeoutError, match="timed out"):
        adapter.predict(
            {},
            expected_records=(_expected_record(),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


@pytest.mark.parametrize("timeout", [float("nan"), float("inf")])
def test_process_adapter_rejects_nonfinite_timeout(timeout: float) -> None:
    with pytest.raises(ProtocolValidationError, match="greater than zero"):
        ProcessPredictionAdapter(_command("pass"), timeout_seconds=timeout)
