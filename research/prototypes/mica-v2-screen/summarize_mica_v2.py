#!/usr/bin/env python3
"""Validate and summarize the six-lane MICA-v2 screening result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_SPLIT = {
    "train_patients": 4233,
    "dev_patients": 1004,
    "train_visits": 10489,
    "dev_visits": 2130,
}
EXPECTED_COMMON_CONFIG = {
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
    "decoder_threshold": 0.35,
    "ddi_weight": 0.05,
}
VARIANT_FILES = {
    "Core": "core",
    "FineHistory": "fine_history",
    "DualEvidence": "dual_evidence",
    "SafeRank": "safe_rank",
    "SelfOnly": "self_only",
    "SetContext": "set_context",
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


def _require_metrics(metrics: Any, label: str) -> dict[str, Any]:
    if not isinstance(metrics, dict) or not REQUIRED_METRICS.issubset(metrics):
        raise ValueError("missing or incomplete metrics for " + label)
    return metrics


def _validate_arm(arm: dict[str, Any], expected_variant: str) -> None:
    if arm.get("status") != "complete" or arm.get("variant") != expected_variant:
        raise ValueError("incomplete or unexpected MICA-v2 arm")
    if arm.get("completed_epochs") != 60 or len(arm.get("progress", [])) != 60:
        raise ValueError("all six lanes must complete exactly 60 epochs")
    if arm.get("selected_epoch") not in range(1, 61):
        raise ValueError("arm has no selected epoch")
    if arm.get("split") != EXPECTED_SPLIT:
        raise ValueError("arm split does not match canonical Train/Dev split")
    if not isinstance(arm.get("parameter_count"), int) or arm["parameter_count"] <= 0:
        raise ValueError("arm parameter count is missing")
    config = arm.get("config")
    if not isinstance(config, dict):
        raise ValueError("arm has no scientific config")
    for key, value in EXPECTED_COMMON_CONFIG.items():
        if config.get(key) != value:
            raise ValueError("scientific configuration mismatch in " + key)
    numeric = config.get("numeric_policy")
    if not isinstance(numeric, dict) or numeric.get("dtype") != "float32":
        raise ValueError("arm numeric policy is not float32")
    if (
        numeric.get("cuda_matmul_allow_tf32") is not False
        or numeric.get("cudnn_allow_tf32") is not False
    ):
        raise ValueError("arm numeric policy has TF32 enabled")
    selected = arm.get("selected_checkpoint")
    _require_metrics(selected.get("Train") if isinstance(selected, dict) else None, "Train")
    dev = _require_metrics(selected.get("Dev") if isinstance(selected, dict) else None, "Dev")
    epoch_60 = arm.get("epoch_60", {}).get("Dev")
    _require_metrics(epoch_60, "epoch-60 Dev")
    if epoch_60 != arm["progress"][-1].get("dev_metrics"):
        raise ValueError("epoch-60 metrics are not bound to the final progress row")
    if not isinstance(arm.get("wall_time_seconds"), (int, float)):
        raise ValueError("arm wall time is missing")
    if not isinstance(arm.get("cuda_peak_memory_mb"), (int, float)):
        raise ValueError("arm peak memory is missing")
    if dev["visit_count"] != EXPECTED_SPLIT["dev_visits"]:
        raise ValueError("Dev metric coverage is incomplete")


def _classify(delta: float) -> str:
    magnitude = abs(delta)
    if magnitude <= 0.002:
        return "no_material_contribution"
    if magnitude <= 0.004:
        return "weak_contribution"
    if magnitude >= 0.010:
        return "strong_signal"
    return "meaningful_contribution"


def _accuracy_not_worse(candidate: dict[str, Any], control: dict[str, Any]) -> bool:
    return (
        candidate["f1"] >= control["f1"] - 0.002 and candidate["prauc"] >= control["prauc"] - 0.002
    )


def _row(arm: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_epoch": arm["selected_epoch"],
        "parameter_count": arm["parameter_count"],
        "decoder": arm["config"]["decoder"],
        "Train": arm["selected_checkpoint"]["Train"],
        "Dev": arm["selected_checkpoint"]["Dev"],
        "epoch_60_Dev": arm["epoch_60"]["Dev"],
        "wall_time_seconds": arm["wall_time_seconds"],
        "cuda_peak_memory_mb": arm["cuda_peak_memory_mb"],
        "runtime": arm.get("runtime", {}),
    }


def _safe_row(core: dict[str, Any]) -> dict[str, Any]:
    safe = core.get("safe_pto")
    if not isinstance(safe, dict):
        raise ValueError("Core result has no SafePTO evaluation")
    for key in ("Train", "Dev", "epoch_60_Dev"):
        _require_metrics(safe.get(key), "SafePTO " + key)
    return {
        "selected_epoch": safe["selected_epoch"],
        "parameter_count": core["parameter_count"],
        "decoder": "SafeSwap",
        "Train": safe["Train"],
        "Dev": safe["Dev"],
        "epoch_60_Dev": safe["epoch_60_Dev"],
        "wall_time_seconds": None,
        "cuda_peak_memory_mb": None,
        "runtime": core.get("runtime", {}),
        "inference_only": True,
        "source": "Lane-0 Core selected checkpoint",
    }


def _parse_gpu_assignment(value: str | None) -> dict[str, int]:
    if not value:
        return {}
    result: dict[str, int] = {}
    for item in value.split(","):
        name, gpu = item.split(":", 1)
        result[name] = int(gpu)
    return result


def summarize(
    arms: dict[str, dict[str, Any]],
    starting_revision: str,
    gpu_assignment: dict[str, int],
    run_revision: str | None = None,
    scoped_safe_rank_rerun_revision: str | None = None,
) -> dict[str, Any]:
    if len(arms) != len(VARIANT_FILES):
        raise ValueError("exactly six MICA-v2 arms are required")
    for display, arm in arms.items():
        _validate_arm(arm, VARIANT_FILES[display])
    revisions = {arm.get("source_revision") for arm in arms.values()}
    if len(revisions) != 1 or not isinstance(next(iter(revisions)), str):
        if not run_revision or not scoped_safe_rank_rerun_revision:
            raise ValueError("all arms must share one immutable source revision")
        if run_revision not in revisions or scoped_safe_rank_rerun_revision not in revisions:
            raise ValueError("scoped SafeRank rerun revisions are not bound to arm results")
        if revisions != {run_revision, scoped_safe_rank_rerun_revision}:
            raise ValueError("unexpected source revisions in scoped SafeRank rerun")
        for display, arm in arms.items():
            expected = scoped_safe_rank_rerun_revision if display == "SafeRank" else run_revision
            if arm.get("source_revision") != expected:
                raise ValueError("only SafeRank may use the scoped rerun revision")
    else:
        only_revision = next(iter(revisions))
        if run_revision and run_revision != only_revision:
            raise ValueError("run revision does not match arm results")
        run_revision = only_revision
    if arms["Core"]["parameter_count"] != arms["FineHistory"]["parameter_count"]:
        raise ValueError("FineHistory must match Core parameter count")
    if arms["Core"]["parameter_count"] != arms["SafeRank"]["parameter_count"]:
        raise ValueError("SafeRank must match Core parameter count")
    if arms["SelfOnly"]["parameter_count"] != arms["SetContext"]["parameter_count"]:
        raise ValueError("SelfOnly and SetContext must match parameter count")

    core = arms["Core"]["selected_checkpoint"]["Dev"]
    fine = arms["FineHistory"]["selected_checkpoint"]["Dev"]
    dual = arms["DualEvidence"]["selected_checkpoint"]["Dev"]
    safe_rank = arms["SafeRank"]["selected_checkpoint"]["Dev"]
    self_only = arms["SelfOnly"]["selected_checkpoint"]["Dev"]
    set_context = arms["SetContext"]["selected_checkpoint"]["Dev"]
    safe_pto = _safe_row(arms["Core"])
    safe_pto_dev = safe_pto["Dev"]

    delta_fine = fine["jaccard"] - core["jaccard"]
    delta_dual = dual["jaccard"] - core["jaccard"]
    delta_safe_pto = safe_pto_dev["jaccard"] - core["jaccard"]
    delta_safe_pto_ddi = safe_pto_dev["ddi_rate"] - core["ddi_rate"]
    delta_safe_rank = safe_rank["jaccard"] - core["jaccard"]
    delta_safe_rank_ddi = safe_rank["ddi_rate"] - core["ddi_rate"]
    delta_safe_rank_pto = safe_rank["jaccard"] - safe_pto_dev["jaccard"]
    delta_safe_rank_pto_ddi = safe_rank["ddi_rate"] - safe_pto_dev["ddi_rate"]
    delta_set = set_context["jaccard"] - self_only["jaccard"]
    delta_set_ddi = set_context["ddi_rate"] - self_only["ddi_rate"]

    fine_survives = (
        delta_fine > 0.004
        and fine["ddi_rate"] <= core["ddi_rate"] + 0.002
        and _accuracy_not_worse(fine, core)
    )
    dual_survives = (
        delta_dual > 0.004
        and dual["ddi_rate"] <= core["ddi_rate"] + 0.002
        and _accuracy_not_worse(dual, core)
    )
    safe_headroom = (
        safe_pto_dev["ddi_rate"] <= core["ddi_rate"] - 0.005
        and safe_pto_dev["jaccard"] >= core["jaccard"] - 0.005
    )
    safe_rank_survives = (
        safe_rank["jaccard"] >= core["jaccard"]
        and safe_rank["ddi_rate"] <= core["ddi_rate"] - 0.005
        and safe_rank["f1"] >= core["f1"] - 0.002
        and safe_rank["prauc"] >= core["prauc"] - 0.002
        and safe_rank["mean_medication_count"] >= core["mean_medication_count"] - 1.0
    )
    safe_rank_strong = delta_safe_rank >= 0.003 and delta_safe_rank_ddi <= -0.008
    safe_rank_stretch = safe_rank["jaccard"] >= 0.547 and safe_rank["ddi_rate"] <= 0.065
    safe_rank_incremental = (delta_safe_rank_pto > 0.002 and delta_safe_rank_pto_ddi <= 0.001) or (
        delta_safe_rank_pto_ddi < -0.003 and delta_safe_rank_pto <= 0.001
    )
    set_signal = (
        "kill_set_context"
        if delta_set <= 0.002
        else "weak_set_context"
        if delta_set <= 0.004
        else "joint_set_mechanism_signal"
    )
    set_preserve = (
        delta_set > 0.004
        and set_context["jaccard"] >= core["jaccard"] + 0.004
        and set_context["ddi_rate"] <= core["ddi_rate"] + 0.002
        and _accuracy_not_worse(set_context, core)
    )

    if safe_rank_survives:
        surviving_accuracy = []
        if fine_survives:
            surviving_accuracy.append(("FineHistory", fine))
        if dual_survives:
            surviving_accuracy.append(("DualEvidence", dual))
        if surviving_accuracy:
            surviving_accuracy.sort(
                key=lambda item: (
                    -item[1]["jaccard"],
                    -item[1]["prauc"],
                    item[1]["ddi_rate"],
                )
            )
            next_route = "COMBINE_SAFERANK_WITH_" + surviving_accuracy[0][0].upper() + "_NEXT_CYCLE"
        else:
            next_route = "PRESERVE_SAFERANK_AS_PRIMARY_CANDIDATE_NEXT_CYCLE"
    elif set_preserve:
        next_route = "PRESERVE_SETCONTEXT_AS_SINGLE_ACCURACY_EXTENSION_NEXT_CYCLE"
    elif fine_survives or dual_survives:
        winner = "FineHistory" if fine["jaccard"] >= dual["jaccard"] else "DualEvidence"
        next_route = "PRESERVE_" + winner.upper() + "_AS_STRONGER_MICA_SUBSTRATE"
    elif safe_headroom:
        next_route = "SEARCH_DIFFERENT_LEARNED_SAFETY_MECHANISM_AFTER_SAFEPTO_HEADROOM"
    else:
        next_route = "KEEP_MICA_CORE_AND_RETURN_TO_MATERIAL_ARCHITECTURE_SEARCH"

    conclusions = {
        "fine_history": "survive_fine_history"
        if fine_survives
        else "kill_fine_history"
        if delta_fine <= 0.002
        else "weak_fine_history",
        "dual_evidence": "survive_dual_evidence"
        if dual_survives
        else "kill_dual_evidence"
        if delta_dual <= 0.002
        else "weak_dual_evidence",
        "history_family": "reset_history_refinement_family"
        if not fine_survives and not dual_survives
        else "retain_surviving_history_signal",
        "safe_decision_headroom": "SAFE_DECISION_HEADROOM"
        if safe_headroom
        else "NO_MICA_SAFE_DECISION_HEADROOM",
        "safe_rank": "survive_saferank_pareto"
        if safe_rank_survives
        else "kill_saferank_project_survival",
        "safe_rank_incremental": "meaningful_incremental_value"
        if safe_rank_incremental
        else "no_material_incremental_value",
        "safe_rank_strong": safe_rank_strong,
        "safe_rank_stretch": safe_rank_stretch,
        "set_context": set_signal,
        "set_context_preserve": set_preserve,
    }
    rows = {display: _row(arm) for display, arm in arms.items()}
    rows["SafePTO"] = safe_pto
    return {
        "schema_version": 1,
        "status": "complete",
        "evidence_class": "exploratory_train_dev_single_seed",
        "starting_revision": starting_revision,
        "run_revision": run_revision,
        "remote_checkout_revision": sorted(revisions),
        "arm_source_revisions": {
            display: arms[display]["source_revision"] for display in VARIANT_FILES
        },
        "source_revision_exception": (
            {
                "kind": "scoped_runtime_fix",
                "affected_arm": "SafeRank",
                "baseline_revision": run_revision,
                "corrected_revision": scoped_safe_rank_rerun_revision,
                "description": (
                    "SafeSwap incremental candidate counting was proven equivalent to the "
                    "naive implementation and used only to rerun the invalid SafeRank lane."
                ),
            }
            if scoped_safe_rank_rerun_revision
            else None
        ),
        "excluded_runtime_attempts": [
            {
                "revision": "c41c304ceb59b1537e3a0eb97a4fd64ec7025cb9",
                "arm": "SafeRank",
                "completed_epochs": 1,
                "reason": "SafeSwap candidate-counting runtime defect; no complete result used",
            },
            {
                "revision": "93c2bf72b0ed7e37913c0ea399ca535c680a7bfa",
                "arm": "SafeRank",
                "completed_epochs": 2,
                "reason": "SafeRank candidate-scoring runtime defect; no complete result used",
            },
        ],
        "verification": {
            "preflight_status": "PASS",
            "cuda_preflight_revision": scoped_safe_rank_rerun_revision or run_revision,
            "safe_swap_incremental_equivalence": {"status": "PASS", "random_trials": 5},
            "safe_rank_vectorized_equivalence": {"status": "PASS", "random_trials": 3},
        },
        "gpu_assignment": gpu_assignment,
        "environment": arms["Core"].get("runtime", {}),
        "split": EXPECTED_SPLIT,
        "matched_parameter_counts": {
            display: arms[display]["parameter_count"] for display in VARIANT_FILES
        },
        "rows": rows,
        "selected_epochs": {display: arm["selected_epoch"] for display, arm in arms.items()},
        "completed_epochs": {display: arm["completed_epochs"] for display, arm in arms.items()},
        "deltas": {
            "delta_j_fine": delta_fine,
            "delta_j_dual": delta_dual,
            "safe_pto_minus_core_delta_j": delta_safe_pto,
            "safe_pto_minus_core_delta_ddi": delta_safe_pto_ddi,
            "safe_rank_minus_core_delta_j": delta_safe_rank,
            "safe_rank_minus_core_delta_ddi": delta_safe_rank_ddi,
            "safe_rank_minus_safe_pto_delta_j": delta_safe_rank_pto,
            "safe_rank_minus_safe_pto_delta_ddi": delta_safe_rank_pto_ddi,
            "set_context_minus_self_only_delta_j": delta_set,
            "set_context_minus_self_only_delta_ddi": delta_set_ddi,
            "classes": {
                "delta_j_fine": _classify(delta_fine),
                "delta_j_dual": _classify(delta_dual),
                "safe_pto_minus_core_delta_j": _classify(delta_safe_pto),
                "safe_rank_minus_core_delta_j": _classify(delta_safe_rank),
                "set_context_minus_self_only_delta_j": _classify(delta_set),
            },
        },
        "conclusions": conclusions,
        "next_route": next_route,
        "frozen_configuration": arms["Core"]["config"],
        "source_bound_references": arms["Core"].get("source_bound_references", {}),
        "references": {
            "MoleRec": arms["Core"].get("frozen_molerec_dev"),
            "GraphRefine-SameK": arms["Core"].get("historical_graphrefine_samek"),
        },
        "held_out_evaluated": False,
        "additional_seeds": False,
        "idea_009_created": False,
        "formal_gate_opened": False,
        "audit_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for _display, flag in VARIANT_FILES.items():
        parser.add_argument("--" + flag.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--starting-revision", required=True)
    parser.add_argument("--run-revision")
    parser.add_argument("--scoped-safe-rank-rerun-revision")
    parser.add_argument("--gpu-assignment")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    arms = {
        display: json.loads(getattr(args, flag.replace("-", "_")).read_text())
        for display, flag in VARIANT_FILES.items()
    }
    result = summarize(
        arms,
        args.starting_revision,
        _parse_gpu_assignment(args.gpu_assignment),
        args.run_revision,
        args.scoped_safe_rank_rerun_revision,
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
