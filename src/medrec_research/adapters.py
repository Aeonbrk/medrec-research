"""Isolated JSON subprocess seam for external baseline adapters."""

from __future__ import annotations

import math
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ._validation import (
    canonical_json,
    parse_json_object,
    require_identifier,
    require_int,
    require_public_string,
    require_single_line_public_string,
    strict_fields,
)
from .errors import ProtocolValidationError
from .prediction import (
    ComparisonPredictionBatch,
    MedicationScore,
    PredictionRecord,
    TargetFreePrediction,
)

_REQUEST_TARGET_FIELDS = frozenset(
    {"ground_truth", "labels", "target_medications", "targets", "y_true"}
)
_REQUEST_SPLIT_MEMBERSHIP_FIELDS = frozenset(
    {"cohort_membership", "evaluation_visit_ids", "split", "split_membership", "test_visit_ids"}
)
_REQUEST_ALLOWED_FIELDS = frozenset({"dataset_id", "seed"})
_REQUEST_FORBIDDEN_FIELDS = _REQUEST_TARGET_FIELDS | _REQUEST_SPLIT_MEMBERSHIP_FIELDS
_OUTPUT_CORE_FIELDS = _REQUEST_TARGET_FIELDS | {"split"}


def _contains_key(value: object, forbidden: frozenset[str]) -> bool:
    if isinstance(value, Mapping):
        return any(
            (isinstance(key, str) and key in forbidden) or _contains_key(item, forbidden)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_key(item, forbidden) for item in value)
    return False


class AdapterError(RuntimeError):
    """Base error for external prediction adapters."""


class AdapterProcessError(AdapterError):
    """Raised when an adapter process exits unsuccessfully."""

    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        super().__init__(f"prediction adapter exited with status {returncode}")


class AdapterLaunchError(AdapterError):
    """Raised when an adapter command cannot be started."""


class AdapterTimeoutError(AdapterError):
    """Raised when an adapter exceeds its declared timeout."""


class AdapterProtocolError(AdapterError):
    """Raised when adapter output violates the JSON PredictionRecord protocol."""


@runtime_checkable
class PredictionAdapter(Protocol):
    """Model-independent prediction boundary."""

    def predict(
        self,
        request: Mapping[str, object],
        *,
        expected_records: Iterable[PredictionRecord],
        medication_vocabulary: Iterable[str],
    ) -> tuple[PredictionRecord, ...]:
        """Return complete prediction records for a JSON-compatible request."""


