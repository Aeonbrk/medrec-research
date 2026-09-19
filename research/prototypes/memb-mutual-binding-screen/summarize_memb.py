#!/usr/bin/env python3
"""Summarize the Medication-Evidence Mutual Binding (MEMB) family screen."""
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
    "mutual_code",
    "scale2_code",
    "specificity_code",
    "foundation_code_anchor",
    "mutual_local",
    "scale2_local",
    "specificity_local",
    "prediction_local_anchor",
)

COMPARISONS: Dict[str, Tuple[str, str]] = {
    "code_commonness_scale2": ("scale2_code", "mutual_code"),
    "code_commonness_scale1": ("foundation_code_anchor", "specificity_code"),
    "local_commonness_scale2": ("scale2_local", "mutual_local"),
    "local_commonness_scale1": ("prediction_local_anchor", "specificity_local"),
    "code_sharpening": ("foundation_code_anchor", "scale2_code"),
    "local_sharpening": ("prediction_local_anchor", "scale2_local"),
}

PRIMARY_COMMONNESS = (
    "code_commonness_scale2",
    "code_commonness_scale1",
    "local_commonness_scale2",
    "local_commonness_scale1",
)


def _read(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lane(root: Path, name: str) -> Mapping[str, Any]:
    path = root / name / "results.json"
    if not path.is_file():
        raise RuntimeError("missing lane result: " + str(path))
    result = _read(path)
    if result.get("status") != "complete" or int(result.get("completed_epochs", 0)) not in {30, 60}:
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
    if int(control["parameter_count"]) != int(candidate["parameter_count"]):
        raise RuntimeError("matched comparison parameter count mismatch")
    if int(control["completed_epochs"]) != int(candidate["completed_epochs"]):
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
        "parameter_count": int(control["parameter_count"]),
        "completed_epochs": int(control["completed_epochs"]),
        "control_selected_checkpoint": int(control["selected_checkpoint"]),
        "candidate_selected_checkpoint": int(candidate["selected_checkpoint"]),
        "control_selected_operating_point": float(control["selected_operating_point"]),
        "candidate_selected_operating_point": float(candidate["selected_operating_point"]),
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


def _pareto_safety_signal(comparison: Mapping[str, Any]) -> bool:
    d = comparison["delta"]
    return (
        float(d["ddi_rate"]) <= -0.010
        and float(d["jaccard"]) >= -0.005
        and float(d["f1"]) >= -0.005
        and float(d["prauc"]) >= -0.005
    )


def run(root: Path) -> Dict[str, Any]:
    results = {name: _lane(root, name) for name in LANES}
    revisions = {str(value["source_revision"]) for value in results.values()}
    if len(revisions) != 1:
        raise RuntimeError("MEMB lanes do not share one immutable revision")
    rngs = {json.dumps(value["config"]["rng"], sort_keys=True) for value in results.values()}
    if len(rngs) != 1:
        raise RuntimeError("MEMB lanes do not share canonical RNG")
    counts = {int(value["parameter_count"]) for value in results.values()}
    if len(counts) != 1:
        raise RuntimeError("MEMB lanes do not share the exact PortfolioModel parameter budget")

    comparisons = {
        name: _comparison(results[control], results[candidate])
        for name, (control, candidate) in COMPARISONS.items()
    }

    portfolio = _read(PORTFOLIO_RESULT)
    expected_local = portfolio["pairs"]["prediction"]["candidate_dev"]
    expected_foundation = portfolio["pairs"]["resolution"]["candidate_dev"]
    local_anchor = results["prediction_local_anchor"]
    foundation_anchor = results["foundation_code_anchor"]
    local_diffs = _metric_abs_diffs(local_anchor["metrics"]["Dev"], expected_local)
    foundation_diffs = _metric_abs_diffs(foundation_anchor["metrics"]["Dev"], expected_foundation)
    anchor_reproduction = {
        "prediction_local": {
            "metric_abs_differences": local_diffs,
            "selected_checkpoint": int(local_anchor["selected_checkpoint"]),
            "expected_selected_checkpoint": int(
                portfolio["pairs"]["prediction"]["candidate_selected_checkpoint"]
            ),
            "selected_operating_point": float(local_anchor["selected_operating_point"]),
            "expected_selected_operating_point": float(
                portfolio["pairs"]["prediction"]["candidate_selected_operating_point"]
            ),
        },
        "foundation_code": {
            "metric_abs_differences": foundation_diffs,
            "selected_checkpoint": int(foundation_anchor["selected_checkpoint"]),
            "expected_selected_checkpoint": int(
                portfolio["pairs"]["resolution"]["candidate_selected_checkpoint"]
            ),
            "selected_operating_point": float(foundation_anchor["selected_operating_point"]),
            "expected_selected_operating_point": float(
                portfolio["pairs"]["resolution"]["candidate_selected_operating_point"]
            ),
        },
    }
    if (
        max(local_diffs.values()) > 1e-9
        or max(foundation_diffs.values()) > 1e-9
        or anchor_reproduction["prediction_local"]["selected_checkpoint"]
        != anchor_reproduction["prediction_local"]["expected_selected_checkpoint"]
        or abs(
            anchor_reproduction["prediction_local"]["selected_operating_point"]
            - anchor_reproduction["prediction_local"]["expected_selected_operating_point"]
        )
        > 1e-12
        or anchor_reproduction["foundation_code"]["selected_checkpoint"]
        != anchor_reproduction["foundation_code"]["expected_selected_checkpoint"]
        or abs(
            anchor_reproduction["foundation_code"]["selected_operating_point"]
            - anchor_reproduction["foundation_code"]["expected_selected_operating_point"]
        )
        > 1e-12
    ):
        raise RuntimeError("historical anchor reproduction failed")

    mhef = _read(MHEF_RESULT)
    relational = _read(RELATIONAL_RESULT)
    wide_global_j = float(
        mhef["matched_comparisons"]["capacity_wide_global"]["control_dev"]["jaccard"]
    )
    summary_add_j = float(relational["best_completed_architecture"]["dev_jaccard"])
    foundation_j = float(expected_foundation["jaccard"])
    prediction_local_j = float(expected_local["jaccard"])

    absolute = {}
    for lane in ("mutual_code", "specificity_code", "mutual_local", "specificity_local"):
        dev = results[lane]["metrics"]["Dev"]
        absolute[lane] = {
            "dev": dev,
            "jaccard_vs_wide_global_add": float(dev["jaccard"]) - wide_global_j,
            "jaccard_vs_summary_add": float(dev["jaccard"]) - summary_add_j,
            "jaccard_vs_foundation_code": float(dev["jaccard"]) - foundation_j,
            "jaccard_vs_prediction_local": float(dev["jaccard"]) - prediction_local_j,
        }

    censored = [name for name in PRIMARY_COMMONNESS if comparisons[name]["horizon_censored"]]
    code_clean = [
        name
        for name in ("code_commonness_scale1", "code_commonness_scale2")
        if comparisons[name]["verdict"] == "CLEAN_MECHANISM_SIGNAL"
    ]
    local_clean = [
        name
        for name in ("local_commonness_scale1", "local_commonness_scale2")
        if comparisons[name]["verdict"] == "CLEAN_MECHANISM_SIGNAL"
    ]
    local_pareto = [
        name
        for name in ("local_commonness_scale1", "local_commonness_scale2")
        if _pareto_safety_signal(comparisons[name])
    ]

    best_code_j = max(
        float(results["mutual_code"]["metrics"]["Dev"]["jaccard"]),
        float(results["specificity_code"]["metrics"]["Dev"]["jaccard"]),
    )
    best_local_j = max(
        float(results["mutual_local"]["metrics"]["Dev"]["jaccard"]),
        float(results["specificity_local"]["metrics"]["Dev"]["jaccard"]),
    )

    if censored:
        routing = "EXTEND_HORIZON_CENSORED_EXACT_MEMB_PAIRS_UNCHANGED"
    elif len(code_clean) == 2 and best_code_j > wide_global_j:
        routing = "PROMOTE_CROSS_SCALE_CODE_COMMONNESS_TO_STABILITY_REVIEW"
    elif len(local_clean) == 2 and best_local_j > wide_global_j:
        routing = "PROMOTE_CROSS_SCALE_LOCAL_COMMONNESS_TO_STABILITY_REVIEW"
    elif code_clean or local_clean:
        routing = "SCALE_SENSITIVE_COMPETITION_SIGNAL_REVIEW_BEFORE_ANY_STABILITY"
    elif local_pareto:
        routing = "LOCAL_ACCURACY_SAFETY_PARETO_SIGNAL_REVIEW_BEFORE_ANY_STABILITY"
    else:
        routing = "KILL_MEDICATION_EVIDENCE_COMPETITION_FAMILY"

    return {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "profile_id": results["mutual_code"]["profile_id"],
        "source_revision": next(iter(revisions)),
        "training_horizon": {
            "epochs": int(results["mutual_code"]["completed_epochs"]),
            "safe_selected_epoch_max": 25,
            "censored_primary_comparisons": censored,
        },
        "common_parameter_count": next(iter(counts)),
        "anchor_reproduction": anchor_reproduction,
        "matched_comparisons": comparisons,
        "absolute_position": {
            "wide_global_add_jaccard": wide_global_j,
            "summary_add_jaccard": summary_add_j,
            "foundation_code_jaccard": foundation_j,
            "prediction_local_jaccard": prediction_local_j,
            "candidates": absolute,
        },
        "clean_code_commonness_comparisons": code_clean,
        "clean_local_commonness_comparisons": local_clean,
        "local_pareto_comparisons": local_pareto,
        "routing": routing,
        "automatic_stability_authorized": False,
        "automatic_mimiciv_authorized": False,
        "automatic_test_authorized": False,
        "test_loaded": False,
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
