#!/usr/bin/env python3
"""Dataset validation, statistics checking, and semantic bridge checks for archived SafeDrug."""

from __future__ import annotations

import importlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class ReproductionError(RuntimeError):
    """Raised when an archived reproduction contract is not satisfied."""


CANONICAL_SIX_INPUTS = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
    "ddi_mask_H.pkl",
    "ehr_adj_final.pkl",
    "idx2drug.pkl",
)
EXPECTED_COUNTS = {
    "patients": 6_350,
    "visits": 15_032,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}
REPORTED_PAPER_METADATA = {
    "paper_reported_visits": 14_995,
    "executable_visits": 15_032,
    "difference": 37,
}
EXPECTED_STATISTICS = {
    "diagnoses": {"numerator": 157_970, "max": 128},
    "procedures": {"numerator": 57_778, "max": 50},
    "medications": {"numerator": 171_900, "max": 65},
}


def matrix_shape(value: Any) -> tuple[int, int]:
    shape = getattr(value, "shape", None)
    if shape is not None and len(shape) == 2:
        return int(shape[0]), int(shape[1])
    rows = len(value)
    columns = len(value[0]) if rows else 0
    if any(len(row) != columns for row in value):
        raise ReproductionError("matrix rows have inconsistent lengths")
    return rows, columns


def count_dataset(records: Any, voc: Any, ddi_adjacency: Any, ddi_mask: Any) -> dict[str, int]:
    """Return paper aggregate counts from already loaded archived values."""
    try:
        ddi_rows, ddi_columns = matrix_shape(ddi_adjacency)
        mask_rows, mask_columns = matrix_shape(ddi_mask)
        medications = len(voc["med_voc"].idx2word)
        counts = {
            "patients": len(records),
            "visits": sum(len(patient) for patient in records),
            "medications": medications,
            "ddi_pairs": sum(
                bool(ddi_adjacency[row][column])
                for row in range(ddi_rows)
                for column in range(row + 1, ddi_columns)
            ),
            "molecular_substructures": mask_columns,
        }
    except (AttributeError, IndexError, KeyError, TypeError) as error:
        raise ReproductionError("archived dataset values have an invalid structure") from error
    if (ddi_rows, ddi_columns) != (medications, medications):
        raise ReproductionError(
            f"ddi_A_final shape must be {medications} x {medications}, observed "
            f"{ddi_rows} x {ddi_columns}"
        )
    if mask_rows != medications:
        raise ReproductionError(
            f"ddi_mask_H rows must equal medication count {medications}, observed {mask_rows}"
        )
    return counts


def require_executable_counts(counts: dict[str, int]) -> None:
    differences = {
        name: {"expected": expected, "observed": counts.get(name)}
        for name, expected in EXPECTED_COUNTS.items()
        if counts.get(name) != expected
    }
    if differences:
        raise ReproductionError(
            f"archived B0 executable data gate failed: {json.dumps(differences)}"
        )


def _validate_records_statistics(records: Any, total_visits: int) -> dict[str, Any]:
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

    return {
        "diagnoses": {
            "numerator": diag_sum,
            "average": round(diag_sum / total_visits, 4),
            "max": max_diag,
        },
        "procedures": {
            "numerator": prod_sum,
            "average": round(prod_sum / total_visits, 4),
            "max": max_prod,
        },
        "medications": {
            "numerator": med_sum,
            "average": round(med_sum / total_visits, 4),
            "max": max_med,
        },
        "corroboration": {"pre_grouping_medication_rows": 288_542},
    }


