from __future__ import annotations

import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from medrec_research import BaselineRegistry, DatasetManifest, RunRecord

PROJECT_ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "fixtures" / "synthetic"


def _registry_text(*, adaptation_budget_sha256: str) -> str:
    qualification_evidence = "\n".join(
        f'''[[baselines.comparison_qualifications.evidence]]
gate = "{gate}"
artifact_sha256 = "{artifact_sha256}"'''
        for gate, artifact_sha256 in (
            ("adaptation_budget", adaptation_budget_sha256),
            ("cohort_identity", "4" * 64),
            ("core_integrity", "5" * 64),
            ("deterministic_adapter", "6" * 64),
            ("independent_evaluation", "7" * 64),
        )
    )
    return f'''schema_version = 1

[[baselines]]
baseline_id = "comparison-reference"
display_name = "Comparison Reference"
supported_modes = ["comparison"]
readiness = "comparison_ready"
adapter_command = ["python", "adapter.py"]
adapter_revision = "adapter-0123456789abcdef"
environment_sha256 = "{"e" * 64}"

[[baselines.readiness_evidence]]
gate = "adapter_smoke"
artifact_sha256 = "{"1" * 64}"

[[baselines.readiness_evidence]]
gate = "environment_lock"
artifact_sha256 = "{"2" * 64}"

[[baselines.comparison_qualifications]]
protocol_version = "1.0"
dataset_manifest_sha256 = "0f40521e11f15028d0e557b42c3abe01268ccfd5e6cd9cedd748fb510cd8163c"
adaptation_budget_sha256 = "{adaptation_budget_sha256}"

{qualification_evidence}

[baselines.source]
repository = "https://example.invalid/comparison-reference.git"
revision = "0123456789abcdef"
status = "pinned"
'''


def _prediction_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "predictions": [
            {
                "schema_version": 1,
                "patient_id": "test-001",
                "visit_id": "test-001-v1",
                "split": "test",
                "target_medications": ["RX_A", "RX_B"],
                "predicted_medications": ["RX_A", "RX_B"],
            },
            {
                "schema_version": 1,
                "patient_id": "test-001",
                "visit_id": "test-001-v2",
                "split": "test",
                "target_medications": ["RX_C"],
                "predicted_medications": ["RX_A", "RX_B"],
            },
            {
                "schema_version": 1,
                "patient_id": "test-002",
                "visit_id": "test-002-v1",
                "split": "test",
                "target_medications": [],
                "predicted_medications": ["RX_A", "RX_B"],
            },
        ],
    }


def test_accept_comparison_recomputes_and_emits_public_record(tmp_path: Path) -> None:
    predictions_path = tmp_path / "predictions.json"
    predictions_path.write_text(json.dumps(_prediction_payload()), encoding="utf-8")
    vocabulary_path = tmp_path / "medications.txt"
    vocabulary_path.write_text("RX_A\nRX_B\nRX_C\n", encoding="utf-8")
    budget_path = tmp_path / "adaptation-budget.json"
    budget_path.write_text('{"trials": 1}\n', encoding="utf-8")
    registry_path = tmp_path / "registry.toml"
    registry_path.write_text(
        _registry_text(adaptation_budget_sha256=sha256(budget_path.read_bytes()).hexdigest()),
        encoding="utf-8",
    )
    config_path = tmp_path / "run-config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "protocol_version": "1.0",
                "seed": 7,
                "selection_split": "validation",
                "evaluation_split": "test",
                "parameters": [{"name": "top_k", "value": 2}],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "run-record.json"

    completed = subprocess.run(
        (
            sys.executable,
            "-m",
            "medrec_research.cli",
            "accept-comparison",
            "--manifest",
            str(FIXTURE_ROOT / "manifest.json"),
            "--registry",
            str(registry_path),
            "--baseline-id",
            "comparison-reference",
            "--predictions",
            str(predictions_path),
            "--medication-vocabulary",
            str(vocabulary_path),
            "--run-config",
            str(config_path),
            "--adaptation-budget",
            str(budget_path),
            "--output",
            str(output_path),
        ),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    registry = BaselineRegistry.load(registry_path)
    manifest = DatasetManifest.load(FIXTURE_ROOT / "manifest.json")
    record = RunRecord.from_json(
        output_path.read_text(encoding="utf-8"),
        baseline=registry.get("comparison-reference"),
        dataset=manifest,
    )
    assert record.evaluation.visit_count == 3
    assert record.evaluation.jaccard == 1 / 3
    assert {artifact.name for artifact in record.artifact_checksums} == {"prediction-records"}
    public_record = output_path.read_text(encoding="utf-8")
    for restricted_value in ("test-001", str(tmp_path), "predicted_medications"):
        assert restricted_value not in public_record


def test_accept_comparison_rejects_noncanonical_vocabulary(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.toml"
    predictions_path = tmp_path / "predictions.json"
    predictions_path.write_text(json.dumps(_prediction_payload()), encoding="utf-8")
    vocabulary_path = tmp_path / "medications.txt"
    vocabulary_path.write_text("RX_B\nRX_A\nRX_C\n", encoding="utf-8")
    budget_path = tmp_path / "budget.json"
    budget_path.write_text("{}\n", encoding="utf-8")
    registry_path.write_text(
        _registry_text(adaptation_budget_sha256=sha256(budget_path.read_bytes()).hexdigest()),
        encoding="utf-8",
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "protocol_version": "1.0",
                "seed": 7,
                "selection_split": "validation",
                "evaluation_split": "test",
                "parameters": [],
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        (
            sys.executable,
            "-m",
            "medrec_research.cli",
            "accept-comparison",
            "--manifest",
            str(FIXTURE_ROOT / "manifest.json"),
            "--registry",
            str(registry_path),
            "--baseline-id",
            "comparison-reference",
            "--predictions",
            str(predictions_path),
            "--medication-vocabulary",
            str(vocabulary_path),
            "--run-config",
            str(config_path),
            "--adaptation-budget",
            str(budget_path),
            "--output",
            str(tmp_path / "output.json"),
        ),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "canonical" in completed.stderr
