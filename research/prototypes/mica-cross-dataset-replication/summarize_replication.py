#!/usr/bin/env python3
# ruff: noqa: UP006,UP035,UP045
"""Summarize four private Stage -1F MICA arm results into public-safe JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

MIMIC_IV_CAP = 39_360
TERMINAL_IMPROVEMENT_THRESHOLD = 0.002
EXPECTED_ARMS = {
    "mimic_iii_shared_pool": ("mimic_iii", "shared_pool"),
    "mimic_iii_drug_query": ("mimic_iii", "drug_query"),
    "mimic_iv_shared_pool": ("mimic_iv", "shared_pool"),
    "mimic_iv_drug_query": ("mimic_iv", "drug_query"),
}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def _load(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("cannot load arm result: " + str(path)) from exc
    if not isinstance(value, dict) or value.get("status") != "complete":
        raise RuntimeError("arm result is not complete: " + str(path))
    if value.get("test_loaded") is not False:
        raise RuntimeError("arm result does not prove Test was untouched: " + str(path))
    return value


def _delta(query: Dict[str, Any], shared: Dict[str, Any]) -> Dict[str, float]:
    q = query["selected_checkpoint"]["Dev"]
    s = shared["selected_checkpoint"]["Dev"]
    return {
        "jaccard": float(q["jaccard"] - s["jaccard"]),
        "f1": float(q["f1"] - s["f1"]),
        "prauc": float(q["prauc"] - s["prauc"]),
        "nll": float(q["nll"] - s["nll"]),
        "ddi": float(q["ddi_rate"] - s["ddi_rate"]),
    }


def _budget_status(iv_query: Dict[str, Any], iv_shared: Dict[str, Any]) -> Dict[str, Any]:
    statuses = []
    for result in (iv_query, iv_shared):
        evaluations = result.get("evaluations", [])
        terminal = result.get("terminal", {})
        previous = evaluations[-2]["dev_metrics"]["jaccard"] if len(evaluations) >= 2 else None
        terminal_j = terminal.get("dev_metrics", {}).get("jaccard")
        statuses.append(
            {
                "selected_terminal": result.get("selected_update") == MIMIC_IV_CAP,
                "completed_cap": result.get("completed_updates") == MIMIC_IV_CAP,
                "previous_jaccard": previous,
                "terminal_jaccard": terminal_j,
                "terminal_improvement": (
                    float(terminal_j - previous)
                    if previous is not None and terminal_j is not None
                    else None
                ),
            }
        )
    inconclusive = any(
        status["selected_terminal"]
        and status["completed_cap"]
        and status["terminal_improvement"] is not None
        and status["terminal_improvement"] > TERMINAL_IMPROVEMENT_THRESHOLD
        for status in statuses
    )
    return {
        "threshold": TERMINAL_IMPROVEMENT_THRESHOLD,
        "arms": statuses,
        "inconclusive": inconclusive,
        "rule": "terminal selected and terminal Jaccard exceeds the preceding full evaluation by >0.002",
    }


def summarize(input_root: Path, output: Path, source_revision: Optional[str]) -> Dict[str, Any]:
    arm_results: Dict[str, Dict[str, Any]] = {}
    for name, (dataset, variant) in EXPECTED_ARMS.items():
        value = _load(input_root / name / "results.json")
        if value.get("dataset") != dataset or value.get("variant") != variant:
            raise RuntimeError("arm identity mismatch for " + name)
        if source_revision is not None and value.get("source_revision") != source_revision:
            raise RuntimeError("source revision mismatch for " + name)
        arm_results[name] = value
    revisions = {value.get("source_revision") for value in arm_results.values()}
    if len(revisions) != 1:
        raise RuntimeError("four arms are not bound to one source revision")
    for value in arm_results.values():
        config = value["config"]
        if (
            config.get("seed") != 20260914
            or config.get("learning_rate") != 1e-4
            or config.get("weight_decay") != 1e-4
            or config.get("batch_size_visits") != 16
            or config.get("decoder_threshold") != 0.35
        ):
            raise RuntimeError("arm configuration is not the frozen Stage -1F recipe")
    iii_shared = arm_results["mimic_iii_shared_pool"]
    iii_query = arm_results["mimic_iii_drug_query"]
    iv_shared = arm_results["mimic_iv_shared_pool"]
    iv_query = arm_results["mimic_iv_drug_query"]
    iii_delta = _delta(iii_query, iii_shared)
    iv_delta = _delta(iv_query, iv_shared)
    budget = _budget_status(iv_query, iv_shared)
    if budget["inconclusive"]:
        verdict = "MIMIC_IV_TRAINING_BUDGET_INCONCLUSIVE"
    elif iii_delta["jaccard"] > 0.004 and iv_delta["jaccard"] > 0.004:
        verdict = "MICA_MECHANISM_REPLICATED_BOTH_DATASETS"
    elif iv_delta["jaccard"] <= 0.0:
        verdict = "MICA_MECHANISM_NOT_REPLICATED_MIMIC_IV"
    else:
        verdict = "WEAK_CROSS_DATASET_REPLICATION"

    def public_arm(value: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "dataset": value["dataset"],
            "variant": value["variant"],
            "source_revision": value["source_revision"],
            "config": value["config"],
            "parameter_count": value["parameter_count"],
            "split": value["split"],
            "updates_per_epoch": value["updates_per_epoch"],
            "completed_updates": value["completed_updates"],
            "completed_epochs": value["completed_epochs"],
            "selected_update": value["selected_update"],
            "selected_epoch": value["selected_epoch"],
            "selected_epoch_equivalent": value["selected_epoch_equivalent"],
            "selected_checkpoint": value["selected_checkpoint"],
            "terminal": value["terminal"],
            "evaluations": value["evaluations"],
            "test_loaded": False,
        }

    result: Dict[str, Any] = {
        "schema_version": 1,
        "stage": "STAGE -1F",
        "status": "complete",
        "source_revision": next(iter(revisions)),
        "common_contract": {
            "seed": 20260914,
            "optimizer": "AdamW",
            "learning_rate": 1e-4,
            "weight_decay": 1e-4,
            "batch_size": 16,
            "threshold": 0.35,
            "mimic_iii_budget": "60 complete epochs",
            "mimic_iv_budget": "39,360 optimizer updates; full Dev evaluation every 3,280 updates",
            "checkpoint": "best complete Dev Jaccard, earliest exact tie",
            "test_loaded": False,
        },
        "arms": {name: public_arm(value) for name, value in arm_results.items()},
        "deltas": {"mimic_iii": iii_delta, "mimic_iv": iv_delta},
        "meaningful_threshold": 0.004,
        "strong_range": [0.008, 0.010],
        "mimic_iv_budget_status": budget,
        "mechanical_checks": {
            "four_complete_arms": True,
            "single_source_revision": True,
            "matched_seed_recipe": True,
            "mimic_iii_60_epoch_budget": all(
                value["dataset"] != "mimic_iii" or value["completed_epochs"] == 60
                for value in arm_results.values()
            ),
            "mimic_iv_exact_update_cap": all(
                value["dataset"] != "mimic_iv" or value["completed_updates"] == MIMIC_IV_CAP
                for value in arm_results.values()
            ),
            "test_loaded": False,
        },
        "verdict": verdict,
        "next_authorized_action": (
            "If budget is conclusive, review this Train/Dev mechanism result before any separately authorized screen; do not enter Stage 0 automatically."
        ),
    }
    _write_json(output, result)
    return result


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            summarize(args.input_root.resolve(), args.output.resolve(), args.source_revision),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
