<!-- markdownlint-disable MD013 -->

# Gate 01 Design-Integrity Audit — Idea 007

## Audit status

- **Auditor**: `ccf-integrity-auditor`
- **Audit mode**: `claim-audit / pre-execution design integrity`
- **Idea**: [`../README.md`](../README.md)
- **Protocol audited**: [`gate-01-protocol.md`](gate-01-protocol.md)
- **Audit date**: `2026-09-09`
- **Audit basis**: protocol text and the admitted R1/R2/R3 packet only
- **Response outcomes accessed**: `NO`
- **G3/G4, R0 Holdout, historical project test accessed**: `NO`
- **Verdict**: `DESIGN_INTEGRITY_PASS`

This is an independent design audit. It does not inspect response coverage,
patient data, split membership, model outputs, or any training result. It checks
whether the frozen protocol can answer the admitted Idea-007 question without
changing the question after results appear.

## Claim-evidence matrix

| Design claim / requirement | Protocol evidence | Audit finding |
| --- | --- | --- |
| Scientific question is the admitted Idea 007 object | Sections 1, 2: medication-in-context post-administration physiological values are training-only supervision for a strictly pre-order candidate-medication student | `SUPPORTED_BY_DESIGN` |
| Claim boundary is observational and non-causal | Section 1 explicitly excludes treatment effect, causal response, efficacy, therapeutic benefit, counterfactual outcome, clinical optimality, and individualized causal benefit | `SUPPORTED_BY_DESIGN` |
| R1 removes only the claimed medication-specific response semantics | Sections 6, 7.1: `V3` and `V8` share `E_rec`, `A`, anchor, window, values/masks, student, latent size, teacher shell/parameter count, loss, optimizer, and updates; focal identity and medication-specific construction are removed only in `V3` | `SUPPORTED_BY_DESIGN / PRIMARY KILLER` |
| R2 separates values from monitoring policy | Sections 3, 7.2: `V6` receives identical `A`, window, availability/frequency pattern, student, teacher capacity, loss, and updates but no physiological values or value-derived summary | `SUPPORTED_BY_DESIGN / PRIMARY KILLER` |
| R3 equal support and positive-only semantics hold | Sections 2, 6, 7.3: one fixed `A(e)`, full `E_rec` recommendation objective, unsupported examples retained, no unchosen-medication target, no differential recommendation weighting | `SUPPORTED_BY_DESIGN / GATE_INVALIDATOR` |
| Teacher capacity is comparable | Section 5.2 fixes one teacher shell, input schema, sequence length, parameter count, latent dimension, optimizer, and update budget across `V3`–`V8` | `SUPPORTED_BY_DESIGN` |
| Required killer family is complete | Section 7 includes Strict Base, Base + Pre-Order Physiology, medication-ablated generic future, static prototype, response shuffle, Monitoring-Mask-Only, Generic KD, and Proposed | `SUPPORTED_BY_DESIGN` |
| Coverage preflight is mechanical, not exploratory | Section 3 permits only linkage, window availability, masks, and aggregate support/concentration; it forbids outcomes, training, representation fitting, metric comparison, and parameter choice | `SUPPORTED_BY_DESIGN` |
| Low or concentrated support stops before training | Sections 3.1–3.2 freeze global/partition count, coverage, medication, and patient concentration floors plus a terminal stop code | `SUPPORTED_BY_DESIGN` |
| Chronology and deployment contract are unambiguous | Sections 2, 4, 5, and 8 freeze the order anchor, 24-hour window, patient-disjoint partitions, Train/Dev/Audit order, pre-order normalization, and inference inputs | `SUPPORTED_BY_DESIGN` |
| Dev cannot tune the outer Gate | Section 8 permits only the same fixed checkpoint rule on Dev; all metrics, thresholds, splits, architecture, and stop rules are frozen before Audit | `SUPPORTED_BY_DESIGN` |
| Audit/Test/Holdout permissions are correct | Section 4 allows one frozen Audit read only after the evaluation freeze and gives zero permission to G3/G4, R0 Holdout, and historical test | `SUPPORTED_BY_DESIGN` |
| `materially`, `comparable`, and `≈` are executable | Section 9 fixes `delta_practical = 0.005`, three seeds, 2,000 two-level patient/seed bootstrap replicates, CI construction, material-win rule, comparability rule, and inconclusive stop | `SUPPORTED_BY_DESIGN` |
| Kill-first decisions are mechanical | Section 9 maps every comparable killer to a terminal stop and requires a material win against every applicable killer plus Base non-inferiority | `SUPPORTED_BY_DESIGN` |
| No-rescue boundary is frozen | Section 10 forbids larger teachers, backbone changes, window/definition changes, extra modalities, subgroup mining, post-hoc features, favorable-seed selection, and new splits | `SUPPORTED_BY_DESIGN` |
| Protocol contains no results or fabricated evidence | Status and Section 11 state `DESIGNED_NOT_EXECUTED`; no result tables, values, predictions, or response outcomes are present | `SUPPORTED_BY_DESIGN` |

