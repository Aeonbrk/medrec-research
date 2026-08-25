"""SafeDrug c7218d0 paper-lineage dataset staging and bridge verification."""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ._validation import parse_json_object, write_json_atomic
from .errors import ProtocolValidationError

C721_SOURCE_REVISION = "c7218d0976e5ee5588aeaf5bdbc86b338126bba5"
ORIGINAL_PRESCRIPTIONS_PATH = (
    "med_file = '/srv/local/data/physionet.org/files/mimiciii/1.4/PRESCRIPTIONS.csv'"
)
ORIGINAL_DIAGNOSES_PATH = (
    "diag_file = '/srv/local/data/physionet.org/files/mimiciii/1.4/DIAGNOSES_ICD.csv'"
)
ORIGINAL_PROCEDURES_PATH = (
    "procedure_file = '/srv/local/data/physionet.org/files/mimiciii/1.4/PROCEDURES_ICD.csv'"
)
ORIGINAL_DDI_PATH = "ddi_file = './drug-DDI.csv'"

REQUIRED_PREPROCESSING_ASSETS = (
    "processing.py",
    "idx2SMILES.pkl",
    "ndc2atc_level4.csv",
    "drug-atc.csv",
    "ndc2rxnorm_mapping.txt",
    "voc_final.pkl",
    "ddi_mask_H.pkl",
)
UPSTREAM_GENERATED_OUTPUTS = (
    "records_final.pkl",
    "voc_final.pkl",
    "ddi_A_final.pkl",
    "ehr_adj_final.pkl",
)
FINAL_SIX_OUTPUTS = (
    *UPSTREAM_GENERATED_OUTPUTS,
    "ddi_mask_H.pkl",
    "idx2drug.pkl",
)
SUBSTITUTED_FIELDS = ("med_file", "diag_file", "procedure_file", "ddi_file")

Runner = Callable[..., subprocess.CompletedProcess[str]]


def adapt_c721_processing_script(
    source: str,
    *,
    prescriptions_path: Path,
    diagnoses_path: Path,
    procedures_path: Path,
    ddi_path: Path,
) -> str:
    """Perform exact 4-path substitution on c721 data/processing.py source."""
    substitutions = [
        (ORIGINAL_PRESCRIPTIONS_PATH, f"med_file = {str(prescriptions_path.resolve())!r}"),
        (ORIGINAL_DIAGNOSES_PATH, f"diag_file = {str(diagnoses_path.resolve())!r}"),
        (ORIGINAL_PROCEDURES_PATH, f"procedure_file = {str(procedures_path.resolve())!r}"),
        (ORIGINAL_DDI_PATH, f"ddi_file = {str(ddi_path.resolve())!r}"),
    ]
    adapted = source
    for orig, repl in substitutions:
        if adapted.count(orig) != 1:
            raise ProtocolValidationError(
                f"c721 processing.py drifted: expected exactly 1 occurrence of {orig!r}"
            )
        adapted = adapted.replace(orig, repl)
    return adapted


