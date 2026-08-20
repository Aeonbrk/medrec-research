"""Comparison Protocol v1.1 amendment and method qualification profiles."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    enum_member,
    parse_json_object,
    require_identifier,
    require_int,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
)
from .errors import ProtocolValidationError

SAFE_DRUG_REPOSITORY = "https://github.com/ycq091044/SafeDrug"
SAFE_DRUG_MAIN_REVISION = "88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a"
MOLEREC_REPOSITORY = "https://github.com/yangnianzu0515/MoleRec"
MOLEREC_REVISION = "dd5afaf0a503fd3de3229f86ec7f26b345d10e3a"
MOLEREC_SAFEDRUG_LINEAGE_REVISION = "c7218d0976e5ee5588aeaf5bdbc86b338126bba5"

REQUIRED_OUTCOMES = (
    "ddi_rate",
    "jaccard",
    "f1",
    "prauc",
    "average_medication_count",
)


class DecoderClass(StrEnum):
    SCORE_THRESHOLD = "score_threshold"
    STRUCTURAL_SEQUENCE = "structural_sequence"


class SelectionSplit(StrEnum):
    VALIDATION = "validation"
    TEST = "test"


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ProtocolValidationError(f"{field} must be a finite number")
    return result


@dataclass(frozen=True, slots=True)
class ThresholdSelectionRule:
    """Validation-only threshold selection with a bounded trial allowance."""

    selection_split: SelectionSplit | str = SelectionSplit.VALIDATION
    selection_metric: str = "f1"
    max_trials: int = 1
    trials_used: int = 1
    test_peeking: bool = False
    stopping_rule: str = "predeclared"
    seed_policy: str = "pinned"
    rule_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        split = enum_member(SelectionSplit, self.selection_split, field="threshold.selection_split")
        object.__setattr__(self, "selection_split", split)
        require_identifier(self.selection_metric, field="threshold.selection_metric")
        if self.selection_metric not in {"ddi_rate", "jaccard", "f1", "prauc"}:
            raise ProtocolValidationError("threshold.selection_metric is not a registered outcome")
        require_int(self.max_trials, field="threshold.max_trials", minimum=1)
        require_int(self.trials_used, field="threshold.trials_used", minimum=0)
        if self.trials_used > self.max_trials:
            raise ProtocolValidationError("threshold trials_used exceeds max_trials")
        if type(self.test_peeking) is not bool:
            raise ProtocolValidationError("threshold.test_peeking must be boolean")
        if self.selection_split is not SelectionSplit.VALIDATION or self.test_peeking:
            raise ProtocolValidationError("threshold selection must use validation data only")
        require_single_line_public_string(self.stopping_rule, field="threshold.stopping_rule")
        require_single_line_public_string(self.seed_policy, field="threshold.seed_policy")
        expected = content_sha256(self._protected_payload())
        if self.rule_sha256:
            require_sha256(self.rule_sha256, field="threshold.rule_sha256")
            if self.rule_sha256 != expected:
                raise ProtocolValidationError("threshold.rule_sha256 does not match rule content")
        else:
            object.__setattr__(self, "rule_sha256", expected)

    def _protected_payload(self) -> dict[str, object]:
        return {
            "max_trials": self.max_trials,
            "selection_metric": self.selection_metric,
            "selection_split": self.selection_split.value,
            "seed_policy": self.seed_policy,
            "stopping_rule": self.stopping_rule,
            "test_peeking": self.test_peeking,
            "trials_used": self.trials_used,
        }

    @property
    def is_valid(self) -> bool:
        return self.selection_split is SelectionSplit.VALIDATION and not self.test_peeking

    def to_dict(self) -> dict[str, object]:
        return {
            **self._protected_payload(),
            "kind": "threshold_selection_rule",
            "rule_sha256": self.rule_sha256,
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def from_dict(cls, value: object) -> ThresholdSelectionRule:
        payload = strict_fields(
            value,
            required=(
                "kind",
                "max_trials",
                "rule_sha256",
                "schema_version",
                "seed_policy",
                "selection_metric",
                "selection_split",
                "stopping_rule",
                "test_peeking",
                "trials_used",
            ),
            context="ThresholdSelectionRule",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "threshold_selection_rule"
        ):
            raise ProtocolValidationError("ThresholdSelectionRule schema or kind is invalid")
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class AdaptationBudget:
    """Equal, content-addressed method adaptation allowance."""

    selection_metric: str = "f1"
    max_trials: int = 1
    max_compute_units: int = 1
    stopping_rule: str = "predeclared"
    seed_policy: str = "pinned"
    mechanical_integration: bool = True
    trials_used: int = 0
    compute_units_used: int = 0
    budget_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.selection_metric, field="budget.selection_metric")
        if self.selection_metric not in {"ddi_rate", "jaccard", "f1", "prauc"}:
            raise ProtocolValidationError("budget.selection_metric is not a registered outcome")
        require_int(self.max_trials, field="budget.max_trials", minimum=1)
        require_int(self.max_compute_units, field="budget.max_compute_units", minimum=1)
        require_int(self.trials_used, field="budget.trials_used", minimum=0)
        require_int(self.compute_units_used, field="budget.compute_units_used", minimum=0)
        if self.trials_used > self.max_trials or self.compute_units_used > self.max_compute_units:
            raise ProtocolValidationError("adaptation budget is exhausted")
        if type(self.mechanical_integration) is not bool:
            raise ProtocolValidationError("budget.mechanical_integration must be boolean")
        require_single_line_public_string(self.stopping_rule, field="budget.stopping_rule")
        require_single_line_public_string(self.seed_policy, field="budget.seed_policy")
        expected = content_sha256(self._protected_payload())
        if self.budget_sha256:
            require_sha256(self.budget_sha256, field="budget.budget_sha256")
            if self.budget_sha256 != expected:
                raise ProtocolValidationError("budget.budget_sha256 does not match budget content")
        else:
            object.__setattr__(self, "budget_sha256", expected)

    def _protected_payload(self) -> dict[str, object]:
        return {
            "compute_units_used": self.compute_units_used,
            "max_compute_units": self.max_compute_units,
            "max_trials": self.max_trials,
            "mechanical_integration": self.mechanical_integration,
            "seed_policy": self.seed_policy,
            "selection_metric": self.selection_metric,
            "stopping_rule": self.stopping_rule,
            "trials_used": self.trials_used,
        }

    @property
    def is_within_budget(self) -> bool:
        return (
            self.trials_used <= self.max_trials
            and self.compute_units_used <= self.max_compute_units
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self._protected_payload(),
            "budget_sha256": self.budget_sha256,
            "kind": "adaptation_budget",
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def from_dict(cls, value: object) -> AdaptationBudget:
        payload = strict_fields(
            value,
            required=(
                "budget_sha256",
                "compute_units_used",
                "kind",
                "max_compute_units",
                "max_trials",
                "mechanical_integration",
                "schema_version",
                "seed_policy",
                "selection_metric",
                "stopping_rule",
                "trials_used",
            ),
            context="AdaptationBudget",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "adaptation_budget"
        ):
            raise ProtocolValidationError("AdaptationBudget schema or kind is invalid")
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class DecoderProfile:
    """One method's unchanged decoder identity under Comparison Mode."""

    method_id: str
    decoder_class: DecoderClass | str
    baseline_core_sha256: str
    data_lineage_revision: str = SAFE_DRUG_MAIN_REVISION
    threshold_rule: ThresholdSelectionRule | None = None
    native_decoder: str = ""
    profile_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.method_id, field="decoder.method_id")
        decoder = enum_member(DecoderClass, self.decoder_class, field="decoder.decoder_class")
        object.__setattr__(self, "decoder_class", decoder)
        require_sha256(self.baseline_core_sha256, field="decoder.baseline_core_sha256")
        require_identifier(self.data_lineage_revision, field="decoder.data_lineage_revision")
        if self.data_lineage_revision == MOLEREC_SAFEDRUG_LINEAGE_REVISION:
            raise ProtocolValidationError(
                "MoleRec source-native c7218d0 lineage cannot satisfy Comparison Protocol v1.1"
            )
        if decoder is DecoderClass.SCORE_THRESHOLD:
            if (
                not isinstance(self.threshold_rule, ThresholdSelectionRule)
                or not self.threshold_rule.is_valid
            ):
                raise ProtocolValidationError(
                    "score_threshold profiles require a valid validation-only threshold rule"
                )
            if not self.native_decoder:
                object.__setattr__(self, "native_decoder", "score-threshold")
        elif self.threshold_rule is not None:
            raise ProtocolValidationError(
                "structural_sequence profiles must not select a threshold"
            )
        if not self.native_decoder:
            raise ProtocolValidationError(
                "decoder.native_decoder must describe the unchanged decoder"
            )
        require_single_line_public_string(self.native_decoder, field="decoder.native_decoder")
        expected = content_sha256(self._protected_payload())
        if self.profile_sha256:
            require_sha256(self.profile_sha256, field="decoder.profile_sha256")
            if self.profile_sha256 != expected:
                raise ProtocolValidationError(
                    "decoder.profile_sha256 does not match profile content"
                )
        else:
            object.__setattr__(self, "profile_sha256", expected)

    def _protected_payload(self) -> dict[str, object]:
        return {
            "baseline_core_sha256": self.baseline_core_sha256,
            "data_lineage_revision": self.data_lineage_revision,
            "decoder_class": self.decoder_class.value,
            "method_id": self.method_id,
            "native_decoder": self.native_decoder,
            "threshold_rule": self.threshold_rule.to_dict() if self.threshold_rule else None,
        }

    @property
    def is_comparison_profile(self) -> bool:
        return self.data_lineage_revision == SAFE_DRUG_MAIN_REVISION

    def to_dict(self) -> dict[str, object]:
        return {
            **self._protected_payload(),
            "kind": "decoder_profile",
            "profile_sha256": self.profile_sha256,
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def from_dict(cls, value: object) -> DecoderProfile:
        payload = strict_fields(
            value,
            required=(
                "baseline_core_sha256",
                "data_lineage_revision",
                "decoder_class",
                "kind",
                "method_id",
                "native_decoder",
                "profile_sha256",
                "schema_version",
                "threshold_rule",
            ),
            context="DecoderProfile",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "decoder_profile"
        ):
            raise ProtocolValidationError("DecoderProfile schema or kind is invalid")
        threshold = payload.pop("threshold_rule")
        payload["threshold_rule"] = (
            ThresholdSelectionRule.from_dict(threshold) if threshold else None
        )
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class IndependentEvaluationInput:
    """Target-free complete prediction coverage for the core evaluator."""

    method_id: str
    expected_visit_digest: str
    prediction_visit_digest: str
    target_join_digest: str
    complete: bool = True
    target_free: bool = True
    evaluator_revision: str = "core-evaluator-v1.1"

    def __post_init__(self) -> None:
        require_identifier(self.method_id, field="evaluation_input.method_id")
        for name in ("expected_visit_digest", "prediction_visit_digest", "target_join_digest"):
            require_sha256(getattr(self, name), field=f"evaluation_input.{name}")
        if type(self.complete) is not bool or type(self.target_free) is not bool:
            raise ProtocolValidationError(
                "evaluation input completeness and target_free must be boolean"
            )
        if not self.complete:
            raise ProtocolValidationError(
                "independent evaluation requires complete prediction coverage"
            )
        if not self.target_free:
            raise ProtocolValidationError("adapter predictions must be target-free")
        require_identifier(self.evaluator_revision, field="evaluation_input.evaluator_revision")

    @property
    def is_independently_evaluable(self) -> bool:
        return self.complete and self.target_free

    def to_dict(self) -> dict[str, object]:
        return {
            "complete": self.complete,
            "evaluator_revision": self.evaluator_revision,
            "expected_visit_digest": self.expected_visit_digest,
            "method_id": self.method_id,
            "prediction_visit_digest": self.prediction_visit_digest,
            "target_free": self.target_free,
            "target_join_digest": self.target_join_digest,
        }

    @classmethod
    def from_dict(cls, value: object) -> IndependentEvaluationInput:
        return cls(
            **strict_fields(
                value,
                required=(
                    "complete",
                    "evaluator_revision",
                    "expected_visit_digest",
                    "method_id",
                    "prediction_visit_digest",
                    "target_free",
                    "target_join_digest",
                ),
                context="IndependentEvaluationInput",
            )
        )


@dataclass(frozen=True, slots=True)
class ComparisonProtocolV1_1:
    """Versioned amendment that owns the five-method comparison semantics."""

    protocol_version: str = "1.1"
    data_lineage_revision: str = SAFE_DRUG_MAIN_REVISION
    required_outcomes: tuple[str, ...] = REQUIRED_OUTCOMES
    uncertainty_procedure: object = (
        ("rounds", 10),
        ("sample_fraction", 0.8),
        ("with_replacement", True),
        ("interval_level", 0.8),
    )
    adaptation_budget: AdaptationBudget = AdaptationBudget()
    decoder_profiles: tuple[DecoderProfile, ...] = ()
    protocol_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        if self.protocol_version != "1.1":
            raise ProtocolValidationError("ComparisonProtocolV1_1 protocol_version must be 1.1")
        require_identifier(self.data_lineage_revision, field="protocol.data_lineage_revision")
        if self.data_lineage_revision != SAFE_DRUG_MAIN_REVISION:
            raise ProtocolValidationError(
                "Comparison Protocol v1.1 must use SafeDrug main processing lineage"
            )
        outcomes = tuple(
            require_identifier(item, field="protocol.required_outcomes")
            for item in self.required_outcomes
        )
        if outcomes != REQUIRED_OUTCOMES:
            raise ProtocolValidationError("Comparison Protocol v1.1 required outcomes are fixed")
        object.__setattr__(self, "required_outcomes", outcomes)
        if not isinstance(self.adaptation_budget, AdaptationBudget):
            raise ProtocolValidationError("protocol.adaptation_budget must be an AdaptationBudget")
        if isinstance(self.uncertainty_procedure, Mapping):
            uncertainty = tuple(sorted(self.uncertainty_procedure.items()))
        else:
            uncertainty = tuple(self.uncertainty_procedure)
        expected_uncertainty = {
            "rounds": 10,
            "sample_fraction": 0.8,
            "with_replacement": True,
            "interval_level": 0.8,
        }
        if dict(uncertainty) != expected_uncertainty:
            raise ProtocolValidationError(
                "protocol uncertainty procedure must use ten-round 80% bootstrap"
            )
        object.__setattr__(
            self,
            "uncertainty_procedure",
            tuple(
                (key, expected_uncertainty[key])
                for key in ("rounds", "sample_fraction", "with_replacement", "interval_level")
            ),
        )
        profiles = tuple(
            item if isinstance(item, DecoderProfile) else DecoderProfile.from_dict(item)
            for item in self.decoder_profiles
        )
        if len({item.method_id for item in profiles}) != len(profiles):
            raise ProtocolValidationError("protocol decoder profile method IDs must be unique")
        if any(not item.is_comparison_profile for item in profiles):
            raise ProtocolValidationError("protocol decoder profiles must use Comparison lineage")
        object.__setattr__(self, "decoder_profiles", profiles)
        expected = content_sha256(self._protected_payload())
        if self.protocol_sha256:
            require_sha256(self.protocol_sha256, field="protocol.protocol_sha256")
            if self.protocol_sha256 != expected:
                raise ProtocolValidationError(
                    "protocol.protocol_sha256 does not match protocol content"
                )
        else:
            object.__setattr__(self, "protocol_sha256", expected)

    def _protected_payload(self) -> dict[str, object]:
        return {
            "adaptation_budget": self.adaptation_budget.to_dict(),
            "data_lineage_revision": self.data_lineage_revision,
            "decoder_profiles": [item.to_dict() for item in self.decoder_profiles],
            "protocol_version": self.protocol_version,
            "required_outcomes": list(self.required_outcomes),
            "uncertainty_procedure": dict(self.uncertainty_procedure),
        }

    @property
    def amendment_sha256(self) -> str:
        return self.protocol_sha256

    def profile_for(self, method_id: str) -> DecoderProfile:
        for profile in self.decoder_profiles:
            if profile.method_id == method_id:
                return profile
        raise KeyError(method_id)

    def validate_evaluation(
        self,
        profile: DecoderProfile,
        evaluation_input: IndependentEvaluationInput,
    ) -> None:
        if profile not in self.decoder_profiles:
            raise ProtocolValidationError("decoder profile is not bound to this protocol amendment")
        if evaluation_input.method_id != profile.method_id:
            raise ProtocolValidationError(
                "independent evaluation method does not match decoder profile"
            )
        if not evaluation_input.is_independently_evaluable:
            raise ProtocolValidationError(
                "comparison qualification requires independent evaluation"
            )
        if not self.adaptation_budget.is_within_budget:
            raise ProtocolValidationError("comparison qualification exceeds the adaptation budget")

    def to_dict(self) -> dict[str, object]:
        return {
            **self._protected_payload(),
            "kind": "comparison_protocol_v1_1",
            "protocol_sha256": self.protocol_sha256,
            "schema_version": self.SCHEMA_VERSION,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, value: object) -> ComparisonProtocolV1_1:
        payload = strict_fields(
            value,
            required=(
                "adaptation_budget",
                "data_lineage_revision",
                "decoder_profiles",
                "kind",
                "protocol_sha256",
                "protocol_version",
                "required_outcomes",
                "schema_version",
                "uncertainty_procedure",
            ),
            context="ComparisonProtocolV1_1",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "comparison_protocol_v1_1"
        ):
            raise ProtocolValidationError("ComparisonProtocolV1_1 schema or kind is invalid")
        profiles = payload.pop("decoder_profiles")
        if not isinstance(profiles, list):
            raise ProtocolValidationError("ComparisonProtocolV1_1 decoder_profiles must be a list")
        payload["decoder_profiles"] = tuple(DecoderProfile.from_dict(item) for item in profiles)
        payload["adaptation_budget"] = AdaptationBudget.from_dict(payload["adaptation_budget"])
        return cls(**payload)

    @classmethod
    def from_json(cls, text: str) -> ComparisonProtocolV1_1:
        return cls.from_dict(parse_json_object(text, context="ComparisonProtocolV1_1"))


ComparisonMethodProfile = DecoderProfile
ComparisonProfile = DecoderProfile
ProtocolV1_1 = ComparisonProtocolV1_1


__all__ = (
    "AdaptationBudget",
    "ComparisonMethodProfile",
    "ComparisonProfile",
    "ComparisonProtocolV1_1",
    "DecoderClass",
    "DecoderProfile",
    "IndependentEvaluationInput",
    "ProtocolV1_1",
    "SelectionSplit",
    "ThresholdSelectionRule",
)
