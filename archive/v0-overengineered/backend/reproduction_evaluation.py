"""Source-native reproduction outcomes and deterministic bootstrap evidence.

This module deliberately stays separate from :mod:`evaluation`.  The existing
evaluator is the Comparison Mode contract; this evaluator adds the source
native DDI/PRAUC inputs and the SafeDrug ten-round bootstrap without changing
legacy records.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    enum_member,
    parse_json_object,
    require_identifier,
    require_int,
    require_probability,
    require_single_line_public_string,
    strict_fields,
)
from .errors import ProtocolValidationError
from .prediction import MedicationScore, PredictionRecord
from .reproduction_contract import (
    REQUIRED_OUTCOMES,
    AttemptValidity,
    EvidenceConclusion,
    RepairEvidence,
)


class ReproductionMetric(StrEnum):
    DDI_RATE = "ddi_rate"
    JACCARD = "jaccard"
    F1 = "f1"
    PRAUC = "prauc"
    AVERAGE_MEDICATION_COUNT = "average_medication_count"


def _metric(value: object, *, field: str) -> ReproductionMetric:
    return enum_member(ReproductionMetric, value, field=field)


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ProtocolValidationError(f"{field} must be a finite number")
    return result


def _codes(value: object, *, field: str, sort: bool = False) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ProtocolValidationError(f"{field} must be a collection of medication codes")
    try:
        result = tuple(require_single_line_public_string(item, field=field) for item in value)
    except TypeError as error:
        raise ProtocolValidationError(
            f"{field} must be a collection of medication codes"
        ) from error
    if len(result) != len(set(result)):
        raise ProtocolValidationError(f"{field} entries must be unique")
    return tuple(sorted(result)) if sort else result


def _pair_set(value: object, *, field: str) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ProtocolValidationError(f"{field} must be a collection of medication pairs")
    pairs: set[tuple[str, str]] = set()
    for pair in value:
        if isinstance(pair, (str, bytes)) or not isinstance(pair, Sequence) or len(pair) != 2:
            raise ProtocolValidationError(f"{field} entries must contain two medication codes")
        left, right = _codes(pair, field=f"{field}.pair")
        if len(left) != 1 or len(right) != 1:
            raise ProtocolValidationError(f"{field} pair codes must be non-empty")
        if left[0] == right[0]:
            raise ProtocolValidationError(f"{field} pairs must contain two distinct codes")
        pairs.add(tuple(sorted((left[0], right[0]))))
    return tuple(sorted(pairs))


def _binary_labels(value: object, *, field: str) -> tuple[int, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ProtocolValidationError(f"{field} must be a collection of binary labels")
    labels = tuple(value)
    if any(type(item) is not int or item not in {0, 1} for item in labels):
        raise ProtocolValidationError(f"{field} must contain only 0 or 1")
    return labels


def _scores(value: object, *, field: str) -> tuple[float, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ProtocolValidationError(f"{field} must be a collection of scores")
    return tuple(_finite(item, field=field) for item in value)


def _set_metrics(target: set[str], predicted: set[str]) -> tuple[float, float, float]:
    if not target and not predicted:
        return 1.0, 1.0, 1.0
    if not target or not predicted:
        return 0.0, 0.0, 0.0
    intersection = len(target & predicted)
    jaccard = intersection / len(target | predicted)
    precision = intersection / len(predicted)
    recall = intersection / len(target)
    f1 = 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)
    return jaccard, f1, recall


def average_precision(labels: Sequence[int], scores: Sequence[float]) -> float:
    """Compute average precision from explicit binary labels and scores."""

    if len(labels) != len(scores) or not labels:
        raise ProtocolValidationError("PRAUC labels and scores must be non-empty and aligned")
    checked_labels = _binary_labels(labels, field="prauc.labels")
    checked_scores = _scores(scores, field="prauc.scores")
    positives = sum(checked_labels)
    if positives == 0:
        return 0.0
    ranked = sorted(range(len(checked_labels)), key=lambda index: (-checked_scores[index], index))
    seen_positive = 0
    accumulated_precision = 0.0
    for rank, index in enumerate(ranked, start=1):
        if checked_labels[index]:
            seen_positive += 1
            accumulated_precision += seen_positive / rank
    return accumulated_precision / positives


@dataclass(frozen=True, slots=True)
class OutcomeObservation:
    """One target/prediction observation with explicit DDI/PRAUC evidence."""

    observation_id: str
    target_medications: tuple[str, ...] = ()
    predicted_medications: tuple[str, ...] = ()
    scores: tuple[MedicationScore, ...] = ()
    ddi_pairs: tuple[tuple[str, str], ...] = ()
    prauc_labels: tuple[int, ...] = ()
    prauc_scores: tuple[float, ...] = ()
    metric_values: object = ()

    def __post_init__(self) -> None:
        require_identifier(self.observation_id, field="observation_id")
        target = _codes(self.target_medications, field="target_medications", sort=True)
        predicted = _codes(self.predicted_medications, field="predicted_medications")
        object.__setattr__(self, "target_medications", target)
        object.__setattr__(self, "predicted_medications", predicted)
        score_records = tuple(
            score if isinstance(score, MedicationScore) else MedicationScore.from_dict(score)
            for score in self.scores
        )
        if score_records and tuple(item.medication_code for item in score_records) != predicted:
            raise ProtocolValidationError("scores must align with predicted_medications")
        object.__setattr__(self, "scores", score_records)
        pairs = _pair_set(self.ddi_pairs, field="ddi_pairs")
        if any(left not in predicted or right not in predicted for left, right in pairs):
            raise ProtocolValidationError("ddi_pairs must refer to predicted medications")
        object.__setattr__(self, "ddi_pairs", pairs)
        labels = _binary_labels(self.prauc_labels, field="prauc_labels")
        prauc_scores = _scores(self.prauc_scores, field="prauc_scores")
        if bool(labels) != bool(prauc_scores) or (labels and len(labels) != len(prauc_scores)):
            raise ProtocolValidationError("prauc labels and scores must be supplied together")
        object.__setattr__(self, "prauc_labels", labels)
        object.__setattr__(self, "prauc_scores", prauc_scores)
        if self.metric_values:
            if not isinstance(self.metric_values, Mapping):
                raise ProtocolValidationError("metric_values must be an object")
            values: dict[str, float] = {}
            for key, value in self.metric_values.items():
                metric = _metric(key, field="metric_values.metric")
                values[metric.value] = _finite(value, field=f"metric_values.{metric.value}")
            object.__setattr__(self, "metric_values", tuple(sorted(values.items())))
        else:
            object.__setattr__(self, "metric_values", ())

    @property
    def _provided_values(self) -> dict[str, float]:
        return dict(self.metric_values) if self.metric_values else {}

    def value(self, metric: ReproductionMetric | str) -> float:
        selected = _metric(metric, field="metric")
        provided = self._provided_values
        if selected.value in provided:
            return provided[selected.value]
        target = set(self.target_medications)
        predicted = set(self.predicted_medications)
        jaccard, f1, _ = _set_metrics(target, predicted)
        if selected is ReproductionMetric.JACCARD:
            return jaccard
        if selected is ReproductionMetric.F1:
            return f1
        if selected is ReproductionMetric.AVERAGE_MEDICATION_COUNT:
            return float(len(predicted))
        if selected is ReproductionMetric.DDI_RATE:
            pair_count = len(tuple(combinations(predicted, 2)))
            return 0.0 if pair_count == 0 else len(self.ddi_pairs) / pair_count
        if not self.prauc_labels:
            raise ProtocolValidationError(
                "PRAUC requires explicitly supplied core-owned labels and scores"
            )
        return average_precision(self.prauc_labels, self.prauc_scores)

    def to_dict(self) -> dict[str, object]:
        return {
            "ddi_pairs": [list(pair) for pair in self.ddi_pairs],
            "metric_values": dict(self.metric_values),
            "observation_id": self.observation_id,
            "prauc_labels": list(self.prauc_labels),
            "prauc_scores": list(self.prauc_scores),
            "predicted_medications": list(self.predicted_medications),
            "scores": [score.to_dict() for score in self.scores],
            "target_medications": list(self.target_medications),
        }

    @classmethod
    def from_dict(cls, value: object) -> OutcomeObservation:
        payload = strict_fields(
            value,
            required=(
                "ddi_pairs",
                "metric_values",
                "observation_id",
                "prauc_labels",
                "prauc_scores",
                "predicted_medications",
                "scores",
                "target_medications",
            ),
            context="OutcomeObservation",
        )
        if not all(isinstance(payload[field], list) for field in ("scores", "ddi_pairs")):
            raise ProtocolValidationError("OutcomeObservation list fields must be lists")
        payload["scores"] = tuple(MedicationScore.from_dict(item) for item in payload["scores"])
        payload["ddi_pairs"] = tuple(tuple(item) for item in payload["ddi_pairs"])
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class BootstrapSpec:
    """The fixed SafeDrug ten-round, 80%-of-test bootstrap procedure."""

    rounds: int = 10
    sample_fraction: float = 0.8
    with_replacement: bool = True
    seed: int = 0
    interval_level: float = 0.8

    def __post_init__(self) -> None:
        require_int(self.rounds, field="bootstrap.rounds", minimum=1)
        if self.rounds != 10:
            raise ProtocolValidationError("bootstrap.rounds must be the source-native ten rounds")
        fraction = require_probability(self.sample_fraction, field="bootstrap.sample_fraction")
        if fraction != 0.8:
            raise ProtocolValidationError("bootstrap.sample_fraction must be 0.8")
        if self.with_replacement is not True:
            raise ProtocolValidationError("bootstrap.with_replacement must be true")
        require_int(self.seed, field="bootstrap.seed", minimum=0)
        level = require_probability(self.interval_level, field="bootstrap.interval_level")
        if level != 0.8:
            raise ProtocolValidationError("bootstrap.interval_level must be 0.8")
        object.__setattr__(self, "sample_fraction", fraction)
        object.__setattr__(self, "interval_level", level)

    def sample_size(self, observation_count: int) -> int:
        require_int(observation_count, field="bootstrap.observation_count", minimum=1)
        size = math.floor(observation_count * self.sample_fraction)
        if size < 1:
            raise ProtocolValidationError(
                "test set is too small to produce an 80%-of-test bootstrap sample"
            )
        return size

    def to_dict(self) -> dict[str, object]:
        return {
            "interval_level": self.interval_level,
            "rounds": self.rounds,
            "sample_fraction": self.sample_fraction,
            "seed": self.seed,
            "with_replacement": self.with_replacement,
        }

    @classmethod
    def from_dict(cls, value: object) -> BootstrapSpec:
        return cls(
            **strict_fields(
                value,
                required=(
                    "interval_level",
                    "rounds",
                    "sample_fraction",
                    "seed",
                    "with_replacement",
                ),
                context="BootstrapSpec",
            )
        )


def _percentile(values: tuple[float, ...], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


@dataclass(frozen=True, slots=True)
class BootstrapEstimate:
    metric: ReproductionMetric | str
    estimates: tuple[float, ...]
    lower: float
    upper: float
    sample_size: int
    rounds: int = 10
    sample_fraction: float = 0.8
    with_replacement: bool = True
    bootstrap_seed: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric", _metric(self.metric, field="bootstrap.metric"))
        values = tuple(_finite(item, field="bootstrap.estimates") for item in self.estimates)
        if len(values) != self.rounds or not values:
            raise ProtocolValidationError("bootstrap.estimates must contain one value per round")
        object.__setattr__(self, "estimates", values)
        require_int(self.sample_size, field="bootstrap.sample_size", minimum=1)
        require_int(self.rounds, field="bootstrap.rounds", minimum=1)
        if self.rounds != 10:
            raise ProtocolValidationError("bootstrap estimate rounds must be 10")
        if self.sample_fraction != 0.8 or self.with_replacement is not True:
            raise ProtocolValidationError("bootstrap estimate must use the source-native procedure")
        require_int(self.bootstrap_seed, field="bootstrap.bootstrap_seed", minimum=0)
        lower = _finite(self.lower, field="bootstrap.lower")
        upper = _finite(self.upper, field="bootstrap.upper")
        if lower > upper:
            raise ProtocolValidationError("bootstrap interval lower must not exceed upper")
        if lower != _percentile(values, 0.1) or upper != _percentile(values, 0.9):
            raise ProtocolValidationError(
                "bootstrap interval must be the declared 80% percentile interval"
            )
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    @property
    def mean(self) -> float:
        return sum(self.estimates) / len(self.estimates)

    @property
    def interval(self) -> tuple[float, float]:
        return self.lower, self.upper

    def to_dict(self) -> dict[str, object]:
        return {
            "bootstrap_seed": self.bootstrap_seed,
            "estimates": list(self.estimates),
            "interval": [self.lower, self.upper],
            "metric": self.metric.value,
            "rounds": self.rounds,
            "sample_fraction": self.sample_fraction,
            "sample_size": self.sample_size,
            "with_replacement": self.with_replacement,
        }

    @classmethod
    def from_dict(cls, value: object) -> BootstrapEstimate:
        payload = strict_fields(
            value,
            required=(
                "bootstrap_seed",
                "estimates",
                "interval",
                "metric",
                "rounds",
                "sample_fraction",
                "sample_size",
                "with_replacement",
            ),
            context="BootstrapEstimate",
        )
        interval = payload.pop("interval")
        if not isinstance(interval, list) or len(interval) != 2:
            raise ProtocolValidationError("BootstrapEstimate interval must contain two numbers")
        payload["lower"], payload["upper"] = interval
        payload["estimates"] = tuple(payload["estimates"])
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class SourceAcceptanceProfile:
    """Predeclared source-backed intervals for one reproduction model."""

    model_id: str
    acceptance_intervals: object = ()
    source_revision: str = ""
    source_reference: str = ""
    required_outcomes: tuple[str, ...] = REQUIRED_OUTCOMES

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.model_id, field="source_profile.model_id")
        if isinstance(self.acceptance_intervals, Mapping):
            intervals: dict[str, tuple[float, float]] = {}
            for key, bounds in self.acceptance_intervals.items():
                metric = _metric(key, field="source_profile.metric")
                if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
                    raise ProtocolValidationError(
                        "source acceptance interval must contain two bounds"
                    )
                lower = _finite(bounds[0], field=f"source_profile.{metric.value}.lower")
                upper = _finite(bounds[1], field=f"source_profile.{metric.value}.upper")
                if lower > upper:
                    raise ProtocolValidationError(
                        "source acceptance interval lower must not exceed upper"
                    )
                intervals[metric.value] = (lower, upper)
        else:
            raise ProtocolValidationError("source_profile.acceptance_intervals must be an object")
        required = tuple(
            _metric(item, field="source_profile.required_outcomes").value
            for item in self.required_outcomes
        )
        if len(required) != len(set(required)) or not set(REQUIRED_OUTCOMES) <= set(required):
            raise ProtocolValidationError(
                "source_profile.required_outcomes must include all required outcomes"
            )
        object.__setattr__(self, "acceptance_intervals", tuple(sorted(intervals.items())))
        object.__setattr__(self, "required_outcomes", required)
        if self.source_revision:
            require_identifier(self.source_revision, field="source_profile.source_revision")
        if self.source_reference:
            require_single_line_public_string(
                self.source_reference, field="source_profile.source_reference"
            )

    @property
    def intervals(self) -> dict[str, tuple[float, float]]:
        return dict(self.acceptance_intervals)

    @property
    def is_complete(self) -> bool:
        return set(REQUIRED_OUTCOMES) <= set(self.intervals)

    def interval_for(self, metric: ReproductionMetric | str) -> tuple[float, float] | None:
        return self.intervals.get(_metric(metric, field="metric").value)

    def to_dict(self) -> dict[str, object]:
        return {
            "acceptance_intervals": {
                key: list(bounds) for key, bounds in self.acceptance_intervals
            },
            "model_id": self.model_id,
            "required_outcomes": list(self.required_outcomes),
            "schema_version": self.SCHEMA_VERSION,
            "source_reference": self.source_reference,
            "source_revision": self.source_revision,
        }

    @classmethod
    def from_dict(cls, value: object) -> SourceAcceptanceProfile:
        payload = strict_fields(
            value,
            required=(
                "acceptance_intervals",
                "model_id",
                "required_outcomes",
                "schema_version",
                "source_reference",
                "source_revision",
            ),
            context="SourceAcceptanceProfile",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("SourceAcceptanceProfile schema_version must be 1")
        return cls(**payload)


def compute_outcomes(observations: Iterable[OutcomeObservation]) -> dict[str, float]:
    values = tuple(observations)
    if not values:
        raise ProtocolValidationError("reproduction evaluation requires at least one observation")
    if any(not isinstance(item, OutcomeObservation) for item in values):
        raise ProtocolValidationError(
            "reproduction observations must be OutcomeObservation records"
        )
    return {
        metric: sum(item.value(metric) for item in values) / len(values)
        for metric in REQUIRED_OUTCOMES
    }


def bootstrap_outcomes(
    observations: Iterable[OutcomeObservation],
    *,
    spec: BootstrapSpec | None = None,
) -> tuple[BootstrapEstimate, ...]:
    values = tuple(observations)
    if not values:
        raise ProtocolValidationError("bootstrap requires at least one observation")
    selected_spec = spec or BootstrapSpec()
    sample_size = selected_spec.sample_size(len(values))
    generator = random.Random(selected_spec.seed)
    samples: dict[str, list[float]] = {metric: [] for metric in REQUIRED_OUTCOMES}
    for _ in range(selected_spec.rounds):
        selected = [values[generator.randrange(len(values))] for _ in range(sample_size)]
        outcome = compute_outcomes(selected)
        for metric in REQUIRED_OUTCOMES:
            samples[metric].append(outcome[metric])
    return tuple(
        BootstrapEstimate(
            metric=metric,
            estimates=tuple(samples[metric]),
            lower=_percentile(tuple(samples[metric]), 0.1),
            upper=_percentile(tuple(samples[metric]), 0.9),
            sample_size=sample_size,
            rounds=selected_spec.rounds,
            sample_fraction=selected_spec.sample_fraction,
            with_replacement=selected_spec.with_replacement,
            bootstrap_seed=selected_spec.seed,
        )
        for metric in REQUIRED_OUTCOMES
    )


@dataclass(frozen=True, slots=True)
class ReproductionEvaluation:
    """Packet-ready source-native conclusion and uncertainty evidence."""

    model_id: str
    validity: AttemptValidity | str
    conclusion: EvidenceConclusion | str
    outcomes: object
    bootstrap_estimates: tuple[BootstrapEstimate, ...]
    source_profile: SourceAcceptanceProfile
    missing_intervals: tuple[str, ...] = ()
    failed_outcomes: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    error: str = ""

    def __post_init__(self) -> None:
        require_identifier(self.model_id, field="evaluation.model_id")
        object.__setattr__(
            self,
            "validity",
            enum_member(AttemptValidity, self.validity, field="evaluation.validity"),
        )
        object.__setattr__(
            self,
            "conclusion",
            enum_member(EvidenceConclusion, self.conclusion, field="evaluation.conclusion"),
        )
        if not isinstance(self.source_profile, SourceAcceptanceProfile):
            raise ProtocolValidationError(
                "evaluation.source_profile must be a SourceAcceptanceProfile"
            )
        if isinstance(self.outcomes, Mapping):
            normalized = {
                str(key): _finite(value, field=f"evaluation.outcomes.{key}")
                for key, value in self.outcomes.items()
            }
        else:
            raise ProtocolValidationError("evaluation.outcomes must be an object")
        if not set(REQUIRED_OUTCOMES) <= set(normalized):
            raise ProtocolValidationError("evaluation.outcomes must include all required outcomes")
        object.__setattr__(self, "outcomes", tuple(sorted(normalized.items())))
        estimates = tuple(
            item if isinstance(item, BootstrapEstimate) else BootstrapEstimate.from_dict(item)
            for item in self.bootstrap_estimates
        )
        if tuple(item.metric.value for item in estimates) != REQUIRED_OUTCOMES:
            raise ProtocolValidationError(
                "evaluation bootstrap estimates must cover required outcomes in order"
            )
        object.__setattr__(self, "bootstrap_estimates", estimates)
        for name in ("missing_intervals", "failed_outcomes", "limitations"):
            items = tuple(
                require_single_line_public_string(item, field=f"evaluation.{name}")
                for item in getattr(self, name)
            )
            object.__setattr__(self, name, items)
        if self.error:
            require_single_line_public_string(self.error, field="evaluation.error")

    @property
    def uncertainty(self) -> dict[str, list[float]]:
        return {item.metric.value: [item.lower, item.upper] for item in self.bootstrap_estimates}

    @property
    def is_current(self) -> bool:
        return self.evaluation_sha256 == content_sha256(self._protected_payload())

    @property
    def evaluation_sha256(self) -> str:
        return content_sha256(self._protected_payload())

    def _protected_payload(self) -> dict[str, object]:
        return {
            "bootstrap_estimates": [item.to_dict() for item in self.bootstrap_estimates],
            "conclusion": self.conclusion.value,
            "failed_outcomes": list(self.failed_outcomes),
            "model_id": self.model_id,
            "missing_intervals": list(self.missing_intervals),
            "outcomes": dict(self.outcomes),
            "source_profile": self.source_profile.to_dict(),
            "validity": self.validity.value,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "bootstrap_estimates": [item.to_dict() for item in self.bootstrap_estimates],
            "conclusion": self.conclusion.value,
            "error": self.error,
            "evaluation_sha256": self.evaluation_sha256,
            "failed_outcomes": list(self.failed_outcomes),
            "kind": "reproduction_evaluation",
            "limitations": list(self.limitations),
            "missing_intervals": list(self.missing_intervals),
            "model_id": self.model_id,
            "outcomes": dict(self.outcomes),
            "schema_version": 1,
            "source_profile": self.source_profile.to_dict(),
            "uncertainty": self.uncertainty,
            "validity": self.validity.value,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, value: object) -> ReproductionEvaluation:
        payload = strict_fields(
            value,
            required=(
                "bootstrap_estimates",
                "conclusion",
                "error",
                "evaluation_sha256",
                "failed_outcomes",
                "kind",
                "limitations",
                "missing_intervals",
                "model_id",
                "outcomes",
                "schema_version",
                "source_profile",
                "uncertainty",
                "validity",
            ),
            context="ReproductionEvaluation",
        )
        if payload.pop("schema_version") != 1 or payload.pop("kind") != "reproduction_evaluation":
            raise ProtocolValidationError("ReproductionEvaluation schema or kind is invalid")
        expected_digest = payload.pop("evaluation_sha256")
        serialized_uncertainty = payload.pop("uncertainty")
        payload["source_profile"] = SourceAcceptanceProfile.from_dict(payload["source_profile"])
        payload["bootstrap_estimates"] = tuple(
            BootstrapEstimate.from_dict(item) for item in payload["bootstrap_estimates"]
        )
        result = cls(**payload)
        if canonical_json(serialized_uncertainty) != canonical_json(result.uncertainty):
            raise ProtocolValidationError(
                "ReproductionEvaluation uncertainty does not match bootstrap estimates"
            )
        if expected_digest != result.evaluation_sha256:
            raise ProtocolValidationError(
                "ReproductionEvaluation digest does not match protected fields"
            )
        return result

    @classmethod
    def from_json(cls, text: str) -> ReproductionEvaluation:
        return cls.from_dict(parse_json_object(text, context="ReproductionEvaluation"))


def classify_reproduction(
    observations: Iterable[OutcomeObservation],
    source_profile: SourceAcceptanceProfile,
    *,
    model_id: str | None = None,
    validity: AttemptValidity | str = AttemptValidity.USABLE,
    spec: BootstrapSpec | None = None,
    repair_evidence: Iterable[RepairEvidence] = (),
) -> ReproductionEvaluation:
    """Compute and classify one model without cross-lane aggregation."""

    selected_model = model_id or source_profile.model_id
    require_identifier(selected_model, field="model_id")
    effective_validity = enum_member(AttemptValidity, validity, field="validity")
    repairs = tuple(repair_evidence)
    if effective_validity is AttemptValidity.USABLE and any(
        item.artifact_changed and not item.has_equivalence_evidence for item in repairs
    ):
        effective_validity = AttemptValidity.USABLE_WITH_LIMITS
    values = tuple(observations)
    try:
        estimates = bootstrap_outcomes(values, spec=spec)
        outcomes = compute_outcomes(values)
        missing = tuple(
            metric for metric in REQUIRED_OUTCOMES if source_profile.interval_for(metric) is None
        )
        failed: list[str] = []
        for estimate in estimates:
            interval = source_profile.interval_for(estimate.metric)
            if interval is not None and (
                estimate.lower < interval[0] or estimate.upper > interval[1]
            ):
                failed.append(estimate.metric.value)
        if effective_validity is AttemptValidity.INVALID or missing:
            conclusion = EvidenceConclusion.INCONCLUSIVE
        elif failed:
            conclusion = EvidenceConclusion.REJECTED
        else:
            conclusion = EvidenceConclusion.ACCEPTED
        limitations = tuple(
            ["source acceptance interval is missing for one or more required outcomes"]
            if missing
            else []
        )
        if effective_validity is AttemptValidity.USABLE_WITH_LIMITS:
            limitations += ("artifact-changing repair lacks independent equivalence evidence",)
        return ReproductionEvaluation(
            model_id=selected_model,
            validity=effective_validity,
            conclusion=conclusion,
            outcomes=outcomes,
            bootstrap_estimates=estimates,
            source_profile=source_profile,
            missing_intervals=missing,
            failed_outcomes=tuple(failed),
            limitations=limitations,
        )
    except ProtocolValidationError as error:
        empty_estimates = tuple(
            BootstrapEstimate(
                metric=metric,
                estimates=(0.0,) * 10,
                lower=0.0,
                upper=0.0,
                sample_size=1,
                bootstrap_seed=(spec or BootstrapSpec()).seed,
            )
            for metric in REQUIRED_OUTCOMES
        )
        return ReproductionEvaluation(
            model_id=selected_model,
            validity=AttemptValidity.INVALID,
            conclusion=EvidenceConclusion.INCONCLUSIVE,
            outcomes={metric: 0.0 for metric in REQUIRED_OUTCOMES},
            bootstrap_estimates=empty_estimates,
            source_profile=source_profile,
            limitations=("outcome evidence is malformed or incomplete",),
            error=str(error),
        )


def observation_from_prediction(
    record: PredictionRecord,
    *,
    ddi_pairs: Iterable[Sequence[str]] = (),
    prauc_labels: Iterable[int] = (),
    prauc_scores: Iterable[float] = (),
) -> OutcomeObservation:
    if not isinstance(record, PredictionRecord):
        raise ProtocolValidationError("record must be a PredictionRecord")
    return OutcomeObservation(
        observation_id=record.visit_id,
        target_medications=record.target_medications,
        predicted_medications=record.predicted_medications,
        scores=record.scores,
        ddi_pairs=tuple(ddi_pairs),
        prauc_labels=tuple(prauc_labels),
        prauc_scores=tuple(prauc_scores),
    )


def evaluate_prediction_records(
    records: Iterable[PredictionRecord],
    *,
    ddi_pairs_by_observation: Mapping[str, Iterable[Sequence[str]]] | None = None,
    prauc_inputs_by_observation: Mapping[str, tuple[Iterable[int], Iterable[float]]] | None = None,
) -> dict[str, float]:
    predictions = tuple(records)
    if not predictions:
        raise ProtocolValidationError(
            "reproduction evaluation requires at least one PredictionRecord"
        )
    observations = []
    for record in predictions:
        ddi_pairs = (ddi_pairs_by_observation or {}).get(record.visit_id, ())
        prauc_labels, prauc_scores = (prauc_inputs_by_observation or {}).get(
            record.visit_id, ((), ())
        )
        observations.append(
            observation_from_prediction(
                record,
                ddi_pairs=ddi_pairs,
                prauc_labels=prauc_labels,
                prauc_scores=prauc_scores,
            )
        )
    return compute_outcomes(observations)


ReproductionClassification = ReproductionEvaluation
evaluate_reproduction = classify_reproduction


__all__ = (
    "BootstrapEstimate",
    "BootstrapSpec",
    "OutcomeObservation",
    "ReproductionClassification",
    "ReproductionEvaluation",
    "ReproductionMetric",
    "SourceAcceptanceProfile",
    "average_precision",
    "bootstrap_outcomes",
    "classify_reproduction",
    "compute_outcomes",
    "evaluate_prediction_records",
    "evaluate_reproduction",
    "observation_from_prediction",
)