def _validate_vocabulary_bijections(voc: Any) -> None:
    if not isinstance(voc, Mapping):
        raise ReproductionError("voc_final must be a mapping containing vocabularies")
    for key in ("diag_voc", "pro_voc", "med_voc"):
        if key not in voc:
            raise ReproductionError(f"voc_final is missing vocabulary '{key}'")
        sub_voc = voc[key]
        idx2word = getattr(sub_voc, "idx2word", None)
        word2idx = getattr(sub_voc, "word2idx", None)
        if idx2word is None or word2idx is None:
            raise ReproductionError(f"vocabulary '{key}' missing idx2word or word2idx mapping")
        if not isinstance(word2idx, Mapping):
            raise ReproductionError(f"vocabulary '{key}' word2idx must be a mapping")

        num_words = len(idx2word) if isinstance(idx2word, (list, tuple)) else len(idx2word.keys())
        if len(word2idx) != num_words:
            raise ReproductionError(
                f"vocabulary '{key}' size mismatch: idx2word has {num_words} entries, word2idx has {len(word2idx)}"
            )

        if isinstance(idx2word, (list, tuple)):
            for idx, word in enumerate(idx2word):
                if word2idx.get(word) != idx:
                    raise ReproductionError(
                        f"vocabulary '{key}' bijection failure at index {idx} for word '{word}'"
                    )
        elif isinstance(idx2word, Mapping):
            expected_indices = set(range(num_words))
            if set(idx2word.keys()) != expected_indices:
                raise ReproductionError(
                    f"vocabulary '{key}' idx2word keys must be contiguous integers 0..{num_words - 1}"
                )
            for idx, word in idx2word.items():
                if word2idx.get(word) != idx:
                    raise ReproductionError(
                        f"vocabulary '{key}' bijection failure at index {idx} for word '{word}'"
                    )
        else:
            raise ReproductionError(f"vocabulary '{key}' idx2word must be list, tuple, or mapping")

    if len(voc["med_voc"].idx2word) != EXPECTED_COUNTS["medications"]:
        raise ReproductionError(
            f"med_voc size must equal {EXPECTED_COUNTS['medications']}, observed {len(voc['med_voc'].idx2word)}"
        )


def _validate_records_structure(records: Any, voc: Any) -> None:
    if not isinstance(records, list):
        raise ReproductionError("records_final must be a list of patients")
    if len(records) != EXPECTED_COUNTS["patients"]:
        raise ReproductionError(
            f"records_final must contain {EXPECTED_COUNTS['patients']} patients, observed {len(records)}"
        )

    diag_size = len(voc["diag_voc"].idx2word)
    pro_size = len(voc["pro_voc"].idx2word)
    med_size = len(voc["med_voc"].idx2word)

    total_visits = 0
    for p_idx, patient in enumerate(records):
        if not isinstance(patient, list):
            raise ReproductionError(f"patient {p_idx} must be a list of admissions")
        total_visits += len(patient)
        for a_idx, admission in enumerate(patient):
            if not isinstance(admission, (list, tuple)) or len(admission) != 3:
                raise ReproductionError(
                    f"patient {p_idx} admission {a_idx} must contain exactly [diagnoses, procedures, medications]"
                )
            diags, pros, meds = admission
            for mod_name, mod_list, max_size in (
                ("diagnoses", diags, diag_size),
                ("procedures", pros, pro_size),
                ("medications", meds, med_size),
            ):
                if not isinstance(mod_list, (list, tuple)):
                    raise ReproductionError(
                        f"patient {p_idx} admission {a_idx} {mod_name} must be a list or tuple"
                    )
                if len(mod_list) != len(set(mod_list)):
                    raise ReproductionError(
                        f"patient {p_idx} admission {a_idx} {mod_name} contains duplicate indices"
                    )
                for code_idx in mod_list:
                    if type(code_idx) is not int or not (0 <= code_idx < max_size):
                        raise ReproductionError(
                            f"patient {p_idx} admission {a_idx} {mod_name} contains invalid index {code_idx} (domain: 0..{max_size - 1})"
                        )

    if total_visits != EXPECTED_COUNTS["visits"]:
        raise ReproductionError(
            f"total visits must equal {EXPECTED_COUNTS['visits']}, observed {total_visits}"
        )


def _validate_idx2drug_contract(idx2drug: Any, med_voc: Any) -> None:
    if not isinstance(idx2drug, Mapping):
        raise ReproductionError("idx2drug must be a mapping")

    idx2word = med_voc.idx2word
    if isinstance(idx2word, (list, tuple)):
        med_codes = list(idx2word)
    else:
        med_codes = [idx2word[i] for i in range(len(idx2word))]

    expected_keys = set(med_codes) | {"seperator", "decoder_point"}
    observed_keys = set(idx2drug.keys())
    if observed_keys != expected_keys:
        missing = sorted(str(k) for k in (expected_keys - observed_keys))
        extra = sorted(str(k) for k in (observed_keys - expected_keys))
        raise ReproductionError(f"idx2drug keys mismatch: missing {missing[:5]}, extra {extra[:5]}")

    for special in ("seperator", "decoder_point"):
        val = idx2drug[special]
        if not isinstance(val, Mapping) or len(val) != 0:
            raise ReproductionError(
                f"idx2drug special key '{special}' must be an empty mapping, observed {type(val)}"
            )

    for code in med_codes:
        val = idx2drug[code]
        if not val:
            raise ReproductionError(
                f"idx2drug entry for code '{code}' must be a non-empty molecule structure"
            )


