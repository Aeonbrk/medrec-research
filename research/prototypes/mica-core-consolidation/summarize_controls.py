#!/usr/bin/env python3
"""Summarize the four public-safe Stage -1C control results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CONTROLS = ("core", "one_clinical_block", "no_post_read_conditioner", "simplified_head")


def _read(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("status") != "complete":
        raise ValueError(f"{path}: result is not complete")
    if result.get("completed_epochs") != 60 or len(result.get("progress", [])) != 60:
        raise ValueError(f"{path}: expected 60 complete epochs")
    return result


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    selected = result["selected_checkpoint"]["Dev"]
    final = result["epoch_60"]["Dev"]
    return {
        "control": result["control"],
        "recipe": result["recipe"],
        "source_revision": result["source_revision"],
        "parameter_count": result["parameter_count"],
        "selected_epoch": result["selected_epoch"],
        "best_dev": selected,
        "epoch_60_dev": final,
        "j_drop": selected["jaccard"] - final["jaccard"],
        "prauc_drop": selected["prauc"] - final["prauc"],
        "nll_drift": final["nll"] - selected["nll"],
        "clinical_attention_blocks": result["config"]["clinical_attention_blocks"],
        "head": (
            "linear_384_to_1_plus_medication_bias"
            if result["control"] == "simplified_head"
            else "current_mica_head"
        ),
    }


def _decision(rows: list[dict[str, Any]]) -> dict[str, Any]:
    core = next(row for row in rows if row["control"] == "core")
    candidates = [row for row in rows if row["control"] != "core"]
    eligible = []
    for row in candidates:
        row["simpler"] = row["parameter_count"] < core["parameter_count"]
        row["best_j_floor_pass"] = row["best_dev"]["jaccard"] >= core["best_dev"]["jaccard"] - 0.002
        row["best_prauc_floor_pass"] = row["best_dev"]["prauc"] >= core["best_dev"]["prauc"] - 0.002
        row["late_degradation_not_worse"] = (
            row["j_drop"] <= core["j_drop"]
            and row["prauc_drop"] <= core["prauc_drop"]
            and row["nll_drift"] <= core["nll_drift"]
        )
        row["meaningful_j_gain"] = row["best_dev"]["jaccard"] - core["best_dev"]["jaccard"] > 0.004
        if (
            row["simpler"]
            and row["best_j_floor_pass"]
            and row["best_prauc_floor_pass"]
            and row["late_degradation_not_worse"]
        ):
            eligible.append(row)
    if eligible:
        winner = max(
            eligible,
            key=lambda row: (row["best_dev"]["jaccard"], -row["parameter_count"]),
        )
        return {
            "decision": "ADOPT_SIMPLIFIED_MICA_CORE",
            "selected_control": winner["control"],
            "eligible_controls": [row["control"] for row in eligible],
            "rule": "fewer parameters, best J/PRAUC within 0.002 of Core, and no worse J/PRAUC drop or NLL drift",
        }
    return {
        "decision": "KEEP_EXISTING_MICA_CORE",
        "selected_control": "core",
        "eligible_controls": [],
        "rule": "no intrinsic simplification met the predeclared accuracy, simplicity, and late-stability rule",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result", action="append", nargs=2, metavar=("CONTROL", "PATH"), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    supplied = {control: Path(path) for control, path in args.result}
    if set(supplied) != set(CONTROLS):
        raise ValueError("exactly the four declared controls are required")
    rows = [_summary(_read(supplied[control])) for control in CONTROLS]
    payload = {
        "stage": "STAGE -1C",
        "status": "complete",
        "evidence_class": "aggregate_result_only",
        "controls": rows,
        "core_consolidation_result": _decision(rows),
        "source_result_files": {control: path.name for control, path in supplied.items()},
        "private_artifacts": "checkpoints, predictions, IDs, targets, and raw logs remain on 319",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
