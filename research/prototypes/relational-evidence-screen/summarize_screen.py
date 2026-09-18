
#!/usr/bin/env python3
"""Summarize fine-code stability and relational-evidence mechanism evidence."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

HERE = Path(__file__).resolve().parent
PRIOR_RESULT = (
    HERE.parents[0]
    / "evidence-access-portfolio"
    / "result.json"
)

NEW_RESOLUTION_PAIRS: Tuple[
    Tuple[str, str, str], ...
] = (
    (
        "stability_1",
        "resolution_visit_s1",
        "resolution_code_s1",
    ),
    (
        "stability_2",
        "resolution_visit_s2",
        "resolution_code_s2",
    ),
    (
        "stability_3",
        "resolution_visit_s3",
        "resolution_code_s3",
    ),
)


def _read(path: Path) -> Mapping[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def _lane(
    root: Path,
    name: str,
) -> Mapping[str, Any]:
    path = root / name / "results.json"
    if not path.is_file():
        raise RuntimeError(
            "missing lane result: " + str(path)
        )
    result = _read(path)
    if (
        result.get("status") != "complete"
        or result.get("completed_epochs") != 60
    ):
        raise RuntimeError(
            "lane is not complete: " + name
        )
    if result.get("test_loaded") is not False:
        raise RuntimeError(
            "Test boundary violated: " + name
        )
    return result


def _pair(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> Dict[str, Any]:
    if (
        control["parameter_count"]
        != candidate["parameter_count"]
    ):
        raise RuntimeError(
            "pair parameter count mismatch"
        )

    c = control["metrics"]["Dev"]
    a = candidate["metrics"]["Dev"]
    delta = {
        "jaccard": (
            float(a["jaccard"])
            - float(c["jaccard"])
        ),
        "f1": (
            float(a["f1"])
            - float(c["f1"])
        ),
        "prauc": (
            float(a["prauc"])
            - float(c["prauc"])
        ),
        "ddi_rate": (
            float(a["ddi_rate"])
            - float(c["ddi_rate"])
        ),
        "average_medication_count": (
            float(a["average_medication_count"])
            - float(c["average_medication_count"])
        ),
    }
    return {
        "control": control["lane"],
        "candidate": candidate["lane"],
        "parameter_count": (
            control["parameter_count"]
        ),
        "control_selected_checkpoint": (
            control["selected_checkpoint"]
        ),
        "candidate_selected_checkpoint": (
            candidate["selected_checkpoint"]
        ),
        "control_selected_operating_point": (
            control["selected_operating_point"]
        ),
        "candidate_selected_operating_point": (
            candidate["selected_operating_point"]
        ),
        "control_dev": c,
        "candidate_dev": a,
        "delta": delta,
    }


def _guardrails(
    delta: Mapping[str, float],
) -> bool:
    return (
        float(delta["f1"]) >= -0.002
        and float(delta["prauc"]) >= -0.002
        and float(delta["ddi_rate"]) <= 0.002
    )


def _mean(
    values: Sequence[float],
) -> float:
    return float(
        sum(values) / len(values)
    )


def _fine_code_stability(
    rows: Sequence[Mapping[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    j = [
        float(row["delta"]["jaccard"])
        for row in rows
    ]
    f1 = [
        float(row["delta"]["f1"])
        for row in rows
    ]
    prauc = [
        float(row["delta"]["prauc"])
        for row in rows
    ]
    ddi = [
        float(row["delta"]["ddi_rate"])
        for row in rows
    ]

    mean_delta = {
        "jaccard": _mean(j),
        "f1": _mean(f1),
        "prauc": _mean(prauc),
        "ddi_rate": _mean(ddi),
    }
    summary = {
        "conditions": len(rows),
        "positive_jaccard_conditions": sum(
            value > 0.0 for value in j
        ),
        "material_jaccard_conditions_gt_0_002": (
            sum(
                value > 0.002
                for value in j
            )
        ),
        "mean_delta": mean_delta,
        "median_delta_jaccard": float(
            statistics.median(j)
        ),
        "std_delta_jaccard": float(
            statistics.stdev(j)
        )
        if len(j) > 1
        else 0.0,
        "min_delta_jaccard": min(j),
        "max_delta_jaccard": max(j),
        "mean_guardrails_pass": (
            _guardrails(mean_delta)
        ),
    }

    if (
        summary[
            "positive_jaccard_conditions"
        ]
        == 4
        and summary[
            "material_jaccard_conditions_gt_0_002"
        ]
        >= 3
        and mean_delta["jaccard"] > 0.004
        and summary["mean_guardrails_pass"]
    ):
        return (
            "STABLE_FINE_CODE_ACCESS",
            summary,
        )

    if (
        summary[
            "positive_jaccard_conditions"
        ]
        == 4
        and mean_delta["jaccard"] > 0.002
        and summary["mean_guardrails_pass"]
    ):
        return (
            "POSITIVE_BUT_SUBTHRESHOLD_FINE_CODE_ACCESS",
            summary,
        )

    return (
        "UNSTABLE_FINE_CODE_ACCESS",
        summary,
    )


def _relational_verdict(
    delta: Mapping[str, float],
) -> str:
    j = float(delta["jaccard"])
    if j <= 0.002:
        return "KILL_RELATIONAL_EVIDENCE"
    if j <= 0.004:
        return (
            "WEAK_RELATIONAL_EVIDENCE_STOP"
        )
    if _guardrails(delta):
        return "RELATIONAL_EVIDENCE_SIGNAL"
    return (
        "RELATIONAL_EVIDENCE_SIGNAL_WITH_COST"
    )


def run(root: Path) -> Dict[str, Any]:
    prior = _read(PRIOR_RESULT)
    if (
        prior.get("status") != "complete"
        or prior.get("test_loaded") is not False
    ):
        raise RuntimeError(
            "prior portfolio result is not valid DEVELOPMENT evidence"
        )

    prior_resolution = prior["pairs"][
        "resolution"
    ]
    canonical = {
        "condition": "canonical",
        "source": "prior evidence-access portfolio",
        "control": prior_resolution[
            "control"
        ],
        "candidate": prior_resolution[
            "candidate"
        ],
        "parameter_count": prior_resolution[
            "parameter_count"
        ],
        "control_selected_checkpoint": (
            prior_resolution[
                "control_selected_checkpoint"
            ]
        ),
        "candidate_selected_checkpoint": (
            prior_resolution[
                "candidate_selected_checkpoint"
            ]
        ),
        "control_selected_operating_point": (
            prior_resolution[
                "control_selected_operating_point"
            ]
        ),
        "candidate_selected_operating_point": (
            prior_resolution[
                "candidate_selected_operating_point"
            ]
        ),
        "control_dev": prior_resolution[
            "control_dev"
        ],
        "candidate_dev": prior_resolution[
            "candidate_dev"
        ],
        "delta": prior_resolution["delta"],
    }

    source_revisions = set()
    resolution_rows = [canonical]
    for (
        condition,
        control_name,
        candidate_name,
    ) in NEW_RESOLUTION_PAIRS:
        control = _lane(root, control_name)
        candidate = _lane(
            root,
            candidate_name,
        )
        if (
            control["seed_condition"]
            != condition
            or candidate["seed_condition"]
            != condition
        ):
            raise RuntimeError(
                "seed-condition mismatch: "
                + condition
            )
        source_revisions.update(
            (
                control["source_revision"],
                candidate["source_revision"],
            )
        )
        row = _pair(
            control,
            candidate,
        )
        row["condition"] = condition
        row["source"] = (
            "relational-evidence screen"
        )
        resolution_rows.append(row)

    unary = _lane(
        root,
        "unary_code_canonical",
    )
    relational = _lane(
        root,
        "relational_code_canonical",
    )
    source_revisions.update(
        (
            unary["source_revision"],
            relational["source_revision"],
        )
    )
    relational_pair = _pair(
        unary,
        relational,
    )
    relational_pair["guardrails_pass"] = (
        _guardrails(
            relational_pair["delta"]
        )
    )
    relational_pair["verdict"] = (
        _relational_verdict(
            relational_pair["delta"]
        )
    )

    if len(source_revisions) != 1:
        raise RuntimeError(
            "new lanes do not share one immutable revision"
        )

    (
        stability_verdict,
        stability_summary,
    ) = _fine_code_stability(
        resolution_rows
    )

    if (
        stability_verdict
        == "STABLE_FINE_CODE_ACCESS"
    ):
        if (
            relational_pair["verdict"]
            == "RELATIONAL_EVIDENCE_SIGNAL"
        ):
            routing = (
                "PROMOTE_RELATIONAL_EVIDENCE_TO_STABILITY_SCREEN"
            )
        elif (
            relational_pair["verdict"]
            == "RELATIONAL_EVIDENCE_SIGNAL_WITH_COST"
        ):
            routing = (
                "QUARANTINE_RELATIONAL_SIGNAL_WITH_COST"
            )
        else:
            routing = (
                "FREEZE_FINE_CODE_FOUNDATION_CONTINUE_ARCHITECTURE_SEARCH"
            )
    elif (
        stability_verdict
        == "POSITIVE_BUT_SUBTHRESHOLD_FINE_CODE_ACCESS"
    ):
        routing = (
            "HOLD_FINE_CODE_FOUNDATION_NO_PROMOTION"
        )
    else:
        routing = (
            "REASSESS_FINE_CODE_FOUNDATION"
        )

    return {
        "schema_version": 1,
        "status": "complete",
        "evidence_role": "DEVELOPMENT",
        "source_revision": next(
            iter(source_revisions)
        ),
        "profile_id": prior["profile_id"],
        "fine_code_stability": {
            "conditions": resolution_rows,
            "summary": stability_summary,
            "verdict": stability_verdict,
        },
        "relational_evidence": (
            relational_pair
        ),
        "routing": routing,
        "test_loaded": False,
        "automatic_test_authorized": False,
        "automatic_mimiciv_authorized": False,
        "automatic_relational_stability_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__
    )
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
    )
    args = parser.parse_args()

    result = run(
        args.root.resolve()
    )
    text = (
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )
    if args.output:
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            text,
            encoding="utf-8",
        )
    print(text, end="")


if __name__ == "__main__":
    main()