## 1. Equal-entitlement audit

`PASS`.

The primary R1 subtraction is not merely a weaker target. The Proposed and
Medication-Ablated Future rows share the complete recommendation example set,
positive administered support, administration anchor, future window, six-channel
value/mask availability, deployable student, latent dimensionality, teacher shell
and parameter count, auxiliary weight, optimizer, seed set, and update budget. The
candidate medication remains in the student for both variants, so the comparison
does not silently change the MedRec task.

Monitoring-Mask-Only receives the same future measurement process and support but
no value tensor or value-derived statistic. Static Prototype and Response Shuffle
preserve support and their stated marginal structures while removing patient-level
response correspondence or patient-specific values. Unsupported examples remain in
the recommendation objective for every privileged row.

No unequal entitlement is left as a tunable implementation choice. A discovered
mismatch is a Gate-invalidating stop, not a repair path.

## 2. Leakage and chronology audit

`PASS`.

The protocol fixes `t(e)`, the first valid administration anchor after the order,
the 24-hour future window, and `A(e)` before any execution. The student sees only
strictly pre-order state, pre-order physiology, and candidate medication. Future
administrations, values, masks, discharge-coded information, and future-derived
normalization statistics are explicitly forbidden on the student path and absent
at inference.

The patient hash split is frozen before the mechanical support preflight. Dev is
limited to the one fixed checkpoint rule, Audit is opened once after all choices
are frozen, and G3/G4, R0 Holdout, and historical test remain quarantined.

## 3. Decision-rule audit

`PASS`.

The primary endpoint is fixed patient-mean Recall@5 at a fixed `K=5`. The practical
margin is fixed at `0.005` absolute Recall@5. A Proposed win requires both the
margin and a positive 95% bootstrap lower bound. A control is `≈` Proposed only
when the 95% upper bound shows that any Proposed advantage is at most the margin.
An interval that cannot establish either statement is explicitly inconclusive and
terminates admission; it cannot be turned into a favorable result by a secondary
metric or subgroup.

The same patient and seed multiplicities are used within each paired contrast, and
the seed set, bootstrap count, bootstrap seed, and interval definition are frozen
before Audit. The rule therefore remains executable without looking at outcomes to
choose a threshold.

## 4. No-rescue and scope audit

`PASS`.

Every requested terminal condition is represented: medication-ablated/generic
future, Monitoring-Mask-Only, Response Shuffle, Static Medication Response
Prototype, richer pre-order physiology, Generic KD, insufficient/concentrated
support, student leakage, unmatched support/sample entitlement, non-inferiority
failure, and statistical inconclusiveness. The protocol forbids the exact rescue
families named by the admission packet. No second response definition, window,
split, modality, backbone, or subgroup is available under Idea 007.

## 5. No-invention and privacy audit

`PASS`.

The artifact contains no observed support count, outcome, prediction, weight,
patient row, or expected direction. The support floors are protocol constants, not
claims about the data. Any future public artifact is restricted to aggregate,
gate-approved evidence; private data and split membership remain outside Git.

## Audit verdict

`DESIGN_INTEGRITY_PASS`

The Gate-01 protocol is fully determined before training and is aligned with the
admitted Idea 007 object, frozen R1/R2/R3 equal-entitlement semantics, chronology
and deployment contract, mechanical support stop, practical/statistical decision
rule, and no-rescue boundary. No protocol change is required. This verdict does
not authorize response-coverage execution, model training, Audit access, or any
scientific result collection.

## Next state and owner

```text
Stage: IDEA_007_GATE_01_DESIGN_FROZEN_AUDITED_TRAINING_NOT_AUTHORIZED
Idea 007: created/admitted
Gate 01: design frozen / integrity audit passed / not executed
Training: NOT AUTHORIZED
Next owner: explicit future execution authorization only; no execution in this turn
```
