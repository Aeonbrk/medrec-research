from __future__ import annotations

import sys

import pytest

from medrec_research import (
    AdapterProcessError,
    AdapterProtocolError,
    AdapterTimeoutError,
    ProcessPredictionAdapter,
    ProtocolValidationError,
)


def _command(source: str) -> tuple[str, ...]:
    return (sys.executable, "-c", source)


def _wire_comparison_prediction() -> dict[str, object]:
    return {
        "patient_id": "synthetic-patient",
        "visit_id": "visit-1",
        "predicted_medications": ["RX_A"],
        "vocabulary_scores": [
            {"medication_code": "RX_A", "score": 0.9},
            {"medication_code": "RX_B", "score": 0.1},
        ],
    }


def test_process_adapter_parses_target_free_comparison_scores() -> None:
    response = {
        "schema_version": 2,
        "method_id": "retain",
        "predictions": [_wire_comparison_prediction()],
    }
    source = (
        "import json, sys; request = json.load(sys.stdin); "
        "assert request['schema_version'] == 2; "
        "assert 'RX_A' not in json.dumps(request); "
        f"json.dump({response!r}, sys.stdout)"
    )

    batch = ProcessPredictionAdapter(_command(source)).predict_comparison(
        {"dataset_id": "synthetic-medrec"},
        method_id="retain",
        expected_visits=(("synthetic-patient", "visit-1"),),
        medication_vocabulary=("RX_A", "RX_B"),
    )

    assert batch.predictions[0].predicted_medications == ("RX_A",)
    assert tuple(item.score for item in batch.predictions[0].vocabulary_scores) == (0.9, 0.1)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("print('not-json')", "valid JSON"),
        (
            "import json; json.dump({'schema_version': 2, 'method_id': 'retain', 'predictions': [{}]}, "
            "__import__('sys').stdout)",
            "required",
        ),
        (
            "import json; json.dump({'schema_version': 1, 'method_id': 'retain', 'predictions': []}, "
            "__import__('sys').stdout)",
            "schema_version must be 2",
        ),
        (
            "import json; json.dump({'schema_version': 2, 'method_id': 'other', 'predictions': []}, "
            "__import__('sys').stdout)",
            "method_id does not match",
        ),
    ],
)
def test_process_adapter_rejects_malformed_or_partial_output(source: str, message: str) -> None:
    with pytest.raises(AdapterProtocolError, match=message):
        ProcessPredictionAdapter(_command(source)).predict_comparison(
            {},
            method_id="retain",
            expected_visits=(("synthetic-patient", "visit-1"),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


@pytest.mark.parametrize("case", ["missing", "extra"])
def test_process_adapter_rejects_incomplete_or_changed_evaluation_cohort(case: str) -> None:
    expected = _wire_comparison_prediction()
    if case == "missing":
        predictions: list[dict[str, object]] = []
    else:
        extra = {**expected, "visit_id": "visit-2"}
        predictions = [expected, extra]
    response = {
        "schema_version": 2,
        "method_id": "retain",
        "predictions": predictions,
    }
    source = f"import json, sys; json.load(sys.stdin); json.dump({response!r}, sys.stdout)"

    with pytest.raises(AdapterProtocolError, match=r"expected evaluation visits|must not be empty"):
        ProcessPredictionAdapter(_command(source)).predict_comparison(
            {},
            method_id="retain",
            expected_visits=(("synthetic-patient", "visit-1"),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


def test_process_adapter_rejects_comparison_score_order_drift() -> None:
    response = {
        "schema_version": 2,
        "method_id": "retain",
        "predictions": [
            {
                "patient_id": "synthetic-patient",
                "visit_id": "visit-1",
                "predicted_medications": ["RX_A"],
                "vocabulary_scores": [
                    {"medication_code": "RX_B", "score": 0.1},
                    {"medication_code": "RX_A", "score": 0.9},
                ],
            }
        ],
    }
    source = f"import json, sys; json.load(sys.stdin); json.dump({response!r}, sys.stdout)"

    with pytest.raises(AdapterProtocolError, match="declared medication vocabulary order"):
        ProcessPredictionAdapter(_command(source)).predict_comparison(
            {},
            method_id="retain",
            expected_visits=(("synthetic-patient", "visit-1"),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


@pytest.mark.parametrize("field", ["split", "target_medications", "labels", "y_true"])
def test_process_adapter_rejects_core_owned_output_fields(field: str) -> None:
    changed = {**_wire_comparison_prediction(), field: ["RX_A"]}
    response = {
        "schema_version": 2,
        "method_id": "retain",
        "predictions": [changed],
    }
    source = f"import json, sys; json.load(sys.stdin); json.dump({response!r}, sys.stdout)"

    with pytest.raises(AdapterProtocolError, match="core-owned fields"):
        ProcessPredictionAdapter(_command(source)).predict_comparison(
            {},
            method_id="retain",
            expected_visits=(("synthetic-patient", "visit-1"),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


def test_process_adapter_rejects_target_bearing_request() -> None:
    with pytest.raises(ProtocolValidationError, match="core-owned target data"):
        ProcessPredictionAdapter(_command("raise SystemExit(99)")).predict_comparison(
            {"nested": {"target_medications": ["RX_A"]}},
            method_id="retain",
            expected_visits=(("synthetic-patient", "visit-1"),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


@pytest.mark.parametrize(
    "adapter_request",
    [
        {"split": "test"},
        {"nested": {"split": "test"}},
        {"test_visit_ids": ["visit-1"]},
    ],
)
def test_process_adapter_rejects_split_bearing_request(adapter_request: dict[str, object]) -> None:
    with pytest.raises(ProtocolValidationError, match="split membership"):
        ProcessPredictionAdapter(_command("raise SystemExit(99)")).predict_comparison(
            adapter_request,
            method_id="retain",
            expected_visits=(("synthetic-patient", "visit-1"),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


def test_process_adapter_rejects_request_fields_outside_the_target_free_schema() -> None:
    with pytest.raises(ProtocolValidationError, match="target-free request fields"):
        ProcessPredictionAdapter(_command("raise SystemExit(99)")).predict_comparison(
            {"nested": {"dataset_id": "synthetic-medrec"}},
            method_id="retain",
            expected_visits=(("synthetic-patient", "visit-1"),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


def test_process_adapter_reports_nonzero_exit_without_echoing_private_stderr() -> None:
    adapter = ProcessPredictionAdapter(
        _command("import sys; print('/private/patient/path', file=sys.stderr); raise SystemExit(7)")
    )

    with pytest.raises(AdapterProcessError, match="status 7") as caught:
        adapter.predict_comparison(
            {},
            method_id="retain",
            expected_visits=(("synthetic-patient", "visit-1"),),
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
        adapter.predict_comparison(
            {},
            method_id="retain",
            expected_visits=(("synthetic-patient", "visit-1"),),
            medication_vocabulary=("RX_A", "RX_B"),
        )


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), 0, -1.0, "300"])
def test_process_adapter_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ProtocolValidationError, match="greater than zero"):
        ProcessPredictionAdapter(_command("pass"), timeout_seconds=timeout)


@pytest.mark.parametrize("cmd", [(), ("",), ("valid", "")])
def test_process_adapter_rejects_invalid_command(cmd: tuple[str, ...]) -> None:
    with pytest.raises(ProtocolValidationError, match="command must contain non-empty strings"):
        ProcessPredictionAdapter(cmd)
