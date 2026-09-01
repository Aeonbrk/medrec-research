"""Deterministic SafeDrug Table 2 Reproduction Mode auditing."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .._validation import (
    parse_json_object,
    require_sha256,
    require_string,
    strict_fields,
    write_json_atomic,
)
from ..errors import ProtocolValidationError

REQUIRED_BASELINES = ("gamenet", "safedrug", "retain", "leap-safedrug")
SUMMARY_METRICS = ("ddi_rate", "jaccard", "avg_f1", "prauc", "avg_medications")
EXPECTED_DATASET_COUNTS = {
    "patients": 6_350,
    "visits": 15_032,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}
ARCHIVED_SOURCE_REVISION = "8deee38cfdb2a38882377ff95cce5922d6d9e8d6"


def load_table2_reference(reference_path: Path) -> dict[str, dict[str, dict[str, float]]]:
    """Load and validate Table 2 published reference targets."""
    try:
        raw_text = reference_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ProtocolValidationError(f"failed to read Table 2 reference: {error}") from error

    parsed = parse_json_object(raw_text, context="Table 2 reference file")
    strict_fields(
        parsed,
        required=("schema_version", "kind", "paper", "baselines"),
        context="Table 2 reference",
    )
    if parsed["schema_version"] != 1 or parsed["kind"] != "safedrug_table2_reference":
        raise ProtocolValidationError("invalid Table 2 reference schema or kind")

    baselines = parsed["baselines"]
    if not isinstance(baselines, Mapping):
        raise ProtocolValidationError("Table 2 reference baselines must be an object")

    result: dict[str, dict[str, dict[str, float]]] = {}
    for baseline_id in REQUIRED_BASELINES:
        if baseline_id not in baselines:
            raise ProtocolValidationError(
                f"Table 2 reference missing required baseline '{baseline_id}'"
            )
        metrics = baselines[baseline_id]
        if not isinstance(metrics, Mapping):
            raise ProtocolValidationError(f"metrics for baseline '{baseline_id}' must be an object")
        baseline_metrics: dict[str, dict[str, float]] = {}
        for metric in SUMMARY_METRICS:
            if metric not in metrics:
                raise ProtocolValidationError(
                    f"baseline '{baseline_id}' missing reference metric '{metric}'"
                )
            target = metrics[metric]
            if not isinstance(target, Mapping) or "mean" not in target or "std" not in target:
                raise ProtocolValidationError(
                    f"metric '{metric}' in '{baseline_id}' must specify mean and std"
                )
            mean = float(target["mean"])
            std = float(target["std"])
            if not math.isfinite(mean) or not math.isfinite(std) or std < 0:
                raise ProtocolValidationError(
                    f"metric '{metric}' in '{baseline_id}' has non-finite or invalid target values"
                )
            baseline_metrics[metric] = {"mean": mean, "std": std}
        result[baseline_id] = baseline_metrics
    return result


def validate_formal_result(
    result_data: dict[str, Any],
    *,
    expected_baseline_id: str,
    context: str,
) -> dict[str, Any]:
    """Validate one formal Reproduction Mode result artifact."""
    strict_fields(
        result_data,
        required=(
            "schema_version",
            "baseline_id",
            "source_revision",
            "dataset_counts",
            "environment",
            "adaptation",
            "checkpoint",
            "test_rounds",
            "harness_summary",
            "upstream_summary",
            "status",
        ),
        optional=("archived_learning_rate",),
        context=context,
    )
    if result_data["schema_version"] != 1:
        raise ProtocolValidationError(f"{context} schema_version must be 1")
    if result_data["baseline_id"] != expected_baseline_id:
        raise ProtocolValidationError(
            f"{context} baseline_id must be '{expected_baseline_id}', observed '{result_data['baseline_id']}'"
        )
    if result_data["source_revision"] != ARCHIVED_SOURCE_REVISION:
        raise ProtocolValidationError(
            f"{context} source_revision must be '{ARCHIVED_SOURCE_REVISION}', observed '{result_data['source_revision']}'"
        )

    # Validate dataset counts
    counts = result_data["dataset_counts"]
    if not isinstance(counts, Mapping):
        raise ProtocolValidationError(f"{context} dataset_counts must be an object")
    for count_name, expected_count in EXPECTED_DATASET_COUNTS.items():
        if counts.get(count_name) != expected_count:
            raise ProtocolValidationError(
                f"{context} dataset count '{count_name}' must be {expected_count}, observed {counts.get(count_name)}"
            )

    # Validate status
    status = result_data["status"]
    if not isinstance(status, Mapping):
        raise ProtocolValidationError(f"{context} status must be an object")
    if status.get("state") != "completed" or status.get("stage") != "terminal":
        raise ProtocolValidationError(
            f"{context} status must have state 'completed' and stage 'terminal'"
        )

    # Validate test rounds
    rounds = result_data["test_rounds"]
    if not isinstance(rounds, list) or len(rounds) != 10:
        raise ProtocolValidationError(
            f"{context} test_rounds must contain exactly 10 rounds, observed {len(rounds) if isinstance(rounds, list) else 'invalid'}"
        )
    for round_idx, round_item in enumerate(rounds):
        if not isinstance(round_item, Mapping):
            raise ProtocolValidationError(f"{context} test round {round_idx} must be an object")
        for metric in SUMMARY_METRICS:
            val = round_item.get(metric)
            if val is None or not isinstance(val, (int, float)) or not math.isfinite(float(val)):
                raise ProtocolValidationError(
                    f"{context} test round {round_idx} metric '{metric}' must be a finite number"
                )

    # Validate harness summary
    harness_summary = result_data["harness_summary"]
    if not isinstance(harness_summary, Mapping):
        raise ProtocolValidationError(f"{context} harness_summary must be an object")
    for metric in SUMMARY_METRICS:
        metric_summary = harness_summary.get(metric)
        if (
            not isinstance(metric_summary, Mapping)
            or "mean" not in metric_summary
            or "std" not in metric_summary
        ):
            raise ProtocolValidationError(
                f"{context} harness_summary missing mean or std for '{metric}'"
            )
        mean_val = float(metric_summary["mean"])
        std_val = float(metric_summary["std"])
        if not math.isfinite(mean_val) or not math.isfinite(std_val):
            raise ProtocolValidationError(
                f"{context} harness_summary has non-finite values for '{metric}'"
            )

    # Validate environment
    env = result_data["environment"]
    if not isinstance(env, Mapping) or "conda_explicit_sha256" not in env:
        raise ProtocolValidationError(f"{context} environment must specify conda_explicit_sha256")
    require_sha256(
        env["conda_explicit_sha256"], field=f"{context} environment.conda_explicit_sha256"
    )

    return result_data


_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40,64}")


def _require_revision(value: object, *, field: str) -> str:
    result = require_string(value, field=field)
    if not _IMMUTABLE_REVISION.fullmatch(result):
        raise ProtocolValidationError(f"{field} must be a 40-64 character lowercase hex revision")
    return result


def validate_ledger_authorities(ledger_data: dict[str, Any]) -> dict[str, str]:
    """Validate runtime state ledger and extract authority identities."""
    if not isinstance(ledger_data, Mapping):
        raise ProtocolValidationError("ledger must be an object")
    if ledger_data.get("schema_version") != 1:
        raise ProtocolValidationError("ledger schema_version must be 1")

    authorities = ledger_data.get("authorities")
    if not isinstance(authorities, Mapping):
        raise ProtocolValidationError("ledger missing authorities section")

    harness_revision = _require_revision(
        authorities.get("harness_revision"), field="authorities.harness_revision"
    )
    preprocessing_revision = _require_revision(
        authorities.get("preprocessing_revision"), field="authorities.preprocessing_revision"
    )
    archived_model_revision = _require_revision(
        authorities.get("archived_model_revision"), field="authorities.archived_model_revision"
    )
    environment_sha256 = require_sha256(
        authorities.get("environment_sha256"), field="authorities.environment_sha256"
    )
    snapshot_subdirectory = require_string(
        authorities.get("snapshot_subdirectory"), field="authorities.snapshot_subdirectory"
    )

    return {
        "harness_revision": harness_revision,
        "preprocessing_revision": preprocessing_revision,
        "archived_model_revision": archived_model_revision,
        "environment_sha256": environment_sha256,
        "snapshot_subdirectory": snapshot_subdirectory,
    }


def audit_safedrug_table2(
    *,
    ledger_path: Path,
    result_paths: Mapping[str, Path],
    output_path: Path,
    reference_path: Path | None = None,
    data_root: Path | None = None,
) -> dict[str, Any]:
    """Audit four formal reproduction results against Table 2 and emit public-safe packet."""
    ref_path = (
        reference_path
        if reference_path is not None
        else Path("research/baselines/preflight/safedrug-table2-reference.json")
    )
    reference = load_table2_reference(ref_path)

    # Validate ledger
    try:
        raw_ledger = ledger_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ProtocolValidationError(f"failed to read ledger: {error}") from error
    ledger_obj = parse_json_object(raw_ledger, context="runtime ledger file")
    authorities = validate_ledger_authorities(ledger_obj)

    # Validate formal lanes in ledger if present
    formal_lanes = ledger_obj.get("formal_lanes")
    if formal_lanes is not None:
        if not isinstance(formal_lanes, Mapping):
            raise ProtocolValidationError("ledger formal_lanes must be an object")
        for baseline_id in REQUIRED_BASELINES:
            if baseline_id not in formal_lanes:
                raise ProtocolValidationError(
                    f"ledger formal_lanes missing baseline '{baseline_id}'"
                )
            lane = formal_lanes[baseline_id]
            if not isinstance(lane, Mapping):
                raise ProtocolValidationError(f"lane for '{baseline_id}' must be an object")
            if lane.get("state") != "completed":
                raise ProtocolValidationError(
                    f"lane for '{baseline_id}' is not completed (state: {lane.get('state')})"
                )
            terminal_id = lane.get("terminal_artifact_id")
            if not terminal_id:
                raise ProtocolValidationError(
                    f"lane for '{baseline_id}' missing terminal_artifact_id"
                )
            if data_root is not None:
                expected_path = (data_root / terminal_id).resolve()
                actual_path = result_paths[baseline_id].resolve()
                if expected_path != actual_path:
                    raise ProtocolValidationError(
                        f"formal result path mismatch for '{baseline_id}': expected {expected_path}, observed {actual_path}"
                    )

    # Ensure all four required baselines are provided
    missing_baselines = [b for b in REQUIRED_BASELINES if b not in result_paths]
    if missing_baselines:
        raise ProtocolValidationError(
            f"missing formal result path(s): {', '.join(missing_baselines)}"
        )

    validated_results: dict[str, dict[str, Any]] = {}
    for baseline_id in REQUIRED_BASELINES:
        path = result_paths[baseline_id]
        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError as error:
            raise ProtocolValidationError(
                f"failed to read result file for '{baseline_id}': {error}"
            ) from error
        parsed = parse_json_object(raw_text, context=f"result file for {baseline_id}")
        validated = validate_formal_result(
            parsed,
            expected_baseline_id=baseline_id,
            context=f"result for {baseline_id}",
        )
        # Check environment sha256 matches authorities
        observed_env = validated["environment"]["conda_explicit_sha256"]
        if observed_env != authorities["environment_sha256"]:
            raise ProtocolValidationError(
                f"result for '{baseline_id}' environment sha256 ({observed_env}) does not match ledger ({authorities['environment_sha256']})"
            )
        validated_results[baseline_id] = validated

    # Perform 20 interval checks
    interval_checks: list[dict[str, Any]] = []
    interval_pass_count = 0

    for baseline_id in REQUIRED_BASELINES:
        observed_summary = validated_results[baseline_id]["harness_summary"]
        ref_baseline = reference[baseline_id]
        for metric in SUMMARY_METRICS:
            t_mean = ref_baseline[metric]["mean"]
            t_std = ref_baseline[metric]["std"]
            lower_bound = t_mean - 2.0 * t_std
            upper_bound = t_mean + 2.0 * t_std
            o_mean = float(observed_summary[metric]["mean"])
            passed = lower_bound <= o_mean <= upper_bound
            if passed:
                interval_pass_count += 1
            interval_checks.append(
                {
                    "baseline_id": baseline_id,
                    "metric": metric,
                    "target_mean": t_mean,
                    "target_std": t_std,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "observed_mean": o_mean,
                    "passed": passed,
                }
            )

    # Perform 3 relationship checks
    # 1. SafeDrug Jaccard is greater than GAMENet Jaccard.
    # 2. SafeDrug F1 is greater than GAMENet F1.
    # 3. SafeDrug DDI rate is lower than LEAP DDI rate.
    safedrug_summary = validated_results["safedrug"]["harness_summary"]
    gamenet_summary = validated_results["gamenet"]["harness_summary"]
    leap_summary = validated_results["leap-safedrug"]["harness_summary"]

    rel1_op_a = float(safedrug_summary["jaccard"]["mean"])
    rel1_op_b = float(gamenet_summary["jaccard"]["mean"])
    rel1_passed = rel1_op_a > rel1_op_b

    rel2_op_a = float(safedrug_summary["avg_f1"]["mean"])
    rel2_op_b = float(gamenet_summary["avg_f1"]["mean"])
    rel2_passed = rel2_op_a > rel2_op_b

    rel3_op_a = float(safedrug_summary["ddi_rate"]["mean"])
    rel3_op_b = float(leap_summary["ddi_rate"]["mean"])
    rel3_passed = rel3_op_a < rel3_op_b

    relationship_checks = [
        {
            "relationship_id": 1,
            "description": "SafeDrug Jaccard is greater than GAMENet Jaccard",
            "operand_a_baseline": "safedrug",
            "operand_a_metric": "jaccard",
            "operand_a_value": rel1_op_a,
            "operand_b_baseline": "gamenet",
            "operand_b_metric": "jaccard",
            "operand_b_value": rel1_op_b,
            "passed": rel1_passed,
        },
        {
            "relationship_id": 2,
            "description": "SafeDrug F1 is greater than GAMENet F1",
            "operand_a_baseline": "safedrug",
            "operand_a_metric": "avg_f1",
            "operand_a_value": rel2_op_a,
            "operand_b_baseline": "gamenet",
            "operand_b_metric": "avg_f1",
            "operand_b_value": rel2_op_b,
            "passed": rel2_passed,
        },
        {
            "relationship_id": 3,
            "description": "SafeDrug DDI rate is lower than LEAP DDI rate",
            "operand_a_baseline": "safedrug",
            "operand_a_metric": "ddi_rate",
            "operand_a_value": rel3_op_a,
            "operand_b_baseline": "leap-safedrug",
            "operand_b_metric": "ddi_rate",
            "operand_b_value": rel3_op_b,
            "passed": rel3_passed,
        },
    ]
    relationship_pass_count = sum(1 for item in relationship_checks if item["passed"])

    all_intervals_passed = interval_pass_count == len(interval_checks)
    all_relationships_passed = relationship_pass_count == len(relationship_checks)
    verdict = (
        "completed_match"
        if (all_intervals_passed and all_relationships_passed)
        else "completed_mismatch"
    )

    packet = {
        "schema_version": 1,
        "kind": "safedrug_table2_audit",
        "verdict": verdict,
        "metadata": {
            "paper_reported_visits": 14995,
            "executable_visits": 15032,
            "difference": 37,
        },
        "interval_checks_passed": interval_pass_count,
        "interval_checks_total": len(interval_checks),
        "relationship_checks_passed": relationship_pass_count,
        "relationship_checks_total": len(relationship_checks),
        "authorities": authorities,
        "baselines_audited": list(REQUIRED_BASELINES),
        "checks": {
            "intervals": interval_checks,
            "relationships": relationship_checks,
        },
    }

    write_json_atomic(output_path, packet)
    return packet


__all__ = (
    "ARCHIVED_SOURCE_REVISION",
    "EXPECTED_DATASET_COUNTS",
    "REQUIRED_BASELINES",
    "SUMMARY_METRICS",
    "audit_safedrug_table2",
    "load_table2_reference",
    "validate_ledger_authorities",
)
