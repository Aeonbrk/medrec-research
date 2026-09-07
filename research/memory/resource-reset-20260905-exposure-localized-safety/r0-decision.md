<!-- markdownlint-disable MD013 -->

# R0 Decision Record — Exposure Resource & Premise Admission

## Verdict

`PASS_R0_EXPOSURE_RESOURCE_AND_PREMISE`

- **Gate ID**: `R0_EXPOSURE_RESOURCE_AND_PREMISE`
- **Authoritative Stage**: `RESOURCE_ADMISSION_R0`
- **Next Owner Skill**: `ccf-pipeline-orchestrator`
- **Idea 006 State**: Not created (prohibited in the same round)
- **Target Venue Goal**: First formal method paper for general medication recommendation, targeting at least a CCF-A venue family (e.g., KDD 2026)

---

## 1. Decision Question Answered

> Can raw MIMIC-IV support a method paper in which medication-order recommendation conditions DDI pressure on a pre-order, execution-confirmed active medication state, and is that safety semantic materially different from visit-union DDI co-membership?

**Yes.** Evaluated strictly on the quarantined Discovery partition of raw MIMIC-IV 3.1:

1. **Resource Feasibility**: All 8 required hospital-wide tables exist with linkable chronological order and administration events. Deterministic medication normalization achieves **81.92%** coverage on eligible medication orders and **81.89%** coverage on eligible eMAR administrations.
2. **Premise Scale & Support**: Across **137,764** Discovery patients with medication orders and **323,216** hospitalizations, we observe **1,050,523** eMAR-observed visit-union DDI patient-pair episodes across **68,695** distinct patients and **391** unique DDI relations from the frozen repository DDI asset.
3. **Material Semantic Mismatch**: Exactly **221,157** episodes (**21.0521%**) are `static-only`—meaning both interacting medications were actually administered to the patient in the same hospitalization, yet their completed order intervals and administration records show no execution-confirmed concurrent-active overlap.
4. **Broad Distribution**: The static-only mismatch is widely distributed across **280** distinct DDI relations that each contribute at least 20 static-only episodes (HHI = **0.0131**, Gini = **0.7651**, top-5 share = **15.52%**), proving that the phenomenon is not an artifact of a single drug pair.
5. **Deployable State Feasibility**: A strictly pre-order execution-confirmed active medication state can be constructed using only past information (provider order time from `poe.ordertime` and prior eMAR administrations from `emar.charttime`), without post-order events, future administrations, or discharge-coded current-visit diagnoses/procedures.

All 7 frozen admission floors pass at full precision.

---

## 2. Frozen R0 Decision Criteria Matrix

| Condition | Domain | Frozen Threshold | Observed Value (Full Precision) | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Condition 1** | Resource Availability | All 8 required tables exist with linkable chronological events | All 8 tables present; `poe.ordertime`, `prescriptions.starttime`, `emar.charttime` linkable | **PASS** |
| **Condition 2** | Normalization Coverage | Order coverage $\ge 0.80$ AND Admin coverage $\ge 0.80$ | Order: **0.819248** (81.92%); Admin: **0.818875** (81.89%) | **PASS** |
| **Condition 3** | Action & DDI Vocabulary | Action vocabulary $\ge 100$; DDI-represented concepts $\ge 60$ | Action vocabulary: **131**; DDI-represented concepts: **91** | **PASS** |
| **Condition 4** | Premise Support | Denominator episodes $\ge 1,000$; distinct patients $\ge 500$; unique relations $\ge 30$ | Episodes: **1,050,523**; Distinct patients: **68,695**; Unique relations: **391** | **PASS** |
| **Condition 5** | Semantic Mismatch | `static_only_fraction` $\ge 0.20$ | `static_only_fraction` = **0.21052085...** (21.0521%) | **PASS** |
| **Condition 6** | Mismatch Distribution | At least 10 DDI relations with $\ge 20$ static-only episodes | **280** DDI relations each with $\ge 20$ static-only episodes | **PASS** |
| **Condition 7** | Deployable State Feasibility | Strictly pre-order active state without future events or discharge codes | Feasible via `poe.ordertime < t` and `emar.charttime < t` | **PASS** |

---

## 3. Real Schema Verification & Linkage Mechanics

Mechanical schema verification of raw MIMIC-IV 3.1:

