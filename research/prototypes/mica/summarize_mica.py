#!/usr/bin/env python3
"""Summarize the three-arm MICA attribution experiment."""

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
VARIANTS = {
    "shared_pool": "SharedPool",
    "drug_query": "DrugQuery",
    "late": "MICA-Late",
}
REQUIRED_METRICS = {
    "jaccard",
    "f1",
    "prauc",
    "precision",
    "recall",
    "ddi_rate",
    "mean_medication_count",
    "std_medication_count",
    "nll",
}


def _require_metrics(arm: dict[str, Any], key: str) -> dict[str, Any]:
    metrics = arm.get("selected_checkpoint", {}).get(key)
    if not isinstance(metrics, dict):
        raise ValueError(f"result is missing selected checkpoint {key} metrics")
    if not REQUIRED_METRICS.issubset(metrics):
        raise ValueError(f"selected checkpoint {key} metrics are incomplete")
    return metrics


def _validate_arm(arm: dict[str, Any], expected_variant: str) -> None:
    if arm.get("status") != "complete" or arm.get("variant") != expected_variant:
        raise ValueError("all MICA results must be complete and have the expected variants")
    revision = arm.get("source_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("result has no full immutable source revision")
    if arm.get("completed_epochs") != 60 or len(arm.get("progress", [])) != 60:
        raise ValueError("all arms must complete all 60 epochs")
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
    if not isinstance(arm.get("wall_time_seconds"), (int, float)):
        raise ValueError("result is missing wall time")
    if not isinstance(arm.get("cuda_peak_memory_mb"), (int, float)):
        raise ValueError("result is missing peak GPU memory")


def _delta_class(delta: float) -> str:
    magnitude = abs(delta)
    if magnitude <= 0.002:
        return "no_material_contribution"
    if magnitude <= 0.004:
        return "weak_contribution"
    if magnitude >= 0.010:
        return "strong_attribution_signal"
    return "meaningful_architecture_contribution"


def _row(arm: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_epoch": arm["selected_epoch"],
        "parameter_count": arm["parameter_count"],
        "Train": arm["selected_checkpoint"]["Train"],
        "Dev": arm["selected_checkpoint"]["Dev"],
        "epoch_60_Dev": arm["epoch_60"]["Dev"],
        "wall_time_seconds": arm["wall_time_seconds"],
        "cuda_peak_memory_mb": arm["cuda_peak_memory_mb"],
        "runtime": arm.get("runtime", {}),
    }


def summarize(
    shared_pool: dict[str, Any], drug_query: dict[str, Any], late: dict[str, Any]
) -> dict[str, Any]:
    _validate_arm(shared_pool, "shared_pool")
    _validate_arm(drug_query, "drug_query")
    _validate_arm(late, "late")
    arms = (shared_pool, drug_query, late)
    if len({arm["source_revision"] for arm in arms}) != 1:
        raise ValueError("matched arms differ in source_revision")
    if len({arm["parameter_count"] for arm in arms}) != 1:
        raise ValueError("matched arms differ in parameter_count")
    if len({json.dumps(arm["split"], sort_keys=True) for arm in arms}) != 1:
        raise ValueError("matched arms differ in split")
    if len({json.dumps(arm["config"], sort_keys=True) for arm in arms}) != 1:
        raise ValueError("matched arms have different scientific configurations")

    shared_dev = shared_pool["selected_checkpoint"]["Dev"]
    query_dev = drug_query["selected_checkpoint"]["Dev"]
    late_dev = late["selected_checkpoint"]["Dev"]
    delta_query = query_dev["jaccard"] - shared_dev["jaccard"]
    delta_film = late_dev["jaccard"] - query_dev["jaccard"]
    delta_late_shared = late_dev["jaccard"] - shared_dev["jaccard"]
    variant_names = tuple(VARIANTS.values())

    if delta_query > 0.004 and delta_film <= 0.002:
        conclusion = "PRESERVE_DRUGQUERY_AS_MICA_CORE_LATE_FILM_UNNECESSARY"
    elif abs(delta_query) <= 0.002 and abs(delta_late_shared) <= 0.002:
        conclusion = "SHAREDPOOL_WITHIN_002_OF_BOTH_NO_MATERIAL_MEDICATION_SPECIFIC_SELECTION"
    elif delta_film > 0.004:
        conclusion = "PRESERVE_MICA_LATE_PREPOOL_CONDITIONING"
    else:
        conclusion = "NO_SINGLE_COMPONENT_ATTRIBUTION_SIGNAL"

    return {
        "schema_version": 2,
        "status": "complete",
        "evidence_class": "exploratory_train_dev_single_seed",
        "source_revision": shared_pool["source_revision"],
        "seed": shared_pool["config"]["seed"],
        "decision": conclusion,
        "frozen_attribution_conclusion": conclusion,
        "deltas": {
            "delta_query": delta_query,
            "delta_query_class": _delta_class(delta_query),
            "delta_film": delta_film,
            "delta_film_class": _delta_class(delta_film),
            "delta_late_shared": delta_late_shared,
            "delta_late_shared_class": _delta_class(delta_late_shared),
        },
        "rows": {variant_names[index]: _row(arm) for index, arm in enumerate(arms)},
        "selected_epochs": {
            variant_names[index]: arm["selected_epoch"] for index, arm in enumerate(arms)
        },
        "split": shared_pool["split"],
        "matched_parameter_count": shared_pool["parameter_count"],
        "frozen_configuration": shared_pool["config"],
        "references": {
            "MoleRec": shared_pool["frozen_molerec_dev"],
            "GraphRefine-SameK": shared_pool["historical_graphrefine_samek"],
        },
        "held_out_evaluated": False,
        "novelty_verified": False,
        "idea_009_created": False,
        "formal_gate_opened": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shared-pool", type=Path, required=True)
    parser.add_argument("--drug-query", type=Path, required=True)
    parser.add_argument("--late", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(
        json.loads(args.shared_pool.read_text()),
        json.loads(args.drug_query.read_text()),
        json.loads(args.late.read_text()),
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
