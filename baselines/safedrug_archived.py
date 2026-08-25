#!/usr/bin/env python3
"""Run one pinned SafeDrug archived Baseline Program lane on 319."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc  # noqa: UP017 -- archived environments may use Python 3.8.

ARCHIVED_REVISION = "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"
TEST_DECLARATION = (
    "parser.add_argument('--Test', action='store_true', default=True, help=\"test mode\")"
)
TRAIN_DECLARATION = TEST_DECLARATION.replace("default=True", "default=False")
EPOCH_FORMAL = "    EPOCH = 50\n"
EPOCH_SMOKE = "    EPOCH = 1\n"

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
ROUND_PATTERN = re.compile(
    r"DDI Rate:\s*([0-9.]+),\s*Jaccard:\s*([0-9.]+),\s*PRAUC:\s*([0-9.]+),\s*"
    r"AVG_PRC:\s*([0-9.]+),\s*AVG_RECALL:\s*([0-9.]+),\s*AVG_F1:\s*([0-9.]+),\s*"
    r"AVG_MED:\s*([0-9.]+)"
)

CANONICAL_SIX_INPUTS = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
    "ddi_mask_H.pkl",
    "ehr_adj_final.pkl",
    "idx2drug.pkl",
)
REGISTRY_IMPORT_MODULES = (
    "torch",
    "dnc",
    "rdkit",
    "pandas",
    "dill",
    "sklearn",
    "models",
    "util",
)


class ReproductionError(RuntimeError):
    """Raised when an archived reproduction contract is not satisfied."""


@dataclass(frozen=True)
class Profile:
    baseline_id: str
    entrypoint: str
    model_name: str
    learning_rate: float
    required_inputs: tuple[str, ...]
    checkpoint_pattern: re.Pattern[str]
    test_uses_basename: bool = False


COMMON_INPUTS = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
)
GATE_INPUTS = (*COMMON_INPUTS, "ddi_mask_H.pkl")
PROFILES = {
    "gamenet": Profile(
        "gamenet",
        "GAMENet.py",
        "GAMENet",
        1e-4,
        (*COMMON_INPUTS, "ehr_adj_final.pkl"),
        re.compile(r"^Epoch_(\d+)_JA_.*_DDI_.*\.model$"),
    ),
    "safedrug": Profile(
        "safedrug",
        "SafeDrug.py",
        "SafeDrug",
        5e-4,
        (
            *COMMON_INPUTS,
            "ehr_adj_final.pkl",
            "ddi_mask_H.pkl",
            "idx2drug.pkl",
        ),
        re.compile(r"^Epoch_(\d+)_TARGET_.*_JA_.*_DDI_.*\.model$"),
    ),
    "retain": Profile(
        "retain",
        "Retain.py",
        "Retain",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_JA_.*_DDI_.*\.model$"),
        test_uses_basename=True,
    ),
    "leap-safedrug": Profile(
        "leap-safedrug",
        "Leap.py",
        "Leap",
        5e-4,
        COMMON_INPUTS,
        re.compile(r"^Epoch_(\d+)_JA_.*_DDI_.*\.model$"),
    ),
}


def profile_for(baseline_id: str) -> Profile:
    try:
        return PROFILES[baseline_id]
    except KeyError as error:
        raise ReproductionError(f"unknown archived baseline '{baseline_id}'") from error


def adapt_training_source(source: str) -> str:
    """Select archived training mode through the only necessary source change."""
    if source.count(TEST_DECLARATION) != 1 or TRAIN_DECLARATION in source:
        raise ReproductionError("archived --Test declaration drifted from audited source")
    adapted = source.replace(TEST_DECLARATION, TRAIN_DECLARATION)
    if adapted.replace(TRAIN_DECLARATION, TEST_DECLARATION) != source:
        raise ReproductionError("training-mode adaptation changed unexpected source bytes")
    return adapted


def adapt_epoch_source(source: str) -> str:
    """Select one training epoch for non-evidence smoke testing."""
    if source.count(EPOCH_FORMAL) != 1 or EPOCH_SMOKE in source:
        raise ReproductionError("archived EPOCH declaration drifted from audited source")
    adapted = source.replace(EPOCH_FORMAL, EPOCH_SMOKE, 1)
    if adapted.replace(EPOCH_SMOKE, EPOCH_FORMAL, 1) != source:
        raise ReproductionError("epoch adaptation changed unexpected source bytes")
    return adapted


def adapt_smoke_source(source: str) -> str:
    """Compose training-mode and 1-epoch adaptations with joint reversibility."""
    train_adapted = adapt_training_source(source)
    smoke_adapted = adapt_epoch_source(train_adapted)
    reversed_source = smoke_adapted.replace(EPOCH_SMOKE, EPOCH_FORMAL, 1).replace(
        TRAIN_DECLARATION, TEST_DECLARATION
    )
    if reversed_source != source:
        raise ReproductionError("smoke adaptation composition is not reversible to original bytes")
    return smoke_adapted


def test_mode_default(source: str) -> bool:
    declarations = {
        TEST_DECLARATION: True,
        TRAIN_DECLARATION: False,
    }
    matches = [value for declaration, value in declarations.items() if declaration in source]
    if len(matches) != 1:
        raise ReproductionError("unable to determine archived --Test default")
    return matches[0]


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


def matrix_shape(value: Any) -> tuple[int, int]:
    shape = getattr(value, "shape", None)
    if shape is not None and len(shape) == 2:
        return int(shape[0]), int(shape[1])
    rows = len(value)
    columns = len(value[0]) if rows else 0
    if any(len(row) != columns for row in value):
        raise ReproductionError("matrix rows have inconsistent lengths")
    return rows, columns


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


def parse_training_log(log_text: str, expected_epochs: int = 50) -> int:
    observed = [int(value) for value in re.findall(r"(?:^|\n)epoch\s+(\d+)\s*-+", log_text)]
    if observed != list(range(1, expected_epochs + 1)):
        raise ReproductionError(
            f"training log must contain exactly epochs 1-{expected_epochs}, observed {observed}"
        )
    best_epochs = [int(value) for value in re.findall(r"best_epoch:\s*(\d+)", log_text)]
    if len(best_epochs) != expected_epochs or not 0 <= best_epochs[-1] < expected_epochs:
        raise ReproductionError("training log has invalid best_epoch evidence")
    return best_epochs[-1]


def select_checkpoint(checkpoint_dir: Path, profile: Profile, best_epoch: int) -> Path:
    matches = [
        path
        for path in checkpoint_dir.iterdir()
        if path.is_file()
        and not path.is_symlink()
        and (match := profile.checkpoint_pattern.fullmatch(path.name))
        and int(match.group(1)) == best_epoch
    ]
    if len(matches) != 1:
        raise ReproductionError(
            f"expected one {profile.baseline_id} checkpoint for epoch {best_epoch}, "
            f"observed {[path.name for path in matches]}"
        )
    return matches[0]


def training_command(python: str, adapted_entrypoint: Path, model_name: str) -> list[str]:
    return [python, str(adapted_entrypoint), "--model_name", model_name]


def test_command(
    python: str,
    original_entrypoint: Path,
    profile: Profile,
    model_name: str,
    checkpoint: Path,
) -> list[str]:
    resume_path = checkpoint.name if profile.test_uses_basename else str(checkpoint.resolve())
    return [
        python,
        str(original_entrypoint),
        "--model_name",
        model_name,
        "--Test",
        "--resume_path",
        resume_path,
    ]


def parse_test_log(log_text: str) -> dict[str, Any]:
    rounds = []
    for match in ROUND_PATTERN.finditer(log_text):
        values = [float(value) for value in match.groups()]
        if not all(math.isfinite(value) for value in values):
            raise ReproductionError("test log contains a non-finite metric")
        rounds.append(
            {
                "ddi_rate": values[0],
                "jaccard": values[1],
                "prauc": values[2],
                "avg_precision": values[3],
                "avg_recall": values[4],
                "avg_f1": values[5],
                "avg_medications": values[6],
            }
        )
    if len(rounds) != 10:
        raise ReproductionError(f"expected exactly 10 test rounds, observed {len(rounds)}")
    summary_pairs = re.findall(r"([0-9.]+)\s*\$\\pm\$\s*([0-9.]+)\s*&", log_text)
    if len(summary_pairs) != 5:
        raise ReproductionError(
            f"expected one upstream 5-metric summary, observed {len(summary_pairs)} pairs"
        )
    summary = {}
    for name in ("ddi_rate", "jaccard", "avg_f1", "prauc", "avg_medications"):
        values = [round_data[name] for round_data in rounds]
        mean = sum(values) / len(values)
        summary[name] = {
            "mean": mean,
            "std": math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)),
        }
    summary_names = ("ddi_rate", "jaccard", "avg_f1", "prauc", "avg_medications")
    upstream_summary = {
        summary_names[index]: {"mean": float(mean), "std": float(std)}
        for index, (mean, std) in enumerate(summary_pairs)
    }
    for name, upstream_value in upstream_summary.items():
        harness_value = summary[name]
        maximum_round_value = max(abs(round_data[name]) for round_data in rounds)
        round_precision = (
            5e-5
            if maximum_round_value == 0
            else 0.5 * 10 ** (math.floor(math.log10(maximum_round_value)) - 3)
        )
        tolerance = round_precision + 5e-5 + 1e-12
        if (
            abs(upstream_value["mean"] - harness_value["mean"]) > tolerance
            or abs(upstream_value["std"] - harness_value["std"]) > tolerance
        ):
            raise ReproductionError(f"upstream summary disagrees with parsed rounds for {name}")
    return {
        "test_rounds": rounds,
        "harness_summary": summary,
        "upstream_summary": upstream_summary,
    }


def load_archived_values(data_dir: Path) -> tuple[Any, Any, Any, Any]:
    dill = importlib.import_module("dill")
    values = []
    for name in GATE_INPUTS:
        with (data_dir / name).open("rb") as stream:
            values.append(dill.load(stream))
    return tuple(values)  # type: ignore[return-value]


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
) -> tuple[dict[str, str], dict[str, int], dict[str, str]]:
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


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def environment_summary() -> dict[str, str]:
    try:
        explicit = subprocess.run(
            ["conda", "list", "--explicit"],
            capture_output=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReproductionError("unable to record active Conda environment") from error
    return {
        "conda_explicit_sha256": hashlib.sha256(explicit).hexdigest(),
        "python": sys.version.split()[0],
    }


def _nvidia_driver_version() -> str:
    proc_path = Path("/proc/driver/nvidia/version")
    if proc_path.is_file():
        try:
            content = proc_path.read_text(encoding="utf-8")
            match = re.search(r"NVRM version:\s*([^\s]+)", content)
            if match:
                return match.group(1)
        except OSError:
            pass
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip().splitlines()[0]
    except OSError:
        pass
    return "unknown"


def _package_version(module_name: str) -> str:
    try:
        mod = importlib.import_module(module_name)
        ver = getattr(mod, "__version__", None)
        if ver is not None:
            return str(ver)
    except Exception:
        pass
    try:
        metadata_mod = importlib.import_module("importlib.metadata")
        return metadata_mod.version(module_name)
    except Exception:
        pass
    return "unknown"


def probe_environment_details() -> dict[str, Any]:
    summary = environment_summary()
    torch_mod = sys.modules.get("torch") or importlib.import_module("torch")

    torch_cuda = getattr(getattr(torch_mod, "version", None), "cuda", None) or "unknown"
    cuda_count = torch_mod.cuda.device_count() if torch_mod.cuda.is_available() else 0
    gpu_name = torch_mod.cuda.get_device_name(0) if cuda_count > 0 else "unknown"
    if cuda_count > 0:
        cap = torch_mod.cuda.get_device_capability(0)
        gpu_cap = f"{cap[0]}.{cap[1]}"
    else:
        gpu_cap = "unknown"

    return {
        "conda_explicit_sha256": summary["conda_explicit_sha256"],
        "python": summary["python"],
        "pytorch": getattr(torch_mod, "__version__", "unknown"),
        "torch_cuda": str(torch_cuda),
        "nvidia_driver": _nvidia_driver_version(),
        "numpy": _package_version("numpy"),
        "pandas": _package_version("pandas"),
        "scipy": _package_version("scipy"),
        "scikit_learn": _package_version("sklearn"),
        "rdkit": _package_version("rdkit"),
        "dill": _package_version("dill"),
        "dnc": _package_version("dnc"),
        "cuda_visible_device_count": cuda_count,
        "gpu_name": gpu_name,
        "gpu_capability": gpu_cap,
    }


def check_cuda_tensor() -> str:
    try:
        torch_mod = sys.modules.get("torch") or importlib.import_module("torch")
        if not torch_mod.cuda.is_available():
            raise ReproductionError("CUDA is not available")
        if torch_mod.cuda.device_count() != 1:
            raise ReproductionError(
                f"expected exactly 1 visible CUDA device, observed {torch_mod.cuda.device_count()}"
            )
        tensor_sum = (torch_mod.ones(1, device="cuda") + 1.0).sum().item()
        if tensor_sum != 2.0:
            raise ReproductionError(
                f"CUDA tensor calculation error: expected 2.0, observed {tensor_sum}"
            )
        return "passed"
    except Exception as error:
        raise ReproductionError(f"CUDA tensor check failed: {error}") from error


def check_rdkit_brics() -> str:
    try:
        chem_mod = importlib.import_module("rdkit.Chem")
        brics_mod = importlib.import_module("rdkit.Chem.BRICS")
        mol = chem_mod.MolFromSmiles("CC(=O)OC1=CC=CC=C1C(=O)O")
        if mol is None:
            raise ReproductionError("RDKit failed to parse test SMILES")
        frags = list(brics_mod.BRICSDecompose(mol))
        if not frags:
            raise ReproductionError("RDKit BRICSDecompose returned empty fragments")
        return "passed"
    except Exception as error:
        raise ReproductionError(f"RDKit BRICS check failed: {error}") from error


def check_dnc_forward() -> str:
    try:
        dnc_mod = importlib.import_module("dnc")
        dnc_cls = dnc_mod.DNC
        torch_mod = sys.modules.get("torch") or importlib.import_module("torch")
        use_cuda = torch_mod.cuda.is_available()
        gpu_id = 0 if use_cuda else -1
        rnn = dnc_cls(
            input_size=10,
            hidden_size=20,
            rnn_type="lstm",
            num_layers=1,
            num_hidden_layers=1,
            nr_cells=5,
            cell_size=10,
            read_heads=2,
            batch_first=True,
            gpu_id=gpu_id,
        )
        x = torch_mod.randn(1, 4, 10)
        if use_cuda:
            x = x.cuda()
        out, _ = rnn(x)
        if out is None or out.shape[0] != 1:
            raise ReproductionError("dnc forward produced invalid output shape")
        return "passed"
    except Exception as error:
        raise ReproductionError(f"dnc forward check failed: {error}") from error


def check_imports(upstream_root: Path) -> dict[str, str]:
    src_dir = str(upstream_root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    results = {}
    for module_name in REGISTRY_IMPORT_MODULES:
        try:
            importlib.import_module(module_name)
            results[module_name] = "passed"
        except Exception as error:
            raise ReproductionError(f"failed to import '{module_name}': {error}") from error
    return results


def verify_upstream_source(upstream_root: Path) -> None:
    try:
        observed_revision = subprocess.run(
            ["git", "-C", str(upstream_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReproductionError("unable to verify archived upstream source") from error
    if observed_revision != ARCHIVED_REVISION:
        raise ReproductionError(f"upstream source must be archived@{ARCHIVED_REVISION}")
    try:
        tracked_changes = subprocess.run(
            [
                "git",
                "-C",
                str(upstream_root),
                "status",
                "--porcelain",
                "--untracked-files=no",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ReproductionError("unable to verify archived upstream cleanliness") from error
    if tracked_changes:
        raise ReproductionError("archived upstream source has tracked modifications")


def run_probe(
    *,
    baseline_id: str,
    upstream_root: Path,
    data_dir: Path | None,
    scope: str,
) -> dict[str, Any]:
    if scope not in ("environment", "full"):
        raise ReproductionError(f"unknown probe scope '{scope}'")
    profile_for(baseline_id)
    verify_upstream_source(upstream_root)

    import_checks = check_imports(upstream_root)
    cuda_status = check_cuda_tensor()
    rdkit_status = check_rdkit_brics()
    dnc_status = check_dnc_forward()
    env_details = probe_environment_details()

    if env_details["cuda_visible_device_count"] != 1:
        raise ReproductionError("probe requires exactly 1 visible CUDA device")

    inputs_result: dict[str, str] | None = None
    dataset_counts: dict[str, int] | None = None
    bridge_checks: dict[str, str] | None = None
    statistics_evidence: dict[str, Any] | None = None
    metadata_disclosure: dict[str, int] | None = None

    if scope == "full":
        if data_dir is None:
            raise ReproductionError("full probe scope requires --dataset-root")
        (
            inputs_result,
            dataset_counts,
            bridge_checks,
            statistics_evidence,
            metadata_disclosure,
        ) = load_and_validate_canonical_inputs(data_dir)

    return {
        "schema_version": 1,
        "kind": "safedrug_archived_probe",
        "scope": scope,
        "baseline_id": baseline_id,
        "source_revision": ARCHIVED_REVISION,
        "environment": env_details,
        "checks": {
            "imports": import_checks,
            "cuda_tensor": cuda_status,
            "rdkit_brics": rdkit_status,
            "dnc_forward": dnc_status,
        },
        "inputs": inputs_result,
        "dataset_counts": dataset_counts,
        "bridge_checks": bridge_checks,
        "statistics": statistics_evidence,
        "metadata": metadata_disclosure or REPORTED_PAPER_METADATA,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def finalize_result(run_root: Path, status: dict[str, Any], result: dict[str, Any]) -> None:
    """Publish terminal status before embedding it in result.json."""
    write_json(run_root / "status.json", status)
    write_json(run_root / "result.json", {**result, "status": status})


def run_logged(command: list[str], *, cwd: Path, env: dict[str, str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if completed.returncode != 0:
        raise ReproductionError(
            f"command failed with exit code {completed.returncode}: {command[1]}"
        )


def run_smoke_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
) -> None:
    if run_root.exists():
        raise ReproductionError(f"run root already exists: {run_root}")
    if (
        upstream_root == data_dir
        or upstream_root in data_dir.parents
        or data_dir in upstream_root.parents
    ):
        raise ReproductionError("dataset root must be outside archived upstream source")
    if (
        upstream_root == run_root
        or upstream_root in run_root.parents
        or run_root in upstream_root.parents
    ):
        raise ReproductionError("run root must be outside archived upstream source")

    verify_upstream_source(upstream_root)

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"archived dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("archived dataset inputs must be regular files, not symlinks")

    _, counts, _, _, _ = load_and_validate_canonical_inputs(data_dir)
    environment_identity = environment_summary()

    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")
    adapted_source = adapt_smoke_source(original_source)

    run_root.mkdir(parents=True)
    work_src = run_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    adapted_entrypoint = work_src / profile.entrypoint
    adapted_entrypoint.write_text(adapted_source, encoding="utf-8")
    data_link = work_src.parent / "data"
    data_link.symlink_to(data_dir, target_is_directory=True)

    model_name = f"{profile.model_name}_{run_root.name}"
    checkpoint_dir = work_src / "saved" / model_name
    checkpoint_dir.mkdir(parents=True)
    started_at = datetime.now(UTC).isoformat()

    adaptation = {
        "archived_revision": ARCHIVED_REVISION,
        "entrypoint": profile.entrypoint,
        "original_sha256": sha256(original_entrypoint),
        "adapted_sha256": sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "training_default": {
            "from": TEST_DECLARATION,
            "to": TRAIN_DECLARATION,
            "occurrences": 1,
            "reverse_verification": "byte-identical",
        },
        "epoch_limit": {
            "from": EPOCH_FORMAL,
            "to": EPOCH_SMOKE,
            "occurrences": 1,
            "reverse_verification": "byte-identical",
        },
    }
    write_json(run_root / "adaptation.json", adaptation)
    write_json(
        run_root / "status.json",
        {
            "schema_version": 1,
            "kind": "safedrug_archived_smoke_status",
            "state": "running",
            "stage": "training",
            "started_at": started_at,
            "finished_at": None,
            "failure_code": None,
        },
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    try:
        run_logged(
            training_command(python, adapted_entrypoint, model_name),
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        best_epoch = parse_training_log(
            (run_root / "train.log").read_text(errors="replace"), expected_epochs=1
        )
        if best_epoch != 0:
            raise ReproductionError(f"smoke mode requires best_epoch 0, observed {best_epoch}")
        checkpoint = select_checkpoint(checkpoint_dir, profile, best_epoch=0)
        finished_at = datetime.now(UTC).isoformat()
        terminal_status = {
            "schema_version": 1,
            "kind": "safedrug_archived_smoke_status",
            "state": "completed",
            "stage": "terminal",
            "started_at": started_at,
            "finished_at": finished_at,
            "failure_code": None,
        }
        write_json(run_root / "status.json", terminal_status)
        smoke_record = {
            "schema_version": 1,
            "kind": "safedrug_archived_smoke",
            "non_evidence": True,
            "baseline_id": profile.baseline_id,
            "source_revision": ARCHIVED_REVISION,
            "environment_sha256": environment_identity["conda_explicit_sha256"],
            "dataset_counts": counts,
            "epochs_requested": 1,
            "epochs_observed": 1,
            "best_epoch": 0,
            "adaptation": {
                "reverse_verification": "byte-identical",
                "training_default": adaptation["training_default"],
                "epoch_limit": adaptation["epoch_limit"],
            },
            "checkpoint": {
                "best_epoch": 0,
                "sha256": sha256(checkpoint),
                "size_bytes": checkpoint.stat().st_size,
            },
            "status": terminal_status,
        }
        write_json(run_root / "smoke.json", smoke_record)
    except Exception:
        write_json(
            run_root / "status.json",
            {
                "schema_version": 1,
                "kind": "safedrug_archived_smoke_status",
                "state": "failed",
                "stage": "terminal",
                "started_at": started_at,
                "finished_at": datetime.now(UTC).isoformat(),
                "failure_code": "smoke_failed",
            },
        )
        raise


def run_formal_lane(
    *,
    profile: Profile,
    upstream_root: Path,
    data_dir: Path,
    run_root: Path,
    python: str,
) -> None:
    if run_root.exists():
        raise ReproductionError(f"run root already exists: {run_root}")
    if (
        upstream_root == data_dir
        or upstream_root in data_dir.parents
        or data_dir in upstream_root.parents
    ):
        raise ReproductionError("dataset root must be outside archived upstream source")
    if (
        upstream_root == run_root
        or upstream_root in run_root.parents
        or run_root in upstream_root.parents
    ):
        raise ReproductionError("run root must be outside archived upstream source")
    verify_upstream_source(upstream_root)

    required_inputs = tuple(dict.fromkeys((*profile.required_inputs, *GATE_INPUTS)))
    missing = [name for name in required_inputs if not (data_dir / name).is_file()]
    if missing:
        raise ReproductionError(f"archived dataset is missing required inputs: {missing}")
    if any((data_dir / name).is_symlink() for name in required_inputs):
        raise ReproductionError("archived dataset inputs must be regular files, not symlinks")
    _, counts, _, _, _ = load_and_validate_canonical_inputs(data_dir)
    environment_identity = environment_summary()

    source_dir = upstream_root / "src"
    original_entrypoint = source_dir / profile.entrypoint
    original_source = original_entrypoint.read_text(encoding="utf-8")
    adapted_source = adapt_training_source(original_source)

    run_root.mkdir(parents=True)
    work_src = run_root / "work" / "src"
    work_src.mkdir(parents=True, exist_ok=False)
    adapted_entrypoint = work_src / profile.entrypoint
    adapted_entrypoint.write_text(adapted_source, encoding="utf-8")
    data_link = work_src.parent / "data"
    data_link.symlink_to(data_dir, target_is_directory=True)

    model_name = f"{profile.model_name}_{run_root.name}"
    checkpoint_dir = work_src / "saved" / model_name
    checkpoint_dir.mkdir(parents=True)
    started_at = datetime.now(UTC).isoformat()
    adaptation = {
        "archived_revision": ARCHIVED_REVISION,
        "entrypoint": profile.entrypoint,
        "original_sha256": sha256(original_entrypoint),
        "adapted_sha256": sha256(adapted_entrypoint),
        "reverse_verification": "byte-identical",
        "change": {"from": TEST_DECLARATION, "to": TRAIN_DECLARATION},
    }
    write_json(run_root / "adaptation.json", adaptation)
    status: dict[str, Any] = {
        "schema_version": 1,
        "kind": "safedrug_archived_formal_status",
        "baseline_id": profile.baseline_id,
        "state": "running",
        "stage": "training",
        "started_at": started_at,
        "finished_at": None,
        "failure_code": None,
    }
    write_json(run_root / "status.json", status)

    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_dir), environment.get("PYTHONPATH", "")))
    )
    try:
        run_logged(
            training_command(python, adapted_entrypoint, model_name),
            cwd=work_src,
            env=environment,
            log_path=run_root / "train.log",
        )
        best_epoch = parse_training_log((run_root / "train.log").read_text(errors="replace"))
        checkpoint = select_checkpoint(checkpoint_dir, profile, best_epoch)
        status["stage"] = "testing"
        write_json(run_root / "status.json", status)
        run_logged(
            test_command(python, original_entrypoint, profile, model_name, checkpoint),
            cwd=work_src,
            env=environment,
            log_path=run_root / "test.log",
        )
        test_data = parse_test_log((run_root / "test.log").read_text(errors="replace"))
        terminal_status = {
            "schema_version": 1,
            "kind": "safedrug_archived_formal_status",
            "baseline_id": profile.baseline_id,
            "state": "completed",
            "stage": "terminal",
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
            "failure_code": None,
        }
        finalize_result(
            run_root,
            terminal_status,
            {
                "schema_version": 1,
                "baseline_id": profile.baseline_id,
                "source_revision": ARCHIVED_REVISION,
                "archived_learning_rate": profile.learning_rate,
                "dataset_counts": counts,
                "environment": environment_identity,
                "adaptation": adaptation,
                "checkpoint": {
                    "best_epoch": best_epoch,
                    "sha256": sha256(checkpoint),
                    "size_bytes": checkpoint.stat().st_size,
                },
                **test_data,
            },
        )
    except Exception:
        write_json(
            run_root / "status.json",
            {
                "schema_version": 1,
                "kind": "safedrug_archived_formal_status",
                "baseline_id": profile.baseline_id,
                "state": "failed",
                "stage": "terminal",
                "started_at": started_at,
                "finished_at": datetime.now(UTC).isoformat(),
                "failure_code": "formal_failed",
            },
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_id", choices=tuple(PROFILES))
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--mode",
        choices=("formal", "smoke", "probe"),
        default="formal",
        help="Reproduction execution mode (default: formal)",
    )
    parser.add_argument(
        "--probe-scope",
        choices=("environment", "full"),
        default="full",
        help="Probe scope when --mode probe (default: full)",
    )
    args = parser.parse_args()

    if args.mode != "probe" and "--probe-scope" in sys.argv:
        parser.error("--probe-scope is only supported when --mode probe")

    if args.mode == "probe":
        probe_result = run_probe(
            baseline_id=args.baseline_id,
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve() if args.dataset_root else None,
            scope=args.probe_scope,
        )
        print(json.dumps(probe_result, indent=None, separators=(",", ":")))
        return

    if args.dataset_root is None:
        parser.error("--dataset-root is required for smoke and formal modes")
    if args.run_root is None:
        parser.error("--run-root is required for smoke and formal modes")

    if args.mode == "smoke":
        run_smoke_lane(
            profile=profile_for(args.baseline_id),
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve(),
            run_root=args.run_root.resolve(),
            python=args.python,
        )
    else:
        run_formal_lane(
            profile=profile_for(args.baseline_id),
            upstream_root=args.upstream_root.resolve(),
            data_dir=args.dataset_root.resolve(),
            run_root=args.run_root.resolve(),
            python=args.python,
        )


if __name__ == "__main__":
    main()
