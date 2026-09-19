#!/usr/bin/env python3
"""Summarize the MSED evidence-distribution architecture screen."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

HERE = Path(__file__).resolve().parent
PORTFOLIO_RESULT = HERE.parents[0] / "evidence-access-portfolio" / "result.json"
MHEF_RESULT = HERE.parents[0] / "mhef-normalization-screen" / "result.json"
RELATIONAL_RESULT = HERE.parents[0] / "final-relational-architecture" / "result.json"

LANES = (
    "msed_ecf_global",
    "point_lme_global",
    "point_mean_global",
    "point_max_global",
    "msed_ecf_only",
    "point_lme_only",
    "prediction_local_anchor",
    "foundation_code_anchor",
)

MATCHED_MSED = (
    "msed_ecf_global",
    "point_lme_global",
    "point_mean_global",
    "point_max_global",
    "msed_ecf_only",
    "point_lme_only",
)

COMPARISONS: Dict[str, Tuple[str, str]] = {
    "distribution_beyond_lme_global": ("point_lme_global", "msed_ecf_global"),
    "distribution_vs_mean_global": ("point_mean_global", "msed_ecf_global"),
    "distribution_vs_max_global": ("point_max_global", "msed_ecf_global"),
    "distribution_beyond_lme_only": ("point_lme_only", "msed_ecf_only"),
    "global_complement": ("msed_ecf_only", "msed_ecf_global"),
}


def _read(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lane(root: Path, name: str) -> Mapping[str, Any]:
    path = root / name / "results.json"
    if not path.is_file():
        raise RuntimeError("missing lane result: " + str(path))
    result = _read(path)
    if result.get("status") != "complete" or result.get("completed_epochs") not in {30, 60}:
        raise RuntimeError("lane is not a complete frozen-horizon run: " + name)
    if result.get("test_loaded") is not False:
        raise RuntimeError("Test boundary violated: " + name)
    return result


def _delta(candidate: Mapping[str, Any], control: Mapping[str, Any], key: str) -> float:
    return float(candidate[key]) - float(control[key])


def _guardrails(delta: Mapping[str, float]) -> bool:
    return (
        float(delta["f1"]) >= -0.002
        and float(delta["prauc"]) >= -0.002
        and float(delta["ddi_rate"]) <= 0.002
    )


def _verdict(delta: Mapping[str, float], censored: bool) -> str:
    if censored:
        return "HORIZON_CENSORED"
    j = float(delta["jaccard"])
    if j <= 0.002:
        return "KILL_NO_MATERIAL_SIGNAL"
    if j <= 0.004:
        return "WEAK_STOP"
    if _guardrails(delta):
        return "CLEAN_MECHANISM_SIGNAL"
    return "SIGNAL_WITH_SUPPORTING_METRIC_COST"


def _comparison(control: Mapping[str, Any], candidate: Mapping[str, Any]) -> Dict[str, Any]:
    if control["parameter_count"] != candidate["parameter_count"]:
        raise RuntimeError("matched comparison parameter count mismatch")
    if control["completed_epochs"] != candidate["completed_epochs"]:
        raise RuntimeError("matched comparison training horizon mismatch")
    c = control["metrics"]["Dev"]
    a = candidate["metrics"]["Dev"]
    delta = {
        "jaccard": _delta(a, c, "jaccard"),
        "f1": _delta(a, c, "f1"),
        "prauc": _delta(a, c, "prauc"),
        "ddi_rate": _delta(a, c, "ddi_rate"),
        "average_medication_count": _delta(a, c, "average_medication_count"),
    }
    censored = bool(control["horizon_censored"] or candidate["horizon_censored"])
    return {
        "control": control["lane"],
        "candidate": candidate["lane"],
        "parameter_count": control["parameter_count"],
        "completed_epochs": control["completed_epochs"],
        "control_selected_checkpoint": control["selected_checkpoint"],
        "candidate_selected_checkpoint": candidate["selected_checkpoint"],
        "control_selected_operating_point": control["selected_operating_point"],
        "candidate_selected_operating_point": candidate["selected_operating_point"],
        "control_dev": c,
        "candidate_dev": a,
        "delta": delta,
        "guardrails_pass": _guardrails(delta),
        "horizon_censored": censored,
        "verdict": _verdict(delta, censored),
    }


def _metric_abs_diffs(left: Mapping[str, Any], right: Mapping[str, Any]) -> Dict[str, float]:
    keys = ("jaccard", "f1", "prauc", "ddi_rate", "average_medication_count")
    return {key: abs(float(left[key]) - float(right[key])) for key in keys}


def run(root: Path) -> Dict[str, Any]:
    results = {name: _lane(root, name) for name in LANES}
    revisions = {str(value["source_revision"]) for value in results.values()}
    if len(revisions) != 1:
        raise RuntimeError("MSED lanes do not share one immutable revision")
    rngs = {json.dumps(value["config"]["rng"], sort_keys=True) for value in results.values()}
    if len(rngs) != 1:
        raise RuntimeError("MSED lanes do not share canonical RNG")

    matched_counts = {int(results[name]["parameter_count"]) for name in MATCHED_MSED}
    if len(matched_counts) != 1:
        raise RuntimeError("matched MSED variants do not share one parameter budget")

    comparisons = {
        name: _comparison(results[control], results[candidate])
        for name, (control, candidate) in COMPARISONS.items()
    }
    censored = [name for name, value in comparisons.items() if value["horizon_censored"]]

    # Reproduce the two historical structural anchors exactly under the same canonical RNG.
    portfolio = _read(PORTFOLIO_RESULT)
    historical_local = portfolio["pairs"]["prediction"]["candidate_dev"]
    historical_foundation = portfolio["pairs"]["resolution"]["candidate_dev"]
    local_anchor = results["prediction_local_anchor"]
    foundation_anchor = results["foundation_code_anchor"]
    local_diffs = _metric_abs_diffs(local_anchor["metrics"]["Dev"], historical_local)
    foundation_diffs = _metric_abs_diffs(foundation_anchor["metrics"]["Dev"], historical_foundation)
    anchor_reproduction = {
        "prediction_local": {
            "metric_abs_differences": local_diffs,
            "selected_checkpoint": local_anchor["selected_checkpoint"],
            "expected_selected_checkpoint": portfolio["pairs"]["prediction"]["candidate_selected_checkpoint"],
            "selected_operating_point": local_anchor["selected_operating_point"],
            "expected_selected_operating_point": portfolio["pairs"]["prediction"]["candidate_selected_operating_point"],
        },
        "foundation_code": {
            "metric_abs_differences": foundation_diffs,
            "selected_checkpoint": foundation_anchor["selected_checkpoint"],
            "expected_selected_checkpoint": portfolio["pairs"]["resolution"]["candidate_selected_checkpoint"],
            "selected_operating_point": foundation_anchor["selected_operating_point"],
            "expected_selected_operating_point": portfolio["pairs"]["resolution"]["candidate_selected_operating_point"],
        },
    }
    if (
        max(local_diffs.values()) > 1e-9
        or max(foundation_diffs.values()) > 1e-9
        or local_anchor["selected_checkpoint"]
        != portfolio["pairs"]["prediction"]["candidate_selected_checkpoint"]
        or foundation_anchor["selected_checkpoint"]
        != portfolio["pairs"]["resolution"]["candidate_selected_checkpoint"]
        or abs(
            float(local_anchor["selected_operating_point"])
            - float(portfolio["pairs"]["prediction"]["candidate_selected_operating_point"])
        )
        > 1e-12
        or abs(
            float(foundation_anchor["selected_operating_point"])
            - float(portfolio["pairs"]["resolution"]["candidate_selected_operating_point"])
        )
        > 1e-12
    ):
        raise RuntimeError("historical MSED anchor reproduction failed")

    mhef = _read(MHEF_RESULT)
    relational = _read(RELATIONAL_RESULT)
    wide_global_j = float(
        mhef["matched_comparisons"]["capacity_wide_global"]["control_dev"]["jaccard"]
    )
    summary_add_j = float(relational["best_completed_architecture"]["dev_jaccard"])
    prediction_local_j = float(historical_local["jaccard"])
    foundation_j = float(historical_foundation["jaccard"])

    candidate = results["msed_ecf_global"]
    candidate_dev = candidate["metrics"]["Dev"]
    candidate_j = float(candidate_dev["jaccard"])
    absolute = {
        "candidate_dev": candidate_dev,
        "jaccard_vs_wide_global_add": candidate_j - wide_global_j,
        "jaccard_vs_summary_add": candidate_j - summary_add_j,
        "jaccard_vs_prediction_local_anchor": candidate_j - prediction_local_j,
        "jaccard_vs_foundation_code_anchor": candidate_j - foundation_j,
        "wide_global_add_jaccard": wide_global_j,
        "summary_add_jaccard": summary_add_j,
        "prediction_local_jaccard": prediction_local_j,
        "foundation_code_jaccard": foundation_j,
    }

    primary = comparisons["distribution_beyond_lme_global"]
    only = comparisons["distribution_beyond_lme_only"]
    global_complement = comparisons["global_complement"]

    if censored:
        routing = "EXTEND_HORIZON_CENSORED_MSED_COMPARISONS_UNCHANGED"
    elif primary["verdict"] == "KILL_NO_MATERIAL_SIGNAL":
        routing = "KILL_MSED_DISTRIBUTION_SHAPE_HYPOTHESIS"
    elif primary["verdict"] == "WEAK_STOP":
        routing = "WEAK_MSED_DISTRIBUTION_SHAPE_STOP"
    elif primary["verdict"] != "CLEAN_MECHANISM_SIGNAL":
        routing = "MSED_SIGNAL_WITH_SUPPORTING_METRIC_COST_STOP_NO_SAFETY_RESCUE"
    elif float(only["delta"]["jaccard"]) <= 0.002 or not only["guardrails_pass"]:
        routing = "GLOBAL_BRANCH_DEPENDENT_DISTRIBUTION_SIGNAL_NO_STABILITY"
    elif candidate_j <= wide_global_j:
        routing = "MECHANISM_SURVIVES_BUT_COMPLETE_MODEL_NOT_ABOVE_STRONG_CAPACITY_CONTROL"
    elif float(global_complement["delta"]["jaccard"]) <= 0.002:
        routing = "SURVIVE_DROP_GLOBAL_PATH_BEFORE_STABILITY"
    else:
        routing = "PROMOTE_MSED_COMPLETE_ARCHITECTURE_TO_MULTI_SEED_STABILITY_REVIEW"

    return {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "source_revision": next(iter(revisions)),
        "profile_id": candidate["profile_id"],
        "training_horizon": {
            "epochs": 30,
            "safe_selected_epoch_max": 25,
            "censored_comparisons": censored,
        },
        "matched_msed_parameter_count": next(iter(matched_counts)),
        "anchor_reproduction": anchor_reproduction,
        "matched_comparisons": comparisons,
        "rank1_absolute_position": absolute,
        "routing": routing,
        "test_loaded": False,
        "automatic_stability_authorized": False,
        "automatic_test_authorized": False,
        "automatic_mimiciv_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.root.resolve())
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
