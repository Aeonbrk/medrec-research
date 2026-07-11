from __future__ import annotations

import pytest

from medrec_research import (
    DatasetManifest,
    DatasetPrivacy,
    DatasetSplit,
    MembershipDigestMethod,
    ProtocolValidationError,
)


def _split(name: str, digit: str) -> DatasetSplit:
    return DatasetSplit(
        name=name,
        patient_count=1,
        visit_count=2,
        patient_membership_digest=digit * 64,
        visit_membership_digest=str((int(digit) + 3) % 10) * 64,
    )


def valid_manifest() -> DatasetManifest:
    return DatasetManifest(
        dataset_id="synthetic-medrec",
        snapshot_id="v1",
        provenance="synthetic-medrec-v1",
        checksum_sha256="a" * 64,
        medication_vocabulary_sha256="b" * 64,
        privacy=DatasetPrivacy.SYNTHETIC,
        membership_digest_method=MembershipDigestMethod.SHA256,
        splits=(
            _split("train", "1"),
            _split("validation", "2"),
            _split("test", "3"),
        ),
        patient_disjoint=True,
        test_evaluation_only=True,
    )


def test_manifest_round_trip_preserves_declared_protocol_splits() -> None:
    manifest = valid_manifest()

    assert DatasetManifest.from_json(manifest.to_json()) == manifest
    assert tuple(split.name.value for split in manifest.splits) == (
        "train",
        "validation",
        "test",
    )
    assert manifest.medication_vocabulary_sha256 == "b" * 64
    assert manifest.manifest_sha256 == DatasetManifest.from_json(manifest.to_json()).manifest_sha256


def test_manifest_rejects_missing_schema_fields() -> None:
    payload = valid_manifest().to_dict()
    del payload["checksum_sha256"]

    with pytest.raises(ProtocolValidationError, match="checksum_sha256"):
        DatasetManifest.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("patient_disjoint", False, "patient-disjoint"),
        ("test_evaluation_only", False, "evaluation-only"),
        ("provenance", "/Users/researcher/private/data", "local path"),
    ],
)
def test_manifest_rejects_unsafe_or_non_protocol_declarations(
    field: str,
    value: object,
    message: str,
) -> None:
    payload = valid_manifest().to_dict()
    payload[field] = value

    with pytest.raises(ProtocolValidationError, match=message):
        DatasetManifest.from_dict(payload)


def test_manifest_requires_exactly_one_train_validation_and_test_split() -> None:
    payload = valid_manifest().to_dict()
    payload["splits"] = payload["splits"][:-1]

    with pytest.raises(ProtocolValidationError, match="train, validation, and test"):
        DatasetManifest.from_dict(payload)


def test_manifest_rejects_empty_or_identical_patient_splits() -> None:
    empty_payload = valid_manifest().to_dict()
    empty_payload["splits"][1]["patient_count"] = 0
    with pytest.raises(ProtocolValidationError, match=r"patient_count.*>= 1"):
        DatasetManifest.from_dict(empty_payload)

    duplicate_payload = valid_manifest().to_dict()
    duplicate_payload["splits"][1]["patient_membership_digest"] = duplicate_payload["splits"][0][
        "patient_membership_digest"
    ]
    with pytest.raises(ProtocolValidationError, match="patient identity digests"):
        DatasetManifest.from_dict(duplicate_payload)


def test_manifest_builder_rejects_overlapping_patients() -> None:
    with pytest.raises(ProtocolValidationError, match="patient-disjoint"):
        DatasetManifest.from_memberships(
            dataset_id="synthetic-medrec",
            snapshot_id="v1",
            provenance="synthetic-medrec-v1",
            checksum_sha256="a" * 64,
            medication_vocabulary=("RX_A",),
            privacy=DatasetPrivacy.SYNTHETIC,
            patients_by_split={
                "train": ("shared-patient",),
                "validation": ("validation-patient",),
                "test": ("shared-patient",),
            },
            visits_by_split={
                "train": (("shared-patient", "train-v1"),),
                "validation": (("validation-patient", "validation-v1"),),
                "test": (("shared-patient", "test-v1"),),
            },
        )


def test_restricted_manifest_builder_requires_hmac_key() -> None:
    kwargs = {
        "dataset_id": "restricted-medrec",
        "snapshot_id": "v1",
        "provenance": "restricted-snapshot-v1",
        "checksum_sha256": "a" * 64,
        "medication_vocabulary": ("RX_A",),
        "privacy": DatasetPrivacy.RESTRICTED,
        "patients_by_split": {
            "train": ("patient-1",),
            "validation": ("patient-2",),
            "test": ("patient-3",),
        },
        "visits_by_split": {
            "train": (("patient-1", "visit-1"),),
            "validation": (("patient-2", "visit-2"),),
            "test": (("patient-3", "visit-3"),),
        },
    }

    with pytest.raises(ProtocolValidationError, match="HMAC key"):
        DatasetManifest.from_memberships(**kwargs)

    manifest = DatasetManifest.from_memberships(
        **kwargs,
        membership_hmac_key=b"a-private-319-only-key-with-32-bytes",
    )

    assert manifest.membership_digest_method is MembershipDigestMethod.HMAC_SHA256
    assert "patient-1" not in manifest.to_json()


def test_manifest_builder_rejects_visit_assigned_to_wrong_split() -> None:
    with pytest.raises(ProtocolValidationError, match=r"visit patient.*split membership"):
        DatasetManifest.from_memberships(
            dataset_id="synthetic-medrec",
            snapshot_id="v1",
            provenance="synthetic-medrec-v1",
            checksum_sha256="a" * 64,
            medication_vocabulary=("RX_A",),
            privacy=DatasetPrivacy.SYNTHETIC,
            patients_by_split={
                "train": ("patient-1",),
                "validation": ("patient-2",),
                "test": ("patient-3",),
            },
            visits_by_split={
                "train": (("patient-2", "visit-1"),),
                "validation": (("patient-2", "visit-2"),),
                "test": (("patient-3", "visit-3"),),
            },
        )


def test_manifest_verifies_exact_evaluation_visit_membership() -> None:
    manifest = DatasetManifest.from_memberships(
        dataset_id="synthetic-medrec",
        snapshot_id="v1",
        provenance="synthetic-medrec-v1",
        checksum_sha256="a" * 64,
        medication_vocabulary=("RX_A",),
        privacy=DatasetPrivacy.SYNTHETIC,
        patients_by_split={
            "train": ("patient-1",),
            "validation": ("patient-2",),
            "test": ("patient-3",),
        },
        visits_by_split={
            "train": (("patient-1", "visit-1"),),
            "validation": (("patient-2", "visit-2"),),
            "test": (("patient-3", "visit-3"),),
        },
    )

    digest = manifest.verify_evaluation_visits((("patient-3", "visit-3"),))
    assert digest == manifest.split("test").visit_membership_digest

    with pytest.raises(ProtocolValidationError, match="eligible test-visit membership"):
        manifest.verify_evaluation_visits((("patient-3", "different-visit"),))
