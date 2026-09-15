#!/usr/bin/env python3
"""Validate and summarize the six bounded MICA dynamic-query lanes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VARIANTS = (
    "core",
    "static_multiquery",
    "global_dynamic_multiquery",
    "evidence_dynamic_multiquery",
    "static_query_adapter",
    "dynamic_query_adapter",
)


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if data.get("status") != "complete" or data.get("completed_epochs") != 60:
        raise RuntimeError(str(path) + " is not a complete 60-epoch result")
    return data


def _metrics(result: dict[str, Any]) -> dict[str, float]:
    return {key: float(value) for key, value in result["metrics"]["Dev"].items()}


def _common_config(result: dict[str, Any]) -> dict[str, Any]:
    config = dict(result["config"])
    config.pop("variant", None)
    config.pop("mechanism", None)
    config.pop("dynamic_query_screen", None)
    return config


def _classify(delta: float) -> str:
    if delta <= 0.002:
        return "no_material_contribution"
    if delta <= 0.004:
        return "weak"
    if delta < 0.008:
        return "meaningful"
    return "strong"


def _survives(dynamic: dict[str, float], control: dict[str, float], core: dict[str, float]) -> bool:
    return (
        dynamic["jaccard"] - control["jaccard"] > 0.004
        and dynamic["jaccard"] >= core["jaccard"]
        and dynamic["f1"] >= core["f1"] - 0.002
        and dynamic["prauc"] >= core["prauc"] - 0.002
        and dynamic["ddi_rate"] <= core["ddi_rate"] + 0.002
    )


def summarize(paths: list[Path]) -> dict[str, Any]:
    if len(paths) != len(VARIANTS):
        raise RuntimeError("exactly six result paths are required")
    rows: dict[str, dict[str, Any]] = {}
    raw: dict[str, dict[str, Any]] = {}
    for path in paths:
        result = _load(path)
        variant = result.get("variant")
        if variant not in VARIANTS or variant in raw:
            raise RuntimeError("missing, duplicate, or unknown variant in result set")
        raw[variant] = result
        rows[variant] = {
            "parameter_count": int(result["parameter_count"]),
            "selected_epoch": int(result["selected_epoch"]),
            "Dev": _metrics(result),
            "epoch_60_Dev": {
                key: float(value) for key, value in result["epoch_60"]["Dev"].items()
            },
        }
    if set(raw) != set(VARIANTS):
        raise RuntimeError("the six required variants are not all present")

    revisions = {result["source_revision"] for result in raw.values()}
    if len(revisions) != 1:
        raise RuntimeError("six lanes do not share one source revision")
    splits = {json.dumps(result["split"], sort_keys=True) for result in raw.values()}
    if len(splits) != 1:
        raise RuntimeError("six lanes do not share one canonical split")
    configs = {json.dumps(_common_config(result), sort_keys=True) for result in raw.values()}
    if len(configs) != 1:
        raise RuntimeError("six lanes do not share one common training configuration")

    multi_counts = {
        rows[variant]["parameter_count"]
        for variant in (
            "static_multiquery",
            "global_dynamic_multiquery",
            "evidence_dynamic_multiquery",
        )
    }
    adapter_counts = {
        rows[variant]["parameter_count"]
        for variant in ("static_query_adapter", "dynamic_query_adapter")
    }
    if len(multi_counts) != 1 or len(adapter_counts) != 1:
        raise RuntimeError("matched dynamic/control families do not have equal parameter counts")

    metric = {variant: rows[variant]["Dev"] for variant in VARIANTS}
    core = metric["core"]
    delta_global = metric["global_dynamic_multiquery"]["jaccard"] - metric["static_multiquery"]["jaccard"]
    delta_evidence = metric["evidence_dynamic_multiquery"]["jaccard"] - metric["static_multiquery"]["jaccard"]
    delta_adapter = metric["dynamic_query_adapter"]["jaccard"] - metric["static_query_adapter"]["jaccard"]
    delta_static_multi_core = metric["static_multiquery"]["jaccard"] - core["jaccard"]
    delta_static_adapter_core = metric["static_query_adapter"]["jaccard"] - core["jaccard"]

    survive_global = _survives(
        metric["global_dynamic_multiquery"], metric["static_multiquery"], core
    )
    survive_evidence = _survives(
        metric["evidence_dynamic_multiquery"], metric["static_multiquery"], core
    )
    survive_adapter = _survives(
        metric["dynamic_query_adapter"], metric["static_query_adapter"], core
    )
    multi_survives = survive_global or survive_evidence

    deltas = (delta_global, delta_evidence, delta_adapter)
    if multi_survives and survive_adapter:
        decision = "SURVIVE_GENERAL_PATIENT_CONDITIONED_QUERY"
    elif multi_survives:
        decision = "SURVIVE_DYNAMIC_MULTIQUERY"
    elif survive_adapter:
        decision = "SURVIVE_CONTINUOUS_DYNAMIC_QUERY"
    elif all(delta <= 0.002 for delta in deltas):
        decision = "KILL_PATIENT_CONDITIONED_QUERY_FAMILY"
    elif any(delta > 0.004 for delta in deltas):
        decision = "MECHANISM_SIGNAL_NO_PROJECT_HEADROOM"
    else:
        decision = "WEAK_DYNAMIC_QUERY_NO_SURVIVOR"

    return {
        "status": "complete",
        "evidence_class": "exploratory_train_dev_single_seed",
        "source_revision": next(iter(revisions)),
        "decision": decision,
        "deltas": {
            "global_dynamic_minus_static_multiquery_jaccard": delta_global,
            "global_dynamic_class": _classify(delta_global),
            "evidence_dynamic_minus_static_multiquery_jaccard": delta_evidence,
            "evidence_dynamic_class": _classify(delta_evidence),
            "dynamic_adapter_minus_static_adapter_jaccard": delta_adapter,
            "dynamic_adapter_class": _classify(delta_adapter),
            "static_multiquery_minus_core_jaccard": delta_static_multi_core,
            "static_adapter_minus_core_jaccard": delta_static_adapter_core,
        },
        "survival": {
            "global_dynamic_multiquery": survive_global,
            "evidence_dynamic_multiquery": survive_evidence,
            "dynamic_query_adapter": survive_adapter,
        },
        "rows": rows,
        "held_out_evaluated": False,
        "formal_gate_opened": False,
        "idea_009_created": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs=6, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = summarize(args.results)
    text = json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
