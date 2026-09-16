"""Deterministic Train/Dev evaluator for the paper experiment contract.

The historical comparison evaluator in :mod:`medrec_research.evaluation` is
kept intact because it describes an older protocol.  This module implements
the current paper contract used by new bounded research prototypes.  It has
no data or model dependencies and is Python 3.8-compatible for the declared
baseline environment on 319.
"""

from __future__ import annotations

import itertools
import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VisitPrediction:
    """One eligible visit with a target-free score vector and decoded set."""

    patient_id: Any
    visit_id: Any
    target_medications: tuple[str, ...]
    predicted_medications: tuple[str, ...]
    medication_scores: tuple[float, ...]


@dataclass(frozen=True)
class SelectionCandidate:
    """One checkpoint/operating-point score considered by joint selection."""

    checkpoint: int
    operating_point: Any
    patient_macro_jaccard: float
    operating_point_index: int


def _finite_score(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must contain finite numbers")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field} must contain finite numbers")
    return normalized


def _metric_sets(target: set[str], predicted: set[str]) -> tuple[float, float, float, float]:
    if not target and not predicted:
        return 1.0, 1.0, 1.0, 1.0
    if not target or not predicted:
        return 0.0, 0.0, 0.0, 0.0
    intersection = len(target & predicted)
    precision = intersection / float(len(predicted))
    recall = intersection / float(len(target))
    f1 = 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)
    return intersection / float(len(target | predicted)), precision, recall, f1


def _average_precision(
    target: set[str], vocabulary: tuple[str, ...], scores: tuple[float, ...]
) -> float:
    """Average precision over every declared coordinate.

    Ties use canonical vocabulary order.  Empty targets have AP ``0.0``
    because no positive ranking exists; the profile records this convention.
    """

    if not target:
        return 0.0
    target_indices = {index for index, code in enumerate(vocabulary) if code in target}
    ranked = sorted(range(len(vocabulary)), key=lambda index: (-scores[index], index))
    found = 0
    total = 0.0
    for rank, index in enumerate(ranked, start=1):
        if index in target_indices:
            found += 1
            total += found / float(rank)
    return total / float(len(target_indices))


def _normalise_pairs(
    ddi_pairs: Iterable[tuple[str, str]], vocabulary: tuple[str, ...]
) -> frozenset[tuple[str, str]]:
    allowed = set(vocabulary)
    normalized: set[tuple[str, str]] = set()
    try:
        for pair in ddi_pairs:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise ValueError("DDI pairs must contain two medication codes")
            left, right = pair
            if not isinstance(left, str) or not isinstance(right, str):
                raise ValueError("DDI pairs must contain medication strings")
            if left == right or left not in allowed or right not in allowed:
                raise ValueError("DDI pairs must use two distinct vocabulary codes")
            normalized.add(tuple(sorted((left, right))))
    except TypeError as error:
        raise ValueError("ddi_pairs must be iterable") from error
    return frozenset(normalized)


