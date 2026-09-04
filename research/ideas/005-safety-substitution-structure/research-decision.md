<!-- markdownlint-disable MD013 -->

# Research Decision: Idea 005 (Safety-Preserving Substitution Structure)

- **Idea**: `005-safety-substitution-structure`
- **Gate**: `gate-01-output-structure-signature`
- **Formal Run ID**: `gate-01-output-structure-signature-20260904-155810`
- **Harness Revision**: `4bb07d3d0050070a811f7a4e307522906470e6f7`
- **Execution Host**: `319-lab`
- **Decision Date**: 2026-09-04
- **Authoritative Verdict**: `PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`
- **Action**: `PASS_GATE_01_RETAIN_IDEA_FOR_SEMANTIC_ADMISSION`
- **Gate 02**: `NOT_AUTHORIZED`

---

## 1. Executive Summary

Idea 005 asks whether safety-aware medication recommendation can be framed around alternative-choice mass allocation (safety by substitution rather than suppression) rather than scalar reranking.

Gate 01 evaluated the preliminary empirical premise: does a material sibling-group mass-allocation error signature remain in frozen MoleRec ATC-3 validation outputs after Dev-only per-medication threshold calibration?

Gate 01 was executed on `319-lab` using the frozen MoleRec Table 1 Comparison identities, evaluating 3,919 eligible singleton-target units across 440 eligible Audit patients (from a deterministic, patient-disjoint 529 Dev / 530 Audit split with seed `2005`). The test split remained completely unindexed, unstaged, unpredicted, unevaluated, and untouched.

The preregistered mechanical decision tree yielded:

1. **Gate A (ATC-3 Group Support)**: **PASS** (20 distinct candidate groups with $\ge 50$ eligible Audit patients each, exceeding the required $\ge 3$ groups).
2. **Gate B (Raw Structural Signature Materiality)**: **PASS** (338 distinct Audit patients with `AnySignature` vs required $\ge 50$; 8 distinct ATC-2 parents each with $\ge 10$ signature patients vs required $\ge 3$).
3. **Gate C (Dev-Only Per-Medication Calibration Control)**: **PASS** (Under Dev-frozen F1-optimal per-medication thresholds, 394 distinct Audit patients exhibit `AnySignature` vs required $\ge 50$; 14 distinct ATC-2 parents each have $\ge 10$ signature patients vs required $\ge 3$).

Because all three gates passed, the mandatory mechanical verdict is:

`PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`

Independent integrity audit by `ccf-integrity-auditor` confirmed `INTEGRITY_PASS` across protocol, execution, identity, test-isolation, calibration-leakage, and numerical invariants.

---

## 2. Quantitative Evidence Summary

All figures independently verified by `ccf-integrity-auditor` from restricted artifacts on 319:

### Cohort Support ($N_{Validation} = 1,059$, $N_{Dev} = 529$, $N_{Audit} = 530$)

| Metric | Observed Value | Gate Requirement | Status |
| :--- | :---: | :---: | :---: |
| Candidate sibling groups ($\|G\| \ge 2$) | 31 | — | Protocol definition |
| Eligible candidate groups in Audit | 31 | — | Descriptive |
| Eligible Audit units ($\|M_t \cap G\| = 1$) | 3,919 | — | Descriptive |
| Eligible Audit patients | 440 | — | Descriptive |
| Candidate groups with $\ge 50$ eligible Audit patients | 20 | $\ge 3$ | **Gate A PASSED** |

### Policy Signatures on Audit Cohort ($N_{Eligible} = 440$ patients, $N_{Units} = 3,919$)

| Metric | Raw Policy ($0.5$) | Calibrated Policy (Dev-F1) | Materiality Floor |
| :--- | :---: | :---: | :---: |
| SplitMassFN Units | 71 | 50 | — |
| SplitMassFN Patients | 65 | 46 | — |
| DuplicateSiblingFP Units | 680 | 1,122 | — |
| DuplicateSiblingFP Patients | 326 | 391 | — |
| AnySignature Units | 751 | 1,172 | — |
| AnySignature Patients | 338 | 394 | $\ge 50$ (Gate B / C) |
| ATC-2 Parents with $\ge 10$ Signature Patients | 8 | 14 | $\ge 3$ (Gate B / C) |
| Gate Status | **Gate B PASSED** | **Gate C PASSED** | — |

---

## 3. Scientific Interpretation

The scientific finding is strictly bounded by the frozen protocol:

> **A material ATC-2-sibling output-structure error signature survives Dev-only per-medication threshold calibration under frozen MoleRec validation.**

This confirms that the observed split-mass false negative and duplicate-sibling false positive phenotypes are not merely trivial artifacts of a single global 0.5 decision threshold that could be eliminated by independent per-label probability calibration. Instead, the multi-label score mass across ATC-2 sibling groups frequently exhibits either mass dispersion (mass $\ge 0.5$ across siblings while missing the singleton target) or redundant co-emission (predicting both the target and non-target siblings).

---

## 4. Strict Non-Expansion Boundaries

This Gate 01 PASS does **NOT** prove or imply:

1. **Therapeutic substitution is established**: ATC-2 prefix grouping is strictly output-space geometry. Sibling codes share pharmacological/therapeutic sub-classifications in ATC, but are not interchangeable drugs.
2. **Safety by substitution is established**: The result does not establish that substituting a non-target sibling for a target medication improves clinical safety or prevents adverse interactions.
3. **Undertreatment is proven**: The result does not prove that missing a target medication while assigning probability mass to siblings causes clinical undertreatment.
4. **ATC siblings are acceptable alternatives**: No clinical guideline, indication mapping, or pharmacological equivalence has been audited.
5. **A proposed model will improve recommendation**: No group-aware decoder, hierarchical loss, or constrained inference model has been implemented or evaluated.
6. **Generalization beyond frozen validation**: No claim is made regarding unseen test data, other baseline models (e.g. SafeDrug, GAMENet), or other data distributions.

---

## 5. Decision & Next Steps

1. **Idea 005 Status**: Retained at Idea / Hypothesis Selection stage.
2. **Gate 02 Status**: **`NOT_AUTHORIZED`**. Gate 02 must not be designed, implemented, or executed in this session.
3. **Test Split**: Remains **`UNTOUCHED`**, **`UNINDEXED`**, and **`UNPREDICTED`**.
4. **Next CCFA Sequence**:
   - The only authorized next step is designing a **Semantic Admission Protocol** for independent review.
   - The Semantic Admission protocol must evaluate whether the 20 high-support ATC-2 sibling groups identified in Gate 01 contain clinically and pharmacologically defensible therapeutic alternatives under external evidence (e.g., ATC hierarchy documentation, pharmacological indications, clinical guidelines).
   - If semantic admission fails or finds that ATC siblings are not clinically viable alternatives, the substitution route terminates without model training.
   - No semantic admission protocol is executed in this session.
