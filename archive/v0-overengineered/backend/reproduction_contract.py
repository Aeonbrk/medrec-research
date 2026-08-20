"""Immutable, public-safe contracts for source-native reproduction work.

The records in this module deliberately do not reuse :mod:`run_record`.  A
reproduction packet describes source-native evidence and a researcher's
decision; it is not a Comparison Mode result and it does not authorize a
remote action.  Scientific fields are content addressed, while presentation
metadata (labels, notes, links, and timestamps) is intentionally left out of
the protected digest.
"""

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
SAFE_DRUG_MODEL_IDS = ("leap", "retain", "gamenet", "safedrug")


class AttemptStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    INVALID = "invalid"


class AttemptValidity(StrEnum):
    USABLE = "usable"
    USABLE_WITH_LIMITS = "usable-with-limits"
    INVALID = "invalid"


class EvidenceConclusion(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class H2Action(StrEnum):
    GO = "go"
    REVISE = "revise"
    KILL = "kill"
    HOLD = "hold"


class Stage(StrEnum):
    """The three separately attributable MoleRec evidence stages."""

    CHECKPOINT_REPLAY = "checkpoint_replay"
    TRAINING_REPRODUCTION = "training_reproduction"
    COMPARISON_QUALIFICATION = "comparison_qualification"

    # Short aliases are useful to callers while the serialized values remain
    # explicit and unambiguous.
    REPLAY = "checkpoint_replay"
    TRAINING = "training_reproduction"
    COMPARISON = "comparison_qualification"


_STAGE_ALIASES = {
    "replay": Stage.CHECKPOINT_REPLAY,
    "checkpoint": Stage.CHECKPOINT_REPLAY,
    "checkpoint_replay": Stage.CHECKPOINT_REPLAY,
    "training": Stage.TRAINING_REPRODUCTION,
    "training_reproduction": Stage.TRAINING_REPRODUCTION,
    "comparison": Stage.COMPARISON_QUALIFICATION,
    "comparison_qualification": Stage.COMPARISON_QUALIFICATION,
}


def _public_value(value: object, *, field_name: str) -> object:
    """Validate and freeze JSON-safe public metadata recursively."""

    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProtocolValidationError(f"{field_name} must contain finite numbers")
        return value
    if isinstance(value, str):
        return require_single_line_public_string(value, field=field_name)
    if isinstance(value, Mapping):
        items: list[tuple[str, object]] = []
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProtocolValidationError(f"{field_name} keys must be strings")
            safe_key = require_identifier(key, field=f"{field_name} key")
            items.append((safe_key, _public_value(item, field_name=f"{field_name}.{safe_key}")))
        return tuple(sorted(items))
    if isinstance(value, (tuple, list)):
        return tuple(_public_value(item, field_name=field_name) for item in value)
    raise ProtocolValidationError(f"{field_name} must contain public JSON values")


def _thaw(value: object) -> object:
    if isinstance(value, tuple):
        if all(
            isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
            for item in value
        ):
            return {item[0]: _thaw(item[1]) for item in value}
        return [_thaw(item) for item in value]
    return value


def _string_tuple(value: object, *, field_name: str, identifiers: bool = False) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (tuple, list)):
        raise ProtocolValidationError(f"{field_name} must be a list")
    result = tuple(
        (
            require_identifier(item, field=field_name)
            if identifiers
            else require_single_line_public_string(item, field=field_name)
        )
        for item in value
    )
    if len(result) != len(set(result)):
        raise ProtocolValidationError(f"{field_name} entries must be unique")
    return result


def _digest_tuple(value: object, *, field_name: str) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        pairs = value.items()
    elif isinstance(value, (tuple, list)):
        pairs = value
    else:
        raise ProtocolValidationError(f"{field_name} must be an object or list of pairs")
    result: list[tuple[str, str]] = []
    for item in pairs:
        if isinstance(value, Mapping):
            name, digest = item
        else:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ProtocolValidationError(f"{field_name} entries must be pairs")
            name, digest = item
        result.append(
            (
                require_identifier(name, field=f"{field_name}.name"),
                require_sha256(digest, field=f"{field_name}.{name}"),
            )
        )
    if not result or len({name for name, _ in result}) != len(result):
        raise ProtocolValidationError(f"{field_name} entries must be non-empty and unique")
    return tuple(result)


