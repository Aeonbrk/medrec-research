<!-- markdownlint-disable MD013 -->

# Idea 005: Safety-Preserving Substitution Structure

- **Idea ID**: `005-safety-substitution-structure`
- **Status**: `TERMINATED / STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`
- **Scientific stage**: Idea / hypothesis selection (Terminated)
- **Target venue assumption**: generic CCF-A AI/ML/KDD-family target
- **Primary method direction**: safety by substitution, not suppression
- **Gate 01**: [`experiments/gate-01-output-structure-signature.md`](experiments/gate-01-output-structure-signature.md)
- **Gate 01 Summary**: [`experiments/gate-01-summary.json`](experiments/gate-01-summary.json)
- **Gate 01 Integrity Audit**: [`experiments/gate-01-integrity-audit.md`](experiments/gate-01-integrity-audit.md) (`INTEGRITY_PASS`)
- **Gate 01 Research Decision**: [`research-decision.md`](research-decision.md) (`PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`)
- **Gate 01 Design audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md) (`DESIGN_INTEGRITY_PASS`)
- **Semantic Admission Protocol**: [`experiments/semantic-admission-protocol.md`](experiments/semantic-admission-protocol.md)
- **Semantic Admission Design Audit**: [`experiments/semantic-admission-design-integrity-audit.md`](experiments/semantic-admission-design-integrity-audit.md) (`DESIGN_INTEGRITY_PASS`)
- **Semantic Candidate Relations**: [`experiments/semantic-candidate-relations.json`](experiments/semantic-candidate-relations.json)
- **Semantic Admission Ledger**: [`experiments/semantic-admission-ledger.md`](experiments/semantic-admission-ledger.md)
- **Semantic Admission Summary**: [`experiments/semantic-admission-summary.json`](experiments/semantic-admission-summary.json)
- **Semantic Admission Integrity Audit**: [`experiments/semantic-admission-integrity-audit.md`](experiments/semantic-admission-integrity-audit.md) (`INTEGRITY_PASS`)
- **Semantic Admission Decision**: [`research-decision-semantic-admission.md`](research-decision-semantic-admission.md) (`STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`)
- **Failure Record**: [`../../memory/failures/safety-substitution-structure-semantic-admission--atc-structure-not-therapeutically-admissible.md`](../../memory/failures/safety-substitution-structure-semantic-admission--atc-structure-not-therapeutically-admissible.md)
- **Literature grounding**: [`literature-search-20260904-safety-substitution-output-structure/`](literature-search-20260904-safety-substitution-output-structure/)
- **Strict idea review**: [`idea-review.md`](idea-review.md)
- **Gate 02**: `NOT_AUTHORIZED`
- **Test split**: remains unindexed, unpredicted, and untouched (100% isolated)

## Scientific question

The candidate paper direction asked whether safety-aware medication recommendation should redirect a risky medication decision toward an acceptable alternative rather than merely removing medication probability mass.

Gate 01 answered the preliminary output-space question:

$$
\boxed{\text{Does the existing ATC-3 output space exhibit a reproducible alternative-choice mass-allocation failure at all?}}
$$

The answer was yes under frozen MoleRec validation: a material ATC-2-sibling output-structure signature remained after Dev-only per-medication threshold calibration.

Semantic Admission asked the necessary follow-up question:

$$
\boxed{\begin{aligned}
&\text{Do the empirically supported target-to-sibling relations contain a material subset}\\
&\text{supported by independent authoritative evidence as alternative treatment structure?}
\end{aligned}}
$$

The answer is **NO** at the current ATC-3 prediction resolution.

## Gate 01 result

Gate 01 used one frozen MoleRec checkpoint, a patient-disjoint validation Dev/Audit split with seed `2005`, and a Dev-only per-medication F1 threshold calibration control.

The formal verdict was:

`PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`

On the Audit partition, 394 distinct patients exhibited a calibrated `AnySignature`, and 14 ATC-2 parents had at least 10 signature patients. The independent integrity audit returned `INTEGRITY_PASS`.

The result supported only the existence of a material output-structure phenotype. It did not establish therapeutic substitution, safety benefit, undertreatment, or method superiority.

## Semantic Admission execution and findings

Semantic Admission was executed under the frozen protocol (`experiments/semantic-admission-protocol.md`) on the frozen Gate-01 restricted run `gate-01-output-structure-signature-20260904-155810`.

1. **Relation Extraction**:
   - 1,121 calibrated signature units across the 20 high-support sibling groups produced 67 candidate directed relations $y_t \to a_t$.
   - 23 relations met the preregistered threshold of $\ge 10$ distinct Audit patients.
2. **Semantic A (Concentration Gate)**: **PASS**
   - The 23 supported relations covered 381 distinct patients (96.70% $\ge 50\%$) across 12 ATC-2 parents ($\ge 3$).
3. **Blinded Evidence Adjudication**:
   - Conducted against specialty-society and national guidelines (Tier A), FDA labeling (Tier B), and WHO ATC (Tier C).
   - Only 4 relations were admitted under Tier-A evidence (`C09A -> C09C`, `J01C -> J01D`, `J01D -> J01M`, `J01M -> J01D`).
   - 19 relations were rejected because empirical sibling co-occurrence reflects complementary combinations (e.g. multimodal analgesia `N02B <-> N02A`; sequential nephron blockade `C03C -> C03A`), disjoint disease severity (`A02B <-> A02A`), or non-substitutable contraindications (`C08C -> C08D`).
   - 14 relations shared an approved indication, but 10 of these 14 (71.4%) were rejected upon clinical review, validating `NAIVE_SHARED_INDICATION` as a necessary negative control.
4. **Semantic B (Material Strict Alternative Admission)**: **FAIL**
   - Admitted relations covered only 75 distinct patients (19.04% < 25.0%).
   - Admitted relations spanned only 2 ATC-2 parents (`C09` with 11 patients, `J01` with 65 patients; required $\ge 3$ parents with $\ge 10$ patients).
5. **Integrity Audit**: **`INTEGRITY_PASS`**
   - All 10 verification invariants passed without discrepancy.

## Authoritative decision

`STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`

Idea 005 is authoritatively **terminated**.

The output-structure phenotype observed in Gate 01 is real, but it is predominantly driven by complementary combination regimens and coarse anatomical co-location, not by clinically defensible therapeutic alternative substitution.

## Stop boundary

- The substitution-structure route is terminated before model training.
- Gate 02 remains `NOT_AUTHORIZED`.
- Test split remains 100% untouched and unpredicted.
- Do not rescue the route by post-hoc loosening of criteria, alternative ontologies, or sub-cohort carving.
