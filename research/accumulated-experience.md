<!-- markdownlint-disable MD013 -->

# Accumulated Experience

This ledger carries the canonical scientific record from `New-Search` commit `9971464253c556345262b22ed6d44b2cc14c9da8`. It is complete for the archive's 6 idea cards, 11 experiment cards, and 12 claim cards. It is a curated memory, not a replacement for source records or raw artifacts.

## Reading the Ledger

The source's `status` or `stage` is a record-local field. The lifecycle column states the durable interpretation for new work in this repository.

| Lifecycle | Meaning |
| --- | --- |
| Supported / scoped | Evidence survives, but only within its stated diagnostic, metric, audit, or guarantee boundary. |
| Mixed / blocked | An executed experiment with mixed evidence whose decision or novelty gate did not clear; it is neither a method pass nor a later-superseded pass. |
| Passed then superseded | An earlier gate passed, but later evidence removed its broader route or method interpretation. |
| Invalidated / failed | A claim or route is closed at the archived boundary and cannot be revived by retuning it. |
| Proposed | A claim or experiment was recorded but not validated. |
| Historical backup | A non-active alternative retained only for its constraints and literature boundary. |

No archived result establishes clinical safety, therapeutic equivalence, patient benefit, baseline reproducibility, or Comparison Mode readiness.

## Ideas

| Node | Source stage / outcome | Lifecycle | Durable takeaway | Archive source |
| --- | --- | --- | --- | --- |
| `idea:boundary_evidence_eligibility_certificate` | `historical-backup` / `demoted-backup-route` | Historical backup | A formal evidence-eligibility function is defensible, but GiantMed, PACE-RAG, SafeRx-Agent, and RxEval create too much overlap for a current route. | `research-wiki/ideas/boundary_evidence_eligibility_certificate.md` |
| `idea:crc_ps` | `failed` / `negative-no-go` | Invalidated / failed | R006 certified no deployable lambda under the preregistered finite-grid UCB contract, closing the current action-family route. | `research-wiki/ideas/crc_ps.md` |
| `idea:differential_prescription_action_modeling` | `historical-alternative` / `maybe-go-secondary-route` | Historical backup | Reopen only for a stricter unsafe-addition, continuation, and omission failure decomposition that survives FLAME, HeteroMed, and TARM. | `research-wiki/ideas/differential_prescription_action_modeling.md` |
| `idea:eg_ter` | `failed` / `negative-historical-memory` | Invalidated / failed | The repair solver lost to a leveled hard-safety baseline; `D_therapeutic` and the hard-filter evaluation lesson remain reusable. | `research-wiki/ideas/eg_ter.md` |
| `idea:egsf` | `failed` / `historical-pivot-memory` | Invalidated / failed | Strong global fixed-lambda reranking beat bucket/context and exact-count selectors, ending the selector-method route. | `research-wiki/ideas/egsf.md` |
| `idea:safety_claim_audit_card` | `historical-backup` / `demoted-backup-route` | Historical backup | The audit/certificate concept is seeded by E3b but remains an unexecuted protocol, not a current recommender method. | `research-wiki/ideas/safety_claim_audit_card.md` |

## Experiments

| Node | Source status | Lifecycle | Durable takeaway | Archive source |
| --- | --- | --- | --- | --- |
| `exp:crc_ps_kdd2025_method_audit` | `completed` | Supported / scoped | KDD 2025 is a mandatory baseline threat but was not found equivalent to the fixed-base, risk-budgeted deployment contract. | `research-wiki/experiments/crc_ps_kdd2025_method_audit.md` |
| `exp:crc_ps_r006_failure_analysis` | `route-gate-failed` | Invalidated / failed | No lambda passed the finite-grid UCB rule: `0/31`, with best UCB `0.090959` against `alpha=0.06`; R007 must not proceed. | `research-wiki/experiments/crc_ps_r006_failure_analysis.md` |
| `exp:eg_ter_e4_minimal_pilot` | `completed` | Passed then superseded | The 50-case pilot beat weak ATC and indication baselines, but E5 later showed its binary advantage was a hard-filter-control artifact. | `research-wiki/experiments/eg_ter_e4_minimal_pilot.md` |
| `exp:eg_ter_e5_robustness` | `route-gate-failed` | Invalidated / failed | When all non-oracle methods shared contraindication, severe-DDI, and coverage filters, Full EG-TER tied HardSafety+Indication on all binary outcomes. | `research-wiki/experiments/eg_ter_e5_robustness.md` |
| `exp:eg_ter_metric_validity_week1` | `blind-validation-passed` | Supported / scoped | Frozen-label validation passed with Spearman `-0.8739`, triplet `0.9677`, false acceptance `0.0286`, and kappa `0.6059`; this supports the metric only. | `research-wiki/experiments/eg_ter_metric_validity_week1.md` |
| `exp:egsf_e0_1_dynamic_budget_audit` | `completed` | Supported / scoped | Train-derived risk strata showed stable proxy-risk shifts, motivating dynamic budgets but not clinical-safety labels or a selector method. | `research-wiki/experiments/egsf_e0_1_dynamic_budget_audit.md` |
| `exp:egsf_e1_train_prior_predictions` | `completed` | Passed then superseded | The bridge emitted parseable metrics and predictions, but its train-prior backbone was not valid final-pilot evidence. | `research-wiki/experiments/egsf_e1_train_prior_predictions.md` |
| `exp:egsf_e2_oracle_frontier_initial` | `completed` | Supported / scoped | The candidate pool contained matched-utility, lower-DDI alternatives, establishing an oracle-frontier diagnostic rather than a deployable selector. | `research-wiki/experiments/egsf_e2_oracle_frontier_initial.md` |
| `exp:egsf_e2b_controls_initial` | `completed` | Mixed / blocked | Post-hoc removal and shrinkage did not explain the gain at matched utility, but fixed-lambda reranking remained competitive, so the novelty gate did not clear and E3/V1 remained blocked. | `research-wiki/experiments/egsf_e2b_controls_initial.md` |
| `exp:egsf_e3b_strong_followup` | `completed` | Invalidated / failed | Validation-selected global lambda `30.0` beat bucket/context and exact-count selectors under calibrated utility and strict count constraints. | `research-wiki/experiments/egsf_e3b_strong_followup.md` |
| `exp:safety_claim_audit_minimal_case_study` | `planned` | Proposed | The proposed case study would use E3b controls to classify E3-Minimal as frontier-real, artifact-driven, or inconclusive without training a new model. | `research-wiki/experiments/safety_claim_audit_minimal_case_study.md` |

