#!/usr/bin/env python3
"""Apply the frozen MICA decision to two completed aggregate result files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

EXPECTED_SPLIT = {
    "train_patients": 4233,
    "dev_patients": 1004,
    "train_visits": 10489,
    "dev_visits": 2130,
}
EXPECTED_CONFIG = {
    "medications": 131,
    "hidden_dim": 128,
    "clinical_attention_blocks": 2,
    "heads": 4,
    "ffn_dim": 256,
    "batch_size_visits": 16,
    "epochs": 60,
    "seed": 20260914,
    "optimizer": "AdamW",
    "learning_rate": 3e-4,
    "weight_decay": 1e-4,
    "betas": [0.9, 0.999],
    "eps": 1e-8,
    "gradient_clip": 5.0,
    "decoder": "sigmoid probability >= 0.35",
    "decoder_threshold": 0.35,
    "loss": "BCE + 0.05 * normalized DDI penalty",
    "ddi_weight": 0.05,
}


def _require_metrics(arm: dict[str, Any], key: str) -> dict[str, Any]:
    metrics = arm.get("selected_checkpoint", {}).get(key)
    if not isinstance(metrics, dict):
        raise ValueError(f"result is missing selected checkpoint {key} metrics")
    required = {
        "jaccard",
        "f1",
        "prauc",
        "precision",
        "recall",
        "ddi_rate",
        "mean_medication_count",
        "std_medication_count",
    }
    if not required.issubset(metrics):
        raise ValueError(f"selected checkpoint {key} metrics are incomplete")
    return metrics


def _validate_arm(arm: dict[str, Any], expected_variant: str) -> None:
    if arm.get("status") != "complete" or arm.get("variant") != expected_variant:
        raise ValueError("both MICA results must be complete and have the expected variants")
    revision = arm.get("source_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("result has no full immutable source revision")
    if arm.get("completed_epochs") != 60 or len(arm.get("progress", [])) != 60:
        raise ValueError("both arms must complete all 60 epochs")
    if arm.get("selected_epoch") not in range(1, 61):
        raise ValueError("result has no selected checkpoint epoch")
    if arm.get("epoch_60", {}).get("Dev") != arm["progress"][-1].get("dev_metrics"):
        raise ValueError("epoch-60 Dev metrics are not bound to the final progress row")
    if arm.get("split") != EXPECTED_SPLIT:
        raise ValueError("result split does not match the canonical Train/Dev contract")
    if not isinstance(arm.get("parameter_count"), int) or arm["parameter_count"] <= 0:
        raise ValueError("result parameter count is missing or invalid")
    config = arm.get("config")
    if not isinstance(config, dict):
        raise ValueError("result is missing scientific configuration")
    for key, value in EXPECTED_CONFIG.items():
        if config.get(key) != value:
            raise ValueError(f"scientific configuration mismatch in {key}")
    numeric = config.get("numeric_policy")
    if not isinstance(numeric, dict) or numeric.get("dtype") != "float32":
        raise ValueError("result is missing the frozen float32 numeric policy")
    if (
        numeric.get("cuda_matmul_allow_tf32") is not False
        or numeric.get("cudnn_allow_tf32") is not False
    ):
        raise ValueError("result has a non-frozen TF32 policy")
    _require_metrics(arm, "Train")
    _require_metrics(arm, "Dev")
    if not isinstance(arm.get("epoch_60", {}).get("Dev"), dict):
        raise ValueError("result is missing epoch-60 Dev metrics")


def summarize(early: dict[str, Any], late: dict[str, Any]) -> dict[str, Any]:
    _validate_arm(early, "early")
    _validate_arm(late, "late")
    if early["source_revision"] != late["source_revision"]:
        raise ValueError("matched arms differ in source_revision")
    if early["parameter_count"] != late["parameter_count"]:
        raise ValueError("matched arms differ in parameter_count")
    if early["split"] != late["split"]:
        raise ValueError("matched arms differ in split")
    if early["config"] != late["config"]:
        raise ValueError("matched arms have different scientific configurations")
    candidate = early["selected_checkpoint"]["Dev"]
    control = late["selected_checkpoint"]["Dev"]
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
        "epoch_60_dev": {
            "early": early["epoch_60"]["Dev"],
            "late": late["epoch_60"]["Dev"],
        },
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
