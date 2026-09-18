#!/usr/bin/env python3
"""Summarize the frozen six-lane ECRC screen from public-safe aggregates only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any, Mapping

DRUGQUERY_ANCHOR_J = 0.539316
ABSOLUTE_FLOOR = DRUGQUERY_ANCHOR_J - 0.002


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "complete":
        raise RuntimeError(str(path) + " is not a complete ECRC result")
    if value.get("test_accessed") is not False:
        raise RuntimeError(str(path) + " does not certify sealed Test")
    return value


def _metrics(result: Mapping[str, Any], oracle: bool) -> Mapping[str, float]:
    key = "Dev_oracle_k_diagnostic" if oracle else "Dev_predicted_k"
    return result["selected_checkpoint"][key]


def _delta(candidate: Mapping[str, Any], control: Mapping[str, Any], oracle: bool) -> dict[str, float]:
    c = _metrics(candidate, oracle)
    b = _metrics(control, oracle)
    return {
        "jaccard": float(c["jaccard"]) - float(b["jaccard"]),
        "f1": float(c["f1"]) - float(b["f1"]),
        "prauc": float(c["prauc"]) - float(b["prauc"]),
        "ddi_rate": float(c["ddi_rate"]) - float(b["ddi_rate"]),
        "average_medication_count": float(c["average_medication_count"])
        - float(b["average_medication_count"]),
        "count_mae_visit": float(c["count_mae_visit"]) - float(b["count_mae_visit"]),
    }


def _pair(control: Mapping[str, Any], candidate: Mapping[str, Any], expected_seed: int) -> dict[str, Any]:
    if int(control["seed"]) != expected_seed or int(candidate["seed"]) != expected_seed:
        raise RuntimeError("paired ECRC seed mismatch")
    if control["source_revision"] != candidate["source_revision"]:
        raise RuntimeError("paired ECRC source revisions differ")
    if int(control["parameter_count"]) != int(candidate["parameter_count"]):
        raise RuntimeError("paired ECRC parameter counts differ")
    return {
        "seed": expected_seed,
        "control_variant": control["variant"],
        "candidate_variant": candidate["variant"],
        "parameter_count": int(control["parameter_count"]),
        "predicted_k_delta": _delta(candidate, control, oracle=False),
        "oracle_k_delta": _delta(candidate, control, oracle=True),
        "control_predicted_k": dict(_metrics(control, False)),
        "candidate_predicted_k": dict(_metrics(candidate, False)),
        "control_oracle_k": dict(_metrics(control, True)),
        "candidate_oracle_k": dict(_metrics(candidate, True)),
    }


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    results = {
        "kind_bce_a": _load(args.kind_bce_a),
        "kcond_bce_a": _load(args.kcond_bce_a),
        "kind_exact_a": _load(args.kind_exact_a),
        "kcond_exact_a": _load(args.kcond_exact_a),
        "kind_exact_b": _load(args.kind_exact_b),
        "kcond_exact_b": _load(args.kcond_exact_b),
    }
    expected = {
        "kind_bce_a": ("kind_bce", 20260923),
        "kcond_bce_a": ("kcond_bce", 20260923),
        "kind_exact_a": ("kind_exact", 20260923),
        "kcond_exact_a": ("kcond_exact", 20260923),
        "kind_exact_b": ("kind_exact", 20260924),
        "kcond_exact_b": ("kcond_exact", 20260924),
    }
    for name, (variant, seed) in expected.items():
        if results[name]["variant"] != variant or int(results[name]["seed"]) != seed:
            raise RuntimeError(name + " does not match the frozen lane identity")
    revisions = {value["source_revision"] for value in results.values()}
    if len(revisions) != 1:
        raise RuntimeError("six ECRC lanes do not share one source revision")

    bce = _pair(results["kind_bce_a"], results["kcond_bce_a"], 20260923)
    exact_a = _pair(results["kind_exact_a"], results["kcond_exact_a"], 20260923)
    exact_b = _pair(results["kind_exact_b"], results["kcond_exact_b"], 20260924)
    exact_pairs = (exact_a, exact_b)

    def avg(surface: str, metric: str) -> float:
        return mean(float(pair[surface][metric]) for pair in exact_pairs)

    predicted_mean = {name: avg("predicted_k_delta", name) for name in (
        "jaccard",
        "f1",
        "prauc",
        "ddi_rate",
        "average_medication_count",
        "count_mae_visit",
    )}
    oracle_mean = {name: avg("oracle_k_delta", name) for name in (
        "jaccard",
        "f1",
        "prauc",
        "ddi_rate",
        "average_medication_count",
        "count_mae_visit",
    )}
    predicted_seed_deltas = [float(pair["predicted_k_delta"]["jaccard"]) for pair in exact_pairs]
    oracle_seed_deltas = [float(pair["oracle_k_delta"]["jaccard"]) for pair in exact_pairs]
    candidate_abs = mean(
        float(pair["candidate_predicted_k"]["jaccard"]) for pair in exact_pairs
    )

    mechanism_present = (
        oracle_mean["jaccard"] > 0.004 and all(value > 0.0 for value in oracle_seed_deltas)
    )
    deployable_value = (
        predicted_mean["jaccard"] > 0.004
        and all(value > 0.0 for value in predicted_seed_deltas)
    )
    support_ok = (
        predicted_mean["f1"] >= -0.002
        and predicted_mean["prauc"] >= -0.002
        and predicted_mean["ddi_rate"] <= 0.002
        and candidate_abs >= ABSOLUTE_FLOOR
    )

    if not mechanism_present:
        decision = "KILL_ECRC_CHOICE_MECHANISM"
        reason = "oracle-K exact comparison does not show material cardinality-conditioned choice value"
    elif not deployable_value:
        decision = "REDESIGN_SIZE_HEAD_ONLY"
        reason = (
            "oracle-K isolates a material choice mechanism, but predicted-K deployment does not "
            "recover >+0.004 Jaccard; only one bounded size-predictor redesign is authorized"
        )
    elif not support_ok:
        decision = "WEAK_STOP_ECRC"
        reason = "primary Jaccard survives but support/absolute-quality constraints fail"
    elif predicted_mean["jaccard"] >= 0.008:
        decision = "STRONG_SURVIVE_ECRC"
        reason = "two-seed exact predicted-K gain is strong and oracle-K confirms the choice mechanism"
    else:
        decision = "SURVIVE_ECRC"
        reason = "two-seed exact predicted-K gain is material and oracle-K confirms the choice mechanism"

    return {
        "schema_version": 1,
        "status": "complete",
        "source_revision": next(iter(revisions)),
        "decision": decision,
        "reason": reason,
        "frozen_thresholds": {
            "mechanism_oracle_k_jaccard": 0.004,
            "deployable_predicted_k_jaccard": 0.004,
            "weak_lower_bound": 0.002,
            "strong_jaccard": 0.008,
            "max_support_drop_f1": 0.002,
            "max_support_drop_prauc": 0.002,
            "max_ddi_increase": 0.002,
            "absolute_candidate_jaccard_floor": ABSOLUTE_FLOOR,
        },
        "bce_supporting_pair": bce,
        "exact_pairs": [exact_a, exact_b],
        "exact_mean_predicted_k_delta": predicted_mean,
        "exact_mean_oracle_k_delta": oracle_mean,
        "exact_predicted_k_jaccard_seed_deltas": predicted_seed_deltas,
        "exact_oracle_k_jaccard_seed_deltas": oracle_seed_deltas,
        "mean_kcond_exact_predicted_k_jaccard": candidate_abs,
        "mechanism_present_under_oracle_k": mechanism_present,
        "deployable_value_under_predicted_k": deployable_value,
        "support_constraints_pass": support_ok,
        "interpretation": {
            "oracle_k": "privileged mechanism diagnostic only; never model performance",
            "bce_pair": "supporting attribution only; not a separate survival gate",
            "size_head_redesign": (
                "authorized only when oracle-K mechanism is material but predicted-K deployment fails"
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind-bce-a", type=Path, required=True)
    parser.add_argument("--kcond-bce-a", type=Path, required=True)
    parser.add_argument("--kind-exact-a", type=Path, required=True)
    parser.add_argument("--kcond-exact-a", type=Path, required=True)
    parser.add_argument("--kind-exact-b", type=Path, required=True)
    parser.add_argument("--kcond-exact-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
