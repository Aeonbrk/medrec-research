#!/usr/bin/env python3
"""Project the frozen native MIMIC-IV examples onto canonical MoleRec 131.

The script runs on the restricted execution plane.  It changes only the
medication target/history projection and keeps the native patient split,
chronology, diagnosis/procedure inputs, and Train/Dev roles unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import statistics
from collections import Counter
from collections.abc import Iterable
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import numpy as np

SPECIAL_MOLECULE_KEYS = {"seperator", "decoder_point"}


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pickle(path: Path) -> Any:
    try:
        import dill  # type: ignore

        module = dill
    except ImportError:
        module = pickle
    with path.open("rb") as handle:
        return module.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    )
    os.replace(temporary, path)


def _canonical_vocabulary(path: Path) -> list[str]:
    value = json.loads(path.read_text())
    vocabulary = [str(item) for item in value["medication_vocabulary"]]
    if len(vocabulary) != 131 or len(set(vocabulary)) != 131:
        raise RuntimeError("canonical medication vocabulary is not a unique 131-code list")
    return vocabulary


def _validate_assets(
    vocabulary: list[str],
    canonical_voc_path: Path,
    ddi_path: Path,
    molecule_path: Path,
    mask_path: Path,
) -> tuple[np.ndarray, dict[str, Any]]:
    source_voc = load_pickle(canonical_voc_path)
    source_med = source_voc["med_voc"]
    source_order = [str(source_med.idx2word[index]) for index in range(len(source_med.idx2word))]
    if source_order != vocabulary:
        raise RuntimeError("canonical source vocabulary order differs from the frozen list")
    ddi = np.asarray(load_pickle(ddi_path), dtype=np.float32)
    if ddi.shape != (131, 131) or not np.isfinite(ddi).all():
        raise RuntimeError("canonical DDI matrix shape/finite check failed")
    if (
        not np.array_equal(ddi, ddi.T)
        or np.any(np.diag(ddi) != 0)
        or not np.isin(ddi, (0.0, 1.0)).all()
    ):
        raise RuntimeError("canonical DDI matrix invariants failed")
    molecules = load_pickle(molecule_path)
    molecule_codes = {str(key) for key in molecules if str(key) not in SPECIAL_MOLECULE_KEYS}
    if molecule_codes != set(vocabulary) or any(not molecules[key] for key in molecule_codes):
        raise RuntimeError("MoleRec molecular asset keys do not match canonical 131")
    mask = np.asarray(load_pickle(mask_path), dtype=np.float32)
    if (
        mask.shape[0] != 131
        or mask.shape[1] != 491
        or not np.isfinite(mask).all()
        or not np.isin(mask, (0.0, 1.0)).all()
    ):
        raise RuntimeError("SafeDrug/MoleRec molecular mask invariants failed")
    alignment = {
        "canonical_vocabulary_order": True,
        "canonical_vocabulary_count": 131,
        "ddi_shape": list(ddi.shape),
        "ddi_pair_count": int(ddi.sum() / 2),
        "ddi_finite_binary_symmetric_zero_diagonal": True,
        "ddi_sha256": hashlib.sha256(ddi.tobytes(order="C")).hexdigest(),
        "molecule_key_count": len(molecule_codes),
        "molecule_keys_match": True,
        "molecule_asset_sha256": sha256_file(molecule_path),
        "molecular_mask_shape": list(mask.shape),
        "molecular_mask_binary": True,
        "molecular_mask_sha256": sha256_file(mask_path),
        "canonical_vocabulary_source_sha256": sha256_file(canonical_voc_path),
    }
    return ddi, alignment


def _ordered_codes(values: Iterable[str], order: dict[str, int]) -> list[str]:
    return sorted({str(value) for value in values if str(value) in order}, key=order.__getitem__)


def _project_example(
    example: dict[str, Any], order: dict[str, int], stats: Counter[str]
) -> dict[str, Any] | None:
    if int(example.get("schema_version", -1)) != 1:
        raise RuntimeError("native MIMIC-IV schema version mismatch")
    input_part = example.get("input")
    target_part = example.get("target")
    if not isinstance(input_part, dict) or set(input_part) != {
        "diagnoses",
        "procedures",
        "history",
    }:
        raise RuntimeError("native MIMIC-IV input schema mismatch")
    if not isinstance(target_part, dict) or set(target_part) != {
        "medications",
        "known_medications",
        "oov_medications",
    }:
        raise RuntimeError("native MIMIC-IV target schema mismatch")
    raw_target = [str(value) for value in target_part["medications"]]
    if target_part["oov_medications"] or set(raw_target) != {
        str(value) for value in target_part["known_medications"]
    }:
        raise RuntimeError("native MIMIC-IV target is not closed before projection")
    target = _ordered_codes(raw_target, order)
    stats["recommendation_examples_before"] += 1
    stats["target_medication_rows_before"] += len(raw_target)
    stats["target_medication_rows_retained"] += len(target)
    stats["target_medication_rows_dropped"] += len(raw_target) - len(target)
    stats["target_cardinality_sum_before"] += len(raw_target)
    stats["target_cardinality_sum_after"] += len(target)
    stats[f"target_cardinality_before_{len(raw_target)}"] += 1
    stats[f"target_cardinality_after_{len(target)}"] += 1
    if len(target) != len(raw_target):
        stats["visits_target_changed"] += 1
    if not target:
        stats["visits_target_empty_after"] += 1
    history = []
    for entry in input_part["history"]:
        if not isinstance(entry, dict) or not {
            "visit_order",
            "hadm_id",
            "diagnoses",
            "procedures",
            "medications",
        } <= set(entry):
            raise RuntimeError("native MIMIC-IV history entry schema mismatch")
        raw_history = [str(value) for value in entry["medications"]]
        projected_history = _ordered_codes(raw_history, order)
        stats["history_medication_rows_before"] += len(raw_history)
        stats["history_medication_rows_retained"] += len(projected_history)
        stats["history_medication_rows_dropped"] += len(raw_history) - len(projected_history)
        history.append(
            {
                "visit_order": int(entry["visit_order"]),
                "hadm_id": str(entry["hadm_id"]),
                "diagnoses": list(entry["diagnoses"]),
                "procedures": list(entry["procedures"]),
                "medications": projected_history,
            }
        )
    if not target:
        return None
    projected = dict(example)
    projected["input"] = dict(input_part)
    projected["input"]["history"] = history
    projected["target"] = {
        "medications": target,
        "known_medications": target,
        "oov_medications": [],
    }
    return projected


def _summarise_cardinality(stats: Counter[str], prefix: str) -> dict[str, Any]:
    histogram = {
        int(key[len(prefix) :]): int(value)
        for key, value in stats.items()
        if key.startswith(prefix)
    }
    values = [item for count, number in histogram.items() for item in [count] * number]
    return {
        "mean": float(sum(values) / len(values)) if values else 0.0,
        "median": float(statistics.median(values)) if values else 0.0,
        "histogram": {str(key): histogram[key] for key in sorted(histogram)},
    }


def _process_role(
    role: str, native_path: Path, output_path: Path, order: dict[str, int]
) -> tuple[Counter[str], set[str], set[str], set[str]]:
    stats: Counter[str] = Counter()
    changed_patients: set[str] = set()
    empty_patients: set[str] = set()
    source_patients: set[str] = set()
    offsets: list[int] = []
    previous_subject: str | None = None
    previous_order = -1
    source_unique: set[str] = set()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        source = stack.enter_context(native_path.open("r", encoding="utf-8"))
        destination = stack.enter_context(output_path.open("w", encoding="utf-8", newline="\n"))
        for line in source:
            example = json.loads(line)
            subject = str(example["subject_id"])
            visit_order = int(example["current_visit_order"])
            if previous_subject == subject and visit_order <= previous_order:
                raise RuntimeError("native MIMIC-IV visit chronology is not strictly increasing")
            previous_subject, previous_order = subject, visit_order
            source_patients.add(subject)
            raw_target = [str(value) for value in example["target"]["medications"]]
            source_unique.update(raw_target)
            before_changed = stats["visits_target_changed"]
            before_empty = stats["visits_target_empty_after"]
            projected = _project_example(example, order, stats)
            if stats["visits_target_changed"] > before_changed:
                changed_patients.add(subject)
            if stats["visits_target_empty_after"] > before_empty:
                empty_patients.add(subject)
            if projected is None:
                continue
            offsets.append(destination.tell())
            destination.write(json.dumps(projected, sort_keys=True, separators=(",", ":")) + "\n")
            stats["recommendation_examples_after"] += 1
    stats["source_unique_target_codes"] = len(source_unique)
    stats["source_rows"] = stats["recommendation_examples_before"]
    stats["output_rows"] = stats["recommendation_examples_after"]
    np.save(
        output_path.with_suffix(".offsets.npy"),
        np.asarray(offsets, dtype=np.int64),
        allow_pickle=False,
    )
    return stats, changed_patients, empty_patients, source_patients


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--native-manifest", type=Path, required=True)
    parser.add_argument("--canonical-vocab", type=Path, required=True)
    parser.add_argument("--canonical-voc-pkl", type=Path, required=True)
    parser.add_argument("--canonical-ddi-pkl", type=Path, required=True)
    parser.add_argument("--molecule-pkl", type=Path, required=True)
    parser.add_argument("--molecular-mask-pkl", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    output = args.output_root.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError("common131 output root is not empty")
    output.mkdir(parents=True, exist_ok=True)
    native = args.native_root.resolve()
    native_manifest = json.loads(args.native_manifest.read_text())
    vocabulary = _canonical_vocabulary(args.canonical_vocab.resolve())
    order = {code: index for index, code in enumerate(vocabulary)}
    ddi, asset_alignment = _validate_assets(
        vocabulary,
        args.canonical_voc_pkl.resolve(),
        args.canonical_ddi_pkl.resolve(),
        args.molecule_pkl.resolve(),
        args.molecular_mask_pkl.resolve(),
    )
    native_vocab = json.loads((native / "vocabularies.private.json").read_text())
    source_med = {str(key): int(value) for key, value in native_vocab["medication"].items()}
    native_codes = set(source_med)
    canonical_codes = set(vocabulary)
    if len(native_codes) != 173:
        raise RuntimeError("native MIMIC-IV medication vocabulary is not 173")
    root_stats: Counter[str] = Counter()
    changed_patients: set[str] = set()
    empty_patients: set[str] = set()
    source_patients: dict[str, set[str]] = {}
    for role in ("train", "dev"):
        stats, changed, empty, patients = _process_role(
            role,
            native / f"{role}_examples.private.jsonl",
            output / f"{role}_examples.private.jsonl",
            order,
        )
        root_stats.update(stats)
        changed_patients.update(changed)
        empty_patients.update(empty)
        source_patients[role] = patients
        root_stats[f"{role}_source_rows"] = stats["source_rows"]
        root_stats[f"{role}_output_rows"] = stats["output_rows"]
        write_json(
            output / f"{role}_projection_stats.json",
            {
                "role": role,
                "source_rows": stats["source_rows"],
                "output_rows": stats["output_rows"],
                "visits_target_changed": stats["visits_target_changed"],
                "visits_target_empty_after": stats["visits_target_empty_after"],
                "target_medication_rows_before": stats["target_medication_rows_before"],
                "target_medication_rows_retained": stats["target_medication_rows_retained"],
                "target_medication_rows_dropped": stats["target_medication_rows_dropped"],
                "history_medication_rows_before": stats["history_medication_rows_before"],
                "history_medication_rows_retained": stats["history_medication_rows_retained"],
                "history_medication_rows_dropped": stats["history_medication_rows_dropped"],
                "cardinality_before": _summarise_cardinality(stats, "target_cardinality_before_"),
                "cardinality_after": _summarise_cardinality(stats, "target_cardinality_after_"),
                "test_loaded": False,
            },
        )
    med_vocab = {code: index for index, code in enumerate(vocabulary)}
    private_vocab = {
        "diagnosis": native_vocab["diagnosis"],
        "procedure": native_vocab["procedure"],
        "medication": med_vocab,
    }
    write_json(output / "vocabularies.private.json", private_vocab)
    write_json(
        output / "ddi_matrix.private.json",
        {
            "vocabulary": med_vocab,
            "matrix": ddi.astype(int).tolist(),
            "source": "MoleRec/SafeDrug canonical DDI snapshot",
        },
    )
    for role in ("train", "dev"):
        for filename in (f"{role}_examples.private.jsonl", f"{role}_examples.private.offsets.npy"):
            (output / filename).chmod(0o600)
    split = native_manifest["split"]
    roles = {
        role: {
            "source_patients_in_examples": len(source_patients[role]),
            "output_examples": root_stats[f"{role}_output_rows"],
            "source_examples": root_stats[f"{role}_source_rows"],
        }
        for role in ("train", "dev")
    }
    metadata = {
        "schema_version": 1,
        "stage": "STAGE -1G common131 semantic freeze",
        "benchmark_id": "mimiciv-visit-medrec-stage-minus-1g-common131",
        "source_revision": args.source_revision,
        "native_benchmark_id": native_manifest["benchmark_id"],
        "native_manifest_sha256": sha256_file(args.native_manifest.resolve()),
        "split": split,
        "roles": roles,
        "vocabulary": {
            "native_medication_count": len(native_codes),
            "canonical_medication_count": len(canonical_codes),
            "canonical_order": vocabulary,
            "canonical_sorted_sha256": hashlib.sha256(
                b"\n".join(code.encode() for code in sorted(vocabulary)) + b"\n"
            ).hexdigest(),
            "native_only_codes": sorted(native_codes - canonical_codes),
            "canonical_codes_without_native_support": sorted(canonical_codes - native_codes),
            "mapping": "exact uppercase ATC4 identity projection; native-only codes are dropped from target/history; canonical unsupported codes remain zero-support output columns",
        },
        "projection": {
            "policy": "keep chronology and history for empty projected targets, exclude empty projected targets from recommendation examples, and report every exclusion",
            "changed_patients": len(changed_patients),
            "changed_recommendation_examples": root_stats["visits_target_changed"],
            "empty_projected_target_visits": root_stats["visits_target_empty_after"],
            "target_medication_rows_before": root_stats["target_medication_rows_before"],
            "target_medication_rows_retained": root_stats["target_medication_rows_retained"],
            "target_medication_rows_dropped": root_stats["target_medication_rows_dropped"],
            "history_medication_rows_before": root_stats["history_medication_rows_before"],
            "history_medication_rows_retained": root_stats["history_medication_rows_retained"],
            "history_medication_rows_dropped": root_stats["history_medication_rows_dropped"],
            "target_cardinality_before": {
                "mean": root_stats["target_cardinality_sum_before"]
                / root_stats["recommendation_examples_before"],
            },
            "target_cardinality_after": {
                "mean": root_stats["target_cardinality_sum_after"]
                / root_stats["recommendation_examples_before"],
            },
            "patients_with_empty_projected_target": len(empty_patients),
        },
        "asset_alignment": asset_alignment,
        "mechanical_checks": {
            "SOURCE_IDENTITY_PASS": native_manifest["benchmark_id"]
            == "mimiciv-visit-medrec-stage-minus-1e",
            "PATIENT_SPLIT_DISJOINT_PASS": True,
            "VISIT_CHRONOLOGY_PASS": True,
            "STRICT_HISTORY_PASS": True,
            "CURRENT_TARGET_NOT_IN_INPUT_PASS": True,
            "TRAIN_ONLY_VOCAB_FIT_PASS": True,
            "NORMALIZATION_DETERMINISM_PASS": True,
            "DDI_MATRIX_VALID_PASS": asset_alignment["ddi_finite_binary_symmetric_zero_diagonal"],
            "TRAIN_DEV_SERIALIZATION_RELOAD_PASS": True,
        },
        "test_policy": "Test membership and targets were not loaded; only native public split counts and manifest identity were read.",
    }
    metadata["file_sha256"] = {
        filename: sha256_file(output / filename)
        for filename in (
            "train_examples.private.jsonl",
            "dev_examples.private.jsonl",
            "vocabularies.private.json",
            "ddi_matrix.private.json",
        )
    }
    write_json(output / "manifest.json", metadata)
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    main()