def _digest_map(value: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return {name: digest for name, digest in value}


def _interval_tuple(value: object, *, field_name: str) -> tuple[tuple[str, float, float], ...]:
    if isinstance(value, Mapping):
        pairs = value.items()
    elif isinstance(value, (tuple, list)):
        pairs = value
    else:
        raise ProtocolValidationError(f"{field_name} must be an object or list")
    result: list[tuple[str, float, float]] = []
    for item in pairs:
        if isinstance(value, Mapping):
            metric, bounds = item
        else:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ProtocolValidationError(f"{field_name} entries must be metric/bounds pairs")
            metric, bounds = item
        metric = require_identifier(metric, field=f"{field_name}.metric")
        if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
            raise ProtocolValidationError(
                f"{field_name}.{metric} must contain lower and upper bounds"
            )
        lower, upper = bounds
        if (
            isinstance(lower, bool)
            or isinstance(upper, bool)
            or not isinstance(lower, (int, float))
            or not isinstance(upper, (int, float))
        ):
            raise ProtocolValidationError(f"{field_name}.{metric} bounds must be numbers")
        lower = float(lower)
        upper = float(upper)
        if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
            raise ProtocolValidationError(f"{field_name}.{metric} bounds are invalid")
        result.append((metric, lower, upper))
    if len({metric for metric, _, _ in result}) != len(result):
        raise ProtocolValidationError(f"{field_name} metrics must be unique")
    required_order = {metric: index for index, metric in enumerate(REQUIRED_OUTCOMES)}
    result.sort(key=lambda item: (required_order.get(item[0], len(required_order)), item[0]))
    return tuple(result)


def _interval_map(value: tuple[tuple[str, float, float], ...]) -> dict[str, list[float]]:
    return {metric: [lower, upper] for metric, lower, upper in value}


def _required_interval_check(
    intervals: tuple[tuple[str, float, float], ...], *, field_name: str
) -> None:
    names = {metric for metric, _, _ in intervals}
    missing = [metric for metric in REQUIRED_OUTCOMES if metric not in names]
    if missing:
        raise ProtocolValidationError(
            f"{field_name} missing required metric interval(s): {', '.join(missing)}"
        )


def _normalize_stage(value: object, *, field_name: str = "stage") -> Stage:
    if isinstance(value, Stage):
        return value
    try:
        return _STAGE_ALIASES[str(value)]
    except (KeyError, TypeError) as error:
        choices = ", ".join(
            item.value
            for item in (
                Stage.CHECKPOINT_REPLAY,
                Stage.TRAINING_REPRODUCTION,
                Stage.COMPARISON_QUALIFICATION,
            )
        )
        raise ProtocolValidationError(f"{field_name} must be one of: {choices}") from error


def _check_public_links(value: object, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        value = (value,)
    return _string_tuple(value, field_name=field_name)


@dataclass(frozen=True, slots=True)
class ModelAnnex:
    """One source-native SafeDrug model's protected scientific behavior."""

    model_id: str
    metric_intervals: object = ()
    source_revision: str = SAFE_DRUG_MAIN_REVISION
    source_branch: str = "main"
    source_repository: str = SAFE_DRUG_REPOSITORY
    preprocessing: object = "source-native"
    eligible_visits: object = "source-native"
    split: object = "source-native"
    feature_access: object = "source-native"
    training: object = "source-native"
    checkpoint: object = "source-native"
    prediction: object = "source-native"
    threshold_or_decoder: object = "source-native"
    required_outcomes: tuple[str, ...] = REQUIRED_OUTCOMES
    target: str = "source-native-reproduction"
    mode: str = "reproduction"
    display_name: str | None = None
    notes: str = ""
    evidence_urls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        model_id = require_identifier(self.model_id, field="model_id")
        object.__setattr__(self, "model_id", model_id)
        require_single_line_public_string(self.source_repository, field="source_repository")
        require_single_line_public_string(self.source_branch, field="source_branch")
        self._check_revision()
        if self.source_revision != SAFE_DRUG_MAIN_REVISION:
            raise ProtocolValidationError(
                "SafeDrug model annex source_revision must use the pinned main commit"
            )
        if self.source_branch != "main":
            raise ProtocolValidationError("SafeDrug model annex source_branch must be main")
        if self.source_repository != SAFE_DRUG_REPOSITORY:
            raise ProtocolValidationError(
                "SafeDrug model annex source_repository is not the pinned SafeDrug source"
            )
        if self.mode != "reproduction":
            raise ProtocolValidationError("ModelAnnex mode must be reproduction")
        require_single_line_public_string(self.target, field="target")
        required = _string_tuple(
            self.required_outcomes, field_name="required_outcomes", identifiers=True
        )
        if not set(REQUIRED_OUTCOMES) <= set(required):
            missing = [item for item in REQUIRED_OUTCOMES if item not in required]
            raise ProtocolValidationError(f"required_outcomes missing: {', '.join(missing)}")
        object.__setattr__(self, "required_outcomes", required)
        intervals = _interval_tuple(self.metric_intervals, field_name="metric_intervals")
        _required_interval_check(intervals, field_name="metric_intervals")
        object.__setattr__(self, "metric_intervals", intervals)
        for name in (
            "preprocessing",
            "eligible_visits",
            "split",
            "feature_access",
            "training",
            "checkpoint",
            "prediction",
            "threshold_or_decoder",
        ):
            object.__setattr__(self, name, _public_value(getattr(self, name), field_name=name))
        if self.display_name is not None:
            require_single_line_public_string(self.display_name, field="display_name")
        if self.notes:
            require_single_line_public_string(self.notes, field="notes")
        object.__setattr__(
            self,
            "evidence_urls",
            _check_public_links(self.evidence_urls, field_name="evidence_urls"),
        )

    def _check_revision(self) -> None:
        if (
            not isinstance(self.source_revision, str)
            or len(self.source_revision) != 40
            or any(char not in "0123456789abcdef" for char in self.source_revision)
        ):
            raise ProtocolValidationError("source_revision must be an immutable commit")

    @property
    def acceptance_intervals(self) -> dict[str, list[float]]:
        return _interval_map(self.metric_intervals)

    @property
    def protected_payload(self) -> dict[str, object]:
        return {
            "eligible_visits": _thaw(self.eligible_visits),
            "feature_access": _thaw(self.feature_access),
            "metric_intervals": _interval_map(self.metric_intervals),
            "mode": self.mode,
            "model_id": self.model_id,
            "prediction": _thaw(self.prediction),
            "preprocessing": _thaw(self.preprocessing),
            "required_outcomes": list(self.required_outcomes),
            "source_branch": self.source_branch,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "split": _thaw(self.split),
            "target": self.target,
            "threshold_or_decoder": _thaw(self.threshold_or_decoder),
            "training": _thaw(self.training),
            "checkpoint": _thaw(self.checkpoint),
        }

    @property
    def annex_sha256(self) -> str:
        return content_sha256(self.protected_payload)

    @property
    def content_sha256(self) -> str:
        return self.annex_sha256

    def to_dict(self) -> dict[str, object]:
        return {
            "checkpoint": _thaw(self.checkpoint),
            "display_name": self.display_name,
            "eligible_visits": _thaw(self.eligible_visits),
            "evidence_urls": list(self.evidence_urls),
            "feature_access": _thaw(self.feature_access),
            "metric_intervals": _interval_map(self.metric_intervals),
            "mode": self.mode,
            "model_id": self.model_id,
            "notes": self.notes,
            "prediction": _thaw(self.prediction),
            "preprocessing": _thaw(self.preprocessing),
            "required_outcomes": list(self.required_outcomes),
            "source_branch": self.source_branch,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "split": _thaw(self.split),
            "target": self.target,
            "threshold_or_decoder": _thaw(self.threshold_or_decoder),
            "training": _thaw(self.training),
            "annex_sha256": self.annex_sha256,
        }

    @classmethod
    def from_dict(cls, value: object) -> ModelAnnex:
        payload = strict_fields(
            value,
            required=("model_id", "metric_intervals"),
            optional=(
                "source_revision",
                "source_branch",
                "source_repository",
                "preprocessing",
                "eligible_visits",
                "split",
                "feature_access",
                "training",
                "checkpoint",
                "prediction",
                "threshold_or_decoder",
                "required_outcomes",
                "target",
                "mode",
                "display_name",
                "notes",
                "evidence_urls",
                "annex_sha256",
            ),
            context="ModelAnnex",
        )
        expected = payload.pop("annex_sha256", None)
        result = cls(**payload)
        if expected is not None and expected != result.annex_sha256:
            raise ProtocolValidationError("ModelAnnex annex_sha256 does not match protected fields")
        return result

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> ModelAnnex:
        return cls.from_dict(parse_json_object(text, context="ModelAnnex"))


@dataclass(frozen=True, slots=True)
class SafeDrugBatchContract:
    """Shared H1 scientific identity for the four SafeDrug model lanes."""

    model_annexes: tuple[ModelAnnex, ...] = ()
    data_lineage: object = "source-native"
    environment_identity: object = "source-native"
    evaluation_semantics: object = "ten-round-80-percent-test-bootstrap"
    resource_ceiling: object = ()
    repair_budget: object = ()
    stopping_rules: object = ()
    non_waivable_boundaries: tuple[str, ...] = (
        "authority",
        "privacy",
        "legality",
        "resource",
    )
    source_repository: str = SAFE_DRUG_REPOSITORY
    source_revision: str = SAFE_DRUG_MAIN_REVISION
    source_branch: str = "main"
    batch_id: str = "safedrug-batch"
    display_name: str | None = None
    notes: str = ""
    evidence_urls: tuple[str, ...] = ()
    created_at: str = ""
    contract_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        annexes = tuple(
            item if isinstance(item, ModelAnnex) else ModelAnnex.from_dict(item)
            for item in self.model_annexes
        )
        if len(annexes) != len(SAFE_DRUG_MODEL_IDS):
            raise ProtocolValidationError(
                "SafeDrug batch contract must contain exactly four model annexes"
            )
        if tuple(item.model_id for item in annexes) != SAFE_DRUG_MODEL_IDS:
            raise ProtocolValidationError(
                "SafeDrug model annexes must use the ordered pinned model IDs"
            )
        object.__setattr__(self, "model_annexes", annexes)
        if (
            self.source_repository != SAFE_DRUG_REPOSITORY
            or self.source_branch != "main"
            or self.source_revision != SAFE_DRUG_MAIN_REVISION
        ):
            raise ProtocolValidationError("SafeDrug batch source must be pinned to main@88ce5c3")
        require_single_line_public_string(self.source_repository, field="source_repository")
        require_single_line_public_string(self.source_branch, field="source_branch")
        self._check_revision()
        require_identifier(self.batch_id, field="batch_id")
        for name in (
            "data_lineage",
            "environment_identity",
            "evaluation_semantics",
            "resource_ceiling",
            "repair_budget",
            "stopping_rules",
        ):
            object.__setattr__(self, name, _public_value(getattr(self, name), field_name=name))
        boundaries = _string_tuple(
            self.non_waivable_boundaries, field_name="non_waivable_boundaries", identifiers=True
        )
        if not boundaries:
            raise ProtocolValidationError("non_waivable_boundaries must not be empty")
        object.__setattr__(self, "non_waivable_boundaries", boundaries)
        if self.display_name is not None:
            require_single_line_public_string(self.display_name, field="display_name")
        if self.notes:
            require_single_line_public_string(self.notes, field="notes")
        object.__setattr__(
            self,
            "evidence_urls",
            _check_public_links(self.evidence_urls, field_name="evidence_urls"),
        )
        if self.created_at:
            require_single_line_public_string(self.created_at, field="created_at")
        expected = self.compute_contract_sha256()
        if self.contract_sha256:
            require_sha256(self.contract_sha256, field="contract_sha256")
            if self.contract_sha256 != expected:
                raise ProtocolValidationError(
                    "contract_sha256 does not match protected scientific fields"
                )
        else:
            object.__setattr__(self, "contract_sha256", expected)

    def _check_revision(self) -> None:
        if (
            not isinstance(self.source_revision, str)
            or len(self.source_revision) != 40
            or any(char not in "0123456789abcdef" for char in self.source_revision)
        ):
            raise ProtocolValidationError("source_revision must be an immutable commit")

    @property
    def dataset_lineage(self) -> object:
        return _thaw(self.data_lineage)

    @property
    def environment(self) -> object:
        return _thaw(self.environment_identity)

    @property
    def protected_payload(self) -> dict[str, object]:
        return {
            "batch_id": self.batch_id,
            "data_lineage": _thaw(self.data_lineage),
            "environment_identity": _thaw(self.environment_identity),
            "evaluation_semantics": _thaw(self.evaluation_semantics),
            "model_annexes": [annex.protected_payload for annex in self.model_annexes],
            "non_waivable_boundaries": list(self.non_waivable_boundaries),
            "repair_budget": _thaw(self.repair_budget),
            "resource_ceiling": _thaw(self.resource_ceiling),
            "source_branch": self.source_branch,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "stopping_rules": _thaw(self.stopping_rules),
            "schema_version": self.SCHEMA_VERSION,
        }

    def compute_contract_sha256(self) -> str:
        return content_sha256(self.protected_payload)

    @property
    def content_sha256(self) -> str:
        return self.contract_sha256

    def is_current(self, digest: str | None = None) -> bool:
        """Return whether ``digest`` (or this record) matches current content."""

        return self.contract_sha256 == self.compute_contract_sha256() and (
            digest is None or digest == self.contract_sha256
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "batch_id": self.batch_id,
            "contract_sha256": self.contract_sha256,
            "created_at": self.created_at,
            "data_lineage": _thaw(self.data_lineage),
            "display_name": self.display_name,
            "environment_identity": _thaw(self.environment_identity),
            "evidence_urls": list(self.evidence_urls),
            "evaluation_semantics": _thaw(self.evaluation_semantics),
            "model_annexes": [annex.to_dict() for annex in self.model_annexes],
            "non_waivable_boundaries": list(self.non_waivable_boundaries),
            "notes": self.notes,
            "repair_budget": _thaw(self.repair_budget),
            "resource_ceiling": _thaw(self.resource_ceiling),
            "schema_version": self.SCHEMA_VERSION,
            "source_branch": self.source_branch,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "stopping_rules": _thaw(self.stopping_rules),
        }

    @classmethod
    def create(cls, **kwargs: object) -> SafeDrugBatchContract:
        """Create a contract while accepting common naming aliases."""

        aliases = {
            "annexes": "model_annexes",
            "dataset_lineage": "data_lineage",
            "environment": "environment_identity",
            "evaluation_protocol": "evaluation_semantics",
            "resource_limits": "resource_ceiling",
            "stopping": "stopping_rules",
            "owner_boundaries": "non_waivable_boundaries",
        }
        normalized = dict(kwargs)
        for alias, target in aliases.items():
            if alias in normalized and target not in normalized:
                normalized[target] = normalized.pop(alias)
        return cls(**normalized)

    @classmethod
    def from_dict(cls, value: object) -> SafeDrugBatchContract:
        payload = strict_fields(
            value,
            required=(
                "model_annexes",
                "data_lineage",
                "environment_identity",
                "evaluation_semantics",
                "resource_ceiling",
                "repair_budget",
                "stopping_rules",
                "non_waivable_boundaries",
                "source_repository",
                "source_revision",
                "source_branch",
                "batch_id",
                "display_name",
                "notes",
                "evidence_urls",
                "created_at",
                "contract_sha256",
                "schema_version",
            ),
            context="SafeDrugBatchContract",
        )
        if payload.pop("schema_version") != cls.SCHEMA_VERSION:
            raise ProtocolValidationError("SafeDrugBatchContract schema_version must be 1")
        annexes = payload.pop("model_annexes")
        if not isinstance(annexes, list):
            raise ProtocolValidationError("SafeDrugBatchContract model_annexes must be a list")
        payload["model_annexes"] = tuple(ModelAnnex.from_dict(item) for item in annexes)
        return cls(**payload)

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> SafeDrugBatchContract:
        return cls.from_dict(parse_json_object(text, context="SafeDrugBatchContract"))


@dataclass(frozen=True, slots=True)
class H1Approval:
    """Researcher approval freezing one current SafeDrug contract."""

    contract_sha256: str
    owner: str
    decision: str = "accepted"
    rationale: str = ""
    approved_at: str = ""
    approval_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_sha256(self.contract_sha256, field="h1.contract_sha256")
        require_identifier(self.owner, field="h1.owner")
        if self.decision != "accepted":
            raise ProtocolValidationError("H1 decision must be accepted")
        if self.rationale:
            require_single_line_public_string(self.rationale, field="h1.rationale")
        require_single_line_public_string(
            self.approved_at, field="h1.approved_at"
        ) if self.approved_at else None
        expected = content_sha256(self._protected_payload())
        if self.approval_sha256:
            require_sha256(self.approval_sha256, field="h1.approval_sha256")
            if self.approval_sha256 != expected:
                raise ProtocolValidationError("h1.approval_sha256 does not match approval fields")
        else:
            object.__setattr__(self, "approval_sha256", expected)

    def _protected_payload(self) -> dict[str, str]:
        return {
            "contract_sha256": self.contract_sha256,
            "decision": self.decision,
            "owner": self.owner,
        }

    @classmethod
    def create(
        cls,
        contract: SafeDrugBatchContract,
        *,
        owner: str | None = None,
        researcher: str | None = None,
        decision: str = "accepted",
        rationale: str = "",
        approved_at: str = "",
    ) -> H1Approval:
        if not isinstance(contract, SafeDrugBatchContract) or not contract.is_current():
            raise ProtocolValidationError("H1 requires a complete current SafeDrugBatchContract")
        selected_owner = owner if owner is not None else researcher
        if selected_owner is None:
            raise ProtocolValidationError("H1 requires a named owner")
        return cls(
            contract_sha256=contract.contract_sha256,
            owner=selected_owner,
            decision=decision,
            rationale=rationale,
            approved_at=approved_at,
        )

    def is_current(self, contract: SafeDrugBatchContract | str) -> bool:
        digest = (
            contract.contract_sha256 if isinstance(contract, SafeDrugBatchContract) else contract
        )
        return self.contract_sha256 == digest and (
            not isinstance(contract, SafeDrugBatchContract) or contract.is_current()
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "approval_sha256": self.approval_sha256,
            "approved_at": self.approved_at,
            "contract_sha256": self.contract_sha256,
            "decision": self.decision,
            "kind": "h1_approval",
            "owner": self.owner,
            "rationale": self.rationale,
            "schema_version": self.SCHEMA_VERSION,
        }

    @classmethod
    def from_dict(cls, value: object) -> H1Approval:
        payload = strict_fields(
            value,
            required=(
                "approval_sha256",
                "approved_at",
                "contract_sha256",
                "decision",
                "kind",
                "owner",
                "rationale",
                "schema_version",
            ),
            context="H1Approval",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "h1_approval"
        ):
            raise ProtocolValidationError("H1Approval schema or kind is invalid")
        return cls(**payload)

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> H1Approval:
        return cls.from_dict(parse_json_object(text, context="H1Approval"))


@dataclass(frozen=True, slots=True)
class RepairEvidence:
    """Public-safe record of one bounded compatibility or endpoint repair."""

    repair_id: str
    kind: str
    description: str
    artifact_changed: bool = False
    before_sha256: str | None = None
    after_sha256: str | None = None
    equivalence_evidence_sha256: str | None = None
    evidence_sha256: str | None = None
    budget_units: int = 1
    endpoint: str | None = None

    def __post_init__(self) -> None:
        require_identifier(self.repair_id, field="repair_id")
        require_identifier(self.kind, field="repair.kind")
        require_single_line_public_string(self.description, field="repair.description")
        if type(self.artifact_changed) is not bool:
            raise ProtocolValidationError("repair.artifact_changed must be a boolean")
        require_int(self.budget_units, field="repair.budget_units", minimum=1)
        for name in (
            "before_sha256",
            "after_sha256",
            "equivalence_evidence_sha256",
            "evidence_sha256",
        ):
            value = getattr(self, name)
            if value is not None:
                require_sha256(value, field=f"repair.{name}")
        if self.artifact_changed and (self.before_sha256 is None or self.after_sha256 is None):
            raise ProtocolValidationError(
                "artifact-changing repair requires before and after digests"
            )
        if self.endpoint is not None:
            require_single_line_public_string(self.endpoint, field="repair.endpoint")

    @property
    def changes_artifact(self) -> bool:
        return self.artifact_changed

    @property
    def has_equivalence_evidence(self) -> bool:
        return self.equivalence_evidence_sha256 is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "after_sha256": self.after_sha256,
            "artifact_changed": self.artifact_changed,
            "before_sha256": self.before_sha256,
            "budget_units": self.budget_units,
            "description": self.description,
            "endpoint": self.endpoint,
            "equivalence_evidence_sha256": self.equivalence_evidence_sha256,
            "evidence_sha256": self.evidence_sha256,
            "kind": self.kind,
            "repair_id": self.repair_id,
        }

    @classmethod
    def from_dict(cls, value: object) -> RepairEvidence:
        return cls(
            **strict_fields(
                value,
                required=(
                    "repair_id",
                    "kind",
                    "description",
                    "artifact_changed",
                    "before_sha256",
                    "after_sha256",
                    "equivalence_evidence_sha256",
                    "evidence_sha256",
                    "budget_units",
                    "endpoint",
                ),
                context="RepairEvidence",
            )
        )


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    """One isolated lane attempt and its QA/QC boundary."""

    attempt_id: str
    lane_id: str
    contract_sha256: str
    status: AttemptStatus | str = AttemptStatus.COMPLETED
    validity: AttemptValidity | str = AttemptValidity.USABLE
    qa_qc: object = ()
    artifact_digests: tuple[tuple[str, str], ...] = ()
    repair_evidence: tuple[RepairEvidence, ...] = ()
    deviations: tuple[str, ...] = ()
    required_outcomes: tuple[str, ...] = REQUIRED_OUTCOMES
    outcomes: object = ()
    uncertainty: object = ()
    privacy_ok: bool = True
    authority_ok: bool = True
    resource_ok: bool = True
    source_revision: str = SAFE_DRUG_MAIN_REVISION
    started_at: str = ""
    finished_at: str = ""
    reason: str = ""
    attempt_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.attempt_id, field="attempt_id")
        require_identifier(self.lane_id, field="lane_id")
        require_sha256(self.contract_sha256, field="attempt.contract_sha256")
        status = enum_member(AttemptStatus, self.status, field="attempt.status")
        validity = enum_member(AttemptValidity, self.validity, field="attempt.validity")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "validity", validity)
        if status in {AttemptStatus.INVALID, AttemptStatus.FAILED, AttemptStatus.BLOCKED}:
            validity = AttemptValidity.INVALID
            object.__setattr__(self, "validity", validity)
        for name in ("privacy_ok", "authority_ok", "resource_ok"):
            if type(getattr(self, name)) is not bool:
                raise ProtocolValidationError(f"attempt.{name} must be a boolean")
        if not self.privacy_ok or not self.authority_ok or not self.resource_ok:
            object.__setattr__(self, "validity", AttemptValidity.INVALID)
        required = _string_tuple(
            self.required_outcomes, field_name="attempt.required_outcomes", identifiers=True
        )
        if not set(REQUIRED_OUTCOMES) <= set(required):
            raise ProtocolValidationError(
                "attempt.required_outcomes must contain all required outcomes"
            )
        object.__setattr__(self, "required_outcomes", required)
        object.__setattr__(self, "qa_qc", _public_value(self.qa_qc, field_name="qa_qc"))
        artifacts = (
            _digest_tuple(self.artifact_digests, field_name="artifact_digests")
            if self.artifact_digests
            else ()
        )
        object.__setattr__(self, "artifact_digests", artifacts)
        repairs = tuple(
            item if isinstance(item, RepairEvidence) else RepairEvidence.from_dict(item)
            for item in self.repair_evidence
        )
        object.__setattr__(self, "repair_evidence", repairs)
        deviations = (
            _string_tuple(self.deviations, field_name="deviations") if self.deviations else ()
        )
        if deviations and not repairs:
            raise ProtocolValidationError("attempt deviations require repair evidence")
        object.__setattr__(self, "deviations", deviations)
        for name in ("outcomes", "uncertainty"):
            normalized = (
                _public_value(getattr(self, name), field_name=f"attempt.{name}")
                if getattr(self, name)
                else ()
            )
            if normalized and isinstance(normalized, tuple):
                values = _thaw(normalized)
                if isinstance(values, dict):
                    missing = [item for item in REQUIRED_OUTCOMES if item not in values]
                    if missing:
                        raise ProtocolValidationError(
                            f"attempt.{name} missing required outcomes: {', '.join(missing)}"
                        )
            object.__setattr__(self, name, normalized)
        if self.source_revision != SAFE_DRUG_MAIN_REVISION:
            raise ProtocolValidationError(
                "attempt source_revision must use the pinned SafeDrug commit"
            )
        for name in ("started_at", "finished_at", "reason"):
            if getattr(self, name):
                require_single_line_public_string(getattr(self, name), field=f"attempt.{name}")
        if (
            any(item.artifact_changed and not item.has_equivalence_evidence for item in repairs)
            and self.validity is AttemptValidity.USABLE
        ):
            object.__setattr__(self, "validity", AttemptValidity.USABLE_WITH_LIMITS)
        expected = content_sha256(self.protected_payload)
        if self.attempt_sha256:
            require_sha256(self.attempt_sha256, field="attempt_sha256")
            if self.attempt_sha256 != expected:
                raise ProtocolValidationError("attempt_sha256 does not match attempt content")
        else:
            object.__setattr__(self, "attempt_sha256", expected)

    @property
    def protected_payload(self) -> dict[str, object]:
        return {
            "artifact_digests": _digest_map(self.artifact_digests),
            "authority_ok": self.authority_ok,
            "contract_sha256": self.contract_sha256,
            "lane_id": self.lane_id,
            "privacy_ok": self.privacy_ok,
            "qa_qc": _thaw(self.qa_qc),
            "repair_evidence": [item.to_dict() for item in self.repair_evidence],
            "required_outcomes": list(self.required_outcomes),
            "resource_ok": self.resource_ok,
            "source_revision": self.source_revision,
            "status": self.status.value,
            "uncertainty": _thaw(self.uncertainty),
            "outcomes": _thaw(self.outcomes),
            "validity": self.validity.value,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_digests": _digest_map(self.artifact_digests),
            "attempt_id": self.attempt_id,
            "attempt_sha256": self.attempt_sha256,
            "authority_ok": self.authority_ok,
            "contract_sha256": self.contract_sha256,
            "deviations": list(self.deviations),
            "finished_at": self.finished_at,
            "kind": "attempt_record",
            "lane_id": self.lane_id,
            "outcomes": _thaw(self.outcomes),
            "privacy_ok": self.privacy_ok,
            "qa_qc": _thaw(self.qa_qc),
            "reason": self.reason,
            "repair_evidence": [item.to_dict() for item in self.repair_evidence],
            "required_outcomes": list(self.required_outcomes),
            "resource_ok": self.resource_ok,
            "schema_version": self.SCHEMA_VERSION,
            "source_revision": self.source_revision,
            "started_at": self.started_at,
            "status": self.status.value,
            "uncertainty": _thaw(self.uncertainty),
            "validity": self.validity.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> AttemptRecord:
        payload = strict_fields(
            value,
            required=(
                "artifact_digests",
                "attempt_id",
                "attempt_sha256",
                "authority_ok",
                "contract_sha256",
                "deviations",
                "finished_at",
                "kind",
                "lane_id",
                "outcomes",
                "privacy_ok",
                "qa_qc",
                "reason",
                "repair_evidence",
                "required_outcomes",
                "resource_ok",
                "schema_version",
                "source_revision",
                "started_at",
                "status",
                "uncertainty",
                "validity",
            ),
            context="AttemptRecord",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "attempt_record"
        ):
            raise ProtocolValidationError("AttemptRecord schema or kind is invalid")
        payload["repair_evidence"] = tuple(
            RepairEvidence.from_dict(item) for item in payload["repair_evidence"]
        )
        return cls(**payload)

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> AttemptRecord:
        return cls.from_dict(parse_json_object(text, context="AttemptRecord"))


@dataclass(frozen=True, slots=True)
class DecisionPacket:
    """Independent, packet-ready evidence for one lane or MoleRec stage."""

    packet_id: str
    contract_sha256: str
    lane_id: str
    attempts: tuple[AttemptRecord, ...]
    conclusion: EvidenceConclusion | str
    validity: AttemptValidity | str
    stage: Stage | str | None = None
    required_outcomes: tuple[str, ...] = REQUIRED_OUTCOMES
    outcomes: object = ()
    uncertainty: object = ()
    limitations: tuple[str, ...] = ()
    allowed_claims: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    action_consequences: tuple[str, ...] = ()
    attempted_lane_ids: tuple[str, ...] = ()
    completed_lane_ids: tuple[str, ...] = ()
    packet_sha256: str = ""
    created_at: str = ""
    notes: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_identifier(self.packet_id, field="packet_id")
        require_sha256(self.contract_sha256, field="packet.contract_sha256")
        require_identifier(self.lane_id, field="packet.lane_id")
        attempts = tuple(
            item if isinstance(item, AttemptRecord) else AttemptRecord.from_dict(item)
            for item in self.attempts
        )
        if not attempts:
            raise ProtocolValidationError("DecisionPacket requires at least one attempt")
        if any(item.lane_id != self.lane_id for item in attempts):
            raise ProtocolValidationError(
                "DecisionPacket attempts must remain isolated to one lane"
            )
        if any(item.contract_sha256 != self.contract_sha256 for item in attempts):
            raise ProtocolValidationError("DecisionPacket attempt contract digest drifted")
        object.__setattr__(self, "attempts", attempts)
        conclusion = enum_member(EvidenceConclusion, self.conclusion, field="packet.conclusion")
        validity = enum_member(AttemptValidity, self.validity, field="packet.validity")
        object.__setattr__(self, "conclusion", conclusion)
        object.__setattr__(self, "validity", validity)
        if self.stage is not None:
            object.__setattr__(
                self, "stage", _normalize_stage(self.stage, field_name="packet.stage")
            )
        required = _string_tuple(
            self.required_outcomes, field_name="packet.required_outcomes", identifiers=True
        )
        if not set(REQUIRED_OUTCOMES) <= set(required):
            raise ProtocolValidationError(
                "packet.required_outcomes must contain all required outcomes"
            )
        object.__setattr__(self, "required_outcomes", required)
        for name in ("outcomes", "uncertainty"):
            value = getattr(self, name)
            thawed = _thaw(value)
            if not isinstance(thawed, dict) or not thawed:
                raise ProtocolValidationError(f"packet.{name} must be a non-empty object")
            normalized = _public_value(thawed, field_name=f"packet.{name}")
            values = _thaw(normalized)
            missing = [item for item in REQUIRED_OUTCOMES if item not in values]
            if missing:
                raise ProtocolValidationError(
                    f"packet.{name} missing required outcomes: {', '.join(missing)}"
                )
            object.__setattr__(self, name, normalized)
        for name in ("limitations", "allowed_claims", "blockers", "action_consequences"):
            object.__setattr__(
                self,
                name,
                _string_tuple(getattr(self, name), field_name=f"packet.{name}")
                if getattr(self, name)
                else (),
            )
        attempted = (
            _string_tuple(
                self.attempted_lane_ids, field_name="packet.attempted_lane_ids", identifiers=True
            )
            if self.attempted_lane_ids
            else (self.lane_id,)
        )
        completed = (
            _string_tuple(
                self.completed_lane_ids, field_name="packet.completed_lane_ids", identifiers=True
            )
            if self.completed_lane_ids
            else tuple(item.lane_id for item in attempts if item.status is AttemptStatus.COMPLETED)
        )
        if self.lane_id not in attempted or any(item != self.lane_id for item in attempted):
            raise ProtocolValidationError("packet attempted_lane_ids must describe only its lane")
        if any(item != self.lane_id for item in completed):
            raise ProtocolValidationError("packet completed_lane_ids must describe only its lane")
        object.__setattr__(self, "attempted_lane_ids", attempted)
        object.__setattr__(self, "completed_lane_ids", completed)
        for name in ("created_at", "notes"):
            if getattr(self, name):
                require_single_line_public_string(getattr(self, name), field=f"packet.{name}")
        expected = content_sha256(self.protected_payload)
        if self.packet_sha256:
            require_sha256(self.packet_sha256, field="packet_sha256")
            if self.packet_sha256 != expected:
                raise ProtocolValidationError("packet_sha256 does not match packet content")
        else:
            object.__setattr__(self, "packet_sha256", expected)

    @property
    def is_current(self) -> bool:
        return self.packet_sha256 == content_sha256(self.protected_payload)

    @property
    def go_eligible(self) -> bool:
        evidence_complete = True
        for record in (self, *self.attempts):
            for name in ("outcomes", "uncertainty"):
                values = _thaw(getattr(record, name))
                if (
                    not isinstance(values, dict)
                    or not values
                    or not set(REQUIRED_OUTCOMES) <= set(values)
                ):
                    evidence_complete = False
                    break
            if not evidence_complete:
                break
        return (
            self.is_current
            and evidence_complete
            and self.validity is AttemptValidity.USABLE
            and self.conclusion is EvidenceConclusion.ACCEPTED
            and not self.blockers
            and all(item.status is AttemptStatus.COMPLETED for item in self.attempts)
            and all(item.validity is AttemptValidity.USABLE for item in self.attempts)
        )

    @property
    def protected_payload(self) -> dict[str, object]:
        return {
            "attempts": [item.attempt_sha256 for item in self.attempts],
            "attempted_lane_ids": list(self.attempted_lane_ids),
            "blockers": list(self.blockers),
            "completed_lane_ids": list(self.completed_lane_ids),
            "conclusion": self.conclusion.value,
            "contract_sha256": self.contract_sha256,
            "lane_id": self.lane_id,
            "stage": self.stage.value if isinstance(self.stage, Stage) else None,
            "required_outcomes": list(self.required_outcomes),
            "validity": self.validity.value,
            "outcomes": _thaw(self.outcomes),
            "uncertainty": _thaw(self.uncertainty),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "action_consequences": list(self.action_consequences),
            "allowed_claims": list(self.allowed_claims),
            "attempted_lane_ids": list(self.attempted_lane_ids),
            "attempts": [item.to_dict() for item in self.attempts],
            "blockers": list(self.blockers),
            "completed_lane_ids": list(self.completed_lane_ids),
            "conclusion": self.conclusion.value,
            "contract_sha256": self.contract_sha256,
            "created_at": self.created_at,
            "kind": "decision_packet",
            "lane_id": self.lane_id,
            "limitations": list(self.limitations),
            "notes": self.notes,
            "outcomes": _thaw(self.outcomes),
            "packet_id": self.packet_id,
            "packet_sha256": self.packet_sha256,
            "required_outcomes": list(self.required_outcomes),
            "schema_version": self.SCHEMA_VERSION,
            "stage": self.stage.value if isinstance(self.stage, Stage) else None,
            "uncertainty": _thaw(self.uncertainty),
            "validity": self.validity.value,
        }

    @classmethod
    def create(
        cls,
        *,
        contract: SafeDrugBatchContract | str,
        attempts: tuple[AttemptRecord, ...],
        **kwargs: object,
    ) -> DecisionPacket:
        digest = (
            contract.contract_sha256 if isinstance(contract, SafeDrugBatchContract) else contract
        )
        return cls(contract_sha256=digest, attempts=attempts, **kwargs)

    @classmethod
    def from_dict(cls, value: object) -> DecisionPacket:
        payload = strict_fields(
            value,
            required=(
                "action_consequences",
                "allowed_claims",
                "attempted_lane_ids",
                "attempts",
                "blockers",
                "completed_lane_ids",
                "conclusion",
                "contract_sha256",
                "created_at",
                "kind",
                "lane_id",
                "limitations",
                "notes",
                "outcomes",
                "packet_id",
                "packet_sha256",
                "required_outcomes",
                "schema_version",
                "uncertainty",
                "validity",
            ),
            optional=("stage",),
            context="DecisionPacket",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "decision_packet"
        ):
            raise ProtocolValidationError("DecisionPacket schema or kind is invalid")
        attempts = payload.pop("attempts")
        if not isinstance(attempts, list):
            raise ProtocolValidationError("DecisionPacket attempts must be a list")
        payload["attempts"] = tuple(AttemptRecord.from_dict(item) for item in attempts)
        return cls(**payload)

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> DecisionPacket:
        return cls.from_dict(parse_json_object(text, context="DecisionPacket"))


@dataclass(frozen=True, slots=True)
class H2Decision:
    """A researcher's action on one current Decision Packet."""

    contract_sha256: str
    packet_sha256: str
    researcher: str
    action: H2Action | str
    rationale: str = ""
    issued_at: str = ""
    decision_sha256: str = ""
    contract_family: str = "safedrug-reproduction"
    source_revision: str = SAFE_DRUG_MAIN_REVISION
    mode: str = "reproduction"
    research_target: str = "source-native-reproduction"

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        require_sha256(self.contract_sha256, field="h2.contract_sha256")
        require_sha256(self.packet_sha256, field="h2.packet_sha256")
        require_identifier(self.researcher, field="h2.researcher")
        action = enum_member(H2Action, self.action, field="h2.action")
        object.__setattr__(self, "action", action)
        if self.rationale:
            require_single_line_public_string(self.rationale, field="h2.rationale")
        if self.issued_at:
            require_single_line_public_string(self.issued_at, field="h2.issued_at")
        require_identifier(self.contract_family, field="h2.contract_family")
        if self.contract_family not in {"safedrug-reproduction", "molerec-reproduction"}:
            raise ProtocolValidationError(
                "H2 contract_family is not a registered reproduction family"
            )
        if self.mode != "reproduction":
            raise ProtocolValidationError("H2 mode must be reproduction")
        expected_source = {
            "safedrug-reproduction": SAFE_DRUG_MAIN_REVISION,
            "molerec-reproduction": MOLEREC_REVISION,
        }[self.contract_family]
        if self.source_revision != expected_source:
            raise ProtocolValidationError("H2 source_revision does not match its contract family")
        expected_target = {
            "safedrug-reproduction": "source-native-reproduction",
            "molerec-reproduction": "molerec-source-native",
        }[self.contract_family]
        if self.research_target != expected_target:
            raise ProtocolValidationError("H2 research_target does not match its contract family")
        require_single_line_public_string(self.research_target, field="h2.research_target")
        expected = content_sha256(self._protected_payload())
        if self.decision_sha256:
            require_sha256(self.decision_sha256, field="decision_sha256")
            if self.decision_sha256 != expected:
                raise ProtocolValidationError("decision_sha256 does not match decision content")
        else:
            object.__setattr__(self, "decision_sha256", expected)

    def _protected_payload(self) -> dict[str, str]:
        return {
            "action": self.action.value,
            "contract_family": self.contract_family,
            "contract_sha256": self.contract_sha256,
            "mode": self.mode,
            "packet_sha256": self.packet_sha256,
            "research_target": self.research_target,
            "source_revision": self.source_revision,
        }

    @classmethod
    def create(
        cls,
        *,
        contract: SafeDrugBatchContract | MoleRecStageContract | str,
        packet: DecisionPacket,
        researcher: str,
        action: H2Action | str,
        rationale: str = "",
        issued_at: str = "",
        contract_family: str = "safedrug-reproduction",
        source_revision: str = SAFE_DRUG_MAIN_REVISION,
        mode: str = "reproduction",
        research_target: str = "source-native-reproduction",
    ) -> H2Decision:
        if not isinstance(packet, DecisionPacket):
            raise ProtocolValidationError("H2 requires a DecisionPacket")
        digest = (
            contract.contract_sha256
            if isinstance(contract, (SafeDrugBatchContract, MoleRecStageContract))
            else contract
        )
        if (
            isinstance(contract, (SafeDrugBatchContract, MoleRecStageContract))
            and not contract.is_current()
        ):
            raise ProtocolValidationError("H2 contract is stale")
        if not packet.is_current:
            raise ProtocolValidationError("H2 packet is stale")
        if packet.contract_sha256 != digest:
            raise ProtocolValidationError("H2 contract and packet digests must match")
        action_value = enum_member(H2Action, action, field="h2.action")
        if action_value is H2Action.GO and not packet.go_eligible:
            raise ProtocolValidationError("H2 go requires current usable accepted evidence")
        if isinstance(contract, SafeDrugBatchContract):
            expected_family = "safedrug-reproduction"
            expected_source = SAFE_DRUG_MAIN_REVISION
            expected_target = "source-native-reproduction"
        elif isinstance(contract, MoleRecStageContract):
            if packet.stage is None:
                raise ProtocolValidationError("MoleRec H2 requires a staged packet")
            expected_family = "molerec-reproduction"
            expected_source = MOLEREC_REVISION
            expected_target = "molerec-source-native"
        elif packet.stage is None:
            expected_family = "safedrug-reproduction"
            expected_source = SAFE_DRUG_MAIN_REVISION
            expected_target = "source-native-reproduction"
        else:
            expected_family = "molerec-reproduction"
            expected_source = MOLEREC_REVISION
            expected_target = "molerec-source-native"
        if (
            contract_family != expected_family
            or source_revision != expected_source
            or mode != "reproduction"
            or research_target != expected_target
        ):
            raise ProtocolValidationError(
                "H2 metadata must remain bound to the packet's reproduction contract family"
            )
        return cls(
            contract_sha256=digest,
            packet_sha256=packet.packet_sha256,
            researcher=researcher,
            action=action_value,
            rationale=rationale,
            issued_at=issued_at,
            contract_family=contract_family,
            source_revision=source_revision,
            mode=mode,
            research_target=research_target,
        )

    @property
    def go_eligible(self) -> bool:
        return self.action is H2Action.GO

    @property
    def allows_execution(self) -> bool:
        """Scientific eligibility only; this is not an Action Gate token."""

        return self.go_eligible

    def is_current(
        self,
        *,
        contract: SafeDrugBatchContract | MoleRecStageContract | str,
        packet: DecisionPacket | str,
    ) -> bool:
        contract_digest = (
            contract.contract_sha256
            if isinstance(contract, (SafeDrugBatchContract, MoleRecStageContract))
            else contract
        )
        packet_digest = packet.packet_sha256 if isinstance(packet, DecisionPacket) else packet
        return (
            self.contract_sha256 == contract_digest
            and self.packet_sha256 == packet_digest
            and (
                not isinstance(contract, (SafeDrugBatchContract, MoleRecStageContract))
                or contract.is_current()
            )
            and (not isinstance(packet, DecisionPacket) or packet.is_current)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action.value,
            "contract_family": self.contract_family,
            "contract_sha256": self.contract_sha256,
            "decision_sha256": self.decision_sha256,
            "issued_at": self.issued_at,
            "kind": "h2_decision",
            "mode": self.mode,
            "packet_sha256": self.packet_sha256,
            "rationale": self.rationale,
            "research_target": self.research_target,
            "researcher": self.researcher,
            "schema_version": self.SCHEMA_VERSION,
            "source_revision": self.source_revision,
        }

    @classmethod
    def from_dict(cls, value: object) -> H2Decision:
        payload = strict_fields(
            value,
            required=(
                "action",
                "contract_family",
                "contract_sha256",
                "decision_sha256",
                "issued_at",
                "kind",
                "mode",
                "packet_sha256",
                "rationale",
                "research_target",
                "researcher",
                "schema_version",
                "source_revision",
            ),
            context="H2Decision",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "h2_decision"
        ):
            raise ProtocolValidationError("H2Decision schema or kind is invalid")
        return cls(**payload)

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> H2Decision:
        return cls.from_dict(parse_json_object(text, context="H2Decision"))


@dataclass(frozen=True, slots=True)
class MoleRecStageContract:
    """Immutable MoleRec stage identity with sequential H2 gating."""

    stage: Stage | str
    variant: str
    artifact_bundle_sha256: str
    parent_h2_sha256: str | None = None
    parent_packet_sha256: str | None = None
    source_repository: str = MOLEREC_REPOSITORY
    source_revision: str = MOLEREC_REVISION
    preprocessing_lineage_revision: str = MOLEREC_SAFEDRUG_LINEAGE_REVISION
    contract_family: str = "molerec-reproduction"
    research_target: str = "molerec-source-native"
    stage_id: str = "molerec-stage"
    notes: str = ""
    evidence_urls: tuple[str, ...] = ()
    bundle_equivalence_sha256: str | None = None
    comparison_scope_sha256: str | None = None
    comparison_protocol_sha256: str | None = None
    contract_sha256: str = ""

    SCHEMA_VERSION: ClassVar[int] = 1

    def __post_init__(self) -> None:
        stage = _normalize_stage(self.stage)
        object.__setattr__(self, "stage", stage)
        require_identifier(self.variant, field="molerec.variant")
        require_sha256(self.artifact_bundle_sha256, field="molerec.artifact_bundle_sha256")
        if self.parent_h2_sha256 is not None:
            require_sha256(self.parent_h2_sha256, field="molerec.parent_h2_sha256")
        if self.parent_packet_sha256 is not None:
            require_sha256(self.parent_packet_sha256, field="molerec.parent_packet_sha256")
        if self.source_repository != MOLEREC_REPOSITORY or self.source_revision != MOLEREC_REVISION:
            raise ProtocolValidationError(
                "MoleRec stage source must use the pinned repository and revision"
            )
        if self.preprocessing_lineage_revision != MOLEREC_SAFEDRUG_LINEAGE_REVISION:
            raise ProtocolValidationError(
                "MoleRec preprocessing lineage must use the pinned SafeDrug c7218d0 commit"
            )
        require_identifier(self.contract_family, field="molerec.contract_family")
        if self.contract_family != "molerec-reproduction":
            raise ProtocolValidationError("MoleRec stage contract family is fixed")
        require_single_line_public_string(self.research_target, field="molerec.research_target")
        require_identifier(self.stage_id, field="molerec.stage_id")
        if self.notes:
            require_single_line_public_string(self.notes, field="molerec.notes")
        object.__setattr__(
            self,
            "evidence_urls",
            _check_public_links(self.evidence_urls, field_name="molerec.evidence_urls"),
        )
        for field in (
            "bundle_equivalence_sha256",
            "comparison_scope_sha256",
            "comparison_protocol_sha256",
        ):
            value = getattr(self, field)
            if value is not None:
                require_sha256(value, field=f"molerec.{field}")
        if (
            self.stage is not Stage.CHECKPOINT_REPLAY
            and self.bundle_equivalence_sha256 != self.artifact_bundle_sha256
        ):
            raise ProtocolValidationError(
                "MoleRec training/comparison stages require exact bundle equivalence"
            )
        if self.stage is Stage.COMPARISON_QUALIFICATION and (
            self.comparison_scope_sha256 is None or self.comparison_protocol_sha256 is None
        ):
            raise ProtocolValidationError(
                "MoleRec comparison qualification requires a current scope and protocol digest"
            )
        self._check_parent_requirements()
        expected = content_sha256(self.protected_payload)
        if self.contract_sha256:
            require_sha256(self.contract_sha256, field="molerec.contract_sha256")
            if self.contract_sha256 != expected:
                raise ProtocolValidationError(
                    "MoleRec stage contract_sha256 does not match protected fields"
                )
        else:
            object.__setattr__(self, "contract_sha256", expected)

    def _check_parent_requirements(self) -> None:
        if self.stage is Stage.CHECKPOINT_REPLAY:
            if self.parent_h2_sha256 is not None or self.parent_packet_sha256 is not None:
                raise ProtocolValidationError(
                    "MoleRec checkpoint replay cannot skip from a parent stage"
                )
            return
        if self.parent_h2_sha256 is None or self.parent_packet_sha256 is None:
            raise ProtocolValidationError("MoleRec stage requires the preceding packet's H2 go")

    @classmethod
    def create(
        cls,
        *,
        stage: Stage | str,
        variant: str,
        artifact_bundle_sha256: str,
        parent_h2: H2Decision | None = None,
        parent_packet: DecisionPacket | None = None,
        artifact_bundle: object | None = None,
        **kwargs: object,
    ) -> MoleRecStageContract:
        normalized_stage = _normalize_stage(stage)
        if artifact_bundle is not None:
            bundle_digest = getattr(artifact_bundle, "bundle_sha256", None)
            if bundle_digest != artifact_bundle_sha256:
                raise ProtocolValidationError("MoleRec stage artifact bundle digest does not match")
            if getattr(artifact_bundle, "variant", None) != variant:
                raise ProtocolValidationError(
                    "MoleRec stage variant does not match artifact bundle"
                )
            if not getattr(artifact_bundle, "is_current", lambda: False)():
                raise ProtocolValidationError("MoleRec stage requires a current artifact bundle")
            if normalized_stage is not Stage.CHECKPOINT_REPLAY:
                kwargs.setdefault("bundle_equivalence_sha256", bundle_digest)
        if normalized_stage is Stage.CHECKPOINT_REPLAY:
            if parent_h2 is not None or parent_packet is not None:
                raise ProtocolValidationError("MoleRec checkpoint replay cannot have a parent H2")
            return cls(
                stage=normalized_stage,
                variant=variant,
                artifact_bundle_sha256=artifact_bundle_sha256,
                **kwargs,
            )
        if parent_h2 is None or parent_packet is None:
            raise ProtocolValidationError("MoleRec stage requires the preceding packet and H2")
        if parent_h2.action is not H2Action.GO or not parent_h2.allows_execution:
            raise ProtocolValidationError("MoleRec stage requires an eligible H2 go")
        if (
            not parent_packet.is_current
            or not parent_packet.go_eligible
            or parent_h2.packet_sha256 != parent_packet.packet_sha256
            or parent_h2.contract_sha256 != parent_packet.contract_sha256
            or parent_h2.decision_sha256 != content_sha256(parent_h2._protected_payload())
        ):
            raise ProtocolValidationError("MoleRec parent H2 or packet is stale")
        expected_parent_stage = {
            Stage.TRAINING_REPRODUCTION: Stage.CHECKPOINT_REPLAY,
            Stage.COMPARISON_QUALIFICATION: Stage.TRAINING_REPRODUCTION,
        }[normalized_stage]
        parent_stage = getattr(parent_packet, "stage", None)
        if parent_stage is None or _normalize_stage(parent_stage) is not expected_parent_stage:
            raise ProtocolValidationError("MoleRec stage cannot skip its preceding evidence stage")
        return cls(
            stage=normalized_stage,
            variant=variant,
            artifact_bundle_sha256=artifact_bundle_sha256,
            parent_h2_sha256=parent_h2.decision_sha256,
            parent_packet_sha256=parent_packet.packet_sha256,
            **kwargs,
        )

    @property
    def protected_payload(self) -> dict[str, object]:
        return {
            "artifact_bundle_sha256": self.artifact_bundle_sha256,
            "contract_family": self.contract_family,
            "parent_h2_sha256": self.parent_h2_sha256,
            "parent_packet_sha256": self.parent_packet_sha256,
            "bundle_equivalence_sha256": self.bundle_equivalence_sha256,
            "comparison_protocol_sha256": self.comparison_protocol_sha256,
            "comparison_scope_sha256": self.comparison_scope_sha256,
            "preprocessing_lineage_revision": self.preprocessing_lineage_revision,
            "research_target": self.research_target,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "stage": self.stage.value,
            "stage_id": self.stage_id,
            "variant": self.variant,
        }

    def is_current(self) -> bool:
        return self.contract_sha256 == content_sha256(self.protected_payload)

    def to_dict(self) -> dict[str, object]:
        return {
            "artifact_bundle_sha256": self.artifact_bundle_sha256,
            "bundle_equivalence_sha256": self.bundle_equivalence_sha256,
            "comparison_protocol_sha256": self.comparison_protocol_sha256,
            "comparison_scope_sha256": self.comparison_scope_sha256,
            "contract_family": self.contract_family,
            "contract_sha256": self.contract_sha256,
            "evidence_urls": list(self.evidence_urls),
            "kind": "molerec_stage_contract",
            "notes": self.notes,
            "parent_h2_sha256": self.parent_h2_sha256,
            "parent_packet_sha256": self.parent_packet_sha256,
            "preprocessing_lineage_revision": self.preprocessing_lineage_revision,
            "research_target": self.research_target,
            "schema_version": self.SCHEMA_VERSION,
            "source_repository": self.source_repository,
            "source_revision": self.source_revision,
            "stage": self.stage.value,
            "stage_id": self.stage_id,
            "variant": self.variant,
        }

    @classmethod
    def from_dict(cls, value: object) -> MoleRecStageContract:
        payload = strict_fields(
            value,
            required=(
                "artifact_bundle_sha256",
                "contract_family",
                "contract_sha256",
                "evidence_urls",
                "kind",
                "notes",
                "parent_h2_sha256",
                "parent_packet_sha256",
                "preprocessing_lineage_revision",
                "research_target",
                "schema_version",
                "source_repository",
                "source_revision",
                "stage",
                "stage_id",
                "variant",
            ),
            optional=(
                "bundle_equivalence_sha256",
                "comparison_protocol_sha256",
                "comparison_scope_sha256",
            ),
            context="MoleRecStageContract",
        )
        if (
            payload.pop("schema_version") != cls.SCHEMA_VERSION
            or payload.pop("kind") != "molerec_stage_contract"
        ):
            raise ProtocolValidationError("MoleRecStageContract schema or kind is invalid")
        payload.setdefault("bundle_equivalence_sha256", None)
        payload.setdefault("comparison_protocol_sha256", None)
        payload.setdefault("comparison_scope_sha256", None)
        return cls(**payload)

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> MoleRecStageContract:
        return cls.from_dict(parse_json_object(text, context="MoleRecStageContract"))


__all__ = (
    "MOLEREC_REPOSITORY",
    "MOLEREC_REVISION",
    "MOLEREC_SAFEDRUG_LINEAGE_REVISION",
    "REQUIRED_OUTCOMES",
    "SAFE_DRUG_MAIN_REVISION",
    "SAFE_DRUG_MODEL_IDS",
    "SAFE_DRUG_REPOSITORY",
    "AttemptRecord",
    "AttemptStatus",
    "AttemptValidity",
    "DecisionPacket",
    "EvidenceConclusion",
    "H1Approval",
    "H2Action",
    "H2Decision",
    "ModelAnnex",
    "MoleRecStageContract",
    "RepairEvidence",
    "SafeDrugBatchContract",
    "Stage",
)
