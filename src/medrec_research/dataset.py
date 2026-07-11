"""Public-safe dataset identity and split declarations."""

from __future__ import annotations

import hmac
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import ClassVar

from ._validation import (
    canonical_json,
    content_sha256,
    enum_member,
    parse_json_object,
    require_identifier,
    require_int,
    require_public_string,
    require_sha256,
    require_single_line_public_string,
    strict_fields,
)
from .errors import ProtocolValidationError


class SplitName(StrEnum):
    """Protocol-owned patient split names."""

    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class DatasetPrivacy(StrEnum):
    """Whether membership digests protect restricted identifiers."""

    SYNTHETIC = "synthetic"
    RESTRICTED = "restricted"


class MembershipDigestMethod(StrEnum):
    """Digest mechanism used for patient and eligible-visit membership."""

    SHA256 = "sha256"
    HMAC_SHA256 = "hmac-sha256"


_SPLIT_ORDER = {name: index for index, name in enumerate(SplitName)}


def _ordered_digest(values: Iterable[str]) -> str:
    serialized = "".join(f"{value}\n" for value in sorted(values))
    return sha256(serialized.encode("utf-8")).hexdigest()


def _membership_token(value: object, key: bytes | None) -> str:
    serialized = canonical_json(value).encode("ascii")
    if key is None:
        return sha256(serialized).hexdigest()
    return hmac.new(key, serialized, sha256).hexdigest()


def _membership_digest_method(
    privacy: DatasetPrivacy,
    key: bytes | None,
) -> MembershipDigestMethod:
    if privacy is DatasetPrivacy.RESTRICTED:
        if not isinstance(key, bytes) or len(key) < 32:
            raise ProtocolValidationError(
                "restricted membership requires a private HMAC key of at least 32 bytes"
            )
        return MembershipDigestMethod.HMAC_SHA256
    if key is not None:
        raise ProtocolValidationError("synthetic membership must not use a private HMAC key")
    return MembershipDigestMethod.SHA256


def _split_mapping(
    value: Mapping[SplitName | str, Iterable[object]],
    *,
    field: str,
) -> dict[SplitName, Iterable[object]]:
    if not isinstance(value, Mapping):
        raise ProtocolValidationError(f"{field} must be a split mapping")
    normalized: dict[SplitName, Iterable[object]] = {}
    for raw_name, items in value.items():
        name = enum_member(SplitName, raw_name, field=f"{field}.split")
        if name in normalized:
            raise ProtocolValidationError(f"{field} must declare each split once")
        normalized[name] = items
    if set(normalized) != set(SplitName):
        raise ProtocolValidationError(f"{field} must declare train, validation, and test")
    return normalized