### 3.1 Medication Request / Order Event Time

- Documented provider order event time is defined by `poe.ordertime` (present in 100% of POE medication records).
- Scheduled prescription course start time is defined by `prescriptions.starttime` (present in 99.89% of prescription records).
- Hospitalization key is `hadm_id` (present in 100% of hospital-admitted prescription and administration events).

### 3.2 Linkage Identifiers

- `poe_id`: Present in **99.09%** of Discovery prescriptions (**14,009,505 / 14,138,795**) and **100.00%** of Discovery eMAR administrations (**20,701,305 / 20,701,305**).
- `pharmacy_id`: Present in **100.00%** of Discovery prescriptions (**14,138,795 / 14,138,795**) and **93.46%** of Discovery eMAR administrations (**19,346,908 / 20,701,305**).
- `emar_detail`: Confirms that `product_code` directly corresponds to the hospital formulary code (`formulary_drug_cd`), providing an exact identity match for barcode-scanned medications.

### 3.3 Status & Timing Fields at Order Time

- `prescriptions.stoptime` and `pharmacy.status` (e.g., `'Discontinued via patient discharge'`) are determined retrospectively upon encounter completion or order discontinuation; they are **not** available at inference time and must not be used as online model features.
- Safe past-only information available at decision time $t$:
  1. Orders placed before $t$ (`poe.ordertime < t`);
  2. Scheduled starts before or at $t$ (`prescriptions.starttime <= t`);
  3. Administration records confirmed before $t$ (`emar.charttime < t`);
  4. Encounters and history completely discharged prior to the current admission.

---

## 4. Medication Normalization & DDI Knowledge Asset

### 4.1 Frozen DDI Asset

- **Identity**: SafeDrug / MoleRec Table 1 canonical DDI matrix (`ddi_A_final.pkl` and `voc_final.pkl`).
- **Medication Representation**: WHO ATC Level 4 (4-character alphanumeric codes).
- **Asset SHA256**: `dcb2078931968533835a5ff090dbf8a3afcf3fef415415a013274bea3a4182a7` (exact match to project frozen digest).
- **Content**: 448 canonical pairwise DDI relations across 91 DDI-represented concepts within the 131-concept action vocabulary.

### 4.2 Evaluated Normalization Paths

| Path | Strategy | Order Coverage (`MAIN`) | Admin Coverage | Unique Concepts | DDI Overlap |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Path 1** | SafeDrug `ndc2atc_level4.csv` alone | 40.15% | 40.21% | 131 | 91 |
| **Path 2** | KGDNet `drug_codes_mapping.csv` alone | 56.88% | 56.91% | 131 | 91 |
| **Path 3** | Combined NDC mapping (Path 1 + Path 2) | 63.93% | 63.96% | 131 | 91 |
| **Path 4 (Selected)** | Combined NDC + BIDMC Formulary Consensus | **81.92%** | **81.89%** | **131** | **91** |

Path 4 is deterministic, auditable, and requires no patient-specific hand mapping. Unmapped order events (~18%) are predominantly non-drug supplies (IV bags, diluents, flushes, irrigation solutions, and repackaged vitamins without ATC codes).

---

## 5. Distinction Between Retrospective Diagnostic and Online State

### 5.1 Retrospective Premise Overlap Diagnostic

In the R0 scientific premise diagnostic:

- A pair $(i, j)$ enters the denominator only when both $i$ and $j$ were confirmed administered in that hospitalization (`emar_observed_visit_union`).
- The episode is categorized as `execution_confirmed_overlap` if completed order intervals $[s_i, e_i]$ and $[s_j, e_j]$ overlap and each drug has an administration timestamp within the overlap interval $[\max(s_i, s_j), \min(e_i, e_j)]$.
- Otherwise, the episode is categorized as `static_only` (21.0521% of episodes).
- This retrospective interval construction serves exclusively as a cohort diagnostic to prove that visit-union co-membership collapses temporally disjoint treatments.

### 5.2 Strict Pre-Order Online Active State

For an online recommender evaluated at order decision time $t$:

- Completed `stoptime` is **never** queried.
- Medication $m$ enters the active regimen $A_t$ if and only if:
  1. An order for $m$ was initiated prior to $t$ (`ordertime < t`);
  2. At least one linked or identity-matched administration occurred prior to $t$ (`charttime < t`);
  3. No post-$t$ events, future administrations, or discharge-coded current-visit diagnoses/procedures are accessed.
