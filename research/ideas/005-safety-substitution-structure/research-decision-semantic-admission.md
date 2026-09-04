<!-- markdownlint-disable MD013 -->

# Research Decision: Idea 005 Semantic Admission

- **Idea ID**: `005-safety-substitution-structure`
- **Idea Name**: Safety-Preserving Substitution Structure
- **Decision Date**: 2026-09-04
- **Formal Gate**: `semantic-admission`
- **Formal Run ID**: `gate-01-output-structure-signature-20260904-155810`
- **Protocol Commit**: `587e3f626cf8c5849553176f8f1fae3aa2eb0d84`
- **Summary**: `experiments/semantic-admission-summary.json`
- **Evidence Ledger**: `experiments/semantic-admission-ledger.md`
- **Integrity Audit**: `experiments/semantic-admission-integrity-audit.md` (`INTEGRITY_PASS`)
- **Authoritative Decision**: **`STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`**
- **Idea Status**: **`TERMINATED`**
- **Gate 02**: `NOT_AUTHORIZED`
- **Test Split**: unindexed, unstaged, unpredicted, unevaluated, and untouched (100% isolated)

---

## 1. Executive Summary

Idea 005 investigated whether model safety should be achieved through therapeutic substitution rather than blanket suppression.

- **Gate 01 Output-Structure Signature**: Established that a material ATC-2-sibling mass-allocation error phenotype exists in frozen MoleRec validation outputs and survives Dev-only per-medication threshold calibration (394 signature patients across 14 parents).
- **Semantic Admission**: Evaluated whether the empirically supported target-to-sibling relations contain a material subset supported by independent authoritative clinical guidelines as alternative-treatment structure at the repository's ATC-3 prediction resolution.

### Result

Under the preregistered, blinded Semantic Admission protocol:

1. **Semantic A (Concentration Gate)**: **PASS**. The 23 supported relations ($\ge 10$ distinct Audit patients) concentrate across 381 distinct patients (96.70% of 394 calibrated signature patients) and span 12 ATC-2 parents.
2. **Semantic B (Material Strict Alternative Admission)**: **FAIL**.
   - Strict Tier-A alternative treatment evidence was confirmed for only 4 relations across 2 ATC-2 parents:
     - `C09`: `C09A` (ACE inhibitors) $\to$ `C09C` (ARBs) (11 patients)
     - `J01`: `J01C` (Extended-spectrum penicillins) $\to$ `J01D` (Cephalosporins/Carbapenems) (10 patients)
     - `J01`: `J01D` (Cephalosporins) $\to$ `J01M` (Fluoroquinolones) (39 patients)
     - `J01`: `J01M` (Fluoroquinolones) $\to$ `J01D` (Cephalosporins) (21 patients)
   - These 4 relations cover only **75 distinct patients** (**19.04%**), failing the preregistered $\ge 25.0\%$ threshold ($19.04\% < 25.0\%$).
   - Admitted relations span only **2 ATC-2 parents** (`C09` and `J01`), failing the preregistered multi-parent requirement of $\ge 3$ parents each with $\ge 10$ admitted patients ($2 < 3$).

Pursuant to the frozen decision tree, the formal verdict is:

$$
\boxed{\text{STOP\_ATC\_STRUCTURE\_NOT\_THERAPEUTICALLY\_ADMISSIBLE}}
$$

Idea 005 is authoritatively **terminated**.

---

## 2. Scientific Interpretation

The central scientific question of Semantic Admission was:

$$
\boxed{\begin{aligned}
&\text{Does the empirically observed output-structure error phenotype have enough real}\\
&\text{clinical alternative-treatment semantics to justify building a substitution model?}
\end{aligned}}
$$

The answer is **NO** at the current ATC-3 prediction resolution.

The empirical phenomenon identified in Gate 01 is genuine: the baseline model frequently misallocates mass among sibling codes sharing an ATC-2 prefix (such as antacids vs PPIs, or opioids vs acetaminophen). However, independent clinical adjudication revealed that this empirical mass-sharing is **not** driven by clinical interchangeability:

1. **Taxonomy Artifact & Disjoint Severity**: High-frequency relations such as `A02B -> A02A` (195 patients) reflect coarse anatomical co-location under WHO ATC, but represent fundamentally disjoint clinical roles (transient on-demand symptom neutralization vs chronic mucosal healing antisecretory therapy).
2. **Complementary Combination Therapy**: Relations such as `N02B -> N02A` (111 patients) and `N02A -> N02B` (32 patients) reflect foundational multimodal analgesia (where non-opioids and opioids are deliberately co-prescribed for synergistic opioid-sparing) or sequential WHO ladder escalation, rather than therapeutic substitution. Similarly, loop diuretics (`C03C`) and thiazides (`C03A`) are combined for sequential nephron blockade in refractory heart failure, not used as interchangeable substitutes.
3. **Clinical Non-Equivalence & Contraindication**: Calcium channel blockers (`C08C -> C08D`) cannot be substituted because non-dihydropyridines depress myocardial contractility and AV conduction, and are strictly contraindicated in HFrEF.
4. **Strong Negative Control Diagnostic**: 14 of the 23 relations (60.9%) shared at least one approved indication under FDA labeling (`NAIVE_SHARED_INDICATION = true`). However, 10 of these 14 relations (71.4%) were rejected upon rigorous clinical review. This decisively validates the protocol's premise that **shared indication $\neq$ therapeutic interchangeability**.

Only two pharmacological domains exhibited genuine, guideline-backed alternative treatment positioning at the ATC-3 level:

- Renin-angiotensin inhibitors (`C09`: ACEi vs ARB in hypertension and heart failure);
- Broad-spectrum systemic antibacterials (`J01`: Penicillins vs Cephalosporins vs Fluoroquinolones in pneumonia, neutropenic fever, and sepsis).

Because these valid domains cover less than 20% of the signature population and span only two parent classes, the substitution premise is too narrow and heterogeneous across the wider vocabulary to sustain a general architectural claim of "safety by substitution" for the medication recommendation benchmark.

---

## 3. Strict Scope & Termination Bounds

1. **Route Termination**:
   The substitution-structure route is terminated before model implementation. No group-aware decoder, loss function, or substitution architecture is authorized.
2. **No Post-Hoc Rescue**:
   In accordance with research integrity policy, the route must not be rescued by:
   - loosening the semantic admission threshold;
   - replacing strict clinical admission with `NAIVE_SHARED_INDICATION`;
   - switching post-hoc to a different medical taxonomy (e.g. RxNorm, MeSH, ICD);
   - restricting the problem post-hoc solely to antibiotics or RAAS inhibitors while claiming a general solution.
3. **Test Split Untouched**:
   The test split ($N=1,058$ patients) remains 100% untouched and unpredicted.
4. **Research Memory**:
   The finding that empirical multi-label sibling errors reflect complementary combinations and taxonomy artifacts rather than therapeutic alternatives is preserved as a durable negative lesson for clinical AI benchmark research.
