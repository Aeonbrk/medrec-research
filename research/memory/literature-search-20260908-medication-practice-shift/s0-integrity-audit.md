# S0 Integrity Audit

## Verdict: `INTEGRITY_AUDIT_PASS`

Mode: `full` (temporal/quarantine, adaptation entitlement, numeric, and claim audit).

## Artifacts checked

- Frozen S0 protocol SSOT.
- `s0-summary.json` and `s0-decision.md`.
- Restricted freeze manifest identity: `9622463c4b4e0caf34402c5197204c33478dd2a06c013436f20946842ef22ad7`.

## Temporal / quarantine

- `year(decision_time) == anchor_year` is the retained-burst rule.
- Exact groups are G0+G1 source, G2 target, and G3+G4 quarantined future reserve.
- G3/G4 clinical data and aggregates were not inspected.
- R0 Holdout and historical project test split were not inspected.
- TargetAudit was not read before the restricted freeze manifest; it was evaluated once afterward.

## Adaptation entitlement

- SourceTrain was the only cohort used for neural weight fitting and source priors.
- TargetPriorBuild supplied only the target marginal prior.
- TargetBiasTune supplied only the scalar alpha selection.
- No target-era neural weight update, learned alpha, adapter, temperature, or transition model was used.
- Alpha grid was exactly `{0.0, 0.25, 0.5, 1.0, 2.0}` with smaller-alpha tie-breaking.

## Numeric consistency

- R_source = `0.43104278290888748`.
- R_target_base = `0.44036989331820281`.
- R_target_bias = `0.44416384460526509`.
- G_base = `-0.0093271104093153312`, CI `['-0.01458539125513871', '-0.0035238891533313781']`.
- G_bias = `-0.013121061696377612`, CI `['-0.018354254930725351', '-0.0074505314275973167']`.
- Recovery = `N/A`.
- Conditions 1–3 = `True`, `False`, `False`.
- Confidence intervals use 2,000 independent patient-clustered two-sample bootstrap replicates with seed 260908; the two target methods share identical TargetAudit patient multiplicities per replicate.

## Claim boundary

- No causal practice-drift claim is made.
- The result is limited to residual temporal deployment shift under the frozen MIMIC-IV order-time task and prior-bias control.

No-invention status: `PASS`; no unsupported number, patient-level artifact, or new scientific direction was added.

Next CCFA owner: `ccf-pipeline-orchestrator`.