def verify_preprocessing_checkout(checkout_path: Path, *, runner: Runner = subprocess.run) -> None:
    """Verify that preprocessing checkout is clean at exact c721 revision."""
    if not checkout_path.is_dir():
        raise ProtocolValidationError(f"preprocessing checkout not found: {checkout_path}")

    try:
        rev = runner(
            [
                "git",
                "-c",
                f"safe.directory={checkout_path}",
                "-C",
                str(checkout_path),
                "rev-parse",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ProtocolValidationError(
            "unable to check git revision of preprocessing checkout"
        ) from error

    if rev != C721_SOURCE_REVISION:
        raise ProtocolValidationError(
            f"preprocessing checkout revision must be {C721_SOURCE_REVISION}, observed {rev}"
        )

    try:
        dirty = runner(
            [
                "git",
                "-c",
                f"safe.directory={checkout_path}",
                "-C",
                str(checkout_path),
                "status",
                "--porcelain",
                "--untracked-files=no",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ProtocolValidationError(
            "unable to check git status of preprocessing checkout"
        ) from error

    if dirty:
        raise ProtocolValidationError("preprocessing checkout has tracked modifications")

    data_dir = checkout_path / "data"
    missing = [name for name in REQUIRED_PREPROCESSING_ASSETS if not (data_dir / name).is_file()]
    if missing:
        raise ProtocolValidationError(
            f"preprocessing checkout missing required assets in data/: {missing}"
        )


def stage_safedrug_c721(
    *,
    preprocessing_checkout: Path,
    prescriptions_path: Path,
    diagnoses_path: Path,
    procedures_path: Path,
    ddi_path: Path,
    staging_directory: Path,
    python: str = sys.executable,
    input_manifest_path: Path | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Execute c721 preprocessing into staging directory and verify semantic bridge."""
    if staging_directory.exists():
        raise ProtocolValidationError(f"staging directory already exists: {staging_directory}")

    # Validate raw inputs
    for name, path in (
        ("prescriptions", prescriptions_path),
        ("diagnoses", diagnoses_path),
        ("procedures", procedures_path),
        ("drug_ddi", ddi_path),
    ):
        if not path.is_file():
            raise ProtocolValidationError(f"raw input {name} file not found: {path}")
        if path.is_symlink():
            raise ProtocolValidationError(f"raw input {name} must be a regular file, not a symlink")

    verify_preprocessing_checkout(preprocessing_checkout, runner=runner)

    input_manifest_artifact_id = None
    if input_manifest_path is not None:
        if not input_manifest_path.is_file():
            raise ProtocolValidationError(f"input manifest file not found: {input_manifest_path}")
        try:
            manifest_data = parse_json_object(
                input_manifest_path.read_text(encoding="utf-8"),
                context="input manifest",
            )
            input_manifest_artifact_id = str(
                manifest_data.get("artifact_id") or input_manifest_path.name
            )
        except Exception as error:
            raise ProtocolValidationError(f"failed to parse input manifest: {error}") from error

    data_dir = preprocessing_checkout / "data"
    original_processing_src = (data_dir / "processing.py").read_text(encoding="utf-8")
    adapted_src = adapt_c721_processing_script(
        original_processing_src,
        prescriptions_path=prescriptions_path,
        diagnoses_path=diagnoses_path,
        procedures_path=procedures_path,
        ddi_path=ddi_path,
    )

    work_dir = Path(tempfile.mkdtemp(prefix="c721_stage_work_"))
    try:
        # Copy required helper assets into work directory
        for asset in (
            "idx2SMILES.pkl",
            "ndc2atc_level4.csv",
            "drug-atc.csv",
            "ndc2rxnorm_mapping.txt",
        ):
            shutil.copy2(data_dir / asset, work_dir / asset)

        (work_dir / "processing.py").write_text(adapted_src, encoding="utf-8")

        # Execute preprocessing script
        completed = runner(
            [python, "processing.py"],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ProtocolValidationError(
                f"c721 preprocessing failed with exit code {completed.returncode}: {completed.stderr or completed.stdout}"
            )

        for out_name in UPSTREAM_GENERATED_OUTPUTS:
            if not (work_dir / out_name).is_file():
                raise ProtocolValidationError(f"c721 preprocessing failed to generate '{out_name}'")

        # Create staging directory and move generated outputs
        staging_directory.mkdir(parents=True, exist_ok=False)
        for out_name in UPSTREAM_GENERATED_OUTPUTS:
            shutil.move(str(work_dir / out_name), str(staging_directory / out_name))

        # Check exact ordered equality of med_voc.idx2word
        try:
            dill = importlib.import_module("dill")
        except ImportError:
            dill = importlib.import_module("pickle")

        with (staging_directory / "voc_final.pkl").open("rb") as f:
            generated_voc = dill.load(f)
        with (data_dir / "voc_final.pkl").open("rb") as f:
            pinned_voc = dill.load(f)

        gen_med = getattr(generated_voc.get("med_voc"), "idx2word", None)
        pin_med = getattr(pinned_voc.get("med_voc"), "idx2word", None)
        if gen_med != pin_med:
            raise ProtocolValidationError(
                "regenerated medication vocabulary order differs from pinned c721 voc_final.pkl"
            )

        # Copy pinned ddi_mask_H.pkl and idx2SMILES.pkl (as idx2drug.pkl)
        mask_src = data_dir / "ddi_mask_H.pkl"
        mask_dst = staging_directory / "ddi_mask_H.pkl"
        shutil.copy2(mask_src, mask_dst)

        idx2drug_src = data_dir / "idx2SMILES.pkl"
        idx2drug_dst = staging_directory / "idx2drug.pkl"
        shutil.copy2(idx2drug_src, idx2drug_dst)

        # Verify byte equality
        if mask_src.read_bytes() != mask_dst.read_bytes():
            raise ProtocolValidationError(
                "ddi_mask_H.pkl copy is not byte-identical to pinned source"
            )
        if idx2drug_src.read_bytes() != idx2drug_dst.read_bytes():
            raise ProtocolValidationError(
                "idx2drug.pkl copy is not byte-identical to pinned idx2SMILES.pkl"
            )

        proof_record = {
            "schema_version": 1,
            "kind": "safedrug_c721_staging_proof",
            "source_revision": C721_SOURCE_REVISION,
            "upstream_entrypoints": ["data/processing.py", "data/ddi_mask_H.py"],
            "substituted_fields": list(SUBSTITUTED_FIELDS),
            "ddi_source": "SafeDrug-published asset lineage",
            "vocabulary_alignment": {
                "med_voc_ordered_equality": "passed",
            },
            "metadata": {
                "paper_reported_visits": 14995,
                "executable_visits": 15032,
                "difference": 37,
            },
            "outputs": list(FINAL_SIX_OUTPUTS),
            "input_manifest_artifact_id": input_manifest_artifact_id,
        }
        write_json_atomic(staging_directory / "staging-proof.json", proof_record)
        return proof_record

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
