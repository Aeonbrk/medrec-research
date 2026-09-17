"""Summarize and decide on the DCPM vs SharedPrecedent mechanism comparison.

Decision Rule:
Primary delta: ΔJ = Jaccard(DCPM) - Jaccard(SharedPrecedent)
- ΔJ > +0.004: MEANINGFUL mechanism signal
- ΔJ ~ +0.010 (>= +0.008): STRONG mechanism signal
- ΔJ <= +0.002: KILL mechanism
Safety override:
- Also accept a genuine ~-0.010 DDI improvement with J loss <= 0.005,
  provided medication count does not explain it.

Enforcement:
No DCPM-v2, K search, temperature search, extra loss, or extra seed
if the mechanism is negative.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def summarize(
    dcpm_result_path: Path, control_result_path: Path, output_path: Path | None = None
) -> dict[str, Any]:
    dcpm_data = json.loads(dcpm_result_path.read_text(encoding="utf-8"))
    control_data = json.loads(control_result_path.read_text(encoding="utf-8"))

    j_dcpm = float(dcpm_data["patient_macro_jaccard"])
    j_ctrl = float(control_data["patient_macro_jaccard"])
    delta_j = j_dcpm - j_ctrl

    f1_dcpm = float(dcpm_data["patient_macro_f1"])
    f1_ctrl = float(control_data["patient_macro_f1"])
    delta_f1 = f1_dcpm - f1_ctrl

    prauc_dcpm = float(dcpm_data["patient_macro_prauc"])
    prauc_ctrl = float(control_data["patient_macro_prauc"])
    delta_prauc = prauc_dcpm - prauc_ctrl

    ddi_dcpm = float(dcpm_data["ddi_rate"])
    ddi_ctrl = float(control_data["ddi_rate"])
    delta_ddi = ddi_dcpm - ddi_ctrl

    med_dcpm = float(dcpm_data["average_medication_count"])
    med_ctrl = float(control_data["average_medication_count"])
    delta_med = med_dcpm - med_ctrl

    # Decision evaluation
    if delta_j >= 0.008:
        verdict = "STRONG_MECHANISM_SIGNAL"
        verdict_reason = (
            f"ΔJ = {delta_j:+.6f} >= +0.008 (~+0.010): strong precedent relevance signal"
        )
    elif delta_j > 0.004:
        verdict = "MEANINGFUL_MECHANISM_SIGNAL"
        verdict_reason = (
            f"ΔJ = {delta_j:+.6f} > +0.004: meaningful candidate-medication precedent signal"
        )
    elif delta_ddi <= -0.008 and delta_j >= -0.005 and abs(delta_med) < 1.0:
        verdict = "MEANINGFUL_SAFETY_IMPROVEMENT"
        verdict_reason = (
            f"ΔDDI = {delta_ddi:+.6f} (genuine safety improvement) with acceptable Jaccard delta {delta_j:+.6f} "
            f"not explained by under-prescription (ΔAvgMed = {delta_med:+.4f})"
        )
    elif delta_j <= 0.002:
        verdict = "KILL_DCPM_MECHANISM"
        verdict_reason = (
            f"ΔJ = {delta_j:+.6f} <= +0.002: drug-conditioned precedent relevance falsified"
        )
    else:
        verdict = "WEAK_SIGNAL_DO_NOT_PROMOTE"
        verdict_reason = f"+0.002 < ΔJ = {delta_j:+.6f} <= +0.004: insufficient signal to promote"

    summary = {
        "schema_version": 1,
        "protocol": "MIMIC-III canonical-131 Paper Dev Screen",
        "scientific_question": (
            "Does candidate-medication-specific relevance over cross-patient Train precedents "
            "improve prediction over one shared patient-level precedent weighting, when both arms "
            "receive identical local evidence, memory cases, peer labels, parameters, and optimization?"
        ),
        "comparison": "dcpm_minus_shared_precedent",
        "seed": dcpm_data.get("seed", 20260921),
        "source_revision": dcpm_data.get("source_revision", ""),
        "parameter_count_dcpm": dcpm_data.get("parameter_count"),
        "parameter_count_control": control_data.get("parameter_count"),
        "dcpm": {
            "variant": "dcpm",
            "mechanism": "candidate-medication-specific query q_im = LN(W_h h_i + W_l l_im + W_d d_m)",
            "selected_epoch": dcpm_data.get("selected_epoch"),
            "selected_threshold": dcpm_data.get("selected_operating_point"),
            "dev_jaccard": j_dcpm,
            "dev_f1": f1_dcpm,
            "dev_prauc": prauc_dcpm,
            "dev_ddi": ddi_dcpm,
            "dev_avg_med": med_dcpm,
        },
        "shared_precedent": {
            "variant": "shared_precedent",
            "mechanism": "shared patient query q_i = LN(W_h h_i + W_l l_bar_i + W_d d_bar)",
            "selected_epoch": control_data.get("selected_epoch"),
            "selected_threshold": control_data.get("selected_operating_point"),
            "dev_jaccard": j_ctrl,
            "dev_f1": f1_ctrl,
            "dev_prauc": prauc_ctrl,
            "dev_ddi": ddi_ctrl,
            "dev_avg_med": med_ctrl,
        },
        "deltas": {
            "delta_jaccard": delta_j,
            "delta_f1": delta_f1,
            "delta_prauc": delta_prauc,
            "delta_ddi": delta_ddi,
            "delta_average_medication_count": delta_med,
        },
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "test_accessed": False,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize DCPM vs SharedPrecedent comparison")
    parser.add_argument("--dcpm-result", type=Path, required=True)
    parser.add_argument("--control-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    summary = summarize(args.dcpm_result, args.control_result, args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
