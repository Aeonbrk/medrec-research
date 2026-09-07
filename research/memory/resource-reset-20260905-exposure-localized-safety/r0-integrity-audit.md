<!-- markdownlint-disable MD013 -->

# R0 Integrity Audit — Exposure Resource & Premise Admission

## Audit Metadata

- **Audit Tool**: `ccf-integrity-auditor`
- **Audit Modes**: `claim-audit`, `numeric-audit`, `quarantine-and-privacy-audit`
- **Audit Date**: 2026-09-07
- **Target Gate**: `R0_EXPOSURE_RESOURCE_AND_PREMISE`
- **Audited Artifacts**:
  - `research/memory/resource-reset-20260905-exposure-localized-safety/r0-summary.json`
  - `research/memory/resource-reset-20260905-exposure-localized-safety/r0-decision.md`
  - `research/memory/resource-reset-20260905-exposure-localized-safety/run_r0_exposure_resource_admission.py`
  - `research/memory/resource-reset-20260905-exposure-localized-safety/r0-resource-admission-protocol.md`
- **Audit Verdict**: `PASS_ALL_AUDITS`

---

## 1. Claim Audit (Claim-Support & Semantic Alignment)

| Candidate Claim / Statement | Target Text Location | Audited Semantic Boundary | Evidence Anchor | Finding |
| :--- | :--- | :--- | :--- | :--- |
| eMAR administration reflects administered drug events | `r0-decision.md` §8.1 | eMAR records that a nurse administered a drug; it is **not** treated as clinical appropriateness or optimal therapy | `r0-summary.json` | **SUPPORTED** |
| Execution-confirmed overlap is an operational exposure surrogate | `r0-decision.md` §5.1, §8.2 | Overlap indicates temporal co-occurrence of active orders with administration evidence; it is **not** an ADE label or proof of clinical harm | `r0-summary.json` | **SUPPORTED** |
| Static-only episodes represent non-concurrent administration | `r0-decision.md` §1, §5.1, §8.3 | Both drugs administered during the same stay without concurrent-active overlap; **not** claimed as "safe DDI", "false DDI", or "prevented ADE" | `r0-summary.json` | **SUPPORTED** |
| R0 PASS establishes resource feasibility and premise validity only | `r0-decision.md` §1, §8.4 | R0 PASS admits the data resource and premise; does **not** claim model superiority, algorithm success, or CCF-A readiness | `r0-summary.json` | **SUPPORTED** |
| Strictly pre-order active state is causally deployable | `r0-decision.md` §5.2 | State at decision time $t$ queries only prior POE orders and prior eMAR administrations; no future administrations or discharge codes used | `run_r0_...py` | **SUPPORTED** |
| No Idea 006 or model training in R0 | `r0-decision.md` Header, §9 | Local scientific execution stops immediately; Idea 006 is not created | Workspace status | **SUPPORTED** |

**Claim Audit Summary**: All claims conform strictly to the required non-claim boundaries. No clinical outcome inflation, ADE conflation, or premature success assertions detected.

---

## 2. Numeric Audit (Value Consistency & Protocol Floors)