## Claims

| Node | Source status | Lifecycle | Durable takeaway | Archive source |
| --- | --- | --- | --- | --- |
| `claim:crc_ps_bounded_loss_only` | `supported` | Supported / scoped | Even a future successful route could claim only the calibrated bounded loss; R006 establishes no broader deployment, safety, confidence, count, or distortion guarantee. | `research-wiki/claims/crc_ps_bounded_loss_only.md` |
| `claim:crc_ps_current_route_deployable_action_rule` | `invalidated` | Invalidated / failed | R006 selected no lambda and therefore produced no finite-sample deployable action rule. | `research-wiki/claims/crc_ps_current_route_deployable_action_rule.md` |
| `claim:crc_ps_not_absorbed_by_hf_strongutility_k` | `proposed` | Proposed | This is an untested falsification rule for a newly preregistered CRC-derived route, not evidence for failed R006. | `research-wiki/claims/crc_ps_not_absorbed_by_hf_strongutility_k.md` |
| `claim:eg_ter_metric_validity` | `supported` | Supported / scoped | The distance is supported for adversarial prescription-pair construct validation, not as proof that an EG-TER repair policy is superior. | `research-wiki/claims/eg_ter_metric_validity.md` |
| `claim:eg_ter_repair_pilot_asymmetric_info` | `invalidated` | Passed then superseded | E4's positive weak-baseline result was absorbed by HardSafety+Indication after E5 equalized hard filters. | `research-wiki/claims/eg_ter_repair_pilot_asymmetric_info.md` |
| `claim:egsf_dynamic_budget_motivated` | `supported` | Supported / scoped | Stable proxy-risk shifts justify examining dynamic risk tolerances, not a clinical-safety claim or the failed selector. | `research-wiki/claims/egsf_dynamic_budget_motivated.md` |
| `claim:egsf_frontier_exists` | `supported` | Supported / scoped | GAMENet candidate pools contain oracle lower-risk alternatives at calibrated utility, but this is not a deployable-selector result. | `research-wiki/claims/egsf_frontier_exists.md` |
| `claim:egsf_minimal_selector` | `invalidated-by-strong-control` | Passed then superseded | The early result exposed an insufficient fixed-lambda-10 control grid; E3b reversed its method interpretation. | `research-wiki/claims/egsf_minimal_selector.md` |
| `claim:egsf_not_fixed_lambda` | `invalidated` | Invalidated / failed | Expanded strict global fixed-lambda controls explain the selector gains, with negative LambdaGaps for bucket/context and exact-count variants. | `research-wiki/claims/egsf_not_fixed_lambda.md` |
| `claim:hard_safety_baseline_trap` | `supported` | Supported / scoped | A leveled hard-safety plus indication baseline can remove an apparently complex method's binary repair advantage. | `research-wiki/claims/hard_safety_baseline_trap.md` |
| `claim:kdd2025_not_equivalent_to_risk_budgeted_deployment` | `supported` | Supported / scoped | The current full-method reading preserves a narrow non-equivalence finding while requiring KDD 2025 as a kill-check baseline. | `research-wiki/claims/kdd2025_not_equivalent_to_risk_budgeted_deployment.md` |
| `claim:safety_claim_audit_protocol` | `proposed` | Proposed | E3b is a seed negative case; the audit classification has not been validated beyond its planned case study. | `research-wiki/claims/safety_claim_audit_protocol.md` |

## Decisive Route Histories