def _validate_and_group(
    samples: Iterable[VisitPrediction], vocabulary: tuple[str, ...]
) -> dict[Any, list[VisitPrediction]]:
    if not vocabulary or len(set(vocabulary)) != len(vocabulary):
        raise ValueError("vocabulary must contain unique medication codes")
    if any(not isinstance(code, str) or not code for code in vocabulary):
        raise ValueError("vocabulary must contain non-empty medication strings")
    allowed = set(vocabulary)
    grouped: dict[Any, list[VisitPrediction]] = defaultdict(list)
    seen_visits: set[tuple[Any, Any]] = set()
    values = tuple(samples)
    if not values:
        raise ValueError("evaluation requires at least one eligible visit")
    for sample in values:
        if not isinstance(sample, VisitPrediction):
            raise ValueError("samples must contain VisitPrediction values")
        key = (sample.patient_id, sample.visit_id)
        try:
            if key in seen_visits:
                raise ValueError("evaluation requires unique patient_id and visit_id pairs")
            seen_visits.add(key)
        except TypeError as error:
            raise ValueError("patient_id and visit_id must be hashable") from error
        target = tuple(sample.target_medications)
        predicted = tuple(sample.predicted_medications)
        if len(target) != len(set(target)):
            raise ValueError("target medications must be unique")
        if len(predicted) != len(set(predicted)):
            raise ValueError("predicted medications must be unique")
        if not set(target) <= allowed:
            raise ValueError("target medication is outside the declared vocabulary")
        if not set(predicted) <= allowed:
            raise ValueError("predicted medication is outside the declared vocabulary")
        if len(sample.medication_scores) != len(vocabulary):
            raise ValueError("medication_scores must cover the full declared vocabulary")
        scores = tuple(
            _finite_score(value, field="medication_scores") for value in sample.medication_scores
        )
        grouped[sample.patient_id].append(
            VisitPrediction(
                patient_id=sample.patient_id,
                visit_id=sample.visit_id,
                target_medications=target,
                predicted_medications=predicted,
                medication_scores=scores,
            )
        )
    return grouped


