#!/usr/bin/env python3
"""Summarize the frozen 8-lane portfolio into four matched mechanism verdicts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping

from portfolio_model import PAIR_MAP, VARIANTS


def _read(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _delta(candidate: Mapping[str, Any], control: Mapping[str, Any], key: str) -> float:
    return float(candidate[key]) - float(control[key])


def _classify(delta_j: float, guardrails: bool) -> str:
    if delta_j <= 0.002:
        return "KILL_NO_MATERIAL_SIGNAL"
    if delta_j <= 0.004:
        return "WEAK_STOP"
    if guardrails:
        return "MECHANISM_SIGNAL"
    return "SIGNAL_WITH_SUPPORTING_METRIC_COST"


def run(root: Path) -> Dict[str, Any]:
    results: Dict[str, Mapping[str, Any]] = {}
    for variant in VARIANTS:
        path = root / variant / "results.json"
        if not path.is_file():
            raise RuntimeError("missing completed result: " + str(path))
        result = _read(path)
        if result.get("status") != "complete" or result.get("completed_epochs") != 60:
            raise RuntimeError("variant is not a complete 60-epoch run: " + variant)
        if result.get("test_loaded") is not False:
            raise RuntimeError("Test boundary violated: " + variant)
        results[variant] = result

    source_revisions = {str(value["source_revision"]) for value in results.values()}
    profiles = {str(value["profile_id"]) for value in results.values()}
    rngs = {json.dumps(value["config"]["rng"], sort_keys=True) for value in results.values()}
    if len(source_revisions) != 1 or len(profiles) != 1 or len(rngs) != 1:
        raise RuntimeError("portfolio lanes do not share one revision/profile/RNG convention")

    pairs: Dict[str, Any] = {}
    survivors = []
    for name, (control_name, candidate_name) in PAIR_MAP.items():
        control_result = results[control_name]
        candidate_result = results[candidate_name]
        if control_result["parameter_count"] != candidate_result["parameter_count"]:
            raise RuntimeError("matched pair parameter counts differ: " + name)
        control = control_result["metrics"]["Dev"]
        candidate = candidate_result["metrics"]["Dev"]
        delta_j = _delta(candidate, control, "jaccard")
        delta_f1 = _delta(candidate, control, "f1")
        delta_prauc = _delta(candidate, control, "prauc")
        delta_ddi = _delta(candidate, control, "ddi_rate")
        delta_count = _delta(candidate, control, "average_medication_count")
        guardrails = delta_f1 >= -0.002 and delta_prauc >= -0.002 and delta_ddi <= 0.002
        verdict = _classify(delta_j, guardrails)
        if verdict == "MECHANISM_SIGNAL":
            survivors.append(name)
        pairs[name] = {
            "control": control_name,
            "candidate": candidate_name,
            "parameter_count": control_result["parameter_count"],
            "control_selected_checkpoint": control_result["selected_checkpoint"],
            "candidate_selected_checkpoint": candidate_result["selected_checkpoint"],
            "control_selected_operating_point": control_result["selected_operating_point"],
            "candidate_selected_operating_point": candidate_result["selected_operating_point"],
            "control_dev": control,
            "candidate_dev": candidate,
            "delta": {
                "jaccard": delta_j,
                "f1": delta_f1,
                "prauc": delta_prauc,
                "ddi_rate": delta_ddi,
                "average_medication_count": delta_count,
            },
            "guardrails_pass": guardrails,
            "verdict": verdict,
        }

    if not survivors:
        routing = "NO_PORTFOLIO_SURVIVOR_STEP_BACK"
    elif len(survivors) == 1:
        routing = "ONE_SURVIVOR_FREEZE_AND_STABILITY"
    else:
        routing = "MULTIPLE_SURVIVORS_ARBITRATE_BEFORE_ANY_COMBINATION"

    return {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "source_revision": next(iter(source_revisions)),
        "profile_id": next(iter(profiles)),
        "rng": json.loads(next(iter(rngs))),
        "pairs": pairs,
        "survivors": survivors,
        "routing": routing,
        "test_loaded": False,
        "automatic_combination_authorized": False,
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