### EGSF Selector

E0.1 supports proxy-risk strata and E2 supports diagnostic frontier existence. E2b found fixed-lambda competition. E3-Minimal's earlier result was overturned by E3b: global lambda `30.0` beat both selector variants under calibrated utility and strict-count controls. The selector idea and fixed-lambda-resistant claims are failed; only the bucket and oracle-frontier diagnostics survive.

Sources: `research-wiki/ideas/egsf.md`, `research-wiki/experiments/egsf_e0_1_dynamic_budget_audit.md`, `research-wiki/experiments/egsf_e2_oracle_frontier_initial.md`, `research-wiki/experiments/egsf_e2b_controls_initial.md`, `research-wiki/experiments/egsf_e3b_strong_followup.md`, `research-wiki/claims/egsf_dynamic_budget_motivated.md`, `research-wiki/claims/egsf_frontier_exists.md`, `research-wiki/claims/egsf_minimal_selector.md`, and `research-wiki/claims/egsf_not_fixed_lambda.md`.

### EG-TER Repair

Blind metric validation supports `D_therapeutic`. E4 passed against unlevelled baselines, then E5 levelled hard filters and eliminated all binary repair differences. The solver is invalidated; the Hard-Safety Baseline Trap and the metric's scoped evaluation role survive.

Sources: `research-wiki/ideas/eg_ter.md`, `research-wiki/experiments/eg_ter_metric_validity_week1.md`, `research-wiki/experiments/eg_ter_e4_minimal_pilot.md`, `research-wiki/experiments/eg_ter_e5_robustness.md`, `research-wiki/claims/eg_ter_metric_validity.md`, `research-wiki/claims/eg_ter_repair_pilot_asymmetric_info.md`, and `research-wiki/claims/hard_safety_baseline_trap.md`.

### CRC-PS Action Family

The KDD audit supports only a narrow distinction between calibration or set confidence and a fixed-base deployment contract. R006 then failed its preregistered finite-grid certificate with zero accepted lambdas, invalidating the deployable-action claim while reinforcing the bounded-loss-only guardrail. R007 is blocked for the archived route.

Sources: `research-wiki/ideas/crc_ps.md`, `research-wiki/experiments/crc_ps_kdd2025_method_audit.md`, `research-wiki/experiments/crc_ps_r006_failure_analysis.md`, `research-wiki/claims/crc_ps_bounded_loss_only.md`, `research-wiki/claims/crc_ps_current_route_deployable_action_rule.md`, `research-wiki/claims/crc_ps_not_absorbed_by_hf_strongutility_k.md`, and `research-wiki/claims/kdd2025_not_equivalent_to_risk_budgeted_deployment.md`.

### Historical Backup Routes

The Safety Claim Audit Card is an unvalidated backup protocol seeded by E3b. The Boundary Evidence-Eligibility Certificate is demoted because of strong overlap with existing literature. Differential Prescription Action Modeling is only a secondary alternative, contingent on a tightly controlled failure-decomposition contribution.

Sources: `research-wiki/ideas/safety_claim_audit_card.md`, `research-wiki/experiments/safety_claim_audit_minimal_case_study.md`, `research-wiki/claims/safety_claim_audit_protocol.md`, `research-wiki/ideas/boundary_evidence_eligibility_certificate.md`, and `research-wiki/ideas/differential_prescription_action_modeling.md`.

## Gaps and Practical Memory

The following gaps remain useful research constraints, not authority to revive their failed parent routes. Their canonical definitions and route-specific limits are in `research-wiki/gap_map.md`.

| Gap | Current meaning |
| --- | --- |
| G1: Safety-Claim Artifact Audit | Historical audit residue after CRC-PS promotion. |
| G2: Frontier Certificate for Safety-Biased MedRec | Demoted backup route. |
| G3: Therapeutic Distortion for Safety Repair | Historical EG-TER metric residue. |
| G4: Constructive Safety Repair Action Space | Historical EG-TER action-space residue. |
| G5: Fixed-Base Prescription-Set Deployment Contract | Future-route constraint; cannot reuse the failed R006 guarantee claim. |
| G6: Confidence Calibration vs Deployed Action Selection | Future-route constraint; must separate calibration from action selection. |
| G7: Count, Coverage, and Under-Prescription Artifact Control | Future work must survive hard-filter, count-matched, KDD-proxy, and base-only controls. |

The portable operational residue is equally narrow: keep patient data and baseline environments out of Git, use the local machine only for harness and public-safe gates, and perform real-data or GPU work only through the current remote-execution contract. Do not inherit archive-specific paths, sockets, or environment names. Source: `findings.md` at the pinned archive commit.

## Exclusions

This ledger deliberately excludes raw and processed EHR data, split membership, patient-level predictions, large metric tables, result CSV or JSON rows, model weights, checkpoints, private traces, timestamped workflow-log duplicates, and server-specific operational details. The source graph and timeline remain available at `research-wiki/graph/edges.jsonl` and `research-wiki/log.md` in the pinned archive.