- Condition 7 is fully satisfied.

---

## 6. Distribution of Static-Only Mismatch

Top 10 DDI relations contributing to static-only episodes:

1. `C07A` (Beta blocking agents) – `J01D` (Other beta-lactam antibacterials): **7,418** episodes
2. `N02A` (Opioids) – `N05B` (Anxiolytics): **7,091** episodes
3. `B01A` (Antithrombotic agents) – `N02A` (Opioids): **6,857** episodes
4. `A02B` (Drugs for acid related disorders) – `N05B` (Anxiolytics): **6,496** episodes
5. `J01D` (Other beta-lactam antibacterials) – `S01A` (Antiinfectives, ophthalmological): **6,464** episodes
6. `N05B` (Anxiolytics) – `N06A` (Antidepressants): **4,988** episodes
7. `C10A` (Lipid modifying agents, plain) – `N02B` (Other analgesics and antipyretics): **4,976** episodes
8. `B01A` (Antithrombotic agents) – `C10A` (Lipid modifying agents, plain): **4,906** episodes
9. `C07A` (Beta blocking agents) – `C10A` (Lipid modifying agents, plain): **4,820** episodes
10. `C03C` (High-ceiling diuretics) – `C10A` (Lipid modifying agents, plain): **4,737** episodes

- **Concentration Statistics**:
  - Herfindahl-Hirschman Index (HHI): **0.0131** (indicates an unconcentrated, highly distributed phenomenon).
  - Gini Coefficient: **0.7651**.
  - Top-5 Concentration Ratio: **15.52%**.
  - Top-10 Concentration Ratio: **26.57%**.
  - Relations with $\ge 20$ static-only episodes: **280** distinct relations (threshold $\ge 10$).

---

## 7. Public & Data Safety Boundary

1. **Quarantine Adherence**:
   - Total MIMIC-IV 3.1 patients: **364,627**.
   - Discovery: **255,345** (70.03%). All R0 scientific aggregates used Discovery only.
   - Dev: **54,647** (14.99%). Completely untouched.
   - Holdout: **54,635** (14.98%). Only membership assigned; zero clinical events or features inspected.
   - Existing project test split: completely untouched.
2. **Privacy Boundary**:
   - Zero patient-level rows, subject identifiers (`subject_id`), hospital admission identifiers (`hadm_id`), or event timestamps are committed to Git.
   - Zero private filesystem paths, server credentials, or SSH host details are committed.
   - All committed artifacts (`r0-summary.json`, `r0-decision.md`, `r0-integrity-audit.md`, `run_r0_exposure_resource_admission.py`) are public-safe aggregates.

---

## 8. Publication Boundary & Non-Claims

R0 PASS establishes only resource feasibility and the validity of the minimum semantic premise. The eventual method paper must respect the following boundaries:

1. **eMAR is not Clinical Appropriateness**: Administration records confirm that a nurse administered a drug; they do not prove the prescription was clinically optimal or free of harm.
2. **Overlap is an Exposure Surrogate, not an ADE**: Execution-confirmed overlap indicates concurrent operational active exposure, not clinical adverse drug event occurrence.
3. **Static-Only is not Safe DDI**: Non-overlapping administration indicates temporal separation during a stay; it must not be claimed as "safe", "prevented ADE", or "false DDI".
4. **R0 PASS is not Model Superiority**: This gate does not evaluate recommender performance, nor does it establish that an exposure-conditioned model will beat a direct exposure-aware scalar reranker or hard filter.

---

## 9. Next Stage Handoff

In accordance with Section 17:

- Local scientific execution for R0 is **terminated**.
- No Idea 006 is created in this run.
- Next owner: `ccf-pipeline-orchestrator`.
- Future sequential steps required before model training:
  1. `ccf-literature-searcher / quick`: Final closest-work delta check on the frozen exposure-conditioned order-time semantics.
  2. If novelty delta remains intact, create Idea 006.
  3. `ccf-experiment-designer`: Freeze Gate 01 comparing end-to-end exposure learning against direct exposure-aware scalar reranking and hard filtering controls under matched exposure-DDI entitlement.
