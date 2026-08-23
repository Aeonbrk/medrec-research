from __future__ import annotations

from pathlib import Path

import pytest

from medrec_research import (
    BaselineDefinition,
    BaselineRegistry,
    DatasetManifest,
    ProtocolValidationError,
)
from medrec_research.commands import (
    accept_comparison_command,
    format_baseline_table,
    parse_prediction_records,
)

PROJECT_ROOT = Path(__file__).parents[2]
FIXTURE_ROOT = PROJECT_ROOT / "fixtures" / "synthetic"


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


def _comparison_baseline(
    *, manifest_sha256: str, adaptation_budget_sha256: str
) -> BaselineDefinition:
    evidence = "\n".join(
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
    registry = BaselineRegistry.from_toml(
        f'''schema_version = 1

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
dataset_manifest_sha256 = "{manifest_sha256}"
adaptation_budget_sha256 = "{adaptation_budget_sha256}"

{evidence}

[baselines.source]
repository = "https://example.invalid/comparison-reference.git"
revision = "0123456789abcdef"
status = "pinned"
'''
    )
    return registry.get("comparison-reference")


def _run_config() -> dict[str, object]:
    return {
        "schema_version": 1,
        "protocol_version": "1.0",
        "seed": 7,
        "selection_split": "validation",
        "evaluation_split": "test",
        "parameters": [{"name": "top_k", "value": 2}],
    }


def test_parse_prediction_records_requires_supported_envelope() -> None:
    with pytest.raises(ProtocolValidationError, match="schema_version must be 1"):
        parse_prediction_records({"schema_version": 2, "predictions": []})

    with pytest.raises(ProtocolValidationError, match="unknown field"):
        parse_prediction_records(
            {"schema_version": 1, "predictions": [], "patient_ids": ["private"]}
        )


def test_accept_comparison_command_recomputes_public_record() -> None:
    manifest = DatasetManifest.load(FIXTURE_ROOT / "manifest.json")
    budget_sha256 = "b" * 64
    baseline = _comparison_baseline(
        manifest_sha256=manifest.manifest_sha256,
        adaptation_budget_sha256=budget_sha256,
    )

    record = accept_comparison_command(
        manifest=manifest,
        baseline=baseline,
        predictions=parse_prediction_records(_prediction_payload()),
        run_config=_run_config(),
        medication_vocabulary=("RX_A", "RX_B", "RX_C"),
        adaptation_budget_sha256=budget_sha256,
        prediction_artifact_sha256="a" * 64,
    )

    assert record.evaluation.visit_count == 3
    assert record.evaluation.jaccard == 1 / 3
    assert record.artifact_checksums[0].name == "prediction-records"
    assert record.artifact_checksums[0].sha256 == "a" * 64


def test_accept_comparison_command_rejects_duplicate_vocabulary() -> None:
    manifest = DatasetManifest.load(FIXTURE_ROOT / "manifest.json")
    budget_sha256 = "b" * 64
    baseline = _comparison_baseline(
        manifest_sha256=manifest.manifest_sha256,
        adaptation_budget_sha256=budget_sha256,
    )

    with pytest.raises(ProtocolValidationError, match="canonical sorted order"):
        accept_comparison_command(
            manifest=manifest,
            baseline=baseline,
            predictions=parse_prediction_records(_prediction_payload()),
            run_config=_run_config(),
            medication_vocabulary=("RX_A", "RX_A", "RX_B", "RX_C"),
            adaptation_budget_sha256=budget_sha256,
            prediction_artifact_sha256="a" * 64,
        )


def test_format_baseline_table_preserves_registry_order() -> None:
    registry = BaselineRegistry.load(PROJECT_ROOT / "baselines" / "registry.toml")

    table = format_baseline_table(registry)

    lines = table.splitlines()
    assert lines[0].startswith("Baseline ID")
    assert [line.split()[0] for line in lines[2:]] == [
        "reference",
        "gamenet",
        "safedrug",
        "retain",
        "leap-safedrug",
    ]
