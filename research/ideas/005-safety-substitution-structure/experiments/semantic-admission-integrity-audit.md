<!-- markdownlint-disable MD013 -->

# Semantic Admission Integrity Audit Report — Safety-Preserving Substitution Structure

- **Idea**: `005-safety-substitution-structure`
- **Gate**: `semantic-admission`
- **Formal Run ID**: `gate-01-output-structure-signature-20260904-155810`
- **Protocol Commit**: `587e3f626cf8c5849553176f8f1fae3aa2eb0d84`
- **Auditor**: `ccf-integrity-auditor`
- **Audit Mode**: `full` (`claim-audit`, `citation-audit`, `numeric-audit`)
- **Integrity Verdict**: `INTEGRITY_PASS`

---

## Output Contract Summary

```text
Mode: full (claim-audit + citation-audit + numeric-audit)
Artifacts checked:
  - research/ideas/005-safety-substitution-structure/experiments/semantic-admission-protocol.md (commit: 587e3f626cf8c5849553176f8f1fae3aa2eb0d84)
  - research/ideas/005-safety-substitution-structure/experiments/semantic-candidate-relations.json
  - research/ideas/005-safety-substitution-structure/experiments/semantic-admission-ledger.md
  - research/ideas/005-safety-substitution-structure/experiments/semantic-admission-summary.json
  - 319-lab:/root/zhb/medrec-data/runs/ideas/005-safety-substitution-structure/gate-01-output-structure-signature-20260904-155810/semantic-admission-restricted-support.json
  - 319-lab:/root/zhb/medrec-data/runs/ideas/005-safety-substitution-structure/gate-01-output-structure-signature-20260904-155810/semantic-admission-blinded-relations.json
Claim-evidence matrix: See Section 1 below (100% claims traceable to audited evidence; scope bounds strictly respected)
Numeric consistency findings: Pass (exact agreement across candidate extraction, concentration gate, admitted patient counts, and decision thresholds)
Citation metadata findings: Pass (all 23 entries backed by stable DOI/URL, recognized specialty-society/national guidelines, correct tiers)
Citation-context findings: Pass (admitted relations possess explicit alternative positioning; rejected relations correctly distinguish complementary combinations, sequential escalation, or disjoint severity)
Severity: NONE
Safe edit suggestions: None required
Next CCFA owner: execution agent / research decision
No-invention status: Verified (100% independently derived from frozen protocol, restricted Gate 01 run, and external guideline evidence)
```

```text
Integrity Status: INTEGRITY_PASS
Mechanical decision independently reproduced: yes
Research decision unlocked: yes
```

---

## 1. Claim-Evidence Matrix

| Claim Location | Claim Statement | Evidence Status | Finding / Category | Verification Result |
| :--- | :--- | :--- | :--- | :--- |
| `semantic-admission-protocol.md` §4 | "Each semantic unit contributes exactly one deterministic directed class relation $y_t \to a_t$." | 1,121 calibrated signature units evaluated across the 20 high-support groups. | **Supported** | SplitMassFN: $\arg\max_{m \in G \setminus \{y_t\}} p_t(m)$; DuplicateSiblingFP: $\arg\max_{m \in (\hat M_t^{cal} \cap G) \setminus \{y_t\}} p_t(m)$; tie-break: ATC-3 ascending. |
| `semantic-admission-summary.json` §Semantic A | Supported relations cover $\ge 50\%$ of calibrated signature patients and span $\ge 3$ ATC-2 parents. | 23 supported relations cover 381 distinct patients (96.70%) across 12 ATC-2 parents. | **Supported** | Semantic A concentration gate unconditionally PASSED. |
| `semantic-admission-ledger.md` §1 | Every ADMIT relation is supported by Tier-A clinical guideline evidence. | All 4 admitted relations cite ACC/AHA or ATS/IDSA guidelines explicitly positioning classes as alternatives. | **Supported** | 0 ADMIT relations based on Tier-B or Tier-C alone. |
| `semantic-admission-ledger.md` §Negative Control | `NAIVE_SHARED_INDICATION = true` is tracked separately and does not determine PASS. | 14 relations have shared indication; 10 are rejected due to complementary combination or distinct disease severity. | **Supported** | Strong negative control prevented semantic inflation. |
| `semantic-admission-summary.json` §Semantic B | Strict ADMIT relations fail the $\ge 25\%$ coverage and $\ge 3$ qualifying parent threshold. | 75 distinct patients (19.04% < 25%) across 2 parents (`C09`: 11 pts, `J01`: 65 pts; $2 < 3$). | **Supported** | Semantic B criteria fail mechanically. |
| `semantic-admission-summary.json` §Verdict | Mechanical verdict is `STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`. | Direct mechanical consequence of Semantic B failure. | **Supported** | Matches preregistered decision tree exactly. |

---

## 2. Evidence Hierarchy & Citation Audit

