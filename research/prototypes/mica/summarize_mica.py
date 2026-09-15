#!/usr/bin/env python3
"""Apply the frozen MICA decision to two completed aggregate result files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize(early: dict, late: dict) -> dict:
    if early["variant"] != "early" or late["variant"] != "late":
        raise ValueError("expected one early and one late result")
    for field in ("source_revision", "parameter_count", "split"):
        if early[field] != late[field]:
            raise ValueError(f"matched arms differ in {field}")
    configs = [{k: v for k, v in arm["config"].items() if k != "variant"} for arm in (early, late)]
    if configs[0] != configs[1]:
        raise ValueError("matched arms have different scientific configurations")
    for arm in (early, late):
        if len(arm["progress"]) != 60 or arm["progress"][-1]["epoch"] != 60:
            raise ValueError("both arms must complete all 60 epochs")
    candidate = early["metrics"]["Dev"]
    control = late["metrics"]["Dev"]
    delta = candidate["jaccard"] - control["jaccard"]
    accuracy = (
        candidate["jaccard"] >= 0.543650
        and candidate["ddi_rate"] <= 0.075328
        and candidate["f1"] >= 0.687394
        and candidate["prauc"] >= 0.773576
    )
    safety = (
        candidate["jaccard"] >= 0.528650
        and candidate["ddi_rate"] <= 0.062223
        and candidate["f1"] >= 0.678480
        and candidate["prauc"] >= 0.768576
    )
    if delta <= 0.002:
        verdict = "KILL_MICA_MECHANISM"
    elif delta <= 0.004:
        verdict = "WEAK_MICA_MECHANISM"
    elif accuracy or safety:
        verdict = "SURVIVE_MICA_ARCHITECTURE_SCREEN"
    else:
        verdict = "KILL_MICA_PROJECT_HEADROOM"
    return {
        "source_revision": early["source_revision"],
        "seed": early["config"]["seed"],
        "status": "complete",
        "evidence_class": "exploratory_train_dev_single_seed",
        "decision": verdict,
        "mechanism_jaccard_delta": delta,
        "strong_mechanism_signal": delta >= 0.010,
        "project_accuracy_bar": accuracy,
        "project_safety_bar": safety,
        "rows": {
            "MICA-Early": candidate,
            "MICA-Late": control,
            "MoleRec": early["frozen_molerec_dev"],
            "GraphRefine-SameK-historical": early["historical_graphrefine_samek"],
        },
        "selected_epochs": {"early": early["selected_epoch"], "late": late["selected_epoch"]},
        "matched_parameter_count": early["parameter_count"],
        "split": early["split"],
        "held_out_evaluated": False,
        "novelty_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--early", type=Path, required=True)
    parser.add_argument("--late", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(json.loads(args.early.read_text()), json.loads(args.late.read_text()))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
