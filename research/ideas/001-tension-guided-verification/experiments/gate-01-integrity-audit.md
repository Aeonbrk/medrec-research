# Gate 01 Integrity Audit Report

- **Idea**: `001-tension-guided-verification`
- **Gate**: `gate-01-routing-opportunity`
- **Formal Run ID**: `gate-01-routing-opportunity-20260902-010537`
- **Audit Date**: 2026-09-02
- **Auditor**: `ccf-integrity-auditor`
- **Audit Mode**: `full` (`numeric-audit`, `claim-audit`, `citation-audit`)

---

## Output Contract Summary

```text
Mode: full
Artifacts checked:
  - research/ideas/001-tension-guided-verification/experiments/gate-01-routing-opportunity.md
  - research/ideas/001-tension-guided-verification/experiments/run_routing_opportunity_gate.py (frozen at c6fc35bce97637a2eddc6319cdec768256abdccb)
  - research/ideas/001-tension-guided-verification/experiments/gate-summary.json
  - Handoff.md
  - 319-lab-via-server:/root/zhb/medrec-data/runs/ideas/001-tension-guided-verification/gate-01-routing-opportunity-20260902-010537/candidate-revision-values.jsonl
  - 319-lab-via-server:/root/zhb/medrec-data/runs/ideas/001-tension-guided-verification/gate-01-routing-opportunity-20260902-010537/gate-summary.json
Claim-evidence matrix: See Section 1 below (2 claims supported, 2 claims overstated in Handoff.md)
Numeric consistency findings: Pass (15,549 rows verified, 0 invariant failures, 0 diffs across all aggregates, intervals, and criteria)
Citation metadata findings: Pass (URP v1.1 baseline and benchmark citations conform to registry)
Citation-context findings: Pass (Protocol citations match frozen scope)
Severity: HIGH (claim overstatement in active Handoff.md blocks P0 closure)
Safe edit suggestions: See Section 4 below (exact replacements for Handoff.md lines 79 and 81)
Next CCFA owner: ccf-paper-writer / Operator for documentation correction
No-invention status: Verified (100% derived from restricted candidate rows and frozen protocol)
```

```text
P0 Status: CLAIM_CORRECTION_REQUIRED
Formal Gate 02 unlocked: no
```

---

## 1. Claim-Evidence Matrix

| Claim Location | Claim Statement | Evidence Status | Finding / Category | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `gate-01-routing-opportunity.md` §11, §296–314 | Under frozen MoleRec validation setting and fixed singleton deletion operator $R_0$, DDI-active predicted medications exhibit substantial heterogeneity in retrospective revision outcomes, and an oracle allocation has statistically supported headroom over Random and RiskOnly. | Empirically verified: $Gap_{O-R}(B) = +68.33\%$ (95% CI: [67.33%, 69.38%]); $Gap_{O-Risk}(10\%) = +62.93\%$ (95% CI: [59.88%, 65.61%]); support: 844 beneficial and 857 non-beneficial patients. | **Supported** | None. Preserves retrospective, metric-specific bounds. |
| `Handoff.md` line 13 | Selective routing opportunity holds under $R_0$; Oracle significantly beats both Random and RiskOnly across all budget tiers. | Empirically verified across 10%, 20%, 30% budgets ($p < 0.05$ via patient-clustered bootstrap). | **Supported** | None. |
| `Handoff.md` line 79 | "only 31.67% of singleton deletions are Pareto-beneficial ($Y^{PB}=1$), while 68.33% are harmful to efficacy ($\Delta J < 0$)." | $\Delta J < 0$ measures retrospective reduction in Jaccard similarity against observed validation prescriptions under $R_0$. Equating observed prescription match with "efficacy" and Jaccard reduction with "harmful to efficacy" exceeds experimental scope. | **Overstated** | Replace "harmful to efficacy ($\Delta J < 0$)" with metric-specific wording: "reduce visit-level Jaccard under singleton deletion ($\Delta J < 0$, non-beneficial revisions under $R_0$)". |
| `Handoff.md` line 81 | "Simple DDI-degree sorting fails to isolate safe deletions and causes substantial efficacy loss (>62% non-beneficial revisions)." | "Safe deletions" and "causes substantial efficacy loss" use causal and clinical safety vocabulary. Gate 01 protocol explicitly states: "This gate does not establish prospective prescribing semantics or clinical safety." | **Overstated** | Replace with: "Simple DDI-degree sorting fails to isolate Pareto-beneficial revisions under $R_0$ and results in >62% non-beneficial revisions (revisions that reduce visit-level Jaccard)." |

### Explicitly Disallowed Claims Check

The audit confirmed that none of the following forbidden claims are asserted in `gate-summary.json` or `gate-01-routing-opportunity.md`:

- "Tension hypothesis confirmed" (Not asserted)
- "Tension predicts revision value" (Not asserted)
- "Tension is necessary" (Not asserted)
- "safe medication deletion" (Flagged in `Handoff.md`)
- "clinical safety improved" (Not asserted)
- "critical treatment medication" (Not asserted)
- "patient benefit" (Not asserted)
- Causal clinical claims (Flagged causal phrasing in `Handoff.md`)
- Deployable routing policy (Explicitly disclaimed in protocol §210)

