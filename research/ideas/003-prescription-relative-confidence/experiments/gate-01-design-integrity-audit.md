<!-- markdownlint-disable MD013 -->

# Gate 01 Design Integrity Audit Report

- **Idea**: `003-prescription-relative-confidence`
- **Gate**: `gate-01-prescription-relative-confidence`
- **Audit Stage**: `Design Preregistration (Pre-Execution)`
- **Audit Date**: 2026-09-02
- **Auditor**: `ccf-integrity-auditor`
- **Audit Mode**: `full` (`claim-audit`, `numeric-audit`, `citation-audit`)

---

## Output Contract Summary

```text
Mode: full
Artifacts checked:
  - research/ideas/003-prescription-relative-confidence/README.md
  - research/ideas/003-prescription-relative-confidence/experiments/gate-01-prescription-relative-confidence.md
  - baselines/registry.toml (frozen Comparison Mode baseline registry)
  - research/baselines/preflight/five-model-comparison-qualification.json (upstream qualification authority)
Claim-evidence matrix: See Section 1 below (all preregistered design claims verified; 0 overstatements)
Numeric consistency findings: Pass (all mathematical definitions, split seeds, bootstrap parameters, ridge penalty, budgets, and frozen SHA256 identities verified)
Citation metadata findings: Pass (Frozen identities conform to registry authority)
Citation-context findings: Pass (Scope strictly validation-only hypothesis selection; test split untouched)
Severity: NONE (all design checks passed with exact specification agreement)
Safe edit suggestions: None required
Next CCFA owner: ccf-pipeline-orchestrator (for P0 state / protocol verification)
No-invention status: Verified (100% compliant with authoritative CCFA scientific contract)
```

```text
Design Audit Status: INTEGRITY_PASS
Preregistered Gate 01 protocol verified: yes
P0 verification and P1 implementation unlocked: yes
```

---

## 1. Claim-Evidence Matrix (Design Protocol)