@dataclass(frozen=True, slots=True)
class ProcessPredictionAdapter:
    """Run a baseline adapter as one isolated command."""

    command: tuple[str, ...]
    timeout_seconds: float = 300.0

    def __post_init__(self) -> None:
        command = tuple(self.command)
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise ProtocolValidationError("adapter command must contain non-empty strings")
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise ProtocolValidationError("timeout_seconds must be greater than zero")
        timeout = float(self.timeout_seconds)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ProtocolValidationError("timeout_seconds must be greater than zero")
        object.__setattr__(self, "command", command)
        object.__setattr__(self, "timeout_seconds", timeout)

    def predict(
        self,
        request: Mapping[str, object],
        *,
        expected_records: Iterable[PredictionRecord],
        medication_vocabulary: Iterable[str],
    ) -> tuple[PredictionRecord, ...]:
        if not isinstance(request, Mapping):
            raise ProtocolValidationError("adapter request must be an object")
        if _contains_key(request, _REQUEST_FORBIDDEN_FIELDS):
            raise ProtocolValidationError(
                "adapter request must not contain core-owned target data or split membership"
            )
        unknown_request_fields = set(request) - _REQUEST_ALLOWED_FIELDS
        if unknown_request_fields:
            raise ProtocolValidationError(
                "adapter request must use only target-free request fields: dataset_id, seed"
            )
        adapter_request: dict[str, object] = {}
        if "dataset_id" in request:
            adapter_request["dataset_id"] = require_identifier(
                request["dataset_id"], field="adapter_request.dataset_id"
            )
        if "seed" in request:
            adapter_request["seed"] = require_int(request["seed"], field="adapter_request.seed")
        try:
            vocabulary = tuple(
                require_single_line_public_string(code, field="medication_vocabulary")
                for code in medication_vocabulary
            )
        except TypeError as error:
            raise ProtocolValidationError(
                "medication_vocabulary must be a collection of medication codes"
            ) from error
        if not vocabulary or len(vocabulary) != len(set(vocabulary)):
            raise ProtocolValidationError(
                "medication_vocabulary must contain unique medication codes"
            )
        vocabulary_set = set(vocabulary)
        try:
            expected = tuple(expected_records)
        except TypeError as error:
            raise ProtocolValidationError(
                "expected_records must be a collection of PredictionRecord objects"
            ) from error
        if not expected or any(not isinstance(record, PredictionRecord) for record in expected):
            raise ProtocolValidationError("expected_records must contain PredictionRecord objects")
        expected_by_key = {(record.patient_id, record.visit_id): record for record in expected}
        if len(expected_by_key) != len(expected):
            raise ProtocolValidationError("expected_records must contain unique visits")
        if any(not set(record.target_medications) <= vocabulary_set for record in expected):
            raise ProtocolValidationError(
                "expected_records contain medications outside medication_vocabulary"
            )
        input_text = canonical_json({"request": adapter_request, "schema_version": 1})
        try:
            completed = subprocess.run(
                self.command,
                input=f"{input_text}\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise AdapterTimeoutError(
                f"prediction adapter timed out after {self.timeout_seconds:g} seconds"
            ) from error
        except OSError as error:
            raise AdapterLaunchError("prediction adapter could not be started") from error
        if completed.returncode != 0:
            raise AdapterProcessError(completed.returncode)
        try:
            response = parse_json_object(completed.stdout, context="adapter output")
            payload = strict_fields(
                response,
                required=("schema_version", "predictions"),
                context="adapter output",
            )
        except ProtocolValidationError as error:
            raise AdapterProtocolError("adapter output must be valid JSON protocol data") from error
        if payload["schema_version"] != 1:
            raise AdapterProtocolError("adapter output schema_version must be 1")
        raw_predictions = payload["predictions"]
        if not isinstance(raw_predictions, list):
            raise AdapterProtocolError("adapter output predictions must be a list")
        wire_predictions: list[tuple[dict[str, object], tuple[MedicationScore, ...]]] = []
        try:
            for item in raw_predictions:
                if _contains_key(item, _OUTPUT_CORE_FIELDS):
                    raise AdapterProtocolError("adapter output must not contain core-owned fields")
                prediction = strict_fields(
                    item,
                    required=("patient_id", "visit_id", "predicted_medications"),
                    optional=("scores",),
                    context="adapter prediction",
                )
                prediction["patient_id"] = require_public_string(
                    prediction["patient_id"], field="patient_id"
                )
                prediction["visit_id"] = require_public_string(
                    prediction["visit_id"], field="visit_id"
                )
                predicted_medications = prediction["predicted_medications"]
                raw_scores = prediction.get("scores", [])
                if not isinstance(predicted_medications, list):
                    raise ProtocolValidationError("predicted_medications must be a list")
                if not isinstance(raw_scores, list):
                    raise ProtocolValidationError("scores must be a list")
                wire_predictions.append(
                    (
                        prediction,
                        tuple(MedicationScore.from_dict(score) for score in raw_scores),
                    )
                )
        except AdapterProtocolError:
            raise
        except ProtocolValidationError as error:
            raise AdapterProtocolError(
                "adapter output must contain complete prediction payloads"
            ) from error
        keys = {
            (prediction["patient_id"], prediction["visit_id"]) for prediction, _ in wire_predictions
        }
        if len(keys) != len(wire_predictions):
            raise AdapterProtocolError("adapter output must contain unique visit predictions")
        if keys != expected_by_key.keys():
            raise AdapterProtocolError("adapter output must match expected evaluation records")
        predictions: list[PredictionRecord] = []
        try:
            for prediction, scores in wire_predictions:
                key = (prediction["patient_id"], prediction["visit_id"])
                expected_record = expected_by_key[key]
                record = PredictionRecord(
                    patient_id=expected_record.patient_id,
                    visit_id=expected_record.visit_id,
                    split=expected_record.split,
                    target_medications=expected_record.target_medications,
                    predicted_medications=tuple(prediction["predicted_medications"]),
                    scores=scores,
                )
                if not set(record.predicted_medications) <= vocabulary_set:
                    raise AdapterProtocolError(
                        "adapter output contains medications outside declared medication vocabulary"
                    )
                predictions.append(record)
        except AdapterProtocolError:
            raise
        except (KeyError, ProtocolValidationError, TypeError) as error:
            raise AdapterProtocolError(
                "adapter output must contain complete prediction payloads"
            ) from error
        return tuple(sorted(predictions, key=lambda record: (record.patient_id, record.visit_id)))

    def predict_comparison(
        self,
        request: Mapping[str, object],
        *,
        method_id: str,
        expected_visits: Iterable[tuple[str, str]],
        medication_vocabulary: Iterable[str],
    ) -> ComparisonPredictionBatch:
        """Run schema v2 without exposing targets or split membership to the adapter."""

        if not isinstance(request, Mapping):
            raise ProtocolValidationError("adapter request must be an object")
        if _contains_key(request, _REQUEST_FORBIDDEN_FIELDS):
            raise ProtocolValidationError(
                "adapter request must not contain core-owned target data or split membership"
            )
        if set(request) - _REQUEST_ALLOWED_FIELDS:
            raise ProtocolValidationError(
                "adapter request must use only target-free request fields: dataset_id, seed"
            )
        normalized_method = require_identifier(method_id, field="method_id")
        adapter_request: dict[str, object] = {}
        if "dataset_id" in request:
            adapter_request["dataset_id"] = require_identifier(
                request["dataset_id"], field="adapter_request.dataset_id"
            )
        if "seed" in request:
            adapter_request["seed"] = require_int(request["seed"], field="adapter_request.seed")
        try:
            vocabulary = tuple(
                require_single_line_public_string(code, field="medication_vocabulary")
                for code in medication_vocabulary
            )
            visits = tuple(
                (
                    require_public_string(key[0], field="patient_id"),
                    require_public_string(key[1], field="visit_id"),
                )
                for key in expected_visits
            )
        except (IndexError, TypeError) as error:
            raise ProtocolValidationError(
                "expected_visits must contain patient_id and visit_id pairs"
            ) from error
        if not vocabulary or len(vocabulary) != len(set(vocabulary)):
            raise ProtocolValidationError(
                "medication_vocabulary must contain unique medication codes"
            )
        if not visits or len(visits) != len(set(visits)):
            raise ProtocolValidationError("expected_visits must contain unique visits")

        input_text = canonical_json({"request": adapter_request, "schema_version": 2})
        try:
            completed = subprocess.run(
                self.command,
                input=f"{input_text}\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise AdapterTimeoutError(
                f"prediction adapter timed out after {self.timeout_seconds:g} seconds"
            ) from error
        except OSError as error:
            raise AdapterLaunchError("prediction adapter could not be started") from error
        if completed.returncode != 0:
            raise AdapterProcessError(completed.returncode)

        try:
            response = parse_json_object(completed.stdout, context="adapter output")
            payload = strict_fields(
                response,
                required=("schema_version", "method_id", "predictions"),
                context="adapter output",
            )
            if payload["schema_version"] != 2:
                raise ProtocolValidationError("adapter output schema_version must be 2")
            if payload["method_id"] != normalized_method:
                raise ProtocolValidationError("adapter output method_id does not match request")
            raw_predictions = payload["predictions"]
            if not isinstance(raw_predictions, list):
                raise ProtocolValidationError("adapter output predictions must be a list")
            predictions: list[TargetFreePrediction] = []
            for item in raw_predictions:
                if _contains_key(item, _OUTPUT_CORE_FIELDS):
                    raise AdapterProtocolError("adapter output must not contain core-owned fields")
                prediction = strict_fields(
                    item,
                    required=(
                        "patient_id",
                        "visit_id",
                        "predicted_medications",
                        "vocabulary_scores",
                    ),
                    context="adapter prediction",
                )
                if not isinstance(prediction["predicted_medications"], list):
                    raise ProtocolValidationError("predicted_medications must be a list")
                if not isinstance(prediction["vocabulary_scores"], list):
                    raise ProtocolValidationError("vocabulary_scores must be a list")
                predictions.append(
                    TargetFreePrediction(
                        patient_id=prediction["patient_id"],
                        visit_id=prediction["visit_id"],
                        predicted_medications=tuple(prediction["predicted_medications"]),
                        vocabulary_scores=tuple(
                            MedicationScore.from_dict(score)
                            for score in prediction["vocabulary_scores"]
                        ),
                    )
                )
            batch = ComparisonPredictionBatch(
                method_id=normalized_method,
                medication_vocabulary=vocabulary,
                predictions=tuple(predictions),
            )
        except AdapterProtocolError:
            raise
        except ProtocolValidationError as error:
            raise AdapterProtocolError(str(error)) from error
        if set(batch.visit_keys) != set(visits):
            raise AdapterProtocolError("adapter output must match expected evaluation visits")
        return batch


__all__ = (
    "AdapterError",
    "AdapterLaunchError",
    "AdapterProcessError",
    "AdapterProtocolError",
    "AdapterTimeoutError",
    "PredictionAdapter",
    "ProcessPredictionAdapter",
)
