"""Unified visit-macro medication-set evaluation."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

from ._validation import (
    content_sha256,
    require_int,
    require_probability,
    require_public_string,
    strict_fields,
)
from .comparison_protocol import REQUIRED_OUTCOMES, IndependentEvaluationInput
from .dataset import DatasetManifest, SplitName
from .errors import ProtocolValidationError
from .prediction import ComparisonPredictionBatch, PredictionRecord


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


@dataclass(frozen=True, slots=True)
class JoinedComparisonBatch:
    """Core-owned target join paired with the untouched score surfaces."""

    predictions: ComparisonPredictionBatch
    records: tuple[PredictionRecord, ...]
    evaluation_input: IndependentEvaluationInput

    def __post_init__(self) -> None:
        if not isinstance(self.predictions, ComparisonPredictionBatch):
            raise ProtocolValidationError("predictions must be a ComparisonPredictionBatch")
        records = tuple(self.records)
        if not records or any(not isinstance(record, PredictionRecord) for record in records):
            raise ProtocolValidationError("joined comparison records must be PredictionRecords")
        record_keys = tuple((record.patient_id, record.visit_id) for record in records)
        if record_keys != self.predictions.visit_keys:
            raise ProtocolValidationError("joined records must align with target-free predictions")
        if self.evaluation_input.method_id != self.predictions.method_id:
            raise ProtocolValidationError("evaluation input method must match predictions")
        object.__setattr__(self, "records", records)


@dataclass(frozen=True, slots=True)
class ComparisonOutcomes:
    """The five fixed Comparison Protocol v1.1 outcomes."""

    ddi_rate: float
    jaccard: float
    f1: float
    prauc: float
    average_medication_count: float

    def __post_init__(self) -> None:
        for field in ("ddi_rate", "jaccard", "f1", "prauc"):
            object.__setattr__(
                self,
                field,
                require_probability(getattr(self, field), field=field),
            )
        value = self.average_medication_count
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ProtocolValidationError("average_medication_count must be a finite number >= 0")
        normalized = float(value)
        if not math.isfinite(normalized) or normalized < 0:
            raise ProtocolValidationError("average_medication_count must be a finite number >= 0")
        object.__setattr__(self, "average_medication_count", normalized)

    def to_dict(self) -> dict[str, float]:
        return {name: getattr(self, name) for name in REQUIRED_OUTCOMES}


@dataclass(frozen=True, slots=True)
class OutcomeInterval:
    """One 80% percentile interval."""

    lower: float
    upper: float

    def __post_init__(self) -> None:
        for field in ("lower", "upper"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ProtocolValidationError("outcome interval bounds must be finite numbers")
            normalized = float(value)
            if not math.isfinite(normalized):
                raise ProtocolValidationError("outcome interval bounds must be finite numbers")
            object.__setattr__(self, field, normalized)
        if self.lower > self.upper:
            raise ProtocolValidationError("outcome interval lower bound exceeds upper bound")

    def to_dict(self) -> dict[str, float]:
        return {"lower": self.lower, "upper": self.upper}


@dataclass(frozen=True, slots=True)
class ComparisonEvaluationResult:
    """Point estimates and the frozen ten bootstrap rounds."""

    point: ComparisonOutcomes
    rounds: tuple[ComparisonOutcomes, ...]
    intervals: tuple[tuple[str, OutcomeInterval], ...]
    bootstrap_seed: int

    def __post_init__(self) -> None:
        require_int(self.bootstrap_seed, field="bootstrap_seed")
        rounds = tuple(self.rounds)
        if len(rounds) != 10 or any(not isinstance(item, ComparisonOutcomes) for item in rounds):
            raise ProtocolValidationError("comparison evaluation requires exactly ten rounds")
        intervals = tuple(self.intervals)
        if tuple(name for name, _ in intervals) != REQUIRED_OUTCOMES:
            raise ProtocolValidationError("comparison intervals must cover the five fixed outcomes")
        if any(not isinstance(interval, OutcomeInterval) for _, interval in intervals):
            raise ProtocolValidationError(
                "comparison intervals must contain OutcomeInterval values"
            )
        object.__setattr__(self, "rounds", rounds)
        object.__setattr__(self, "intervals", intervals)

    def interval(self, outcome: str) -> OutcomeInterval:
        return dict(self.intervals)[outcome]

    def to_dict(self) -> dict[str, object]:
        return {
            "bootstrap_seed": self.bootstrap_seed,
            "interval_level": 0.8,
            "intervals": {name: interval.to_dict() for name, interval in self.intervals},
            "point": self.point.to_dict(),
            "rounds": [item.to_dict() for item in self.rounds],
        }


def _vocabulary_digest(vocabulary: tuple[str, ...]) -> str:
    serialized = "".join(f"{code}\n" for code in sorted(vocabulary))
    return sha256(serialized.encode("utf-8")).hexdigest()


def join_comparison_targets(
    predictions: ComparisonPredictionBatch,
    *,
    targets: Mapping[tuple[str, str], Iterable[str]],
    dataset_manifest: DatasetManifest,
    membership_hmac_key: bytes | None = None,
) -> JoinedComparisonBatch:
    """Verify the frozen cohort, then join targets inside the protocol core."""

    if not isinstance(predictions, ComparisonPredictionBatch):
        raise ProtocolValidationError("predictions must be a ComparisonPredictionBatch")
    if not isinstance(dataset_manifest, DatasetManifest):
        raise ProtocolValidationError("dataset_manifest must be a DatasetManifest")
    if not isinstance(targets, Mapping):
        raise ProtocolValidationError("targets must map visit keys to medication codes")
    normalized_targets: dict[tuple[str, str], tuple[str, ...]] = {}
    try:
        for raw_key, medications in targets.items():
            if not isinstance(raw_key, (list, tuple)) or len(raw_key) != 2:
                raise ProtocolValidationError("target keys must contain patient_id and visit_id")
            key = (
                require_public_string(raw_key[0], field="patient_id"),
                require_public_string(raw_key[1], field="visit_id"),
            )
            values = tuple(
                require_public_string(code, field="target_medications") for code in medications
            )
            if len(values) != len(set(values)):
                raise ProtocolValidationError("target medication codes must be unique")
            normalized_targets[key] = tuple(sorted(values))
    except TypeError as error:
        raise ProtocolValidationError(
            "targets must map visit keys to medication-code collections"
        ) from error
    verified_visit_digest = dataset_manifest.verify_evaluation_visits(
        normalized_targets,
        membership_hmac_key=membership_hmac_key,
    )
    target_keys = set(normalized_targets)
    if set(predictions.visit_keys) != target_keys:
        raise ProtocolValidationError("predictions must cover the exact eligible test visits")
    if _vocabulary_digest(predictions.medication_vocabulary) != (
        dataset_manifest.medication_vocabulary_sha256
    ):
        raise ProtocolValidationError("prediction vocabulary does not match the Dataset Manifest")
    vocabulary = set(predictions.medication_vocabulary)
    if any(not set(values) <= vocabulary for values in normalized_targets.values()):
        raise ProtocolValidationError("targets contain medications outside the declared vocabulary")

    records = tuple(
        PredictionRecord(
            patient_id=item.patient_id,
            visit_id=item.visit_id,
            split=SplitName.TEST,
            target_medications=normalized_targets[(item.patient_id, item.visit_id)],
            predicted_medications=item.predicted_medications,
        )
        for item in predictions.predictions
    )
    target_join_digest = content_sha256(
        [
            {
                "patient_id": record.patient_id,
                "target_medications": list(record.target_medications),
                "visit_id": record.visit_id,
            }
            for record in records
        ]
    )
    evaluation_input = IndependentEvaluationInput(
        method_id=predictions.method_id,
        expected_visit_digest=verified_visit_digest,
        prediction_visit_digest=verified_visit_digest,
        target_join_digest=target_join_digest,
    )
    return JoinedComparisonBatch(
        predictions=predictions,
        records=records,
        evaluation_input=evaluation_input,
    )


def _average_precision(targets: set[str], scores: tuple[tuple[str, float], ...]) -> float:
    if not targets:
        return 0.0
    ranked = sorted(scores, key=lambda item: -item[1])
    found = 0
    average_precision = 0.0
    index = 0
    while index < len(ranked):
        score = ranked[index][1]
        end = index
        group_positives = 0
        while end < len(ranked) and ranked[end][1] == score:
            group_positives += ranked[end][0] in targets
            end += 1
        if group_positives:
            found += group_positives
            average_precision += (group_positives / len(targets)) * (found / end)
        index = end
    return average_precision


def _comparison_outcomes(
    visits: tuple[tuple[PredictionRecord, tuple[tuple[str, float], ...]], ...],
    *,
    ddi_pairs: frozenset[tuple[str, str]],
) -> ComparisonOutcomes:
    jaccard = 0.0
    f1 = 0.0
    prauc = 0.0
    medication_count = 0
    ddi_count = 0
    predicted_pair_count = 0
    for record, scores in visits:
        visit_jaccard, _, _, visit_f1 = _visit_metrics(record)
        jaccard += visit_jaccard
        f1 += visit_f1
        prauc += _average_precision(set(record.target_medications), scores)
        medications = tuple(record.predicted_medications)
        medication_count += len(medications)
        for left_index, left in enumerate(medications):
            for right in medications[left_index + 1 :]:
                predicted_pair_count += 1
                ddi_count += tuple(sorted((left, right))) in ddi_pairs
    count = len(visits)
    return ComparisonOutcomes(
        ddi_rate=0.0 if predicted_pair_count == 0 else ddi_count / predicted_pair_count,
        jaccard=jaccard / count,
        f1=f1 / count,
        prauc=prauc / count,
        average_medication_count=medication_count / count,
    )


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def evaluate_comparison_predictions(
    joined: JoinedComparisonBatch,
    *,
    ddi_pairs: Iterable[tuple[str, str]],
    bootstrap_seed: int,
) -> ComparisonEvaluationResult:
    """Compute the fixed outcomes and deterministic ten-round 80% bootstrap."""

    if not isinstance(joined, JoinedComparisonBatch):
        raise ProtocolValidationError("joined must be a JoinedComparisonBatch")
    require_int(bootstrap_seed, field="bootstrap_seed")
    vocabulary = set(joined.predictions.medication_vocabulary)
    normalized_pairs: set[tuple[str, str]] = set()
    try:
        for raw_pair in ddi_pairs:
            if not isinstance(raw_pair, (list, tuple)) or len(raw_pair) != 2:
                raise ProtocolValidationError("DDI pairs must contain two medication codes")
            pair = tuple(sorted((raw_pair[0], raw_pair[1])))
            if pair[0] == pair[1] or not set(pair) <= vocabulary:
                raise ProtocolValidationError("DDI pairs must use two distinct vocabulary codes")
            normalized_pairs.add(pair)
    except TypeError as error:
        raise ProtocolValidationError("ddi_pairs must be a collection") from error
    scores_by_key = {
        (item.patient_id, item.visit_id): tuple(
            (score.medication_code, score.score) for score in item.vocabulary_scores
        )
        for item in joined.predictions.predictions
    }
    visits = tuple(
        (record, scores_by_key[(record.patient_id, record.visit_id)]) for record in joined.records
    )
    frozen_pairs = frozenset(normalized_pairs)
    point = _comparison_outcomes(visits, ddi_pairs=frozen_pairs)
    randomizer = random.Random(bootstrap_seed)
    sample_size = max(1, round(0.8 * len(visits)))
    rounds = tuple(
        _comparison_outcomes(
            tuple(visits[randomizer.randrange(len(visits))] for _ in range(sample_size)),
            ddi_pairs=frozen_pairs,
        )
        for _ in range(10)
    )
    intervals = tuple(
        (
            name,
            OutcomeInterval(
                lower=_percentile([getattr(item, name) for item in rounds], 0.1),
                upper=_percentile([getattr(item, name) for item in rounds], 0.9),
            ),
        )
        for name in REQUIRED_OUTCOMES
    )
    return ComparisonEvaluationResult(
        point=point,
        rounds=rounds,
        intervals=intervals,
        bootstrap_seed=bootstrap_seed,
    )


__all__ = (
    "ComparisonEvaluationResult",
    "ComparisonOutcomes",
    "EvaluationResult",
    "JoinedComparisonBatch",
    "OutcomeInterval",
    "evaluate_comparison_predictions",
    "evaluate_predictions",
    "join_comparison_targets",
)