| Protocol Section | Preregistered Specification | Verification Status | Finding / Category | Remediation |
| :--- | :--- | :--- | :--- | :--- |
| `gate-01-prescription-relative-confidence.md` §2 | Central scientific question: incremental false-positive routing information of within-prescription relative confidence beyond StrongControl. | Formally stated as a falsifiable hypothesis. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §3 | Candidate universe $\mathcal{Q}_t = \{m \in \hat{M}_t : d_t(m) > 0\}$, revision operator $R_0(\hat{M}_t, m) = \hat{M}_t \setminus \{m\}$, outcome $Y^{PB}_{t,m} = \mathbf{1}[m \notin M_t]$. | Ground truth $M_t$ is evaluation-only; never a prediction feature. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §5 | Observable $r_t(m) = (\\#\{j: s_t(j) > s_t(m)\} + 0.5 \\cdot \\#\{j \\ne m: s_t(j) == s_t(m)\}) / (n_t - 1)$. | Well-defined mid-rank in $[0, 1]$; $n_t \ge 2$ guaranteed; exact floating-point equality; no $\epsilon$. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §6 | Train-only prevalence $p_{train}(m) = (C_{train}(m) + 1) / (V_{train} + 2)$ using eligible training visits only. | Strict training split isolation; no validation/test leakage; prevalence table restricted. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §8 | StrongControl features $[u, c, f, u \cdot c, u \cdot f]$; RankAugmented features $[u, c, f, u \cdot c, u \cdot f, r]$. | Differs by exactly the single observable $r_t(m)$; controls for score, size, and prevalence. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §9 | Dev-only ridge linear probability estimator with unpenalized intercept and $\lambda = 10^{-6}$. | Fully deterministic; no standardization; no CV; no tuning. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §10 | Fresh validation split: seed `2003`, 529 Dev / 530 Audit patients. Test split untouched. | Patient-disjoint; seed fixed before outcome inspection; zero test indexing. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §11 | Deterministic 5-key tie-breaking for ranking. | Fully specified descending/ascending keys across all policies. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §12 | Review budgets 10%, 20% (primary) and 30% (secondary descriptive). Primary metric $\Delta_{\text{Rank-Control}}$. | Clear budget floors $k(B) = \lfloor B \cdot N_{\text{Audit}} \rfloor$; 30% cannot affect PASS/FAIL. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §13 | Audit support rule: $\ge 50$ $Y^{PB}=1$ patients, $\ge 50$ $Y^{PB}=0$ patients, $k(10\%) > 0, k(20\%) > 0$. | Explicit fallback to `INCONCLUSIVE_INSUFFICIENT_AUDIT_SUPPORT`. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §14 | Patient-clustered bootstrap: 1,000 replicates, seed `1203`, 95% percentile interval. | Frozen Dev coefficients and train prevalence; no refitting inside bootstrap. | **Supported** | None. |
| `gate-01-prescription-relative-confidence.md` §15 | Preregistered decision tree (Gates A, B, C) with explicit stop conditions. | Rigid deterministic stopping; no post-hoc override permitted. | **Supported** | None. |

---

## 2. Frozen Identity Audit

The preregistered protocol binds to the exact authoritative upstream identities established in `research/baselines/preflight/five-model-comparison-qualification.json` and `baselines/registry.toml`:

| Identity Field | Target Specification | Protocol Text Match | Audit Status |
| :--- | :--- | :--- | :--- |
| `model_source_revision` | `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a` | Exact string match | PASS |
| `checkpoint_sha256` | `5de4665570d8730f2c49ca7de963a43847037c00480c52e580d651cd79fd0dca` | Exact string match | PASS |
| `baseline_core_sha256` | `516b7b5ffdc98665d8489305112b12f8ac7df3600dc22ea73fd2b15fbd6bc511` | Exact string match | PASS |
| `adapter_sha256` | `9bb5d114a5c7f834f928a65dbd7e67c352840978ddb5f7a6a396d825cff90531` | Exact string match | PASS |
| `baseline_environment_name` | `medrec-molerec-table1` | Exact string match | PASS |
| `baseline_environment_sha256` | `6a01d31391312fc4a930e9ef23acabf0223b2f979164c98938a6f4473e0d4dda` | Exact string match | PASS |
| `dataset_id` | `molerec-table1-comparison-v1-1` | Exact string match | PASS |
| `dataset_manifest_sha256` | `82d4efc2e03e22008d0aa80e862cedfd4538dc1038be45252abdd21fc3e04712` | Exact string match | PASS |
| `snapshot_id` | `molerec-table1-c721-www23` | Exact string match | PASS |
| `snapshot_sha256` | `42c09b2a23fc55b9484f2a25fa55231b95f2bae717f35b6e1cb60827c1b18f58` | Exact string match | PASS |
| `medication_vocabulary_sha256` | `6f24de0f8d438b943814094964dee0287697b8951a174321d19a3c17ee504c08` | Exact string match | PASS |
| `ddi_asset_sha256` | `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` | Exact string match | PASS |
| `feature_availability_sha256` | `9e403591dce7ec8cc202968d45dca81643f7220564816039fff964dd32cf7fc9` | Exact string match | PASS |

---

## 3. Data Leakage and Boundary Firewall Audit

1. **Test Split Isolation**: Protocol explicitly forbids indexing, staging, predicting, or evaluating test data. Zero test references permitted in runner code.
2. **Train-Only Prevalence Firewall**: Prevalence is computed solely over eligible visits of training patients. No validation or test data enters prevalence counts.
3. **Partition Independence**: Fresh seed `2003` shuffle over 1,059 validation patients ensures zero leakage from Idea 001 or Idea 002 partitions. Dev and Audit are strictly patient-disjoint.
4. **Dev-Only Estimator Fitting**: Ridge regression weights $\hat{\beta}_0, \hat{\beta}$ are fit strictly on Dev candidates. Audit candidates are evaluated using frozen coefficients.
5. **No Upstream Score Leakage**: While candidate corpora from Idea 001/002 contained only DDI-active candidates, Idea 003 requires regeneration of the full predicted prescription $\hat{M}_t$ to compute rank $r_t(m)$ accurately across all co-predicted medications.
6. **Privacy and Public-Safe Boundary**: Ground-truth target prescriptions, raw candidate rows, patient identifiers, visit identifiers, private checkpoint paths, and the per-medication prevalence table are designated as restricted research data and excluded from Git.

---

## 4. Decision Tree and Authorized Wording Audit

1. **Support Gate (Gate A)**: Requires $\ge 50$ Audit patients with $Y^{PB}=1$ and $\ge 50$ with $Y^{PB}=0$.
2. **Oracle Headroom Gate (Gate B)**: Requires $LowerCI_{95\%}(\text{Oracle} - \text{StrongControl}) > 0$ at both 10% and 20% budgets. Failing this yields `STOP_NO_RESIDUAL_HEADROOM_AFTER_STRONG_CONTROL`.
3. **Signal Gate (Gate C)**: Requires $LowerCI_{95\%}(\text{RankAugmented} - \text{StrongControl}) > 0$ at both 10% and 20% budgets. Failing this yields `STOP_NO_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE`. Passing yields `PASS_INCREMENTAL_PRESCRIPTION_RELATIVE_CONFIDENCE`.
4. **Wording Integrity**: Authorized PASS and FAIL wording are strictly verbatim from the CCFA contract, precluding unsupported generalizations (e.g., claims of clinical safety, causality, or cross-backbone optimality).

---

## 5. Auditor Conclusion

The design artifacts for Gate 01 of Idea 003 are complete, mathematically consistent, and fully verified against repository standards.

- **Verdict**: **`INTEGRITY_PASS`**
- **Authorization**: P0 state/protocol verification and P1 implementation are authorized to proceed.
