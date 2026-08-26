from __future__ import annotations

import pickle
from pathlib import Path

import pytest

from medrec_research.errors import ProtocolValidationError
from medrec_research.molerec_snapshot import (
    SNAPSHOT_FILES,
    build_molerec_snapshot,
    publish_molerec_snapshot,
    validate_molerec_snapshot,
)


def _valid_inputs() -> tuple[object, dict[str, object], list[list[int]], list[list[int]]]:
    from tests.unit.test_molerec_program import valid_records_and_vocab

    return valid_records_and_vocab()


def _write(path: Path, value: object) -> None:
    with path.open("wb") as stream:
        pickle.dump(value, stream)


def _source_directories(tmp_path: Path) -> tuple[Path, Path]:
    common = tmp_path / "common"
    molecular = tmp_path / "molecular"
    common.mkdir()
    molecular.mkdir()
    records, vocabulary, ddi, ddi_mask = _valid_inputs()
    _write(common / "records_final.pkl", records)
    _write(common / "voc_final.pkl", vocabulary)
    _write(common / "ddi_A_final.pkl", ddi)
    _write(common / "ehr_adj_final.pkl", [[0] * 131 for _ in range(131)])
    _write(molecular / "ddi_mask_H.pkl", ddi_mask)
    _write(molecular / "substructure_smiles.pkl", [f"S{index}" for index in range(491)])
    _write(
        molecular / "idx2SMILES.pkl",
        {f"M{index}": f"smiles-{index}" for index in range(131)},
    )
    return common, molecular


def test_builder_publishes_exact_paired_eight_file_snapshot(tmp_path: Path) -> None:
    common, molecular = _source_directories(tmp_path)
    staging = tmp_path / "staging"
    published = tmp_path / "snapshots" / "molerec-table1-c721-www23"
    proof_path = tmp_path / "proof.json"

    proof = build_molerec_snapshot(
        common_snapshot=common,
        molerec_data_directory=molecular,
        staging_directory=staging,
    )
    published_proof = publish_molerec_snapshot(
        staging_directory=staging,
        snapshot_directory=published,
        proof_path=proof_path,
    )

    assert proof == published_proof
    assert tuple(sorted(path.name for path in published.iterdir())) == tuple(sorted(SNAPSHOT_FILES))
    assert proof["counts"] == {
        "patients": 6350,
        "visits": 15032,
        "medications": 131,
        "molecular_substructures": 491,
        "ddi_pairs": 448,
    }
    assert proof["paper_reported_visits"] == 14_995
    assert proof_path.is_file()
    assert (published / "idx2SMILES.pkl").read_bytes() == (published / "idx2drug.pkl").read_bytes()


def test_validator_rejects_broken_compatibility_alias(tmp_path: Path) -> None:
    common, molecular = _source_directories(tmp_path)
    snapshot = tmp_path / "snapshot"
    build_molerec_snapshot(
        common_snapshot=common,
        molerec_data_directory=molecular,
        staging_directory=snapshot,
    )
    (snapshot / "idx2drug.pkl").write_bytes(b"not-the-paired-asset")

    with pytest.raises(ProtocolValidationError, match="byte-identical"):
        validate_molerec_snapshot(snapshot)


def test_builder_requires_canonical_molerec_asset_names(tmp_path: Path) -> None:
    common, molecular = _source_directories(tmp_path)
    (molecular / "substructure_smiles.pkl").rename(molecular / "sub_structure.pkl")

    with pytest.raises(ProtocolValidationError, match=r"substructure_smiles\.pkl"):
        build_molerec_snapshot(
            common_snapshot=common,
            molerec_data_directory=molecular,
            staging_directory=tmp_path / "staging",
        )
