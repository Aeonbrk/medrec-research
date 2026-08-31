"""Four-axis MoleRec Table 1 audit over finalized v2 reproduction artifacts."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

from .._validation import (
    parse_json_object,
    require_sha256,
    require_string,
    strict_fields,
    write_json_atomic,
)
from ..errors import ProtocolValidationError
from .reproduction_evidence import reopen_finalized_pair
from .safedrug_selection import require_selected_safedrug_lane

REQUIRED_MOLEREC_BASELINES = ("retain", "leap", "gamenet", "safedrug", "molerec")
SCIENTIFIC_IDENTITY_IDS = {
    "retain": "retain",
    "leap": "leap-safedrug",
    "gamenet": "gamenet",
    "safedrug": "safedrug",
    "molerec": "molerec",
}
REQUIRED_LANE_IDS = (
    "molerec-retain",
    "molerec-leap",
    "molerec-gamenet",
    "molerec-safedrug-lr-1e-5",
    "molerec-safedrug-lr-1e-4",
    "molerec-safedrug-lr-5e-4",
    "molerec-embedding",
)
SUMMARY_METRICS = (
    "ddi_rate",
    "jaccard",
    "avg_f1",
    "prauc",
    "avg_medications",
)
METRIC_ALIASES = {
    "ddi_rate": ("ddi_rate",),
    "jaccard": ("jaccard", "ja"),
    "avg_f1": ("avg_f1", "f1"),
    "prauc": ("prauc",),
    "avg_medications": ("avg_medications", "med"),
}
EXPECTED_DATASET_COUNTS = {
    "patients": 6_350,
    "visits": 15_032,
    "medications": 131,
    "ddi_pairs": 448,
    "molecular_substructures": 491,
}
IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40}")


def _number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ProtocolValidationError(f"{field} must be a finite number")
    return result


def _revision(value: object, *, field: str) -> str:
    result = require_string(value, field=field)
    if not IMMUTABLE_REVISION.fullmatch(result):
        raise ProtocolValidationError(f"{field} must be an immutable Git revision")
    return result


def load_molerec_table1_reference(
    reference_path: Path,
) -> dict[str, dict[str, dict[str, float]]]:
    """Load exact five-model/five-metric reference coverage."""
    try:
        parsed = parse_json_object(
            reference_path.read_text(encoding="utf-8"),
            context="MoleRec Table 1 reference",
        )
    except OSError as error:
        raise ProtocolValidationError(
            f"failed to read MoleRec Table 1 reference: {error}"
        ) from error
    root = strict_fields(
        parsed,
        required=("schema_version", "kind", "paper", "baselines"),
        context="MoleRec Table 1 reference",
    )
    if root["schema_version"] != 1 or root["kind"] != "molerec_table1_reference":
        raise ProtocolValidationError("invalid MoleRec Table 1 reference schema or kind")
    baselines = root["baselines"]
    if not isinstance(baselines, Mapping) or set(baselines) != set(REQUIRED_MOLEREC_BASELINES):
        raise ProtocolValidationError(
            "MoleRec Table 1 reference must contain exactly five baselines"
        )

    result: dict[str, dict[str, dict[str, float]]] = {}
    for baseline_id in REQUIRED_MOLEREC_BASELINES:
        metrics = baselines[baseline_id]
        if not isinstance(metrics, Mapping) or set(metrics) != set(SUMMARY_METRICS):
            raise ProtocolValidationError(
                f"reference baseline '{baseline_id}' must contain exactly five metrics"
            )
        parsed_metrics: dict[str, dict[str, float]] = {}
        for metric in SUMMARY_METRICS:
            target = strict_fields(
                metrics[metric],
                required=("mean", "std"),
                context=f"reference {baseline_id}.{metric}",
            )
            mean = _number(target["mean"], field=f"reference {baseline_id}.{metric}.mean")
            std = _number(target["std"], field=f"reference {baseline_id}.{metric}.std")
            if std < 0:
                raise ProtocolValidationError(
                    f"reference {baseline_id}.{metric}.std must be non-negative"
                )
            parsed_metrics[metric] = {"mean": mean, "std": std}
        result[baseline_id] = parsed_metrics
    return result


def _load_ledger(path: Path) -> dict[str, Any]:
    try:
        parsed = parse_json_object(
            path.read_text(encoding="utf-8"), context="MoleRec attempt ledger"
        )
    except OSError as error:
        raise ProtocolValidationError(f"failed to read MoleRec attempt ledger: {error}") from error
    root = strict_fields(
        parsed,
        required=(
            "schema_version",
            "kind",
            "attempt_id",
            "harness_revision",
            "preprocessing_revision",
            "snapshot_id",
            "environment_sha256",
            "test_lane_ids",
            "lanes",
        ),
        optional=("continuation_id",),
        context="MoleRec attempt ledger",
    )
    if root["schema_version"] != 2 or root["kind"] != "molerec_table1_attempt_ledger_v2":
        raise ProtocolValidationError("MoleRec attempt ledger must use schema_version 2")
    attempt_id = require_string(root["attempt_id"], field="ledger.attempt_id")
    harness_revision = _revision(root["harness_revision"], field="ledger.harness_revision")
    preprocessing_revision = _revision(
        root["preprocessing_revision"], field="ledger.preprocessing_revision"
    )
    snapshot_id = require_string(root["snapshot_id"], field="ledger.snapshot_id")
    environment_sha256 = require_sha256(
        root["environment_sha256"], field="ledger.environment_sha256"
    )

    test_lane_ids = root["test_lane_ids"]
    if not isinstance(test_lane_ids, Mapping) or set(test_lane_ids) != set(
        REQUIRED_MOLEREC_BASELINES
    ):
        raise ProtocolValidationError("ledger.test_lane_ids must map exactly five baselines")
    normalized_test_lane_ids = {
        baseline_id: require_string(
            test_lane_ids[baseline_id], field=f"ledger.test_lane_ids.{baseline_id}"
        )
        for baseline_id in REQUIRED_MOLEREC_BASELINES
    }
    if not set(normalized_test_lane_ids.values()).issubset(set(REQUIRED_LANE_IDS)):
        raise ProtocolValidationError("ledger.test_lane_ids contains an undeclared lane")

    lanes = root["lanes"]
    if not isinstance(lanes, Mapping) or set(lanes) != set(REQUIRED_LANE_IDS):
        raise ProtocolValidationError("ledger.lanes must contain exactly seven declared lanes")
    normalized_lanes: dict[str, dict[str, Any]] = {}
    for lane_id in REQUIRED_LANE_IDS:
        lane = strict_fields(
            lanes[lane_id],
            required=(
                "scientific_baseline_id",
                "program_id",
                "profile_id",
                "model_source_revision",
                "active_submission_id",
            ),
            optional=("state",),
            context=f"ledger lane {lane_id}",
        )
        normalized_lanes[lane_id] = {
            "scientific_baseline_id": require_string(
                lane["scientific_baseline_id"],
                field=f"ledger lane {lane_id}.scientific_baseline_id",
            ),
            "program_id": require_string(
                lane["program_id"], field=f"ledger lane {lane_id}.program_id"
            ),
            "profile_id": require_string(
                lane["profile_id"], field=f"ledger lane {lane_id}.profile_id"
            ),
            "model_source_revision": _revision(
                lane["model_source_revision"], field=f"ledger lane {lane_id}.model_source_revision"
            ),
            "active_submission_id": require_string(
                lane["active_submission_id"], field=f"ledger lane {lane_id}.active_submission_id"
            ),
            "state": lane.get("state"),
        }

    return {
        "attempt_id": attempt_id,
        "harness_revision": harness_revision,
        "preprocessing_revision": preprocessing_revision,
        "snapshot_id": snapshot_id,
        "environment_sha256": environment_sha256,
        "test_lane_ids": normalized_test_lane_ids,
        "lanes": normalized_lanes,
    }


def _identity_for(ledger: Mapping[str, Any], lane_id: str) -> dict[str, str]:
    lane = ledger["lanes"][lane_id]
    return {
        "attempt_id": ledger["attempt_id"],
        "lane_id": lane_id,
        "scientific_baseline_id": lane["scientific_baseline_id"],
        "program_id": lane["program_id"],
        "profile_id": lane["profile_id"],
        "harness_revision": ledger["harness_revision"],
        "model_source_revision": lane["model_source_revision"],
        "preprocessing_revision": ledger["preprocessing_revision"],
        "snapshot_id": ledger["snapshot_id"],
        "environment_sha256": ledger["environment_sha256"],
        "mode": "formal",
        "submission_id": lane["active_submission_id"],
    }


def _read_selection(path: Path | None, *, expected_lane_id: str) -> tuple[bool, str | None]:
    if path is None or not path.is_file():
        return False, "selection.json is missing"
    try:
        selection = parse_json_object(
            path.read_text(encoding="utf-8"), context="SafeDrug selection"
        )
        require_selected_safedrug_lane(selection, expected_lane_id)
    except (OSError, ProtocolValidationError) as error:
        return False, str(error)
    return True, None


def _metric_value(container: object, metric: str, *, field: str) -> float:
    if not isinstance(container, Mapping):
        raise ProtocolValidationError(f"{field} must be an object")
    for alias in METRIC_ALIASES[metric]:
        if alias in container:
            value = container[alias]
            if isinstance(value, Mapping):
                value = value.get("mean")
            return _number(value, field=f"{field}.{alias}")
    raise ProtocolValidationError(f"{field} is missing metric '{metric}'")


def _summary(result: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    raw_summary = result.get("harness_summary")
    if not isinstance(raw_summary, Mapping) or set(raw_summary) != set(SUMMARY_METRICS):
        raise ProtocolValidationError("result harness_summary must contain exactly five metrics")
    summary: dict[str, dict[str, float]] = {}
    for metric in SUMMARY_METRICS:
        target = strict_fields(
            raw_summary[metric],
            required=("mean", "std"),
            context=f"result harness_summary.{metric}",
        )
        mean = _number(target["mean"], field=f"result harness_summary.{metric}.mean")
        std = _number(target["std"], field=f"result harness_summary.{metric}.std")
        if std < 0:
            raise ProtocolValidationError(
                f"result harness_summary.{metric}.std must be non-negative"
            )
        summary[metric] = {"mean": mean, "std": std}
    return summary


def _rounds(result: Mapping[str, Any]) -> tuple[dict[str, float], ...]:
    raw_rounds = result.get("rounds")
    if not isinstance(raw_rounds, list) or len(raw_rounds) != 10:
        raise ProtocolValidationError("result must contain exactly ten aggregate rounds")
    normalized: list[dict[str, float]] = []
    for index, raw_round in enumerate(raw_rounds):
        metrics = raw_round.get("metrics", raw_round) if isinstance(raw_round, Mapping) else None
        normalized.append(
            {
                metric: _metric_value(metrics, metric, field=f"result.rounds[{index}]")
                for metric in SUMMARY_METRICS
            }
        )
    return tuple(normalized)


def _validate_result_artifact(result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    summary: dict[str, dict[str, float]] | None = None
    try:
        counts = result.get("dataset_counts")
        if counts != EXPECTED_DATASET_COUNTS:
            raise ProtocolValidationError(
                "dataset counts do not match the MoleRec executable contract"
            )
        if result.get("epochs_requested") != 50 or result.get("epochs_observed") != 50:
            raise ProtocolValidationError(
                "formal result must contain 50 requested and observed epochs"
            )
        checkpoint = result.get("checkpoint")
        if not isinstance(checkpoint, Mapping) or not checkpoint.get("sha256"):
            raise ProtocolValidationError("formal result is missing checkpoint identity")
        summary = _summary(result)
        rounds = _rounds(result)
        for metric in SUMMARY_METRICS:
            values = [row[metric] for row in rounds]
            computed_mean = fmean(values)
            computed_std = pstdev(values)
            declared = summary[metric]
            if not math.isclose(computed_mean, declared["mean"], rel_tol=1e-12, abs_tol=1e-12):
                raise ProtocolValidationError(f"{metric} mean disagrees with ten raw rounds")
            if not math.isclose(computed_std, declared["std"], rel_tol=1e-12, abs_tol=1e-12):
                raise ProtocolValidationError(
                    f"{metric} population std disagrees with ten raw rounds"
                )
    except ProtocolValidationError as error:
        errors.append(str(error))
    return {"summary": summary, "errors": errors}


def _interval_checks(
    reference: Mapping[str, Mapping[str, Mapping[str, float]]],
    summaries: Mapping[str, dict[str, dict[str, float]] | None],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for baseline_id in REQUIRED_MOLEREC_BASELINES:
        for metric in SUMMARY_METRICS:
            target = reference[baseline_id][metric]
            lower = target["mean"] - 2.0 * target["std"]
            upper = target["mean"] + 2.0 * target["std"]
            observed = summaries[baseline_id]
            observed_mean = observed[metric]["mean"] if observed is not None else None
            passed = observed_mean is not None and lower <= observed_mean <= upper
            checks.append(
                {
                    "baseline_id": baseline_id,
                    "metric": metric,
                    "target_mean": target["mean"],
                    "target_std": target["std"],
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "observed_mean": observed_mean,
                    "passed": passed,
                }
            )
    return checks


def _relationship_checks(
    summaries: Mapping[str, dict[str, dict[str, float]] | None],
) -> list[dict[str, Any]]:
    relationships = (
        ("molerec", "jaccard", ">", "safedrug", "MoleRec Jaccard is greater than SafeDrug Jaccard"),
        ("molerec", "avg_f1", ">", "safedrug", "MoleRec F1 is greater than SafeDrug F1"),
        ("molerec", "prauc", ">", "safedrug", "MoleRec PRAUC is greater than SafeDrug PRAUC"),
        (
            "molerec",
            "ddi_rate",
            "<",
            "safedrug",
            "MoleRec DDI rate is lower than SafeDrug DDI rate",
        ),
    )
    checks: list[dict[str, Any]] = []
    for index, (left_baseline, metric, operator, right_baseline, description) in enumerate(
        relationships, start=1
    ):
        left_summary = summaries[left_baseline]
        right_summary = summaries[right_baseline]
        left = left_summary[metric]["mean"] if left_summary is not None else None
        right = right_summary[metric]["mean"] if right_summary is not None else None
        passed = (
            left is not None
            and right is not None
            and (left > right if operator == ">" else left < right)
        )
        checks.append(
            {
                "relationship_id": index,
                "description": description,
                "operand_a_baseline": left_baseline,
                "operand_a_metric": metric,
                "operand_a_value": left,
                "operand_b_baseline": right_baseline,
                "operand_b_metric": metric,
                "operand_b_value": right,
                "operator": operator,
                "passed": passed,
            }
        )
    return checks


def audit_molerec_table1(
    *,
    ledger_path: Path,
    result_paths: Mapping[str, Path],
    output_path: Path,
    reference_path: Path | None = None,
    selection_path: Path | None = None,
    data_root: Path | None = None,
) -> dict[str, Any]:
    """Audit finalized five-model artifacts without treating direction as reproduction."""
    del data_root
    reference = load_molerec_table1_reference(
        reference_path or Path("research/baseline-preflight/molerec-table1-reference.json")
    )
    ledger = _load_ledger(ledger_path)
    result_lane_ids = ledger["test_lane_ids"]
    selection_valid, selection_error = _read_selection(
        selection_path,
        expected_lane_id=result_lane_ids["safedrug"],
    )

    execution_errors: list[str] = []
    artifact_errors: list[str] = []
    summaries: dict[str, dict[str, dict[str, float]] | None] = {}
    validated_results: dict[str, dict[str, Any]] = {}
    for baseline_id in REQUIRED_MOLEREC_BASELINES:
        lane_id = result_lane_ids[baseline_id]
        expected_identity = _identity_for(ledger, lane_id)
        result_path = result_paths.get(baseline_id)
        if result_path is None:
            execution_errors.append(f"missing result path for {baseline_id}")
            artifact_errors.append(f"missing result path for {baseline_id}")
            summaries[baseline_id] = None
            continue
        try:
            status, result = reopen_finalized_pair(
                result_path.parent,
                expected_identity=expected_identity,
            )
            if status["state"] != "completed" or result.get("state") != "completed":
                raise ProtocolValidationError(f"{baseline_id} result pair is not completed")
            if result["identity"]["scientific_baseline_id"] != SCIENTIFIC_IDENTITY_IDS[baseline_id]:
                raise ProtocolValidationError(
                    f"{baseline_id} result has the wrong scientific baseline"
                )
            validated_results[baseline_id] = result
        except (OSError, ProtocolValidationError) as error:
            execution_errors.append(f"{baseline_id}: {error}")
            artifact_errors.append(f"{baseline_id}: {error}")
            summaries[baseline_id] = None
            continue

        artifact = _validate_result_artifact(validated_results[baseline_id])
        if artifact["errors"]:
            artifact_errors.extend(f"{baseline_id}: {error}" for error in artifact["errors"])
        summaries[baseline_id] = artifact["summary"]

    if not selection_valid:
        artifact_errors.append(selection_error or "selection.json is invalid")
    interval_checks = _interval_checks(reference, summaries)
    relationship_checks = _relationship_checks(summaries)
    interval_passed = sum(1 for check in interval_checks if check["passed"])
    relationship_passed = sum(1 for check in relationship_checks if check["passed"])
    execution_passed = not execution_errors
    artifact_passed = not artifact_errors and selection_valid
    point_passed = interval_passed == len(interval_checks) and artifact_passed
    direction_passed = relationship_passed == len(relationship_checks) and artifact_passed
    axes = {
        "execution_integrity": {
            "passed": execution_passed,
            "errors": execution_errors,
        },
        "paper_point_fidelity": {
            "passed": point_passed,
            "checks_passed": interval_passed,
            "checks_total": len(interval_checks),
        },
        "directional_relationships": {
            "passed": direction_passed,
            "checks_passed": relationship_passed,
            "checks_total": len(relationship_checks),
        },
        "artifact_completeness": {
            "passed": artifact_passed,
            "errors": artifact_errors,
        },
    }

    if not execution_passed or not artifact_passed:
        verdict = "selection_incomplete" if not selection_valid else "formal_incomplete"
    elif point_passed and direction_passed:
        verdict = "completed_match"
    else:
        verdict = "completed_mismatch"

    packet = {
        "schema_version": 2,
        "kind": "molerec_table1_audit_v2",
        "verdict": verdict,
        "metadata": {
            "paper_reported_visits": 14_995,
            "executable_visits": 15_032,
            "difference": 37,
        },
        "baselines_audited": list(REQUIRED_MOLEREC_BASELINES),
        "selection": {
            "valid": selection_valid,
            "selected_lane_id": result_lane_ids["safedrug"] if selection_valid else None,
            "error": selection_error,
        },
        "authorities": {
            "attempt_id": ledger["attempt_id"],
            "harness_revision": ledger["harness_revision"],
            "preprocessing_revision": ledger["preprocessing_revision"],
            "snapshot_id": ledger["snapshot_id"],
            "environment_sha256": ledger["environment_sha256"],
            "test_lane_ids": result_lane_ids,
        },
        "axes": axes,
        "interval_checks_passed": interval_passed,
        "interval_checks_total": len(interval_checks),
        "relationship_checks_passed": relationship_passed,
        "relationship_checks_total": len(relationship_checks),
        "checks": {
            "intervals": interval_checks,
            "relationships": relationship_checks,
        },
    }
    write_json_atomic(output_path, packet)
    return packet


__all__ = (
    "EXPECTED_DATASET_COUNTS",
    "REQUIRED_LANE_IDS",
    "REQUIRED_MOLEREC_BASELINES",
    "SUMMARY_METRICS",
    "audit_molerec_table1",
    "load_molerec_table1_reference",
)
