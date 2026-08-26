from __future__ import annotations

import json
import pickle
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from medrec_research import ProtocolValidationError
from medrec_research.safedrug_c721 import (
    C721_SOURCE_REVISION,
    ORIGINAL_DDI_PATH,
    ORIGINAL_DIAGNOSES_PATH,
    ORIGINAL_PRESCRIPTIONS_PATH,
    ORIGINAL_PROCEDURES_PATH,
    REQUIRED_PREPROCESSING_ASSETS,
    adapt_c721_processing_script,
    stage_safedrug_c721,
    verify_preprocessing_checkout,
)

SAMPLE_PROCESSING_SCRIPT = f"""import pandas as pd
import dill
import numpy as np

# Process data
if __name__ == '__main__':
    {ORIGINAL_PRESCRIPTIONS_PATH}
    {ORIGINAL_DIAGNOSES_PATH}
    {ORIGINAL_PROCEDURES_PATH}
    med_structure_file = './idx2SMILES.pkl'
    ndc2atc_file = './ndc2atc_level4.csv'
    cid_atc = './drug-atc.csv'
    ndc_rxnorm_file = './ndc2rxnorm_mapping.txt'
    {ORIGINAL_DDI_PATH}

    dill.dump({{'diag_voc': None, 'med_voc': None, 'pro_voc': None}}, open('voc_final.pkl', 'wb'))
    dill.dump([], open('records_final.pkl', 'wb'))
    dill.dump([], open('ehr_adj_final.pkl', 'wb'))
    dill.dump([], open('ddi_A_final.pkl', 'wb'))
"""


def test_adapt_c721_processing_script_exact_substitutions() -> None:
    p_rx = Path("/path/to/rx.csv.gz")
    p_dx = Path("/path/to/dx.csv.gz")
    p_pr = Path("/path/to/pr.csv.gz")
    p_ddi = Path("/path/to/ddi.csv")

    adapted = adapt_c721_processing_script(
        SAMPLE_PROCESSING_SCRIPT,
        prescriptions_path=p_rx,
        diagnoses_path=p_dx,
        procedures_path=p_pr,
        ddi_path=p_ddi,
    )

    assert ORIGINAL_PRESCRIPTIONS_PATH not in adapted
    assert ORIGINAL_DIAGNOSES_PATH not in adapted
    assert ORIGINAL_PROCEDURES_PATH not in adapted
    assert ORIGINAL_DDI_PATH not in adapted

    assert f"med_file = {str(p_rx.resolve())!r}" in adapted
    assert f"diag_file = {str(p_dx.resolve())!r}" in adapted
    assert f"procedure_file = {str(p_pr.resolve())!r}" in adapted
    assert f"ddi_file = {str(p_ddi.resolve())!r}" in adapted


def test_adapt_c721_processing_script_rejects_drift() -> None:
    with pytest.raises(ProtocolValidationError, match="drifted"):
        adapt_c721_processing_script(
            "incomplete script",
            prescriptions_path=Path("rx"),
            diagnoses_path=Path("dx"),
            procedures_path=Path("pr"),
            ddi_path=Path("ddi"),
        )


def make_mock_checkout(root: Path) -> Path:
    checkout = root / "SafeDrug-c7218d0"
    data_dir = checkout / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "processing.py").write_text(SAMPLE_PROCESSING_SCRIPT, encoding="utf-8")
    for asset in REQUIRED_PREPROCESSING_ASSETS:
        if asset == "voc_final.pkl":
            med_voc = SimpleNamespace(idx2word=[f"M{i}" for i in range(131)])
            with (data_dir / asset).open("wb") as f:
                pickle.dump({"med_voc": med_voc}, f)
        elif asset != "processing.py":
            (data_dir / asset).write_bytes(b"dummy_asset_content")
    return checkout


