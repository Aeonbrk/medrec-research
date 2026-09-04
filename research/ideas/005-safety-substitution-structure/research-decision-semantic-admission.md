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

Under the preregistered, support-count-blinded Semantic Admission protocol:

1. **Semantic A (Concentration Gate)**: **PASS**. The 23 supported relations ($\ge 10$ distinct Audit patients) concentrate across 381 distinct patients (96.70% of 394 calibrated signature patients) and span 12 ATC-2 parents.
2. **Semantic B (Material Strict Alternative Admission)**: **FAIL**.
   - Strict Tier-A alternative treatment evidence at the ATC-3 class resolution was confirmed for only 1 relation across 1 ATC-2 parent:
     - `C09`: `C09A` (ACE inhibitors) $\to$ `C09C` (ARBs) (11 patients)
   - Re-audit of the three candidate antibacterial relations (`J01C -> J01D`, `J01D -> J01M`, `J01M -> J01D`) under frozen protocol §8.1(4) confirmed that clinical guidelines (IDSA/ATS) support only specific agent/regimen alternatives in select infection contexts (e.g. piperacillin-tazobactam vs cefepime for empiric pseudomonal coverage; ceftriaxone vs levofloxacin in CAP for penicillin-allergic patients), rather than wholesale interchangeability between heterogeneous ATC-3 classes. Under §8.2, class heterogeneity and context-specific regimen choices fail class-level equivalence, resulting in `REJECT_NOT_ALTERNATIVE`.
   - The single admitted relation covers only **11 distinct patients** (**2.79%**), failing the preregistered $\ge 25.0\%$ threshold ($2.79\% < 25.0\%$).
   - Admitted relations span only **1 ATC-2 parent** (`C09`), failing the preregistered multi-parent requirement of $\ge 3$ parents each with $\ge 10$ admitted patients ($1 < 3$).

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

The empirical phenomenon identified in Gate 01 is genuine: the baseline model frequently misallocates mass among sibling codes sharing an ATC-2 prefix. However, support-count-blinded evidence adjudication revealed that many high-support relations correspond clinically to complementary combination therapy, disjoint treatment contexts, or coarse taxonomy co-location rather than therapeutic alternatives:

1. **Taxonomy Artifact & Disjoint Severity**: High-frequency relations such as `A02B -> A02A` (195 patients) reflect coarse anatomical co-location under WHO ATC, but represent fundamentally disjoint clinical roles (transient on-demand symptom neutralization vs chronic mucosal healing antisecretory therapy).
2. **Complementary Combination Regimens**: Relations such as `N02B -> N02A` (111 patients) and `N02A -> N02B` (32 patients) clinically correspond to foundational multimodal analgesia (where non-opioids and opioids are co-prescribed for synergistic opioid-sparing) or sequential WHO ladder escalation, rather than therapeutic substitution. Similarly, loop diuretics (`C03C`) and thiazides (`C03A`) are combined for sequential nephron blockade in refractory heart failure, not used as interchangeable substitutes.
3. **Clinical Non-Equivalence & Contraindication**: Calcium channel blockers (`C08C -> C08D`) cannot be substituted because non-dihydropyridines depress myocardial contractility and AV conduction, and are strictly contraindicated in HFrEF.
4. **Negative Control Diagnostic**: Among the 14 supported relations labeled `NAIVE_SHARED_INDICATION`, 13 failed strict semantic admission (92.9%). This confirms that shared indication alone is insufficient for therapeutic substitution.

Under this frozen supported-relation set, current ATC-3 action space, and preregistered evidence criteria, strict admitted support did not reach the required multi-parent materiality (only ACEi vs ARB in `C09` met class-resolution alternative criteria, covering 2.79% of patients in 1 parent). Therefore, the substitution premise is too narrow and heterogeneous across the wider vocabulary to sustain a general architectural claim of "safety by substitution" for the medication recommendation benchmark.

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
