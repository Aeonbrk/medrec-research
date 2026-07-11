"""Unified visit-macro medication-set evaluation."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from ._validation import require_int, require_probability, strict_fields
from .dataset import SplitName
from .errors import ProtocolValidationError
from .prediction import PredictionRecord


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Aggregate visit-macro metrics with no patient-level content."""

    visit_count: int
    jaccard: float
    precision: float
    recall: float
    f1: float
    mean_medication_count: float

    def __post_init__(self) -> None:
        require_int(self.visit_count, field="visit_count", minimum=1)
        for field in ("jaccard", "precision", "recall", "f1"):
            object.__setattr__(
                self,
                field,
                require_probability(getattr(self, field), field=field),
            )
        if isinstance(self.mean_medication_count, bool) or not isinstance(
            self.mean_medication_count, (int, float)
        ):
            raise ProtocolValidationError("mean_medication_count must be a finite number >= 0")
        mean_count = float(self.mean_medication_count)
        if not math.isfinite(mean_count) or mean_count < 0:
            raise ProtocolValidationError("mean_medication_count must be a finite number >= 0")
        object.__setattr__(self, "mean_medication_count", mean_count)

    def to_dict(self) -> dict[str, object]:
        return {
            "f1": self.f1,
            "jaccard": self.jaccard,
            "mean_medication_count": self.mean_medication_count,
            "precision": self.precision,
            "recall": self.recall,
            "visit_count": self.visit_count,
        }

    @classmethod
    def from_dict(cls, value: object) -> EvaluationResult:
        payload = strict_fields(
            value,
            required=(
                "visit_count",
                "jaccard",
                "precision",
                "recall",
                "f1",
                "mean_medication_count",
            ),
            context="EvaluationResult",
        )
        return cls(
            visit_count=payload["visit_count"],
            jaccard=payload["jaccard"],
            precision=payload["precision"],
            recall=payload["recall"],
            f1=payload["f1"],
            mean_medication_count=payload["mean_medication_count"],
        )


def _visit_metrics(record: PredictionRecord) -> tuple[float, float, float, float]:
    target = set(record.target_medications)
    predicted = set(record.predicted_medications)
    if not target and not predicted:
        return (1.0, 1.0, 1.0, 1.0)
    if not target or not predicted:
        return (0.0, 0.0, 0.0, 0.0)
    intersection = len(target & predicted)
    precision = intersection / len(predicted)
    recall = intersection / len(target)
    f1 = 0.0 if precision + recall == 0.0 else 2 * precision * recall / (precision + recall)
    return (intersection / len(target | predicted), precision, recall, f1)


def evaluate_predictions(records: Iterable[PredictionRecord]) -> EvaluationResult:
    """Evaluate test predictions using visit-level macro averaging."""

    predictions = tuple(records)
    if not predictions:
        raise ProtocolValidationError("evaluation requires at least one PredictionRecord")
    if any(record.split is not SplitName.TEST for record in predictions):
        raise ProtocolValidationError("evaluation accepts only test split PredictionRecords")
    visit_keys = {(record.patient_id, record.visit_id) for record in predictions}
    if len(visit_keys) != len(predictions):
        raise ProtocolValidationError("evaluation requires unique patient_id and visit_id pairs")
    totals = [0.0, 0.0, 0.0, 0.0]
    medication_count = 0
    for record in predictions:
        for index, metric in enumerate(_visit_metrics(record)):
            totals[index] += metric
        medication_count += len(record.predicted_medications)
    count = len(predictions)
    return EvaluationResult(
        visit_count=count,
        jaccard=totals[0] / count,
        precision=totals[1] / count,
        recall=totals[2] / count,
        f1=totals[3] / count,
        mean_medication_count=medication_count / count,
    )


__all__ = ("EvaluationResult", "evaluate_predictions")
