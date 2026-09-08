<!-- markdownlint-disable MD013 -->

# Failure Memory: Medication Practice-Shift S0 — No Material Forward Degradation

## Verdict

`FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`

Execution HEAD: `80378462aa04f459d80b99f7755a9f59f94a0640`

Integrity audit: `INTEGRITY_AUDIT_PASS`

## Decisive evidence

Under the frozen MIMIC-IV 3.1 temporal protocol, only bursts satisfying `year(decision_time) == patient.anchor_year` were retained. Source era used G0+G1 and the target era used G2. G3/G4 remained uninspected.

The frozen SourceOnly model did not degrade in the target era:

- `R_source = 0.4310427829`;
- `R_target_base = 0.4403698933`;
- `G_base = R_source - R_target_base = -0.0093271104`;
- 95% patient-clustered bootstrap CI for `G_base`: `[-0.0145853913, -0.0035238892]`.

The simple target-era medication-prior logit correction increased target Recall@5 further:

- selected `alpha = 1.0`;
- `R_target_bias = 0.4441638446`;
- `G_bias = -0.0131210617`;
- 95% CI: `[-0.0183542549, -0.0074505314]`.

Condition 1 passed. Conditions 2 and 3 failed. Recovery is undefined because there was no positive source-to-target degradation to recover.

## Interpretation

The tested chronological split does not support the premise that a source-era medication-order predictor suffers a material forward-period performance drop. The sign is opposite: target-era Recall@5 is higher than source-era Recall@5, and a simple target-prior correction improves it further.

Therefore a temporal adaptation method is not scientifically admitted under this frozen setting.

## Reusable constraint

> Do not build a deployment-shift adaptation method until the project first demonstrates an actual material degradation under a leakage-safe chronological protocol and after giving simple marginal-prior correction a fair chance.

Chronological difference alone is not evidence of harmful deployment shift.

## Exact closure boundary

Closed under the recorded premise:

- MIMIC-IV 3.1;
- exact anchor-year matching;
- G0+G1 source versus G2 target;
- patient-disjoint source train/tune/audit and target prior-build/bias-tune/audit;
- frozen causal medication-order task;
- SourceOnly model with target-era per-medication logit-bias control;
- Recall@5-based S0 gate.

Do not rescue this route by changing year groups, removing anchor-year matching, switching to eICU, adding new clinical features, weakening the prior control, or running S0b.

## Non-claims

This failure does not establish that prescribing practice never changes, that other institutions have no shift, or that every medication-recommendation task is temporally stable. It establishes only that the preregistered project-local forward-degradation premise was absent in the tested environment.

## Quarantine status

- G3/G4 future reserve: untouched;
- R0 Holdout: untouched;
- historical project test split: untouched.
