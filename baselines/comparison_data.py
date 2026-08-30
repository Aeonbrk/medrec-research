#!/usr/bin/env python3
"""Stage one target-free five-model Comparison cohort on 319."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pickle
import secrets
from pathlib import Path


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _vocabulary(idx2word: object) -> tuple[str, ...]:
    return tuple(str(idx2word[index]) for index in range(len(idx2word)))


def _identifier(key: bytes, kind: str, *indices: int) -> str:
    message = ":".join((kind, *(str(index) for index in indices))).encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _split_ranges(patient_count: int) -> dict[str, range]:
    split_point = int(patient_count * 2 / 3)
    evaluation_length = int((patient_count - split_point) / 2)
    return {
        "train": range(0, split_point),
        "test": range(split_point, split_point + evaluation_length),
        "validation": range(split_point + evaluation_length, patient_count),
    }


def _eligible_memberships(
    records: list[object], key: bytes
) -> tuple[
    dict[str, tuple[str, ...]],
    dict[str, tuple[tuple[str, str], ...]],
    tuple[dict[str, object], ...],
    dict[tuple[str, str], tuple[int, ...]],
]:
    patients_by_split: dict[str, tuple[str, ...]] = {}
    visits_by_split: dict[str, tuple[tuple[str, str], ...]] = {}
    contexts: list[dict[str, object]] = []
    targets: dict[tuple[str, str], tuple[int, ...]] = {}
    for split, patient_indices in _split_ranges(len(records)).items():
        patients: list[str] = []
        visits: list[tuple[str, str]] = []
        for patient_index in patient_indices:
            patient_id = _identifier(key, "patient", patient_index)
            patients.append(patient_id)
            patient = records[patient_index]
            for visit_index in range(1, len(patient)):
                visit_id = _identifier(key, "visit", patient_index, visit_index)
                visit_key = (patient_id, visit_id)
                visits.append(visit_key)
                if split != "test":
                    continue
                history = tuple(
                    (
                        tuple(int(code) for code in admission[0]),
                        tuple(int(code) for code in admission[1]),
                        tuple(int(code) for code in admission[2]),
                    )
                    for admission in patient[:visit_index]
                )
                current = patient[visit_index]
                contexts.append(
                    {
                        "current_diagnoses": tuple(int(code) for code in current[0]),
                        "current_procedures": tuple(int(code) for code in current[1]),
                        "history": history,
                        "patient_id": patient_id,
                        "visit_id": visit_id,
                    }
                )
                targets[visit_key] = tuple(int(code) for code in current[2])
        patients_by_split[split] = tuple(patients)
        visits_by_split[split] = tuple(visits)
    return patients_by_split, visits_by_split, tuple(contexts), targets


def _write_pickle(path: Path, value: object) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    with temporary.open("wb") as stream:
        pickle.dump(value, stream, protocol=pickle.HIGHEST_PROTOCOL)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--dataset-id", default="molerec-table1-comparison-v1-1")
    args = parser.parse_args()

    import dill

    from medrec_research import DatasetManifest
    from medrec_research._validation import content_sha256

    dataset_root = args.dataset_root.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=False)
    key_path = output_root / "membership-hmac.key"
    membership_key = secrets.token_bytes(32)
    key_path.write_bytes(membership_key)
    key_path.chmod(0o600)

    records_path = dataset_root / "records_final.pkl"
    vocabulary_path = dataset_root / "voc_final.pkl"
    ddi_path = dataset_root / "ddi_A_final.pkl"
    records = dill.load(records_path.open("rb"))
    voc = dill.load(vocabulary_path.open("rb"))
    ddi_matrix = dill.load(ddi_path.open("rb"))
    medication_vocabulary = _vocabulary(voc["med_voc"].idx2word)
    voc_size = (
        len(voc["diag_voc"].idx2word),
        len(voc["pro_voc"].idx2word),
        len(medication_vocabulary),
    )
    patients, visits, contexts, integer_targets = _eligible_memberships(records, membership_key)
    targets = {
        key: tuple(medication_vocabulary[index] for index in values)
        for key, values in integer_targets.items()
    }
    ddi_pairs = tuple(
        (medication_vocabulary[left], medication_vocabulary[right])
        for left in range(len(medication_vocabulary))
        for right in range(left + 1, len(medication_vocabulary))
        if ddi_matrix[left][right] == 1
    )
    snapshot_sha256 = content_sha256(
        {
            "ddi_A_final.pkl": _file_sha256(ddi_path),
            "records_final.pkl": _file_sha256(records_path),
            "voc_final.pkl": _file_sha256(vocabulary_path),
        }
    )
    manifest = DatasetManifest.from_memberships(
        dataset_id=args.dataset_id,
        snapshot_id="molerec-table1-c721-www23",
        provenance="SafeDrug archived processing lineage c7218d0976e5ee5588aeaf5bdbc86b338126bba5",
        checksum_sha256=snapshot_sha256,
        medication_vocabulary=medication_vocabulary,
        privacy="restricted",
        patients_by_split=patients,
        visits_by_split=visits,
        membership_hmac_key=membership_key,
    )
    feature_rule = {
        "current_diagnoses": True,
        "current_medications": False,
        "current_procedures": True,
        "eligible_visit_rule": "test visits with at least one prior visit",
        "history_diagnoses": True,
        "history_medications": True,
        "history_procedures": True,
    }
    feature_bundle = {
        "contexts": contexts,
        "dataset_id": args.dataset_id,
        "medication_vocabulary": medication_vocabulary,
        "schema_version": 1,
        "voc_size": voc_size,
    }
    target_bundle = {
        "dataset_id": args.dataset_id,
        "schema_version": 1,
        "targets": targets,
    }
    _write_pickle(output_root / "features.pkl", feature_bundle)
    _write_pickle(output_root / "targets.pkl", target_bundle)
    _write_pickle(output_root / "ddi-pairs.pkl", ddi_pairs)
    (output_root / "dataset-manifest.json").write_text(
        manifest.to_json(indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "dataset_manifest_sha256": manifest.manifest_sha256,
        "ddi_asset_sha256": content_sha256(list(ddi_pairs)),
        "eligible_test_visit_count": len(contexts),
        "feature_availability_sha256": content_sha256(feature_rule),
        "medication_count": len(medication_vocabulary),
        "patient_counts": {split: len(values) for split, values in patients.items()},
        "schema_version": 1,
        "snapshot_sha256": snapshot_sha256,
    }
    (output_root / "public-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
