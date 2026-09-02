<!-- markdownlint-disable MD013 -->

# Reusable lessons

Source boundary: `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. Each path below refers to that revision.

## Put the strongest simple control before the method story

A weak scalar-penalty grid made EGSF look context-sensitive. The expanded global fixed-lambda control removed that interpretation. Future selector work should predeclare a broad scalar-control search, calibrate utility, enforce strict and exact count controls, and require positive subgroup confidence intervals before attributing value to context conditioning. Archive evidence: `research-wiki/experiments/egsf_e3b_strong_followup.md` and `idea-stage/EGSF_PIVOT_IDEA_DISCOVERY.md`.

## Level feasibility rules across policies

Safety-repair comparisons are not informative when the proposed policy alone receives the strongest contraindication, severe-DDI, and coverage filters. Apply the same non-oracle feasibility filter to each policy, then compare ranking or repair value inside the same candidate set. Archive evidence: `research-wiki/claims/hard_safety_baseline_trap.md` and `research-wiki/experiments/eg_ter_e5_robustness.md`.

## Separate metric validity from policy superiority

A diagnostic distance can rank substitutions sensibly while adding no independent repair value after feasibility is leveled. Carry `D_therapeutic` only as a scoped treatment-drift metric; do not use its construct-validity evidence to justify a solver. Archive evidence: `research-wiki/claims/eg_ter_metric_validity.md` and `research-wiki/ideas/eg_ter.md`.

## Preserve a passed gate's final lifecycle

An early pass can establish a narrow fact while failing to establish the route that motivated it. EGSF E3-Minimal and EG-TER E4 are historical positive gates whose method interpretations were later overturned by stronger controls. Record the pass and the superseding evidence together; never recast either as a surviving success. Archive evidence: `research-wiki/claims/egsf_minimal_selector.md`, `research-wiki/claims/eg_ter_repair_pilot_asymmetric_info.md`, `research-wiki/experiments/egsf_e3b_strong_followup.md`, and `research-wiki/experiments/eg_ter_e5_robustness.md`.

## Keep diagnostics out of deployment claims

Candidate-frontier existence, proxy-risk strata, and a full-method audit can motivate a control or research question without producing a deployable policy. Label each artifact as diagnostic, metric, audit, or action evidence before carrying it forward. Archive evidence: `research-wiki/claims/egsf_dynamic_budget_motivated.md`, `research-wiki/claims/egsf_frontier_exists.md`, and `research-wiki/claims/kdd2025_not_equivalent_to_risk_budgeted_deployment.md`.

## State guarantees at the calibrated target

A finite-sample bound on a preregistered loss does not certify clinical safety, individual medication correctness, count preservation, confidence calibration, or therapeutic equivalence. Name the bounded loss, assumptions, action family, and guard conditions each time the guarantee is discussed. Archive evidence: `research-wiki/claims/crc_ps_bounded_loss_only.md`.

## Treat a failed gate as a route boundary

When a preregistered gate returns no accepted action, tuning the risk budget, grid, loss, utility floor, count rule, or guards is not a repair of the recorded experiment. It is a new route with new novelty and preregistration obligations. Archive evidence: `research-wiki/experiments/crc_ps_r006_failure_analysis.md` and `refine-logs/CRC_PS_R006_FAILURE_ANALYSIS.md`.

## Preserve residue without promoting it

Failed routes can leave useful assets: EGSF left a strong-control diagnostic package, EG-TER left a continuous distortion metric and a leveled hard-filter protocol, and CRC-PS left a calibration stop rule and guarantee boundary. Reuse those assets as controls or diagnostics until new evidence supports a new claim. Archive evidence: `ARCHITECTURE.md`, `docs/PROJECT_SENSE.md`, and the three Failure Records under `failures/` ([CRC-PS](failures/crc-ps-r006--conformal-risk-certificate-exhaustion.md), [EG-TER](failures/eg-ter-repair--hard-safety-filter-baseline-trap.md), [EGSF](failures/egsf-selector--global-scalar-reranking-dominance.md)).

## Keep archive logistics out of active research records

Portable operational lessons are limited to the current repository's remote-execution and privacy contracts. Do not copy archive-specific hosts, paths, sockets, environment names, raw results, or traces into research evidence. Archive evidence: `findings.md` and the source-boundary exclusions in `archive-evidence-index.md`.

## Keep clinical language narrower than proxy evidence

Retrospective labels, DDI proxies, contraindication rules, and synthetic or adversarial cases can falsify a method story or test software logic. They cannot by themselves establish patient benefit, prescribing safety, or therapeutic equivalence. Archive evidence: `docs/PROJECT_SENSE.md`, `research-wiki/claims/eg_ter_metric_validity.md`, and `research-wiki/claims/crc_ps_bounded_loss_only.md`.

## Separate point-estimate fidelity from directional relationships

In Reproduction Mode, validating directional advantages (e.g. Model A > Model B) does not establish reproduction of the published point estimates when observed means fall outside the reported $2\sigma$ statistical bounds. A directional pass with point interval misses must be honestly classified as `completed_mismatch`, not full reproduction. See `research/baselines/failures/safedrug-four-model-table2-mismatch-2026-08-26.md`.

## Distinguish percentage-point differences from relative percentages

Report metric shifts explicitly: an absolute change in Jaccard from $0.5017$ to $0.5148$ is a $+1.312$ percentage-point change ($+0.01312$ absolute), which represents a $+2.62\%$ relative increase. Never report $+1.312$ percentage points as "$+1.31\%$ improvement" without clarifying whether the metric is points or relative.

## Use validation-only selection for candidate model lanes

When upstream literature explores multiple candidate hyperparameters (such as learning rates) without pre-declaring one canonical configuration, train all disclosed candidate lanes and select the final model using validation metrics only (e.g. max validation Jaccard, min validation DDI). Never evaluate non-selected candidates on the test set or leak test metrics into model selection.

## Document minimal hardware compatibility deviations explicitly

When running archived scientific baselines on newer hardware (such as RTX 3090 / Ampere requiring CUDA 11+ instead of recorded CUDA 10.2), keep scientific package versions identical and record the necessary CUDA/driver runtime deviation as an environment compatibility deviation, not exact historical reproduction.

## Residual Oracle headroom is not evidence for a proposed mechanism

Establishing that an oracle routing or revision allocation has substantial headroom over trivial baselines (e.g. random or risk-only) proves that heterogeneity exists, but does not validate any specific proposed selection mechanism. When a strong observable control (such as the base recommender's own confidence) explains substantial variance, the proposed additional signal must demonstrate preregistered incremental information beyond that control before mechanism-specific modeling or architectural expansion is justified. Evidence: Idea 001 Gate 01 (`gate-summary.json`) vs Gate 02 (`gate-02-summary.json`).
