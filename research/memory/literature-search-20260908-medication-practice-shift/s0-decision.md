# S0 — Medication Practice-Shift Admission

## Verdict: `FAIL_S0_NO_MATERIAL_RESIDUAL_PRACTICE_SHIFT`

- MIMIC-IV version: `3.1`
- Stage: `PRE_IDEA_PRACTICE_SHIFT_S0`
- Freeze SHA256: `9622463c4b4e0caf34402c5197204c33478dd2a06c013436f20946842ef22ad7`
- Actual batch size: `2048`
- Source checkpoint epoch: `5`
- SourceTune BCE: `0.053861558136644713`
- Integrity audit: `INTEGRITY_AUDIT_PASS`

## Temporal and quarantine contract

- Retained only when `year(decision_time) == patient.anchor_year`.
- G3/G4 clinical events, bursts, labels, distributions, predictions, and performance were not inspected.
- R0 Holdout and the historical project test split were untouched.
- TargetAudit was accessed exactly once after freeze: `True`.

## Support floors

| Cohort | Patients | Bursts | Minimum patients | Minimum bursts | PASS |
| :--- | ---: | ---: | ---: | ---: | :--- |
| SourceTrain | 55755 | 681145 | 5000 | 100000 | True |
| SourceTune | 6978 | 83713 | 500 | 10000 | True |
| SourceAudit | 6985 | 86958 | 500 | 10000 | True |
| TargetPriorBuild | 2848 | 37281 | 500 | 10000 | True |
| TargetBiasTune | 2805 | 37535 | 500 | 10000 | True |
| TargetAudit | 22412 | 303207 | 2000 | 50000 | True |

## TargetBiasTune alpha grid

| alpha | Recall@5 | NDCG@5 | Hit@5 | micro-PRAUC |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.43690768254888696 | 0.34450193045001459 | 0.54437191954176101 | 0.17357825337430682 |
| 0.25 | 0.43942310124353834 | 0.34575465154210611 | 0.54738244305315042 | 0.17454173379999005 |
| 0.5 | 0.4404584476445435 | 0.34611932933668854 | 0.54855468229652327 | 0.17518125383213512 |
| 1 | 0.44296995237607423 | 0.34729643771035973 | 0.55119222059411221 | 0.1756304116147786 |
| 2 | 0.44244742333494691 | 0.34535063024291068 | 0.5510323697881977 | 0.17269584216648204 |

Selected alpha: `1` (tie-break: smaller alpha).

## Primary quantities

- R_source: `0.43104278290888748`
- R_target_base: `0.44036989331820281`
- R_target_bias: `0.44416384460526509`
- G_base: `-0.0093271104093153312`, 95% CI `['-0.01458539125513871', '-0.0035238891533313781']`
- G_bias: `-0.013121061696377612`, 95% CI `['-0.018354254930725351', '-0.0074505314275973167']`
- Recovery: `N/A`

| Condition | PASS |
| :--- | :--- |
| Condition 1 — support floors | True |
| Condition 2 — material base gap | False |
| Condition 3 — residual after prior bias | False |

S0 does not support a material forward temporal-deployment degradation or residual practice-shift premise under this frozen setting. It does not establish causal practice drift, clinical benefit, or method superiority.

Next state: `NO_HIGH_VALUE_DIRECTION_YET`

Next CCFA owner: `ccf-pipeline-orchestrator`
