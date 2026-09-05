<!-- markdownlint-disable MD013 -->

# B0 — Cardinality Attribution Decision Record

## 1. Scientific Protocol Identity

- **Audit Gate**: `B0 — Cardinality Attribution`
- **Single Source of Truth**: `research/premise-audit/README.md`
- **Backbone Identity**: MoleRec Table 1 Comparison Mode (`dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`)
- **Checkpoint SHA256**: `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca`
- **Dataset Manifest SHA256**: `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712`
- **Diagnostic Intervention**: `oracle-count` / TopK(scores, |target|) / diagnostic-only / non-deployable
- **Test Split Isolation**: Untouched (100% test isolation, zero test visits indexed or evaluated)

---

## 2. Quantitative Evidence

### 2.1 Sample Size and Count Distribution

- **Validation Cohort Patients**: 1059 (859 patients with $\ge 1$ eligible visit)
- **Validation Visits**: 1220
- **Under-count Prevalence ($|\hat M_t| < |M_t|$)**: 0.3377 (33.77%)
- **Equal-count Prevalence ($|\hat M_t| = |M_t|$)**: 0.0779 (7.79%)
- **Over-count Prevalence ($|\hat M_t| > |M_t|$)**: 0.5844 (58.44%)

### 2.2 Primary Paired Outcomes

| Metric | Original Frozen ($\hat M_t^{orig}$) | Oracle-Count Diagnostic ($\hat M_t^{oc}$) | Paired Delta | 95% Patient Bootstrap CI |
| :--- | :--- | :--- | :--- | :--- |
| **F1** | 0.6881 | 0.6981 | +0.0100 | [+0.0067, +0.0134] |
| **Pair-Normalized DDI Rate** | 0.0445 | 0.0445 | -0.0000 | [-0.0007, +0.0007] |

### 2.3 Secondary and Corroborating Outcomes

| Metric | Original Frozen ($\hat M_t^{orig}$) | Oracle-Count Diagnostic ($\hat M_t^{oc}$) | Paired Delta | 95% Patient Bootstrap CI |
| :--- | :--- | :--- | :--- | :--- |
| **Jaccard** | 0.5340 | 0.5468 | +0.0128 | [+0.0092, +0.0166] |
| **Recall** | 0.7340 | 0.6981 | -0.0359 | [-0.0435, -0.0282] |
| **Precision** | 0.6700 | 0.6981 | +0.0282 | [+0.0220, +0.0345] |
| **Medication Count** | 21.55 | 19.95 | -1.59 | [-1.94, -1.25] |
| **Absolute DDI Pairs / Visit** | 10.5648 | 9.4402 | -1.1246 | [-1.4924, -0.7676] |

---

## 3. Frozen Decision Gate Evaluation

| Condition | Threshold Requirement | Observed Empirical Value | Gate Status |
| :--- | :--- | :--- | :--- |
| **1. Under-count Prevalence** | $P(\lvert\hat M_t\rvert < \lvert M_t\rvert) \ge 0.20$ | 0.3377 (33.77%) | PASS |
| **2. F1 Material Recovery** | $\Delta F1 \ge +0.010$ and 95% CI lower > 0 | +0.009977 (95% CI: [+0.0067, +0.0134]) | FAIL |
| **3. Safety-Side Attribution** | $\Delta DDI \ge +0.005$ and 95% CI lower > 0 | -0.000002 (95% CI: [-0.0007, +0.0007]) | FAIL |

---

## 4. Final Verdict and Next State

- **Verdict**: `FAIL_B0_NO_MATERIAL_COUNT_SAFETY_TRADEOFF`
- **Diagnostic Role**: Diagnostic attribution only; oracle-count is strictly non-deployable and not a baseline.
- **Scientific Interpretation**:
  - Restoring reference count under unchanged rankings does not produce the required material count-mediated trade-off.
  - Retrospective target fidelity does not imply clinical efficacy; DDI rate proxy does not imply clinical safety.
- **Next state**: `NO_HIGH_VALUE_DIRECTION_YET`
- **Next Owner**: `ccf-pipeline-orchestrator`