---

## 2. Numeric Consistency Findings

An independent audit script was executed directly on `319-lab-via-server` using Python standard library only (without importing runner functions `evaluate_policies_at_budgets`, `run_patient_clustered_bootstrap`, or `evaluate_gate_verdict`).

### 2.1 Row-Level Invariant Audit

All 15,549 rows of `/root/zhb/medrec-data/runs/ideas/001-tension-guided-verification/gate-01-routing-opportunity-20260902-010537/candidate-revision-values.jsonl` were checked:

1. **Active DDI degree positive**: $d_t(m) > 0$ held for 15,549 / 15,549 rows.
2. **Violation delta strictly negative**: $\Delta V_{t,m} = -d_t(m) < 0$ held for 15,549 / 15,549 rows.
3. **Pareto-beneficial logical equivalence**: $Y^{PB}_{t,m} = \mathbf 1[\Delta J_{t,m} \ge 0 \land \Delta V_{t,m} < 0]$ held for 15,549 / 15,549 rows.
4. **Harmful revision logical equivalence**: $Y^H_{t,m} = \mathbf 1[\Delta J_{t,m} < 0]$ held for 15,549 / 15,549 rows.
5. **Required fields present**: `patient_order`, `visit_order`, `medication_code`, `active_ddi_degree`, `delta_jaccard`, `delta_violation`, `pareto_beneficial`, `harmful_revision` were present in all rows.
6. **Identifier consistency**: `patient_order` and `(patient_order, visit_order)` mapped bijectively to private patient and visit identifiers without collision.

**Invariant Failures Count**: 0.

### 2.2 Recomputed Support Statistics

| Metric | Recorded Public Summary | Independently Derived | Diff | Status |
| :--- | :--- | :--- | :--- | :--- |
| `eligible_candidates` | 15,549 | 15,549 | 0 | Exact match |
| `eligible_visits` | 1,219 | 1,219 | 0 | Exact match |
| `eligible_patients` | 858 | 858 | 0 | Exact match |
| `beneficial_patients` | 844 | 844 | 0 | Exact match |
| `non_beneficial_patients` | 857 | 857 | 0 | Exact match |
| `support_sufficient` | `true` ($\ge 50$ threshold) | `true` | - | Exact match |

### 2.3 Recomputed Policy Yields and Gaps