def _validate_binary_symmetric_matrix(
    matrix: Any,
    expected_size: int,
    name: str,
    *,
    require_zero_diagonal: bool = True,
) -> None:
    rows, cols = matrix_shape(matrix)
    if (rows, cols) != (expected_size, expected_size):
        raise ReproductionError(
            f"{name} shape must be {expected_size} x {expected_size}, observed {rows} x {cols}"
        )
    for r in range(rows):
        if require_zero_diagonal and matrix[r][r] != 0:
            raise ReproductionError(
                f"{name} must have zero diagonal, observed {matrix[r][r]} at ({r}, {r})"
            )
        for c in range(cols):
            val = matrix[r][c]
            if val not in (0, 1, 0.0, 1.0):
                raise ReproductionError(
                    f"{name} must be binary, observed non-binary value {val} at ({r}, {c})"
                )
            if matrix[r][c] != matrix[c][r]:
                raise ReproductionError(
                    f"{name} must be symmetric, mismatch at ({r}, {c}) vs ({c}, {r})"
                )


def _validate_ddi_mask(ddi_mask: Any, med_count: int, substructure_count: int) -> None:
    rows, cols = matrix_shape(ddi_mask)
    if (rows, cols) != (med_count, substructure_count):
        raise ReproductionError(
            f"ddi_mask_H shape must be {med_count} x {substructure_count}, observed {rows} x {cols}"
        )
    for r in range(rows):
        for c in range(cols):
            val = ddi_mask[r][c]
            if val not in (0, 1, 0.0, 1.0) or not math.isfinite(float(val)):
                raise ReproductionError(
                    f"ddi_mask_H must be binary and finite, observed {val} at ({r}, {c})"
                )


def load_and_validate_canonical_inputs(
    data_dir: Path,
) -> tuple[dict[str, str], dict[str, int], dict[str, str], dict[str, Any], dict[str, int]]:
    dill = importlib.import_module("dill")
    missing = [name for name in CANONICAL_SIX_INPUTS if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"archived dataset is missing canonical inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in CANONICAL_SIX_INPUTS):
        raise ReproductionError("archived dataset inputs must be regular files, not symlinks")

    loaded: dict[str, Any] = {}
    for name in CANONICAL_SIX_INPUTS:
        with (data_dir / name).open("rb") as stream:
            try:
                loaded[name] = dill.load(stream)
            except Exception as error:
                raise ReproductionError(
                    f"failed to load canonical input '{name}': {error}"
                ) from error

    records = loaded["records_final.pkl"]
    voc = loaded["voc_final.pkl"]
    ddi_A = loaded["ddi_A_final.pkl"]
    ddi_mask = loaded["ddi_mask_H.pkl"]
    ehr_adj = loaded["ehr_adj_final.pkl"]
    idx2drug = loaded["idx2drug.pkl"]

    counts = count_dataset(records, voc, ddi_A, ddi_mask)
    require_executable_counts(counts)

    medications = counts["medications"]
    molecular_substructures = counts["molecular_substructures"]

    # Semantic Bridge Checks
    _validate_vocabulary_bijections(voc)
    _validate_records_structure(records, voc)
    _validate_idx2drug_contract(idx2drug, voc["med_voc"])
    _validate_binary_symmetric_matrix(ddi_A, medications, "ddi_A_final", require_zero_diagonal=True)
    _validate_binary_symmetric_matrix(
        ehr_adj, medications, "ehr_adj_final", require_zero_diagonal=True
    )
    _validate_ddi_mask(ddi_mask, medications, molecular_substructures)
    statistics_evidence = _validate_records_statistics(records, counts["visits"])

    bridge_checks = {
        "vocabulary_bijections": "passed",
        "records_structure": "passed",
        "idx2drug_contract": "passed",
        "ddi_matrix_properties": "passed",
        "ehr_matrix_properties": "passed",
        "ddi_mask_properties": "passed",
        "records_statistics": "passed",
    }

    input_results = {name: "passed" for name in CANONICAL_SIX_INPUTS}
    return input_results, counts, bridge_checks, statistics_evidence, REPORTED_PAPER_METADATA
