#!/usr/bin/env python3
"""Summarize the 30-epoch final relational architecture search."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

HERE = Path(__file__).resolve().parent
PRIOR_RESULT = (
    HERE.parents[0]
    / "evidence-access-portfolio"
    / "result.json"
)

LANES = (
    "foundation_code",
    "summary_add",
    "summary_mul",
    "factorized_pair",
    "nonseparable_pair",
    "joint_competition_pair",
    "untyped_edge_pair",
    "temporal_edge_pair",
)

PAIRS: Dict[str, Tuple[str, str]] = {
    "summary_operator": ("summary_add", "summary_mul"),
    "pair_granularity": ("factorized_pair", "nonseparable_pair"),
    "relation_competition": ("nonseparable_pair", "joint_competition_pair"),
    "temporal_edge": ("untyped_edge_pair", "temporal_edge_pair"),
}


def _read(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lane(root: Path, name: str) -> Mapping[str, Any]:
    path = root / name / "results.json"
    if not path.is_file():
        raise RuntimeError("missing lane result: " + str(path))
    result = _read(path)
    if result.get("status") != "complete" or result.get("completed_epochs") != 30:
        raise RuntimeError("lane is not a complete 30-epoch run: " + name)
    if result.get("test_loaded") is not False:
        raise RuntimeError("Test boundary violated: " + name)
    return result


def _delta(
    candidate: Mapping[str, Any],
    control: Mapping[str, Any],
    key: str,
) -> float:
    return float(candidate[key]) - float(control[key])


def _guardrails(delta: Mapping[str, float]) -> bool:
    return (
        float(delta["f1"]) >= -0.002
        and float(delta["prauc"]) >= -0.002
        and float(delta["ddi_rate"]) <= 0.002
    )


def _mechanism_verdict(
    delta: Mapping[str, float],
    censored: bool,
) -> str:
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


def _pair(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> Dict[str, Any]:
    if control["parameter_count"] != candidate["parameter_count"]:
        raise RuntimeError("matched pair parameter count mismatch")
    c = control["metrics"]["Dev"]
    a = candidate["metrics"]["Dev"]
    delta = {
        "jaccard": _delta(a, c, "jaccard"),
        "f1": _delta(a, c, "f1"),
        "prauc": _delta(a, c, "prauc"),
        "ddi_rate": _delta(a, c, "ddi_rate"),
        "average_medication_count": _delta(
            a, c, "average_medication_count"
        ),
    }
    censored = bool(control["horizon_censored"] or candidate["horizon_censored"])
    return {
        "control": control["lane"],
        "candidate": candidate["lane"],
        "parameter_count": control["parameter_count"],
        "control_selected_checkpoint": control["selected_checkpoint"],
        "candidate_selected_checkpoint": candidate["selected_checkpoint"],
        "control_selected_operating_point": control["selected_operating_point"],
        "candidate_selected_operating_point": candidate["selected_operating_point"],
        "control_dev": c,
        "candidate_dev": a,
        "delta": delta,
        "guardrails_pass": _guardrails(delta),
        "horizon_censored": censored,
        "verdict": _mechanism_verdict(delta, censored),
    }


def _metric_diff(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    key: str,
) -> float:
    return abs(float(left[key]) - float(right[key]))


def run(root: Path) -> Dict[str, Any]:
    results = {name: _lane(root, name) for name in LANES}

    source_revisions = {str(value["source_revision"]) for value in results.values()}
    if len(source_revisions) != 1:
        raise RuntimeError("architecture lanes do not share one immutable revision")
    rngs = {
        json.dumps(value["config"]["rng"], sort_keys=True)
        for value in results.values()
    }
    if len(rngs) != 1:
        raise RuntimeError("architecture lanes do not share the canonical RNG")
    if results["foundation_code"]["horizon_censored"]:
        raise RuntimeError("foundation anchor is horizon-censored; runner validation failed")

    prior = _read(PRIOR_RESULT)
    prior_foundation = prior["pairs"]["resolution"]
    prior_dev = prior_foundation["candidate_dev"]
    foundation = results["foundation_code"]
    foundation_dev = foundation["metrics"]["Dev"]

    reproduction_diffs = {
        key: _metric_diff(foundation_dev, prior_dev, key)
        for key in (
            "jaccard",
            "f1",
            "prauc",
            "ddi_rate",
            "average_medication_count",
        )
    }
    reproduction_pass = (
        foundation["selected_checkpoint"]
        == prior_foundation["candidate_selected_checkpoint"]
        and abs(
            float(foundation["selected_operating_point"])
            - float(prior_foundation["candidate_selected_operating_point"])
        )
        <= 1e-12
        and max(reproduction_diffs.values()) <= 1e-9
    )
    if not reproduction_pass:
        raise RuntimeError(
            "30-epoch foundation anchor does not reproduce prior resolution_code"
        )

    pairs = {
        name: _pair(results[control], results[candidate])
        for name, (control, candidate) in PAIRS.items()
    }

    absolute: Dict[str, Any] = {}
    for name, result in results.items():
        dev = result["metrics"]["Dev"]
        absolute[name] = {
            "selected_checkpoint": result["selected_checkpoint"],
            "selected_operating_point": result["selected_operating_point"],
            "horizon_censored": result["horizon_censored"],
            "parameter_count": result["parameter_count"],
            "dev": dev,
            "delta_vs_foundation": {
                "jaccard": _delta(dev, foundation_dev, "jaccard"),
                "f1": _delta(dev, foundation_dev, "f1"),
                "prauc": _delta(dev, foundation_dev, "prauc"),
                "ddi_rate": _delta(dev, foundation_dev, "ddi_rate"),
                "average_medication_count": _delta(
                    dev, foundation_dev, "average_medication_count"
                ),
            },
        }

    relational_names = [name for name in LANES if name != "foundation_code"]
    interpretable = [
        name for name in relational_names if not results[name]["horizon_censored"]
    ]
    if interpretable:
        best = max(
            interpretable,
            key=lambda name: float(results[name]["metrics"]["Dev"]["jaccard"]),
        )
    else:
        best = None

    censored_pairs = [
        name for name, value in pairs.items() if value["horizon_censored"]
    ]
    clean_signals = [
        name
        for name, value in pairs.items()
        if value["verdict"] == "CLEAN_MECHANISM_SIGNAL"
    ]

    if censored_pairs:
        routing = "EXTEND_HORIZON_CENSORED_COMPARISONS_BEFORE_ARBITRATION"
    elif best is None:
        routing = "NO_INTERPRETABLE_RELATIONAL_VARIANT"
    else:
        best_gain = float(
            absolute[best]["delta_vs_foundation"]["jaccard"]
        )
        if not clean_signals and best_gain <= 0.002:
            routing = "RELATIONAL_REDESIGN_NO_COMPLETE_MODEL_GAIN"
        elif clean_signals:
            routing = "RELATIONAL_ARCHITECTURE_SURVIVOR_ARBITRATE_FOR_STABILITY"
        else:
            routing = "WEAK_RELATIONAL_ARCHITECTURE_STOP"

    return {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "source_revision": next(iter(source_revisions)),
        "profile_id": results["foundation_code"]["profile_id"],
        "training_horizon": {
            "epochs": 30,
            "safe_selected_epoch_max": 25,
            "censored_pairs": censored_pairs,
        },
        "foundation_reproduction": {
            "pass": reproduction_pass,
            "selected_checkpoint": foundation["selected_checkpoint"],
            "selected_operating_point": foundation["selected_operating_point"],
            "metric_abs_differences_vs_prior": reproduction_diffs,
        },
        "matched_mechanisms": pairs,
        "absolute_variants": absolute,
        "clean_mechanism_signals": clean_signals,
        "best_interpretable_relational_variant": best,
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
