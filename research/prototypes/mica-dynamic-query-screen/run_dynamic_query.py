#!/usr/bin/env python3
"""Run one bounded MICA patient-conditioned-query Train/Dev lane."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mica_dynamic_query import (
    ADAPTER_DIM,
    ROUTES,
    VARIANTS,
    MICADynamicQuery,
    parameter_count,
)


def _load_v2_runner() -> Any:
    path = Path(__file__).resolve().parents[1] / "mica-v2-screen" / "run_mica_v2.py"
    spec = importlib.util.spec_from_file_location("mica_dynamic_base_runner", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load the proven MICA-v2 runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_RUNNER = _load_v2_runner()
_ORIGINAL_CONFIG = _RUNNER._scientific_config

_MECHANISMS = {
    "core": "exact MICA-Core DrugQuery anchor",
    "static_multiquery": "K=4 medication queries with learned patient-independent route mixture",
    "global_dynamic_multiquery": "same K=4 queries/parameters; route mixture augmented by patient global clinical summary",
    "evidence_dynamic_multiquery": "same K=4 queries/parameters; route mixture augmented by route evidence-support score",
    "static_query_adapter": "one medication query with parameter-matched static low-rank adapter",
    "dynamic_query_adapter": "same adapter; medication query changes with patient clinical summary",
}


def _scientific_config(variant: str, numeric_policy: dict[str, object]) -> dict[str, Any]:
    config = dict(_ORIGINAL_CONFIG("core", numeric_policy))
    config["variant"] = variant
    config["mechanism"] = _MECHANISMS[variant]
    config["dynamic_query_screen"] = {
        "routes": ROUTES if "multiquery" in variant else None,
        "adapter_dim": ADAPTER_DIM if "adapter" in variant else None,
        "route_prior": "learned per-medication patient-independent logits"
        if "multiquery" in variant
        else None,
        "dynamic_signal": {
            "global_dynamic_multiquery": "masked mean of assembled clinical keys",
            "evidence_dynamic_multiquery": "mean-normalized logsumexp of route-to-token affinities",
            "dynamic_query_adapter": "masked mean of assembled normalized clinical tokens",
        }.get(variant),
        "counterfactual_teacher": False,
        "route_competition": False,
        "null_route": False,
        "hyperparameter_sweep": False,
    }
    return config


_RUNNER.VARIANTS = VARIANTS
_RUNNER.MICAv2 = MICADynamicQuery
_RUNNER.parameter_count = parameter_count
_RUNNER._scientific_config = _scientific_config


def run(args: argparse.Namespace) -> dict[str, Any]:
    return _RUNNER.run(args)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--train-dev-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), sort_keys=True))


if __name__ == "__main__":
    main()