| Metric / Quantity | `r0-summary.json` | `r0-decision.md` | Protocol Floor | Consistency Check | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Raw MIMIC-IV Version | `"3.1"` | `3.1` | Local authorized version | Exact match | **PASS** |
| Required Tables Available | `8/8` (100.0%) | `8/8` (100.0%) | All 8 required tables | Exact match | **PASS** |
| Total Cohort Patients | `364,627` | `364,627` | Total in `patients.csv.gz` | Exact match | **PASS** |
| Discovery Patients | `255,345` | `255,345` | Hash fraction $< 0.70$ (70.03%) | Exact match | **PASS** |
| Dev Patients | `54,647` | `54,647` | Hash fraction $[0.70, 0.85)$ (14.99%) | Exact match | **PASS** |
| Holdout Patients | `54,635` | `54,635` | Hash fraction $[0.85, 1.00]$ (14.98%) | Exact match | **PASS** |
| Discovery Patients with Orders | `137,764` | `137,764` | Distinct Discovery patients | Exact match | **PASS** |
| Discovery Hospitalizations with Orders | `323,216` | `323,216` | Distinct Discovery `hadm_id` | Exact match | **PASS** |
| Total Discovery Prescription Rows | `14,138,795` | `14,138,795` | Event-level count | Exact match | **PASS** |
| Main Medication Orders | `11,701,152` | `11,701,152` | `drug_type == 'MAIN'` | Exact match | **PASS** |
| Eligible eMAR Administration Events | `20,701,305` | `20,701,305` | Event-level admin count | Exact match | **PASS** |
| Order Direct Link (`poe_id`) | `14,009,505` (99.09%) | `99.09%` | None specified | Exact match | **PASS** |
| Order Direct Link (`pharmacy_id`) | `14,138,795` (100.0%) | `100.00%` | None specified | Exact match | **PASS** |
| Admin Direct Link (`poe_id`) | `20,701,305` (100.0%) | `100.00%` | None specified | Exact match | **PASS** |
| Admin Direct Link (`pharmacy_id`) | `19,346,908` (93.46%) | `93.46%` | None specified | Exact match | **PASS** |
| Order Normalization Coverage (Main) | `0.819248` (81.92%) | `81.92%` | $\ge 0.80$ (80.00%) | Exact match; passes floor | **PASS** |
| Administration Normalization Coverage | `0.818875` (81.89%) | `81.89%` | $\ge 0.80$ (80.00%) | Exact match; passes floor | **PASS** |
| Action Vocabulary Size | `131` | `131` | $\ge 100$ | Exact match; passes floor | **PASS** |
| DDI Knowledge Asset SHA256 | `dcb20789...` | `dcb20789...` | Exact match to frozen digest | Exact match | **PASS** |
| DDI-Represented Concepts | `91` | `91` | $\ge 60$ | Exact match; passes floor | **PASS** |
| eMAR-Observed Visit-Union Episodes | `1,050,523` | `1,050,523` | $\ge 1,000$ | Exact match; passes floor | **PASS** |
| Execution-Confirmed Overlap Episodes | `829,366` | `829,366` | Operational overlap count | Exact match | **PASS** |
| Static-Only Episodes | `221,157` | `221,157` | Denominator minus overlap | Exact match | **PASS** |
| `static_only_fraction` | `0.21052085...` | `21.0521%` | $\ge 0.20$ (20.00%) | Exact match; passes floor | **PASS** |
| Distinct Contributing Patients | `68,695` | `68,695` | $\ge 500$ | Exact match; passes floor | **PASS** |
| Unique DDI Relations in Denominator | `391` | `391` | $\ge 30$ | Exact match; passes floor | **PASS** |
| Relations with $\ge 20$ Static-Only | `280` | `280` | $\ge 10$ | Exact match; passes floor | **PASS** |
| Top-5 Concentration Ratio | `0.155211` | `15.52%` | None specified | Exact match | **PASS** |
| Top-10 Concentration Ratio | `0.265662` | `26.57%` | None specified | Exact match | **PASS** |
| Herfindahl-Hirschman Index (HHI) | `0.013105` | `0.0131` | Low concentration ($< 0.15$) | Exact match | **PASS** |
| Gini Coefficient | `0.765109` | `0.7651` | Distribution metric | Exact match | **PASS** |

**Numeric Audit Summary**: Complete numerical agreement across summary JSON and decision markdown. All condition floors evaluated at full precision without rounding tricks.

---

## 3. Quarantine & Privacy Audit

1. **Quarantine Partition Isolation**:
   - Dev subset (54,647 patients) was completely unused during R0 scientific analysis.
   - Holdout subset (54,635 patients) only had membership assigned from `subject_id` hash; zero medication events, orders, administrations, features, or DDI metrics were inspected.
   - Existing project test split remains completely untouched.
2. **Public-Safe Artifact Audit**:
   - Checked `r0-summary.json`, `r0-decision.md`, `r0-integrity-audit.md`, and `run_r0_exposure_resource_admission.py`.
   - Confirmed: Zero patient identifiers (`subject_id`), hospitalization admission identifiers (`hadm_id`), raw timestamps, or individual patient trajectories are present.
   - Confirmed: Zero private filesystem paths, database credentials, server hostnames, or SSH connection strings are present in committed files.

---

## 4. Final Audit Verdict

`PASS_ALL_AUDITS`

- Claim-Evidence Consistency: **PASS**
- Numeric Consistency: **PASS**
- Protocol Threshold Compliance: **PASS**
- Quarantine Integrity: **PASS**
- Privacy & Anonymity: **PASS**

Next owner: `ccf-pipeline-orchestrator`.
