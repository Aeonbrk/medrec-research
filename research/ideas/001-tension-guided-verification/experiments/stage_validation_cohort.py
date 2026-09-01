#!/usr/bin/env python3
"""Idea-local validation cohort staging helper.

Runs under Python 3.8 in `medrec-molerec-table1` (with dill) on 319.
Produces restricted feature bundle and plain-JSON metadata for Python 3.11 runner.
Accesses only the validation split of the snapshot. Test split is never touched.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
from collections.abc import Iterable
from pathlib import Path


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _content_sha256(value: object) -> str:
    serialized = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode("ascii")).hexdigest()


def _vocabulary_sha256(vocabulary: Iterable[str]) -> str:
    """Authoritative medication vocabulary hash matching DatasetManifest._ordered_digest."""
    serialized = "".join(f"{code}\n" for code in sorted(vocabulary))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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


def _vocabulary(idx2word: object) -> tuple[str, ...]:
    return tuple(str(idx2word[index]) for index in range(len(idx2word)))  # type: ignore[index]


FEATURE_RULE = {
    "current_diagnoses": True,
    "current_medications": False,
    "current_procedures": True,
    "eligible_visit_rule": "test visits with at least one prior visit",
    "history_diagnoses": True,
    "history_medications": True,
    "history_procedures": True,
}


def stage_validation(
    dataset_root: Path,
    output_dir: Path,
    dataset_id: str = "molerec-table1-comparison-v1-1",
    membership_key: bytes | None = None,
) -> dict[str, object]:
    try:
        import dill as serializer
    except ImportError:
        import pickle as serializer  # type: ignore[no-redef]

    dataset_root = dataset_root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if membership_key is None:
        membership_key = secrets.token_bytes(32)

    records_path = dataset_root / "records_final.pkl"
    vocabulary_path = dataset_root / "voc_final.pkl"
    ddi_path = dataset_root / "ddi_A_final.pkl"

    with records_path.open("rb") as stream:
        records = serializer.load(stream)
    with vocabulary_path.open("rb") as stream:
        voc = serializer.load(stream)
    with ddi_path.open("rb") as stream:
        ddi_matrix = serializer.load(stream)

    medication_vocabulary = _vocabulary(voc["med_voc"].idx2word)
    voc_size = (
        len(voc["diag_voc"].idx2word),
        len(voc["pro_voc"].idx2word),
        len(medication_vocabulary),
    )

    # 1. Compute raw DDI asset identity using authority algorithm from baselines/comparison_data.py
    raw_ddi_pairs = tuple(
        (medication_vocabulary[left], medication_vocabulary[right])
        for left in range(len(medication_vocabulary))
        for right in range(left + 1, len(medication_vocabulary))
        if ddi_matrix[left][right] == 1
    )
    ddi_asset_sha256 = _content_sha256(list(raw_ddi_pairs))

    # 2. Canonicalize every DDI relation with unordered-pair semantics: tuple(sorted((left, right)))
    canonical_ddi_set = set()
    for left, right in raw_ddi_pairs:
        canonical_ddi_set.add(tuple(sorted((left, right))))
    canonical_ddi_pairs = sorted(canonical_ddi_set)
    canonical_ddi_semantics_sha256 = _content_sha256(canonical_ddi_pairs)

    # 3. Extract strictly validation split; never read, evaluate, or index test split
    splits = _split_ranges(len(records))
    validation_patient_indices = splits["validation"]

    contexts: list[dict[str, object]] = []
    expected_visits: list[list[str]] = []
    targets: dict[str, list[str]] = {}
    visit_traversal_metadata: list[dict[str, object]] = []

    for patient_order, patient_index in enumerate(validation_patient_indices):
        patient_id = _identifier(membership_key, "patient", patient_index)
        patient = records[patient_index]
        for visit_order, visit_index in enumerate(range(1, len(patient)), start=1):
            visit_id = _identifier(membership_key, "visit", patient_index, visit_index)
            visit_key = f"{patient_id}:{visit_id}"
            expected_visits.append([patient_id, visit_id])

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
            med_targets = [medication_vocabulary[int(code)] for code in current[2]]
            targets[visit_key] = med_targets

            visit_traversal_metadata.append(
                {
                    "patient_id": patient_id,
                    "visit_id": visit_id,
                    "patient_order": patient_order,
                    "visit_order": visit_order,
                }
            )

    # Write features.pkl for molerec_comparison.py
    features_bundle = {
        "contexts": contexts,
        "dataset_id": dataset_id,
        "medication_vocabulary": medication_vocabulary,
        "schema_version": 1,
        "voc_size": voc_size,
    }
    features_path = output_dir / "features.pkl"
    with features_path.open("wb") as stream:
        serializer.dump(features_bundle, stream)

    # Compute checksums
    snapshot_sha256 = _content_sha256(
        {
            "ddi_A_final.pkl": _file_sha256(ddi_path),
            "records_final.pkl": _file_sha256(records_path),
            "voc_final.pkl": _file_sha256(vocabulary_path),
        }
    )
    vocab_sha256 = _vocabulary_sha256(medication_vocabulary)
    feature_availability_sha256 = _content_sha256(FEATURE_RULE)

    meta = {
        "dataset_id": dataset_id,
        "features_path": str(features_path),
        "expected_visits": expected_visits,
        "targets": targets,
        "ddi_pairs": [list(pair) for pair in canonical_ddi_pairs],
        "medication_vocabulary": list(medication_vocabulary),
        "visit_traversal_metadata": visit_traversal_metadata,
        "snapshot_sha256": snapshot_sha256,
        "ddi_asset_sha256": ddi_asset_sha256,
        "canonical_ddi_semantics_sha256": canonical_ddi_semantics_sha256,
        "feature_availability_sha256": feature_availability_sha256,
        "medication_vocabulary_sha256": vocab_sha256,
        "validation_patient_count": len(validation_patient_indices),
        "validation_visit_count": len(contexts),
    }

    meta_path = output_dir / "validation-meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True, help="Snapshot root directory")
    parser.add_argument("--output-dir", type=Path, required=True, help="Staging output directory")
    parser.add_argument("--dataset-id", default="molerec-table1-comparison-v1-1")
    args = parser.parse_args()

    meta = stage_validation(
        dataset_root=args.dataset_root,
        output_dir=args.output_dir,
        dataset_id=args.dataset_id,
    )
    print(
        json.dumps(
            {
                "features_path": meta["features_path"],
                "validation_patient_count": meta["validation_patient_count"],
                "validation_visit_count": meta["validation_visit_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