def _macro(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("cannot average an empty sequence")
    return float(sum(values) / len(values))


def evaluate(
    samples: Iterable[VisitPrediction],
    *,
    vocabulary: Sequence[str],
    ddi_pairs: Iterable[tuple[str, str]] = (),
    eligible_patient_ids: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Compute current paper-contract metrics with patient-macro weighting.

    Set metrics and AP are averaged over visits within each patient and then
    equally across patients.  DDI is the pooled predicted-pair rate.  The
    returned dictionary contains supplementary visit-macro values so callers
    cannot silently substitute a different estimand during selection/reporting.
    """

    canonical_vocabulary = tuple(vocabulary)
    grouped = _validate_and_group(samples, canonical_vocabulary)
    frozen_ddi = _normalise_pairs(ddi_pairs, canonical_vocabulary)
    patient_rows: list[dict[str, float]] = []
    visit_rows: list[dict[str, float]] = []
    ddi_interactions = 0
    predicted_pair_count = 0
    target_cardinality: list[float] = []
    predicted_cardinality: list[float] = []
    empty_target_visits = 0
    empty_prediction_visits = 0
    both_empty_visits = 0
    support = {code: 0 for code in canonical_vocabulary}

    for patient_id in sorted(grouped, key=lambda value: str(value)):
        patient_visits = grouped[patient_id]
        per_patient: dict[str, list[float]] = {
            "jaccard": [],
            "precision": [],
            "recall": [],
            "f1": [],
            "prauc": [],
            "predicted_medication_count": [],
            "target_medication_count": [],
        }
        for sample in patient_visits:
            target = set(sample.target_medications)
            predicted = set(sample.predicted_medications)
            for code in target:
                support[code] += 1
            jaccard, precision, recall, f1 = _metric_sets(target, predicted)
            ap = _average_precision(target, canonical_vocabulary, sample.medication_scores)
            row = {
                "jaccard": jaccard,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "prauc": ap,
                "predicted_medication_count": float(len(predicted)),
                "target_medication_count": float(len(target)),
            }
            visit_rows.append(row)
            for name, value in row.items():
                per_patient[name].append(value)
            target_cardinality.append(float(len(target)))
            predicted_cardinality.append(float(len(predicted)))
            if not target:
                empty_target_visits += 1
            if not predicted:
                empty_prediction_visits += 1
            if not target and not predicted:
                both_empty_visits += 1
            ordered = sorted(predicted)
            for left, right in itertools.combinations(ordered, 2):
                predicted_pair_count += 1
                ddi_interactions += int((left, right) in frozen_ddi)
        patient_rows.append({name: _macro(values) for name, values in per_patient.items()})

    result: dict[str, Any] = {
        "aggregation": "patient_macro",
        "patient_count": len(patient_rows),
        "visit_count": len(visit_rows),
        "jaccard": _macro([row["jaccard"] for row in patient_rows]),
        "f1": _macro([row["f1"] for row in patient_rows]),
        "precision": _macro([row["precision"] for row in patient_rows]),
        "recall": _macro([row["recall"] for row in patient_rows]),
        "prauc": _macro([row["prauc"] for row in patient_rows]),
        "average_medication_count": _macro(
            [row["predicted_medication_count"] for row in patient_rows]
        ),
        "target_average_medication_count": _macro(
            [row["target_medication_count"] for row in patient_rows]
        ),
        "ddi_rate": 0.0 if predicted_pair_count == 0 else ddi_interactions / predicted_pair_count,
        "predicted_pair_count": predicted_pair_count,
        "ddi_interacting_pair_count": ddi_interactions,
        "empty_target_visits": empty_target_visits,
        "empty_prediction_visits": empty_prediction_visits,
        "both_empty_visits": both_empty_visits,
        "zero_support_coordinates": [code for code in canonical_vocabulary if support[code] == 0],
        "visit_macro": {
            "jaccard": _macro([row["jaccard"] for row in visit_rows]),
            "f1": _macro([row["f1"] for row in visit_rows]),
            "precision": _macro([row["precision"] for row in visit_rows]),
            "recall": _macro([row["recall"] for row in visit_rows]),
            "prauc": _macro([row["prauc"] for row in visit_rows]),
            "average_medication_count": _macro(
                [row["predicted_medication_count"] for row in visit_rows]
            ),
            "target_average_medication_count": _macro(
                [row["target_medication_count"] for row in visit_rows]
            ),
        },
        "continuous_score": {
            "kind": "finite medication score per declared coordinate",
            "coordinate_order": list(canonical_vocabulary),
            "tie_break": "canonical vocabulary order",
            "empty_target_average_precision": 0.0,
        },
    }
    if eligible_patient_ids is not None:
        eligible = tuple(eligible_patient_ids)
        if len(eligible) != len(set(eligible)):
            raise ValueError("eligible_patient_ids must be unique")
        observed = set(grouped)
        result["eligible_patient_count"] = len(eligible)
        result["patients_with_no_eligible_visit"] = len(set(eligible) - observed)
    else:
        result["eligible_patient_count"] = len(patient_rows)
        result["patients_with_no_eligible_visit"] = 0
    return result


def select_joint(
    candidates: Iterable[SelectionCandidate],
    *,
    operating_point_order: Sequence[Any],
    native_default: Any,
) -> SelectionCandidate:
    """Select one checkpoint/operating point using the frozen tie-break.

    The caller must provide every legal operating point for every checkpoint.
    Ties use the operating point closest to ``native_default``, then the
    declared operating-point order, then the earlier checkpoint.
    """

    values = tuple(candidates)
    if not values:
        raise ValueError("joint selection requires candidates")
    order = tuple(operating_point_order)
    if not order or len(set(order)) != len(order):
        raise ValueError("operating_point_order must contain unique values")
    order_index = {value: index for index, value in enumerate(order)}
    if any(candidate.operating_point not in order_index for candidate in values):
        raise ValueError("candidate operating point is not in operating_point_order")
    if any(candidate.checkpoint < 0 for candidate in values):
        raise ValueError("checkpoint must be non-negative")
    best = None
    for candidate in values:
        score = _finite_score(candidate.patient_macro_jaccard, field="patient_macro_jaccard")
        try:
            distance = abs(float(candidate.operating_point) - float(native_default))
        except (TypeError, ValueError) as error:
            raise ValueError("native_default and operating points must be numeric") from error
        key = (-score, distance, order_index[candidate.operating_point], candidate.checkpoint)
        if best is None or key < best[0]:
            best = (key, candidate)
    assert best is not None
    return best[1]


__all__ = ("SelectionCandidate", "VisitPrediction", "evaluate", "select_joint")
