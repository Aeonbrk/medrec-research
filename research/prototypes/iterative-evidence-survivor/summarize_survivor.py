#!/usr/bin/env python3
"""Summarize final-resolution attribution and four-condition depth stability."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

HERE = Path(__file__).resolve().parent
PRIOR_RESULT = HERE.parents[0] / "evidence-access-portfolio" / "result.json"

NEW_DEPTH_PAIRS: Tuple[Tuple[str, str, str], ...] = (
    ("stability_1", "depth_state_s1", "depth_reread_s1"),
    ("stability_2", "depth_state_s2", "depth_reread_s2"),
    ("stability_3", "depth_state_s3", "depth_reread_s3"),
)


def _read(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lane(root: Path, name: str) -> Mapping[str, Any]:
    path = root / name / "results.json"
    if not path.is_file():
        raise RuntimeError("missing lane result: " + str(path))
    result = _read(path)
    if result.get("status") != "complete" or result.get("completed_epochs") != 60:
        raise RuntimeError("lane is not a complete 60-epoch run: " + name)
    if result.get("test_loaded") is not False:
        raise RuntimeError("Test boundary violated: " + name)
    return result


def _pair(control: Mapping[str, Any], candidate: Mapping[str, Any]) -> Dict[str, Any]:
    if control["parameter_count"] != candidate["parameter_count"]:
        raise RuntimeError("pair parameter count mismatch")
    c = control["metrics"]["Dev"]
    a = candidate["metrics"]["Dev"]
    delta = {
        "jaccard": float(a["jaccard"]) - float(c["jaccard"]),
        "f1": float(a["f1"]) - float(c["f1"]),
        "prauc": float(a["prauc"]) - float(c["prauc"]),
        "ddi_rate": float(a["ddi_rate"]) - float(c["ddi_rate"]),
        "average_medication_count": float(a["average_medication_count"])
        - float(c["average_medication_count"]),
    }
    return {
        "control": control["lane"],
        "candidate": candidate["lane"],
        "control_selected_checkpoint": control["selected_checkpoint"],
        "candidate_selected_checkpoint": candidate["selected_checkpoint"],
        "control_selected_operating_point": control["selected_operating_point"],
        "candidate_selected_operating_point": candidate["selected_operating_point"],
        "parameter_count": control["parameter_count"],
        "control_dev": c,
        "candidate_dev": a,
        "delta": delta,
    }


def _guardrails(delta: Mapping[str, float]) -> bool:
    return (
        float(delta["f1"]) >= -0.002
        and float(delta["prauc"]) >= -0.002
        and float(delta["ddi_rate"]) <= 0.002
    )


def _resolution_verdict(delta: Mapping[str, float]) -> str:
    j = float(delta["jaccard"])
    if j <= 0.002:
        return "CODE_RESOLUTION_NOT_INCREMENTAL_UNDER_REREAD"
    if j <= 0.004:
        return "WEAK_CODE_RESOLUTION_UNDER_REREAD"
    if _guardrails(delta):
        return "CODE_RESOLUTION_CARRIES_FINAL_ARCHITECTURE"
    return "CODE_RESOLUTION_SIGNAL_WITH_COST"


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values))


def _stability_verdict(
    rows: Sequence[Mapping[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    j = [float(row["delta"]["jaccard"]) for row in rows]
    f1 = [float(row["delta"]["f1"]) for row in rows]
    prauc = [float(row["delta"]["prauc"]) for row in rows]
    ddi = [float(row["delta"]["ddi_rate"]) for row in rows]
    mean_delta = {
        "jaccard": _mean(j),
        "f1": _mean(f1),
        "prauc": _mean(prauc),
        "ddi_rate": _mean(ddi),
    }
    summary = {
        "conditions": len(rows),
        "positive_jaccard_conditions": sum(value > 0.0 for value in j),
        "material_jaccard_conditions_gt_0_002": sum(
            value > 0.002 for value in j
        ),
        "mean_delta": mean_delta,
        "median_delta_jaccard": float(statistics.median(j)),
        "std_delta_jaccard": float(statistics.stdev(j))
        if len(j) > 1
        else 0.0,
        "min_delta_jaccard": min(j),
        "max_delta_jaccard": max(j),
        "mean_guardrails_pass": _guardrails(mean_delta),
    }
    if (
        summary["positive_jaccard_conditions"] == 4
        and summary["material_jaccard_conditions_gt_0_002"] >= 3
        and mean_delta["jaccard"] > 0.004
        and summary["mean_guardrails_pass"]
    ):
        return "STABLE_DEPTH_REREAD", summary
    if (
        summary["positive_jaccard_conditions"] == 4
        and mean_delta["jaccard"] > 0.002
        and summary["mean_guardrails_pass"]
    ):
        return "POSITIVE_BUT_SUBTHRESHOLD_DEPTH_STABILITY", summary
    return "UNSTABLE_DEPTH_REREAD", summary


def run(root: Path) -> Dict[str, Any]:
    prior = _read(PRIOR_RESULT)
    if prior.get("status") != "complete" or prior.get("test_loaded") is not False:
        raise RuntimeError(
            "prior portfolio result is not valid completed DEVELOPMENT evidence"
        )
    prior_depth = prior["pairs"]["depth"]
    canonical = {
        "condition": "canonical",
        "source": "prior evidence-access portfolio",
        "control": prior_depth["control"],
        "candidate": prior_depth["candidate"],
        "control_selected_checkpoint": prior_depth["control_selected_checkpoint"],
        "candidate_selected_checkpoint": prior_depth["candidate_selected_checkpoint"],
        "control_selected_operating_point": prior_depth[
            "control_selected_operating_point"
        ],
        "candidate_selected_operating_point": prior_depth[
            "candidate_selected_operating_point"
        ],
        "parameter_count": prior_depth["parameter_count"],
        "control_dev": prior_depth["control_dev"],
        "candidate_dev": prior_depth["candidate_dev"],
        "delta": prior_depth["delta"],
    }

    source_revisions = set()
    depth_rows = [canonical]
    for condition, control_name, candidate_name in NEW_DEPTH_PAIRS:
        control = _lane(root, control_name)
        candidate = _lane(root, candidate_name)
        if (
            control["seed_condition"] != condition
            or candidate["seed_condition"] != condition
        ):
            raise RuntimeError("seed-condition mismatch for " + condition)
        source_revisions.update(
            (control["source_revision"], candidate["source_revision"])
        )
        row = _pair(control, candidate)
        row["condition"] = condition
        row["source"] = "survivor screen"
        depth_rows.append(row)

    visit = _lane(root, "resolution_visit_canonical")
    code = _lane(root, "resolution_code_canonical")
    source_revisions.update((visit["source_revision"], code["source_revision"]))
    resolution = _pair(visit, code)
    resolution["guardrails_pass"] = _guardrails(resolution["delta"])
    resolution["verdict"] = _resolution_verdict(resolution["delta"])

    if len(source_revisions) != 1:
        raise RuntimeError(
            "new survivor lanes do not share one immutable revision"
        )
    stability_verdict, stability_summary = _stability_verdict(depth_rows)

    if stability_verdict == "STABLE_DEPTH_REREAD":
        if (
            resolution["verdict"]
            == "CODE_RESOLUTION_CARRIES_FINAL_ARCHITECTURE"
        ):
            routing = "PROMOTE_FINE_CODE_REREAD_TO_PAPER_CANDIDATE_REVIEW"
        elif resolution["verdict"] in {
            "CODE_RESOLUTION_NOT_INCREMENTAL_UNDER_REREAD",
            "WEAK_CODE_RESOLUTION_UNDER_REREAD",
        }:
            routing = "PROMOTE_REREAD_WITH_RESOLUTION_SIMPLIFICATION_REVIEW"
        else:
            routing = "HOLD_REREAD_RESOLUTION_COST_REVIEW"
    elif (
        stability_verdict
        == "POSITIVE_BUT_SUBTHRESHOLD_DEPTH_STABILITY"
    ):
        routing = "HOLD_REREAD_NO_PAPER_PROMOTION"
    else:
        routing = "RETURN_TO_ARCHITECTURE_SEARCH_DEPTH_NOT_STABLE"

    return {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "source_revision": next(iter(source_revisions)),
        "profile_id": prior["profile_id"],
        "resolution_attribution": resolution,
        "depth_stability": {
            "conditions": depth_rows,
            "summary": stability_summary,
            "verdict": stability_verdict,
        },
        "routing": routing,
        "test_loaded": False,
        "automatic_test_authorized": False,
        "automatic_mimiciv_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.root.resolve())
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
