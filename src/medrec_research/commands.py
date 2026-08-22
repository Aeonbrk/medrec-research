"""Deterministic value transformations used by CLI handlers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ._validation import require_single_line_public_string, strict_fields
from .dataset import DatasetManifest, SplitName
from .errors import ProtocolValidationError
from .evaluation import evaluate_predictions
from .prediction import PredictionRecord
from .registry import BaselineDefinition, BaselineRegistry
from .run_record import ArtifactChecksum, RunParameter, RunRecord


def parse_prediction_records(payload: object) -> tuple[PredictionRecord, ...]:
    """Validate a prediction-file value and return its records."""
    parsed = strict_fields(
        payload,
        required=("schema_version", "predictions"),
        context="predictions file",
    )
    if parsed["schema_version"] != 1:
        raise ProtocolValidationError("predictions schema_version must be 1")
    prediction_items = parsed["predictions"]
    if not isinstance(prediction_items, list):
        raise ProtocolValidationError("predictions must be a list")
    return tuple(PredictionRecord.from_dict(item) for item in prediction_items)


def accept_comparison_command(
    *,
    manifest: DatasetManifest,
    baseline: BaselineDefinition,
    predictions: Sequence[PredictionRecord],
    run_config: Mapping[str, object],
    medication_vocabulary: Sequence[str],
    adaptation_budget_sha256: str,
    prediction_artifact_sha256: str,
) -> RunRecord:
    """Validate structured comparison values and create a public Run Record."""
    config = strict_fields(
        run_config,
        required=(
            "schema_version",
            "protocol_version",
            "seed",
            "selection_split",
            "evaluation_split",
            "parameters",
        ),
        context="comparison run config",
    )
    if config["schema_version"] != 1:
        raise ProtocolValidationError("comparison run config schema_version must be 1")
    protocol_version = require_single_line_public_string(
        config["protocol_version"], field="protocol_version"
    )
    if not baseline.qualifies_for(
        protocol_version=protocol_version,
        dataset_manifest_sha256=manifest.manifest_sha256,
        adaptation_budget_sha256=adaptation_budget_sha256,
    ):
        raise ProtocolValidationError(
            f"baseline '{baseline.baseline_id}' is not qualified for comparison under the "
            "provided protocol/dataset/budget"
        )

    vocabulary = tuple(medication_vocabulary)
    if vocabulary != tuple(sorted(set(vocabulary))):
        raise ProtocolValidationError("medication vocabulary must be in canonical sorted order")

    raw_parameters = config["parameters"]
    if not isinstance(raw_parameters, list):
        raise ProtocolValidationError("comparison run config parameters must be a list")
    parameters = tuple(RunParameter.from_dict(item) for item in raw_parameters)

    return RunRecord.create(
        mode="comparison",
        protocol_version=protocol_version,
        baseline=baseline,
        dataset=manifest,
        seed=config["seed"],
        selection_split=config["selection_split"],
        evaluation_split=config["evaluation_split"],
        parameters=parameters,
        evaluation=evaluate_predictions(predictions),
        adaptation_budget_sha256=adaptation_budget_sha256,
        artifact_checksums=(
            ArtifactChecksum(
                name="prediction-records",
                sha256=prediction_artifact_sha256,
            ),
        ),
        evaluation_visit_membership_digest=manifest.split(SplitName.TEST).visit_membership_digest,
    )


def format_baseline_table(registry: BaselineRegistry) -> str:
    """Render the current registry table without performing terminal I/O."""
    lines = [
        f"{'Baseline ID':<20} {'Display Name':<25} {'Readiness':<20} {'Modes'}",
        "-" * 80,
    ]
    lines.extend(
        f"{baseline.baseline_id:<20} {baseline.display_name:<25} "
        f"{baseline.readiness.value:<20} "
        f"{', '.join(mode.value for mode in baseline.supported_modes)}"
        for baseline in registry.baselines
    )
    return "\n".join(lines)


__all__ = (
    "accept_comparison_command",
    "format_baseline_table",
    "parse_prediction_records",
)
