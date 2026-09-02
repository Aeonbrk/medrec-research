<!-- markdownlint-disable MD013 -->

# Gate 01 Integrity Audit Report

- **Idea**: `002-score-geometry-sufficiency`
- **Gate**: `gate-01-score-geometry-sufficiency`
- **Formal Run ID**: `gate-01-score-geometry-sufficiency-20260902-174013`
- **Harness Revision**: `28fc24c64998c81563446f3f8e5bc10340e2b17b`
- **Audit Date**: 2026-09-02
- **Auditor**: `ccf-integrity-auditor`
- **Audit Mode**: `full` (`numeric-audit`, `claim-audit`, `citation-audit`)

---

## Output Contract Summary

```text
Mode: full
Artifacts checked:
  - research/ideas/002-score-geometry-sufficiency/experiments/gate-01-score-geometry-sufficiency.md
  - research/ideas/002-score-geometry-sufficiency/experiments/run_score_geometry_sufficiency_gate.py (frozen at 28fc24c64998c81563446f3f8e5bc10340e2b17b)
  - research/ideas/002-score-geometry-sufficiency/experiments/gate-01-summary.json (SHA256: ee2ef10ffb9bd9b4e52135f6062e2e4375c6dabc7c53799f436117a39b476a58)
  - 319-lab:/root/zhb/medrec-data/runs/ideas/002-score-geometry-sufficiency/gate-01-score-geometry-sufficiency-20260902-174013/gate-01-candidates.jsonl
  - 319-lab:/root/zhb/medrec-data/runs/ideas/002-score-geometry-sufficiency/gate-01-score-geometry-sufficiency-20260902-174013/gate-01-dev-map.json
  - 319-lab:/root/zhb/medrec-data/runs/ideas/002-score-geometry-sufficiency/gate-01-score-geometry-sufficiency-20260902-174013/gate-01-summary.json
  - 319-lab:/root/zhb/medrec-data/runs/ideas/001-tension-guided-verification/gate-02-confidence-sufficiency-20260902-155433/gate-02-candidates.jsonl (SHA256: 50b8f7587f44ec81dd5ec0ec188d953cf9edfbb332279ce3fb759ae33ed2e736)
Claim-evidence matrix: See Section 1 below (all 4 empirical claims supported; 0 overstatements)
Numeric consistency findings: Pass (15,549 rows verified, 0 invariant failures, 0 partition leaks, 0 split mismatches, 0 diffs across all yields, gaps, cutpoints, bin risks, and bootstrap intervals)
Citation metadata findings: Pass (Frozen identities conform to registry authority)
Citation-context findings: Pass (Protocol scope strictly validation-only hypothesis selection)
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
| `gate-01-score-geometry-sufficiency.md` §2 | "A preregistered low-complexity non-monotone mapping of the frozen MoleRec medication score contains reproducible false-positive ranking structure that raw ScoreOnly fails to exploit." | Tested via 5-bin quintile map on 8,127 Audit candidates across 422 eligible patients. | **Supported as Falsified** | Formal hypothesis is cleanly falsified with zero numeric discrepancy. |
| `gate-01-summary.json` & §15 | `ScoreOnly` sorting ($s_t(m) \uparrow$) yields 61.21% (10% budget), 59.32% (20% budget), 56.32% (30% budget), substantially beating Random (31.46%). | Empirically verified: $Score - Random = +29.74\%$ (10%, 95% CI: [26.60%, 33.75%]), $+27.86\%$ (20%, 95% CI: [25.28%, 30.16%]). | **Supported** | None. |
| `gate-01-summary.json` & §15 | Residual Oracle headroom survives on fresh Idea-002 Audit split: Oracle achieves 100.0% yield, beating ScoreOnly by $+38.79\%$ (10% budget) and $+40.68\%$ (20% budget). | Empirically verified: $Oracle - Score = +38.79\%$ (10%, 95% CI: [34.36%, 42.29%]), $+40.68\%$ (20%, 95% CI: [37.65%, 44.06%]). Both lower CIs $> 0$. | **Supported** | None. |
| `gate-01-summary.json` & §15 | `ScoreGeometry` achieves identical yield to `ScoreOnly` ($Geometry - Score = 0.0\%$, 95% CI: [0.0%, 0.0%] across all budgets). Preregistered score map supplies zero incremental routing signal. | Empirically verified: Dev quintile map has strictly monotonic empirical risks ($\hat p_1 > \hat p_2 > \hat p_3 > \hat p_4 > \hat p_5$). With raw score ascending tie-break, candidate ordering collapses identically to `ScoreOnly`. | **Supported** | None. |

### Explicitly Disallowed Claims Check

The audit confirmed that none of the forbidden claims are asserted in active repository documentation:

- "Score geometry universally fails across all possible bin counts or representations" (Not asserted; scoped to preregistered 5-bin map)
- "Recommender confidence is the only useful signal" (Not asserted; residual Oracle headroom remains $+38.79\%$ to $+40.68\%$)
- Clinical safety, patient benefit, or clinician intent claims (Not asserted; retrospective benchmark metric definitions strictly maintained)
- Prospective prescribing validity (Explicitly disclaimed in protocol §1.3 and §20)
- Tension route revival (Explicitly disclaimed)

---

## 2. Frozen Identity Audit

The formal public summary records exactly the 10 frozen identities, verified against registry authority and execution environment:

| Identity Field | Expected Frozen Target | Recorded in `gate-01-summary.json` | Audit Status |
| :--- | :--- | :--- | :--- |
| `harness_revision` | `28fc24c64998c81563446f3f8e5bc10340e2b17b` | `28fc24c64998c81563446f3f8e5bc10340e2b17b` | Exact match |
| `model_source_revision` | `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` | `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` | Exact match |
| `checkpoint_sha256` | `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca` | `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca` | Exact match |
| `baseline_core_sha256` | `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511` | `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511` | Exact match |
| `adapter_sha256` | `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531` | `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531` | Exact match |
| `baseline_environment_name` | `medrec-molerec-table1` | `medrec-molerec-table1` | Exact match |
| `dataset_manifest_sha256` | `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712` | `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712` | Exact match |
| `snapshot_sha256` | `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58` | `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58` | Exact match |
| `medication_vocabulary_sha256` | `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08` | `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08` | Exact match |
| `ddi_asset_sha256` | `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` | `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` | Exact match |

---

## 3. Candidate Corpus & Row-Level Invariant Audit

Evaluated on all 15,549 rows of `gate-01-candidates.jsonl`:

1. **Row Count**: exactly 15,549 rows, matching upstream audited candidate corpus `gate-02-confidence-sufficiency-20260902-155433` (SHA256: `50b8f7587f44ec81dd5ec0ec188d953cf9edfbb332279ce3fb759ae33ed2e736`).
2. **Review Universe Invariant**: active DDI degree $d_t(m) > 0$ holds for 15,549 / 15,549 rows.
3. **Singleton Deletion Invariant**: $\Delta V_{t,m} = -d_t(m) < 0$ holds for 15,549 / 15,549 rows.
4. **Pareto-Beneficial Definition**: $Y^{PB}_{t,m} = \mathbf 1[\Delta J_{t,m} \ge 0 \land \Delta V_{t,m} < 0]$ holds for 15,549 / 15,549 rows.
5. **Score Domain**: $s_t(m) \in [0, 1]$ and finite for 15,549 / 15,549 rows.
6. **Partition Assignment**: `gate01_partition` is strictly `"dev"` or `"audit"` for 15,549 / 15,549 rows.
7. **Zero Patient Overlap**: 0 candidate rows belong to both partitions; 0 patients have candidate rows spanning both Dev and Audit.
8. **Dead Metadata Firewall**: Historical `gate02_partition` is completely absent from `gate-01-candidates.jsonl` output schema.

**Invariant Failures Count**: `0`.

---

## 4. Fresh Split Integrity Audit

The complete validation cohort was independently partitioned using standard library `random.Random(2002)` over $0 \dots 1058$ ($N=1059$):

| Cohort Metric | Expected (Preregistered) | Recorded (Public Summary) | Independently Recomputed | Diff | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Complete Validation Patients | 1,059 | 1,059 | 1,059 | 0 | Exact match |
| Dev Allocated Patients | 529 | 529 | 529 | 0 | Exact match |
| Audit Allocated Patients | 530 | 530 | 530 | 0 | Exact match |
| Dev Eligible Patients (with $\mathcal Q$) | 436 | 436 | 436 | 0 | Exact match |
| Dev Candidates | 7,422 | 7,422 | 7,422 | 0 | Exact match |
| Audit Eligible Patients (with $\mathcal Q$) | 422 | 422 | 422 | 0 | Exact match |
| Audit Candidates | 8,127 | 8,127 | 8,127 | 0 | Exact match |
| Total Candidates ($7,422 + 8,127$) | 15,549 | 15,549 | 15,549 | 0 | Exact match |
| Dev-Audit Patient Overlap | 0 | 0 | 0 | 0 | Exact match |
| Test Split Contamination | None | None | None | 0 | Verified |

---

## 5. Dev-Only Score Geometry Map Audit

Computed strictly from the 7,422 Dev partition candidates without any access to Audit labels:

### Cutpoints

| Quintile $q$ | Target Cutpoint Index ($\lceil q N_D \rceil$) | Recorded Cutpoint | Independently Recomputed | Status |
| :---: | :---: | :---: | :---: | :---: |
| 0.2 | 1485 (score sorted index 1484) | 0.75836181640625 | 0.75836181640625 | Exact match |
| 0.4 | 2969 (score sorted index 2968) | 0.8908411264419556 | 0.8908411264419556 | Exact match |
| 0.6 | 4454 (score sorted index 4453) | 0.9492053389549255 | 0.9492053389549255 | Exact match |
| 0.8 | 5938 (score sorted index 5937) | 0.9794603586196899 | 0.9794603586196899 | Exact match |

### Empirical Bin Risk and Ordering

| Bin | Score Interval | Dev Candidates | Distinct Patients | Dev $P(Y^{PB}=1)$ | Priority Rank | Status |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| B1 | $s \le 0.758362$ | 1,485 | 409 | 0.581145 (863 / 1485) | 1 | Exact match |
| B2 | $0.758362 < s \le 0.890841$ | 1,484 | 403 | 0.462938 (687 / 1484) | 2 | Exact match |
| B3 | $0.890841 < s \le 0.949205$ | 1,485 | 412 | 0.317172 (471 / 1485) | 3 | Exact match |
| B4 | $0.949205 < s \le 0.979460$ | 1,484 | 408 | 0.179919 (267 / 1484) | 4 | Exact match |
| B5 | $s > 0.979460$ | 1,484 | 362 | 0.053908 (80 / 1484) | 5 | Exact match |

### Order Equivalence Finding

Because $\hat p_1 > \hat p_2 > \hat p_3 > \hat p_4 > \hat p_5$ is strictly monotonic non-increasing with model score, and within each bin candidate tie-breaking sorts by $s$ ascending, the induced `ScoreGeometry` candidate ranking on Dev is **100% order-equivalent to raw ScoreOnly**:

- `dev_score_geometry.order_equivalent_to_scoreonly`: `true` (Exact match).
- `dev_early_stop_verdict`: `STOP_DEV_ORDER_EQUIVALENT` (Condition met per protocol §9.4).

---

## 6. Audit Policy Yields, Gaps & Headroom Audit

Evaluated on all 8,127 Audit candidates across 422 patients using the frozen Dev quintile map:

| Policy / Metric | Budget | Recorded in Summary | Independently Recomputed | Difference | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Random** ($P(Y^{PB}=1)$) | All | 0.31463024486280300 | 0.31463024486280300 | 0.0 | Exact match |
| **ScoreOnly** | 10% | 0.61206896551724130 | 0.61206896551724130 | 0.0 | Exact match |
| | 20% | 0.59323076923076920 | 0.59323076923076920 | 0.0 | Exact match |
| | 30% | 0.56316652994257590 | 0.56316652994257590 | 0.0 | Exact match |
| **ScoreGeometry** | 10% | 0.61206896551724130 | 0.61206896551724130 | 0.0 | Exact match |
| | 20% | 0.59323076923076920 | 0.59323076923076920 | 0.0 | Exact match |
| | 30% | 0.56316652994257590 | 0.56316652994257590 | 0.0 | Exact match |
| **Oracle** | 10% | 1.00000000000000000 | 1.00000000000000000 | 0.0 | Exact match |
| | 20% | 1.00000000000000000 | 1.00000000000000000 | 0.0 | Exact match |
| | 30% | 1.00000000000000000 | 1.00000000000000000 | 0.0 | Exact match |
| **Score - Random** | 10% | 0.29743872065443830 | 0.29743872065443830 | 0.0 | Exact match |
| | 20% | 0.27860052436796623 | 0.27860052436796623 | 0.0 | Exact match |
| | 30% | 0.24853628507977288 | 0.24853628507977288 | 0.0 | Exact match |
| **Geometry - Score** | 10% | 0.00000000000000000 | 0.00000000000000000 | 0.0 | Exact match |
| | 20% | 0.00000000000000000 | 0.00000000000000000 | 0.0 | Exact match |
| | 30% | 0.00000000000000000 | 0.00000000000000000 | 0.0 | Exact match |
| **Oracle - Score** | 10% | 0.38793103448275870 | 0.38793103448275870 | 0.0 | Exact match |
| | 20% | 0.40676923076923077 | 0.40676923076923077 | 0.0 | Exact match |
| | 30% | 0.43683347005742410 | 0.43683347005742410 | 0.0 | Exact match |
| **Oracle - Geometry** | 10% | 0.38793103448275870 | 0.38793103448275870 | 0.0 | Exact match |
| | 20% | 0.40676923076923077 | 0.40676923076923077 | 0.0 | Exact match |
| | 30% | 0.43683347005742410 | 0.43683347005742410 | 0.0 | Exact match |
| **Geometry Residual Capture** | 10% | 0.00000000000000000 | 0.00000000000000000 | 0.0 | Exact match |
| | 20% | 0.00000000000000000 | 0.00000000000000000 | 0.0 | Exact match |
| | 30% | 0.00000000000000000 | 0.00000000000000000 | 0.0 | Exact match |

---

## 7. Patient-Clustered Bootstrap Uncertainty Audit

Resampling unit: Audit patient ($N=422$ unique clusters). Replicates: 1,000, seed: 1203.

| Metric | Budget | Recorded 95% CI | Independently Recomputed 95% CI | Status |
| :--- | :---: | :---: | :---: | :---: |
| **ScoreOnly Yield** | 10% | [0.577102, 0.656406] | [0.577102, 0.656406] | Exact match |
| | 20% | [0.559443, 0.623548] | [0.559443, 0.623548] | Exact match |
| | 30% | [0.536761, 0.588607] | [0.536761, 0.588607] | Exact match |
| **ScoreGeometry Yield** | 10% | [0.577102, 0.656406] | [0.577102, 0.656406] | Exact match |
| | 20% | [0.559443, 0.623548] | [0.559443, 0.623548] | Exact match |
| | 30% | [0.536761, 0.588607] | [0.536761, 0.588607] | Exact match |
| **Score - Random** | 10% | [0.265999, 0.337452] | [0.265999, 0.337452] | Exact match |
| | 20% | [0.252789, 0.301563] | [0.252789, 0.301563] | Exact match |
| | 30% | [0.230716, 0.265182] | [0.230716, 0.265182] | Exact match |
| **Geometry - Score** | 10% | [0.000000, 0.000000] | [0.000000, 0.000000] | Exact match |
| | 20% | [0.000000, 0.000000] | [0.000000, 0.000000] | Exact match |
| | 30% | [0.000000, 0.000000] | [0.000000, 0.000000] | Exact match |
| **Oracle - Score** | 10% | [0.343594, 0.422898] | [0.343594, 0.422898] | Exact match |
| | 20% | [0.376452, 0.440557] | [0.376452, 0.440557] | Exact match |
| | 30% | [0.411393, 0.462322] | [0.411393, 0.462322] | Exact match |
| **Oracle - Geometry** | 10% | [0.343594, 0.422898] | [0.343594, 0.422898] | Exact match |
| | 20% | [0.376452, 0.440557] | [0.376452, 0.440557] | Exact match |
| | 30% | [0.411393, 0.462322] | [0.411393, 0.462322] | Exact match |
| **Geometry Residual Capture** | 10% | [0.000000, 0.000000] | [0.000000, 0.000000] | Exact match |
| | 20% | [0.000000, 0.000000] | [0.000000, 0.000000] | Exact match |
| | 30% | [0.000000, 0.000000] | [0.000000, 0.000000] | Exact match |

---

## 8. Decision Tree Verification

1. **Gate 01-A Support Check**:
   - Audit beneficial patients ($Y^{PB}=1$): $419 \ge 50$ (Pass)
   - Audit non-beneficial patients ($Y^{PB}=0$): $421 \ge 50$ (Pass)
   - `support_sufficient`: `true`
2. **Gate 01-B Residual Headroom Check**:
   - $\text{LowerCI}_{95\%}[\text{Gap}_{Oracle-Score}(10\%)] = 0.343594 > 0$ (Pass)
   - $\text{LowerCI}_{95\%}[\text{Gap}_{Oracle-Score}(20\%)] = 0.376452 > 0$ (Pass)
   - Residual Oracle headroom independently holds on the fresh Audit partition.
3. **Gate 01-C Incremental Score Geometry Check**:
   - $\text{LowerCI}_{95\%}[\text{Gap}_{Geometry-Score}(10\%)] = 0.000000 \not> 0$ (Fail)
   - $\text{LowerCI}_{95\%}[\text{Gap}_{Geometry-Score}(20\%)] = 0.000000 \not> 0$ (Fail)
   - Verdict condition: Fail at both primary budgets.
   - Formal Decision Tree Verdict: **`STOP_NO_INCREMENTAL_SCORE_GEOMETRY`**.
4. **Dev Early Stop Diagnostic**:
   - `order_equivalent_to_scoreonly` on Dev: `true`
   - `dev_early_stop_verdict`: `STOP_DEV_ORDER_EQUIVALENT` (Independently confirmed).

---

## 9. Final Auditor Verdict

```text
P5 Status: INTEGRITY_PASS
Audit Verdict: PASS
Formal Gate 01 verdict independently reproduced: yes
P6 research decision unlocked: yes
```
