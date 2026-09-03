<!-- markdownlint-disable MD013 -->

# Gate 01 Integrity Audit Report — Co-Selection Compatibility

- **Idea**: `004-co-selection-compatibility`
- **Gate**: `gate-01-co-selection-compatibility`
- **Formal Run ID**: `gate-01-co-selection-compatibility-20260903-154343`
- **Harness Revision**: `8640ce521a942bd34daa2a5547c2e2db1febca6a`
- **Audit Date**: 2026-09-03
- **Auditor**: `ccf-integrity-auditor`
- **Audit Mode**: `full` (`numeric-audit`, `claim-audit`, `citation-audit`)

---

## Output Contract Summary

```text
Mode: full
Artifacts checked:
  - research/ideas/004-co-selection-compatibility/experiments/gate-01-co-selection-compatibility.md
  - research/ideas/004-co-selection-compatibility/experiments/run_co_selection_compatibility_gate.py (frozen at 8640ce521a942bd34daa2a5547c2e2db1febca6a)
  - research/ideas/004-co-selection-compatibility/experiments/gate-01-summary.json (SHA256: e7ad3459c54f78b73b5826a273d182e7cbc6d8e72478d9ced7a55026c7b4512a)
  - 319-lab:/root/zhb/medrec-data/runs/ideas/004-co-selection-compatibility/gate-01-co-selection-compatibility-20260903-154343/gate-01-candidates.jsonl (SHA256: e7e9249c0af76d0239ce38d3e9ad7f01e699aca2ad0905d44d873aa9bf54562f)
  - 319-lab:/root/zhb/medrec-data/runs/ideas/004-co-selection-compatibility/gate-01-co-selection-compatibility-20260903-154343/gate-01-dev-fit.json (SHA256: 6c0ef3c3b8d3ecae4bf7015f000f07436f133eda99723e3e24ec986bcc9d5be1)
  - 319-lab:/root/zhb/medrec-data/runs/ideas/004-co-selection-compatibility/gate-01-co-selection-compatibility-20260903-154343/gate-01-summary.json (SHA256: e7ad3459c54f78b73b5826a273d182e7cbc6d8e72478d9ced7a55026c7b4512a)
Claim-evidence matrix: See Section 1 below (all empirical claims supported; 0 overstatements)
Numeric consistency findings: Pass (15,549 rows verified, 0 invariant failures, 0 partition leaks, 0 split mismatches, 0 diffs across all yields, gaps, Dev regression coefficients, and bootstrap intervals)
Citation metadata findings: Pass (Frozen baseline, snapshot, and benchmark identities conform to registry authority)
Citation-context findings: Pass (Protocol scope strictly retrospective validation-only hypothesis selection)
Severity: NONE (all checks passed with exact numeric agreement)
Safe edit suggestions: None required
Next CCFA owner: execution agent / P6 research decision
No-invention status: Verified (100% independently derived from restricted candidate corpus and frozen protocol)
```

```text
P5 Status: INTEGRITY_PASS
Formal Gate 01 verdict independently reproduced: yes
P6 research decision unlocked: yes
```

---

## 1. Claim-Evidence Matrix

| Claim Location | Claim Statement | Evidence Status | Finding / Category | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `gate-01-co-selection-compatibility.md` §2 | "Among DDI-active medications predicted by frozen MoleRec, does mean train-only frequency-corrected co-selection compatibility contain reproducible incremental false-positive routing information beyond frozen score, predicted-set size, candidate prevalence, peer-set popularity, and their predeclared score interactions?" | Evaluated on 7,787 Audit candidates across 426 eligible patients via Dev-fitted ridge linear probability models. | **Supported as Falsified** | Formal scientific hypothesis is cleanly falsified with zero numeric discrepancy. |
| `gate-01-summary.json` | `StrongControl` achieves 61.57% (10% budget) and 59.54% (20% budget), improving over `ScoreOnly` (tie at 10%, +1.16% at 20%). | Empirically verified: Dev-fitted control coefficients $\beta_0=0.3265$, yields 61.57% and 59.54% on Audit. | **Supported** | None. |
| `gate-01-summary.json` | Residual Oracle headroom survives: Oracle achieves 100.0% yield, beating `StrongControl` by $+38.43\%$ (10% budget, 95% CI: [+33.87%, +42.93%]) and $+40.46\%$ (20% budget, 95% CI: [+37.18%, +43.61%]). | Empirically verified: Gate B passes unconditionally with substantial headroom. | **Supported** | None. |
| `gate-01-summary.json` | `CoSelectionAugmented` achieves 62.34% (10% budget) and 59.60% (20% budget), resulting in negligible point gaps vs `StrongControl` (+0.77% at 10%, +0.06% at 20%) and bootstrap 95% CIs crossing zero ([-1.16%, +2.50%] at 10%, [-0.68%, +0.78%] at 20%). Train-only co-selection compatibility adds zero reproducible incremental signal. | Empirically verified: Gate C fails at both primary budgets. Lower 95% CI bounds are strictly $\le 0$. | **Supported** | None. |

