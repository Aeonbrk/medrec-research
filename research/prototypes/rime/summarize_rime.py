#!/usr/bin/env python3
"""Compare completed RIME and count-only aggregate result records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PRIMARY_METRICS = {
    "jaccard": "delta_jaccard",
    "f1": "delta_f1",
    "prauc": "delta_prauc",
    "ddi_rate": "delta_ddi_rate",
    "average_medication_count": "delta_avg_med",
}


def _read(path: Path, variant: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "complete" or value.get("variant") != variant:
        raise ValueError(f"{path} is not a complete {variant} RIME result")
    if value.get("source_bound_references", {}).get("test_accessed") is not False:
        raise ValueError(f"{path} does not prove that Test stayed sealed")
    return value


def summarize(composition_path: Path, control_path: Path) -> dict[str, Any]:
    composition = _read(composition_path, "composition")
    control = _read(control_path, "count_only")
    if composition.get("source_revision") != control.get("source_revision"):
        raise ValueError("composition and control source revisions differ")
    if composition.get("parameter_count") != control.get("parameter_count"):
        raise ValueError("composition and control parameter counts differ")
    if composition.get("config", {}).get("seed") != control.get("config", {}).get("seed"):
        raise ValueError("composition and control seeds differ")
    composition_metrics = composition["selected_checkpoint"]["Dev"]
    control_metrics = control["selected_checkpoint"]["Dev"]
    deltas = {
        output_name: float(composition_metrics[input_name] - control_metrics[input_name])
        for input_name, output_name in PRIMARY_METRICS.items()
    }
    accuracy_support = deltas["delta_f1"] >= -0.002 and deltas["delta_prauc"] >= -0.002
    pareto = (
        deltas["delta_jaccard"] > 0.0
        and deltas["delta_f1"] >= 0.0
        and deltas["delta_prauc"] >= 0.0
        and deltas["delta_ddi_rate"] <= 0.0
    )
    if deltas["delta_jaccard"] >= 0.004 and accuracy_support:
        decision = "SURVIVE_ACCURACY"
    elif pareto:
        decision = "SURVIVE_ACCURACY_SAFETY_PARETO"
    else:
        decision = "KILL_RIME_FORMULATION"
    return {
        "schema_version": 1,
        "status": "complete",
        "comparison": "composition_minus_count_only",
        "source_revision": composition["source_revision"],
        "parameter_count": composition["parameter_count"],
        "composition": {
            "selected_epoch": composition["selected_epoch"],
            "metrics": composition_metrics,
            "inference": composition["selected_inference"]["Dev"],
        },
        "count_only": {
            "selected_epoch": control["selected_epoch"],
            "metrics": control_metrics,
            "inference": control["selected_inference"]["Dev"],
        },
        "deltas": deltas,
        "supporting_metric_gate": {
            "f1_not_below_minus_0.002": deltas["delta_f1"] >= -0.002,
            "prauc_not_below_minus_0.002": deltas["delta_prauc"] >= -0.002,
            "accuracy_safety_pareto": pareto,
        },
        "decision": decision,
        "test_accessed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composition", type=Path, required=True)
    parser.add_argument("--count-only", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.composition, args.count_only)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
