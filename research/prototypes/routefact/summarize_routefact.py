#!/usr/bin/env python3
"""Validate and summarize the frozen RouteFact minus RouteAux comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

EXPECTED_SEED = 20260922
EXPECTED_EPOCHS = 60


def _load(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "complete":
        raise RuntimeError("result is not complete: " + str(path))
    if value.get("seed") != EXPECTED_SEED or value.get("completed_epochs") != EXPECTED_EPOCHS:
        raise RuntimeError("result does not satisfy frozen seed/epoch contract")
    if value.get("test_loaded") is not False:
        raise RuntimeError("Test access flag is not false")
    return value


def _metric(result: Dict[str, Any], key: str) -> float:
    return float(result["metrics"]["Dev"][key])


def run(args: argparse.Namespace) -> Dict[str, Any]:
    control = _load(args.route_aux)
    full = _load(args.route_fact)
    if control.get("variant") != "route_aux" or full.get("variant") != "route_fact":
        raise RuntimeError("comparison arms are mislabeled")
    shared_fields = (
        "profile_id",
        "source_revision",
        "seed",
        "parameter_count",
        "route_target_metadata_sha256",
    )
    for field in shared_fields:
        if control.get(field) != full.get(field):
            raise RuntimeError("matched-control field differs: " + field)
    if control["config"].get("route_count") != full["config"].get("route_count"):
        raise RuntimeError("route counts differ")

    delta_j = _metric(full, "jaccard") - _metric(control, "jaccard")
    delta_f1 = _metric(full, "f1") - _metric(control, "f1")
    delta_prauc = _metric(full, "prauc") - _metric(control, "prauc")
    delta_ddi = _metric(full, "ddi_rate") - _metric(control, "ddi_rate")
    delta_avgmed = _metric(full, "average_medication_count") - _metric(
        control, "average_medication_count"
    )

    if delta_j <= 0.002:
        decision = "KILL_ROUTEFACT_MECHANISM"
    elif delta_j <= 0.004:
        decision = "WEAK_ROUTEFACT_SIGNAL_STOP_NO_RESCUE"
    elif delta_f1 < -0.002 or delta_prauc < -0.002:
        decision = "INCONSISTENT_ROUTEFACT_SIGNAL_STOP"
    elif delta_j >= 0.008:
        decision = "STRONG_ROUTEFACT_SIGNAL_ADVANCE"
    else:
        decision = "MEANINGFUL_ROUTEFACT_SIGNAL_ADVANCE"

    result = {
        "schema_version": 1,
        "comparison": "route_fact_minus_route_aux",
        "profile_id": control["profile_id"],
        "source_revision": control["source_revision"],
        "seed": EXPECTED_SEED,
        "completed_epochs": EXPECTED_EPOCHS,
        "parameter_count_each_arm": control["parameter_count"],
        "route_target_metadata_sha256": control["route_target_metadata_sha256"],
        "route_aux": {
            "selected_epoch": control["selected_checkpoint"],
            "selected_threshold": control["selected_operating_point"],
            "metrics": control["metrics"]["Dev"],
        },
        "route_fact": {
            "selected_epoch": full["selected_checkpoint"],
            "selected_threshold": full["selected_operating_point"],
            "metrics": full["metrics"]["Dev"],
        },
        "deltas": {
            "jaccard": delta_j,
            "f1": delta_f1,
            "prauc": delta_prauc,
            "ddi_rate": delta_ddi,
            "average_medication_count": delta_avgmed,
        },
        "decision": decision,
        "decision_boundary": {
            "kill": "delta_j <= +0.002",
            "weak_stop": "+0.002 < delta_j <= +0.004",
            "advance": "delta_j > +0.004 with F1/PRAUC not worse by >0.002",
            "strong": "delta_j >= +0.008",
        },
        "safety_note": "DDI and cardinality are reported jointly; no safety override is predeclared for this non-safety mechanism screen.",
        "test_loaded": False,
    }
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route-aux", type=Path, required=True)
    parser.add_argument("--route-fact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main() -> None:
    print(json.dumps(run(parse_args()), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