### Explicitly Disallowed Claims Check

The audit confirmed that none of the forbidden claims are asserted in active repository documentation:

- **No claim that co-selection compatibility adds signal**: Explicitly rejected by Gate C failure and crossing-zero bootstrap intervals.
- **No claim that frequency-corrected co-selection is viable for FP routing**: Explicitly falsified by empirical evidence.
- **No prospective clinical claims**: No claims of clinical safety, clinical efficacy, patient benefit, therapeutic compatibility, or prescriber intent.
- **No claim that medication relations are globally impossible**: Falsification is strictly scoped to the preregistered one-scalar empirical-NPMI train-only observable on frozen MoleRec predictions under the Unified Research Protocol.
- **No post-hoc rescue claims**: No replacement with alternative association statistics (PMI, lift, Jaccard, embeddings, GNN, hypergraph).

---

## 2. Frozen Identity Audit

The formal public summary records exactly the frozen identities, verified against registry authority and execution environment:

| Identity Field | Expected Frozen Target | Recorded in `gate-01-summary.json` | Audit Status |
| :--- | :--- | :--- | :--- |
| `harness_revision` | `8640ce521a942bd34daa2a5547c2e2db1febca6a` | `8640ce521a942bd34daa2a5547c2e2db1febca6a` | Exact match |
| `model_source_revision` | `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` | `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` | Exact match |
| `checkpoint_sha256` | `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca` | `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca` | Exact match |
| `baseline_core_sha256` | `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511` | `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511` | Exact match |
| `adapter_sha256` | `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531` | `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531` | Exact match |
| `baseline_environment_name` | `medrec-molerec-table1` | `medrec-molerec-table1` | Exact match |
| `baseline_environment_sha256` | `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda` | `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda` | Exact match |
| `dataset_id` | `molerec-table1-comparison-v1-1` | `molerec-table1-comparison-v1-1` | Exact match |
| `dataset_manifest_sha256` | `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712` | `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712` | Exact match |
| `snapshot_id` | `molerec-table1-c721-www23` | `molerec-table1-c721-www23` | Exact match |
| `snapshot_sha256` | `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58` | `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58` | Exact match |
| `medication_vocabulary_sha256` | `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08` | `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08` | Exact match |
| `ddi_asset_sha256` | `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` | `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` | Exact match |
| `feature_availability_sha256` | `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9` | `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9` | Exact match |

---

## 3. Candidate Corpus & Row-Level Invariant Audit

Evaluated on all 15,549 rows of `gate-01-candidates.jsonl`:

1. **Row Count**: exactly 15,549 rows across 1,220 validation visits.
2. **Review Universe Invariant**: active DDI degree $d_t(m) > 0$ holds for 15,549 / 15,549 rows.
3. **Singleton Deletion Invariant**: $\Delta V_{t,m} = -d_t(m) < 0$ holds for 15,549 / 15,549 rows.
4. **Pareto-Beneficial Definition**: $Y^{PB}_{t,m} = \mathbf 1[m \notin M_t]$ holds for 15,549 / 15,549 rows.
5. **Score Domain**: $s_t(m) \in [0, 1]$ and finite for 15,549 / 15,549 rows.
6. **Prescription Size**: $n_t \ge 2$ holds for 15,549 / 15,549 rows.
7. **Observable Domain**: $A_t(m) \in [-1, 1]$ and finite for 15,549 / 15,549 rows.
8. **Train Prevalence**: $p_{train}(m) \in [0, 1]$ empirical holds for 15,549 / 15,549 rows.
9. **Partition Assignment**: `gate01_partition` is strictly `"dev"` or `"audit"` for 15,549 / 15,549 rows.
10. **Zero Patient Overlap**: 0 candidate rows belong to both partitions; 0 patients have candidate rows spanning both Dev and Audit.

