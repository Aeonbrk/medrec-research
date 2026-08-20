from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from medrec_research import ProtocolCheckRecord

PROJECT_ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "fixtures" / "synthetic"


def _run_cli(
    visits: Path,
    output: Path,
    *,
    manifest: Path = FIXTURE_ROOT / "manifest.json",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (
            sys.executable,
            "-m",
            "medrec_research.cli",
            "reference",
            "--manifest",
            str(manifest),
            "--visits",
            str(visits),
            "--output",
            str(output),
            "--top-k",
            "2",
            "--seed",
            "7",
        ),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_reference_cli_writes_deterministic_public_protocol_check(tmp_path: Path) -> None:
    first_output = tmp_path / "first.json"
    second_output = tmp_path / "second.json"

    first = _run_cli(FIXTURE_ROOT / "visits.json", first_output)
    second = _run_cli(FIXTURE_ROOT / "visits.json", second_output)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    first_bytes = first_output.read_bytes()
    assert first_bytes == second_output.read_bytes()

    public_record = first_bytes.decode("utf-8")
    record = ProtocolCheckRecord.from_json(public_record)
    parameters = {parameter.name: parameter.value for parameter in record.parameters}
    assert parameters == {"seed": 7, "strategy": "train-frequency", "top_k": 2}
    assert record.evaluation.visit_count == 3
    assert record.evaluation.jaccard == pytest.approx(1 / 3)
    assert record.evaluation.precision == pytest.approx(1 / 3)
    assert record.evaluation.recall == pytest.approx(1 / 3)
    assert record.evaluation.f1 == pytest.approx(1 / 3)
    assert record.evaluation.mean_medication_count == 2.0
    assert (
        record.medication_vocabulary_sha256
        == "b493d4d41dda5b325209e17ca7d012a23c110951cb1fcad5b2eab9a036386561"
    )
    assert record.checks == (
        "dataset-manifest-verified",
        "deterministic-evaluation",
        "test-targets-core-owned",
    )

    for private_value in (
        "patient_id",
        "predicted_medications",
        "train-001",
        "test-001",
        str(tmp_path),
    ):
        assert private_value not in public_record


def test_reference_cli_rejects_fixture_checksum_mismatch(tmp_path: Path) -> None:
    original = (FIXTURE_ROOT / "visits.json").read_text(encoding="utf-8")
    tampered_visits = tmp_path / "visits.json"
    tampered_visits.write_text(original.replace("RX_C", "RX_Z", 1), encoding="utf-8")
    output = tmp_path / "run.json"

    completed = _run_cli(tampered_visits, output)

    assert completed.returncode == 2
    assert "checksum" in completed.stderr
    assert not output.exists()


def test_reference_cli_rejects_vocabulary_checksum_mismatch(tmp_path: Path) -> None:
    original = (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
    tampered_manifest = tmp_path / "manifest.json"
    tampered_manifest.write_text(
        original.replace(
            "b493d4d41dda5b325209e17ca7d012a23c110951cb1fcad5b2eab9a036386561",
            "0" * 64,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "run.json"

    completed = _run_cli(
        FIXTURE_ROOT / "visits.json",
        output,
        manifest=tampered_manifest,
    )

    assert completed.returncode == 2
    assert "vocabulary" in completed.stderr
    assert not output.exists()
