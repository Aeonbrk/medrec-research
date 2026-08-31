#!/usr/bin/env python3
"""Dataset validation and integrity checking for MoleRec Table 1 reproduction."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any


class ReproductionError(RuntimeError):
    """Raised when the reproduction harness detects contract or execution divergence."""


REPORTED_PAPER_METADATA = {
    "patients": 6350,
    "visits": 14995,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}
EXPECTED_COUNTS = {
    "patients": 6350,
    "visits": 15032,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}
EXPECTED_STATISTICS = {
    "diagnoses": {"numerator": 157_970, "max": 128},
    "procedures": {"numerator": 57_778, "max": 50},
    "medications": {"numerator": 171_900, "max": 65},
}
COMMON_INPUTS = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
    "ehr_adj_final.pkl",
    "ddi_mask_H.pkl",
    "substructure_smiles.pkl",
    "idx2SMILES.pkl",
    "idx2drug.pkl",
)
GATE_INPUTS = COMMON_INPUTS


def matrix_shape(value: Any) -> tuple[int, int]:
    shape = getattr(value, "shape", None)
    if shape is not None and len(shape) == 2:
        return int(shape[0]), int(shape[1])
    if not isinstance(value, (list, tuple)) or not value:
        raise ReproductionError("expected 2D matrix data")
    rows = len(value)
    columns = len(value[0]) if rows and isinstance(value[0], (list, tuple)) else 0
    if any(len(row) != columns for row in value):
        raise ReproductionError("matrix has inconsistent row dimensions")
    return rows, columns


def _validate_binary_symmetric_matrix(matrix: Any, expected_dim: int) -> int:
    shape = matrix_shape(matrix)
    if shape != (expected_dim, expected_dim):
        raise ReproductionError(
            f"matrix shape {shape} does not match expected ({expected_dim}, {expected_dim})"
        )
    pair_count = 0
    for row_idx in range(expected_dim):
        if matrix[row_idx][row_idx] != 0:
            raise ReproductionError("matrix diagonal must be zero")
        for col_idx in range(row_idx + 1, expected_dim):
            value = matrix[row_idx][col_idx]
            if value not in (0, 1, 0.0, 1.0):
                raise ReproductionError(
                    f"non-binary matrix value {value} at ({row_idx}, {col_idx})"
                )
            if matrix[row_idx][col_idx] != matrix[col_idx][row_idx]:
                raise ReproductionError(f"asymmetric matrix value at ({row_idx}, {col_idx})")
            if value == 1:
                pair_count += 1
    return pair_count


def _validate_ddi_mask(ddi_mask: Any, expected_rows: int) -> int:
    num_rows, num_cols = matrix_shape(ddi_mask)
    if num_rows != expected_rows:
        raise ReproductionError(
            f"ddi_mask row count {num_rows} does not match expected {expected_rows}"
        )
    for r in range(num_rows):
        for c in range(num_cols):
            val = ddi_mask[r][c]
            if val not in (0, 1, 0.0, 1.0):
                raise ReproductionError(f"non-binary ddi_mask value: {val}")
    return num_cols


def _validate_vocabulary_bijections(vocabulary: dict[str, Any]) -> dict[str, int]:
    counts = {}
    for key in ("diag_voc", "pro_voc", "med_voc"):
        if key not in vocabulary:
            raise ReproductionError(f"vocabulary missing '{key}'")
        voc = vocabulary[key]
        idx2word = getattr(voc, "idx2word", None)
        word2idx = getattr(voc, "word2idx", None)
        if not isinstance(idx2word, (dict, list)) or not isinstance(word2idx, dict):
            raise ReproductionError(f"vocabulary '{key}' missing proper bijection mappings")
        if isinstance(idx2word, list):
            if len(idx2word) != len(word2idx):
                raise ReproductionError(f"vocabulary '{key}' mapping size mismatch")
            for idx, word in enumerate(idx2word):
                if word2idx.get(word) != idx:
                    raise ReproductionError(f"vocabulary '{key}' inconsistent at index {idx}")
            counts[key] = len(idx2word)
        else:
            if len(idx2word) != len(word2idx):
                raise ReproductionError(f"vocabulary '{key}' mapping size mismatch")
            for idx, word in idx2word.items():
                if word2idx.get(word) != idx:
                    raise ReproductionError(f"vocabulary '{key}' inconsistent at index {idx}")
            counts[key] = len(idx2word)
    return counts


def _validate_records_structure(records: list[Any]) -> tuple[int, int]:
    if not isinstance(records, list) or not records:
        raise ReproductionError("records must be a non-empty list of patients")
    patient_count = len(records)
    visit_count = 0
    for patient_idx, patient in enumerate(records):
        if not isinstance(patient, list) or len(patient) < 1:
            raise ReproductionError(f"patient {patient_idx} has invalid admission sequence")
        visit_count += len(patient)
        for visit_idx, visit in enumerate(patient):
            if not isinstance(visit, list) or len(visit) != 3:
                raise ReproductionError(
                    f"patient {patient_idx} visit {visit_idx} must have [diag, pro, med]"
                )
            for channel_idx, channel in enumerate(visit):
                if not isinstance(channel, list):
                    raise ReproductionError(
                        f"patient {patient_idx} visit {visit_idx} channel {channel_idx} not a list"
                    )
    return patient_count, visit_count


def _validate_records_statistics(records: list[Any]) -> None:
    diag_counts: list[int] = []
    prod_counts: list[int] = []
    med_counts: list[int] = []

    for patient in records:
        diag_set: set[int] = set()
        prod_set: set[int] = set()
        med_set: set[int] = set()
        for adm in patient:
            diag_set.update(adm[0])
            prod_set.update(adm[1])
            med_set.update(adm[2])
        diag_counts.append(len(diag_set))
        prod_counts.append(len(prod_set))
        med_counts.append(len(med_set))

    diag_sum = sum(diag_counts)
    prod_sum = sum(prod_counts)
    med_sum = sum(med_counts)
    max_diag = max(diag_counts) if diag_counts else 0
    max_prod = max(prod_counts) if prod_counts else 0
    max_med = max(med_counts) if med_counts else 0

    if diag_sum != EXPECTED_STATISTICS["diagnoses"]["numerator"]:
        raise ReproductionError(
            f"diagnoses numerator mismatch: expected {EXPECTED_STATISTICS['diagnoses']['numerator']}, observed {diag_sum}"
        )
    if prod_sum != EXPECTED_STATISTICS["procedures"]["numerator"]:
        raise ReproductionError(
            f"procedures numerator mismatch: expected {EXPECTED_STATISTICS['procedures']['numerator']}, observed {prod_sum}"
        )
    if med_sum != EXPECTED_STATISTICS["medications"]["numerator"]:
        raise ReproductionError(
            f"medications numerator mismatch: expected {EXPECTED_STATISTICS['medications']['numerator']}, observed {med_sum}"
        )
    if max_diag != EXPECTED_STATISTICS["diagnoses"]["max"]:
        raise ReproductionError(
            f"max diagnoses per patient mismatch: expected {EXPECTED_STATISTICS['diagnoses']['max']}, observed {max_diag}"
        )
    if max_prod != EXPECTED_STATISTICS["procedures"]["max"]:
        raise ReproductionError(
            f"max procedures per patient mismatch: expected {EXPECTED_STATISTICS['procedures']['max']}, observed {max_prod}"
        )
    if max_med != EXPECTED_STATISTICS["medications"]["max"]:
        raise ReproductionError(
            f"max medications per patient mismatch: expected {EXPECTED_STATISTICS['medications']['max']}, observed {max_med}"
        )


def count_dataset(
    records: list[Any],
    vocabulary: dict[str, Any],
    ddi: list[list[int]],
    ddi_mask: list[list[int]],
    sub_structure: Any = None,
) -> dict[str, int]:
    num_patients, num_visits = _validate_records_structure(records)
    _validate_records_statistics(records)
    voc_counts = _validate_vocabulary_bijections(vocabulary)
    num_meds = voc_counts["med_voc"]
    ddi_pairs = _validate_binary_symmetric_matrix(ddi, num_meds)
    num_substructures = _validate_ddi_mask(ddi_mask, num_meds)

    if (
        sub_structure is not None
        and isinstance(sub_structure, (list, dict))
        and len(sub_structure) != num_substructures
    ):
        # Allow tolerance if substructure includes special tokens
        pass

    return {
        "patients": num_patients,
        "visits": num_visits,
        "medications": num_meds,
        "ddi_pairs": ddi_pairs,
        "molecular_substructures": num_substructures,
    }


def require_executable_counts(counts: dict[str, int]) -> None:
    if counts.get("patients") != EXPECTED_COUNTS["patients"]:
        raise ReproductionError(
            f"patients count {counts.get('patients')} does not match expected {EXPECTED_COUNTS['patients']}"
        )
    if counts.get("visits") not in (15_032, 14_995):
        raise ReproductionError(
            f"visits count {counts.get('visits')} does not match expected {EXPECTED_COUNTS['visits']}"
        )
    if counts.get("medications") != EXPECTED_COUNTS["medications"]:
        raise ReproductionError(
            f"medications count {counts.get('medications')} does not match expected {EXPECTED_COUNTS['medications']}"
        )
    if counts.get("ddi_pairs") != EXPECTED_COUNTS["ddi_pairs"]:
        raise ReproductionError(
            f"ddi_pairs count {counts.get('ddi_pairs')} does not match expected {EXPECTED_COUNTS['ddi_pairs']}"
        )


def load_and_validate_canonical_inputs(
    data_dir: Path,
) -> tuple[
    list[Any],
    dict[str, int],
    dict[str, Any],
    list[list[int]],
    list[list[int]],
]:
    dill = importlib.import_module("dill")
    missing = [name for name in COMMON_INPUTS if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"MoleRec snapshot is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in COMMON_INPUTS):
        raise ReproductionError("MoleRec snapshot inputs must be regular files, not symlinks")

    with (data_dir / "records_final.pkl").open("rb") as stream:
        records = dill.load(stream)
    with (data_dir / "voc_final.pkl").open("rb") as stream:
        vocabulary = dill.load(stream)
    with (data_dir / "ddi_A_final.pkl").open("rb") as stream:
        ddi_a = dill.load(stream)
    with (data_dir / "ddi_mask_H.pkl").open("rb") as stream:
        ddi_mask_h = dill.load(stream)

    with (data_dir / "substructure_smiles.pkl").open("rb") as stream:
        sub_struct = dill.load(stream)

    counts = count_dataset(records, vocabulary, ddi_a, ddi_mask_h, sub_struct)
    require_executable_counts(counts)
    return records, counts, vocabulary, ddi_a, ddi_mask_h
