#!/usr/bin/env python3
"""Summarize the frozen EBRA pair and apply the v1.4 horizon/routing rules."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "complete":
        raise RuntimeError(f"run is not complete: {path}")
    if value.get("test_loaded") is not False:
        raise RuntimeError(f"Test was loaded: {path}")
    if value.get("completed_epochs") not in (15, 30, 60):
        raise RuntimeError(f"unexpected completed epoch count: {path}")
    return value


def _metric(result: dict[str, Any], name: str) -> float:
    return float(result["metrics"]["Dev"][name])


def _route(delta: dict[str, float]) -> str:
    if delta["jaccard"] <= 0.002:
        return "KILL_SET_ASSIGNMENT_HYPOTHESIS"
    if delta["jaccard"] <= 0.004:
        return "WEAK_STOP"
    if delta["f1"] >= -0.002 and delta["prauc"] >= -0.002 and delta["ddi_rate"] <= 0.002:
        return "SURVIVE_TO_STABILITY"
    if (
        delta["ddi_rate"] <= -0.010
        and delta["jaccard"] >= -0.005
        and delta["f1"] >= -0.005
        and delta["prauc"] >= -0.005
    ):
        return "SURVIVE_TO_PARETO_REVIEW"
    return "SIGNAL_REVIEW_BEFORE_STABILITY"


def summarize(control: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    if control["profile_id"] != candidate["profile_id"]:
        raise RuntimeError("profile mismatch")
    if control["source_revision"] != candidate["source_revision"]:
        raise RuntimeError("source revision mismatch")
    if control["completed_epochs"] != candidate["completed_epochs"]:
        raise RuntimeError("matched arms did not run the same epoch budget")
    if control["parameter_count"] != candidate["parameter_count"]:
        raise RuntimeError("matched arms do not have equal parameter counts")

    names = ("jaccard", "f1", "prauc", "ddi_rate", "average_medication_count")
    metrics = {
        "fixed_multilabel": {name: _metric(control, name) for name in names},
        "ebra_assignment": {name: _metric(candidate, name) for name in names},
    }
    delta = {
        name: metrics["ebra_assignment"][name] - metrics["fixed_multilabel"][name] for name in names
    }
    selected_epochs = {
        "fixed_multilabel": int(control["selected_checkpoint"]),
        "ebra_assignment": int(candidate["selected_checkpoint"]),
    }
    max_selected = max(selected_epochs.values())
    total_epochs = int(control["completed_epochs"])
    if total_epochs == 15 and max_selected > 10:
        horizon_status = "HORIZON_CENSORED_15_TO_30"
        routing = None
        next_action = "EXTEND_EXACT_PAIR_UNCHANGED_TO_30"
    elif total_epochs == 30 and max_selected > 25:
        horizon_status = "HORIZON_CENSORED_30_TO_60"
        routing = None
        next_action = "EXTEND_EXACT_PAIR_UNCHANGED_TO_60"
    else:
        horizon_status = "INTERPRETABLE"
        routing = _route(delta)
        next_action = None

    return {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "profile_id": control["profile_id"],
        "source_revision": control["source_revision"],
        "snapshot_id": control["snapshot_id"],
        "train_dev_id": control["train_dev_id"],
        "arms": {
            "fixed_multilabel": {
                "parameter_count": control["parameter_count"],
                "completed_epochs": control["completed_epochs"],
                "selected_epoch": control["selected_checkpoint"],
                "selected_threshold": control["selected_operating_point"],
                "native_decode": False,
                "metrics": control["metrics"]["Dev"],
            },
            "ebra_assignment": {
                "parameter_count": candidate["parameter_count"],
                "completed_epochs": candidate["completed_epochs"],
                "selected_epoch": candidate["selected_checkpoint"],
                "selected_threshold": None,
                "native_decode": True,
                "metrics": candidate["metrics"]["Dev"],
            },
        },
        "dev_metrics": metrics,
        "delta_ebra_minus_fixed": delta,
        "selected_epochs": selected_epochs,
        "completed_epochs": total_epochs,
        "horizon_status": horizon_status,
        "routing": routing,
        "next_action": next_action,
        "test_loaded": False,
        "partial_curves_used_for_design": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed", type=Path, required=True)
    parser.add_argument("--ebra", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    result = summarize(_read(args.fixed), _read(args.ebra))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
