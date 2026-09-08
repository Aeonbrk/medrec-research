# M0 — Event-Sourced Regimen-Edit Admission

## Verdict: `FAIL_M0_NO_INCREMENTAL_EVENT_EDIT_STRUCTURE`

- Gate: `M0_EVENT_SOURCED_EDIT_ADMISSION`
- MIMIC-IV: `3.1`
- Stage: `PRE_IDEA_EVENT_EDIT_M0`
- Repository revision: `62fd9ec383816d290d8ce0e214a1e8b0b222f8f3`
- Actual batch size: `2048`
- Freeze manifest SHA256: `N/A`
- Integrity audit: `INTEGRITY_AUDIT_PASS`

## Semantic boundary

The target is a raw provider-order workflow mark `(transaction_type, medication)` with action vocabulary `New / Change / D/C`. It is not a verified clinical or therapeutic intention. Medication metrics measure fidelity to mapped observed order workflow, not clinical benefit.

The pre-order state is an operational, execution-confirmed regimen state reconstructed from prior eMAR evidence and causal D/C pointers. It is not a pharmacokinetic concentration estimate.

## Phase A admission

- Visibility: `EditTrain+EditTune only; EditAudit withheld until freeze`
- Overall support: `True`
- Per-action support: `True`
- Change/D/C pre-order consistency: `False`
- Distributed action semantics: `True`
- Phase A: `False`

| Partition | Patients | Bursts | Mapped target events | Mapped target marks |
| :--- | ---: | ---: | ---: | ---: |
| EditTrain | 78172 | 1104963 | 2490173 | 2242799 |
| EditTune | 9904 | 140707 | 317533 | 286133 |
| EditAudit | 0 | 0 | 0 | 0 |

## Phase A exact values

- Overall mapped events/patients: `2807706` / `88076` (floor `250000` / `10000`; PASS `True`).
- `New` mapped events/patients: `2064107` / `88052` (floor `20000` / `2000`; PASS `True`).
- `Change` mapped events/patients: `278259` / `54519` (floor `20000` / `2000`; PASS `True`).
- `D/C` mapped events/patients: `465340` / `60517` (floor `20000` / `2000`; PASS `True`).
- `Change` active-before: `47940` / `278259` = `0.17228553254342177` (floor `0.70`; PASS `False`).
- `D/C` active-before: `74143` / `465340` = `0.15933081187948597` (floor `0.70`; PASS `False`).
- Distributed concepts: `103` (floor `50`; PASS `True`).

## Frozen conditions

| Condition | PASS |
| :--- | :--- |
| phase_a_all_admission_conditions | False |
| models_trained | False |
| m0b_not_run | True |
| idea_007_not_created | True |

## Quarantine and routing

- EditAudit formal access occurred exactly once after freeze: `False`.
- G3/G4 future reserve: untouched; no event, aggregate, feature, prediction, or metric was inspected.
- R0 Holdout: untouched.
- Historical project test split: untouched.
- Next state: `NO_HIGH_VALUE_DIRECTION_YET`.
- Next CCFA owner: `ccf-pipeline-orchestrator`.

M0 is a bounded premise-selection gate. Even PASS does not establish a publishable method, clinical utility, causal treatment reasoning, or superiority to state-of-the-art medication recommendation models.
