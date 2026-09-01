<!-- markdownlint-disable MD013 -->

# Failure Record: EG-TER repair route

Source boundary: `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. Every archive path in this record refers to that revision.

## Decision

The EG-TER repair-policy route is failed. `D_therapeutic` remains reusable only as a scoped continuous diagnostic metric after hard-safety feasibility has been enforced.

## What was tested

An initial minimal pilot compared the EG-TER repair policy with ATC-only and indication-only policies. The route gate then gave every non-oracle policy the same contraindication, severe-DDI, and coverage-loss filter and compared ranking behavior inside that leveled feasible set. Archive evidence: `research-wiki/experiments/eg_ter_e4_minimal_pilot.md` and `research-wiki/experiments/eg_ter_e5_robustness.md`.

## Why it failed

After filter leveling, Full EG-TER and HardSafety+Indication tied on certified repair recall `1.0000`, unsafe repair rate `0.0000`, abstention precision `1.0000`, and false abstention rate `0.0000`. Mean `D_therapeutic` favored Full EG-TER only slightly, `0.3355` versus `0.3389`, with bootstrap 95% CI for the paired difference `[-0.005009, -0.001984]`. Archive evidence: `research-wiki/experiments/eg_ter_e5_robustness.md` at commit `9971464253c556345262b22ed6d44b2cc14c9da8`.

The shared hard filter absorbed the binary repair advantage seen against the earlier baselines. The remaining distortion difference supports a measurement role, not an independently effective solver. This is the Hard-Safety Baseline Trap. Archive evidence: `research-wiki/claims/hard_safety_baseline_trap.md` and `refine-logs/EG_TER_E5_ROBUSTNESS_ANALYSIS.md`.

## Reusable residue

- `D_therapeutic` as a continuous treatment-drift diagnostic, with the archived validation caveats attached.
- A leveled hard-filter comparison protocol for contraindication, severe-DDI, and coverage feasibility.
- The E4-to-E5 sequence as a negative case showing how a weak-baseline pilot can overstate policy value.

## Non-revival boundary

Do not use E4 as solver evidence and do not proceed to solver planning under the recorded policy design. A future repair route needs a new mechanism that improves repair quality beyond equally hard-filtered baselines, not only a small distortion margin. Archive evidence: `research-wiki/ideas/eg_ter.md`.

## Uncertainty

The metric-validity evidence is narrow construct validation over synthetic and adversarial prescription-pair cases. The archive records a local conservative fallback for one labeler, overlap between evidence-packet fields and graph concepts, and no external clinician or pharmacist validation. It therefore supports neither therapeutic equivalence nor clinical safety. Archive evidence: `research-wiki/claims/eg_ter_metric_validity.md` and `research-wiki/experiments/eg_ter_metric_validity_week1.md`.
