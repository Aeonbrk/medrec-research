<!-- markdownlint-disable MD013 -->

# Failure Record: CRC-PS R006 action family

Source boundary: `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. Every archive path in this record refers to that revision.

## Decision

The preregistered CRC-PS action family is `NO_GO_FOR_ACTION_FAMILY`. It produced no certified lambda, so the route has no deployable prescription-set action rule and R007 must not run from this route.

## What was tested

R006 calibrated a fixed prescription-set action family on evaluation-only outputs. Acceptance required a finite-grid upper confidence bound plus count, utility, coverage, and non-empty guards. The analysis used no test data, and restricted rows remained on the remote host. Archive evidence: `research-wiki/experiments/crc_ps_r006_failure_analysis.md` and `refine-logs/CRC_PS_R006_FAILURE_ANALYSIS.md`.

## Why it failed

Raw mean loss met the risk budget and row-level guards passed for `15/31` lambdas, but finite-grid acceptance held for `0/31`. The best row had mean loss `0.055483` under `alpha=0.06`, while its corrected UCB was `0.090959`; `selected_lambda` remained null. Archive evidence: `research-wiki/experiments/crc_ps_r006_failure_analysis.md` at commit `9971464253c556345262b22ed6d44b2cc14c9da8`.

The action family became feasible at higher lambda values, but the finite-sample correction left no certificate margin. Aggregate recomputation of the restricted calibration output matched the public summary up to floating-point noise and exposed no artifact-status rows. The archive therefore classifies this as a statistical certificate failure, not a software or data repair case. Archive evidence: `refine-logs/CRC_PS_R006_FAILURE_ANALYSIS.md`.

## Reusable residue

- A stop rule that distinguishes raw empirical feasibility from finite-grid certification.
- A guarantee boundary limited to the preregistered bounded loss and its assumptions.
- Public-safe aggregate reporting that can validate restricted computation without exporting patient-level rows.
- Required future controls for count, coverage, under-prescription, strong utility filling, and non-conformal count-matched thresholds.

## Non-revival boundary

Do not rerun R007, inspect test results, or tune R006 in place. Changing `alpha`, `delta`, the lambda grid, calibrated loss, utility floor, count rule, or guards creates a new preregistered route that needs a new novelty check, refinement, and experiment plan. Archive evidence: `research-wiki/ideas/crc_ps.md`.

## Uncertainty

This record invalidates the archived CRC-PS action family and guarantee claim, not conformal risk control in general. The archive does not show whether a materially different, newly preregistered CRC-derived route could pass, nor whether such a route would survive novelty and strong-control review. Archive evidence: `research-wiki/claims/crc_ps_current_route_deployable_action_rule.md`.