def test_verify_preprocessing_checkout_happy_path(tmp_path: Path) -> None:
    checkout = make_mock_checkout(tmp_path)

    def mock_runner(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        if "rev-parse" in cmd:
            return SimpleNamespace(stdout=f"{C721_SOURCE_REVISION}\n", returncode=0)
        if "status" in cmd:
            return SimpleNamespace(stdout="", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    verify_preprocessing_checkout(checkout, runner=mock_runner)


def test_verify_preprocessing_checkout_rejects_dirty_or_wrong_rev(tmp_path: Path) -> None:
    checkout = make_mock_checkout(tmp_path)

    def mock_runner_bad_rev(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        if "rev-parse" in cmd:
            return SimpleNamespace(stdout="bad_rev_12345\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    with pytest.raises(ProtocolValidationError, match="revision"):
        verify_preprocessing_checkout(checkout, runner=mock_runner_bad_rev)

    def mock_runner_dirty(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        if "rev-parse" in cmd:
            return SimpleNamespace(stdout=f"{C721_SOURCE_REVISION}\n", returncode=0)
        if "status" in cmd:
            return SimpleNamespace(stdout=" M data/processing.py\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    with pytest.raises(ProtocolValidationError, match="tracked modifications"):
        verify_preprocessing_checkout(checkout, runner=mock_runner_dirty)


def test_stage_safedrug_c721_happy_path(tmp_path: Path) -> None:
    checkout = make_mock_checkout(tmp_path)
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    p_rx = raw_dir / "PRESCRIPTIONS.csv.gz"
    p_dx = raw_dir / "DIAGNOSES_ICD.csv.gz"
    p_pr = raw_dir / "PROCEDURES_ICD.csv.gz"
    p_ddi = raw_dir / "drug-DDI.csv"
    for f in (p_rx, p_dx, p_pr, p_ddi):
        f.touch()

    staging_dir = tmp_path / "staging"

    def mock_runner(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        if "rev-parse" in cmd:
            return SimpleNamespace(stdout=f"{C721_SOURCE_REVISION}\n", returncode=0)
        if "status" in cmd:
            return SimpleNamespace(stdout="", returncode=0)
        if "processing.py" in cmd:
            cwd = Path(kwargs.get("cwd", "."))
            med_voc = SimpleNamespace(idx2word=[f"M{i}" for i in range(131)])
            with (cwd / "voc_final.pkl").open("wb") as stream:
                pickle.dump({"med_voc": med_voc}, stream)
            for out_name in ("records_final.pkl", "ddi_A_final.pkl", "ehr_adj_final.pkl"):
                (cwd / out_name).write_bytes(b"dummy_generated_data")
            return SimpleNamespace(stdout="ok", stderr="", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    manifest_file = tmp_path / "input-manifest.json"
    manifest_file.write_text(json.dumps({"artifact_id": "manifest-123"}), encoding="utf-8")

    proof = stage_safedrug_c721(
        preprocessing_checkout=checkout,
        prescriptions_path=p_rx,
        diagnoses_path=p_dx,
        procedures_path=p_pr,
        ddi_path=p_ddi,
        staging_directory=staging_dir,
        python="python",
        input_manifest_path=manifest_file,
        runner=mock_runner,
    )

    assert proof["schema_version"] == 1
    assert proof["kind"] == "safedrug_c721_staging_proof"
    assert proof["source_revision"] == C721_SOURCE_REVISION
    assert proof["vocabulary_alignment"]["med_voc_ordered_equality"] == "passed"
    assert proof["metadata"] == {
        "paper_reported_visits": 14_995,
        "executable_visits": 15_032,
        "difference": 37,
    }
    assert len(proof["outputs"]) == 6

    # Verify all 6 outputs exist in staging
    for name in (
        "records_final.pkl",
        "voc_final.pkl",
        "ddi_A_final.pkl",
        "ehr_adj_final.pkl",
        "ddi_mask_H.pkl",
        "idx2drug.pkl",
        "staging-proof.json",
    ):
        assert (staging_dir / name).is_file()

    # Verify byte equality of mask and molecule map
    assert (staging_dir / "ddi_mask_H.pkl").read_bytes() == (
        checkout / "data" / "ddi_mask_H.pkl"
    ).read_bytes()
    assert (staging_dir / "idx2drug.pkl").read_bytes() == (
        checkout / "data" / "idx2SMILES.pkl"
    ).read_bytes()


def test_stage_safedrug_c721_rejects_existing_staging_dir(tmp_path: Path) -> None:
    checkout = make_mock_checkout(tmp_path)
    staging_dir = tmp_path / "staging_exists"
    staging_dir.mkdir()

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    p_rx = raw_dir / "PRESCRIPTIONS.csv.gz"
    p_dx = raw_dir / "DIAGNOSES_ICD.csv.gz"
    p_pr = raw_dir / "PROCEDURES_ICD.csv.gz"
    p_ddi = raw_dir / "drug-DDI.csv"
    for f in (p_rx, p_dx, p_pr, p_ddi):
        f.touch()

    with pytest.raises(ProtocolValidationError, match="staging directory already exists"):
        stage_safedrug_c721(
            preprocessing_checkout=checkout,
            prescriptions_path=p_rx,
            diagnoses_path=p_dx,
            procedures_path=p_pr,
            ddi_path=p_ddi,
            staging_directory=staging_dir,
        )


def test_stage_safedrug_c721_rejects_vocabulary_order_mismatch(tmp_path: Path) -> None:
    checkout = make_mock_checkout(tmp_path)
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    p_rx = raw_dir / "PRESCRIPTIONS.csv.gz"
    p_dx = raw_dir / "DIAGNOSES_ICD.csv.gz"
    p_pr = raw_dir / "PROCEDURES_ICD.csv.gz"
    p_ddi = raw_dir / "drug-DDI.csv"
    for f in (p_rx, p_dx, p_pr, p_ddi):
        f.touch()

    staging_dir = tmp_path / "staging"

    def mock_runner(cmd: list[str], **kwargs: Any) -> SimpleNamespace:
        if "rev-parse" in cmd:
            return SimpleNamespace(stdout=f"{C721_SOURCE_REVISION}\n", returncode=0)
        if "status" in cmd:
            return SimpleNamespace(stdout="", returncode=0)
        if "processing.py" in cmd:
            cwd = Path(kwargs.get("cwd", "."))
            # Reversed med voc
            med_voc = SimpleNamespace(idx2word=[f"M{130 - i}" for i in range(131)])
            with (cwd / "voc_final.pkl").open("wb") as stream:
                pickle.dump({"med_voc": med_voc}, stream)
            for out_name in ("records_final.pkl", "ddi_A_final.pkl", "ehr_adj_final.pkl"):
                (cwd / out_name).write_bytes(b"dummy_generated_data")
            return SimpleNamespace(stdout="ok", stderr="", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    with pytest.raises(ProtocolValidationError, match="vocabulary order differs"):
        stage_safedrug_c721(
            preprocessing_checkout=checkout,
            prescriptions_path=p_rx,
            diagnoses_path=p_dx,
            procedures_path=p_pr,
            ddi_path=p_ddi,
            staging_directory=staging_dir,
            runner=mock_runner,
        )


def test_molerec_environment_hash_waits_for_u5_and_tls_stays_enabled() -> None:
    from medrec_research import BaselineRegistry

    registry_path = Path(__file__).parents[2] / "baselines" / "registry.toml"
    registry = BaselineRegistry.load(registry_path)
    program = registry.get_program("safedrug-archived")
    assert program.conda_environment == "medrec-molerec-table1"
    assert program.environment_sha256 is None

    readme_text = (Path(__file__).parents[2] / "environments" / "README.md").read_text(
        encoding="utf-8"
    )
    assert "ssl_verify: true" in readme_text