| Policy / Metric | Budget | Recorded Public Summary | Independently Derived | Diff | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pareto_beneficial_yield` (Random) | All | 0.31674062640684286 | 0.31674062640684286 | 0.0 | Exact match |
| `harmful_revision_yield` | All | 0.6832593735931571 | 0.6832593735931571 | 0.0 | Exact match |
| `risk_only_yield` | 10% | 0.37065637065637064 | 0.37065637065637064 | 0.0 | Exact match |
| `risk_only_yield` | 20% | 0.3563846896108073 | 0.3563846896108073 | 0.0 | Exact match |
| `risk_only_yield` | 30% | 0.32868782161234994 | 0.32868782161234994 | 0.0 | Exact match |
| `oracle_yield` | 10% | 1.0 | 1.0 | 0.0 | Exact match |
| `oracle_yield` | 20% | 1.0 | 1.0 | 0.0 | Exact match |
| `oracle_yield` | 30% | 1.0 | 1.0 | 0.0 | Exact match |
| `oracle_minus_random` | 10% | 0.6832593735931571 | 0.6832593735931571 | 0.0 | Exact match |
| `oracle_minus_random` | 20% | 0.6832593735931571 | 0.6832593735931571 | 0.0 | Exact match |
| `oracle_minus_random` | 30% | 0.6832593735931571 | 0.6832593735931571 | 0.0 | Exact match |
| `oracle_minus_risk_only` | 10% | 0.6293436293436294 | 0.6293436293436294 | 0.0 | Exact match |
| `oracle_minus_risk_only` | 20% | 0.6436153103891926 | 0.6436153103891926 | 0.0 | Exact match |
| `oracle_minus_risk_only` | 30% | 0.6713121783876501 | 0.6713121783876501 | 0.0 | Exact match |

### 2.4 Recomputed Bootstrap Confidence Intervals

Reproduced via Python `random.Random(1203)`, 1,000 patient clusters, linear quantile interpolation $(n-1)q$:

| Metric | Budget | Lower 95% (Recorded) | Lower 95% (Recomputed) | Upper 95% (Recorded) | Upper 95% (Recomputed) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `risk_only_yield` | 10% | 0.3438630902134164 | 0.3438630902134164 | 0.40122041499612654 | 0.40122041499612654 | Exact match |
| `risk_only_yield` | 20% | 0.3325951707624268 | 0.3325951707624268 | 0.37823496274376067 | 0.37823496274376067 | Exact match |
| `risk_only_yield` | 30% | 0.30941486463630813 | 0.30941486463630813 | 0.3474387012992247 | 0.3474387012992247 | Exact match |
| `oracle_minus_random` | 10% | 0.6732866793075132 | 0.6732866793075132 | 0.6938271544886716 | 0.6938271544886716 | Exact match |
| `oracle_minus_random` | 20% | 0.6732866793075132 | 0.6732866793075132 | 0.6938271544886716 | 0.6938271544886716 | Exact match |
| `oracle_minus_random` | 30% | 0.6732866793075132 | 0.6732866793075132 | 0.6938271544886716 | 0.6938271544886716 | Exact match |
| `oracle_minus_risk_only` | 10% | 0.5987795850038734 | 0.5987795850038734 | 0.6561369097865837 | 0.6561369097865837 | Exact match |
| `oracle_minus_risk_only` | 20% | 0.6217650372562394 | 0.6217650372562394 | 0.6674048292375732 | 0.6674048292375732 | Exact match |
| `oracle_minus_risk_only` | 30% | 0.6525612987007754 | 0.6525612987007754 | 0.6905851353636919 | 0.6905851353636919 | Exact match |

### 2.5 Decision Criteria and Verdict

- `support_requirement_met`: `true` (Recorded: `true`)
- `gap_oracle_random_10_ci_above_zero`: `true` (Recorded: `true`)
- `gap_oracle_random_20_ci_above_zero`: `true` (Recorded: `true`)
- `gap_oracle_risk_indistinguishable_from_zero`: `false` (Recorded: `false`)
- **Final Verdict**: `pass` (Recorded: `pass`)

---

## 3. Cryptographic and Identity Consistency Findings

The recorded execution identities in `gate-summary.json` match the frozen prerequisites of Gate 01 exactly:

| Identity Key | Frozen Authority / Expected | Recorded in `gate-summary.json` | Status |
| :--- | :--- | :--- | :--- |
| `harness_revision` | `c6fc35bce97637a2eddc6319cdec768256abdccb` | `c6fc35bce97637a2eddc6319cdec768256abdccb` | Exact match |
| `model_source_revision` | `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` | `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` | Exact match |
| `baseline_core_sha256` | `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511` | `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511` | Exact match |
| `adapter_sha256` | `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531` | `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531` | Exact match |
| `checkpoint_sha256` | `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca` | `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca` | Exact match |
| `baseline_environment_sha256` | `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda` | `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda` | Exact match |
| `dataset_manifest_sha256` | `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712` | `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712` | Exact match |
| `ddi_asset_sha256` | `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` | `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` | Exact match |
| `feature_availability_sha256` | `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9` | `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9` | Exact match |
| `medication_vocabulary_size` | `131` | `131` | Exact match |
| `summary_sha256` (Local vs 319) | `61e0db6abde3852044d3f58b1087d9dd98002c31a779da8f5469c28330c92b89` | `61e0db6abde3852044d3f58b1087d9dd98002c31a779da8f5469c28330c92b89` | Exact match |

---

## 4. Remediation Ledger for `Handoff.md`

Because numeric verification passed with zero differences and verdict `pass` is mathematically confirmed, the only blocker to formal `AUDIT_PASS` is active claim overstatement in `Handoff.md`.

The exact required corrections are:

### Replacement 1 (`Handoff.md:L79`)

- **Current Text**:

  ```markdown
  1. **Base Prevalence**: Within the review universe $\mathcal Q$ (15,549 candidate revisions across 1,219 visits and 858 validation patients), only **31.67%** of singleton deletions are Pareto-beneficial ($Y^{PB}=1$), while **68.33%** are harmful to efficacy ($\Delta J < 0$).
  ```

- **Required Replacement**:

  ```markdown
  1. **Base Prevalence**: Within the review universe $\mathcal Q$ (15,549 candidate revisions across 1,219 visits and 858 validation patients), only **31.67%** of singleton deletions are Pareto-beneficial ($Y^{PB}=1$), while **68.33%** reduce visit-level Jaccard under singleton deletion ($\Delta J < 0$, non-beneficial revisions under $R_0$).
  ```

### Replacement 2 (`Handoff.md:L81`)

- **Current Text**:

  ```markdown
  3. **RiskOnly Policy**: Yields **37.07%** (10% budget), **35.64%** (20% budget), **32.87%** (30% budget). Simple DDI-degree sorting fails to isolate safe deletions and causes substantial efficacy loss (>62% non-beneficial revisions).
  ```

- **Required Replacement**:

  ```markdown
  3. **RiskOnly Policy**: Yields **37.07%** (10% budget), **35.64%** (20% budget), **32.87%** (30% budget). Simple DDI-degree sorting fails to isolate Pareto-beneficial revisions under $R_0$ and results in >62% non-beneficial revisions (revisions that reduce visit-level Jaccard).
  ```

---

## 5. Audit Determination & Next Action

- **P0 Status**: `CLAIM_CORRECTION_REQUIRED`
- **Formal Gate 02 Unlocked**: `no`
- **Action**: In accordance with P0 governance, the auditor does not automatically edit the documentation during the first audit pass. Gate 02 execution remains blocked until the specified text adjustments are committed and a clean verification pass confirms alignment.
