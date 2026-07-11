"""Protocol prediction records independent of model representation."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import ClassVar

from ._validation import (
    canonical_json,
    enum_member,
    parse_json_object,
    require_int,
    require_public_string,
    require_single_line_public_string,
    strict_fields,
)
from .dataset import SplitName
from .errors import ProtocolValidationError


def _medication_codes(value: Iterable[object], *, field: str, sort: bool) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise ProtocolValidationError(f"{field} must be a collection of medication codes")
    try:
        codes = tuple(require_single_line_public_string(item, field=field) for item in value)
    except TypeError as error:
        raise ProtocolValidationError(
            f"{field} must be a collection of medication codes"
        ) from error
    if len(codes) != len(set(codes)):
        raise ProtocolValidationError(f"{field} medication codes must be unique")
    return tuple(sorted(codes)) if sort else codes


@dataclass(frozen=True, slots=True)
class MedicationScore:
    """Finite score aligned with a predicted medication code."""

    medication_code: str
    score: float

    def __post_init__(self) -> None:
        require_single_line_public_string(
            self.medication_code,
            field="scores.medication_code",
        )
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise ProtocolValidationError("scores.score must be a finite number")
        score = float(self.score)
        if not math.isfinite(score):
            raise ProtocolValidationError("scores.score must be a finite number")
        object.__setattr__(self, "score", score)

    def to_dict(self) -> dict[str, object]:
        return {"medication_code": self.medication_code, "score": self.score}

    @classmethod
    def from_dict(cls, value: object) -> MedicationScore:
        payload = strict_fields(
            value,
            required=("medication_code", "score"),
            context="MedicationScore",
        )
        return cls(medication_code=payload["medication_code"], score=payload["score"])


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    """Visit-level medication set prediction used by protocol evaluation."""

    SCHEMA_VERSION: ClassVar[int] = 1

    patient_id: str
    visit_id: str
    split: SplitName | str
    target_medications: tuple[str, ...]
    predicted_medications: tuple[str, ...]
    scores: tuple[MedicationScore, ...] = ()

    def __post_init__(self) -> None:
        require_public_string(self.patient_id, field="patient_id")
        require_public_string(self.visit_id, field="visit_id")
        object.__setattr__(self, "split", enum_member(SplitName, self.split, field="split"))
        object.__setattr__(
            self,
            "target_medications",
            _medication_codes(self.target_medications, field="target_medications", sort=True),
        )
        object.__setattr__(
            self,
            "predicted_medications",
            _medication_codes(
                self.predicted_medications, field="predicted_medications", sort=False
            ),
        )
        scores = tuple(
            score if isinstance(score, MedicationScore) else MedicationScore.from_dict(score)
            for score in self.scores
        )
        if scores:
            score_codes = tuple(score.medication_code for score in scores)
            if score_codes != self.predicted_medications:
                raise ProtocolValidationError(
                    "scores must align with predicted_medications in the same order"
                )
            ranked = tuple(sorted(scores, key=lambda item: (-item.score, item.medication_code)))
            if scores != ranked:
                raise ProtocolValidationError(
                    "scores must use descending score order with medication-code tie breaking"
                )
        object.__setattr__(self, "scores", scores)

    @classmethod
    def from_scores(
        cls,
        *,
        patient_id: str,
        visit_id: str,
        split: SplitName | str,
        target_medications: Iterable[str],
        medication_scores: Mapping[str, float],
        max_medications: int,
    ) -> PredictionRecord:
        require_int(max_medications, field="max_medications")
        ranked = tuple(
            sorted(
                (MedicationScore(code, score) for code, score in medication_scores.items()),
                key=lambda item: (-item.score, item.medication_code),
            )[:max_medications]
        )
        return cls(
            patient_id=patient_id,
            visit_id=visit_id,
            split=split,
            target_medications=tuple(target_medications),
            predicted_medications=tuple(item.medication_code for item in ranked),
            scores=ranked,
        )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "patient_id": self.patient_id,
            "predicted_medications": list(self.predicted_medications),
            "schema_version": self.SCHEMA_VERSION,
            "split": self.split.value,
            "target_medications": list(self.target_medications),
            "visit_id": self.visit_id,
        }
        if self.scores:
            payload["scores"] = [score.to_dict() for score in self.scores]
        return payload

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> PredictionRecord:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "patient_id",
                "visit_id",
                "split",
                "target_medications",
                "predicted_medications",
            ),
            optional=("scores",),
            context="PredictionRecord",
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ProtocolValidationError(
                f"PredictionRecord schema_version must be {cls.SCHEMA_VERSION}"
            )
        targets = payload["target_medications"]
        predictions = payload["predicted_medications"]
        scores = payload.get("scores", [])
        if not isinstance(targets, list):
            raise ProtocolValidationError("target_medications must be a list")
        if not isinstance(predictions, list):
            raise ProtocolValidationError("predicted_medications must be a list")
        if not isinstance(scores, list):
            raise ProtocolValidationError("scores must be a list")
        return cls(
            patient_id=payload["patient_id"],
            visit_id=payload["visit_id"],
            split=payload["split"],
            target_medications=tuple(targets),
            predicted_medications=tuple(predictions),
            scores=tuple(MedicationScore.from_dict(item) for item in scores),
        )

    @classmethod
    def from_json(cls, text: str) -> PredictionRecord:
        return cls.from_dict(parse_json_object(text, context="PredictionRecord"))


__all__ = ("MedicationScore", "PredictionRecord")
