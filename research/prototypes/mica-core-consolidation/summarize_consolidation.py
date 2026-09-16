#!/usr/bin/env python3
"""Summarize public-safe Stage -1B/-1C result JSON files.

The input files contain aggregate metrics only.  This script does not read
predictions, targets, patient identifiers, checkpoints, or raw logs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

RECIPES = ("t0_current_anchor", "t1_lower_constant", "t2_cosine_decay")
CONTROLS = ("core", "one_clinical_block", "no_post_read_conditioner", "simplified_head")


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "complete":
        raise ValueError(f"{path}: result is not complete")
    if payload.get("completed_epochs") != 60 or len(payload.get("progress", [])) != 60:
        raise ValueError(f"{path}: expected 60 complete epochs")
    return payload


def _recipe_summary(payload: dict[str, Any]) -> dict[str, Any]:
    config = payload["config"]
    progress = payload["progress"]
    selected = payload["selected_checkpoint"]["Dev"]
    final = payload["epoch_60"]["Dev"]
    best_j = float(selected["jaccard"])
    best_p = float(selected["prauc"])
    best_nll = float(selected["nll"])
    return {
        "recipe": payload["recipe"],
        "control": payload["control"],
        "source_revision": payload["source_revision"],
        "parameter_count": payload["parameter_count"],
        "selected_epoch": payload["selected_epoch"],
        "best_dev": selected,
        "epoch_60_dev": final,
        "j_drop": best_j - float(final["jaccard"]),
        "prauc_drop": best_p - float(final["prauc"]),
        "nll_drift": float(final["nll"]) - best_nll,
        "learning_rate_start": progress[0]["learning_rate"],
        "learning_rate_epoch_60": progress[-1]["learning_rate"],
        "schedule": config["schedule"],
        "config": {
            "seed": config["seed"],
            "batch_size_visits": config["batch_size_visits"],
            "weight_decay": config["weight_decay"],
            "epochs": config["epochs"],
            "optimizer": config["optimizer"],
            "clinical_attention_blocks": config["clinical_attention_blocks"],
        },
    }


def _recipe_decision(rows: list[dict[str, Any]]) -> dict[str, Any]:
    anchor = next(row for row in rows if row["recipe"] == "t0_current_anchor")
    candidates = [row for row in rows if row["recipe"] != "t0_current_anchor"]
    eligible = []
    for row in candidates:
        # The project rule supplies the peak-J floor and a non-material PRAUC
        # tolerance.  “Stable” is judged from the full trajectory, never from
        # epoch 60 alone: all three late-degradation indicators must improve.
        peak_ok = row["best_dev"]["jaccard"] >= anchor["best_dev"]["jaccard"] - 0.002
        prauc_ok = row["best_dev"]["prauc"] >= anchor["best_dev"]["prauc"] - 0.002
        degradation_reduced = (
            row["j_drop"] < anchor["j_drop"]
            and row["prauc_drop"] < anchor["prauc_drop"]
            and row["nll_drift"] < anchor["nll_drift"]
        )
        row["peak_j_floor_pass"] = peak_ok
        row["peak_prauc_floor_pass"] = prauc_ok
        row["late_degradation_reduced"] = degradation_reduced
        if peak_ok and prauc_ok and degradation_reduced:
            eligible.append(row)
    if eligible:
        # Prefer peak J; use smaller J/PRAUC degradation and NLL drift only as
        # deterministic tie-breakers. This prevents an epoch-60-only win.
        winner = max(
            eligible,
            key=lambda row: (
                row["best_dev"]["jaccard"],
                -row["j_drop"],
                -row["prauc_drop"],
                -row["nll_drift"],
            ),
        )
        return {
            "decision": "ADOPT_STABLE_RECIPE_FOR_STAGE_MINUS_1C",
            "selected_recipe": winner["recipe"],
            "anchor": anchor["recipe"],
            "eligible_recipes": [row["recipe"] for row in eligible],
            "rule": "peak J >= anchor - 0.002, peak PRAUC >= anchor - 0.002, and J/PRAUC drops plus NLL drift all lower than anchor",
        }
    return {
        "decision": "KEEP_CURRENT_RECIPE_WITH_EARLY_CHECKPOINTING",
        "selected_recipe": "t0_current_anchor",
        "anchor": anchor["recipe"],
        "eligible_recipes": [],
        "rule": "no lower/cosine recipe met the peak and full-trajectory stability rule",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--result", action="append", nargs=2, metavar=("RECIPE", "PATH"), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    supplied = {recipe: Path(path) for recipe, path in args.result}
    if set(supplied) != set(RECIPES):
        raise ValueError("exactly the three declared recipes are required")
    rows = [_recipe_summary(_read(supplied[recipe])) for recipe in RECIPES]
    summary = {
        "stage": "STAGE -1B",
        "status": "complete",
        "evidence_class": "aggregate_result_only",
        "recipes": rows,
        "training_recipe_decision": _recipe_decision(rows),
        "source_result_files": {recipe: path.name for recipe, path in supplied.items()},
        "private_artifacts": "checkpoints, predictions, IDs, targets, and raw logs remain on 319",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
