#!/usr/bin/env python3
"""Summarize the 30-epoch MHEF normalization-domain architecture screen."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

HERE = Path(__file__).resolve().parent
PRIOR_RELATIONAL_RESULT = HERE.parents[0] / "final-relational-architecture" / "result.json"

LANES = (
    "mhef_independent_add",
    "coupled_budget_add",
    "wide_global_add",
    "mhef_independent_concat",
    "coupled_budget_concat",
    "private_only_add",
    "hash_partition_a_add",
    "hash_partition_b_add",
)

COMPARISONS: Dict[str, Tuple[str, str]] = {
    "normalization_add": ("coupled_budget_add", "mhef_indepent_add"),
    "normalization_concat": ("coupled_budget_concat", "mhef_independent_concat"),
    "capacity_wide_global": ("wide_global_add", "mhef_independent_add"),
    "global_complement": ("private_only_add", "mhef_independent_add"),
    "semantic_partition_a": ("hash_partition_a_add", "mhef_independent_add"),
    "semantic_partition_b": ("hash_partition_b_add", "mhef_independent_add"),
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


def run(root: Path) -> Dict[str, Any]:
    results = {name: _lane(root, name) for name in LANES}
    revisions = {str(value["source_revision"]) for value in results.values()}
    if len(revisions) != 1:
        raise RuntimeError("MHEF lanes do not share one immutable revision")
    rngs = {json.dumps(value["config"]["rng"], sort_keys=True) for value in results.values()}
    if len(rngs) != 1:
        raise RuntimeError("MHEF lanes do not share the canonical RNG")
    parameter_counts = {int(value["parameter_count"]) for value in results.values()}
    if len(parameter_counts) != 1:
        raise RuntimeError("MHEF lanes do not share one parameter budget")

    comparisons = {
        name: _comparison(results[control], results[candidate])
        for name, (control, candidate) in COMPARISONS.items()
    }
    censored = [name for name, value in comparisons.items() if value["horizon_censored"]]

    prior = _read(PRIOR_RELATIONAL_RESULT)
    prior_best = prior["best_completed_architecture"]
    prior_best_j = float(prior_best["dev_jaccard"])
    foundation_j = float(prior["foundation_reproduction"]["dev_metrics"]["jaccard"])

    candidate = results["mhef_independent_add"]
    candidate_dev = candidate["metrics"]["Dev"]
    candidate_j = float(candidate_dev["jaccard"])
    candidate_absolute = {
        "jaccard_vs_prior_summary_add": candidate_j - prior_best_j,
        "jaccard_vs_stable_foundation": candidate_j - foundation_j,
        "prior_summary_add_jaccard": prior_best_j,
        "stable_foundation_jaccard": foundation_j,
    }

    main = comparisons["normalization_add"]
    concat = comparisons["normalization_concat"]
    wide = comparisons["capacity_wide_global"]
    global_comp = comparisons["global_complement"]
    semantic_a = comparisons["semantic_partition_a"]
    semantic_b = comparisons["semantic_partition_b"]

    if censored:
        routing = "EXTEND_HORIZON_CENSORED_MHEF_LANES_UNCHANGED"
    elif main["verdict"] == "KILL_NO_MATERIAL_SIGNAL":
        routing = "KILL_MHEF_NORMALIZATION_HYPOTHESIS"
    elif main["verdict"] == "WEAK_STOP":
        routing = "WEAK_MHEF_NORMALIZATION_STOP"
    elif main["verdict"] != "CLEAN_MECHANISM_SIGNAL":
        routing = "MHEF_SIGNAL_WITH_SUPPORTING_METRIC_COST_STOP_NO_SAFETY_RESCUE"
    elif wide["delta"]["jaccard"] <= 0.002:
        routing = "KILL_ATTRIBUTION_WIDE_GLOBAL_ABSORBS_GAIN"
    elif concat["delta"]["jaccard"] <= 0.002 or not concat["guardrails_pass"]:
        routing = "HEAD_DEPENDENT_NORMALIZATION_SIGNAL_NO_STABILITY"
    elif (
        semantic_a["delta"]["jaccard"] <= 0.002
        or semantic_b["delta"]["jaccard"] <= 0.002
    ):
        routing = "GENERIC_PARTITION_SIGNAL_NOT_HETEROGENEOUS_VIEW_EVIDENCE"
    elif candidate_j < prior_best_j:
        routing = "MECHANISM_SURVIVES_BUT_COMPLETE_MODEL_BELOW_PRIOR_BEST"
    elif global_comp["delta"]["jaccard"] <= 0.002:
        routing = "SURVIVE_DROP_GLOBAL_PATH_BEFORE_STABILITY"
    else:
        routing = "PROMOTE_MHEF_COMPLETE_ARCHITECTURE_TO_MULTI_SEED_STABILITY"

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
        "common_parameter_count": next(iter(parameter_counts)),
        "matched_comparisons": comparisons,
        "rank1_absolute_position": candidate_absolute,
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
