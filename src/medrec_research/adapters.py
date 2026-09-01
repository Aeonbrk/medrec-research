"""Isolated JSON subprocess seam for external baseline adapters."""

from __future__ import annotations

import math
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

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
        visit_set = set(visits)
        if not visits or len(visits) != len(visit_set):
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
        if set(batch.visit_keys) != visit_set:
            raise AdapterProtocolError("adapter output must match expected evaluation visits")
        return batch


__all__ = (
    "AdapterError",
    "AdapterLaunchError",
    "AdapterProcessError",
    "AdapterProtocolError",
    "AdapterTimeoutError",
    "ProcessPredictionAdapter",
)