1. **Tier-A Verification for ADMIT**:
   - `C09A -> C09C`: 2017 ACC/AHA High Blood Pressure Guideline ([10.1161/HYP.0000000000000065](https://doi.org/10.1161/HYP.0000000000000065)) & 2022 AHA/ACC/HFSA Heart Failure Guideline ([10.1161/CIR.0000000000001063](https://doi.org/10.1161/CIR.0000000000001063)). Explicit first-line alternatives for hypertension/HFrEF; ARB alternative when ACEi intolerant; dual blockade contraindicated. (Tier A validated).
   - `J01C -> J01D`: 2011 IDSA Neutropenic Fever Guideline ([10.1093/cid/cir073](https://doi.org/10.1093/cid/cir073)) & 2016 IDSA/ATS HAP/VAP Guideline ([10.1093/cid/ciw353](https://doi.org/10.1093/cid/ciw353)). Broad-spectrum antipseudomonal monotherapy alternatives (piperacillin-tazobactam vs cefepime/meropenem). (Tier A validated).
   - `J01D -> J01M` & `J01M -> J01D`: 2019 ATS/IDSA CAP Guideline ([10.1164/rccm.201908-1581ST](https://doi.org/10.1164/rccm.201908-1581ST)). Inpatient empiric alternative monotherapy / substitute for beta-lactam intolerance (cephalosporin vs respiratory fluoroquinolone). (Tier A validated).

2. **Citation Context Audit**:
   - Confirmed that citation context supports alternative therapeutic positioning, NOT mere mention in the same chapter.
   - For rejected relations sharing an approved indication (`A02A <-> A02B`, `C03C -> C03A`, `C03C -> C03D`, `C08C -> C08D`, `N02A <-> N02B`, `N05A <-> N05B`, `N05C -> N05B`), the audit confirmed that guidelines describe them as complementary combinations (e.g. multimodal analgesia for N02, sequential nephron blockade for C03), sequential escalation (WHO ladder), or disjoint disease stages/severities (transient on-demand neutralizing vs mucosal healing for A02; non-DHP contraindicated in HFrEF for C08).

3. **Absence of Improper Authority**:
   - WHO ATC and RxNorm were used strictly for code definition and hierarchy; ZERO relations received ADMIT based on WHO ATC classification.
   - DailyMed / FDA labeling alone produced ZERO ADMIT labels.

---

## 3. Blinding & Process Audit

1. **Extraction Consistency**:
   - The extraction script strictly implemented the frozen candidate selection formulas for SplitMassFN and DuplicateSiblingFP on the frozen Gate-01 run `gate-01-output-structure-signature-20260904-155810`.
   - Exactly 1,121 units were processed across the 20 high-support groups.

2. **Blinding Integrity**:
   - The blinded relation artifact (`semantic-admission-blinded-relations.json`) contained only `target_atc3`, `candidate_atc3`, and `atc2_parent`.
   - Support counts remained strictly quarantined in `semantic-admission-restricted-support.json` until after all 23 relation labels were formulated and frozen.

3. **No Retrospective Loosening**:
   - No criteria were altered after observing high support for `A02B -> A02A` (195 patients) or `N02B -> N02A` (111 patients).
   - The clinical rejection of these high-frequency relations was strictly maintained based on their complementary and sequential clinical roles.

---

## 4. Numerical Audit

| Parameter | Preregistered Rule / Target | Audited Observed Value | Status |
| :--- | :--- | :--- | :--- |
| **Calibrated Signature Units** | All units in 20 groups with AnySignature | 1,121 units | Exact match |
| **Calibrated Signature Patients** | Frozen Gate 01 total | 394 patients | Exact match |
| **Total Candidate Relations** | Extracted from 1,121 units | 67 relations | Exact match |
| **Supported Relations** | Distinct audit patients $\ge 10$ | 23 relations | Exact match |
| **Semantic A Patient Coverage** | $\ge 50.0\%$ ($197 / 394$) | 381 patients ($96.70\%$) | **PASS** |
| **Semantic A Parent Span** | $\ge 3$ ATC-2 parents | 12 parents | **PASS** |
| **Strict Admitted Relations** | Formally meeting Tier-A criteria | 4 relations (`C09A->C09C`, `J01C->J01D`, `J01D->J01M`, `J01M->J01D`) | Exact match |
| **Strict Rejected Relations** | Not alternative / complementary / disjoint | 19 relations | Exact match |
| **Strict Unresolved Relations** | Insufficient evidence | 0 relations | Exact match |
| **Semantic B Patient Coverage** | $\ge 25.0\%$ ($99 / 394$) | 75 patients ($19.04\%$) | **FAIL** ($19.04\% < 25.0\%$) |
| **Semantic B Qualifying Parents** | $\ge 3$ parents with $\ge 10$ admitted pts | 2 parents (`C09`: 11, `J01`: 65) | **FAIL** ($2 < 3$) |
| **Mechanical Decision** | Decision tree terminal node | `STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE` | **Verified** |

---

## 5. Test Isolation & Scope Boundary Audit

1. **Test Split Isolation**:
   - The test partition ($N=1,058$ patients, $1,206$ visits) remained completely unindexed, unstaged, unpredicted, unevaluated, and untouched.
   - Zero test data was read during relation extraction, support aggregation, or clinical adjudication.

2. **Model Training & Gate 02 Boundary**:
   - Zero model retraining or fine-tuning occurred.
   - Zero group-aware decoders or loss functions were implemented.
   - Gate 02 remains `NOT_AUTHORIZED`.

---

## 6. Audit Verdict

All protocol, evidence hierarchy, blinding, numeric, and boundary invariants have been satisfied.

Integrity Verdict: **`INTEGRITY_PASS`**.
The mechanical verdict `STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE` is fully authorized.