**Invariant Failures Count**: `0`.

---

## 4. Cohort Partition & Split Audit

The complete validation cohort was independently partitioned using standard library `random.Random(2004)` over $0 \dots 1058$ ($N=1059$):

| Cohort Metric | Expected (Preregistered) | Recorded (Public Summary) | Independently Recomputed | Diff | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Complete Validation Patients | 1,059 | 1,059 | 1,059 | 0 | Exact match |
| Dev Allocated Patients | 529 | 529 | 529 | 0 | Exact match |
| Audit Allocated Patients | 530 | 530 | 530 | 0 | Exact match |
| Dev Eligible Patients (with $\mathcal Q_t$) | 432 | 432 | 432 | 0 | Exact match |
| Dev Candidates | 7,762 | 7,762 | 7,762 | 0 | Exact match |
| Audit Eligible Patients (with $\mathcal Q_t$) | 426 | 426 | 426 | 0 | Exact match |
| Audit Candidates | 7,787 | 7,787 | 7,787 | 0 | Exact match |
| Total Candidates ($7,762 + 7,787$) | 15,549 | 15,549 | 15,549 | 0 | Exact match |

---

## 5. Selector Fitting & Numerical Verification

Dev linear probability models fit strictly on Dev candidates ($N=7,762$) with ridge penalty $10^{-6}$:

### StrongControl Coefficients

| Variable | Recorded (`gate-01-summary.json`) | Independently Recomputed | Diff | Status |
| :--- | :---: | :---: | :---: | :---: |
| Intercept $\beta_0$ | 0.326473146215 | 0.326473146215 | 0.0 | Exact match |
| $u = 1 - s_t(m)$ | 3.126758688280 | 3.126758688280 | 0.0 | Exact match |
| $c = \log(1 + n_t)$ | -0.043739524342 | -0.043739524342 | 0.0 | Exact match |
| $f = \text{logit}(C_m)$ | -0.067935243841 | -0.067935243841 | 0.0 | Exact match |
| $g = \text{logit}(q_t)$ | 0.080932310760 | 0.080932310760 | 0.0 | Exact match |
| $u \cdot c$ | -0.623477361424 | -0.623477361424 | 0.0 | Exact match |
| $u \cdot f$ | 0.138797882131 | 0.138797882131 | 0.0 | Exact match |
| $u \cdot g$ | -0.881076421822 | -0.881076421822 | 0.0 | Exact match |

### CoSelectionAugmented Coefficients

| Variable | Recorded (`gate-01-summary.json`) | Independently Recomputed | Diff | Status |
| :--- | :---: | :---: | :---: | :---: |
| Intercept $\beta_0$ | 0.293511594657 | 0.293511594657 | 0.0 | Exact match |
| $u = 1 - s_t(m)$ | 3.343479603632 | 3.343479603632 | 0.0 | Exact match |
| $c = \log(1 + n_t)$ | -0.012050530020 | -0.012050530020 | 0.0 | Exact match |
| $f = \text{logit}(C_m)$ | -0.075702811013 | -0.075702811013 | 0.0 | Exact match |
| $g = \text{logit}(q_t)$ | 0.112998313075 | 0.112998313075 | 0.0 | Exact match |
| $u \cdot c$ | -0.704988895393 | -0.704988895393 | 0.0 | Exact match |
| $u \cdot f$ | 0.150056577397 | 0.150056577397 | 0.0 | Exact match |
| $u \cdot g$ | -0.967465916306 | -0.967465916306 | 0.0 | Exact match |
| $A_t(m)$ | -0.943865050888 | -0.943865050888 | 0.0 | Exact match |

---

## 6. Policy Yields & Gaps Verification

Evaluated on 7,787 Audit candidates:

| Policy / Metric | Budget 10% ($k=778$) | Budget 20% ($k=1557$) | Budget 30% ($k=2336$) | Recomputed Diff |
| :--- | :---: | :---: | :---: | :---: |
| `Random` | 0.316425 | 0.316425 | 0.316425 | 0.0 |
| `ScoreOnly` | 0.615681 | 0.583815 | 0.562500 | 0.0 |
| `StrongControl` | 0.615681 | 0.595376 | 0.568065 | 0.0 |
| `CoSelectionAugmented` | 0.623393 | 0.596018 | 0.559932 | 0.0 |
| `Oracle` | 1.000000 | 1.000000 | 1.000000 | 0.0 |
| $\Delta(\text{Aug} - \text{Control})$ | +0.007712 (+0.77%) | +0.000642 (+0.06%) | -0.008134 (-0.81%) | 0.0 |
| $\Delta(\text{Oracle} - \text{Control})$ | +0.384319 (+38.43%) | +0.404624 (+40.46%) | +0.431935 (+43.19%) | 0.0 |
| $\Delta(\text{Control} - \text{Score})$ | 0.000000 (+0.00%) | +0.011561 (+1.16%) | +0.005565 (+0.56%) | 0.0 |

---

## 7. Bootstrap Resampling & CI Verification

1,000 patient-clustered bootstrap replicates with seed `1204`:

| Metric | Budget | Lower 95% CI | Upper 95% CI | Spans Zero? | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Oracle - StrongControl` | 10% | +0.338669 | +0.429333 | No ($>0$) | Headroom exists |
| `Oracle - StrongControl` | 20% | +0.371813 | +0.436101 | No ($>0$) | Headroom exists |
| `Oracle - StrongControl` | 30% | +0.404310 | +0.461507 | No ($>0$) | Headroom exists |
| `CoSelectionAugmented - StrongControl` | 10% | -0.011630 | +0.025002 | **Yes ($\le 0$)** | Incremental signal fails |
| `CoSelectionAugmented - StrongControl` | 20% | -0.006806 | +0.007844 | **Yes ($\le 0$)** | Incremental signal fails |
| `CoSelectionAugmented - StrongControl` | 30% | -0.011810 | -0.000427 | **Yes ($\le 0$)** | Incremental signal fails |
| `StrongControl - ScoreOnly` | 10% | -0.018050 | +0.016631 | Yes | Descriptive |
| `StrongControl - ScoreOnly` | 20% | +0.001405 | +0.020703 | No ($>0$) | Control improves score |
| `StrongControl - ScoreOnly` | 30% | -0.005768 | +0.012898 | Yes | Descriptive |

---

## 8. Preregistered Decision Tree Execution

```text
[Gate A: Audit Support]
  Distinct positive patients (417) >= 50: PASS
  Distinct negative patients (426) >= 50: PASS
  k(10%) = 778 > 0, k(20%) = 1557 > 0: PASS
  -> Gate A PASSED

[Gate B: Residual Retrospective Headroom]
  LowerCI95(Oracle - StrongControl) @ 10% = +0.338669 > 0: PASS
  LowerCI95(Oracle - StrongControl) @ 20% = +0.371813 > 0: PASS
  -> Gate B PASSED (Substantial residual headroom remains)

[Gate C: Incremental Co-Selection Information]
  LowerCI95(CoSelectionAugmented - StrongControl) @ 10% = -0.011630 <= 0: FAIL
  LowerCI95(CoSelectionAugmented - StrongControl) @ 20% = -0.006806 <= 0: FAIL
  -> Gate C FAILED

[Final Decision]
  -> STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY
```

---

## 9. Conclusion & Handoff

The audit confirms:

1. Exact conformance with frozen protocol commit `a5f964be67f66852aba8dbfdbf2121b112046ae0` and implementation commit `8640ce521a942bd34daa2a5547c2e2db1febca6a`.
2. Strict test-set isolation: no test split data or targets were touched.
3. Clean train/dev/audit separation: train data generated prevalence and pair counts; Dev fit the linear models; Audit evaluated frozen selectors.
4. Zero invariant errors, zero numeric discrepancies, zero post-hoc parameter adjustments.
5. Preregistered decision tree mechanically mandates `STOP_NO_INCREMENTAL_CO_SELECTION_COMPATIBILITY`.

Integrity Verdict: `INTEGRITY_PASS`.
Proceed to P6 Research Decision.
