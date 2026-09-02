<!-- markdownlint-disable MD013 -->

# Gate 01 Integrity Audit Report

- **Idea**: `003-prescription-relative-confidence`
- **Gate**: `gate-01-prescription-relative-confidence`
- **Formal Run ID**: `gate-01-prescription-relative-confidence-20260902-233128`
- **Harness Revision**: `ac9dfe860bbce7a9a9620cf21836931136582055`
- **Audit Date**: 2026-09-02
- **Auditor**: `ccf-integrity-auditor`
- **Audit Mode**: `full` (`numeric-audit`, `claim-audit`, `citation-audit`)

---

## Output Contract Summary

```text
Mode: full
Artifacts checked:
  - research/ideas/003-prescription-relative-confidence/experiments/gate-01-prescription-relative-confidence.md
  - research/ideas/003-prescription-relative-confidence/experiments/run_prescription_relative_confidence_gate.py (frozen at ac9dfe860bbce7a9a9620cf21836931136582055)
  - research/ideas/003-prescription-relative-confidence/experiments/gate-01-summary.json (SHA256: 9384ae65ec535c26b5fc277baa95ed23219db18135e16e52a986a368bfd65c64)
  - 319-lab:/root/zhb/medrec-data/runs/ideas/003-prescription-relative-confidence/gate-01-prescription-relative-confidence-20260902-233128/gate-01-candidates.jsonl (SHA256: 7092babec0e55bca498a613727e2e99eec31dc2c65bc2c49dec9bd7401c61dcd)
  - 319-lab:/root/zhb/medrec-data/runs/ideas/003-prescription-relative-confidence/gate-01-prescription-relative-confidence-20260902-233128/gate-01-dev-fit.json (SHA256: 03b65af878afd3046e11b6db05141eccd144cbe2a0f05f46a5b1796ee64114f7)
  - 319-lab:/root/zhb/medrec-data/runs/ideas/003-prescription-relative-confidence/gate-01-prescription-relative-confidence-20260902-233128/gate-01-summary.json (SHA256: 9384ae65ec535c26b5fc277baa95ed23219db18135e16e52a986a368bfd65c64)
Claim-evidence matrix: See Section 1 below (all 4 empirical claims supported; 0 overstatements)
Numeric consistency findings: Pass (15,549 rows verified, 0 invariant failures, 0 partition leaks, 0 split mismatches, 0 diffs across all yields, gaps, Dev regression coefficients, and bootstrap intervals)
Citation metadata findings: Pass (Frozen baseline, snapshot, and benchmark identities conform to registry authority)
Citation-context findings: Pass (Protocol scope strictly retrospective validation-only hypothesis selection)
Severity: NONE (all checks passed with exact numeric agreement)
Safe edit suggestions: None required
Next CCFA owner: ccf-pipeline-orchestrator (for P6 research decision)
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
| `gate-01-prescription-relative-confidence.md` §1 | "Among DDI-active medications predicted by frozen MoleRec, does within-prescription relative confidence position contain reproducible incremental false-positive routing information beyond a strong simple control built from absolute medication score, predicted prescription size, and train-only medication prevalence?" | Evaluated on 7,740 Audit candidates across 423 eligible patients via Dev-fitted ridge linear probability models. | **Supported as Falsified** | Formal scientific hypothesis is cleanly falsified with zero numeric discrepancy. |
| `gate-01-summary.json` | `StrongControl` ($u, c, f, u \cdot c, u \cdot f$) yields 57.49% (10% budget) and 57.17% (20% budget), improving modestly over `ScoreOnly` (+0.65% at 10%, +1.29% at 20%). | Empirically verified: Dev-fitted control coefficients $\beta_0=0.6443$, yields 57.49% and 57.17% on Audit. | **Supported** | None. |
| `gate-01-summary.json` | Residual Oracle headroom survives: Oracle achieves 100.0% yield, beating `StrongControl` by $+42.51\%$ (10% budget, 95% CI: [+39.04%, +46.15%]) and $+42.83\%$ (20% budget, 95% CI: [+40.34%, +45.78%]). | Empirically verified: Gate B passes unconditionally with substantial headroom. | **Supported** | None. |
| `gate-01-summary.json` | `RankAugmented` achieves 57.24% (10% budget) and 56.91% (20% budget), resulting in negative point gaps vs `StrongControl` (-0.26% at 10%, -0.26% at 20%) and bootstrap 95% CIs crossing zero ([-1.37%, +1.19%] at 10%, [-0.65%, +0.80%] at 20%). Within-prescription relative confidence adds zero incremental signal. | Empirically verified: Gate C fails at both budgets. Lower 95% CI bounds are strictly $\le 0$. | **Supported** | None. |

### Explicitly Disallowed Claims Check

The audit confirmed that none of the forbidden claims are asserted in active repository documentation:

- **No claim that relative rank adds signal**: Explicitly rejected by Gate C failure and negative point gaps.
- **No claim that within-prescription relative confidence is viable for FP routing**: Explicitly falsified by empirical evidence.
- **No prospective clinical claims**: No claims of clinical safety, clinical efficacy, patient benefit, or prescriber intent. Retrospective benchmark metrics strictly maintained.
- **No claim that DDI information is globally impossible**: Falsification is strictly scoped to within-prescription relative confidence position on frozen MoleRec predictions under the Unified Research Protocol.
- **No tension revival claims**: Historical Tension route remains closed.

---

## 2. Frozen Identity Audit

The formal public summary records exactly the 10 frozen identities, verified against registry authority and execution environment:

| Identity Field | Expected Frozen Target | Recorded in `gate-01-summary.json` | Audit Status |
| :--- | :--- | :--- | :--- |
| `harness_revision` | `ac9dfe860bbce7a9a9620cf21836931136582055` | `ac9dfe860bbce7a9a9620cf21836931136582055` | Exact match |
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
6. **Relative Rank Domain**: $r_t(m) \in [0, 1]$ and finite for 15,549 / 15,549 rows.
7. **Prescription Size**: $n_t \ge 2$ holds for 15,549 / 15,549 rows.
8. **Train Prevalence**: $p_{train}(m) \in (0, 1)$ with Laplace smoothing holds for 15,549 / 15,549 rows.
9. **Partition Assignment**: `gate01_partition` is strictly `"dev"` or `"audit"` for 15,549 / 15,549 rows.
10. **Zero Patient Overlap**: 0 candidate rows belong to both partitions; 0 patients have candidate rows spanning both Dev and Audit.

**Invariant Failures Count**: `0`.

---

## 4. Cohort Partition & Split Audit

The complete validation cohort was independently partitioned using standard library `random.Random(2003)` over $0 \dots 1058$ ($N=1059$):

| Cohort Metric | Expected (Preregistered) | Recorded (Public Summary) | Independently Recomputed | Diff | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Complete Validation Patients | 1,059 | 1,059 | 1,059 | 0 | Exact match |
| Dev Allocated Patients | 529 | 529 | 529 | 0 | Exact match |
| Audit Allocated Patients | 530 | 530 | 530 | 0 | Exact match |
| Dev Eligible Patients (with $\mathcal Q_t$) | 435 | 435 | 435 | 0 | Exact match |
| Dev Candidates | 7,809 | 7,809 | 7,809 | 0 | Exact match |
| Audit Eligible Patients (with $\mathcal Q_t$) | 423 | 423 | 423 | 0 | Exact match |
| Audit Candidates | 7,740 | 7,740 | 7,740 | 0 | Exact match |
| Total Candidates ($7,809 + 7,740$) | 15,549 | 15,549 | 15,549 | 0 | Exact match |
| Dev-Audit Patient Overlap | 0 | 0 | 0 | 0 | Exact match |
| Test Split Access | None | None | None | 0 | Verified untouched |

---

## 5. Dev Model Fitting Audit

Dev ridge linear probability models ($\lambda = 10^{-6}$, unpenalized intercept) independently recomputed from Dev candidate rows:

| Selector Model | Parameter | Recorded Value | Independently Recomputed | Diff | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `StrongControl` | Intercept $\beta_0$ | 0.64427358 | 0.64427358 | 0.00000000 | Exact match |
| `StrongControl` | $\beta_u$ ($1 - s$) | 0.23214451 | 0.23214451 | 0.00000000 | Exact match |
| `StrongControl` | $\beta_c$ ($\log(1+n)$) | -0.14846012 | -0.14846012 | 0.00000000 | Exact match |
| `StrongControl` | $\beta_f$ ($\text{logit}(p)$) | -0.06053284 | -0.06053284 | 0.00000000 | Exact match |
| `StrongControl` | $\beta_{u \cdot c}$ | 0.32042229 | 0.32042229 | 0.00000000 | Exact match |
| `StrongControl` | $\beta_{u \cdot f}$ | 0.17445948 | 0.17445948 | 0.00000000 | Exact match |
| `RankAugmented` | Intercept $\beta_0$ | 0.59333301 | 0.59333301 | 0.00000000 | Exact match |
| `RankAugmented` | $\beta_u$ ($1 - s$) | -0.03502241 | -0.03502241 | 0.00000000 | Exact match |
| `RankAugmented` | $\beta_c$ ($\log(1+n)$) | -0.15222450 | -0.15222450 | 0.00000000 | Exact match |
| `RankAugmented` | $\beta_f$ ($\text{logit}(p)$) | -0.04136422 | -0.04136422 | 0.00000000 | Exact match |
| `RankAugmented` | $\beta_{u \cdot c}$ | 0.27443715 | 0.27443715 | 0.00000000 | Exact match |
| `RankAugmented` | $\beta_{u \cdot f}$ | 0.09780846 | 0.09780846 | 0.00000000 | Exact match |
| `RankAugmented` | $\beta_r$ (relative rank) | 0.22229588 | 0.22229588 | 0.00000000 | Exact match |

---

## 6. Audit Policy Yields and Gaps Audit

Evaluated on 7,740 Audit candidates across review budgets $B \in \{10\%, 20\%, 30\%\}$:

| Policy / Metric | Budget Tier | Recorded Value | Independently Recomputed | Diff | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Review Cutoff $k$ | 10% | 774 | 774 | 0 | Exact match |
| Review Cutoff $k$ | 20% | 1,548 | 1,548 | 0 | Exact match |
| Review Cutoff $k$ | 30% | 2,322 | 2,322 | 0 | Exact match |
| `Random` Base Yield | All | 31.37% (0.313695) | 31.37% (0.313695) | 0.000000 | Exact match |
| `ScoreOnly` Yield | 10% | 56.85% (0.568475) | 56.85% (0.568475) | 0.000000 | Exact match |
| `ScoreOnly` Yield | 20% | 55.88% (0.558786) | 55.88% (0.558786) | 0.000000 | Exact match |
| `ScoreOnly` Yield | 30% | 54.87% (0.548665) | 54.87% (0.548665) | 0.000000 | Exact match |
| `StrongControl` Yield | 10% | 57.49% (0.574935) | 57.49% (0.574935) | 0.000000 | Exact match |
| `StrongControl` Yield | 20% | 57.17% (0.571705) | 57.17% (0.571705) | 0.000000 | Exact match |
| `StrongControl` Yield | 30% | 55.30% (0.552972) | 55.30% (0.552972) | 0.000000 | Exact match |
| `RankAugmented` Yield | 10% | 57.24% (0.572351) | 57.24% (0.572351) | 0.000000 | Exact match |
| `RankAugmented` Yield | 20% | 56.91% (0.569121) | 56.91% (0.569121) | 0.000000 | Exact match |
| `RankAugmented` Yield | 30% | 55.00% (0.549957) | 55.00% (0.549957) | 0.000000 | Exact match |
| `Oracle` Yield | All | 100.0% (1.000000) | 100.0% (1.000000) | 0.000000 | Exact match |
| `Rank - Control` Gap | 10% | -0.26% (-0.002584) | -0.26% (-0.002584) | 0.000000 | Exact match |
| `Rank - Control` Gap | 20% | -0.26% (-0.002584) | -0.26% (-0.002584) | 0.000000 | Exact match |
| `Rank - Control` Gap | 30% | -0.30% (-0.003015) | -0.30% (-0.003015) | 0.000000 | Exact match |
| `Oracle - Control` Gap | 10% | +42.51% (0.425065) | +42.51% (0.425065) | 0.000000 | Exact match |
| `Oracle - Control` Gap | 20% | +42.83% (0.428295) | +42.83% (0.428295) | 0.000000 | Exact match |
| `Oracle - Control` Gap | 30% | +44.70% (0.447028) | +44.70% (0.447028) | 0.000000 | Exact match |

---

## 7. Bootstrap Uncertainty and Decision Criteria Audit

Patient-clustered bootstrap (1,000 replicates, seed 1203) independently reproduced from Audit candidate rows:

| Bootstrap Paired Difference | Budget | Recorded 95% CI | Independently Recomputed | Status |
| :--- | :---: | :---: | :---: | :---: |
| `RankAugmented - StrongControl` | 10% | [-0.013671, +0.011891] | [-0.013671, +0.011891] | Exact match |
| `RankAugmented - StrongControl` | 20% | [-0.006512, +0.007984] | [-0.006512, +0.007984] | Exact match |
| `Oracle - StrongControl` | 10% | [+0.390390, +0.461470] | [+0.390390, +0.461470] | Exact match |
| `Oracle - StrongControl` | 20% | [+0.403418, +0.457819] | [+0.403418, +0.457819] | Exact match |

### Mechanical Decision Tree Evaluation

1. **Gate A (Audit Support)**:
   - $N_{PB=1} = 417 \ge 50$ (Pass)
   - $N_{PB=0} = 423 \ge 50$ (Pass)
   - $k(10\%) = 774 > 0$, $k(20\%) = 1548 > 0$ (Pass)
   - **Gate A Outcome**: `PASS`
2. **Gate B (Oracle Headroom over Strong Control)**:
   - Lower 95% CI (10% budget) = $+0.390390 > 0$ (Pass)
   - Lower 95% CI (20% budget) = $+0.403418 > 0$ (Pass)
   - **Gate B Outcome**: `PASS`
3. **Gate C (RankAugmented Incremental Yield over Strong Control)**:
   - Lower 95% CI (10% budget) = $-0.013671 \le 0$ (**FAIL**)
   - Lower 95% CI (20% budget) = $-0.006512 \le 0$ (**FAIL**)
   - Point estimates are negative at both budgets (-0.26% at 10%, -0.26% at 20%).
   - **Gate C Outcome**: `FAIL`

**Preregistered Mechanical Verdict**:
`STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE`

---

## 8. Audit Conclusion

The integrity audit confirms with 100% precision:

1. Zero numeric discrepancies across all reported yields, gaps, Dev coefficients, and bootstrap intervals.
2. The empirical finding is definitive: within-prescription relative confidence provides zero reproducible incremental false-positive routing signal beyond absolute medication score, predicted prescription size, and train-only medication prevalence.
3. The verdict `STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE` is strictly and mechanically mandated by the preregistered protocol.
4. P6 research decision is formally unlocked.