@dataclass(frozen=True, slots=True)
class DatasetSplit:
    """Aggregate identity for one patient-disjoint split."""

    name: SplitName | str
    patient_count: int
    visit_count: int
    patient_membership_digest: str
    visit_membership_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", enum_member(SplitName, self.name, field="split.name"))
        require_int(self.patient_count, field="split.patient_count", minimum=1)
        require_int(self.visit_count, field="split.visit_count", minimum=1)
        require_sha256(
            self.patient_membership_digest,
            field="split.patient_membership_digest",
        )
        require_sha256(
            self.visit_membership_digest,
            field="split.visit_membership_digest",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name.value,
            "patient_count": self.patient_count,
            "patient_membership_digest": self.patient_membership_digest,
            "visit_membership_digest": self.visit_membership_digest,
            "visit_count": self.visit_count,
        }

    @classmethod
    def from_dict(cls, value: object) -> DatasetSplit:
        payload = strict_fields(
            value,
            required=(
                "name",
                "patient_count",
                "visit_count",
                "patient_membership_digest",
                "visit_membership_digest",
            ),
            context="DatasetSplit",
        )
        return cls(
            name=payload["name"],
            patient_count=payload["patient_count"],
            visit_count=payload["visit_count"],
            patient_membership_digest=payload["patient_membership_digest"],
            visit_membership_digest=payload["visit_membership_digest"],
        )


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    """Public-safe identity for a local dataset snapshot."""

    SCHEMA_VERSION: ClassVar[int] = 2

    dataset_id: str
    snapshot_id: str
    provenance: str
    checksum_sha256: str
    medication_vocabulary_sha256: str
    privacy: DatasetPrivacy | str
    membership_digest_method: MembershipDigestMethod | str
    splits: tuple[DatasetSplit, ...]
    patient_disjoint: bool
    test_evaluation_only: bool

    def __post_init__(self) -> None:
        require_identifier(self.dataset_id, field="dataset_id")
        require_public_string(self.snapshot_id, field="snapshot_id")
        require_public_string(self.provenance, field="provenance")
        require_sha256(self.checksum_sha256, field="checksum_sha256")
        require_sha256(
            self.medication_vocabulary_sha256,
            field="medication_vocabulary_sha256",
        )
        privacy = enum_member(DatasetPrivacy, self.privacy, field="privacy")
        digest_method = enum_member(
            MembershipDigestMethod,
            self.membership_digest_method,
            field="membership_digest_method",
        )
        if privacy is DatasetPrivacy.RESTRICTED:
            if digest_method is not MembershipDigestMethod.HMAC_SHA256:
                raise ProtocolValidationError(
                    "restricted DatasetManifest membership requires hmac-sha256"
                )
        elif digest_method is not MembershipDigestMethod.SHA256:
            raise ProtocolValidationError("synthetic DatasetManifest membership requires sha256")
        object.__setattr__(self, "privacy", privacy)
        object.__setattr__(self, "membership_digest_method", digest_method)
        splits = tuple(
            split if isinstance(split, DatasetSplit) else DatasetSplit.from_dict(split)
            for split in self.splits
        )
        if len(splits) != 3 or {split.name for split in splits} != set(SplitName):
            raise ProtocolValidationError(
                "DatasetManifest must declare exactly one train, validation, and test split"
            )
        if len({split.patient_membership_digest for split in splits}) != len(splits):
            raise ProtocolValidationError("split patient identity digests must be distinct")
        if len({split.visit_membership_digest for split in splits}) != len(splits):
            raise ProtocolValidationError("split visit identity digests must be distinct")
        if not self.patient_disjoint:
            raise ProtocolValidationError("DatasetManifest must declare patient-disjoint splits")
        if not self.test_evaluation_only:
            raise ProtocolValidationError("DatasetManifest must declare test as evaluation-only")
        object.__setattr__(
            self, "splits", tuple(sorted(splits, key=lambda item: _SPLIT_ORDER[item.name]))
        )

    @property
    def patient_count(self) -> int:
        return sum(split.patient_count for split in self.splits)

    @property
    def visit_count(self) -> int:
        return sum(split.visit_count for split in self.splits)

    @property
    def manifest_sha256(self) -> str:
        return content_sha256(self.to_dict())

    def split(self, name: SplitName | str) -> DatasetSplit:
        split_name = enum_member(SplitName, name, field="split")
        return next(split for split in self.splits if split.name is split_name)

    def verify_evaluation_visits(
        self,
        visits: Iterable[tuple[str, str]],
        *,
        membership_hmac_key: bytes | None = None,
    ) -> str:
        """Verify exact eligible test-visit membership while identifiers remain private."""

        _membership_digest_method(self.privacy, membership_hmac_key)
        try:
            raw_visits = tuple(visits)
        except TypeError as error:
            raise ProtocolValidationError("evaluation visits must be a collection") from error
        normalized: list[tuple[str, str]] = []
        for raw_visit in raw_visits:
            if not isinstance(raw_visit, (list, tuple)) or len(raw_visit) != 2:
                raise ProtocolValidationError(
                    "each evaluation visit must contain patient_id and visit_id"
                )
            normalized.append(
                (
                    require_public_string(raw_visit[0], field="patient_id"),
                    require_public_string(raw_visit[1], field="visit_id"),
                )
            )
        expected = self.split(SplitName.TEST)
        if len(normalized) != expected.visit_count or len(set(normalized)) != len(normalized):
            raise ProtocolValidationError(
                "evaluation visits do not match eligible test-visit membership"
            )
        digest = _ordered_digest(
            _membership_token(visit, membership_hmac_key) for visit in normalized
        )
        if digest != expected.visit_membership_digest:
            raise ProtocolValidationError(
                "evaluation visits do not match eligible test-visit membership"
            )
        return digest

    def to_dict(self) -> dict[str, object]:
        return {
            "checksum_sha256": self.checksum_sha256,
            "dataset_id": self.dataset_id,
            "medication_vocabulary_sha256": self.medication_vocabulary_sha256,
            "membership_digest_method": self.membership_digest_method.value,
            "patient_disjoint": self.patient_disjoint,
            "privacy": self.privacy.value,
            "provenance": self.provenance,
            "schema_version": self.SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "splits": [split.to_dict() for split in self.splits],
            "test_evaluation_only": self.test_evaluation_only,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return canonical_json(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, value: object) -> DatasetManifest:
        payload = strict_fields(
            value,
            required=(
                "schema_version",
                "dataset_id",
                "snapshot_id",
                "provenance",
                "checksum_sha256",
                "medication_vocabulary_sha256",
                "privacy",
                "membership_digest_method",
                "splits",
                "patient_disjoint",
                "test_evaluation_only",
            ),
            context="DatasetManifest",
        )
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ProtocolValidationError(
                f"DatasetManifest schema_version must be {cls.SCHEMA_VERSION}"
            )
        raw_splits = payload["splits"]
        if not isinstance(raw_splits, list):
            raise ProtocolValidationError("DatasetManifest.splits must be a list")
        if type(payload["patient_disjoint"]) is not bool:
            raise ProtocolValidationError("patient_disjoint must be a boolean")
        if type(payload["test_evaluation_only"]) is not bool:
            raise ProtocolValidationError("test_evaluation_only must be a boolean")
        return cls(
            dataset_id=payload["dataset_id"],
            snapshot_id=payload["snapshot_id"],
            provenance=payload["provenance"],
            checksum_sha256=payload["checksum_sha256"],
            medication_vocabulary_sha256=payload["medication_vocabulary_sha256"],
            privacy=payload["privacy"],
            membership_digest_method=payload["membership_digest_method"],
            splits=tuple(DatasetSplit.from_dict(item) for item in raw_splits),
            patient_disjoint=payload["patient_disjoint"],
            test_evaluation_only=payload["test_evaluation_only"],
        )

    @classmethod
    def from_memberships(
        cls,
        *,
        dataset_id: str,
        snapshot_id: str,
        provenance: str,
        checksum_sha256: str,
        medication_vocabulary: Iterable[str],
        privacy: DatasetPrivacy | str,
        patients_by_split: Mapping[SplitName | str, Iterable[str]],
        visits_by_split: Mapping[SplitName | str, Iterable[tuple[str, str]]],
        membership_hmac_key: bytes | None = None,
    ) -> DatasetManifest:
        """Build a manifest while restricted memberships are available on 319."""

        normalized_privacy = enum_member(DatasetPrivacy, privacy, field="privacy")
        digest_method = _membership_digest_method(
            normalized_privacy,
            membership_hmac_key,
        )

        raw_patients = _split_mapping(patients_by_split, field="patients_by_split")
        raw_visits = _split_mapping(visits_by_split, field="visits_by_split")
        patients: dict[SplitName, tuple[str, ...]] = {}
        all_patients: set[str] = set()
        for split in SplitName:
            try:
                split_patients = tuple(
                    require_public_string(patient_id, field="patient_id")
                    for patient_id in raw_patients[split]
                )
            except TypeError as error:
                raise ProtocolValidationError(
                    "patients_by_split values must be collections"
                ) from error
            if not split_patients or len(split_patients) != len(set(split_patients)):
                raise ProtocolValidationError("each split requires unique, nonempty patient_ids")
            overlap = all_patients.intersection(split_patients)
            if overlap:
                raise ProtocolValidationError("dataset patients must be patient-disjoint")
            patients[split] = split_patients
            all_patients.update(split_patients)

        splits: list[DatasetSplit] = []
        all_visit_keys: set[tuple[str, str]] = set()
        for split in SplitName:
            try:
                split_visits = tuple(raw_visits[split])
            except TypeError as error:
                raise ProtocolValidationError(
                    "visits_by_split values must be collections"
                ) from error
            if not split_visits:
                raise ProtocolValidationError("each split requires at least one eligible visit")
            visit_tokens: list[str] = []
            normalized_visits: list[tuple[str, str]] = []
            split_patient_ids = set(patients[split])
            for raw_visit in split_visits:
                if not isinstance(raw_visit, (list, tuple)) or len(raw_visit) != 2:
                    raise ProtocolValidationError(
                        "each eligible visit must contain patient_id and visit_id"
                    )
                patient_id = require_public_string(raw_visit[0], field="patient_id")
                visit_id = require_public_string(raw_visit[1], field="visit_id")
                if patient_id not in split_patient_ids:
                    raise ProtocolValidationError(
                        "visit patient must belong to the declared split membership"
                    )
                key = (patient_id, visit_id)
                if key in all_visit_keys:
                    raise ProtocolValidationError("eligible visits must be unique")
                all_visit_keys.add(key)
                normalized_visits.append(key)
                visit_tokens.append(_membership_token(key, membership_hmac_key))
            patient_tokens = (
                _membership_token(patient_id, membership_hmac_key) for patient_id in patients[split]
            )
            splits.append(
                DatasetSplit(
                    name=split,
                    patient_count=len(patients[split]),
                    visit_count=len(normalized_visits),
                    patient_membership_digest=_ordered_digest(patient_tokens),
                    visit_membership_digest=_ordered_digest(visit_tokens),
                )
            )

        vocabulary = tuple(
            require_single_line_public_string(code, field="medication_vocabulary")
            for code in medication_vocabulary
        )
        if not vocabulary or len(vocabulary) != len(set(vocabulary)):
            raise ProtocolValidationError(
                "medication_vocabulary must contain unique medication codes"
            )
        return cls(
            dataset_id=dataset_id,
            snapshot_id=snapshot_id,
            provenance=provenance,
            checksum_sha256=checksum_sha256,
            medication_vocabulary_sha256=_ordered_digest(vocabulary),
            privacy=normalized_privacy,
            membership_digest_method=digest_method,
            splits=tuple(splits),
            patient_disjoint=True,
            test_evaluation_only=True,
        )

    @classmethod
    def from_json(cls, text: str) -> DatasetManifest:
        return cls.from_dict(parse_json_object(text, context="DatasetManifest"))

    @classmethod
    def load(cls, path: str | Path) -> DatasetManifest:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


__all__ = (
    "DatasetManifest",
    "DatasetPrivacy",
    "DatasetSplit",
    "MembershipDigestMethod",
    "SplitName",
)
