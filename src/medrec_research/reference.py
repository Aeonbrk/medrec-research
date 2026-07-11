"""Deterministic synthetic reference vertical slice."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from ._validation import (
    content_sha256,
    enum_member,
    parse_json_object,
    require_int,
    require_public_string,
    strict_fields,
)
from .dataset import DatasetManifest, DatasetPrivacy, SplitName
from .errors import ProtocolValidationError
from .evaluation import evaluate_predictions
from .prediction import PredictionRecord
from .protocol_check import ProtocolCheckRecord
from .run_record import ArtifactChecksum, RunParameter

_PROTOCOL_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class ReferenceConfig:
    """Fixed configuration for the train-frequency reference."""

    top_k: int = 2
    seed: int = 0

    def __post_init__(self) -> None:
        require_int(self.top_k, field="top_k", minimum=1)
        require_int(self.seed, field="seed")


def _load_synthetic_records(
    manifest: DatasetManifest,
    visits_path: str | Path,
) -> tuple[PredictionRecord, ...]:
    raw_data = Path(visits_path).read_bytes()
    if sha256(raw_data).hexdigest() != manifest.checksum_sha256:
        raise ProtocolValidationError("synthetic visits checksum does not match DatasetManifest")
    try:
        text = raw_data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProtocolValidationError("synthetic visits must be UTF-8 JSON") from error
    payload = strict_fields(
        parse_json_object(text, context="synthetic visits"),
        required=("schema_version", "patients"),
        context="synthetic visits",
    )
    if payload["schema_version"] != 1:
        raise ProtocolValidationError("synthetic visits schema_version must be 1")
    patients = payload["patients"]
    if not isinstance(patients, list):
        raise ProtocolValidationError("synthetic visits patients must be a list")

    records: list[PredictionRecord] = []
    seen_patient_ids: set[str] = set()
    split_patients = {split: [] for split in SplitName}
    split_visits = {split: [] for split in SplitName}
    for raw_patient in patients:
        patient = strict_fields(
            raw_patient,
            required=("patient_id", "split", "visits"),
            context="synthetic patient",
        )
        patient_id = require_public_string(patient["patient_id"], field="patient_id")
        split = enum_member(SplitName, patient["split"], field="split")
        if patient_id in seen_patient_ids:
            raise ProtocolValidationError(
                "synthetic patient_id values must be unique across splits"
            )
        seen_patient_ids.add(patient_id)
        split_patients[split].append(patient_id)
        visits = patient["visits"]
        if not isinstance(visits, list):
            raise ProtocolValidationError("synthetic patient visits must be a list")
        for raw_visit in visits:
            visit = strict_fields(
                raw_visit,
                required=("visit_id", "target_medications"),
                context="synthetic visit",
            )
            target_medications = visit["target_medications"]
            if not isinstance(target_medications, list):
                raise ProtocolValidationError("target_medications must be a list")
            records.append(
                PredictionRecord(
                    patient_id=patient_id,
                    visit_id=visit["visit_id"],
                    split=split,
                    target_medications=tuple(target_medications),
                    predicted_medications=(),
                )
            )
            split_visits[split].append((patient_id, visit["visit_id"]))

    visit_keys = {(record.patient_id, record.visit_id) for record in records}
    if len(visit_keys) != len(records):
        raise ProtocolValidationError("synthetic visit_id values must be unique per patient")
    observed_vocabulary = list(
        {medication for record in records for medication in record.target_medications}
    )
    if manifest.privacy is not DatasetPrivacy.SYNTHETIC:
        raise ProtocolValidationError("reference harness accepts only synthetic Dataset Manifests")
    observed_manifest = DatasetManifest.from_memberships(
        dataset_id=manifest.dataset_id,
        snapshot_id=manifest.snapshot_id,
        provenance=manifest.provenance,
        checksum_sha256=manifest.checksum_sha256,
        medication_vocabulary=observed_vocabulary,
        privacy=DatasetPrivacy.SYNTHETIC,
        patients_by_split=split_patients,
        visits_by_split=split_visits,
    )
    if observed_manifest != manifest:
        raise ProtocolValidationError(
            "synthetic cohort or vocabulary identity does not match DatasetManifest"
        )
    return tuple(records)


def run_reference_slice(
    manifest_path: str | Path,
    visits_path: str | Path,
    *,
    config: ReferenceConfig | None = None,
) -> ProtocolCheckRecord:
    """Run the synthetic harness and return a non-evidentiary protocol check."""

    config = ReferenceConfig() if config is None else config
    manifest = DatasetManifest.load(manifest_path)
    records = _load_synthetic_records(manifest, visits_path)
    frequencies = Counter(
        medication
        for record in records
        if record.split is SplitName.TRAIN
        for medication in record.target_medications
    )
    if not frequencies:
        raise ProtocolValidationError("reference baseline requires training medications")
    predicted_medications = tuple(
        medication
        for medication, _ in sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))[
            : config.top_k
        ]
    )
    test_predictions = tuple(
        PredictionRecord(
            patient_id=record.patient_id,
            visit_id=record.visit_id,
            split=record.split,
            target_medications=record.target_medications,
            predicted_medications=predicted_medications,
        )
        for record in records
        if record.split is SplitName.TEST
    )
    evaluation = evaluate_predictions(test_predictions)
    return ProtocolCheckRecord.create(
        protocol_version=_PROTOCOL_VERSION,
        dataset=manifest,
        parameters=(
            RunParameter("seed", config.seed),
            RunParameter("strategy", "train-frequency"),
            RunParameter("top_k", config.top_k),
        ),
        evaluation=evaluation,
        artifact_checksums=(
            ArtifactChecksum(
                "synthetic-predictions",
                content_sha256([record.to_dict() for record in test_predictions]),
            ),
        ),
        checks=(
            "dataset-manifest-verified",
            "deterministic-evaluation",
            "test-targets-core-owned",
        ),
    )


__all__ = ("ReferenceConfig", "run_reference_slice")
