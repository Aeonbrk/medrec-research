"""Build and validate the additive eight-file MoleRec Table 1 snapshot."""

from __future__ import annotations

import importlib
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .._validation import write_json_atomic
from ..errors import ProtocolValidationError

SNAPSHOT_ID = "snapshots/molerec-table1-c721-www23"
SNAPSHOT_FILES = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
    "ehr_adj_final.pkl",
    "ddi_mask_H.pkl",
    "substructure_smiles.pkl",
    "idx2SMILES.pkl",
    "idx2drug.pkl",
)
COMMON_FILES = SNAPSHOT_FILES[:4]
MOLECULAR_FILES = SNAPSHOT_FILES[4:7]
EXPECTED_DATASET_COUNTS = {
    "patients": 6_350,
    "visits": 15_032,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}


def _pickle_module() -> Any:
    try:
        return importlib.import_module("dill")
    except ImportError:
        return importlib.import_module("pickle")


def _load(path: Path) -> Any:
    with path.open("rb") as stream:
        return _pickle_module().load(stream)


def _require_regular_file(path: Path, *, context: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise ProtocolValidationError(f"{context} must be a regular file: {path}")


def _matrix_shape(value: Any, *, name: str) -> tuple[int, int]:
    shape = getattr(value, "shape", None)
    if shape is not None and len(shape) == 2:
        return int(shape[0]), int(shape[1])
    if not isinstance(value, (list, tuple)) or not value:
        raise ProtocolValidationError(f"{name} must be a non-empty 2D matrix")
    width = len(value[0]) if isinstance(value[0], (list, tuple)) else 0
    if width == 0 or any(not isinstance(row, (list, tuple)) or len(row) != width for row in value):
        raise ProtocolValidationError(f"{name} must have rectangular rows")
    return len(value), width


def _validate_symmetric_matrix(value: Any, *, name: str, size: int) -> int:
    if _matrix_shape(value, name=name) != (size, size):
        raise ProtocolValidationError(f"{name} must be {size} x {size}")
    pairs = 0
    for row in range(size):
        if value[row][row] != 0:
            raise ProtocolValidationError(f"{name} must have a zero diagonal")
        for column in range(row + 1, size):
            if value[row][column] != value[column][row]:
                raise ProtocolValidationError(f"{name} must be symmetric")
            if value[row][column] not in (0, 1, 0.0, 1.0):
                raise ProtocolValidationError(f"{name} must be binary")
            pairs += int(value[row][column] == 1)
    return pairs


def _ordered_medications(vocabulary: Mapping[str, Any]) -> list[Any]:
    med_voc = vocabulary.get("med_voc")
    idx2word = getattr(med_voc, "idx2word", None)
    if isinstance(idx2word, (list, tuple)):
        return list(idx2word)
    if isinstance(idx2word, Mapping):
        try:
            return [idx2word[index] for index in range(len(idx2word))]
        except KeyError as error:
            raise ProtocolValidationError("med_voc.idx2word keys must be contiguous") from error
    raise ProtocolValidationError("voc_final.med_voc.idx2word must be a sequence or mapping")


def _validate_molecular_assets(
    *,
    vocabulary: Mapping[str, Any],
    ddi_mask: Any,
    substructures: Any,
    idx2smiles: Any,
) -> dict[str, int]:
    medications = _ordered_medications(vocabulary)
    if len(medications) != 131:
        raise ProtocolValidationError("med_voc must contain 131 ordered medications")
    rows, columns = _matrix_shape(ddi_mask, name="ddi_mask_H")
    if rows != len(medications) or columns != 491:
        raise ProtocolValidationError("ddi_mask_H must align to 131 medications x 491 columns")
    for row in range(rows):
        for value in ddi_mask[row]:
            if value not in (0, 1, 0.0, 1.0):
                raise ProtocolValidationError("ddi_mask_H must be binary")

    if not isinstance(substructures, (Mapping, Sequence)) or isinstance(
        substructures, (str, bytes)
    ):
        raise ProtocolValidationError("substructure_smiles.pkl must be a collection")
    if len(substructures) != columns:
        raise ProtocolValidationError("substructure_smiles.pkl must align to ddi_mask_H columns")

    if isinstance(idx2smiles, Mapping):
        missing = [medication for medication in medications if medication not in idx2smiles]
        if missing:
            raise ProtocolValidationError("idx2SMILES.pkl is missing medication vocabulary entries")
        if any(not idx2smiles[medication] for medication in medications):
            raise ProtocolValidationError("idx2SMILES.pkl has empty medication entries")
    elif isinstance(idx2smiles, Sequence) and not isinstance(idx2smiles, (str, bytes)):
        if len(idx2smiles) != len(medications):
            raise ProtocolValidationError("idx2SMILES.pkl must align to medication vocabulary")
        if any(not value for value in idx2smiles):
            raise ProtocolValidationError("idx2SMILES.pkl has empty medication entries")
    else:
        raise ProtocolValidationError("idx2SMILES.pkl must be a mapping or sequence")

    return {"medications": len(medications), "molecular_substructures": columns}


def _validate_common_dataset(
    *,
    records: Any,
    vocabulary: Mapping[str, Any],
    ddi_pairs: int,
    molecular_substructures: int,
) -> dict[str, int]:
    if not isinstance(records, list) or not records:
        raise ProtocolValidationError("records_final.pkl must contain a non-empty patient list")
    visits = 0
    for patient_index, patient in enumerate(records):
        if not isinstance(patient, list) or not patient:
            raise ProtocolValidationError(
                f"records_final.pkl patient {patient_index} must contain admissions"
            )
        visits += len(patient)
        for visit_index, visit in enumerate(patient):
            if not isinstance(visit, list) or len(visit) != 3:
                raise ProtocolValidationError(
                    f"records_final.pkl visit {patient_index}:{visit_index} must have three channels"
                )
            if any(not isinstance(channel, list) for channel in visit):
                raise ProtocolValidationError(
                    f"records_final.pkl visit {patient_index}:{visit_index} has a non-list channel"
                )

    medication_count = len(_ordered_medications(vocabulary))
    counts = {
        "patients": len(records),
        "visits": visits,
        "medications": medication_count,
        "ddi_pairs": ddi_pairs,
        "molecular_substructures": molecular_substructures,
    }
    if counts != EXPECTED_DATASET_COUNTS:
        raise ProtocolValidationError(
            "MoleRec snapshot common counts do not match the executable contract: "
            f"observed {counts}, expected {EXPECTED_DATASET_COUNTS}"
        )
    return counts


def validate_molerec_snapshot(snapshot_directory: Path) -> dict[str, Any]:
    """Validate exact files, paired assets, and common matrix invariants."""
    if not snapshot_directory.is_dir():
        raise ProtocolValidationError(f"MoleRec snapshot directory not found: {snapshot_directory}")
    observed = tuple(sorted(path.name for path in snapshot_directory.iterdir() if path.is_file()))
    expected = tuple(sorted(SNAPSHOT_FILES))
    if observed != expected:
        raise ProtocolValidationError(
            f"MoleRec snapshot must contain exactly the eight consumer files, observed {observed}"
        )
    for name in SNAPSHOT_FILES:
        _require_regular_file(snapshot_directory / name, context="MoleRec snapshot input")

    vocabulary = _load(snapshot_directory / "voc_final.pkl")
    if not isinstance(vocabulary, Mapping):
        raise ProtocolValidationError("voc_final.pkl must contain a mapping")
    records = _load(snapshot_directory / "records_final.pkl")
    medications = _ordered_medications(vocabulary)
    if len(medications) != EXPECTED_DATASET_COUNTS["medications"]:
        raise ProtocolValidationError("voc_final.pkl must contain 131 medications")
    ddi_pairs = _validate_symmetric_matrix(
        _load(snapshot_directory / "ddi_A_final.pkl"),
        name="ddi_A_final",
        size=len(medications),
    )
    _validate_symmetric_matrix(
        _load(snapshot_directory / "ehr_adj_final.pkl"),
        name="ehr_adj_final",
        size=len(medications),
    )
    molecular_counts = _validate_molecular_assets(
        vocabulary=vocabulary,
        ddi_mask=_load(snapshot_directory / "ddi_mask_H.pkl"),
        substructures=_load(snapshot_directory / "substructure_smiles.pkl"),
        idx2smiles=_load(snapshot_directory / "idx2SMILES.pkl"),
    )
    if (snapshot_directory / "idx2SMILES.pkl").read_bytes() != (
        snapshot_directory / "idx2drug.pkl"
    ).read_bytes():
        raise ProtocolValidationError("idx2drug.pkl must be byte-identical to idx2SMILES.pkl")

    counts = _validate_common_dataset(
        records=records,
        vocabulary=vocabulary,
        ddi_pairs=ddi_pairs,
        molecular_substructures=molecular_counts["molecular_substructures"],
    )

    return {
        "snapshot_id": SNAPSHOT_ID,
        "files": list(SNAPSHOT_FILES),
        "counts": counts,
        "paired_alias": "idx2drug.pkl == idx2SMILES.pkl",
        "paper_reported_visits": 14_995,
    }


def build_molerec_snapshot(
    *,
    common_snapshot: Path,
    molerec_data_directory: Path,
    staging_directory: Path,
) -> dict[str, Any]:
    """Copy the paired eight-file snapshot into a new, validated staging directory."""
    if staging_directory.exists():
        raise ProtocolValidationError(
            f"snapshot staging directory already exists: {staging_directory}"
        )
    for name in COMMON_FILES:
        _require_regular_file(common_snapshot / name, context="common snapshot input")
    for name in MOLECULAR_FILES:
        _require_regular_file(molerec_data_directory / name, context="MoleRec source input")

    staging_directory.mkdir(parents=True)
    for name in COMMON_FILES:
        shutil.copy2(common_snapshot / name, staging_directory / name)
    for name in MOLECULAR_FILES:
        shutil.copy2(molerec_data_directory / name, staging_directory / name)
    shutil.copy2(
        molerec_data_directory / "idx2SMILES.pkl",
        staging_directory / "idx2drug.pkl",
    )
    try:
        return validate_molerec_snapshot(staging_directory)
    except BaseException:
        shutil.rmtree(staging_directory, ignore_errors=True)
        raise


def publish_molerec_snapshot(
    *,
    staging_directory: Path,
    snapshot_directory: Path,
    proof_path: Path | None = None,
) -> dict[str, Any]:
    """Atomically publish a validated staging directory and optional proof outside it."""
    proof = validate_molerec_snapshot(staging_directory)
    if snapshot_directory.exists():
        raise ProtocolValidationError(f"published snapshot already exists: {snapshot_directory}")
    snapshot_directory.parent.mkdir(parents=True, exist_ok=True)
    staging_directory.replace(snapshot_directory)
    if proof_path is not None:
        write_json_atomic(proof_path, proof)
    return proof


__all__ = (
    "COMMON_FILES",
    "MOLECULAR_FILES",
    "SNAPSHOT_FILES",
    "SNAPSHOT_ID",
    "build_molerec_snapshot",
    "publish_molerec_snapshot",
    "validate_molerec_snapshot",
)
