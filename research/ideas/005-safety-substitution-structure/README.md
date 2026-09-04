<!-- markdownlint-disable MD013 -->

# Idea 005: Safety-Preserving Substitution Structure

- **Idea ID**: `005-safety-substitution-structure`
- **Status**: `GATE_01_PASSED / SEMANTIC_ADMISSION_DESIGNED_NOT_EXECUTED`
- **Scientific stage**: Idea / hypothesis selection
- **Target venue assumption**: generic CCF-A AI/ML/KDD-family target
- **Primary method direction**: safety by substitution, not suppression
- **Gate 01**: [`experiments/gate-01-output-structure-signature.md`](experiments/gate-01-output-structure-signature.md)
- **Gate 01 Summary**: [`experiments/gate-01-summary.json`](experiments/gate-01-summary.json)
- **Integrity Audit**: [`experiments/gate-01-integrity-audit.md`](experiments/gate-01-integrity-audit.md) (`INTEGRITY_PASS`)
- **Research Decision**: [`research-decision.md`](research-decision.md) (`PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`)
- **Design audit**: [`experiments/gate-01-design-integrity-audit.md`](experiments/gate-01-design-integrity-audit.md) (`DESIGN_INTEGRITY_PASS`)
- **Semantic Admission Protocol**: [`experiments/semantic-admission-protocol.md`](experiments/semantic-admission-protocol.md)
- **Semantic Admission Design Audit**: [`experiments/semantic-admission-design-integrity-audit.md`](experiments/semantic-admission-design-integrity-audit.md) (`DESIGN_INTEGRITY_PASS`)
- **Literature grounding**: [`literature-search-20260904-safety-substitution-output-structure/`](literature-search-20260904-safety-substitution-output-structure/)
- **Strict idea review**: [`idea-review.md`](idea-review.md)
- **Gate 02**: `NOT_AUTHORIZED`
- **Test split**: remains unindexed, unpredicted, and untouched

## Scientific question

The candidate paper direction asks whether safety-aware medication recommendation should redirect a risky medication decision toward an acceptable alternative rather than merely removing medication probability mass.

Gate 01 answered the preliminary output-space question:

$$
\boxed{\text{Does the existing ATC-3 output space exhibit a reproducible alternative-choice mass-allocation failure at all?}}
$$

The answer was yes under frozen MoleRec validation: a material ATC-2-sibling output-structure signature remained after Dev-only per-medication threshold calibration.

The current unresolved question is semantic:

$$
\boxed{\begin{aligned}
&\text{Do the empirically supported target-to-sibling relations contain a material subset}\\
&\text{supported by independent authoritative evidence as alternative treatment structure?}
\end{aligned}}
$$

No new model is authorized before that question is answered.

## Why this is materially different from Ideas 001--004

Ideas 001--004 tested low-dimensional observables or transformations on a frozen recommender for medication-level routing. Their repeated scoped failures lower the expected value of another scalar/context reranker.

Idea 005 instead asks about the structure of the multi-label output itself. The proposed downstream mechanism, if semantically admitted, would change how prediction mass is allocated among alternative actions under safety pressure. Gate 01 established only the output-structure premise.

## Candidate group semantics

The executable medication vocabulary follows the SafeDrug/MoleRec coarse `ATC3` representation obtained by truncating the upstream ATC4 mapping to four characters. For Gate 01, medications sharing the same three-character ATC 2nd-level prefix form an ATC-2 sibling candidate group when at least two ATC-3 codes are present in the frozen vocabulary.

This grouping is an output-space probe, not a therapeutic-equivalence definition:

$$
\text{same ATC-2 parent} \not\Rightarrow \text{clinically substitutable}.
$$

WHO ATC / RxNorm evidence may resolve identity and taxonomy but cannot by itself establish therapeutic alternatives.

## Gate 01 result

Gate 01 used one frozen MoleRec checkpoint, a patient-disjoint validation Dev/Audit split with seed `2005`, and a Dev-only per-medication F1 threshold calibration control.

The formal verdict was:

`PASS_OUTPUT_STRUCTURE_SIGNATURE_BEYOND_PER_DRUG_CALIBRATION`

On the Audit partition, 394 distinct patients exhibited a calibrated `AnySignature`, and 14 ATC-2 parents had at least 10 signature patients. The independent integrity audit returned `INTEGRITY_PASS`.

The result supports only the existence of a material output-structure phenotype. It does not establish therapeutic substitution, safety benefit, undertreatment, or method superiority.

## Semantic Admission

The frozen Semantic Admission protocol is the only authorized next scientific task.

For each calibrated Gate-01 signature unit in the 20 high-support sibling groups, the protocol deterministically selects one primary target-to-sibling relation before any clinical evidence is inspected. Relations occurring in at least 10 distinct Audit patients form the supported semantic review set.

The evidence hierarchy is deliberately strict:

- authoritative guideline / formulary evidence is required for strict alternative-treatment admission;
- FDA / DailyMed shared indication is corroborating evidence only;
- WHO ATC / RxNorm is identity and taxonomy evidence only.

A separate `NAIVE_SHARED_INDICATION` label acts as the strongest cheap semantic control. It cannot determine PASS.

Semantic Admission passes only if strict admitted relations cover at least 25% of the 394 calibrated-signature patients and span at least 3 ATC-2 parents with at least 10 admitted-relation patients per parent, after first establishing that supported relations cover at least 50% of calibrated-signature patients across at least 3 parents.

Possible terminal outcomes are:

- `STOP_SEMANTIC_SIGNAL_TOO_DIFFUSE`;
- `STOP_ATC_STRUCTURE_NOT_THERAPEUTICALLY_ADMISSIBLE`;
- `PASS_SEMANTIC_ADMISSION_FOR_METHOD_DESIGN`.

## What Semantic Admission PASS would mean

`PASS_SEMANTIC_ADMISSION_FOR_METHOD_DESIGN` means only:

> A material, multi-parent subset of the empirically observed ATC-sibling output-structure relations is supported by independent authoritative evidence as alternative treatment structure at the repository's prediction resolution.

PASS would authorize formulation and review of a concrete group-aware method hypothesis. It would not authorize a clinical substitution system, test evaluation, or a patient-benefit claim.

## Stop boundary

If Semantic Admission fails, the substitution route terminates before model training. Do not rescue it by loosening the definition to shared indication, changing taxonomy granularity after inspection, or selecting different relations.

Gate 02 remains `NOT_AUTHORIZED` regardless of Semantic Admission design status. Test remains untouched.
